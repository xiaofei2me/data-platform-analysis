"""M3.1 Business Understanding Quality Assessment。

目标：

    在 M3 第一阶段（业务术语 / Domain / Object 候选 + 证据）之上只做质量评估：
    标出 UNKNOWN / AMBIGUOUS 及其主因，复核 Evidence 构成与 Confidence 分布，
    给出核心表优先复核顺序，为 M3.2 业务过程识别提供质量基线。

输入（只读，不访问 DataWorks / MaxCompute API，不读取 source/）：

    analysis/business/tables.json
    analysis/business/domains.json
    analysis/business/objects.json
    analysis/business/terms.json
    analysis/inventory/tables.json
    analysis/inventory/columns.json
    analysis/sql/table-references.json
    analysis/lineage/table-lineage.json
    analysis/lineage/core-table-candidates.json

输出：

    analysis/business/quality-assessment.json
    analysis/business/quality-assessment.md
    analysis/business/review-checklist.md

原则：

1. 只评估不识别：不修改 M3 提取规则、不选 winner（不产生 best / primary /
   final domain）、不产生业务结论，不输出「某表属于销售域 / 应改成 DWD」这类判断。
2. 不修改已有 M3 产物（terms / tables / domains / objects / summary.md 原样）。
3. 输入缺失或结构非法 → 明确报错 + 非零退出，不自动回退执行 M2 / analyze-business。
4. 输出 deterministic：无时间戳 / UUID / 随机抽样；
   样本按稳定排序截断到 QUALITY_SAMPLE_LIMIT，checklist 每区限行并注明总数。
5. 不使用 LLM / Embedding / Vector DB / 外部 API。
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...config import PROJECT_ROOT
from ...io_utils import ensure_dir, write_json, write_text
from ..models import (
    BUSINESS_CONFIDENCE_HIGH,
    BUSINESS_CONFIDENCE_ORDER,
    BUSINESS_CONFIDENCE_UNKNOWN,
    BUSINESS_EVIDENCE_COLUMN_COMMENT,
    BUSINESS_EVIDENCE_COLUMN_NAME,
    BUSINESS_EVIDENCE_LINEAGE,
    BUSINESS_EVIDENCE_ORDER,
    BUSINESS_EVIDENCE_SQL,
    BUSINESS_NAMING_EVIDENCE_TYPES,
    QUALITY_AMBIGUOUS_CONFLICT,
    QUALITY_AMBIGUOUS_DOMINANT,
    QUALITY_AMBIGUOUS_KEYWORD,
    QUALITY_AMBIGUOUS_MULTI_DOMAIN,
    QUALITY_AMBIGUOUS_REASON_ORDER,
    QUALITY_AMBIGUOUS_UNRESOLVED,
    QUALITY_CHECKLIST_ROW_LIMIT,
    QUALITY_CONFIDENCE_RANK,
    QUALITY_DIVERSITY_BUCKETS,
    QUALITY_SAMPLE_LIMIT,
    QUALITY_STRONG_MIN_DIVERSITY,
    QUALITY_STRONG_MIN_RANK,
    QUALITY_UNKNOWN_COMMENT,
    QUALITY_UNKNOWN_CORE,
    QUALITY_UNKNOWN_INSUFFICIENT,
    QUALITY_UNKNOWN_NAMING,
    QUALITY_UNKNOWN_REASON_ORDER,
    QUALITY_UNKNOWN_SPARSE,
    QUALITY_UNKNOWN_SQL,
    BusinessQualityResult,
    QualityChecklistRow,
    QualitySample,
    evidence_type_sort_key,
    numeric_id_sort_key,
    quality_diversity_bucket,
)
from ..naming import qualify_table_ref
from ..reports import render_business_quality_report, render_review_checklist

logger = logging.getLogger(__name__)

# ============================================================
# 输入与输出布局
# ============================================================

QUALITY_INPUT_FILES: tuple[tuple[str, str, str], ...] = (
    ("business/tables.json", "tables", "tables"),
    ("business/domains.json", "domains", "domains"),
    ("business/objects.json", "objects", "objects"),
    ("business/terms.json", "terms", "terms"),
    ("inventory/tables.json", "tables", "inventory_tables"),
    ("inventory/columns.json", "columns", "inventory_columns"),
    ("sql/table-references.json", "references", "references"),
    ("lineage/table-lineage.json", "edges", "edges"),
    ("lineage/core-table-candidates.json", "candidates", "candidates"),
)
"""M3.1 依赖的 M2 / M3 产物（相对 analysis/ 路径 → JSON 数组字段名 → 属性名）。"""

OUTPUT_FILES: tuple[str, ...] = (
    "quality-assessment.json",
    "quality-assessment.md",
    "review-checklist.md",
)
"""M3.1 产物文件名（固定顺序）；只覆盖这三个文件，不动已有 M3 产物。"""

LAYER_UNDETERMINED = "(未确定)"
"""warehouse_layer / candidate_sub_layer 为空时的聚合与展示值。"""

DERIVED_EVIDENCE_TYPES: frozenset[str] = frozenset(
    {BUSINESS_EVIDENCE_SQL, BUSINESS_EVIDENCE_LINEAGE}
)
"""派生证据（SQL / 血缘）；direct_only 表示全部证据都是命名类直接证据。"""


class BusinessQualityError(RuntimeError):
    """M3.1 无法继续的输入 / 结构错误。"""


def _display_path(path: Path) -> str:
    """日志与报告中展示的路径：项目根内用相对路径，其余保持绝对。"""

    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))

    except ValueError:
        return str(path)


# ============================================================
# 通用小工具
# ============================================================


def _text(value: Any) -> str | None:
    """把值转成非空字符串，空值返回 None。"""

    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _table_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """与 M3 相同的表稳定排序键。"""

    return (
        numeric_id_sort_key(record.get("workspace_id")),
        str(record.get("project") or ""),
        str(record.get("schema") or ""),
        str(record.get("table") or ""),
        str(record.get("table_key") or ""),
    )


def _workspace_projects(tables: Sequence[Mapping[str, Any]]) -> dict[int, str]:
    """workspace_id → project，用于补齐 SQL 中的裸表引用。"""

    projects: dict[int, str] = {}

    for table in sorted(tables, key=_table_sort_key):
        workspace_id = table.get("workspace_id")
        project = _text(table.get("project"))

        if isinstance(workspace_id, int) and project:
            projects.setdefault(workspace_id, project)

    return projects


def _dict_values(records: Any, key: str, path: Path) -> list[dict[str, Any]]:
    """校验并取出 JSON 数组里的对象条目。"""

    if not isinstance(records, list):
        raise BusinessQualityError(f"缺少 {key} 数组：{path}")

    items: list[dict[str, Any]] = []

    for position, entry in enumerate(records):
        if not isinstance(entry, dict):
            raise BusinessQualityError(f"{key}[{position}] 不是对象：{path}")

        items.append(entry)

    return items


# ============================================================
# M2 / M3 产物读取
# ============================================================


@dataclass
class QualityInputs:
    """M3.1 读取到的 M2 / M3 产物（只做结构校验，不改写）。"""

    tables: list[dict[str, Any]] = field(default_factory=list)
    domains: list[dict[str, Any]] = field(default_factory=list)
    objects: list[dict[str, Any]] = field(default_factory=list)
    terms: list[dict[str, Any]] = field(default_factory=list)
    inventory_tables: list[dict[str, Any]] = field(default_factory=list)
    inventory_columns: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)


def read_quality_inputs(analysis_dir: Path) -> QualityInputs:
    """读取 M3.1 依赖的全部 M2 / M3 产物。

    任何输入缺失都明确报错，不自动回退执行 M2 / analyze-business。
    """

    missing = [
        relative
        for relative, _key, _attr in QUALITY_INPUT_FILES
        if not (analysis_dir / relative).exists()
    ]

    if missing:
        raise BusinessQualityError(
            "M2 / M3 产物缺失，无法执行 M3.1 Business Quality Assessment："
            f"{'、'.join(missing)}（目录：{_display_path(analysis_dir)}）；"
            "请先执行 analyze 生成 M2 产物、analyze-business 生成 M3 产物"
        )

    def load(relative: str, key: str) -> list[dict[str, Any]]:
        path = analysis_dir / relative

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))

        except json.JSONDecodeError as exc:
            raise BusinessQualityError(f"产物不是合法的 JSON：{path}（{exc}）") from exc

        if not isinstance(raw, dict):
            raise BusinessQualityError(f"产物根节点不是对象：{path}")

        return _dict_values(raw.get(key), key, path)

    inputs = QualityInputs()

    for relative, key, attr in QUALITY_INPUT_FILES:
        setattr(inputs, attr, load(relative, key))

    logger.info(
        "M3.1 输入已读取：%s（business table=%s，inventory table=%s，reference=%s，edge=%s）",
        _display_path(analysis_dir),
        len(inputs.tables),
        len(inputs.inventory_tables),
        len(inputs.references),
        len(inputs.edges),
    )

    return inputs


# ============================================================
# 信号索引
# ============================================================


def _index_table_comments(tables: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    """table_key(casefold) → 是否有表注释。"""

    index: dict[str, bool] = {}

    for record in sorted(tables, key=_table_sort_key):
        key = _text(record.get("table_key")) or _text(record.get("table"))

        if not key:
            continue

        folded = key.casefold()
        index[folded] = index.get(folded, False) or bool(_text(record.get("comment")))

    return index


def _index_column_comments(columns: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    """table_key(casefold) → 是否有字段注释。"""

    index: dict[str, bool] = {}

    for record in sorted(
        columns,
        key=lambda item: (
            str(item.get("table_key") or ""),
            str(item.get("column_name") or ""),
        ),
    ):
        key = _text(record.get("table_key")) or _text(record.get("table"))

        if not key:
            continue

        folded = key.casefold()

        if _text(record.get("comment")):
            index[folded] = True

        else:
            index.setdefault(folded, False)

    return index


def _sql_reference_keys(
    references: Sequence[Mapping[str, Any]],
    workspace_projects: Mapping[int, str],
) -> set[str]:
    """被 SQL 引用的表（补齐裸表名后 casefold）。"""

    keys: set[str] = set()

    for record in references:
        workspace_id = record.get("workspace_id")
        project = workspace_projects.get(workspace_id) if isinstance(workspace_id, int) else None

        for field_name in ("source_tables", "target_tables"):
            values = record.get(field_name)

            if not isinstance(values, list):
                continue

            for item in values:
                if not isinstance(item, str):
                    continue

                table_ref = item.strip()

                if table_ref:
                    keys.add(qualify_table_ref(table_ref, project).casefold())

    return keys


def _lineage_edge_keys(edges: Sequence[Mapping[str, Any]]) -> set[str]:
    """参与血缘的表（source_key / target_key casefold）。"""

    keys: set[str] = set()

    for record in edges:
        for field_name in ("source_key", "target_key"):
            value = _text(record.get(field_name))

            if value:
                keys.add(value.casefold())

    return keys


def _core_file_keys(candidates: Sequence[Mapping[str, Any]]) -> set[str]:
    """M2.4 核心表候选文件里的 table_key（casefold）。"""

    return {
        key.casefold()
        for record in candidates
        if (key := _text(record.get("table_key")))
    }


# ============================================================
# 分类规则
# ============================================================


def _unknown_reason(signals: Mapping[str, Any]) -> str:
    """UNKNOWN 主因级联：注释 → SQL → 命名 → 血缘 → 稀疏。"""

    if signals["has_table_comment"] or signals["has_column_comment"]:
        return QUALITY_UNKNOWN_COMMENT

    if signals["has_sql_reference"]:
        return QUALITY_UNKNOWN_SQL

    if signals["business_term_count"]:
        return QUALITY_UNKNOWN_NAMING

    if signals["has_lineage_edge"]:
        return QUALITY_UNKNOWN_INSUFFICIENT

    return QUALITY_UNKNOWN_SPARSE


def _candidate_types(candidate: Mapping[str, Any]) -> set[str]:
    """候选证据的 evidence type 集合。"""

    return {
        str(entry.get("type") or "")
        for entry in candidate.get("evidence") or []
        if isinstance(entry, dict)
    }


def _candidate_locations(candidate: Mapping[str, Any]) -> set[tuple[str, ...]]:
    """候选证据的去重位置集合。"""

    return {
        _location_key(entry)
        for entry in candidate.get("evidence") or []
        if isinstance(entry, dict)
    }


def _ambiguous_reason(candidates: Sequence[Mapping[str, Any]]) -> str:
    """AMBIGUOUS 主因分类（至少两个候选）。"""

    ranks = [
        QUALITY_CONFIDENCE_RANK.get(str(candidate.get("confidence") or ""), 0)
        for candidate in candidates
    ]
    ranks.sort(reverse=True)

    strong_count = sum(
        1
        for candidate in candidates
        if QUALITY_CONFIDENCE_RANK.get(str(candidate.get("confidence") or ""), 0)
        >= QUALITY_STRONG_MIN_RANK
        and len(_candidate_types(candidate)) >= QUALITY_STRONG_MIN_DIVERSITY
    )
    location_sets = [_candidate_locations(candidate) for candidate in candidates]
    shared = bool(set.intersection(*location_sets)) if location_sets else False
    type_sets = [_candidate_types(candidate) for candidate in candidates]
    disjoint = any(
        left.isdisjoint(right)
        for index, left in enumerate(type_sets)
        for right in type_sets[index + 1 :]
    )
    top_rank = ranks[0] if ranks else 0
    second_rank = ranks[1] if len(ranks) > 1 else 0

    if strong_count >= 2 and not shared:
        return QUALITY_AMBIGUOUS_CONFLICT if disjoint else QUALITY_AMBIGUOUS_MULTI_DOMAIN

    if strong_count == 1 and top_rank > second_rank:
        return QUALITY_AMBIGUOUS_DOMINANT

    if shared:
        return QUALITY_AMBIGUOUS_KEYWORD

    if disjoint:
        return QUALITY_AMBIGUOUS_CONFLICT

    return QUALITY_AMBIGUOUS_UNRESOLVED


def _location_key(entry: Mapping[str, Any]) -> tuple[str, ...]:
    """证据去重位置：列级 / 语句级 / 血缘边 / 表级。"""

    evidence_type = str(entry.get("type") or "")

    if evidence_type in (BUSINESS_EVIDENCE_COLUMN_NAME, BUSINESS_EVIDENCE_COLUMN_COMMENT):
        return (
            evidence_type,
            str(entry.get("table_key") or ""),
            str(entry.get("column_name") or ""),
        )

    if evidence_type == BUSINESS_EVIDENCE_SQL:
        return (
            evidence_type,
            str(entry.get("workspace_id") or ""),
            str(entry.get("file_id") or ""),
            str(entry.get("statement_id") or ""),
        )

    if evidence_type == BUSINESS_EVIDENCE_LINEAGE:
        return (
            evidence_type,
            str(entry.get("source_table") or ""),
            str(entry.get("target_table") or ""),
        )

    return (evidence_type, str(entry.get("table_key") or ""))


def _format_candidate(candidate: Mapping[str, Any], key_field: str) -> str:
    """候选的紧凑写法：key(confidence)。"""

    return f"{candidate.get(key_field) or ''}({candidate.get('confidence') or ''})"


def _evidence_digest(
    evidence: Sequence[Mapping[str, Any]],
    signals: Mapping[str, Any],
) -> str:
    """checklist 的压缩证据摘要。"""

    if not evidence:
        return (
            f"signals: table_comment={'y' if signals['has_table_comment'] else 'n'}, "
            f"column_comment={'y' if signals['has_column_comment'] else 'n'}, "
            f"sql={'y' if signals['has_sql_reference'] else 'n'}, "
            f"lineage={'y' if signals['has_lineage_edge'] else 'n'}, "
            f"terms={signals['business_term_count']}"
        )

    type_counts = Counter(str(entry.get("type") or "") for entry in evidence)
    ordered = sorted(type_counts, key=lambda item: (evidence_type_sort_key(item), item))
    types_text = "+".join(f"{item}×{type_counts[item]}" for item in ordered)

    return f"entries={len(evidence)}, diversity={len(type_counts)}, types={types_text}"


# ============================================================
# 样本与清单构建
# ============================================================


def _build_sample(
    *,
    record: Mapping[str, Any],
    signals: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    domain_candidates: Sequence[Mapping[str, Any]],
    object_candidates: Sequence[Mapping[str, Any]],
    unknown_reason: str | None,
    ambiguous_reason: str | None,
) -> QualitySample:
    """构建一条质量评估样本。"""

    evidence_types = [str(entry.get("type") or "") for entry in evidence]
    type_counts = Counter(evidence_types)
    is_core = bool(record.get("is_core_candidate"))
    reason_tags: list[str] = []

    if unknown_reason is not None:
        reason_tags.append(unknown_reason)

        if is_core:
            reason_tags.append(QUALITY_UNKNOWN_CORE)

    if ambiguous_reason is not None:
        reason_tags.append(ambiguous_reason)

    return QualitySample(
        table_key=str(record.get("table_key") or ""),
        workspace_id=int(record.get("workspace_id") or 0),
        project=str(record.get("project") or ""),
        table=str(record.get("table") or ""),
        warehouse_layer=_text(record.get("warehouse_layer")),
        candidate_sub_layer=_text(record.get("candidate_sub_layer")),
        is_core_candidate=is_core,
        candidate_domains=[_format_candidate(item, "domain") for item in domain_candidates],
        candidate_objects=[_format_candidate(item, "object") for item in object_candidates],
        evidence_summary={
            "entry_count": len(evidence),
            "source_count": len({_location_key(entry) for entry in evidence}),
            "diversity": len(type_counts),
            "by_source_type": {
                evidence_type: type_counts[evidence_type]
                for evidence_type in sorted(
                    type_counts,
                    key=lambda item: (evidence_type_sort_key(item), item),
                )
            },
        },
        unknown_reason=unknown_reason,
        ambiguous_reason=ambiguous_reason,
        reason_tags=reason_tags,
        signals=dict(signals),
    )


def _build_checklist_row(
    priority: int,
    *,
    record: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    signals: Mapping[str, Any],
    domain_candidates: Sequence[Mapping[str, Any]],
    object_candidates: Sequence[Mapping[str, Any]],
    reason: str,
) -> QualityChecklistRow:
    """构建 review-checklist.md 的一行。"""

    prefix = "unknown:" if priority == 1 else "ambiguous:"

    return QualityChecklistRow(
        priority=priority,
        table=str(record.get("table_key") or ""),
        domain_candidates=", ".join(
            _format_candidate(item, "domain") for item in domain_candidates
        )
        or "-",
        object_candidates=", ".join(
            _format_candidate(item, "object") for item in object_candidates
        )
        or "-",
        evidence=_evidence_digest(evidence, signals),
        note=f"{prefix}{reason}",
    )


def _top_terms(counter: Counter[str]) -> list[dict[str, Any]]:
    """按（表数降序，词升序）取前 QUALITY_SAMPLE_LIMIT 个业务词。"""

    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))

    return [
        {"term": term, "table_count": count}
        for term, count in ranked[:QUALITY_SAMPLE_LIMIT]
    ]


# ============================================================
# 质量评估构建
# ============================================================


def build_business_quality(inputs: QualityInputs) -> BusinessQualityResult:
    """从 M2 / M3 产物构建 M3.1 质量评估结果（不读写文件）。"""

    tables = sorted(inputs.tables, key=_table_sort_key)

    table_comment_flags = _index_table_comments(inputs.inventory_tables)
    column_comment_flags = _index_column_comments(inputs.inventory_columns)
    sql_reference_keys = _sql_reference_keys(
        inputs.references,
        _workspace_projects(inputs.inventory_tables),
    )
    lineage_keys = _lineage_edge_keys(inputs.edges)
    core_file_keys = _core_file_keys(inputs.candidates)

    unknown_reason_counts: Counter[str] = Counter()
    unknown_layer_counts: Counter[str] = Counter()
    unknown_sub_layer_counts: Counter[str] = Counter()
    unknown_term_counts: Counter[str] = Counter()
    ambiguous_reason_counts: Counter[str] = Counter()
    ambiguous_term_counts: Counter[str] = Counter()
    ambiguous_domain_tables = 0
    ambiguous_object_tables = 0
    ambiguous_both_tables = 0

    source_entry_counts: Counter[str] = Counter()
    source_table_counts: Counter[str] = Counter()
    source_locations: dict[str, set[tuple[str, ...]]] = {}
    diversity_counts: Counter[str] = Counter()
    candidate_diversity: dict[str, Counter[str]] = {"domain": Counter(), "object": Counter()}
    confidence_counts: dict[str, Counter[str]] = {"domain": Counter(), "object": Counter()}
    high_diversity_counts: Counter[str] = Counter()

    table_count_with_evidence = 0
    direct_only_table_count = 0
    repeated_keyword_table_count = 0
    high_total = 0
    high_naming_only = 0
    high_with_sql = 0
    high_with_lineage = 0
    high_repeated_keyword = 0
    high_single_keyword = 0

    covered_count = 0
    unknown_count = 0
    ambiguous_count = 0
    core_count = 0
    core_unknown_count = 0
    core_ambiguous_count = 0
    core_high_count = 0
    core_low_evidence_count = 0
    core_flag_mismatch_count = 0

    samples_unknown: list[QualitySample] = []
    samples_ambiguous: list[QualitySample] = []
    samples_core_unknown: list[QualitySample] = []
    samples_core_ambiguous: list[QualitySample] = []
    mismatch_samples: list[dict[str, Any]] = []
    checklist: list[QualityChecklistRow] = []

    for record in tables:
        table_key = str(record.get("table_key") or "")
        lookup_key = table_key.casefold()

        evidence = [entry for entry in record.get("evidence") or [] if isinstance(entry, dict)]
        domain_candidates = [
            item for item in record.get("domain_candidates") or [] if isinstance(item, dict)
        ]
        object_candidates = [
            item
            for item in record.get("business_object_candidates") or []
            if isinstance(item, dict)
        ]
        business_terms = [str(term) for term in record.get("business_terms") or []]
        is_core = bool(record.get("is_core_candidate"))
        is_unknown = not domain_candidates and not object_candidates
        is_ambiguous = len(domain_candidates) > 1 or len(object_candidates) > 1

        signals: dict[str, Any] = {
            "has_table_comment": table_comment_flags.get(lookup_key, False),
            "has_column_comment": column_comment_flags.get(lookup_key, False),
            "has_sql_reference": lookup_key in sql_reference_keys,
            "has_lineage_edge": lookup_key in lineage_keys,
            "business_term_count": len(business_terms),
        }

        unknown_reason_value = _unknown_reason(signals)
        unknown_reason = unknown_reason_value if is_unknown else None

        all_candidates = [*domain_candidates, *object_candidates]
        ambiguous_reason_value = (
            _ambiguous_reason(all_candidates) if is_ambiguous else QUALITY_AMBIGUOUS_UNRESOLVED
        )
        ambiguous_reason = ambiguous_reason_value if is_ambiguous else None

        evidence_types = [str(entry.get("type") or "") for entry in evidence]
        type_set = set(evidence_types)
        diversity = len(type_set)
        keyword_counts = Counter(str(entry.get("keyword") or "") for entry in evidence)

        diversity_counts[quality_diversity_bucket(diversity)] += 1

        if evidence:
            table_count_with_evidence += 1

            if type_set.isdisjoint(DERIVED_EVIDENCE_TYPES):
                direct_only_table_count += 1

            if any(count >= 2 for count in keyword_counts.values()):
                repeated_keyword_table_count += 1

            for evidence_type in type_set:
                source_table_counts[evidence_type] += 1

            for entry, evidence_type in zip(evidence, evidence_types, strict=True):
                source_entry_counts[evidence_type] += 1
                source_locations.setdefault(evidence_type, set()).add(_location_key(entry))

        for category, candidates in (
            ("domain", domain_candidates),
            ("object", object_candidates),
        ):
            for candidate in candidates:
                confidence = str(candidate.get("confidence") or "")
                confidence_counts[category][confidence or BUSINESS_CONFIDENCE_UNKNOWN] += 1

                candidate_types = _candidate_types(candidate)
                candidate_diversity[category][
                    quality_diversity_bucket(len(candidate_types))
                ] += 1

                if confidence != BUSINESS_CONFIDENCE_HIGH:
                    continue

                high_total += 1
                high_diversity_counts[quality_diversity_bucket(len(candidate_types))] += 1

                if candidate_types and candidate_types <= set(BUSINESS_NAMING_EVIDENCE_TYPES):
                    high_naming_only += 1

                if BUSINESS_EVIDENCE_SQL in candidate_types:
                    high_with_sql += 1

                if BUSINESS_EVIDENCE_LINEAGE in candidate_types:
                    high_with_lineage += 1

                candidate_keywords = Counter(
                    str(entry.get("keyword") or "")
                    for entry in candidate.get("evidence") or []
                    if isinstance(entry, dict)
                )

                if any(count >= 2 for count in candidate_keywords.values()):
                    high_repeated_keyword += 1

                if len(candidate_keywords) == 1:
                    high_single_keyword += 1

        has_high_candidate = any(
            str(candidate.get("confidence") or "") == BUSINESS_CONFIDENCE_HIGH
            for candidate in all_candidates
        )

        if not is_unknown:
            covered_count += 1

        if is_unknown:
            unknown_count += 1
            unknown_reason_counts[unknown_reason_value] += 1
            unknown_layer_counts[str(record.get("warehouse_layer") or LAYER_UNDETERMINED)] += 1
            unknown_sub_layer_counts[
                str(record.get("candidate_sub_layer") or LAYER_UNDETERMINED)
            ] += 1

            for term in business_terms:
                unknown_term_counts[term] += 1

        if is_ambiguous:
            ambiguous_count += 1
            ambiguous_reason_counts[ambiguous_reason_value] += 1
            domain_flag = len(domain_candidates) > 1
            object_flag = len(object_candidates) > 1
            ambiguous_domain_tables += int(domain_flag)
            ambiguous_object_tables += int(object_flag)
            ambiguous_both_tables += int(domain_flag and object_flag)

            for term in business_terms:
                ambiguous_term_counts[term] += 1

        if is_core:
            core_count += 1
            core_unknown_count += int(is_unknown)
            core_ambiguous_count += int(is_ambiguous)
            core_high_count += int(has_high_candidate)
            core_low_evidence_count += int(diversity <= 1)

        if is_core != (lookup_key in core_file_keys):
            core_flag_mismatch_count += 1

            if len(mismatch_samples) < QUALITY_SAMPLE_LIMIT:
                mismatch_samples.append(
                    {
                        "table_key": table_key,
                        "tables_flag": is_core,
                        "core_file_flag": lookup_key in core_file_keys,
                    }
                )

        sample: QualitySample | None = None

        if is_unknown or is_ambiguous:
            sample = _build_sample(
                record=record,
                signals=signals,
                evidence=evidence,
                domain_candidates=domain_candidates,
                object_candidates=object_candidates,
                unknown_reason=unknown_reason,
                ambiguous_reason=ambiguous_reason,
            )

            if is_unknown and len(samples_unknown) < QUALITY_SAMPLE_LIMIT:
                samples_unknown.append(sample)

            if is_ambiguous and len(samples_ambiguous) < QUALITY_SAMPLE_LIMIT:
                samples_ambiguous.append(sample)

            if is_core and is_unknown and len(samples_core_unknown) < QUALITY_SAMPLE_LIMIT:
                samples_core_unknown.append(sample)

            if is_core and is_ambiguous and len(samples_core_ambiguous) < QUALITY_SAMPLE_LIMIT:
                samples_core_ambiguous.append(sample)

        # 清单三区：核心表优先，行数上限在渲染时按区截断并注明总数。
        if is_unknown and is_core:
            checklist.append(
                _build_checklist_row(
                    1,
                    record=record,
                    evidence=evidence,
                    signals=signals,
                    domain_candidates=domain_candidates,
                    object_candidates=object_candidates,
                    reason=unknown_reason_value,
                )
            )

        elif is_ambiguous and is_core:
            checklist.append(
                _build_checklist_row(
                    2,
                    record=record,
                    evidence=evidence,
                    signals=signals,
                    domain_candidates=domain_candidates,
                    object_candidates=object_candidates,
                    reason=ambiguous_reason_value,
                )
            )

        elif is_ambiguous:
            checklist.append(
                _build_checklist_row(
                    3,
                    record=record,
                    evidence=evidence,
                    signals=signals,
                    domain_candidates=domain_candidates,
                    object_candidates=object_candidates,
                    reason=ambiguous_reason_value,
                )
            )

    # 按优先级分组；稳定排序保证同一优先级内仍是表的确定性顺序。
    checklist.sort(key=lambda row: row.priority)

    summary: dict[str, Any] = {
        "table_count": len(tables),
        "term_count": len(inputs.terms),
        "domain_count": len(inputs.domains),
        "object_count": len(inputs.objects),
        "unknown_count": unknown_count,
        "ambiguous_count": ambiguous_count,
        "covered_count": covered_count,
        "core_count": core_count,
        "core_unknown_count": core_unknown_count,
        "core_ambiguous_count": core_ambiguous_count,
    }

    unknown_section: dict[str, Any] = {
        "count": unknown_count,
        "note": (
            "UNKNOWN 只表示现有词典与证据无法给出 Domain / Object 候选，"
            "不代表表没有业务含义；core_unknown_count 是与核心表候选的重叠标记，"
            "不计入 by_reason 合计。"
        ),
        "by_reason": {
            reason: unknown_reason_counts.get(reason, 0)
            for reason in QUALITY_UNKNOWN_REASON_ORDER
        },
        "core_unknown_count": core_unknown_count,
        "by_layer": dict(sorted(unknown_layer_counts.items())),
        "by_sub_layer": dict(sorted(unknown_sub_layer_counts.items())),
        "top_terms": _top_terms(unknown_term_counts),
        "samples": [sample.to_dict() for sample in samples_unknown],
    }

    ambiguous_section: dict[str, Any] = {
        "count": ambiguous_count,
        "note": (
            "AMBIGUOUS = 同时存在多个 Domain 或多个 Object 候选，全部保留待人工判定；"
            "count = domain + object − domain_and_object（by_type 可重叠）；"
            "M3 summary.md 的 AMBIGUOUS 只统计多个 Domain 候选。"
        ),
        "by_reason": {
            reason: ambiguous_reason_counts.get(reason, 0)
            for reason in QUALITY_AMBIGUOUS_REASON_ORDER
        },
        "by_type": {
            "domain": ambiguous_domain_tables,
            "object": ambiguous_object_tables,
            "domain_and_object": ambiguous_both_tables,
        },
        "top_terms": _top_terms(ambiguous_term_counts),
        "samples": [sample.to_dict() for sample in samples_ambiguous],
    }

    evidence_quality_section: dict[str, Any] = {
        "note": (
            "diversity 是证据类型数（0 / 1 / 2 / 3+），不等于 confidence；"
            "source_count 是该类型下去重后的证据位置数；"
            "entry_count 保留同一关键词被多个来源命中的重复计数。"
        ),
        "table_count_with_evidence": table_count_with_evidence,
        "direct_only_table_count": direct_only_table_count,
        "repeated_keyword_table_count": repeated_keyword_table_count,
        "by_source_type": {
            evidence_type: {
                "entry_count": source_entry_counts.get(evidence_type, 0),
                "source_count": len(source_locations.get(evidence_type, set())),
                "table_count": source_table_counts.get(evidence_type, 0),
            }
            for evidence_type in BUSINESS_EVIDENCE_ORDER
        },
        "by_diversity": {
            bucket: diversity_counts.get(bucket, 0) for bucket in QUALITY_DIVERSITY_BUCKETS
        },
        "candidate_by_diversity": {
            "domain": {
                bucket: candidate_diversity["domain"].get(bucket, 0)
                for bucket in QUALITY_DIVERSITY_BUCKETS
            },
            "object": {
                bucket: candidate_diversity["object"].get(bucket, 0)
                for bucket in QUALITY_DIVERSITY_BUCKETS
            },
        },
    }

    confidence_review_section: dict[str, Any] = {
        "note": (
            "confidence 是 M3 按证据类型数算出的候选证据等级"
            "（≥3=high，2=medium，表注释单独命中=medium，其余=low），"
            "不是业务确认；high 必然 diversity ≥ 3。"
        ),
        **{
            category: {
                level: confidence_counts[category].get(level, 0)
                for level in BUSINESS_CONFIDENCE_ORDER
            }
            for category in ("domain", "object")
        },
        "combined": {
            level: confidence_counts["domain"].get(level, 0)
            + confidence_counts["object"].get(level, 0)
            for level in BUSINESS_CONFIDENCE_ORDER
        },
        "high_total": high_total,
        "high_diversity": {
            bucket: high_diversity_counts.get(bucket, 0)
            for bucket in QUALITY_DIVERSITY_BUCKETS
        },
        "high_naming_only": high_naming_only,
        "high_with_sql": high_with_sql,
        "high_with_lineage": high_with_lineage,
        "high_repeated_keyword": high_repeated_keyword,
        "high_single_keyword": high_single_keyword,
    }

    core_table_review_section: dict[str, Any] = {
        "note": (
            "core 口径是 analysis/business/tables.json 的 is_core_candidate；"
            "core_low_evidence_count（diversity ≤ 1）与 core_unknown_count 有重叠："
            "UNKNOWN 的表证据必然为空。"
        ),
        "core_count": core_count,
        "core_flag_mismatch_count": core_flag_mismatch_count,
        "core_unknown_count": core_unknown_count,
        "core_ambiguous_count": core_ambiguous_count,
        "core_high_count": core_high_count,
        "core_low_evidence_count": core_low_evidence_count,
        "samples": {
            "core_unknown": [sample.to_dict() for sample in samples_core_unknown],
            "core_ambiguous": [sample.to_dict() for sample in samples_core_ambiguous],
            "core_flag_mismatch": mismatch_samples,
        },
    }

    return BusinessQualityResult(
        summary=summary,
        unknown=unknown_section,
        ambiguous=ambiguous_section,
        evidence_quality=evidence_quality_section,
        confidence_review=confidence_review_section,
        core_table_review=core_table_review_section,
        checklist=checklist,
    )


# ============================================================
# 产物写出与运行入口
# ============================================================


def write_business_quality(
    result: BusinessQualityResult,
    output_dir: Path,
) -> tuple[Path, ...]:
    """写出 M3.1 产物，返回路径列表（固定顺序）。

    只覆盖本模块声明的三个文件，不删除、不改写已有 M3 产物。
    """

    ensure_dir(output_dir)

    paths = {name: output_dir / name for name in OUTPUT_FILES}

    write_json(paths["quality-assessment.json"], result.to_dict())
    write_text(
        paths["quality-assessment.md"],
        render_business_quality_report(
            summary=result.summary,
            unknown=result.unknown,
            ambiguous=result.ambiguous,
            evidence_quality=result.evidence_quality,
            confidence_review=result.confidence_review,
            core_table_review=result.core_table_review,
            analysis_dir=_display_path(result.analysis_dir),
        ),
    )
    write_text(
        paths["review-checklist.md"],
        render_review_checklist(
            rows=result.checklist,
            row_limit=QUALITY_CHECKLIST_ROW_LIMIT,
        ),
    )

    logger.info(
        "M3.1 产物已写出：%s",
        "，".join(_display_path(paths[name]) for name in OUTPUT_FILES),
    )

    return tuple(paths[name] for name in OUTPUT_FILES)


def run_business_quality_assessment(
    *,
    analysis_dir: Path,
    output_dir: Path,
) -> BusinessQualityResult:
    """执行 M3.1 Business Quality Assessment 并写出产物。

    只读 M2 / M3 产物；输入缺失时直接报错，不自动回退去跑 M2 / analyze-business。
    """

    inputs = read_quality_inputs(analysis_dir)

    result = build_business_quality(inputs)
    result.analysis_dir = analysis_dir

    core_unknown = int(result.summary.get("core_unknown_count") or 0)

    if core_unknown:
        logger.warning(
            "M3.1 检出 %s 张核心表候选没有任何 Domain / Object 候选（UNKNOWN），"
            "优先人工补证据；明细见 %s",
            core_unknown,
            _display_path(output_dir / "review-checklist.md"),
        )

    write_business_quality(result, output_dir)

    logger.info(
        "M3.1 Business Quality Assessment 完成：table=%s，unknown=%s，ambiguous=%s，"
        "core_unknown=%s，core_ambiguous=%s",
        result.summary.get("table_count"),
        result.summary.get("unknown_count"),
        result.summary.get("ambiguous_count"),
        result.summary.get("core_unknown_count"),
        result.summary.get("core_ambiguous_count"),
    )

    return result

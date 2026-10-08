"""M3.5 Fact / Dimension Candidate Analysis。

目标：

    从 M3.4 的 Grain Candidate 与 M3.2 的 Object 结构里产出「当前业务模型的
    候选视图」——Fact Candidate、Dimension Candidate 与二者之间的候选关系，
    并保留可回溯到 M2 / M3 / M3.2 / M3.3 / M3.4 产物的证据链。

    Fact Candidate
          ├── 粒度来自通过 Fact Gate 的 Grain Candidate（形态或度量字段）
          ├── modeling_roles 恒为 [fact_candidate]（机器阶段不改角色）
          ├── strength = 证据源多样性（process / grain / table / column /
          │               sql / lineage / object）
          └── status 恒为 candidate（只有清单 human_status 回填后才改变）
    Dimension Candidate
          ├── 按 M3.1 的 Object 逐个生成（object-scoped，不按表生成）
          ├── attributes 只是关联表里观察到的字段清单，不等于维度属性
          └── modeling_roles 可能同时命中 dimension_candidate +
              fact_related_object（role_status=ambiguous，必须人工裁决）
    Fact-Dimension Relationship
          ├── 每 (fact, dimension) 至少一类证据才产出一行，不做无证据笛卡尔积
          └── relationship ≠ 业务关系，确认必须人工完成

输入（只读 analysis/ 与 config/ 之外的产物，不读 source/，不调 API，
不修改 M2 / M3 / M3.1 / M3.2 / M3.3 / M3.4 产物）：

    analysis/understanding/business/grain-candidates.json
    analysis/understanding/business/grain-tables.json
    analysis/understanding/business/processes.json
    analysis/understanding/business/process-objects.json
    analysis/understanding/business/objects-registry.json
    analysis/understanding/business/object-tables.json
    analysis/understanding/business/object-relationships.json
    analysis/inventory/tables.json
    analysis/inventory/columns.json
    analysis/evidence/sql/table-references.json
    analysis/evidence/lineage/table-lineage.json
    analysis/evidence/lineage/core-table-candidates.json
    analysis/evidence/profiling/tables.json
    analysis/evidence/profiling/columns.json
    analysis/evidence/layer/assessments.json
    understanding/business/process-review-checklist.md   （可选：Process 人工确认）
    understanding/business/grain-review-checklist.md     （可选：Grain 人工确认）
    analysis/understanding/modeling/model-review-checklist.md        （可选：本阶段清单回填）

    不读 grain-signals / process-signals / process-tables：M3.5 不重算信号，
    grain candidate 已经携带全部粒度结论；不读 sql/statements.json：表级引用
    足以支撑证据，语句正文不属于本阶段；不读 business/{tables,terms,domains}
    与 quality-assessment.json：它们是 M3 / M3.1 的分类结论，重读等于重新分类。

输出（Stage 11，M3.5 产物统一写在 analysis/understanding/modeling/）：

    analysis/understanding/modeling/fact-candidates.json
    analysis/understanding/modeling/dimension-candidates.json
    analysis/understanding/modeling/fact-dimension-relationships.json
    analysis/understanding/modeling/fact-tables.json
    analysis/understanding/modeling/dimension-tables.json
    analysis/understanding/modeling/model-evidence-matrix.json
    analysis/understanding/modeling/model-summary.md
    analysis/understanding/modeling/model-review-checklist.md

原则：

1. candidate ≠ confirmed：机器阶段不产出 confirmed fact / dimension；
   只有 model-review-checklist.md 的 human_status 回填后重跑才改状态。
2. layer ≠ role：layer/assessments.json 只作为 candidate_layer 结构证据，
   不参与 fact / dimension 判定；表名含 fact / dim / dwd 也不参与判定。
3. Fact Gate：transaction / event / snapshot 直接进入候选；periodic /
   aggregation / unknown 必须有 measure 字段才进入候选；未过闸的 grain
   只计数，不产出 Fact Candidate，也不当作「没有事实」的结论。
4. Dimension 按 Object 生成：一个 Object 一个 Dimension Candidate，
   属性多不构成强结论，0 关联表也不硬造候选内容。
5. 关系只在有证据时产出：process_object / object_relationship /
   table_reference / sql_reference / lineage 至少命中一类。
6. 不伪造唯一性：Profiling 只有 metadata_only，candidate_key ≠ unique，
   strength 只反映证据源多样性。
7. 输出 deterministic：无时间戳 / UUID / 随机抽样，全部稳定排序。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ....io_utils import (
    ensure_dir,
    relocate_legacy_artifacts,
    write_json,
    write_text,
)
from ...models import (
    DIMENSION_EVIDENCE_COLUMN,
    DIMENSION_EVIDENCE_FACT_REFERENCE,
    DIMENSION_EVIDENCE_LINEAGE,
    DIMENSION_EVIDENCE_OBJECT,
    DIMENSION_EVIDENCE_ORDER,
    DIMENSION_EVIDENCE_PROCESS,
    DIMENSION_EVIDENCE_SQL,
    EVIDENCE_STRENGTH_ORDER,
    EVIDENCE_STRENGTH_WEAK,
    FACT_EVIDENCE_COLUMN,
    FACT_EVIDENCE_GRAIN,
    FACT_EVIDENCE_LINEAGE,
    FACT_EVIDENCE_OBJECT,
    FACT_EVIDENCE_ORDER,
    FACT_EVIDENCE_PROCESS,
    FACT_EVIDENCE_SQL,
    FACT_EVIDENCE_TABLE,
    GRAIN_EVIDENCE_COLUMN,
    GRAIN_EVIDENCE_LINEAGE,
    GRAIN_EVIDENCE_OBJECT,
    GRAIN_EVIDENCE_OBJECT_RELATIONSHIP,
    GRAIN_EVIDENCE_PROCESS_SIGNAL,
    GRAIN_EVIDENCE_SQL,
    GRAIN_EVIDENCE_TABLE,
    GRAIN_PATTERN_AGGREGATION,
    GRAIN_PATTERN_EVENT,
    GRAIN_PATTERN_ORDER,
    GRAIN_PATTERN_PERIODIC,
    GRAIN_PATTERN_SNAPSHOT,
    GRAIN_PATTERN_TRANSACTION,
    GRAIN_PATTERN_UNKNOWN,
    GRAIN_ROLE_ANCHOR,
    GRAIN_ROLE_ORDER,
    GRAIN_ROLE_SUPPORTING,
    GRAIN_UNRESOLVED_INSUFFICIENT,
    GRAIN_UNRESOLVED_MULTIPLE_KEYS,
    MODEL_ATTRIBUTE_LIMIT,
    MODEL_CANDIDATE_NOTE,
    MODEL_CANDIDATE_TYPE_DIMENSION,
    MODEL_CANDIDATE_TYPE_FACT,
    MODEL_CANDIDATE_TYPE_RELATIONSHIP,
    MODEL_CHECKLIST_REQUIRED_COLUMNS,
    MODEL_CHECKLIST_ROW_LIMIT,
    MODEL_DIMENSION_UNRESOLVED_AMBIGUOUS,
    MODEL_DIMENSION_UNRESOLVED_ATTRIBUTE,
    MODEL_DIMENSION_UNRESOLVED_FACT,
    MODEL_DIMENSION_UNRESOLVED_LINEAGE,
    MODEL_DIMENSION_UNRESOLVED_OBJECT,
    MODEL_DIMENSION_UNRESOLVED_ORDER,
    MODEL_DIMENSION_UNRESOLVED_PROCESS,
    MODEL_DIMENSION_UNRESOLVED_SQL,
    MODEL_EXAMPLE_LIMIT,
    MODEL_FACT_UNRESOLVED_AMBIGUOUS_GRAIN,
    MODEL_FACT_UNRESOLVED_GRAIN,
    MODEL_FACT_UNRESOLVED_LINEAGE,
    MODEL_FACT_UNRESOLVED_MEASURE,
    MODEL_FACT_UNRESOLVED_OBJECT,
    MODEL_FACT_UNRESOLVED_ORDER,
    MODEL_FACT_UNRESOLVED_PROCESS,
    MODEL_FACT_UNRESOLVED_SQL,
    MODEL_HUMAN_STATUS_PENDING,
    MODEL_PRIORITY_DIMENSION,
    MODEL_PRIORITY_FACT_AMBIGUOUS,
    MODEL_PRIORITY_FACT_EVIDENCE,
    MODEL_PRIORITY_ORDER,
    MODEL_PRIORITY_RELATIONSHIP,
    MODEL_REL_EVIDENCE_LINEAGE,
    MODEL_REL_EVIDENCE_OBJECT_RELATIONSHIP,
    MODEL_REL_EVIDENCE_ORDER,
    MODEL_REL_EVIDENCE_PROCESS_OBJECT,
    MODEL_REL_EVIDENCE_SQL_REFERENCE,
    MODEL_REL_EVIDENCE_TABLE_REFERENCE,
    MODEL_REL_UNRESOLVED_INSUFFICIENT,
    MODEL_REL_UNRESOLVED_LINEAGE,
    MODEL_REL_UNRESOLVED_OBJECT_LINK,
    MODEL_REL_UNRESOLVED_ORDER,
    MODEL_REL_UNRESOLVED_SQL,
    MODEL_ROLE_DIMENSION,
    MODEL_ROLE_FACT,
    MODEL_ROLE_FACT_RELATED_OBJECT,
    MODEL_ROLE_STATUS_AMBIGUOUS,
    MODEL_ROLE_STATUS_CANDIDATE,
    MODEL_ROLE_STATUS_ORDER,
    MODEL_STATUS_BY_HUMAN_STATUS,
    MODEL_STATUS_CANDIDATE,
    MODEL_STATUS_CONFIRMED,
    MODEL_STATUS_ORDER,
    BusinessModelResult,
    ModelChecklistRow,
    evidence_strength,
    normalize_human_status,
)
from ...naming import qualify_table_ref
from ...reports import (
    render_model_review_checklist,
    render_model_summary,
)
from ..business.grain import (
    IDENTIFIER_NAMES,
    IDENTIFIER_TOKENS,
    BusinessGrainError,
    _dict_values,
    _display_path,
    _evidence_entry,
    _parse_checklist_rows,
    _profiling_stats,
    _rank,
    _status_counts,
    _table_column_sort_key,
)
from ..business.objects import _string_list, _table_sort_key, _text, _workspace_projects
from ..business.understanding import tokenize_identifier

logger = logging.getLogger(__name__)

# ============================================================
# 输入与输出布局
# ============================================================

ARRAY_INPUT_FILES: tuple[tuple[str, str, str], ...] = (
    ("understanding/business/grain-candidates.json", "candidates", "grain_candidates"),
    ("understanding/business/grain-tables.json", "tables", "grain_tables"),
    ("understanding/business/processes.json", "processes", "processes"),
    ("understanding/business/process-objects.json", "objects", "process_objects"),
    ("understanding/business/objects-registry.json", "objects", "registry_objects"),
    ("understanding/business/object-tables.json", "associations", "associations"),
    ("understanding/business/object-relationships.json", "relationships", "object_relationships"),
    ("inventory/tables.json", "tables", "inventory_tables"),
    ("inventory/columns.json", "columns", "columns"),
    ("evidence/sql/table-references.json", "references", "references"),
    ("evidence/lineage/table-lineage.json", "edges", "edges"),
    ("evidence/lineage/core-table-candidates.json", "candidates", "core_candidates"),
    ("evidence/profiling/tables.json", "tables", "profile_tables"),
    ("evidence/profiling/columns.json", "columns", "profile_columns"),
    ("evidence/layer/assessments.json", "assessments", "assessments"),
)
"""M3.5 依赖的数组型 M2 / M3 产物（相对 analysis/ 路径 → JSON 数组字段名 → 属性名）。"""

PROCESS_CHECKLIST_INPUT_FILE = "understanding/business/process-review-checklist.md"
"""M3.3 人工确认清单（可选输入）：只用于刷新 Process 的人工确认状态。"""

GRAIN_CHECKLIST_INPUT_FILE = "understanding/business/grain-review-checklist.md"
"""M3.4 人工确认清单（可选输入）：只用于记录 Grain 的人工确认状态。"""

CARRYOVER_CHECKLIST_INPUT_FILE = "understanding/modeling/model-review-checklist.md"
"""本阶段清单（可选输入）：回填过的人工状态在重跑时被带回去。"""

INPUT_FILES: tuple[str, ...] = tuple(relative for relative, _key, _attr in ARRAY_INPUT_FILES)
"""M3.5 的必需输入（相对 analysis/ 路径）；三个 markdown 清单属于可选输入。"""

OUTPUT_FILES: tuple[str, ...] = (
    "fact-candidates.json",
    "dimension-candidates.json",
    "fact-dimension-relationships.json",
    "fact-tables.json",
    "dimension-tables.json",
    "model-evidence-matrix.json",
    "model-summary.md",
    "model-review-checklist.md",
)
"""M3.5 产物文件名（固定顺序，写出到 analysis/understanding/modeling/）；
只覆盖这八个文件，不动已有 M2 / M3 产物。"""

PROCESS_CHECKLIST_REQUIRED_COLUMNS: tuple[str, ...] = ("process_key", "confirmed")
"""process-review-checklist.md 必须包含的列，缺一即报错。"""

GRAIN_CHECKLIST_REQUIRED_COLUMNS: tuple[str, ...] = (
    "grain_candidate_id",
    "confirmed",
)
"""grain-review-checklist.md 必须包含的列，缺一即报错。"""

FACT_GATE_DIRECT_PATTERNS: frozenset[str] = frozenset(
    {
        GRAIN_PATTERN_TRANSACTION,
        GRAIN_PATTERN_EVENT,
        GRAIN_PATTERN_SNAPSHOT,
    }
)
"""Fact Gate：形态本身即行级事实，直接进入候选。"""

FACT_GATE_MEASURE_PATTERNS: frozenset[str] = frozenset(
    {
        GRAIN_PATTERN_PERIODIC,
        GRAIN_PATTERN_AGGREGATION,
        GRAIN_PATTERN_UNKNOWN,
    }
)
"""Fact Gate：聚合 / 周期 / 未知形态必须有度量字段才进入候选。"""

FACT_GATE_REASON_MEASURE = "no_measure_evidence"
FACT_GATE_REASON_PATTERN = "pattern_not_in_vocabulary"

FACT_GATE_REASON_ORDER: tuple[str, ...] = (
    FACT_GATE_REASON_MEASURE,
    FACT_GATE_REASON_PATTERN,
)
"""Fact Gate 未通过原因的固定顺序。"""

GRAIN_SOURCE_TO_FACT: dict[str, str] = {
    GRAIN_EVIDENCE_PROCESS_SIGNAL: FACT_EVIDENCE_PROCESS,
    GRAIN_EVIDENCE_COLUMN: FACT_EVIDENCE_COLUMN,
    GRAIN_EVIDENCE_TABLE: FACT_EVIDENCE_TABLE,
    GRAIN_EVIDENCE_SQL: FACT_EVIDENCE_SQL,
    GRAIN_EVIDENCE_LINEAGE: FACT_EVIDENCE_LINEAGE,
    GRAIN_EVIDENCE_OBJECT: FACT_EVIDENCE_OBJECT,
    GRAIN_EVIDENCE_OBJECT_RELATIONSHIP: FACT_EVIDENCE_OBJECT,
}
"""M3.4 grain 证据 source_type → M3.5 fact 证据 source_type 的映射。"""


class BusinessModelError(RuntimeError):
    """M3.5 无法继续的输入 / 结构错误。"""


# ============================================================
# 通用小工具
# ============================================================


def _examples(values: Sequence[str]) -> str:
    """reason 里列出的示例：最多 MODEL_EXAMPLE_LIMIT 个 + 总数。"""

    ordered = sorted(values)

    if len(ordered) <= MODEL_EXAMPLE_LIMIT:
        return "、".join(ordered)

    return f"{'、'.join(ordered[:MODEL_EXAMPLE_LIMIT])} 等 {len(ordered)} 个"


def _sources(entries: Sequence[Mapping[str, Any]], order: Sequence[str]) -> list[str]:
    """按固定顺序返回出现过的证据 source_type。"""

    present = {str(entry.get("source_type") or "") for entry in entries}

    return [source for source in order if source in present]


def _evidence_counts(
    entries: Sequence[Mapping[str, Any]],
    order: Sequence[str],
) -> dict[str, int]:
    """按固定顺序输出每个证据 source_type 的条目数。"""

    counts = {source: 0 for source in order}

    for entry in entries:
        source = str(entry.get("source_type") or "")
        counts[source] = counts.get(source, 0) + 1

    return counts


def _unresolved_counts(
    rows: Sequence[Mapping[str, Any]],
    order: Sequence[str],
) -> dict[str, int]:
    """按固定顺序输出每个未决原因命中的候选行数。"""

    counts = {reason: 0 for reason in order}

    for row in rows:
        for reason in row.get("unresolved_reasons") or []:
            counts[str(reason)] = counts.get(str(reason), 0) + 1

    return counts


def _sort_evidence(
    entries: Sequence[Mapping[str, Any]],
    order: Sequence[str],
) -> list[dict[str, Any]]:
    """按（source_type 固定顺序, source_id, column_name, reason）去重排序。"""

    seen: dict[tuple[Any, ...], dict[str, Any]] = {}

    for entry in entries:
        key = (
            str(entry.get("source_type") or ""),
            str(entry.get("source_id") or ""),
            str(entry.get("column_name") or ""),
            str(entry.get("reason") or ""),
        )
        seen.setdefault(key, dict(entry))

    def sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            _rank(str(item.get("source_type") or ""), order),
            str(item.get("source_id") or ""),
            str(item.get("column_name") or ""),
            str(item.get("reason") or ""),
        )

    return sorted(seen.values(), key=sort_key)


def _pair(left: str, right: str) -> tuple[str, str]:
    """Object 对的规范顺序（小的在前）。"""

    return (left, right) if left <= right else (right, left)


def _reason_sort(reason: str, order: Sequence[str]) -> tuple[int, str]:
    return (_rank(reason, order), reason)


# ============================================================
# M2 / M3 产物读取
# ============================================================


@dataclass
class ModelInputs:
    """M3.5 读取到的 M2 / M3 产物（只做结构校验，不改写）。"""

    grain_candidates: list[dict[str, Any]] = field(default_factory=list)
    grain_tables: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    process_objects: list[dict[str, Any]] = field(default_factory=list)
    registry_objects: list[dict[str, Any]] = field(default_factory=list)
    associations: list[dict[str, Any]] = field(default_factory=list)
    object_relationships: list[dict[str, Any]] = field(default_factory=list)
    inventory_tables: list[dict[str, Any]] = field(default_factory=list)
    columns: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    core_candidates: list[dict[str, Any]] = field(default_factory=list)
    profile_tables: list[dict[str, Any]] = field(default_factory=list)
    profile_columns: list[dict[str, Any]] = field(default_factory=list)
    assessments: list[dict[str, Any]] = field(default_factory=list)
    process_checklist_text: str = ""
    process_checklist_path: Path = field(default_factory=Path)
    grain_checklist_text: str = ""
    grain_checklist_path: Path = field(default_factory=Path)
    carryover_text: str = ""
    carryover_path: Path = field(default_factory=Path)
    analysis_dir: Path = field(default_factory=Path)


def read_model_inputs(analysis_dir: Path) -> ModelInputs:
    """读取 M3.5 依赖的全部 M2 / M3 产物。

    任何必需输入缺失或 JSON 非法都明确报错，
    不自动回退执行 analyze / analyze --stage。
    """

    missing = [relative for relative in INPUT_FILES if not (analysis_dir / relative).exists()]

    if missing:
        raise BusinessModelError(
            "M2 / M3 / M3.4 产物缺失，无法执行 M3.5 Fact / Dimension "
            f"Candidate Analysis：{'、'.join(missing)}"
            f"（目录：{_display_path(analysis_dir)}）；"
            "请先执行 analyze --stage evidence 生成 M2 产物、"
            "analyze --stage understanding 生成 M3 ~ M3.5 产物"
        )

    def load(relative: str, key: str) -> list[dict[str, Any]]:
        path = analysis_dir / relative

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))

        except json.JSONDecodeError as exc:
            raise BusinessModelError(f"产物不是合法的 JSON：{path}（{exc}）") from exc

        if not isinstance(raw, dict):
            raise BusinessModelError(f"产物根节点不是对象：{path}")

        try:
            return _dict_values(raw.get(key), key, path)

        except BusinessGrainError as exc:
            raise BusinessModelError(str(exc)) from exc

    inputs = ModelInputs()
    inputs.analysis_dir = analysis_dir
    inputs.process_checklist_path = analysis_dir / PROCESS_CHECKLIST_INPUT_FILE
    inputs.grain_checklist_path = analysis_dir / GRAIN_CHECKLIST_INPUT_FILE
    inputs.carryover_path = analysis_dir / CARRYOVER_CHECKLIST_INPUT_FILE

    for relative, key, attr in ARRAY_INPUT_FILES:
        setattr(inputs, attr, load(relative, key))

    for path, attr, label in (
        (inputs.process_checklist_path, "process_checklist_text", "process review"),
        (inputs.grain_checklist_path, "grain_checklist_text", "grain review"),
        (inputs.carryover_path, "carryover_text", "model review"),
    ):
        if not path.exists():
            continue

        try:
            setattr(inputs, attr, path.read_text(encoding="utf-8"))

        except OSError as exc:
            raise BusinessModelError(f"无法读取 {label} 清单：{path}（{exc}）") from exc

    _validate_inputs(inputs)

    logger.info(
        "M3.5 输入已读取：%s（grain=%s，process=%s，association=%s，column=%s）",
        _display_path(analysis_dir),
        len(inputs.grain_candidates),
        len(inputs.processes),
        len(inputs.associations),
        len(inputs.columns),
    )

    return inputs


def _validate_inputs(inputs: ModelInputs) -> None:
    """校验跨文件引用，报错即退出（不存在静默忽略）。"""

    process_keys = {_text(record.get("process_key")) for record in inputs.processes}
    registry_objects = {_text(record.get("object")) for record in inputs.registry_objects}

    grain_ids: set[str] = set()

    for position, record in enumerate(inputs.grain_candidates):
        grain_id = _text(record.get("grain_candidate_id"))
        process_key = _text(record.get("process_candidate_id"))

        if not grain_id:
            raise BusinessModelError(
                "grain-candidates.json 缺少 grain_candidate_id："
                f"candidates[{position}]（{_display_path(inputs.analysis_dir)}）"
            )

        if grain_id in grain_ids:
            raise BusinessModelError(
                f"grain-candidates.json 的 grain_candidate_id 重复：{grain_id}"
            )

        grain_ids.add(grain_id)

        if not process_key or process_key not in process_keys:
            raise BusinessModelError(
                f"grain candidate {grain_id} 引用未知 process candidate："
                f"{process_key or '（空）'}；请先执行 analyze --stage understanding"
            )

        unknown = sorted(
            {
                text
                for item in record.get("matched_objects") or []
                if (text := _text(item)) is not None and text not in registry_objects
            }
        )

        if unknown:
            raise BusinessModelError(
                f"grain candidate {grain_id} 的 matched_objects 含未知 Object："
                f"{'、'.join(unknown)}；请先执行 analyze --stage understanding"
            )

    for position, record in enumerate(inputs.grain_tables):
        grain_id = _text(record.get("grain_candidate_id"))

        if grain_id not in grain_ids:
            raise BusinessModelError(
                f"grain-tables.json 的 tables[{position}] 引用未知 grain "
                f"candidate：{grain_id or '（空）'}"
            )


# ============================================================
# 人工确认状态（只读，按清单回填候选 status）
# ============================================================


def _checklist_rows(
    text: str,
    *,
    required: Sequence[str],
    source: Path,
    label: str,
) -> dict[str, dict[str, str]]:
    """解析清单里的 Markdown 表；空文件返回 {}，缺列报错。"""

    if not text.strip():
        return {}

    try:
        return _parse_checklist_rows(
            text,
            required=required,
            source=source,
            label=label,
        )

    except BusinessGrainError as exc:
        raise BusinessModelError(str(exc)) from exc


def _checklist_flags(
    text: str,
    *,
    required: Sequence[str],
    source: Path,
    label: str,
) -> dict[str, bool]:
    """解析清单里的 confirmed 列：主键列 → 是否已确认。"""

    return {
        key: (row.get("confirmed", "") or "").strip().casefold()
        in {"true", "yes", "y", "1", "confirmed", "是"}
        for key, row in _checklist_rows(
            text,
            required=required,
            source=source,
            label=label,
        ).items()
    }


def _apply_carryover(
    rows: list[dict[str, Any]],
    carry_over: Mapping[str, Mapping[str, str]],
    *,
    key_field: str,
    label: str,
) -> None:
    """把清单里的 human_status 回填成候选 status（只对命中的行生效）。"""

    if not carry_over:
        return

    known = 0

    for row in rows:
        key = str(row.get(key_field) or "")
        previous = carry_over.get(key)

        if not previous:
            continue

        raw = str(previous.get("human_status", "") or "").strip()
        normalized = normalize_human_status(raw)

        if normalized is None:
            if raw:
                logger.warning(
                    "%s 的 %s=%s 无法识别 human_status：%s（按未回填处理）",
                    label,
                    key_field,
                    key,
                    raw,
                )

            continue

        row["status"] = MODEL_STATUS_BY_HUMAN_STATUS[normalized]
        row["human_validated"] = row["status"] == MODEL_STATUS_CONFIRMED

        if normalized != MODEL_HUMAN_STATUS_PENDING:
            known += 1

    if known:
        logger.info("%s 已回填 %s 行人工状态", label, known)


# ============================================================
# 索引
# ============================================================


@dataclass
class ModelIndexes:
    """构建候选所需的全部索引（全部只读）。"""

    grain_candidates: tuple[dict[str, Any], ...] = ()
    grain_tables_by_id: dict[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    grain_validated: dict[str, bool] = field(default_factory=dict)
    processes: dict[str, dict[str, Any]] = field(default_factory=dict)
    process_validated: dict[str, bool] = field(default_factory=dict)
    process_objects: dict[str, tuple[str, ...]] = field(default_factory=dict)
    processes_by_object: dict[str, tuple[str, ...]] = field(default_factory=dict)
    registry: dict[str, dict[str, Any]] = field(default_factory=dict)
    assoc_tables_by_object: dict[str, tuple[str, ...]] = field(default_factory=dict)
    assoc_folded_by_object: dict[str, frozenset[str]] = field(default_factory=dict)
    assoc_by_key: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    object_pairs: dict[tuple[str, str], str] = field(default_factory=dict)
    table_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    layer_by_table: dict[str, str | None] = field(default_factory=dict)
    core_keys: frozenset[str] = frozenset()
    column_names_by_table: dict[str, tuple[str, ...]] = field(default_factory=dict)
    object_anchor_tables: dict[str, frozenset[str]] = field(default_factory=dict)
    sql_statements: tuple[dict[str, Any], ...] = ()
    sql_tables: tuple[frozenset[str], ...] = ()
    statements_by_table: dict[str, tuple[int, ...]] = field(default_factory=dict)
    lineage_edges: tuple[dict[str, Any], ...] = ()
    lineage_by_table: dict[str, tuple[int, ...]] = field(default_factory=dict)
    profiling: dict[str, Any] = field(default_factory=dict)


def _index_grain_tables(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[dict[str, Any], ...]]:
    """grain_candidate_id → 该候选的表行（anchor 在前，supporting 按表名排序）。"""

    grouped: dict[str, list[dict[str, Any]]] = {}

    for record in sorted(
        rows,
        key=lambda item: (
            _rank(str(item.get("role") or ""), GRAIN_ROLE_ORDER),
            str(item.get("table_key") or "").casefold(),
        ),
    ):
        grain_id = _text(record.get("grain_candidate_id"))

        if grain_id:
            grouped.setdefault(grain_id, []).append(dict(record))

    return {key: tuple(values) for key, values in grouped.items()}


def _index_processes(
    rows: Sequence[Mapping[str, Any]],
    checklist_text: str,
    checklist_path: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, bool]]:
    """process_key → 行；process_key → 人工确认状态（机器状态 ∪ 清单回填）。"""

    processes = {
        key: dict(record)
        for record in rows
        if (key := _text(record.get("process_key"))) is not None
    }

    validated = {key: bool(record.get("human_validated")) for key, record in processes.items()}

    for key, confirmed in _checklist_flags(
        checklist_text,
        required=PROCESS_CHECKLIST_REQUIRED_COLUMNS,
        source=checklist_path,
        label="process-review-checklist.md",
    ).items():
        validated[key] = validated.get(key, False) or confirmed

    return processes, validated


def _index_process_objects(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    """(process_key → objects, object → process_keys)。"""

    by_process: dict[str, set[str]] = {}
    by_object: dict[str, set[str]] = {}

    for record in sorted(
        rows,
        key=lambda item: (
            str(item.get("process_key") or ""),
            str(item.get("object") or ""),
        ),
    ):
        process_key = _text(record.get("process_key"))
        obj = _text(record.get("object"))

        if not process_key or not obj:
            continue

        by_process.setdefault(process_key, set()).add(obj)
        by_object.setdefault(obj, set()).add(process_key)

    return (
        {key: tuple(sorted(values)) for key, values in by_process.items()},
        {key: tuple(sorted(values)) for key, values in by_object.items()},
    )


def _index_associations(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[
    dict[str, tuple[str, ...]],
    dict[str, frozenset[str]],
    dict[tuple[str, str], dict[str, Any]],
]:
    """(object → 表, object → 表 casefold 集合, (object, folded table) → 行)。"""

    by_object: dict[str, dict[str, str]] = {}
    folded_by_object: dict[str, set[str]] = {}
    by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for record in sorted(
        rows,
        key=lambda item: (
            str(item.get("object") or ""),
            str(item.get("table_key") or "").casefold(),
        ),
    ):
        obj = _text(record.get("object"))
        table_key = _text(record.get("table_key"))

        if not obj or not table_key:
            continue

        folded = table_key.casefold()
        by_object.setdefault(obj, {})[folded] = table_key
        folded_by_object.setdefault(obj, set()).add(folded)
        by_key[(obj, folded)] = dict(record)

    return (
        {
            obj: tuple(sorted(tables.values(), key=str.casefold))
            for obj, tables in sorted(by_object.items())
        },
        {obj: frozenset(values) for obj, values in sorted(folded_by_object.items())},
        by_key,
    )


def _index_object_pairs(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], str]:
    """规范 Object 对 → relationship evidence_strength（M3.2 关系证据）。"""

    index: dict[tuple[str, str], str] = {}

    for record in rows:
        left = _text(record.get("object_a"))
        right = _text(record.get("object_b"))

        if not left or not right:
            continue

        index[_pair(left, right)] = str(record.get("evidence_strength") or "")

    return index


def _index_table_meta(
    inventory_tables: Sequence[Mapping[str, Any]],
    extra_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """folded table_key → 展示元数据（inventory 优先，M3 产物兜底）。"""

    meta: dict[str, dict[str, Any]] = {}

    def merge(record: Mapping[str, Any]) -> None:
        key = _text(record.get("table_key"))

        if not key:
            return

        folded = key.casefold()
        table_name = _text(record.get("table_name")) or _text(record.get("table"))

        meta.setdefault(
            folded,
            {
                "table_key": key,
                "table_name": table_name or key,
                "workspace_id": record.get("workspace_id"),
                "project": _text(record.get("project")) or "",
                "comment": _text(record.get("comment")) or None,
            },
        )

    for record in sorted(inventory_tables, key=_table_sort_key):
        merge(record)

    for record in sorted(extra_rows, key=_table_sort_key):
        merge(record)

    return meta


def _index_layers(rows: Sequence[Mapping[str, Any]]) -> dict[str, str | None]:
    """folded table_identifier → candidate_layer（只作结构证据，不作角色判定）。"""

    index: dict[str, str | None] = {}

    for record in sorted(
        rows,
        key=lambda item: str(item.get("table_identifier") or "").casefold(),
    ):
        identifier = _text(record.get("table_identifier"))

        if not identifier:
            continue

        index.setdefault(identifier.casefold(), _text(record.get("candidate_layer")) or None)

    return index


def _index_sql(
    references: Sequence[Mapping[str, Any]],
    workspace_projects: Mapping[int, str],
) -> tuple[
    tuple[dict[str, Any], ...],
    tuple[frozenset[str], ...],
    dict[str, tuple[int, ...]],
]:
    """语句级索引：语句身份、语句引用的表集合、表 → 语句下标。"""

    grouped: dict[tuple[int, str, int, str], set[str]] = {}

    for record in references:
        workspace_id = record.get("workspace_id")
        project = workspace_projects.get(workspace_id) if isinstance(workspace_id, int) else None
        raw_statement_id = record.get("statement_id")
        identity = (
            workspace_id if isinstance(workspace_id, int) else 0,
            str(record.get("file_id") or ""),
            raw_statement_id if isinstance(raw_statement_id, int) else 0,
            str(record.get("file_name") or ""),
        )

        for field_name in ("source_tables", "target_tables"):
            for item in _string_list(record.get(field_name)):
                folded = qualify_table_ref(item, project).casefold()

                if folded:
                    grouped.setdefault(identity, set()).add(folded)

    identities = sorted(grouped)
    statements = tuple(
        {
            "workspace_id": workspace_id,
            "file_id": file_id,
            "statement_id": statement_id,
            "file_name": file_name,
        }
        for workspace_id, file_id, statement_id, file_name in identities
    )
    tables = tuple(frozenset(grouped[identity]) for identity in identities)

    by_table: dict[str, list[int]] = {}

    for position, table_set in enumerate(tables):
        for folded in table_set:
            by_table.setdefault(folded, []).append(position)

    return statements, tables, {key: tuple(value) for key, value in by_table.items()}


def _index_lineage(
    edges: Sequence[Mapping[str, Any]],
) -> tuple[tuple[dict[str, Any], ...], dict[str, tuple[int, ...]]]:
    """血缘边数组（稳定排序）与 表 → 血缘边下标。"""

    rows: list[dict[str, Any]] = []

    for record in edges:
        source = _text(record.get("source_key")) or _text(record.get("source_table"))
        target = _text(record.get("target_key")) or _text(record.get("target_table"))

        if not source or not target:
            continue

        rows.append(
            {
                "workspace_id": record.get("workspace_id"),
                "source_key": source,
                "target_key": target,
                "source_folded": source.casefold(),
                "target_folded": target.casefold(),
            }
        )

    rows.sort(
        key=lambda item: (
            str(item.get("workspace_id") or ""),
            str(item["source_folded"]),
            str(item["target_folded"]),
            str(item["source_key"]),
            str(item["target_key"]),
        )
    )

    by_table: dict[str, list[int]] = {}

    for position, row in enumerate(rows):
        by_table.setdefault(row["source_folded"], []).append(position)
        by_table.setdefault(row["target_folded"], []).append(position)

    return tuple(rows), {key: tuple(value) for key, value in by_table.items()}


def _index_columns(
    columns: Sequence[Mapping[str, Any]],
    wanted: set[str],
    objects: Sequence[str],
) -> tuple[dict[str, tuple[str, ...]], dict[str, frozenset[str]]]:
    """wanted 表的字段清单；object → 含命中该 Object 的标识字段的表。"""

    names: dict[str, list[str]] = {}
    anchors: dict[str, set[str]] = {}

    for record in sorted(columns, key=_table_column_sort_key):
        table_key = _text(record.get("table_key"))

        if not table_key:
            continue

        folded = table_key.casefold()

        if folded not in wanted:
            continue

        name = _text(record.get("column_name"))

        if not name:
            continue

        names.setdefault(folded, []).append(name)

        tokens = {token.casefold() for token in tokenize_identifier(name)}

        if not tokens:
            continue

        if not (tokens & IDENTIFIER_TOKENS or name.casefold() in IDENTIFIER_NAMES):
            continue

        for obj in objects:
            if obj.casefold() in tokens:
                anchors.setdefault(obj, set()).add(folded)

    return (
        {key: tuple(values) for key, values in names.items()},
        {key: frozenset(values) for key, values in anchors.items()},
    )


def build_model_indexes(inputs: ModelInputs) -> ModelIndexes:
    """把 M3.5 输入整理成只读索引（列形态索引稍后按需补）。"""

    workspace_projects = _workspace_projects(inputs.inventory_tables)
    process_objects, processes_by_object = _index_process_objects(inputs.process_objects)
    registry = {
        key: dict(record)
        for record in inputs.registry_objects
        if (key := _text(record.get("object"))) is not None
    }
    assoc_tables, assoc_folded, assoc_by_key = _index_associations(inputs.associations)
    sql_statements, sql_tables, statements_by_table = _index_sql(
        inputs.references, workspace_projects
    )
    lineage_edges, lineage_by_table = _index_lineage(inputs.edges)

    grain_validated = _checklist_flags(
        inputs.grain_checklist_text,
        required=GRAIN_CHECKLIST_REQUIRED_COLUMNS,
        source=inputs.grain_checklist_path,
        label="grain-review-checklist.md",
    )
    processes, process_validated = _index_processes(
        inputs.processes,
        inputs.process_checklist_text,
        inputs.process_checklist_path,
    )

    extra_rows = [
        *inputs.grain_tables,
        *inputs.associations,
    ]

    return ModelIndexes(
        grain_candidates=tuple(dict(record) for record in inputs.grain_candidates),
        grain_tables_by_id=_index_grain_tables(inputs.grain_tables),
        grain_validated=grain_validated,
        processes=processes,
        process_validated=process_validated,
        process_objects=process_objects,
        processes_by_object=processes_by_object,
        registry=registry,
        assoc_tables_by_object=assoc_tables,
        assoc_folded_by_object=assoc_folded,
        assoc_by_key=assoc_by_key,
        object_pairs=_index_object_pairs(inputs.object_relationships),
        table_meta=_index_table_meta(inputs.inventory_tables, extra_rows),
        layer_by_table=_index_layers(inputs.assessments),
        core_keys=frozenset(
            folded
            for record in inputs.core_candidates
            if (table_key := _text(record.get("table_key"))) is not None
            for folded in (table_key.casefold(),)
        ),
        sql_statements=sql_statements,
        sql_tables=sql_tables,
        statements_by_table=statements_by_table,
        lineage_edges=lineage_edges,
        lineage_by_table=lineage_by_table,
        profiling=_profiling_stats(inputs.profile_tables, inputs.profile_columns),
    )


# ============================================================
# Fact Gate 与 Fact Candidate
# ============================================================


def fact_gate(grain: Mapping[str, Any]) -> tuple[bool, str | None]:
    """Fact Gate：返回（是否进入候选，未进入原因）。"""

    pattern = str(grain.get("grain_pattern") or "")

    if pattern in FACT_GATE_DIRECT_PATTERNS:
        return True, None

    if pattern in FACT_GATE_MEASURE_PATTERNS:
        if grain.get("measure_columns"):
            return True, None

        return False, FACT_GATE_REASON_MEASURE

    return False, FACT_GATE_REASON_PATTERN


def _fact_evidence(
    grain: Mapping[str, Any],
    process_row: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """fact 证据 = M3.4 grain 证据映射 + process / grain / 度量字段证据。"""

    entries: list[dict[str, Any]] = []

    for entry in grain.get("evidence") or []:
        source = GRAIN_SOURCE_TO_FACT.get(str(entry.get("source_type") or ""))

        if source is None:
            continue

        mapped = dict(entry)
        mapped["source_type"] = source
        entries.append(mapped)

    table_key = _text(grain.get("table_key")) or ""
    workspace_id = grain.get("workspace_id")
    process_key = _text(grain.get("process_candidate_id"))
    grain_id = _text(grain.get("grain_candidate_id"))
    pattern = str(grain.get("grain_pattern") or "")
    objects = [str(item) for item in grain.get("matched_objects") or []]

    entries.append(
        _evidence_entry(
            FACT_EVIDENCE_PROCESS,
            f"process:{process_key}",
            workspace_id=workspace_id,
            table_key=table_key,
            column_name=None,
            reason=(
                f"M3.3 process candidate：status="
                f"{process_row.get('status') or MODEL_STATUS_CANDIDATE}，"
                f"strength={process_row.get('strength') or '-'}"
                + (f"，objects={_examples(objects)}" if objects else "")
            ),
        )
    )
    grain_keys = _examples([str(item) for item in grain.get("candidate_keys") or []])
    entries.append(
        _evidence_entry(
            FACT_EVIDENCE_GRAIN,
            f"grain:{grain_id}",
            workspace_id=workspace_id,
            table_key=table_key,
            column_name=None,
            reason=(
                f"M3.4 grain candidate：pattern={pattern}，candidate_keys={grain_keys or '（空）'}"
            ),
        )
    )

    measures = [str(item) for item in grain.get("measure_columns") or []]

    if measures:
        entries.append(
            _evidence_entry(
                FACT_EVIDENCE_COLUMN,
                f"{table_key}.measures",
                workspace_id=workspace_id,
                table_key=table_key,
                column_name=None,
                reason=f"度量字段（M3.4 measure_columns）：{_examples(measures)}",
            )
        )

    return _sort_evidence(entries, FACT_EVIDENCE_ORDER)


def _fact_unresolved(
    *,
    grain: Mapping[str, Any],
    process_row: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    object_keys: Sequence[str],
) -> list[str]:
    """fact 未决原因（固定顺序）。"""

    grain_unresolved = {str(item) for item in grain.get("unresolved_reasons") or []}
    sources = set(_sources(evidence, FACT_EVIDENCE_ORDER))
    pattern = str(grain.get("grain_pattern") or "")
    reasons: list[str] = []

    if str(process_row.get("strength") or "") == EVIDENCE_STRENGTH_WEAK:
        reasons.append(MODEL_FACT_UNRESOLVED_PROCESS)

    if (
        str(grain.get("strength") or "") == EVIDENCE_STRENGTH_WEAK
        or GRAIN_UNRESOLVED_INSUFFICIENT in grain_unresolved
    ):
        reasons.append(MODEL_FACT_UNRESOLVED_GRAIN)

    if pattern == GRAIN_PATTERN_UNKNOWN or GRAIN_UNRESOLVED_MULTIPLE_KEYS in grain_unresolved:
        reasons.append(MODEL_FACT_UNRESOLVED_AMBIGUOUS_GRAIN)

    if not grain.get("measure_columns"):
        reasons.append(MODEL_FACT_UNRESOLVED_MEASURE)

    if FACT_EVIDENCE_SQL not in sources:
        reasons.append(MODEL_FACT_UNRESOLVED_SQL)

    if FACT_EVIDENCE_LINEAGE not in sources:
        reasons.append(MODEL_FACT_UNRESOLVED_LINEAGE)

    if not object_keys:
        reasons.append(MODEL_FACT_UNRESOLVED_OBJECT)

    return sorted(
        set(reasons),
        key=lambda reason: _reason_sort(reason, MODEL_FACT_UNRESOLVED_ORDER),
    )


def _fact_rows(
    indexes: ModelIndexes,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """(fact candidate 行, Fact Gate 计数)。"""

    gate: dict[str, Any] = {
        "qualified_count": 0,
        "rejected_count": 0,
        "rejected_reason_counts": {reason: 0 for reason in FACT_GATE_REASON_ORDER},
    }
    raw: list[dict[str, Any]] = []

    for grain in indexes.grain_candidates:
        passed, reason = fact_gate(grain)

        if not passed:
            gate["rejected_count"] += 1
            gate["rejected_reason_counts"][str(reason)] += 1
            continue

        gate["qualified_count"] += 1

        process_key = _text(grain.get("process_candidate_id")) or ""
        grain_id = _text(grain.get("grain_candidate_id")) or ""
        process_row = indexes.processes.get(process_key, {})
        grain_table_rows = indexes.grain_tables_by_id.get(grain_id, ())
        anchor = next(
            (row for row in grain_table_rows if str(row.get("role") or "") == GRAIN_ROLE_ANCHOR),
            grain_table_rows[0] if grain_table_rows else {},
        )
        supporting = [
            row for row in grain_table_rows if str(row.get("role") or "") == GRAIN_ROLE_SUPPORTING
        ]
        primary_table = _text(anchor.get("table_key")) or _text(grain.get("table_key")) or ""
        table_keys = [
            primary_table,
            *(key for row in supporting if (key := _text(row.get("table_key"))) is not None),
        ]
        object_keys = sorted(
            {
                text
                for item in grain.get("matched_objects") or []
                if (text := _text(item)) is not None
            }
        )
        evidence = _fact_evidence(grain, process_row)
        reasons = _fact_unresolved(
            grain=grain,
            process_row=process_row,
            evidence=evidence,
            object_keys=object_keys,
        )
        signature = (
            f"process={process_key}|grain={grain_id}"
            f"|objects={','.join(object_keys)}"
            f"|tables={','.join(table_keys)}"
        )

        raw.append(
            {
                "_signature": signature,
                "canonical_signature": signature,
                "process_candidate_id": process_key,
                "grain_candidate_id": grain_id,
                "table_key": table_keys[0],
                "table_name": _text(anchor.get("table_name")) or table_keys[0],
                "workspace_id": anchor.get("workspace_id") if anchor else grain.get("workspace_id"),
                "project": _text(anchor.get("project")) or "",
                "grain_pattern": str(grain.get("grain_pattern") or ""),
                "candidate_keys": [str(item) for item in grain.get("candidate_keys") or []],
                "time_attributes": [str(item) for item in grain.get("time_columns") or []],
                "measures": [str(item) for item in grain.get("measure_columns") or []],
                "identifier_columns": [str(item) for item in grain.get("identifier_columns") or []],
                "object_keys": object_keys,
                "table_keys": table_keys,
                "supporting_table_count": int(anchor.get("supporting_table_count") or 0)
                if anchor
                else len(supporting),
                "candidate_layer": indexes.layer_by_table.get(table_keys[0].casefold()),
                "core_candidate": bool(grain.get("core_candidate")),
                "process_human_validated": bool(indexes.process_validated.get(process_key)),
                "grain_human_validated": bool(indexes.grain_validated.get(grain_id)),
                "modeling_roles": [MODEL_ROLE_FACT],
                "role_status": MODEL_ROLE_STATUS_CANDIDATE,
                "evidence_strength": evidence_strength(
                    len(_sources(evidence, FACT_EVIDENCE_ORDER))
                ),
                "evidence_sources": _sources(evidence, FACT_EVIDENCE_ORDER),
                "evidence_counts": _evidence_counts(evidence, FACT_EVIDENCE_ORDER),
                "evidence": evidence,
                "unresolved_reasons": reasons,
                "status": MODEL_STATUS_CANDIDATE,
                "human_validated": False,
            }
        )

    raw.sort(key=lambda item: str(item["_signature"]))

    rows = [
        {
            "fact_key": f"fact_candidate_{position:03d}",
            **{key: value for key, value in item.items() if not key.startswith("_")},
        }
        for position, item in enumerate(raw, start=1)
    ]

    counts = gate["rejected_reason_counts"]
    gate["rejected_reason_counts"] = {
        reason: counts[reason] for reason in FACT_GATE_REASON_ORDER if counts.get(reason)
    }

    return rows, gate


def _fact_table_evidence(
    *,
    folded: str,
    fact: Mapping[str, Any],
    indexes: ModelIndexes,
) -> dict[str, int]:
    """fact → table 行的表级证据计数（结构证据，不是 fact 本身的证据）。"""

    meta = indexes.table_meta.get(folded, {})
    column_names = {name.casefold() for name in indexes.column_names_by_table.get(folded, ())}
    relevant = {
        name.casefold()
        for name in [
            *[str(item) for item in fact.get("candidate_keys") or []],
            *[str(item) for item in fact.get("measures") or []],
        ]
    }
    object_keys = [str(item) for item in fact.get("object_keys") or []]

    return {
        FACT_EVIDENCE_PROCESS: 1 if fact.get("process_candidate_id") else 0,
        FACT_EVIDENCE_GRAIN: 1 if fact.get("grain_candidate_id") else 0,
        FACT_EVIDENCE_TABLE: 1 if meta.get("comment") else 0,
        FACT_EVIDENCE_COLUMN: len(relevant & column_names),
        FACT_EVIDENCE_SQL: 1 if folded in indexes.statements_by_table else 0,
        FACT_EVIDENCE_LINEAGE: 1 if folded in indexes.lineage_by_table else 0,
        FACT_EVIDENCE_OBJECT: sum(
            1
            for obj in object_keys
            if folded in indexes.assoc_folded_by_object.get(obj, frozenset())
        ),
    }


def _fact_table_rows(
    indexes: ModelIndexes,
    fact_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """fact → table 行（role 复用 M3.4 grain 的 anchor / supporting）。"""

    rows: list[dict[str, Any]] = []

    for fact in fact_rows:
        grain_table_rows = indexes.grain_tables_by_id.get(
            str(fact.get("grain_candidate_id") or ""), ()
        )
        role_by_table = {
            key.casefold(): str(record.get("role") or "")
            for record in grain_table_rows
            if (key := _text(record.get("table_key"))) is not None
        }

        for position, table_key in enumerate(fact.get("table_keys") or []):
            folded = str(table_key).casefold()
            meta = indexes.table_meta.get(folded, {})
            role = role_by_table.get(
                folded,
                GRAIN_ROLE_ANCHOR if position == 0 else GRAIN_ROLE_SUPPORTING,
            )

            rows.append(
                {
                    "fact_key": fact.get("fact_key"),
                    "process_candidate_id": fact.get("process_candidate_id"),
                    "grain_candidate_id": fact.get("grain_candidate_id"),
                    "table_key": meta.get("table_key") or table_key,
                    "table_name": meta.get("table_name") or table_key,
                    "workspace_id": meta.get("workspace_id"),
                    "project": meta.get("project") or "",
                    "role": role,
                    "supporting_table_count": fact.get("supporting_table_count"),
                    "candidate_layer": indexes.layer_by_table.get(folded),
                    "core_candidate": bool(fact.get("core_candidate"))
                    or folded in indexes.core_keys,
                    "evidence": _fact_table_evidence(folded=folded, fact=fact, indexes=indexes),
                }
            )

    return rows


# ============================================================
# Dimension Candidate
# ============================================================


def _attributes(
    object_key: str,
    indexes: ModelIndexes,
) -> tuple[list[dict[str, Any]], int]:
    """关联表字段清单（去重，按覆盖表数倒序、字段名升序）与总数。"""

    counts: dict[str, int] = {}
    display: dict[str, str] = {}

    for table_key in indexes.assoc_tables_by_object.get(object_key, ()):
        for name in indexes.column_names_by_table.get(table_key.casefold(), ()):
            folded = name.casefold()
            counts[folded] = counts.get(folded, 0) + 1
            display.setdefault(folded, name)

    rows: list[dict[str, Any]] = [
        {"column_name": display[folded], "table_count": table_count}
        for folded, table_count in counts.items()
    ]
    rows.sort(key=lambda item: (-int(item["table_count"]), str(item["column_name"])))

    return rows[:MODEL_ATTRIBUTE_LIMIT], len(rows)


def _dimension_evidence(
    *,
    object_key: str,
    indexes: ModelIndexes,
    fact_keys: Sequence[str],
    process_keys: Sequence[str],
    attributes: Sequence[Mapping[str, Any]],
    attribute_count: int,
) -> list[dict[str, Any]]:
    """dimension 证据（object / column / process / fact_reference / sql / lineage）。"""

    tables = indexes.assoc_tables_by_object.get(object_key, ())
    first_table = tables[0] if tables else ""
    meta = indexes.table_meta.get(first_table.casefold(), {})
    registry = indexes.registry.get(object_key, {})
    workspace_id = meta.get("workspace_id")

    entries: list[dict[str, Any]] = [
        _evidence_entry(
            DIMENSION_EVIDENCE_OBJECT,
            f"object:{object_key}",
            workspace_id=workspace_id,
            table_key=first_table,
            column_name=None,
            reason=(
                f"M3.2 Object registry：status="
                f"{registry.get('status') or MODEL_STATUS_CANDIDATE}，"
                f"association={len(tables)} 张表"
                f"（core={int(registry.get('core_table_count') or 0)}）"
            ),
        )
    ]

    if attribute_count:
        entries.append(
            _evidence_entry(
                DIMENSION_EVIDENCE_COLUMN,
                f"object:{object_key}.attributes",
                workspace_id=workspace_id,
                table_key=first_table,
                column_name=None,
                reason=(
                    f"关联表字段 {attribute_count} 个（去重、按覆盖表数排序）："
                    f"{_examples([str(item.get('column_name')) for item in attributes])}"
                ),
            )
        )

    if process_keys:
        entries.append(
            _evidence_entry(
                DIMENSION_EVIDENCE_PROCESS,
                f"process:{object_key}",
                workspace_id=workspace_id,
                table_key=first_table,
                column_name=None,
                reason=(
                    f"出现在 {len(process_keys)} 个 process candidate："
                    f"{_examples(list(process_keys))}"
                ),
            )
        )

    if fact_keys:
        entries.append(
            _evidence_entry(
                DIMENSION_EVIDENCE_FACT_REFERENCE,
                f"fact_reference:{object_key}",
                workspace_id=workspace_id,
                table_key=first_table,
                column_name=None,
                reason=(
                    f"被 {len(fact_keys)} 个 fact candidate 引用：{_examples(list(fact_keys))}"
                ),
            )
        )

    sql_tables = [
        table_key for table_key in tables if table_key.casefold() in indexes.statements_by_table
    ]

    if sql_tables:
        entries.append(
            _evidence_entry(
                DIMENSION_EVIDENCE_SQL,
                f"sql:{object_key}",
                workspace_id=workspace_id,
                table_key=first_table,
                column_name=None,
                reason=(f"{len(sql_tables)} 张关联表出现在 SQL 引用中：{_examples(sql_tables)}"),
            )
        )

    lineage_tables = [
        table_key for table_key in tables if table_key.casefold() in indexes.lineage_by_table
    ]

    if lineage_tables:
        entries.append(
            _evidence_entry(
                DIMENSION_EVIDENCE_LINEAGE,
                f"lineage:{object_key}",
                workspace_id=workspace_id,
                table_key=first_table,
                column_name=None,
                reason=(f"{len(lineage_tables)} 张关联表参与血缘边：{_examples(lineage_tables)}"),
            )
        )

    return _sort_evidence(entries, DIMENSION_EVIDENCE_ORDER)


def _dimension_unresolved(
    *,
    tables: Sequence[str],
    attribute_count: int,
    process_keys: Sequence[str],
    fact_keys: Sequence[str],
    evidence: Sequence[Mapping[str, Any]],
    role_status: str,
) -> list[str]:
    """dimension 未决原因（固定顺序）。"""

    sources = set(_sources(evidence, DIMENSION_EVIDENCE_ORDER))
    reasons: list[str] = []

    if not tables:
        reasons.append(MODEL_DIMENSION_UNRESOLVED_OBJECT)

    if not attribute_count:
        reasons.append(MODEL_DIMENSION_UNRESOLVED_ATTRIBUTE)

    if not process_keys:
        reasons.append(MODEL_DIMENSION_UNRESOLVED_PROCESS)

    if not fact_keys:
        reasons.append(MODEL_DIMENSION_UNRESOLVED_FACT)

    if DIMENSION_EVIDENCE_SQL not in sources:
        reasons.append(MODEL_DIMENSION_UNRESOLVED_SQL)

    if DIMENSION_EVIDENCE_LINEAGE not in sources:
        reasons.append(MODEL_DIMENSION_UNRESOLVED_LINEAGE)

    if role_status == MODEL_ROLE_STATUS_AMBIGUOUS:
        reasons.append(MODEL_DIMENSION_UNRESOLVED_AMBIGUOUS)

    return sorted(
        set(reasons),
        key=lambda reason: _reason_sort(reason, MODEL_DIMENSION_UNRESOLVED_ORDER),
    )


def _dimension_rows(
    indexes: ModelIndexes,
    fact_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(dimension candidate 行, dimension → table 行)。"""

    fact_keys_by_object: dict[str, list[str]] = {}
    fact_object_keys: set[str] = set()

    for fact in fact_rows:
        fact_key = str(fact.get("fact_key") or "")

        for obj in fact.get("object_keys") or []:
            fact_object_keys.add(str(obj))
            fact_keys_by_object.setdefault(str(obj), []).append(fact_key)

    raw: list[dict[str, Any]] = []

    for object_key in sorted(indexes.registry):
        registry = indexes.registry[object_key]
        tables = indexes.assoc_tables_by_object.get(object_key, ())
        attributes, attribute_count = _attributes(object_key, indexes)
        process_keys = list(indexes.processes_by_object.get(object_key, ()))
        fact_keys = sorted(set(fact_keys_by_object.get(object_key, ())))
        roles = [MODEL_ROLE_DIMENSION]

        if object_key in fact_object_keys:
            roles.append(MODEL_ROLE_FACT_RELATED_OBJECT)

        role_status = MODEL_ROLE_STATUS_AMBIGUOUS if len(roles) > 1 else MODEL_ROLE_STATUS_CANDIDATE
        evidence = _dimension_evidence(
            object_key=object_key,
            indexes=indexes,
            fact_keys=fact_keys,
            process_keys=process_keys,
            attributes=attributes,
            attribute_count=attribute_count,
        )
        reasons = _dimension_unresolved(
            tables=tables,
            attribute_count=attribute_count,
            process_keys=process_keys,
            fact_keys=fact_keys,
            evidence=evidence,
            role_status=role_status,
        )
        signature = f"object={object_key}"

        raw.append(
            {
                "_signature": signature,
                "canonical_signature": signature,
                "object_key": object_key,
                "object_name": _text(registry.get("name")) or object_key,
                "registry_status": str(registry.get("status") or MODEL_STATUS_CANDIDATE),
                "table_keys": list(tables),
                "table_count": len(tables),
                "attributes": attributes,
                "attribute_count": attribute_count,
                "candidate_layers": sorted(
                    {
                        layer
                        for table_key in tables
                        if (layer := indexes.layer_by_table.get(table_key.casefold()))
                    }
                ),
                "core_table_count": int(registry.get("core_table_count") or 0),
                "referenced_by_processes": process_keys,
                "referenced_by_facts": fact_keys,
                "modeling_roles": roles,
                "role_status": role_status,
                "evidence_strength": evidence_strength(
                    len(_sources(evidence, DIMENSION_EVIDENCE_ORDER))
                ),
                "evidence_sources": _sources(evidence, DIMENSION_EVIDENCE_ORDER),
                "evidence_counts": _evidence_counts(evidence, DIMENSION_EVIDENCE_ORDER),
                "evidence": evidence,
                "unresolved_reasons": reasons,
                "status": MODEL_STATUS_CANDIDATE,
                "human_validated": False,
            }
        )

    raw.sort(key=lambda item: str(item["_signature"]))

    rows = [
        {
            "dimension_key": f"dimension_candidate_{position:03d}",
            **{key: value for key, value in item.items() if not key.startswith("_")},
        }
        for position, item in enumerate(raw, start=1)
    ]

    fact_tables = {
        str(table_key).casefold()
        for fact in fact_rows
        for table_key in fact.get("table_keys") or []
    }
    table_rows = _dimension_table_rows(indexes, rows, fact_tables)

    return rows, table_rows


def _dimension_table_rows(
    indexes: ModelIndexes,
    dimension_rows: Sequence[Mapping[str, Any]],
    fact_tables: set[str],
) -> list[dict[str, Any]]:
    """dimension → table 行（anchor = 含命中 Object 的标识字段且不是 fact 表）。"""

    rows: list[dict[str, Any]] = []

    for dimension in dimension_rows:
        object_key = str(dimension.get("object_key") or "")
        anchors = indexes.object_anchor_tables.get(object_key, frozenset())

        for table_key in dimension.get("table_keys") or []:
            folded = str(table_key).casefold()
            meta = indexes.table_meta.get(folded, {})
            association = indexes.assoc_by_key.get((object_key, folded), {})
            role = (
                GRAIN_ROLE_ANCHOR
                if folded in anchors and folded not in fact_tables
                else GRAIN_ROLE_SUPPORTING
            )

            rows.append(
                {
                    "dimension_key": dimension.get("dimension_key"),
                    "object_key": object_key,
                    "object_name": dimension.get("object_name"),
                    "table_key": meta.get("table_key") or table_key,
                    "table_name": meta.get("table_name") or table_key,
                    "workspace_id": association.get("workspace_id")
                    if association
                    else meta.get("workspace_id"),
                    "project": _text(association.get("project")) or _text(meta.get("project")),
                    "role": role,
                    "candidate_layer": indexes.layer_by_table.get(folded),
                    "core_candidate": bool(association.get("core_candidate")),
                    "status": str(association.get("status") or MODEL_STATUS_CANDIDATE),
                    "confidence": str(association.get("confidence") or ""),
                }
            )

    return rows


# ============================================================
# Fact ↔ Dimension Relationship
# ============================================================


def _relationship_entry(
    source_type: str,
    source_id: str,
    *,
    workspace_id: Any,
    table_key: str | None,
    object_key: str,
    process_key: str,
    grain_key: str,
    reason: str,
) -> dict[str, Any]:
    """关系证据条目：按任务要求保留 source_type / source_id / workspace_id /
    table_key / object_key / process_key / grain_key。"""

    return {
        "source_type": source_type,
        "source_id": source_id,
        "workspace_id": workspace_id,
        "table_key": table_key,
        "object_key": object_key,
        "process_key": process_key,
        "grain_key": grain_key,
        "reason": reason,
    }


def _relationship_evidence(
    *,
    fact: Mapping[str, Any],
    dimension: Mapping[str, Any],
    indexes: ModelIndexes,
    fact_tables: set[str],
    statement_indexes: Sequence[int],
    edge_indexes: Sequence[int],
) -> list[dict[str, Any]]:
    """(fact, dimension) 的关系证据（每类最多一条，至少一类才产出候选）。"""

    object_key = str(dimension.get("object_key") or "")
    process_key = str(fact.get("process_candidate_id") or "")
    grain_key = str(fact.get("grain_candidate_id") or "")
    anchor_table = str(fact.get("table_key") or "")
    assoc = indexes.assoc_folded_by_object.get(object_key, frozenset())
    entries: list[dict[str, Any]] = []

    if object_key in indexes.process_objects.get(process_key, ()):
        entries.append(
            _relationship_entry(
                MODEL_REL_EVIDENCE_PROCESS_OBJECT,
                f"process_object:{process_key}:{object_key}",
                workspace_id=fact.get("workspace_id"),
                table_key=anchor_table,
                object_key=object_key,
                process_key=process_key,
                grain_key=grain_key,
                reason=(
                    f"M3.3 process-objects：{object_key} 以 participant 角色出现在 {process_key}"
                ),
            )
        )

    for other in fact.get("object_keys") or []:
        if str(other) == object_key:
            continue

        pair = _pair(object_key, str(other))
        strength = indexes.object_pairs.get(pair)

        if strength is None:
            continue

        entries.append(
            _relationship_entry(
                MODEL_REL_EVIDENCE_OBJECT_RELATIONSHIP,
                f"object_relationship:{pair[0]}-{pair[1]}",
                workspace_id=fact.get("workspace_id"),
                table_key=anchor_table,
                object_key=object_key,
                process_key=process_key,
                grain_key=grain_key,
                reason=(f"M3.2 关系证据：{pair[0]} ↔ {pair[1]}（evidence_strength={strength}）"),
            )
        )

    shared = sorted(fact_tables & assoc)

    if shared:
        display = [
            str(indexes.table_meta.get(folded, {}).get("table_key") or folded) for folded in shared
        ]
        entries.append(
            _relationship_entry(
                MODEL_REL_EVIDENCE_TABLE_REFERENCE,
                f"table_reference:{display[0]}:{object_key}",
                workspace_id=indexes.table_meta.get(shared[0], {}).get("workspace_id"),
                table_key=display[0],
                object_key=object_key,
                process_key=process_key,
                grain_key=grain_key,
                reason=(
                    f"{len(display)} 张表既是 fact candidate 表又是 {object_key} "
                    f"的关联表：{_examples(display)}"
                ),
            )
        )

    for position in statement_indexes:
        hit = sorted(fact_tables & indexes.sql_tables[position] & assoc)

        if not hit:
            continue

        statement = indexes.sql_statements[position]
        display = [
            str(indexes.table_meta.get(folded, {}).get("table_key") or folded) for folded in hit
        ]
        entries.append(
            _relationship_entry(
                MODEL_REL_EVIDENCE_SQL_REFERENCE,
                (
                    f"sql:{statement['workspace_id']}:{statement['file_id']}"
                    f":{statement['statement_id']}"
                ),
                workspace_id=statement["workspace_id"],
                table_key=display[0],
                object_key=object_key,
                process_key=process_key,
                grain_key=grain_key,
                reason=(
                    f"同一条 SQL 语句同时引用 fact 表与 {object_key} 关联表：{_examples(display)}"
                ),
            )
        )
        break

    for position in edge_indexes:
        edge = indexes.lineage_edges[position]
        other = (
            edge["target_folded"] if edge["source_folded"] in fact_tables else edge["source_folded"]
        )

        if other not in assoc:
            continue

        lineage_display = str(indexes.table_meta.get(other, {}).get("table_key") or other)
        entries.append(
            _relationship_entry(
                MODEL_REL_EVIDENCE_LINEAGE,
                f"lineage:{edge['source_key']}->{edge['target_key']}",
                workspace_id=edge.get("workspace_id"),
                table_key=lineage_display,
                object_key=object_key,
                process_key=process_key,
                grain_key=grain_key,
                reason=(f"表级血缘连接 fact 表与 {object_key} 关联表：{lineage_display}"),
            )
        )
        break

    return _sort_evidence(entries, MODEL_REL_EVIDENCE_ORDER)


def _relationship_unresolved(evidence: Sequence[Mapping[str, Any]]) -> list[str]:
    """关系未决原因（固定顺序）。"""

    sources = set(_sources(evidence, MODEL_REL_EVIDENCE_ORDER))
    reasons: list[str] = []

    if len(sources) < 2:
        reasons.append(MODEL_REL_UNRESOLVED_INSUFFICIENT)

    if not (
        MODEL_REL_EVIDENCE_PROCESS_OBJECT in sources
        or MODEL_REL_EVIDENCE_OBJECT_RELATIONSHIP in sources
    ):
        reasons.append(MODEL_REL_UNRESOLVED_OBJECT_LINK)

    if MODEL_REL_EVIDENCE_SQL_REFERENCE not in sources:
        reasons.append(MODEL_REL_UNRESOLVED_SQL)

    if MODEL_REL_EVIDENCE_LINEAGE not in sources:
        reasons.append(MODEL_REL_UNRESOLVED_LINEAGE)

    return sorted(
        set(reasons),
        key=lambda reason: _reason_sort(reason, MODEL_REL_UNRESOLVED_ORDER),
    )


def _relationship_rows(
    indexes: ModelIndexes,
    fact_rows: Sequence[Mapping[str, Any]],
    dimension_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """fact ↔ dimension 关系行：只在至少一类证据时产出。"""

    raw: list[dict[str, Any]] = []

    for fact in fact_rows:
        fact_tables = {str(table).casefold() for table in fact.get("table_keys") or []}
        statement_indexes = sorted(
            {
                position
                for table in fact_tables
                for position in indexes.statements_by_table.get(table, ())
            }
        )
        edge_indexes = sorted(
            {
                position
                for table in fact_tables
                for position in indexes.lineage_by_table.get(table, ())
            }
        )

        for dimension in dimension_rows:
            evidence = _relationship_evidence(
                fact=fact,
                dimension=dimension,
                indexes=indexes,
                fact_tables=fact_tables,
                statement_indexes=statement_indexes,
                edge_indexes=edge_indexes,
            )

            if not evidence:
                continue

            object_key = str(dimension.get("object_key") or "")
            assoc = indexes.assoc_folded_by_object.get(object_key, frozenset())
            shared = sorted(fact_tables & assoc)
            sources = _sources(evidence, MODEL_REL_EVIDENCE_ORDER)
            signature = f"fact={fact.get('fact_key')}|dimension={dimension.get('dimension_key')}"

            raw.append(
                {
                    "_signature": signature,
                    "canonical_signature": signature,
                    "fact_key": fact.get("fact_key"),
                    "dimension_key": dimension.get("dimension_key"),
                    "object_key": object_key,
                    "process_candidate_id": fact.get("process_candidate_id"),
                    "grain_candidate_id": fact.get("grain_candidate_id"),
                    "fact_table_key": fact.get("table_key"),
                    "shared_table_keys": [
                        str(indexes.table_meta.get(folded, {}).get("table_key") or folded)
                        for folded in shared
                    ],
                    "evidence_strength": evidence_strength(len(sources)),
                    "evidence_sources": sources,
                    "evidence_counts": _evidence_counts(evidence, MODEL_REL_EVIDENCE_ORDER),
                    "evidence": evidence,
                    "unresolved_reasons": _relationship_unresolved(evidence),
                    "status": MODEL_STATUS_CANDIDATE,
                    "human_validated": False,
                }
            )

    raw.sort(key=lambda item: str(item["_signature"]))

    return [
        {
            "relationship_key": f"fact_dimension_relationship_{position:03d}",
            **{key: value for key, value in item.items() if not key.startswith("_")},
        }
        for position, item in enumerate(raw, start=1)
    ]


# ============================================================
# 证据矩阵与复核清单
# ============================================================


def _evidence_matrix_rows(
    fact_rows: Sequence[Mapping[str, Any]],
    dimension_rows: Sequence[Mapping[str, Any]],
    relationship_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """model-evidence-matrix.json 的行：fact / dimension 候选的证据覆盖统计。"""

    relationship_by_fact: dict[str, int] = {}
    relationship_by_dimension: dict[str, int] = {}

    for row in relationship_rows:
        fact_key = str(row.get("fact_key") or "")
        dimension_key = str(row.get("dimension_key") or "")
        relationship_by_fact[fact_key] = relationship_by_fact.get(fact_key, 0) + 1
        relationship_by_dimension[dimension_key] = (
            relationship_by_dimension.get(dimension_key, 0) + 1
        )

    rows: list[dict[str, Any]] = []

    for fact in fact_rows:
        fact_key = str(fact.get("fact_key") or "")
        rows.append(
            {
                "candidate_type": MODEL_CANDIDATE_TYPE_FACT,
                "candidate_key": fact_key,
                "status": fact.get("status"),
                "evidence_strength": fact.get("evidence_strength"),
                "evidence_sources": list(fact.get("evidence_sources") or []),
                "evidence_counts": dict(fact.get("evidence_counts") or {}),
                "table_count": len(fact.get("table_keys") or []),
                "process_count": 1 if fact.get("process_candidate_id") else 0,
                "grain_count": 1 if fact.get("grain_candidate_id") else 0,
                "object_count": len(fact.get("object_keys") or []),
                "relationship_count": relationship_by_fact.get(fact_key, 0),
                "unresolved_count": len(fact.get("unresolved_reasons") or []),
            }
        )

    for dimension in dimension_rows:
        dimension_key = str(dimension.get("dimension_key") or "")
        rows.append(
            {
                "candidate_type": MODEL_CANDIDATE_TYPE_DIMENSION,
                "candidate_key": dimension_key,
                "status": dimension.get("status"),
                "evidence_strength": dimension.get("evidence_strength"),
                "evidence_sources": list(dimension.get("evidence_sources") or []),
                "evidence_counts": dict(dimension.get("evidence_counts") or {}),
                "table_count": len(dimension.get("table_keys") or []),
                "process_count": len(dimension.get("referenced_by_processes") or []),
                "grain_count": 0,
                "object_count": 1,
                "relationship_count": relationship_by_dimension.get(dimension_key, 0),
                "unresolved_count": len(dimension.get("unresolved_reasons") or []),
            }
        )

    return rows


def _fact_priority(row: Mapping[str, Any]) -> str | None:
    """fact 候选的复核优先级（None = 不进清单）。"""

    reasons = set(row.get("unresolved_reasons") or [])

    if row.get("evidence_strength") == EVIDENCE_STRENGTH_WEAK or reasons & {
        MODEL_FACT_UNRESOLVED_PROCESS,
        MODEL_FACT_UNRESOLVED_GRAIN,
        MODEL_FACT_UNRESOLVED_MEASURE,
        MODEL_FACT_UNRESOLVED_OBJECT,
    }:
        return MODEL_PRIORITY_FACT_EVIDENCE

    if reasons & {
        MODEL_FACT_UNRESOLVED_AMBIGUOUS_GRAIN,
        MODEL_FACT_UNRESOLVED_SQL,
        MODEL_FACT_UNRESOLVED_LINEAGE,
    }:
        return MODEL_PRIORITY_FACT_AMBIGUOUS

    return None


def _dimension_priority(row: Mapping[str, Any]) -> str | None:
    """dimension 候选的复核优先级。"""

    if row.get("evidence_strength") == EVIDENCE_STRENGTH_WEAK or row.get("unresolved_reasons"):
        return MODEL_PRIORITY_DIMENSION

    return None


def _relationship_priority(row: Mapping[str, Any]) -> str | None:
    """关系候选的复核优先级（只列证据不足或缺 Object 直接链接的行）。"""

    reasons = set(row.get("unresolved_reasons") or [])

    if row.get("evidence_strength") == EVIDENCE_STRENGTH_WEAK or reasons & {
        MODEL_REL_UNRESOLVED_INSUFFICIENT,
        MODEL_REL_UNRESOLVED_OBJECT_LINK,
    }:
        return MODEL_PRIORITY_RELATIONSHIP

    return None


def _build_checklist_rows(
    fact_rows: Sequence[Mapping[str, Any]],
    dimension_rows: Sequence[Mapping[str, Any]],
    relationship_rows: Sequence[Mapping[str, Any]],
) -> list[ModelChecklistRow]:
    """按优先级收集清单行（优先级 → 弱证据在前 → 未决多在前 → key）。"""

    rows: list[ModelChecklistRow] = []

    def add(
        row: Mapping[str, Any],
        key_field: str,
        priority: str | None,
    ) -> None:
        if priority is None:
            return

        rows.append(
            ModelChecklistRow(
                candidate_key=str(row.get(key_field) or ""),
                candidate_type={
                    "fact_key": MODEL_CANDIDATE_TYPE_FACT,
                    "dimension_key": MODEL_CANDIDATE_TYPE_DIMENSION,
                    "relationship_key": MODEL_CANDIDATE_TYPE_RELATIONSHIP,
                }[key_field],
                priority=priority,
                current_status=str(row.get("status") or MODEL_STATUS_CANDIDATE),
                evidence_strength=str(row.get("evidence_strength") or ""),
                unresolved_reasons=[str(item) for item in row.get("unresolved_reasons") or []],
            )
        )

    for row in fact_rows:
        add(row, "fact_key", _fact_priority(row))

    for row in dimension_rows:
        add(row, "dimension_key", _dimension_priority(row))

    for row in relationship_rows:
        add(row, "relationship_key", _relationship_priority(row))

    rows.sort(
        key=lambda item: (
            _rank(item.priority, MODEL_PRIORITY_ORDER),
            _rank(item.evidence_strength, EVIDENCE_STRENGTH_ORDER),
            -len(item.unresolved_reasons),
            item.candidate_key,
        )
    )

    return rows


# ============================================================
# 产物组装、写出与运行入口
# ============================================================


def _checklist_carry_over(inputs: ModelInputs) -> dict[str, dict[str, str]]:
    return _checklist_rows(
        inputs.carryover_text,
        required=MODEL_CHECKLIST_REQUIRED_COLUMNS,
        source=inputs.carryover_path,
        label="model-review-checklist.md",
    )


def build_business_model(inputs: ModelInputs) -> BusinessModelResult:
    """从 M2 / M3 / M3.2 / M3.3 / M3.4 产物构建 M3.5 的六个 JSON 与两个
    Markdown 产物正文。"""

    indexes = build_model_indexes(inputs)
    fact_rows, gate = _fact_rows(indexes)

    indexes.column_names_by_table, indexes.object_anchor_tables = _index_columns(
        inputs.columns,
        {
            folded
            for row in fact_rows
            for folded in (str(table_key).casefold() for table_key in row.get("table_keys") or [])
        }
        | {folded for tables in indexes.assoc_folded_by_object.values() for folded in tables},
        tuple(indexes.registry),
    )

    fact_table_rows = _fact_table_rows(indexes, fact_rows)
    dimension_rows, dimension_table_rows = _dimension_rows(indexes, fact_rows)
    relationship_rows = _relationship_rows(indexes, fact_rows, dimension_rows)

    carry_over = _checklist_carry_over(inputs)
    _apply_carryover(fact_rows, carry_over, key_field="fact_key", label="fact")
    _apply_carryover(dimension_rows, carry_over, key_field="dimension_key", label="dimension")
    _apply_carryover(
        relationship_rows,
        carry_over,
        key_field="relationship_key",
        label="relationship",
    )

    fact_payload: dict[str, Any] = {
        "count": len(fact_rows),
        "note": (
            f"{MODEL_CANDIDATE_NOTE}；fact 只来自通过 Fact Gate 的 grain "
            "candidate（transaction / event / snapshot 直接通过，periodic / "
            "aggregation / unknown 必须有 measure 字段）。"
        ),
        "status_counts": _status_counts(
            [str(row.get("status") or "") for row in fact_rows], MODEL_STATUS_ORDER
        ),
        "strength_counts": _status_counts(
            [str(row.get("evidence_strength") or "") for row in fact_rows],
            EVIDENCE_STRENGTH_ORDER,
        ),
        "pattern_counts": _status_counts(
            [str(row.get("grain_pattern") or "") for row in fact_rows],
            GRAIN_PATTERN_ORDER,
        ),
        "unresolved_counts": _unresolved_counts(fact_rows, MODEL_FACT_UNRESOLVED_ORDER),
        "gate": gate,
        "process_count": len({str(row.get("process_candidate_id") or "") for row in fact_rows}),
        "grain_count": len({str(row.get("grain_candidate_id") or "") for row in fact_rows}),
        "table_count": len(
            {
                str(table_key).casefold()
                for row in fact_rows
                for table_key in row.get("table_keys") or []
            }
        ),
        "object_count": len(
            {str(obj) for row in fact_rows for obj in row.get("object_keys") or []}
        ),
        "candidates": fact_rows,
    }

    dimension_payload: dict[str, Any] = {
        "count": len(dimension_rows),
        "note": (
            f"{MODEL_CANDIDATE_NOTE}；dimension 按 M3.1 Object 逐个生成，"
            "attributes 只是关联表里观察到的字段清单，属性多不构成强结论。"
        ),
        "status_counts": _status_counts(
            [str(row.get("status") or "") for row in dimension_rows],
            MODEL_STATUS_ORDER,
        ),
        "strength_counts": _status_counts(
            [str(row.get("evidence_strength") or "") for row in dimension_rows],
            EVIDENCE_STRENGTH_ORDER,
        ),
        "role_status_counts": _status_counts(
            [str(row.get("role_status") or "") for row in dimension_rows],
            MODEL_ROLE_STATUS_ORDER,
        ),
        "unresolved_counts": _unresolved_counts(dimension_rows, MODEL_DIMENSION_UNRESOLVED_ORDER),
        "table_count": len(
            {
                str(table_key).casefold()
                for row in dimension_rows
                for table_key in row.get("table_keys") or []
            }
        ),
        "candidates": dimension_rows,
    }

    relationship_payload: dict[str, Any] = {
        "count": len(relationship_rows),
        "note": (
            f"{MODEL_CANDIDATE_NOTE}；relationship ≠ 业务关系，每行至少一类证据，确认必须人工完成。"
        ),
        "status_counts": _status_counts(
            [str(row.get("status") or "") for row in relationship_rows],
            MODEL_STATUS_ORDER,
        ),
        "strength_counts": _status_counts(
            [str(row.get("evidence_strength") or "") for row in relationship_rows],
            EVIDENCE_STRENGTH_ORDER,
        ),
        "unresolved_counts": _unresolved_counts(relationship_rows, MODEL_REL_UNRESOLVED_ORDER),
        "evidence_source_counts": _evidence_counts(
            [entry for row in relationship_rows for entry in row.get("evidence") or []],
            MODEL_REL_EVIDENCE_ORDER,
        ),
        "relationships": relationship_rows,
    }

    fact_tables_payload: dict[str, Any] = {
        "count": len(fact_table_rows),
        "note": (
            "fact → table 只表达技术角色（role 复用 M3.4 grain 的 anchor / "
            "supporting）；core_candidate 只作证据覆盖与复核优先级，"
            "不是业务价值判断。"
        ),
        "role_counts": _status_counts(
            [str(row.get("role") or "") for row in fact_table_rows], GRAIN_ROLE_ORDER
        ),
        "tables": fact_table_rows,
    }

    dimension_tables_payload: dict[str, Any] = {
        "count": len(dimension_table_rows),
        "note": (
            "dimension → table 只表达技术角色（anchor = 含命中该 Object 的标识"
            "字段且不是 fact candidate 表，supporting = 其余关联表）；"
            "role 不是 DWD / DWS 结论。"
        ),
        "role_counts": _status_counts(
            [str(row.get("role") or "") for row in dimension_table_rows],
            GRAIN_ROLE_ORDER,
        ),
        "tables": dimension_table_rows,
    }

    matrix_rows = _evidence_matrix_rows(fact_rows, dimension_rows, relationship_rows)

    evidence_matrix_payload: dict[str, Any] = {
        "count": len(matrix_rows),
        "note": (
            "evidence matrix 只做覆盖统计：每行是一个 fact / dimension 候选的"
            "证据源、计数与关联实体数量，不是结论；关系证据见 "
            "fact-dimension-relationships.json。"
        ),
        "fact_evidence_order": list(FACT_EVIDENCE_ORDER),
        "dimension_evidence_order": list(DIMENSION_EVIDENCE_ORDER),
        "relationship_evidence_order": list(MODEL_REL_EVIDENCE_ORDER),
        "rows": matrix_rows,
    }

    checklist_rows = _build_checklist_rows(fact_rows, dimension_rows, relationship_rows)

    result = BusinessModelResult(
        fact_candidates=fact_payload,
        dimension_candidates=dimension_payload,
        relationships=relationship_payload,
        fact_tables=fact_tables_payload,
        dimension_tables=dimension_tables_payload,
        evidence_matrix=evidence_matrix_payload,
        checklist_rows=checklist_rows,
        analysis_dir=inputs.analysis_dir,
    )

    result.summary = render_model_summary(
        fact_candidates=fact_payload,
        dimension_candidates=dimension_payload,
        relationships=relationship_payload,
        fact_tables=fact_tables_payload,
        dimension_tables=dimension_tables_payload,
        evidence_matrix=evidence_matrix_payload,
        processes=[indexes.processes[key] for key in sorted(indexes.processes)],
        inventory_table_count=len(inputs.inventory_tables),
        grain_candidate_count=len(inputs.grain_candidates),
        priority_counts=result.priority_counts,
        profiling=indexes.profiling,
        analysis_dir=inputs.analysis_dir,
    )
    result.checklist = render_model_review_checklist(
        checklist_rows,
        carry_over=carry_over,
        row_limit=MODEL_CHECKLIST_ROW_LIMIT,
    )

    return result


def write_business_model(
    result: BusinessModelResult,
    output_dir: Path,
) -> tuple[Path, ...]:
    """写出 M3.5 产物，返回路径列表（固定顺序）。

    只覆盖本模块声明的八个文件，不删除、不改写已有 M2 / M3 产物。
    """

    ensure_dir(output_dir)

    paths = {name: output_dir / name for name in OUTPUT_FILES}

    write_json(paths["fact-candidates.json"], result.fact_candidates)
    write_json(paths["dimension-candidates.json"], result.dimension_candidates)
    write_json(paths["fact-dimension-relationships.json"], result.relationships)
    write_json(paths["fact-tables.json"], result.fact_tables)
    write_json(paths["dimension-tables.json"], result.dimension_tables)
    write_json(paths["model-evidence-matrix.json"], result.evidence_matrix)
    write_text(paths["model-summary.md"], result.summary)
    write_text(paths["model-review-checklist.md"], result.checklist)

    logger.info(
        "M3.5 产物已写出：%s",
        "，".join(_display_path(paths[name]) for name in OUTPUT_FILES),
    )

    return tuple(paths[name] for name in OUTPUT_FILES)


def run_business_model_analysis(
    *,
    analysis_dir: Path,
    output_dir: Path,
) -> BusinessModelResult:
    """执行 M3.5 Fact / Dimension Candidate Analysis 并写出产物。

    只读 M2 / M3 / M3.2 / M3.3 / M3.4 产物；输入缺失时直接报错，
    不自动回退去跑前置阶段。
    """

    # 旧布局把 M3.5 产物写在 business/：先清理遗留文件（本阶段清单搬迁保留人工列），
    # 保证同一阶段的产物只存在于 output_dir。
    relocate_legacy_artifacts(
        analysis_dir,
        output_dir,
        legacy_dir="business",
        output_files=OUTPUT_FILES,
        carryover_files=(Path(CARRYOVER_CHECKLIST_INPUT_FILE).name,),
    )

    inputs = read_model_inputs(analysis_dir)
    result = build_business_model(inputs)
    result.analysis_dir = analysis_dir

    write_business_model(result, output_dir)

    logger.info(
        "M3.5 Fact / Dimension Candidate Analysis 完成：fact=%s（%s），"
        "dimension=%s，relationship=%s，fact table=%s，dimension table=%s",
        result.fact_count,
        "，".join(f"{key}={value}" for key, value in result.status_counts.items()),
        result.dimension_count,
        result.relationship_count,
        result.fact_table_count,
        result.dimension_table_count,
    )

    return result

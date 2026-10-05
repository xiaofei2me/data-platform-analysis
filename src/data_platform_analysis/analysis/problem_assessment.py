"""M3.6 v2 Current-State Problem Assessment。

把 M3.6 的 finding 聚合成有证据支撑的 problem candidate，建立

    Problem → Evidence → Impact → Root Cause → Refactoring Rationale
    → Human Confirmation

的证据链，为 M4 Target DWD Design 提供「先解决什么、为什么、还差什么
人工确认」的输入。

判断边界（与 M3.6 一致）：

    Evidence First ─ 每条 problem 至少一条 evidence，并能回溯到
                table / column / process / grain / object /
                lineage / relationship / finding。
    Candidate ≠ Confirmed ─ 机器阶段 status 只能是 candidate 或
                review_required；confirmed / rejected 只能来自
                current-state-problem-review-checklist.md 的人工回填。
    Finding ≠ Problem ─ finding 是逐条观测，problem 是同一根因下的
                聚合；Finding Count ≠ Problem Count ≠ Confirmed
                Problem Count。一条 finding 可以进入多条 problem。
    不设计 Target DWD ─ 只输出当前问题、证据、影响、根因、重构理由
                与人工确认入口，不产出 DWD / DWS / Semantic Layer
                结论，不改写 M3.6 已有五个产物，不改上游 M1 / M3 / M3.5。

输入（全部复用 M3.6 已读的 13 个产物，不读 profiling / SQL 参考 /
source/，不调用 LLM / 外部 API）：

    analysis/business/current-state-problem-review-checklist.md  （可选回填）

输出（由 model_review.run_current_state_model_analysis 一并写出）：

    analysis/business/current-state-problems.json
    analysis/business/current-state-problem-evidence.json
    analysis/business/current-state-problem-summary.md
    analysis/business/current-state-problem-review-checklist.md
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..io_utils import ensure_dir, write_json, write_text
from .business_grain import (
    BusinessGrainError,
    _display_path,
    _parse_checklist_rows,
    _rank,
    _status_counts,
)
from .business_model import fact_gate
from .business_objects import _text
from .model_review import (
    CurrentStateModelError,
    ReviewIndexes,
    ReviewInputs,
    _fold,
    build_review_indexes,
)
from .models import (
    AGGREGATE_ASSESSMENT_MODEL_PROBLEM,
    AGGREGATE_ASSESSMENT_ORDER,
    AGGREGATE_ASSESSMENT_REVIEW_REQUIRED,
    AGGREGATE_ASSESSMENT_VALID,
    AGGREGATE_MIN_UPSTREAM_FOR_VALID,
    EVIDENCE_STRENGTH_MODERATE,
    EVIDENCE_STRENGTH_ORDER,
    EVIDENCE_STRENGTH_STRONG,
    EVIDENCE_STRENGTH_WEAK,
    FINDING_TYPE_AGGREGATE_FACT,
    FINDING_TYPE_DIMENSION_OBJECT_DERIVED,
    FINDING_TYPE_DUPLICATE_FACT,
    FINDING_TYPE_EVIDENCE_STRENGTH,
    FINDING_TYPE_FACT_GATE_NO_MEASURE,
    FINDING_TYPE_FACT_GATE_PATTERN,
    FINDING_TYPE_FACT_WITHOUT_MEASURE,
    FINDING_TYPE_GRAIN_CONFLICT,
    FINDING_TYPE_MIXED_GRAIN,
    FINDING_TYPE_MULTI_PROCESS_TABLE,
    FINDING_TYPE_OVERLAPPING_FACT,
    FINDING_TYPE_PROCESS_MULTIPLE_GRAINS,
    FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE,
    FINDING_TYPE_RELATIONSHIP_TECHNICAL,
    FINDING_TYPE_RESULT_TABLE,
    FINDING_TYPE_ROLE_AMBIGUOUS,
    FINDING_TYPE_SNAPSHOT_PERIODIC,
    FINDING_TYPE_WIDE_ANALYTICAL_TABLE,
    GRAIN_ASSESSMENT_CONFIRMED_CONFLICT,
    GRAIN_ASSESSMENT_ORDER,
    GRAIN_ASSESSMENT_POSSIBLE_CONFLICT,
    GRAIN_ASSESSMENT_REVIEW_REQUIRED,
    MODEL_HUMAN_STATUS_PENDING,
    MODEL_STATUS_NEEDS_DISCUSSION,
    OVERLAP_CLASS_DIVERGENT_STRUCTURE,
    OVERLAP_CLASS_DUPLICATION,
    OVERLAP_CLASS_ORDER,
    OVERLAP_CLASS_STRUCTURAL,
    OVERLAP_CLASS_TECHNICAL_COPY,
    PROBLEM_CANDIDATE_NOTE,
    PROBLEM_CARRYOVER_FILE,
    PROBLEM_CHECKLIST_REQUIRED_COLUMNS,
    PROBLEM_EVIDENCE_COLUMN,
    PROBLEM_EVIDENCE_FINDING,
    PROBLEM_EVIDENCE_GRAIN,
    PROBLEM_EVIDENCE_LINEAGE,
    PROBLEM_EVIDENCE_OBJECT,
    PROBLEM_EVIDENCE_ORDER,
    PROBLEM_EVIDENCE_PROCESS,
    PROBLEM_EVIDENCE_RELATIONSHIP,
    PROBLEM_EVIDENCE_ROW_LIMIT,
    PROBLEM_EVIDENCE_SET,
    PROBLEM_EVIDENCE_SQL,
    PROBLEM_EVIDENCE_TABLE,
    PROBLEM_ID_FORMAT,
    PROBLEM_IMPACT_AI_SEMANTIC_RISK,
    PROBLEM_IMPACT_ANALYTICAL_RISK,
    PROBLEM_IMPACT_DATA_CONSUMER_CONFUSION,
    PROBLEM_IMPACT_DUPLICATED_MODEL,
    PROBLEM_IMPACT_GOVERNANCE_DIFFICULTY,
    PROBLEM_IMPACT_GRAIN_INCONSISTENCY,
    PROBLEM_IMPACT_MAINTENANCE_COST,
    PROBLEM_IMPACT_METRIC_AMBIGUITY,
    PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY,
    PROBLEM_IMPACT_ORDER,
    PROBLEM_IMPACT_QUERY_COMPLEXITY,
    PROBLEM_IMPACT_REUSE_DIFFICULTY,
    PROBLEM_IMPACT_TITLE,
    PROBLEM_OUTPUT_FILES,
    PROBLEM_ROOT_CAUSE_AGGREGATION_ATOMIC_MIX,
    PROBLEM_ROOT_CAUSE_DUPLICATED_PIPELINES,
    PROBLEM_ROOT_CAUSE_GATE_MEASURE_DEPENDENCY,
    PROBLEM_ROOT_CAUSE_LAYER_OVERLAP,
    PROBLEM_ROOT_CAUSE_MULTIPLE_GRAINS,
    PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION,
    PROBLEM_ROOT_CAUSE_ORDER,
    PROBLEM_ROOT_CAUSE_RESPONSIBILITY_MIX,
    PROBLEM_ROOT_CAUSE_SOURCE_REPLICATION,
    PROBLEM_ROOT_CAUSE_UNKNOWN,
    PROBLEM_ROOT_CAUSE_UNRESOLVED_ROLE,
    PROBLEM_SCOPE_DIMENSION,
    PROBLEM_SCOPE_ORDER,
    PROBLEM_SCOPE_PROCESS,
    PROBLEM_SCOPE_SET,
    PROBLEM_SCOPE_STAGE,
    PROBLEM_SCOPE_TABLE,
    PROBLEM_SCOPE_TABLE_SET,
    PROBLEM_STATUS_BY_HUMAN_STATUS,
    PROBLEM_STATUS_CANDIDATE,
    PROBLEM_STATUS_CONFIRMED,
    PROBLEM_STATUS_ORDER,
    PROBLEM_STATUS_REVIEW_REQUIRED,
    PROBLEM_TYPE_AGGREGATION,
    PROBLEM_TYPE_COVERAGE_GAP,
    PROBLEM_TYPE_DIMENSION_IDENTIFICATION,
    PROBLEM_TYPE_DUPLICATION,
    PROBLEM_TYPE_FACT_IDENTIFICATION,
    PROBLEM_TYPE_GRAIN,
    PROBLEM_TYPE_MIXED_RESPONSIBILITY,
    PROBLEM_TYPE_ORDER,
    PROBLEM_TYPE_OVERLAP,
    PROBLEM_TYPE_PRIORITY,
    PROBLEM_TYPE_PROCESS_ALIGNMENT,
    PROBLEM_TYPE_ROLE_AMBIGUITY,
    PROBLEM_TYPE_SELECTION_AMBIGUITY,
    PROBLEM_TYPE_SEMANTIC_AMBIGUITY,
    PROBLEM_TYPE_SET,
    PROBLEM_TYPE_UNKNOWN_MODEL,
    REVIEW_EVIDENCE_COLUMN,
    REVIEW_EVIDENCE_DIMENSION,
    REVIEW_EVIDENCE_FACT,
    REVIEW_EVIDENCE_GRAIN,
    REVIEW_EVIDENCE_LINEAGE,
    REVIEW_EVIDENCE_OBJECT,
    REVIEW_EVIDENCE_PROCESS,
    REVIEW_EVIDENCE_RELATIONSHIP,
    REVIEW_EVIDENCE_SQL,
    REVIEW_EVIDENCE_TABLE,
    REVIEW_PRIORITY_ORDER,
    REVIEW_SEVERITY_BY_PRIORITY,
    SELECTION_AMBIGUITY_MIN_DUPLICATION,
    UNKNOWN_REASON_NO_ANCHOR,
    UNKNOWN_REASON_NO_EVIDENCE,
    UNKNOWN_REASON_ORDER,
    CurrentStateProblemResult,
    normalize_human_status,
)
from .reports import (
    render_current_state_problem_review_checklist,
    render_current_state_problem_summary,
)

logger = logging.getLogger(__name__)

# ============================================================
# 模块常量
# ============================================================

PROBLEM_EVIDENCE_SAMPLE = 5
"""problems.json 里每条 problem 展示的证据样例条数（全量在 evidence 产物）。"""

PROBLEM_UNRESOLVED_REASON = (
    "机器只能基于 M1–M3.6 的只读证据做聚合，不能判断业务对错、权威版本与优先级；"
    "problem 保持 candidate，需人工回填清单后才能变成 confirmed"
)
"""problem 的未解决原因（机器阶段恒定口径）。"""

SIGNAL_AGGREGATE = "AGGREGATE"
SIGNAL_MIXED_GRAIN = "MIXED_GRAIN"
SIGNAL_PERIODIC_FACT = "PERIODIC_FACT"
SIGNAL_SNAPSHOT_FACT = "SNAPSHOT_FACT"
SIGNAL_WIDE = "WIDE"
SIGNAL_RESULT = "RESULT"
SIGNAL_DIMENSION = "DIMENSION"

SIGNAL_ORDER: tuple[str, ...] = (
    SIGNAL_DIMENSION,
    SIGNAL_AGGREGATE,
    SIGNAL_MIXED_GRAIN,
    SIGNAL_PERIODIC_FACT,
    SIGNAL_SNAPSHOT_FACT,
    SIGNAL_WIDE,
    SIGNAL_RESULT,
)
"""职责信号的固定顺序（MIXED_RESPONSIBILITY 判定与展示用）。"""

RESPONSIBILITY_SELF_SUFFICIENT: frozenset[str] = frozenset({SIGNAL_WIDE, SIGNAL_RESULT})
"""只出现一个也构成职责混杂的信号：宽表分析职责与结果落地职责。"""

AGGREGATE_SIGNALS: frozenset[str] = frozenset({SIGNAL_AGGREGATE, SIGNAL_PERIODIC_FACT})
"""同时出现时把职责混杂判定为「聚合与原子数据混合」的信号组合。"""

GRAIN_FINDING_TYPES: tuple[str, ...] = (
    FINDING_TYPE_GRAIN_CONFLICT,
    FINDING_TYPE_MIXED_GRAIN,
    FINDING_TYPE_SNAPSHOT_PERIODIC,
)
"""进入 GRAIN_PROBLEM 的 finding 类型（都以表为 scope）。"""

CORE_SHAPE_FINDING_TYPES: tuple[str, ...] = (
    FINDING_TYPE_AGGREGATE_FACT,
    FINDING_TYPE_MIXED_GRAIN,
    FINDING_TYPE_RESULT_TABLE,
    FINDING_TYPE_WIDE_ANALYTICAL_TABLE,
)
"""进入 MIXED_RESPONSIBILITY 判定的形态类 finding。"""

FINDING_SOURCE_TO_PROBLEM_EVIDENCE: dict[str, str] = {
    REVIEW_EVIDENCE_TABLE: PROBLEM_EVIDENCE_TABLE,
    REVIEW_EVIDENCE_COLUMN: PROBLEM_EVIDENCE_COLUMN,
    REVIEW_EVIDENCE_PROCESS: PROBLEM_EVIDENCE_PROCESS,
    REVIEW_EVIDENCE_GRAIN: PROBLEM_EVIDENCE_GRAIN,
    REVIEW_EVIDENCE_OBJECT: PROBLEM_EVIDENCE_OBJECT,
    REVIEW_EVIDENCE_SQL: PROBLEM_EVIDENCE_SQL,
    REVIEW_EVIDENCE_LINEAGE: PROBLEM_EVIDENCE_LINEAGE,
    REVIEW_EVIDENCE_RELATIONSHIP: PROBLEM_EVIDENCE_RELATIONSHIP,
    REVIEW_EVIDENCE_FACT: PROBLEM_EVIDENCE_TABLE,
    REVIEW_EVIDENCE_DIMENSION: PROBLEM_EVIDENCE_TABLE,
}
"""finding 证据类型 → problem 证据类型；profiling / layer 本阶段不参与问题证据。"""

IMPACT_TYPES_BY_TYPE: dict[str, tuple[str, ...]] = {
    PROBLEM_TYPE_GRAIN: (PROBLEM_IMPACT_GRAIN_INCONSISTENCY,
        PROBLEM_IMPACT_METRIC_AMBIGUITY,),
    PROBLEM_TYPE_OVERLAP: (PROBLEM_IMPACT_QUERY_COMPLEXITY,
        PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY,),
    PROBLEM_TYPE_DUPLICATION: (
        PROBLEM_IMPACT_DUPLICATED_MODEL,
        PROBLEM_IMPACT_MAINTENANCE_COST,
        PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY,
    ),
    PROBLEM_TYPE_MIXED_RESPONSIBILITY: (PROBLEM_IMPACT_MAINTENANCE_COST,
        PROBLEM_IMPACT_GOVERNANCE_DIFFICULTY,),
    PROBLEM_TYPE_ROLE_AMBIGUITY: (PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY,
        PROBLEM_IMPACT_DATA_CONSUMER_CONFUSION,),
    PROBLEM_TYPE_PROCESS_ALIGNMENT: (PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY,
        PROBLEM_IMPACT_QUERY_COMPLEXITY,),
    PROBLEM_TYPE_AGGREGATION: (PROBLEM_IMPACT_METRIC_AMBIGUITY,
        PROBLEM_IMPACT_MAINTENANCE_COST,),
    PROBLEM_TYPE_FACT_IDENTIFICATION: (PROBLEM_IMPACT_ANALYTICAL_RISK,
        PROBLEM_IMPACT_METRIC_AMBIGUITY,),
    PROBLEM_TYPE_DIMENSION_IDENTIFICATION: (PROBLEM_IMPACT_REUSE_DIFFICULTY,
        PROBLEM_IMPACT_DATA_CONSUMER_CONFUSION,),
    PROBLEM_TYPE_SELECTION_AMBIGUITY: (PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY,
        PROBLEM_IMPACT_QUERY_COMPLEXITY,),
    PROBLEM_TYPE_SEMANTIC_AMBIGUITY: (PROBLEM_IMPACT_AI_SEMANTIC_RISK,
        PROBLEM_IMPACT_METRIC_AMBIGUITY,),
    PROBLEM_TYPE_COVERAGE_GAP: (PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY,
        PROBLEM_IMPACT_ANALYTICAL_RISK,),
    PROBLEM_TYPE_UNKNOWN_MODEL: (PROBLEM_IMPACT_GOVERNANCE_DIFFICULTY,
        PROBLEM_IMPACT_DATA_CONSUMER_CONFUSION,),
}
"""problem_type → 影响类型（结构后果，只在问题成立时给）。"""

ROOT_CAUSE_BY_TYPE: dict[str, str] = {
    PROBLEM_TYPE_GRAIN: PROBLEM_ROOT_CAUSE_MULTIPLE_GRAINS,
    PROBLEM_TYPE_OVERLAP: PROBLEM_ROOT_CAUSE_LAYER_OVERLAP,
    PROBLEM_TYPE_DUPLICATION: PROBLEM_ROOT_CAUSE_DUPLICATED_PIPELINES,
    PROBLEM_TYPE_MIXED_RESPONSIBILITY: PROBLEM_ROOT_CAUSE_RESPONSIBILITY_MIX,
    PROBLEM_TYPE_ROLE_AMBIGUITY: PROBLEM_ROOT_CAUSE_UNRESOLVED_ROLE,
    PROBLEM_TYPE_PROCESS_ALIGNMENT: PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION,
    PROBLEM_TYPE_AGGREGATION: PROBLEM_ROOT_CAUSE_AGGREGATION_ATOMIC_MIX,
    PROBLEM_TYPE_FACT_IDENTIFICATION: PROBLEM_ROOT_CAUSE_GATE_MEASURE_DEPENDENCY,
    PROBLEM_TYPE_DIMENSION_IDENTIFICATION: PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION,
    PROBLEM_TYPE_SELECTION_AMBIGUITY: PROBLEM_ROOT_CAUSE_DUPLICATED_PIPELINES,
    PROBLEM_TYPE_SEMANTIC_AMBIGUITY: PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION,
    PROBLEM_TYPE_COVERAGE_GAP: PROBLEM_ROOT_CAUSE_UNKNOWN,
    PROBLEM_TYPE_UNKNOWN_MODEL: PROBLEM_ROOT_CAUSE_UNKNOWN,
}
"""problem_type → 默认根因（classification 可覆盖）。"""

REVIEW_REQUIRED_CLASSIFICATIONS: frozenset[str] = frozenset(
    {
        GRAIN_ASSESSMENT_REVIEW_REQUIRED,
        AGGREGATE_ASSESSMENT_REVIEW_REQUIRED,
    }
)
"""classification 直接把 status 抬到 review_required 的取值。"""


# ============================================================
# 证据构造
# ============================================================


PROBLEM_EVIDENCE_ROW_KEYS: tuple[str, ...] = (
    "evidence_type",
    "evidence_id",
    "table_key",
    "table_name",
    "column_name",
    "process_key",
    "grain_key",
    "object_key",
    "finding_id",
    "reason",
)
"""problem 证据行的字段顺序（两个产物一致）。"""


def _problem_evidence(
    evidence_type: str,
    evidence_id: str,
    *,
    table_key: str = "",
    table_name: str = "",
    column_name: str | None = None,
    process_key: str = "",
    grain_key: str = "",
    object_key: str = "",
    finding_id: str = "",
    reason: str = "",
) -> dict[str, Any]:
    """构造一条 problem 证据行（类型必须在 PROBLEM_EVIDENCE_SET 内）。"""

    if evidence_type not in PROBLEM_EVIDENCE_SET:
        raise CurrentStateModelError(f"未知的 problem 证据类型：{evidence_type}")

    return {
        "evidence_type": evidence_type,
        "evidence_id": evidence_id,
        "table_key": table_key,
        "table_name": table_name,
        "column_name": column_name,
        "process_key": process_key,
        "grain_key": grain_key,
        "object_key": object_key,
        "finding_id": finding_id,
        "reason": reason,
    }


def _sort_evidence(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """按（类型固定顺序, evidence_id, table_key, column_name, finding_id, reason）去重排序。"""

    seen: dict[tuple[Any, ...], dict[str, Any]] = {}

    for row in rows:
        key = (
            str(row.get("evidence_type") or ""),
            str(row.get("evidence_id") or ""),
            str(row.get("table_key") or ""),
            str(row.get("column_name") or ""),
            str(row.get("finding_id") or ""),
            str(row.get("reason") or ""),
        )
        seen.setdefault(
            key,
            {name: row.get(name) for name in (*PROBLEM_EVIDENCE_ROW_KEYS, "reason")},
        )

    return sorted(
        seen.values(),
        key=lambda row: (
            _rank(str(row.get("evidence_type") or ""), PROBLEM_EVIDENCE_ORDER),
            str(row.get("evidence_id") or ""),
            str(row.get("table_key") or ""),
            str(row.get("column_name") or ""),
            str(row.get("finding_id") or ""),
            str(row.get("reason") or ""),
        ),
    )


def _problem_evidence_strength(type_count: int) -> str:
    """按 distinct evidence 类型数给出问题级 evidence_strength。

    问题级口径比关系证据更严格：≥4 类 = strong，3 类 = moderate，≤2 类 = weak。
    """

    if type_count >= 4:
        return EVIDENCE_STRENGTH_STRONG

    if type_count == 3:
        return EVIDENCE_STRENGTH_MODERATE

    return EVIDENCE_STRENGTH_WEAK


def _finding_evidence(finding: Mapping[str, Any]) -> list[dict[str, Any]]:
    """把一条 finding 的证据映射成 problem 证据（不足一条时用 table 兜底）。"""

    rows: list[dict[str, Any]] = []

    for entry in finding.get("evidence") or []:
        source_type = str(entry.get("source_type") or "")
        mapped = FINDING_SOURCE_TO_PROBLEM_EVIDENCE.get(source_type)

        if not mapped:
            continue

        prefix = ""

        if source_type in (REVIEW_EVIDENCE_FACT, REVIEW_EVIDENCE_DIMENSION):
            prefix = f"（{source_type}）"

        rows.append(
            _problem_evidence(
                mapped,
                str(entry.get("source_id") or ""),
                table_key=str(entry.get("table_key") or ""),
                table_name=str(finding.get("table_name") or ""),
                column_name=_text(entry.get("column_name")),
                finding_id=str(finding.get("finding_id") or ""),
                reason=f"{prefix}{entry.get('reason') or ''}".strip(),
            )
        )

    if rows:
        return rows

    table_key = str(finding.get("table_key") or "")

    if table_key:
        return [
            _problem_evidence(
                PROBLEM_EVIDENCE_TABLE,
                table_key,
                table_key=table_key,
                table_name=str(finding.get("table_name") or ""),
                finding_id=str(finding.get("finding_id") or ""),
                reason=str(finding.get("description") or "finding 仅提供表级证据"),
            )
        ]

    raise CurrentStateModelError(
        f"finding {finding.get('finding_type')}（{finding.get('scope_key')}）"
        "没有可映射的 problem 证据：Evidence First 不允许无证据问题"
    )


# ============================================================
# 上下文
# ============================================================


@dataclass
class _Context:
    """problem 聚合所需的只读上下文。"""

    inputs: ReviewInputs
    indexes: ReviewIndexes
    findings: list[dict[str, Any]] = field(default_factory=list)
    table_rows: list[dict[str, Any]] = field(default_factory=list)
    finding_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    findings_by_type: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    findings_by_table: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    table_by_key: dict[str, dict[str, Any]] = field(default_factory=dict)
    grains_by_table: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    fact_anchor_tables: frozenset[str] = frozenset()
    processes_with_fact: frozenset[str] = frozenset()


def _table_row(ctx: _Context, table_key: str) -> dict[str, Any]:
    return ctx.table_by_key.get(table_key) or {}


def _grains(ctx: _Context, table_key: str) -> list[dict[str, Any]]:
    return ctx.grains_by_table.get(table_key) or []


def _grain_signatures(grains: Sequence[Mapping[str, Any]]) -> set[tuple[str, str]]:
    """grain 候选的签名集合：(grain_pattern, 候选键 slug)。"""

    return {
        (
            str(grain.get("grain_pattern") or ""),
            "+".join(sorted(str(key) for key in grain.get("candidate_keys") or [])),
        )
        for grain in grains
    }


def _table_processes(ctx: _Context, table_key: str) -> tuple[str, ...]:
    """表所属 process：table row 的 process_candidate_ids 优先，缺时回退 grain 索引。"""

    row = _table_row(ctx, table_key)
    declared = [str(value) for value in row.get("process_candidate_ids") or [] if value]

    if declared:
        return tuple(sorted(set(declared)))

    return ctx.indexes.processes_by_table.get(_fold(table_key), ())


def _column_set(ctx: _Context, table_key: str) -> frozenset[str]:
    return frozenset(ctx.indexes.column_names.get(_fold(table_key), ()))


def _process_key(record: Mapping[str, Any]) -> str:
    """process 记录的稳定 key（processes.json 用 process_key）。"""

    return str(record.get("process_key") or record.get("process_candidate_id") or "")


def _keys_slug(grain: Mapping[str, Any]) -> str:
    """grain 候选键的稳定 slug。"""

    return "+".join(sorted(str(key) for key in grain.get("candidate_keys") or []))


def _component_processes(ctx: _Context, tables: Sequence[str]) -> list[str]:
    """连通分量涉及的全部 process（去重排序）。"""

    return sorted(
        {
            process
            for table_key in tables
            for process in _table_processes(ctx, table_key)
        }
    )


def _finding_ids(findings: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        str(finding.get("finding_id") or "")
        for finding in findings
        if finding.get("finding_id")
    ]


def _lineage_pairs(
    ctx: _Context,
    tables: Sequence[str],
) -> list[tuple[str, str]]:
    """连通分量内部的血缘边（两个方向都算）。"""

    folded = {_fold(table): table for table in tables}
    pairs: set[tuple[str, str]] = set()

    for table in tables:
        source = _fold(table)

        for target in ctx.indexes.lineage_out.get(source, ()):
            if target in folded:
                left, right = sorted((table, folded[target]))
                pairs.add((left, right))

        for target in ctx.indexes.lineage_in.get(source, ()):
            if target in folded:
                left, right = sorted((folded[target], table))
                pairs.add((left, right))

    return sorted(pairs)


def _jaccard_stats(
    ctx: _Context,
    tables: Sequence[str],
) -> tuple[float | None, tuple[str, str] | None]:
    """连通分量内部的字段重合度（只比较字段数达标的表对）。"""

    best: float | None = None
    best_pair: tuple[str, str] | None = None

    for position, left in enumerate(tables):
        for right in tables[position + 1 :]:
            left_set = _column_set(ctx, left)
            right_set = _column_set(ctx, right)

            if len(left_set) < 10 or len(right_set) < 10:
                continue

            total = len(left_set | right_set)

            if not total:
                continue

            ratio = len(left_set & right_set) / total

            if best is None or ratio > best:
                best = ratio
                best_pair = (left, right)

    return best, best_pair


def _shared_grain_signature(
    ctx: _Context,
    tables: Sequence[str],
) -> tuple[str, str] | None:
    """所有表共享的 grain 签名（无共享返回 None）。"""

    shared: set[tuple[str, str]] | None = None

    for table in tables:
        signatures = _grain_signatures(_grains(ctx, table))
        shared = signatures if shared is None else (shared & signatures)

        if not shared:
            return None

    return sorted(shared)[0] if shared else None


def _shared_processes(ctx: _Context, tables: Sequence[str]) -> tuple[str, ...]:
    shared: set[str] | None = None

    for table in tables:
        processes = set(_table_processes(ctx, table))
        shared = processes if shared is None else (shared & processes)

        if not shared:
            return ()

    return tuple(sorted(shared or ()))


def _layers(ctx: _Context, tables: Sequence[str]) -> frozenset[str]:
    return frozenset(
        str(ctx.indexes.layer_by_table.get(_fold(table)) or "") for table in tables
    ) - {""}


def _is_technical_copy(
    ctx: _Context,
    tables: Sequence[str],
    lineage_pairs: Sequence[tuple[str, str]],
    min_jaccard: float | None,
) -> bool:
    """跨层 + 有血缘方向或字段近乎相同 → 疑似技术副本（仍不判定对错）。"""

    if len(_layers(ctx, tables)) < 2:
        return False

    return bool(lineage_pairs) or (min_jaccard is not None and min_jaccard >= 0.9)


def _table_has_finding(
    ctx: _Context,
    table_key: str,
    finding_types: Sequence[str],
) -> bool:
    wanted = set(finding_types)

    return any(
        finding.get("finding_type") in wanted
        for finding in ctx.findings_by_table.get(table_key, [])
    )


def _table_finding_ids(
    ctx: _Context,
    table_key: str,
    finding_types: Sequence[str],
) -> list[str]:
    wanted = set(finding_types)

    return sorted(
        str(finding.get("finding_id") or "")
        for finding in ctx.findings_by_table.get(table_key, [])
        if finding.get("finding_type") in wanted and finding.get("finding_id")
    )


def _dup_finding_tables(finding: Mapping[str, Any]) -> list[str]:
    """duplicate_fact finding 涉及的表（来自 table 证据）。"""

    tables = {
        str(entry.get("table_key") or "")
        for entry in finding.get("evidence") or []
        if str(entry.get("source_type") or "") == REVIEW_EVIDENCE_TABLE
        and entry.get("table_key")
    }

    if tables:
        return sorted(tables)

    return sorted({str(key) for key in finding.get("related_keys") or [] if _looks_like_table(key)})


def _looks_like_table(value: Any) -> bool:
    text = str(value or "")
    return bool(text) and "." in text and "|" not in text


# ============================================================
# problem 构造骨架
# ============================================================


def _raw_problem(
    problem_type: str,
    scope: str,
    scope_key: str,
    *,
    classification: str = "",
    table_keys: Sequence[str] = (),
    process_keys: Sequence[str] = (),
    grain_keys: Sequence[str] = (),
    object_keys: Sequence[str] = (),
    finding_ids: Sequence[str] = (),
    evidence: Sequence[Mapping[str, Any]] = (),
    description: str = "",
    problem_statement: str = "",
    why_change: str = "",
    human_question: str = "",
    signals: Sequence[str] = (),
    impact_types: Sequence[str] = (),
    root_cause: str = "",
) -> dict[str, Any]:
    """构造一条待编号的 problem（final 阶段补齐 id / priority / status）。"""

    if problem_type not in PROBLEM_TYPE_SET:
        raise CurrentStateModelError(f"未知的 problem_type：{problem_type}")

    if scope not in PROBLEM_SCOPE_SET:
        raise CurrentStateModelError(f"未知的 problem scope：{scope}")

    return {
        "canonical_signature": f"{problem_type}|{scope}|{scope_key}",
        "problem_type": problem_type,
        "scope": scope,
        "scope_key": scope_key,
        "classification": classification,
        "table_keys": sorted({str(key) for key in table_keys if key}),
        "process_keys": sorted({str(key) for key in process_keys if key}),
        "grain_keys": sorted({str(key) for key in grain_keys if key}),
        "object_keys": sorted({str(key) for key in object_keys if key}),
        "finding_ids": sorted({str(key) for key in finding_ids if key}),
        "evidence": list(evidence),
        "description": description,
        "problem_statement": problem_statement,
        "why_change": why_change,
        "human_question": human_question,
        "signals": [signal for signal in SIGNAL_ORDER if signal in set(signals)],
        "impact_types": [impact for impact in PROBLEM_IMPACT_ORDER if impact in set(impact_types)],
        "root_cause": root_cause,
    }


class _ProblemBuilder:
    """把各 builder 产出的 raw problem 编号、补证据、补状态。"""

    def __init__(self, ctx: _Context) -> None:
        self.ctx = ctx
        self.raws: list[dict[str, Any]] = []
        self.consumed: set[str] = set()

    def add(self, raw: dict[str, Any]) -> None:
        self.raws.append(raw)
        self.consumed.update(str(key) for key in raw.get("finding_ids") or [])

    def _priority(self, raw: Mapping[str, Any]) -> str:
        priorities = [
            str(finding.get("priority") or "")
            for finding_id in raw.get("finding_ids") or []
            for finding in (self.ctx.finding_by_id.get(str(finding_id)),)
            if finding
        ]
        priorities = [value for value in priorities if value in REVIEW_PRIORITY_ORDER]

        if priorities:
            return min(priorities, key=lambda value: _rank(value, REVIEW_PRIORITY_ORDER))

        return PROBLEM_TYPE_PRIORITY[str(raw.get("problem_type") or "")]

    def finalize(self, carry_over: Mapping[str, Mapping[str, str]]) -> list[dict[str, Any]]:
        """编号 → 证据 → 状态 → 人工回填 → 稳定排序。"""

        self.raws.sort(key=lambda raw: str(raw.get("canonical_signature") or ""))

        rows = [dict(raw) for raw in self.raws]

        for position, row in enumerate(rows, start=1):
            row["problem_id"] = PROBLEM_ID_FORMAT.format(index=position)

        if carry_over:
            _apply_problem_carry_over(rows, carry_over)

        for row in rows:
            self._enrich(row)

        rows.sort(
            key=lambda row: (
                _rank(str(row.get("priority") or ""), REVIEW_PRIORITY_ORDER),
                _rank(str(row.get("problem_type") or ""), PROBLEM_TYPE_ORDER),
                _rank(str(row.get("scope") or ""), PROBLEM_SCOPE_ORDER),
                str(row.get("scope_key") or ""),
                str(row.get("problem_id") or ""),
            )
        )

        return rows

    def _enrich(self, row: dict[str, Any]) -> None:
        evidence = _sort_evidence(row.get("evidence") or [])

        if not evidence:
            raise CurrentStateModelError(
                f"problem {row.get('canonical_signature')} 缺少 evidence："
                "Evidence First 不允许只有结论没有证据"
            )

        type_counts = Counter(str(item.get("evidence_type") or "") for item in evidence)
        strength = _problem_evidence_strength(len(type_counts))

        row["evidence_total"] = len(evidence)
        row["evidence_truncated"] = len(evidence) > PROBLEM_EVIDENCE_ROW_LIMIT
        row["evidence_type_counts"] = {
            name: int(type_counts.get(name) or 0) for name in PROBLEM_EVIDENCE_ORDER
        }
        row["evidence_strength"] = strength
        row["evidence"] = evidence[:PROBLEM_EVIDENCE_SAMPLE]

        priority = self._priority(row)
        row["priority"] = priority
        row["severity"] = REVIEW_SEVERITY_BY_PRIORITY[priority]
        row["evidence_row_limit"] = PROBLEM_EVIDENCE_ROW_LIMIT

        row.setdefault("classification", "")
        row["finding_ids"] = sorted({str(key) for key in row.get("finding_ids") or [] if key})
        row["finding_count"] = len(row["finding_ids"])
        row["finding_types"] = sorted(
            {
                str(finding.get("finding_type") or "")
                for finding_id in row["finding_ids"]
                for finding in (self.ctx.finding_by_id.get(finding_id),)
                if finding
            }
        )
        row["affected_table_count"] = len(row.get("table_keys") or [])
        row["impact_types"] = [
            impact
            for impact in PROBLEM_IMPACT_ORDER
            if impact in set(row.get("impact_types") or [])
        ]
        row["root_cause"] = row.get("root_cause") or ROOT_CAUSE_BY_TYPE.get(
            str(row.get("problem_type") or ""), PROBLEM_ROOT_CAUSE_UNKNOWN
        )

        row["human_review_required"] = True
        row.setdefault("human_validated", False)
        row.setdefault("status", PROBLEM_STATUS_CANDIDATE)

        if str(row.get("status")) == PROBLEM_STATUS_CANDIDATE:
            if strength == EVIDENCE_STRENGTH_WEAK:
                row["status"] = PROBLEM_STATUS_REVIEW_REQUIRED
            elif str(row.get("classification") or "") in REVIEW_REQUIRED_CLASSIFICATIONS:
                row["status"] = PROBLEM_STATUS_REVIEW_REQUIRED

        impact_titles = [PROBLEM_IMPACT_TITLE[impact] for impact in row["impact_types"]]
        row["impact"] = "影响类型：" + "、".join(impact_titles) + "（结构推导，需人工确认）"
        row["unresolved_reason"] = PROBLEM_UNRESOLVED_REASON

        row["rationale"] = {
            "current_state": str(row.get("description") or ""),
            "problem": str(row.get("problem_statement") or ""),
            "evidence": _evidence_summary(evidence),
            "impact": str(row.get("impact") or ""),
            "why_change": str(row.get("why_change") or ""),
        }

        row["evidence_rows"] = evidence
        row.pop("problem_statement", None)


def _evidence_summary(evidence: Sequence[Mapping[str, Any]]) -> str:
    counts = Counter(str(item.get("evidence_type") or "") for item in evidence)
    parts = [
        f"{name}={counts[name]}" for name in PROBLEM_EVIDENCE_ORDER if counts.get(name)
    ]
    samples = [
        str(item.get("evidence_id") or "") for item in evidence[:PROBLEM_EVIDENCE_SAMPLE]
    ]

    return "；".join(["，".join(parts), f"样例：{'、'.join(samples)}"])


def _apply_problem_carry_over(
    rows: list[dict[str, Any]],
    carry_over: Mapping[str, Mapping[str, str]],
) -> None:
    """把问题清单里的人工状态回填成 problem status（只对命中的行生效）。"""

    known = 0

    for row in rows:
        key = str(row.get("problem_id") or "")
        previous = carry_over.get(key)

        if not previous:
            continue

        raw = str(previous.get("human_status", "") or "").strip()
        normalized = normalize_human_status(raw)

        if normalized is None:
            if raw:
                logger.warning(
                    "problem 清单的 problem_id=%s 无法识别 human_status：%s（按未回填处理）",
                    key,
                    raw,
                )

            continue

        if normalized == MODEL_STATUS_NEEDS_DISCUSSION:
            mapped: str | None = PROBLEM_STATUS_REVIEW_REQUIRED
        else:
            mapped = PROBLEM_STATUS_BY_HUMAN_STATUS.get(normalized)

        if mapped not in PROBLEM_STATUS_ORDER:
            continue

        row["status"] = mapped
        # 与 M3.6 finding 口径一致：只有 confirmed 才算人工已裁决。
        row["human_validated"] = mapped == PROBLEM_STATUS_CONFIRMED

        if normalized != MODEL_HUMAN_STATUS_PENDING:
            known += 1

    if known:
        logger.info("problem 已回填 %s 行人工状态", known)


# ============================================================
# builder：grain / overlap / duplication
# ============================================================


def _grain_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    table_keys = sorted(
        {
            str(finding.get("scope_key") or "")
            for finding_type in GRAIN_FINDING_TYPES
            for finding in ctx.findings_by_type.get(finding_type, [])
            if finding.get("scope_key")
        }
    )

    for table_key in table_keys:
        grains = _grains(ctx, table_key)

        if not grains:
            continue

        processes = _table_processes(ctx, table_key)
        key_sets = [
            frozenset(str(key) for key in grain.get("candidate_keys") or [])
            for grain in grains
        ]
        has_empty = any(not keys for keys in key_sets)
        disjoint = any(
            not (left <= right or right <= left)
            for position, left in enumerate(key_sets)
            for right in key_sets[position + 1 :]
        )

        if len(processes) > 1 or has_empty:
            assessment = GRAIN_ASSESSMENT_REVIEW_REQUIRED
        elif disjoint:
            assessment = GRAIN_ASSESSMENT_CONFIRMED_CONFLICT
        else:
            assessment = GRAIN_ASSESSMENT_POSSIBLE_CONFLICT

        finding_ids = _table_finding_ids(ctx, table_key, GRAIN_FINDING_TYPES)
        row = _table_row(ctx, table_key)
        column_names = sorted({key for keys in key_sets for key in keys})

        evidence = [
            _problem_evidence(
                PROBLEM_EVIDENCE_TABLE,
                table_key,
                table_key=table_key,
                table_name=str(row.get("table_name") or ""),
                reason=f"{len(grains)} 个 grain candidate，grain assessment={assessment}",
            ),
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_GRAIN,
                    str(grain.get("grain_candidate_id") or ""),
                    table_key=table_key,
                    table_name=str(row.get("table_name") or ""),
                    grain_key=str(grain.get("grain_candidate_id") or ""),
                    process_key=str(grain.get("process_candidate_id") or ""),
                    reason=(
                        f"pattern={grain.get('grain_pattern')}，"
                        "candidate_keys="
                        f"{_keys_slug(grain) or '（空）'}"
                    ),
                )
                for grain in grains
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_PROCESS,
                    process_key,
                    table_key=table_key,
                    process_key=process_key,
                    reason=f"表 {table_key} 的 grain candidate 归属该 process",
                )
                for process_key in processes
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_COLUMN,
                    f"{table_key}#{column_name}",
                    table_key=table_key,
                    table_name=str(row.get("table_name") or ""),
                    column_name=column_name,
                    reason="候选键字段（用于判断粒度）",
                )
                for column_name in column_names
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_FINDING,
                    finding_id,
                    table_key=table_key,
                    finding_id=finding_id,
                    reason="粒度类 finding（逐条观测）",
                )
                for finding_id in finding_ids
            ],
        ]

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_GRAIN,
                PROBLEM_SCOPE_TABLE,
                table_key,
                classification=assessment,
                table_keys=[table_key],
                process_keys=processes,
                grain_keys=[str(grain.get("grain_candidate_id") or "") for grain in grains],
                finding_ids=finding_ids,
                evidence=evidence,
                description=(
                    f"表 {table_key} 有 {len(grains)} 个 grain candidate、"
                    f"{len(key_sets)} 组候选键、{len(processes)} 个 process；"
                    f"grain assessment={assessment}"
                ),
                problem_statement=(
                    f"表 {table_key} 的行级含义不唯一：候选键"
                    + ("存在空集，" if has_empty else "")
                    + ("且互不包含（disjoint），" if disjoint else "")
                    + "机器无法在当前证据下确定唯一业务粒度。"
                ),
                why_change=(
                    "M4 必须先由人工裁决该表的唯一业务粒度，"
                    "再决定采信哪一组候选键；未裁决前不能直接进 Target DWD。"
                ),
                human_question=(
                    f"表 {table_key} 的业务粒度到底是哪一组键？"
                    "其余 grain candidate 应作废还是并存？"
                ),
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_GRAIN],
                root_cause=(
                    PROBLEM_ROOT_CAUSE_MULTIPLE_GRAINS
                    if assessment != GRAIN_ASSESSMENT_REVIEW_REQUIRED
                    else PROBLEM_ROOT_CAUSE_UNKNOWN
                ),
            )
        )


@dataclass
class _Component:
    """overlapping_fact 连通分量。"""

    tables: list[str] = field(default_factory=list)
    overlap_finding_ids: list[str] = field(default_factory=list)


def _components(ctx: _Context) -> list[_Component]:
    """overlapping_fact 表对 → union-find 连通分量（稳定排序）。"""

    parent: dict[str, str] = {}

    def find(node: str) -> str:
        while parent.setdefault(node, node) != node:
            parent[node] = parent[parent[node]]
            node = parent[node]

        return node

    def union(left: str, right: str) -> None:
        root_left, root_right = find(left), find(right)

        if root_left != root_right:
            parent[root_right] = root_left

    for finding in ctx.findings_by_type.get(FINDING_TYPE_OVERLAPPING_FACT, []):
        related = [str(key) for key in finding.get("related_keys") or [] if key]

        if len(related) != 2:
            continue

        union(_fold(related[0]), _fold(related[1]))

    buckets: dict[str, set[str]] = defaultdict(set)
    display: dict[str, str] = {}

    for node in parent:
        buckets[find(node)].add(node)

    for finding in ctx.findings_by_type.get(FINDING_TYPE_OVERLAPPING_FACT, []):
        related = [str(key) for key in finding.get("related_keys") or [] if key]

        for key in related:
            display.setdefault(_fold(key), key)

    components: list[_Component] = []

    for root in sorted(buckets):
        tables = sorted(buckets[root], key=lambda node: node.casefold())
        component = _Component(tables=[display.get(node, node) for node in tables])

        for finding in ctx.findings_by_type.get(FINDING_TYPE_OVERLAPPING_FACT, []):
            related = [str(key) for key in finding.get("related_keys") or [] if key]

            if len(related) == 2 and _fold(related[0]) in buckets[root]:
                finding_id = str(finding.get("finding_id") or "")

                if finding_id:
                    component.overlap_finding_ids.append(finding_id)

        component.overlap_finding_ids.sort()
        components.append(component)

    components.sort(key=lambda component: tuple(table.casefold() for table in component.tables))

    return components


def _overlap_problems(
    ctx: _Context,
    builder: _ProblemBuilder,
) -> None:
    """连通分量 → MODEL_OVERLAP / MODEL_DUPLICATION。"""

    dup_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for finding in ctx.findings_by_type.get(FINDING_TYPE_DUPLICATE_FACT, []):
        for table_key in _dup_finding_tables(finding):
            dup_by_table[_fold(table_key)].append(finding)

    for index, component in enumerate(_components(ctx), start=1):
        tables = component.tables
        shared_processes = _shared_processes(ctx, tables)
        shared_signature = _shared_grain_signature(ctx, tables)
        lineage_pairs = _lineage_pairs(ctx, tables)
        min_jaccard, best_pair = _jaccard_stats(ctx, tables)
        technical_copy = _is_technical_copy(ctx, tables, lineage_pairs, min_jaccard)

        if shared_processes and shared_signature:
            problem_type = PROBLEM_TYPE_DUPLICATION
            classification = (
                OVERLAP_CLASS_TECHNICAL_COPY if technical_copy else OVERLAP_CLASS_DUPLICATION
            )
        else:
            problem_type = PROBLEM_TYPE_OVERLAP
            classification = (
                OVERLAP_CLASS_TECHNICAL_COPY if technical_copy else OVERLAP_CLASS_STRUCTURAL
            )

        scope_key = "|".join(sorted(tables, key=lambda table: table.casefold()))
        finding_ids = list(component.overlap_finding_ids)
        covered_dup: set[str] = set()

        for table_key in tables:
            for finding in dup_by_table.get(_fold(table_key), []):
                group_tables = {_fold(item) for item in _dup_finding_tables(finding)}

                if group_tables <= {_fold(item) for item in tables}:
                    finding_id = str(finding.get("finding_id") or "")

                    if finding_id:
                        finding_ids.append(finding_id)
                        covered_dup.add(finding_id)

        grain_samples = [grain for table_key in tables for grain in _grains(ctx, table_key)[:1]]
        shared_columns: list[str] = []

        if best_pair:
            shared_columns = sorted(
                _column_set(ctx, best_pair[0]) & _column_set(ctx, best_pair[1])
            )[:PROBLEM_EVIDENCE_SAMPLE]

        evidence = [
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_TABLE,
                    table_key,
                    table_key=table_key,
                    table_name=str(_table_row(ctx, table_key).get("table_name") or ""),
                    reason=f"{len(_column_set(ctx, table_key))} 个字段，属于连通分量 #{index}",
                )
                for table_key in tables
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_PROCESS,
                    process_key,
                    process_key=process_key,
                    reason=(
                        "分量内表共享该 process"
                        if process_key in shared_processes
                        else "分量内表的 process"
                    ),
                )
                for process_key in sorted(_component_processes(ctx, tables))
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_GRAIN,
                    str(grain.get("grain_candidate_id") or ""),
                    table_key=str(grain.get("table_key") or ""),
                    grain_key=str(grain.get("grain_candidate_id") or ""),
                    process_key=str(grain.get("process_candidate_id") or ""),
                    reason=(
                        "共享 grain 签名 "
                        f"pattern={grain.get('grain_pattern')}，keys="
                        f"{'+'.join(sorted(str(k) for k in grain.get('candidate_keys') or []))}"
                    ),
                )
                for grain in grain_samples
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_LINEAGE,
                    f"{left} → {right}",
                    table_key=left,
                    reason="连通分量内部的表级血缘方向",
                )
                for left, right in lineage_pairs
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_COLUMN,
                    f"{best_pair[0]}#{column_name}",
                    table_key=best_pair[0],
                    column_name=column_name,
                    reason=f"与 {best_pair[1]} 共享的字段（Jaccard {min_jaccard:.2f}）",
                )
                for column_name in shared_columns
                if best_pair and min_jaccard is not None
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_FINDING,
                    finding_id,
                    finding_id=finding_id,
                    reason="字段重合 / 重复类 finding（逐条观测）",
                )
                for finding_id in sorted(set(finding_ids))
            ],
        ]

        jaccard_text = f"{min_jaccard:.2f}" if min_jaccard is not None else "无法比较"
        shared_process_text = "、".join(shared_processes) or "（无共享 process）"
        shared_signature_text = (
            f"pattern={shared_signature[0]}，keys={shared_signature[1]}"
            if shared_signature
            else "（无共享 grain 签名）"
        )

        builder.add(
            _raw_problem(
                problem_type,
                PROBLEM_SCOPE_TABLE_SET,
                scope_key,
                classification=classification,
                table_keys=tables,
                process_keys=shared_processes or _component_processes(ctx, tables),
                grain_keys=[
                    str(grain.get("grain_candidate_id") or "") for grain in grain_samples
                ],
                finding_ids=finding_ids,
                evidence=evidence,
                description=(
                    f"{len(tables)} 张表通过 {len(component.overlap_finding_ids)} 对字段重合 "
                    f"finding 连通（最大 Jaccard {jaccard_text}），共享 process："
                    f"{shared_process_text}，共享 grain 签名：{shared_signature_text}，"
                    f"层：{'、'.join(sorted(_layers(ctx, tables))) or '（未分层）'}，"
                    f"内部血缘边 {len(lineage_pairs)} 条"
                ),
                problem_statement=(
                    f"{len(tables)} 张表构成一个结构重合的模型簇："
                    + (
                        "同一粒度被多张表表达，"
                        if classification == OVERLAP_CLASS_DUPLICATION
                        else ""
                    )
                    + "机器只能证明字段与结构重合，不能判断哪张是权威版本。"
                ),
                why_change=(
                    "M4 需要先裁决这个模型簇中哪些是同一业务口径的多份表达、"
                    "权威表是哪一张，再决定收敛范围；收敛前必须人工确认。"
                ),
                human_question=(
                    f"这 {len(tables)} 张表是否是同一逻辑模型的多份表达？"
                    "权威表是哪一张？先收敛哪一张？"
                ),
                impact_types=IMPACT_TYPES_BY_TYPE[problem_type],
                root_cause=(
                    PROBLEM_ROOT_CAUSE_SOURCE_REPLICATION
                    if classification == OVERLAP_CLASS_TECHNICAL_COPY
                    else (
                        PROBLEM_ROOT_CAUSE_DUPLICATED_PIPELINES
                        if classification == OVERLAP_CLASS_DUPLICATION
                        else PROBLEM_ROOT_CAUSE_LAYER_OVERLAP
                    )
                ),
            )
        )


def _duplicate_problems(ctx: _Context, builder: _ProblemBuilder) -> list[dict[str, Any]]:
    """连通分量之外的 duplicate_fact 组 → MODEL_DUPLICATION（结构分歧）。"""

    emitted: list[dict[str, Any]] = []

    for finding in ctx.findings_by_type.get(FINDING_TYPE_DUPLICATE_FACT, []):
        finding_id = str(finding.get("finding_id") or "")

        if finding_id in builder.consumed:
            continue

        tables = _dup_finding_tables(finding)

        if len(tables) < 2:
            continue

        shared_signature = _shared_grain_signature(ctx, tables)
        lineage_pairs = _lineage_pairs(ctx, tables)
        min_jaccard, best_pair = _jaccard_stats(ctx, tables)
        technical_copy = _is_technical_copy(ctx, tables, lineage_pairs, min_jaccard)

        classification = (
            OVERLAP_CLASS_TECHNICAL_COPY if technical_copy else OVERLAP_CLASS_DIVERGENT_STRUCTURE
        )
        process_keys = [
            str(finding.get("process_candidate_id") or ""),
            *[
                process
                for table_key in tables
                for process in _table_processes(ctx, table_key)
            ],
        ]
        grain_samples = [grain for table_key in tables for grain in _grains(ctx, table_key)[:1]]
        shared_columns: list[str] = []

        if best_pair:
            shared_columns = sorted(
                _column_set(ctx, best_pair[0]) & _column_set(ctx, best_pair[1])
            )[:PROBLEM_EVIDENCE_SAMPLE]

        evidence = [
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_TABLE,
                    table_key,
                    table_key=table_key,
                    table_name=str(_table_row(ctx, table_key).get("table_name") or ""),
                    reason="同一逻辑事实的候选落在该表",
                )
                for table_key in tables
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_GRAIN,
                    str(grain.get("grain_candidate_id") or ""),
                    table_key=str(grain.get("table_key") or ""),
                    grain_key=str(grain.get("grain_candidate_id") or ""),
                    process_key=str(grain.get("process_candidate_id") or ""),
                    reason=f"pattern={grain.get('grain_pattern')}，keys={_keys_slug(grain)}",
                )
                for grain in grain_samples
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_PROCESS,
                    process_key,
                    process_key=process_key,
                    reason="重复组的 process 归属",
                )
                for process_key in sorted({key for key in process_keys if key})
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_LINEAGE,
                    f"{left} → {right}",
                    table_key=left,
                    reason="表级血缘方向（判断是否技术副本）",
                )
                for left, right in lineage_pairs
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_COLUMN,
                    f"{best_pair[0]}#{column_name}",
                    table_key=best_pair[0],
                    column_name=column_name,
                    reason=f"与 {best_pair[1]} 共享的字段（Jaccard {min_jaccard:.2f}）",
                )
                for column_name in shared_columns
                if best_pair and min_jaccard is not None
            ],
            _problem_evidence(
                PROBLEM_EVIDENCE_FINDING,
                finding_id,
                table_key=tables[0],
                finding_id=finding_id,
                reason="duplicate_fact finding（逐条观测）",
            ),
        ]

        jaccard_text = f"{min_jaccard:.2f}" if min_jaccard is not None else "无法比较"

        raw = _raw_problem(
            PROBLEM_TYPE_DUPLICATION,
            PROBLEM_SCOPE_TABLE_SET,
            str(finding.get("scope_key") or "|".join(tables)),
            classification=classification,
            table_keys=tables,
            process_keys=[key for key in process_keys if key],
            grain_keys=[
                str(grain.get("grain_candidate_id") or "") for grain in grain_samples
            ],
            finding_ids=[finding_id],
            evidence=evidence,
            description=(
                f"{len(tables)} 张表共享同一 process / grain 形态 / 候选键 / Object"
                f"（scope_key={finding.get('scope_key')}），共享 grain 签名："
                + (
                    f"pattern={shared_signature[0]}，keys={shared_signature[1]}"
                    if shared_signature
                    else "（无共享签名）"
                )
                + f"，最大 Jaccard {jaccard_text}，血缘边 {len(lineage_pairs)} 条，"
                f"但没有形成字段重合连通分量"
            ),
            problem_statement=(
                "同一逻辑事实的候选被复制到多张表，且结构已经分歧；"
                "机器不判断哪张是权威版本。"
            ),
            why_change=(
                "M4 需要先确认权威表与副本关系，避免同一事实被重复建模与重复计数。"
            ),
            human_question=(
                f"{tables[0]} 等 {len(tables)} 张表是否是同一逻辑模型的副本？"
                "权威表是哪一张？"
            ),
            impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_DUPLICATION],
            root_cause=(
                PROBLEM_ROOT_CAUSE_SOURCE_REPLICATION
                if classification == OVERLAP_CLASS_TECHNICAL_COPY
                else PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION
            ),
        )
        builder.add(raw)
        emitted.append(raw)

    return emitted


# ============================================================
# builder：职责 / 角色 / 聚合 / 识别 / 对齐
# ============================================================


def _table_signals(row: Mapping[str, Any]) -> set[str]:
    """表的职责信号（固定口径，只来自 M3.6 形态与角色）。"""

    roles = {str(role) for role in row.get("current_roles") or []}
    patterns = {str(pattern) for pattern in row.get("grain_patterns") or []}
    signals: set[str] = set()

    # FACT 是基线角色，不单独构成职责信号；否则所有聚合事实都会被算成职责混杂。
    if "DIMENSION" in roles:
        signals.add(SIGNAL_DIMENSION)
    if "WIDE_ANALYTICAL" in roles:
        signals.add(SIGNAL_WIDE)
    if "RESULT_TABLE" in roles:
        signals.add(SIGNAL_RESULT)
    if str(row.get("model_shape") or "") == "AGGREGATE" or "aggregation" in patterns:
        signals.add(SIGNAL_AGGREGATE)
    if str(row.get("model_shape") or "") == "MIXED":
        signals.add(SIGNAL_MIXED_GRAIN)
    if "periodic" in patterns and "FACT" in roles:
        signals.add(SIGNAL_PERIODIC_FACT)
    if "snapshot" in patterns and "FACT" in roles:
        signals.add(SIGNAL_SNAPSHOT_FACT)

    return signals


def _is_mixed_responsibility(signals: set[str]) -> bool:
    """≥2 个职责信号，或命中宽表 / 结果落地职责（单信号即构成混杂）。"""

    return len(signals) >= 2 or bool(signals & RESPONSIBILITY_SELF_SUFFICIENT)


def _mixed_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    for row in sorted(ctx.table_rows, key=lambda item: str(item.get("table_key") or "")):
        table_key = str(row.get("table_key") or "")

        if not table_key:
            continue

        signals = _table_signals(row)

        if not _is_mixed_responsibility(signals):
            continue

        finding_ids = _table_finding_ids(ctx, table_key, CORE_SHAPE_FINDING_TYPES)

        if not finding_ids:
            continue

        processes = _table_processes(ctx, table_key)
        grains = _grains(ctx, table_key)

        evidence = [
            _problem_evidence(
                PROBLEM_EVIDENCE_TABLE,
                table_key,
                table_key=table_key,
                table_name=str(row.get("table_name") or ""),
                reason=(
                    f"model_shape={row.get('model_shape')}，"
                    f"roles={'+'.join(str(r) for r in row.get('current_roles') or [])}，"
                    f"signals={'+'.join(signal for signal in SIGNAL_ORDER if signal in signals)}"
                ),
            ),
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_FINDING,
                    finding_id,
                    table_key=table_key,
                    finding_id=finding_id,
                    reason="形态类 finding（逐条观测）",
                )
                for finding_id in finding_ids
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_PROCESS,
                    process_key,
                    table_key=table_key,
                    process_key=process_key,
                    reason="该表的 process 归属",
                )
                for process_key in processes
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_GRAIN,
                    str(grain.get("grain_candidate_id") or ""),
                    table_key=table_key,
                    grain_key=str(grain.get("grain_candidate_id") or ""),
                    process_key=str(grain.get("process_candidate_id") or ""),
                    reason=f"pattern={grain.get('grain_pattern')}",
                )
                for grain in grains[:PROBLEM_EVIDENCE_SAMPLE]
            ],
        ]

        signal_text = "、".join(signal for signal in SIGNAL_ORDER if signal in signals)

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_MIXED_RESPONSIBILITY,
                PROBLEM_SCOPE_TABLE,
                table_key,
                table_keys=[table_key],
                process_keys=processes,
                grain_keys=[str(g.get("grain_candidate_id") or "") for g in grains],
                finding_ids=finding_ids,
                evidence=evidence,
                signals=sorted(signals),
                description=(
                    f"表 {table_key} 同时呈现 {len(signals)} 个职责信号：{signal_text}"
                    f"（model_shape={row.get('model_shape')}）"
                ),
                problem_statement=(
                    f"表 {table_key} 同时承担多种职责（{signal_text}），"
                    "无法用单一模型职责描述它。"
                ),
                why_change=(
                    "M4 需要先裁决该表应承担的单一职责边界，"
                    "再决定是否拆分；职责未拆清前不能直接进 Target DWD。"
                ),
                human_question=(
                    f"表 {table_key} 的信号为 {signal_text}；"
                    "它到底承担哪一种职责？是否需要拆分？"
                ),
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_MIXED_RESPONSIBILITY],
                root_cause=(
                    PROBLEM_ROOT_CAUSE_AGGREGATION_ATOMIC_MIX
                    if signals & AGGREGATE_SIGNALS and signals - {SIGNAL_AGGREGATE}
                    else PROBLEM_ROOT_CAUSE_RESPONSIBILITY_MIX
                ),
            )
        )


def _role_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    for finding in ctx.findings_by_type.get(FINDING_TYPE_ROLE_AMBIGUOUS, []):
        finding_id = str(finding.get("finding_id") or "")
        dimension_key = str(finding.get("scope_key") or "")

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_ROLE_AMBIGUITY,
                PROBLEM_SCOPE_DIMENSION,
                dimension_key or str(finding.get("table_key") or ""),
                table_keys=[str(finding.get("table_key") or "")]
                if finding.get("table_key")
                else [],
                finding_ids=[finding_id] if finding_id else [],
                evidence=_finding_evidence(finding),
                description=str(finding.get("description") or ""),
                problem_statement=(
                    f"Object {dimension_key} 的模型角色未解析："
                    "既被当作维度又被其它角色引用，M4 无法确定它的建模位置。"
                ),
                why_change=(
                    "M4 必须先由人工确认该 Object 的唯一模型角色，"
                    "再决定它在目标模型中的位置。"
                ),
                human_question=str(finding.get("human_question") or "")
                or f"Object {dimension_key} 的模型角色到底是什么？",
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_ROLE_AMBIGUITY],
                root_cause=PROBLEM_ROOT_CAUSE_UNRESOLVED_ROLE,
            )
        )


def _aggregate_assessment(ctx: _Context, table_key: str) -> str:
    """聚合表评估：conflict / duplication → model_problem；有事实上游 → valid。"""

    if _table_has_finding(
        ctx,
        table_key,
        (FINDING_TYPE_GRAIN_CONFLICT, FINDING_TYPE_MIXED_GRAIN),
    ):
        return AGGREGATE_ASSESSMENT_MODEL_PROBLEM

    for finding in ctx.findings_by_type.get(FINDING_TYPE_DUPLICATE_FACT, []):
        if _fold(table_key) in {_fold(item) for item in _dup_finding_tables(finding)}:
            return AGGREGATE_ASSESSMENT_MODEL_PROBLEM

    upstream = ctx.indexes.lineage_in.get(_fold(table_key), ())

    anchors = [
        ancestor
        for ancestor in upstream
        if ancestor in ctx.fact_anchor_tables
    ]

    if len(anchors) >= AGGREGATE_MIN_UPSTREAM_FOR_VALID:
        return AGGREGATE_ASSESSMENT_VALID

    return AGGREGATE_ASSESSMENT_REVIEW_REQUIRED


def _aggregation_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
    orphans: list[tuple[str, str]] = []

    for row in sorted(ctx.table_rows, key=lambda item: str(item.get("table_key") or "")):
        table_key = str(row.get("table_key") or "")

        if not _table_finding_ids(ctx, table_key, (FINDING_TYPE_AGGREGATE_FACT,)):
            continue

        assessment = _aggregate_assessment(ctx, table_key)

        if assessment == AGGREGATE_ASSESSMENT_VALID:
            continue

        processes = _table_processes(ctx, table_key)

        if processes:
            buckets[(processes[0], assessment)].append(table_key)
        else:
            orphans.append((table_key, assessment))

    for process_key, assessment in sorted(buckets):
        tables = sorted(set(buckets[(process_key, assessment)]))
        _emit_aggregation_problem(
            ctx,
            builder,
            scope=PROBLEM_SCOPE_PROCESS,
            scope_key=process_key,
            tables=tables,
            assessment=assessment,
            process_keys=[process_key],
        )

    for table_key, assessment in sorted(orphans):
        _emit_aggregation_problem(
            ctx,
            builder,
            scope=PROBLEM_SCOPE_TABLE,
            scope_key=table_key,
            tables=[table_key],
            assessment=assessment,
            process_keys=list(_table_processes(ctx, table_key)),
        )


def _emit_aggregation_problem(
    ctx: _Context,
    builder: _ProblemBuilder,
    *,
    scope: str,
    scope_key: str,
    tables: Sequence[str],
    assessment: str,
    process_keys: Sequence[str],
) -> None:
    finding_ids = sorted(
        {
            finding_id
            for table_key in tables
            for finding_id in _table_finding_ids(ctx, table_key, (FINDING_TYPE_AGGREGATE_FACT,))
        }
    )
    grains = [grain for table_key in tables for grain in _grains(ctx, table_key)[:1]]

    evidence = [
        *[
            _problem_evidence(
                PROBLEM_EVIDENCE_TABLE,
                table_key,
                table_key=table_key,
                table_name=str(_table_row(ctx, table_key).get("table_name") or ""),
                reason=(
                    f"聚合表评估={assessment}，"
                    f"column_count={_table_row(ctx, table_key).get('column_count')}"
                ),
            )
            for table_key in tables
        ],
        *[
            _problem_evidence(
                PROBLEM_EVIDENCE_PROCESS,
                process_key,
                process_key=process_key,
                reason="聚合表的 process 归属",
            )
            for process_key in sorted({key for key in process_keys if key})
        ],
        *[
            _problem_evidence(
                PROBLEM_EVIDENCE_GRAIN,
                str(grain.get("grain_candidate_id") or ""),
                table_key=str(grain.get("table_key") or ""),
                grain_key=str(grain.get("grain_candidate_id") or ""),
                process_key=str(grain.get("process_candidate_id") or ""),
                reason=f"聚合表的上游粒度 pattern={grain.get('grain_pattern')}",
            )
            for grain in grains
        ],
        *[
            _problem_evidence(
                PROBLEM_EVIDENCE_FINDING,
                finding_id,
                finding_id=finding_id,
                reason="aggregate_fact finding（逐条观测）",
            )
            for finding_id in finding_ids
        ],
    ]

    builder.add(
        _raw_problem(
            PROBLEM_TYPE_AGGREGATION,
            scope,
            scope_key,
            classification=assessment,
            table_keys=tables,
            process_keys=process_keys,
            grain_keys=[str(g.get("grain_candidate_id") or "") for g in grains],
            finding_ids=finding_ids,
            evidence=evidence,
            description=(
                f"{len(tables)} 张聚合表（assessment={assessment}）："
                f"{tables[0]} 等"
            ),
            problem_statement=(
                "聚合表的上游原子事实来源未确认（无 fact-anchor 血缘，或自身带粒度 / "
                "重复问题），聚合口径无法回溯。"
            ),
            why_change=(
                "M4 必须先确认聚合表的上游事实来源与聚合口径，"
                "再决定是否保留该聚合层；口径未回溯前不采信。"
            ),
            human_question=(
                f"{'、'.join(tables[:3])} 等 {len(tables)} 张聚合表的上游事实是什么？"
                "聚合口径是否可以回溯到原子事实？"
            ),
            impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_AGGREGATION],
            root_cause=(
                PROBLEM_ROOT_CAUSE_AGGREGATION_ATOMIC_MIX
                if assessment == AGGREGATE_ASSESSMENT_MODEL_PROBLEM
                else PROBLEM_ROOT_CAUSE_UNKNOWN
            ),
        )
    )


def _fact_identification_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    gate_findings: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for finding_type in (FINDING_TYPE_FACT_GATE_NO_MEASURE, FINDING_TYPE_FACT_GATE_PATTERN):
        for finding in ctx.findings_by_type.get(finding_type, []):
            gate_findings[str(finding.get("scope_key") or "")].append(finding)

    for scope_key in sorted(gate_findings):
        findings = gate_findings[scope_key]
        finding_ids = sorted(_finding_ids(findings))
        evidence: list[dict[str, Any]] = [
            row for finding in findings for row in _finding_evidence(finding)
        ]

        rejected = [
            grain
            for grain in ctx.inputs.grain_candidates
            if str(grain.get("grain_pattern") or "") == scope_key
            and not _fact_gate_passed(grain)
        ]

        for grain in rejected:
            evidence.append(
                _problem_evidence(
                    PROBLEM_EVIDENCE_GRAIN,
                    str(grain.get("grain_candidate_id") or ""),
                    table_key=str(grain.get("table_key") or ""),
                    grain_key=str(grain.get("grain_candidate_id") or ""),
                    process_key=str(grain.get("process_candidate_id") or ""),
                    reason="被 Fact Gate 排除、未产出 fact candidate 的 grain 候选",
                )
            )
            evidence.append(
                _problem_evidence(
                    PROBLEM_EVIDENCE_TABLE,
                    str(grain.get("table_key") or ""),
                    table_key=str(grain.get("table_key") or ""),
                    table_name=str(grain.get("table_name") or ""),
                    reason="被 Fact Gate 排除的表（当前不进入事实模型）",
                )
            )
            evidence.append(
                _problem_evidence(
                    PROBLEM_EVIDENCE_PROCESS,
                    str(grain.get("process_candidate_id") or ""),
                    process_key=str(grain.get("process_candidate_id") or ""),
                    reason="被排除 grain 候选的 process 归属",
                )
            )

        table_keys = sorted(
            {str(grain.get("table_key") or "") for grain in rejected if grain.get("table_key")}
        )
        process_keys = sorted(
            {
                str(grain.get("process_candidate_id") or "")
                for grain in rejected
                if grain.get("process_candidate_id")
            }
        )

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_FACT_IDENTIFICATION,
                PROBLEM_SCOPE_STAGE,
                scope_key,
                table_keys=table_keys,
                process_keys=process_keys,
                grain_keys=[
                    str(grain.get("grain_candidate_id") or "") for grain in rejected
                ],
                finding_ids=finding_ids,
                evidence=evidence,
                description=(
                    f"Fact Gate 因 {scope_key} 排除 {len(rejected)} 个 grain candidate"
                    "（未产出 fact candidate）"
                ),
                problem_statement=(
                    "事实识别闸门把「没有显式 measure / 不匹配 pattern」的表排除在事实模型之外，"
                    "这些表是否仍是事实表当前无法证明，事实覆盖存在缺口。"
                ),
                why_change=(
                    "M4 需要先人工确认这些被排除的表是否仍应作为事实，"
                    "再决定事实覆盖范围；不能默认闸门结论就是业务结论。"
                ),
                human_question=(
                    f"grain_pattern={scope_key} 且被 Fact Gate 排除的 "
                    f"{len(rejected)} 张表是否仍应作为事实表？"
                ),
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_FACT_IDENTIFICATION],
                root_cause=(
                    PROBLEM_ROOT_CAUSE_GATE_MEASURE_DEPENDENCY
                    if FINDING_TYPE_FACT_GATE_NO_MEASURE
                    in {str(finding.get("finding_type")) for finding in findings}
                    else PROBLEM_ROOT_CAUSE_UNKNOWN
                ),
            )
        )

    _fact_without_measure_problems(ctx, builder)


def _fact_gate_passed(grain: Mapping[str, Any]) -> bool:
    passed, _reason = fact_gate(grain)

    return bool(passed)


def _fact_without_measure_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for finding in ctx.findings_by_type.get(FINDING_TYPE_FACT_WITHOUT_MEASURE, []):
        table_key = str(finding.get("table_key") or "")

        if table_key:
            by_table[table_key].append(finding)

    for table_key in sorted(by_table):
        findings = by_table[table_key]
        finding_ids = sorted(_finding_ids(findings))
        row = _table_row(ctx, table_key)
        evidence = [
            _problem_evidence(
                PROBLEM_EVIDENCE_TABLE,
                table_key,
                table_key=table_key,
                table_name=str(row.get("table_name") or ""),
                reason=f"measure_count={row.get('measure_count')}",
            ),
            *[
                row_entry
                for finding in findings
                for row_entry in _finding_evidence(finding)
            ],
        ]

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_FACT_IDENTIFICATION,
                PROBLEM_SCOPE_TABLE,
                table_key,
                table_keys=[table_key],
                process_keys=list(_table_processes(ctx, table_key)),
                finding_ids=finding_ids,
                evidence=evidence,
                description=(
                    f"表 {table_key} 被识别为 fact candidate，但没有 measure 字段"
                    f"（{len(findings)} 条 finding）"
                ),
                problem_statement=(
                    "事实识别依赖 measure 字段，而这些表没有显式度量；"
                    "它们可能是无显式度量的真实事实，也可能是识别错误。"
                ),
                why_change=(
                    "M4 必须先人工判断这些表是否是事实，"
                    "否则事实模型会漏建或错建。"
                ),
                human_question=(
                    f"表 {table_key} 没有 measure 字段，它仍然是事实表吗？"
                    "度量在哪里计算？"
                ),
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_FACT_IDENTIFICATION],
                root_cause=PROBLEM_ROOT_CAUSE_GATE_MEASURE_DEPENDENCY,
            )
        )


def _dimension_identification_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    _stage_problems(
        ctx,
        builder,
        finding_types=(FINDING_TYPE_DIMENSION_OBJECT_DERIVED,),
        problem_type=PROBLEM_TYPE_DIMENSION_IDENTIFICATION,
        statement=(
            "维度候选的定义来自 Object 派生证据，而非显式维度表声明；"
            "维度边界与权威来源未确认。"
        ),
        why_change=(
            "M4 需要先确认这些 Object 是否构成正式维度及其权威来源，"
            "再决定维度模型。"
        ),
        root_cause=PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION,
    )


def _semantic_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    _stage_problems(
        ctx,
        builder,
        finding_types=(
            FINDING_TYPE_EVIDENCE_STRENGTH,
            FINDING_TYPE_RELATIONSHIP_TECHNICAL,
            FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE,
        ),
        problem_type=PROBLEM_TYPE_SEMANTIC_AMBIGUITY,
        statement=(
            "关系 / 强度结论只由技术引用或共现证据支撑，"
            "缺少业务语义证据，语义结论存在误读风险。"
        ),
        why_change=(
            "M4 需要先由人工补齐业务语义证据，"
            "再决定这些关系是否进入目标模型的语义层。"
        ),
        root_cause=PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION,
    )


def _stage_problems(
    ctx: _Context,
    builder: _ProblemBuilder,
    *,
    finding_types: Sequence[str],
    problem_type: str,
    statement: str,
    why_change: str,
    root_cause: str,
) -> None:
    for finding_type in finding_types:
        for finding in ctx.findings_by_type.get(finding_type, []):
            finding_id = str(finding.get("finding_id") or "")
            scope_key = str(finding.get("scope_key") or "") or finding_id

            builder.add(
                _raw_problem(
                    problem_type,
                    PROBLEM_SCOPE_STAGE,
                    scope_key,
                    table_keys=[str(finding.get("table_key") or "")]
                    if finding.get("table_key")
                    else [],
                    finding_ids=[finding_id] if finding_id else [],
                    evidence=_finding_evidence(finding),
                    description=str(finding.get("description") or ""),
                    problem_statement=statement,
                    why_change=why_change,
                    human_question=str(finding.get("human_question") or ""),
                    impact_types=IMPACT_TYPES_BY_TYPE[problem_type],
                    root_cause=root_cause,
                )
            )


def _process_alignment_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    table_findings = ctx.findings_by_type.get(FINDING_TYPE_MULTI_PROCESS_TABLE, [])
    process_findings = ctx.findings_by_type.get(FINDING_TYPE_PROCESS_MULTIPLE_GRAINS, [])

    for finding in table_findings:
        finding_id = str(finding.get("finding_id") or "")
        table_key = str(finding.get("scope_key") or "")

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_PROCESS_ALIGNMENT,
                PROBLEM_SCOPE_TABLE,
                table_key,
                table_keys=[table_key],
                process_keys=list(_table_processes(ctx, table_key)),
                finding_ids=[finding_id] if finding_id else [],
                evidence=_finding_evidence(finding),
                description=str(finding.get("description") or ""),
                problem_statement=(
                    f"表 {table_key} 被多个 process 共同使用，"
                    "表级模型归属与过程职责没有唯一对应关系。"
                ),
                why_change=(
                    "M4 需要先确认这张表归属哪个过程、是否应该共享，"
                    "再决定建模位置。"
                ),
                human_question=str(finding.get("human_question") or "")
                or f"表 {table_key} 应归属哪个 process？",
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_PROCESS_ALIGNMENT],
                root_cause=PROBLEM_ROOT_CAUSE_UNKNOWN,
            )
        )

    for finding in process_findings:
        finding_id = str(finding.get("finding_id") or "")
        process_key = str(finding.get("scope_key") or "")
        tables = sorted(
            {
                str(grain.get("table_key") or "")
                for grain in ctx.inputs.grain_candidates
                if str(grain.get("process_candidate_id") or "") == process_key
                and grain.get("table_key")
            }
        )
        evidence = [
            *_finding_evidence(finding),
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_TABLE,
                    table_key,
                    table_key=table_key,
                    table_name=str(_table_row(ctx, table_key).get("table_name") or ""),
                    reason="该 process 下带 grain 候选的表",
                )
                for table_key in tables
            ],
            _problem_evidence(
                PROBLEM_EVIDENCE_PROCESS,
                process_key,
                process_key=process_key,
                reason="多粒度 problem 的 process 作用域",
            ),
        ]

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_PROCESS_ALIGNMENT,
                PROBLEM_SCOPE_PROCESS,
                process_key,
                table_keys=tables,
                process_keys=[process_key],
                finding_ids=[finding_id] if finding_id else [],
                evidence=evidence,
                description=str(finding.get("description") or ""),
                problem_statement=(
                    f"process {process_key} 下的表使用多种 grain 形态，"
                    "过程职责与模型粒度没有对齐。"
                ),
                why_change=(
                    "M4 需要先确认该过程内各表的粒度关系与共享口径，"
                    "再决定是否统一进入同一目标模型。"
                ),
                human_question=str(finding.get("human_question") or "")
                or f"process {process_key} 下的多粒度表应该如何对齐？",
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_PROCESS_ALIGNMENT],
                root_cause=PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION,
            )
        )


def _selection_ambiguity_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    counts: dict[str, list[str]] = defaultdict(list)

    for raw in builder.raws:
        if raw.get("problem_type") != PROBLEM_TYPE_DUPLICATION:
            continue

        for process_key in raw.get("process_keys") or []:
            counts[str(process_key)].append(str(raw.get("scope_key") or ""))

    for process_key in sorted(counts):
        scope_keys = sorted(set(counts[process_key]))

        if len(scope_keys) < SELECTION_AMBIGUITY_MIN_DUPLICATION:
            continue

        tables = sorted(
            {
                table_key
                for raw in builder.raws
                if raw.get("problem_type") == PROBLEM_TYPE_DUPLICATION
                and process_key in {str(key) for key in raw.get("process_keys") or []}
                for table_key in raw.get("table_keys") or []
            }
        )
        finding_ids = sorted(
            {
                finding_id
                for raw in builder.raws
                if raw.get("problem_type") == PROBLEM_TYPE_DUPLICATION
                and process_key in {str(key) for key in raw.get("process_keys") or []}
                for finding_id in raw.get("finding_ids") or []
            }
        )

        evidence = [
            _problem_evidence(
                PROBLEM_EVIDENCE_PROCESS,
                process_key,
                process_key=process_key,
                reason=f"{len(scope_keys)} 个重复组落在该 process",
            ),
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_TABLE,
                    table_key,
                    table_key=table_key,
                    table_name=str(_table_row(ctx, table_key).get("table_name") or ""),
                    reason="重复组涉及的表",
                )
                for table_key in tables
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_FINDING,
                    finding_id,
                    finding_id=finding_id,
                    reason="该 process 的重复组 finding",
                )
                for finding_id in finding_ids
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_GRAIN,
                    str(grain.get("grain_candidate_id") or ""),
                    table_key=str(grain.get("table_key") or ""),
                    grain_key=str(grain.get("grain_candidate_id") or ""),
                    process_key=process_key,
                    reason=f"pattern={grain.get('grain_pattern')}",
                )
                for grain in [
                    item
                    for item in ctx.inputs.grain_candidates
                    if str(item.get("process_candidate_id") or "") == process_key
                ][:PROBLEM_EVIDENCE_SAMPLE]
            ],
        ]

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_SELECTION_AMBIGUITY,
                PROBLEM_SCOPE_PROCESS,
                process_key,
                table_keys=tables,
                process_keys=[process_key],
                finding_ids=finding_ids,
                evidence=evidence,
                description=(
                    f"process {process_key} 下有 {len(scope_keys)} 个重复模型组、"
                    f"{len(tables)} 张表，消费者难以选择正确模型"
                ),
                problem_statement=(
                    "同一 process 下重复模型过多，模型选择没有唯一入口，"
                    "消费者只能靠猜。"
                ),
                why_change=(
                    "M4 需要先收敛该 process 的权威模型集合，"
                    "再决定目标模型的入口与命名。"
                ),
                human_question=(
                    f"process {process_key} 下的 {len(scope_keys)} 个重复组"
                    "应该收敛成几个模型？权威入口是哪个？"
                ),
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_SELECTION_AMBIGUITY],
                root_cause=PROBLEM_ROOT_CAUSE_DUPLICATED_PIPELINES,
            )
        )


def _coverage_gap_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    ordered_processes = sorted(
        ctx.inputs.processes,
        key=lambda item: _process_key(item),
    )

    for process in ordered_processes:
        process_key = _process_key(process)

        if not process_key or process_key in ctx.processes_with_fact:
            continue

        grains = [
            grain
            for grain in ctx.inputs.grain_candidates
            if str(grain.get("process_candidate_id") or "") == process_key
        ]
        tables = sorted(
            {str(grain.get("table_key") or "") for grain in grains if grain.get("table_key")}
        )

        evidence = [
            _problem_evidence(
                PROBLEM_EVIDENCE_PROCESS,
                process_key,
                process_key=process_key,
                reason="该 process 没有任何 fact candidate",
            ),
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_GRAIN,
                    str(grain.get("grain_candidate_id") or ""),
                    table_key=str(grain.get("table_key") or ""),
                    grain_key=str(grain.get("grain_candidate_id") or ""),
                    process_key=process_key,
                    reason=f"pattern={grain.get('grain_pattern')}（未产出 fact candidate）",
                )
                for grain in grains[:PROBLEM_EVIDENCE_SAMPLE]
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_TABLE,
                    table_key,
                    table_key=table_key,
                    table_name=str(_table_row(ctx, table_key).get("table_name") or ""),
                    reason="该 process 下带 grain 候选的表（无事实锚点）",
                )
                for table_key in tables[:PROBLEM_EVIDENCE_SAMPLE]
            ],
        ]

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_COVERAGE_GAP,
                PROBLEM_SCOPE_PROCESS,
                process_key,
                table_keys=tables,
                process_keys=[process_key],
                grain_keys=[
                    str(grain.get("grain_candidate_id") or "") for grain in grains
                ],
                evidence=evidence,
                description=(
                    f"process {process_key} 有 {len(grains)} 个 grain candidate、"
                    f"{len(tables)} 张表，但没有任何 fact candidate"
                ),
                problem_statement=(
                    "过程存在，但没有任何事实进入模型："
                    "要么该过程的事实被闸门排除，要么事实识别存在缺口。"
                ),
                why_change=(
                    "M4 需要先确认该过程是否真的没有可建模事实，"
                    "再决定目标模型是否需要覆盖它。"
                ),
                human_question=(
                    f"process {process_key} 真的没有事实需要建模吗？"
                    "它的事实应该来自哪里？"
                ),
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_COVERAGE_GAP],
                root_cause=PROBLEM_ROOT_CAUSE_UNKNOWN,
            )
        )


def _unknown_model_problems(ctx: _Context, builder: _ProblemBuilder) -> None:
    buckets: dict[str, list[str]] = defaultdict(list)

    for row in sorted(ctx.table_rows, key=lambda item: str(item.get("table_key") or "")):
        table_key = str(row.get("table_key") or "")
        roles = {str(role) for role in row.get("current_roles") or []}

        if roles != {"UNKNOWN"}:
            continue

        if (
            not row.get("fact_supporting")
            and not row.get("dimension_supporting")
            and not row.get("lineage_in_degree")
            and not row.get("lineage_out_degree")
        ):
            buckets[UNKNOWN_REASON_NO_ANCHOR].append(table_key)
        else:
            buckets[UNKNOWN_REASON_NO_EVIDENCE].append(table_key)

    for reason in sorted(buckets):
        tables = sorted(set(buckets[reason]))

        evidence = [
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_TABLE,
                    table_key,
                    table_key=table_key,
                    table_name=str(_table_row(ctx, table_key).get("table_name") or ""),
                    reason=(
                        f"current_role=UNKNOWN，reason={reason}，"
                        f"column_count={_table_row(ctx, table_key).get('column_count')}"
                    ),
                )
                for table_key in tables
            ],
            *[
                _problem_evidence(
                    PROBLEM_EVIDENCE_LINEAGE,
                    f"lineage:{table_key}",
                    table_key=table_key,
                    reason="血缘证据（存在入边 / 出边，但不足以判定角色）",
                )
                for table_key in tables
                if _table_row(ctx, table_key).get("lineage_in_degree")
                or _table_row(ctx, table_key).get("lineage_out_degree")
            ],
        ]

        builder.add(
            _raw_problem(
                PROBLEM_TYPE_UNKNOWN_MODEL,
                PROBLEM_SCOPE_TABLE_SET,
                reason,
                classification=reason,
                table_keys=tables,
                evidence=evidence,
                description=(
                    f"{len(tables)} 张表的 current_role=UNKNOWN，reason={reason}"
                    "（无事实 / 维度锚点或血缘证据不足）"
                ),
                problem_statement=(
                    "这些表既没有事实 / 维度锚点，也没有足够的血缘证据；"
                    "它们是否属于可建模的业务模型范围当前无法判定。"
                ),
                why_change=(
                    "M4 需要先人工确认这些表的范围归属（纳入 / 排除 / 补证据），"
                    "否则目标模型会静默遗漏或错误纳入它们。"
                ),
                human_question=(
                    f"这 {len(tables)} 张 UNKNOWN 表（reason={reason}）"
                    "是否属于可建模的业务模型范围？应如何处置？"
                ),
                impact_types=IMPACT_TYPES_BY_TYPE[PROBLEM_TYPE_UNKNOWN_MODEL],
                root_cause=(
                    PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION
                    if reason == UNKNOWN_REASON_NO_ANCHOR
                    else PROBLEM_ROOT_CAUSE_UNKNOWN
                ),
            )
        )


# ============================================================
# 聚合入口
# ============================================================


def _build_context(
    inputs: ReviewInputs,
    findings: Sequence[Mapping[str, Any]],
    table_rows: Sequence[Mapping[str, Any]],
) -> _Context:
    ctx = _Context(inputs=inputs, indexes=build_review_indexes(inputs))
    ctx.findings = [dict(finding) for finding in findings]
    ctx.table_rows = [dict(row) for row in table_rows]

    ctx.finding_by_id = {
        str(finding.get("finding_id") or ""): finding
        for finding in ctx.findings
        if finding.get("finding_id")
    }

    for finding in ctx.findings:
        finding_type = str(finding.get("finding_type") or "")
        ctx.findings_by_type.setdefault(finding_type, []).append(finding)

        table_key = str(finding.get("table_key") or "")

        if table_key:
            ctx.findings_by_table.setdefault(table_key, []).append(finding)

        scope_key = str(finding.get("scope_key") or "")

        if finding_type in GRAIN_FINDING_TYPES and scope_key:
            ctx.findings_by_table.setdefault(scope_key, []).append(finding)

    for row in ctx.table_rows:
        table_key = str(row.get("table_key") or "")

        if table_key:
            ctx.table_by_key.setdefault(table_key, row)

    for grain in inputs.grain_candidates:
        table_key = str(grain.get("table_key") or "")

        if table_key:
            ctx.grains_by_table.setdefault(table_key, []).append(grain)

    ctx.fact_anchor_tables = frozenset(
        _fold(fact.get("table_key")) for fact in inputs.fact_candidates if fact.get("table_key")
    )
    ctx.processes_with_fact = frozenset(
        str(fact.get("process_candidate_id") or "")
        for fact in inputs.fact_candidates
        if fact.get("process_candidate_id")
    )

    return ctx


def build_current_state_problems(
    inputs: ReviewInputs,
    findings: Sequence[Mapping[str, Any]],
    table_rows: Sequence[Mapping[str, Any]],
    *,
    carry_over: Mapping[str, Mapping[str, str]] | None = None,
) -> CurrentStateProblemResult:
    """把 M3.6 finding 聚合成 problem candidate（Evidence First，确定性输出）。"""

    ctx = _build_context(inputs, findings, table_rows)
    builder = _ProblemBuilder(ctx)

    _grain_problems(ctx, builder)
    _overlap_problems(ctx, builder)
    _duplicate_problems(ctx, builder)
    _mixed_problems(ctx, builder)
    _role_problems(ctx, builder)
    _aggregation_problems(ctx, builder)
    _fact_identification_problems(ctx, builder)
    _dimension_identification_problems(ctx, builder)
    _semantic_problems(ctx, builder)
    _process_alignment_problems(ctx, builder)
    _unknown_model_problems(ctx, builder)
    _selection_ambiguity_problems(ctx, builder)
    _coverage_gap_problems(ctx, builder)

    normalized_carry_over = carry_over or {}
    rows = builder.finalize(normalized_carry_over)
    problems_payload, evidence_payload = _payloads(ctx, rows)

    result = CurrentStateProblemResult()
    result.problems = problems_payload
    result.evidence = evidence_payload
    result.summary = render_current_state_problem_summary(
        problems=problems_payload,
        evidence=evidence_payload,
    )
    result.checklist = render_current_state_problem_review_checklist(
        rows, carry_over=normalized_carry_over
    )

    return result


def _payloads(
    ctx: _Context,
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    finding_count = len(ctx.findings)
    covered = {finding_id for row in rows for finding_id in row.get("finding_ids") or []}
    uncovered = [
        finding
        for finding in ctx.findings
        if str(finding.get("finding_id") or "") not in covered
    ]

    problems_payload: dict[str, Any] = {
        "count": len(rows),
        "note": PROBLEM_CANDIDATE_NOTE,
        "finding_count": finding_count,
        "problem_type_counts": _status_counts(
            [str(row.get("problem_type") or "") for row in rows], PROBLEM_TYPE_ORDER
        ),
        "status_counts": _status_counts(
            [str(row.get("status") or "") for row in rows], PROBLEM_STATUS_ORDER
        ),
        "priority_counts": _status_counts(
            [str(row.get("priority") or "") for row in rows], REVIEW_PRIORITY_ORDER
        ),
        "severity_by_priority": {
            priority: REVIEW_SEVERITY_BY_PRIORITY[priority] for priority in REVIEW_PRIORITY_ORDER
        },
        "classification_counts": _classification_counts(rows),
        "impact_counts": _status_counts(
            [
                str(impact)
                for row in rows
                for impact in row.get("impact_types") or []
            ],
            PROBLEM_IMPACT_ORDER,
        ),
        "root_cause_counts": _status_counts(
            [str(row.get("root_cause") or "") for row in rows], PROBLEM_ROOT_CAUSE_ORDER
        ),
        "evidence_strength_counts": _status_counts(
            [str(row.get("evidence_strength") or "") for row in rows], EVIDENCE_STRENGTH_ORDER
        ),
        "distinct_affected_table_count": len(
            {str(table_key) for row in rows for table_key in row.get("table_keys") or []}
        ),
        "finding_coverage": {
            "finding_count": finding_count,
            "covered_finding_count": len(covered),
            "uncovered_finding_count": len(uncovered),
            "uncovered_by_type": dict(
                sorted(
                    Counter(
                        str(finding.get("finding_type") or "") for finding in uncovered
                    ).items()
                )
            ),
        },
        "problems": [_problem_row(row) for row in rows],
    }

    evidence_rows = [
        {
            "problem_id": str(row.get("problem_id") or ""),
            "problem_type": str(row.get("problem_type") or ""),
            "classification": str(row.get("classification") or ""),
            "scope": str(row.get("scope") or ""),
            "scope_key": str(row.get("scope_key") or ""),
            "evidence_strength": str(row.get("evidence_strength") or ""),
            "evidence_total": int(row.get("evidence_total") or 0),
            "evidence_truncated": bool(row.get("evidence_truncated")),
            "evidence_row_limit": PROBLEM_EVIDENCE_ROW_LIMIT,
            "evidence_type_counts": dict(row.get("evidence_type_counts") or {}),
            "evidence": [
                {name: item.get(name) for name in PROBLEM_EVIDENCE_ROW_KEYS}
                for item in list(row.get("evidence_rows") or [])[:PROBLEM_EVIDENCE_ROW_LIMIT]
            ],
        }
        for row in rows
    ]

    evidence_payload: dict[str, Any] = {
        "count": len(rows),
        "note": (
            "每条 problem 至少一条 evidence；单 problem 证据行上限 "
            f"{PROBLEM_EVIDENCE_ROW_LIMIT} 行，超出按固定顺序截断并保留 "
            "evidence_total / evidence_truncated。"
        ),
        "evidence_type_counts": _status_counts(
            [
                str(item.get("evidence_type") or "")
                for row in rows
                for item in row.get("evidence_rows") or []
            ],
            PROBLEM_EVIDENCE_ORDER,
        ),
        "evidence_row_total": sum(int(row.get("evidence_total") or 0) for row in rows),
        "problems": evidence_rows,
    }

    return problems_payload, evidence_payload


def _problem_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """problems.json 里的 problem 记录（证据样例 + 计数，全量证据在 evidence 产物）。"""

    names = (
        "problem_id",
        "canonical_signature",
        "problem_type",
        "classification",
        "priority",
        "severity",
        "status",
        "human_validated",
        "human_review_required",
        "scope",
        "scope_key",
        "table_keys",
        "process_keys",
        "grain_keys",
        "object_keys",
        "finding_ids",
        "finding_count",
        "finding_types",
        "affected_table_count",
        "signals",
        "evidence_strength",
        "evidence_total",
        "evidence_truncated",
        "evidence_type_counts",
        "impact_types",
        "root_cause",
        "description",
        "impact",
        "unresolved_reason",
        "human_question",
        "rationale",
    )

    payload = {name: row.get(name) for name in names if name in row}
    payload["evidence"] = list(row.get("evidence") or [])
    payload["evidence_sample_limit"] = PROBLEM_EVIDENCE_SAMPLE

    return payload


def _classification_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    order = [
        *GRAIN_ASSESSMENT_ORDER,
        *OVERLAP_CLASS_ORDER,
        *AGGREGATE_ASSESSMENT_ORDER,
        *UNKNOWN_REASON_ORDER,
        "unclassified",
    ]
    values = [
        str(row.get("classification") or "") or "unclassified" for row in rows
    ]

    counts = _status_counts(values, order)

    for key in [key for key in counts if counts[key] == 0 and key != "unclassified"]:
        counts.pop(key)

    return counts


def read_problem_carry_over(analysis_dir: Path) -> dict[str, dict[str, str]]:
    """解析问题清单回填；文件不存在或为空返回 {}，缺列报错。"""

    path = analysis_dir / PROBLEM_CARRYOVER_FILE

    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8")

    if not text.strip():
        return {}

    try:
        return _parse_checklist_rows(
            text,
            required=PROBLEM_CHECKLIST_REQUIRED_COLUMNS,
            source=path,
            label="current-state-problem-review-checklist.md",
        )

    except BusinessGrainError as exc:
        raise CurrentStateModelError(str(exc)) from exc


def write_current_state_problems(
    result: CurrentStateProblemResult,
    output_dir: Path,
) -> tuple[Path, ...]:
    """写出 M3.6 v2 的四个产物，返回路径列表（固定顺序）。

    只覆盖 PROBLEM_OUTPUT_FILES 声明的四个文件，
    不删除、不改写 M3.6 已有五个产物与更早阶段产物。
    """

    ensure_dir(output_dir)

    paths = {name: output_dir / name for name in PROBLEM_OUTPUT_FILES}

    write_json(paths["current-state-problems.json"], result.problems)
    write_json(paths["current-state-problem-evidence.json"], result.evidence)
    write_text(paths["current-state-problem-summary.md"], result.summary)
    write_text(paths["current-state-problem-review-checklist.md"], result.checklist)

    logger.info(
        "M3.6 v2 Problem Assessment 产物已写出：%s",
        "，".join(_display_path(paths[name]) for name in PROBLEM_OUTPUT_FILES),
    )

    return tuple(paths[name] for name in PROBLEM_OUTPUT_FILES)


__all__ = [
    "build_current_state_problems",
    "read_problem_carry_over",
    "write_current_state_problems",
]

"""M3.6 Current-State Model Review。

目标：

    不再继续猜测业务模型，而是评审 M3.5 的候选结果，回答
    「当前大数据平台的数据模型实际上是什么样、哪些判断可信、
    哪些地方存在设计问题 / 粒度问题 / 职责混杂 / 重复 / 异常 /
    无法确认」，为 M4 Target DWD Design 提供证据与评审发现。

    M3.5 Candidate ──→ M3.6 Current-State Model Review
                          ├── Current-State Model Understanding（形态分类）
                          ├── Model Issues / Anti-patterns（结构化 finding）
                          ├── Human Review Checklist（人工问题）
                          └── M4 输入（只给证据与发现，不设计目标模型）

判断边界：

    Evidence ── 一切 finding 必须能回溯到 table / column / lineage /
                object / process / grain / M3.5 candidate。
    Candidate ─ 机器阶段 status 恒为 candidate，finding ≠ confirmed 问题。
    Review Finding ─ 异常只标记 Review，不判定 Wrong；多过程、宽表、
                聚合事实、多种粒度都只先给问题与证据。
    Human Confirmation ─ 只有 current-state-review-checklist.md 回填
                human_status 后重跑才改变 status。

输入（只读 M2 / M3 / M3.5 产物，不读 source/，不调 API，不改写上游）：

    analysis/understanding/modeling/fact-candidates.json
    analysis/understanding/modeling/dimension-candidates.json
    analysis/understanding/modeling/fact-dimension-relationships.json
    analysis/understanding/modeling/fact-tables.json
    analysis/understanding/modeling/dimension-tables.json
    analysis/understanding/business/grain-candidates.json       （重新走 Fact Gate，不改闸门）
    analysis/understanding/business/processes.json
    analysis/understanding/business/objects-registry.json
    analysis/inventory/tables.json
    analysis/inventory/columns.json
    analysis/evidence/lineage/table-lineage.json
    analysis/evidence/lineage/core-table-candidates.json
    analysis/evidence/layer/assessments.json
    analysis/review/current-state-review-checklist.md   （可选：本阶段清单回填）

输出（Stage 12 ～ 14，M3.6 产物统一写在 analysis/review/）：

    analysis/review/current-state-model.json
    analysis/review/current-state-model-tables.json
    analysis/review/current-state-findings.json
    analysis/review/current-state-model-summary.md
    analysis/review/current-state-review-checklist.md

原则：

1. Evidence First：每条 finding 都带 evidence 条目（source_type /
   source_id / reason），不允许只有「可能存在问题」一句话。
2. Candidate ≠ Finding ≠ Confirmed：三者分别落在 M3.5 候选、M3.6
   finding 与人工回填三个位置，互不改写。
3. Technical ≠ Business：SQL JOIN、表级血缘、表共现都是技术引用，
   不能直接断言业务维度关系。
4. 异常不等于错误：multi-process / 宽表 / 聚合事实 / 多粒度只给 Review。
5. 不为「数字好看」改规则：Fact Gate、strength 口径、候选数量一律
   按原样评审并记录为 finding，不在本阶段修改 M3.5。
6. 输出 deterministic：无时间戳 / UUID / 随机抽样，全部稳定排序。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...io_utils import (
    ensure_dir,
    relocate_legacy_artifacts,
    write_json,
    write_text,
)
from ..models import (
    CURRENT_MODEL_ROLE_AMBIGUOUS,
    CURRENT_MODEL_ROLE_DIMENSION,
    CURRENT_MODEL_ROLE_FACT,
    CURRENT_MODEL_ROLE_ORDER,
    CURRENT_MODEL_ROLE_RESULT,
    CURRENT_MODEL_ROLE_UNKNOWN,
    CURRENT_MODEL_ROLE_WIDE,
    CURRENT_MODEL_SHAPE_MIXED,
    CURRENT_MODEL_SHAPE_ORDER,
    CURRENT_MODEL_SHAPE_UNKNOWN,
    CURRENT_STATE_NOTE,
    EVIDENCE_STRENGTH_ORDER,
    FACT_EVIDENCE_GRAIN,
    FACT_EVIDENCE_ORDER,
    FACT_EVIDENCE_PROCESS,
    FINDING_CANDIDATE_NOTE,
    FINDING_ID_FORMAT,
    FINDING_SCOPE_DIMENSION,
    FINDING_SCOPE_FACT,
    FINDING_SCOPE_FACT_GROUP,
    FINDING_SCOPE_ORDER,
    FINDING_SCOPE_PROCESS,
    FINDING_SCOPE_STAGE,
    FINDING_SCOPE_TABLE,
    FINDING_SCOPE_TABLE_PAIR,
    FINDING_TYPE_AGGREGATE_FACT,
    FINDING_TYPE_DIMENSION_OBJECT_DERIVED,
    FINDING_TYPE_DUPLICATE_FACT,
    FINDING_TYPE_EVIDENCE_STRENGTH,
    FINDING_TYPE_FACT_GATE_NO_MEASURE,
    FINDING_TYPE_FACT_GATE_PATTERN,
    FINDING_TYPE_FACT_WITHOUT_MEASURE,
    FINDING_TYPE_GRAIN_CONFLICT,
    FINDING_TYPE_GROUP,
    FINDING_TYPE_MIXED_GRAIN,
    FINDING_TYPE_MULTI_PROCESS_TABLE,
    FINDING_TYPE_ORDER,
    FINDING_TYPE_OVERLAPPING_FACT,
    FINDING_TYPE_PRIORITY,
    FINDING_TYPE_PROCESS_MULTIPLE_GRAINS,
    FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE,
    FINDING_TYPE_RELATIONSHIP_TECHNICAL,
    FINDING_TYPE_RESULT_TABLE,
    FINDING_TYPE_ROLE_AMBIGUOUS,
    FINDING_TYPE_SNAPSHOT_PERIODIC,
    FINDING_TYPE_WIDE_ANALYTICAL_TABLE,
    GRAIN_PATTERN_AGGREGATION,
    GRAIN_PATTERN_ORDER,
    GRAIN_PATTERN_PERIODIC,
    GRAIN_PATTERN_SNAPSHOT,
    GRAIN_PATTERN_TO_SHAPE,
    GRAIN_ROLE_ANCHOR,
    MODEL_ATTRIBUTE_LIMIT,
    MODEL_STATUS_CANDIDATE,
    MODEL_STATUS_ORDER,
    PROBLEM_CARRYOVER_FILE,
    PROBLEM_OUTPUT_FILES,
    REVIEW_CHECKLIST_REQUIRED_COLUMNS,
    REVIEW_CHECKLIST_ROW_LIMIT,
    REVIEW_EVIDENCE_COLUMN,
    REVIEW_EVIDENCE_DIMENSION,
    REVIEW_EVIDENCE_FACT,
    REVIEW_EVIDENCE_GRAIN,
    REVIEW_EVIDENCE_LINEAGE,
    REVIEW_EVIDENCE_OBJECT,
    REVIEW_EVIDENCE_ORDER,
    REVIEW_EVIDENCE_PROCESS,
    REVIEW_EVIDENCE_RELATIONSHIP,
    REVIEW_EVIDENCE_TABLE,
    REVIEW_EXAMPLE_LIMIT,
    REVIEW_GROUP_ORDER,
    REVIEW_PRIORITY_ORDER,
    REVIEW_SEVERITY_BY_PRIORITY,
    CurrentStateModelResult,
)
from ..reports import (
    render_current_state_review_checklist,
    render_current_state_summary,
)
from ..understanding.business.grain import (
    BusinessGrainError,
    _dict_values,
    _display_path,
    _evidence_entry,
    _parse_checklist_rows,
    _rank,
    _status_counts,
    _table_column_sort_key,
)
from ..understanding.business.objects import _table_sort_key, _text
from ..understanding.modeling.business_model import (
    FACT_GATE_DIRECT_PATTERNS,
    FACT_GATE_REASON_MEASURE,
    FACT_GATE_REASON_PATTERN,
    _apply_carryover,
    _examples,
    _sort_evidence,
    _sources,
    fact_gate,
)

logger = logging.getLogger(__name__)

# ============================================================
# 输入与输出布局
# ============================================================

ARRAY_INPUT_FILES: tuple[tuple[str, str, str], ...] = (
    ("understanding/modeling/fact-candidates.json", "candidates", "fact_candidates"),
    ("understanding/modeling/dimension-candidates.json", "candidates", "dimension_candidates"),
    ("understanding/modeling/fact-dimension-relationships.json", "relationships", "relationships"),
    ("understanding/modeling/fact-tables.json", "tables", "fact_tables"),
    ("understanding/modeling/dimension-tables.json", "tables", "dimension_tables"),
    ("understanding/business/grain-candidates.json", "candidates", "grain_candidates"),
    ("understanding/business/processes.json", "processes", "processes"),
    ("understanding/business/objects-registry.json", "objects", "registry_objects"),
    ("inventory/tables.json", "tables", "inventory_tables"),
    ("inventory/columns.json", "columns", "columns"),
    ("evidence/lineage/table-lineage.json", "edges", "edges"),
    ("evidence/lineage/core-table-candidates.json", "candidates", "core_candidates"),
    ("evidence/layer/assessments.json", "assessments", "assessments"),
)
"""M3.6 依赖的数组型产物（相对 analysis/ 路径 → JSON 数组字段名 → 属性名）。"""

CARRYOVER_CHECKLIST_INPUT_FILE = "review/current-state-review-checklist.md"
"""本阶段清单（可选输入）：回填过的人工状态在重跑时被带回去。"""

INPUT_FILES: tuple[str, ...] = tuple(relative for relative, _key, _attr in ARRAY_INPUT_FILES)
"""M3.6 的必需输入（相对 analysis/ 路径）；清单属于可选输入。"""

OUTPUT_FILES: tuple[str, ...] = (
    "current-state-model.json",
    "current-state-model-tables.json",
    "current-state-findings.json",
    "current-state-model-summary.md",
    "current-state-review-checklist.md",
)
"""M3.6 产物文件名（固定顺序，写出到 analysis/review/）；
只覆盖这五个文件，不动已有 M2 / M3 / M3.5 产物。"""

LEGACY_OUTPUT_FILES: tuple[str, ...] = (
    *OUTPUT_FILES,
    "model-review-findings.json",
)
"""旧布局残留的 M3.6 产物 basename（含改名前的 model-review-findings.json），
用于清理 business/ 遗留。"""

WIDE_COLUMN_THRESHOLD = 100
"""WIDE_ANALYTICAL_TABLE 的字段数阈值（inventory/columns.json 实际字段数）。"""

WIDE_MEASURE_THRESHOLD = 20
"""WIDE_ANALYTICAL_TABLE 的度量字段数阈值（fact candidate 的 measure_columns）。"""

OVERLAP_MIN_COLUMNS = 10
"""OVERLAPPING_FACT 参与比较的最少字段数（避免小表噪声）。"""

OVERLAP_MIN_JACCARD = 0.5
"""OVERLAPPING_FACT 的字段重合度阈值（交集 / 并集）。"""

RESULT_MIN_INCOMING = 1
"""RESULT_TABLE 的最少血缘入边（无出边 + 有入边 = 疑似输出结果）。"""

TECHNICAL_RELATIONSHIP_SOURCES: frozenset[str] = frozenset(
    {
        "table_reference",
        "sql_reference",
        "lineage",
    }
)
"""只有技术引用（无 Object / Process 链接）的关系证据来源。"""


class CurrentStateModelError(RuntimeError):
    """M3.6 无法继续的输入 / 结构错误。"""


# ============================================================
# 通用小工具
# ============================================================


def _fold(table_key: Any) -> str:
    return str(table_key or "").casefold()


def _evidence(
    source_type: str,
    source_id: str,
    *,
    workspace_id: Any = None,
    table_key: str = "",
    column_name: str | None = None,
    reason: str,
) -> dict[str, Any]:
    """finding 证据条目（字段与 M2 ~ M3.5 一致）。"""

    return _evidence_entry(
        source_type,
        source_id,
        workspace_id=workspace_id,
        table_key=table_key,
        column_name=column_name,
        reason=reason,
    )


def _shape_of(patterns: Sequence[str]) -> str:
    """grain_pattern 集合 → model_shape（多种形态 → MIXED）。"""

    shapes = {
        GRAIN_PATTERN_TO_SHAPE.get(str(pattern), CURRENT_MODEL_SHAPE_UNKNOWN)
        for pattern in patterns
    }

    if not shapes:
        return CURRENT_MODEL_SHAPE_UNKNOWN

    if len(shapes) > 1:
        return CURRENT_MODEL_SHAPE_MIXED

    return next(iter(shapes))


def _key_slug(keys: Sequence[str]) -> str:
    return "+".join(sorted(str(key) for key in keys)) or "（无候选键）"


# ============================================================
# 输入读取与校验
# ============================================================


@dataclass
class ReviewInputs:
    """M3.6 读取到的 M2 / M3 / M3.5 产物（只做结构校验，不改写）。"""

    fact_candidates: list[dict[str, Any]] = field(default_factory=list)
    dimension_candidates: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    fact_tables: list[dict[str, Any]] = field(default_factory=list)
    dimension_tables: list[dict[str, Any]] = field(default_factory=list)
    grain_candidates: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    registry_objects: list[dict[str, Any]] = field(default_factory=list)
    inventory_tables: list[dict[str, Any]] = field(default_factory=list)
    columns: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    core_candidates: list[dict[str, Any]] = field(default_factory=list)
    assessments: list[dict[str, Any]] = field(default_factory=list)
    payload_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    carryover_text: str = ""
    carryover_path: Path = field(default_factory=Path)
    analysis_dir: Path = field(default_factory=Path)


def read_review_inputs(analysis_dir: Path) -> ReviewInputs:
    """读取 M3.6 依赖的全部 M2 / M3 / M3.5 产物。

    任何必需输入缺失或 JSON 非法都明确报错，
    不自动回退执行 analyze / analyze --stage。
    """

    missing = [relative for relative in INPUT_FILES if not (analysis_dir / relative).exists()]

    if missing:
        raise CurrentStateModelError(
            "M2 / M3 / M3.5 产物缺失，无法执行 M3.6 Current-State Model "
            f"Review：{'、'.join(missing)}"
            f"（目录：{_display_path(analysis_dir)}）；"
            "请先执行 analyze --stage evidence 生成 M2 产物、"
            "analyze --stage understanding 生成 M3 ~ M3.5 产物"
        )

    def load(relative: str, key: str, attr: str) -> list[dict[str, Any]]:
        path = analysis_dir / relative

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))

        except json.JSONDecodeError as exc:
            raise CurrentStateModelError(f"产物不是合法的 JSON：{path}（{exc}）") from exc

        if not isinstance(raw, dict):
            raise CurrentStateModelError(f"产物根节点不是对象：{path}")

        try:
            items = _dict_values(raw.get(key), key, path)

        except BusinessGrainError as exc:
            raise CurrentStateModelError(str(exc)) from exc

        inputs.payload_meta[attr] = {name: value for name, value in raw.items() if name != key}

        return items

    inputs = ReviewInputs()
    inputs.analysis_dir = analysis_dir
    inputs.carryover_path = analysis_dir / CARRYOVER_CHECKLIST_INPUT_FILE

    for relative, key, attr in ARRAY_INPUT_FILES:
        setattr(inputs, attr, load(relative, key, attr))

    if inputs.carryover_path.exists():
        try:
            inputs.carryover_text = inputs.carryover_path.read_text(encoding="utf-8")

        except OSError as exc:
            raise CurrentStateModelError(
                f"无法读取 current-state review 清单：{inputs.carryover_path}（{exc}）"
            ) from exc

    _validate_inputs(inputs)

    logger.info(
        "M3.6 输入已读取：%s（fact=%s，dimension=%s，relationship=%s，table=%s）",
        _display_path(analysis_dir),
        len(inputs.fact_candidates),
        len(inputs.dimension_candidates),
        len(inputs.relationships),
        len(inputs.inventory_tables),
    )

    return inputs


def _validate_inputs(inputs: ReviewInputs) -> None:
    """校验跨文件引用，报错即退出（不存在静默忽略）。"""

    process_keys = {_text(record.get("process_key")) for record in inputs.processes}
    registry_objects = {_text(record.get("object")) for record in inputs.registry_objects}
    grain_ids: set[str] = set()

    for position, record in enumerate(inputs.grain_candidates):
        grain_id = _text(record.get("grain_candidate_id"))
        process_key = _text(record.get("process_candidate_id"))

        if not grain_id:
            raise CurrentStateModelError(
                "grain-candidates.json 缺少 grain_candidate_id："
                f"candidates[{position}]（{_display_path(inputs.analysis_dir)}）"
            )

        if grain_id in grain_ids:
            raise CurrentStateModelError(
                f"grain-candidates.json 的 grain_candidate_id 重复：{grain_id}"
            )

        grain_ids.add(grain_id)

        if not process_key or process_key not in process_keys:
            raise CurrentStateModelError(
                f"grain candidate {grain_id} 引用未知 process candidate："
                f"{process_key or '（空）'}；请先执行 analyze --stage understanding"
            )

    fact_keys: set[str] = set()

    for position, record in enumerate(inputs.fact_candidates):
        fact_key = _text(record.get("fact_key"))

        if not fact_key:
            raise CurrentStateModelError(
                f"fact-candidates.json 缺少 fact_key：candidates[{position}]"
            )

        if fact_key in fact_keys:
            raise CurrentStateModelError(f"fact-candidates.json 的 fact_key 重复：{fact_key}")

        fact_keys.add(fact_key)

        process_key = _text(record.get("process_candidate_id"))
        grain_id = _text(record.get("grain_candidate_id"))

        if not process_key or process_key not in process_keys:
            raise CurrentStateModelError(
                f"fact candidate {fact_key} 引用未知 process candidate：{process_key or '（空）'}"
            )

        if not grain_id or grain_id not in grain_ids:
            raise CurrentStateModelError(
                f"fact candidate {fact_key} 引用未知 grain candidate：{grain_id or '（空）'}"
            )

    dimension_keys: set[str] = set()

    for position, record in enumerate(inputs.dimension_candidates):
        dimension_key = _text(record.get("dimension_key"))
        object_key = _text(record.get("object_key"))

        if not dimension_key:
            raise CurrentStateModelError(
                f"dimension-candidates.json 缺少 dimension_key：candidates[{position}]"
            )

        if dimension_key in dimension_keys:
            raise CurrentStateModelError(
                f"dimension-candidates.json 的 dimension_key 重复：{dimension_key}"
            )

        dimension_keys.add(dimension_key)

        if not object_key or object_key not in registry_objects:
            raise CurrentStateModelError(
                f"dimension candidate {dimension_key} 引用未知 Object："
                f"{object_key or '（空）'}；请先执行 analyze --stage understanding"
            )

    for position, record in enumerate(inputs.relationships):
        relationship_key = _text(record.get("relationship_key"))

        if not relationship_key:
            raise CurrentStateModelError(
                f"fact-dimension-relationships.json 缺少 relationship_key："
                f"relationships[{position}]"
            )

        if _text(record.get("fact_key")) not in fact_keys:
            raise CurrentStateModelError(
                f"relationship {relationship_key} 引用未知 fact candidate："
                f"{_text(record.get('fact_key')) or '（空）'}"
            )

        if _text(record.get("dimension_key")) not in dimension_keys:
            raise CurrentStateModelError(
                f"relationship {relationship_key} 引用未知 dimension candidate："
                f"{_text(record.get('dimension_key')) or '（空）'}"
            )

    for position, record in enumerate(inputs.fact_tables):
        if _text(record.get("fact_key")) not in fact_keys:
            raise CurrentStateModelError(
                f"fact-tables.json 的 tables[{position}] 引用未知 fact candidate："
                f"{_text(record.get('fact_key')) or '（空）'}"
            )

    for position, record in enumerate(inputs.dimension_tables):
        if _text(record.get("dimension_key")) not in dimension_keys:
            raise CurrentStateModelError(
                f"dimension-tables.json 的 tables[{position}] 引用未知 dimension "
                f"candidate：{_text(record.get('dimension_key')) or '（空）'}"
            )


def _checklist_carry_over(inputs: ReviewInputs) -> dict[str, dict[str, str]]:
    """解析本阶段清单回填；空文件返回 {}，缺列报错。"""

    if not inputs.carryover_text.strip():
        return {}

    try:
        return _parse_checklist_rows(
            inputs.carryover_text,
            required=REVIEW_CHECKLIST_REQUIRED_COLUMNS,
            source=inputs.carryover_path,
            label="current-state-review-checklist.md",
        )

    except BusinessGrainError as exc:
        raise CurrentStateModelError(str(exc)) from exc


# ============================================================
# 索引
# ============================================================


@dataclass
class ReviewIndexes:
    """评审所需的只读索引。"""

    table_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    column_names: dict[str, tuple[str, ...]] = field(default_factory=dict)
    layer_by_table: dict[str, str | None] = field(default_factory=dict)
    core_keys: frozenset[str] = frozenset()
    lineage_in: dict[str, tuple[str, ...]] = field(default_factory=dict)
    lineage_out: dict[str, tuple[str, ...]] = field(default_factory=dict)
    processes_by_table: dict[str, tuple[str, ...]] = field(default_factory=dict)
    facts_by_anchor: dict[str, tuple[int, ...]] = field(default_factory=dict)


def build_review_indexes(inputs: ReviewInputs) -> ReviewIndexes:
    """把 M3.6 输入整理成只读索引（全部稳定排序）。"""

    table_meta: dict[str, dict[str, Any]] = {}

    for record in sorted(inputs.inventory_tables, key=_table_sort_key):
        key = _text(record.get("table_key"))

        if not key:
            continue

        table_meta.setdefault(
            key.casefold(),
            {
                "table_key": key,
                "table_name": _text(record.get("table_name")) or _text(record.get("table")) or key,
                "workspace_id": record.get("workspace_id"),
                "project": _text(record.get("project")) or "",
                "comment": _text(record.get("comment")),
            },
        )

    column_names: dict[str, list[str]] = {}

    for record in sorted(inputs.columns, key=_table_column_sort_key):
        key = _text(record.get("table_key"))
        name = _text(record.get("column_name"))

        if not key or not name:
            continue

        column_names.setdefault(key.casefold(), []).append(name)

    layer_by_table: dict[str, str | None] = {}

    for record in sorted(
        inputs.assessments,
        key=lambda item: str(item.get("table_identifier") or "").casefold(),
    ):
        identifier = _text(record.get("table_identifier"))

        if not identifier:
            continue

        layer_by_table.setdefault(identifier.casefold(), _text(record.get("candidate_layer")))

    core_keys = frozenset(
        folded
        for record in inputs.core_candidates
        if (table_key := _text(record.get("table_key"))) is not None
        for folded in (table_key.casefold(),)
    )

    incoming: dict[str, set[str]] = {}
    outgoing: dict[str, set[str]] = {}

    for record in inputs.edges:
        source = _text(record.get("source_key")) or _text(record.get("source_table"))
        target = _text(record.get("target_key")) or _text(record.get("target_table"))

        if not source or not target or source.casefold() == target.casefold():
            continue

        outgoing.setdefault(source.casefold(), set()).add(target.casefold())
        incoming.setdefault(target.casefold(), set()).add(source.casefold())

    process_map: dict[str, set[str]] = {}

    for record in inputs.grain_candidates:
        key = _text(record.get("table_key"))
        process_key = _text(record.get("process_candidate_id"))

        if not key or not process_key:
            continue

        process_map.setdefault(key.casefold(), set()).add(process_key)

    anchor_map: dict[str, set[int]] = {}

    for position, record in enumerate(inputs.fact_candidates):
        key = _text(record.get("table_key"))

        if not key:
            continue

        anchor_map.setdefault(key.casefold(), set()).add(position)

    return ReviewIndexes(
        table_meta=table_meta,
        column_names={key: tuple(values) for key, values in column_names.items()},
        layer_by_table=layer_by_table,
        core_keys=core_keys,
        lineage_in={key: tuple(sorted(values)) for key, values in incoming.items()},
        lineage_out={key: tuple(sorted(values)) for key, values in outgoing.items()},
        processes_by_table={key: tuple(sorted(values)) for key, values in process_map.items()},
        facts_by_anchor={key: tuple(sorted(values)) for key, values in anchor_map.items()},
    )


# ============================================================
# finding 构造
# ============================================================


def _finding(
    finding_type: str,
    *,
    scope: str,
    scope_key: str,
    signature: str,
    description: str,
    impact: str,
    unresolved_reason: str,
    human_question: str,
    evidence: Sequence[Mapping[str, Any]],
    workspace_id: Any = None,
    table_key: str | None = None,
    table_name: str | None = None,
    process_candidate_id: str | None = None,
    grain_candidate_id: str | None = None,
    related_keys: Sequence[str] = (),
    human_review_required: bool = True,
) -> dict[str, Any]:
    """构造一条 review finding（证据至少一条，缺证据即断言失败）。"""

    entries = _sort_evidence(evidence, REVIEW_EVIDENCE_ORDER)

    if not entries:
        raise CurrentStateModelError(
            f"finding {finding_type}（{scope}:{scope_key}）缺少 evidence；"
            "Evidence First：不允许只有结论没有证据"
        )

    priority = FINDING_TYPE_PRIORITY[finding_type]

    return {
        "canonical_signature": signature,
        "priority": priority,
        "severity": REVIEW_SEVERITY_BY_PRIORITY[priority],
        "finding_type": finding_type,
        "review_group": FINDING_TYPE_GROUP[finding_type],
        "scope": scope,
        "scope_key": scope_key,
        "workspace_id": workspace_id,
        "table_key": table_key,
        "table_name": table_name,
        "process_candidate_id": process_candidate_id,
        "grain_candidate_id": grain_candidate_id,
        "current_role": None,
        "related_keys": [str(key) for key in related_keys],
        "evidence_sources": _sources(entries, REVIEW_EVIDENCE_ORDER),
        "evidence": entries,
        "description": description,
        "impact": impact,
        "unresolved_reason": unresolved_reason,
        "human_question": human_question,
        "human_review_required": human_review_required,
        "status": MODEL_STATUS_CANDIDATE,
        "human_validated": False,
    }


def _finalize_findings(
    rows: list[dict[str, Any]],
    carry_over: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    """编号（按 canonical signature）→ 回填人工状态 → 按优先级输出排序。"""

    rows.sort(
        key=lambda row: (
            str(row.get("canonical_signature") or ""),
            str(row.get("finding_type") or ""),
            str(row.get("scope") or ""),
            str(row.get("scope_key") or ""),
        )
    )

    for position, row in enumerate(rows, start=1):
        row["finding_id"] = FINDING_ID_FORMAT.format(index=position)

    if carry_over:
        _apply_carryover(rows, carry_over, key_field="finding_id", label="finding")

    rows.sort(
        key=lambda row: (
            _rank(str(row.get("priority") or ""), REVIEW_PRIORITY_ORDER),
            _rank(str(row.get("finding_type") or ""), FINDING_TYPE_ORDER),
            _rank(str(row.get("scope") or ""), FINDING_SCOPE_ORDER),
            str(row.get("scope_key") or ""),
            str(row.get("finding_id") or ""),
        )
    )

    return rows


# ============================================================
# Fact Gate 与 Fact Strength 评审
# ============================================================


def _fact_gate_review(
    inputs: ReviewInputs,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """重新走 Fact Gate（只读、不改闸门）并产出排除项 finding。"""

    qualified = 0
    rejected = 0
    reason_counts: dict[str, int] = {}
    passed_by_pattern: dict[str, int] = {}
    rejected_by_pattern: dict[str, int] = {}
    measure_rejected_by_pattern: dict[str, int] = {}
    samples: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for grain in inputs.grain_candidates:
        pattern = str(grain.get("grain_pattern") or "")
        passed, reason = fact_gate(grain)

        if passed:
            qualified += 1
            passed_by_pattern[pattern] = passed_by_pattern.get(pattern, 0) + 1
            continue

        rejected += 1
        label = str(reason or "")
        reason_counts[label] = reason_counts.get(label, 0) + 1
        rejected_by_pattern[pattern] = rejected_by_pattern.get(pattern, 0) + 1

        if label == FACT_GATE_REASON_MEASURE:
            measure_rejected_by_pattern[pattern] = measure_rejected_by_pattern.get(pattern, 0) + 1

        bucket = samples.setdefault((label, pattern), [])

        if len(bucket) < REVIEW_EXAMPLE_LIMIT:
            bucket.append(
                {
                    "grain_candidate_id": str(grain.get("grain_candidate_id") or ""),
                    "table_key": str(grain.get("table_key") or ""),
                    "grain_pattern": pattern,
                    "candidate_keys": [str(item) for item in grain.get("candidate_keys") or []],
                    "identifier_columns": [
                        str(item) for item in grain.get("identifier_columns") or []
                    ],
                }
            )

    sample_rejected: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for (label, pattern), rows in sorted(samples.items()):
        sample_rejected.setdefault(label, {})[pattern] = rows

    block: dict[str, Any] = {
        "qualified_count": qualified,
        "rejected_count": rejected,
        "rejected_reason_counts": dict(sorted(reason_counts.items(), key=lambda item: item[0])),
        "passed_by_pattern": dict(sorted(passed_by_pattern.items())),
        "rejected_by_pattern": dict(sorted(rejected_by_pattern.items())),
        "measure_rejected_by_pattern": dict(sorted(measure_rejected_by_pattern.items())),
        "sample_rejected": sample_rejected,
        "m35_gate": dict(inputs.payload_meta.get("fact_candidates", {}).get("gate") or {}),
        "gate_rule": (
            "transaction / event / snapshot 直接通过；periodic / aggregation / unknown "
            "必须有 measure_columns；本阶段只复算并评审，不修改闸门"
        ),
    }
    block["matches_m35"] = bool(
        int((block["m35_gate"] or {}).get("qualified_count") or 0) == qualified
        and int((block["m35_gate"] or {}).get("rejected_count") or 0) == rejected
    )

    findings: list[dict[str, Any]] = []
    pattern_total: dict[str, int] = {}

    for grain in inputs.grain_candidates:
        pattern = str(grain.get("grain_pattern") or "")
        pattern_total[pattern] = pattern_total.get(pattern, 0) + 1

    for pattern in sorted(
        measure_rejected_by_pattern,
        key=lambda item: (_rank(item, GRAIN_PATTERN_ORDER), item),
    ):
        count = measure_rejected_by_pattern[pattern]
        total = pattern_total.get(pattern, 0)
        bucket = samples.get((FACT_GATE_REASON_MEASURE, pattern), [])
        examples = [f"{item['grain_candidate_id']}（{item['table_key']}）" for item in bucket]
        evidence = [
            _evidence(
                REVIEW_EVIDENCE_GRAIN,
                f"grain_candidates:{pattern}",
                reason=(
                    f"grain_pattern={pattern} 的 {total} 个 grain candidate 中 "
                    f"{count} 个因 {FACT_GATE_REASON_MEASURE} 未通过 Fact Gate"
                ),
            ),
            *[
                _evidence(
                    REVIEW_EVIDENCE_GRAIN,
                    item["grain_candidate_id"],
                    table_key=item["table_key"],
                    reason=(
                        f"candidate_keys={_key_slug(item['candidate_keys'])}，"
                        f"identifier_columns={_examples(item['identifier_columns'])}，"
                        "measure_columns=（空）"
                    ),
                )
                for item in bucket
            ],
        ]

        findings.append(
            _finding(
                FINDING_TYPE_FACT_GATE_NO_MEASURE,
                scope=FINDING_SCOPE_STAGE,
                scope_key=pattern,
                signature=f"{FINDING_TYPE_FACT_GATE_NO_MEASURE}|stage|{pattern}",
                description=(
                    f"Fact Gate 因 {FACT_GATE_REASON_MEASURE} 排除 {count} / {total} 个 "
                    f"grain_pattern={pattern} 的 grain candidate（未产出 fact candidate）"
                ),
                impact=(
                    "这些表当前完全不进入事实模型；若其中存在没有显式度量的真实事实，"
                    "M4 的事实覆盖会出现缺口"
                ),
                unresolved_reason=(
                    "机器只能判断 measure_columns 是否存在，"
                    "无法判断「没有显式 measure 的表是否仍是事实表」"
                ),
                human_question=(
                    f"grain_pattern={pattern} 且无 measure 字段的表是否仍应作为 "
                    f"fact candidate？示例：{_examples(examples) or '（无示例）'}"
                ),
                evidence=evidence,
            )
        )

    pattern_reason_count = int(reason_counts.get(FACT_GATE_REASON_PATTERN) or 0)

    if pattern_reason_count:
        findings.append(
            _finding(
                FINDING_TYPE_FACT_GATE_PATTERN,
                scope=FINDING_SCOPE_STAGE,
                scope_key=FACT_GATE_REASON_PATTERN,
                signature=f"{FINDING_TYPE_FACT_GATE_PATTERN}|stage",
                description=(
                    f"Fact Gate 因 {FACT_GATE_REASON_PATTERN} 排除 "
                    f"{pattern_reason_count} 个 grain candidate"
                ),
                impact="词表之外的形态无法进入事实模型，可能存在未知的模型形态",
                unresolved_reason="机器不扩展形态词表，未知形态一律留给人工判断",
                human_question="是否存在未被词表覆盖的 grain 形态？请补充形态或确认排除正确",
                evidence=[
                    _evidence(
                        REVIEW_EVIDENCE_GRAIN,
                        f"grain_candidates:{FACT_GATE_REASON_PATTERN}",
                        reason=(
                            f"{pattern_reason_count} 个 grain candidate 的形态不在 Fact Gate 词表内"
                        ),
                    )
                ],
            )
        )

    return block, findings


def _strength_review(
    inputs: ReviewInputs,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """评审 evidence_strength 的真实含义（Evidence Strength ≠ Candidate Confidence）。"""

    facts = inputs.fact_candidates
    total = len(facts)
    strength_counts = _status_counts(
        [str(row.get("evidence_strength") or "") for row in facts],
        EVIDENCE_STRENGTH_ORDER,
    )
    source_presence = {
        source: sum(
            1
            for row in facts
            if source in {str(item) for item in row.get("evidence_sources") or []}
        )
        for source in FACT_EVIDENCE_ORDER
    }
    constructional = [FACT_EVIDENCE_PROCESS, FACT_EVIDENCE_GRAIN]

    block: dict[str, Any] = {
        "total": total,
        "strength_counts": strength_counts,
        "evidence_source_presence": source_presence,
        "constructional_sources": constructional,
        "interpretation": "Evidence Strength（证据源多样性）≠ Candidate Confidence（候选可信度）",
        "observation": (
            "process 与 grain 证据由候选构造本身产生（每个 fact candidate 必然携带），"
            "column 证据来自 M3.4 的字段形态；因此「≥3 类证据」几乎必然成立，"
            "strong 只说明证据来源丰富，不说明该表高度确定是事实表"
        ),
    }

    if not total:
        return block, []

    evidence = [
        _evidence(
            REVIEW_EVIDENCE_FACT,
            f"evidence_source:{source}",
            reason=f"{count} / {total} 个 fact candidate 带有 {source} 证据源",
        )
        for source, count in sorted(source_presence.items(), key=lambda item: item[0])
    ]
    evidence.append(
        _evidence(
            REVIEW_EVIDENCE_GRAIN,
            "grain_candidate:constructional",
            reason=(
                "process / grain 两类证据由 M3.4 grain candidate 构造直接产生，"
                "不构成对事实表的独立佐证"
            ),
        )
    )

    return (
        block,
        [
            _finding(
                FINDING_TYPE_EVIDENCE_STRENGTH,
                scope=FINDING_SCOPE_STAGE,
                scope_key="fact_evidence_strength",
                signature=f"{FINDING_TYPE_EVIDENCE_STRENGTH}|stage",
                description=(
                    f"{total} 个 fact candidate 的 evidence_strength 分布为 "
                    f"{_examples([f'{key}={value}' for key, value in strength_counts.items()])}；"
                    "其中 process / grain 由候选构造必然携带"
                ),
                impact=(
                    "若把 strong 读成「该表确定是事实表」，会高估当前模型的可信度；"
                    "M4 需要区分 Evidence Strength 与 Candidate Confidence"
                ),
                unresolved_reason=("机器不引入业务知识，无法在证据源之外给出候选可信度"),
                human_question=(
                    "M4 是否需要独立的 Candidate Confidence 口径？"
                    "在不看 strength 的情况下如何认定事实表成立？"
                ),
                evidence=evidence,
            )
        ],
    )


# ============================================================
# Grain / Fact 评审
# ============================================================


def _grain_findings(inputs: ReviewInputs) -> list[dict[str, Any]]:
    """GRAIN_CONFLICT / MIXED_GRAIN / SNAPSHOT_PERIODIC_AMBIGUOUS。"""

    anchor: dict[str, list[dict[str, Any]]] = {}

    for fact in sorted(inputs.fact_candidates, key=lambda row: str(row.get("fact_key") or "")):
        key = _fold(fact.get("table_key"))

        if key:
            anchor.setdefault(key, []).append(fact)

    findings: list[dict[str, Any]] = []

    for folded in sorted(anchor):
        rows = anchor[folded]
        meta = _meta_for(inputs, folded)
        table_key = str(meta.get("table_key") or folded)
        workspace_id = meta.get("workspace_id")
        table_name = str(meta.get("table_name") or table_key)
        fact_keys = [str(row.get("fact_key") or "") for row in rows]
        patterns = sorted({str(row.get("grain_pattern") or "") for row in rows})
        key_sets = sorted(
            {tuple(sorted(str(key) for key in row.get("candidate_keys") or [])) for row in rows}
        )
        pattern_text = _examples(patterns)

        if len(key_sets) > 1:
            evidence = [
                _evidence(
                    REVIEW_EVIDENCE_TABLE,
                    table_key,
                    workspace_id=workspace_id,
                    table_key=table_key,
                    reason=f"{len(rows)} 个 fact candidate 的 anchor 表都是这张表",
                ),
                _evidence(
                    REVIEW_EVIDENCE_COLUMN,
                    f"{table_key}.candidate_keys",
                    workspace_id=workspace_id,
                    table_key=table_key,
                    reason=(
                        f"{len(key_sets)} 组互不相同的候选键："
                        f"{_examples(['+'.join(keys) or '（空）' for keys in key_sets])}"
                    ),
                ),
                *[
                    _evidence(
                        REVIEW_EVIDENCE_FACT,
                        str(row.get("fact_key") or ""),
                        workspace_id=workspace_id,
                        table_key=table_key,
                        reason=(
                            f"pattern={row.get('grain_pattern')}，"
                            f"candidate_keys={_key_slug(list(row.get('candidate_keys') or []))}"
                        ),
                    )
                    for row in rows[:REVIEW_EXAMPLE_LIMIT]
                ],
            ]
            findings.append(
                _finding(
                    FINDING_TYPE_GRAIN_CONFLICT,
                    scope=FINDING_SCOPE_TABLE,
                    scope_key=table_key,
                    signature=f"{FINDING_TYPE_GRAIN_CONFLICT}|table|{folded}",
                    description=(
                        f"同一张表被 {len(rows)} 个 fact candidate 用 {len(key_sets)} 组"
                        f"互不相同的候选键定义粒度（形态：{pattern_text}）"
                    ),
                    impact=(
                        "该表的行级含义不唯一，M4 无法直接采信任一 fact candidate，"
                        "事实粒度必须先裁决"
                    ),
                    unresolved_reason=(
                        "Profiling 为 metadata-only，无法证明哪组键唯一；机器不挑 winner"
                    ),
                    human_question=(
                        f"表 {table_key} 的业务粒度到底是哪一组键？"
                        "其余 fact candidate 应作废还是并存？"
                    ),
                    evidence=evidence,
                    workspace_id=workspace_id,
                    table_key=table_key,
                    table_name=table_name,
                    process_candidate_id=_text(rows[0].get("process_candidate_id")),
                    related_keys=fact_keys,
                )
            )

        if len(patterns) > 1:
            evidence = [
                _evidence(
                    REVIEW_EVIDENCE_TABLE,
                    table_key,
                    workspace_id=workspace_id,
                    table_key=table_key,
                    reason=f"该表的 fact candidate 覆盖 {len(patterns)} 种 grain 形态",
                ),
                _evidence(
                    REVIEW_EVIDENCE_FACT,
                    f"patterns:{folded}",
                    workspace_id=workspace_id,
                    table_key=table_key,
                    reason=f"grain_pattern={_examples(patterns)}",
                ),
                *[
                    _evidence(
                        REVIEW_EVIDENCE_FACT,
                        str(row.get("fact_key") or ""),
                        workspace_id=workspace_id,
                        table_key=table_key,
                        reason=(
                            f"pattern={row.get('grain_pattern')}，"
                            f"candidate_keys={_key_slug(list(row.get('candidate_keys') or []))}，"
                            f"measures={_examples(list(row.get('measures') or [])) or '（空）'}"
                        ),
                    )
                    for row in rows[:REVIEW_EXAMPLE_LIMIT]
                ],
            ]
            findings.append(
                _finding(
                    FINDING_TYPE_MIXED_GRAIN,
                    scope=FINDING_SCOPE_TABLE,
                    scope_key=table_key,
                    signature=f"{FINDING_TYPE_MIXED_GRAIN}|table|{folded}",
                    description=(
                        f"同一张表同时被判断为 {len(patterns)} 种 grain 形态：{pattern_text}"
                    ),
                    impact=("表内可能同时存在不同粒度的行 / 字段；按任一形态单独建模都会失真"),
                    unresolved_reason=(
                        "机器只依据字段形态证据分类，无法判断表内数据实际落在哪个粒度"
                    ),
                    human_question=(
                        f"表 {table_key} 是否同时包含 {pattern_text} 粒度的数据？"
                        "哪一部分才是需要建模的事实？"
                    ),
                    evidence=evidence,
                    workspace_id=workspace_id,
                    table_key=table_key,
                    table_name=table_name,
                    process_candidate_id=_text(rows[0].get("process_candidate_id")),
                    related_keys=fact_keys,
                )
            )

        if GRAIN_PATTERN_SNAPSHOT in patterns and GRAIN_PATTERN_PERIODIC in patterns:
            evidence = [
                _evidence(
                    REVIEW_EVIDENCE_FACT,
                    f"snapshot_periodic:{folded}",
                    workspace_id=workspace_id,
                    table_key=table_key,
                    reason=(
                        f"同一表上同时存在 {GRAIN_PATTERN_SNAPSHOT} 与 "
                        f"{GRAIN_PATTERN_PERIODIC} 两种形态的 fact candidate"
                    ),
                ),
                _evidence(
                    REVIEW_EVIDENCE_TABLE,
                    table_key,
                    workspace_id=workspace_id,
                    table_key=table_key,
                    reason=f"fact_keys={_examples(fact_keys)}",
                ),
            ]
            findings.append(
                _finding(
                    FINDING_TYPE_SNAPSHOT_PERIODIC,
                    scope=FINDING_SCOPE_TABLE,
                    scope_key=table_key,
                    signature=f"{FINDING_TYPE_SNAPSHOT_PERIODIC}|table|{folded}",
                    description=(
                        f"表 {table_key} 同时出现 snapshot 与 periodic 两种形态，"
                        "快照状态与周期状态可能混在同一张表"
                    ),
                    impact="快照与周期事实的累加语义不同，混用会导致重复统计",
                    unresolved_reason="机器无法判断该表是按周期覆盖还是按快照留痕",
                    human_question="该表是周期快照（每期一行）还是周期累加（每期增量）？",
                    evidence=evidence,
                    workspace_id=workspace_id,
                    table_key=table_key,
                    table_name=table_name,
                    process_candidate_id=_text(rows[0].get("process_candidate_id")),
                    related_keys=fact_keys,
                )
            )

    return findings


def _meta_for(inputs: ReviewInputs, folded: str) -> dict[str, Any]:
    for record in inputs.inventory_tables:
        key = _text(record.get("table_key"))

        if key and key.casefold() == folded:
            return {
                "table_key": key,
                "table_name": _text(record.get("table_name")) or _text(record.get("table")) or key,
                "workspace_id": record.get("workspace_id"),
                "project": _text(record.get("project")) or "",
            }

    return {"table_key": folded, "table_name": folded, "workspace_id": None, "project": ""}


def _fact_findings(inputs: ReviewInputs) -> list[dict[str, Any]]:
    """FACT_WITHOUT_MEASURE（逐 fact）与 AGGREGATE_FACT（逐表）。"""

    findings: list[dict[str, Any]] = []

    for fact in sorted(inputs.fact_candidates, key=lambda row: str(row.get("fact_key") or "")):
        measures = [str(item) for item in fact.get("measures") or []]

        if measures:
            continue

        fact_key = str(fact.get("fact_key") or "")
        table_key = str(fact.get("table_key") or "")
        workspace_id = fact.get("workspace_id")
        pattern = str(fact.get("grain_pattern") or "")
        identifier_columns = [str(item) for item in fact.get("identifier_columns") or []]
        field_examples = (
            _examples(
                [*identifier_columns, *[str(item) for item in fact.get("time_attributes") or []]]
            )
            or "（无字段示例）"
        )

        findings.append(
            _finding(
                FINDING_TYPE_FACT_WITHOUT_MEASURE,
                scope=FINDING_SCOPE_FACT,
                scope_key=fact_key,
                signature=f"{FINDING_TYPE_FACT_WITHOUT_MEASURE}|fact|{fact_key}",
                description=(
                    f"fact candidate 通过 grain_pattern={pattern} 进入候选，"
                    "但 measure_columns 为空（没有任何度量字段）"
                ),
                impact=("缺度量的事实候选无法支撑指标计算；也可能是度量字段未被 M3.4 识别"),
                unresolved_reason=(
                    "机器只判断 measure_columns 是否存在，无法判断哪些数值字段应当算度量"
                ),
                human_question=(
                    f"表 {table_key} 是否存在业务度量？{field_examples} 中哪些应当作为度量？"
                ),
                evidence=[
                    _evidence(
                        REVIEW_EVIDENCE_FACT,
                        fact_key,
                        workspace_id=workspace_id,
                        table_key=table_key,
                        reason=(
                            f"pattern={pattern}，"
                            f"candidate_keys={_key_slug(list(fact.get('candidate_keys') or []))}，"
                            "measures=（空）"
                        ),
                    ),
                    _evidence(
                        REVIEW_EVIDENCE_GRAIN,
                        str(fact.get("grain_candidate_id") or ""),
                        workspace_id=workspace_id,
                        table_key=table_key,
                        reason=(
                            "形态本身即行级事实（transaction / event / snapshot）"
                            "所以未过 measure 闸门"
                            if pattern in FACT_GATE_DIRECT_PATTERNS
                            else "候选未携带度量字段"
                        ),
                    ),
                    _evidence(
                        REVIEW_EVIDENCE_TABLE,
                        table_key,
                        workspace_id=workspace_id,
                        table_key=table_key,
                        reason=(
                            f"identifier_columns={_examples(identifier_columns)}，度量字段缺失"
                        ),
                    ),
                ],
                workspace_id=workspace_id,
                table_key=table_key,
                table_name=str(fact.get("table_name") or table_key),
                process_candidate_id=_text(fact.get("process_candidate_id")),
                grain_candidate_id=_text(fact.get("grain_candidate_id")),
                related_keys=[fact_key],
            )
        )

    aggregate: dict[str, list[dict[str, Any]]] = {}

    for fact in inputs.fact_candidates:
        if str(fact.get("grain_pattern") or "") != GRAIN_PATTERN_AGGREGATION:
            continue

        key = _fold(fact.get("table_key"))

        if key:
            aggregate.setdefault(key, []).append(fact)

    for folded in sorted(aggregate):
        rows = sorted(
            aggregate[folded],
            key=lambda row: str(row.get("fact_key") or ""),
        )
        meta = _meta_for(inputs, folded)
        table_key = str(meta.get("table_key") or folded)
        measures = sorted({str(item) for row in rows for item in row.get("measures") or []})
        findings.append(
            _finding(
                FINDING_TYPE_AGGREGATE_FACT,
                scope=FINDING_SCOPE_TABLE,
                scope_key=table_key,
                signature=f"{FINDING_TYPE_AGGREGATE_FACT}|table|{folded}",
                description=(
                    f"该表有 {len(rows)} 个 grain_pattern=aggregation 的 fact candidate"
                    f"（度量字段 {len(measures)} 个）"
                ),
                impact=(
                    "聚合事实本身可以是有效模型；但若缺少原子事实与稳定粒度，M4 可能把汇总当成明细"
                ),
                unresolved_reason=("机器无法区分「设计上的聚合事实」与「被误判成事实的汇总结果」"),
                human_question=(
                    f"表 {table_key} 是原子事实、周期汇总，还是报表结果？是否已有对应的明细事实？"
                ),
                evidence=[
                    _evidence(
                        REVIEW_EVIDENCE_TABLE,
                        table_key,
                        workspace_id=meta.get("workspace_id"),
                        table_key=table_key,
                        reason=f"{len(rows)} 个聚合形态 fact candidate 的 anchor 表",
                    ),
                    _evidence(
                        REVIEW_EVIDENCE_FACT,
                        str(rows[0].get("fact_key") or ""),
                        workspace_id=meta.get("workspace_id"),
                        table_key=table_key,
                        reason=(
                            f"candidate_keys={_key_slug(list(rows[0].get('candidate_keys') or []))}"
                        ),
                    ),
                    _evidence(
                        REVIEW_EVIDENCE_COLUMN,
                        f"{table_key}.measures",
                        workspace_id=meta.get("workspace_id"),
                        table_key=table_key,
                        reason=f"度量字段：{_examples(measures) or '（空）'}",
                    ),
                ],
                workspace_id=meta.get("workspace_id"),
                table_key=table_key,
                table_name=str(meta.get("table_name") or table_key),
                process_candidate_id=_text(rows[0].get("process_candidate_id")),
                related_keys=[str(row.get("fact_key") or "") for row in rows],
            )
        )

    return findings


# ============================================================
# Dimension 与 Relationship 评审
# ============================================================


def _dimension_review(
    inputs: ReviewInputs,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Dimension 评审：是否只是 Object 的直接映射 + 角色歧义。"""

    dims = inputs.dimension_candidates
    role_status_counts = _status_counts(
        [str(row.get("role_status") or "") for row in dims],
        ["candidate", "ambiguous"],
    )
    object_keys = sorted(
        {str(row.get("object_key") or "") for row in dims if row.get("object_key")}
    )

    block: dict[str, Any] = {
        "count": len(dims),
        "object_keys": object_keys,
        "derived_from_object_count": len(object_keys),
        "role_status_counts": role_status_counts,
        "strength_counts": _status_counts(
            [str(row.get("evidence_strength") or "") for row in dims],
            EVIDENCE_STRENGTH_ORDER,
        ),
        "unresolved_counts": _status_counts(
            [
                reason
                for row in dims
                for reason in (str(item) for item in row.get("unresolved_reasons") or [])
            ],
            ["fact_and_dimension_ambiguous", "missing_fact_reference"],
        ),
        "attribute_limit": MODEL_ATTRIBUTE_LIMIT,
        "observation": (
            "dimension candidate 按 M3.2 Object 一一映射生成，"
            "没有独立的 Dimension Suitability 判定；attributes 只是关联表字段清单"
            f"（上限 {MODEL_ATTRIBUTE_LIMIT} 条），不是维度属性结论"
        ),
        "status_counts": _status_counts(
            [str(row.get("status") or "") for row in dims], MODEL_STATUS_ORDER
        ),
    }

    findings: list[dict[str, Any]] = []

    if dims:
        findings.append(
            _finding(
                FINDING_TYPE_DIMENSION_OBJECT_DERIVED,
                scope=FINDING_SCOPE_STAGE,
                scope_key="object_mapping",
                signature=f"{FINDING_TYPE_DIMENSION_OBJECT_DERIVED}|stage",
                description=(
                    f"{len(dims)} 个 dimension candidate 与 {len(object_keys)} 个 "
                    "M3.2 Object 一一对应，未经独立的 Dimension Suitability 判断"
                ),
                impact=(
                    "当前维度覆盖度等于 Object 识别覆盖度；未被识别为 Object 的维度在 M3.5 中不存在"
                ),
                unresolved_reason=("机器不引入业务知识，无法在 Object 之外判断哪些表应成为维度"),
                human_question=(
                    f"这 {len(object_keys)} 类 Object 是否覆盖了真实的维度集合？"
                    "哪些缺失的维度（如时间、渠道、活动）需要补识别？"
                ),
                evidence=[
                    *[
                        _evidence(
                            REVIEW_EVIDENCE_OBJECT,
                            f"object:{str(row.get('object_key') or '')}",
                            table_key=str((row.get("table_keys") or [""])[0] or ""),
                            reason=(
                                f"dimension candidate {row.get('dimension_key')} "
                                f"由 Object {row.get('object_key')} 生成"
                                f"（table_count={row.get('table_count')}，"
                                f"role_status={row.get('role_status')}）"
                            ),
                        )
                        for row in dims[:REVIEW_EXAMPLE_LIMIT]
                    ],
                    _evidence(
                        REVIEW_EVIDENCE_DIMENSION,
                        "dimension_candidates",
                        reason=(
                            f"dimension={len(dims)}，object={len(object_keys)}，"
                            "一一映射，无独立 suitability 判定"
                        ),
                    ),
                ],
            )
        )

    for row in sorted(dims, key=lambda item: str(item.get("dimension_key") or "")):
        if str(row.get("role_status") or "") != "ambiguous":
            continue

        dimension_key = str(row.get("dimension_key") or "")
        object_key = str(row.get("object_key") or "")
        fact_keys = [str(item) for item in row.get("referenced_by_facts") or []]
        table_keys = [str(item) for item in row.get("table_keys") or []]

        findings.append(
            _finding(
                FINDING_TYPE_ROLE_AMBIGUOUS,
                scope=FINDING_SCOPE_DIMENSION,
                scope_key=dimension_key,
                signature=f"{FINDING_TYPE_ROLE_AMBIGUOUS}|dimension|{dimension_key}",
                description=(
                    f"Object {object_key} 同时命中 dimension_candidate 与 "
                    "fact_related_object，角色不唯一"
                ),
                impact=(
                    "同一对象既被当作维度又被当作事实相关对象；M4 若不裁决会出现维度 / 事实职责混杂"
                ),
                unresolved_reason=(
                    "机器不自动决定最终事实 / 维度角色，角色裁决需要业务与建模共同确认"
                ),
                human_question=(f"Object {object_key} 究竟是维度、退化维度，还是事实的一部分？"),
                evidence=[
                    _evidence(
                        REVIEW_EVIDENCE_DIMENSION,
                        dimension_key,
                        table_key=table_keys[0] if table_keys else "",
                        reason=(
                            "modeling_roles="
                            + _examples([str(item) for item in row.get("modeling_roles") or []])
                            + "，role_status=ambiguous"
                        ),
                    ),
                    _evidence(
                        REVIEW_EVIDENCE_OBJECT,
                        f"object:{object_key}",
                        table_key=table_keys[0] if table_keys else "",
                        reason=(
                            f"关联表 {len(table_keys)} 张，"
                            f"被 {len(fact_keys)} 个 fact candidate 引用"
                        ),
                    ),
                    _evidence(
                        REVIEW_EVIDENCE_FACT,
                        f"referenced_by:{object_key}",
                        table_key=table_keys[0] if table_keys else "",
                        reason=f"引用该 Object 的 fact：{_examples(fact_keys) or '（无）'}",
                    ),
                ],
                table_key=table_keys[0] if table_keys else None,
                related_keys=[dimension_key, object_key, *fact_keys],
            )
        )

    return block, findings


def _relationship_review(
    inputs: ReviewInputs,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """关系评审：技术引用 ≠ 业务关系。"""

    rows = inputs.relationships
    single_evidence = 0
    technical_only = 0
    co_occurrence_only = 0
    no_shared_table = 0
    source_counts: dict[str, int] = {
        source: 0
        for source in [
            "process_object",
            "object_relationship",
            "table_reference",
            "sql_reference",
            "lineage",
        ]
    }
    technical_samples: list[str] = []
    co_occurrence_samples: list[str] = []

    for row in rows:
        sources = {str(item) for item in row.get("evidence_sources") or []}

        for source in sources:
            source_counts[source] = source_counts.get(source, 0) + 1

        if len(sources) < 2:
            single_evidence += 1

        if sources and sources <= TECHNICAL_RELATIONSHIP_SOURCES:
            technical_only += 1

            if len(technical_samples) < REVIEW_EXAMPLE_LIMIT:
                technical_samples.append(str(row.get("relationship_key") or ""))

        if "object_relationship" in sources and "process_object" not in sources:
            co_occurrence_only += 1

            if len(co_occurrence_samples) < REVIEW_EXAMPLE_LIMIT:
                co_occurrence_samples.append(str(row.get("relationship_key") or ""))

        if not row.get("shared_table_keys"):
            no_shared_table += 1

    block: dict[str, Any] = {
        "count": len(rows),
        "strength_counts": _status_counts(
            [str(row.get("evidence_strength") or "") for row in rows],
            EVIDENCE_STRENGTH_ORDER,
        ),
        "single_evidence_count": single_evidence,
        "technical_only_count": technical_only,
        "object_co_occurrence_only_count": co_occurrence_only,
        "no_shared_table_count": no_shared_table,
        "evidence_source_counts": source_counts,
        "observation": (
            "关系行的 Object / Process 链接来自 M3.2 的表共现、同 SQL 与表级血缘；"
            "技术引用 ≠ 业务关系，确认前必须核对 source_id"
        ),
        "status_counts": _status_counts(
            [str(row.get("status") or "") for row in rows], MODEL_STATUS_ORDER
        ),
    }

    findings: list[dict[str, Any]] = []

    if technical_only:
        findings.append(
            _finding(
                FINDING_TYPE_RELATIONSHIP_TECHNICAL,
                scope=FINDING_SCOPE_STAGE,
                scope_key="technical_only",
                signature=f"{FINDING_TYPE_RELATIONSHIP_TECHNICAL}|stage",
                description=(
                    f"{technical_only} / {len(rows)} 行关系只有技术引用证据"
                    "（table_reference / sql_reference / lineage），"
                    "没有任何 Object 或 Process 直接链接"
                ),
                impact=(
                    "把这些行当成 Fact → Dimension 业务关系会凭空放大维度覆盖；M4 不能据此确认维度"
                ),
                unresolved_reason=("机器不把 SQL JOIN / 血缘 / 共现升级为业务关系"),
                human_question=(
                    "只有技术引用的关系是否需要保留为业务关系候选？"
                    f"示例：{_examples(technical_samples) or '（无）'}"
                ),
                evidence=[
                    _evidence(
                        REVIEW_EVIDENCE_RELATIONSHIP,
                        "relationship:technical_only",
                        reason=(
                            f"{technical_only} 行的 evidence_sources 全部落在"
                            f"{_examples(sorted(TECHNICAL_RELATIONSHIP_SOURCES))}"
                        ),
                    ),
                    *[
                        _evidence(
                            REVIEW_EVIDENCE_RELATIONSHIP,
                            key,
                            reason="仅有技术引用证据",
                        )
                        for key in technical_samples
                    ],
                ],
            )
        )

    if co_occurrence_only:
        findings.append(
            _finding(
                FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE,
                scope=FINDING_SCOPE_STAGE,
                scope_key="object_co_occurrence",
                signature=f"{FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE}|stage",
                description=(
                    f"{co_occurrence_only} / {len(rows)} 行关系的 Object 链接只来自 "
                    "M3.2 的共现 / SQL / 血缘证据，没有 process participant 证据"
                ),
                impact=("共现只能说明表被一起使用，不等于该 Object 是此事实的正式维度"),
                unresolved_reason="机器不引入业务知识判断维度归属",
                human_question=(
                    "这些 Object 是否是对应事实的正式业务维度？"
                    f"示例：{_examples(co_occurrence_samples) or '（无）'}"
                ),
                evidence=[
                    _evidence(
                        REVIEW_EVIDENCE_RELATIONSHIP,
                        "relationship:object_co_occurrence",
                        reason=(
                            f"{co_occurrence_only} 行含 object_relationship 但不含 process_object"
                        ),
                    ),
                    *[
                        _evidence(
                            REVIEW_EVIDENCE_RELATIONSHIP,
                            key,
                            reason="Object 链接缺少 process participant 证据",
                        )
                        for key in co_occurrence_samples
                    ],
                ],
            )
        )

    return block, findings


# ============================================================
# 模型反模式
# ============================================================


def _duplicate_fact_findings(inputs: ReviewInputs) -> list[dict[str, Any]]:
    """同 process / 同 grain 形态 / 同候选键 / 同 Object、落在不同表 → 疑似重复。"""

    groups: dict[tuple[str, str, tuple[str, ...], tuple[str, ...]], list[dict[str, Any]]] = {}

    for fact in inputs.fact_candidates:
        key = (
            str(fact.get("process_candidate_id") or ""),
            str(fact.get("grain_pattern") or ""),
            tuple(sorted(str(item) for item in fact.get("candidate_keys") or [])),
            tuple(sorted(str(item) for item in fact.get("object_keys") or [])),
        )
        groups.setdefault(key, []).append(fact)

    findings: list[dict[str, Any]] = []

    for key in sorted(groups):
        rows = sorted(groups[key], key=lambda row: str(row.get("fact_key") or ""))
        tables = sorted({str(row.get("table_key") or "") for row in rows})

        if len(rows) < 2 or len(tables) < 2:
            continue

        process_key, pattern, candidate_keys, object_keys = key
        scope_key = f"{process_key}|{pattern}|{_key_slug(list(candidate_keys))}"
        evidence = [
            _evidence(
                REVIEW_EVIDENCE_TABLE,
                table_key,
                table_key=table_key,
                reason=f"同一逻辑事实的候选落在表 {table_key}",
            )
            for table_key in tables[:REVIEW_EXAMPLE_LIMIT]
        ]
        evidence.extend(
            _evidence(
                REVIEW_EVIDENCE_FACT,
                str(row.get("fact_key") or ""),
                table_key=str(row.get("table_key") or ""),
                reason=(
                    f"pattern={row.get('grain_pattern')}，"
                    f"objects={_examples(list(object_keys)) or '（空）'}"
                ),
            )
            for row in rows[:REVIEW_EXAMPLE_LIMIT]
        )

        findings.append(
            _finding(
                FINDING_TYPE_DUPLICATE_FACT,
                scope=FINDING_SCOPE_FACT_GROUP,
                scope_key=scope_key,
                signature=(
                    f"{FINDING_TYPE_DUPLICATE_FACT}|{process_key}|{pattern}"
                    f"|keys={','.join(candidate_keys)}|objects={','.join(object_keys)}"
                    f"|tables={','.join(tables)}"
                ),
                description=(
                    f"{len(rows)} 个 fact candidate 具有相同的 process、grain 形态、"
                    f"候选键与 Object，却落在 {len(tables)} 张不同的表上"
                ),
                impact="同一逻辑模型可能被复制多份，M4 若全部建模会重复计数",
                unresolved_reason="机器不判断哪张表是权威版本，也不删除任何候选",
                human_question=(f"{_examples(tables)} 是否是同一逻辑模型的副本？权威表是哪一张？"),
                evidence=evidence,
                table_key=tables[0],
                process_candidate_id=process_key,
                related_keys=[*tables, *(str(row.get("fact_key") or "") for row in rows)],
            )
        )

    return findings


def _overlapping_fact_findings(
    inputs: ReviewInputs,
    indexes: ReviewIndexes,
) -> list[dict[str, Any]]:
    """同 process / 同形态下字段高度重合的表对 → 疑似重叠模型。"""

    groups: dict[tuple[str, str], list[str]] = {}

    for fact in inputs.fact_candidates:
        table_key = str(fact.get("table_key") or "")

        if not table_key:
            continue

        key = (
            str(fact.get("process_candidate_id") or ""),
            str(fact.get("grain_pattern") or ""),
        )
        bucket = groups.setdefault(key, [])

        if table_key not in bucket:
            bucket.append(table_key)

    wanted = {
        folded for values in groups.values() for folded in (table.casefold() for table in values)
    }
    column_sets = {
        folded: {name.casefold() for name in indexes.column_names.get(folded, ())}
        for folded in wanted
    }

    findings: list[dict[str, Any]] = []

    for key in sorted(groups):
        process_key, pattern = key
        tables = sorted(groups[key], key=lambda table: table.casefold())

        for position, left in enumerate(tables):
            for right in tables[position + 1 :]:
                left_set = column_sets.get(left.casefold(), set())
                right_set = column_sets.get(right.casefold(), set())

                if len(left_set) < OVERLAP_MIN_COLUMNS or len(right_set) < OVERLAP_MIN_COLUMNS:
                    continue

                total = len(left_set | right_set)

                if not total:
                    continue

                shared = left_set & right_set
                ratio = len(shared) / total

                if ratio < OVERLAP_MIN_JACCARD:
                    continue

                shared_names = sorted(shared)
                findings.append(
                    _finding(
                        FINDING_TYPE_OVERLAPPING_FACT,
                        scope=FINDING_SCOPE_TABLE_PAIR,
                        scope_key=f"{left}|{right}",
                        signature=(
                            f"{FINDING_TYPE_OVERLAPPING_FACT}|{process_key}|{pattern}"
                            f"|{left.casefold()}|{right.casefold()}"
                        ),
                        description=(
                            f"同一 process（{process_key}）与同一 grain 形态（{pattern}）"
                            f"下，两张表字段重合 {len(shared)} / {total}"
                            f"（Jaccard {ratio:.2f}）"
                        ),
                        impact="疑似同一逻辑模型的副本 / 临时表，M4 可能重复建模",
                        unresolved_reason=("机器只能比较字段重合度，无法判断哪张表是权威版本"),
                        human_question=(
                            f"{left} 与 {right} 是否是同一张表的副本？权威表是哪一张？"
                        ),
                        evidence=[
                            _evidence(
                                REVIEW_EVIDENCE_COLUMN,
                                left,
                                table_key=left,
                                reason=f"{len(left_set)} 个字段，与 {right} 重合 {len(shared)}",
                            ),
                            _evidence(
                                REVIEW_EVIDENCE_COLUMN,
                                right,
                                table_key=right,
                                reason=f"{len(right_set)} 个字段，与 {left} 重合 {len(shared)}",
                            ),
                            _evidence(
                                REVIEW_EVIDENCE_FACT,
                                f"overlap:{process_key}:{pattern}",
                                table_key=left,
                                reason=(
                                    "重合字段示例："
                                    f"{_examples(shared_names[:REVIEW_EXAMPLE_LIMIT])}"
                                ),
                            ),
                        ],
                        table_key=left,
                        related_keys=[left, right],
                    )
                )

    return findings


def _table_issue_findings(
    inputs: ReviewInputs,
    indexes: ReviewIndexes,
) -> list[dict[str, Any]]:
    """MULTI_PROCESS_TABLE / WIDE_ANALYTICAL_TABLE / RESULT_TABLE。"""

    findings: list[dict[str, Any]] = []
    anchor_tables = sorted(
        {
            _fold(fact.get("table_key"))
            for fact in inputs.fact_candidates
            if _fold(fact.get("table_key"))
        }
    )
    anchor_facts: dict[str, list[dict[str, Any]]] = {
        folded: [
            inputs.fact_candidates[position] for position in indexes.facts_by_anchor.get(folded, ())
        ]
        for folded in anchor_tables
    }

    for folded in sorted(indexes.processes_by_table):
        process_keys = indexes.processes_by_table[folded]
        meta = _meta_for(inputs, folded)

        if len(process_keys) < 2:
            continue

        table_key = str(meta.get("table_key") or folded)
        findings.append(
            _finding(
                FINDING_TYPE_MULTI_PROCESS_TABLE,
                scope=FINDING_SCOPE_TABLE,
                scope_key=table_key,
                signature=f"{FINDING_TYPE_MULTI_PROCESS_TABLE}|table|{folded}",
                description=(f"该表出现在 {len(process_keys)} 个不同的 process candidate 中"),
                impact="一张表服务多个业务过程时，职责可能混杂（不一定是错误）",
                unresolved_reason="机器不判断过程边界是否划分正确",
                human_question=(f"表 {table_key} 是否确实服务于多个业务过程？还是过程划分过细？"),
                evidence=[
                    _evidence(
                        REVIEW_EVIDENCE_TABLE,
                        table_key,
                        workspace_id=meta.get("workspace_id"),
                        table_key=table_key,
                        reason=f"出现在 {len(process_keys)} 个 process candidate",
                    ),
                    *[
                        _evidence(
                            REVIEW_EVIDENCE_PROCESS,
                            process_key,
                            workspace_id=meta.get("workspace_id"),
                            table_key=table_key,
                            reason=f"{process_key} 的 grain candidate 覆盖该表",
                        )
                        for process_key in process_keys[:REVIEW_EXAMPLE_LIMIT]
                    ],
                ],
                workspace_id=meta.get("workspace_id"),
                table_key=table_key,
                table_name=str(meta.get("table_name") or table_key),
                related_keys=list(process_keys),
            )
        )

    for folded in anchor_tables:
        meta = _meta_for(inputs, folded)
        table_key = str(meta.get("table_key") or folded)
        column_count = len(indexes.column_names.get(folded, ()))
        rows = anchor_facts.get(folded, [])
        measure_count = max((len(row.get("measures") or []) for row in rows), default=0)
        measure_examples = (
            _examples([str(item) for item in rows[0].get("measures") or []]) if rows else ""
        )

        if column_count >= WIDE_COLUMN_THRESHOLD or measure_count >= WIDE_MEASURE_THRESHOLD:
            findings.append(
                _finding(
                    FINDING_TYPE_WIDE_ANALYTICAL_TABLE,
                    scope=FINDING_SCOPE_TABLE,
                    scope_key=table_key,
                    signature=f"{FINDING_TYPE_WIDE_ANALYTICAL_TABLE}|table|{folded}",
                    description=(
                        f"该表 {column_count} 个字段、最多 {measure_count} 个度量字段"
                        "（阈值：字段 ≥ "
                        f"{WIDE_COLUMN_THRESHOLD} 或度量 ≥ {WIDE_MEASURE_THRESHOLD}）"
                    ),
                    impact=(
                        "明显是宽的分析型表，可能把多个过程的指标与维度属性放在一起（本阶段不拆分）"
                    ),
                    unresolved_reason="机器不判断是否应当拆分，也不产出目标分层",
                    human_question=(
                        f"表 {table_key} 是否混合了多个业务过程的字段？M4 需要如何处理这张表？"
                    ),
                    evidence=[
                        _evidence(
                            REVIEW_EVIDENCE_COLUMN,
                            table_key,
                            workspace_id=meta.get("workspace_id"),
                            table_key=table_key,
                            reason=f"{column_count} 个字段（inventory/columns.json）",
                        ),
                        _evidence(
                            REVIEW_EVIDENCE_FACT,
                            str(rows[0].get("fact_key") or "") if rows else f"measures:{folded}",
                            workspace_id=meta.get("workspace_id"),
                            table_key=table_key,
                            reason=(
                                f"度量字段最多 {measure_count} 个：{measure_examples or '（空）'}"
                            ),
                        ),
                    ],
                    workspace_id=meta.get("workspace_id"),
                    table_key=table_key,
                    table_name=str(meta.get("table_name") or table_key),
                    process_candidate_id=_text(
                        rows[0].get("process_candidate_id") if rows else None
                    ),
                    related_keys=[str(row.get("fact_key") or "") for row in rows],
                )
            )

        in_degree = len(indexes.lineage_in.get(folded, ()))
        out_degree = len(indexes.lineage_out.get(folded, ()))
        is_view = any(
            bool(record.get("is_virtual_view"))
            for record in inputs.inventory_tables
            if _fold(record.get("table_key")) == folded
        )
        result_like = is_view or (in_degree >= RESULT_MIN_INCOMING and out_degree == 0)

        if not rows or not result_like:
            continue

        incoming = indexes.lineage_in.get(folded, ())
        findings.append(
            _finding(
                FINDING_TYPE_RESULT_TABLE,
                scope=FINDING_SCOPE_TABLE,
                scope_key=table_key,
                signature=f"{FINDING_TYPE_RESULT_TABLE}|table|{folded}",
                description=(
                    "该表是 fact candidate 表且"
                    + ("虚拟视图（is_virtual_view）" if is_view else "血缘只有入边没有出边")
                    + f"（入边 {in_degree}，出边 {out_degree}）"
                ),
                impact=("疑似结果 / 输出表：如果把结果表当事实，M4 会把派生数据当源数据"),
                unresolved_reason="机器不判断该表是中间结果还是正式落地事实",
                human_question=(
                    f"表 {table_key} 是计算结果还是权威事实？它的上游是否已经有对应事实？"
                ),
                evidence=[
                    _evidence(
                        REVIEW_EVIDENCE_TABLE,
                        table_key,
                        workspace_id=meta.get("workspace_id"),
                        table_key=table_key,
                        reason=f"is_virtual_view={is_view}，入边 {in_degree}，出边 {out_degree}",
                    ),
                    *[
                        _evidence(
                            REVIEW_EVIDENCE_LINEAGE,
                            source,
                            workspace_id=meta.get("workspace_id"),
                            table_key=table_key,
                            reason=f"上游表 {source} 通过血缘写入该表",
                        )
                        for source in incoming[:REVIEW_EXAMPLE_LIMIT]
                    ],
                ],
                workspace_id=meta.get("workspace_id"),
                table_key=table_key,
                table_name=str(meta.get("table_name") or table_key),
                process_candidate_id=_text(rows[0].get("process_candidate_id") if rows else None),
                related_keys=[str(row.get("fact_key") or "") for row in rows],
            )
        )

    return findings


def _process_findings(inputs: ReviewInputs) -> list[dict[str, Any]]:
    """一个 process 多个 grain：信息性记录（不是错误）。"""

    patterns: dict[str, set[str]] = {}

    for fact in inputs.fact_candidates:
        process_key = str(fact.get("process_candidate_id") or "")

        if not process_key:
            continue

        patterns.setdefault(process_key, set()).add(str(fact.get("grain_pattern") or ""))

    findings: list[dict[str, Any]] = []

    for process_key in sorted(patterns):
        values = sorted(patterns[process_key])

        if len(values) < 2:
            continue

        findings.append(
            _finding(
                FINDING_TYPE_PROCESS_MULTIPLE_GRAINS,
                scope=FINDING_SCOPE_PROCESS,
                scope_key=process_key,
                signature=f"{FINDING_TYPE_PROCESS_MULTIPLE_GRAINS}|process|{process_key}",
                description=(
                    f"process {process_key} 下的 fact candidate 覆盖 {len(values)} 种"
                    f" grain 形态：{_examples(values)}"
                ),
                impact=(
                    "一个业务过程对应多个粒度是正常现象（订单 / 订单行 / 日汇总…），仅作信息记录"
                ),
                unresolved_reason="机器不判断这些粒度是否都属于同一业务过程",
                human_question=(
                    "（信息性）这些粒度是否都属于同一业务过程？是否需要区分过程与子过程？"
                ),
                evidence=[
                    _evidence(
                        REVIEW_EVIDENCE_PROCESS,
                        process_key,
                        reason=f"该 process 的 fact candidate 覆盖形态 {_examples(values)}",
                    ),
                    _evidence(
                        REVIEW_EVIDENCE_GRAIN,
                        f"grains:{process_key}",
                        reason=f"grain_pattern={_examples(values)}",
                    ),
                ],
                process_candidate_id=process_key,
                human_review_required=False,
            )
        )

    return findings


# ============================================================
# Current-State Model 分类
# ============================================================


def _table_rows(
    inputs: ReviewInputs,
    indexes: ReviewIndexes,
    findings: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """逐表描述当前模型形态（全部 inventory 表，UNKNOWN 保留）。"""

    facts_by_anchor: dict[str, list[dict[str, Any]]] = {
        folded: [
            inputs.fact_candidates[position] for position in indexes.facts_by_anchor.get(folded, ())
        ]
        for folded in indexes.facts_by_anchor
    }
    fact_anchors: set[str] = set()
    fact_supporting: set[str] = set()
    dimension_anchor: dict[str, str] = {}
    dimension_supporting: set[str] = set()

    for row in inputs.fact_tables:
        folded = _fold(row.get("table_key"))

        if not folded:
            continue

        if str(row.get("role") or "") == GRAIN_ROLE_ANCHOR:
            fact_anchors.add(folded)
            fact_supporting.discard(folded)
        elif folded not in fact_anchors:
            fact_supporting.add(folded)

    for row in inputs.dimension_tables:
        folded = _fold(row.get("table_key"))

        if not folded:
            continue

        if str(row.get("role") or "") == GRAIN_ROLE_ANCHOR:
            dimension_anchor[folded] = str(row.get("dimension_key") or "")
            dimension_supporting.discard(folded)
        elif folded not in dimension_anchor:
            dimension_supporting.add(folded)

    finding_ids: dict[str, list[str]] = {}

    for finding in findings:
        keys = [str(item) for item in finding.get("related_keys") or []]
        table_key = _text(finding.get("table_key"))

        targets: set[str] = {key for key in keys if "." in key}

        if table_key:
            targets.add(table_key)

        if str(finding.get("scope") or "") == FINDING_SCOPE_TABLE_PAIR:
            targets = {part for part in str(finding.get("scope_key") or "").split("|")}

        for target in sorted(targets):
            finding_ids.setdefault(target.casefold(), []).append(
                str(finding.get("finding_id") or "")
            )

    rows: list[dict[str, Any]] = []

    for record in sorted(inputs.inventory_tables, key=_table_sort_key):
        key = _text(record.get("table_key"))

        if not key:
            continue

        folded = key.casefold()
        anchor_facts = facts_by_anchor.get(folded, [])
        fact_keys = sorted(str(row.get("fact_key") or "") for row in anchor_facts)
        patterns = sorted({str(row.get("grain_pattern") or "") for row in anchor_facts})
        key_sets = sorted(
            {
                tuple(sorted(str(item) for item in row.get("candidate_keys") or []))
                for row in anchor_facts
            }
        )
        column_names = indexes.column_names.get(folded, ())
        measure_count = max((len(row.get("measures") or []) for row in anchor_facts), default=0)
        dimension_key = dimension_anchor.get(folded)
        is_view = bool(record.get("is_virtual_view"))
        in_degree = len(indexes.lineage_in.get(folded, ()))
        out_degree = len(indexes.lineage_out.get(folded, ()))
        roles: set[str] = set()

        if anchor_facts and dimension_key:
            roles.update(
                {
                    CURRENT_MODEL_ROLE_AMBIGUOUS,
                    CURRENT_MODEL_ROLE_FACT,
                    CURRENT_MODEL_ROLE_DIMENSION,
                }
            )
        elif anchor_facts:
            roles.add(CURRENT_MODEL_ROLE_FACT)
        elif dimension_key:
            roles.add(CURRENT_MODEL_ROLE_DIMENSION)

        if len(column_names) >= WIDE_COLUMN_THRESHOLD or measure_count >= WIDE_MEASURE_THRESHOLD:
            roles.add(CURRENT_MODEL_ROLE_WIDE)

        if is_view or (anchor_facts and in_degree >= RESULT_MIN_INCOMING and out_degree == 0):
            roles.add(CURRENT_MODEL_ROLE_RESULT)

        if not roles:
            roles.add(CURRENT_MODEL_ROLE_UNKNOWN)

        ordered_roles = [role for role in CURRENT_MODEL_ROLE_ORDER if role in roles]
        current_role = ordered_roles[0]
        fact_dimension_roles = {
            CURRENT_MODEL_ROLE_FACT,
            CURRENT_MODEL_ROLE_DIMENSION,
            CURRENT_MODEL_ROLE_AMBIGUOUS,
        }

        rows.append(
            {
                "table_key": key,
                "table_name": _text(record.get("table_name")) or _text(record.get("table")) or key,
                "workspace_id": record.get("workspace_id"),
                "project": _text(record.get("project")) or "",
                "schema": _text(record.get("schema")) or "",
                "candidate_layer": indexes.layer_by_table.get(folded),
                "core_candidate": folded in indexes.core_keys,
                "current_role": current_role,
                "current_roles": ordered_roles,
                "model_shape": _shape_of(patterns),
                "role_ambiguous": len(roles & fact_dimension_roles) > 1,
                "fact_anchor_count": len(anchor_facts),
                "fact_keys": fact_keys,
                "fact_supporting": folded in fact_supporting,
                "dimension_key": dimension_key,
                "dimension_supporting": folded in dimension_supporting,
                "process_candidate_ids": list(indexes.processes_by_table.get(folded, ())),
                "grain_patterns": patterns,
                "grain_key_set_count": len(key_sets),
                "column_count": len(column_names),
                "measure_count": measure_count,
                "is_virtual_view": is_view,
                "lineage_in_degree": in_degree,
                "lineage_out_degree": out_degree,
                "finding_ids": sorted(set(finding_ids.get(folded, []))),
                "status": MODEL_STATUS_CANDIDATE,
                "human_validated": False,
            }
        )

    return rows


# ============================================================
# 产物组装、写出与运行入口
# ============================================================


def _model_payload(
    inputs: ReviewInputs,
    table_rows: Sequence[Mapping[str, Any]],
    findings: Sequence[Mapping[str, Any]],
    gate_review: Mapping[str, Any],
    strength_review: Mapping[str, Any],
    dimension_review: Mapping[str, Any],
    relationship_review: Mapping[str, Any],
) -> dict[str, Any]:
    """current-state-model.json：范围、形态总览、模型质量与四项评审。"""

    type_counts = _status_counts(
        [str(row.get("finding_type") or "") for row in findings], FINDING_TYPE_ORDER
    )

    def quality(finding_type: str) -> int:
        return int(type_counts.get(finding_type) or 0)

    workspace_ids = sorted(
        {
            record.get("workspace_id")
            for record in inputs.inventory_tables
            if record.get("workspace_id") is not None
        },
        key=str,
    )

    return {
        "count": len(table_rows),
        "note": f"{CURRENT_STATE_NOTE}；{FINDING_CANDIDATE_NOTE}",
        "scope": {
            "workspace_ids": workspace_ids,
            "inventory_table_count": len(inputs.inventory_tables),
            "classified_table_count": len(table_rows),
            "fact_count": len(inputs.fact_candidates),
            "dimension_count": len(inputs.dimension_candidates),
            "relationship_count": len(inputs.relationships),
            "fact_table_row_count": len(inputs.fact_tables),
            "dimension_table_row_count": len(inputs.dimension_tables),
            "process_count": len(inputs.processes),
            "grain_count": len(inputs.grain_candidates),
            "object_count": len(inputs.registry_objects),
        },
        "role_counts": _status_counts(
            [str(row.get("current_role") or "") for row in table_rows],
            CURRENT_MODEL_ROLE_ORDER,
        ),
        "shape_counts": _status_counts(
            [str(row.get("model_shape") or "") for row in table_rows],
            CURRENT_MODEL_SHAPE_ORDER,
        ),
        "finding_count": len(findings),
        "priority_counts": _status_counts(
            [str(row.get("priority") or "") for row in findings], REVIEW_PRIORITY_ORDER
        ),
        "finding_type_counts": type_counts,
        "review_group_counts": _status_counts(
            [str(row.get("review_group") or "") for row in findings], REVIEW_GROUP_ORDER
        ),
        "status_counts": _status_counts(
            [str(row.get("status") or "") for row in findings], MODEL_STATUS_ORDER
        ),
        "model_quality": {
            "grain_conflict": quality(FINDING_TYPE_GRAIN_CONFLICT),
            "mixed_grain": quality(FINDING_TYPE_MIXED_GRAIN),
            "role_ambiguity": quality(FINDING_TYPE_ROLE_AMBIGUOUS),
            "duplicate_fact": quality(FINDING_TYPE_DUPLICATE_FACT),
            "overlapping_fact": quality(FINDING_TYPE_OVERLAPPING_FACT),
            "multi_process_table": quality(FINDING_TYPE_MULTI_PROCESS_TABLE),
            "wide_analytical": quality(FINDING_TYPE_WIDE_ANALYTICAL_TABLE),
            "aggregate_fact": quality(FINDING_TYPE_AGGREGATE_FACT),
            "snapshot_periodic": quality(FINDING_TYPE_SNAPSHOT_PERIODIC),
            "result_table": quality(FINDING_TYPE_RESULT_TABLE),
            "fact_without_measure": quality(FINDING_TYPE_FACT_WITHOUT_MEASURE),
            "relationship_technical_only": int(
                relationship_review.get("technical_only_count") or 0
            ),
            "relationship_object_co_occurrence": int(
                relationship_review.get("object_co_occurrence_only_count") or 0
            ),
        },
        "fact_gate_review": dict(gate_review),
        "evidence_strength_review": dict(strength_review),
        "dimension_review": dict(dimension_review),
        "relationship_review": dict(relationship_review),
        "finding_status_counts_note": (
            "机器阶段 finding 的 status 恒为 candidate；"
            "只有 current-state-review-checklist.md 回填后才会改变"
        ),
    }


def build_current_state_model(inputs: ReviewInputs) -> CurrentStateModelResult:
    """从 M2 / M3 / M3.5 产物构建 M3.6 的三个 JSON 与两个 Markdown 正文。"""

    indexes = build_review_indexes(inputs)
    gate_review, gate_findings = _fact_gate_review(inputs)
    strength_review, strength_findings = _strength_review(inputs)
    dimension_review, dimension_findings = _dimension_review(inputs)
    relationship_review, relationship_findings = _relationship_review(inputs)

    raw_findings = [
        *gate_findings,
        *strength_findings,
        *_grain_findings(inputs),
        *_fact_findings(inputs),
        *dimension_findings,
        *relationship_findings,
        *_duplicate_fact_findings(inputs),
        *_overlapping_fact_findings(inputs, indexes),
        *_table_issue_findings(inputs, indexes),
        *_process_findings(inputs),
    ]

    carry_over = _checklist_carry_over(inputs)
    findings = _finalize_findings(raw_findings, carry_over)
    table_rows = _table_rows(inputs, indexes, findings)

    model_payload = _model_payload(
        inputs,
        table_rows,
        findings,
        gate_review,
        strength_review,
        dimension_review,
        relationship_review,
    )

    findings_payload: dict[str, Any] = {
        "count": len(findings),
        "note": (
            f"{FINDING_CANDIDATE_NOTE}；每条 finding 都带 evidence，"
            "异常只标记 Review，不判定 Wrong。"
        ),
        "priority_counts": dict(model_payload["priority_counts"]),
        "finding_type_counts": dict(model_payload["finding_type_counts"]),
        "review_group_counts": dict(model_payload["review_group_counts"]),
        "status_counts": dict(model_payload["status_counts"]),
        "severity_by_priority": {
            priority: REVIEW_SEVERITY_BY_PRIORITY[priority] for priority in REVIEW_PRIORITY_ORDER
        },
        "findings": findings,
    }

    tables_payload: dict[str, Any] = {
        "count": len(table_rows),
        "note": (
            "current_role / model_shape 只描述当前平台已经存在的模型形态，"
            "不是 Target DWD 设计；UNKNOWN 一律保留。"
        ),
        "role_counts": dict(model_payload["role_counts"]),
        "shape_counts": dict(model_payload["shape_counts"]),
        "tables": table_rows,
    }

    result = CurrentStateModelResult(
        model=model_payload,
        tables=tables_payload,
        findings=findings_payload,
        analysis_dir=inputs.analysis_dir,
    )

    result.summary = render_current_state_summary(
        current_model=model_payload,
        findings=findings_payload,
        analysis_dir=inputs.analysis_dir,
    )
    result.checklist = render_current_state_review_checklist(
        findings,
        carry_over=carry_over,
        row_limit=REVIEW_CHECKLIST_ROW_LIMIT,
    )

    return result


def write_current_state_model(
    result: CurrentStateModelResult,
    output_dir: Path,
) -> tuple[Path, ...]:
    """写出 M3.6 产物，返回路径列表（固定顺序）。

    只覆盖本模块声明的五个文件，不删除、不改写已有 M2 / M3 / M3.5 产物。
    """

    ensure_dir(output_dir)

    paths = {name: output_dir / name for name in OUTPUT_FILES}

    write_json(paths["current-state-model.json"], result.model)
    write_json(paths["current-state-model-tables.json"], result.tables)
    write_json(paths["current-state-findings.json"], result.findings)
    write_text(paths["current-state-model-summary.md"], result.summary)
    write_text(paths["current-state-review-checklist.md"], result.checklist)

    logger.info(
        "M3.6 产物已写出：%s",
        "，".join(_display_path(paths[name]) for name in OUTPUT_FILES),
    )

    return tuple(paths[name] for name in OUTPUT_FILES)


def run_current_state_model_analysis(
    *,
    analysis_dir: Path,
    output_dir: Path,
) -> CurrentStateModelResult:
    """执行 M3.6 Current-State Model Review 并写出产物。

    只读 M2 / M3 / M3.5 产物；输入缺失时直接报错，
    不自动回退去跑前置阶段。
    """

    # 旧布局把 M3.6 产物写在 business/：先清理遗留文件（两份清单搬迁保留人工列），
    # 保证同一阶段的产物只存在于 output_dir。
    relocate_legacy_artifacts(
        analysis_dir,
        output_dir,
        legacy_dir="business",
        output_files=(*LEGACY_OUTPUT_FILES, *PROBLEM_OUTPUT_FILES),
        carryover_files=(
            Path(CARRYOVER_CHECKLIST_INPUT_FILE).name,
            Path(PROBLEM_CARRYOVER_FILE).name,
        ),
    )

    inputs = read_review_inputs(analysis_dir)
    result = build_current_state_model(inputs)
    result.analysis_dir = analysis_dir

    write_current_state_model(result, output_dir)

    # M3.6 v2：在同一次运行里把 finding 聚合成 problem candidate 并写出四个新产物。
    # 局部导入避免 problem_assessment → model_review 的循环依赖。
    from .problems import (
        build_current_state_problems,
        read_problem_carry_over,
        write_current_state_problems,
    )

    problem_result = build_current_state_problems(
        inputs,
        result.findings["findings"],
        result.tables["tables"],
        carry_over=read_problem_carry_over(analysis_dir),
    )
    problem_result.analysis_dir = analysis_dir
    write_current_state_problems(problem_result, output_dir)
    result.problem = problem_result

    priority_text = "，".join(f"{key}={value}" for key, value in result.priority_counts.items())
    problem_status_text = "，".join(
        f"{key}={value}" for key, value in problem_result.status_counts.items()
    )

    logger.info(
        "M3.6 Current-State Model Review 完成：table=%s，finding=%s（%s）；"
        "M3.6 v2 Problem Assessment 完成：problem=%s（%s）",
        result.table_count,
        result.finding_count,
        priority_text,
        problem_result.problem_count,
        problem_status_text,
    )

    return result

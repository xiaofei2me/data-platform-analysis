"""M3.4 Grain Candidate Analysis。

目标：

    从 M3.3 的 Process Candidate 与 M2 / M3 的列、SQL、血缘、Profiling 证据里
    识别「Grain Candidate」——某个 process 在某张表上「一行代表什么」的候选。

    Grain Candidate
          ├── candidate_keys（真实存在的字段；可为空，空 = 证据不足）
          ├── grain_pattern（transaction / snapshot / event / periodic /
          │                   aggregation / unknown）
          ├── strength（证据源多样性：weak / moderate / strong）
          ├── evidence（可回溯到 source_type / source_id 的证据条目）
          ├── unresolved_reasons（no_identifier_signal / multiple_possible_keys /
          │                       missing_sql_evidence / missing_lineage_evidence /
          │                       time_semantics_unclear / aggregation_level_unclear /
          │                       insufficient_evidence）
          └── status（恒为 candidate，机器阶段不产出 confirmed grain）

输入（只读 analysis/ 与 config/ 之外的产物，不读 source/，不调 API，
不修改 M2 / M3 / M3.1 / M3.2 / M3.3 产物）：

    analysis/business/process-signals.json
    analysis/business/processes.json
    analysis/business/process-tables.json
    analysis/business/process-objects.json
    analysis/business/objects-registry.json
    analysis/business/object-tables.json
    analysis/business/object-relationships.json
    analysis/inventory/tables.json
    analysis/inventory/columns.json
    analysis/sql/statements.json
    analysis/sql/table-references.json
    analysis/lineage/table-lineage.json
    analysis/lineage/core-table-candidates.json
    analysis/profiling/tables.json
    analysis/profiling/columns.json
    analysis/business/process-review-checklist.md   （可选：Process 人工确认状态）
    analysis/business/grain-review-checklist.md     （可选：本阶段清单的人工回填）

输出：

    analysis/business/grain-signals.json
    analysis/business/grain-candidates.json
    analysis/business/grain-tables.json
    analysis/business/grain-summary.md
    analysis/business/grain-review-checklist.md

原则：

1. Grain Signal ≠ Grain Candidate：identifier / time / measure / snapshot /
   event / periodic / aggregation 只是字段或表上的形态信号，命中信号不等于
   识别出一个 grain。
2. Grain Candidate ≠ Confirmed Grain：status 恒为 candidate；Process 的
   human_validated 不向 Grain 传递，机器阶段不产出 confirmed grain。
3. 候选键必须是 inventory/columns.json 里真实存在的字段：不存在的字段
   不能进入 candidate_keys，也不能成为 supporting 表的判定依据。
4. 不做笛卡尔积：每个 (process, table) 按证据形态级联取一种展开方式，
   优先事务证据，其次 Object × 时间，再到快照 / 周期 / 事件；
   宁可少生成候选，也不生成无法解释的键组合。
5. 多候选全保留：一个表可能有多个候选键组合，全部输出并标记
   multiple_possible_keys，不挑 winner、不打分、不排序取一。
6. 不伪造唯一性：Profiling 只有 metadata_only，is_candidate_key 全为 false，
   因此候选键没有任何行级唯一性证明，strength 只反映证据源多样性。
7. 不命名事实表 / 维度表：grain-tables 的 role 只用技术含义
   （anchor / supporting），core_candidate 只作证据覆盖与复核优先级。
8. 输出 deterministic：无时间戳 / UUID / 随机抽样，全部稳定排序。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT
from ..io_utils import ensure_dir, write_json, write_text
from .business_objects import (
    _string_list,
    _table_sort_key,
    _text,
    _workspace_projects,
)
from .business_understanding import tokenize_identifier
from .models import (
    EVIDENCE_STRENGTH_ORDER,
    EVIDENCE_STRENGTH_WEAK,
    GRAIN_CANDIDATE_NOTE,
    GRAIN_CHECKLIST_ROW_LIMIT,
    GRAIN_EVIDENCE_COLUMN,
    GRAIN_EVIDENCE_LINEAGE,
    GRAIN_EVIDENCE_OBJECT,
    GRAIN_EVIDENCE_OBJECT_RELATIONSHIP,
    GRAIN_EVIDENCE_ORDER,
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
    GRAIN_SIGNAL_AGGREGATION,
    GRAIN_SIGNAL_EVENT,
    GRAIN_SIGNAL_EXAMPLE_LIMIT,
    GRAIN_SIGNAL_IDENTIFIER,
    GRAIN_SIGNAL_MEASURE,
    GRAIN_SIGNAL_PERIODIC,
    GRAIN_SIGNAL_SNAPSHOT,
    GRAIN_SIGNAL_TIME,
    GRAIN_SIGNAL_TYPE_ORDER,
    GRAIN_STATUS_CANDIDATE,
    GRAIN_STATUS_ORDER,
    GRAIN_UNRESOLVED_AGGREGATION,
    GRAIN_UNRESOLVED_INSUFFICIENT,
    GRAIN_UNRESOLVED_LINEAGE,
    GRAIN_UNRESOLVED_MULTIPLE_KEYS,
    GRAIN_UNRESOLVED_NO_IDENTIFIER,
    GRAIN_UNRESOLVED_ORDER,
    GRAIN_UNRESOLVED_SQL,
    GRAIN_UNRESOLVED_TIME,
    PROCESS_SIGNAL_EVENT_TIME,
    PROCESS_SIGNAL_STATUS,
    PROCESS_SIGNAL_TRANSACTION_ID,
    PROCESS_SIGNAL_TRANSACTION_MEASURE,
    PROCESS_SIGNAL_TYPE_ORDER,
    BusinessGrainResult,
    evidence_strength,
)
from .naming import qualify_table_ref
from .reports import render_grain_review_checklist, render_grain_summary

logger = logging.getLogger(__name__)

# ============================================================
# 输入与输出布局
# ============================================================

ARRAY_INPUT_FILES: tuple[tuple[str, str, str], ...] = (
    ("business/process-signals.json", "signals", "process_signals"),
    ("business/processes.json", "processes", "processes"),
    ("business/process-tables.json", "tables", "process_tables"),
    ("business/process-objects.json", "objects", "process_objects"),
    ("business/objects-registry.json", "objects", "registry_objects"),
    ("business/object-tables.json", "associations", "associations"),
    ("business/object-relationships.json", "relationships", "relationships"),
    ("inventory/tables.json", "tables", "inventory_tables"),
    ("inventory/columns.json", "columns", "columns"),
    ("sql/statements.json", "statements", "statements"),
    ("sql/table-references.json", "references", "references"),
    ("lineage/table-lineage.json", "edges", "edges"),
    ("lineage/core-table-candidates.json", "candidates", "core_candidates"),
    ("profiling/tables.json", "tables", "profile_tables"),
    ("profiling/columns.json", "columns", "profile_columns"),
)
"""M3.4 依赖的数组型 M2 / M3 产物（相对 analysis/ 路径 → JSON 数组字段名 → 属性名）。"""

PROCESS_CHECKLIST_INPUT_FILE = "business/process-review-checklist.md"
"""M3.3 人工确认清单（可选输入）：只用于记录 Process 是否已被人工确认。"""

CARRYOVER_CHECKLIST_INPUT_FILE = "business/grain-review-checklist.md"
"""本阶段清单（可选输入）：回填过的人工确认在重跑时被带回去。"""

INPUT_FILES: tuple[str, ...] = tuple(
    relative for relative, _key, _attr in ARRAY_INPUT_FILES
)
"""M3.4 的必需输入（相对 analysis/ 路径）；两个 markdown 清单属于可选输入。"""

OUTPUT_FILES: tuple[str, ...] = (
    "grain-signals.json",
    "grain-candidates.json",
    "grain-tables.json",
    "grain-summary.md",
    "grain-review-checklist.md",
)
"""M3.4 产物文件名（固定顺序）；只覆盖这五个文件，不动已有 M2 / M3 产物。"""

PROCESS_CHECKLIST_REQUIRED_COLUMNS: tuple[str, ...] = ("process_key", "confirmed")
"""process-review-checklist.md 必须包含的列，缺一即报错。"""

GRAIN_CHECKLIST_REQUIRED_COLUMNS: tuple[str, ...] = (
    "grain_candidate_id",
    "confirmed",
    "note",
)
"""grain-review-checklist.md 回填列：缺一即报错（其余列由机器生成）。"""

GRAIN_SUPPORTING_ROW_LIMIT = 5
"""grain-tables.json 中每个 candidate 最多列出的 supporting 表数量。"""

_TRUE_VALUES: frozenset[str] = frozenset({"true", "yes", "y", "1", "confirmed", "是"})

# ============================================================
# 字段名形态 token（模块常量，不进 config：只影响候选生成，不是业务规则）
# ============================================================

IDENTIFIER_TOKENS: frozenset[str] = frozenset(
    {"id", "no", "number", "key", "code", "guid", "uuid"}
)
"""字段名最后一个 token 命中即视为标识形态（例如 order_id / batch_no）。"""

IDENTIFIER_NAMES: frozenset[str] = frozenset({"id", "guid", "uuid"})
"""整体等于这些名字的字段也算标识形态。"""

TIME_TOKENS: frozenset[str] = frozenset(
    {"date", "time", "day", "dt", "ds", "ymd", "datetime", "timestamp"}
)
"""字段名含这些 token 即视为时间形态（例如 order_date / update_time / ds）。"""

PERIODIC_TOKENS: frozenset[str] = frozenset(
    {
        "month",
        "months",
        "mo",
        "year",
        "years",
        "yr",
        "quarter",
        "week",
        "weeks",
        "period",
        "periods",
        "cycle",
    }
)
"""字段名含这些 token 即视为周期形态（例如 month_id / quarter_key）。"""

SNAPSHOT_TOKENS: frozenset[str] = frozenset({"snapshot", "snap"})
"""字段名含这些 token 即视为快照形态。"""

EVENT_TOKENS: frozenset[str] = frozenset({"event", "events"})
"""字段名含这些 token 即视为事件形态。"""

_FLAG_TXN = "txn"
_FLAG_IDENTIFIER = "identifier"
_FLAG_TIME = "time"
_FLAG_MEASURE = "measure"
_FLAG_STATUS = "status"
_FLAG_SNAPSHOT = "snapshot"
_FLAG_PERIODIC = "periodic"
_FLAG_EVENT = "event"
_FLAG_PARTITION = "partition"
"""列级形态标记（内部使用，不写入产物）。"""

_TIME_EVIDENCE_FLAGS: frozenset[str] = frozenset(
    {_FLAG_PARTITION, _FLAG_PERIODIC, _FLAG_SNAPSHOT, _FLAG_EVENT}
)
"""让时间字段「语义明确」的三类具体证据：分区 / 周期 / 快照 / 事件。"""

_COLUMN_SIGNAL_TYPES: tuple[str, ...] = (
    PROCESS_SIGNAL_TRANSACTION_ID,
    PROCESS_SIGNAL_TRANSACTION_MEASURE,
    PROCESS_SIGNAL_EVENT_TIME,
    PROCESS_SIGNAL_STATUS,
)
"""来自 process-signals.json 的列级信号类型。"""


_FLAG_BY_GRAIN_SIGNAL: dict[str, str] = {
    GRAIN_SIGNAL_IDENTIFIER: _FLAG_IDENTIFIER,
    GRAIN_SIGNAL_TIME: _FLAG_TIME,
    GRAIN_SIGNAL_MEASURE: _FLAG_MEASURE,
    GRAIN_SIGNAL_SNAPSHOT: _FLAG_SNAPSHOT,
    GRAIN_SIGNAL_EVENT: _FLAG_EVENT,
    GRAIN_SIGNAL_PERIODIC: _FLAG_PERIODIC,
}
"""列级 Grain Signal → 形态标记（aggregation 是表级信号，不在此表里）。"""

_TOKENS_BY_GRAIN_SIGNAL: dict[str, frozenset[str]] = {
    GRAIN_SIGNAL_IDENTIFIER: IDENTIFIER_TOKENS,
    GRAIN_SIGNAL_TIME: TIME_TOKENS,
    GRAIN_SIGNAL_PERIODIC: PERIODIC_TOKENS,
    GRAIN_SIGNAL_SNAPSHOT: SNAPSHOT_TOKENS,
    GRAIN_SIGNAL_EVENT: EVENT_TOKENS,
}
"""形态 token 集合：signal 文案与 reason 用它解释字段名证据。"""

_PROCESS_SIGNAL_BY_GRAIN_SIGNAL: dict[str, str] = {
    GRAIN_SIGNAL_IDENTIFIER: PROCESS_SIGNAL_TRANSACTION_ID,
    GRAIN_SIGNAL_MEASURE: PROCESS_SIGNAL_TRANSACTION_MEASURE,
    GRAIN_SIGNAL_TIME: PROCESS_SIGNAL_EVENT_TIME,
}
"""Grain Signal 对应的 M3.3 process signal 类型（其余形态没有规则文本）。"""


class BusinessGrainError(RuntimeError):
    """M3.4 无法继续的输入 / 结构错误。"""


def _display_path(path: Path) -> str:
    """日志与报告中展示的路径：项目根内用相对路径，其余保持绝对。"""

    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))

    except ValueError:
        return str(path)


# ============================================================
# 通用小工具
# ============================================================


def _status_counts(values: Sequence[str], order: Sequence[str]) -> dict[str, int]:
    """按固定顺序输出计数（缺项补 0，未登记值排最后）。"""

    counts = {value: 0 for value in order}

    for value in values:
        counts[value] = counts.get(value, 0) + 1

    return counts


def _dict_values(records: Any, key: str, path: Path) -> list[dict[str, Any]]:
    """校验并取出 JSON 数组里的对象条目。"""

    if not isinstance(records, list):
        raise BusinessGrainError(f"缺少 {key} 数组：{path}")

    items: list[dict[str, Any]] = []

    for position, entry in enumerate(records):
        if not isinstance(entry, dict):
            raise BusinessGrainError(f"{key}[{position}] 不是对象：{path}")

        items.append(entry)

    return items


def _rank(value: str, order: Sequence[str]) -> int:
    """固定顺序里的位置；未登记值排最后。"""

    try:
        return order.index(value)

    except ValueError:
        return len(order)


def _confirmed_flag(value: str) -> bool:
    return (value or "").strip().casefold() in _TRUE_VALUES


def _example_list(values: Sequence[str]) -> str:
    """reason 里列出的字段示例：最多 GRAIN_SIGNAL_EXAMPLE_LIMIT 个 + 总数。"""

    ordered = sorted(values)

    if len(ordered) <= GRAIN_SIGNAL_EXAMPLE_LIMIT:
        return "、".join(ordered)

    return (
        f"{'、'.join(ordered[:GRAIN_SIGNAL_EXAMPLE_LIMIT])}"
        f" 等 {len(ordered)} 个字段"
    )


# ============================================================
# M2 / M3 产物读取
# ============================================================


@dataclass
class GrainInputs:
    """M3.4 读取到的 M2 / M3 产物（只做结构校验，不改写）。"""

    process_signals: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    process_tables: list[dict[str, Any]] = field(default_factory=list)
    process_objects: list[dict[str, Any]] = field(default_factory=list)
    registry_objects: list[dict[str, Any]] = field(default_factory=list)
    associations: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    inventory_tables: list[dict[str, Any]] = field(default_factory=list)
    columns: list[dict[str, Any]] = field(default_factory=list)
    statements: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    core_candidates: list[dict[str, Any]] = field(default_factory=list)
    profile_tables: list[dict[str, Any]] = field(default_factory=list)
    profile_columns: list[dict[str, Any]] = field(default_factory=list)
    process_checklist_text: str = ""
    process_checklist_path: Path = field(default_factory=Path)
    carryover_text: str = ""
    carryover_path: Path = field(default_factory=Path)
    analysis_dir: Path = field(default_factory=Path)


def read_grain_inputs(analysis_dir: Path) -> GrainInputs:
    """读取 M3.4 依赖的全部 M2 / M3 / M3.3 产物。

    任何必需输入缺失或 JSON 非法都明确报错，
    不自动回退执行 analyze / analyze-business / analyze-business-objects /
    analyze-business-processes。
    """

    missing = [
        relative for relative in INPUT_FILES if not (analysis_dir / relative).exists()
    ]

    if missing:
        raise BusinessGrainError(
            "M2 / M3 / M3.3 产物缺失，无法执行 M3.4 Grain Candidate Analysis："
            f"{'、'.join(missing)}（目录：{_display_path(analysis_dir)}）；"
            "请先执行 analyze 生成 M2 产物、analyze-business 生成 M3 产物、"
            "analyze-business-quality 生成 M3.1 产物、"
            "analyze-business-objects 生成 M3.2 产物、"
            "analyze-business-processes 生成 M3.3 产物"
        )

    def load(relative: str, key: str) -> list[dict[str, Any]]:
        path = analysis_dir / relative

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))

        except json.JSONDecodeError as exc:
            raise BusinessGrainError(
                f"产物不是合法的 JSON：{path}（{exc}）"
            ) from exc

        if not isinstance(raw, dict):
            raise BusinessGrainError(f"产物根节点不是对象：{path}")

        return _dict_values(raw.get(key), key, path)

    inputs = GrainInputs()
    inputs.analysis_dir = analysis_dir
    inputs.process_checklist_path = analysis_dir / PROCESS_CHECKLIST_INPUT_FILE
    inputs.carryover_path = analysis_dir / CARRYOVER_CHECKLIST_INPUT_FILE

    for relative, key, attr in ARRAY_INPUT_FILES:
        setattr(inputs, attr, load(relative, key))

    if inputs.process_checklist_path.exists():
        try:
            inputs.process_checklist_text = inputs.process_checklist_path.read_text(
                encoding="utf-8"
            )

        except OSError as exc:
            raise BusinessGrainError(
                f"无法读取 process review 清单：{inputs.process_checklist_path}（{exc}）"
            ) from exc

    if inputs.carryover_path.exists():
        try:
            inputs.carryover_text = inputs.carryover_path.read_text(encoding="utf-8")

        except OSError as exc:
            raise BusinessGrainError(
                f"无法读取 grain review 清单：{inputs.carryover_path}（{exc}）"
            ) from exc

    logger.info(
        "M3.4 输入已读取：%s（process table=%s，column=%s，reference=%s，profile=%s）",
        _display_path(analysis_dir),
        len(inputs.process_tables),
        len(inputs.columns),
        len(inputs.references),
        len(inputs.profile_columns),
    )

    return inputs


# ============================================================
# 人工确认状态（只读，不改变 Grain 的 candidate 状态）
# ============================================================


def _parse_checklist_rows(
    text: str,
    *,
    required: Sequence[str],
    source: Path,
    label: str,
) -> dict[str, dict[str, str]]:
    """解析清单里的 Markdown 表：主键列 → {列名: 单元格文本}。

    文件为空返回 {}；表头存在但缺必需列时报错。
    """

    if not text.strip():
        return {}

    columns: dict[str, int] = {}

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped.startswith("|"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]

        if not cells or cells[0].casefold() != required[0]:
            continue

        missing = [name for name in required if name not in cells]

        if missing:
            raise BusinessGrainError(
                f"{label} 缺少必需列：{'、'.join(missing)}（{source}）"
            )

        columns = {name: position for position, name in enumerate(cells) if name}
        break

    if not columns:
        raise BusinessGrainError(
            f"{label} 找不到 {required[0]} 表头"
            f"（必需列：{'、'.join(required)}）：{source}"
        )

    rows: dict[str, dict[str, str]] = {}
    key_index = columns[required[0]]

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped.startswith("|"):
            continue

        values = [cell.strip() for cell in stripped.strip("|").split("|")]
        key = values[key_index] if key_index < len(values) else ""

        if not key or key.casefold() == required[0] or set(key) <= {"-"}:
            continue

        rows.setdefault(
            key,
            {
                name: values[index] if index < len(values) else ""
                for name, index in columns.items()
            },
        )

    return rows


def _parse_checklist_flags(
    text: str,
    *,
    required: Sequence[str],
    source: Path,
    label: str,
) -> dict[str, bool]:
    """解析清单里的 confirmed 列：主键列 → 是否已确认。"""

    return {
        key: _confirmed_flag(row.get("confirmed", ""))
        for key, row in _parse_checklist_rows(
            text,
            required=required,
            source=source,
            label=label,
        ).items()
    }


# ============================================================
# 索引
# ============================================================


@dataclass
class GrainIndexes:
    """构建候选所需的全部索引（全部只读）。"""

    table_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    table_comment: dict[str, str | None] = field(default_factory=dict)
    columns_by_table: dict[str, tuple[ColumnFacts, ...]] = field(default_factory=dict)
    column_signals: dict[tuple[str, str], tuple[tuple[str, str], ...]] = field(
        default_factory=dict
    )
    table_signal_columns: dict[str, dict[str, tuple[str, ...]]] = field(
        default_factory=dict
    )
    process_objects: dict[str, tuple[str, ...]] = field(default_factory=dict)
    object_status: dict[str, str] = field(default_factory=dict)
    associations: dict[str, dict[str, str]] = field(default_factory=dict)
    relationships: dict[tuple[str, str], str] = field(default_factory=dict)
    sql_refs: dict[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    lineage_refs: dict[str, tuple[tuple[int, str, str], ...]] = field(
        default_factory=dict
    )
    lineage_tables: set[str] = field(default_factory=set)
    core_keys: set[str] = field(default_factory=set)
    process_tables_by_process: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    process_validated: dict[str, bool] = field(default_factory=dict)
    profiling: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ColumnFacts:
    """一个字段的形态事实（name + 注释 + 形态标记）。"""

    name: str
    ordinal: int
    comment: str | None
    flags: frozenset[str]

    @property
    def folded(self) -> str:
        return self.name.casefold()

    def has(self, flag: str) -> bool:
        return flag in self.flags


def _column_flags(
    name: str,
    signal_types: Sequence[str],
    is_partition: bool,
) -> frozenset[str]:
    """一个字段的形态标记：M3.3 信号 + 字段名形态 + 分区标记。"""

    folded = name.casefold()
    tokens = {token.casefold() for token in tokenize_identifier(name)}
    flags: set[str] = set()

    if PROCESS_SIGNAL_TRANSACTION_ID in signal_types:
        flags.add(_FLAG_TXN)
        flags.add(_FLAG_IDENTIFIER)

    if PROCESS_SIGNAL_TRANSACTION_MEASURE in signal_types:
        flags.add(_FLAG_MEASURE)

    if PROCESS_SIGNAL_EVENT_TIME in signal_types:
        flags.add(_FLAG_TIME)

    if PROCESS_SIGNAL_STATUS in signal_types:
        flags.add(_FLAG_STATUS)

    if tokens:
        if tokens & IDENTIFIER_TOKENS or folded in IDENTIFIER_NAMES:
            flags.add(_FLAG_IDENTIFIER)

        if tokens & TIME_TOKENS or tokens & PERIODIC_TOKENS or tokens & SNAPSHOT_TOKENS:
            flags.add(_FLAG_TIME)

        if tokens & PERIODIC_TOKENS:
            flags.add(_FLAG_PERIODIC)

        if tokens & SNAPSHOT_TOKENS:
            flags.add(_FLAG_SNAPSHOT)

        if tokens & EVENT_TOKENS:
            flags.add(_FLAG_EVENT)

    if is_partition:
        flags.add(_FLAG_PARTITION)

    return frozenset(flags)


def _index_process_signals(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[
    dict[tuple[str, str], tuple[tuple[str, str], ...]],
    dict[str, dict[str, tuple[str, ...]]],
]:
    """(table_key(casefold), column) → 列级信号；table_key → 信号类型 → 字段列表。"""

    column_signals: dict[tuple[str, str], list[tuple[str, str]]] = {}
    table_signals: dict[str, dict[str, set[str]]] = {}

    for row in sorted(rows, key=lambda item: (
        str(item.get("table_key") or "").casefold(),
        str(item.get("column_name") or ""),
        _rank(str(item.get("signal_type") or ""), PROCESS_SIGNAL_TYPE_ORDER),
    )):
        folded = str(row.get("table_key") or "").casefold()
        signal_type = str(row.get("signal_type") or "")
        column_name = _text(row.get("column_name"))

        if not folded or signal_type not in _COLUMN_SIGNAL_TYPES or not column_name:
            continue

        column_signals.setdefault((folded, column_name), []).append(
            (signal_type, str(row.get("signal") or ""))
        )
        table_signals.setdefault(folded, {}).setdefault(signal_type, set()).add(
            column_name
        )

    frozen_columns = {
        key: tuple(
            sorted(
                set(hits),
                key=lambda item: (
                    _rank(item[0], PROCESS_SIGNAL_TYPE_ORDER),
                    item[1],
                ),
            )
        )
        for key, hits in column_signals.items()
    }
    frozen_tables = {
        folded: {
            signal_type: tuple(sorted(columns))
            for signal_type, columns in sorted(
                by_type.items(),
                key=lambda item: _rank(item[0], PROCESS_SIGNAL_TYPE_ORDER),
            )
        }
        for folded, by_type in table_signals.items()
    }

    return frozen_columns, frozen_tables


def _index_columns(
    columns: Sequence[Mapping[str, Any]],
    wanted: set[str],
    column_signals: Mapping[tuple[str, str], Sequence[tuple[str, str]]],
) -> dict[str, tuple[ColumnFacts, ...]]:
    """只保留 process 表的字段形态（按 ordinal + 字段名稳定排序）。"""

    grouped: dict[str, list[ColumnFacts]] = {}

    for record in sorted(columns, key=_table_column_sort_key):
        folded = str(record.get("table_key") or "").casefold()

        if folded not in wanted:
            continue

        name = _text(record.get("column_name"))

        if not name:
            continue

        ordinal = record.get("ordinal")
        signal_types = [
            signal_type
            for signal_type, _signal in column_signals.get((folded, name), ())
        ]
        flags = _column_flags(
            name,
            signal_types,
            bool(record.get("is_partition")),
        )

        grouped.setdefault(folded, []).append(
            ColumnFacts(
                name=name,
                ordinal=ordinal if isinstance(ordinal, int) else 0,
                comment=_text(record.get("comment")),
                flags=flags,
            )
        )

    return {folded: tuple(items) for folded, items in grouped.items()}


def _table_column_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    ordinal = record.get("ordinal")

    return (
        str(record.get("table_key") or "").casefold(),
        ordinal if isinstance(ordinal, int) else 0,
        str(record.get("column_name") or ""),
    )


def _index_table_meta(
    process_tables: Sequence[Mapping[str, Any]],
    inventory_tables: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, str | None]]:
    """process 表的展示元数据 + inventory 的表注释。"""

    meta: dict[str, dict[str, Any]] = {}

    for record in sorted(process_tables, key=_table_sort_key):
        key = _text(record.get("table_key"))

        if not key:
            continue

        meta.setdefault(
            key.casefold(),
            {
                "table_key": key,
                "table_name": _text(record.get("table_name")) or key,
                "workspace_id": record.get("workspace_id"),
                "project": _text(record.get("project")) or "",
                "core_candidate": bool(record.get("core_candidate")),
            },
        )

    comments: dict[str, str | None] = {}

    for record in sorted(inventory_tables, key=_table_sort_key):
        key = _text(record.get("table_key"))

        if not key:
            continue

        comments.setdefault(key.casefold(), _text(record.get("comment")))

    return meta, comments


def _index_sql_refs(
    references: Sequence[Mapping[str, Any]],
    workspace_projects: Mapping[int, str],
) -> dict[str, tuple[dict[str, Any], ...]]:
    """table_key(casefold) → 被引用的语句（稳定排序，含 file_name / statement_id）。"""

    grouped: dict[str, set[tuple[int, str, int, str]]] = {}

    for record in references:
        workspace_id = record.get("workspace_id")
        project = workspace_projects.get(workspace_id) if isinstance(workspace_id, int) else None
        raw_statement_id = record.get("statement_id")
        statement_id = (
            raw_statement_id if isinstance(raw_statement_id, int) else 0
        )
        identity = (
            workspace_id if isinstance(workspace_id, int) else 0,
            str(record.get("file_id") or ""),
            statement_id,
            str(record.get("file_name") or ""),
        )

        for field_name in ("source_tables", "target_tables"):
            for item in _string_list(record.get(field_name)):
                folded = qualify_table_ref(item, project).casefold()
                grouped.setdefault(folded, set()).add(identity)

    return {
        folded: tuple(
            {
                "workspace_id": workspace_id,
                "file_id": file_id,
                "statement_id": statement_id,
                "file_name": file_name,
            }
            for workspace_id, file_id, statement_id, file_name in sorted(items)
        )
        for folded, items in grouped.items()
    }


def _index_lineage_refs(
    edges: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[tuple[int, str, str], ...]]:
    """table_key(casefold) → 参与的血缘边（稳定排序去重）。"""

    grouped: dict[str, set[tuple[int, str, str]]] = {}

    for record in edges:
        workspace_id = record.get("workspace_id")
        identity = (
            workspace_id if isinstance(workspace_id, int) else 0,
            str(record.get("source_key") or record.get("source_table") or ""),
            str(record.get("target_key") or record.get("target_table") or ""),
        )
        target = _text(record.get("target_key")) or _text(record.get("target_table"))
        source = _text(record.get("source_key")) or _text(record.get("source_table"))

        if source:
            grouped.setdefault(source.casefold(), set()).add(identity)

        if target:
            grouped.setdefault(target.casefold(), set()).add(identity)

    return {folded: tuple(sorted(items)) for folded, items in grouped.items()}


def _index_associations(
    associations: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    """table_key(casefold) → Object → association status（M3.2 关联）。"""

    index: dict[str, dict[str, str]] = {}

    for record in sorted(
        associations,
        key=lambda item: (
            str(item.get("table_key") or "").casefold(),
            str(item.get("object") or ""),
        ),
    ):
        key = _text(record.get("table_key"))
        obj = _text(record.get("object"))

        if not key or not obj:
            continue

        index.setdefault(key.casefold(), {})[obj] = str(
            record.get("status") or GRAIN_STATUS_CANDIDATE
        )

    return index


def _index_relationships(
    relationships: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], str]:
    """排序 Object 对 → relationship evidence_strength。"""

    index: dict[tuple[str, str], str] = {}

    for record in relationships:
        left = _text(record.get("object_a"))
        right = _text(record.get("object_b"))

        if not left or not right:
            continue

        index[(left, right)] = str(record.get("evidence_strength") or "")

    return index


def _index_core_keys(
    core_candidates: Sequence[Mapping[str, Any]],
    process_tables: Sequence[Mapping[str, Any]],
) -> set[str]:
    """core 表候选（M2.4 ∪ M3.3 process-tables 标记）；只作证据覆盖与复核优先级。"""

    keys = {
        key.casefold()
        for record in core_candidates
        if (key := _text(record.get("table_key")))
    }

    for record in process_tables:
        if record.get("core_candidate") and (key := _text(record.get("table_key"))):
            keys.add(key.casefold())

    return keys


def _profiling_stats(
    profile_tables: Sequence[Mapping[str, Any]],
    profile_columns: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Profiling 证据可用性统计（metadata-only，用于 limitations）。"""

    candidate_key_count = sum(
        1 for record in profile_columns if record.get("is_candidate_key")
    )

    return {
        "table_count": len(profile_tables),
        "column_count": len(profile_columns),
        "candidate_key_count": candidate_key_count,
        "metadata_only_column_count": sum(
            1 for record in profile_columns if record.get("profile_status") == "metadata_only"
        ),
        "data_sample_table_count": sum(
            1 for record in profile_tables if record.get("data_sample_available")
        ),
    }


def build_indexes(inputs: GrainInputs) -> GrainIndexes:
    """把 M3.4 输入整理成只读索引。"""

    table_meta, table_comment = _index_table_meta(
        inputs.process_tables, inputs.inventory_tables
    )
    column_signals, table_signal_columns = _index_process_signals(inputs.process_signals)

    process_folds = set(table_meta)
    columns_by_table = _index_columns(
        inputs.columns, process_folds, column_signals
    )

    process_objects: dict[str, set[str]] = {}

    for record in sorted(
        inputs.process_objects,
        key=lambda item: (
            str(item.get("process_key") or ""),
            str(item.get("object") or ""),
        ),
    ):
        key = _text(record.get("process_key"))
        obj = _text(record.get("object"))

        if key and obj:
            process_objects.setdefault(key, set()).add(obj)

    process_tables_by_process: dict[str, set[str]] = {}

    for record in inputs.process_tables:
        key = _text(record.get("process_key"))
        table = _text(record.get("table_key"))

        if key and table:
            process_tables_by_process.setdefault(key, set()).add(table)

    workspace_projects = _workspace_projects(inputs.inventory_tables)
    sql_refs = _index_sql_refs(inputs.references, workspace_projects)
    lineage_refs = _index_lineage_refs(inputs.edges)

    process_validated = {
        str(record.get("process_key") or ""): bool(record.get("human_validated"))
        for record in inputs.processes
    }

    for key, confirmed in _parse_checklist_flags(
        inputs.process_checklist_text,
        required=("process_key", "confirmed"),
        source=inputs.process_checklist_path,
        label="process-review-checklist.md",
    ).items():
        process_validated[key] = process_validated.get(key, False) or confirmed

    return GrainIndexes(
        table_meta=table_meta,
        table_comment=table_comment,
        columns_by_table=columns_by_table,
        column_signals=column_signals,
        table_signal_columns=table_signal_columns,
        process_objects={key: tuple(sorted(values)) for key, values in process_objects.items()},
        object_status={
            str(record.get("object") or ""): str(
                record.get("status") or GRAIN_STATUS_CANDIDATE
            )
            for record in inputs.registry_objects
        },
        associations=_index_associations(inputs.associations),
        relationships=_index_relationships(inputs.relationships),
        sql_refs=sql_refs,
        lineage_refs=lineage_refs,
        lineage_tables=set(lineage_refs),
        core_keys=_index_core_keys(inputs.core_candidates, inputs.process_tables),
        process_tables_by_process={
            key: tuple(sorted(values, key=str.casefold))
            for key, values in process_tables_by_process.items()
        },
        process_validated=process_validated,
        profiling=_profiling_stats(inputs.profile_tables, inputs.profile_columns),
    )


# ============================================================
# Grain Signal
# ============================================================


def _grain_signal_reason(
    signal_type: str,
    column_name: str,
    signal_text: str,
) -> tuple[str, str]:
    """(signal 值, reason 文案)：说明这个字段为什么有该类信号。

    优先用 M3.3 的 process signal 规则文本；没有规则命中时用字段名形态 token。
    """

    if signal_text:
        return signal_text, (
            f"M3.3 process signal {signal_text} 命中字段 {column_name}"
        )

    tokens = {
        token.casefold() for token in tokenize_identifier(column_name)
    } | ({column_name.casefold()} if column_name.casefold() in IDENTIFIER_NAMES else set())
    token_set = _TOKENS_BY_GRAIN_SIGNAL.get(signal_type)
    matched = sorted(tokens & token_set) if token_set else []

    if matched:
        label = "、".join(matched)
        return label, f"字段名含 {signal_type} 形态 token：{label}"

    folded = column_name.casefold()

    if folded in IDENTIFIER_NAMES:
        return folded, f"字段名整体为标识形态：{folded}"

    return column_name, f"字段名形态命中 {signal_type} 信号"


def _column_grain_signals(
    folded: str,
    columns: Sequence[ColumnFacts],
    column_signals: Mapping[tuple[str, str], Sequence[tuple[str, str]]],
    meta: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """列级 Grain Signal 行（identifier / time / measure / snapshot / event / periodic）。"""

    rows: list[dict[str, Any]] = []
    table_key = str(meta.get("table_key") or folded)

    for column in sorted(columns, key=lambda item: (item.ordinal, item.name)):
        hits = dict(column_signals.get((folded, column.name), ()))

        for signal_type in GRAIN_SIGNAL_TYPE_ORDER:
            if signal_type == GRAIN_SIGNAL_AGGREGATION:
                continue

            flag = _FLAG_BY_GRAIN_SIGNAL.get(signal_type)

            if flag is None or flag not in column.flags:
                continue

            signal_value, reason = _grain_signal_reason(
                signal_type,
                column.name,
                hits.get(_PROCESS_SIGNAL_BY_GRAIN_SIGNAL.get(signal_type, ""), ""),
            )

            rows.append(
                {
                    "signal_type": signal_type,
                    "signal": signal_value,
                    "table_key": table_key,
                    "table_name": meta.get("table_name") or table_key,
                    "workspace_id": meta.get("workspace_id"),
                    "project": meta.get("project") or "",
                    "column_name": column.name,
                    "source": "column",
                    "reason": reason,
                    "evidence": [
                        {
                            "source_type": GRAIN_EVIDENCE_COLUMN,
                            "source_id": f"{table_key}.{column.name}",
                            "workspace_id": meta.get("workspace_id"),
                            "table_key": table_key,
                            "column_name": column.name,
                            "reason": reason,
                        }
                    ],
                }
            )

    return rows


def _table_grain_signals(
    folded: str,
    table_signal_columns: Mapping[str, Mapping[str, Sequence[str]]],
    columns: Sequence[ColumnFacts],
    meta: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """表级 aggregation 信号：有度量信号、没有事务标识信号。"""

    hits = table_signal_columns.get(folded, {})
    measure_columns = list(hits.get(PROCESS_SIGNAL_TRANSACTION_MEASURE, ()))

    if not measure_columns or PROCESS_SIGNAL_TRANSACTION_ID in hits:
        return []

    table_key = str(meta.get("table_key") or folded)
    reason = (
        "表上有度量信号（transaction_measure）但没有事务标识信号"
        f"（transaction_id）：{_example_list(measure_columns)}"
    )

    return [
        {
            "signal_type": GRAIN_SIGNAL_AGGREGATION,
            "signal": "measure_without_transaction",
            "table_key": table_key,
            "table_name": meta.get("table_name") or table_key,
            "workspace_id": meta.get("workspace_id"),
            "project": meta.get("project") or "",
            "column_name": None,
            "source": "table",
            "reason": reason,
            "evidence": [
                {
                    "source_type": GRAIN_EVIDENCE_TABLE,
                    "source_id": table_key,
                    "workspace_id": meta.get("workspace_id"),
                    "table_key": table_key,
                    "column_name": None,
                    "reason": reason,
                }
            ],
        }
    ]


def _grain_signal_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _rank(str(row.get("signal_type") or ""), GRAIN_SIGNAL_TYPE_ORDER),
        str(row.get("table_key") or "").casefold(),
        str(row.get("column_name") or ""),
        str(row.get("signal") or ""),
    )


def build_grain_signals(
    indexes: GrainIndexes,
    inputs: GrainInputs,
) -> list[dict[str, Any]]:
    """全部 Grain Signal 行（只覆盖 process 表，稳定排序）。"""

    rows: list[dict[str, Any]] = []

    for folded, meta in sorted(indexes.table_meta.items(), key=lambda item: item[0]):
        columns = indexes.columns_by_table.get(folded, ())
        rows.extend(
            _column_grain_signals(folded, columns, indexes.column_signals, meta)
        )
        rows.extend(
            _table_grain_signals(folded, indexes.table_signal_columns, columns, meta)
        )

    return sorted(rows, key=_grain_signal_sort_key)


# ============================================================
# 候选键展开
# ============================================================


def _flag_names(
    columns: Sequence[ColumnFacts],
    flag: str,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            (column.name for column in columns if column.has(flag)),
            key=str.casefold,
        )
    )


def _object_pairs(
    columns: Sequence[ColumnFacts],
    objects: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    """(标识字段, Object) 对：字段 token 精确命中该 process 的 Object。"""

    pairs: set[tuple[str, str]] = set()
    wanted = {obj.casefold(): obj for obj in objects}

    for column in columns:
        if not column.has(_FLAG_IDENTIFIER):
            continue

        tokens = {token.casefold() for token in tokenize_identifier(column.name)}

        for folded, obj in sorted(wanted.items()):
            if folded in tokens:
                pairs.add((column.name, obj))

    return tuple(sorted(pairs, key=lambda item: (item[0].casefold(), item[1])))


def _txn_objects(
    columns: Sequence[ColumnFacts],
    objects: Sequence[str],
) -> set[str]:
    """事务标识字段命中的 Object（这些 Object 不再出现在事务 × Object 组合里）。"""

    matched: set[str] = set()
    wanted = {obj.casefold() for obj in objects}

    for column in columns:
        if not column.has(_FLAG_TXN):
            continue

        matched |= {
            token
            for token in (item.casefold() for item in tokenize_identifier(column.name))
            if token in wanted
        }

    return matched


def _candidate_key_forms(
    folded: str,
    indexes: GrainIndexes,
    process_key: str,
) -> tuple[tuple[str, ...], ...]:
    """候选键组合：每个 (process, table) 只走一种证据形态（级联，不叠加）。"""

    columns = indexes.columns_by_table.get(folded, ())
    objects = indexes.process_objects.get(process_key, ())
    txn_columns = _flag_names(columns, _FLAG_TXN)
    partition_time = tuple(
        sorted(
            (
                column.name
                for column in columns
                if column.has(_FLAG_TIME) and column.has(_FLAG_PARTITION)
            ),
            key=str.casefold,
        )
    )
    time_columns = _flag_names(columns, _FLAG_TIME)
    snapshot_columns = _flag_names(columns, _FLAG_SNAPSHOT)
    periodic_columns = _flag_names(columns, _FLAG_PERIODIC)
    event_id_columns = tuple(
        sorted(
            (
                column.name
                for column in columns
                if column.has(_FLAG_EVENT) and column.has(_FLAG_IDENTIFIER)
            ),
            key=str.casefold,
        )
    )
    pairs = _object_pairs(columns, objects)

    forms: list[tuple[str, ...]] = []

    if txn_columns:
        for column in txn_columns:
            forms.append((column,))

        blocked = _txn_objects(columns, objects)

        for column in txn_columns:
            for name, obj in pairs:
                if obj in blocked:
                    continue

                forms.append(tuple(sorted({column, name})))

        return tuple(forms)

    if pairs and partition_time:
        return tuple(
            tuple(sorted({name, time}))
            for name, _obj in pairs
            for time in partition_time
        )

    if pairs and time_columns:
        return tuple(
            tuple(sorted({name, time}))
            for name, _obj in pairs
            for time in time_columns
        )

    if snapshot_columns:
        return tuple((name,) for name in snapshot_columns)

    if periodic_columns:
        return tuple((name,) for name in periodic_columns)

    if event_id_columns:
        return tuple((name,) for name in event_id_columns)

    return ()


def _grain_pattern(
    keys: Sequence[str],
    columns: Mapping[str, ColumnFacts],
) -> str:
    """候选键 → grain_pattern（只看候选键上的形态证据）。"""

    if not keys:
        return GRAIN_PATTERN_UNKNOWN

    flags = [columns[name].flags for name in keys if name in columns]

    if any(_FLAG_TXN in item for item in flags):
        return GRAIN_PATTERN_TRANSACTION

    if any(_FLAG_SNAPSHOT in item for item in flags):
        return GRAIN_PATTERN_SNAPSHOT

    if any(_FLAG_PERIODIC in item for item in flags):
        return GRAIN_PATTERN_PERIODIC

    if any(_FLAG_EVENT in item for item in flags):
        return GRAIN_PATTERN_EVENT

    if any(_FLAG_TIME in item for item in flags):
        return GRAIN_PATTERN_AGGREGATION

    return GRAIN_PATTERN_UNKNOWN


def _time_semantics_unclear(keys: Sequence[str], columns: Mapping[str, ColumnFacts]) -> bool:
    """候选键里的字段是否只有「名字像时间」这一层证据。"""

    for name in keys:
        column = columns.get(name)

        if column is None:
            continue

        if column.has(_FLAG_TIME) and not (column.flags & _TIME_EVIDENCE_FLAGS):
            return True

    return False


# ============================================================
# 证据
# ============================================================


def _evidence_entry(
    source_type: str,
    source_id: str,
    *,
    workspace_id: Any,
    table_key: str,
    column_name: str | None,
    reason: str,
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "workspace_id": workspace_id,
        "table_key": table_key,
        "column_name": column_name,
        "reason": reason,
    }


def _evidence_sort_key(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _rank(str(entry.get("source_type") or ""), GRAIN_EVIDENCE_ORDER),
        str(entry.get("source_id") or ""),
        str(entry.get("column_name") or ""),
        str(entry.get("reason") or ""),
    )


def _dedupe_evidence(entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}

    for entry in entries:
        key = (
            str(entry.get("source_type") or ""),
            str(entry.get("source_id") or ""),
            str(entry.get("column_name") or ""),
            str(entry.get("reason") or ""),
        )
        seen.setdefault(key, dict(entry))

    return sorted(seen.values(), key=_evidence_sort_key)


def _column_evidence(
    keys: Sequence[str],
    columns: Mapping[str, ColumnFacts],
    *,
    workspace_id: Any,
    table_key: str,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for name in sorted(keys, key=str.casefold):
        column = columns.get(name)

        if column is None:
            continue

        reason = "字段存在于 `inventory/columns.json`"

        if column.comment:
            reason = f"{reason}；字段注释：{column.comment}"

        entries.append(
            _evidence_entry(
                GRAIN_EVIDENCE_COLUMN,
                f"{table_key}.{name}",
                workspace_id=workspace_id,
                table_key=table_key,
                column_name=name,
                reason=reason,
            )
        )

    return entries


def _process_signal_evidence(
    folded: str,
    keys: Sequence[str],
    indexes: GrainIndexes,
    *,
    workspace_id: Any,
    table_key: str,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    covered: set[str] = set()

    for name in sorted(keys, key=str.casefold):
        for signal_type, signal in indexes.column_signals.get((folded, name), ()):
            covered.add(signal_type)
            entries.append(
                _evidence_entry(
                    GRAIN_EVIDENCE_PROCESS_SIGNAL,
                    f"{signal_type}:{table_key}.{name}",
                    workspace_id=workspace_id,
                    table_key=table_key,
                    column_name=name,
                    reason=(
                        f"M3.3 process signal {signal_type}（规则 {signal}）"
                        f"命中候选键字段 {name}"
                    ),
                )
            )

    for signal_type, names in indexes.table_signal_columns.get(folded, {}).items():
        if signal_type in covered or not names:
            continue

        entries.append(
            _evidence_entry(
                GRAIN_EVIDENCE_PROCESS_SIGNAL,
                f"{signal_type}:{table_key}",
                workspace_id=workspace_id,
                table_key=table_key,
                column_name=None,
                reason=f"表上有 {signal_type} 信号：{_example_list(list(names))}",
            )
        )

    return entries


def _object_evidence(
    folded: str,
    keys: Sequence[str],
    indexes: GrainIndexes,
    *,
    workspace_id: Any,
    table_key: str,
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """候选键命中的 Object 证据 + matched_objects。"""

    entries: list[dict[str, Any]] = []
    matched: dict[str, str] = {}
    association = indexes.associations.get(folded, {})

    for name in sorted(keys, key=str.casefold):
        tokens = {token.casefold() for token in tokenize_identifier(name)}

        for obj in sorted(indexes.object_status):
            if obj.casefold() not in tokens or obj not in association:
                continue

            matched[obj] = name
            entries.append(
                _evidence_entry(
                    GRAIN_EVIDENCE_OBJECT,
                    f"object:{obj}",
                    workspace_id=workspace_id,
                    table_key=table_key,
                    column_name=name,
                    reason=(
                        f"候选键字段 {name} 命中 Object {obj}；"
                        f"M3.2 association 显示该表是 {obj} 的候选表"
                        f"（status={association[obj]}）"
                    ),
                )
            )

    objects = tuple(sorted(matched))

    for position, left in enumerate(objects):
        for right in objects[position + 1 :]:
            strength = indexes.relationships.get((left, right))

            if strength is None:
                continue

            entries.append(
                _evidence_entry(
                    GRAIN_EVIDENCE_OBJECT_RELATIONSHIP,
                    f"relationship:{left}-{right}",
                    workspace_id=workspace_id,
                    table_key=table_key,
                    column_name=None,
                    reason=(
                        f"M3.2 关系证据：{left} ↔ {right}"
                        f"（evidence_strength={strength}）"
                    ),
                )
            )

    return entries, objects


def _sql_evidence(
    folded: str,
    indexes: GrainIndexes,
    *,
    workspace_id: Any,
    table_key: str,
) -> list[dict[str, Any]]:
    refs = indexes.sql_refs.get(folded, ())

    if not refs:
        return []

    first = refs[0]
    return [
        _evidence_entry(
            GRAIN_EVIDENCE_SQL,
            (
                f"sql:{first['workspace_id']}:{first['file_id']}"
                f":{first['statement_id']}"
            ),
            workspace_id=workspace_id,
            table_key=table_key,
            column_name=None,
            reason=(
                f"表被 {len(refs)} 条 SQL 语句引用（source/target），"
                f"首条 {first['file_name']}#{first['statement_id']}"
            ),
        )
    ]


def _lineage_evidence(
    folded: str,
    indexes: GrainIndexes,
    *,
    workspace_id: Any,
    table_key: str,
) -> list[dict[str, Any]]:
    edges = indexes.lineage_refs.get(folded, ())

    if not edges:
        return []

    first = edges[0]
    return [
        _evidence_entry(
            GRAIN_EVIDENCE_LINEAGE,
            f"lineage:{first[0]}:{first[1]}->{first[2]}",
            workspace_id=workspace_id,
            table_key=table_key,
            column_name=None,
            reason=f"参与 {len(edges)} 条表级血缘边（source/target）",
        )
    ]


def _build_evidence(
    folded: str,
    keys: Sequence[str],
    indexes: GrainIndexes,
    *,
    workspace_id: Any,
    table_key: str,
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """一个候选的全部证据条目（稳定排序、去重）与 matched_objects。"""

    columns = indexes.columns_by_table.get(folded, ())
    column_index = {column.name: column for column in columns}
    comment = indexes.table_comment.get(folded)

    entries: list[dict[str, Any]] = [
        *_column_evidence(
            keys,
            column_index,
            workspace_id=workspace_id,
            table_key=table_key,
        ),
        *_process_signal_evidence(
            folded,
            keys,
            indexes,
            workspace_id=workspace_id,
            table_key=table_key,
        ),
        *_sql_evidence(
            folded,
            indexes,
            workspace_id=workspace_id,
            table_key=table_key,
        ),
        *_lineage_evidence(
            folded,
            indexes,
            workspace_id=workspace_id,
            table_key=table_key,
        ),
    ]

    object_entries, matched = _object_evidence(
        folded,
        keys,
        indexes,
        workspace_id=workspace_id,
        table_key=table_key,
    )
    entries.extend(object_entries)

    if comment:
        entries.append(
            _evidence_entry(
                GRAIN_EVIDENCE_TABLE,
                table_key,
                workspace_id=workspace_id,
                table_key=table_key,
                column_name=None,
                reason=f"表注释：{comment}",
            )
        )

    return _dedupe_evidence(entries), matched


def _evidence_counts(entries: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {source_type: 0 for source_type in GRAIN_EVIDENCE_ORDER}

    for entry in entries:
        source_type = str(entry.get("source_type") or "")
        counts[source_type] = counts.get(source_type, 0) + 1

    return counts


def _evidence_sources(entries: Sequence[Mapping[str, Any]]) -> list[str]:
    counts = _evidence_counts(entries)

    return [
        source_type
        for source_type in GRAIN_EVIDENCE_ORDER
        if counts.get(source_type)
    ]


# ============================================================
# 构建
# ============================================================


@dataclass
class _TableContext:
    """一张 (process, table) 的形态上下文。"""

    folded: str
    table_key: str
    workspace_id: Any
    core_candidate: bool
    columns: dict[str, ColumnFacts]
    identifier_columns: tuple[str, ...]
    time_columns: tuple[str, ...]
    measure_columns: tuple[str, ...]


def _unresolved_reasons(
    *,
    keys: Sequence[str],
    evidence: Sequence[Mapping[str, Any]],
    table_context: _TableContext,
    indexes: GrainIndexes,
    candidate_group_size: int,
) -> list[str]:
    """固定顺序的 unresolved_reasons：只表达证据不足，不是业务结论。"""

    reasons: set[str] = set()

    if not any(
        table_context.columns[key].has(_FLAG_IDENTIFIER)
        for key in keys
        if key in table_context.columns
    ):
        reasons.add(GRAIN_UNRESOLVED_NO_IDENTIFIER)

    if candidate_group_size > 1:
        reasons.add(GRAIN_UNRESOLVED_MULTIPLE_KEYS)

    if not indexes.sql_refs.get(table_context.folded):
        reasons.add(GRAIN_UNRESOLVED_SQL)

    if table_context.folded not in indexes.lineage_tables:
        reasons.add(GRAIN_UNRESOLVED_LINEAGE)

    if _time_semantics_unclear(keys, table_context.columns) or (
        not keys and table_context.time_columns
    ):
        reasons.add(GRAIN_UNRESOLVED_TIME)

    if table_context.measure_columns and _grain_pattern(
        keys,
        table_context.columns,
    ) in (GRAIN_PATTERN_AGGREGATION, GRAIN_PATTERN_UNKNOWN):
        reasons.add(GRAIN_UNRESOLVED_AGGREGATION)

    if not keys or len(_evidence_sources(evidence)) < 2:
        reasons.add(GRAIN_UNRESOLVED_INSUFFICIENT)

    return [reason for reason in GRAIN_UNRESOLVED_ORDER if reason in reasons]


def _candidate_rows(
    indexes: GrainIndexes,
    inputs: GrainInputs,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(grain candidate 行, grain → table 行)。"""

    raw: list[dict[str, Any]] = []

    for record in sorted(
        inputs.process_tables,
        key=lambda item: (
            str(item.get("process_key") or ""),
            str(item.get("table_key") or "").casefold(),
        ),
    ):
        process_key = str(record.get("process_key") or "")
        table_key = str(record.get("table_key") or "")
        folded = table_key.casefold()

        if not process_key or not table_key:
            continue

        meta = indexes.table_meta.get(folded, {})
        display_key = str(meta.get("table_key") or table_key)
        workspace_id = meta.get("workspace_id")
        columns = {
            column.name: column for column in indexes.columns_by_table.get(folded, ())
        }
        table_columns = indexes.columns_by_table.get(folded, ())

        forms = _candidate_key_forms(folded, indexes, process_key)
        key_sets = sorted(set(forms)) or [()]
        context = _TableContext(
            folded=folded,
            table_key=display_key,
            workspace_id=workspace_id,
            core_candidate=bool(meta.get("core_candidate")),
            columns=columns,
            identifier_columns=_flag_names(table_columns, _FLAG_IDENTIFIER),
            time_columns=_flag_names(table_columns, _FLAG_TIME),
            measure_columns=_flag_names(table_columns, _FLAG_MEASURE),
        )

        for keys in key_sets:
            key_list = list(keys)
            evidence, matched = _build_evidence(
                folded,
                key_list,
                indexes,
                workspace_id=workspace_id,
                table_key=display_key,
            )
            pattern = _grain_pattern(key_list, columns)
            reasons = _unresolved_reasons(
                keys=key_list,
                evidence=evidence,
                table_context=context,
                indexes=indexes,
                candidate_group_size=len(key_sets),
            )
            signature = (
                f"process={process_key}|table={display_key.casefold()}"
                f"|keys={','.join(key_list)}|pattern={pattern}"
            )
            strength = (
                evidence_strength(len(_evidence_sources(evidence)))
                if key_list
                else EVIDENCE_STRENGTH_WEAK
            )

            raw.append(
                {
                    "_signature": signature,
                    "process_candidate_id": process_key,
                    "table_key": display_key,
                    "table_name": str(meta.get("table_name") or display_key),
                    "workspace_id": workspace_id,
                    "project": str(meta.get("project") or ""),
                    "canonical_signature": signature,
                    "candidate_keys": key_list,
                    "grain_pattern": pattern,
                    "status": GRAIN_STATUS_CANDIDATE,
                    "process_human_validated": bool(
                        indexes.process_validated.get(process_key)
                    ),
                    "time_columns": list(context.time_columns),
                    "measure_columns": list(context.measure_columns),
                    "identifier_columns": list(context.identifier_columns),
                    "strength": strength,
                    "evidence_sources": _evidence_sources(evidence),
                    "evidence": evidence,
                    "unresolved_reasons": reasons,
                    "matched_objects": list(matched),
                    "core_candidate": context.core_candidate,
                }
            )

    raw.sort(key=lambda item: str(item["_signature"]))

    candidates: list[dict[str, Any]] = []
    grain_tables: list[dict[str, Any]] = []

    for position, item in enumerate(raw, start=1):
        candidate_id = f"grain_candidate_{position:03d}"
        key_list = [str(name) for name in item["candidate_keys"]]
        evidence_counts = _evidence_counts(item["evidence"])
        anchor_key = str(item["table_key"]).casefold()
        process_key = str(item["process_candidate_id"])
        siblings = [
            sibling
            for sibling in indexes.process_tables_by_process.get(process_key, ())
            if sibling.casefold() != anchor_key
        ]
        supporting = [
            sibling
            for sibling in siblings
            if key_list
            and all(
                any(
                    column.name == key
                    for column in indexes.columns_by_table.get(sibling.casefold(), ())
                )
                for key in key_list
            )
        ]

        candidate = {
            "grain_candidate_id": candidate_id,
            **{key: value for key, value in item.items() if not key.startswith("_")},
        }
        candidates.append(candidate)

        grain_tables.append(
            _grain_table_row(
                candidate_id=candidate_id,
                process_key=process_key,
                folded=anchor_key,
                role=GRAIN_ROLE_ANCHOR,
                indexes=indexes,
                keys=key_list,
                evidence_counts=evidence_counts,
                supporting_table_count=len(supporting),
            )
        )

        for sibling in supporting[:GRAIN_SUPPORTING_ROW_LIMIT]:
            grain_tables.append(
                _grain_table_row(
                    candidate_id=candidate_id,
                    process_key=process_key,
                    folded=sibling.casefold(),
                    role=GRAIN_ROLE_SUPPORTING,
                    indexes=indexes,
                    keys=key_list,
                    evidence_counts=None,
                    supporting_table_count=0,
                )
            )

    return candidates, grain_tables


def _grain_table_row(
    *,
    candidate_id: str,
    process_key: str,
    folded: str,
    role: str,
    indexes: GrainIndexes,
    keys: Sequence[str],
    evidence_counts: dict[str, int] | None,
    supporting_table_count: int,
) -> dict[str, Any]:
    meta = indexes.table_meta.get(folded, {})
    display_key = str(meta.get("table_key") or folded)
    columns = indexes.columns_by_table.get(folded, ())
    present = {column.name.casefold() for column in columns}

    if evidence_counts is None:
        counts = {source_type: 0 for source_type in GRAIN_EVIDENCE_ORDER}
        counts[GRAIN_EVIDENCE_COLUMN] = sum(
            1 for key in keys if key.casefold() in present
        )

        if indexes.sql_refs.get(folded):
            counts[GRAIN_EVIDENCE_SQL] = 1

        if folded in indexes.lineage_tables:
            counts[GRAIN_EVIDENCE_LINEAGE] = 1

        if indexes.table_comment.get(folded):
            counts[GRAIN_EVIDENCE_TABLE] = 1
    else:
        counts = dict(evidence_counts)

    return {
        "grain_candidate_id": candidate_id,
        "process_candidate_id": process_key,
        "table_key": display_key,
        "table_name": str(meta.get("table_name") or display_key),
        "workspace_id": meta.get("workspace_id"),
        "project": str(meta.get("project") or ""),
        "role": role,
        "supporting_table_count": supporting_table_count,
        "core_candidate": bool(
            folded in indexes.core_keys or meta.get("core_candidate")
        ),
        "evidence": counts,
    }


def build_business_grain(inputs: GrainInputs) -> BusinessGrainResult:
    """从 M2 / M3 / M3.3 产物构建 M3.4 的三个 JSON 与两个 Markdown 产物正文。"""

    indexes = build_indexes(inputs)
    signal_rows = build_grain_signals(indexes, inputs)
    candidate_rows, grain_table_rows = _candidate_rows(indexes, inputs)

    signals_payload = {
        "count": len(signal_rows),
        "note": (
            "Grain Signal 只表示字段 / 表上存在某类 grain 相关信号，"
            f"不是 {GRAIN_CANDIDATE_NOTE}。"
        ),
        "table_count": len(
            {str(row.get("table_key") or "").casefold() for row in signal_rows}
        ),
        "type_counts": _status_counts(
            [str(row.get("signal_type") or "") for row in signal_rows],
            GRAIN_SIGNAL_TYPE_ORDER,
        ),
        "signals": signal_rows,
    }

    candidates_payload = {
        "count": len(candidate_rows),
        "note": (
            f"{GRAIN_CANDIDATE_NOTE}；candidate_keys 只包含真实存在的字段，"
            "空候选键表示证据不足，不是「没有 grain」的结论。"
        ),
        "status_counts": _status_counts(
            [str(row.get("status") or "") for row in candidate_rows],
            GRAIN_STATUS_ORDER,
        ),
        "pattern_counts": _status_counts(
            [str(row.get("grain_pattern") or "") for row in candidate_rows],
            GRAIN_PATTERN_ORDER,
        ),
        "strength_counts": _status_counts(
            [str(row.get("strength") or "") for row in candidate_rows],
            EVIDENCE_STRENGTH_ORDER,
        ),
        "process_count": len(
            {str(row.get("process_candidate_id") or "") for row in candidate_rows}
        ),
        "table_count": len(
            {str(row.get("table_key") or "").casefold() for row in candidate_rows}
        ),
        "candidates": candidate_rows,
    }

    grain_tables_payload = {
        "count": len(grain_table_rows),
        "note": (
            "grain → table 只表达技术角色（anchor = 候选键来自该表，"
            "supporting = 该表也包含全部候选键）；"
            "core_candidate 只作证据覆盖与复核优先级，不是业务价值判断。"
        ),
        "role_counts": _status_counts(
            [str(row.get("role") or "") for row in grain_table_rows],
            GRAIN_ROLE_ORDER,
        ),
        "tables": grain_table_rows,
    }

    result = BusinessGrainResult(
        signals=signals_payload,
        candidates=candidates_payload,
        grain_tables=grain_tables_payload,
        analysis_dir=inputs.analysis_dir,
    )

    result.summary = render_grain_summary(
        signals=signals_payload,
        candidates=candidates_payload,
        grain_tables=grain_tables_payload,
        processes=inputs.processes,
        inventory_table_count=len(inputs.inventory_tables),
        process_table_count=len(inputs.process_tables),
        profiling=indexes.profiling,
        analysis_dir=inputs.analysis_dir,
    )
    result.checklist = render_grain_review_checklist(
        candidate_rows,
        carry_over=_parse_checklist_rows(
            inputs.carryover_text,
            required=GRAIN_CHECKLIST_REQUIRED_COLUMNS,
            source=inputs.carryover_path,
            label="grain-review-checklist.md",
        ),
        row_limit=GRAIN_CHECKLIST_ROW_LIMIT,
    )

    return result


# ============================================================
# 产物写出与运行入口
# ============================================================


def write_business_grain(
    result: BusinessGrainResult,
    output_dir: Path,
) -> tuple[Path, ...]:
    """写出 M3.4 产物，返回路径列表（固定顺序）。

    只覆盖本模块声明的五个文件，不删除、不改写已有 M2 / M3 产物。
    """

    ensure_dir(output_dir)

    paths = {name: output_dir / name for name in OUTPUT_FILES}

    write_json(paths["grain-signals.json"], result.signals)
    write_json(paths["grain-candidates.json"], result.candidates)
    write_json(paths["grain-tables.json"], result.grain_tables)
    write_text(paths["grain-summary.md"], result.summary)
    write_text(paths["grain-review-checklist.md"], result.checklist)

    logger.info(
        "M3.4 产物已写出：%s",
        "，".join(_display_path(paths[name]) for name in OUTPUT_FILES),
    )

    return tuple(paths[name] for name in OUTPUT_FILES)


def run_business_grain_analysis(
    *,
    analysis_dir: Path,
    output_dir: Path,
) -> BusinessGrainResult:
    """执行 M3.4 Grain Candidate Analysis 并写出产物。

    只读 M2 / M3 / M3.3 产物；输入缺失时直接报错，
    不自动回退去跑前置阶段。
    """

    inputs = read_grain_inputs(analysis_dir)
    result = build_business_grain(inputs)
    result.analysis_dir = analysis_dir

    write_business_grain(result, output_dir)

    logger.info(
        "M3.4 Grain Candidate Analysis 完成：signal=%s，grain candidate=%s"
        "（%s），grain table=%s，confirmed=%s",
        result.signal_count,
        result.candidate_count,
        "，".join(
            f"{key}={value}" for key, value in result.pattern_counts.items()
        ),
        result.grain_table_count,
        result.status_counts.get(GRAIN_STATUS_CANDIDATE, 0),
    )

    return result

"""M3.3 Business Process Candidate Analysis。

目标：

    从 M3.2 的 Object / Relationship / Table Association 与 M2 的 Column / SQL /
    Lineage 语义证据中识别「Process Signal」，并把信号组合成 Business Process
    Candidate，作为 M3.4 Grain Candidate Analysis 的机器输入。

    Business Process Candidate
          ├── objects（只来自 M3.2 association，不重新识别 Object）
          ├── signals（列级 transaction / measure / event time / status
          │           + 表级 multi_object / lifecycle）
          ├── evidence（column / table / sql / lineage / object relationship）
          └── unresolved_questions（名称、语义、grain、人工验证）

输入（只读 analysis/ 与 config/，不读 source/，不调 API，不修改 M2 / M3 / M3.1 / M3.2）：

    analysis/understanding/business/objects-registry.json
    analysis/understanding/business/object-tables.json
    analysis/understanding/business/object-relationships.json
    analysis/understanding/business/tables.json
    analysis/understanding/business/terms.json
    analysis/understanding/business/review-checklist.md
    analysis/inventory/tables.json
    analysis/inventory/columns.json
    analysis/evidence/sql/statements.json
    analysis/evidence/sql/table-references.json
    analysis/evidence/lineage/table-lineage.json
    analysis/evidence/lineage/core-table-candidates.json
    config/process-rules.yaml
    understanding/business/process-review-checklist.md   （可选：已回填的人工确认）

输出：

    analysis/understanding/business/process-signals.json
    analysis/understanding/business/processes.json
    analysis/understanding/business/process-tables.json
    analysis/understanding/business/process-objects.json
    analysis/understanding/business/process-summary.md
    understanding/business/process-review-checklist.md

原则：

1. 不重新识别 Object：参与对象只来自 object-tables.json 的 association，
   表名 / 字段名只用于统计信号与证据，本模块不建立第二套 Object classifier。
2. Signal ≠ Process：命中 process-rules.yaml 只说明字段 / 表上存在某类过程信号，
   不等于识别出一个业务过程；证据不足时只保留 signal，不生成 candidate。
3. Candidate ≠ Confirmed：status 恒为 candidate；只有人工回填 process-review-checklist.md
   才可能把 human_validated 置为 true，机器阶段不产出 confirmed process。
4. 不命名 Process：输出只有 process_key，没有 process_name / Sales Process 之类命名；
   命名属于人工确认环节。
5. 不判定 Grain：只记录 grain_signals（transaction / aggregation / time grouping），
   任何位置都写 grain not determined。
6. 不做 Object ↔ Process 简单映射：candidate 由多个信号与多类证据共同支撑，
   不产出「某个 Object 对应一个 Process」的一对一映射。
7. 分组去重：按精确 Object 集合分组，一张表只进入一个 candidate，
   避免 amount / quantity 等重复信号各自生成一个 candidate。
8. 输出 deterministic：无时间戳 / UUID / 随机抽样，全部稳定排序。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

from .... import config
from ....io_utils import (
    ensure_dir,
    relocate_legacy_artifacts,
    write_json,
    write_text,
)
from ...models import (
    GRAIN_SIGNAL_AGGREGATION_COLUMNS,
    GRAIN_SIGNAL_ORDER,
    GRAIN_SIGNAL_TIME_GROUPING,
    GRAIN_SIGNAL_TRANSACTION_IDENTIFIER,
    GRAIN_UNDETERMINED_NOTE,
    OBJECT_STATUS_CONFIRMED,
    PROCESS_CANDIDATE_TERM_LIMIT,
    PROCESS_COLUMN_SIGNAL_ORDER,
    PROCESS_LEVEL_1,
    PROCESS_LEVEL_2,
    PROCESS_LEVEL_3,
    PROCESS_LEVEL_ORDER,
    PROCESS_ROLE_PARTICIPANT,
    PROCESS_SIGNAL_EVENT_TIME,
    PROCESS_SIGNAL_EXAMPLE_LIMIT,
    PROCESS_SIGNAL_LIFECYCLE,
    PROCESS_SIGNAL_MULTI_OBJECT,
    PROCESS_SIGNAL_STATUS,
    PROCESS_SIGNAL_TRANSACTION_ID,
    PROCESS_SIGNAL_TRANSACTION_MEASURE,
    PROCESS_SIGNAL_TYPE_ORDER,
    PROCESS_STATUS_CANDIDATE,
    PROCESS_STRENGTH_ORDER,
    PROCESS_UNRESOLVED_LINEAGE,
    PROCESS_UNRESOLVED_RELATIONSHIP,
    PROCESS_UNRESOLVED_REQUIRED,
    PROCESS_UNRESOLVED_SQL,
    BusinessProcessResult,
    process_evidence_strength,
)
from ...reports import (
    render_process_review_checklist,
    render_process_summary,
)
from .objects import (
    HumanReview,
    _cell,
    _index_core_keys,
    _lineage_table_keys,
    _referenced_table_keys,
    _split_row,
    _table_sort_key,
    _text,
    _workspace_projects,
    parse_review_checklist,
)
from .understanding import tokenize_identifier

logger = logging.getLogger(__name__)

# ============================================================
# 输入与输出布局
# ============================================================

ARRAY_INPUT_FILES: tuple[tuple[str, str, str], ...] = (
    ("understanding/business/objects-registry.json", "objects", "registry_objects"),
    ("understanding/business/object-tables.json", "associations", "associations"),
    ("understanding/business/object-relationships.json", "relationships", "relationships"),
    ("understanding/business/tables.json", "tables", "tables"),
    ("understanding/business/terms.json", "terms", "terms"),
    ("inventory/tables.json", "tables", "inventory_tables"),
    ("inventory/columns.json", "columns", "columns"),
    ("evidence/sql/statements.json", "statements", "statements"),
    ("evidence/sql/table-references.json", "references", "references"),
    ("evidence/lineage/table-lineage.json", "edges", "edges"),
    ("evidence/lineage/core-table-candidates.json", "candidates", "candidates"),
)
"""M3.3 依赖的数组型 M2 / M3 / M3.2 产物（相对 analysis/ 路径 → JSON 数组字段名 → 属性名）。"""

CHECKLIST_INPUT_FILE = "understanding/business/review-checklist.md"
"""M3.1 人工复核清单：表级人工确认的唯一来源。"""

PROCESS_CHECKLIST_INPUT_FILE = "understanding/business/process-review-checklist.md"
"""M3.3 人工确认清单（可选输入）：回填过的人工确认在重跑时被带回去。"""

INPUT_FILES: tuple[str, ...] = (
    *(relative for relative, _key, _attr in ARRAY_INPUT_FILES),
    CHECKLIST_INPUT_FILE,
)
"""M3.3 的必需输入（相对 analysis/ 路径）；process-review-checklist.md 属于可选输入。"""

OUTPUT_FILES: tuple[str, ...] = (
    "process-signals.json",
    "processes.json",
    "process-tables.json",
    "process-objects.json",
    "process-summary.md",
    "process-review-checklist.md",
)
"""M3.3 产物文件名（固定顺序）；只覆盖这六个文件，不动已有 M2 / M3 / M3.1 / M3.2 产物。"""

PROCESS_RULE_SECTIONS: tuple[tuple[str, str], ...] = (
    ("transaction_identifiers", PROCESS_SIGNAL_TRANSACTION_ID),
    ("transaction_measures", PROCESS_SIGNAL_TRANSACTION_MEASURE),
    ("event_time", PROCESS_SIGNAL_EVENT_TIME),
    ("status", PROCESS_SIGNAL_STATUS),
)
"""config/process-rules.yaml 的段名 → 信号类型。"""

PROCESS_CHECKLIST_REQUIRED_COLUMNS: tuple[str, ...] = (
    "process_key",
    "human_process_name",
    "confirmed",
    "note",
)
"""process-review-checklist.md 必须包含的列，缺一即报错。"""

_GRAIN_SIGNAL_BY_TYPE: dict[str, str] = {
    PROCESS_SIGNAL_TRANSACTION_ID: GRAIN_SIGNAL_TRANSACTION_IDENTIFIER,
    PROCESS_SIGNAL_TRANSACTION_MEASURE: GRAIN_SIGNAL_AGGREGATION_COLUMNS,
    PROCESS_SIGNAL_EVENT_TIME: GRAIN_SIGNAL_TIME_GROUPING,
}
"""列级信号 → grain 信号类型；status 不是 grain 信号。"""

_TRUE_VALUES: frozenset[str] = frozenset({"true", "yes", "y", "1", "confirmed", "是"})
"""confirmed 单元格里表示「已确认」的写法（其余一律按未确认处理）。"""


class BusinessProcessesError(RuntimeError):
    """M3.3 无法继续的输入 / 配置 / 结构错误。"""


def _display_path(path: Path) -> str:
    """日志与报告中展示的路径：项目根内用相对路径，其余保持绝对。"""

    try:
        return str(path.resolve().relative_to(config.PROJECT_ROOT))

    except ValueError:
        return str(path)


# ============================================================
# 通用小工具
# ============================================================


def _status_counts(statuses: Sequence[str], order: Sequence[str]) -> dict[str, int]:
    """按固定顺序输出状态计数（缺项补 0，未登记值排最后）。"""

    counts = {status: 0 for status in order}

    for status in statuses:
        counts[status] = counts.get(status, 0) + 1

    return counts


def _dict_values(records: Any, key: str, path: Path) -> list[dict[str, Any]]:
    """校验并取出 JSON 数组里的对象条目。"""

    if not isinstance(records, list):
        raise BusinessProcessesError(f"缺少 {key} 数组：{path}")

    items: list[dict[str, Any]] = []

    for position, entry in enumerate(records):
        if not isinstance(entry, dict):
            raise BusinessProcessesError(f"{key}[{position}] 不是对象：{path}")

        items.append(entry)

    return items


def _signal_rank(signal_type: str) -> int:
    """信号类型的固定排序位置；未登记类型排最后。"""

    try:
        return PROCESS_SIGNAL_TYPE_ORDER.index(signal_type)

    except ValueError:
        return len(PROCESS_SIGNAL_TYPE_ORDER)


def _level_rank(level: str) -> int:
    try:
        return PROCESS_LEVEL_ORDER.index(level)

    except ValueError:
        return len(PROCESS_LEVEL_ORDER)


# ============================================================
# Process Signal 规则（config/process-rules.yaml）
# ============================================================


@dataclass(frozen=True)
class SignalRule:
    """一条列级过程信号规则：原文 + 分词结果（casefold）。"""

    text: str
    tokens: tuple[str, ...]


@dataclass
class ProcessRules:
    """config/process-rules.yaml 的加载结果。"""

    version: str
    source_path: Path
    signals: dict[str, tuple[SignalRule, ...]] = field(default_factory=dict)

    @property
    def rule_count(self) -> int:
        return sum(len(rules) for rules in self.signals.values())


def _parse_rule_section(value: Any, label: str, path: Path) -> tuple[SignalRule, ...]:
    """解析一个规则段：必须是非空字符串列表，忽略大小写去重。"""

    if not isinstance(value, list) or not value:
        raise BusinessProcessesError(f"process-rules 配置段 {label} 必须是非空列表：{path}")

    rules: list[SignalRule] = []
    seen: set[str] = set()

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BusinessProcessesError(
                "process-rules 规则只能包含非空字符串"
                f"（YAML 裸 no/yes 会被解析成布尔值，需要加引号）：{item!r}（{path}）"
            )

        text = item.strip()
        folded = text.casefold()

        if folded in seen:
            raise BusinessProcessesError(
                f"process-rules 配置段 {label} 存在重复规则：{text}（{path}）"
            )

        seen.add(folded)

        tokens = tuple(token.casefold() for token in tokenize_identifier(text))

        if not tokens:
            raise BusinessProcessesError(f"process-rules 规则分词后为空：{text}（{path}）")

        rules.append(SignalRule(text=text, tokens=tokens))

    return tuple(rules)


def load_process_rules(path: Path) -> ProcessRules:
    """读取并严格校验 process-rules 配置。

    校验失败一律抛 BusinessProcessesError，不静默回退默认规则。
    """

    if not path.exists():
        raise BusinessProcessesError(f"process-rules 配置文件不存在：{path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    except yaml.YAMLError as exc:
        raise BusinessProcessesError(f"process-rules 配置不是合法的 YAML：{path}（{exc}）") from exc

    if raw is None:
        raise BusinessProcessesError(f"process-rules 配置为空：{path}")

    if not isinstance(raw, dict):
        raise BusinessProcessesError(f"process-rules 配置根节点必须是映射：{path}")

    version = raw.get("version")

    if not isinstance(version, str) or not version.strip():
        raise BusinessProcessesError(f"process-rules 配置缺少 version：{path}")

    signals = {
        signal_type: _parse_rule_section(raw.get(section), section, path)
        for section, signal_type in PROCESS_RULE_SECTIONS
    }

    owners: dict[str, str] = {}

    for signal_type in PROCESS_COLUMN_SIGNAL_ORDER:
        for rule in signals[signal_type]:
            owner = owners.setdefault(rule.text.casefold(), signal_type)

            if owner != signal_type:
                raise BusinessProcessesError(
                    "process-rules 规则跨段冲突（同一规则不能出现在多个信号类型）："
                    f"{rule.text} 同时属于 {owner} 与 {signal_type}（{path}）"
                )

    rules = ProcessRules(
        version=version.strip(),
        source_path=path,
        signals=signals,
    )

    logger.info(
        "process-rules 已加载：%s（version=%s，rule=%s）",
        _display_path(path),
        rules.version,
        rules.rule_count,
    )

    return rules


def _rule_match_index(tokens: Sequence[str], rule: SignalRule) -> int | None:
    """规则 token 是否是字段 token 的连续子序列；返回最早命中位置。"""

    size = len(rule.tokens)

    if size == 0 or size > len(tokens):
        return None

    for index in range(len(tokens) - size + 1):
        if list(tokens[index : index + size]) == list(rule.tokens):
            return index

    return None


def _best_rule(tokens: Sequence[str], rules: Sequence[SignalRule]) -> SignalRule | None:
    """一个字段在一个信号类型内命中的规则：最早 + 最长 + 规则文本升序。"""

    best: tuple[tuple[int, int, str], SignalRule] | None = None

    for rule in rules:
        index = _rule_match_index(tokens, rule)

        if index is None:
            continue

        key = (index, -len(rule.tokens), rule.text)

        if best is None or key < best[0]:
            best = (key, rule)

    return best[1] if best else None


def _match_column(
    column_name: str,
    rules: ProcessRules,
) -> list[tuple[str, SignalRule]]:
    """一个字段名命中的全部信号类型（按 PROCESS_COLUMN_SIGNAL_ORDER）。"""

    tokens = [token.casefold() for token in tokenize_identifier(column_name)]

    if not tokens:
        return []

    hits: list[tuple[str, SignalRule]] = []

    for signal_type in PROCESS_COLUMN_SIGNAL_ORDER:
        rule = _best_rule(tokens, rules.signals[signal_type])

        if rule is not None:
            hits.append((signal_type, rule))

    return hits


# ============================================================
# M2 / M3 / M3.2 产物读取
# ============================================================


@dataclass
class ProcessInputs:
    """M3.3 读取到的 M2 / M3 / M3.1 / M3.2 产物（只做结构校验，不改写）。"""

    registry_objects: list[dict[str, Any]] = field(default_factory=list)
    associations: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    terms: list[dict[str, Any]] = field(default_factory=list)
    inventory_tables: list[dict[str, Any]] = field(default_factory=list)
    columns: list[dict[str, Any]] = field(default_factory=list)
    statements: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    checklist_text: str = ""
    checklist_path: Path = field(default_factory=Path)
    process_checklist_text: str = ""
    process_checklist_path: Path = field(default_factory=Path)
    analysis_dir: Path = field(default_factory=Path)


def read_process_inputs(analysis_dir: Path) -> ProcessInputs:
    """读取 M3.3 依赖的全部 M2 / M3 / M3.2 产物。

    任何必需输入缺失或 JSON 非法都明确报错，
    不自动回退执行 analyze / analyze --stage。
    """

    missing = [relative for relative in INPUT_FILES if not (analysis_dir / relative).exists()]

    if missing:
        raise BusinessProcessesError(
            "M2 / M3 / M3.2 产物缺失，无法执行 M3.3 Business Process Candidate Analysis："
            f"{'、'.join(missing)}（目录：{_display_path(analysis_dir)}）；"
            "请先执行 analyze --stage evidence 生成 M2 产物、"
            "analyze --stage understanding 生成 M3 ~ M3.5 产物"
        )

    def load(relative: str, key: str) -> list[dict[str, Any]]:
        path = analysis_dir / relative

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))

        except json.JSONDecodeError as exc:
            raise BusinessProcessesError(f"产物不是合法的 JSON：{path}（{exc}）") from exc

        if not isinstance(raw, dict):
            raise BusinessProcessesError(f"产物根节点不是对象：{path}")

        return _dict_values(raw.get(key), key, path)

    inputs = ProcessInputs()
    inputs.analysis_dir = analysis_dir
    inputs.checklist_path = analysis_dir / CHECKLIST_INPUT_FILE
    inputs.process_checklist_path = analysis_dir / PROCESS_CHECKLIST_INPUT_FILE

    for relative, key, attr in ARRAY_INPUT_FILES:
        setattr(inputs, attr, load(relative, key))

    try:
        inputs.checklist_text = inputs.checklist_path.read_text(encoding="utf-8")

    except OSError as exc:
        raise BusinessProcessesError(
            f"无法读取人工复核清单：{inputs.checklist_path}（{exc}）"
        ) from exc

    if inputs.process_checklist_path.exists():
        try:
            inputs.process_checklist_text = inputs.process_checklist_path.read_text(
                encoding="utf-8"
            )

        except OSError as exc:
            raise BusinessProcessesError(
                f"无法读取 process review 清单：{inputs.process_checklist_path}（{exc}）"
            ) from exc

    logger.info(
        "M3.3 输入已读取：%s（association=%s，relationship=%s，column=%s，statement=%s）",
        _display_path(analysis_dir),
        len(inputs.associations),
        len(inputs.relationships),
        len(inputs.columns),
        len(inputs.statements),
    )

    return inputs


# ============================================================
# 索引
# ============================================================


def _index_table_display(
    inventory_tables: Sequence[Mapping[str, Any]],
    tables: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """table_key(casefold) → 展示用元数据（table_key 原文 / 表名 / workspace / project）。"""

    meta: dict[str, dict[str, Any]] = {}

    for record in sorted(tables, key=_table_sort_key) + sorted(
        inventory_tables, key=_table_sort_key
    ):
        key = _text(record.get("table_key"))

        if not key:
            continue

        folded = key.casefold()

        entry = meta.setdefault(
            folded,
            {
                "table_key": key,
                "table_name": _text(record.get("table")) or key,
                "workspace_id": record.get("workspace_id"),
                "project": _text(record.get("project")) or "",
                "warehouse_layers": set(),
                "candidate_layers": set(),
                "core_candidate": False,
            },
        )

        entry["table_name"] = _text(record.get("table")) or entry["table_name"]

        if not entry["project"]:
            entry["project"] = _text(record.get("project")) or ""

        if entry["workspace_id"] is None:
            entry["workspace_id"] = record.get("workspace_id")

    return meta


def _index_associations(
    associations: Sequence[Mapping[str, Any]],
    meta: dict[str, dict[str, Any]],
) -> dict[str, set[str]]:
    """在表元数据上补充 Object / Layer / core 标记，返回 table_key → Object 集合。"""

    objects: dict[str, set[str]] = {}

    ordered = sorted(
        associations,
        key=lambda item: (
            str(item.get("table_key") or "").casefold(),
            str(item.get("object") or ""),
        ),
    )

    for record in ordered:
        key = _text(record.get("table_key"))

        if not key:
            continue

        folded = key.casefold()
        obj = _text(record.get("object"))

        entry = meta.setdefault(
            folded,
            {
                "table_key": key,
                "table_name": _text(record.get("table_name")) or key,
                "workspace_id": record.get("workspace_id"),
                "project": _text(record.get("project")) or "",
                "warehouse_layers": set(),
                "candidate_layers": set(),
                "core_candidate": False,
            },
        )

        warehouse_layer = _text(record.get("warehouse_layer"))
        candidate_layer = _text(record.get("candidate_layer"))

        if warehouse_layer:
            entry["warehouse_layers"].add(warehouse_layer)

        if candidate_layer:
            entry["candidate_layers"].add(candidate_layer)

        if record.get("core_candidate"):
            entry["core_candidate"] = True

        if obj:
            objects.setdefault(folded, set()).add(obj)

    return objects


def _relationship_pairs(
    relationships: Sequence[Mapping[str, Any]],
) -> set[tuple[str, str]]:
    """M3.2 relationship 的（排序）Object 对。"""

    pairs: set[tuple[str, str]] = set()

    for record in relationships:
        left = _text(record.get("object_a"))
        right = _text(record.get("object_b"))

        if left and right:
            pairs.add(tuple(sorted((left, right))))  # type: ignore[arg-type]

    return pairs


def _term_counts(terms: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """terms.json → normalized_term → count（缺失条目按 0 计）。"""

    counts: dict[str, int] = {}

    for record in sorted(
        terms,
        key=lambda item: (str(item.get("normalized_term") or ""), str(item.get("term") or "")),
    ):
        normalized = _text(record.get("normalized_term")) or _text(record.get("term"))

        if not normalized:
            continue

        try:
            value = int(record.get("count") or 0)

        except (TypeError, ValueError):
            value = 0

        counts.setdefault(normalized.casefold(), value)

    return counts


# ============================================================
# Process Signal 提取
# ============================================================


def _column_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    ordinal = record.get("ordinal")

    return (
        str(record.get("table_key") or "").casefold(),
        ordinal if isinstance(ordinal, int) else 0,
        str(record.get("column_name") or ""),
    )


def _extract_column_signals(
    columns: Sequence[Mapping[str, Any]],
    rules: ProcessRules,
) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    """列级信号行 + table_key(casefold) → 命中的列级信号类型集合。"""

    rows: list[dict[str, Any]] = []
    table_types: dict[str, set[str]] = {}

    for record in sorted(columns, key=_column_sort_key):
        key = _text(record.get("table_key"))
        column_name = _text(record.get("column_name"))

        if not key or not column_name:
            continue

        folded = key.casefold()

        for signal_type, rule in _match_column(column_name, rules):
            table_types.setdefault(folded, set()).add(signal_type)

            rows.append(
                {
                    "table_key": key,
                    "table_name": _text(record.get("table")) or key,
                    "workspace_id": record.get("workspace_id"),
                    "project": _text(record.get("project")) or "",
                    "signal_type": signal_type,
                    "signal": rule.text,
                    "column_name": column_name,
                    "source": "column",
                    "evidence": [
                        {
                            "type": "column",
                            "table_key": key,
                            "column_name": column_name,
                            "column_comment": _text(record.get("comment")),
                        }
                    ],
                }
            )

    return rows, table_types


def _extract_table_signals(
    table_meta: Mapping[str, dict[str, Any]],
    table_objects: Mapping[str, set[str]],
    table_types: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    """表级信号行：multi_object（参与 ≥2 Object）与 lifecycle（status + event_time）。"""

    rows: list[dict[str, Any]] = []

    for folded in sorted(set(table_objects) | set(table_types)):
        objects = sorted(table_objects.get(folded, set()))
        column_types = table_types.get(folded, set())
        meta = table_meta.get(folded, {})

        conditions: list[tuple[str, str]] = []

        if len(objects) >= 2:
            conditions.append((PROCESS_SIGNAL_MULTI_OBJECT, ",".join(objects)))

        if {
            PROCESS_SIGNAL_STATUS,
            PROCESS_SIGNAL_EVENT_TIME,
        } <= column_types:
            conditions.append(
                (
                    PROCESS_SIGNAL_LIFECYCLE,
                    f"{PROCESS_SIGNAL_STATUS}+{PROCESS_SIGNAL_EVENT_TIME}",
                )
            )

        for signal_type, value in conditions:
            rows.append(
                {
                    "table_key": meta.get("table_key") or folded,
                    "table_name": meta.get("table_name") or folded,
                    "workspace_id": meta.get("workspace_id"),
                    "project": meta.get("project") or "",
                    "signal_type": signal_type,
                    "signal": value,
                    "column_name": None,
                    "source": "table",
                    "evidence": [
                        {
                            "type": "table",
                            "table_key": meta.get("table_key") or folded,
                        }
                    ],
                }
            )

    return rows


def _signal_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(row.get("table_key") or "").casefold(),
        _signal_rank(str(row.get("signal_type") or "")),
        str(row.get("column_name") or ""),
        str(row.get("signal") or ""),
    )


# ============================================================
# 人工确认
# ============================================================


def _parse_process_checklist(text: str) -> dict[str, dict[str, str]]:
    """解析 process-review-checklist.md：process_key → 人工回填的三列原文。

    表结构非法（找不到必需列）时报错；重复的 process_key 行只保留首个。
    """

    if not text.strip():
        return {}

    columns: dict[str, int] = {}

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped.startswith("|"):
            continue

        cells = [cell.casefold() for cell in _split_row(stripped)]

        if not cells or cells[0] != "process_key":
            continue

        found = {
            name: cells.index(name) for name in PROCESS_CHECKLIST_REQUIRED_COLUMNS if name in cells
        }

        if len(found) == len(PROCESS_CHECKLIST_REQUIRED_COLUMNS):
            columns = found
            break

        raise BusinessProcessesError(
            "process-review-checklist.md 缺少必需列："
            f"{'、'.join(name for name in PROCESS_CHECKLIST_REQUIRED_COLUMNS if name not in cells)}"
        )

    if not columns:
        raise BusinessProcessesError(
            "process-review-checklist.md 找不到 process_key 表头"
            f"（必需列：{'、'.join(PROCESS_CHECKLIST_REQUIRED_COLUMNS)}）"
        )

    reviews: dict[str, dict[str, str]] = {}

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped.startswith("|"):
            continue

        cells = _split_row(stripped)

        key = _cell(cells, columns["process_key"])

        if not key or key.casefold() == "process_key" or set(key) <= {"-"}:
            continue

        reviews.setdefault(
            key,
            {
                "human_process_name": _cell(cells, columns["human_process_name"]),
                "confirmed": _cell(cells, columns["confirmed"]),
                "note": _cell(cells, columns["note"]),
            },
        )

    return reviews


def _confirmed_flag(value: str) -> bool:
    return (value or "").strip().casefold() in _TRUE_VALUES


def _load_reviews(
    inputs: ProcessInputs,
) -> tuple[dict[str, HumanReview], dict[str, dict[str, str]]]:
    """表级人工回填（review-checklist.md）与 process 级人工回填（本阶段清单）。"""

    try:
        table_reviews = parse_review_checklist(
            inputs.checklist_text,
            source=inputs.checklist_path,
        )

    except Exception as exc:  # noqa: BLE001 - 统一转成本阶段错误提示
        raise BusinessProcessesError(
            f"无法解析人工复核清单：{inputs.checklist_path}（{exc}）"
        ) from exc

    process_reviews = _parse_process_checklist(inputs.process_checklist_text)

    return table_reviews, process_reviews


# ============================================================
# 分组与门槛
# ============================================================


@dataclass
class ProcessGroup:
    """按精确 Object 集合分出的一个候选组（一张表只属于一个组）。"""

    objects: tuple[str, ...]
    tables: tuple[str, ...] = ()
    column_signal_types: frozenset[str] = frozenset()
    table_signal_types: frozenset[str] = frozenset()
    relationship_count: int = 0
    sql_table_count: int = 0
    lineage_table_count: int = 0
    core_table_count: int = 0
    levels: tuple[str, ...] = ()

    @property
    def signal_types(self) -> tuple[str, ...]:
        present = set(self.column_signal_types) | set(self.table_signal_types)

        return tuple(
            signal_type for signal_type in PROCESS_SIGNAL_TYPE_ORDER if signal_type in present
        )

    @property
    def canonical_signature(self) -> str:
        """候选的稳定身份：Object 集合 + 列级信号类型（不含时间戳 / 随机量）。"""

        return (
            f"objects={','.join(self.objects)}|signals={','.join(sorted(self.column_signal_types))}"
        )


def _group_tables(
    table_objects: Mapping[str, set[str]],
) -> dict[tuple[str, ...], list[str]]:
    """table_key(casefold) 集合 → 按精确 Object 集合分组的表（disjoint，天然去重）。"""

    groups: dict[tuple[str, ...], list[str]] = {}

    for folded, objects in table_objects.items():
        if not objects:
            continue

        groups.setdefault(tuple(sorted(objects)), []).append(folded)

    return {key: sorted(tables) for key, tables in sorted(groups.items())}


def _evaluate_group(
    *,
    objects: tuple[str, ...],
    tables: Sequence[str],
    table_types: Mapping[str, set[str]],
    table_level_types: Mapping[str, set[str]],
    table_meta: Mapping[str, dict[str, Any]],
    sql_keys: set[str],
    lineage_keys: set[str],
    relationship_pairs: set[tuple[str, str]],
    core_keys: set[str],
) -> ProcessGroup | None:
    """按 Level 1 / 2 / 3 + 「至少一个列级信号」门槛判断该组能否成为 candidate。"""

    column_types: set[str] = set()

    for folded in tables:
        column_types |= table_types.get(folded, set())

    if not column_types:
        return None

    has_transaction = PROCESS_SIGNAL_TRANSACTION_ID in column_types
    has_measure = PROCESS_SIGNAL_TRANSACTION_MEASURE in column_types
    has_event_time = PROCESS_SIGNAL_EVENT_TIME in column_types
    has_status = PROCESS_SIGNAL_STATUS in column_types

    has_sql = any(folded in sql_keys for folded in tables)
    has_lineage = any(folded in lineage_keys for folded in tables)

    relationship_count = sum(
        1 for left, right in combinations(sorted(objects), 2) if (left, right) in relationship_pairs
    )

    level_1 = has_transaction and bool(objects or has_measure or has_event_time or has_status)
    level_2 = len(objects) >= 2 and (has_sql or has_lineage or has_measure or has_event_time)
    level_3 = relationship_count > 0 and (
        has_transaction or has_event_time or has_measure or has_status
    )

    levels = tuple(
        level
        for level, hit in (
            (PROCESS_LEVEL_1, level_1),
            (PROCESS_LEVEL_2, level_2),
            (PROCESS_LEVEL_3, level_3),
        )
        if hit
    )

    if not levels:
        return None

    return ProcessGroup(
        objects=objects,
        tables=tuple(tables),
        column_signal_types=frozenset(column_types),
        table_signal_types=frozenset(
            signal_type
            for folded in tables
            for signal_type in (table_level_types.get(folded) or set())
        ),
        relationship_count=relationship_count,
        sql_table_count=sum(1 for folded in tables if folded in sql_keys),
        lineage_table_count=sum(1 for folded in tables if folded in lineage_keys),
        core_table_count=sum(
            1
            for folded in tables
            if folded in core_keys or table_meta.get(folded, {}).get("core_candidate")
        ),
        levels=levels,
    )


# ============================================================
# 构建
# ============================================================


def _index_business_terms(
    tables: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[str, ...]]:
    """table_key(casefold) → 该表的 business_terms（稳定排序、去重）。"""

    index: dict[str, set[str]] = {}

    for record in sorted(tables, key=_table_sort_key):
        key = _text(record.get("table_key"))

        if not key:
            continue

        terms = record.get("business_terms")

        if not isinstance(terms, list):
            continue

        bucket = index.setdefault(key.casefold(), set())

        for item in terms:
            if isinstance(item, str) and item.strip():
                bucket.add(item.strip())

    return {key: tuple(sorted(values)) for key, values in index.items()}


def _candidate_terms(
    *,
    objects: Sequence[str],
    column_rows: Sequence[Mapping[str, Any]],
    table_terms: Sequence[str],
    term_counts: Mapping[str, int],
) -> list[str]:
    """候选命名线索：Object 名 → 命中的信号规则 → business_terms（count 降序）。

    只是给后续人工命名用的线索，不构成 process name。
    """

    ordered: list[str] = []
    seen: set[str] = set()

    def push(value: str) -> None:
        folded = value.casefold()

        if folded and folded not in seen:
            seen.add(folded)
            ordered.append(value)

    for name in sorted(objects):
        push(name)

    for row in sorted(column_rows, key=_signal_sort_key):
        push(str(row.get("signal") or ""))

    for term in sorted(
        table_terms,
        key=lambda item: (-term_counts.get(item.casefold(), 0), item.casefold(), item),
    ):
        push(term)

    return ordered[:PROCESS_CANDIDATE_TERM_LIMIT]


def _grain_signals(
    column_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """只聚合 grain 相关信号，不产出 grain 结论。"""

    payload: dict[str, Any] = {"note": GRAIN_UNDETERMINED_NOTE}

    by_type: dict[str, dict[str, set[str]]] = {
        grain_signal: {"tables": set(), "examples": set()} for grain_signal in GRAIN_SIGNAL_ORDER
    }

    for row in column_rows:
        grain_signal = _GRAIN_SIGNAL_BY_TYPE.get(str(row.get("signal_type") or ""))

        if grain_signal is None:
            continue

        bucket = by_type[grain_signal]
        bucket["tables"].add(str(row.get("table_key") or "").casefold())

        if column_name := str(row.get("column_name") or ""):
            bucket["examples"].add(column_name)

    for grain_signal in GRAIN_SIGNAL_ORDER:
        bucket = by_type[grain_signal]
        examples = sorted(str(item) for item in bucket["examples"])

        payload[grain_signal] = {
            "table_count": len(bucket["tables"]),
            "examples": examples[:PROCESS_SIGNAL_EXAMPLE_LIMIT],
        }

    return payload


def _unresolved_questions(group: ProcessGroup) -> list[str]:
    """固定四条 + 证据缺失的条件问题。"""

    questions = list(PROCESS_UNRESOLVED_REQUIRED)

    if not group.sql_table_count:
        questions.append(PROCESS_UNRESOLVED_SQL)

    if not group.lineage_table_count:
        questions.append(PROCESS_UNRESOLVED_LINEAGE)

    if not group.relationship_count:
        questions.append(PROCESS_UNRESOLVED_RELATIONSHIP)

    return questions


def _evidence_sources(evidence: Mapping[str, int]) -> list[str]:
    order = (
        "column",
        "table",
        "sql",
        "lineage",
        "object_relationship",
    )

    return [source for source in order if evidence.get(source)]


def _group_column_rows(
    column_rows: Sequence[Mapping[str, Any]],
    tables: frozenset[str] | set[str],
) -> list[dict[str, Any]]:
    """取出组内表的列级信号行（深拷贝，避免写出时互相影响）。"""

    wanted = set(tables)

    return [
        dict(row) for row in column_rows if str(row.get("table_key") or "").casefold() in wanted
    ]


def _group_table_signal_types(
    table_rows: Sequence[Mapping[str, Any]],
) -> dict[str, set[str]]:
    """table_key(casefold) → 表级信号类型。"""

    index: dict[str, set[str]] = {}

    for row in table_rows:
        key = str(row.get("table_key") or "").casefold()
        index.setdefault(key, set()).add(str(row.get("signal_type") or ""))

    return index


def _table_status(review: HumanReview | None) -> str:
    if review is None or review.status is None:
        return PROCESS_STATUS_CANDIDATE

    return review.status


def build_business_processes(
    inputs: ProcessInputs,
    rules: ProcessRules,
) -> BusinessProcessResult:
    """从 M2 / M3 / M3.2 产物构建 M3.3 的四个 JSON 与两个 Markdown 产物正文。"""

    table_meta = _index_table_display(inputs.inventory_tables, inputs.tables)
    table_objects = _index_associations(inputs.associations, table_meta)
    core_keys = _index_core_keys(inputs.tables, inputs.candidates)
    relationship_pairs = _relationship_pairs(inputs.relationships)
    sql_keys = _referenced_table_keys(
        inputs.references,
        _workspace_projects(inputs.inventory_tables),
    )
    lineage_keys = _lineage_table_keys(inputs.edges)
    term_counts = _term_counts(inputs.terms)
    business_terms = _index_business_terms(inputs.tables)

    column_rows, table_types = _extract_column_signals(inputs.columns, rules)
    table_rows = _extract_table_signals(table_meta, table_objects, table_types)
    signal_rows = sorted([*column_rows, *table_rows], key=_signal_sort_key)
    table_level_types = _group_table_signal_types(table_rows)

    table_reviews, process_reviews = _load_reviews(inputs)
    confirmed_tables = {
        key for key, review in table_reviews.items() if review.status == OBJECT_STATUS_CONFIRMED
    }
    registry_status = {
        str(item.get("object") or ""): str(item.get("status") or PROCESS_STATUS_CANDIDATE)
        for item in inputs.registry_objects
    }

    groups: list[ProcessGroup] = []

    for objects, tables in _group_tables(table_objects).items():
        group = _evaluate_group(
            objects=objects,
            tables=tables,
            table_types=table_types,
            table_level_types=table_level_types,
            table_meta=table_meta,
            sql_keys=sql_keys,
            lineage_keys=lineage_keys,
            relationship_pairs=relationship_pairs,
            core_keys=core_keys,
        )

        if group is not None:
            groups.append(group)

    groups.sort(key=lambda item: item.canonical_signature)

    processes: list[dict[str, Any]] = []
    process_table_rows: list[dict[str, Any]] = []
    process_object_rows: list[dict[str, Any]] = []

    for position, group in enumerate(groups, start=1):
        process_key = f"process_candidate_{position:03d}"
        meta = [table_meta.get(folded, {}) for folded in group.tables]
        display = [
            str(item.get("table_key") or folded)
            for item, folded in zip(meta, group.tables, strict=True)
        ]
        display_keys = sorted(display, key=str.casefold)
        group_tables = set(group.tables)
        group_column_rows = _group_column_rows(column_rows, group_tables)
        signal_types = group.signal_types
        confirmed_count = sum(1 for key in group.tables if key in confirmed_tables)
        review = process_reviews.get(process_key, {})
        all_tables_confirmed = bool(group.tables) and confirmed_count == len(group.tables)
        human_validated = _confirmed_flag(review.get("confirmed", "")) or all_tables_confirmed

        evidence = {
            "column": len(group_column_rows),
            "table": sum(
                1
                for row in table_rows
                if str(row.get("table_key") or "").casefold() in group_tables
            ),
            "sql": group.sql_table_count,
            "lineage": group.lineage_table_count,
            "object_relationship": group.relationship_count,
        }

        table_count_by_signal: dict[tuple[str, str], set[str]] = {}

        for row in [*group_column_rows, *table_rows]:
            folded = str(row.get("table_key") or "").casefold()

            if folded not in group_tables:
                continue

            identity = (str(row.get("signal_type") or ""), str(row.get("signal") or ""))
            table_count_by_signal.setdefault(identity, set()).add(folded)

        signals = [
            {
                "signal_type": signal_type,
                "signal": signal,
                "table_count": len(table_count_by_signal[(signal_type, signal)]),
            }
            for signal_type, signal in sorted(
                table_count_by_signal,
                key=lambda item: (_signal_rank(item[0]), item[1]),
            )
        ]

        processes.append(
            {
                "process_key": process_key,
                "status": PROCESS_STATUS_CANDIDATE,
                "human_validated": human_validated,
                "canonical_signature": group.canonical_signature,
                "objects": list(group.objects),
                "tables": display_keys,
                "table_count": len(display_keys),
                "signal_types": list(signal_types),
                "signals": signals,
                "candidate_terms": _candidate_terms(
                    objects=group.objects,
                    column_rows=group_column_rows,
                    table_terms=sorted(
                        {term for folded in group.tables for term in business_terms.get(folded, ())}
                    ),
                    term_counts=term_counts,
                ),
                "evidence": evidence,
                "evidence_sources": _evidence_sources(evidence),
                "levels": list(sorted(group.levels, key=_level_rank)),
                "process_evidence_strength": process_evidence_strength(group.levels),
                "candidate_layer": sorted(
                    {str(layer) for item in meta for layer in item.get("candidate_layers", set())}
                ),
                "warehouse_layer": sorted(
                    {str(layer) for item in meta for layer in item.get("warehouse_layers", set())}
                ),
                "core_table_count": group.core_table_count,
                "checklist_table_count": sum(
                    1 for folded in group.tables if folded in table_reviews
                ),
                "confirmed_table_count": confirmed_count,
                "grain_signals": _grain_signals(group_column_rows),
                "unresolved_questions": _unresolved_questions(group),
            }
        )

        for folded, display_key in sorted(
            zip(group.tables, display, strict=True),
            key=lambda item: item[1].casefold(),
        ):
            item_meta = table_meta.get(folded, {})
            column_type_count = sum(
                1
                for row in group_column_rows
                if str(row.get("table_key") or "").casefold() == folded
            )
            table_type_count = len(table_level_types.get(folded, set()))

            process_table_rows.append(
                {
                    "process_key": process_key,
                    "table_key": display_key,
                    "table_name": item_meta.get("table_name") or display_key,
                    "workspace_id": item_meta.get("workspace_id"),
                    "project": item_meta.get("project") or "",
                    "objects": list(group.objects),
                    "signals": sorted(
                        set(table_types.get(folded, set())) | table_level_types.get(folded, set()),
                        key=_signal_rank,
                    ),
                    "evidence": {
                        "column": column_type_count,
                        "table": table_type_count,
                        "sql": 1 if folded in sql_keys else 0,
                        "lineage": 1 if folded in lineage_keys else 0,
                    },
                    "core_candidate": bool(folded in core_keys or item_meta.get("core_candidate")),
                    "status": _table_status(table_reviews.get(folded)),
                }
            )

        for obj in group.objects:
            object_tables = sorted(
                folded for folded in group.tables if obj in table_objects.get(folded, set())
            )

            process_object_rows.append(
                {
                    "process_key": process_key,
                    "object": obj,
                    "role": PROCESS_ROLE_PARTICIPANT,
                    "object_status": registry_status.get(obj, PROCESS_STATUS_CANDIDATE),
                    "status": PROCESS_STATUS_CANDIDATE,
                    "table_count": len(object_tables),
                    "core_table_count": sum(
                        1
                        for folded in object_tables
                        if folded in core_keys or table_meta.get(folded, {}).get("core_candidate")
                    ),
                    "signal_types": sorted(
                        {
                            signal_type
                            for folded in object_tables
                            for signal_type in (
                                set(table_types.get(folded, set()))
                                | table_level_types.get(folded, set())
                            )
                        },
                        key=_signal_rank,
                    ),
                    "relationship_count": sum(
                        1
                        for left, right in combinations(sorted(group.objects), 2)
                        if obj in (left, right) and (left, right) in relationship_pairs
                    ),
                }
            )

    status_counts = _status_counts(
        [str(item["status"]) for item in processes],
        [PROCESS_STATUS_CANDIDATE],
    )
    strength_counts = _status_counts(
        [str(item["process_evidence_strength"]) for item in processes],
        PROCESS_STRENGTH_ORDER,
    )
    level_counts = _status_counts(
        [level for item in processes for level in item["levels"]],
        PROCESS_LEVEL_ORDER,
    )

    signal_type_counts = _status_counts(
        [str(row.get("signal_type") or "") for row in signal_rows],
        PROCESS_SIGNAL_TYPE_ORDER,
    )

    signals_payload = {
        "count": len(signal_rows),
        "note": "Process Signal 只表示字段 / 表上存在某类过程信号，不等于 Business Process。",
        "rules_version": rules.version,
        "table_count": len({str(row.get("table_key") or "").casefold() for row in signal_rows}),
        "type_counts": signal_type_counts,
        "signals": signal_rows,
    }

    processes_payload = {
        "count": len(processes),
        "note": (
            "process candidate 不是 confirmed process；本阶段不命名 Process、"
            f"不判定 Grain（{GRAIN_UNDETERMINED_NOTE}）。"
        ),
        "rules_version": rules.version,
        "status_counts": status_counts,
        "strength_counts": strength_counts,
        "level_counts": level_counts,
        "processes": processes,
    }

    process_tables_payload = {
        "count": len(process_table_rows),
        "note": "表只是某个 process candidate 的证据载体，不等于该表只属于一个过程。",
        "status_counts": _status_counts(
            [str(item["status"]) for item in process_table_rows],
            [PROCESS_STATUS_CANDIDATE, OBJECT_STATUS_CONFIRMED],
        ),
        "tables": process_table_rows,
    }

    process_objects_payload = {
        "count": len(process_object_rows),
        "note": (
            "object 只以 participant 角色参与 process candidate，"
            "不表达 fact / dimension / owner，也不构成 Object ↔ Process 的简单映射。"
        ),
        "objects": process_object_rows,
    }

    result = BusinessProcessResult(
        signals=signals_payload,
        processes=processes_payload,
        process_tables=process_tables_payload,
        process_objects=process_objects_payload,
        analysis_dir=inputs.analysis_dir,
    )

    result.summary = render_process_summary(
        signals=signals_payload,
        processes=processes_payload,
        process_tables=process_tables_payload,
        process_objects=process_objects_payload,
        inventory_table_count=len(inputs.inventory_tables),
        object_table_count=len(table_objects),
        rules_version=rules.version,
        analysis_dir=inputs.analysis_dir,
    )
    result.checklist = render_process_review_checklist(processes, carry_over=process_reviews)

    return result


# ============================================================
# 产物写出与运行入口
# ============================================================


def write_business_processes(
    result: BusinessProcessResult,
    output_dir: Path,
) -> tuple[Path, ...]:
    """写出 M3.3 产物，返回路径列表（固定顺序）。

    只覆盖本模块声明的六个文件，不删除、不改写已有 M2 / M3 / M3.1 / M3.2 产物。
    """

    ensure_dir(output_dir)

    paths = {name: output_dir / name for name in OUTPUT_FILES}

    write_json(paths["process-signals.json"], result.signals)
    write_json(paths["processes.json"], result.processes)
    write_json(paths["process-tables.json"], result.process_tables)
    write_json(paths["process-objects.json"], result.process_objects)
    write_text(paths["process-summary.md"], result.summary)
    write_text(paths["process-review-checklist.md"], result.checklist)

    logger.info(
        "M3.3 产物已写出：%s",
        "，".join(_display_path(paths[name]) for name in OUTPUT_FILES),
    )

    return tuple(paths[name] for name in OUTPUT_FILES)


def run_business_process_analysis(
    *,
    analysis_dir: Path,
    output_dir: Path,
    rules_path: Path,
) -> BusinessProcessResult:
    """执行 M3.3 Business Process Candidate Analysis 并写出产物。

    只读 M2 / M3 / M3.1 / M3.2 产物与 process-rules 配置；
    输入缺失时直接报错，不自动回退去跑前置阶段。
    """

    # 旧布局把 M3.3 产物写在 business/：先清理遗留文件（process 清单搬迁保留人工列），
    # 保证同一阶段的产物只存在于 output_dir。
    relocate_legacy_artifacts(
        analysis_dir,
        output_dir,
        legacy_dir="business",
        output_files=OUTPUT_FILES,
        carryover_files=(Path(PROCESS_CHECKLIST_INPUT_FILE).name,),
    )

    rules = load_process_rules(rules_path)
    inputs = read_process_inputs(analysis_dir)

    result = build_business_processes(inputs, rules)
    result.analysis_dir = analysis_dir

    write_business_processes(result, output_dir)

    logger.info(
        "M3.3 Business Process Candidate Analysis 完成：signal=%s，process candidate=%s"
        "（weak=%s，moderate=%s，strong=%s），human_validated=%s",
        result.signal_count,
        result.process_count,
        result.process_strength_counts.get(PROCESS_STRENGTH_ORDER[0], 0),
        result.process_strength_counts.get(PROCESS_STRENGTH_ORDER[1], 0),
        result.process_strength_counts.get(PROCESS_STRENGTH_ORDER[2], 0),
        sum(1 for item in result.processes.get("processes") or [] if item.get("human_validated")),
    )

    return result

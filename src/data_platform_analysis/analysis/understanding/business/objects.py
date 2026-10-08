"""M3.2 Business Object & Relationship Analysis。

目标：

    从 M3 已经产出的 Object candidate + Table + Column + SQL + Lineage 中，
    建立「业务对象 — 表 — 字段 — 关系」的证据结构，产出 Object Graph 与
    Evidence，作为 M3.3 Business Process 候选分析的机器输入。

    Business Object
          ├── related tables
          │        ├── columns
          │        └── evidence
          └── relationships
                   ├── source / target evidence
                   ├── SQL evidence
                   └── lineage evidence

输入（只读 analysis/ 产物，不读 source/，不调 API，不修改 M2 / M3 / M3.1）：

    analysis/understanding/business/objects.json
    analysis/understanding/business/tables.json
    analysis/understanding/business/domains.json
    analysis/understanding/business/quality-assessment.json
    analysis/understanding/business/review-checklist.md
    analysis/inventory/tables.json
    analysis/inventory/columns.json
    analysis/evidence/sql/statements.json
    analysis/evidence/sql/table-references.json
    analysis/evidence/lineage/table-lineage.json
    analysis/evidence/lineage/core-table-candidates.json
    analysis/evidence/layer/assessments.json

输出：

    analysis/understanding/business/objects-registry.json
    analysis/understanding/business/object-tables.json
    analysis/understanding/business/object-relationships.json
    analysis/understanding/business/object-evidence-matrix.json
    analysis/understanding/business/object-graph.md

原则：

1. 不重新识别 Object：Object 清单只来自 objects.json；表名 / 字段名 / SQL 原文
   只用于统计既有 candidate 的证据，本模块绝不建立第二套 Object classifier。
   当前 Object 覆盖不足时只记录 limitation，不偷偷改 M3 词典。
2. Candidate ≠ Confirmed：默认 status = candidate；只有 review-checklist.md 中
   显式回填 confirmed / rejected / needs_discussion 才改变状态，
   没出现在清单中 ≠ confirmed。
3. Table ≠ Object：一个 Object 关联多张表，一张表也可以是多个 Object 的候选，
   不做「customer object = 一张表」的一对一假设。
4. Relationship ≠ 业务关系：关系只表达 co_occurrence / sql_reference / lineage
   三种表级证据，relationship_type 恒为 candidate，不产出 owns / contains /
   belongs_to / one-to-many，也不据此推导 Business Process 或 Grain。
5. core_candidate 沿用 M2.4 / M3 定义：lineage upstream / downstream 结构指标，
   不是业务价值判断。
6. 输入缺失 / JSON 非法 → 明确报错 + 非零退出，不自动回退执行其他阶段。
7. 输出 deterministic：无时间戳 / UUID / 随机抽样，全部稳定排序。
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

from .... import config
from ....io_utils import ensure_dir, write_json, write_text
from ...models import (
    BUSINESS_EVIDENCE_LINEAGE,
    BUSINESS_EVIDENCE_ORDER,
    BUSINESS_EVIDENCE_SQL,
    OBJECT_GRAPH_ROW_LIMIT,
    OBJECT_STATUS_CANDIDATE,
    OBJECT_STATUS_CONFIRMED,
    OBJECT_STATUS_NEEDS_DISCUSSION,
    OBJECT_STATUS_ORDER,
    OBJECT_STATUS_REJECTED,
    OBJECT_STATUS_SET,
    RELATIONSHIP_EVIDENCE_CO_OCCURRENCE,
    RELATIONSHIP_EVIDENCE_LINEAGE,
    RELATIONSHIP_EVIDENCE_ORDER,
    RELATIONSHIP_EVIDENCE_SQL,
    RELATIONSHIP_TYPE_CANDIDATE,
    BusinessObjectResult,
    evidence_strength,
    evidence_type_sort_key,
    numeric_id_sort_key,
)
from ...naming import qualify_table_ref
from ...reports import render_object_graph
from .quality import LAYER_UNDETERMINED

logger = logging.getLogger(__name__)

# ============================================================
# 输入与输出布局
# ============================================================

ARRAY_INPUT_FILES: tuple[tuple[str, str, str], ...] = (
    ("understanding/business/objects.json", "objects", "objects"),
    ("understanding/business/tables.json", "tables", "tables"),
    ("understanding/business/domains.json", "domains", "domains"),
    ("inventory/tables.json", "tables", "inventory_tables"),
    ("inventory/columns.json", "columns", "inventory_columns"),
    ("evidence/sql/statements.json", "statements", "statements"),
    ("evidence/sql/table-references.json", "references", "references"),
    ("evidence/lineage/table-lineage.json", "edges", "edges"),
    ("evidence/lineage/core-table-candidates.json", "candidates", "candidates"),
    ("evidence/layer/assessments.json", "assessments", "assessments"),
)
"""M3.2 依赖的数组型 M2 / M3 产物（相对 analysis/ 路径 → JSON 数组字段名 → 属性名）。"""

QUALITY_INPUT_FILE = "understanding/business/quality-assessment.json"
"""M3.1 质量基线（对象型 JSON，单独校验）。"""

CHECKLIST_INPUT_FILE = "understanding/business/review-checklist.md"
"""M3.1 人工复核清单：唯一的人工确认来源。"""

INPUT_FILES: tuple[str, ...] = (
    *(relative for relative, _key, _attr in ARRAY_INPUT_FILES),
    QUALITY_INPUT_FILE,
    CHECKLIST_INPUT_FILE,
)
"""M3.2 的全部输入（相对 analysis/ 路径）。"""

OUTPUT_FILES: tuple[str, ...] = (
    "objects-registry.json",
    "object-tables.json",
    "object-relationships.json",
    "object-evidence-matrix.json",
    "object-graph.md",
)
"""M3.2 产物文件名（固定顺序）；只覆盖这五个文件，不动已有 M2 / M3 / M3.1 产物。"""

CHECKLIST_REQUIRED_COLUMNS: tuple[str, ...] = (
    "table",
    "human domain",
    "human object",
    "status",
)
"""review-checklist.md 必须包含的列，缺一即报错。"""

_SPLIT_NAME_RE = re.compile(r"[,，;；、]+")
"""human domain / human object 单元格的分隔符。"""

_TABLE_SEPARATOR_RE = re.compile(r"^:?-+:?$")
"""Markdown 表格分隔行（例如 `| --- | --- |`）。"""

_EMPTY_NAME_VALUES: frozenset[str] = frozenset({"", "-", "—", "n/a", "na", "none", "null", "无"})
"""human 单元格里的空占位写法，解析时忽略。"""


class BusinessObjectsError(RuntimeError):
    """M3.2 无法继续的输入 / 结构错误。"""


def _display_path(path: Path) -> str:
    """日志与报告中展示的路径：项目根内用相对路径，其余保持绝对。"""

    try:
        return str(path.resolve().relative_to(config.PROJECT_ROOT))

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
    """与 M2 / M3 相同的表稳定排序键。"""

    return (
        numeric_id_sort_key(record.get("workspace_id")),
        str(record.get("project") or ""),
        str(record.get("schema") or ""),
        str(record.get("table") or ""),
        str(record.get("table_key") or ""),
    )


def _statement_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        numeric_id_sort_key(record.get("workspace_id")),
        numeric_id_sort_key(record.get("file_id")),
        numeric_id_sort_key(record.get("statement_id")),
    )


def _reference_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return _statement_sort_key(record)


def _edge_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        numeric_id_sort_key(record.get("workspace_id")),
        str(record.get("source_key") or ""),
        str(record.get("target_key") or ""),
    )


def _string_list(value: Any) -> list[str]:
    """取出字符串数组并去空白去重（保持首次出现顺序）。"""

    if not isinstance(value, list):
        return []

    seen: dict[str, None] = {}

    for item in value:
        if not isinstance(item, str):
            continue

        text = item.strip()

        if text:
            seen.setdefault(text, None)

    return list(seen)


def _dict_values(records: Any, key: str, path: Path) -> list[dict[str, Any]]:
    """校验并取出 JSON 数组里的对象条目。"""

    if not isinstance(records, list):
        raise BusinessObjectsError(f"缺少 {key} 数组：{path}")

    items: list[dict[str, Any]] = []

    for position, entry in enumerate(records):
        if not isinstance(entry, dict):
            raise BusinessObjectsError(f"{key}[{position}] 不是对象：{path}")

        items.append(entry)

    return items


def _evidence_entry_sort_key(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    """候选证据条目的稳定排序键（列级 → 语句级 → 关键词）。"""

    return (
        str(entry.get("table_key") or ""),
        str(entry.get("column_name") or ""),
        numeric_id_sort_key(entry.get("workspace_id")),
        numeric_id_sort_key(entry.get("file_id")),
        numeric_id_sort_key(entry.get("statement_id")),
        str(entry.get("keyword") or ""),
        str(entry.get("value") or ""),
    )


def _group_evidence(evidence: Sequence[Any]) -> dict[str, list[dict[str, Any]]]:
    """把 M3 候选证据按 type 分组，组内去重并稳定排序。

    组顺序沿用 BUSINESS_EVIDENCE_ORDER（直接证据在前，派生证据在后），
    未登记的 type 排在最后，不丢证据。
    """

    buckets: dict[str, dict[str, dict[str, Any]]] = {}

    for entry in evidence:
        if not isinstance(entry, dict):
            continue

        kind = str(entry.get("type") or "") or "unknown"
        identity = json.dumps(entry, ensure_ascii=False, sort_keys=True, default=str)
        buckets.setdefault(kind, {}).setdefault(identity, dict(entry))

    return {
        kind: sorted(buckets[kind].values(), key=_evidence_entry_sort_key)
        for kind in sorted(buckets, key=lambda item: (evidence_type_sort_key(item), item))
    }


# ============================================================
# review-checklist 解析（唯一的人工确认来源）
# ============================================================


@dataclass
class HumanReview:
    """review-checklist.md 中一行人工回填结果。

    status 只保留被认可的取值（confirmed / rejected / needs_discussion），
    其余（pending / done / 空）一律为 None，表示「没有人工确认」；
    status_raw 保留原文，供报告追溯。
    """

    table_key: str
    human_domains: tuple[str, ...] = ()
    human_objects: tuple[str, ...] = ()
    status: str | None = None
    status_raw: str = ""


def _split_names(value: str) -> tuple[str, ...]:
    """拆解 human domain / human object 单元格，归一化后稳定排序。"""

    names: set[str] = set()

    for part in _SPLIT_NAME_RE.split(value or ""):
        name = part.strip().strip("*`").strip().casefold()

        if name in _EMPTY_NAME_VALUES:
            continue

        names.add(name)

    return tuple(sorted(names))


def _normalize_status(value: str) -> str | None:
    """把 status 单元格归一化成受支持的状态，其余返回 None。"""

    text = (value or "").strip().casefold().replace(" ", "_").replace("-", "_")

    return text if text in OBJECT_STATUS_SET else None


def _split_row(line: str) -> list[str]:
    """按 | 拆分 Markdown 表格行并去除首尾空白。"""

    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _cell(cells: list[str], position: int) -> str:
    """按列位置取单元格值，越界返回空串。"""

    return cells[position].strip() if position < len(cells) else ""


def parse_review_checklist(text: str, *, source: Path) -> dict[str, HumanReview]:
    """解析 review-checklist.md，返回 table_key(casefold) → 人工回填结果。

    表结构非法（找不到必需列）时报错；重复的 table 行只保留首个，保证确定性。
    """

    lines = text.splitlines()
    header_index = -1
    columns: dict[str, int] = {}

    for index, line in enumerate(lines):
        stripped = line.strip()

        if not stripped.startswith("|"):
            continue

        cells = [cell.casefold() for cell in _split_row(stripped)]

        if not cells or cells[0] != "table":
            continue

        found = {name: cells.index(name) for name in CHECKLIST_REQUIRED_COLUMNS if name in cells}

        if len(found) == len(CHECKLIST_REQUIRED_COLUMNS):
            header_index = index
            columns = found
            break

    if header_index < 0:
        raise BusinessObjectsError(
            "review-checklist.md 缺少必需列（"
            f"{'、'.join(CHECKLIST_REQUIRED_COLUMNS)}）：{_display_path(source)}"
        )

    table_column = columns["table"]
    reviews: dict[str, HumanReview] = {}
    skipped = 0

    for line in lines[header_index + 1 :]:
        stripped = line.strip()

        if not stripped.startswith("|"):
            continue

        cells = _split_row(stripped)

        if table_column >= len(cells):
            continue

        table_cell = cells[table_column].strip()

        # 分隔行与重复表头不是数据行。
        if _TABLE_SEPARATOR_RE.match(table_cell) or table_cell.casefold() == "table":
            continue

        if not table_cell:
            continue

        lookup_key = table_cell.casefold()

        if lookup_key in reviews:
            skipped += 1
            continue

        status_cell = _cell(cells, columns["status"])

        reviews[lookup_key] = HumanReview(
            table_key=table_cell,
            human_domains=_split_names(_cell(cells, columns["human domain"])),
            human_objects=_split_names(_cell(cells, columns["human object"])),
            status=_normalize_status(status_cell),
            status_raw=status_cell,
        )

    if skipped:
        logger.warning(
            "review-checklist.md 有 %s 行 table 重复，只保留首次出现：%s",
            skipped,
            _display_path(source),
        )

    logger.info(
        "review-checklist.md 已解析：%s 行人工回填（其中 %s 行有认可的 status）",
        len(reviews),
        sum(1 for item in reviews.values() if item.status),
    )

    return reviews


def _resolve_machine_status(
    obj: str,
    review: HumanReview | None,
) -> str:
    """机器 candidate 在人工回填后的状态。

    规则（确定性）：

    1. 没有清单行 → candidate（未回填 ≠ confirmed）。
    2. confirmed：只确认 human object 单元格里显式列出的 Object；
       只确认了 human domain 或留空，不推断到 Object。
    3. rejected / needs_discussion：human object 留空时作用于该表全部
       machine candidate；列出了 Object 时只作用于列出的 Object。
    """

    if review is None or review.status is None:
        return OBJECT_STATUS_CANDIDATE

    if review.status == OBJECT_STATUS_CONFIRMED:
        return OBJECT_STATUS_CONFIRMED if obj in review.human_objects else OBJECT_STATUS_CANDIDATE

    if not review.human_objects or obj in review.human_objects:
        return review.status

    return OBJECT_STATUS_CANDIDATE


def _aggregate_status(statuses: Sequence[str]) -> str:
    """把一个 Object 的全部 association 状态聚合成 Object 级状态。

    全部 confirmed → confirmed；全部 rejected → rejected；
    出现 needs_discussion → needs_discussion；其余（含混合）→ candidate。
    """

    if not statuses:
        return OBJECT_STATUS_CANDIDATE

    if all(item == OBJECT_STATUS_CONFIRMED for item in statuses):
        return OBJECT_STATUS_CONFIRMED

    if all(item == OBJECT_STATUS_REJECTED for item in statuses):
        return OBJECT_STATUS_REJECTED

    if OBJECT_STATUS_NEEDS_DISCUSSION in statuses:
        return OBJECT_STATUS_NEEDS_DISCUSSION

    return OBJECT_STATUS_CANDIDATE


def _status_counts(statuses: Sequence[str]) -> dict[str, int]:
    """按 OBJECT_STATUS_ORDER 输出状态计数（固定顺序，缺项补 0）。"""

    counts = {status: 0 for status in OBJECT_STATUS_ORDER}

    for status in statuses:
        counts[status] = counts.get(status, 0) + 1

    return counts


# ============================================================
# M2 / M3 / M3.1 产物读取
# ============================================================


@dataclass
class ObjectInputs:
    """M3.2 读取到的 M2 / M3 / M3.1 产物（只做结构校验，不改写）。"""

    objects: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    domains: list[dict[str, Any]] = field(default_factory=list)
    inventory_tables: list[dict[str, Any]] = field(default_factory=list)
    inventory_columns: list[dict[str, Any]] = field(default_factory=list)
    statements: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    assessments: list[dict[str, Any]] = field(default_factory=list)
    quality_summary: dict[str, Any] = field(default_factory=dict)
    checklist_text: str = ""
    checklist_path: Path = field(default_factory=Path)
    analysis_dir: Path = field(default_factory=Path)


def read_object_inputs(analysis_dir: Path) -> ObjectInputs:
    """读取 M3.2 依赖的全部 M2 / M3 / M3.1 产物。

    任何输入缺失或 JSON 非法都明确报错，
    不自动回退执行 analyze / analyze --stage。
    """

    missing = [relative for relative in INPUT_FILES if not (analysis_dir / relative).exists()]

    if missing:
        raise BusinessObjectsError(
            "M2 / M3 / M3.1 产物缺失，无法执行 M3.2 Business Object & Relationship Analysis："
            f"{'、'.join(missing)}（目录：{_display_path(analysis_dir)}）；"
            "请先执行 analyze --stage evidence 生成 M2 产物、"
            "analyze --stage understanding 生成 M3 ~ M3.5 产物"
        )

    def load(relative: str, key: str) -> list[dict[str, Any]]:
        path = analysis_dir / relative

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))

        except json.JSONDecodeError as exc:
            raise BusinessObjectsError(f"产物不是合法的 JSON：{path}（{exc}）") from exc

        if not isinstance(raw, dict):
            raise BusinessObjectsError(f"产物根节点不是对象：{path}")

        return _dict_values(raw.get(key), key, path)

    inputs = ObjectInputs()
    inputs.analysis_dir = analysis_dir
    inputs.checklist_path = analysis_dir / CHECKLIST_INPUT_FILE

    for relative, key, attr in ARRAY_INPUT_FILES:
        setattr(inputs, attr, load(relative, key))

    quality_path = analysis_dir / QUALITY_INPUT_FILE

    try:
        quality_raw = json.loads(quality_path.read_text(encoding="utf-8"))

    except json.JSONDecodeError as exc:
        raise BusinessObjectsError(f"产物不是合法的 JSON：{quality_path}（{exc}）") from exc

    if not isinstance(quality_raw, dict) or not isinstance(quality_raw.get("summary"), dict):
        raise BusinessObjectsError(f"产物缺少 summary 对象：{quality_path}")

    inputs.quality_summary = dict(quality_raw["summary"])

    checklist_path = inputs.checklist_path

    try:
        inputs.checklist_text = checklist_path.read_text(encoding="utf-8")

    except OSError as exc:
        raise BusinessObjectsError(f"无法读取人工复核清单：{checklist_path}（{exc}）") from exc

    logger.info(
        "M3.2 输入已读取：%s（business table=%s，reference=%s，edge=%s，assessment=%s）",
        _display_path(analysis_dir),
        len(inputs.tables),
        len(inputs.references),
        len(inputs.edges),
        len(inputs.assessments),
    )

    return inputs


# ============================================================
# 索引
# ============================================================


def _workspace_projects(tables: Sequence[Mapping[str, Any]]) -> dict[int, str]:
    """workspace_id → project，用于补齐 SQL 中的裸表引用。"""

    projects: dict[int, str] = {}

    for table in sorted(tables, key=_table_sort_key):
        workspace_id = table.get("workspace_id")
        project = _text(table.get("project"))

        if isinstance(workspace_id, int) and project:
            projects.setdefault(workspace_id, project)

    return projects


def _index_candidate_layers(assessments: Sequence[Mapping[str, Any]]) -> dict[str, str | None]:
    """M2.2 candidate_layer 索引：table_identifier(casefold) → candidate_layer。"""

    index: dict[str, str | None] = {}

    for record in assessments:
        identifier = _text(record.get("table_identifier")) or _text(record.get("table_name"))

        if not identifier:
            continue

        index.setdefault(identifier.casefold(), _text(record.get("candidate_layer")))

    return index


def _index_core_keys(
    tables: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
) -> set[str]:
    """核心表候选索引：M2.4 core-table-candidates ∪ M3 tables.json 的 is_core_candidate。"""

    keys = {key.casefold() for record in candidates if (key := _text(record.get("table_key")))}

    for record in tables:
        if record.get("is_core_candidate"):
            key = _text(record.get("table_key"))

            if key:
                keys.add(key.casefold())

    return keys


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


def _index_domains(domains: Sequence[Mapping[str, Any]]) -> dict[str, tuple[str, ...]]:
    """table_key(casefold) → 该表的 Domain 候选（稳定排序）。"""

    index: dict[str, set[str]] = {}

    for record in domains:
        domain = _text(record.get("domain"))

        if not domain:
            continue

        tables = record.get("tables")

        if not isinstance(tables, list):
            continue

        for entry in tables:
            if not isinstance(entry, dict):
                continue

            key = _text(entry.get("table_key"))

            if key:
                index.setdefault(key.casefold(), set()).add(domain)

    return {key: tuple(sorted(values)) for key, values in index.items()}


def _table_flags(
    tables: Sequence[Mapping[str, Any]],
) -> tuple[set[str], set[str]]:
    """按 M3.1 口径返回 UNKNOWN 表与 AMBIGUOUS 表（table_key casefold）。"""

    unknown: set[str] = set()
    ambiguous: set[str] = set()

    for record in tables:
        key = _text(record.get("table_key"))

        if not key:
            continue

        lookup_key = key.casefold()
        domains = [item for item in record.get("domain_candidates") or [] if isinstance(item, dict)]
        objects = [
            item
            for item in record.get("business_object_candidates") or []
            if isinstance(item, dict)
        ]

        if not domains and not objects:
            unknown.add(lookup_key)

        if len(domains) > 1 or len(objects) > 1:
            ambiguous.add(lookup_key)

    return unknown, ambiguous


def _referenced_table_keys(
    references: Sequence[Mapping[str, Any]],
    workspace_projects: Mapping[int, str],
) -> set[str]:
    """被 SQL 引用的表（补齐裸表名后 casefold）。"""

    keys: set[str] = set()

    for record in references:
        workspace_id = record.get("workspace_id")
        project = workspace_projects.get(workspace_id) if isinstance(workspace_id, int) else None

        for field_name in ("source_tables", "target_tables"):
            for item in _string_list(record.get(field_name)):
                keys.add(qualify_table_ref(item, project).casefold())

    return keys


def _lineage_table_keys(edges: Sequence[Mapping[str, Any]]) -> set[str]:
    """参与血缘的表（source_key / target_key casefold）。"""

    keys: set[str] = set()

    for record in edges:
        for field_name in ("source_key", "target_key"):
            value = _text(record.get(field_name))

            if value:
                keys.add(value.casefold())

    return keys


# ============================================================
# Object ↔ Table association
# ============================================================


def _has_human_signal(review: HumanReview | None) -> bool:
    """清单行是否给出了可用的人工信息（认可的 status 或人工填写的名称）。"""

    if review is None:
        return False

    return bool(review.status or review.human_objects or review.human_domains)


def _build_associations(
    *,
    tables: Sequence[Mapping[str, Any]],
    reviews: Mapping[str, HumanReview],
    candidate_layer_by_key: Mapping[str, str | None],
    core_keys: set[str],
) -> list[dict[str, Any]]:
    """构建 Object ↔ Table association（一个 Object × 一张表一条记录）。"""

    associations: list[dict[str, Any]] = []
    unmatched_reviews = set(reviews)
    human_object_tables = 0

    for record in sorted(tables, key=_table_sort_key):
        table_key = str(record.get("table_key") or "")
        lookup_key = table_key.casefold()
        review = reviews.get(lookup_key)

        if review is not None:
            unmatched_reviews.discard(lookup_key)

        candidates = _object_candidates(record)
        machine_objects = {obj for obj, _confidence, _evidence in candidates}
        human_objects = set(review.human_objects) if review is not None else set()
        entries: list[tuple[str, str | None, list[dict[str, Any]], str]] = []

        for obj, confidence, evidence in sorted(candidates, key=lambda item: item[0]):
            entries.append((obj, confidence, evidence, _resolve_machine_status(obj, review)))

        # 人工确认 / 待讨论的 Object 可能不在机器候选里（例如 P1 的 UNKNOWN 表），
        # 这类 association 只来自人工回填，不经过任何机器分类器。
        extra_objects = sorted(
            human_objects - machine_objects
            if review is not None
            and review.status
            in {
                OBJECT_STATUS_CONFIRMED,
                OBJECT_STATUS_NEEDS_DISCUSSION,
            }
            else set()
        )

        if extra_objects:
            human_object_tables += 1

            for obj in extra_objects:
                extra_status = (
                    review.status if review is not None else None
                ) or OBJECT_STATUS_CANDIDATE
                entries.append((obj, None, [], extra_status))

        if not entries:
            continue

        human_payload: dict[str, Any] | None = None

        if _has_human_signal(review) and review is not None:
            human_payload = {
                "human_domain": list(review.human_domains),
                "human_object": list(review.human_objects),
                "status_raw": review.status_raw,
            }

        candidate_layer = candidate_layer_by_key.get(lookup_key)
        candidate_layer = (
            candidate_layer
            if candidate_layer is not None
            else _text(record.get("candidate_sub_layer"))
        )

        for obj, confidence, evidence, status in entries:
            association: dict[str, Any] = {
                "object": obj,
                "table_key": table_key,
                "workspace_id": int(record.get("workspace_id") or 0),
                "project": str(record.get("project") or ""),
                "table_name": str(record.get("table") or ""),
                "warehouse_layer": _text(record.get("warehouse_layer")),
                "candidate_layer": candidate_layer,
                "core_candidate": lookup_key in core_keys,
                "confidence": confidence,
                "evidence": _group_evidence(evidence),
                "status": status,
            }

            if human_payload is not None:
                association["human"] = dict(human_payload)

            associations.append(association)

    if unmatched_reviews:
        logger.warning(
            "review-checklist.md 有 %s 行的 table 不在 business/tables.json 中，已忽略：%s",
            len(unmatched_reviews),
            "、".join(sorted(reviews[key].table_key for key in unmatched_reviews)[:5]),
        )

    if human_object_tables:
        logger.info(
            "M3.2 读到 %s 张表的人工 Object 回填（不经机器分类器）",
            human_object_tables,
        )

    return sorted(associations, key=_association_sort_key)


def _object_candidates(
    record: Mapping[str, Any],
) -> list[tuple[str, str | None, list[dict[str, Any]]]]:
    """从 business/tables.json 取出一张表的 Object candidate（归一化 + 去重）。"""

    slots: dict[str, tuple[str, str | None, list[dict[str, Any]]]] = {}

    for item in record.get("business_object_candidates") or []:
        if not isinstance(item, dict):
            continue

        obj = _text(item.get("object"))

        if not obj:
            continue

        normalized = obj.casefold()
        evidence = [entry for entry in item.get("evidence") or [] if isinstance(entry, dict)]

        if normalized in slots:
            existing = slots[normalized]
            slots[normalized] = (
                existing[0],
                existing[1],
                [*existing[2], *evidence],
            )

        else:
            slots[normalized] = (normalized, _text(item.get("confidence")), evidence)

    return [slots[key] for key in sorted(slots)]


def _association_sort_key(association: Mapping[str, Any]) -> tuple[Any, ...]:
    """association 稳定排序：Object 升序 → 表稳定排序键。"""

    return (
        str(association.get("object") or ""),
        numeric_id_sort_key(association.get("workspace_id")),
        str(association.get("project") or ""),
        str(association.get("table_name") or ""),
        str(association.get("table_key") or ""),
    )


# ============================================================
# Business Object Registry
# ============================================================


def _build_registry(
    *,
    associations: Sequence[Mapping[str, Any]],
    objects: Sequence[Mapping[str, Any]],
    table_comment_flags: Mapping[str, bool],
    column_comment_flags: Mapping[str, bool],
    referenced_keys: set[str],
    lineage_keys: set[str],
) -> dict[str, Any]:
    """把 Object candidate 统一整理成 registry（不产生 winner，不做重新分类）。"""

    names: dict[str, str | None] = {}

    for record in sorted(objects, key=lambda item: str(item.get("object") or "").casefold()):
        obj = _text(record.get("object"))

        if obj:
            names.setdefault(obj.casefold(), _text(record.get("name")))

    grouped: dict[str, list[Mapping[str, Any]]] = {}

    for association in associations:
        grouped.setdefault(str(association.get("object") or ""), []).append(association)

    for obj in sorted(grouped):
        names.setdefault(obj, None)

    entries: list[dict[str, Any]] = []

    for obj in sorted(names):
        rows = grouped.get(obj, [])
        statuses = [str(row.get("status") or OBJECT_STATUS_CANDIDATE) for row in rows]
        evidence_type_counts = {kind: 0 for kind in BUSINESS_EVIDENCE_ORDER}
        entry_count = 0
        sql_evidence_tables = 0
        lineage_evidence_tables = 0

        for row in rows:
            evidence = row.get("evidence") or {}

            for kind, values in evidence.items():
                evidence_type_counts[kind] = evidence_type_counts.get(kind, 0) + len(values)
                entry_count += len(values)

            sql_evidence_tables += int(bool(evidence.get(BUSINESS_EVIDENCE_SQL)))
            lineage_evidence_tables += int(bool(evidence.get(BUSINESS_EVIDENCE_LINEAGE)))

        lookup_keys = [str(row.get("table_key") or "").casefold() for row in rows]
        ordered_type_counts = {kind: evidence_type_counts[kind] for kind in BUSINESS_EVIDENCE_ORDER}

        for kind in sorted(
            key for key in evidence_type_counts if key not in BUSINESS_EVIDENCE_ORDER
        ):
            ordered_type_counts[kind] = evidence_type_counts[kind]

        entries.append(
            {
                "object": obj,
                "name": names.get(obj),
                "table_count": len(rows),
                "candidate_table_count": sum(
                    1 for status in statuses if status == OBJECT_STATUS_CANDIDATE
                ),
                "core_table_count": sum(1 for row in rows if row.get("core_candidate")),
                "status_counts": _status_counts(statuses),
                "status": _aggregate_status(statuses),
                "evidence_summary": {
                    "association_count": len(rows),
                    "evidence_entry_count": entry_count,
                    "evidence_type_counts": ordered_type_counts,
                    "table_count_with_table_comment": sum(
                        1 for key in lookup_keys if table_comment_flags.get(key, False)
                    ),
                    "table_count_with_column_comment": sum(
                        1 for key in lookup_keys if column_comment_flags.get(key, False)
                    ),
                    "table_count_with_sql_evidence": sql_evidence_tables,
                    "table_count_with_lineage_evidence": lineage_evidence_tables,
                    "table_count_referenced_by_sql": sum(
                        1 for key in lookup_keys if key in referenced_keys
                    ),
                    "table_count_in_lineage": sum(1 for key in lookup_keys if key in lineage_keys),
                },
                "tables": [str(row.get("table_key") or "") for row in rows],
            }
        )

    return {
        "count": len(entries),
        "note": (
            "Object 清单只来自 analysis/understanding/business/objects.json"
            "（+ 人工回填的新 Object），"
            "M3.2 不做第二次 Object 分类；status 默认 candidate，"
            "只有 review-checklist.md 显式回填 confirmed / rejected / needs_discussion 才会改变，"
            "未出现在清单中 ≠ confirmed；tables 按表稳定排序，一个 Object 可以关联多张表。"
        ),
        "status_counts": _status_counts([entry["status"] for entry in entries]),
        "objects": entries,
    }


# ============================================================
# Object Relationship Candidates
# ============================================================


def _evidence_entry(
    *,
    evidence_type: str,
    source_object: str,
    target_object: str,
    source_table: str,
    workspace_id: Any,
    target_table: str | None = None,
    file_id: Any = None,
    statement_id: Any = None,
) -> tuple[str, dict[str, Any]]:
    """构造一条关系证据：返回 (稳定标识 evidence_id, 证据条目)。"""

    if evidence_type == RELATIONSHIP_EVIDENCE_CO_OCCURRENCE:
        evidence_id = f"co:{source_table}"

    elif evidence_type == RELATIONSHIP_EVIDENCE_SQL:
        evidence_id = f"sql:{workspace_id}:{file_id}:{statement_id}:{source_table}->{target_table}"

    else:
        evidence_id = f"lineage:{workspace_id}:{source_table}->{target_table}"

    entry: dict[str, Any] = {
        "evidence_id": evidence_id,
        "source_object": source_object,
        "target_object": target_object,
        "source_table": source_table,
        "workspace_id": workspace_id,
    }

    if target_table is not None:
        entry["target_table"] = target_table

    if evidence_type == RELATIONSHIP_EVIDENCE_SQL:
        entry["file_id"] = file_id
        entry["statement_id"] = statement_id

    return evidence_id, entry


def _build_relationships(
    *,
    associations: Sequence[Mapping[str, Any]],
    table_meta: Mapping[str, tuple[str, int]],
    references: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    workspace_projects: Mapping[int, str],
    core_keys: set[str],
) -> dict[str, Any]:
    """从 co_occurrence / sql_reference / lineage 推导 Object relationship 候选。

    关系身份是 (object_a, object_b) 的排序对，三种证据合并进同一条记录；
    只表达「表级证据存在」，relationship_type 恒为 candidate。
    """

    table_objects: dict[str, list[str]] = {}

    for association in associations:
        if str(association.get("status")) == OBJECT_STATUS_REJECTED:
            continue

        obj = str(association.get("object") or "")
        lookup_key = str(association.get("table_key") or "").casefold()

        if not obj or not lookup_key:
            continue

        objects = table_objects.setdefault(lookup_key, [])

        if obj not in objects:
            objects.append(obj)

    for lookup_key in table_objects:
        table_objects[lookup_key] = sorted(table_objects[lookup_key])

    buckets: dict[tuple[str, str], dict[str, dict[str, dict[str, Any]]]] = {}

    def slot(pair: tuple[str, str], evidence_type: str) -> dict[str, dict[str, Any]]:
        return buckets.setdefault(pair, {kind: {} for kind in RELATIONSHIP_EVIDENCE_ORDER})[
            evidence_type
        ]

    def canonical(lookup_key: str) -> str:
        meta = table_meta.get(lookup_key)
        return meta[0] if meta else lookup_key

    def workspace_of(lookup_key: str) -> Any:
        meta = table_meta.get(lookup_key)
        return meta[1] if meta else None

    # Level 1：同一张表同时是两个 Object 的候选。
    for lookup_key in sorted(table_objects):
        objects = table_objects[lookup_key]

        if len(objects) < 2:
            continue

        table_key = canonical(lookup_key)
        workspace_id = workspace_of(lookup_key)

        for source_object, target_object in combinations(objects, 2):
            evidence_id, entry = _evidence_entry(
                evidence_type=RELATIONSHIP_EVIDENCE_CO_OCCURRENCE,
                source_object=source_object,
                target_object=target_object,
                source_table=table_key,
                workspace_id=workspace_id,
            )
            slot((source_object, target_object), RELATIONSHIP_EVIDENCE_CO_OCCURRENCE).setdefault(
                evidence_id, entry
            )

    # Level 2：同一条 SQL 语句同时引用了两个表。
    for reference in sorted(references, key=_reference_sort_key):
        workspace_id = reference.get("workspace_id")
        project = workspace_projects.get(workspace_id) if isinstance(workspace_id, int) else None
        file_id = reference.get("file_id")
        statement_id = reference.get("statement_id")

        source_keys = sorted(
            {
                qualify_table_ref(item, project).casefold()
                for item in _string_list(reference.get("source_tables"))
            }
        )
        target_keys = sorted(
            {
                qualify_table_ref(item, project).casefold()
                for item in _string_list(reference.get("target_tables"))
            }
        )

        for source_key in source_keys:
            source_objects = table_objects.get(source_key, [])

            if not source_objects:
                continue

            for target_key in target_keys:
                if target_key == source_key:
                    continue

                target_objects = table_objects.get(target_key, [])

                if not target_objects:
                    continue

                source_table = canonical(source_key)
                target_table = canonical(target_key)

                for source_object in source_objects:
                    for target_object in target_objects:
                        if source_object == target_object:
                            continue

                        left, right = sorted((source_object, target_object))
                        pair = (left, right)
                        evidence_id, entry = _evidence_entry(
                            evidence_type=RELATIONSHIP_EVIDENCE_SQL,
                            source_object=source_object,
                            target_object=target_object,
                            source_table=source_table,
                            target_table=target_table,
                            workspace_id=workspace_id,
                            file_id=file_id,
                            statement_id=statement_id,
                        )
                        slot(pair, RELATIONSHIP_EVIDENCE_SQL).setdefault(evidence_id, entry)

    # Level 3：一条表级血缘连接了两个表。
    for edge in sorted(edges, key=_edge_sort_key):
        source_raw = _text(edge.get("source_key"))
        target_raw = _text(edge.get("target_key"))

        if not source_raw or not target_raw:
            continue

        source_key = source_raw.casefold()
        target_key = target_raw.casefold()

        if source_key == target_key:
            continue

        source_objects = table_objects.get(source_key, [])
        target_objects = table_objects.get(target_key, [])

        if not source_objects or not target_objects:
            continue

        workspace_id = edge.get("workspace_id")
        source_table = canonical(source_key)
        target_table = canonical(target_key)

        for source_object in source_objects:
            for target_object in target_objects:
                if source_object == target_object:
                    continue

                left, right = sorted((source_object, target_object))
                pair = (left, right)
                evidence_id, entry = _evidence_entry(
                    evidence_type=RELATIONSHIP_EVIDENCE_LINEAGE,
                    source_object=source_object,
                    target_object=target_object,
                    source_table=source_table,
                    target_table=target_table,
                    workspace_id=workspace_id,
                )
                slot(pair, RELATIONSHIP_EVIDENCE_LINEAGE).setdefault(evidence_id, entry)

    relationships: list[dict[str, Any]] = []
    distribution: dict[str, dict[str, int]] = {
        evidence_type: {"entry_count": 0, "relationship_count": 0}
        for evidence_type in RELATIONSHIP_EVIDENCE_ORDER
    }

    for pair in sorted(buckets):
        by_type = buckets[pair]
        evidence: dict[str, list[dict[str, Any]]] = {}
        counts: dict[str, int] = {}
        present: list[str] = []
        core_related = False

        for evidence_type in RELATIONSHIP_EVIDENCE_ORDER:
            entries = by_type.get(evidence_type, {})
            ordered = sorted(entries.values(), key=_evidence_entry_sort_key)
            evidence[evidence_type] = ordered
            counts[evidence_type] = len(ordered)

            if ordered:
                present.append(evidence_type)
                distribution[evidence_type]["entry_count"] += len(ordered)
                distribution[evidence_type]["relationship_count"] += 1

                for entry in ordered:
                    for field_name in ("source_table", "target_table"):
                        table = _text(entry.get(field_name))

                        if table and table.casefold() in core_keys:
                            core_related = True

        diversity = len(present)

        relationships.append(
            {
                "object_a": pair[0],
                "object_b": pair[1],
                "relationship_type": RELATIONSHIP_TYPE_CANDIDATE,
                "evidence_types": present,
                "evidence_diversity": diversity,
                "evidence_strength": evidence_strength(diversity),
                "evidence_count": counts,
                "core_related": core_related,
                "evidence": evidence,
            }
        )

    statement_refs = {
        (
            str(entry.get("workspace_id")),
            str(entry.get("file_id")),
            str(entry.get("statement_id")),
        )
        for relationship in relationships
        for entry in relationship["evidence"][RELATIONSHIP_EVIDENCE_SQL]
    }

    return {
        "count": len(relationships),
        "note": (
            "relationship_type 恒为 candidate：co_occurrence / sql_reference / lineage "
            "只是表级证据，不等于业务关系，不产出 owns / contains / belongs_to / "
            "one-to-many / many-to-many；evidence_strength 只反映证据类型数"
            "（1=weak，2=moderate，3=strong），不是 confidence / probability；"
            "core_related 表示至少一个 endpoint 关联核心表候选"
            "（lineage 结构指标，不是业务价值判断）。"
        ),
        "evidence_distribution": distribution,
        "sql_statement_count": len(statement_refs),
        "relationships": relationships,
    }


# ============================================================
# Object Evidence Matrix
# ============================================================


def _build_matrix(
    *,
    associations: Sequence[Mapping[str, Any]],
    relationships: Sequence[Mapping[str, Any]],
    domain_by_table: Mapping[str, tuple[str, ...]],
    unknown_keys: set[str],
    ambiguous_keys: set[str],
) -> dict[str, Any]:
    """按 Object 汇总事实口径的证据矩阵（只汇总，不解释）。"""

    grouped: dict[str, list[Mapping[str, Any]]] = {}

    for association in associations:
        grouped.setdefault(str(association.get("object") or ""), []).append(association)

    relationship_counts = {obj: 0 for obj in grouped}

    for relationship in relationships:
        for field_name in ("object_a", "object_b"):
            obj = str(relationship.get(field_name) or "")
            relationship_counts[obj] = relationship_counts.get(obj, 0) + 1

    rows: list[dict[str, Any]] = []

    for obj in sorted(grouped):
        rows_associations = grouped[obj]
        layers: set[str] = set()
        domains: set[str] = set()
        evidence_types: set[str] = set()
        unknown_count = 0
        ambiguous_count = 0

        for row in rows_associations:
            layers.add(str(row.get("candidate_layer") or LAYER_UNDETERMINED))
            lookup_key = str(row.get("table_key") or "").casefold()
            domains.update(domain_by_table.get(lookup_key, ()))
            unknown_count += int(lookup_key in unknown_keys)
            ambiguous_count += int(lookup_key in ambiguous_keys)

            for kind, values in (row.get("evidence") or {}).items():
                if values:
                    evidence_types.add(kind)

        statuses = [str(row.get("status") or OBJECT_STATUS_CANDIDATE) for row in rows_associations]

        rows.append(
            {
                "object": obj,
                "table_count": len(rows_associations),
                "core_table_count": sum(
                    1 for row in rows_associations if row.get("core_candidate")
                ),
                "candidate_layers": sorted(layers),
                "domains": sorted(domains),
                "evidence_types": sorted(
                    evidence_types,
                    key=lambda item: (evidence_type_sort_key(item), item),
                ),
                "unknown_table_count": unknown_count,
                "ambiguous_table_count": ambiguous_count,
                "status_counts": _status_counts(statuses),
                "relationship_count": relationship_counts.get(obj, 0),
            }
        )

    return {
        "count": len(rows),
        "note": (
            "只做事实汇总，不含业务解释：unknown / ambiguous 沿用 M3.1 口径"
            "（unknown = 该表没有任何 Domain / Object 候选，因此人工回填的 Object "
            "才会落在 unknown 表上；ambiguous = 多 Domain 或多 Object 候选）；"
            "candidate_layers 是 M2.2 candidate_layer 的去重取值，"
            "「(未确定)」表示该表没有层级证据。"
        ),
        "objects": rows,
    }


# ============================================================
# 构建入口
# ============================================================


def build_business_objects(inputs: ObjectInputs) -> BusinessObjectResult:
    """从 M2 / M3 / M3.1 产物构建 M3.2 结果（不读写文件）。"""

    tables = sorted(inputs.tables, key=_table_sort_key)
    reviews = parse_review_checklist(inputs.checklist_text, source=inputs.checklist_path)

    candidate_layer_by_key = _index_candidate_layers(inputs.assessments)
    core_keys = _index_core_keys(tables, inputs.candidates)
    table_comment_flags = _index_table_comments(inputs.inventory_tables)
    column_comment_flags = _index_column_comments(inputs.inventory_columns)
    domain_by_table = _index_domains(inputs.domains)
    unknown_keys, ambiguous_keys = _table_flags(tables)
    workspace_projects = _workspace_projects(inputs.inventory_tables)
    referenced_keys = _referenced_table_keys(inputs.references, workspace_projects)
    lineage_keys = _lineage_table_keys(inputs.edges)

    table_meta: dict[str, tuple[str, int]] = {}

    for record in tables:
        key = _text(record.get("table_key"))

        if key:
            table_meta.setdefault(
                key.casefold(),
                (key, int(record.get("workspace_id") or 0)),
            )

    associations = _build_associations(
        tables=tables,
        reviews=reviews,
        candidate_layer_by_key=candidate_layer_by_key,
        core_keys=core_keys,
    )

    registry = _build_registry(
        associations=associations,
        objects=inputs.objects,
        table_comment_flags=table_comment_flags,
        column_comment_flags=column_comment_flags,
        referenced_keys=referenced_keys,
        lineage_keys=lineage_keys,
    )

    relationships = _build_relationships(
        associations=associations,
        table_meta=table_meta,
        references=inputs.references,
        edges=inputs.edges,
        workspace_projects=workspace_projects,
        core_keys=core_keys,
    )

    matrix = _build_matrix(
        associations=associations,
        relationships=relationships.get("relationships") or [],
        domain_by_table=domain_by_table,
        unknown_keys=unknown_keys,
        ambiguous_keys=ambiguous_keys,
    )

    associations_payload = {
        "count": len(associations),
        "note": (
            "一条记录 = 一个 Object candidate × 一张表；evidence 按 M3 的 evidence type "
            "分组（table_name / table_comment / column_name / column_comment / sql / lineage），"
            "只引用 statement_id / table_key / column_name，不复制 SQL 原文；"
            "candidate_layer 是 M2.2 的唯一层级判定，不是「该 Object 属于该层」；"
            "status 规则见 object-graph.md。"
        ),
        "status_counts": _status_counts(
            [str(item.get("status") or OBJECT_STATUS_CANDIDATE) for item in associations]
        ),
        "associations": associations,
    }

    result = BusinessObjectResult(
        registry=registry,
        associations=associations_payload,
        relationships=relationships,
        matrix=matrix,
        analysis_dir=inputs.analysis_dir,
    )

    result.graph = render_object_graph(
        registry=result.registry,
        associations=result.associations,
        relationships=result.relationships,
        matrix=result.matrix,
        quality_summary=inputs.quality_summary,
        statement_count=len(inputs.statements),
        relationship_row_limit=OBJECT_GRAPH_ROW_LIMIT,
        analysis_dir=inputs.analysis_dir,
    )

    return result


# ============================================================
# 产物写出与运行入口
# ============================================================


def write_business_objects(
    result: BusinessObjectResult,
    output_dir: Path,
) -> tuple[Path, ...]:
    """写出 M3.2 产物，返回路径列表（固定顺序）。

    只覆盖本模块声明的五个文件，不删除、不改写已有 M2 / M3 / M3.1 产物。
    """

    ensure_dir(output_dir)

    paths = {name: output_dir / name for name in OUTPUT_FILES}

    write_json(paths["objects-registry.json"], result.registry)
    write_json(paths["object-tables.json"], result.associations)
    write_json(paths["object-relationships.json"], result.relationships)
    write_json(paths["object-evidence-matrix.json"], result.matrix)
    write_text(paths["object-graph.md"], result.graph)

    logger.info(
        "M3.2 产物已写出：%s",
        "，".join(_display_path(paths[name]) for name in OUTPUT_FILES),
    )

    return tuple(paths[name] for name in OUTPUT_FILES)


def run_business_object_analysis(
    *,
    analysis_dir: Path,
    output_dir: Path,
) -> BusinessObjectResult:
    """执行 M3.2 Business Object & Relationship Analysis 并写出产物。

    只读 M2 / M3 / M3.1 产物；输入缺失时直接报错，
    不自动回退去跑 analyze / analyze --stage。
    """

    inputs = read_object_inputs(analysis_dir)

    result = build_business_objects(inputs)
    result.analysis_dir = analysis_dir

    confirmed = result.association_status_counts.get(OBJECT_STATUS_CONFIRMED, 0)

    if confirmed:
        logger.info(
            "M3.2 读到 %s 条人工确认的 Object association（来自 review-checklist.md）",
            confirmed,
        )

    if not result.relationship_count:
        logger.warning(
            "M3.2 没有推导出任何 Object relationship：当前 Object candidate 之间"
            "缺少同表共现 / SQL 引用 / 血缘证据"
        )

    write_business_objects(result, output_dir)

    logger.info(
        "M3.2 Business Object & Relationship Analysis 完成：object=%s，association=%s，"
        "relationship=%s（core=%s），confirmed=%s",
        result.object_count,
        result.association_count,
        result.relationship_count,
        result.core_relationship_count,
        confirmed,
    )

    return result

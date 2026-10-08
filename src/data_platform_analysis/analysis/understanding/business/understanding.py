"""M3 Business Understanding 第一阶段。

目标：

    从 M2 已有证据（表 / 字段的名称与注释、SQL、血缘、层级判定）反向提取业务语义，
    产出「业务候选 + 证据链」，回答「这张表可能表达什么业务概念、可能属于什么业务
    主题、和哪些业务对象有关、为什么这么判断」，
    为后续业务过程识别、Grain 分析、DWD / DWS 重构提供输入。

输入（只读，不访问 DataWorks / MaxCompute API，不读取 source/）：

    analysis/inventory/tables.json
    analysis/inventory/columns.json
    analysis/evidence/sql/statements.json
    analysis/evidence/sql/table-references.json
    analysis/evidence/lineage/table-lineage.json
    analysis/evidence/lineage/core-table-candidates.json
    analysis/evidence/layer/assessments.json
    config/business-rules.yaml

输出：

    analysis/understanding/business/terms.json
    analysis/understanding/business/tables.json
    analysis/understanding/business/domains.json
    analysis/understanding/business/objects.json
    analysis/understanding/business/summary.md

原则：

1. Observed Fact → Derived Evidence → Candidate → Human Review → Design Decision。
   本阶段只产出 Candidate 与 Evidence：不产出业务结论，也不生成
   「这是销售订单事实表」这类业务描述（那属于后续 LLM / 业务分析阶段）。
2. 层级只读取 M2.2 Layer Assessment（warehouse_layer / candidate_sub_layer）：
   M3 不判定层级，也不因为某张表「像 DWD / DWS」而修改它的层级。
3. 证据来源按优先级：表注释 > 字段注释 > 表名 > 字段名 > SQL > 血缘；
   SQL / Lineage 只补充 Direct Evidence（名称与注释）未覆盖到的关键词，
   避免同一信号被重复计数抬高 confidence。
4. 同时命中多个 Domain / Object 时全部保留，不擅自选择一个。
5. 输出 deterministic：相同输入两次运行产物完全一致，
   不含时间戳 / UUID / 随机排序 / 非确定性集合遍历。
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .... import config
from ....io_utils import ensure_dir, write_json, write_text
from ...models import (
    BUSINESS_CONFIDENCE_HIGH,
    BUSINESS_CONFIDENCE_LOW,
    BUSINESS_CONFIDENCE_MEDIUM,
    BUSINESS_CONFIDENCE_UNKNOWN,
    BUSINESS_EVIDENCE_COLUMN_COMMENT,
    BUSINESS_EVIDENCE_COLUMN_NAME,
    BUSINESS_EVIDENCE_LINEAGE,
    BUSINESS_EVIDENCE_SQL,
    BUSINESS_EVIDENCE_TABLE_COMMENT,
    BUSINESS_EVIDENCE_TABLE_NAME,
    BUSINESS_TERM_SOURCE_COLUMN_NAME,
    BUSINESS_TERM_SOURCE_ORDER,
    BUSINESS_TERM_SOURCE_TABLE_NAME,
    BusinessObjectCandidate,
    BusinessTableUnderstanding,
    BusinessTerm,
    DomainCandidate,
    DomainSummary,
    DomainTableRef,
    ObjectSummary,
    confidence_sort_key,
    evidence_type_sort_key,
    numeric_id_sort_key,
)
from ...naming import qualify_table_ref, table_name_of
from ...reports import render_business_summary

logger = logging.getLogger(__name__)

# ============================================================
# 输入与输出布局
# ============================================================

M2_INPUT_FILES: tuple[tuple[str, str], ...] = (
    ("inventory/tables.json", "tables"),
    ("inventory/columns.json", "columns"),
    ("evidence/sql/statements.json", "statements"),
    ("evidence/sql/table-references.json", "references"),
    ("evidence/lineage/table-lineage.json", "edges"),
    ("evidence/lineage/core-table-candidates.json", "candidates"),
    ("evidence/layer/assessments.json", "assessments"),
)
"""M3 依赖的 M2 产物（相对 analysis/ 的路径 → JSON 数组字段名）。"""

OUTPUT_FILES: tuple[str, ...] = (
    "terms.json",
    "tables.json",
    "domains.json",
    "objects.json",
    "summary.md",
)

TERMS_SORT_BY = "count_desc,normalized_term_asc"
"""terms.json 的排序约定。"""


class BusinessUnderstandingError(RuntimeError):
    """M3 无法继续的配置 / 输入错误。"""


def _display_path(path: Path) -> str:
    """日志与报告中展示的路径：项目根内用相对路径，其余保持绝对。"""

    try:
        return str(path.resolve().relative_to(config.PROJECT_ROOT))

    except ValueError:
        return str(path)


# ============================================================
# 业务规则配置
# ============================================================


@dataclass(frozen=True)
class BusinessCategoryRule:
    """一个业务类别（Domain 或 Object）的候选识别规则。"""

    key: str
    name: str
    keywords: tuple[str, ...]
    """配置原文关键词，保持配置顺序。"""

    keyword_casefolds: frozenset[str]
    """casefold 后的关键词集合，用于匹配。"""

    def matches(self, keyword: str) -> bool:
        """判断某条 evidence 的关键词是否属于本类别。"""

        return keyword.casefold() in self.keyword_casefolds


@dataclass(frozen=True)
class BusinessRules:
    """business-rules.yaml 的内存表示。"""

    version: str
    source_path: Path
    stopwords: frozenset[str]
    domains: tuple[BusinessCategoryRule, ...]
    objects: tuple[BusinessCategoryRule, ...]

    @property
    def all_keywords(self) -> tuple[str, ...]:
        """Domain + Object 全部关键词，按配置顺序去重（casefold 粒度）。"""

        seen: dict[str, str] = {}

        for rule in (*self.domains, *self.objects):
            for keyword in rule.keywords:
                seen.setdefault(keyword.casefold(), keyword)

        return tuple(seen.values())


def load_business_rules(path: Path) -> BusinessRules:
    """读取并严格校验 business-rules 配置。

    校验失败一律抛 BusinessUnderstandingError，不静默回退默认词典。
    """

    if not path.exists():
        raise BusinessUnderstandingError(f"Business Rules 配置文件不存在：{path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    except yaml.YAMLError as exc:
        raise BusinessUnderstandingError(
            f"Business Rules 配置不是合法的 YAML：{path}（{exc}）"
        ) from exc

    if raw is None:
        raise BusinessUnderstandingError(f"Business Rules 配置为空：{path}")

    if not isinstance(raw, dict):
        raise BusinessUnderstandingError(f"Business Rules 配置根节点必须是映射：{path}")

    version = raw.get("version")

    if not isinstance(version, str) or not version.strip():
        raise BusinessUnderstandingError(f"Business Rules 配置缺少 version：{path}")

    stopwords = _parse_stopwords(raw.get("stopwords"), path)
    domains = _parse_categories(raw.get("domains"), label="domains", path=path)
    objects = _parse_categories(raw.get("objects"), label="objects", path=path)

    rules = BusinessRules(
        version=version.strip(),
        source_path=path,
        stopwords=stopwords,
        domains=domains,
        objects=objects,
    )

    conflicts = sorted({keyword.casefold() for keyword in rules.all_keywords} & rules.stopwords)

    if conflicts:
        raise BusinessUnderstandingError(
            "Business Rules 关键词与 stopwords 冲突（关键词不能是技术 token）："
            f"{', '.join(conflicts)}（{path}）"
        )

    logger.info(
        "Business Rules 已加载：%s（version=%s，domain=%s，object=%s，keyword=%s，stopword=%s）",
        _display_path(rules.source_path),
        rules.version,
        len(rules.domains),
        len(rules.objects),
        len(rules.all_keywords),
        len(rules.stopwords),
    )

    return rules


def _parse_stopwords(value: Any, path: Path) -> frozenset[str]:
    """解析 stopwords：必须是非空字符串列表，大小写不敏感去重。"""

    if not isinstance(value, list) or not value:
        raise BusinessUnderstandingError(f"stopwords 必须是非空列表：{path}")

    seen: set[str] = set()

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BusinessUnderstandingError(
                f"stopwords 只能包含非空字符串（YAML 裸 no/yes 会被解析成布尔值，"
                f"需要加引号）：{item!r}（{path}）"
            )

        token = item.strip().casefold()

        if token in seen:
            raise BusinessUnderstandingError(f"stopwords 包含重复项：{item}（{path}）")

        seen.add(token)

    return frozenset(seen)


def _parse_categories(
    value: Any,
    *,
    label: str,
    path: Path,
) -> tuple[BusinessCategoryRule, ...]:
    """解析 domains / objects 映射，保持配置顺序。"""

    if not isinstance(value, dict) or not value:
        raise BusinessUnderstandingError(f"{label} 必须是非空映射：{path}")

    rules: list[BusinessCategoryRule] = []
    seen_keys: set[str] = set()

    for raw_key, spec in value.items():
        key = str(raw_key).strip()

        if not key:
            raise BusinessUnderstandingError(f"{label} 包含空的 key：{path}")

        if key in seen_keys:
            raise BusinessUnderstandingError(f"{label} 存在重复的 key：{key}（{path}）")

        seen_keys.add(key)

        if not isinstance(spec, dict):
            raise BusinessUnderstandingError(f"{label}.{raw_key} 必须是映射：{path}")

        name = _required_text(spec.get("name"), label=f"{label}.{raw_key}.name", path=path)
        keywords = _parse_keywords(
            spec.get("keywords"),
            label=f"{label}.{raw_key}.keywords",
            path=path,
        )

        rules.append(
            BusinessCategoryRule(
                key=key,
                name=name,
                keywords=keywords,
                keyword_casefolds=frozenset(keyword.casefold() for keyword in keywords),
            )
        )

    return tuple(rules)


def _parse_keywords(value: Any, *, label: str, path: Path) -> tuple[str, ...]:
    """解析关键词列表：非空字符串、大小写不敏感去重、保持配置顺序。"""

    if not isinstance(value, list) or not value:
        raise BusinessUnderstandingError(f"{label} 必须是非空列表：{path}")

    keywords: list[str] = []
    seen: set[str] = set()

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BusinessUnderstandingError(f"{label} 只能包含非空字符串：{item!r}（{path}）")

        keyword = item.strip()
        token = keyword.casefold()

        if token in seen:
            raise BusinessUnderstandingError(f"{label} 包含重复关键词：{keyword}（{path}）")

        seen.add(token)
        keywords.append(keyword)

    return tuple(keywords)


def _required_text(value: Any, *, label: str, path: Path) -> str:
    """取非空字符串，否则报配置错误。"""

    if isinstance(value, str) and value.strip():
        return value.strip()

    raise BusinessUnderstandingError(f"{label} 必须是非空字符串：{value!r}（{path}）")


# ============================================================
# 分词与关键词匹配
# ============================================================

CAMEL_CASE_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+")
SEPARATOR_RE = re.compile(r"[_\-. ]+")


def tokenize_identifier(name: str) -> list[str]:
    """把标识符拆成 surface token（保留原始大小写）。

    支持 snake_case / camelCase / PascalCase 与数字：

        dwd_sales_order → dwd / sales / order
        customerId      → customer / Id
        CustomerID      → Customer / ID

    这里只做分词，不判断哪些 token 是业务词。
    """

    if not name:
        return []

    tokens: list[str] = []

    for part in SEPARATOR_RE.split(name):
        if part:
            tokens.extend(CAMEL_CASE_RE.findall(part))

    return tokens


def business_tokens(name: str, stopwords: frozenset[str]) -> list[str]:
    """返回可用于业务语义匹配的 token。

    剔除 stopwords（技术 token）与纯数字，因此
    `dwd_sales_order` 中的 `dwd` 不会被当成业务词。
    """

    tokens: list[str] = []

    for token in tokenize_identifier(name):
        normalized = token.casefold()

        if normalized in stopwords or normalized.isdigit():
            continue

        tokens.append(token)

    return tokens


class KeywordMatcher:
    """业务关键词匹配器。

    同一套关键词服务两类匹配：

    1. token 精确匹配（表名 / 字段名 / 血缘邻居表名分词后比较）；
    2. 自由文本匹配（注释与 SQL 原文：英文按词边界，中文按子串）。

    两类匹配结果都按配置顺序返回，保证输出 deterministic。
    """

    def __init__(self, keywords: Sequence[str]) -> None:
        ordered: dict[str, str] = {}

        for raw in keywords:
            text = raw.strip()

            if text:
                ordered.setdefault(text.casefold(), text)

        self._ordered = ordered
        self._ascii = {key: value for key, value in ordered.items() if key.isascii()}
        self._non_ascii = tuple((key, value) for key, value in ordered.items() if not key.isascii())
        self._pattern: re.Pattern[str] | None = None

        if self._ascii:
            # 长关键词优先，避免前缀关键词抢匹配（边界正则同样兜底）。
            alternation = "|".join(
                re.escape(key) for key in sorted(self._ascii, key=len, reverse=True)
            )
            self._pattern = re.compile(rf"(?<![a-z0-9])(?:{alternation})(?![a-z0-9])")

    @property
    def keywords(self) -> tuple[str, ...]:
        """全部关键词（配置原文，去重，配置顺序）。"""

        return tuple(self._ordered.values())

    def match_tokens(self, tokens: Sequence[str]) -> list[str]:
        """token 精确命中关键词，按配置顺序返回。"""

        if not tokens:
            return []

        present = {token.casefold() for token in tokens}

        return [value for key, value in self._ordered.items() if key in present]

    def match_text(self, text: str) -> list[str]:
        """自由文本命中关键词（英文词边界 / 中文子串），按配置顺序返回。"""

        if not text:
            return []

        lowered = text.casefold()
        matched: set[str] = set()

        if self._pattern is not None:
            matched.update(hit.group(0) for hit in self._pattern.finditer(lowered))

        for key, _value in self._non_ascii:
            if key in lowered:
                matched.add(key)

        return [value for key, value in self._ordered.items() if key in matched]


def resolve_confidence(evidence_types: Iterable[str]) -> str:
    """按命中的 evidence type 数量给出 confidence。

    - high：≥3 种独立证据来源；
    - medium：2 种来源，或唯一来源是表注释（强证据单独命中）；
    - low：唯一来源是表名 / 字段名 / 字段注释 / SQL / 血缘；
    - unknown：没有任何来源。
    """

    types = set(evidence_types)

    if not types:
        return BUSINESS_CONFIDENCE_UNKNOWN

    if len(types) >= 3:
        return BUSINESS_CONFIDENCE_HIGH

    if len(types) == 2:
        return BUSINESS_CONFIDENCE_MEDIUM

    if BUSINESS_EVIDENCE_TABLE_COMMENT in types:
        return BUSINESS_CONFIDENCE_MEDIUM

    return BUSINESS_CONFIDENCE_LOW


# ============================================================
# M2 产物读取
# ============================================================


@dataclass
class M2Inputs:
    """M3 读取到的 M2 产物（只做结构校验，不改写）。"""

    tables: list[dict[str, Any]] = field(default_factory=list)
    columns: list[dict[str, Any]] = field(default_factory=list)
    statements: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    assessments: list[dict[str, Any]] = field(default_factory=list)


def read_m2_inputs(analysis_dir: Path) -> M2Inputs:
    """读取 M3 依赖的全部 M2 产物。

    任何输入缺失都明确报错，不自动回退执行 M2。
    """

    missing = [
        relative for relative, _key in M2_INPUT_FILES if not (analysis_dir / relative).exists()
    ]

    if missing:
        raise BusinessUnderstandingError(
            "M2 产物缺失，无法执行 M3 Business Understanding："
            f"{'、'.join(missing)}（目录：{_display_path(analysis_dir)}）；"
            "请先执行 analyze --stage evidence 生成 M2 产物"
        )

    def load(relative: str, key: str) -> list[dict[str, Any]]:
        path = analysis_dir / relative

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))

        except json.JSONDecodeError as exc:
            raise BusinessUnderstandingError(f"M2 产物不是合法的 JSON：{path}（{exc}）") from exc

        if not isinstance(raw, dict) or not isinstance(raw.get(key), list):
            raise BusinessUnderstandingError(f"M2 产物缺少 {key} 数组：{path}")

        items: list[dict[str, Any]] = []

        for position, entry in enumerate(raw[key]):
            if not isinstance(entry, dict):
                raise BusinessUnderstandingError(f"{key}[{position}] 不是对象：{path}")

            items.append(entry)

        return items

    inputs = M2Inputs()

    for relative, key in M2_INPUT_FILES:
        setattr(inputs, key, load(relative, key))

    logger.info(
        "M2 输入已读取：%s（table=%s，column=%s，statement=%s，edge=%s）",
        _display_path(analysis_dir),
        len(inputs.tables),
        len(inputs.columns),
        len(inputs.statements),
        len(inputs.edges),
    )

    return inputs


# ============================================================
# 排序键
# ============================================================


def _table_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        numeric_id_sort_key(record.get("workspace_id")),
        str(record.get("project") or ""),
        str(record.get("schema") or ""),
        str(record.get("table") or ""),
        str(record.get("table_key") or ""),
    )


def _column_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        numeric_id_sort_key(record.get("workspace_id")),
        str(record.get("project") or ""),
        str(record.get("table") or ""),
        int(record.get("ordinal") or 0),
        str(record.get("column_name") or ""),
    )


def _statement_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        numeric_id_sort_key(record.get("workspace_id")),
        numeric_id_sort_key(record.get("file_id")),
        int(record.get("statement_id") or 0),
    )


def _reference_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return _statement_sort_key(record)


def _edge_sort_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        numeric_id_sort_key(record.get("workspace_id")),
        str(record.get("source_key") or ""),
        str(record.get("target_key") or ""),
    )


def _statement_ref_key(record: Mapping[str, Any]) -> tuple[str, str, str]:
    """statement / reference 共用的关联键。"""

    return (
        str(record.get("workspace_id")),
        str(record.get("file_id")),
        str(record.get("statement_id")),
    )


def _output_statement_ids(ref: tuple[str, str, str]) -> tuple[int | str, str, int | str]:
    """把关联键还原成输出用的 ID 类型：数字 ID 转 int，file_id 保持字符串。"""

    workspace_id, file_id, statement_id = ref

    return (
        int(workspace_id) if workspace_id.isdigit() else workspace_id,
        file_id,
        int(statement_id) if statement_id.isdigit() else statement_id,
    )


def _text(value: Any) -> str | None:
    """把值转成非空字符串，空值返回 None。"""

    if value is None:
        return None

    text = str(value).strip()

    return text or None


# ============================================================
# 索引
# ============================================================


def _group_columns(
    columns: Sequence[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    """按 table_key（casefold）聚合字段，保持列顺序。"""

    grouped: dict[str, list[Mapping[str, Any]]] = {}

    for column in sorted(columns, key=_column_sort_key):
        table_key = _text(column.get("table_key")) or _text(column.get("table"))

        if not table_key:
            continue

        grouped.setdefault(table_key.casefold(), []).append(column)

    return grouped


def _index_layers(
    assessments: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[str | None, str | None]]:
    """M2.2 层级判定索引：table_identifier(casefold) → (warehouse, sub_layer)。"""

    index: dict[str, tuple[str | None, str | None]] = {}

    for record in assessments:
        identifier = _text(record.get("table_identifier")) or _text(record.get("table_name"))

        if not identifier:
            continue

        index.setdefault(
            identifier.casefold(),
            (_text(record.get("workspace_layer")), _text(record.get("candidate_layer"))),
        )

    return index


def _index_core_candidates(
    candidates: Sequence[Mapping[str, Any]],
) -> set[str]:
    """M2.4 核心表候选索引（table_key casefold，与表索引口径一致）。"""

    return {key.casefold() for record in candidates if (key := _text(record.get("table_key")))}


def _workspace_projects(
    tables: Sequence[Mapping[str, Any]],
) -> dict[int, str]:
    """workspace_id → project，用于补齐 SQL 中的裸表引用。"""

    projects: dict[int, str] = {}

    for table in sorted(tables, key=_table_sort_key):
        workspace_id = table.get("workspace_id")
        project = _text(table.get("project"))

        if isinstance(workspace_id, int) and project:
            projects.setdefault(workspace_id, project)

    return projects


def _scan_statements(
    statements: Sequence[Mapping[str, Any]],
    matcher: KeywordMatcher,
) -> dict[tuple[str, str, str], list[str]]:
    """扫描 M2.3 语句原文，得到每条语句命中的业务关键词。

    只做关键词轻量扫描，不重新解析 SQL 结构；
    SELECT / JOIN / GROUP BY / WHERE / 函数 / 别名都落在原文里，
    关键词出现即计为一条 SQL 证据。
    """

    hits: dict[tuple[str, str, str], list[str]] = {}

    for statement in sorted(statements, key=_statement_sort_key):
        sql = _text(statement.get("sql"))
        hits[_statement_ref_key(statement)] = matcher.match_text(sql) if sql else []

    return hits


def _index_table_statements(
    references: Sequence[Mapping[str, Any]],
    statement_keywords: Mapping[tuple[str, str, str], Sequence[str]],
    workspace_projects: Mapping[int, str],
) -> dict[str, dict[str, tuple[str, str, str]]]:
    """table_key(casefold) → keyword → 首条命中的语句标识。

    表引用取自 M2.3 的 table-references；裸表引用按 Workspace 对应的
    project 补齐。同一关键词只保留按确定性顺序的第一条语句作为代表证据。
    """

    index: dict[str, dict[str, tuple[str, str, str]]] = {}

    for reference in sorted(references, key=_reference_sort_key):
        keywords = statement_keywords.get(_statement_ref_key(reference))

        if not keywords:
            continue

        workspace_id = reference.get("workspace_id")
        project = workspace_projects.get(workspace_id) if isinstance(workspace_id, int) else None
        key = _statement_ref_key(reference)

        raw_tables: list[str] = []

        for field_name in ("source_tables", "target_tables"):
            values = reference.get(field_name)

            if isinstance(values, list):
                raw_tables.extend(item for item in values if isinstance(item, str))

        for raw in raw_tables:
            table_key = qualify_table_ref(raw, project)
            slot = index.setdefault(table_key.casefold(), {})

            for keyword in keywords:
                slot.setdefault(keyword, key)

    return index


LineageHit = tuple[str, str]
"""血缘命中：(source_table, target_table) 的 SQL 原始写法。"""


def _index_lineage(
    edges: Sequence[Mapping[str, Any]],
    matcher: KeywordMatcher,
    stopwords: frozenset[str],
) -> dict[str, dict[str, LineageHit]]:
    """table_key(casefold) → keyword → 首条命中的血缘边。

    上下游业务语义传播：邻居表名命中的关键词，作为本表的 lineage 证据；
    同一关键词只保留按确定性顺序的第一条边。
    """

    index: dict[str, dict[str, LineageHit]] = {}

    for edge in sorted(edges, key=_edge_sort_key):
        source_key = _text(edge.get("source_key"))
        target_key = _text(edge.get("target_key"))

        if not source_key or not target_key:
            continue

        source_table = _text(edge.get("source_table")) or table_name_of(source_key)
        target_table = _text(edge.get("target_table")) or table_name_of(target_key)

        source_keywords = matcher.match_tokens(
            business_tokens(table_name_of(source_key), stopwords)
        )
        target_keywords = matcher.match_tokens(
            business_tokens(table_name_of(target_key), stopwords)
        )

        hit: LineageHit = (source_table, target_table)

        target_slot = index.setdefault(target_key.casefold(), {})

        for keyword in source_keywords:
            target_slot.setdefault(keyword, hit)

        source_slot = index.setdefault(source_key.casefold(), {})

        for keyword in target_keywords:
            source_slot.setdefault(keyword, hit)

    return index


# ============================================================
# 候选构建
# ============================================================


@dataclass
class BusinessUnderstandingResult:
    """一次 M3 运行的结果。"""

    rules_path: Path
    rules_version: str
    analysis_dir: Path
    tables: list[BusinessTableUnderstanding] = field(default_factory=list)
    terms: list[BusinessTerm] = field(default_factory=list)
    domains: list[DomainSummary] = field(default_factory=list)
    objects: list[ObjectSummary] = field(default_factory=list)

    @property
    def unknown_table_count(self) -> int:
        """没有任何 Domain / Object 命中的表数量。"""

        return sum(1 for item in self.tables if item.is_unknown)

    @property
    def ambiguous_table_count(self) -> int:
        """同时命中多个 Domain 的表数量。"""

        return sum(1 for item in self.tables if item.is_ambiguous)

    @property
    def strong_table_count(self) -> int:
        """存在 high 级别候选的表数量。"""

        return sum(1 for item in self.tables if item.has_strong_evidence)


def build_business_understanding(
    rules: BusinessRules,
    inputs: M2Inputs,
) -> BusinessUnderstandingResult:
    """从 M2 产物构建 M3 业务理解结果（不读写文件）。"""

    matcher = KeywordMatcher(rules.all_keywords)

    tables = sorted(inputs.tables, key=_table_sort_key)
    columns_by_table = _group_columns(inputs.columns)
    layer_by_key = _index_layers(inputs.assessments)
    core_keys = _index_core_candidates(inputs.candidates)
    workspace_projects = _workspace_projects(tables)
    statement_keywords = _scan_statements(inputs.statements, matcher)
    table_statements = _index_table_statements(
        inputs.references,
        statement_keywords,
        workspace_projects,
    )
    lineage_hits = _index_lineage(inputs.edges, matcher, rules.stopwords)

    understandings: list[BusinessTableUnderstanding] = []

    term_sources: dict[str, list[dict[str, Any]]] = {}
    term_forms: dict[str, Counter[str]] = {}

    domain_refs: dict[str, list[DomainTableRef]] = {rule.key: [] for rule in rules.domains}
    domain_evidence_types: dict[str, Counter[str]] = {rule.key: Counter() for rule in rules.domains}
    object_refs: dict[str, list[DomainTableRef]] = {rule.key: [] for rule in rules.objects}
    object_evidence_types: dict[str, Counter[str]] = {rule.key: Counter() for rule in rules.objects}

    for table in tables:
        table_key = str(table.get("table_key") or "")
        table_name = str(table.get("table") or "")
        comment = _text(table.get("comment"))
        lookup_key = table_key.casefold()

        evidence = _build_evidence(
            rules=rules,
            matcher=matcher,
            table_key=table_key,
            table_name=table_name,
            comment=comment,
            columns=columns_by_table.get(lookup_key, []),
            table_statements=table_statements.get(lookup_key, {}),
            lineage_hits=lineage_hits.get(lookup_key, {}),
        )

        domain_candidates = _build_domain_candidates(rules.domains, evidence)
        object_candidates = _build_object_candidates(rules.objects, evidence)

        business_terms = _collect_terms(
            sources=(
                (BUSINESS_TERM_SOURCE_TABLE_NAME, table_name, None),
                *(
                    (BUSINESS_TERM_SOURCE_COLUMN_NAME, str(column.get("column_name") or ""), column)
                    for column in columns_by_table.get(lookup_key, [])
                ),
            ),
            table_key=table_key,
            stopwords=rules.stopwords,
            term_sources=term_sources,
            term_forms=term_forms,
        )

        warehouse_layer, candidate_sub_layer = layer_by_key.get(lookup_key, (None, None))

        understandings.append(
            BusinessTableUnderstanding(
                workspace_id=int(table.get("workspace_id") or 0),
                project=str(table.get("project") or ""),
                table=table_name,
                table_key=table_key,
                warehouse_layer=warehouse_layer,
                candidate_sub_layer=candidate_sub_layer,
                is_core_candidate=lookup_key in core_keys,
                business_terms=business_terms,
                domain_candidates=domain_candidates,
                business_object_candidates=object_candidates,
                evidence=evidence,
            )
        )

        for domain_candidate in domain_candidates:
            domain_refs[domain_candidate.domain].append(
                DomainTableRef(table_key=table_key, confidence=domain_candidate.confidence)
            )

            for item in domain_candidate.evidence:
                domain_evidence_types[domain_candidate.domain][str(item["type"])] += 1

        for object_candidate in object_candidates:
            object_refs[object_candidate.object].append(
                DomainTableRef(table_key=table_key, confidence=object_candidate.confidence)
            )

            for item in object_candidate.evidence:
                object_evidence_types[object_candidate.object][str(item["type"])] += 1

    terms = _build_terms(term_sources, term_forms)

    return BusinessUnderstandingResult(
        rules_path=rules.source_path,
        rules_version=rules.version,
        analysis_dir=Path(),
        tables=understandings,
        terms=terms,
        domains=_build_domain_summaries(rules.domains, domain_refs, domain_evidence_types),
        objects=_build_object_summaries(rules.objects, object_refs, object_evidence_types),
    )


def _build_evidence(
    *,
    rules: BusinessRules,
    matcher: KeywordMatcher,
    table_key: str,
    table_name: str,
    comment: str | None,
    columns: Sequence[Mapping[str, Any]],
    table_statements: Mapping[str, tuple[str, str, str]],
    lineage_hits: Mapping[str, LineageHit],
) -> list[dict[str, Any]]:
    """构建单张表的全部证据，顺序固定。

    Direct Evidence（表名 / 表注释 / 字段名 / 字段注释）按来源逐条保留：
    同一关键词被多个来源命中正是「多来源独立证据」，因此不去重。
    派生 Evidence（SQL / 血缘）只补充 Direct Evidence 未覆盖的关键词，
    避免同一信号被重复计数抬高 confidence。
    """

    evidence: list[dict[str, Any]] = []
    covered: set[str] = set()

    def add_direct(keyword: str, entry: dict[str, Any]) -> None:
        covered.add(keyword)
        evidence.append(entry)

    for keyword in matcher.match_tokens(business_tokens(table_name, rules.stopwords)):
        add_direct(
            keyword,
            {
                "type": BUSINESS_EVIDENCE_TABLE_NAME,
                "table_key": table_key,
                "keyword": keyword,
            },
        )

    if comment:
        for keyword in matcher.match_text(comment):
            add_direct(
                keyword,
                {
                    "type": BUSINESS_EVIDENCE_TABLE_COMMENT,
                    "table_key": table_key,
                    "value": comment,
                    "keyword": keyword,
                },
            )

    for column in columns:
        column_name = str(column.get("column_name") or "")

        if not column_name:
            continue

        for keyword in matcher.match_tokens(business_tokens(column_name, rules.stopwords)):
            add_direct(
                keyword,
                {
                    "type": BUSINESS_EVIDENCE_COLUMN_NAME,
                    "table_key": table_key,
                    "column_name": column_name,
                    "keyword": keyword,
                },
            )

        column_comment = _text(column.get("comment"))

        if column_comment:
            for keyword in matcher.match_text(column_comment):
                add_direct(
                    keyword,
                    {
                        "type": BUSINESS_EVIDENCE_COLUMN_COMMENT,
                        "table_key": table_key,
                        "column_name": column_name,
                        "value": column_comment,
                        "keyword": keyword,
                    },
                )

    # ----------------------------------------------------
    # SQL：同一关键词已被 Direct Evidence 覆盖时不再重复计数。
    # ----------------------------------------------------
    for keyword in matcher.keywords:
        if keyword in covered:
            continue

        statement_ref = table_statements.get(keyword)

        if statement_ref is None:
            continue

        workspace_id, file_id, statement_id = _output_statement_ids(statement_ref)

        evidence.append(
            {
                "type": BUSINESS_EVIDENCE_SQL,
                "workspace_id": workspace_id,
                "file_id": file_id,
                "statement_id": statement_id,
                "keyword": keyword,
            }
        )
        covered.add(keyword)

    # ----------------------------------------------------
    # Lineage：上下游表名关键词传播，同样不与已有关键词重复。
    # ----------------------------------------------------
    for keyword in matcher.keywords:
        if keyword in covered:
            continue

        hit = lineage_hits.get(keyword)

        if hit is None:
            continue

        source_table, target_table = hit

        evidence.append(
            {
                "type": BUSINESS_EVIDENCE_LINEAGE,
                "source_table": source_table,
                "target_table": target_table,
                "keyword": keyword,
            }
        )
        covered.add(keyword)

    return evidence


def _build_domain_candidates(
    rules: Sequence[BusinessCategoryRule],
    evidence: Sequence[Mapping[str, Any]],
) -> list[DomainCandidate]:
    """按 Domain 规则切分证据并给出 confidence；命中多个时全部保留。"""

    candidates: list[DomainCandidate] = []

    for rule in rules:
        subset = [dict(item) for item in evidence if rule.matches(str(item.get("keyword") or ""))]

        if not subset:
            continue

        candidates.append(
            DomainCandidate(
                domain=rule.key,
                name=rule.name,
                confidence=resolve_confidence(str(item["type"]) for item in subset),
                evidence=subset,
            )
        )

    candidates.sort(key=lambda item: (confidence_sort_key(item.confidence), item.domain))

    return candidates


def _build_object_candidates(
    rules: Sequence[BusinessCategoryRule],
    evidence: Sequence[Mapping[str, Any]],
) -> list[BusinessObjectCandidate]:
    """按 Object 规则切分证据并给出 confidence；命中多个时全部保留。"""

    candidates: list[BusinessObjectCandidate] = []

    for rule in rules:
        subset = [dict(item) for item in evidence if rule.matches(str(item.get("keyword") or ""))]

        if not subset:
            continue

        candidates.append(
            BusinessObjectCandidate(
                object=rule.key,
                name=rule.name,
                confidence=resolve_confidence(str(item["type"]) for item in subset),
                evidence=subset,
            )
        )

    candidates.sort(key=lambda item: (confidence_sort_key(item.confidence), item.object))

    return candidates


# ============================================================
# 业务术语汇总
# ============================================================


def _term_source_sort_key(source: Mapping[str, Any]) -> tuple[int, str, str]:
    """sources 的确定性排序键：来源类型 → 表 → 字段。"""

    source_type = str(source.get("type") or "")

    try:
        type_rank = BUSINESS_TERM_SOURCE_ORDER.index(source_type)

    except ValueError:
        type_rank = len(BUSINESS_TERM_SOURCE_ORDER)

    return (
        type_rank,
        str(source.get("table_key") or ""),
        str(source.get("column_name") or ""),
    )


def _pick_term(forms: Counter[str]) -> str:
    """从多种原始写法中选出 term：出现次数最多，并列取字典序最小。"""

    best = max(forms.values())

    return min(form for form, count in forms.items() if count == best)


def _collect_terms(
    *,
    sources: Iterable[tuple[str, str, Mapping[str, Any] | None]],
    table_key: str,
    stopwords: frozenset[str],
    term_sources: dict[str, list[dict[str, Any]]],
    term_forms: dict[str, Counter[str]],
) -> list[str]:
    """把一张表的表名 / 字段名分词结果登记到全局术语汇总。

    - 同一 (归一词, 来源位置) 只登记一条 source，避免重复位置撑爆 terms.json；
    - count 按 token 出现次数累加，能反映真实出现频率；
    - 返回本表的 business_terms：按（本表出现次数降序，词升序）稳定排序。
    """

    local_counts: Counter[str] = Counter()
    local_forms: dict[str, Counter[str]] = {}
    seen: set[tuple[str, str, str, str]] = set()

    for source_type, value, column in sources:
        if not value:
            continue

        column_name = str(column.get("column_name") or "") if column else ""

        for token in business_tokens(value, stopwords):
            normalized = token.casefold()

            local_counts[normalized] += 1
            local_forms.setdefault(normalized, Counter())[token] += 1
            term_forms.setdefault(normalized, Counter())[token] += 1

            location = (source_type, table_key, column_name)

            if (normalized, *location) in seen:
                continue

            seen.add((normalized, *location))

            source: dict[str, Any] = {
                "type": source_type,
                "table_key": table_key,
            }

            if column_name:
                source["column_name"] = column_name

            term_sources.setdefault(normalized, []).append(source)

    return [
        _pick_term(local_forms[normalized])
        for normalized in sorted(local_counts, key=lambda key: (-local_counts[key], key))
    ]


def _build_terms(
    term_sources: Mapping[str, list[dict[str, Any]]],
    term_forms: Mapping[str, Counter[str]],
) -> list[BusinessTerm]:
    """把全局术语登记合并成 terms.json 的候选列表。"""

    terms: list[BusinessTerm] = []

    for normalized, sources in term_sources.items():
        forms = term_forms.get(normalized)

        if not forms:
            continue

        terms.append(
            BusinessTerm(
                term=_pick_term(forms),
                normalized_term=normalized,
                count=sum(forms.values()),
                sources=sorted(sources, key=_term_source_sort_key),
            )
        )

    terms.sort(key=lambda item: (-item.count, item.normalized_term))

    return terms


# ============================================================
# Domain / Object 汇总
# ============================================================


def _ref_sort_key(ref: DomainTableRef) -> tuple[tuple[int, str], str]:
    return (confidence_sort_key(ref.confidence), ref.table_key)


def _build_domain_summaries(
    rules: Sequence[BusinessCategoryRule],
    refs: Mapping[str, Sequence[DomainTableRef]],
    evidence_types: Mapping[str, Mapping[str, int]],
) -> list[DomainSummary]:
    """按 key 升序汇总每个 Domain 的候选表与证据构成。"""

    summaries: list[DomainSummary] = []

    for rule in sorted(rules, key=lambda item: item.key):
        table_refs = sorted(refs.get(rule.key, ()), key=_ref_sort_key)
        counts = Counter(ref.confidence for ref in table_refs)

        summaries.append(
            DomainSummary(
                domain=rule.key,
                name=rule.name,
                table_count=len(table_refs),
                confidence_counts={
                    confidence: counts[confidence]
                    for confidence in sorted(counts, key=confidence_sort_key)
                },
                evidence_type_counts=dict(
                    sorted(
                        evidence_types.get(rule.key, {}).items(),
                        key=lambda item: (evidence_type_sort_key(item[0]), item[0]),
                    )
                ),
                tables=table_refs,
            )
        )

    return summaries


def _build_object_summaries(
    rules: Sequence[BusinessCategoryRule],
    refs: Mapping[str, Sequence[DomainTableRef]],
    evidence_types: Mapping[str, Mapping[str, int]],
) -> list[ObjectSummary]:
    """按 key 升序汇总每个业务对象的候选表与证据构成。"""

    summaries: list[ObjectSummary] = []

    for rule in sorted(rules, key=lambda item: item.key):
        table_refs = sorted(refs.get(rule.key, ()), key=_ref_sort_key)
        counts = Counter(ref.confidence for ref in table_refs)

        summaries.append(
            ObjectSummary(
                object=rule.key,
                name=rule.name,
                table_count=len(table_refs),
                confidence_counts={
                    confidence: counts[confidence]
                    for confidence in sorted(counts, key=confidence_sort_key)
                },
                evidence_type_counts=dict(
                    sorted(
                        evidence_types.get(rule.key, {}).items(),
                        key=lambda item: (evidence_type_sort_key(item[0]), item[0]),
                    )
                ),
                tables=table_refs,
            )
        )

    return summaries


# ============================================================
# 产物写出与运行入口
# ============================================================


def write_business_understanding(
    result: BusinessUnderstandingResult,
    output_dir: Path,
) -> tuple[Path, ...]:
    """写出 analysis/understanding/business 全部产物，返回路径列表（固定顺序）。"""

    ensure_dir(output_dir)

    # 只清理本模块声明的产物，避免上一次运行的残留混入。
    for name in OUTPUT_FILES:
        path = output_dir / name

        if path.exists():
            path.unlink()

    paths = {name: output_dir / name for name in OUTPUT_FILES}

    write_json(
        paths["terms.json"],
        {
            "count": len(result.terms),
            "sort_by": TERMS_SORT_BY,
            "terms": [item.to_dict() for item in result.terms],
        },
    )
    write_json(
        paths["tables.json"],
        {
            "count": len(result.tables),
            "tables": [item.to_dict() for item in result.tables],
        },
    )
    write_json(
        paths["domains.json"],
        {
            "count": len(result.domains),
            "domains": [item.to_dict() for item in result.domains],
        },
    )
    write_json(
        paths["objects.json"],
        {
            "count": len(result.objects),
            "objects": [item.to_dict() for item in result.objects],
        },
    )
    write_text(
        paths["summary.md"],
        render_business_summary(
            tables=result.tables,
            terms=result.terms,
            domains=result.domains,
            objects=result.objects,
            rules_path=_display_path(result.rules_path),
            rules_version=result.rules_version,
            analysis_dir=_display_path(result.analysis_dir),
        ),
    )

    logger.info(
        "M3 产物已写出：%s",
        "，".join(_display_path(paths[name]) for name in OUTPUT_FILES),
    )

    return tuple(paths[name] for name in OUTPUT_FILES)


def run_business_understanding(
    *,
    analysis_dir: Path,
    rules_path: Path,
    output_dir: Path,
) -> BusinessUnderstandingResult:
    """执行 M3 Business Understanding 并写出 analysis/understanding/business 产物。

    只读 M2 产物与 business-rules 配置；缺失 M2 输入时直接报错，
    不自动回退去跑 M2。
    """

    rules = load_business_rules(rules_path)
    inputs = read_m2_inputs(analysis_dir)

    result = build_business_understanding(rules, inputs)
    result.analysis_dir = analysis_dir

    unknown = result.unknown_table_count

    if unknown:
        logger.warning(
            "M3 检出 %s 张表没有任何 Domain / Object 候选（UNKNOWN），明细见 %s",
            unknown,
            _display_path(output_dir / "summary.md"),
        )

    ambiguous = result.ambiguous_table_count

    if ambiguous:
        logger.warning(
            "M3 检出 %s 张表同时命中多个 Domain（AMBIGUOUS），"
            "全部候选都保留，需人工判定；明细见 %s",
            ambiguous,
            _display_path(output_dir / "summary.md"),
        )

    write_business_understanding(result, output_dir)

    logger.info(
        "M3 Business Understanding 完成：table=%s，term=%s，domain=%s，object=%s，"
        "unknown=%s，ambiguous=%s",
        len(result.tables),
        len(result.terms),
        len(result.domains),
        len(result.objects),
        unknown,
        ambiguous,
    )

    return result

"""M2.1 Analysis Scope Rules：Inventory 内部的规则化分类。

本模块回答四个问题（全部归属 Inventory，不新增独立阶段）：

1. 资产身份：NodeId 是否有效、格式是否成立；
2. 内容状态：Content 是否可用、该类型是否预期需要 Content；
3. 分析资格：整体分析范围（overall_eligible）与 SQL 分析输入（sql_eligible）；
4. 非正式任务：测试 / 临时 / 演示任务的强证据排除与弱证据待确认。

三个概念严格分开：

- 资产有效性：对象是否是已知且可追溯的资产（Inventory 全量登记，永不过滤）；
- 分析资格：对象是否适合某项具体分析（overall_eligible / sql_eligible）；
- 清理候选资格：是否有充分证据值得后续人工核查（cleanup_candidate），
  比「排除分析」更严格，且永远不等于「可以删除」。

规则来自 config/analysis-scope-rules.yaml：判定条件、结果与启用状态都在配置里，
代码只解释白名单内的 condition.kind。配置非法时抛 ScopeRulesError，
由 Pipeline 转成 Fatal Error，不回退默认值，也不静默忽略。

可复现性：同一份 Inventory 与同一版本规则必然产生相同分类结果；
分类只依赖 FileInventory 字段与只读 Snapshot 内容，不依赖时间与随机数。
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..models import (
    NODE_ID_STATE_INVALID,
    NODE_ID_STATE_MISSING,
    NODE_ID_STATE_VALID,
    FileInventory,
    node_id_state,
)
from ..snapshot import SnapshotReader

# ============================================================
# 状态常量
# ============================================================

CONTENT_STATE_PRESENT = "present"
CONTENT_STATE_EMPTY_TEXT = "empty_text"
CONTENT_STATE_NOT_COLLECTED = "not_collected"
CONTENT_STATE_PATH_MISSING = "path_missing"
CONTENT_STATE_READ_ERROR = "read_error"

EXPECTATION_REQUIRED = "required"
EXPECTATION_NOT_REQUIRED = "not_required"
EXPECTATION_UNKNOWN = "unknown"

EXCLUSION_IDENTITY = "identity"
EXCLUSION_INFORMAL = "informal_task"

CLEANUP_NEVER = "never"
CLEANUP_ALWAYS = "always"
CLEANUP_WHEN_NODE_ID_MISSING = "when_node_id_missing"

RULE_TYPE_NODE_IDENTITY = "node_identity"
RULE_TYPE_INFORMAL_TASK = "informal_task"
RULE_TYPE_CONTENT_STATE = "content_state"
RULE_TYPE_SQL_ELIGIBILITY = "sql_eligibility"

RULE_TYPES: tuple[str, ...] = (
    RULE_TYPE_NODE_IDENTITY,
    RULE_TYPE_INFORMAL_TASK,
    RULE_TYPE_CONTENT_STATE,
    RULE_TYPE_SQL_ELIGIBILITY,
)

CONDITION_KINDS: frozenset[str] = frozenset(
    {
        "node_id_missing",
        "node_id_invalid",
        "node_id_valid",
        "informal_name_strong",
        "informal_name_weak",
        "content_state",
        "content_gap",
        "sql_eligible",
        "sql_blocked",
    }
)

CLASSIFICATIONS: frozenset[str] = frozenset(
    {
        "excluded_identity",
        "excluded_informal",
        "identity_confirmed",
        "review",
        "content_ok",
        "content_allowed_empty",
        "content_missing",
        "content_expectation_unknown",
        "not_sql_eligible",
        "sql_eligible",
    }
)

CLEANUP_POLICIES: frozenset[str] = frozenset(
    {CLEANUP_NEVER, CLEANUP_ALWAYS, CLEANUP_WHEN_NODE_ID_MISSING}
)

CONTENT_GAP_STATES: frozenset[str] = frozenset(
    {
        CONTENT_STATE_EMPTY_TEXT,
        CONTENT_STATE_NOT_COLLECTED,
        CONTENT_STATE_PATH_MISSING,
        CONTENT_STATE_READ_ERROR,
    }
)

SQL_BLOCKER_IDENTITY = "identity"
SQL_BLOCKER_INFORMAL = "informal"
SQL_BLOCKER_NODE_TYPE = "node_type"
SQL_BLOCKER_CONTENT = "content"

SQL_BLOCKERS: frozenset[str] = frozenset(
    {
        SQL_BLOCKER_IDENTITY,
        SQL_BLOCKER_INFORMAL,
        SQL_BLOCKER_NODE_TYPE,
        SQL_BLOCKER_CONTENT,
    }
)

INFORMAL_SEPARATOR = re.compile(r"[^0-9a-zA-Z]+")
"""文件名 token 切分：连续的非字母数字字符视为分隔符。"""

INFORMAL_NUMERIC_SUFFIX = re.compile(r"^([0-9a-zA-Z]+?)([0-9]+)$")
"""整名 informal token + 纯数字后缀（例如 test111）的强证据形状。"""

CONTENT_READ_LIMIT = 1 << 20
"""判断 Content 是否空白时读取的最大字节数（超出按有内容处理）。"""


# ============================================================
# 配置模型
# ============================================================


class ScopeRulesError(RuntimeError):
    """Analysis Scope Rules 配置错误：缺失、非法、字段不合法或规则冲突。"""


@dataclass(frozen=True)
class ScopeCondition:
    """规则判定条件：kind 由代码解释，params 由配置声明。"""

    kind: str
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScopeResult:
    """规则判定结果或处理动作。"""

    classification: str
    reason_code: str
    overall_eligible: bool | None = None
    sql_eligible: bool | None = None
    review_required: bool | None = None
    cleanup_candidate: str = CLEANUP_NEVER


@dataclass(frozen=True)
class ScopeRule:
    """一条可校验、可启用 / 禁用的判定规则。"""

    id: str
    description: str
    type: str
    scope: str
    enabled: bool
    condition: ScopeCondition
    result: ScopeResult


@dataclass(frozen=True)
class ScopeRules:
    """一次分类运行使用的完整规则集。"""

    version: str
    source_path: str
    rules: tuple[ScopeRule, ...]
    content_expectations: Mapping[str, str]
    sql_capable_content_formats: frozenset[str]
    informal_tokens: frozenset[str]

    def enabled_rules_of(self, rule_type: str) -> tuple[ScopeRule, ...]:
        """返回某个类型下已启用的规则，保持配置顺序。"""

        return tuple(rule for rule in self.rules if rule.type == rule_type and rule.enabled)

    def rule_by_id(self, rule_id: str) -> ScopeRule | None:
        for rule in self.rules:
            if rule.id == rule_id:
                return rule

        return None


# ============================================================
# 配置加载与校验
# ============================================================


def load_scope_rules(path: Path) -> ScopeRules:
    """加载并校验 Analysis Scope Rules 配置。

    配置缺失、非法 YAML、缺 version、未知字段、重复规则 ID、
    未知 condition kind、未知 classification、必需规则组为空
    都是配置错误，直接抛 ScopeRulesError。
    """

    if not path.exists():
        raise ScopeRulesError(f"Analysis Scope Rules 配置文件不存在：{path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScopeRulesError(f"Analysis Scope Rules 配置不是合法的 YAML：{path}（{exc}）") from exc
    except OSError as exc:
        raise ScopeRulesError(f"Analysis Scope Rules 配置读取失败：{path}（{exc}）") from exc

    if raw is None:
        raise ScopeRulesError(f"Analysis Scope Rules 配置为空：{path}")

    if not isinstance(raw, dict):
        raise ScopeRulesError(f"Analysis Scope Rules 配置根节点必须是映射：{path}")

    _reject_unknown_keys(
        raw,
        {
            "version",
            "content_expectations",
            "sql_capable_content_formats",
            "informal_task_names",
            "rules",
        },
        str(path),
    )

    version = _required_text(raw.get("version"), "version", path)

    expectations = _parse_content_expectations(raw.get("content_expectations"), path)
    sql_formats = _parse_format_list(
        raw.get("sql_capable_content_formats"), "sql_capable_content_formats", path
    )
    informal_tokens = _parse_informal_tokens(raw.get("informal_task_names"), path)
    rules = _parse_rules(raw.get("rules"), path)

    for rule_type in RULE_TYPES:
        if not any(rule.type == rule_type and rule.enabled for rule in rules):
            raise ScopeRulesError(f"规则类型 {rule_type} 没有任何已启用的规则（{path}）")

    _validate_group_mutual_exclusion(rules, path)

    return ScopeRules(
        version=version,
        source_path=str(path),
        rules=rules,
        content_expectations=expectations,
        sql_capable_content_formats=sql_formats,
        informal_tokens=informal_tokens,
    )


def _parse_content_expectations(value: Any, path: Path) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ScopeRulesError(f"content_expectations 必须是非空映射：{path}")

    allowed = {EXPECTATION_REQUIRED, EXPECTATION_NOT_REQUIRED, EXPECTATION_UNKNOWN}
    parsed: dict[str, str] = {}

    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ScopeRulesError(f"content_expectations 包含空的格式名：{path}")

        if item not in allowed:
            raise ScopeRulesError(
                f"content_expectations.{key} 必须是 {sorted(allowed)} 之一，实际为 {item!r}：{path}"
            )

        parsed[key.strip().upper()] = str(item)

    return parsed


def _parse_format_list(value: Any, label: str, path: Path) -> frozenset[str]:
    if not isinstance(value, list) or not value:
        raise ScopeRulesError(f"{label} 必须是非空列表：{path}")

    items: list[str] = []

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ScopeRulesError(f"{label} 只能包含非空字符串：{path}")

        items.append(item.strip().upper())

    if len(set(items)) != len(items):
        raise ScopeRulesError(f"{label} 包含重复项：{path}")

    return frozenset(items)


def _parse_informal_tokens(value: Any, path: Path) -> frozenset[str]:
    if not isinstance(value, dict):
        raise ScopeRulesError(f"informal_task_names 必须是映射：{path}")

    _reject_unknown_keys(value, {"tokens"}, str(path))

    tokens = value.get("tokens")

    if not isinstance(tokens, list) or not tokens:
        raise ScopeRulesError(f"informal_task_names.tokens 必须是非空列表：{path}")

    parsed: list[str] = []

    for token in tokens:
        if not isinstance(token, str) or not token.strip():
            raise ScopeRulesError(f"informal_task_names.tokens 只能包含非空字符串：{path}")

        normalized = token.strip().lower()

        if not re.fullmatch(r"[0-9a-z]+", normalized):
            raise ScopeRulesError(
                f"informal_task_names.tokens 只能包含纯字母数字 token：{token!r}（{path}）"
            )

        parsed.append(normalized)

    if len(set(parsed)) != len(parsed):
        raise ScopeRulesError(f"informal_task_names.tokens 包含重复项：{path}")

    return frozenset(parsed)


def _parse_rules(value: Any, path: Path) -> tuple[ScopeRule, ...]:
    if not isinstance(value, list) or not value:
        raise ScopeRulesError(f"rules 必须是非空列表：{path}")

    rules: list[ScopeRule] = []
    seen_ids: set[str] = set()

    for position, item in enumerate(value):
        label = f"rules[{position}]"

        if not isinstance(item, dict):
            raise ScopeRulesError(f"{label} 必须是映射：{path}")

        _reject_unknown_keys(
            item,
            {"id", "description", "type", "scope", "enabled", "condition", "result"},
            f"{label}（{path}）",
        )

        rule_id = _required_text(item.get("id"), f"{label}.id", path)

        if rule_id in seen_ids:
            raise ScopeRulesError(f"规则 ID 重复：{rule_id}（{path}）")

        seen_ids.add(rule_id)

        rule_type = _required_text(item.get("type"), f"{label}.type", path)

        if rule_type not in RULE_TYPES:
            raise ScopeRulesError(
                f"{label}.type 必须是 {list(RULE_TYPES)} 之一，实际为 {rule_type!r}：{path}"
            )

        scope = _required_text(item.get("scope"), f"{label}.scope", path)

        if scope != "all_files":
            raise ScopeRulesError(f"{label}.scope 当前只支持 all_files，实际为 {scope!r}：{path}")

        enabled = item.get("enabled")

        if not isinstance(enabled, bool):
            raise ScopeRulesError(f"{label}.enabled 必须是布尔值：{path}")

        rules.append(
            ScopeRule(
                id=rule_id,
                description=_required_text(item.get("description"), f"{label}.description", path),
                type=rule_type,
                scope=scope,
                enabled=enabled,
                condition=_parse_condition(item.get("condition"), f"{label}.condition", path),
                result=_parse_result(item.get("result"), f"{label}.result", path),
            )
        )

    return tuple(rules)


def _parse_condition(value: Any, label: str, path: Path) -> ScopeCondition:
    if not isinstance(value, dict):
        raise ScopeRulesError(f"{label} 必须是映射：{path}")

    kind = _required_text(value.get("kind"), f"{label}.kind", path)

    if kind not in CONDITION_KINDS:
        raise ScopeRulesError(
            f"{label}.kind 必须是 {sorted(CONDITION_KINDS)} 之一，实际为 {kind!r}：{path}"
        )

    params = {key: item for key, item in value.items() if key != "kind"}

    for list_key in ("expectations", "states", "by"):
        if list_key in params:
            items = params[list_key]

            if not isinstance(items, list) or not items:
                raise ScopeRulesError(f"{label}.{list_key} 必须是非空列表：{path}")

            if not all(isinstance(item, str) and item.strip() for item in items):
                raise ScopeRulesError(f"{label}.{list_key} 只能包含非空字符串：{path}")

    by_values = params.get("by")

    if by_values is not None:
        unknown = sorted(set(str(item) for item in by_values) - SQL_BLOCKERS)

        if unknown:
            raise ScopeRulesError(f"{label}.by 包含未知阻断维度 {unknown}：{path}")

    unknown_params = set(params) - {"expectations", "states", "by"}

    if unknown_params:
        raise ScopeRulesError(f"{label} 包含未知参数 {sorted(unknown_params)}：{path}")

    return ScopeCondition(kind=kind, params=dict(params))


def _parse_result(value: Any, label: str, path: Path) -> ScopeResult:
    if not isinstance(value, dict):
        raise ScopeRulesError(f"{label} 必须是映射：{path}")

    _reject_unknown_keys(
        value,
        {
            "classification",
            "reason_code",
            "overall_eligible",
            "sql_eligible",
            "review_required",
            "cleanup_candidate",
        },
        f"{label}（{path}）",
    )

    classification = _required_text(value.get("classification"), f"{label}.classification", path)

    if classification not in CLASSIFICATIONS:
        raise ScopeRulesError(
            f"{label}.classification 必须是 {sorted(CLASSIFICATIONS)} 之一，"
            f"实际为 {classification!r}：{path}"
        )

    cleanup = value.get("cleanup_candidate", CLEANUP_NEVER)

    if cleanup not in CLEANUP_POLICIES:
        raise ScopeRulesError(
            f"{label}.cleanup_candidate 必须是 {sorted(CLEANUP_POLICIES)} 之一，"
            f"实际为 {cleanup!r}：{path}"
        )

    return ScopeResult(
        classification=classification,
        reason_code=_required_text(value.get("reason_code"), f"{label}.reason_code", path),
        overall_eligible=_optional_bool(
            value.get("overall_eligible"), f"{label}.overall_eligible", path
        ),
        sql_eligible=_optional_bool(value.get("sql_eligible"), f"{label}.sql_eligible", path),
        review_required=_optional_bool(
            value.get("review_required"), f"{label}.review_required", path
        ),
        cleanup_candidate=str(cleanup),
    )


def _validate_group_mutual_exclusion(rules: Sequence[ScopeRule], path: Path) -> None:
    """校验同一类型内已启用规则的判定维度互斥，避免同一文件得出矛盾结论。"""

    for rule_type in RULE_TYPES:
        group = [rule for rule in rules if rule.type == rule_type and rule.enabled]

        seen: dict[tuple[str, tuple[str, ...]], str] = {}

        for rule in group:
            key = _condition_signature(rule.condition)

            if key in seen:
                raise ScopeRulesError(
                    f"规则类型 {rule_type} 内 {seen[key]} 与 {rule.id} 判定条件重复，"
                    f"同一文件会得到矛盾结论：{path}"
                )

            seen[key] = rule.id


def _condition_signature(condition: ScopeCondition) -> tuple[str, tuple[str, ...]]:
    """把条件压成互斥签名：kind + 排序后的取值集合。"""

    values: list[str] = []

    for key in ("expectations", "states", "by"):
        items = condition.params.get(key)

        if isinstance(items, list):
            values.append(f"{key}={'|'.join(sorted(str(item) for item in items))}")

    return condition.kind, tuple(values)


def _reject_unknown_keys(raw: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(raw) - allowed)

    if unknown:
        raise ScopeRulesError(f"{label} 包含未知字段 {unknown}")


def _required_text(value: Any, label: str, path: Path) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()

    raise ScopeRulesError(f"{label} 必须是非空字符串，实际为 {value!r}：{path}")


def _optional_bool(value: Any, label: str, path: Path) -> bool | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    raise ScopeRulesError(f"{label} 必须是布尔值：{path}")


# ============================================================
# 事实状态计算
# ============================================================


def content_expectation(rules: ScopeRules, content_format: str) -> str:
    """按类型注册表的 content_format 查询内容期望，未知格式返回 unknown。"""

    key = (content_format or "").strip().upper()

    return str(rules.content_expectations.get(key, EXPECTATION_UNKNOWN))


def match_informal_name(rules: ScopeRules, file_name: str | None) -> str | None:
    """文件名的非正式任务匹配强度：strong / weak / None。

    strong：整名（去掉扩展名、分隔符规范化后）就是一个 informal token，
            或 token + 纯数字后缀，或 token 后紧跟扩展名；
    weak  ：token 作为独立词出现在名称中，但名称还包含其他词。

    一律忽略大小写、按非字母数字字符切分，不做子串匹配。
    """

    if not file_name or not file_name.strip():
        return None

    stem = file_name.strip()
    dot = stem.rfind(".")

    if dot > 0:
        stem = stem[:dot]

    normalized = INFORMAL_SEPARATOR.sub(" ", stem).strip().lower()

    if not normalized:
        return None

    compact = normalized.replace(" ", "")

    if compact in rules.informal_tokens:
        return "strong"

    match = INFORMAL_NUMERIC_SUFFIX.match(compact)

    if match and match.group(1) in rules.informal_tokens:
        return "strong"

    tokens = [token for token in normalized.split() if token]

    if not tokens:
        return None

    if len(tokens) == 1 and tokens[0] in rules.informal_tokens:
        return "strong"

    if any(token in rules.informal_tokens for token in tokens):
        return "weak"

    return None


def content_state_of(reader: SnapshotReader, file: FileInventory) -> str:
    """Content 事实状态。

    区分四种不同语义（绝不混为一谈）：
    - not_collected：content_file 为空，采集结果事实（API 未返回内容）；
    - path_missing ：content_file 指向的 Snapshot 文件不存在，技术异常；
    - empty_text   ：文件存在但内容为空白；
    - present      ：文件存在且有内容。
    """

    if not file.content_file:
        return CONTENT_STATE_NOT_COLLECTED

    path = reader.resolve(file.content_file)

    if not path.exists():
        return CONTENT_STATE_PATH_MISSING

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return CONTENT_STATE_READ_ERROR

    if len(text) > CONTENT_READ_LIMIT:
        return CONTENT_STATE_PRESENT

    return CONTENT_STATE_PRESENT if text.strip() else CONTENT_STATE_EMPTY_TEXT


# ============================================================
# 判定结果
# ============================================================


@dataclass(frozen=True)
class FileScopeDecision:
    """单个 DataWorks File 的规则分类结果。

    稳定身份是 workspace_id + file_id，与 FileInventory 一致；
    一条结果可同时命中多条规则，reason_codes / matched_rule_ids 保留全部命中。
    """

    workspace_id: int
    workspace_name: str
    file_id: str
    node_id: int | str | None
    file_name: str | None
    file_type: int | None
    file_type_name: str
    task_type: str
    category: str
    content_format: str

    node_id_state: str
    content_state: str
    content_expectation: str

    identity_eligible: bool
    overall_eligible: bool
    sql_eligible: bool

    exclusion_class: str | None
    reason_code: str
    reason_codes: tuple[str, ...]
    sql_reason_code: str
    matched_rule_ids: tuple[str, ...]
    evidence: tuple[str, ...]

    review_required: bool
    cleanup_candidate: bool

    def to_dict(self) -> dict[str, Any]:
        """序列化为 excluded-tasks.json / review-tasks.json 的单条记录。"""

        return {
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "file_id": self.file_id,
            "node_id": self.node_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_type_name": self.file_type_name,
            "task_type": self.task_type,
            "category": self.category,
            "content_format": self.content_format,
            "node_id_state": self.node_id_state,
            "content_state": self.content_state,
            "content_expectation": self.content_expectation,
            "identity_eligible": self.identity_eligible,
            "overall_eligible": self.overall_eligible,
            "sql_eligible": self.sql_eligible,
            "exclusion_class": self.exclusion_class,
            "reason_code": self.reason_code,
            "reason_codes": list(self.reason_codes),
            "sql_reason_code": self.sql_reason_code,
            "matched_rule_ids": list(self.matched_rule_ids),
            "evidence": list(self.evidence),
            "review_required": self.review_required,
            "cleanup_candidate": self.cleanup_candidate,
        }


@dataclass(frozen=True)
class FileScopeStats:
    """规则分类统计：唯一对象口径与规则命中口径分开。"""

    rules_version: str = ""
    total_count: int = 0

    node_id_valid_count: int = 0
    node_id_missing_count: int = 0
    node_id_invalid_count: int = 0

    task_type_counts: Mapping[str, int] = field(default_factory=dict)

    content_present_count: int = 0
    content_empty_text_count: int = 0
    content_empty_allowed_count: int = 0
    content_empty_unexpected_count: int = 0
    content_not_collected_count: int = 0
    content_path_missing_count: int = 0
    content_read_error_count: int = 0
    content_gap_unknown_expectation_count: int = 0
    content_expectation_unknown_count: int = 0

    overall_eligible_count: int = 0
    identity_excluded_count: int = 0
    informal_excluded_count: int = 0
    excluded_total_count: int = 0
    sql_eligible_count: int = 0
    sql_ineligible_count: int = 0
    review_count: int = 0
    cleanup_candidate_count: int = 0

    informal_strong_count: int = 0
    informal_weak_count: int = 0

    exclusion_class_counts: Mapping[str, int] = field(default_factory=dict)
    reason_counts: Mapping[str, int] = field(default_factory=dict)
    sql_reason_counts: Mapping[str, int] = field(default_factory=dict)
    rule_hit_counts: Mapping[str, int] = field(default_factory=dict)
    rule_types: Mapping[str, str] = field(default_factory=dict)
    rule_descriptions: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FileScope:
    """一次 Inventory 运行的全部规则分类结果。"""

    rules_version: str
    rules_path: str
    decisions: tuple[FileScopeDecision, ...]
    rule_index: Mapping[str, ScopeRule] = field(default_factory=dict)

    def decision(self, workspace_id: int, file_id: int | str) -> FileScopeDecision | None:
        """按稳定身份查询判定结果；未登记对象返回 None。"""

        key = (workspace_id, str(file_id))

        for decision in self.decisions:
            if (decision.workspace_id, decision.file_id) == key:
                return decision

        return None

    def excluded(self) -> list[FileScopeDecision]:
        """明确排除出正式业务分析的对象（与 excluded-tasks.json 一致）。"""

        return [item for item in self.decisions if item.exclusion_class is not None]

    def review(self) -> list[FileScopeDecision]:
        """待确认对象（与 review-tasks.json 一致）。"""

        return [item for item in self.decisions if item.review_required]

    def sql_eligible_files(self, files: Sequence[FileInventory]) -> list[FileInventory]:
        """按统一资格判定筛选 SQL 分析输入，保持输入顺序。

        下游 SQL Analysis 用它取代各自拼装的过滤条件，
        保证「分析范围」只由 Inventory 的规则分类定义一次。
        """

        index = {(item.workspace_id, item.file_id): item for item in self.decisions}
        selected: list[FileInventory] = []

        for file in files:
            decision = index.get((file.workspace_id, str(file.file_id)))

            if decision is not None and decision.sql_eligible:
                selected.append(file)

        return selected

    def stats(self) -> FileScopeStats:
        """计算规则分类统计（唯一对象数与规则命中数分开）。"""

        task_types: Counter[str] = Counter()
        reasons: Counter[str] = Counter()
        sql_reasons: Counter[str] = Counter()
        rule_hits: Counter[str] = Counter()
        classes: Counter[str] = Counter()

        for item in self.decisions:
            task_types[item.task_type] += 1
            reasons[item.reason_code] += 1
            sql_reasons[item.sql_reason_code] += 1
            rule_hits.update(item.matched_rule_ids)

            if item.exclusion_class is not None:
                classes[item.exclusion_class] += 1

        return FileScopeStats(
            rules_version=self.rules_version,
            total_count=len(self.decisions),
            node_id_valid_count=sum(
                1 for item in self.decisions if item.node_id_state == NODE_ID_STATE_VALID
            ),
            node_id_missing_count=sum(
                1 for item in self.decisions if item.node_id_state == NODE_ID_STATE_MISSING
            ),
            node_id_invalid_count=sum(
                1 for item in self.decisions if item.node_id_state == NODE_ID_STATE_INVALID
            ),
            task_type_counts=dict(sorted(task_types.items())),
            content_present_count=sum(
                1 for item in self.decisions if item.content_state == CONTENT_STATE_PRESENT
            ),
            content_empty_text_count=sum(
                1 for item in self.decisions if item.content_state == CONTENT_STATE_EMPTY_TEXT
            ),
            content_empty_allowed_count=sum(
                1
                for item in self.decisions
                if item.content_state in CONTENT_GAP_STATES
                and item.content_expectation == EXPECTATION_NOT_REQUIRED
            ),
            content_empty_unexpected_count=sum(
                1
                for item in self.decisions
                if item.content_state in CONTENT_GAP_STATES
                and item.content_expectation == EXPECTATION_REQUIRED
            ),
            content_gap_unknown_expectation_count=sum(
                1
                for item in self.decisions
                if item.content_state in CONTENT_GAP_STATES
                and item.content_expectation == EXPECTATION_UNKNOWN
            ),
            content_not_collected_count=sum(
                1 for item in self.decisions if item.content_state == CONTENT_STATE_NOT_COLLECTED
            ),
            content_path_missing_count=sum(
                1 for item in self.decisions if item.content_state == CONTENT_STATE_PATH_MISSING
            ),
            content_read_error_count=sum(
                1 for item in self.decisions if item.content_state == CONTENT_STATE_READ_ERROR
            ),
            content_expectation_unknown_count=sum(
                1 for item in self.decisions if item.content_expectation == EXPECTATION_UNKNOWN
            ),
            overall_eligible_count=sum(1 for item in self.decisions if item.overall_eligible),
            identity_excluded_count=sum(
                1 for item in self.decisions if item.exclusion_class == EXCLUSION_IDENTITY
            ),
            informal_excluded_count=sum(
                1 for item in self.decisions if item.exclusion_class == EXCLUSION_INFORMAL
            ),
            excluded_total_count=sum(
                1 for item in self.decisions if item.exclusion_class is not None
            ),
            sql_eligible_count=sum(1 for item in self.decisions if item.sql_eligible),
            sql_ineligible_count=sum(1 for item in self.decisions if not item.sql_eligible),
            review_count=sum(1 for item in self.decisions if item.review_required),
            cleanup_candidate_count=sum(1 for item in self.decisions if item.cleanup_candidate),
            informal_strong_count=rule_hits.get("INFORMAL_TASK_STRONG", 0),
            informal_weak_count=rule_hits.get("INFORMAL_TASK_WEAK", 0),
            exclusion_class_counts=dict(sorted(classes.items())),
            reason_counts=dict(sorted(reasons.items())),
            sql_reason_counts=dict(sorted(sql_reasons.items())),
            rule_hit_counts=dict(sorted(rule_hits.items())),
            rule_types={rule.id: rule.type for rule in self.rule_index.values()},
            rule_descriptions={rule.id: rule.description for rule in self.rule_index.values()},
        )


def build_file_scope(
    inventory_files: Sequence[FileInventory],
    workspace_names: Mapping[int, str],
    *,
    rules: ScopeRules,
    reader: SnapshotReader,
) -> FileScope:
    """对 Inventory 登记的全部 File 执行规则分类。

    输入必须是完整清单（不做任何过滤）；输出与输入同序、数量一致。
    """

    decisions = tuple(
        classify_file(
            file,
            rules=rules,
            workspace_name=str(workspace_names.get(file.workspace_id) or file.workspace_id),
            content_state=content_state_of(reader, file),
        )
        for file in inventory_files
    )

    return FileScope(
        rules_version=rules.version,
        rules_path=rules.source_path,
        decisions=decisions,
        rule_index={rule.id: rule for rule in rules.rules},
    )


def classify_file(
    file: FileInventory,
    *,
    rules: ScopeRules,
    workspace_name: str,
    content_state: str,
) -> FileScopeDecision:
    """按处理顺序执行四组规则，返回无矛盾的分类结果。

    顺序：node_identity → informal_task → content_state → sql_eligibility。
    每组内取第一条命中的已启用规则；命中全部记录在 matched_rule_ids。
    """

    expectation = content_expectation(rules, file.content_format)
    state = node_id_state(file.node_id)
    informal = match_informal_name(rules, file.file_name)

    matched: list[ScopeRule] = []
    reason_codes: list[str] = []
    evidence: list[str] = []

    identity_rule = _first_match(
        rules.enabled_rules_of(RULE_TYPE_NODE_IDENTITY),
        node_id=state,
    )

    identity_eligible = False

    if identity_rule is not None:
        matched.append(identity_rule)
        reason_codes.append(identity_rule.result.reason_code)
        evidence.append(_identity_evidence(identity_rule.id, state, file.node_id))
        identity_eligible = identity_rule.result.overall_eligible is True

    informal_rule = _first_match(
        rules.enabled_rules_of(RULE_TYPE_INFORMAL_TASK),
        informal=informal,
    )

    informal_excluded = False

    if informal_rule is not None:
        matched.append(informal_rule)
        reason_codes.append(informal_rule.result.reason_code)

        if informal == "strong":
            evidence.append(f"文件名整体命中 informal token：{file.file_name}")
        elif informal == "weak":
            evidence.append(f"文件名包含 informal token（证据不足，待确认）：{file.file_name}")

        informal_excluded = informal_rule.result.overall_eligible is False

    content_rule = _first_match(
        rules.enabled_rules_of(RULE_TYPE_CONTENT_STATE),
        content_state=content_state,
        expectation=expectation,
    )

    if content_rule is not None:
        matched.append(content_rule)
        reason_codes.append(content_rule.result.reason_code)
        evidence.append(
            _content_evidence(content_rule.id, content_state, expectation, file.content_format)
        )

    overall_eligible = identity_eligible and not informal_excluded
    review_required = any(item.result.review_required is True for item in matched)

    blocker, sql_rule = _sql_eligibility(
        rules=rules,
        identity_eligible=identity_eligible,
        informal_excluded=informal_excluded,
        content_format=file.content_format,
        content_state=content_state,
    )

    sql_eligible = False
    sql_reason_code = ""

    if sql_rule is not None:
        matched.append(sql_rule)
        sql_eligible = sql_rule.result.sql_eligible is True
        sql_reason_code = sql_rule.result.reason_code

        # 身份阻断时复用实际命中的身份原因（MISSING / INVALID 由事实决定）。
        if blocker == SQL_BLOCKER_IDENTITY and identity_rule is not None:
            sql_reason_code = identity_rule.result.reason_code

    cleanup_policy = _cleanup_policy(matched)
    cleanup_candidate = _resolve_cleanup(cleanup_policy, state)

    if not identity_eligible:
        exclusion_class: str | None = EXCLUSION_IDENTITY
    elif informal_excluded:
        exclusion_class = EXCLUSION_INFORMAL
    else:
        exclusion_class = None

    primary_reason = _primary_reason(reason_codes, exclusion_class, sql_reason_code)

    return FileScopeDecision(
        workspace_id=file.workspace_id,
        workspace_name=workspace_name,
        file_id=str(file.file_id),
        node_id=file.node_id,
        file_name=file.file_name,
        file_type=file.file_type,
        file_type_name=file.file_type_name,
        task_type=file.task_type,
        category=file.category,
        content_format=file.content_format,
        node_id_state=state,
        content_state=content_state,
        content_expectation=expectation,
        identity_eligible=identity_eligible,
        overall_eligible=overall_eligible,
        sql_eligible=sql_eligible,
        exclusion_class=exclusion_class,
        reason_code=primary_reason,
        reason_codes=tuple(reason_codes),
        sql_reason_code=sql_reason_code,
        matched_rule_ids=tuple(item.id for item in matched),
        evidence=tuple(evidence),
        review_required=review_required,
        cleanup_candidate=cleanup_candidate,
    )


def _first_match(group: Sequence[ScopeRule], **facts: Any) -> ScopeRule | None:
    """在一组规则里取第一条命中的已启用规则。"""

    for rule in group:
        if _matches(rule.condition, facts):
            return rule

    return None


def _matches(condition: ScopeCondition, facts: Mapping[str, Any]) -> bool:
    """按白名单 kind 解释判定条件；不解释的组合一律不命中。"""

    kind = condition.kind

    if kind == "node_id_missing":
        return facts.get("node_id") == NODE_ID_STATE_MISSING

    if kind == "node_id_invalid":
        return facts.get("node_id") == NODE_ID_STATE_INVALID

    if kind == "node_id_valid":
        return facts.get("node_id") == NODE_ID_STATE_VALID

    if kind == "informal_name_strong":
        return facts.get("informal") == "strong"

    if kind == "informal_name_weak":
        return facts.get("informal") == "weak"

    if kind == "content_state":
        states = condition.params.get("states")
        return isinstance(states, list) and facts.get("content_state") in states

    if kind == "content_gap":
        expectations = condition.params.get("expectations")
        return (
            facts.get("content_state") in CONTENT_GAP_STATES
            and isinstance(expectations, list)
            and facts.get("expectation") in expectations
        )

    if kind == "sql_eligible":
        return facts.get("blocker") is None

    if kind == "sql_blocked":
        blockers = condition.params.get("by")
        return (
            isinstance(blockers, list)
            and facts.get("blocker") is not None
            and facts.get("blocker") in blockers
        )

    return False


def _sql_eligibility(
    *,
    rules: ScopeRules,
    identity_eligible: bool,
    informal_excluded: bool,
    content_format: str,
    content_state: str,
) -> tuple[str | None, ScopeRule | None]:
    """计算 SQL 分析资格的阻断维度与命中规则。

    阻断优先级：identity → informal → node_type → content（确定性顺序）。
    """

    if not identity_eligible:
        blocker: str | None = SQL_BLOCKER_IDENTITY
    elif informal_excluded:
        blocker = SQL_BLOCKER_INFORMAL
    elif (content_format or "").strip().upper() not in rules.sql_capable_content_formats:
        blocker = SQL_BLOCKER_NODE_TYPE
    elif content_state != CONTENT_STATE_PRESENT:
        blocker = SQL_BLOCKER_CONTENT
    else:
        blocker = None

    rule = _first_match(
        rules.enabled_rules_of(RULE_TYPE_SQL_ELIGIBILITY),
        blocker=blocker,
    )

    return blocker, rule


def _cleanup_policy(matched: Sequence[ScopeRule]) -> str:
    """取命中的规则中最严格的清理候选策略。"""

    if any(item.result.cleanup_candidate == CLEANUP_ALWAYS for item in matched):
        return CLEANUP_ALWAYS

    if any(item.result.cleanup_candidate == CLEANUP_WHEN_NODE_ID_MISSING for item in matched):
        return CLEANUP_WHEN_NODE_ID_MISSING

    return CLEANUP_NEVER


def _resolve_cleanup(policy: str, state: str) -> bool:
    if policy == CLEANUP_ALWAYS:
        return True

    if policy == CLEANUP_WHEN_NODE_ID_MISSING:
        return state == NODE_ID_STATE_MISSING

    return False


def _primary_reason(
    reason_codes: Sequence[str],
    exclusion_class: str | None,
    sql_reason_code: str,
) -> str:
    """首要原因：排除分类优先，其次是 SQL 资格原因，最后是身份原因。"""

    if exclusion_class == EXCLUSION_INFORMAL and "INFORMAL_TASK_STRONG" in reason_codes:
        return "INFORMAL_TASK_STRONG"

    if exclusion_class == EXCLUSION_IDENTITY and reason_codes:
        return reason_codes[0]

    if sql_reason_code and sql_reason_code != "SQL_ANALYSIS_ELIGIBLE":
        return sql_reason_code

    if reason_codes:
        return reason_codes[0]

    return "UNCLASSIFIED"


def _identity_evidence(rule_id: str, state: str, node_id: int | str | None) -> str:
    if rule_id == "NODE_ID_MISSING":
        return f"node_id 缺失（{node_id!r}）"

    if rule_id == "NODE_ID_INVALID":
        return f"node_id 格式无效（{node_id!r}）"

    return f"node_id 有效（{node_id!r}，状态 {state}）"


def _content_evidence(
    rule_id: str,
    content_state: str,
    expectation: str,
    content_format: str,
) -> str:
    if rule_id == "CONTENT_PRESENT":
        return f"Content 可用（format={content_format}）"

    if rule_id == "CONTENT_GAP_NOT_REQUIRED":
        return f"Content 缺失但类型不要求（format={content_format}，状态 {content_state}）"

    if rule_id == "CONTENT_GAP_REQUIRED":
        return f"Content 缺失但类型预期需要（format={content_format}，状态 {content_state}）"

    return f"Content 缺失且内容期望未知（format={content_format}，状态 {content_state}）"


# ============================================================
# 序列化产物
# ============================================================


def excluded_tasks_payload(scope: FileScope) -> dict[str, Any]:
    """生成 inventory/excluded-tasks.json 的完整结构。

    这是分析范围判定的产物，不是删除任务的指令清单。
    """

    records = scope.excluded()

    return {
        "count": len(records),
        "rules_version": scope.rules_version,
        "rules_path": scope.rules_path,
        "note": (
            "分析范围判定产物：记录被排除出正式业务分析的 DataWorks 资产。"
            "本文件不触发任何删除 / 禁用 / 修改操作，"
            "cleanup_candidate 仅表示值得后续人工核查。"
        ),
        "tasks": [item.to_dict() for item in records],
    }


def review_tasks_payload(scope: FileScope) -> dict[str, Any]:
    """生成 inventory/review-tasks.json 的完整结构。

    待确认对象不计入确定的无效任务，也不因弱证据进入清理候选。
    """

    records = scope.review()

    return {
        "count": len(records),
        "rules_version": scope.rules_version,
        "rules_path": scope.rules_path,
        "note": (
            "弱证据待确认清单：命中非正式任务弱证据规则的对象。"
            "不计入确定的排除任务，不进入清理候选，需人工复核后决定。"
        ),
        "tasks": [item.to_dict() for item in records],
    }

"""Analysis Scope Rules：配置模型、加载与校验。

规则来自 ``config/analysis-scope-rules.yaml``：判定条件、结果与启用状态都在配置里，
代码只解释白名单内的 ``condition.kind``。配置非法时抛 :class:`ScopeRulesError`，
由 Pipeline 转成 Fatal Error，不回退默认值，也不静默忽略。

本模块只负责「配置长什么样、怎么读、怎么校验」；判定执行见
:mod:`data_platform_analysis.analysis.scope.decision`。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .content import (
    CONTENT_STATES,
    EXPECTATION_UNKNOWN,
    EXPECTATIONS,
    ContentCheckConfig,
)

# ============================================================
# 配置词表（白名单）
# ============================================================

EXCLUSION_IDENTITY = "identity"
EXCLUSION_INFORMAL = "informal_task"

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
        "review",
        "content_ok",
        "content_allowed_empty",
        "content_missing",
        "content_expectation_unknown",
        "not_sql_eligible",
        "sql_eligible",
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

SQL_REASON_ANALYSIS_ELIGIBLE = "SQL_ANALYSIS_ELIGIBLE"
"""SQL 分析资格通过的 reason_code（与通过规则同名，来自 config YAML）。

报告须把它与阻断原因（NODE_ID_MISSING 等）分开呈现，
避免「SQL 阻断原因」表里混入通过原因。
"""


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
    """规则判定结果。"""

    classification: str
    reason_code: str
    overall_eligible: bool | None = None
    sql_eligible: bool | None = None
    review_required: bool | None = None


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
    content_check: ContentCheckConfig
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
    未知 condition kind、未知 classification、必需规则组为空、
    ``content_check`` 结构或取值非法都是配置错误，直接抛 ScopeRulesError。
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
            "content_check",
            "sql_capable_content_formats",
            "informal_task_names",
            "rules",
        },
        str(path),
    )

    version = _required_text(raw.get("version"), "version", path)

    expectations = _parse_content_expectations(raw.get("content_expectations"), path)
    content_check = _parse_content_check(raw.get("content_check"), expectations, path)
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
        content_check=content_check,
        sql_capable_content_formats=sql_formats,
        informal_tokens=informal_tokens,
    )


def content_expectation(rules: ScopeRules, content_format: str) -> str:
    """按类型注册表的 content_format 查询内容期望，未知格式返回 unknown。"""

    key = (content_format or "").strip().upper()

    return str(rules.content_expectations.get(key, EXPECTATION_UNKNOWN))


def _parse_content_expectations(value: Any, path: Path) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ScopeRulesError(f"content_expectations 必须是非空映射：{path}")

    parsed: dict[str, str] = {}

    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ScopeRulesError(f"content_expectations 包含空的格式名：{path}")

        if item not in EXPECTATIONS:
            raise ScopeRulesError(
                f"content_expectations.{key} 必须是 {sorted(EXPECTATIONS)} 之一，"
                f"实际为 {item!r}：{path}"
            )

        parsed[key.strip().upper()] = str(item)

    return parsed


def _parse_content_check(
    value: Any,
    expectations: Mapping[str, str],
    path: Path,
) -> ContentCheckConfig:
    """解析 ``content_check``：结构错误、字段缺失、类型错误、未知格式都是配置错误。"""

    if not isinstance(value, dict):
        raise ScopeRulesError(f"content_check 必须是映射：{path}")

    _reject_unknown_keys(value, {"enabled", "enabled_formats"}, str(path))

    enabled = value.get("enabled")

    if not isinstance(enabled, bool):
        raise ScopeRulesError(f"content_check.enabled 必须是布尔值：{path}")

    formats = _parse_format_list(
        value.get("enabled_formats"), "content_check.enabled_formats", path
    )

    unknown = sorted(formats - set(expectations))

    if unknown:
        raise ScopeRulesError(
            f"content_check.enabled_formats 包含 content_expectations 未登记的格式 "
            f"{unknown}：{path}"
        )

    return ContentCheckConfig(enabled=enabled, enabled_formats=formats)


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

    allowed_values = {"expectations": set(EXPECTATIONS), "states": set(CONTENT_STATES)}

    for list_key, allowed in allowed_values.items():
        items = params.get(list_key)

        if items is None:
            continue

        unknown = sorted({str(item) for item in items} - allowed)

        if unknown:
            raise ScopeRulesError(f"{label}.{list_key} 包含未知取值 {unknown}：{path}")

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
        },
        f"{label}（{path}）",
    )

    classification = _required_text(value.get("classification"), f"{label}.classification", path)

    if classification not in CLASSIFICATIONS:
        raise ScopeRulesError(
            f"{label}.classification 必须是 {sorted(CLASSIFICATIONS)} 之一，"
            f"实际为 {classification!r}：{path}"
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

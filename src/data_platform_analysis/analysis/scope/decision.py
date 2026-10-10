"""Analysis Scope Rules 的判定执行：对全量 File 逐个产出无矛盾的分类结果。

处理顺序（确定性，同一文件不会得出互相矛盾的结论）：
``node_identity`` → ``informal_task`` → ``content_state`` → ``sql_eligibility``。

分类只依赖 FileInventory 字段与 :func:`content_state_of` 给出的事实状态，
不依赖时间与随机数：同一份 Inventory 与同一版本规则必然产生相同结果。
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..models import (
    NODE_ID_STATE_MISSING,
    NODE_ID_STATE_VALID,
    FileInventory,
    node_id_state,
)
from ..snapshot import SnapshotReader
from .content import (
    CONTENT_GAP_STATES,
    CONTENT_STATE_EMPTY_TEXT,
    CONTENT_STATE_NOT_CHECKED,
    CONTENT_STATE_NOT_COLLECTED,
    CONTENT_STATE_PATH_MISSING,
    CONTENT_STATE_PRESENT,
    CONTENT_STATE_READ_ERROR,
    EXPECTATION_NOT_REQUIRED,
    EXPECTATION_REQUIRED,
    EXPECTATION_UNKNOWN,
    content_state_of,
)
from .rules import (
    EXCLUSION_IDENTITY,
    EXCLUSION_INFORMAL,
    RULE_TYPE_CONTENT_STATE,
    RULE_TYPE_INFORMAL_TASK,
    RULE_TYPE_NODE_IDENTITY,
    RULE_TYPE_SQL_ELIGIBILITY,
    SQL_BLOCKER_CONTENT,
    SQL_BLOCKER_IDENTITY,
    SQL_BLOCKER_INFORMAL,
    SQL_BLOCKER_NODE_TYPE,
    SQL_REASON_ANALYSIS_ELIGIBLE,
    ScopeCondition,
    ScopeRule,
    ScopeRules,
    content_expectation,
)

INFORMAL_SEPARATOR = re.compile(r"[^0-9a-zA-Z]+")
"""文件名 token 切分：连续的非字母数字字符视为分隔符。"""

INFORMAL_NUMERIC_SUFFIX = re.compile(r"^([0-9a-zA-Z]+?)([0-9]+)$")
"""整名 informal token + 纯数字后缀（例如 test111）的强证据形状。"""


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

    def to_dict(self) -> dict[str, Any]:
        """序列化为 sql-candidates / excluded-tasks / review-tasks 的单条记录。"""

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
        }


@dataclass(frozen=True)
class FileScopeStats:
    """规则分类统计：唯一对象口径与规则命中口径分开。"""

    rules_version: str = ""
    total_count: int = 0

    node_id_valid_count: int = 0
    node_id_missing_count: int = 0

    task_type_counts: Mapping[str, int] = field(default_factory=dict)

    content_not_checked_count: int = 0
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
    sql_eligible_count: int = 0
    sql_ineligible_count: int = 0
    review_count: int = 0

    informal_strong_count: int = 0
    informal_weak_count: int = 0
    informal_absorbed_by_identity_count: int = 0
    """命中会排除整体资格的 informal 规则、但最终 exclusion_class 为 identity 的文件数。

    规则命中数与最终排除分类可能不同：同一文件若同时命中 NODE_ID_MISSING 与
    INFORMAL_TASK_STRONG，identity 排除优先，exclusion_class = identity，
    因此不出现在 informal_excluded_count 中。
    该数字从文件级判定结果直接计算，不是从 rule_hit_counts 与
    exclusion_class_counts 的差值推断。
    """

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

    def sql_candidates(self) -> list[FileScopeDecision]:
        """SQL 分析候选（与 scope/inputs/sql-candidates.json 一致）：sql_eligible = true。"""

        return [item for item in self.decisions if item.sql_eligible]

    def excluded(self) -> list[FileScopeDecision]:
        """SQL 分析排除（与 scope/inputs/excluded-tasks.json 一致）：sql_eligible = false。"""

        return [item for item in self.decisions if not item.sql_eligible]

    def review(self) -> list[FileScopeDecision]:
        """待确认对象（与 scope/review-tasks.json 一致）。"""

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

    def overall_eligible_files(self, files: Sequence[FileInventory]) -> list[FileInventory]:
        """按整体分析资格（overall_eligible）筛选，保持输入顺序。

        与 sql_eligible_files 同源同口径：整体分析资格 =
        身份有效且非明确非正式任务（identity_eligible and not informal_excluded）。
        这是「参与 Analysis 的 File」的权威口径，不等同于 SQL 分析输入。
        """

        index = {(item.workspace_id, item.file_id): item for item in self.decisions}
        selected: list[FileInventory] = []

        for file in files:
            decision = index.get((file.workspace_id, str(file.file_id)))

            if decision is not None and decision.overall_eligible:
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

        # 会排除整体资格的 informal 规则（result.overall_eligible = false）；
        # 这些规则命中若被更高优先级的 identity 排除吸收，只算 identity 分类。
        informal_excluding_ids = {
            rule.id
            for rule in self.rule_index.values()
            if rule.type == RULE_TYPE_INFORMAL_TASK and rule.result.overall_eligible is False
        }

        informal_absorbed_by_identity_count = sum(
            1
            for item in self.decisions
            if item.exclusion_class == EXCLUSION_IDENTITY
            and any(rule_id in informal_excluding_ids for rule_id in item.matched_rule_ids)
        )

        return FileScopeStats(
            rules_version=self.rules_version,
            total_count=len(self.decisions),
            node_id_valid_count=sum(
                1 for item in self.decisions if item.node_id_state == NODE_ID_STATE_VALID
            ),
            node_id_missing_count=sum(
                1 for item in self.decisions if item.node_id_state == NODE_ID_STATE_MISSING
            ),
            task_type_counts=dict(sorted(task_types.items())),
            content_not_checked_count=sum(
                1 for item in self.decisions if item.content_state == CONTENT_STATE_NOT_CHECKED
            ),
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
            sql_eligible_count=sum(1 for item in self.decisions if item.sql_eligible),
            sql_ineligible_count=sum(1 for item in self.decisions if not item.sql_eligible),
            review_count=sum(1 for item in self.decisions if item.review_required),
            informal_strong_count=rule_hits.get("INFORMAL_TASK_STRONG", 0),
            informal_weak_count=rule_hits.get("INFORMAL_TASK_WEAK", 0),
            informal_absorbed_by_identity_count=informal_absorbed_by_identity_count,
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
            content_state=content_state_of(reader, file, content_check=rules.content_check),
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

    身份维度默认放行：未命中任何身份规则时 ``identity_eligible = True``，
    只有命中规则且规则显式声明 ``overall_eligible: false`` 才被排除。
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

    identity_eligible = True

    if identity_rule is not None:
        matched.append(identity_rule)
        reason_codes.append(identity_rule.result.reason_code)
        evidence.append(_identity_evidence(identity_rule.id, state, file.node_id))
        identity_eligible = identity_rule.result.overall_eligible is not False

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

        # 身份阻断时复用实际命中的身份原因（MISSING 由事实决定）。
        if blocker == SQL_BLOCKER_IDENTITY and identity_rule is not None:
            sql_reason_code = identity_rule.result.reason_code

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
    ``not_checked``（未启用 Content 检查）与 ``present`` 一样不构成阻断：
    未检查既不是内容缺失，也不因未检查而阻断分析资格。
    """

    if not identity_eligible:
        blocker: str | None = SQL_BLOCKER_IDENTITY
    elif informal_excluded:
        blocker = SQL_BLOCKER_INFORMAL
    elif (content_format or "").strip().upper() not in rules.sql_capable_content_formats:
        blocker = SQL_BLOCKER_NODE_TYPE
    elif content_state not in (CONTENT_STATE_PRESENT, CONTENT_STATE_NOT_CHECKED):
        blocker = SQL_BLOCKER_CONTENT
    else:
        blocker = None

    rule = _first_match(
        rules.enabled_rules_of(RULE_TYPE_SQL_ELIGIBILITY),
        blocker=blocker,
    )

    return blocker, rule


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

    if sql_reason_code and sql_reason_code != SQL_REASON_ANALYSIS_ELIGIBLE:
        return sql_reason_code

    if reason_codes:
        return reason_codes[0]

    return "UNCLASSIFIED"


def _identity_evidence(rule_id: str, state: str, node_id: int | str | None) -> str:
    if rule_id == "NODE_ID_MISSING":
        return f"node_id 缺失（{node_id!r}）"

    return f"node_id 存在（{node_id!r}，状态 {state}）"


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

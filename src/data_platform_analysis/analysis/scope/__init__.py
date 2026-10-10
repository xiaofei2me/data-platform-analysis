"""M2.1 Analysis Scope Rules：对全量 File 执行一次规则化分类。

本包回答四个问题（Scope 阶段的资格评估职责，消费 Inventory 全量资产）：

1. 资产身份：NodeId 是否缺失、格式是否成立；
2. 内容状态：Content 是否已检查、检查后是否可用、该类型是否预期需要 Content；
3. 分析资格：整体分析范围（overall_eligible）与 SQL 分析输入（sql_eligible）；
4. 非正式任务：测试 / 临时 / 演示任务的强证据排除与弱证据待确认。

两个概念严格分开：

- 资产有效性：对象是否是已知且可追溯的资产（Inventory 全量登记，永不过滤）；
- 分析资格：对象是否适合某项具体分析（overall_eligible / sql_eligible）。

模块划分：

- :mod:`~...scope.content`    Content 是否检查与检查后的事实状态（唯一的文件系统读取点）；
- :mod:`~...scope.rules`      配置模型、加载与校验（配置非法 → ScopeRulesError）；
- :mod:`~...scope.decision`   判定执行与 FileScope / FileScopeDecision / FileScopeStats；
- :mod:`~...scope.outputs`    产物路径常量与 scope/ 下的清单、Summary payload。

正式产物统一归属 ``analysis/scope/``（清单在 ``inputs/``，
规则发现在 ``findings/``，当前尚未实现）。

可复现性：同一份 Inventory 与同一版本规则必然产生相同分类结果；
分类只依赖 FileInventory 字段与只读 Snapshot 内容，不依赖时间与随机数。
"""

from __future__ import annotations

from .content import (
    CONTENT_GAP_STATES,
    CONTENT_READ_LIMIT,
    CONTENT_STATE_EMPTY_TEXT,
    CONTENT_STATE_NOT_CHECKED,
    CONTENT_STATE_NOT_COLLECTED,
    CONTENT_STATE_PATH_MISSING,
    CONTENT_STATE_PRESENT,
    CONTENT_STATE_READ_ERROR,
    CONTENT_STATES,
    EXPECTATION_NOT_REQUIRED,
    EXPECTATION_REQUIRED,
    EXPECTATION_UNKNOWN,
    EXPECTATIONS,
    ContentCheckConfig,
    content_state_of,
)
from .decision import (
    INFORMAL_NUMERIC_SUFFIX,
    INFORMAL_SEPARATOR,
    FileScope,
    FileScopeDecision,
    FileScopeStats,
    build_file_scope,
    classify_file,
    match_informal_name,
)
from .outputs import (
    EXCLUDED_TASKS_RELATIVE_PATH,
    REVIEW_TASKS_RELATIVE_PATH,
    SCOPE_RELATIVE_DIR,
    SCOPE_SUMMARY_JSON_RELATIVE_PATH,
    SCOPE_SUMMARY_MD_RELATIVE_PATH,
    SQL_CANDIDATES_RELATIVE_PATH,
    excluded_tasks_payload,
    review_tasks_payload,
    scope_summary_payload,
    sql_candidates_payload,
)
from .rules import (
    CLASSIFICATIONS,
    CONDITION_KINDS,
    EXCLUSION_IDENTITY,
    EXCLUSION_INFORMAL,
    RULE_TYPE_CONTENT_STATE,
    RULE_TYPE_INFORMAL_TASK,
    RULE_TYPE_NODE_IDENTITY,
    RULE_TYPE_SQL_ELIGIBILITY,
    RULE_TYPES,
    SQL_BLOCKER_CONTENT,
    SQL_BLOCKER_IDENTITY,
    SQL_BLOCKER_INFORMAL,
    SQL_BLOCKER_NODE_TYPE,
    SQL_BLOCKERS,
    ScopeCondition,
    ScopeResult,
    ScopeRule,
    ScopeRules,
    ScopeRulesError,
    content_expectation,
    load_scope_rules,
)

__all__ = [
    "CLASSIFICATIONS",
    "CONDITION_KINDS",
    "CONTENT_GAP_STATES",
    "CONTENT_READ_LIMIT",
    "CONTENT_STATE_EMPTY_TEXT",
    "CONTENT_STATE_NOT_CHECKED",
    "CONTENT_STATE_NOT_COLLECTED",
    "CONTENT_STATE_PATH_MISSING",
    "CONTENT_STATE_PRESENT",
    "CONTENT_STATE_READ_ERROR",
    "CONTENT_STATES",
    "ContentCheckConfig",
    "EXCLUDED_TASKS_RELATIVE_PATH",
    "EXCLUSION_IDENTITY",
    "EXCLUSION_INFORMAL",
    "EXPECTATIONS",
    "EXPECTATION_NOT_REQUIRED",
    "EXPECTATION_REQUIRED",
    "EXPECTATION_UNKNOWN",
    "REVIEW_TASKS_RELATIVE_PATH",
    "RULE_TYPES",
    "RULE_TYPE_CONTENT_STATE",
    "RULE_TYPE_INFORMAL_TASK",
    "RULE_TYPE_NODE_IDENTITY",
    "RULE_TYPE_SQL_ELIGIBILITY",
    "SCOPE_RELATIVE_DIR",
    "SCOPE_SUMMARY_JSON_RELATIVE_PATH",
    "SCOPE_SUMMARY_MD_RELATIVE_PATH",
    "SQL_BLOCKERS",
    "SQL_BLOCKER_CONTENT",
    "SQL_BLOCKER_IDENTITY",
    "SQL_BLOCKER_INFORMAL",
    "SQL_BLOCKER_NODE_TYPE",
    "SQL_CANDIDATES_RELATIVE_PATH",
    "FileScope",
    "FileScopeDecision",
    "FileScopeStats",
    "INFORMAL_NUMERIC_SUFFIX",
    "INFORMAL_SEPARATOR",
    "ScopeCondition",
    "ScopeResult",
    "ScopeRule",
    "ScopeRules",
    "ScopeRulesError",
    "build_file_scope",
    "classify_file",
    "content_expectation",
    "content_state_of",
    "excluded_tasks_payload",
    "load_scope_rules",
    "match_informal_name",
    "review_tasks_payload",
    "scope_summary_payload",
    "sql_candidates_payload",
]

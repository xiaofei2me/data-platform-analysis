"""Analysis Scope Rules 的正式产物：Scope 目录下的清单与 Summary。

产物统一归属 ``analysis/scope/``：

- ``scope/inputs/sql-candidates.json`` ：全部且仅 ``sql_eligible = true``；
- ``scope/inputs/excluded-tasks.json`` ：全部且仅 ``sql_eligible = false``；
- ``scope/review-tasks.json``          ：``review_required = true``（弱证据待确认，
  与前两份是不同维度，可同时出现在候选与待确认里）；
- ``scope/summary.json``               ：资格与规则分类的机器可读统计；
- ``scope/summary.md``                 ：同一份统计的人读报告（由 reports 渲染）。

前两份互斥且合计覆盖全部登记文件；三份清单都是分析范围判定的产物，
不触发任何删除 / 禁用 / 修改操作，也不改变 Inventory 全量资产。

规则发现（``scope/findings/``）当前尚未实现：现有规则只做资格分类与
审核标记，不产出整改问题，因此不生成 findings 产物、不虚构发现数量。
"""

from __future__ import annotations

from typing import Any

from .decision import FileScope

SCOPE_RELATIVE_DIR = "scope"
"""Scope 阶段产物根目录（相对 analysis/）。"""

SQL_CANDIDATES_RELATIVE_PATH = "scope/inputs/sql-candidates.json"
"""SQL 分析候选清单：M2.3 SQL Analysis 的输入契约。"""

EXCLUDED_TASKS_RELATIVE_PATH = "scope/inputs/excluded-tasks.json"
"""SQL 分析排除清单：与候选清单互斥且合计覆盖全部登记文件。"""

REVIEW_TASKS_RELATIVE_PATH = "scope/review-tasks.json"
"""弱证据待确认清单：独立维度，不改变 sql_eligible。"""

SCOPE_SUMMARY_JSON_RELATIVE_PATH = "scope/summary.json"
"""Scope Summary（机器可读统计）。"""

SCOPE_SUMMARY_MD_RELATIVE_PATH = "scope/summary.md"
"""Scope Summary（人读报告）。"""


def _payload(scope: FileScope, records: list[Any], note: str) -> dict[str, Any]:
    return {
        "count": len(records),
        "rules_version": scope.rules_version,
        "rules_path": scope.rules_path,
        "note": note,
        "tasks": [item.to_dict() for item in records],
    }


def sql_candidates_payload(scope: FileScope) -> dict[str, Any]:
    """生成 scope/inputs/sql-candidates.json 的完整结构。

    这是 SQL 分析候选的判定镜像；SQL Analysis 仍通过
    ``FileScope.sql_eligible_files()`` 消费同一份判定，不重新过滤。
    """

    return _payload(
        scope,
        scope.sql_candidates(),
        (
            "分析范围判定产物：记录通过 SQL 分析资格（sql_eligible = true）的 DataWorks 资产，"
            "是 M2.3 SQL Analysis 的候选输入。"
            "本文件与 scope/inputs/excluded-tasks.json 互斥，两者合计覆盖全部登记文件；"
            "清单只是判定结果的镜像，本文件不触发任何删除 / 禁用 / 修改操作。"
        ),
    )


def excluded_tasks_payload(scope: FileScope) -> dict[str, Any]:
    """生成 scope/inputs/excluded-tasks.json 的完整结构。

    这是分析范围判定的产物，不是删除任务的指令清单。
    """

    return _payload(
        scope,
        scope.excluded(),
        (
            "分析范围判定产物：记录未通过 SQL 分析资格（sql_eligible = false）的 DataWorks 资产。"
            "本文件不触发任何删除 / 禁用 / 修改操作；"
            "与 scope/inputs/sql-candidates.json 互斥，两者合计覆盖全部登记文件。"
        ),
    )


def review_tasks_payload(scope: FileScope) -> dict[str, Any]:
    """生成 scope/review-tasks.json 的完整结构。

    待确认对象只是弱证据标记，不改变 sql_eligible，也不计入确定排除。
    """

    return _payload(
        scope,
        scope.review(),
        (
            "弱证据待确认清单：命中非正式任务弱证据规则的对象。"
            "弱证据不改变 sql_eligible，也不计入确定排除，需人工复核后决定。"
            "本文件不触发任何删除 / 禁用 / 修改操作。"
        ),
    )


def scope_summary_payload(scope: FileScope) -> dict[str, Any]:
    """生成 scope/summary.json：Scope 资格与规则分类的机器可读统计。

    全部数字来自 ``FileScope.stats()`` 的既有计算结果，
    不在此重复实现资格判定或规则匹配；findings 尚未实现时如实标注
    count = 0，不虚构整改问题。
    """

    stats = scope.stats()

    return {
        "rules_version": stats.rules_version,
        "rules_path": scope.rules_path,
        "totals": {
            "evaluated_count": stats.total_count,
            "sql_candidates_count": stats.sql_eligible_count,
            "excluded_count": stats.sql_ineligible_count,
            "review_required_count": stats.review_count,
        },
        "eligibility": {
            "overall_eligible_count": stats.overall_eligible_count,
            "identity_excluded_count": stats.identity_excluded_count,
            "informal_excluded_count": stats.informal_excluded_count,
            "sql_eligible_count": stats.sql_eligible_count,
            "sql_ineligible_count": stats.sql_ineligible_count,
            "sql_reason_counts": dict(stats.sql_reason_counts),
            "exclusion_class_counts": dict(stats.exclusion_class_counts),
            "reason_counts": dict(stats.reason_counts),
        },
        "identity": {
            "node_id_valid_count": stats.node_id_valid_count,
            "node_id_missing_count": stats.node_id_missing_count,
            "task_type_counts": dict(stats.task_type_counts),
        },
        "content_states": {
            "present_count": stats.content_present_count,
            "not_checked_count": stats.content_not_checked_count,
            "empty_text_count": stats.content_empty_text_count,
            "not_collected_count": stats.content_not_collected_count,
            "path_missing_count": stats.content_path_missing_count,
            "read_error_count": stats.content_read_error_count,
            "empty_allowed_count": stats.content_empty_allowed_count,
            "empty_unexpected_count": stats.content_empty_unexpected_count,
            "gap_unknown_expectation_count": stats.content_gap_unknown_expectation_count,
            "expectation_unknown_count": stats.content_expectation_unknown_count,
        },
        "rule_hits": {
            "hit_counts": dict(stats.rule_hit_counts),
            "types": dict(stats.rule_types),
            "descriptions": dict(stats.rule_descriptions),
        },
        "findings": {
            "count": 0,
            "note": (
                "Scope 规则发现（scope/findings/）尚未实现："
                "当前规则只做资格分类与审核标记，不产出整改问题，因此不生成发现产物。"
            ),
        },
        "inputs": {
            "sql_candidates": SQL_CANDIDATES_RELATIVE_PATH,
            "excluded_tasks": EXCLUDED_TASKS_RELATIVE_PATH,
            "review_tasks": REVIEW_TASKS_RELATIVE_PATH,
        },
    }

"""M2.1 Analysis Scope Rules 的规则化分类测试。

覆盖：资格判定（overall_eligible / sql_eligible）、非正式任务强弱证据、
内容状态阻断、排除 / 待确认两份产物，以及配置非法时的 fail-fast。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import assert_sandbox, write_snapshot


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_scope_products_written_and_classified(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """排除 / 待确认清单与全量清单同时产出，分类互斥且不删除任何记录。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_daily",
                "node_id": "7001",
                "content": "INSERT INTO ${ws_a}.t1 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "no_node",
                "content": "INSERT INTO ${ws_a}.t2 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "103",
                "file_name": "test",
                "node_id": "7003",
                "content": "INSERT INTO ${ws_a}.t3 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "104",
                "file_name": "imp_s_ka_stock_test",
                "node_id": "7004",
                "content": "INSERT INTO ${ws_a}.t4 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "105",
                "file_name": "test_001",
                "content": "INSERT INTO ${ws_a}.t5 SELECT 1;",
            },
        ],
    )

    assert run_cli("analyze", "--stage", "inventory") == 0

    # 全量清单不因分类减少任何记录。
    assert _read(Path("analysis/inventory/files.json"))["count"] == 5

    excluded = _read(Path("analysis/inventory/excluded-tasks.json"))
    review = _read(Path("analysis/inventory/review-tasks.json"))

    assert excluded["count"] == 3
    assert review["count"] == 1

    excluded_by_id = {item["file_id"]: item for item in excluded["tasks"]}

    assert set(excluded_by_id) == {"102", "103", "105"}
    assert excluded_by_id["102"]["exclusion_class"] == "identity"
    assert excluded_by_id["102"]["reason_code"] == "NODE_ID_MISSING"
    assert excluded_by_id["103"]["exclusion_class"] == "informal_task"
    # 清理候选需要两条独立证据：非正式命名 + 未提交节点。
    assert excluded_by_id["103"]["cleanup_candidate"] is False
    assert excluded_by_id["105"]["exclusion_class"] == "identity"
    assert "INFORMAL_TASK_STRONG" in excluded_by_id["105"]["matched_rule_ids"]
    assert excluded_by_id["105"]["cleanup_candidate"] is True

    # 清单是分析范围判定的产物，不是删除指令。
    assert "不触发任何删除" in excluded["note"]
    assert review["tasks"][0]["file_id"] == "104"
    assert review["tasks"][0]["review_required"] is True
    assert review["tasks"][0]["cleanup_candidate"] is False


def test_informal_name_matching_is_whole_token(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """强证据要求整名命中，弱证据要求独立 token，不误伤业务任务名。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "201",
                "file_name": "contest",
                "node_id": "7101",
                "content": "INSERT INTO ${ws_a}.t1 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "202",
                "file_name": "test",
                "node_id": "7102",
                "content": "INSERT INTO ${ws_a}.t2 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "203",
                "file_name": "tmp_dws_order",
                "node_id": "7103",
                "content": "INSERT INTO ${ws_a}.t3 SELECT 1;",
            },
        ],
    )

    assert run_cli("analyze", "--stage", "inventory") == 0

    excluded = _read(Path("analysis/inventory/excluded-tasks.json"))
    review = _read(Path("analysis/inventory/review-tasks.json"))

    # contest 含 test 子串，但不是整词，不命中任何非正式任务规则。
    assert {item["file_id"] for item in excluded["tasks"]} == {"202"}
    assert {item["file_id"] for item in review["tasks"]} == {"203"}


def test_sql_input_follows_unified_eligibility(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """SQL Analysis 只消费统一资格判定：身份、格式、内容三项缺一不可。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "301",
                "file_name": "etl_ok",
                "node_id": "7201",
                "content": "INSERT INTO ${ws_a}.t1 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "302",
                "file_name": "python_job",
                "node_id": "7202",
                "content": "print('x')",
                "file_type": 22,
                "content_format": "PYTHON",
            },
            {
                "workspace_id": 9001,
                "file_id": "303",
                "file_name": "no_node_sql",
                "content": "INSERT INTO ${ws_a}.t3 SELECT 1;",
            },
        ],
    )

    assert run_cli("analyze", "--stage", "evidence") == 0

    statements = _read(Path("analysis/evidence/sql/statements.json"))
    assert {item["file_id"] for item in statements["statements"]} == {"301"}

    # 非 SQL 格式与身份不满足的对象留在清单里，只是不进入 SQL 输入。
    assert _read(Path("analysis/inventory/files.json"))["count"] == 3

    excluded = _read(Path("analysis/inventory/excluded-tasks.json"))
    assert {item["file_id"] for item in excluded["tasks"]} == {"303"}


def test_content_gap_blocks_sql_and_keeps_inventory_error(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Content 缺失在 Inventory 阶段分类并记录，不再进入 SQL 分析。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "401",
                "file_name": "etl_missing_content",
                "node_id": "7301",
                "content": "INSERT INTO ${ws_a}.t1 SELECT 1;",
            }
        ],
    )

    missing = assert_sandbox(
        Path("source/dataworks/workspaces/9001/content/401__etl_missing_content.sql")
    )
    missing.unlink()

    assert run_cli("analyze", "--stage", "evidence") == 0

    statements = _read(Path("analysis/evidence/sql/statements.json"))
    assert statements["count"] == 0

    # Snapshot 完整性问题仍然记录，只是归属 Inventory 阶段。
    errors = _read(Path("analysis/evidence/errors.json"))
    assert errors["count"] == 1
    assert errors["errors"][0]["error_type"] == "CONTENT_FILE_MISSING"
    assert errors["errors"][0]["stage"] == "inventory"
    assert errors["errors"][0]["file_id"] == "401"

    summary = Path("analysis/inventory/summary.md").read_text(encoding="utf-8")
    assert "| SQL_BLOCKED_BY_CONTENT |" in summary


def test_inventory_summary_reports_scope_counts(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Summary 第 11 节给出规则分类统计，且互斥口径能加回总数。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "501",
                "file_name": "etl_ok",
                "node_id": "7401",
                "content": "INSERT INTO ${ws_a}.t1 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "502",
                "file_name": "no_node",
                "content": "INSERT INTO ${ws_a}.t2 SELECT 1;",
            },
        ],
    )

    assert run_cli("analyze", "--stage", "inventory") == 0

    summary = Path("analysis/inventory/summary.md").read_text(encoding="utf-8")

    assert "## 11. 分析范围规则分类" in summary
    assert "| 登记文件 | 2 |" in summary
    assert "| 整体分析资格 | 1 |" in summary
    assert "| SQL 分析输入 | 1 |" in summary
    assert "| 明确排除 | 1 |" in summary
    # 排除 ≠ 删除，也不等于清理候选。
    assert "不是删除、禁用或修改 DataWorks 资产的指令" in summary
    assert "| 清理候选 | 0 |" in summary

    # Node ID 状态互斥且合计等于登记文件。
    assert "| Node ID 状态 | valid（有效） | 1 |" in summary
    assert "| Node ID 状态 | missing（缺失） | 1 |" in summary


def test_invalid_rules_config_fails_fast(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """规则配置非法时直接失败，不回退默认规则也不静默忽略。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "601",
                "file_name": "etl_a",
                "node_id": "7501",
                "content": "INSERT INTO ${ws_a}.t1 SELECT 1;",
            }
        ],
    )

    bad_rules = Path("config/bad-scope-rules.yaml")
    bad_rules.parent.mkdir(parents=True, exist_ok=True)
    bad_rules.write_text(
        'version: "1.0"\n'
        "rules: []\n"
        "content_expectations: {}\n"
        "sql_capable_content_formats: [SQL]\n"
        "informal_task_names:\n"
        "  tokens: [test]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SCOPE_RULES_PATH", str(bad_rules))

    assert run_cli("analyze", "--stage", "inventory") == 1
    assert not Path("analysis/inventory/files.json").exists()

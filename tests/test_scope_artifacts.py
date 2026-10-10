"""Scope 产物目录契约与人工 checklist 保护的黑盒测试。

覆盖：

1. Scope 正式产物统一归属 analysis/scope/（清单在 inputs/、Summary 在根），
   Inventory 目录不再承载资格清单；
2. scope/summary.json 的统计与清单契约一致，findings 未实现时如实标注
   count = 0、不生成 findings 产物；
3. 全量 / 阶段运行的清场保留人工回填 checklist（M3.6 两份裁决清单），
   carry-over 机制在重跑后继续合并人工列；
4. 生产 analysis/ 与 source/ 不被测试触碰（cli_env 沙箱 + assert_sandbox）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import write_snapshot


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_fixture_snapshot() -> None:
    """一份能同时产出 Inventory / Scope / Evidence / Review 产物的最小 Snapshot。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_ok",
                "node_id": "7001",
                "content": "INSERT INTO ${ws_a}.dwd_order SELECT * FROM ${ws_a}.ods_order;",
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "no_node",
                "content": "INSERT INTO ${ws_a}.t2 SELECT 1;",
            },
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [
                    {"name": "id", "type": "STRING"},
                    {"name": "amt", "type": "DOUBLE"},
                ],
            },
            {
                "workspace_id": 9001,
                "table": "ods_order",
                "columns": [{"name": "id", "type": "STRING"}],
            },
        ],
    )


# ============================================================
# 1. Scope 产物目录归属
# ============================================================


def test_scope_products_live_under_scope_dir(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Scope 清单与 Summary 写入 scope/；Inventory 目录只剩资产盘点产物。"""

    _write_fixture_snapshot()

    assert run_cli("analyze", "--stage", "inventory") == 0

    scope_dir = Path("analysis/scope")

    for name in (
        "inputs/sql-candidates.json",
        "inputs/excluded-tasks.json",
        "review-tasks.json",
        "summary.json",
        "summary.md",
    ):
        assert (scope_dir / name).exists(), name

    # Inventory 只保留资产索引与盘点报告，不再承载 Scope 清单。
    inventory_names = {path.name for path in Path("analysis/inventory").iterdir()}
    assert inventory_names == {
        "workspaces.json",
        "files.json",
        "tables.json",
        "columns.json",
        "summary.md",
    }
    assert not (scope_dir / "findings" / "rule-findings.json").exists()


def test_scope_inventory_stage_writes_only_assets_and_scope(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """--stage inventory 只重建 inventory/ + scope/ + 根 summary.md。"""

    _write_fixture_snapshot()

    assert run_cli("analyze", "--stage", "inventory") == 0

    root_names = {path.name for path in Path("analysis").iterdir()}
    assert root_names == {"inventory", "scope", "summary.md"}


def test_candidates_and_excluded_are_complementary(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """候选与排除清单互斥且合计覆盖评估集合；Inventory 保留全部资产。"""

    _write_fixture_snapshot()

    assert run_cli("analyze", "--stage", "inventory") == 0

    files = _read(Path("analysis/inventory/files.json"))
    candidates = _read(Path("analysis/scope/inputs/sql-candidates.json"))
    excluded = _read(Path("analysis/scope/inputs/excluded-tasks.json"))
    review = _read(Path("analysis/scope/review-tasks.json"))

    assert files["count"] == 2
    assert candidates["count"] == 1
    assert excluded["count"] == 1
    assert candidates["count"] + excluded["count"] == files["count"]
    assert not (
        {item["file_id"] for item in candidates["tasks"]}
        & {item["file_id"] for item in excluded["tasks"]}
    )
    # 被排除的资产仍完整保留在 Inventory。
    assert {item["file_id"] for item in files["files"]} == {"101", "102"}
    assert {item["file_id"] for item in excluded["tasks"]} == {"102"}
    assert review["count"] == 0


# ============================================================
# 2. scope/summary.json 契约
# ============================================================


def test_scope_summary_json_matches_lists_and_needs_fabrication(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """summary.json 统计来自既有判定；findings 未实现时如实为 0。"""

    _write_fixture_snapshot()

    assert run_cli("analyze", "--stage", "inventory") == 0

    payload = _read(Path("analysis/scope/summary.json"))
    candidates = _read(Path("analysis/scope/inputs/sql-candidates.json"))
    excluded = _read(Path("analysis/scope/inputs/excluded-tasks.json"))

    assert payload["totals"]["evaluated_count"] == candidates["count"] + excluded["count"]
    assert payload["totals"]["sql_candidates_count"] == candidates["count"]
    assert payload["totals"]["excluded_count"] == excluded["count"]
    assert payload["eligibility"]["sql_eligible_count"] == candidates["count"]
    assert payload["identity"]["node_id_valid_count"] == 1
    assert payload["identity"]["node_id_missing_count"] == 1

    # 内容状态：present 与 not_checked 不混淆，缺口单独计数。
    assert payload["content_states"]["present_count"] == 2
    assert payload["content_states"]["not_checked_count"] == 0
    assert payload["content_states"]["path_missing_count"] == 0

    # 规则发现尚未实现：不虚构数量，不生成 findings 产物。
    assert payload["findings"]["count"] == 0
    assert "尚未实现" in payload["findings"]["note"]
    assert payload["inputs"]["sql_candidates"] == "scope/inputs/sql-candidates.json"
    assert payload["inputs"]["excluded_tasks"] == "scope/inputs/excluded-tasks.json"

    # Scope Summary 报告指向新路径，不再引用 inventory/ 下的清单。
    summary_md = Path("analysis/scope/summary.md").read_text(encoding="utf-8")
    assert "scope/inputs/sql-candidates.json" in summary_md
    assert "inventory/sql-candidates.json" not in summary_md


# ============================================================
# 3. 人工回填 checklist 保护
# ============================================================


def _backfill_checklists() -> tuple[str, str]:
    """在两份 M3.6 裁决清单的真实行上回填人工三列，返回回填后的片段。"""

    finding_path = Path("analysis/review/current-state-review-checklist.md")
    problem_path = Path("analysis/review/current-state-problem-review-checklist.md")

    finding_text = finding_path.read_text(encoding="utf-8")
    problem_text = problem_path.read_text(encoding="utf-8")

    assert "| model_finding_0001 |" in finding_text
    assert "| problem_0001 |" in problem_text

    finding_text = finding_text.replace(
        "需要补识别？ | pending |  |  |",
        "需要补识别？ | confirmed | 李四 | 已确认维度集合 |",
        1,
    )
    problem_text = problem_text.replace(
        "需要补识别？ | pending |  |  |",
        "需要补识别？ | confirmed | 李四 | 已确认维度问题 |",
        1,
    )

    finding_path.write_text(finding_text, encoding="utf-8")
    problem_path.write_text(problem_text, encoding="utf-8")

    return "李四 | 已确认维度集合", "李四 | 已确认维度问题"


def test_manual_checklists_survive_stage_reset_and_full_rerun(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """清场保留人工回填：evidence 清场不丢清单，全量重跑 carry-over 人工列。"""

    _write_fixture_snapshot()

    assert run_cli("analyze") == 0

    finding_marker, problem_marker = _backfill_checklists()

    # ---- --stage evidence 触发全量清场：两份清单必须原样保留 ----
    assert run_cli("analyze", "--stage", "evidence") == 0

    finding_text = Path("analysis/review/current-state-review-checklist.md").read_text(
        encoding="utf-8"
    )
    problem_text = Path("analysis/review/current-state-problem-review-checklist.md").read_text(
        encoding="utf-8"
    )
    assert finding_marker in finding_text
    assert problem_marker in problem_text

    # ---- 全量重跑：机器列重算，人工三列经 carry-over 保留 ----
    assert run_cli("analyze") == 0

    finding_text = Path("analysis/review/current-state-review-checklist.md").read_text(
        encoding="utf-8"
    )
    problem_text = Path("analysis/review/current-state-problem-review-checklist.md").read_text(
        encoding="utf-8"
    )
    assert finding_marker in finding_text
    assert problem_marker in problem_text
    assert "confirmed | 李四 | 已确认维度集合" in finding_text
    assert "confirmed | 李四 | 已确认维度问题" in problem_text

    # 人工回填同步回写 JSON status：机器阶段永远不写 confirmed。
    problems = _read(Path("analysis/review/current-state-problems.json"))
    assert problems["status_counts"].get("confirmed") == 1
    problem_by_id = {item["problem_id"]: item for item in problems["problems"]}
    assert problem_by_id["problem_0001"]["status"] == "confirmed"

"""Inventory 与 Scope 的职责边界与统计口径测试。

覆盖任务要求：

1. `build_inventory_summary()` 不再依赖 FileScope，也不执行任何 Scope 判定；
2. 内容状态是唯一实现（analysis/scope/content.py）的采集事实，
   Inventory Summary 与 Scope Summary 的六态数字必须一致；
3. Scope Summary 只来自 FileScope.stats()，md 与 json 同源，渲染层不重算；
4. 资格清单互斥且穷尽，待确认是独立维度、不参与加总；
5. 规则发现状态如实标注 not_implemented，且 md / json 共用同一常量；
6. 已移除的资格字段与口径不再出现在 Inventory 模型与源码中。
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import fields
from pathlib import Path
from typing import Any

from helpers import assert_sandbox, write_snapshot

from data_platform_analysis.analysis.errors import ErrorLedger
from data_platform_analysis.analysis.inventory.inventory import (
    DataWorksInventorySummary,
    Inventory,
    InventoryBuilder,
    WorkspaceInventorySummary,
    build_inventory_summary,
)
from data_platform_analysis.analysis.scope import (
    FINDINGS_STATUS_NOT_IMPLEMENTED,
    ContentCheckConfig,
    build_file_scope,
    content_state_of,
    load_scope_rules,
    scope_summary_payload,
)
from data_platform_analysis.analysis.scope import decision as scope_decision
from data_platform_analysis.analysis.snapshot import SnapshotReader
from data_platform_analysis.config import settings

REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_MODULE = (
    REPO_ROOT / "src" / "data_platform_analysis" / "analysis" / "inventory" / "inventory.py"
)

REMOVED_INVENTORY_IDENTIFIERS = (
    "eligible_count",
    "eligible_sql_format_count",
    "eligible_content_available_count",
    "eligible_sql_content_count",
    "eligible_file_count",
    "is_analysis_eligible",
    "build_file_scope",
    "sql_eligible_files",
)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_inventory(source_dir: Path) -> tuple[Inventory, SnapshotReader]:
    """在当前沙盒 Snapshot 上构建 Inventory，返回清单与只读 Snapshot 访问器。"""

    reader = SnapshotReader(source_dir=source_dir, ledger=ErrorLedger())
    identities = reader.select_identities(reader.load_workspace_identities(), None)
    return InventoryBuilder(reader=reader, identities=identities).build(), reader


def _sample_snapshot() -> None:
    """两个 SQL 文件（一个有 Node ID，一个缺失）+ 一个 Python 文件。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": "7001",
                "content": "INSERT INTO t SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "draft_a",
                "content": "INSERT INTO t SELECT 2;",
            },
            {
                "workspace_id": 9001,
                "file_id": "103",
                "file_name": "py_job",
                "node_id": "7003",
                "content": "print('x')",
                "content_format": "PYTHON",
            },
        ],
    )


# ============================================================
# 1. Inventory Summary 不依赖 Scope 判定
# ============================================================


def test_build_inventory_summary_signature_has_no_scope() -> None:
    """签名只接受 Inventory 数据 + 客观的 content_check，不接受 FileScope。"""

    parameters = inspect.signature(build_inventory_summary).parameters

    assert "scope" not in parameters
    assert "content_check" in parameters
    assert parameters["content_check"].kind is inspect.Parameter.KEYWORD_ONLY


def test_inventory_module_has_no_scope_dependency() -> None:
    """Inventory 模型层源码不引用任何 Scope 判定符号。"""

    source = INVENTORY_MODULE.read_text(encoding="utf-8")

    for identifier in REMOVED_INVENTORY_IDENTIFIERS:
        assert identifier not in source, identifier

    # 只允许引用内容事实（content_state_of / ContentCheckConfig），
    # 不允许引用 scope 的判定模块入口。
    assert "from ..scope.content import" in source
    assert "from ..scope.decision import" not in source
    assert "from ..scope import" not in source


def test_build_inventory_summary_never_invokes_scope_judgment(
    cli_env: Any,
    monkeypatch: Any,
) -> None:
    """构建 Inventory Summary 时，Scope 判定入口即使被调用也会立刻失败。"""

    _sample_snapshot()
    inventory, reader = _build_inventory(Path("source"))

    def _boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("Inventory Summary 不得执行 Scope 判定")

    monkeypatch.setattr(scope_decision, "build_file_scope", _boom)
    monkeypatch.setattr(scope_decision, "classify_file", _boom)
    monkeypatch.setattr(scope_decision.FileScope, "stats", _boom)

    summary = build_inventory_summary(
        inventory,
        reader=reader,
        content_check=ContentCheckConfig(
            enabled=True,
            enabled_formats=frozenset({"SQL"}),
        ),
    )

    assert summary.dataworks.registered_count == 3
    assert summary.dataworks.valid_node_id_count == 2
    assert summary.dataworks.missing_node_id_count == 1


def test_removed_eligibility_fields_are_gone() -> None:
    """模型上只保留资产事实字段，资格字段已删除、内容六态字段已新增。"""

    dataworks_fields = {item.name for item in fields(DataWorksInventorySummary)}
    workspace_fields = {item.name for item in fields(WorkspaceInventorySummary)}

    assert dataworks_fields.isdisjoint(
        {
            "eligible_count",
            "eligible_sql_format_count",
            "eligible_content_available_count",
            "eligible_sql_content_count",
        }
    )
    assert "content_state_counts" in dataworks_fields

    assert "eligible_file_count" not in workspace_fields
    assert "valid_node_id_count" in workspace_fields


# ============================================================
# 2. 内容状态语义：未检查 / 缺口 / 可用严格分开
# ============================================================


def test_content_check_disabled_reports_not_checked_only(cli_env: Any) -> None:
    """关闭 Content 检查：全部 not_checked，三桶都不计，绝不记作缺失。"""

    _sample_snapshot()
    inventory, reader = _build_inventory(Path("source"))

    summary = build_inventory_summary(
        inventory,
        reader=reader,
        content_check=ContentCheckConfig(enabled=False, enabled_formats=frozenset()),
    )

    counts = summary.dataworks.content_state_counts

    assert counts["not_checked"] == 3
    assert counts["present"] == 0
    assert sum(counts.values()) == 3
    assert summary.dataworks.content_not_checked_count == 3
    assert summary.dataworks.content_available_count == 0
    assert summary.dataworks.content_unavailable_count == 0


def test_content_check_enabled_separates_gap_states(cli_env: Any) -> None:
    """启用检查：present / path_missing / not_checked 各归各桶，六态互斥。"""

    _sample_snapshot()
    assert_sandbox(Path("source/dataworks/workspaces/9001/content/101__etl_a.sql")).unlink()
    inventory, reader = _build_inventory(Path("source"))

    summary = build_inventory_summary(
        inventory,
        reader=reader,
        content_check=ContentCheckConfig(
            enabled=True,
            enabled_formats=frozenset({"SQL"}),
        ),
    )

    counts = summary.dataworks.content_state_counts

    # 101 SQL 内容文件被删除 → path_missing；102 SQL 存在 → present；
    # 103 PYTHON 未启用检查 → not_checked。
    assert counts["path_missing"] == 1
    assert counts["present"] == 1
    assert counts["not_checked"] == 1
    assert sum(counts.values()) == 3

    assert summary.dataworks.content_unavailable_count == 1
    assert summary.dataworks.content_path_missing_count == 1
    assert summary.dataworks.content_available_count == 1
    assert summary.dataworks.content_not_checked_count == 1


def test_content_state_comes_from_single_authoritative_implementation(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Inventory Summary 的六态计数 = content_state_of() 直接统计结果。"""

    _sample_snapshot()

    assert run_cli("analyze", "--stage", "inventory") == 0

    inventory, reader = _build_inventory(Path("source"))
    content_check = load_scope_rules(settings.scope_rules_path).content_check

    expected: dict[str, int] = {}
    for file in inventory.files:
        state = content_state_of(reader, file, content_check=content_check)
        expected[state] = expected.get(state, 0) + 1

    summary_md = Path("analysis/inventory/summary.md").read_text(encoding="utf-8")

    for state, count in expected.items():
        assert re.search(rf"^\| {re.escape(state)} \| {count:,} \|", summary_md, re.M), state

    assert re.search(r"^\| \*\*合计\*\* \| 3 \|", summary_md, re.M)


# ============================================================
# 3. Scope Summary 只来自 FileScope，md 与 json 同源
# ============================================================


def test_scope_summary_payload_is_derived_from_file_scope(cli_env: Any) -> None:
    """payload 的每个数字都能由 FileScope 自己的集合推导出来。"""

    _sample_snapshot()
    inventory, reader = _build_inventory(Path("source"))
    rules = load_scope_rules(settings.scope_rules_path)

    workspace_names = {
        workspace.workspace_id: workspace.workspace_name for workspace in inventory.workspaces
    }
    scope = build_file_scope(
        inventory.files,
        workspace_names,
        rules=rules,
        reader=reader,
    )
    payload = scope_summary_payload(scope)

    candidates = {(item.workspace_id, item.file_id) for item in scope.sql_candidates()}
    excluded = {(item.workspace_id, item.file_id) for item in scope.excluded()}
    review = {(item.workspace_id, item.file_id) for item in scope.review()}
    registered = {(item.workspace_id, str(item.file_id)) for item in inventory.files}

    assert candidates.isdisjoint(excluded)
    assert candidates | excluded == registered
    assert payload["totals"]["evaluated_count"] == len(registered)
    assert payload["totals"]["sql_candidates_count"] == len(candidates)
    assert payload["totals"]["excluded_count"] == len(excluded)
    assert payload["totals"]["review_required_count"] == len(review)
    assert payload["eligibility"]["overall_eligible_count"] == sum(
        1 for item in scope.decisions if item.overall_eligible
    )


def test_scope_summary_md_and_json_use_the_same_numbers(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """人读报告的头条数字逐个出现在机器可读 Summary 里。"""

    _sample_snapshot()

    assert run_cli("analyze", "--stage", "inventory") == 0

    payload = _read(Path("analysis/scope/summary.json"))
    summary_md = Path("analysis/scope/summary.md").read_text(encoding="utf-8")

    totals = payload["totals"]
    identity = payload["identity"]

    assert f"| 登记文件 | {totals['evaluated_count']} |" in summary_md
    assert f"| SQL 候选 | {totals['sql_candidates_count']} |" in summary_md
    assert f"| SQL 分析排除 | {totals['excluded_count']} |" in summary_md
    assert f"| 待确认 | {totals['review_required_count']} |" in summary_md
    assert f"| Node ID 状态 | valid（有效） | {identity['node_id_valid_count']} |" in summary_md
    assert f"| Node ID 状态 | missing（缺失） | {identity['node_id_missing_count']} |" in summary_md

    # 两份资格清单互斥且穷尽（按 workspace_id + file_id 复合身份）。
    candidates = _read(Path("analysis/scope/inputs/sql-candidates.json"))["tasks"]
    excluded = _read(Path("analysis/scope/inputs/excluded-tasks.json"))["tasks"]
    files = _read(Path("analysis/inventory/files.json"))["files"]

    candidate_keys = {(int(item["workspace_id"]), str(item["file_id"])) for item in candidates}
    excluded_keys = {(int(item["workspace_id"]), str(item["file_id"])) for item in excluded}
    file_keys = {(int(item["workspace_id"]), str(item["file_id"])) for item in files}

    assert candidate_keys.isdisjoint(excluded_keys)
    assert candidate_keys | excluded_keys == file_keys


def test_inventory_and_scope_share_content_state_numbers(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """同一份 Snapshot 下，两份 Summary 的内容状态数字必须一致。"""

    _sample_snapshot()

    assert run_cli("analyze", "--stage", "inventory") == 0

    inventory_md = Path("analysis/inventory/summary.md").read_text(encoding="utf-8")
    payload = _read(Path("analysis/scope/summary.json"))
    states = payload["content_states"]

    assert f"| present | {states['present_count']} |" in inventory_md
    assert f"| not_checked | {states['not_checked_count']} |" in inventory_md
    assert f"| path_missing | {states['path_missing_count']} |" in inventory_md


def test_review_is_independent_dimension(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """弱证据待确认不改变资格，也不计入两份资格清单的加总。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "dwd_order_test",
                "node_id": "7001",
                "content": "INSERT INTO t SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "dwd_order",
                "node_id": "7002",
                "content": "INSERT INTO t SELECT 2;",
            },
        ],
    )

    assert run_cli("analyze", "--stage", "inventory") == 0

    payload = _read(Path("analysis/scope/summary.json"))
    candidates = _read(Path("analysis/scope/inputs/sql-candidates.json"))["tasks"]
    review = _read(Path("analysis/scope/review-tasks.json"))["tasks"]

    candidate_keys = {(int(item["workspace_id"]), str(item["file_id"])) for item in candidates}
    review_keys = {(int(item["workspace_id"]), str(item["file_id"])) for item in review}

    # 弱证据命中者仍然是 SQL 候选：两个维度可以重叠。
    assert (9001, "101") in candidate_keys
    assert (9001, "101") in review_keys

    # 待确认不参与资格清单加总。
    assert payload["totals"]["review_required_count"] == 1
    assert payload["totals"]["sql_candidates_count"] == 2
    assert payload["totals"]["excluded_count"] == 0


def test_findings_status_is_marked_not_implemented(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """规则发现未实现：json 有 status 字段，md 与 json 共用同一常量。"""

    _sample_snapshot()

    assert run_cli("analyze", "--stage", "inventory") == 0

    payload = _read(Path("analysis/scope/summary.json"))
    summary_md = Path("analysis/scope/summary.md").read_text(encoding="utf-8")

    assert payload["findings"]["status"] == FINDINGS_STATUS_NOT_IMPLEMENTED
    assert FINDINGS_STATUS_NOT_IMPLEMENTED == "not_implemented"
    assert payload["findings"]["count"] == 0

    assert "| findings.status | not_implemented |" in summary_md
    assert "| findings.count | 0 |" in summary_md


# ============================================================
# 4. 阶段契约（逃生条款的落地说明）
# ============================================================


def test_stage_inventory_contract_also_writes_scope(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """`--stage inventory` 按 Stage 01 契约同时产出 inventory/ 与 scope/。

    Stage 01（docs/STAGE_INDEX.md）= Inventory + Scope 两份产物，
    因此**不允许**只跑 Inventory 而完全不构建 Scope：
    Scope 规则非法时整个阶段以退出码 1 失败（见
    tests/test_analysis_scope_rules.py）。这里记录该契约：
    两份产物同阶段产出，但 Inventory Summary 本身不消费 Scope 判定。
    """

    _sample_snapshot()

    assert run_cli("analyze", "--stage", "inventory") == 0

    assert Path("analysis/inventory/files.json").exists()
    assert Path("analysis/inventory/summary.md").exists()
    assert Path("analysis/scope/summary.md").exists()
    assert Path("analysis/scope/inputs/sql-candidates.json").exists()

    # 阶段产物各自独立：Inventory 报告不含 Scope 口径。
    inventory_md = Path("analysis/inventory/summary.md").read_text(encoding="utf-8")
    assert "| 整体分析资格 |" not in inventory_md
    assert "| SQL 分析排除 |" not in inventory_md
    assert "| 当前分析候选 |" not in inventory_md

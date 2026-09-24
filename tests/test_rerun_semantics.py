"""Ticket 04：重复执行语义——权威清理与注册表 upsert。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _ws(workspace_id: int, name: str) -> dict[str, Any]:
    return {
        "id": workspace_id,
        "name": name,
        "maxcompute_project": "mc_demo",
    }


def _two_nodes() -> list[dict[str, Any]]:
    return [
        {
            "NodeId": "101",
            "NodeName": "keep_me",
            "NodeType": "Shell",
            "Script": "SELECT 1;",
        },
        {
            "NodeId": "102",
            "NodeName": "ghost_me",
            "NodeType": "Shell",
            "Script": "SELECT 2;",
        },
    ]


def test_ghost_node_files_cleaned_on_rerun(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """上游删除的节点在重采后不再残留（权威集合清理）。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        json.dumps([_ws(9001, "ws-a")]),
    )

    cli_env.nodes_by_project[9001] = _two_nodes()
    assert run_cli("dataworks") == 0

    base = (
        Path("source")
        / "dataworks"
        / "workspaces"
        / "9001"
    )
    assert (base / "nodes" / "101.json").exists()
    assert (base / "nodes" / "102.json").exists()
    assert (base / "sql" / "102_1.sql").exists()

    # 上游删除 102 后重采。
    cli_env.nodes_by_project[9001] = _two_nodes()[:1]
    assert run_cli("dataworks") == 0

    assert (base / "nodes" / "101.json").exists()
    assert not (base / "nodes" / "102.json").exists()
    assert not (base / "sql" / "102_1.sql").exists()


def test_failed_node_old_files_kept(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """本次 get_node 失败的节点保留上一次成功采集的文件。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        json.dumps([_ws(9001, "ws-a")]),
    )

    cli_env.nodes_by_project[9001] = _two_nodes()
    assert run_cli("dataworks") == 0

    base = (
        Path("source")
        / "dataworks"
        / "workspaces"
        / "9001"
    )

    # 102 仍在权威列表中，但详情获取失败。
    cli_env.failing_node_ids[9001] = {"102"}
    assert run_cli("dataworks") == 1

    # 旧文件保留。
    assert (base / "nodes" / "102.json").exists()
    assert (base / "sql" / "102_1.sql").exists()

    index = json.loads(
        (base / "nodes-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert [n["node_id"] for n in index["nodes"]] == [
        "101"
    ]
    assert index["failed_nodes"] == [
        {"node_id": "102"}
    ]


def test_failed_workspace_no_cleanup(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """采集失败的 Workspace 不执行清理，保留旧 Snapshot。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        json.dumps(
            [
                _ws(9001, "ws-a"),
                _ws(9002, "ws-b"),
            ]
        ),
    )

    cli_env.nodes_by_project[9001] = _two_nodes()[:1]
    cli_env.nodes_by_project[9002] = _two_nodes()
    assert run_cli("dataworks") == 0

    ws_b = (
        Path("source")
        / "dataworks"
        / "workspaces"
        / "9002"
    )
    assert (ws_b / "nodes" / "101.json").exists()
    assert (ws_b / "nodes" / "102.json").exists()

    # 9002 整体失败。
    cli_env.failing_projects.add(9002)
    assert run_cli("dataworks") == 1

    # 旧文件全部保留。
    assert (ws_b / "nodes" / "101.json").exists()
    assert (ws_b / "nodes" / "102.json").exists()

    workspaces_index = json.loads(
        (
            Path("source")
            / "dataworks"
            / "workspaces-index.json"
        ).read_text(encoding="utf-8")
    )
    entries = {
        e["id"]: e
        for e in workspaces_index["workspaces"]
    }
    assert entries[9002]["status"] == "failed"


def test_workspaces_index_upsert_preserves_unlisted_entries(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """从配置移除的 Workspace：index 条目与目录均不自动删除。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        json.dumps(
            [
                _ws(9001, "ws-a"),
                _ws(9002, "ws-b"),
            ]
        ),
    )
    cli_env.nodes_by_project[9001] = _two_nodes()[:1]
    cli_env.nodes_by_project[9002] = _two_nodes()[:1]
    assert run_cli("dataworks") == 0

    # 从配置中移除 9002 后重跑 9001。
    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        json.dumps([_ws(9001, "ws-a-renamed")]),
    )
    assert run_cli("dataworks") == 0

    workspaces_index = json.loads(
        (
            Path("source")
            / "dataworks"
            / "workspaces-index.json"
        ).read_text(encoding="utf-8")
    )
    entries = {
        e["id"]: e
        for e in workspaces_index["workspaces"]
    }

    # 9001 被 upsert 更新。
    assert entries[9001]["name"] == "ws-a-renamed"
    assert "generated_at" in entries[9001]

    # 9002 条目原样保留。
    assert entries[9002]["name"] == "ws-b"
    assert entries[9002]["status"] == "ok"

    # 9002 目录未被删除。
    assert (
        Path("source")
        / "dataworks"
        / "workspaces"
        / "9002"
        / "nodes"
        / "101.json"
    ).exists()

"""Ticket 03：容错采集与失败可观测。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import make_node, make_workspace, workspaces_env


def test_workspace_failure_continues_and_writes_manifest(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """单 Workspace 失败：其余照采、status=failed、manifest 仍生成、exit 1。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a", "mc_a"),
            make_workspace(9002, "ws-b", "mc_b"),
            make_workspace(9003, "ws-c", "mc_c"),
        ),
    )

    cli_env.failing_projects.add(9002)
    cli_env.nodes_by_project[9001] = [
        make_node(
            "101",
            "SELECT 1;",
            name="a_etl",
        ),
    ]
    cli_env.nodes_by_project[9003] = [
        make_node(
            "301",
            "SELECT 3;",
            name="c_etl",
        ),
    ]

    code = run_cli("export")

    # 存在失败 → 非零退出。
    assert code == 1

    dataworks_dir = Path("source") / "dataworks"

    # 其余 Workspace 照常落盘。
    assert (
        dataworks_dir
        / "workspaces"
        / "9001"
        / "nodes"
        / "101.json"
    ).exists()
    assert (
        dataworks_dir
        / "workspaces"
        / "9003"
        / "nodes"
        / "301.json"
    ).exists()

    # 注册表记录失败状态。
    workspaces_index = json.loads(
        (dataworks_dir / "workspaces-index.json").read_text(
            encoding="utf-8"
        )
    )
    entries = {
        e["id"]: e
        for e in workspaces_index["workspaces"]
    }
    assert entries[9001]["status"] == "ok"
    assert entries[9003]["status"] == "ok"
    assert entries[9002]["status"] == "failed"
    assert entries[9002]["error"]

    # DataWorks 部分失败时 manifest 仍然生成（D-8 修复点）。
    manifest = json.loads(
        (Path("source") / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    manifest_ids = {
        w["id"]
        for w in manifest["sources"]["dataworks"]["workspaces"]
    }
    assert manifest_ids == {9001, 9002, 9003}

    # MaxCompute 照常采集。
    tables = json.loads(
        (
            Path("source")
            / "maxcompute"
            / "metadata"
            / "tables-index.json"
        ).read_text(encoding="utf-8")
    )
    assert tables["count"] == 1


def test_node_failure_recorded_as_failed_nodes(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """节点详情失败：记入 failed_nodes、其余节点照采、exit 1。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a", "mc_a"),
        ),
    )

    cli_env.nodes_by_project[9001] = [
        make_node(
            "101",
            "SELECT 1;",
            name="ok_node",
        ),
        make_node(
            "102",
            "SELECT 2;",
            name="bad_node",
        ),
    ]
    cli_env.failing_node_ids[9001] = {"102"}

    code = run_cli("export")

    assert code == 1

    base = (
        Path("source")
        / "dataworks"
        / "workspaces"
        / "9001"
    )

    index = json.loads(
        (base / "nodes-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert index["count"] == 1
    assert index["nodes"][0]["node_id"] == "101"
    assert index["failed_nodes"] == [
        {"node_id": "102"}
    ]

    # 成功节点仍落盘。
    assert (base / "nodes" / "101.json").exists()

    # 注册表反映节点级失败。
    workspaces_index = json.loads(
        (
            Path("source")
            / "dataworks"
            / "workspaces-index.json"
        ).read_text(encoding="utf-8")
    )
    entry = workspaces_index["workspaces"][0]
    assert entry["status"] == "ok"
    assert entry["node_count"] == 1
    assert entry["failed_node_count"] == 1

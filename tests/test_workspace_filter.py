"""Ticket 05：`--workspace` 单 Workspace 精准采集。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _three_workspaces() -> str:
    return json.dumps(
        [
            {
                "id": 9001,
                "name": "ws-a",
                "maxcompute_project": "mc_a",
            },
            {
                "id": 9002,
                "name": "ws-b",
                "maxcompute_project": "mc_b",
            },
            {
                "id": 9003,
                "name": "ws-c",
                "maxcompute_project": "mc_c",
            },
        ]
    )


def _node(node_id: str, script: str) -> dict[str, Any]:
    return {
        "NodeId": node_id,
        "NodeName": f"node_{node_id}",
        "NodeType": "Shell",
        "Script": script,
    }


def test_workspace_filter_partial_upsert(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """只重跑选中 Workspace：其余 index 条目与目录字节不变。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        _three_workspaces(),
    )
    for ws_id in (9001, 9002, 9003):
        cli_env.nodes_by_project[ws_id] = [
            _node(f"{ws_id}1", f"SELECT {ws_id};")
        ]

    # 基线：全量采集。
    assert run_cli("dataworks") == 0

    dataworks_dir = Path("source") / "dataworks"
    index_b_before = (
        dataworks_dir
        / "workspaces"
        / "9002"
        / "nodes-index.json"
    ).read_bytes()
    index_c_before = (
        dataworks_dir
        / "workspaces"
        / "9003"
        / "nodes-index.json"
    ).read_bytes()
    registry = json.loads(
        (dataworks_dir / "workspaces-index.json").read_text(
            encoding="utf-8"
        )
    )
    registry_b_before = next(
        e
        for e in registry["workspaces"]
        if e["id"] == 9002
    )

    # 仅重跑 9001。
    cli_env.nodes_by_project[9001] = [
        _node("90011", "SELECT 'updated';"),
        _node("90012", "SELECT 'new';"),
    ]
    assert (
        run_cli("dataworks", "--workspace", "9001") == 0
    )

    # 未选中的 Workspace 目录字节不变。
    assert (
        dataworks_dir
        / "workspaces"
        / "9002"
        / "nodes-index.json"
    ).read_bytes() == index_b_before
    assert (
        dataworks_dir
        / "workspaces"
        / "9003"
        / "nodes-index.json"
    ).read_bytes() == index_c_before

    # 选中的 Workspace 已更新。
    index_a = json.loads(
        (
            dataworks_dir
            / "workspaces"
            / "9001"
            / "nodes-index.json"
        ).read_text(encoding="utf-8")
    )
    assert index_a["count"] == 2

    # 注册表：9001 更新，9002/9003 原样。
    registry_after = json.loads(
        (dataworks_dir / "workspaces-index.json").read_text(
            encoding="utf-8"
        )
    )
    entries = {
        e["id"]: e
        for e in registry_after["workspaces"]
    }
    assert entries[9001]["node_count"] == 2
    assert entries[9002] == registry_b_before


def test_workspace_filter_unconfigured_id(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """未配置的 id → 报错退出，且不发起任何采集。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        _three_workspaces(),
    )

    code = run_cli("dataworks", "--workspace", "999")

    assert code != 0
    assert not Path("source").exists()


def test_export_with_workspace_filter_skips_manifest(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """export --workspace 过滤采集：不写 manifest（仅全量 export 写入）。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        _three_workspaces(),
    )
    cli_env.nodes_by_project[9002] = [
        _node("90021", "SELECT 2;")
    ]

    assert (
        run_cli("export", "--workspace", "9002") == 0
    )

    # 选中 Workspace 已落盘。
    assert (
        Path("source")
        / "dataworks"
        / "workspaces"
        / "9002"
        / "nodes"
        / "90021.json"
    ).exists()

    # 过滤运行不写 manifest。
    assert not (
        Path("source") / "manifest.json"
    ).exists()

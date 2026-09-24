"""Ticket 02：多 Workspace 全量采集——新布局与身份字段基线。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import make_node, make_workspace, workspaces_env


def test_export_dual_workspace_snapshot(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """一次 export 产出两个 Workspace 的独立 Snapshot。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a", "mc_a"),
            make_workspace(9002, "ws-b", "mc_b"),
        ),
    )

    cli_env.nodes_by_project[9001] = [
        make_node(
            "101",
            "INSERT OVERWRITE TABLE a SELECT 1;",
            name="daily_etl",
        ),
    ]
    cli_env.nodes_by_project[9002] = [
        make_node(
            "201",
            "print('b')",
            name="dim_load",
            node_type="Python",
        ),
        make_node(
            "202",
            "SELECT 2;",
            name="ads_build",
        ),
    ]

    code = run_cli("export")

    assert code == 0

    dataworks_dir = Path("source") / "dataworks"

    # 目录按稳定 id 组织（ADR-0001）。
    ws_a = dataworks_dir / "workspaces" / "9001"
    ws_b = dataworks_dir / "workspaces" / "9002"
    assert (ws_a / "nodes" / "101.json").exists()
    assert (ws_b / "nodes" / "201.json").exists()
    assert (ws_b / "nodes" / "202.json").exists()
    assert (
        ws_a / "sql" / "101_1.sql"
    ).read_text(encoding="utf-8").strip() == (
        "INSERT OVERWRITE TABLE a SELECT 1;"
    )

    # nodes-index：顶层 workspace 元数据 + 条目级 workspace_id。
    index_a = json.loads(
        (ws_a / "nodes-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert index_a["workspace"]["id"] == 9001
    assert index_a["workspace"]["name"] == "ws-a"
    assert index_a["count"] == 1
    assert index_a["nodes"][0]["workspace_id"] == 9001
    assert index_a["nodes"][0]["node_id"] == "101"

    index_b = json.loads(
        (ws_b / "nodes-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert index_b["count"] == 2
    assert {
        n["workspace_id"] for n in index_b["nodes"]
    } == {9002}

    # lineage 记录级 workspace_id。
    lineage_b = (
        ws_b / "lineage" / "task-lineage.jsonl"
    ).read_text(encoding="utf-8")
    records = [
        json.loads(line)
        for line in lineage_b.strip().splitlines()
    ]
    assert len(records) == 2
    assert {r["workspace_id"] for r in records} == {9002}

    # 根级注册表。
    workspaces_index = json.loads(
        (dataworks_dir / "workspaces-index.json").read_text(
            encoding="utf-8"
        )
    )
    entries = {
        e["id"]: e
        for e in workspaces_index["workspaces"]
    }
    assert set(entries) == {9001, 9002}
    assert entries[9001]["name"] == "ws-a"
    assert entries[9001]["maxcompute_project"] == "mc_a"
    assert entries[9001]["status"] == "ok"
    assert entries[9001]["node_count"] == 1
    assert entries[9002]["node_count"] == 2
    assert "generated_at" in entries[9001]

    # manifest 列出全部 Workspace。
    manifest = json.loads(
        (Path("source") / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    manifest_ids = {
        w["id"]
        for w in manifest["sources"]["dataworks"][
            "workspaces"
        ]
    }
    assert manifest_ids == {9001, 9002}

    # MaxCompute 布局不受影响。
    tables = json.loads(
        (
            Path("source")
            / "maxcompute"
            / "metadata"
            / "tables-index.json"
        ).read_text(encoding="utf-8")
    )
    assert tables["count"] == 1


def test_export_single_entry_workspace_list(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """长度为 1 的数组走同一路径，产出相同布局。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        workspaces_env(
            make_workspace(7, "only"),
        ),
    )
    cli_env.nodes_by_project[7] = [
        make_node(
            "701",
            "SELECT 7;",
            name="only_node",
        ),
    ]

    assert run_cli("export") == 0

    index = json.loads(
        (
            Path("source")
            / "dataworks"
            / "workspaces"
            / "7"
            / "nodes-index.json"
        ).read_text(encoding="utf-8")
    )
    assert index["count"] == 1
    assert index["nodes"][0]["workspace_id"] == 7

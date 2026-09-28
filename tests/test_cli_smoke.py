"""Ticket 02：多 Workspace 全量采集——新布局与身份字段基线。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import make_file, make_workspace, workspaces_env


def test_export_dual_workspace_snapshot(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """一次 export 产出两个 Workspace 的独立 Snapshot。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a", "mc_a"),
            make_workspace(9002, "ws-b", "mc_b"),
        ),
    )

    cli_env.files_by_project[9001] = [
        make_file(
            "101",
            "daily_etl",
            content="INSERT OVERWRITE TABLE a SELECT 1;",
        ),
    ]
    cli_env.files_by_project[9002] = [
        make_file(
            "201",
            "dim_load",
            file_type=1221,
            content="print('b')",
        ),
        make_file(
            "202",
            "ads_build",
        ),
    ]

    code = run_cli("export")

    assert code == 0

    dataworks_dir = Path("source") / "dataworks"

    # 目录按稳定 id 组织（ADR-0001）。
    ws_a = dataworks_dir / "workspaces" / "9001"
    ws_b = dataworks_dir / "workspaces" / "9002"
    assert (ws_a / "files" / "101__daily_etl.json").exists()
    assert (ws_b / "files" / "201__dim_load.json").exists()
    assert (ws_b / "files" / "202__ads_build.json").exists()

    # Content 扩展名由 ListFiles.FileType 决定：
    # 10 -> .sql，1221 -> .py。
    assert (ws_a / "content" / "101__daily_etl.sql").read_text(
        encoding="utf-8"
    ).strip() == "INSERT OVERWRITE TABLE a SELECT 1;"
    assert (ws_b / "content" / "201__dim_load.py").exists()

    # files-index：顶层 workspace 元数据 + 条目级 workspace_id。
    index_a = json.loads((ws_a / "files-index.json").read_text(encoding="utf-8"))
    assert index_a["workspace"]["id"] == 9001
    assert index_a["workspace"]["name"] == "ws-a"
    assert index_a["count"] == 1
    assert index_a["failed_files"] == []
    assert index_a["files"][0]["workspace_id"] == 9001
    assert index_a["files"][0]["file_id"] == "101"
    assert index_a["files"][0]["file_name"] == "daily_etl"
    assert index_a["files"][0]["file_type_name"] == "ODPS SQL"

    index_b = json.loads((ws_b / "files-index.json").read_text(encoding="utf-8"))
    assert index_b["count"] == 2
    assert {f["workspace_id"] for f in index_b["files"]} == {9002}

    # 根级注册表。
    workspaces_index = json.loads(
        (dataworks_dir / "workspaces-index.json").read_text(encoding="utf-8")
    )
    entries = {e["id"]: e for e in workspaces_index["workspaces"]}
    assert set(entries) == {9001, 9002}
    assert entries[9001]["name"] == "ws-a"
    assert entries[9001]["status"] == "ok"
    assert entries[9001]["file_count"] == 1
    assert entries[9001]["failed_file_count"] == 0
    assert entries[9002]["file_count"] == 2
    assert "generated_at" in entries[9001]

    # manifest 列出全部 Workspace。
    manifest = json.loads((Path("source") / "manifest.json").read_text(encoding="utf-8"))
    manifest_ids = {w["id"] for w in manifest["sources"]["dataworks"]["workspaces"]}
    assert manifest_ids == {9001, 9002}

    # MaxCompute：每个 Workspace 独立的 tables-index。
    tables_a = json.loads(
        (Path("source") / "maxcompute" / "workspaces" / "9001" / "tables-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert tables_a["count"] == 1
    assert tables_a["project"] == "ws-a"


def test_export_single_entry_workspace_list(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """长度为 1 的数组走同一路径，产出相同布局。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(
            make_workspace(7, "only"),
        ),
    )
    cli_env.files_by_project[7] = [
        make_file(
            "701",
            "only_file",
        ),
    ]

    assert run_cli("export") == 0

    index = json.loads(
        (Path("source") / "dataworks" / "workspaces" / "7" / "files-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert index["count"] == 1
    assert index["files"][0]["workspace_id"] == 7

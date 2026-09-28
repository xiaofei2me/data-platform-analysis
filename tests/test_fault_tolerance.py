"""Ticket 03：容错采集与失败可观测。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import make_file, make_workspace, workspaces_env


def test_workspace_failure_continues_and_writes_manifest(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """单 Workspace 失败：其余照采、status=failed、manifest 仍生成、exit 1。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a", "mc_a"),
            make_workspace(9002, "ws-b", "mc_b"),
            make_workspace(9003, "ws-c", "mc_c"),
        ),
    )

    cli_env.failing_projects.add(9002)
    cli_env.files_by_project[9001] = [
        make_file(
            "101",
            "a_etl",
        ),
    ]
    cli_env.files_by_project[9003] = [
        make_file(
            "301",
            "c_etl",
        ),
    ]

    code = run_cli("export")

    # 存在失败 → 非零退出。
    assert code == 1

    dataworks_dir = Path("source") / "dataworks"

    # 其余 Workspace 照常落盘。
    assert (dataworks_dir / "workspaces" / "9001" / "files" / "101__a_etl.json").exists()
    assert (dataworks_dir / "workspaces" / "9003" / "files" / "301__c_etl.json").exists()

    # 注册表记录失败状态。
    workspaces_index = json.loads(
        (dataworks_dir / "workspaces-index.json").read_text(encoding="utf-8")
    )
    entries = {e["id"]: e for e in workspaces_index["workspaces"]}
    assert entries[9001]["status"] == "ok"
    assert entries[9003]["status"] == "ok"
    assert entries[9002]["status"] == "failed"
    assert entries[9002]["error"]

    # DataWorks 部分失败时 manifest 仍然生成（D-8 修复点）。
    manifest = json.loads((Path("source") / "manifest.json").read_text(encoding="utf-8"))
    manifest_ids = {w["id"] for w in manifest["sources"]["dataworks"]["workspaces"]}
    assert manifest_ids == {9001, 9002, 9003}

    # MaxCompute 照常采集。
    tables = json.loads(
        (Path("source") / "maxcompute" / "workspaces" / "9001" / "tables-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert tables["count"] == 1


def test_file_failure_recorded_as_failed_files(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """文件详情失败：记入 failed_files、其余文件照采、exit 1。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a", "mc_a"),
        ),
    )

    cli_env.files_by_project[9001] = [
        make_file(
            "101",
            "ok_file",
        ),
        make_file(
            "102",
            "bad_file",
        ),
    ]
    cli_env.failing_file_ids[9001] = {"102"}

    code = run_cli("dataworks")

    assert code == 1

    base = Path("source") / "dataworks" / "workspaces" / "9001"

    index = json.loads((base / "files-index.json").read_text(encoding="utf-8"))
    assert index["count"] == 1
    assert index["files"][0]["file_id"] == "101"
    assert len(index["failed_files"]) == 1
    assert index["failed_files"][0]["file_id"] == "102"
    assert index["failed_files"][0]["file_name"] == "bad_file"
    assert index["failed_files"][0]["error"]

    # 成功文件仍落盘。
    assert (base / "files" / "101__ok_file.json").exists()
    assert not (base / "files" / "102__bad_file.json").exists()

    # 注册表反映文件级失败。
    workspaces_index = json.loads(
        (Path("source") / "dataworks" / "workspaces-index.json").read_text(encoding="utf-8")
    )
    entry = workspaces_index["workspaces"][0]
    assert entry["status"] == "failed"
    assert entry["file_count"] == 1
    assert entry["failed_file_count"] == 1

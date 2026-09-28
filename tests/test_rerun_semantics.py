"""Ticket 04：重复执行语义——权威清理与注册表 upsert。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import make_file, make_workspace, workspaces_env


def _two_files() -> list[dict[str, Any]]:
    return [
        make_file(
            "101",
            "keep_me",
        ),
        make_file(
            "102",
            "ghost_me",
        ),
    ]


def test_ghost_file_cleaned_on_rerun(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """上游删除的文件在重采后不再残留（权威集合清理）。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(make_workspace(9001, "ws-a")),
    )

    cli_env.files_by_project[9001] = _two_files()
    assert run_cli("dataworks") == 0

    base = Path("source") / "dataworks" / "workspaces" / "9001"
    assert (base / "files" / "101__keep_me.json").exists()
    assert (base / "files" / "102__ghost_me.json").exists()
    assert (base / "content" / "102__ghost_me.sql").exists()

    # 上游删除 102 后重采。
    cli_env.files_by_project[9001] = _two_files()[:1]
    assert run_cli("dataworks") == 0

    assert (base / "files" / "101__keep_me.json").exists()
    assert not (base / "files" / "102__ghost_me.json").exists()
    assert not (base / "content" / "102__ghost_me.sql").exists()


def test_failed_file_old_snapshot_kept(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """本次 GetFile 失败的文件保留上一次成功采集的 Snapshot。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(make_workspace(9001, "ws-a")),
    )

    cli_env.files_by_project[9001] = _two_files()
    assert run_cli("dataworks") == 0

    base = Path("source") / "dataworks" / "workspaces" / "9001"

    # 102 仍在权威列表中，但详情获取失败。
    cli_env.failing_file_ids[9001] = {"102"}
    assert run_cli("dataworks") == 1

    # 旧 Snapshot 保留。
    assert (base / "files" / "102__ghost_me.json").exists()
    assert (base / "content" / "102__ghost_me.sql").exists()

    index = json.loads((base / "files-index.json").read_text(encoding="utf-8"))
    assert [f["file_id"] for f in index["files"]] == ["101"]
    assert [f["file_id"] for f in index["failed_files"]] == ["102"]


def test_failed_workspace_no_cleanup(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """采集失败的 Workspace 不执行清理，保留旧 Snapshot。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a"),
            make_workspace(9002, "ws-b"),
        ),
    )

    cli_env.files_by_project[9001] = _two_files()[:1]
    cli_env.files_by_project[9002] = _two_files()
    assert run_cli("dataworks") == 0

    ws_b = Path("source") / "dataworks" / "workspaces" / "9002"
    assert (ws_b / "files" / "101__keep_me.json").exists()
    assert (ws_b / "files" / "102__ghost_me.json").exists()

    # 9002 整体失败。
    cli_env.failing_projects.add(9002)
    assert run_cli("dataworks") == 1

    # 旧 Snapshot 全部保留。
    assert (ws_b / "files" / "101__keep_me.json").exists()
    assert (ws_b / "files" / "102__ghost_me.json").exists()

    workspaces_index = json.loads(
        (Path("source") / "dataworks" / "workspaces-index.json").read_text(encoding="utf-8")
    )
    entries = {e["id"]: e for e in workspaces_index["workspaces"]}
    assert entries[9002]["status"] == "failed"


def test_workspaces_index_upsert_preserves_unlisted_entries(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """从配置移除的 Workspace：index 条目与目录均不自动删除。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a"),
            make_workspace(9002, "ws-b"),
        ),
    )
    cli_env.files_by_project[9001] = _two_files()[:1]
    cli_env.files_by_project[9002] = _two_files()[:1]
    assert run_cli("dataworks") == 0

    # 从配置中移除 9002 后重跑 9001。
    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(make_workspace(9001, "ws-a-renamed")),
    )
    assert run_cli("dataworks") == 0

    workspaces_index = json.loads(
        (Path("source") / "dataworks" / "workspaces-index.json").read_text(encoding="utf-8")
    )
    entries = {e["id"]: e for e in workspaces_index["workspaces"]}

    # 9001 被 upsert 更新。
    assert entries[9001]["name"] == "ws-a-renamed"
    assert entries[9001]["file_count"] == 1
    assert "generated_at" in entries[9001]

    # 9002 条目原样保留。
    assert entries[9002]["name"] == "ws-b"
    assert entries[9002]["status"] == "ok"

    # 9002 目录未被删除。
    assert (
        Path("source") / "dataworks" / "workspaces" / "9002" / "files" / "101__keep_me.json"
    ).exists()

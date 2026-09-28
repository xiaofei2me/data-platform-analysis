"""ListFiles 分页：多页合并、服务端分页差异与异常结构防护。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from helpers import make_files, make_workspace, workspaces_env

from data_platform_analysis import config as config_module
from data_platform_analysis.dataworks import DataWorksClient


def test_list_files_merges_multiple_pages(
    cli_env: Any,
    monkeypatch: Any,
) -> None:
    """多页结果按顺序合并为完整 File 集合。"""

    monkeypatch.setenv("DATAWORKS_PAGE_SIZE", "2")
    config_module.reset_settings()

    cli_env.files_by_project[9001] = make_files(1000, 5)

    files = DataWorksClient().list_files(9001)

    assert [file["FileId"] for file in files] == [
        "1000",
        "1001",
        "1002",
        "1003",
        "1004",
    ]
    assert [call["page_number"] for call in cli_env.list_files_calls] == [1, 2, 3]


def test_list_files_uses_total_count_when_server_caps_page_size(
    cli_env: Any,
    monkeypatch: Any,
) -> None:
    """服务端每页上限小于请求 page_size 时，以 TotalCount 为准，不提前截断。"""

    monkeypatch.setenv("DATAWORKS_PAGE_SIZE", "100")
    config_module.reset_settings()

    cli_env.page_size_cap = 2
    cli_env.files_by_project[9001] = make_files(1000, 5)

    files = DataWorksClient().list_files(9001)

    # 不能因为「本页不满 page_size」就当成最后一页。
    assert len(files) == 5
    assert [call["page_number"] for call in cli_env.list_files_calls] == [1, 2, 3]


def test_list_files_malformed_response_raises(
    cli_env: Any,
) -> None:
    """服务端声明有数据却返回空页：视为采集失败，而不是权威空集合。"""

    cli_env.malformed_projects.add(9001)

    with pytest.raises(RuntimeError):
        DataWorksClient().list_files(9001)


def test_malformed_list_files_fails_workspace_and_keeps_snapshot(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """异常结构 → Workspace 失败、旧 Snapshot 保留、不 Cleanup、exit 1。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(make_workspace(9001, "ws-a")),
    )
    cli_env.files_by_project[9001] = make_files(1000, 2)

    assert run_cli("dataworks") == 0

    base = Path("source") / "dataworks" / "workspaces" / "9001"
    before = sorted(path.name for path in (base / "files").glob("*.json"))
    assert len(before) == 2

    # 服务端开始返回异常结构。
    cli_env.malformed_projects.add(9001)
    assert run_cli("dataworks") == 1

    # 旧 Snapshot 与旧 index 全部保留。
    assert sorted(path.name for path in (base / "files").glob("*.json")) == before
    index = json.loads((base / "files-index.json").read_text(encoding="utf-8"))
    assert index["count"] == 2

    # 注册表标记该 Workspace 失败。
    registry = json.loads(
        (Path("source") / "dataworks" / "workspaces-index.json").read_text(encoding="utf-8")
    )
    entries = {entry["id"]: entry for entry in registry["workspaces"]}
    assert entries[9001]["status"] == "failed"
    assert entries[9001]["error"]

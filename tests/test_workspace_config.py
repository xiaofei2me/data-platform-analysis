"""Ticket 02：多 Workspace 配置——解析、fail-fast 与配置视图。"""

from __future__ import annotations

from typing import Any

from helpers import make_workspace, workspaces_env


def test_invalid_workspaces_json_fails_fast(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """DATAWORKS_WORKSPACES 不是合法 JSON → 启动即失败。"""

    # 旧字段一并提供：确保旧实现能跑通（exit 0），
    # 红灯必须来自新校验而非旧必填项缺失。
    monkeypatch.setenv("DATAWORKS_PROJECT_ID", "9001")
    monkeypatch.setenv("DATAWORKS_WORKSPACES", "{not-json")

    assert run_cli("config") != 0


def test_duplicate_workspace_id_fails_fast(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """重复 workspace id → 启动即失败。"""

    monkeypatch.setenv("DATAWORKS_PROJECT_ID", "9001")
    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        workspaces_env(
            make_workspace(1, "ws-a"),
            make_workspace(1, "ws-b"),
        ),
    )

    assert run_cli("config") != 0


def test_duplicate_workspace_name_fails_fast(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """重复 workspace name → 启动即失败。"""

    monkeypatch.setenv("DATAWORKS_PROJECT_ID", "9001")
    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        workspaces_env(
            make_workspace(1, "same"),
            make_workspace(2, "same"),
        ),
    )

    assert run_cli("config") != 0


def test_config_subcommand_shows_workspaces(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    """config 子命令展示全部 Workspace 且以 0 退出。"""

    monkeypatch.setenv(
        "DATAWORKS_WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a"),
            make_workspace(9002, "ws-b"),
        ),
    )

    assert run_cli("config") == 0

    output = capsys.readouterr().out
    assert "DATAWORKS_WORKSPACES" in output
    assert "9001 (ws-a)" in output
    assert "9002 (ws-b)" in output

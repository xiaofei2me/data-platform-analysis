"""Ticket 02：多 Workspace 配置——解析、fail-fast 与配置视图。"""

from __future__ import annotations

from typing import Any

from helpers import make_workspace, workspaces_env


def test_invalid_workspaces_json_fails_fast(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """WORKSPACES 不是合法 JSON → 启动即失败。"""

    monkeypatch.setenv("WORKSPACES", "{not-json")

    assert run_cli("config") != 0


def test_duplicate_workspace_id_fails_fast(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """重复 workspace id → 启动即失败。"""

    monkeypatch.setenv(
        "WORKSPACES",
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

    monkeypatch.setenv(
        "WORKSPACES",
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
        "WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a"),
            make_workspace(9002, "ws-b"),
        ),
    )

    assert run_cli("config") == 0

    output = capsys.readouterr().out
    assert "WORKSPACES" in output
    # Rich 表格可能折行，这里只断言不会被拆开的原子 token。
    assert "9001" in output
    assert "ws-a" in output
    assert "9002" in output
    assert "ws-b" in output

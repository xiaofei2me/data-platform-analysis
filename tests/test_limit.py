"""采集限制模式 `--limit`——CLI 解析、分页截断与 Cleanup 禁止。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from helpers import make_file, make_files, make_workspace, workspaces_env

from data_platform_analysis import config as config_module
from data_platform_analysis.cli import build_parser
from data_platform_analysis.dataworks import DataWorksClient

# ============================================================
# CLI 参数解析
# ============================================================


def test_limit_is_parsed_for_each_subcommand() -> None:
    """dataworks / maxcompute / export 都接受 --limit。"""

    parser = build_parser()

    assert parser.parse_args(["dataworks", "--limit", "5"]).limit == 5
    assert parser.parse_args(["maxcompute", "--limit", "3"]).limit == 3
    assert parser.parse_args(["export", "--limit", "1"]).limit == 1


def test_limit_defaults_to_none() -> None:
    """不传 --limit 时保持全量行为（limit=None）。"""

    parser = build_parser()

    assert parser.parse_args(["dataworks"]).limit is None
    assert parser.parse_args(["maxcompute"]).limit is None
    assert parser.parse_args(["export"]).limit is None


def test_limit_rejects_zero(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """--limit 0 直接失败。"""

    assert run_cli("dataworks", "--limit", "0") != 0
    assert run_cli("export", "--limit", "0") != 0


def test_limit_rejects_negative(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """--limit 负数直接失败。"""

    assert run_cli("dataworks", "--limit", "-1") != 0
    assert run_cli("maxcompute", "--limit", "-3") != 0


def test_limit_rejects_non_integer(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """--limit 非整数直接失败。"""

    assert run_cli("export", "--limit", "abc") != 0


# ============================================================
# DataWorks list_files(limit=)
# ============================================================


def test_list_files_limit_stops_paging(
    cli_env: Any,
    monkeypatch: Any,
) -> None:
    """limit=3 最多返回 3 个，并在达到限制后停止分页。"""

    monkeypatch.setenv("DATAWORKS_PAGE_SIZE", "2")
    config_module.reset_settings()

    cli_env.files_by_project[9001] = make_files(1000, 10)

    files = DataWorksClient().list_files(9001, limit=3)

    assert len(files) == 3
    assert [file["FileId"] for file in files] == ["1000", "1001", "1002"]

    # 分页在第 2 页就停止：
    # 第 1 页 2 个 + 第 2 页取 1 个 = 3，不再请求第 3 页。
    calls = cli_env.list_files_calls
    assert [call["page_number"] for call in calls] == [1, 2]


def test_list_files_limit_is_workspace_total_across_use_types(
    cli_env: Any,
    monkeypatch: Any,
) -> None:
    """多 UseType 下 limit=3 是整个 Workspace 总共 3 个。"""

    monkeypatch.setenv("DATAWORKS_USE_TYPES", "NORMAL,MANUAL")
    config_module.reset_settings()

    cli_env.files_by_project[9001] = [
        make_file("n1", "normal_1", use_type="NORMAL"),
        make_file("n2", "normal_2", use_type="NORMAL"),
        make_file("m1", "manual_1", use_type="MANUAL"),
        make_file("m2", "manual_2", use_type="MANUAL"),
        make_file("m3", "manual_3", use_type="MANUAL"),
    ]

    files = DataWorksClient().list_files(9001, limit=3)

    # 不是每个 UseType 各 3 个（6 个），而是整个 Workspace 共 3 个。
    assert len(files) == 3
    assert [file["FileId"] for file in files] == ["n1", "n2", "m1"]

    # MANUAL 只查第 1 页就结束，不再继续分页。
    calls = cli_env.list_files_calls
    assert [call["use_type"] for call in calls] == ["NORMAL", "MANUAL"]
    assert [call["page_number"] for call in calls] == [1, 1]


def test_list_files_without_limit_returns_all(
    cli_env: Any,
) -> None:
    """不传 limit 时全量返回，分页行为不变。"""

    cli_env.files_by_project[9001] = make_files(1000, 5)

    files = DataWorksClient().list_files(9001)

    assert len(files) == 5


# ============================================================
# DataWorks limit 模式禁止 Cleanup
# ============================================================


def test_dataworks_limit_mode_skips_cleanup(
    cli_env: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """limit 模式返回部分集合，绝对不能据此删除旧 Snapshot。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(make_workspace(9001, "ws-a")),
    )
    cli_env.files_by_project[9001] = make_files(1000, 4)

    assert run_cli("dataworks") == 0

    base = Path("source") / "dataworks" / "workspaces" / "9001"

    full_raw = sorted(p.name for p in (base / "files").glob("*.json"))
    full_content = sorted(p.name for p in (base / "content").glob("*"))
    assert len(full_raw) == 4
    assert len(full_content) == 4

    # 限制模式重采。
    assert run_cli("dataworks", "--limit", "2") == 0

    # 旧 Snapshot 一个都不能少。
    assert sorted(p.name for p in (base / "files").glob("*.json")) == full_raw
    assert sorted(p.name for p in (base / "content").glob("*")) == full_content

    # index 反映本次受限采集。
    index = json.loads((base / "files-index.json").read_text(encoding="utf-8"))
    assert index["count"] == 2


# ============================================================
# MaxCompute limit
# ============================================================


def test_maxcompute_limit_calls_get_table_once_per_table(
    cli_env: Any,
    fake_odps: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """limit=3 只执行 3 次 GetTable。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(make_workspace(9001, "ws-a")),
    )
    fake_odps.set_table_names("t1", "t2", "t3", "t4", "t5")

    assert run_cli("maxcompute", "--limit", "3") == 0

    assert fake_odps.get_table_calls == ["t1", "t2", "t3"]

    index = json.loads(
        (Path("source") / "maxcompute" / "workspaces" / "9001" / "tables-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert index["count"] == 3


def test_maxcompute_limit_mode_skips_cleanup(
    cli_env: Any,
    fake_odps: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """limit 模式禁止 MaxCompute Snapshot Cleanup。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(make_workspace(9001, "ws-a")),
    )
    fake_odps.set_table_names("t1", "t2", "t3", "t4", "t5")

    assert run_cli("maxcompute") == 0

    tables_dir = Path("source") / "maxcompute" / "workspaces" / "9001" / "tables"
    full_snapshots = sorted(p.name for p in tables_dir.glob("*.json"))
    assert len(full_snapshots) == 5

    get_table_after_full = len(fake_odps.get_table_calls)

    # 限制模式重采。
    assert run_cli("maxcompute", "--limit", "2") == 0

    # 旧 Snapshot 一个都不能少。
    assert sorted(p.name for p in tables_dir.glob("*.json")) == full_snapshots
    assert fake_odps.get_table_calls[get_table_after_full:] == ["t1", "t2"]

    index = json.loads(
        (Path("source") / "maxcompute" / "workspaces" / "9001" / "tables-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert index["count"] == 2


# ============================================================
# export_all 向下传递 limit
# ============================================================


def test_export_all_propagates_limit_per_workspace(
    cli_env: Any,
    fake_odps: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """多 Workspace 时，每个 Workspace 最多 N 个 File 和 N 个 Table。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a"),
            make_workspace(9002, "ws-b"),
        ),
    )
    cli_env.files_by_project[9001] = make_files(1000, 4)
    cli_env.files_by_project[9002] = make_files(2000, 4)
    fake_odps.set_table_names("t1", "t2", "t3", "t4")

    assert run_cli("export", "--limit", "2") == 0

    dataworks_dir = Path("source") / "dataworks"
    maxcompute_dir = Path("source") / "maxcompute"

    for ws_id in (9001, 9002):
        file_index = json.loads(
            (dataworks_dir / "workspaces" / str(ws_id) / "files-index.json").read_text(
                encoding="utf-8"
            )
        )
        assert file_index["count"] == 2

        table_index = json.loads(
            (maxcompute_dir / "workspaces" / str(ws_id) / "tables-index.json").read_text(
                encoding="utf-8"
            )
        )
        assert table_index["count"] == 2

    # GetTable 次数 = Workspace 数 × limit。
    assert len(fake_odps.get_table_calls) == 4


def test_export_all_without_limit_is_full(
    cli_env: Any,
    fake_odps: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """不传 limit 时现有全量行为不变。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(
            make_workspace(9001, "ws-a"),
            make_workspace(9002, "ws-b"),
        ),
    )
    cli_env.files_by_project[9001] = make_files(1000, 3)
    cli_env.files_by_project[9002] = make_files(2000, 3)
    fake_odps.set_table_names("t1", "t2", "t3")

    assert run_cli("export") == 0

    dataworks_dir = Path("source") / "dataworks"
    maxcompute_dir = Path("source") / "maxcompute"

    for ws_id in (9001, 9002):
        file_index = json.loads(
            (dataworks_dir / "workspaces" / str(ws_id) / "files-index.json").read_text(
                encoding="utf-8"
            )
        )
        assert file_index["count"] == 3

        table_index = json.loads(
            (maxcompute_dir / "workspaces" / str(ws_id) / "tables-index.json").read_text(
                encoding="utf-8"
            )
        )
        assert table_index["count"] == 3

    # 全量：每个 Workspace 的每张表都执行 GetTable。
    assert len(fake_odps.get_table_calls) == 6


# ============================================================
# limit 模式日志
# ============================================================


class _RecordingHandler(logging.Handler):
    """收集指定 Logger 的日志文本。"""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def test_limit_mode_logs_display_limit_and_cleanup_skip(
    cli_env: Any,
    fake_odps: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """limit 模式日志明确显示限制模式以及 Cleanup=SKIP。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(make_workspace(9001, "ws-a")),
    )
    cli_env.files_by_project[9001] = make_files(1000, 2)
    fake_odps.set_table_names("t1", "t2")

    handler = _RecordingHandler()
    export_logger = logging.getLogger("data_platform_analysis.export")
    export_logger.addHandler(handler)

    try:
        assert run_cli("export", "--limit", "1") == 0
    finally:
        export_logger.removeHandler(handler)

    messages = handler.messages

    assert any("采集限制模式" in message and "limit=1" in message for message in messages)
    assert any(
        "跳过 DataWorks Snapshot Cleanup" in message and "Cleanup=SKIP" in message
        for message in messages
    )
    assert any(
        "跳过 MaxCompute Snapshot Cleanup" in message and "Cleanup=SKIP" in message
        for message in messages
    )


def test_full_mode_does_not_log_cleanup_skip(
    cli_env: Any,
    fake_odps: Any,
    run_cli: Any,
    monkeypatch: Any,
) -> None:
    """非 limit 模式不输出 Cleanup=SKIP。"""

    monkeypatch.setenv(
        "WORKSPACES",
        workspaces_env(make_workspace(9001, "ws-a")),
    )
    cli_env.files_by_project[9001] = make_files(1000, 1)

    handler = _RecordingHandler()
    export_logger = logging.getLogger("data_platform_analysis.export")
    export_logger.addHandler(handler)

    try:
        assert run_cli("export") == 0
    finally:
        export_logger.removeHandler(handler)

    assert not any("Cleanup=SKIP" in message for message in handler.messages)

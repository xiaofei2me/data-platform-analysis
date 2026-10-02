"""M2.1 Warehouse Inventory 的黑盒测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import write_snapshot


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_inventory_lists(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """清单计数与身份字段都来自 Snapshot，不夹带层级判定。"""

    write_snapshot(
        Path("source"),
        workspaces=[
            {"id": 9001, "name": "ws_a"},
            {"id": 9002, "name": "ws_b"},
        ],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "daily_etl",
                "node_id": "7001",
                "content": "INSERT OVERWRITE TABLE ws_a.dwd_order SELECT 1;",
            },
            {
                "workspace_id": 9002,
                "file_id": "201",
                "file_name": "python_job",
                "content": "print('x')",
                "file_type": 22,
                "content_format": "PYTHON",
            },
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "comment": "订单明细",
                "columns": [
                    {"name": "id", "type": "BIGINT", "comment": "主键"},
                    {"name": "ds", "type": "STRING", "comment": "分区"},
                ],
                "partitions": ["ds"],
            },
            {
                "workspace_id": 9001,
                "table": "s_ods_log",
                "columns": [{"name": "id", "type": "BIGINT"}],
            },
            {
                "workspace_id": 9002,
                "table": "ads_report",
                "columns": [{"name": "id", "type": "BIGINT"}],
            },
        ],
    )

    assert run_cli("analyze") == 0

    workspaces = _read(Path("analysis/inventory/workspaces.json"))
    assert workspaces["count"] == 2

    by_id = {item["workspace_id"]: item for item in workspaces["workspaces"]}
    assert by_id[9001]["project"] == "ws_a"
    assert by_id[9001]["file_count"] == 1
    assert by_id[9001]["table_count"] == 2
    assert by_id[9002]["file_count"] == 1

    files = _read(Path("analysis/inventory/files.json"))
    assert files["count"] == 2

    file_by_id = {item["file_id"]: item for item in files["files"]}
    assert file_by_id["101"]["content_format"] == "SQL"
    assert file_by_id["101"]["node_id"] == 7001
    assert file_by_id["201"]["content_format"] == "PYTHON"

    tables = _read(Path("analysis/inventory/tables.json"))
    assert tables["count"] == 3

    table_by_name = {item["table"]: item for item in tables["tables"]}

    dwd_order = table_by_name["dwd_order"]
    assert dwd_order["table_key"] == "ws_a.dwd_order"
    # 层级判定属于 M2.2，M2.1 不再产出 layer_candidate 字段。
    assert "layer_candidate" not in dwd_order
    assert "layer_candidate_evidence" not in dwd_order
    assert "layer" not in dwd_order
    assert not any(key.startswith("confirmed_") for key in dwd_order)

    columns = _read(Path("analysis/inventory/columns.json"))
    assert columns["count"] == 4

    column_by_name = {(item["table"], item["column_name"]): item for item in columns["columns"]}
    assert column_by_name[("dwd_order", "id")]["is_partition"] is False
    assert column_by_name[("dwd_order", "ds")]["is_partition"] is True

    assert Path("analysis/inventory/summary.md").exists()
    assert Path("analysis/Summary.md").exists()


def test_inventory_is_deterministic(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """连续两次分析产出完全一致的 JSON。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "daily_etl",
                "content": "INSERT OVERWRITE TABLE ws_a.dwd_order SELECT 1;",
            }
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )

    assert run_cli("analyze") == 0

    first = Path("analysis/inventory/tables.json").read_text(encoding="utf-8")
    summary_first = Path("analysis/Summary.md").read_text(encoding="utf-8")

    assert run_cli("analyze") == 0

    assert Path("analysis/inventory/tables.json").read_text(encoding="utf-8") == first
    assert Path("analysis/Summary.md").read_text(encoding="utf-8") == summary_first

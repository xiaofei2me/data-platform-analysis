"""M2.4 Table Lineage 的黑盒测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import write_snapshot


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


RULES_TEXT = """\
version: "1.0"

workspace_layers:
  - workspace_id: 9001
    workspace_name: ws_a
    layer: CDM

  - workspace_id: 9002
    workspace_name: ws_b
    layer: ADS

sub_layers:
  CDM:
    DWD:
      prefixes:
        - "dwd_"
      suffixes: []
    DIM:
      prefixes:
        - "dim_"
      suffixes: []

matching:
  case_sensitive: false
"""


def test_lineage_dedup_cross_workspace_and_candidates(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """同一条边去重、跨 Workspace 识别、核心表按指标排序。"""

    rules_path = tmp_path / "config" / "layer-rules.yaml"
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text(RULES_TEXT, encoding="utf-8")
    monkeypatch.setenv("LAYER_RULES_PATH", str(rules_path))

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
                "file_name": "load_order_a",
                "node_id": "9101",
                "content": ("INSERT INTO ${ws_a}.dwd_order SELECT * FROM ${ws_a}.ods_order;"),
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "load_order_b",
                "node_id": "9102",
                "content": ("INSERT INTO ${ws_a}.dwd_order SELECT * FROM ${ws_a}.ods_order;"),
            },
            {
                "workspace_id": 9001,
                "file_id": "103",
                "file_name": "load_x",
                "node_id": "9103",
                "content": ("INSERT INTO ${ws_a}.dwd_x SELECT * FROM ws_b.dim_y;"),
            },
            {
                "workspace_id": 9001,
                "file_id": "104",
                "file_name": "load_z",
                "node_id": "9104",
                "content": ("INSERT INTO ${ws_a}.dwd_z SELECT * FROM other.unknown_table;"),
            },
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            },
            {
                "workspace_id": 9001,
                "table": "ods_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            },
            {
                "workspace_id": 9002,
                "table": "dim_y",
                "columns": [{"name": "id", "type": "BIGINT"}],
            },
        ],
    )

    assert run_cli("analyze") == 0

    lineage = _read(Path("analysis/lineage/table-lineage.json"))
    assert lineage["count"] == 3

    by_target = {item["target_key"]: item for item in lineage["edges"]}

    deduped = by_target["ws_a.dwd_order"]
    assert deduped["source_key"] == "ws_a.ods_order"
    assert [item["file_id"] for item in deduped["evidence"]] == ["101", "102"]
    # ws_a 是 CDM：target 命中 dwd_ 规则；source 无 ods_ 规则 → UNKNOWN。
    assert deduped["source_layer_candidate"] is None
    assert deduped["target_layer_candidate"] == "DWD"
    assert deduped["source_workspace_id"] == 9001
    assert deduped["target_workspace_id"] == 9001

    cross = by_target["ws_a.dwd_x"]
    assert cross["source_table"] == "ws_b.dim_y"
    assert cross["source_workspace_id"] == 9002
    assert cross["target_workspace_id"] == 9001
    # 层级来自 M2.2：workspace 事实优先于表名前缀（ws_b 是 ADS，表名是 dim_）。
    assert cross["source_layer_candidate"] == "ADS"
    # target 不在 Inventory 中，层级无从判定。
    assert cross["target_layer_candidate"] is None

    unknown = by_target["ws_a.dwd_z"]
    assert unknown["source_workspace_id"] is None
    assert unknown["target_workspace_id"] == 9001

    assert Path("analysis/lineage/summary.md").exists()

    candidates = _read(Path("analysis/lineage/core-table-candidates.json"))
    assert candidates["sort_by"] == "downstream_count_desc"

    downstream = [item["downstream_count"] for item in candidates["candidates"]]
    assert downstream == sorted(downstream, reverse=True)

    by_key = {item["table_key"]: item for item in candidates["candidates"]}
    assert by_key["ws_a.ods_order"]["downstream_count"] == 1
    assert by_key["ws_a.dwd_order"]["upstream_count"] == 1
    assert by_key["ws_a.dwd_order"]["layer_candidate"] == "DWD"
    assert by_key["ws_b.dim_y"]["layer_candidate"] == "ADS"
    assert by_key["other.unknown_table"]["in_inventory"] is False
    assert by_key["other.unknown_table"]["workspace_id"] is None

    summary = Path("analysis/Summary.md").read_text(encoding="utf-8")
    assert "跨 Workspace 血缘" in summary


def test_lineage_keeps_sql_spelling_and_raw_reference(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """SQL 原始写法保留在 source_table，规范标识写进 source_key。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "load",
                "node_id": "9101",
                "content": ("INSERT INTO TABLE ${ws_a}.dwd_order SELECT * FROM ${ws_a}.ods_order;"),
            }
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            },
            {
                "workspace_id": 9001,
                "table": "ods_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            },
        ],
    )

    assert run_cli("analyze") == 0

    edges = _read(Path("analysis/lineage/table-lineage.json"))["edges"]
    assert len(edges) == 1

    edge = edges[0]
    assert edge["source_table"] == "ws_a.ods_order"
    assert edge["source_key"] == "ws_a.ods_order"  # same as source_table after normalization
    assert edge["target_table"] == "ws_a.dwd_order"
    assert edge["target_key"] == "ws_a.dwd_order"

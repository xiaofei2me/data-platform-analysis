"""Analysis NodeId Eligibility（Analysis Scope Filter）的黑盒测试。

原则：

1. Collection / Snapshot 保留全部 File，NodeId 为空也不删除。
2. 只有 NodeId 有效的 File 才进入 SQL / Table Reference / Lineage Analysis。
3. NodeId 为空是 Analysis Scope Filter，不是 Analysis Error。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from helpers import source_tree_hash, write_snapshot


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_node_id_is_analyzed(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """NodeId 有效的 File 正常进入 SQL Analysis。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "committed_node",
                "node_id": 123,
                "content": "SELECT * FROM ws_a.ods_order;",
            }
        ],
    )

    assert run_cli("analyze") == 0

    statements = _read(Path("analysis/evidence/sql/statements.json"))
    assert statements["count"] > 0
    assert {item["node_id"] for item in statements["statements"]} == {123}

    references = _read(Path("analysis/evidence/sql/table-references.json"))
    assert {item["node_id"] for item in references["references"]} == {123}

    assert _read(Path("analysis/evidence/errors.json"))["count"] == 0


def test_node_id_none_is_excluded(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """node_id=None 的 File 不产生任何 SQL Evidence，也不产生 error。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "uncommitted_draft",
                "node_id": None,
                "content": "INSERT INTO ${ws_a}.dwd_order SELECT * FROM ${ws_a}.ods_order;",
            }
        ],
    )

    assert run_cli("analyze") == 0

    assert _read(Path("analysis/evidence/sql/statements.json"))["count"] == 0
    assert _read(Path("analysis/evidence/sql/table-references.json"))["count"] == 0
    assert _read(Path("analysis/evidence/sql/parse-errors.json"))["count"] == 0
    assert _read(Path("analysis/evidence/lineage/table-lineage.json"))["count"] == 0
    assert _read(Path("analysis/evidence/errors.json"))["count"] == 0


@pytest.mark.parametrize("node_id", ["", "   "])
def test_blank_node_id_is_excluded(
    cli_env: Any,
    run_cli: Any,
    node_id: str,
) -> None:
    """空字符串与纯空白 NodeId 都被排除，但仍保留在 Snapshot Inventory。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "blank_node",
                "node_id": node_id,
                "content": "INSERT INTO ${ws_a}.dwd_order SELECT * FROM ${ws_a}.ods_order;",
            }
        ],
    )

    assert run_cli("analyze") == 0

    files = _read(Path("analysis/inventory/files.json"))
    assert files["count"] == 1
    assert files["files"][0]["node_id"] is None

    assert _read(Path("analysis/evidence/sql/statements.json"))["count"] == 0
    assert _read(Path("analysis/evidence/sql/table-references.json"))["count"] == 0
    assert _read(Path("analysis/evidence/lineage/table-lineage.json"))["count"] == 0
    assert _read(Path("analysis/evidence/errors.json"))["count"] == 0


def test_snapshot_keeps_files_without_node_id(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Analysis 不修改 source/，NodeId 为空的 File 仍完整保留在 Snapshot。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "committed",
                "node_id": 123,
                "content": "SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "201",
                "file_name": "draft",
                "node_id": None,
                "content": "SELECT 2;",
            },
        ],
    )

    before = source_tree_hash(Path("source"))

    assert run_cli("analyze") == 0

    assert source_tree_hash(Path("source")) == before

    files = _read(Path("analysis/inventory/files.json"))
    assert files["count"] == 2
    assert {item["file_id"] for item in files["files"]} == {"101", "201"}

    assert Path("source/dataworks/workspaces/9001/files/101__committed.json").exists()
    assert Path("source/dataworks/workspaces/9001/content/101__committed.sql").exists()
    assert Path("source/dataworks/workspaces/9001/files/201__draft.json").exists()
    assert Path("source/dataworks/workspaces/9001/content/201__draft.sql").exists()


def test_excluded_file_produces_no_evidence(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """statements / references / lineage 都只来自 NodeId 有效的 File。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "committed",
                "node_id": 9001,
                "content": "INSERT INTO ${ws_a}.dwd_order SELECT * FROM ${ws_a}.ods_order;",
            },
            {
                "workspace_id": 9001,
                "file_id": "201",
                "file_name": "draft",
                "node_id": None,
                "content": "INSERT INTO ${ws_a}.dwd_secret SELECT * FROM ${ws_a}.ods_draft;",
            },
        ],
    )

    assert run_cli("analyze") == 0

    statements = _read(Path("analysis/evidence/sql/statements.json"))["statements"]
    assert statements
    assert {item["file_id"] for item in statements} == {"101"}
    assert all(item["node_id"] for item in statements)

    references = _read(Path("analysis/evidence/sql/table-references.json"))["references"]
    assert references
    assert {item["file_id"] for item in references} == {"101"}
    assert all(item["node_id"] for item in references)

    lineage = _read(Path("analysis/evidence/lineage/table-lineage.json"))["edges"]
    assert lineage
    assert {item["target_key"] for item in lineage} == {"ws_a.dwd_order"}
    assert all(evidence["file_id"] == "101" for item in lineage for evidence in item["evidence"])

    assert _read(Path("analysis/evidence/errors.json"))["count"] == 0

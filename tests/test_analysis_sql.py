"""M2.2 SQL Analysis 的黑盒测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import write_snapshot


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_split_and_reference_extraction(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """按分号切分语句，提取 source / target，CTE 不算 source。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "daily_etl",
                "node_id": "7001",
                "content": (
                    "-- header comment\n"
                    "DROP TABLE IF EXISTS ${ws_a}.dwd_order;\n"
                    "CREATE TABLE IF NOT EXISTS ${ws_a}.dwd_order "
                    "(id BIGINT COMMENT '主键') LIFECYCLE 30;\n"
                    "INSERT OVERWRITE TABLE ${ws_a}.dwd_order PARTITION (ds='${bizdate}')\n"
                    "SELECT c.id, d.id\n"
                    "FROM (\n"
                    "    SELECT id FROM ${ws_a}.ods_order\n"
                    ") c\n"
                    "LEFT JOIN ${ws_a}.dim_day d ON c.id = d.id;\n"
                    "WITH src AS (SELECT id FROM ${ws_a}.ods_order)\n"
                    "INSERT INTO ${ws_a}.dwd_order SELECT id FROM src;"
                ),
            }
        ],
    )

    assert run_cli("analyze") == 0

    statements = _read(Path("analysis/sql/statements.json"))
    assert statements["count"] == 4
    assert [item["statement_id"] for item in statements["statements"]] == [1, 2, 3, 4]
    assert {item["parse_status"] for item in statements["statements"]} == {"success"}
    assert {item["dialect"] for item in statements["statements"]} == {"odps"}

    references = _read(Path("analysis/sql/table-references.json"))

    by_statement = {item["statement_id"]: item for item in references["references"]}

    assert set(by_statement) == {2, 3, 4}

    # DROP 不产生表引用。
    assert 1 not in by_statement

    # CREATE TABLE 只有 target。
    assert by_statement[2]["source_tables"] == []
    assert by_statement[2]["target_tables"] == ["ws_a.dwd_order"]

    # 子查询别名 c 不是表，跨 Project 归一化保留原写法。
    assert by_statement[3]["source_tables"] == [
        "ws_a.dim_day",
        "ws_a.ods_order",
    ]
    assert by_statement[3]["target_tables"] == ["ws_a.dwd_order"]
    assert by_statement[3]["node_id"] == 7001

    # CTE 名称 src 不算 source。
    assert by_statement[4]["source_tables"] == ["ws_a.ods_order"]

    assert _read(Path("analysis/sql/parse-errors.json"))["count"] == 0


def test_parse_error_isolation(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """单条语句解析失败只影响该条，同一文件后续语句照常提取。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "301",
                "file_name": "broken_then_good",
                "content": (
                    "ALTER TABLE ${ws_a}.t1 ADD COLUMN (c STRING COMMENT 'x');\n"
                    "INSERT INTO ${ws_a}.t2 SELECT * FROM ${ws_a}.t1;\n"
                ),
            },
            {
                "workspace_id": 9001,
                "file_id": "302",
                "file_name": "unsupported",
                "content": "MSCK REPAIR TABLE ${ws_a}.t1;\n",
            },
        ],
    )

    assert run_cli("analyze") == 0

    statements = _read(Path("analysis/sql/statements.json"))
    status_by_id = {
        (item["file_id"], item["statement_id"]): item["parse_status"]
        for item in statements["statements"]
    }
    assert status_by_id[("301", 1)] == "error"
    assert status_by_id[("301", 2)] == "success"
    assert status_by_id[("302", 1)] == "unsupported"

    parse_errors = _read(Path("analysis/sql/parse-errors.json"))
    assert parse_errors["count"] == 2
    assert {item["error_type"] for item in parse_errors["errors"]} == {
        "SQL_PARSE_ERROR",
        "SQL_UNSUPPORTED_STATEMENT",
    }

    references = _read(Path("analysis/sql/table-references.json"))["references"]
    good = [item for item in references if item["file_id"] == "301" and item["statement_id"] == 2]
    assert len(good) == 1
    assert good[0]["target_tables"] == ["ws_a.t2"]
    assert good[0]["source_tables"] == ["ws_a.t1"]

    errors = _read(Path("analysis/errors.json"))
    assert errors["count"] == 2
    assert {item["stage"] for item in errors["errors"]} == {"sql"}


def test_non_sql_file_and_missing_content(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """非 SQL 文件被跳过；content 缺失记录为可恢复错误。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "401",
                "file_name": "python_job",
                "content": "print('x')",
                "file_type": 22,
                "content_format": "PYTHON",
            },
            {
                "workspace_id": 9001,
                "file_id": "402",
                "file_name": "missing_content",
                "content": "INSERT INTO ${ws_a}.t1 SELECT 1;",
            },
        ],
    )

    missing = Path("source/dataworks/workspaces/9001/content/402__missing_content.sql")
    missing.unlink()

    assert run_cli("analyze") == 0

    assert _read(Path("analysis/sql/statements.json"))["count"] == 0

    errors = _read(Path("analysis/errors.json"))
    assert errors["count"] == 1
    assert errors["errors"][0]["error_type"] == "CONTENT_FILE_MISSING"
    assert errors["errors"][0]["file_id"] == "402"

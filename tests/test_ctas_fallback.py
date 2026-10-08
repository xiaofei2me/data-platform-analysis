"""CTAS Fallback 的单元测试与 Golden Case 黑盒测试。

Golden Case 来自真实 Snapshot：

    workspace 466337 / file 504340625 / statement 2

该语句 sqlglot 解析为 Command，必须由 token scanner 提取出
1 个 target 与 4 个 source，而不是记成 SQL_UNSUPPORTED_STATEMENT。

scanner 曾出现过死循环，因此所有单元测试都通过守护线程加超时看门狗，
死循环会直接把测试判为失败，而不是挂住整个测试进程。
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest
from helpers import write_snapshot

from data_platform_analysis.analysis.evidence.sql.fallback import (
    extract_ctas_references,
    is_ctas_statement,
)
from data_platform_analysis.analysis.evidence.sql.sql_analysis import split_statements

FIXTURES = Path(__file__).parent / "fixtures"

GOLDEN_CONTENT = (FIXTURES / "golden_504340625.sql").read_text(encoding="utf-8")

GOLDEN_SOURCES = [
    "dme_cdm.dwd_master_data_product_pos_bu",
    "dme_ods.s_o2o_dmall_sale_info_all",
    "dme_ods.s_o2o_platform_sale_info",
    "dme_ods.s_tmkt_o2o_k1k2_mapping",
]
GOLDEN_TARGET = "dme_cdm.dwd_o2o_platform_sale_info_temp01"

WATCHDOG_TIMEOUT = 5.0


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_with_watchdog(
    raw_sql: str,
    timeout: float = WATCHDOG_TIMEOUT,
) -> tuple[list[str], list[str]]:
    """在守护线程里跑 scanner，超时即失败（防止死循环挂住测试进程）。"""

    values: dict[str, tuple[list[str], list[str]]] = {}
    errors: list[BaseException] = []

    def _run() -> None:
        try:
            values["value"] = extract_ctas_references(raw_sql)
        except BaseException as exc:  # noqa: BLE001 - 看门狗需要原样捕获
            errors.append(exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    assert not thread.is_alive(), f"CTAS scanner 在 {timeout}s 内没有结束，疑似死循环"
    assert not errors, f"CTAS scanner 抛出异常：{errors[0]!r}"

    return values["value"]


def golden_statement_2() -> str:
    """返回 Golden File 的第 2 条语句（statement_id = 2）。"""

    fragments, error = split_statements(GOLDEN_CONTENT)

    assert error is None
    assert len(fragments) == 3

    return fragments[1]


def test_golden_statement_is_extracted_without_hang() -> None:
    """Golden statement 2：不挂起，且恰好提取 4 个 source + 1 个 target。"""

    fragment = golden_statement_2()

    assert is_ctas_statement(fragment)

    sources, targets = extract_with_watchdog(fragment)

    assert sources == GOLDEN_SOURCES
    assert targets == [GOLDEN_TARGET]


@pytest.mark.parametrize(
    "fragment",
    [
        "create table p.t1 as select * from p.s1",
        "CREATE TABLE IF NOT EXISTS ${p}.t1 AS SELECT 1",
        "create or replace temporary table p.t1 as select 1",
        "create table p.t1 as (with a AS (SELECT 1) SELECT * FROM a)",
        "-- header comment\ncreate table p.t1 as select 1 from p.s1",
        "create table p.t1 as -- note\nselect 1 from p.s1",
        "create table p.t1 as /* note */ select 1 from p.s1",
    ],
)
def test_is_ctas_statement_accepts_ctas(fragment: str) -> None:
    """具备 CTAS 特征的语句进入 fallback 门槛。"""

    assert is_ctas_statement(fragment) is True


@pytest.mark.parametrize(
    "fragment",
    [
        "insert overwrite table p.t1 select 1 from p.s1",
        "insert into p.t1 select 1 from p.s1",
        "msck repair table p.t1",
        "create table p.t1 (id bigint)",
        "create view v1 as select 1 from p.s1",
        "alter table p.t1 add columns (c int)",
        "drop table if exists p.t1",
        "select * from p.s1",
    ],
)
def test_is_ctas_statement_rejects_other_sql(fragment: str) -> None:
    """非 CTAS 语句不进 fallback，保持原有 parse_status 行为。"""

    assert is_ctas_statement(fragment) is False


def test_simple_ctas_sources_and_target() -> None:
    """基础 CTAS：target 来自 CREATE TABLE，source 来自 FROM。"""

    sources, targets = extract_with_watchdog("create table ${p}.t1 as select a.id from ${q}.s1 a")

    assert sources == ["q.s1"]
    assert targets == ["p.t1"]


def test_cte_is_not_a_source() -> None:
    """CTE 名称不算 source，CTE 内部的物理表才算。"""

    sources, targets = extract_with_watchdog(
        "create table p.t1 as "
        "with cte as (select * from p.s1) "
        "select * from cte join p.s2 on cte.id = p.s2.id"
    )

    assert sources == ["p.s1", "p.s2"]
    assert "cte" not in sources
    assert targets == ["p.t1"]


def test_subquery_alias_and_lateral_view_are_not_tables() -> None:
    """子查询 alias、LATERAL VIEW alias 都不是表；逗号列表与 UNION 都要覆盖。"""

    sources, _ = extract_with_watchdog(
        "create table p.t1 as "
        "select * from ("
        "select * from p.s1 lateral view explode(c) cc as item"
        ") x left join p.s2 s on x.id = s.id "
        "union all "
        "select * from p.s3, p.s4"
    )

    assert sources == ["p.s1", "p.s2", "p.s3", "p.s4"]

    for alias in ("x", "s", "cc", "item"):
        assert alias not in sources


def test_scheduler_variables_are_normalized() -> None:
    """${...} 归一化成 project.table，裸 $ 不进结果。"""

    sources, targets = extract_with_watchdog(
        "create table ${dme_cdm}.t1 as select * from ${dme_ods}.s1"
    )

    assert sources == ["dme_ods.s1"]
    assert targets == ["dme_cdm.t1"]

    sources, _ = extract_with_watchdog("create table p.t1 as select * from $.s1")

    assert all("$" not in source for source in sources)


def test_target_is_not_reported_as_source() -> None:
    """自引用场景下 target 不会同时出现在 sources。"""

    sources, targets = extract_with_watchdog("create table ${p}.t1 as select * from ${p}.t1")

    assert targets == ["p.t1"]
    assert sources == []


def test_golden_file_is_analyzed_by_fallback(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Golden File 走 CLI：statement 2 由 fallback 提取，不再记 unsupported。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 466337, "name": "dme_cdm"}],
        files=[
            {
                "workspace_id": 466337,
                "file_id": "504340625",
                "file_name": "dwd_o2o_platform_sale_info",
                "node_id": "700006513476",
                "content": GOLDEN_CONTENT,
            }
        ],
    )

    assert run_cli("analyze") == 0

    statements = _read(Path("analysis/evidence/sql/statements.json"))
    assert statements["count"] == 3

    by_statement = {item["statement_id"]: item for item in statements["statements"]}
    assert by_statement[2]["parse_status"] == "success"
    assert by_statement[2]["extraction_method"] == "fallback"
    assert by_statement[1]["extraction_method"] == "ast"
    assert by_statement[3]["extraction_method"] == "ast"

    references = _read(Path("analysis/evidence/sql/table-references.json"))["references"]
    golden_reference = [item for item in references if item["statement_id"] == 2]

    assert len(golden_reference) == 1
    assert golden_reference[0]["source_tables"] == GOLDEN_SOURCES
    assert golden_reference[0]["target_tables"] == [GOLDEN_TARGET]
    assert golden_reference[0]["extraction_method"] == "fallback"

    assert _read(Path("analysis/evidence/sql/parse-errors.json"))["count"] == 0
    assert _read(Path("analysis/evidence/errors.json"))["count"] == 0

    edges = _read(Path("analysis/evidence/lineage/table-lineage.json"))["edges"]
    fallback_edges = [
        edge
        for edge in edges
        if edge["target_key"] == GOLDEN_TARGET and edge["source_key"] in GOLDEN_SOURCES
    ]

    assert len(fallback_edges) == len(GOLDEN_SOURCES)

    for edge in fallback_edges:
        assert any(evidence["extraction_method"] == "fallback" for evidence in edge["evidence"])

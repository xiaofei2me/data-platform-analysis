"""504340939 Golden Regression：DataWorks 全角右括号导致的 SQL_PARSE_ERROR 修复。

Golden 来自真实 Snapshot，以完整最小 snapshot 形式固化在

    tests/fixtures/snapshot_466339/

即

    workspace_id = 466339
    file_id      = 504340939
    statement_id = 8

修复前该语句是 SQL_PARSE_ERROR（Expecting ）。 Line 226, Col: 51），
根因是 DataWorks / MaxCompute 实际支持的全角右括号 U+FF09 不被
sqlglot ODPS parser 接受——属于 Parser Compatibility Gap，不是源 SQL 错误。

修复后必须满足：

1. 不再产生 SQL_PARSE_ERROR；
2. parse_status = success；
3. extraction_method = ast；
4. normalization_applied = true；
5. table references 正确、无 false positive；
6. statement_id / workspace_id / file_id 保持不变；
7. raw SQL 与 Snapshot 完全不变。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from helpers import assert_sandbox, source_tree_hash

from data_platform_analysis.analysis.evidence.sql.sql_analysis import split_statements

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOT_FIXTURE = FIXTURES / "snapshot_466339"

WORKSPACE_ID = 466339
FILE_ID = "504340939"
FILE_NAME = "tb_sales_city_attack_customer"
NODE_ID = 700006513666
"""Inventory / Statement / Reference 里的 NodeId（数字形态归一化为 int）。"""

STATEMENT_ID = 8

CONTENT_RELATIVE = f"dataworks/workspaces/{WORKSPACE_ID}/content/{FILE_ID}__{FILE_NAME}.sql"

GOLDEN_SOURCES = [
    "dme_ads.tb_controlling_reports_database_by_customer_mf",
    "dme_ads.tb_controlling_reports_database_by_customer_mf_v2",
    "dme_ads.tb_sales_city_attack_customer_tmp0",
    "dme_ads.tb_sales_city_attack_customer_tmp1",
    "dme_ads.tb_sales_city_attack_customer_tmp1_01",
    "dme_cdm.dwd_sap_customer_summary_bu",
]
GOLDEN_TARGET = "dme_ads.tb_sales_city_attack_customer_tmp2"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_snapshot() -> dict[str, str]:
    """把 fixture snapshot 复制成临时 source/，返回分析前的内容哈希。

    只能在 `cli_env`（`chdir(tmp_path)`）生效时调用；
    `assert_sandbox` 保证这里绝不会删到仓库根的真实 `source/`。
    """

    target = assert_sandbox(Path("source"))

    if target.exists():
        shutil.rmtree(target)

    shutil.copytree(SNAPSHOT_FIXTURE, target)

    return source_tree_hash(target)


def golden_content() -> str:
    """返回 fixture snapshot 里的 raw SQL。"""

    return (SNAPSHOT_FIXTURE / CONTENT_RELATIVE).read_text(encoding="utf-8")


def raw_statement_8() -> str:
    """返回 Golden File 的第 8 条语句（statement_id = 8）raw fragment。"""

    fragments, error = split_statements(golden_content())

    assert error is None
    assert len(fragments) == 39

    return fragments[STATEMENT_ID - 1]


def analyze(run_cli: Any) -> None:
    """按质量门禁的方式执行 analysis。"""

    assert run_cli("analyze", "--workspace", str(WORKSPACE_ID)) == 0


def test_fixture_matches_real_snapshot_shape() -> None:
    """fixture 保留真实 files-index 条目，statement 8 确实带全角右括号。"""

    index = _read(SNAPSHOT_FIXTURE / f"dataworks/workspaces/{WORKSPACE_ID}/files-index.json")

    assert index["workspace"] == {"id": WORKSPACE_ID, "name": "dme_ads"}
    assert index["count"] == 1
    assert len(index["files"]) == 1

    entry = index["files"][0]
    assert entry["file_id"] == FILE_ID
    assert entry["file_name"] == FILE_NAME
    assert entry["node_id"] == str(NODE_ID)
    assert entry["content_format"] == "SQL"
    assert (
        entry["raw_file"]
        == f"dataworks/workspaces/{WORKSPACE_ID}/files/{FILE_ID}__{FILE_NAME}.json"
    )
    assert entry["content_file"] == CONTENT_RELATIVE

    raw = raw_statement_8()
    assert "LAUNDRY'） and a.months<'202405'" in raw
    assert "LAUNDRY') and a.months<'202405'" not in raw


def test_golden_statement_8_is_parsed_with_normalization(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """statement 8 从 SQL_PARSE_ERROR 变成 AST success，raw SQL 保持不变。"""

    before = prepare_snapshot()

    analyze(run_cli)

    # Raw Snapshot 不可变。
    assert source_tree_hash(Path("source")) == before

    # 不再有 SQL_PARSE_ERROR，也不产生任何可恢复错误。
    assert _read(Path("analysis/evidence/sql/parse-errors.json"))["count"] == 0
    assert _read(Path("analysis/evidence/errors.json"))["count"] == 0

    statements = _read(Path("analysis/evidence/sql/statements.json"))
    assert statements["count"] == 39

    golden = [
        item
        for item in statements["statements"]
        if item["workspace_id"] == WORKSPACE_ID
        and item["file_id"] == FILE_ID
        and item["statement_id"] == STATEMENT_ID
    ]
    assert len(golden) == 1

    statement = golden[0]

    # 身份可追溯：workspace_id → file_id → statement_id。
    assert statement["node_id"] == NODE_ID
    assert statement["file_name"] == FILE_NAME
    assert statement["dialect"] == "odps"

    # 解析与提取方式。
    assert statement["parse_status"] == "success"
    assert statement["extraction_method"] == "ast"
    assert statement["normalization_applied"] is True
    assert statement["normalizations"] == [{"from": "）", "to": ")", "count": 1}]

    # raw SQL 完全不变。
    assert statement["sql"] == raw_statement_8()
    assert "LAUNDRY'） and" in statement["sql"]
    assert "LAUNDRY') and" not in statement["sql"]

    # 其余语句没有被误判为归一化。
    untouched = [
        item
        for item in statements["statements"]
        if item["statement_id"] != STATEMENT_ID and item["normalization_applied"]
    ]
    assert untouched == []


def test_golden_statement_8_table_references(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """statement 8 提取到正确的 source / target，且没有 false positive。"""

    prepare_snapshot()

    analyze(run_cli)

    references = [
        item
        for item in _read(Path("analysis/evidence/sql/table-references.json"))["references"]
        if item["file_id"] == FILE_ID and item["statement_id"] == STATEMENT_ID
    ]
    assert len(references) == 1

    reference = references[0]

    assert reference["workspace_id"] == WORKSPACE_ID
    assert reference["node_id"] == NODE_ID
    assert reference["extraction_method"] == "ast"
    assert reference["source_tables"] == GOLDEN_SOURCES
    assert reference["target_tables"] == [GOLDEN_TARGET]

    # false positive 防线：不出现裸 $、别名或 CTE 名。
    for table in reference["source_tables"] + reference["target_tables"]:
        assert "$" not in table
        assert table.count(".") == 1

    for alias in ("a", "b", "t", "x", "s", "cc", "item"):
        assert alias not in reference["source_tables"]

    # 血缘边来自该语句的证据。
    edges = [
        edge
        for edge in _read(Path("analysis/evidence/lineage/table-lineage.json"))["edges"]
        if edge["target_key"] == GOLDEN_TARGET
    ]
    assert {edge["source_key"] for edge in edges} == set(GOLDEN_SOURCES)

    for edge in edges:
        assert any(
            evidence["statement_id"] == STATEMENT_ID
            and evidence["file_id"] == FILE_ID
            and evidence["extraction_method"] == "ast"
            for evidence in edge["evidence"]
        )


def test_golden_statement_8_ctas_uses_ast_not_fallback(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """statement 8 是 CTAS，但走 normalization + AST，不走 CTAS fallback。

    同时确认归一化没有波及同文件的其他语句——
    全角括号与 CTAS fallback 是两个独立阶段。
    """

    prepare_snapshot()

    analyze(run_cli)

    statements = {
        item["statement_id"]: item
        for item in _read(Path("analysis/evidence/sql/statements.json"))["statements"]
    }

    golden = statements[STATEMENT_ID]
    assert golden["sql"].lstrip().lower().startswith("create table")
    assert golden["extraction_method"] == "ast"
    assert golden["normalization_applied"] is True

    for statement_id, statement in statements.items():
        if statement_id == STATEMENT_ID:
            continue

        assert statement["normalization_applied"] is False
        assert statement["normalizations"] == []
        assert statement["extraction_method"] in ("ast", "fallback")

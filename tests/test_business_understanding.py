"""M3 Business Understanding 的测试。

覆盖任务要求的场景：分词与关键词匹配 / confidence 规则 / 四类 Direct Evidence /
SQL 与血缘证据的防膨胀规则 / 多 Domain 多 Object 全保留 / 层级只读 M2.2 /
UNKNOWN 与 AMBIGUOUS / 术语汇总与 stopwords / 汇总产物 / 报告小节 /
CLI 黑盒与确定性 / 错误路径 / 不进入 analyze 流水线。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from helpers import write_snapshot

from data_platform_analysis.analysis.business.understanding import (
    BusinessUnderstandingError,
    KeywordMatcher,
    business_tokens,
    load_business_rules,
    resolve_confidence,
    run_business_understanding,
    tokenize_identifier,
)
from data_platform_analysis.analysis.models import (
    BUSINESS_CONFIDENCE_HIGH,
    BUSINESS_CONFIDENCE_LOW,
    BUSINESS_CONFIDENCE_MEDIUM,
    BUSINESS_CONFIDENCE_UNKNOWN,
    BUSINESS_EVIDENCE_COLUMN_COMMENT,
    BUSINESS_EVIDENCE_COLUMN_NAME,
    BUSINESS_EVIDENCE_LINEAGE,
    BUSINESS_EVIDENCE_SQL,
    BUSINESS_EVIDENCE_TABLE_COMMENT,
    BUSINESS_EVIDENCE_TABLE_NAME,
)

# ============================================================
# 测试数据
# ============================================================

RULES_TEXT = """\
version: "1.0"

stopwords:
  - dwd
  - id

domains:
  sales:
    name: 销售
    keywords:
      - 销售
      - sales
  customer:
    name: 客户
    keywords:
      - 客户
      - customer

objects:
  order:
    name: 订单
    keywords:
      - 订单
      - order
  product:
    name: 产品
    keywords:
      - product
"""

EMPTY_STOPWORDS_RULES_TEXT = RULES_TEXT.replace(
    "stopwords:\n  - dwd\n  - id\n",
    "stopwords: []\n",
)

KEYWORD_CONFLICT_RULES_TEXT = RULES_TEXT.replace(
    "  - dwd\n  - id\n",
    "  - dwd\n  - sales\n",
)


def _write_rules(path: Path, text: str = RULES_TEXT) -> Path:
    """写出 business-rules 配置。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    return path


def _table(
    workspace_id: int,
    project: str,
    table: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """构造 M2.1 tables.json 中的单条记录。"""

    return {
        "workspace_id": workspace_id,
        "workspace_name": project,
        "project": project,
        "schema": "",
        "table": table,
        "comment": comment,
        "table_key": f"{project}.{table}",
    }


def _column(
    workspace_id: int,
    project: str,
    table: str,
    column_name: str,
    ordinal: int,
    comment: str | None = None,
) -> dict[str, Any]:
    """构造 M2.1 columns.json 中的单条记录。"""

    return {
        "workspace_id": workspace_id,
        "project": project,
        "schema": "",
        "table": table,
        "ordinal": ordinal,
        "column_name": column_name,
        "data_type": "STRING",
        "comment": comment,
        "is_partition": False,
        "table_key": f"{project}.{table}",
    }


def _write_m2(
    analysis_dir: Path,
    *,
    tables: list[dict[str, Any]],
    columns: list[dict[str, Any]],
    statements: list[dict[str, Any]] | None = None,
    references: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    candidates: list[dict[str, Any]] | None = None,
    assessments: list[dict[str, Any]] | None = None,
) -> None:
    """直接写出 M3 依赖的全部 M2 产物（不跑 M2，也不需要 source/）。"""

    payloads: list[tuple[str, str, list[dict[str, Any]]]] = [
        ("inventory", "tables", tables),
        ("inventory", "columns", columns),
        ("sql", "statements", list(statements or [])),
        ("sql", "references", list(references or [])),
        ("lineage", "edges", list(edges or [])),
        ("lineage", "candidates", list(candidates or [])),
        ("layer", "assessments", list(assessments or [])),
    ]

    # M2 文件名与 JSON 字段名各不相同，单独列出。
    names = {
        "tables": "tables.json",
        "columns": "columns.json",
        "statements": "statements.json",
        "references": "table-references.json",
        "edges": "table-lineage.json",
        "candidates": "core-table-candidates.json",
        "assessments": "assessments.json",
    }

    for folder, key, records in payloads:
        path = analysis_dir / folder / names[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"count": len(records), key: records},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def _assessment(
    workspace_id: int,
    project: str,
    table: str,
    workspace_layer: str | None,
    candidate_layer: str | None,
) -> dict[str, Any]:
    """构造 M2.2 assessments.json 中的单条记录。"""

    return {
        "workspace_id": workspace_id,
        "workspace_name": project,
        "workspace_layer": workspace_layer,
        "project": project,
        "table_name": table,
        "table_identifier": f"{project}.{table}",
        "candidate_layer": candidate_layer,
        "status": "MATCH" if candidate_layer else "UNKNOWN",
        "evidence": [],
    }


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _by_table(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["table_key"]: item for item in payload["tables"]}


def _evidence_types(item: dict[str, Any]) -> set[str]:
    return {entry["type"] for entry in item["evidence"]}


# ============================================================
# 1. 分词与 stopwords
# ============================================================


def test_tokenizer_supports_snake_camel_and_digits() -> None:
    """snake_case / camelCase / PascalCase / 数字都能拆开。"""

    assert tokenize_identifier("dwd_sales_order") == ["dwd", "sales", "order"]
    assert tokenize_identifier("customerId") == ["customer", "Id"]
    assert tokenize_identifier("CustomerID") == ["Customer", "ID"]
    assert tokenize_identifier("order2024") == ["order2024"]


def test_business_tokens_drop_stopwords_and_digits() -> None:
    """技术 token（dwd）与纯数字不进入业务词。"""

    stopwords = frozenset({"dwd", "id"})

    # 纯数字 token 同样剔除。
    assert business_tokens("dwd_sales_2024", frozenset({"dwd"})) == ["sales"]
    assert "dwd" not in business_tokens("dwd_sales_order", stopwords)
    assert business_tokens("dwd_id", stopwords) == []


# ============================================================
# 2. 关键词匹配：英文词边界 / 中文子串 / 大小写
# ============================================================


def test_keyword_match_uses_word_boundary_for_english(tmp_path: Path) -> None:
    """英文按词边界匹配：wholesale 中的 sales 不算命中。"""

    rules = load_business_rules(_write_rules(tmp_path / "business-rules.yaml"))
    matcher = KeywordMatcher(rules.all_keywords)

    assert matcher.match_text("wholesale metrics") == []
    assert matcher.match_text("sales amount") == ["sales"]
    assert matcher.match_text("SALES Amount") == ["sales"]


def test_keyword_match_chinese_substring(tmp_path: Path) -> None:
    """中文按子串匹配。"""

    rules = load_business_rules(_write_rules(tmp_path / "business-rules.yaml"))
    matcher = KeywordMatcher(rules.all_keywords)

    assert matcher.match_text("销售订单明细表") == ["销售", "订单"]
    assert matcher.match_text("库存快照") == []


# ============================================================
# 3. confidence 规则
# ============================================================


def test_confidence_by_independent_evidence_types() -> None:
    """≥3 种来源 = high，2 种 = medium，1 种表注释 = medium，其余 = low。"""

    assert (
        resolve_confidence(
            [BUSINESS_EVIDENCE_TABLE_NAME, BUSINESS_EVIDENCE_COLUMN_COMMENT, BUSINESS_EVIDENCE_SQL]
        )
        == BUSINESS_CONFIDENCE_HIGH
    )
    assert (
        resolve_confidence([BUSINESS_EVIDENCE_TABLE_NAME, BUSINESS_EVIDENCE_COLUMN_NAME])
        == BUSINESS_CONFIDENCE_MEDIUM
    )
    assert resolve_confidence([BUSINESS_EVIDENCE_TABLE_COMMENT]) == BUSINESS_CONFIDENCE_MEDIUM
    assert resolve_confidence([BUSINESS_EVIDENCE_TABLE_NAME]) == BUSINESS_CONFIDENCE_LOW
    assert resolve_confidence([BUSINESS_EVIDENCE_SQL]) == BUSINESS_CONFIDENCE_LOW
    assert resolve_confidence([]) == BUSINESS_CONFIDENCE_UNKNOWN


# ============================================================
# 4. Direct Evidence：表名 / 表注释 / 字段名 / 字段注释
# ============================================================


def test_direct_evidence_sources_are_all_recorded(tmp_path: Path) -> None:
    """四类 Direct Evidence 各自成条，同一关键词多来源不去重。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[_table(9001, "proj", "dwd_sales", comment="销售明细表")],
        columns=[
            _column(9001, "proj", "dwd_sales", "sales_amount", 0),
            _column(9001, "proj", "dwd_sales", "customer_id", 1, comment="客户编号"),
        ],
        assessments=[
            _assessment(9001, "proj", "dwd_sales", "CDM", "DWD"),
        ],
    )

    result = run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    item = _by_table({"tables": [entry.to_dict() for entry in result.tables]})[
        "proj.dwd_sales"
    ]

    # 表名 + 字段名命中 sales；表注释命中中文「销售」，各成一条。
    sales_evidence = [entry for entry in item["evidence"] if entry["keyword"] == "sales"]
    assert {entry["type"] for entry in sales_evidence} == {
        BUSINESS_EVIDENCE_TABLE_NAME,
        BUSINESS_EVIDENCE_COLUMN_NAME,
    }

    chinese_evidence = [entry for entry in item["evidence"] if entry["keyword"] == "销售"]
    assert {entry["type"] for entry in chinese_evidence} == {BUSINESS_EVIDENCE_TABLE_COMMENT}

    customer_evidence = [
        entry for entry in item["evidence"] if entry["keyword"] in {"customer", "客户"}
    ]
    assert {entry["type"] for entry in customer_evidence} == {
        BUSINESS_EVIDENCE_COLUMN_NAME,
        BUSINESS_EVIDENCE_COLUMN_COMMENT,
    }

    comment_entry = next(
        entry for entry in item["evidence"] if entry["type"] == BUSINESS_EVIDENCE_TABLE_COMMENT
    )
    assert comment_entry["value"] == "销售明细表"
    assert comment_entry["table_key"] == "proj.dwd_sales"

    column_comment = next(
        entry for entry in item["evidence"] if entry["type"] == BUSINESS_EVIDENCE_COLUMN_COMMENT
    )
    assert column_comment["column_name"] == "customer_id"
    assert column_comment["value"] == "客户编号"

    # sales 域拿到 3 类独立来源（表名 / 字段名 / 表注释）→ high。
    domain = next(entry for entry in item["domain_candidates"] if entry["domain"] == "sales")
    assert domain["confidence"] == BUSINESS_CONFIDENCE_HIGH


# ============================================================
# 5. SQL 证据只补充未覆盖关键词（防膨胀）
# ============================================================


def test_sql_evidence_skips_keyword_covered_by_direct_evidence(tmp_path: Path) -> None:
    """SQL 里已出现在表名中的关键词不再重复记 SQL 证据。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[_table(9001, "proj", "dwd_sales")],
        columns=[_column(9001, "proj", "dwd_sales", "id", 0)],
        statements=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "statement_id": 1,
                "sql": "SELECT sales, customer FROM proj.dwd_sales",
            }
        ],
        references=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "statement_id": 1,
                "source_tables": [],
                "target_tables": ["proj.dwd_sales"],
            }
        ],
        assessments=[_assessment(9001, "proj", "dwd_sales", "CDM", "DWD")],
    )

    result = run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    item = _by_table({"tables": [entry.to_dict() for entry in result.tables]})[
        "proj.dwd_sales"
    ]
    sql_entries = [entry for entry in item["evidence"] if entry["type"] == BUSINESS_EVIDENCE_SQL]

    # sales 已被表名覆盖，不再产生 sql 证据；customer 只出现在 SQL 中。
    assert [entry["keyword"] for entry in sql_entries] == ["customer"]
    assert sql_entries[0]["workspace_id"] == 9001
    assert sql_entries[0]["file_id"] == "101"
    assert sql_entries[0]["statement_id"] == 1
    assert "sales" not in {
        entry["keyword"] for entry in item["evidence"] if entry["type"] == BUSINESS_EVIDENCE_SQL
    }


# ============================================================
# 6. 血缘证据只补充未覆盖关键词（防膨胀）
# ============================================================


def test_lineage_evidence_only_for_uncovered_keyword(tmp_path: Path) -> None:
    """邻居表名带来的关键词只在名称 / 注释 / SQL 都没覆盖时才记入。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[
            _table(9001, "proj", "dwd_sales"),
            _table(9001, "proj", "dim_customer"),
        ],
        columns=[_column(9001, "proj", "dwd_sales", "id", 0)],
        edges=[
            {
                "workspace_id": 9001,
                "source_table": "proj.dim_customer",
                "target_table": "proj.dwd_sales",
                "source_key": "proj.dim_customer",
                "target_key": "proj.dwd_sales",
            }
        ],
        assessments=[
            _assessment(9001, "proj", "dwd_sales", "CDM", "DWD"),
            _assessment(9001, "proj", "dim_customer", "CDM", "DIM"),
        ],
    )

    result = run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    items = _by_table({"tables": [entry.to_dict() for entry in result.tables]})
    target = items["proj.dwd_sales"]

    lineage_entries = [
        entry for entry in target["evidence"] if entry["type"] == BUSINESS_EVIDENCE_LINEAGE
    ]

    assert len(lineage_entries) == 1
    assert lineage_entries[0]["keyword"] == "customer"
    assert lineage_entries[0]["source_table"] == "proj.dim_customer"
    assert lineage_entries[0]["target_table"] == "proj.dwd_sales"

    # 反向：source 侧自己的表名已覆盖 customer，不再把它记成血缘证据；
    # 它从邻居拿到的只有 sales。
    source = items["proj.dim_customer"]
    source_lineage = [
        entry for entry in source["evidence"] if entry["type"] == BUSINESS_EVIDENCE_LINEAGE
    ]
    assert [entry["keyword"] for entry in source_lineage] == ["sales"]


def test_lineage_keyword_already_in_direct_evidence_is_not_duplicated(
    tmp_path: Path,
) -> None:
    """邻居关键词已被本表字段名覆盖时，不产生 lineage 证据。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[
            _table(9001, "proj", "dwd_sales"),
            _table(9001, "proj", "dim_customer"),
        ],
        columns=[_column(9001, "proj", "dwd_sales", "customer_id", 0)],
        edges=[
            {
                "workspace_id": 9001,
                "source_table": "proj.dim_customer",
                "target_table": "proj.dwd_sales",
                "source_key": "proj.dim_customer",
                "target_key": "proj.dwd_sales",
            }
        ],
        assessments=[
            _assessment(9001, "proj", "dwd_sales", "CDM", "DWD"),
            _assessment(9001, "proj", "dim_customer", "CDM", "DIM"),
        ],
    )

    result = run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    target = _by_table({"tables": [entry.to_dict() for entry in result.tables]})[
        "proj.dwd_sales"
    ]

    assert BUSINESS_EVIDENCE_LINEAGE not in _evidence_types(target)
    assert BUSINESS_EVIDENCE_COLUMN_NAME in _evidence_types(target)


# ============================================================
# 7. 多 Domain / 多 Object 全保留，不擅自选择
# ============================================================


def test_multi_domain_and_object_candidates_are_all_kept(tmp_path: Path) -> None:
    """同时命中多个类别时全部保留，并按 confidence 降序排列。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[_table(9001, "proj", "dwd_sales", comment="销售订单表")],
        columns=[
            _column(9001, "proj", "dwd_sales", "customer_id", 0),
            _column(9001, "proj", "dwd_sales", "product_id", 1),
        ],
        assessments=[_assessment(9001, "proj", "dwd_sales", "CDM", "DWD")],
    )

    result = run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    item = _by_table({"tables": [entry.to_dict() for entry in result.tables]})[
        "proj.dwd_sales"
    ]

    # Domain：sales（表名 + 表注释 → medium）、customer（字段名 → low），全保留。
    domain_confidence = {
        entry["domain"]: entry["confidence"] for entry in item["domain_candidates"]
    }
    assert set(domain_confidence) == {"sales", "customer"}
    assert domain_confidence["sales"] == BUSINESS_CONFIDENCE_MEDIUM
    assert domain_confidence["customer"] == BUSINESS_CONFIDENCE_LOW
    assert [entry["domain"] for entry in item["domain_candidates"]] == ["sales", "customer"]

    # Object：order（表注释）、product（字段名），同样全保留。
    object_confidence = {
        entry["object"]: entry["confidence"] for entry in item["business_object_candidates"]
    }
    assert set(object_confidence) == {"order", "product"}
    assert object_confidence["order"] == BUSINESS_CONFIDENCE_MEDIUM
    assert object_confidence["product"] == BUSINESS_CONFIDENCE_LOW
    assert [entry["object"] for entry in item["business_object_candidates"]] == [
        "order",
        "product",
    ]

    # 候选自带证据子集，且证据类型不超出表级 evidence。
    sales = next(entry for entry in item["domain_candidates"] if entry["domain"] == "sales")
    assert sales["evidence"]
    assert all(entry["keyword"] for entry in sales["evidence"])


# ============================================================
# 8. 层级只读 M2.2，不自行判定
# ============================================================


def test_layer_is_copied_from_m2_assessment(tmp_path: Path) -> None:
    """warehouse_layer / candidate_sub_layer 直接来自 M2.2，缺失时留空。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[
            _table(9001, "proj", "dwd_sales"),
            _table(9001, "proj", "no_layer_table"),
        ],
        columns=[_column(9001, "proj", "dwd_sales", "sales_amt", 0)],
        assessments=[_assessment(9001, "proj", "dwd_sales", "CDM", "DWD")],
    )

    result = run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    items = _by_table({"tables": [entry.to_dict() for entry in result.tables]})

    assessed = items["proj.dwd_sales"]
    assert assessed["warehouse_layer"] == "CDM"
    assert assessed["candidate_sub_layer"] == "DWD"
    assert assessed["is_core_candidate"] is False

    # 没有 M2.2 记录 → 留空，而不是按表名猜一个层级。
    missing = items["proj.no_layer_table"]
    assert missing["warehouse_layer"] is None
    assert missing["candidate_sub_layer"] is None


def test_core_candidate_flag_comes_from_m2_lineage(tmp_path: Path) -> None:
    """is_core_candidate 来自 M2.4 核心表候选（大小写不敏感对齐）。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[_table(9001, "proj", "dwd_sales")],
        columns=[_column(9001, "proj", "dwd_sales", "sales_amt", 0)],
        candidates=[{"table_key": "PROJ.DWD_SALES", "workspace_id": 9001}],
        assessments=[_assessment(9001, "proj", "dwd_sales", "CDM", "DWD")],
    )

    result = run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    item = _by_table({"tables": [entry.to_dict() for entry in result.tables]})[
        "proj.dwd_sales"
    ]

    assert item["is_core_candidate"] is True


# ============================================================
# 9. UNKNOWN / AMBIGUOUS
# ============================================================


def test_unknown_and_ambiguous_flags(tmp_path: Path) -> None:
    """没有任何候选 → UNKNOWN；命中多个 Domain → AMBIGUOUS。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[
            _table(9001, "proj", "dwd_sales", comment="销售明细"),
            _table(9001, "proj", "tmp_x"),
            _table(9001, "proj", "mix_a", comment="销售客户"),
        ],
        columns=[_column(9001, "proj", "dwd_sales", "sales_amt", 0)],
        assessments=[
            _assessment(9001, "proj", "dwd_sales", "CDM", "DWD"),
            _assessment(9001, "proj", "tmp_x", "CDM", None),
            _assessment(9001, "proj", "mix_a", "CDM", None),
        ],
    )

    result = run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    flags = {entry.table_key: entry for entry in result.tables}

    # 无任何候选 → UNKNOWN。
    assert result.unknown_table_count == 1
    assert flags["proj.tmp_x"].is_unknown
    assert not flags["proj.dwd_sales"].is_unknown

    # 同时命中 sales / customer → AMBIGUOUS，两个候选都保留。
    assert result.ambiguous_table_count == 1
    assert flags["proj.mix_a"].is_ambiguous
    assert len(flags["proj.mix_a"].domain_candidates) == 2

    # dwd_sales：表名 + 字段名 + 表注释 3 类来源 → high。
    assert result.strong_table_count == 1
    assert flags["proj.dwd_sales"].has_strong_evidence


# ============================================================
# 10. 术语汇总与 stopwords
# ============================================================


def test_terms_exclude_stopwords_and_are_sorted(tmp_path: Path) -> None:
    """terms.json 按 count 降序、normalized 升序；dwd 不进入术语。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[_table(9001, "proj", "dwd_sales", comment="销售明细")],
        columns=[
            _column(9001, "proj", "dwd_sales", "dwd_id", 0),
            _column(9001, "proj", "dwd_sales", "sales_id", 1),
            _column(9001, "proj", "dwd_sales", "Sales_Amt", 2),
        ],
        assessments=[_assessment(9001, "proj", "dwd_sales", "CDM", "DWD")],
    )

    run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    payload = _read(analysis_dir / "business" / "terms.json")

    assert payload["sort_by"] == "count_desc,normalized_term_asc"
    assert payload["count"] == len(payload["terms"])

    keys = [(-item["count"], item["normalized_term"]) for item in payload["terms"]]
    assert keys == sorted(keys)

    normalized = {item["normalized_term"] for item in payload["terms"]}
    assert "dwd" not in normalized
    assert "sales" in normalized
    assert "sales_id" not in normalized  # 术语是分词后的 token，不是整串

    sales = next(item for item in payload["terms"] if item["normalized_term"] == "sales")
    assert sales["term"] in {"sales", "Sales"}  # 并列时取出现次数最多的原始写法
    assert sales["count"] == 3
    assert sales["sources"][0]["type"] in {"table_name", "column_name"}
    assert all(source["table_key"] == "proj.dwd_sales" for source in sales["sources"])

    # 表内 business_terms 同样剔除 stopwords，按出现次数降序。
    tables_payload = _read(analysis_dir / "business" / "tables.json")
    item = _by_table(tables_payload)["proj.dwd_sales"]
    assert "dwd" not in item["business_terms"]
    assert item["business_terms"][0] == "sales"


# ============================================================
# 11. domains.json / objects.json 汇总
# ============================================================


def test_domain_and_object_summaries_are_complete(tmp_path: Path) -> None:
    """配置里的类别全部出现在汇总里，confidence 计数与表数一致。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[
            _table(9001, "proj", "dwd_sales"),
            _table(9001, "proj", "no_match", comment="完全无关"),
        ],
        columns=[_column(9001, "proj", "dwd_sales", "sales_amt", 0)],
        assessments=[
            _assessment(9001, "proj", "dwd_sales", "CDM", "DWD"),
            _assessment(9001, "proj", "no_match", "CDM", None),
        ],
    )

    run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    domains = _read(analysis_dir / "business" / "domains.json")
    objects = _read(analysis_dir / "business" / "objects.json")

    assert domains["count"] == 2
    assert objects["count"] == 2

    sales = next(item for item in domains["domains"] if item["domain"] == "sales")
    assert sales["name"] == "销售"
    assert sales["table_count"] == 1
    assert sum(sales["confidence_counts"].values()) == 1
    assert sales["tables"][0]["table_key"] == "proj.dwd_sales"

    # 没有命中的类别也保留（table_count = 0），配置与产物一一对应。
    customer = next(item for item in domains["domains"] if item["domain"] == "customer")
    assert customer["table_count"] == 0
    assert customer["tables"] == []

    assert [item["domain"] for item in domains["domains"]] == sorted(
        item["domain"] for item in domains["domains"]
    )
    assert [item["object"] for item in objects["objects"]] == ["order", "product"]


# ============================================================
# 12. summary.md 小节
# ============================================================


def test_summary_contains_required_sections(tmp_path: Path) -> None:
    """summary.md 覆盖 7 个小节，且不生成业务描述式结论。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(
        analysis_dir,
        tables=[
            _table(9001, "proj", "dwd_sales"),
            _table(9001, "proj", "tmp_x"),
        ],
        columns=[_column(9001, "proj", "dwd_sales", "sales_amt", 0)],
        assessments=[
            _assessment(9001, "proj", "dwd_sales", "CDM", "DWD"),
            _assessment(9001, "proj", "tmp_x", "CDM", None),
        ],
    )

    run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=_write_rules(tmp_path / "business-rules.yaml"),
        output_dir=analysis_dir / "business",
    )

    summary = (analysis_dir / "business" / "summary.md").read_text(encoding="utf-8")

    for heading in (
        "# M3 Business Understanding Summary",
        "## 1. Overview",
        "## 2. Domain Candidates",
        "## 3. Business Object Candidates",
        "## 4. Business Terms",
        "## 5. Evidence Composition",
        "## 6. Ambiguous / Unknown",
        "## 7. Limitations",
    ):
        assert heading in summary

    assert "proj.tmp_x" in summary  # UNKNOWN 明细里能看到具体表
    assert "销售" in summary
    assert "不是业务结论" in summary

    # 不输出「这是……事实表」这类业务描述。
    assert "这是" not in summary
    assert "事实表" not in summary


# ============================================================
# 13. CLI 黑盒：analyze-business + 确定性 + 只读 M2
# ============================================================


def test_analyze_business_command_writes_outputs(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze-business 产出 5 个文件，两次运行字节一致，且不修改 M2 输入。"""

    rules_path = _write_rules(tmp_path / "config" / "business-rules.yaml")
    monkeypatch.setenv("BUSINESS_RULES_PATH", str(rules_path))

    _write_m2(
        Path("analysis"),
        tables=[_table(9001, "proj", "dwd_sales", comment="销售明细")],
        columns=[_column(9001, "proj", "dwd_sales", "sales_amt", 0)],
        assessments=[_assessment(9001, "proj", "dwd_sales", "CDM", "DWD")],
    )

    m2_inputs = {
        path: path.read_bytes() for path in sorted(Path("analysis").rglob("*.json"))
    }

    assert run_cli("analyze-business") == 0

    business_dir = Path("analysis/business")
    for name in ("terms.json", "tables.json", "domains.json", "objects.json", "summary.md"):
        assert (business_dir / name).exists(), name

    first_run = {path: path.read_bytes() for path in sorted(business_dir.rglob("*"))}

    # M2 输入一个字节都没变。
    assert {path: path.read_bytes() for path in m2_inputs} == m2_inputs

    assert run_cli("analyze-business") == 0
    assert {path: path.read_bytes() for path in sorted(business_dir.rglob("*"))} == first_run


def test_analyze_business_command_fails_without_m2_inputs(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """M2 产物缺失 → 退出码 1，提示先跑 analyze，不写产物。"""

    rules_path = _write_rules(tmp_path / "config" / "business-rules.yaml")
    monkeypatch.setenv("BUSINESS_RULES_PATH", str(rules_path))

    assert run_cli("analyze-business") == 1
    assert not Path("analysis/business").exists()


def test_analyze_command_does_not_run_business_stage(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze 仍只跑 M2，不产出 analysis/business。"""

    rules_path = _write_rules(tmp_path / "config" / "business-rules.yaml")
    monkeypatch.setenv("BUSINESS_RULES_PATH", str(rules_path))

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "proj"}],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_sales",
                "columns": [{"name": "sales_amt", "type": "BIGINT"}],
            }
        ],
    )

    assert run_cli("analyze") == 0

    assert Path("analysis/layer/assessments.json").exists()
    assert not Path("analysis/business").exists()


# ============================================================
# 14. 错误路径
# ============================================================


def test_missing_rules_file_raises(tmp_path: Path) -> None:
    """词典缺失 → 明确报错，不回退默认词典。"""

    with pytest.raises(BusinessUnderstandingError, match="配置文件不存在"):
        load_business_rules(tmp_path / "business-rules.yaml")


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    """词典不是合法 YAML → 明确报错。"""

    path = tmp_path / "business-rules.yaml"
    path.write_text("version: [\n", encoding="utf-8")

    with pytest.raises(BusinessUnderstandingError, match="不是合法的 YAML"):
        load_business_rules(path)


def test_missing_version_raises(tmp_path: Path) -> None:
    """缺少 version → 明确报错。"""

    path = tmp_path / "business-rules.yaml"
    path.write_text("stopwords: [a]\ndomains: {}\nobjects: {}\n", encoding="utf-8")

    with pytest.raises(BusinessUnderstandingError, match="缺少 version"):
        load_business_rules(path)


def test_empty_stopwords_raises(tmp_path: Path) -> None:
    """stopwords 为空 → 明确报错（技术 token 必须显式声明）。"""

    with pytest.raises(BusinessUnderstandingError, match="stopwords 必须是非空列表"):
        load_business_rules(
            _write_rules(tmp_path / "business-rules.yaml", EMPTY_STOPWORDS_RULES_TEXT)
        )


def test_keyword_conflicting_with_stopwords_raises(tmp_path: Path) -> None:
    """关键词与 stopwords 冲突 → 明确报错。"""

    with pytest.raises(BusinessUnderstandingError, match="关键词与 stopwords 冲突"):
        load_business_rules(
            _write_rules(tmp_path / "business-rules.yaml", KEYWORD_CONFLICT_RULES_TEXT)
        )


def test_bare_yaml_boolean_stopword_raises(tmp_path: Path) -> None:
    """YAML 裸 no 被解析成布尔值 → 明确报错并提示加引号。"""

    text = RULES_TEXT.replace("  - dwd\n  - id\n", '  - dwd\n  - no\n')
    path = _write_rules(tmp_path / "business-rules.yaml", text)

    with pytest.raises(BusinessUnderstandingError, match="需要加引号"):
        load_business_rules(path)

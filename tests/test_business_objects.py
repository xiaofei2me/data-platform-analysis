"""M3.2 Business Object & Relationship Analysis 的测试。

覆盖任务要求的场景：输入缺失 / 非法 / 只读 / checklist 解析 / 状态规则 /
三种关系证据与合并 / strength 映射 / core 标记 / 产物结构与报告 / 确定性 / CLI 黑盒。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_business_understanding import (
    RULES_TEXT,
    _assessment,
    _column,
    _table,
    _write_m2,
    _write_rules,
)

from data_platform_analysis.analysis.models import (
    EVIDENCE_STRENGTH_MODERATE,
    EVIDENCE_STRENGTH_STRONG,
    EVIDENCE_STRENGTH_WEAK,
    OBJECT_STATUS_CANDIDATE,
    OBJECT_STATUS_CONFIRMED,
    OBJECT_STATUS_NEEDS_DISCUSSION,
    OBJECT_STATUS_REJECTED,
    RELATIONSHIP_EVIDENCE_CO_OCCURRENCE,
    RELATIONSHIP_EVIDENCE_LINEAGE,
    RELATIONSHIP_EVIDENCE_SQL,
    RELATIONSHIP_TYPE_CANDIDATE,
)
from data_platform_analysis.analysis.understanding.business.objects import (
    OUTPUT_FILES,
    BusinessObjectsError,
    HumanReview,
    parse_review_checklist,
    read_object_inputs,
    run_business_object_analysis,
)
from data_platform_analysis.analysis.understanding.business.quality import (
    run_business_quality_assessment,
)
from data_platform_analysis.analysis.understanding.business.understanding import (
    run_business_understanding,
)

# ============================================================
# 测试数据
# ============================================================

OBJECT_RULES_TEXT = """\
version: "1.0"

stopwords:
  - dwd
  - id

domains:
  customer:
    name: 客户
    keywords:
      - 客户
      - customer
  sales:
    name: 销售
    keywords:
      - 销售
      - sales

objects:
  customer:
    name: 客户
    keywords:
      - 客户
      - customer
  order:
    name: 订单
    keywords:
      - 订单
      - order
  product:
    name: 产品
    keywords:
      - product
      - 商品
  store:
    name: 门店
    keywords:
      - 门店
      - store
"""

M3_NAMES = (
    "terms.json",
    "tables.json",
    "domains.json",
    "objects.json",
    "summary.md",
)

M31_NAMES = (
    "quality-assessment.json",
    "quality-assessment.md",
    "review-checklist.md",
)

CHECKLIST_TEMPLATE = """\
# M3.1 Review Checklist

| table | human domain | human object | status |
| --- | --- | --- | --- |
{rows}
"""


def _row(
    table: str,
    human_domain: str = "",
    human_object: str = "",
    status: str = "pending",
) -> str:
    """构造一行 review-checklist。"""

    return f"| {table} | {human_domain} | {human_object} | {status} |"


def _prepare(
    tmp_path: Path,
    *,
    rules_text: str = OBJECT_RULES_TEXT,
    **m2: Any,
) -> Path:
    """写出 M2 产物并跑完 M3 / M3.1，返回 analysis 目录。"""

    analysis_dir = tmp_path / "analysis"
    rules_path = _write_rules(tmp_path / "config" / "business-rules.yaml", rules_text)

    _write_m2(analysis_dir, **m2)

    run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=rules_path,
        output_dir=analysis_dir / "understanding" / "business",
    )
    run_business_quality_assessment(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "understanding" / "business",
    )

    return analysis_dir


def _run(analysis_dir: Path) -> Any:
    return run_business_object_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "understanding" / "business",
    )


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_checklist(analysis_dir: Path, *rows: str) -> None:
    """覆盖 M3.1 生成的清单，只保留人工回填需要的四列。"""

    text = CHECKLIST_TEMPLATE.format(rows="\n".join(rows))
    (analysis_dir / "understanding" / "business" / "review-checklist.md").write_text(
        text, encoding="utf-8"
    )


def _relate(payload: dict[str, Any], object_a: str, object_b: str) -> dict[str, Any]:
    """按排序对取出一条关系记录。"""

    for item in payload["relationships"]:
        if (item["object_a"], item["object_b"]) == tuple(sorted((object_a, object_b))):
            return item

    raise AssertionError(f"missing relationship: {object_a} ↔ {object_b}")


def _assoc(
    payload: dict[str, Any],
    obj: str,
    table_key: str,
) -> dict[str, Any]:
    """取出 (object, table_key) 的 association 记录。"""

    for item in payload["associations"]:
        if item["object"] == obj and item["table_key"] == table_key:
            return item

    raise AssertionError(f"missing association: {obj} × {table_key}")


def _relationship_fixture(tmp_path: Path) -> Path:
    """三种关系证据 + 强弱分明的默认 fixture（写完 M2 / M3 / M3.1 后先跑一次 M3.2）。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[
            _table(9001, "proj", "cust_order", comment="客户订单"),
            _table(9001, "proj", "order_line", comment="订单"),
            _table(9001, "proj", "crm_base", comment="客户"),
            _table(9001, "proj", "store_order", comment="门店订单"),
            _table(9001, "proj", "plain_tbl"),
        ],
        columns=[
            _column(9001, "proj", "order_line", "product_name", 0, comment="product"),
        ],
        statements=[
            {
                "workspace_id": 9001,
                "file_id": "1",
                "statement_id": 1,
                "sql": "select c1 from proj.crm_base",
            }
        ],
        references=[
            {
                "workspace_id": 9001,
                "file_id": "1",
                "statement_id": 1,
                "source_tables": ["proj.crm_base"],
                "target_tables": ["proj.order_line"],
            }
        ],
        edges=[
            {
                "workspace_id": 9001,
                "source_table": "proj.crm_base",
                "target_table": "proj.order_line",
                "source_key": "proj.crm_base",
                "target_key": "proj.order_line",
            }
        ],
        candidates=[
            {"table_key": "proj.crm_base", "workspace_id": 9001, "in_inventory": True},
        ],
        assessments=[
            _assessment(9001, "proj", "cust_order", "CDM", "DIM"),
            _assessment(9001, "proj", "order_line", "CDM", "DWD"),
            _assessment(9001, "proj", "crm_base", "CDM", "DIM"),
            _assessment(9001, "proj", "store_order", "CDM", "DWS"),
            _assessment(9001, "proj", "plain_tbl", "CDM", "ODS"),
        ],
    )
    _run(analysis_dir)

    return analysis_dir


def _status_fixture(tmp_path: Path) -> Path:
    """状态规则用的最小 fixture（无 SQL / 血缘，避免额外候选）。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[
            _table(9001, "proj", "order_only", comment="订单"),
            _table(9001, "proj", "cust_pair", comment="客户订单"),
        ],
        columns=[],
    )
    _run(analysis_dir)

    return analysis_dir


# ============================================================
# 1. 输入缺失 / 非法 / 只读
# ============================================================


def test_missing_inputs_raise(tmp_path: Path) -> None:
    """输入全缺 → 明确报错，不回退跑其他阶段，也不写产物。"""

    analysis_dir = tmp_path / "analysis"

    with pytest.raises(BusinessObjectsError, match="产物缺失"):
        run_business_object_analysis(
            analysis_dir=analysis_dir,
            output_dir=analysis_dir / "understanding" / "business",
        )

    assert not (analysis_dir / "understanding" / "business").exists()


def test_missing_single_input_raises(tmp_path: Path) -> None:
    """缺一个输入 → 报错点名该文件。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[_table(9001, "proj", "crm_base", comment="客户")],
        columns=[],
    )
    (analysis_dir / "evidence" / "lineage" / "core-table-candidates.json").unlink()

    with pytest.raises(BusinessObjectsError, match="core-table-candidates.json"):
        run_business_object_analysis(
            analysis_dir=analysis_dir,
            output_dir=analysis_dir / "understanding" / "business",
        )

    assert not (analysis_dir / "understanding" / "business" / "objects-registry.json").exists()


def test_invalid_json_raises(tmp_path: Path) -> None:
    """产物不是合法 JSON → 明确报错，不写 M3.2 产物。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[_table(9001, "proj", "crm_base", comment="客户")],
        columns=[],
    )
    (analysis_dir / "understanding" / "business" / "objects.json").write_text("{", encoding="utf-8")

    with pytest.raises(BusinessObjectsError, match="不是合法的 JSON"):
        run_business_object_analysis(
            analysis_dir=analysis_dir,
            output_dir=analysis_dir / "understanding" / "business",
        )

    assert not (analysis_dir / "understanding" / "business" / "object-graph.md").exists()


def test_inputs_are_read_only(tmp_path: Path) -> None:
    """M2 / M3 / M3.1 产物在 M3.2 运行前后字节一致。"""

    analysis_dir = _relationship_fixture(tmp_path)
    business_dir = analysis_dir / "understanding" / "business"
    before = {path: path.read_bytes() for path in sorted(analysis_dir.rglob("*")) if path.is_file()}

    _run(analysis_dir)

    after = {path: path.read_bytes() for path in sorted(analysis_dir.rglob("*")) if path.is_file()}

    for path, content in before.items():
        assert after[path] == content, path

    # 只新增 OUTPUT_FILES，不覆盖已有产物。
    assert {path.name for path in business_dir.iterdir()} == set(M3_NAMES) | set(M31_NAMES) | set(
        OUTPUT_FILES
    )


# ============================================================
# 2. review-checklist 解析
# ============================================================


def test_parse_review_checklist_rows(tmp_path: Path) -> None:
    """四列解析、分隔行 / 重复表头跳过、名称分隔符与空占位。"""

    text = """\
# Checklist

| table | human domain | human object | status |
| --- | --- | --- | --- |
| proj.a | 客户,销售 | customer、order | confirmed |
| proj.b | - | - | pending |
| table | human domain | human object | status |
| proj.c | 客户 |  | rejected |
"""

    reviews = parse_review_checklist(text, source=tmp_path / "review-checklist.md")

    assert list(reviews) == ["proj.a", "proj.b", "proj.c"]
    assert reviews["proj.a"] == HumanReview(
        table_key="proj.a",
        human_domains=("客户", "销售"),
        human_objects=("customer", "order"),
        status=OBJECT_STATUS_CONFIRMED,
        status_raw="confirmed",
    )
    assert reviews["proj.b"].human_domains == ()
    assert reviews["proj.b"].human_objects == ()
    assert reviews["proj.b"].status is None
    assert reviews["proj.c"].status == OBJECT_STATUS_REJECTED


def test_parse_review_checklist_missing_columns_raises(tmp_path: Path) -> None:
    """缺必需列 → 报错并点名缺失列。"""

    text = """\
| table | human domain |
| --- | --- |
| proj.a | 客户 |
"""

    with pytest.raises(BusinessObjectsError, match="human object"):
        parse_review_checklist(text, source=tmp_path / "review-checklist.md")


def test_parse_review_checklist_duplicate_table_keeps_first(tmp_path: Path) -> None:
    """同一 table 出现多次只保留首行，保证确定性。"""

    text = """\
| table | human domain | human object | status |
| --- | --- | --- | --- |
| proj.a | 客户 | customer | confirmed |
| proj.a | 销售 | order | rejected |
"""

    reviews = parse_review_checklist(text, source=tmp_path / "review-checklist.md")

    assert reviews["proj.a"].status == OBJECT_STATUS_CONFIRMED
    assert reviews["proj.a"].human_objects == ("customer",)


def test_status_value_normalization(tmp_path: Path) -> None:
    """大小写 / 首尾空白归一化；pending / done / 未知值都不是已确认状态。"""

    text = """\
| table | human domain | human object | status |
| --- | --- | --- | --- |
| proj.confirmed | | | ConfIrMed  |
| proj.pending | | | pending |
| proj.done | | | done |
| proj.unknown | | | 未知状态 |
| proj.empty | | |  |
"""

    reviews = parse_review_checklist(text, source=tmp_path / "review-checklist.md")

    assert reviews["proj.confirmed"].status == OBJECT_STATUS_CONFIRMED
    assert reviews["proj.pending"].status is None
    assert reviews["proj.done"].status is None
    assert reviews["proj.unknown"].status is None
    assert reviews["proj.empty"].status is None


# ============================================================
# 3. 状态规则
# ============================================================


def test_default_status_is_candidate(tmp_path: Path) -> None:
    """清单是 M3.1 生成的 pending 版本 → 全部 candidate，未回填 ≠ confirmed。"""

    analysis_dir = _status_fixture(tmp_path)
    result = _run(analysis_dir)
    payload = _read(analysis_dir / "understanding" / "business" / "objects-registry.json")

    assert result.object_count == 4
    assert payload["status_counts"]["candidate"] == 4
    assert payload["status_counts"]["confirmed"] == 0
    assert all(item["status"] == OBJECT_STATUS_CANDIDATE for item in payload["objects"])
    assert {item["object"]: item["table_count"] for item in payload["objects"]} == {
        "customer": 1,
        "order": 2,
        "product": 0,
        "store": 0,
    }
    assert result.association_status_counts[OBJECT_STATUS_CANDIDATE] == 3


def test_confirmed_requires_explicit_human_object(tmp_path: Path) -> None:
    """confirmed 只作用于 human object 显式列出的 Object；只填 domain 不推断。"""

    analysis_dir = _status_fixture(tmp_path)
    _write_checklist(
        analysis_dir,
        _row("proj.order_only", human_domain="销售", status="confirmed"),
        _row("proj.cust_pair", human_domain="客户", status="confirmed"),
    )
    _run(analysis_dir)

    payload = _read(analysis_dir / "understanding" / "business" / "objects-registry.json")

    assert payload["status_counts"]["confirmed"] == 0
    assert payload["status_counts"]["candidate"] == 4

    association = _read(analysis_dir / "understanding" / "business" / "object-tables.json")
    assert association["status_counts"][OBJECT_STATUS_CONFIRMED] == 0
    assert _assoc(association, "order", "proj.order_only")["status"] == (OBJECT_STATUS_CANDIDATE)


def test_confirmed_with_human_object(tmp_path: Path) -> None:
    """列出 Object 才 confirmed；同表其他候选仍是 candidate；全确认后 Object 级 confirmed。"""

    analysis_dir = _status_fixture(tmp_path)
    _write_checklist(
        analysis_dir,
        _row("proj.order_only", human_object="order", status="confirmed"),
        _row("proj.cust_pair", human_object="order", status="confirmed"),
    )
    _run(analysis_dir)

    association = _read(analysis_dir / "understanding" / "business" / "object-tables.json")
    registry = _read(analysis_dir / "understanding" / "business" / "objects-registry.json")

    assert _assoc(association, "order", "proj.order_only")["status"] == (OBJECT_STATUS_CONFIRMED)
    assert _assoc(association, "order", "proj.cust_pair")["status"] == (OBJECT_STATUS_CONFIRMED)
    assert _assoc(association, "customer", "proj.cust_pair")["status"] == (OBJECT_STATUS_CANDIDATE)

    statuses = {item["object"]: item["status"] for item in registry["objects"]}
    assert statuses["order"] == OBJECT_STATUS_CONFIRMED
    assert statuses["customer"] == OBJECT_STATUS_CANDIDATE
    assert registry["status_counts"][OBJECT_STATUS_CONFIRMED] == 1


def test_rejected_covers_all_and_leaves_relationships(tmp_path: Path) -> None:
    """human object 留空的 rejected 作用于该表全部候选，且这些候选不参与关系推导。"""

    analysis_dir = _status_fixture(tmp_path)
    _write_checklist(analysis_dir, _row("proj.cust_pair", status="rejected"))
    _run(analysis_dir)

    association = _read(analysis_dir / "understanding" / "business" / "object-tables.json")
    registry = _read(analysis_dir / "understanding" / "business" / "objects-registry.json")
    relationships = _read(analysis_dir / "understanding" / "business" / "object-relationships.json")

    assert _assoc(association, "customer", "proj.cust_pair")["status"] == (OBJECT_STATUS_REJECTED)
    assert _assoc(association, "order", "proj.cust_pair")["status"] == (OBJECT_STATUS_REJECTED)
    assert association["status_counts"][OBJECT_STATUS_REJECTED] == 2

    statuses = {item["object"]: item["status"] for item in registry["objects"]}
    assert statuses["customer"] == OBJECT_STATUS_REJECTED
    assert statuses["order"] == OBJECT_STATUS_CANDIDATE

    # cust_pair 上的 customer ↔ order 共现被排除，只剩 order_only 的单一 Object。
    assert relationships["count"] == 0


def test_needs_discussion_backfills_new_object(tmp_path: Path) -> None:
    """needs_discussion + 机器候选外的 human object → 新建 association，不经机器分类器。"""

    analysis_dir = _status_fixture(tmp_path)
    _write_checklist(
        analysis_dir,
        _row("proj.cust_pair", human_object="member", status="needs_discussion"),
    )
    _run(analysis_dir)

    association = _read(analysis_dir / "understanding" / "business" / "object-tables.json")
    registry = _read(analysis_dir / "understanding" / "business" / "objects-registry.json")

    extra = _assoc(association, "member", "proj.cust_pair")
    assert extra["status"] == OBJECT_STATUS_NEEDS_DISCUSSION
    assert extra["confidence"] is None
    assert extra["evidence"] == {}
    assert extra["human"]["human_object"] == ["member"]

    assert "member" not in RULES_TEXT
    statuses = {item["object"]: item["status"] for item in registry["objects"]}
    assert statuses["member"] == OBJECT_STATUS_NEEDS_DISCUSSION
    assert registry["status_counts"][OBJECT_STATUS_NEEDS_DISCUSSION] == 1


# ============================================================
# 4. 关系推导
# ============================================================


def test_relationship_merges_three_evidence_sources(tmp_path: Path) -> None:
    """同表 + SQL + 血缘三来源合并成一条记录，evidence 保留三类。"""

    analysis_dir = _relationship_fixture(tmp_path)
    relationships = _read(analysis_dir / "understanding" / "business" / "object-relationships.json")
    pair = _relate(relationships, "customer", "order")

    assert relationships["count"] == 4
    assert pair["evidence_types"] == [
        RELATIONSHIP_EVIDENCE_CO_OCCURRENCE,
        RELATIONSHIP_EVIDENCE_SQL,
        RELATIONSHIP_EVIDENCE_LINEAGE,
    ]
    assert pair["evidence_diversity"] == 3
    assert pair["evidence_strength"] == EVIDENCE_STRENGTH_STRONG
    assert pair["evidence_count"] == {
        RELATIONSHIP_EVIDENCE_CO_OCCURRENCE: 2,
        RELATIONSHIP_EVIDENCE_SQL: 1,
        RELATIONSHIP_EVIDENCE_LINEAGE: 1,
    }
    assert pair["core_related"] is True


def test_relationship_strength_mapping(tmp_path: Path) -> None:
    """证据类型数 → weak / moderate / strong 的确定性映射。"""

    analysis_dir = _relationship_fixture(tmp_path)
    relationships = _read(analysis_dir / "understanding" / "business" / "object-relationships.json")

    assert _relate(relationships, "order", "store")["evidence_strength"] == (EVIDENCE_STRENGTH_WEAK)
    assert _relate(relationships, "order", "store")["evidence_types"] == [
        RELATIONSHIP_EVIDENCE_CO_OCCURRENCE
    ]
    assert _relate(relationships, "customer", "product")["evidence_strength"] == (
        EVIDENCE_STRENGTH_MODERATE
    )
    assert _relate(relationships, "customer", "product")["evidence_types"] == [
        RELATIONSHIP_EVIDENCE_SQL,
        RELATIONSHIP_EVIDENCE_LINEAGE,
    ]
    assert _relate(relationships, "order", "product")["evidence_strength"] == (
        EVIDENCE_STRENGTH_STRONG
    )


def test_relationship_identity_is_sorted_pair(tmp_path: Path) -> None:
    """关系身份是排序对：无自环、无重复、按 (object_a, object_b) 稳定排序。"""

    analysis_dir = _relationship_fixture(tmp_path)
    relationships = _read(analysis_dir / "understanding" / "business" / "object-relationships.json")
    pairs = [(item["object_a"], item["object_b"]) for item in relationships["relationships"]]

    assert pairs == [
        ("customer", "order"),
        ("customer", "product"),
        ("order", "product"),
        ("order", "store"),
    ]
    assert all(a < b for a, b in pairs)
    assert len(set(pairs)) == len(pairs)


def test_relationship_type_always_candidate(tmp_path: Path) -> None:
    """relationship_type 恒为 candidate，不产出 owns / contains / one-to-many。"""

    analysis_dir = _relationship_fixture(tmp_path)
    relationships = _read(analysis_dir / "understanding" / "business" / "object-relationships.json")

    assert {item["relationship_type"] for item in relationships["relationships"]} == {
        RELATIONSHIP_TYPE_CANDIDATE
    }

    body = json.dumps(relationships["relationships"], ensure_ascii=False)
    assert "one-to-many" not in body
    assert "many-to-many" not in body
    assert "belongs_to" not in body


def test_evidence_uses_stable_ids_without_sql_text(tmp_path: Path) -> None:
    """证据条目只引用稳定标识，不复制 SQL 原文。"""

    analysis_dir = _relationship_fixture(tmp_path)
    relationships = _read(analysis_dir / "understanding" / "business" / "object-relationships.json")
    sql_text = "select c1 from proj.crm_base"
    raw = json.dumps(relationships, ensure_ascii=False)

    assert sql_text not in raw
    assert "select" not in raw

    sql_entry = _relate(relationships, "customer", "order")["evidence"][RELATIONSHIP_EVIDENCE_SQL][
        0
    ]
    assert set(sql_entry) == {
        "evidence_id",
        "source_object",
        "target_object",
        "source_table",
        "target_table",
        "workspace_id",
        "file_id",
        "statement_id",
    }
    assert sql_entry["statement_id"] == 1
    assert sql_entry["evidence_id"].startswith("sql:9001:1:1:")


def test_core_related_flag(tmp_path: Path) -> None:
    """core_related 只表达「endpoint 关联核心表候选」。"""

    analysis_dir = _relationship_fixture(tmp_path)
    relationships = _read(analysis_dir / "understanding" / "business" / "object-relationships.json")

    assert _relate(relationships, "customer", "order")["core_related"] is True
    assert _relate(relationships, "customer", "product")["core_related"] is True
    assert _relate(relationships, "order", "store")["core_related"] is False


def test_evidence_distribution_and_statement_count(tmp_path: Path) -> None:
    """三种证据的 entry / relationship 计数与 SQL 语句数。"""

    analysis_dir = _relationship_fixture(tmp_path)
    relationships = _read(analysis_dir / "understanding" / "business" / "object-relationships.json")

    assert relationships["evidence_distribution"] == {
        RELATIONSHIP_EVIDENCE_CO_OCCURRENCE: {
            "entry_count": 4,
            "relationship_count": 3,
        },
        RELATIONSHIP_EVIDENCE_SQL: {"entry_count": 3, "relationship_count": 3},
        RELATIONSHIP_EVIDENCE_LINEAGE: {"entry_count": 3, "relationship_count": 3},
    }
    assert relationships["sql_statement_count"] == 1


def test_association_evidence_grouped_by_business_type(tmp_path: Path) -> None:
    """association 的 evidence 按 M3 的 evidence type 分组，只引用稳定标识。"""

    analysis_dir = _relationship_fixture(tmp_path)
    association = _read(analysis_dir / "understanding" / "business" / "object-tables.json")
    row = _assoc(association, "order", "proj.cust_order")

    assert set(row["evidence"]) >= {"table_comment", "table_name"}
    assert row["evidence"]["table_comment"][0]["type"] == "table_comment"
    assert row["confidence"] is not None
    assert row["candidate_layer"] == "DIM"
    assert row["warehouse_layer"] == "CDM"
    assert row["core_candidate"] is False


# ============================================================
# 5. 产物结构与报告
# ============================================================


def test_output_structure_and_report(tmp_path: Path) -> None:
    """五个产物的顶层结构固定，报告 8 节且措辞只说证据不说业务关系。"""

    analysis_dir = _relationship_fixture(tmp_path)
    result = _run(analysis_dir)
    business_dir = analysis_dir / "understanding" / "business"

    assert result.object_count == 4
    assert result.association_count == 8
    assert result.relationship_count == 4
    assert result.core_relationship_count == 3

    registry = _read(business_dir / "objects-registry.json")
    assert list(registry) == ["count", "note", "status_counts", "objects"]
    assert [item["object"] for item in registry["objects"]] == [
        "customer",
        "order",
        "product",
        "store",
    ]
    assert set(registry["objects"][0]) >= {
        "object",
        "name",
        "table_count",
        "core_table_count",
        "status",
        "status_counts",
        "evidence_summary",
        "tables",
    }

    associations = _read(business_dir / "object-tables.json")
    assert list(associations) == ["count", "note", "status_counts", "associations"]

    matrix = _read(business_dir / "object-evidence-matrix.json")
    assert list(matrix) == ["count", "note", "objects"]
    assert set(matrix["objects"][0]) == {
        "object",
        "table_count",
        "core_table_count",
        "candidate_layers",
        "domains",
        "evidence_types",
        "unknown_table_count",
        "ambiguous_table_count",
        "status_counts",
        "relationship_count",
    }

    report = (business_dir / "object-graph.md").read_text(encoding="utf-8")
    assert report.startswith("# M3.2 Business Object & Relationship Analysis")

    for index in range(1, 9):
        assert f"## {index}." in report

    # 措辞边界：只讲证据，不产生业务关系结论，不推导 Business Process / Grain。
    assert "这不是「存在业务关系」的结论" in report
    assert "存在业务关系：" not in report
    assert "确认存在业务关系" not in report
    assert "table co-occurrence / SQL reference / lineage evidence" in report
    assert "本阶段不做 Business Process、不做 Grain 判断" in report
    assert "co_occurrence" in report
    assert "candidate" in report

    for name in OUTPUT_FILES:
        assert (business_dir / name).exists(), name

    assert _read(business_dir / "objects-registry.json") == result.registry
    assert _read(business_dir / "object-relationships.json") == result.relationships


def test_matrix_reports_unknown_and_ambiguous(tmp_path: Path) -> None:
    """matrix 沿用 M3.1 口径统计 unknown / ambiguous。"""

    analysis_dir = _relationship_fixture(tmp_path)
    result = _run(analysis_dir)
    matrix = {item["object"]: item for item in result.matrix["objects"]}

    assert matrix["store"]["table_count"] == 1
    assert matrix["store"]["relationship_count"] == 1
    assert matrix["customer"]["table_count"] == 2
    assert matrix["customer"]["core_table_count"] == 1
    assert matrix["order"]["relationship_count"] == 3


def test_deterministic_across_runs(tmp_path: Path) -> None:
    """两次运行字节一致（无时间戳 / 随机抽样）。"""

    analysis_dir = _relationship_fixture(tmp_path)
    business_dir = analysis_dir / "understanding" / "business"

    _run(analysis_dir)
    first_run = {
        path.name: path.read_bytes()
        for path in sorted(business_dir.iterdir())
        if path.name in OUTPUT_FILES
    }

    _run(analysis_dir)
    second_run = {
        path.name: path.read_bytes()
        for path in sorted(business_dir.iterdir())
        if path.name in OUTPUT_FILES
    }

    assert first_run == second_run
    assert set(first_run) == set(OUTPUT_FILES)


# ============================================================
# 6. 错误路径（输入读取）
# ============================================================


def test_read_object_inputs_reports_missing_paths(tmp_path: Path) -> None:
    """read_object_inputs 逐个列出缺失的输入相对路径。"""

    analysis_dir = _status_fixture(tmp_path)
    (analysis_dir / "evidence" / "sql" / "statements.json").unlink()

    with pytest.raises(BusinessObjectsError, match="sql/statements.json"):
        read_object_inputs(analysis_dir)


# ============================================================
# 7. CLI 黑盒
# ============================================================


def test_analyze_business_objects_command(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze --stage understanding 产出 5 个对象文件，两次运行字节一致，且不改 M2 输入。"""

    rules_path = _write_rules(tmp_path / "config" / "business-rules.yaml")
    monkeypatch.setenv("BUSINESS_RULES_PATH", str(rules_path))

    _write_m2(
        Path("analysis"),
        tables=[
            _table(9001, "proj", "cust_order", comment="客户订单"),
            _table(9001, "proj", "order_line", comment="订单"),
        ],
        columns=[
            _column(9001, "proj", "order_line", "product_name", 0, comment="product"),
        ],
        edges=[
            {
                "workspace_id": 9001,
                "source_table": "proj.cust_order",
                "target_table": "proj.order_line",
                "source_key": "proj.cust_order",
                "target_key": "proj.order_line",
            }
        ],
    )

    m2_inputs = {path: path.read_bytes() for path in sorted(Path("analysis").rglob("*.json"))}

    assert run_cli("analyze", "--stage", "understanding") == 0

    business_dir = Path("analysis/understanding/business")

    for name in OUTPUT_FILES:
        assert (business_dir / name).exists(), name

    for path, content in m2_inputs.items():
        assert path.read_bytes() == content, path

    first_run = {path: path.read_bytes() for path in sorted(business_dir.iterdir())}

    assert run_cli("analyze", "--stage", "understanding") == 0
    assert {path: path.read_bytes() for path in sorted(business_dir.iterdir())} == first_run


def test_analyze_business_objects_command_fails_without_inputs(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
) -> None:
    """前置产物缺失 → 退出码 1，不写任何对象产物。"""

    assert run_cli("analyze", "--stage", "understanding") == 1
    assert not Path("analysis/understanding/business/objects-registry.json").exists()
    assert not Path("analysis/understanding/business/object-graph.md").exists()

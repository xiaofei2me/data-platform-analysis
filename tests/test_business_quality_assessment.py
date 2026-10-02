"""M3.1 Business Understanding Quality Assessment 的测试。

覆盖任务要求的场景：UNKNOWN 主因级联 / AMBIGUOUS 五类分类与 by_type 口径 /
证据质量与 diversity / confidence 复核 / 核心表优先级与清单分区 /
输出结构与报告 / 确定性与只读 / 缺失与非法输入报错 / CLI 黑盒。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_business_understanding import (
    RULES_TEXT,
    _column,
    _table,
    _write_m2,
    _write_rules,
)

from data_platform_analysis.analysis.business_quality import (
    BusinessQualityError,
    run_business_quality_assessment,
)
from data_platform_analysis.analysis.business_understanding import (
    run_business_understanding,
)
from data_platform_analysis.analysis.models import (
    QUALITY_AMBIGUOUS_CONFLICT,
    QUALITY_AMBIGUOUS_DOMINANT,
    QUALITY_AMBIGUOUS_KEYWORD,
    QUALITY_AMBIGUOUS_MULTI_DOMAIN,
    QUALITY_AMBIGUOUS_UNRESOLVED,
    QUALITY_UNKNOWN_COMMENT,
    QUALITY_UNKNOWN_INSUFFICIENT,
    QUALITY_UNKNOWN_NAMING,
    QUALITY_UNKNOWN_SPARSE,
    QUALITY_UNKNOWN_SQL,
)

# ============================================================
# 测试数据
# ============================================================

CUSTOMER_RULES_TEXT = """\
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
      - member

objects:
  order:
    name: 订单
    keywords:
      - 订单
      - order
"""

OUTPUT_NAMES = (
    "quality-assessment.json",
    "quality-assessment.md",
    "review-checklist.md",
)

M3_NAMES = (
    "terms.json",
    "tables.json",
    "domains.json",
    "objects.json",
    "summary.md",
)


def _prepare(
    tmp_path: Path,
    *,
    rules_text: str = RULES_TEXT,
    **m2: Any,
) -> Path:
    """写出 M2 产物并跑完 M3，返回 analysis 目录。"""

    analysis_dir = tmp_path / "analysis"
    rules_path = _write_rules(tmp_path / "config" / "business-rules.yaml", rules_text)

    _write_m2(analysis_dir, **m2)

    run_business_understanding(
        analysis_dir=analysis_dir,
        rules_path=rules_path,
        output_dir=analysis_dir / "business",
    )

    return analysis_dir


def _quality(analysis_dir: Path) -> Any:
    return run_business_quality_assessment(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload(result: Any) -> dict[str, Any]:
    return result.to_dict()


# ============================================================
# 1. UNKNOWN 主因级联
# ============================================================


def test_unknown_reason_cascade(tmp_path: Path) -> None:
    """五类 UNKNOWN 主因按 注释 → SQL → 命名 → 血缘 → 稀疏 级联判定。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[
            _table(9001, "proj", "cmt_tmp", comment="临时表"),
            _table(9001, "proj", "sql_ref"),
            _table(9001, "proj", "name_gap"),
            _table(9001, "proj", "dwd_id"),
            _table(9001, "proj", "id_dwd"),
        ],
        columns=[],
        references=[
            {
                "workspace_id": 9001,
                "file_id": "1",
                "statement_id": 1,
                "source_tables": [],
                "target_tables": ["proj.sql_ref"],
            }
        ],
        edges=[
            {
                "workspace_id": 9001,
                "source_table": "proj.dwd_id",
                "target_table": "proj.other",
                "source_key": "proj.dwd_id",
                "target_key": "proj.other",
            }
        ],
    )

    payload = _payload(_quality(analysis_dir))

    assert payload["summary"]["unknown_count"] == 5
    assert payload["summary"]["covered_count"] == 0
    assert payload["unknown"]["count"] == 5
    assert payload["unknown"]["by_reason"] == {
        QUALITY_UNKNOWN_COMMENT: 1,
        QUALITY_UNKNOWN_SQL: 1,
        QUALITY_UNKNOWN_NAMING: 1,
        QUALITY_UNKNOWN_INSUFFICIENT: 1,
        QUALITY_UNKNOWN_SPARSE: 1,
    }
    assert payload["unknown"]["by_layer"] == {"(未确定)": 5}

    reasons = {item["table_key"]: item["unknown_reason"] for item in payload["unknown"]["samples"]}
    assert reasons == {
        "proj.cmt_tmp": QUALITY_UNKNOWN_COMMENT,
        "proj.sql_ref": QUALITY_UNKNOWN_SQL,
        "proj.name_gap": QUALITY_UNKNOWN_NAMING,
        "proj.dwd_id": QUALITY_UNKNOWN_INSUFFICIENT,
        "proj.id_dwd": QUALITY_UNKNOWN_SPARSE,
    }

    signals = {item["table_key"]: item["signals"] for item in payload["unknown"]["samples"]}
    assert signals["proj.cmt_tmp"]["has_table_comment"] is True
    assert signals["proj.sql_ref"]["has_sql_reference"] is True
    assert signals["proj.name_gap"]["business_term_count"] > 0
    assert signals["proj.dwd_id"]["has_lineage_edge"] is True
    assert signals["proj.id_dwd"] == {
        "has_table_comment": False,
        "has_column_comment": False,
        "has_sql_reference": False,
        "has_lineage_edge": False,
        "business_term_count": 0,
    }

    top_terms = payload["unknown"]["top_terms"]
    assert top_terms
    assert all(entry["table_count"] >= 1 for entry in top_terms)


def test_unknown_samples_truncate_deterministically(tmp_path: Path) -> None:
    """样本按稳定排序截断到 20 条，count 仍是全量。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[_table(9001, "proj", f"unk{index:02d}") for index in range(25)],
        columns=[],
    )

    payload = _payload(_quality(analysis_dir))
    sample_keys = [item["table_key"] for item in payload["unknown"]["samples"]]

    assert payload["unknown"]["count"] == 25
    assert len(sample_keys) == 20
    assert sample_keys == [f"proj.unk{index:02d}" for index in range(20)]


# ============================================================
# 2. AMBIGUOUS 分类
# ============================================================


def test_ambiguous_reason_classification(tmp_path: Path) -> None:
    """五类 AMBIGUOUS 主因各自命中一次。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[
            _table(9001, "proj", "mix_dir", comment="销售数据"),
            _table(9001, "proj", "dom_dir", comment="销售数据"),
            _table(9001, "proj", "cooc"),
            _table(9001, "proj", "customer_pool", comment="销售数据"),
            _table(9001, "proj", "unres"),
        ],
        columns=[
            _column(9001, "proj", "mix_dir", "sales_amt", 0),
            _column(9001, "proj", "mix_dir", "customer_id", 1, comment="客户编号"),
            _column(9001, "proj", "dom_dir", "sales_amt", 0),
            _column(9001, "proj", "dom_dir", "customer_id", 1),
            _column(9001, "proj", "cooc", "sales_customer", 0),
            _column(9001, "proj", "customer_pool", "sales_amt", 0),
            _column(9001, "proj", "customer_pool", "cid", 1, comment="客户编号"),
            _column(9001, "proj", "unres", "sales_amt", 0),
            _column(9001, "proj", "unres", "customer_id", 1),
        ],
    )

    payload = _payload(_quality(analysis_dir))

    assert payload["ambiguous"]["count"] == 5
    assert payload["ambiguous"]["by_reason"] == {
        QUALITY_AMBIGUOUS_MULTI_DOMAIN: 1,
        QUALITY_AMBIGUOUS_DOMINANT: 1,
        QUALITY_AMBIGUOUS_KEYWORD: 1,
        QUALITY_AMBIGUOUS_CONFLICT: 1,
        QUALITY_AMBIGUOUS_UNRESOLVED: 1,
    }
    assert payload["unknown"]["count"] == 0

    reasons = {
        item["table_key"]: item["ambiguous_reason"] for item in payload["ambiguous"]["samples"]
    }
    assert reasons == {
        "proj.mix_dir": QUALITY_AMBIGUOUS_MULTI_DOMAIN,
        "proj.dom_dir": QUALITY_AMBIGUOUS_DOMINANT,
        "proj.cooc": QUALITY_AMBIGUOUS_KEYWORD,
        "proj.customer_pool": QUALITY_AMBIGUOUS_CONFLICT,
        "proj.unres": QUALITY_AMBIGUOUS_UNRESOLVED,
    }

    for sample in payload["ambiguous"]["samples"]:
        assert sample["unknown_reason"] is None
        assert sample["ambiguous_reason"]
        assert sample["candidate_domains"]


def test_ambiguous_by_type_counts(tmp_path: Path) -> None:
    """by_type 覆盖多 Domain / 多 Object / 两者兼有，count = domain + object − both。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[
            _table(9001, "proj", "dom_only", comment="销售数据"),
            _table(9001, "proj", "obj_only"),
            _table(9001, "proj", "both_case", comment="销售数据"),
        ],
        columns=[
            _column(9001, "proj", "dom_only", "sales_amt", 0),
            _column(9001, "proj", "dom_only", "customer_id", 1, comment="客户编号"),
            _column(9001, "proj", "obj_only", "sales_amt", 0),
            _column(9001, "proj", "obj_only", "order_id", 1),
            _column(9001, "proj", "obj_only", "product_name", 2),
            _column(9001, "proj", "both_case", "sales_amt", 0),
            _column(9001, "proj", "both_case", "customer_id", 1, comment="客户编号"),
            _column(9001, "proj", "both_case", "order_id", 2),
            _column(9001, "proj", "both_case", "product_name", 3),
        ],
    )

    payload = _payload(_quality(analysis_dir))
    by_type = payload["ambiguous"]["by_type"]

    assert payload["ambiguous"]["count"] == 3
    assert by_type == {"domain": 2, "object": 2, "domain_and_object": 1}
    assert by_type["domain"] + by_type["object"] - by_type["domain_and_object"] == 3


# ============================================================
# 3. 证据质量
# ============================================================


def test_evidence_quality_diversity_and_sources(tmp_path: Path) -> None:
    """diversity 分桶、按类型的 entry / source / table 计数、直接证据与重复关键词。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[_table(9001, "proj", "sales_base", comment="销售数据")],
        columns=[_column(9001, "proj", "sales_base", "sales_amt", 0, comment="销售金额")],
    )

    payload = _payload(_quality(analysis_dir))
    evidence_quality = payload["evidence_quality"]

    assert evidence_quality["table_count_with_evidence"] == 1
    assert evidence_quality["direct_only_table_count"] == 1
    assert evidence_quality["repeated_keyword_table_count"] == 1
    assert evidence_quality["by_diversity"] == {"0": 0, "1": 0, "2": 0, "3+": 1}
    assert evidence_quality["candidate_by_diversity"]["domain"] == {
        "0": 0,
        "1": 0,
        "2": 0,
        "3+": 1,
    }

    by_source_type = evidence_quality["by_source_type"]
    assert by_source_type["table_name"] == {
        "entry_count": 1,
        "source_count": 1,
        "table_count": 1,
    }
    assert by_source_type["column_comment"] == {
        "entry_count": 1,
        "source_count": 1,
        "table_count": 1,
    }
    assert by_source_type["sql"] == {"entry_count": 0, "source_count": 0, "table_count": 0}
    assert by_source_type["lineage"] == {
        "entry_count": 0,
        "source_count": 0,
        "table_count": 0,
    }


def test_confidence_review_high_with_sql(tmp_path: Path) -> None:
    """high 候选拆解：命名类 + SQL 三类证据，high_naming_only 为 0。"""

    analysis_dir = _prepare(
        tmp_path,
        rules_text=CUSTOMER_RULES_TEXT,
        tables=[_table(9001, "proj", "crm_base", comment="客户数据")],
        columns=[_column(9001, "proj", "crm_base", "member_id", 0)],
        statements=[
            {
                "workspace_id": 9001,
                "file_id": "1",
                "statement_id": 1,
                "sql": "select customer_id from t",
            }
        ],
        references=[
            {
                "workspace_id": 9001,
                "file_id": "1",
                "statement_id": 1,
                "source_tables": [],
                "target_tables": ["proj.crm_base"],
            }
        ],
    )

    payload = _payload(_quality(analysis_dir))
    review = payload["confidence_review"]

    assert review["domain"]["high"] == 1
    assert review["object"]["high"] == 0
    assert review["combined"]["high"] == 1
    assert review["high_total"] == 1
    assert review["high_diversity"] == {"0": 0, "1": 0, "2": 0, "3+": 1}
    assert review["high_naming_only"] == 0
    assert review["high_with_sql"] == 1
    assert review["high_with_lineage"] == 0
    assert review["high_single_keyword"] == 0
    assert review["high_repeated_keyword"] == 0


# ============================================================
# 4. 核心表复核与清单分区
# ============================================================


def test_core_review_and_checklist_priorities(tmp_path: Path) -> None:
    """核心表优先级：P1 核心+UNKNOWN、P2 核心+AMBIGUOUS、P3 非核心+AMBIGUOUS。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[
            _table(9001, "proj", "core_unk"),
            _table(9001, "proj", "core_amb", comment="销售数据"),
            _table(9001, "proj", "plain_amb", comment="销售数据"),
        ],
        columns=[
            _column(9001, "proj", "core_amb", "sales_amt", 0),
            _column(9001, "proj", "core_amb", "customer_id", 1, comment="客户编号"),
            _column(9001, "proj", "plain_amb", "sales_amt", 0),
            _column(9001, "proj", "plain_amb", "customer_id", 1, comment="客户编号"),
        ],
        candidates=[
            {"table_key": "proj.core_unk", "workspace_id": 9001, "in_inventory": True},
            {"table_key": "proj.core_amb", "workspace_id": 9001, "in_inventory": True},
        ],
    )

    result = _quality(analysis_dir)
    payload = _payload(result)
    core = payload["core_table_review"]

    assert core["core_count"] == 2
    assert core["core_flag_mismatch_count"] == 0
    assert core["core_unknown_count"] == 1
    assert core["core_ambiguous_count"] == 1
    assert core["core_high_count"] == 0
    assert core["core_low_evidence_count"] == 1

    assert [item["table_key"] for item in core["samples"]["core_unknown"]] == ["proj.core_unk"]
    assert [item["table_key"] for item in core["samples"]["core_ambiguous"]] == ["proj.core_amb"]
    assert "core_unknown" in core["samples"]["core_unknown"][0]["reason_tags"]

    rows = result.checklist

    assert [row.priority for row in rows] == [1, 2, 3]
    assert rows[0].table == "proj.core_unk"
    assert rows[0].domain_candidates == "-"
    assert rows[0].note.startswith("unknown:")
    assert rows[0].evidence.startswith("signals:")

    assert rows[1].table == "proj.core_amb"
    assert rows[1].note.startswith("ambiguous:")
    assert rows[1].evidence.startswith("entries=")
    assert "sales(medium)" in rows[1].domain_candidates
    assert "customer(medium)" in rows[1].domain_candidates

    assert rows[2].table == "proj.plain_amb"


def test_core_flag_mismatch_detected(tmp_path: Path) -> None:
    """tables.json 的 core 标记与 core 文件不一致时计数并给出样本。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[
            _table(9001, "proj", "plain_amb", comment="销售数据"),
            _table(9001, "proj", "other_tbl"),
        ],
        columns=[
            _column(9001, "proj", "plain_amb", "sales_amt", 0),
            _column(9001, "proj", "plain_amb", "customer_id", 1, comment="客户编号"),
        ],
    )

    tables_path = analysis_dir / "business" / "tables.json"
    payload = _read(tables_path)

    for item in payload["tables"]:
        if item["table_key"] == "proj.plain_amb":
            item["is_core_candidate"] = True

    tables_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _payload(_quality(analysis_dir))["core_table_review"]

    assert result["core_flag_mismatch_count"] == 1
    assert result["core_count"] == 1
    assert result["samples"]["core_flag_mismatch"] == [
        {
            "table_key": "proj.plain_amb",
            "tables_flag": True,
            "core_file_flag": False,
        }
    ]


# ============================================================
# 5. 输出结构与报告
# ============================================================


def test_output_structure_and_reports(tmp_path: Path) -> None:
    """JSON 固定六个顶层小节、summary 固定键、样本字段齐全、Markdown 分节。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[
            _table(9001, "proj", "core_unk"),
            _table(9001, "proj", "plain_amb", comment="销售数据"),
        ],
        columns=[
            _column(9001, "proj", "plain_amb", "sales_amt", 0),
            _column(9001, "proj", "plain_amb", "customer_id", 1, comment="客户编号"),
        ],
        candidates=[{"table_key": "proj.core_unk", "workspace_id": 9001}],
    )

    result = _quality(analysis_dir)
    payload = _payload(result)
    business_dir = analysis_dir / "business"

    assert list(payload) == [
        "summary",
        "unknown",
        "ambiguous",
        "evidence_quality",
        "confidence_review",
        "core_table_review",
    ]
    assert "checklist" not in payload
    assert list(payload["summary"]) == [
        "table_count",
        "term_count",
        "domain_count",
        "object_count",
        "unknown_count",
        "ambiguous_count",
        "covered_count",
        "core_count",
        "core_unknown_count",
        "core_ambiguous_count",
    ]
    assert payload["summary"]["table_count"] == 2

    sample = payload["unknown"]["samples"][0]
    assert set(sample) == {
        "table_key",
        "workspace_id",
        "project",
        "table",
        "warehouse_layer",
        "candidate_sub_layer",
        "is_core_candidate",
        "candidate_domains",
        "candidate_objects",
        "evidence_summary",
        "unknown_reason",
        "ambiguous_reason",
        "reason_tags",
        "signals",
    }
    assert set(sample["evidence_summary"]) == {
        "entry_count",
        "source_count",
        "diversity",
        "by_source_type",
    }

    written = _read(business_dir / "quality-assessment.json")
    assert written == payload

    report = (business_dir / "quality-assessment.md").read_text(encoding="utf-8")
    assert report.startswith("# M3.1 Business Understanding Quality Assessment")

    for index in range(1, 8):
        assert f"## {index}." in report

    checklist = (business_dir / "review-checklist.md").read_text(encoding="utf-8")
    assert "## Priority 1 — 核心表 + UNKNOWN（共 1 条）" in checklist
    assert "## Priority 2 — 核心表 + AMBIGUOUS（共 0 条）" in checklist
    assert "## Priority 3 — 非核心表 + AMBIGUOUS（共 1 条）" in checklist
    assert "| table | current domain candidates | current object candidates |" in checklist
    assert "| proj.core_unk |" in checklist
    assert "pending" in checklist


# ============================================================
# 6. 确定性与只读
# ============================================================


def test_quality_is_deterministic_and_readonly(tmp_path: Path) -> None:
    """两次运行字节一致，且 M3 / M2 产物一个字节都不变。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[
            _table(9001, "proj", "core_unk"),
            _table(9001, "proj", "plain_amb", comment="销售数据"),
        ],
        columns=[_column(9001, "proj", "plain_amb", "sales_amt", 0)],
        candidates=[{"table_key": "proj.core_unk", "workspace_id": 9001}],
    )

    business_dir = analysis_dir / "business"
    m3_before = {name: (business_dir / name).read_bytes() for name in M3_NAMES}
    m2_before = {
        path: path.read_bytes()
        for path in sorted(analysis_dir.rglob("*.json"))
        if "business" not in path.parts
    }

    _quality(analysis_dir)

    assert {name: (business_dir / name).read_bytes() for name in M3_NAMES} == m3_before
    assert {path: path.read_bytes() for path in m2_before} == m2_before
    assert {path.name for path in business_dir.iterdir()} == set(M3_NAMES) | set(OUTPUT_NAMES)

    first_run = {path.name: path.read_bytes() for path in sorted(business_dir.iterdir())}

    _quality(analysis_dir)

    assert {path.name: path.read_bytes() for path in sorted(business_dir.iterdir())} == first_run


# ============================================================
# 7. 错误路径
# ============================================================


def test_missing_inputs_raise(tmp_path: Path) -> None:
    """输入全缺 → 明确报错，不自动跑 M2 / analyze-business，也不写产物。"""

    analysis_dir = tmp_path / "analysis"

    with pytest.raises(BusinessQualityError, match="产物缺失"):
        run_business_quality_assessment(
            analysis_dir=analysis_dir,
            output_dir=analysis_dir / "business",
        )

    assert not (analysis_dir / "business").exists()


def test_missing_m3_inputs_raise(tmp_path: Path) -> None:
    """只有 M2 产物 → 报错并点名缺失的 business/tables.json。"""

    analysis_dir = tmp_path / "analysis"

    _write_m2(analysis_dir, tables=[_table(9001, "proj", "only_tbl")], columns=[])

    with pytest.raises(BusinessQualityError, match="business/tables.json"):
        run_business_quality_assessment(
            analysis_dir=analysis_dir,
            output_dir=analysis_dir / "business",
        )

    assert not (analysis_dir / "business" / "quality-assessment.json").exists()


def test_invalid_json_raises(tmp_path: Path) -> None:
    """产物不是合法 JSON → 明确报错。"""

    analysis_dir = _prepare(
        tmp_path,
        tables=[_table(9001, "proj", "only_tbl")],
        columns=[],
    )
    (analysis_dir / "business" / "tables.json").write_text("{", encoding="utf-8")

    with pytest.raises(BusinessQualityError, match="不是合法的 JSON"):
        run_business_quality_assessment(
            analysis_dir=analysis_dir,
            output_dir=analysis_dir / "business",
        )


# ============================================================
# 8. CLI 黑盒
# ============================================================


def test_analyze_business_quality_command(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze-business-quality 产出 3 个文件，两次运行字节一致，且不改 M3 产物。"""

    rules_path = _write_rules(tmp_path / "config" / "business-rules.yaml")
    monkeypatch.setenv("BUSINESS_RULES_PATH", str(rules_path))

    _write_m2(
        Path("analysis"),
        tables=[
            _table(9001, "proj", "core_unk"),
            _table(9001, "proj", "plain_amb", comment="销售数据"),
        ],
        columns=[_column(9001, "proj", "plain_amb", "sales_amt", 0)],
        candidates=[{"table_key": "proj.core_unk", "workspace_id": 9001}],
    )

    assert run_cli("analyze-business") == 0

    business_dir = Path("analysis/business")
    m3_before = {path: path.read_bytes() for path in sorted(business_dir.iterdir())}

    assert run_cli("analyze-business-quality") == 0

    for name in OUTPUT_NAMES:
        assert (business_dir / name).exists(), name

    assert {path: path.read_bytes() for path in m3_before} == m3_before

    first_run = {path: path.read_bytes() for path in sorted(business_dir.iterdir())}

    assert run_cli("analyze-business-quality") == 0
    assert {path: path.read_bytes() for path in sorted(business_dir.iterdir())} == first_run


def test_analyze_business_quality_command_fails_without_m3(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """缺 M3 产物 → 退出码 1，不写质量产物。"""

    rules_path = _write_rules(tmp_path / "config" / "business-rules.yaml")
    monkeypatch.setenv("BUSINESS_RULES_PATH", str(rules_path))

    _write_m2(
        Path("analysis"),
        tables=[_table(9001, "proj", "only_tbl")],
        columns=[],
    )

    assert run_cli("analyze-business-quality") == 1
    assert not Path("analysis/business/quality-assessment.json").exists()

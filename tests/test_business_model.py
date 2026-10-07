"""M3.5 Fact / Dimension Candidate Analysis 的测试。

覆盖任务要求的场景：输入缺失 / 非法 / 只读 / Fact Gate / 证据映射 /
候选键与签名确定性 / 角色非层级 / 状态回填 / 产物结构与报告 /
确定性 / CLI 黑盒 / 回归不变更。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_business_grain import _pipeline as _grain_pipeline

from data_platform_analysis.analysis.business.grain import (
    CARRYOVER_CHECKLIST_INPUT_FILE,
    run_business_grain_analysis,
)
from data_platform_analysis.analysis.model.business_model import (
    ARRAY_INPUT_FILES,
    FACT_GATE_REASON_MEASURE,
    FACT_GATE_REASON_PATTERN,
    INPUT_FILES,
    OUTPUT_FILES,
    BusinessModelError,
    ModelIndexes,
    _attributes,
    fact_gate,
    read_model_inputs,
    run_business_model_analysis,
)
from data_platform_analysis.analysis.model.business_model import (
    CARRYOVER_CHECKLIST_INPUT_FILE as MODEL_CARRYOVER_FILE,
)
from data_platform_analysis.analysis.models import (
    DIMENSION_EVIDENCE_ORDER,
    EVIDENCE_STRENGTH_MODERATE,
    EVIDENCE_STRENGTH_STRONG,
    EVIDENCE_STRENGTH_WEAK,
    FACT_EVIDENCE_ORDER,
    GRAIN_PATTERN_AGGREGATION,
    GRAIN_PATTERN_EVENT,
    GRAIN_PATTERN_PERIODIC,
    GRAIN_PATTERN_SNAPSHOT,
    GRAIN_PATTERN_TRANSACTION,
    GRAIN_PATTERN_UNKNOWN,
    GRAIN_ROLE_ORDER,
    MODEL_ATTRIBUTE_LIMIT,
    MODEL_CANDIDATE_NOTE,
    MODEL_CANDIDATE_TYPE_DIMENSION,
    MODEL_CANDIDATE_TYPE_FACT,
    MODEL_CHECKLIST_HEADERS,
    MODEL_CHECKLIST_ROW_LIMIT,
    MODEL_DIMENSION_UNRESOLVED_ORDER,
    MODEL_FACT_UNRESOLVED_ORDER,
    MODEL_PRIORITY_ORDER,
    MODEL_REL_EVIDENCE_ORDER,
    MODEL_REL_UNRESOLVED_ORDER,
    MODEL_REPORT_ROW_LIMIT,
    MODEL_ROLE_DIMENSION,
    MODEL_ROLE_FACT_RELATED_OBJECT,
    MODEL_ROLE_ORDER,
    MODEL_STATUS_CANDIDATE,
    MODEL_STATUS_CONFIRMED,
    MODEL_STATUS_ORDER,
    evidence_strength,
)

# ============================================================
# 测试数据
# ============================================================

MODEL_CARRYOVER_TEMPLATE = """\
# M3.5 Model Review Checklist

| candidate_key | candidate_type | priority | current_status | evidence_strength \
| unresolved_reasons | human_status | human_name | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{rows}
"""


def _pipeline(tmp_path: Path) -> Path:
    """M2 → M3 → M3.1 → M3.2 → M3.3 → M3.4，返回 analysis 目录。"""

    analysis_dir = _grain_pipeline(tmp_path)
    run_business_grain_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )

    return analysis_dir


def _run(analysis_dir: Path) -> Any:
    return run_business_model_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "model",
    )


def _read(analysis_dir: Path, name: str) -> Any:
    return json.loads((analysis_dir / "model" / name).read_text(encoding="utf-8"))


def _facts(analysis_dir: Path) -> list[dict[str, Any]]:
    return _read(analysis_dir, "fact-candidates.json")["candidates"]


def _dimensions(analysis_dir: Path) -> list[dict[str, Any]]:
    return _read(analysis_dir, "dimension-candidates.json")["candidates"]


def _relationships(analysis_dir: Path) -> list[dict[str, Any]]:
    return _read(analysis_dir, "fact-dimension-relationships.json")["relationships"]


def _write_carryover(analysis_dir: Path, *rows: str) -> None:
    """覆盖本阶段清单，用于人工状态回填测试。"""

    text = MODEL_CARRYOVER_TEMPLATE.format(rows="\n".join(rows))
    path = analysis_dir / MODEL_CARRYOVER_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _facts_for_grain(
    rows: list[dict[str, Any]],
    grain_id: str,
) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("grain_candidate_id") == grain_id]


# ============================================================
# 1. 输入缺失 / 非法
# ============================================================


def test_missing_inputs_raise(tmp_path: Path) -> None:
    """必需产物缺失 → 明确报错，并提示先跑前置阶段。"""

    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    with pytest.raises(BusinessModelError, match="产物缺失"):
        read_model_inputs(analysis_dir)


def test_missing_single_input_reports_path(tmp_path: Path) -> None:
    """缺 profiling/columns.json → 报错信息点名该文件。"""

    analysis_dir = _pipeline(tmp_path)
    (analysis_dir / "profiling" / "columns.json").unlink()

    with pytest.raises(BusinessModelError, match="profiling/columns.json"):
        read_model_inputs(analysis_dir)


def test_invalid_json_raises(tmp_path: Path) -> None:
    """产物不是合法 JSON → 报错，不回退、不静默跳过。"""

    analysis_dir = _pipeline(tmp_path)
    (analysis_dir / "lineage" / "table-lineage.json").write_text("{", encoding="utf-8")

    with pytest.raises(BusinessModelError, match="不是合法的 JSON"):
        read_model_inputs(analysis_dir)


def test_array_payload_with_non_object_root_raises(tmp_path: Path) -> None:
    """产物根节点不是对象 → 明确报错。"""

    analysis_dir = _pipeline(tmp_path)
    (analysis_dir / "business" / "grain-candidates.json").write_text("[]", encoding="utf-8")

    with pytest.raises(BusinessModelError, match="根节点不是对象"):
        read_model_inputs(analysis_dir)


def test_grain_with_unknown_process_reference_raises(tmp_path: Path) -> None:
    """grain candidate 引用未知 process candidate → 明确报错。"""

    analysis_dir = _pipeline(tmp_path)
    path = analysis_dir / "business" / "grain-candidates.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidates"][0]["process_candidate_id"] = "process_candidate_999"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(BusinessModelError, match="未知 process candidate"):
        read_model_inputs(analysis_dir)


def test_grain_with_unknown_object_reference_raises(tmp_path: Path) -> None:
    """grain candidate 的 matched_objects 含未知 Object → 明确报错。"""

    analysis_dir = _pipeline(tmp_path)
    path = analysis_dir / "business" / "grain-candidates.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidates"][0]["matched_objects"] = ["unknown_object"]
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(BusinessModelError, match="未知 Object"):
        read_model_inputs(analysis_dir)


def test_carryover_without_required_columns_raises(tmp_path: Path) -> None:
    """本阶段清单存在但缺必需列 → 明确报错。"""

    analysis_dir = _pipeline(tmp_path)
    path = analysis_dir / MODEL_CARRYOVER_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# M3.5 Model Review Checklist\n\n| candidate_key | human_status |\n"
        "| --- | --- |\n| fact_candidate_001 | confirmed |\n",
        encoding="utf-8",
    )

    with pytest.raises(BusinessModelError, match="缺少必需列"):
        _run(analysis_dir)


def test_optional_checklists_are_optional(tmp_path: Path) -> None:
    """三份清单都不存在时也能正常运行（只读、可选）。"""

    analysis_dir = _pipeline(tmp_path)

    for relative in (CARRYOVER_CHECKLIST_INPUT_FILE, MODEL_CARRYOVER_FILE):
        path = analysis_dir / relative
        if path.exists():
            path.unlink()

    result = _run(analysis_dir)

    assert result.fact_count > 0


def test_declared_files_and_output_names(tmp_path: Path) -> None:
    """必需输入 15 个数组型产物，输出固定 8 个文件。"""

    analysis_dir = _pipeline(tmp_path)

    assert len(INPUT_FILES) == 15
    assert len(ARRAY_INPUT_FILES) == 15

    for relative in INPUT_FILES:
        assert (analysis_dir / relative).exists(), relative

    assert len(OUTPUT_FILES) == 8
    assert set(OUTPUT_FILES) == {
        "fact-candidates.json",
        "dimension-candidates.json",
        "fact-dimension-relationships.json",
        "fact-tables.json",
        "dimension-tables.json",
        "model-evidence-matrix.json",
        "model-summary.md",
        "model-review-checklist.md",
    }


def test_inputs_are_read_only(tmp_path: Path) -> None:
    """M2 ~ M3.4 产物在 M3.5 前后字节不变（回归不变更）。"""

    analysis_dir = _pipeline(tmp_path)
    before = {
        path: path.read_bytes()
        for path in sorted(analysis_dir.rglob("*"))
        if path.is_file() and path.name not in OUTPUT_FILES
    }

    _run(analysis_dir)

    after = {
        path: path.read_bytes()
        for path in sorted(analysis_dir.rglob("*"))
        if path.is_file() and path.name not in OUTPUT_FILES
    }

    assert after == before


# ============================================================
# 2. Fact Gate
# ============================================================


def test_fact_gate_direct_patterns() -> None:
    """transaction / event / snapshot 直接通过（不需要度量字段）。"""

    for pattern in (
        GRAIN_PATTERN_TRANSACTION,
        GRAIN_PATTERN_EVENT,
        GRAIN_PATTERN_SNAPSHOT,
    ):
        assert fact_gate({"grain_pattern": pattern}) == (True, None)


def test_fact_gate_requires_measure() -> None:
    """periodic / aggregation / unknown 必须有度量字段才通过。"""

    for pattern in (
        GRAIN_PATTERN_PERIODIC,
        GRAIN_PATTERN_AGGREGATION,
        GRAIN_PATTERN_UNKNOWN,
    ):
        passed, reason = fact_gate({"grain_pattern": pattern, "measure_columns": []})
        assert (passed, reason) == (False, FACT_GATE_REASON_MEASURE)

        passed, reason = fact_gate({"grain_pattern": pattern, "measure_columns": ["amount"]})
        assert (passed, reason) == (True, None)


def test_fact_gate_unknown_pattern() -> None:
    """模式词表之外的形态一律不通过。"""

    assert fact_gate({"grain_pattern": "weird"}) == (
        False,
        FACT_GATE_REASON_PATTERN,
    )


def test_gate_payload_counts_and_zero_reasons_are_omitted(tmp_path: Path) -> None:
    """gate 计数覆盖全部 grain candidate，零计数原因不写入产物。"""

    analysis_dir = _pipeline(tmp_path)
    result = _run(analysis_dir)
    gate = result.fact_candidates["gate"]

    grain_count = len(
        json.loads(
            (analysis_dir / "business" / "grain-candidates.json").read_text(encoding="utf-8")
        )["candidates"]
    )

    assert gate["qualified_count"] + gate["rejected_count"] == grain_count
    assert result.fact_count == gate["qualified_count"]
    assert all(count > 0 for count in gate["rejected_reason_counts"].values())
    assert set(gate["rejected_reason_counts"]) <= {
        FACT_GATE_REASON_MEASURE,
        FACT_GATE_REASON_PATTERN,
    }


# ============================================================
# 3. Fact Candidate
# ============================================================


def test_fact_rows_match_qualified_grains(tmp_path: Path) -> None:
    """fact candidate 只来自通过 Fact Gate 的 grain candidate。"""

    analysis_dir = _pipeline(tmp_path)
    result = _run(analysis_dir)

    qualified: set[str] = set()
    rejected: set[str] = set()

    for grain in read_model_inputs(analysis_dir).grain_candidates:
        grain_id = str(grain.get("grain_candidate_id") or "")
        passed, _reason = fact_gate(grain)
        (qualified if passed else rejected).add(grain_id)

    facts = _facts(analysis_dir)

    assert len(facts) == len(qualified)
    assert {row["grain_candidate_id"] for row in facts} == qualified
    assert rejected.isdisjoint({row["grain_candidate_id"] for row in facts})
    assert result.fact_count == len(qualified)


def test_fact_status_and_modeling_roles(tmp_path: Path) -> None:
    """fact 候选恒为 candidate，角色词表只有 fact_candidate。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    for row in _facts(analysis_dir):
        assert row["status"] == MODEL_STATUS_CANDIDATE
        assert row["human_validated"] is False
        assert row["modeling_roles"] == ["fact_candidate"]
        assert row["role_status"] == "candidate"
        assert row["evidence_strength"] in {
            EVIDENCE_STRENGTH_WEAK,
            EVIDENCE_STRENGTH_MODERATE,
            EVIDENCE_STRENGTH_STRONG,
        }


def test_fact_evidence_vocabulary_and_order(tmp_path: Path) -> None:
    """fact 证据只用 7 类词表，且按固定顺序展示。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    vocabulary = set(FACT_EVIDENCE_ORDER)

    for row in _facts(analysis_dir):
        sources = row["evidence_sources"]
        assert set(sources) <= vocabulary
        assert sources == [source for source in FACT_EVIDENCE_ORDER if source in set(sources)]
        assert set(row["evidence_counts"]) <= vocabulary
        assert all(entry["source_type"] in vocabulary for entry in row["evidence"])


def test_fact_strength_comes_from_evidence_diversity(tmp_path: Path) -> None:
    """strength 只等于证据源类型的数量（1/2/≥3 → weak/moderate/strong）。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    for row in _facts(analysis_dir):
        diversity = len(set(row["evidence_sources"]))
        assert row["evidence_strength"] == evidence_strength(diversity)


def test_fact_unresolved_reasons_follow_fixed_order(tmp_path: Path) -> None:
    """未决原因只用固定词表，且按固定顺序输出。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    vocabulary = set(MODEL_FACT_UNRESOLVED_ORDER)

    for row in _facts(analysis_dir):
        reasons = row["unresolved_reasons"]
        assert set(reasons) <= vocabulary
        assert reasons == [
            reason for reason in MODEL_FACT_UNRESOLVED_ORDER if reason in set(reasons)
        ]


def test_fact_key_and_signature_are_deterministic(tmp_path: Path) -> None:
    """fact_key 稳定编号；canonical_signature 不含随机成分。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    first = [row["fact_key"] for row in _facts(analysis_dir)]

    _run(analysis_dir)
    second = [row["fact_key"] for row in _facts(analysis_dir)]

    assert first == second
    assert first == [f"fact_candidate_{position:03d}" for position in range(1, len(first) + 1)]

    for row in _facts(analysis_dir):
        signature = row["canonical_signature"]
        assert "process=" in signature
        assert "grain=" in signature
        assert "tables=" in signature
        assert signature == row.get("canonical_signature")


def test_fact_row_keeps_anchor_and_supporting_tables(tmp_path: Path) -> None:
    """fact 行保留 M3.4 的 anchor 表与 supporting 表。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    multi = [
        row
        for row in _facts(analysis_dir)
        if len(row["table_keys"]) > 1 and row["supporting_table_count"]
    ]

    assert multi, "fixture 应包含带 supporting 表的 fact candidate"

    for row in multi:
        assert len(row["table_keys"]) == 1 + row["supporting_table_count"]
        assert len(set(row["table_keys"])) == len(row["table_keys"])


# ============================================================
# 4. Dimension Candidate
# ============================================================


def test_one_dimension_per_object(tmp_path: Path) -> None:
    """dimension 按 Object 逐个生成，键稳定编号。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    registry = read_model_inputs(analysis_dir).registry_objects
    dimensions = _dimensions(analysis_dir)

    assert len(dimensions) == len(registry)
    assert {row["object_key"] for row in dimensions} == {
        str(record.get("object")) for record in registry
    }
    assert [row["dimension_key"] for row in dimensions] == [
        f"dimension_candidate_{position:03d}" for position in range(1, len(dimensions) + 1)
    ]
    assert [row["canonical_signature"] for row in dimensions] == [
        f"object={row['object_key']}" for row in dimensions
    ]


def test_dimension_attributes_are_capped() -> None:
    """attributes 截断到固定上限，attribute_count 仍是全量。"""

    indexes = ModelIndexes()
    indexes.assoc_tables_by_object["customer"] = ("proj.t1", "proj.t2")
    names = [f"col_{position:03d}" for position in range(60)]
    indexes.column_names_by_table["proj.t1"] = names
    indexes.column_names_by_table["proj.t2"] = names

    rows, count = _attributes("customer", indexes)

    assert len(rows) == MODEL_ATTRIBUTE_LIMIT
    assert count == 60
    assert rows[0]["table_count"] == 2


def test_dimension_attributes_are_capped_in_output(tmp_path: Path) -> None:
    """输出里的 attributes 不超过上限，attribute_count 不小于列表长度。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    for row in _dimensions(analysis_dir):
        assert len(row["attributes"]) <= MODEL_ATTRIBUTE_LIMIT
        assert row["attribute_count"] >= len(row["attributes"])


def test_dimension_role_status_when_object_in_fact(tmp_path: Path) -> None:
    """Object 出现在 fact 关系里 → role_status=ambiguous，角色可多选。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    fact_objects = {str(obj) for row in _facts(analysis_dir) for obj in row["object_keys"]}

    for row in _dimensions(analysis_dir):
        assert set(row["modeling_roles"]) <= set(MODEL_ROLE_ORDER)
        assert MODEL_ROLE_DIMENSION in row["modeling_roles"]

        if row["object_key"] in fact_objects:
            assert MODEL_ROLE_FACT_RELATED_OBJECT in row["modeling_roles"]
            assert row["role_status"] == "ambiguous"
        else:
            assert row["role_status"] == "candidate"


def test_dimension_evidence_vocabulary_and_unresolved_order(tmp_path: Path) -> None:
    """dimension 证据与未决原因都只用固定词表并按固定顺序。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    evidence_vocabulary = set(DIMENSION_EVIDENCE_ORDER)
    unresolved_vocabulary = set(MODEL_DIMENSION_UNRESOLVED_ORDER)

    for row in _dimensions(analysis_dir):
        sources = row["evidence_sources"]
        assert set(sources) <= evidence_vocabulary
        assert sources == [source for source in DIMENSION_EVIDENCE_ORDER if source in set(sources)]

        reasons = row["unresolved_reasons"]
        assert set(reasons) <= unresolved_vocabulary
        assert reasons == [
            reason for reason in MODEL_DIMENSION_UNRESOLVED_ORDER if reason in set(reasons)
        ]


def test_dimension_table_anchor_excludes_fact_tables(tmp_path: Path) -> None:
    """dimension → table 的 anchor 不能落在 fact candidate 表上。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    fact_tables = {
        str(table_key).casefold() for row in _facts(analysis_dir) for table_key in row["table_keys"]
    }

    rows = _read(analysis_dir, "dimension-tables.json")["tables"]

    assert rows
    assert set(row["role"] for row in rows) <= set(GRAIN_ROLE_ORDER)

    for row in rows:
        if row["role"] == "anchor":
            assert str(row["table_key"]).casefold() not in fact_tables


def test_dimension_keys_are_deterministic(tmp_path: Path) -> None:
    """两次运行的 dimension_key 顺序一致。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    first = [row["dimension_key"] for row in _dimensions(analysis_dir)]

    _run(analysis_dir)
    second = [row["dimension_key"] for row in _dimensions(analysis_dir)]

    assert first == second


# ============================================================
# 5. Fact ↔ Dimension Relationship
# ============================================================


def test_relationship_requires_evidence(tmp_path: Path) -> None:
    """每行至少一类证据；无证据的组合不产出关系候选。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    rows = _relationships(analysis_dir)

    assert rows

    for row in rows:
        assert row["evidence"], row["relationship_key"]
        assert row["evidence_sources"]
        assert row["fact_key"].startswith("fact_candidate_")
        assert row["dimension_key"].startswith("dimension_candidate_")


def test_relationship_evidence_vocabulary(tmp_path: Path) -> None:
    """关系证据只用 5 类词表并按固定顺序。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    vocabulary = set(MODEL_REL_EVIDENCE_ORDER)

    for row in _relationships(analysis_dir):
        sources = row["evidence_sources"]
        assert set(sources) <= vocabulary
        assert sources == [source for source in MODEL_REL_EVIDENCE_ORDER if source in set(sources)]
        assert all(entry["source_type"] in vocabulary for entry in row["evidence"])


def test_relationship_unresolved_reasons_follow_fixed_order(tmp_path: Path) -> None:
    """关系未决原因只用固定词表并按固定顺序。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    vocabulary = set(MODEL_REL_UNRESOLVED_ORDER)

    for row in _relationships(analysis_dir):
        reasons = row["unresolved_reasons"]
        assert set(reasons) <= vocabulary
        assert reasons == [
            reason for reason in MODEL_REL_UNRESOLVED_ORDER if reason in set(reasons)
        ]


def test_relationship_keys_are_deterministic(tmp_path: Path) -> None:
    """关系键由 fact / dimension 组合稳定生成，两次运行一致。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    first = [row["relationship_key"] for row in _relationships(analysis_dir)]

    _run(analysis_dir)
    second = [row["relationship_key"] for row in _relationships(analysis_dir)]

    assert first == second
    assert first == [
        f"fact_dimension_relationship_{position:03d}" for position in range(1, len(first) + 1)
    ]

    for row in _relationships(analysis_dir):
        assert row["canonical_signature"] == (
            f"fact={row['fact_key']}|dimension={row['dimension_key']}"
        )


# ============================================================
# 6. 人工状态回填
# ============================================================


def test_machine_status_is_candidate_without_carryover(tmp_path: Path) -> None:
    """无人工回填时，全部候选 status 恒为 candidate。"""

    analysis_dir = _pipeline(tmp_path)
    result = _run(analysis_dir)

    assert set(result.status_counts) == set(MODEL_STATUS_ORDER)
    assert result.status_counts[MODEL_STATUS_CANDIDATE] == result.fact_count
    assert result.status_counts[MODEL_STATUS_CONFIRMED] == 0


def test_carryover_confirmed_backfills_status(tmp_path: Path) -> None:
    """清单回填 confirmed → 该候选 status 变 confirmed，其余保持 candidate。"""

    analysis_dir = _pipeline(tmp_path)
    _write_carryover(
        analysis_dir,
        "| fact_candidate_001 | fact | P1 | candidate | strong | - | confirmed | 事实 A | 已确认 |",
    )
    _run(analysis_dir)

    rows = _facts(analysis_dir)
    first = next(row for row in rows if row["fact_key"] == "fact_candidate_001")

    assert first["status"] == MODEL_STATUS_CONFIRMED
    assert first["human_validated"] is True

    for row in rows:
        if row["fact_key"] != "fact_candidate_001":
            assert row["status"] == MODEL_STATUS_CANDIDATE
            assert row["human_validated"] is False


def test_carryover_needs_review_maps_to_needs_discussion(tmp_path: Path) -> None:
    """human_status=needs_review → status=needs_discussion（确定性映射）。"""

    analysis_dir = _pipeline(tmp_path)
    _write_carryover(
        analysis_dir,
        "| dimension_candidate_001 | dimension | P3 | candidate | strong | - "
        "| needs_review | 客户 | 待讨论 |",
    )
    _run(analysis_dir)

    rows = _dimensions(analysis_dir)
    first = next(row for row in rows if row["dimension_key"] == "dimension_candidate_001")

    assert first["status"] == "needs_discussion"
    assert first["human_validated"] is False


def test_carryover_unknown_human_status_keeps_candidate(tmp_path: Path) -> None:
    """human_status 取值不可识别 → 按未回填处理，不报错、不改 status。"""

    analysis_dir = _pipeline(tmp_path)
    _write_carryover(
        analysis_dir,
        "| fact_candidate_001 | fact | P1 | candidate | strong | - | maybe | 事实 A | 备注 |",
    )
    _run(analysis_dir)

    first = next(row for row in _facts(analysis_dir) if row["fact_key"] == "fact_candidate_001")

    assert first["status"] == MODEL_STATUS_CANDIDATE
    assert first["human_validated"] is False


# ============================================================
# 7. 产物结构与报告
# ============================================================


def test_evidence_matrix_rows_and_counts(tmp_path: Path) -> None:
    """evidence matrix 只含 fact 与 dimension 行。"""

    analysis_dir = _pipeline(tmp_path)
    result = _run(analysis_dir)
    rows = result.evidence_matrix["rows"]

    assert len(rows) == result.fact_count + result.dimension_count
    assert {row["candidate_type"] for row in rows} == {
        MODEL_CANDIDATE_TYPE_FACT,
        MODEL_CANDIDATE_TYPE_DIMENSION,
    }

    for row in rows:
        assert row["candidate_key"]
        assert row["status"] in set(MODEL_STATUS_ORDER)
        assert set(row["evidence_sources"]) <= (
            set(FACT_EVIDENCE_ORDER)
            if row["candidate_type"] == MODEL_CANDIDATE_TYPE_FACT
            else set(DIMENSION_EVIDENCE_ORDER)
        )
        assert row["unresolved_count"] >= 0


def test_output_structure_and_payload_counts(tmp_path: Path) -> None:
    """八个产物全部写出，payload 顶层计数与候选行数一致。"""

    analysis_dir = _pipeline(tmp_path)
    result = _run(analysis_dir)

    for name in OUTPUT_FILES:
        assert (analysis_dir / "model" / name).exists(), name

    assert result.fact_candidates["count"] == len(result.fact_candidates["candidates"])
    assert result.dimension_candidates["count"] == len(result.dimension_candidates["candidates"])
    assert result.relationships["count"] == len(result.relationships["relationships"])
    assert MODEL_CANDIDATE_NOTE in result.summary
    assert MODEL_CANDIDATE_NOTE in str(result.fact_candidates["note"])


def test_summary_has_required_sections(tmp_path: Path) -> None:
    """model-summary.md 含八个小节。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    summary = (analysis_dir / "model" / "model-summary.md").read_text(encoding="utf-8")

    for index, title in enumerate(
        (
            "Overview",
            "Fact Candidates",
            "Dimension Candidates",
            "Fact ↔ Dimension Relationships",
            "Evidence Coverage",
            "Evidence Gaps",
            "Human Review",
            "Limitations",
        ),
        start=1,
    ):
        assert f"## {index}. {title}" in summary

    assert "DWD / DWS" in summary
    assert "candidate ≠ confirmed" in summary


def test_summary_tables_are_truncated_with_note(tmp_path: Path) -> None:
    """明细表按固定上限截断并注明总数。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    summary = (analysis_dir / "model" / "model-summary.md").read_text(encoding="utf-8")

    fact_count = len(_facts(analysis_dir))

    if fact_count > MODEL_REPORT_ROW_LIMIT:
        assert f"只列出前 {MODEL_REPORT_ROW_LIMIT} 条，共 {fact_count} 条" in summary
    else:
        assert "完整明细见 `analysis/model/fact-candidates.json`" in summary


def test_checklist_sections_follow_priority_order_and_row_limit(
    tmp_path: Path,
) -> None:
    """清单按 P1 → P4 分区，每区行数不超过固定上限。"""

    analysis_dir = _pipeline(tmp_path)
    result = _run(analysis_dir)
    checklist = (analysis_dir / "model" / "model-review-checklist.md").read_text(
        encoding="utf-8"
    )

    positions = [checklist.index(f"## {priority}") for priority in MODEL_PRIORITY_ORDER]
    assert positions == sorted(positions)

    header = "| " + " | ".join(MODEL_CHECKLIST_HEADERS) + " |"
    assert header in checklist

    section_rows = {priority: 0 for priority in MODEL_PRIORITY_ORDER}

    for row in result.checklist_rows:
        section_rows[row.priority] += 1
        assert row.candidate_type in {
            MODEL_CANDIDATE_TYPE_FACT,
            MODEL_CANDIDATE_TYPE_DIMENSION,
            "fact_dimension_relationship",
        }
        assert row.current_status in set(MODEL_STATUS_ORDER)
        assert len(row.unresolved_reasons) >= 0

    for priority, total in section_rows.items():
        rendered = checklist.count(f"| {priority} |")
        assert rendered == min(total, MODEL_CHECKLIST_ROW_LIMIT)


def test_checklist_defaults_show_pending_for_new_rows(tmp_path: Path) -> None:
    """未回填的清单行 human_status 显示 pending。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    checklist = (analysis_dir / "model" / "model-review-checklist.md").read_text(
        encoding="utf-8"
    )

    rows = [
        line
        for line in checklist.splitlines()
        if line.startswith("| fact_") or line.startswith("| dimension_")
    ]

    assert rows
    assert all(line.split("|")[7].strip() == "pending" for line in rows)


def test_role_vocabulary_is_anchor_supporting_only(tmp_path: Path) -> None:
    """role 只用 anchor / supporting，不出现 DWD / DWS / fact / dimension 命名。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    for name in ("fact-tables.json", "dimension-tables.json"):
        payload = _read(analysis_dir, name)
        roles = {row["role"] for row in payload["tables"]}
        assert roles <= set(GRAIN_ROLE_ORDER), name
        assert set(payload["role_counts"]) <= set(GRAIN_ROLE_ORDER)


# ============================================================
# 8. 确定性与 CLI 黑盒
# ============================================================


def test_deterministic_across_runs(tmp_path: Path) -> None:
    """两次运行字节一致（无时间戳 / UUID / 随机抽样）。"""

    analysis_dir = _pipeline(tmp_path)
    model_dir = analysis_dir / "model"

    _run(analysis_dir)
    first = {name: (model_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)}

    _run(analysis_dir)
    second = {name: (model_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)}

    assert first == second


def test_analyze_business_model_command(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze-business-model 产出 8 个文件，两次运行一致且不改前置产物。"""

    from test_business_grain import _write_profiling  # noqa: PLC0415
    from test_business_objects import _write_m2 as write_m2  # noqa: PLC0415
    from test_business_processes import (  # noqa: PLC0415
        _m2_payloads,
        _write_process_rules,
    )

    rules_path = _write_process_rules(tmp_path / "config" / "process-rules.yaml")
    monkeypatch.setenv("PROCESS_RULES_PATH", str(rules_path))

    write_m2(Path("analysis"), **_m2_payloads())

    assert run_cli("analyze-business") == 0
    assert run_cli("analyze-business-quality") == 0
    assert run_cli("analyze-business-objects") == 0
    assert run_cli("analyze-business-processes") == 0
    _write_profiling(Path("analysis"))
    assert run_cli("analyze-business-grain") == 0

    business_dir = Path("analysis/business")
    model_dir = Path("analysis/model")
    assert not (model_dir / "fact-candidates.json").exists()

    before = {path.name: path.read_bytes() for path in sorted(business_dir.iterdir())}

    assert run_cli("analyze-business-model") == 0

    for name in OUTPUT_FILES:
        assert (model_dir / name).exists(), name
        assert not (business_dir / name).exists(), name

    for name, content in before.items():
        assert (business_dir / name).read_bytes() == content, name

    first = {name: (model_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)}

    assert run_cli("analyze-business-model") == 0
    assert {name: (model_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)} == first


def test_analyze_business_model_command_fails_without_inputs(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """缺前置产物 → 退出码 1，不写任何 M3.5 产物。"""

    assert run_cli("analyze-business-model") == 1

    for name in OUTPUT_FILES:
        assert not Path("analysis/model").joinpath(name).exists(), name


def test_legacy_artifacts_in_business_are_relocated(tmp_path: Path) -> None:
    """旧布局残留在 business/ 的 M3.5 产物在重跑时清理：机器产物删除、清单搬迁。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    model_dir = analysis_dir / "model"
    business_dir = analysis_dir / "business"
    checklist = (model_dir / "model-review-checklist.md").read_bytes()

    # 模拟旧布局：清单与机器产物都残留在 business/。
    (business_dir / "model-review-checklist.md").write_bytes(checklist)
    (business_dir / "fact-candidates.json").write_text("{stale}", encoding="utf-8")
    (model_dir / "model-review-checklist.md").unlink()

    _run(analysis_dir)

    assert not (business_dir / "model-review-checklist.md").exists()
    assert not (business_dir / "fact-candidates.json").exists()
    assert (model_dir / "model-review-checklist.md").exists()
    assert (model_dir / "fact-candidates.json").exists()

"""M3.6 Current-State Model Review 的测试。

覆盖任务要求的场景：输入缺失 / 非法 / 只读 / Fact Gate 复算与强度口径 /
粒度与事实评审 / 维度与关系评审 / 9 类反模式 / current-state 分类 /
产物结构与报告 / 清单分区与回填（含转义竖线）/ 确定性 / CLI 黑盒 /
M3.5 产物回归不变更。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_business_model import _pipeline as _model_pipeline

from data_platform_analysis.analysis.business_grain import _split_markdown_row
from data_platform_analysis.analysis.business_model import (
    run_business_model_analysis,
)
from data_platform_analysis.analysis.model_review import (
    ARRAY_INPUT_FILES,
    CARRYOVER_CHECKLIST_INPUT_FILE,
    INPUT_FILES,
    OUTPUT_FILES,
    WIDE_COLUMN_THRESHOLD,
    CurrentStateModelError,
    read_review_inputs,
    run_current_state_model_analysis,
)
from data_platform_analysis.analysis.models import (
    CURRENT_MODEL_ROLE_AMBIGUOUS,
    CURRENT_MODEL_ROLE_DIMENSION,
    CURRENT_MODEL_ROLE_FACT,
    CURRENT_MODEL_ROLE_ORDER,
    CURRENT_MODEL_ROLE_RESULT,
    CURRENT_MODEL_ROLE_UNKNOWN,
    CURRENT_MODEL_SHAPE_MIXED,
    CURRENT_MODEL_SHAPE_ORDER,
    CURRENT_MODEL_SHAPE_TRANSACTION,
    FINDING_TYPE_AGGREGATE_FACT,
    FINDING_TYPE_DIMENSION_OBJECT_DERIVED,
    FINDING_TYPE_DUPLICATE_FACT,
    FINDING_TYPE_EVIDENCE_STRENGTH,
    FINDING_TYPE_FACT_GATE_NO_MEASURE,
    FINDING_TYPE_FACT_GATE_PATTERN,
    FINDING_TYPE_FACT_WITHOUT_MEASURE,
    FINDING_TYPE_GRAIN_CONFLICT,
    FINDING_TYPE_MIXED_GRAIN,
    FINDING_TYPE_MULTI_PROCESS_TABLE,
    FINDING_TYPE_OVERLAPPING_FACT,
    FINDING_TYPE_PROCESS_MULTIPLE_GRAINS,
    FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE,
    FINDING_TYPE_RELATIONSHIP_TECHNICAL,
    FINDING_TYPE_RESULT_TABLE,
    FINDING_TYPE_ROLE_AMBIGUOUS,
    FINDING_TYPE_SNAPSHOT_PERIODIC,
    FINDING_TYPE_WIDE_ANALYTICAL_TABLE,
    MODEL_STATUS_CANDIDATE,
    MODEL_STATUS_CONFIRMED,
    REVIEW_CHECKLIST_HEADERS,
    REVIEW_CHECKLIST_ROW_LIMIT,
    REVIEW_GROUP_ORDER,
    REVIEW_GROUP_TITLE,
    REVIEW_REPORT_ROW_LIMIT,
)

# ============================================================
# 测试数据
# ============================================================

REPO_ROOT = Path(__file__).resolve().parents[1]

CARRYOVER_TEMPLATE = """\
# M3.6 Current-State Review Checklist

| finding_id | finding_type | priority | scope_key | evidence \
| system_interpretation | human_question | human_status | human_name | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{rows}
"""


def _pipeline(tmp_path: Path) -> Path:
    """M2 → M3.4 → M3.5 → M3.6，返回 analysis 目录。"""

    analysis_dir = _model_pipeline(tmp_path)
    run_business_model_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )
    run_current_state_model_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )

    return analysis_dir


def _pre_model_pipeline(tmp_path: Path) -> Path:
    """M2 → M3.4 → M3.5（不含 M3.6），用于验证 M3.6 不改写 M3.5 产物。"""

    analysis_dir = _model_pipeline(tmp_path)
    run_business_model_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )

    return analysis_dir


def _run(analysis_dir: Path) -> Any:
    return run_current_state_model_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )


def _read(analysis_dir: Path, name: str) -> Any:
    """读取产物（读前确保已跑过一次，测试里可以省掉显式 _run）。"""

    _run(analysis_dir)

    return json.loads((analysis_dir / "business" / name).read_text(encoding="utf-8"))


def _findings(analysis_dir: Path) -> list[dict[str, Any]]:
    return _read(analysis_dir, "model-review-findings.json")["findings"]


def _count(findings: list[dict[str, Any]], finding_type: str) -> int:
    return sum(1 for row in findings if row["finding_type"] == finding_type)


def _table_rows(analysis_dir: Path) -> dict[str, dict[str, Any]]:
    rows = _read(analysis_dir, "current-state-model-tables.json")["tables"]
    return {row["table_key"]: row for row in rows}


# ------------------------------------------------------------
# 合成 M3.5 产物（反模式与分类测试用）
# ------------------------------------------------------------


def _table(table_key: str, *, is_view: bool = False) -> dict[str, Any]:
    project, name = table_key.split(".", 1)

    return {
        "workspace_id": 1,
        "workspace_name": "ws",
        "project": project,
        "schema": "",
        "table": name,
        "comment": None,
        "column_count": 1,
        "partition_count": 0,
        "size": 1,
        "is_virtual_view": is_view,
        "lifecycle": -1,
        "table_key": table_key,
    }


def _column(table_key: str, name: str, ordinal: int) -> dict[str, Any]:
    project, table = table_key.split(".", 1)

    return {
        "workspace_id": 1,
        "project": project,
        "schema": "",
        "table": table,
        "ordinal": ordinal,
        "column_name": name,
        "data_type": "STRING",
        "comment": None,
        "is_partition": False,
        "table_key": table_key,
    }


def _grain(
    grain_id: str,
    table_key: str,
    pattern: str,
    keys: list[str],
    *,
    process: str = "process_candidate_001",
    measures: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "grain_candidate_id": grain_id,
        "process_candidate_id": process,
        "table_key": table_key,
        "table_name": table_key.split(".", 1)[1],
        "workspace_id": 1,
        "project": table_key.split(".", 1)[0],
        "grain_pattern": pattern,
        "candidate_keys": list(keys),
        "identifier_columns": list(keys),
        "measure_columns": list(measures or []),
        "evidence": [],
    }


def _fact(
    fact_key: str,
    grain_id: str,
    table_key: str,
    pattern: str,
    keys: list[str],
    *,
    process: str = "process_candidate_001",
    measures: list[str] | None = None,
    objects: list[str] | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "fact_key": fact_key,
        "process_candidate_id": process,
        "grain_candidate_id": grain_id,
        "table_key": table_key,
        "table_name": table_key.split(".", 1)[1],
        "workspace_id": 1,
        "project": table_key.split(".", 1)[0],
        "grain_pattern": pattern,
        "candidate_keys": list(keys),
        "identifier_columns": list(keys),
        "time_attributes": [],
        "measures": list(measures or []),
        "object_keys": list(objects or []),
        "table_keys": [table_key],
        "evidence_sources": list(sources or ["process", "grain", "column"]),
        "evidence_strength": "strong",
        "status": MODEL_STATUS_CANDIDATE,
        "human_validated": False,
        "unresolved_reasons": [],
    }


def _dimension(
    dimension_key: str,
    object_key: str,
    table_keys: list[str],
    *,
    role_status: str = "candidate",
    facts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "dimension_key": dimension_key,
        "object_key": object_key,
        "object_name": object_key,
        "table_keys": list(table_keys),
        "table_count": len(table_keys),
        "role_status": role_status,
        "modeling_roles": ["dimension"],
        "referenced_by_facts": list(facts or []),
        "evidence_strength": "strong",
        "unresolved_reasons": [],
        "status": MODEL_STATUS_CANDIDATE,
        "human_validated": False,
        "attribute_count": 0,
        "attributes": [],
    }


def _relationship(
    relationship_key: str,
    fact_key: str,
    dimension_key: str,
    sources: list[str],
    *,
    shared: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "relationship_key": relationship_key,
        "fact_key": fact_key,
        "dimension_key": dimension_key,
        "object_key": "customer",
        "shared_table_keys": list(shared or []),
        "evidence_strength": "strong" if len(sources) >= 3 else "moderate",
        "evidence_sources": list(sources),
        "status": MODEL_STATUS_CANDIDATE,
        "human_validated": False,
        "unresolved_reasons": [],
    }


def _base_columns() -> list[dict[str, Any]]:
    overlap = [f"c{index}" for index in range(11)]
    wide = [f"w{index:03d}" for index in range(WIDE_COLUMN_THRESHOLD)]

    return [
        *(_column("proj.orders", name, index) for index, name in enumerate(overlap)),
        *(_column("proj.orders_bak", name, index) for index, name in enumerate(overlap)),
        *(_column("proj.wide", name, index) for index, name in enumerate(wide)),
        _column("proj.result", "id", 0),
        _column("proj.sink", "id", 0),
        _column("proj.dim_customer", "customer_id", 0),
        _column("proj.cal", "month", 0),
    ]


def _default_inputs() -> dict[str, list[dict[str, Any]]]:
    """一套覆盖 9 类反模式的合成 M3.5 / M2 产物。"""

    grains = [
        _grain("grain_candidate_001", "proj.orders", "transaction", ["order_id"]),
        _grain(
            "grain_candidate_002",
            "proj.orders",
            "periodic",
            ["ds"],
            measures=["amount"],
        ),
        _grain("grain_candidate_003", "proj.orders_bak", "transaction", ["order_id"]),
        _grain("grain_candidate_004", "proj.wide", "transaction", ["id"]),
        _grain("grain_candidate_005", "proj.result", "transaction", ["id"]),
        _grain(
            "grain_candidate_006",
            "proj.orders",
            "snapshot",
            ["ds"],
            measures=["amount"],
        ),
        _grain(
            "grain_candidate_007",
            "proj.wide",
            "aggregation",
            ["ds"],
            process="process_candidate_002",
            measures=["amount"],
        ),
        # 无度量 → Fact Gate 按 no_measure_evidence 排除。
        _grain("grain_candidate_008", "proj.cal", "periodic", ["month"]),
        # 形态不在词表 → Fact Gate 按 pattern_not_in_vocabulary 排除。
        _grain("grain_candidate_009", "proj.cal", "mystery", ["month"]),
        _grain("grain_candidate_010", "proj.sink", "transaction", ["order_id"]),
    ]

    facts = [
        _fact(
            "fact_candidate_001",
            "grain_candidate_001",
            "proj.orders",
            "transaction",
            ["order_id"],
            objects=["customer"],
        ),
        _fact(
            "fact_candidate_002",
            "grain_candidate_002",
            "proj.orders",
            "periodic",
            ["ds"],
            measures=["amount"],
        ),
        _fact(
            "fact_candidate_003",
            "grain_candidate_003",
            "proj.orders_bak",
            "transaction",
            ["order_id"],
            objects=["customer"],
        ),
        _fact(
            "fact_candidate_004",
            "grain_candidate_004",
            "proj.wide",
            "transaction",
            ["id"],
            objects=["customer"],
        ),
        _fact(
            "fact_candidate_005",
            "grain_candidate_005",
            "proj.result",
            "transaction",
            ["id"],
            objects=["order"],
        ),
        _fact(
            "fact_candidate_006",
            "grain_candidate_006",
            "proj.orders",
            "snapshot",
            ["ds"],
            measures=["amount"],
        ),
        _fact(
            "fact_candidate_007",
            "grain_candidate_007",
            "proj.wide",
            "aggregation",
            ["ds"],
            process="process_candidate_002",
            measures=["amount"],
            objects=["order"],
        ),
        _fact(
            "fact_candidate_008",
            "grain_candidate_010",
            "proj.sink",
            "transaction",
            ["order_id"],
            objects=["order"],
        ),
    ]

    dimensions = [
        _dimension(
            "dimension_candidate_001",
            "customer",
            ["proj.dim_customer", "proj.cal"],
            facts=["fact_candidate_001"],
        ),
        _dimension(
            "dimension_candidate_002",
            "order",
            ["proj.orders"],
            role_status="ambiguous",
            facts=["fact_candidate_001"],
        ),
    ]

    relationships = [
        _relationship(
            "relationship_001",
            "fact_candidate_001",
            "dimension_candidate_001",
            ["sql_reference"],
        ),
        _relationship(
            "relationship_002",
            "fact_candidate_002",
            "dimension_candidate_002",
            ["object_relationship"],
            shared=["proj.orders"],
        ),
    ]

    fact_tables: list[dict[str, Any]] = [
        {
            "fact_key": row["fact_key"],
            "table_key": row["table_key"],
            "role": "anchor",
            "status": MODEL_STATUS_CANDIDATE,
        }
        for row in facts
    ]
    fact_tables.append(
        {
            "fact_key": "fact_candidate_001",
            "table_key": "proj.cal",
            "role": "supporting",
            "status": MODEL_STATUS_CANDIDATE,
        }
    )

    dimension_tables = [
        {
            "dimension_key": "dimension_candidate_001",
            "object_key": "customer",
            "table_key": "proj.dim_customer",
            "role": "anchor",
            "status": MODEL_STATUS_CANDIDATE,
        },
        {
            "dimension_key": "dimension_candidate_001",
            "object_key": "customer",
            "table_key": "proj.cal",
            "role": "supporting",
            "status": MODEL_STATUS_CANDIDATE,
        },
        {
            "dimension_key": "dimension_candidate_002",
            "object_key": "order",
            "table_key": "proj.orders",
            "role": "anchor",
            "status": MODEL_STATUS_CANDIDATE,
        },
    ]

    return {
        "fact_candidates": facts,
        "dimension_candidates": dimensions,
        "relationships": relationships,
        "fact_tables": fact_tables,
        "dimension_tables": dimension_tables,
        "grain_candidates": grains,
        "processes": [
            {"process_key": "process_candidate_001"},
            {"process_key": "process_candidate_002"},
        ],
        "registry_objects": [{"object": "customer"}, {"object": "order"}],
        "inventory_tables": [
            _table("proj.orders"),
            _table("proj.orders_bak"),
            _table("proj.wide"),
            _table("proj.result", is_view=True),
            _table("proj.sink"),
            _table("proj.dim_customer"),
            _table("proj.cal"),
        ],
        "columns": _base_columns(),
        "edges": [
            {"source_key": "proj.orders", "target_key": "proj.result"},
            {"source_key": "proj.orders", "target_key": "proj.sink"},
        ],
        "core_candidates": [{"table_key": "proj.orders"}],
        "assessments": [{"table_identifier": "proj.orders", "candidate_layer": "DWD"}],
    }


def _write_inputs(
    analysis_dir: Path,
    *,
    gate: dict[str, Any] | None = None,
    **overrides: list[dict[str, Any]],
) -> Path:
    """写出 M3.6 需要的 13 个输入产物（按属性名覆盖默认值）。"""

    records_by_attr = _default_inputs()
    records_by_attr.update(overrides)

    for relative, key, attr in ARRAY_INPUT_FILES:
        path = analysis_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "count": len(records_by_attr[attr]),
            key: records_by_attr[attr],
        }

        if attr == "fact_candidates" and gate is not None:
            payload["gate"] = gate

        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return analysis_dir


def _write_carryover(analysis_dir: Path, *rows: str) -> None:
    text = CARRYOVER_TEMPLATE.format(rows="\n".join(rows))
    (analysis_dir / CARRYOVER_CHECKLIST_INPUT_FILE).write_text(text, encoding="utf-8")


def _patch_checklist_status(
    analysis_dir: Path,
    finding_id: str,
    *,
    status: str = "confirmed",
    name: str = "tester",
    note: str = "人工确认",
) -> Path:
    """把清单里某一行的人工三列回填（用于回填与确定性测试）。"""

    path = analysis_dir / "business" / "current-state-review-checklist.md"
    lines = path.read_text(encoding="utf-8").splitlines()

    for index, line in enumerate(lines):
        if not line.startswith(f"| {finding_id} "):
            continue

        cells = _split_markdown_row(line)
        cells[7], cells[8], cells[9] = status, name, note
        lines[index] = "| " + " | ".join(cells) + " |"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    raise AssertionError(f"checklist 中缺少 {finding_id} 行")


# ============================================================
# 1. 输入缺失 / 非法 / 只读
# ============================================================


def test_missing_inputs_raise(tmp_path: Path) -> None:
    """必需产物缺失 → 明确报错，并提示先跑前置阶段。"""

    with pytest.raises(CurrentStateModelError) as excinfo:
        read_review_inputs(tmp_path / "analysis")

    message = str(excinfo.value)

    for relative in INPUT_FILES:
        assert relative in message, relative

    assert "analyze-business-model" in message


def test_invalid_json_raises(tmp_path: Path) -> None:
    """输入不是合法 JSON → 报错并带上文件路径。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    path = analysis_dir / "business" / "fact-candidates.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(CurrentStateModelError, match="fact-candidates.json"):
        read_review_inputs(analysis_dir)


def test_non_object_root_raises(tmp_path: Path) -> None:
    """根节点不是对象 → 报错。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    path = analysis_dir / "inventory" / "tables.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(CurrentStateModelError, match="根节点不是对象"):
        read_review_inputs(analysis_dir)


def test_unknown_process_reference_raises(tmp_path: Path) -> None:
    """grain 引用未知 process → 报错，不静默忽略。"""

    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        grain_candidates=[
            _grain("grain_candidate_001", "proj.orders", "transaction", ["order_id"])
        ],
        fact_candidates=[],
        dimension_candidates=[],
        relationships=[],
        fact_tables=[],
        dimension_tables=[],
        processes=[],
    )

    with pytest.raises(CurrentStateModelError, match="未知 process candidate"):
        read_review_inputs(analysis_dir)


def test_duplicate_fact_key_raises(tmp_path: Path) -> None:
    """fact_key 重复 → 报错。"""

    fact = _fact(
        "fact_candidate_001",
        "grain_candidate_001",
        "proj.orders",
        "transaction",
        ["order_id"],
    )
    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        fact_candidates=[fact, dict(fact)],
    )

    with pytest.raises(CurrentStateModelError, match="fact_key 重复"):
        read_review_inputs(analysis_dir)


def test_relationship_unknown_dimension_raises(tmp_path: Path) -> None:
    """relationship 引用未知 dimension → 报错。"""

    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        relationships=[
            _relationship(
                "relationship_001",
                "fact_candidate_001",
                "dimension_candidate_999",
                ["sql_reference"],
            )
        ],
    )

    with pytest.raises(CurrentStateModelError, match="未知 dimension"):
        read_review_inputs(analysis_dir)


def test_carryover_without_required_columns_raises(tmp_path: Path) -> None:
    """清单缺回填列 → 报错。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    (analysis_dir / CARRYOVER_CHECKLIST_INPUT_FILE).write_text(
        "| finding_id |\n| --- |\n| model_finding_0001 |\n",
        encoding="utf-8",
    )

    with pytest.raises(CurrentStateModelError, match="缺少必需列"):
        _run(analysis_dir)


def test_optional_checklist_is_optional(tmp_path: Path) -> None:
    """清单属于可选输入，缺失也能继续。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    inputs = read_review_inputs(analysis_dir)

    assert inputs.carryover_text == ""


def test_declared_files_and_output_names() -> None:
    """输入 / 输出文件名按任务书固定。"""

    assert len(INPUT_FILES) == 13
    assert INPUT_FILES[-1] == "layer/assessments.json"
    assert OUTPUT_FILES == (
        "current-state-model.json",
        "current-state-model-tables.json",
        "model-review-findings.json",
        "current-state-model-summary.md",
        "current-state-review-checklist.md",
    )


def test_inputs_are_read_only(tmp_path: Path) -> None:
    """M3.6 只读上游产物：13 个输入文件字节不变。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    before = {
        relative: (analysis_dir / relative).read_bytes() for relative in INPUT_FILES
    }

    run_current_state_model_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )

    for relative, content in before.items():
        assert (analysis_dir / relative).read_bytes() == content, relative


# ============================================================
# 2. Fact Gate 复算与 Evidence Strength 口径
# ============================================================


def test_gate_counts_rejections_by_reason_and_pattern(tmp_path: Path) -> None:
    """复算 Fact Gate：无度量与词表外形态分别计数、分别产出 finding。"""

    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        gate={"qualified_count": 8, "rejected_count": 2},
    )
    result = _run(analysis_dir)
    gate = result.model["fact_gate_review"]
    findings = _findings(analysis_dir)

    assert gate["qualified_count"] == 8
    assert gate["rejected_count"] == 2
    assert gate["rejected_reason_counts"] == {
        "no_measure_evidence": 1,
        "pattern_not_in_vocabulary": 1,
    }
    assert gate["measure_rejected_by_pattern"] == {"periodic": 1}
    assert gate["matches_m35"] is True
    assert _count(findings, FINDING_TYPE_FACT_GATE_NO_MEASURE) == 1
    assert _count(findings, FINDING_TYPE_FACT_GATE_PATTERN) == 1


def test_gate_no_measure_finding_carries_grain_evidence(tmp_path: Path) -> None:
    """排除 finding 的证据能回溯到具体 grain candidate。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)
    row = next(
        item
        for item in _findings(analysis_dir)
        if item["finding_type"] == FINDING_TYPE_FACT_GATE_NO_MEASURE
    )

    assert row["scope"] == "stage"
    assert row["priority"] == "P0"
    assert row["evidence_sources"] == ["grain"]
    assert any(
        entry["source_id"] == "grain_candidate_008" for entry in row["evidence"]
    )


def test_strength_semantics_finding_is_stage_level(tmp_path: Path) -> None:
    """strength 全为 strong 也要记一条 Evidence Strength ≠ Confidence 的 finding。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    result = _run(analysis_dir)
    findings = _findings(analysis_dir)
    rows = [
        row
        for row in findings
        if row["finding_type"] == FINDING_TYPE_EVIDENCE_STRENGTH
    ]

    assert len(rows) == 1
    assert rows[0]["scope"] == "stage"
    assert rows[0]["review_group"] == "fact_review"
    assert result.model["evidence_strength_review"]["strength_counts"]["strong"] == 8


# ============================================================
# 3. Grain / Fact 评审
# ============================================================


def test_grain_conflict_and_mixed_grain_on_same_table(tmp_path: Path) -> None:
    """同表多组候选键 → grain_conflict；多形态 → mixed_grain 与快照周期歧义。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    findings = _findings(analysis_dir)
    conflicts = [
        row for row in findings if row["finding_type"] == FINDING_TYPE_GRAIN_CONFLICT
    ]

    assert len(conflicts) == 2
    assert {row["scope_key"] for row in conflicts} == {"proj.orders", "proj.wide"}
    assert {row["priority"] for row in conflicts} == {"P0"}
    assert _count(findings, FINDING_TYPE_MIXED_GRAIN) >= 1
    assert _count(findings, FINDING_TYPE_SNAPSHOT_PERIODIC) == 1


def test_fact_without_measure_and_aggregate_fact(tmp_path: Path) -> None:
    """无度量事实候选逐条记录；聚合形态逐表记录。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    findings = _findings(analysis_dir)
    measure_free = [
        row
        for row in findings
        if row["finding_type"] == FINDING_TYPE_FACT_WITHOUT_MEASURE
    ]

    assert {row["scope_key"] for row in measure_free} == {
        "fact_candidate_001",
        "fact_candidate_003",
        "fact_candidate_004",
        "fact_candidate_005",
        "fact_candidate_008",
    }
    assert _count(findings, FINDING_TYPE_AGGREGATE_FACT) == 1


def test_process_multiple_grains_is_informational(tmp_path: Path) -> None:
    """一个 process 多种 grain：P3、human_review_required=False。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    rows = [
        row
        for row in _findings(analysis_dir)
        if row["finding_type"] == FINDING_TYPE_PROCESS_MULTIPLE_GRAINS
    ]

    assert len(rows) == 1
    assert rows[0]["priority"] == "P3"
    assert rows[0]["human_review_required"] is False
    assert rows[0]["scope_key"] == "process_candidate_001"


# ============================================================
# 4. Dimension / Relationship 评审
# ============================================================


def test_dimension_object_mapping_and_role_ambiguity(tmp_path: Path) -> None:
    """dimension = Object 直接映射；ambiguous 角色单独记录。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    findings = _findings(analysis_dir)
    derived = [
        row
        for row in findings
        if row["finding_type"] == FINDING_TYPE_DIMENSION_OBJECT_DERIVED
    ]

    assert len(derived) == 1
    assert derived[0]["priority"] == "P2"
    assert derived[0]["scope"] == "stage"

    ambiguous = [
        row for row in findings if row["finding_type"] == FINDING_TYPE_ROLE_AMBIGUOUS
    ]
    assert len(ambiguous) == 1
    assert ambiguous[0]["scope_key"] == "dimension_candidate_002"
    assert ambiguous[0]["priority"] == "P0"


def test_relationship_technical_only_and_co_occurrence(tmp_path: Path) -> None:
    """只有技术引用 / 只有共现的关系各自记一条 stage 级 finding。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    findings = _findings(analysis_dir)
    review = _read(analysis_dir, "current-state-model.json")["relationship_review"]

    assert _count(findings, FINDING_TYPE_RELATIONSHIP_TECHNICAL) == 1
    assert _count(findings, FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE) == 1
    assert review["technical_only_count"] == 1
    assert review["object_co_occurrence_only_count"] == 1
    assert review["single_evidence_count"] == 2


# ============================================================
# 5. 反模式
# ============================================================


def test_duplicate_and_overlapping_fact(tmp_path: Path) -> None:
    """同逻辑事实落在不同表 → duplicate_fact；字段高度重合 → overlapping_fact。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    findings = _findings(analysis_dir)
    duplicates = [
        row for row in findings if row["finding_type"] == FINDING_TYPE_DUPLICATE_FACT
    ]

    assert len(duplicates) == 1
    assert duplicates[0]["scope"] == "fact_group"
    assert set(duplicates[0]["related_keys"]) >= {
        "proj.orders",
        "proj.orders_bak",
        "fact_candidate_001",
        "fact_candidate_003",
    }

    overlaps = [
        row for row in findings if row["finding_type"] == FINDING_TYPE_OVERLAPPING_FACT
    ]
    assert len(overlaps) == 1
    assert overlaps[0]["scope"] == "table_pair"
    assert overlaps[0]["scope_key"] == "proj.orders|proj.orders_bak"


def test_overlap_thresholds(tmp_path: Path) -> None:
    """字段不重合的表对不产生 overlapping_fact。"""

    columns = [
        *(_column("proj.orders", f"c{index}", index) for index in range(11)),
        *(_column("proj.orders_bak", f"d{index}", index) for index in range(11)),
        *(_column("proj.wide", f"w{index:03d}", index) for index in range(100)),
        _column("proj.result", "id", 0),
        _column("proj.sink", "id", 0),
        _column("proj.dim_customer", "customer_id", 0),
        _column("proj.cal", "month", 0),
    ]
    analysis_dir = _write_inputs(tmp_path / "analysis", columns=columns)
    findings = _findings(analysis_dir)

    assert _count(findings, FINDING_TYPE_OVERLAPPING_FACT) == 0


def test_multi_process_table(tmp_path: Path) -> None:
    """同一张表出现在多个 process candidate → multi_process_table。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    findings = _findings(analysis_dir)
    rows = [
        row
        for row in findings
        if row["finding_type"] == FINDING_TYPE_MULTI_PROCESS_TABLE
    ]

    assert len(rows) == 1
    assert rows[0]["scope_key"] == "proj.wide"
    assert rows[0]["priority"] == "P1"


def test_wide_and_result_table(tmp_path: Path) -> None:
    """宽表与结果表（视图 + 只有入边）各自记录。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    findings = _findings(analysis_dir)
    wide = [
        row
        for row in findings
        if row["finding_type"] == FINDING_TYPE_WIDE_ANALYTICAL_TABLE
    ]
    results = [row for row in findings if row["finding_type"] == FINDING_TYPE_RESULT_TABLE]

    assert {row["scope_key"] for row in wide} == {"proj.wide"}
    assert {row["scope_key"] for row in results} == {"proj.result", "proj.sink"}
    assert wide[0]["priority"] == "P2"


# ============================================================
# 6. Current-state 分类
# ============================================================


def test_every_inventory_table_is_classified(tmp_path: Path) -> None:
    """全部 inventory 表都有 current_role / model_shape，状态恒 candidate。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)
    payload = _read(analysis_dir, "current-state-model-tables.json")
    rows = payload["tables"]

    assert payload["count"] == len(rows) == 7
    assert set(payload["role_counts"]) <= set(CURRENT_MODEL_ROLE_ORDER)
    assert set(payload["shape_counts"]) <= set(CURRENT_MODEL_SHAPE_ORDER)
    assert {row["status"] for row in rows} == {MODEL_STATUS_CANDIDATE}
    assert all(row["current_role"] in CURRENT_MODEL_ROLE_ORDER for row in rows)


def test_role_and_shape_classification(tmp_path: Path) -> None:
    """fact + dimension anchor → 角色歧义；混合形态 → MIXED；未知 → UNKNOWN。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)
    rows = _table_rows(analysis_dir)

    orders = rows["proj.orders"]
    assert orders["current_role"] == CURRENT_MODEL_ROLE_AMBIGUOUS
    assert orders["role_ambiguous"] is True
    assert orders["model_shape"] == CURRENT_MODEL_SHAPE_MIXED

    assert rows["proj.dim_customer"]["current_role"] == CURRENT_MODEL_ROLE_DIMENSION
    assert rows["proj.wide"]["current_role"] == CURRENT_MODEL_ROLE_FACT
    assert rows["proj.result"]["current_roles"] == [
        CURRENT_MODEL_ROLE_FACT,
        CURRENT_MODEL_ROLE_RESULT,
    ]
    assert rows["proj.sink"]["model_shape"] == CURRENT_MODEL_SHAPE_TRANSACTION
    assert rows["proj.cal"]["current_role"] == CURRENT_MODEL_ROLE_UNKNOWN
    assert rows["proj.cal"]["fact_supporting"] is True


def test_findings_are_linked_back_to_tables(tmp_path: Path) -> None:
    """finding_id 回链到对应表行，未涉及的表保持空列表。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)
    findings = _findings(analysis_dir)
    rows = _table_rows(analysis_dir)
    known = {row["finding_id"] for row in findings}

    assert rows["proj.orders"]["finding_ids"]
    assert set(rows["proj.orders"]["finding_ids"]) <= known
    assert rows["proj.dim_customer"]["finding_ids"] == []


# ============================================================
# 7. 产物结构、报告与清单
# ============================================================


def test_output_structure_and_payload_counts(tmp_path: Path) -> None:
    """5 个产物齐全，计数字段互相一致。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    result = _run(analysis_dir)

    for name in OUTPUT_FILES:
        assert (analysis_dir / "business" / name).exists(), name

    model = _read(analysis_dir, "current-state-model.json")
    findings = _read(analysis_dir, "model-review-findings.json")

    assert model["count"] == 7
    assert findings["count"] == result.finding_count == len(findings["findings"])
    assert sum(model["priority_counts"].values()) == findings["count"]
    assert sum(model["finding_type_counts"].values()) == findings["count"]
    assert sum(model["review_group_counts"].values()) == findings["count"]
    assert model["status_counts"] == {
        "candidate": findings["count"],
        "confirmed": 0,
        "rejected": 0,
        "needs_discussion": 0,
    }
    assert model["model_quality"]["grain_conflict"] == 2
    assert model["fact_gate_review"]["matches_m35"] is False


def test_summary_has_six_sections(tmp_path: Path) -> None:
    """summary 覆盖 Scope / Overview / Quality / Findings / Review / M4。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)
    summary = (
        analysis_dir / "business" / "current-state-model-summary.md"
    ).read_text(encoding="utf-8")

    for heading in (
        "## 1. Scope",
        "## 2. Current Model Overview",
        "## 3. Model Quality",
        "## 4. Priority Findings",
        "## 5. Human Review",
        "## 6. M4 Input",
    ):
        assert heading in summary, heading

    m4_section = summary.split("## 6. M4 Input")[1]
    assert "不能带入 M4 的内容" in m4_section
    assert "evidence_strength=strong" in summary


def test_summary_truncates_findings_table(tmp_path: Path) -> None:
    """summary 明细表超过行数上限时截断并注明总数。"""

    extra = REVIEW_REPORT_ROW_LIMIT + 10
    grains = [
        _grain(f"grain_candidate_{index:03d}", "proj.orders", "transaction", ["order_id"])
        for index in range(1, extra + 1)
    ]
    facts = [
        _fact(
            f"fact_candidate_{index:03d}",
            f"grain_candidate_{index:03d}",
            "proj.orders",
            "transaction",
            ["order_id"],
        )
        for index in range(1, extra + 1)
    ]
    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        grain_candidates=grains,
        fact_candidates=facts,
        fact_tables=[
            {
                "fact_key": row["fact_key"],
                "table_key": row["table_key"],
                "role": "anchor",
                "status": MODEL_STATUS_CANDIDATE,
            }
            for row in facts
        ],
    )
    _run(analysis_dir)
    summary = (
        analysis_dir / "business" / "current-state-model-summary.md"
    ).read_text(encoding="utf-8")
    total = _read(analysis_dir, "model-review-findings.json")["count"]

    assert total > REVIEW_REPORT_ROW_LIMIT
    assert f"只列出前 {REVIEW_REPORT_ROW_LIMIT} 条" in summary
    assert f"共 {total} 条" in summary


def test_checklist_sections_follow_review_groups(tmp_path: Path) -> None:
    """清单按 5 个 review group 分区，列固定且默认 pending。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)
    checklist = (
        analysis_dir / "business" / "current-state-review-checklist.md"
    ).read_text(encoding="utf-8")

    for group in REVIEW_GROUP_ORDER:
        assert f"## {REVIEW_GROUP_TITLE[group]}" in checklist, group

    assert "| " + " | ".join(REVIEW_CHECKLIST_HEADERS) + " |" in checklist

    rows = [
        _split_markdown_row(line)
        for line in checklist.splitlines()
        if line.startswith("| model_finding_")
    ]
    assert rows
    assert all(cells[7] == "pending" for cells in rows)


def test_checklist_row_limit_and_note(tmp_path: Path) -> None:
    """单个分区超过行数上限时截断并给出 JSON 出口。"""

    extra = REVIEW_CHECKLIST_ROW_LIMIT + 5
    grains = [
        _grain(f"grain_candidate_{index:03d}", "proj.orders", "transaction", ["order_id"])
        for index in range(1, extra + 1)
    ]
    facts = [
        _fact(
            f"fact_candidate_{index:03d}",
            f"grain_candidate_{index:03d}",
            "proj.orders",
            "transaction",
            ["order_id"],
        )
        for index in range(1, extra + 1)
    ]
    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        grain_candidates=grains,
        fact_candidates=facts,
        fact_tables=[
            {
                "fact_key": row["fact_key"],
                "table_key": row["table_key"],
                "role": "anchor",
                "status": MODEL_STATUS_CANDIDATE,
            }
            for row in facts
        ],
    )
    _run(analysis_dir)
    checklist = (
        analysis_dir / "business" / "current-state-review-checklist.md"
    ).read_text(encoding="utf-8")

    assert f"只列出前 {REVIEW_CHECKLIST_ROW_LIMIT} 行" in checklist
    assert "model-review-findings.json" in checklist


# ============================================================
# 8. 人工回填
# ============================================================


def test_carryover_confirmed_backfills_status(tmp_path: Path) -> None:
    """回填 confirmed 后 finding 状态变成 confirmed。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)

    _write_carryover(
        analysis_dir,
        "| model_finding_0001 | fact_gate_no_measure | P0 | transaction | grain "
        "| 机器观测 | 问题 | confirmed | tester | 已确认 |",
    )
    _run(analysis_dir)

    row = next(
        item
        for item in _findings(analysis_dir)
        if item["finding_id"] == "model_finding_0001"
    )

    assert row["status"] == MODEL_STATUS_CONFIRMED
    assert row["human_validated"] is True


def test_carryover_survives_escaped_pipe_in_scope_key(tmp_path: Path) -> None:
    """scope_key 含竖线（转义成 `\\|`）时回填不串列（回归测试）。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)

    duplicate = next(
        row
        for row in _findings(analysis_dir)
        if row["finding_type"] == FINDING_TYPE_DUPLICATE_FACT
    )
    assert "|" in duplicate["scope_key"]

    _patch_checklist_status(analysis_dir, duplicate["finding_id"])
    _run(analysis_dir)

    row = next(
        item
        for item in _findings(analysis_dir)
        if item["finding_id"] == duplicate["finding_id"]
    )
    path = analysis_dir / "business" / "current-state-review-checklist.md"
    kept = [
        _split_markdown_row(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith(f"| {duplicate['finding_id']} ")
    ]

    assert row["status"] == MODEL_STATUS_CONFIRMED
    assert row["human_validated"] is True
    assert len(kept) == 1
    assert kept[0][7] == "confirmed"
    assert kept[0][8] == "tester"
    assert kept[0][9] == "人工确认"


# ============================================================
# 9. 确定性与 CLI 黑盒
# ============================================================


def test_deterministic_across_runs(tmp_path: Path) -> None:
    """两次运行字节一致（第二次带清单回填输入，验证幂等）。"""

    analysis_dir = _pre_model_pipeline(tmp_path)
    business_dir = analysis_dir / "business"
    names = sorted(OUTPUT_FILES)

    _run(analysis_dir)
    first = {name: (business_dir / name).read_bytes() for name in names}

    _run(analysis_dir)
    second = {name: (business_dir / name).read_bytes() for name in names}

    assert first == second


def test_pipeline_run_keeps_m35_outputs(tmp_path: Path) -> None:
    """M3.6 不改写 M3.5 的 8 个产物。"""

    from data_platform_analysis.analysis.business_model import (  # noqa: PLC0415
        OUTPUT_FILES as MODEL_OUTPUT_FILES,
    )

    analysis_dir = _pre_model_pipeline(tmp_path)
    business_dir = analysis_dir / "business"
    before = {name: (business_dir / name).read_bytes() for name in MODEL_OUTPUT_FILES}

    _run(analysis_dir)

    for name, content in before.items():
        assert (business_dir / name).read_bytes() == content, name


def test_analyze_current_state_model_command(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze-current-state-model 产出 5 个文件，两次运行一致且不改上游。"""

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
    assert run_cli("analyze-business-model") == 0

    business_dir = Path("analysis/business")
    before = {path.name: path.read_bytes() for path in sorted(business_dir.iterdir())}

    assert run_cli("analyze-current-state-model") == 0

    for name in OUTPUT_FILES:
        assert (business_dir / name).exists(), name

    for name, content in before.items():
        assert (business_dir / name).read_bytes() == content, name

    first = {name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)}

    assert run_cli("analyze-current-state-model") == 0
    assert {name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)} == first


def test_analyze_current_state_model_command_fails_without_inputs(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """缺前置产物 → 退出码 1，不写任何 M3.6 产物。"""

    assert run_cli("analyze-current-state-model") == 1

    for name in OUTPUT_FILES:
        assert not Path("analysis/business").joinpath(name).exists(), name


def test_module_entry_point_exists() -> None:
    """支持 `python -m data_platform_analysis.cli` 的入口。"""

    source = (REPO_ROOT / "src" / "data_platform_analysis" / "cli.py").read_text(
        encoding="utf-8"
    )

    assert 'if __name__ == "__main__":' in source
    assert "analyze-current-state-model" in source
    assert "run_analyze_current_state_model" in source

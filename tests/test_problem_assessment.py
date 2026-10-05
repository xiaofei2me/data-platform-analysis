"""M3.6 v2 Current-State Problem Assessment 测试（spec §29）。

覆盖：Finding → Problem 聚合边界、13 类 taxonomy、四种 status 与人工回填、
Evidence First（证据 ≥1 且可追溯）、四分类 overlap / duplication、
四个新产物、两跑确定性，以及「不改写已有 5 个 M3.6 产物与 13 个输入」。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from test_model_review import (  # 复用 M3.6 v1 合成输入夹具
    _column,
    _fact,
    _grain,
    _run,
    _table,
    _write_inputs,
)

from data_platform_analysis.analysis import problem_assessment as problem_module
from data_platform_analysis.analysis.model_review import (
    INPUT_FILES,
    build_current_state_model,
    read_review_inputs,
)
from data_platform_analysis.analysis.model_review import (
    OUTPUT_FILES as REVIEW_OUTPUT_FILES,
)
from data_platform_analysis.analysis.models import (
    GRAIN_ASSESSMENT_CONFIRMED_CONFLICT,
    GRAIN_ASSESSMENT_POSSIBLE_CONFLICT,
    GRAIN_ASSESSMENT_REVIEW_REQUIRED,
    MODEL_STATUS_CANDIDATE,
    OVERLAP_CLASS_DIVERGENT_STRUCTURE,
    OVERLAP_CLASS_STRUCTURAL,
    OVERLAP_CLASS_TECHNICAL_COPY,
    PROBLEM_CHECKLIST_HEADERS,
    PROBLEM_EVIDENCE_ROW_LIMIT,
    PROBLEM_OUTPUT_FILES,
    PROBLEM_STATUS_CANDIDATE,
    PROBLEM_STATUS_CONFIRMED,
    PROBLEM_STATUS_REJECTED,
    PROBLEM_STATUS_REVIEW_REQUIRED,
    PROBLEM_SUMMARY_ROW_LIMIT,
    PROBLEM_TYPE_COVERAGE_GAP,
    PROBLEM_TYPE_DUPLICATION,
    PROBLEM_TYPE_GRAIN,
    PROBLEM_TYPE_MIXED_RESPONSIBILITY,
    PROBLEM_TYPE_ORDER,
    PROBLEM_TYPE_OVERLAP,
    PROBLEM_TYPE_PROCESS_ALIGNMENT,
    PROBLEM_TYPE_SELECTION_AMBIGUITY,
    PROBLEM_TYPE_TITLE,
    PROBLEM_TYPE_UNKNOWN_MODEL,
    UNKNOWN_REASON_NO_ANCHOR,
    UNKNOWN_REASON_NO_EVIDENCE,
)
from data_platform_analysis.analysis.problem_assessment import (
    build_current_state_problems,
    read_problem_carry_over,
    write_current_state_problems,
)
from data_platform_analysis.analysis.reports import (
    render_current_state_problem_review_checklist,
)

PROBLEMS_FILE = PROBLEM_OUTPUT_FILES[0]
EVIDENCE_FILE = PROBLEM_OUTPUT_FILES[1]
SUMMARY_FILE = PROBLEM_OUTPUT_FILES[2]
CHECKLIST_FILE = PROBLEM_OUTPUT_FILES[3]

MACHINE_STATUSES = {PROBLEM_STATUS_CANDIDATE, PROBLEM_STATUS_REVIEW_REQUIRED}


# ------------------------------------------------------------
# 夹具与工具
# ------------------------------------------------------------


def _result(analysis_dir: Path) -> Any:
    result = _run(analysis_dir)

    assert result.problem is not None

    return result.problem


def _payload(analysis_dir: Path, name: str) -> Any:
    return json.loads((analysis_dir / "business" / name).read_text(encoding="utf-8"))


def _problems(analysis_dir: Path) -> list[dict[str, Any]]:
    return _result(analysis_dir).problems["problems"]


def _of_type(rows: list[dict[str, Any]], problem_type: str) -> list[dict[str, Any]]:
    return [row for row in rows if row["problem_type"] == problem_type]


def _hash_inputs(analysis_dir: Path) -> str:
    digest = hashlib.sha256()

    for relative in INPUT_FILES:
        digest.update(relative.encode("utf-8"))
        digest.update((analysis_dir / relative).read_bytes())

    return digest.hexdigest()


def _rerun_problem_only(analysis_dir: Path) -> None:
    """只重跑 Problem Assessment（验证它不改写已有 M3.6 五个产物）。"""

    inputs = read_review_inputs(analysis_dir)
    model = build_current_state_model(inputs)
    write_current_state_problems(
        build_current_state_problems(
            inputs,
            model.findings["findings"],
            model.tables["tables"],
            carry_over=read_problem_carry_over(analysis_dir),
        ),
        analysis_dir / "business",
    )


def _patch_problem_status(
    analysis_dir: Path,
    problem_id: str,
    *,
    status: str = "confirmed",
    name: str = "tester",
    note: str = "人工确认",
) -> Path:
    """把问题清单里某一行的人工三列回填（列序同 PROBLEM_CHECKLIST_HEADERS）。"""

    from data_platform_analysis.analysis.business_grain import _split_markdown_row

    path = analysis_dir / "business" / CHECKLIST_FILE
    lines = path.read_text(encoding="utf-8").splitlines()

    for index, line in enumerate(lines):
        if not line.startswith(f"| {problem_id} "):
            continue

        cells = _split_markdown_row(line)
        assert len(cells) == len(PROBLEM_CHECKLIST_HEADERS), cells
        cells[7], cells[8], cells[9] = status, name, note
        lines[index] = "| " + " | ".join(cells) + " |"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    raise AssertionError(f"问题清单中缺少 {problem_id} 行")


def _hier_inputs() -> dict[str, list[dict[str, Any]]]:
    """单表 + 互为子集的两组候选键 → possible_conflict。"""

    table = _table("proj.hier")

    return {
        "inventory_tables": [table],
        "columns": [
            _column("proj.hier", "order_id", 0),
            _column("proj.hier", "ds", 1),
            _column("proj.hier", "amount", 2),
        ],
        "grain_candidates": [
            _grain("grain_candidate_001", "proj.hier", "transaction", ["order_id"]),
            _grain(
                "grain_candidate_002",
                "proj.hier",
                "transaction",
                ["order_id", "ds"],
                measures=["amount"],
            ),
        ],
        "fact_candidates": [
            _fact(
                "fact_candidate_001",
                "grain_candidate_001",
                "proj.hier",
                "transaction",
                ["order_id"],
                objects=["customer"],
            ),
            _fact(
                "fact_candidate_002",
                "grain_candidate_002",
                "proj.hier",
                "transaction",
                ["order_id", "ds"],
                measures=["amount"],
                objects=["customer"],
            ),
        ],
        "fact_tables": [
            {
                "fact_key": "fact_candidate_001",
                "table_key": "proj.hier",
                "role": "anchor",
                "status": MODEL_STATUS_CANDIDATE,
            },
            {
                "fact_key": "fact_candidate_002",
                "table_key": "proj.hier",
                "role": "anchor",
                "status": MODEL_STATUS_CANDIDATE,
            },
        ],
        "dimension_candidates": [],
        "relationships": [],
        "dimension_tables": [],
        "processes": [{"process_key": "process_candidate_001"}],
        "edges": [],
        "core_candidates": [],
        "assessments": [],
    }


def _overlap_inputs(*, cross_layer: bool) -> dict[str, list[dict[str, Any]]]:
    """两张字段重合 ≥0.5、候选键不同的表 → MODEL_OVERLAP。"""

    left_columns = [f"c{index}" for index in range(11)]
    right_columns = [*left_columns[:8], "b0", "b1", "b2"]

    return {
        "inventory_tables": [_table("proj.dup_a"), _table("proj.dup_b")],
        "columns": [
            *(
                _column("proj.dup_a", name, index)
                for index, name in enumerate(left_columns)
            ),
            *(
                _column("proj.dup_b", name, index)
                for index, name in enumerate(right_columns)
            ),
        ],
        "grain_candidates": [
            _grain("grain_candidate_001", "proj.dup_a", "transaction", ["a_id"]),
            _grain("grain_candidate_002", "proj.dup_b", "transaction", ["b_id"]),
        ],
        "fact_candidates": [
            _fact(
                "fact_candidate_001",
                "grain_candidate_001",
                "proj.dup_a",
                "transaction",
                ["a_id"],
                objects=["customer"],
            ),
            _fact(
                "fact_candidate_002",
                "grain_candidate_002",
                "proj.dup_b",
                "transaction",
                ["b_id"],
                objects=["customer"],
            ),
        ],
        "fact_tables": [
            {
                "fact_key": "fact_candidate_001",
                "table_key": "proj.dup_a",
                "role": "anchor",
                "status": MODEL_STATUS_CANDIDATE,
            },
            {
                "fact_key": "fact_candidate_002",
                "table_key": "proj.dup_b",
                "role": "anchor",
                "status": MODEL_STATUS_CANDIDATE,
            },
        ],
        "dimension_candidates": [],
        "relationships": [],
        "dimension_tables": [],
        "processes": [{"process_key": "process_candidate_001"}],
        "edges": (
            [{"source_key": "proj.dup_a", "target_key": "proj.dup_b"}]
            if cross_layer
            else []
        ),
        "core_candidates": [],
        "assessments": (
            [
                {"table_identifier": "proj.dup_a", "candidate_layer": "DWD"},
                {"table_identifier": "proj.dup_b", "candidate_layer": "DWS"},
            ]
            if cross_layer
            else [
                {"table_identifier": "proj.dup_a", "candidate_layer": "DWD"},
                {"table_identifier": "proj.dup_b", "candidate_layer": "DWD"},
            ]
        ),
    }


def _divergent_inputs() -> dict[str, list[dict[str, Any]]]:
    """同键同形态但字段零重合 → duplicate_fact 且未进连通分量。"""

    left_columns = [f"x{index}" for index in range(12)]
    right_columns = [f"y{index}" for index in range(12)]

    return {
        "inventory_tables": [_table("proj.div_a"), _table("proj.div_b")],
        "columns": [
            *(
                _column("proj.div_a", name, index)
                for index, name in enumerate(left_columns)
            ),
            *(
                _column("proj.div_b", name, index)
                for index, name in enumerate(right_columns)
            ),
        ],
        "grain_candidates": [
            _grain("grain_candidate_001", "proj.div_a", "transaction", ["d_id"]),
            _grain("grain_candidate_002", "proj.div_b", "transaction", ["d_id"]),
        ],
        "fact_candidates": [
            _fact(
                "fact_candidate_001",
                "grain_candidate_001",
                "proj.div_a",
                "transaction",
                ["d_id"],
                objects=["customer"],
            ),
            _fact(
                "fact_candidate_002",
                "grain_candidate_002",
                "proj.div_b",
                "transaction",
                ["d_id"],
                objects=["customer"],
            ),
        ],
        "fact_tables": [
            {
                "fact_key": "fact_candidate_001",
                "table_key": "proj.div_a",
                "role": "anchor",
                "status": MODEL_STATUS_CANDIDATE,
            },
            {
                "fact_key": "fact_candidate_002",
                "table_key": "proj.div_b",
                "role": "anchor",
                "status": MODEL_STATUS_CANDIDATE,
            },
        ],
        "dimension_candidates": [],
        "relationships": [],
        "dimension_tables": [],
        "processes": [{"process_key": "process_candidate_001"}],
        "edges": [],
        "core_candidates": [],
        "assessments": [],
    }


# ============================================================
# 1. 产物与边界
# ============================================================


def test_problem_outputs_written_and_no_stage_beyond_m36_v2(tmp_path: Path) -> None:
    """写出 4 个新产物；除 M3.6 声明产物外不产生任何文件。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    before = {path.name for path in (analysis_dir / "business").iterdir()}

    result = _result(analysis_dir)

    after = {path.name for path in (analysis_dir / "business").iterdir()}

    assert set(REVIEW_OUTPUT_FILES) | set(PROBLEM_OUTPUT_FILES) <= after
    assert after - before == set(REVIEW_OUTPUT_FILES) | set(PROBLEM_OUTPUT_FILES)
    assert not any("m3.7" in name or "target" in name for name in after)
    assert result.problem_count > 0


def test_existing_m36_outputs_and_inputs_untouched(tmp_path: Path) -> None:
    """Problem Assessment 只写 4 个新文件：已有 5 个 M3.6 产物与 13 个输入字节不变。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    inputs_hash = _hash_inputs(analysis_dir)
    _run(analysis_dir)
    business = analysis_dir / "business"
    before = {name: (business / name).read_bytes() for name in REVIEW_OUTPUT_FILES}

    _rerun_problem_only(analysis_dir)

    assert _hash_inputs(analysis_dir) == inputs_hash
    assert {name: (business / name).read_bytes() for name in REVIEW_OUTPUT_FILES} == before


def test_two_runs_are_byte_identical(tmp_path: Path) -> None:
    """两跑 9 个 M3.6 产物字节一致（确定性输出）。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)
    business = analysis_dir / "business"
    names = (*REVIEW_OUTPUT_FILES, *PROBLEM_OUTPUT_FILES)
    first = {name: (business / name).read_bytes() for name in names}

    _run(analysis_dir)

    assert {name: (business / name).read_bytes() for name in names} == first


# ============================================================
# 2. 聚合计数与 Finding 覆盖
# ============================================================


def test_payload_counts_are_self_consistent(tmp_path: Path) -> None:
    """count / 各类计数 / problem_id 格式 / note 保持自洽。"""

    payload = _result(_write_inputs(tmp_path / "analysis")).problems
    rows = payload["problems"]

    assert payload["count"] == len(rows)
    assert sum(payload["problem_type_counts"].values()) == payload["count"]
    assert sum(payload["status_counts"].values()) == payload["count"]
    assert sum(payload["priority_counts"].values()) == payload["count"]
    assert sum(payload["root_cause_counts"].values()) == payload["count"]
    assert sum(payload["impact_counts"].values()) >= payload["count"]
    ids = [row["problem_id"] for row in rows]
    assert len(set(ids)) == len(ids)
    # 编号按 canonical signature 排序产生，展示顺序另行排序。
    assert sorted(ids) == [f"problem_{index:04d}" for index in range(1, len(rows) + 1)]
    assert "Finding Count ≠ Problem Count" in payload["note"]


def test_finding_coverage_accounting(tmp_path: Path) -> None:
    """covered + uncovered == finding_count，uncovered 只允许有解释的类型。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    result = _run(analysis_dir)
    coverage = result.problem.problems["finding_coverage"]

    assert coverage["finding_count"] == result.finding_count
    assert (
        coverage["covered_finding_count"] + coverage["uncovered_finding_count"]
        == coverage["finding_count"]
    )
    # 合成夹具没有「合法聚合事实」，必须 100% 覆盖。
    assert coverage["uncovered_finding_count"] == 0
    assert coverage["uncovered_by_type"] == {}


# ============================================================
# 3. Finding → Problem 聚合边界
# ============================================================


def test_multiple_grain_findings_aggregate_into_one_problem(tmp_path: Path) -> None:
    """多条 finding → 1 个 problem；不同表不误合并。"""

    rows = _problems(_write_inputs(tmp_path / "analysis"))
    grain_rows = _of_type(rows, PROBLEM_TYPE_GRAIN)
    by_table = {row["scope_key"]: row for row in grain_rows}

    assert set(by_table) == {"proj.orders", "proj.wide"}
    orders = by_table["proj.orders"]
    assert orders["classification"] == GRAIN_ASSESSMENT_CONFIRMED_CONFLICT
    assert len(orders["finding_ids"]) >= 3  # grain_conflict + mixed_grain + snapshot
    wide = by_table["proj.wide"]
    # 同一表跨两个 process → 三态里的 review_required。
    assert wide["classification"] == GRAIN_ASSESSMENT_REVIEW_REQUIRED


def test_grain_possible_conflict_when_keys_are_hierarchical(tmp_path: Path) -> None:
    """候选键互为子集 → possible_conflict（不是 confirmed 也不是 review_required）。"""

    analysis_dir = _write_inputs(tmp_path / "analysis", **_hier_inputs())
    grain_rows = _of_type(_problems(analysis_dir), PROBLEM_TYPE_GRAIN)

    assert len(grain_rows) == 1
    assert grain_rows[0]["scope_key"] == "proj.hier"
    assert grain_rows[0]["classification"] == GRAIN_ASSESSMENT_POSSIBLE_CONFLICT
    assert grain_rows[0]["status"] == PROBLEM_STATUS_CANDIDATE


def test_stage_findings_map_to_distinct_stage_problems(tmp_path: Path) -> None:
    """stage 类 finding 1:1 映射成各自 problem，不跨 finding 合并。"""

    rows = _problems(_write_inputs(tmp_path / "analysis"))
    semantic = _of_type(rows, "SEMANTIC_AMBIGUITY")

    assert len(semantic) >= 3
    assert len({row["scope_key"] for row in semantic}) == len(semantic)
    assert all(len(row["finding_ids"]) == 1 for row in semantic)


# ============================================================
# 4. Overlap / Duplication 四分类
# ============================================================


@pytest.mark.parametrize("cross_layer", [False, True])
def test_overlap_classification(tmp_path: Path, cross_layer: bool) -> None:
    """字段重合但无共享 grain 签名 → MODEL_OVERLAP；跨层 + 血缘 → technical_copy。"""

    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        **_overlap_inputs(cross_layer=cross_layer),
    )
    rows = _problems(analysis_dir)
    overlap = _of_type(rows, PROBLEM_TYPE_OVERLAP)

    assert len(overlap) == 1
    assert _of_type(rows, PROBLEM_TYPE_DUPLICATION) == []
    expected = OVERLAP_CLASS_TECHNICAL_COPY if cross_layer else OVERLAP_CLASS_STRUCTURAL
    assert overlap[0]["classification"] == expected
    assert set(overlap[0]["table_keys"]) == {"proj.dup_a", "proj.dup_b"}


def test_duplicate_outside_component_is_structurally_divergent(
    tmp_path: Path,
) -> None:
    """同键同形态但字段零重合 → MODEL_DUPLICATION + 结构分歧分类。"""

    analysis_dir = _write_inputs(tmp_path / "analysis", **_divergent_inputs())
    rows = _problems(analysis_dir)
    duplication = _of_type(rows, PROBLEM_TYPE_DUPLICATION)

    assert len(duplication) == 1
    assert _of_type(rows, PROBLEM_TYPE_OVERLAP) == []
    assert duplication[0]["classification"] == OVERLAP_CLASS_DIVERGENT_STRUCTURE
    assert duplication[0]["status"] == PROBLEM_STATUS_CANDIDATE


# ============================================================
# 5. 职责 / 对齐 / 未知 / 覆盖缺口 / 选择歧义
# ============================================================


def test_mixed_responsibility_only_for_multi_signal_tables(tmp_path: Path) -> None:
    """≥2 职责信号（或自足信号）的表才进 MIXED_RESPONSIBILITY。"""

    rows = _problems(_write_inputs(tmp_path / "analysis"))
    mixed = {row["scope_key"] for row in _of_type(rows, PROBLEM_TYPE_MIXED_RESPONSIBILITY)}

    assert mixed == {"proj.orders", "proj.wide", "proj.result", "proj.sink"}
    assert "proj.dim_customer" not in mixed
    assert "proj.cal" not in mixed


def test_process_alignment_and_selection_ambiguity_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """process_multiple_grains → PROCESS_MODEL_ALIGNMENT；选择歧义需 ≥10 个重复组。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    rows = _problems(analysis_dir)
    alignment = _of_type(rows, PROBLEM_TYPE_PROCESS_ALIGNMENT)

    assert {"process_candidate_001", "proj.wide"} <= {row["scope_key"] for row in alignment}
    # 默认阈值（10 组）下不应出现选择歧义问题。
    assert _of_type(rows, PROBLEM_TYPE_SELECTION_AMBIGUITY) == []

    monkeypatch.setattr(problem_module, "SELECTION_AMBIGUITY_MIN_DUPLICATION", 1)
    lowered = _problems(analysis_dir)
    selection = _of_type(lowered, PROBLEM_TYPE_SELECTION_AMBIGUITY)

    assert len(selection) == 1
    assert selection[0]["scope_key"] == "process_candidate_001"


def test_unknown_model_reasons_split_and_weak_status(tmp_path: Path) -> None:
    """UNKNOWN 表按 NO_ANCHOR / NO_EVIDENCE 分组；证据类型不足 → weak → review_required。"""

    ghosts = [_table(f"proj.ghost_{index:03d}") for index in range(60)]
    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        inventory_tables=[*_default_inventory(), *ghosts],
    )
    rows = _problems(analysis_dir)
    unknown = _of_type(rows, PROBLEM_TYPE_UNKNOWN_MODEL)
    by_reason = {row["classification"]: row for row in unknown}

    assert set(by_reason) == {UNKNOWN_REASON_NO_ANCHOR, UNKNOWN_REASON_NO_EVIDENCE}
    no_anchor = by_reason[UNKNOWN_REASON_NO_ANCHOR]
    assert len(no_anchor["table_keys"]) == 60
    # 只有 TABLE 一类证据 → weak → 机器置为 review_required。
    assert no_anchor["evidence_strength"] == "weak"
    assert no_anchor["status"] == PROBLEM_STATUS_REVIEW_REQUIRED


def test_unknown_evidence_rows_are_truncated(tmp_path: Path) -> None:
    """单 problem 证据行超上限 → 截断到 50 行并保留 evidence_total。"""

    ghosts = [_table(f"proj.ghost_{index:03d}") for index in range(60)]
    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        inventory_tables=[*_default_inventory(), *ghosts],
    )
    evidence = _result(analysis_dir).evidence
    row = next(
        item
        for item in evidence["problems"]
        if item["classification"] == UNKNOWN_REASON_NO_ANCHOR
    )

    assert row["evidence_total"] == 60
    assert row["evidence_truncated"] is True
    assert len(row["evidence"]) == PROBLEM_EVIDENCE_ROW_LIMIT


def test_coverage_gap_for_process_without_fact(tmp_path: Path) -> None:
    """存在 fact 的 process 不发问题；没有 fact 的 process → MODEL_COVERAGE_GAP。"""

    analysis_dir = _write_inputs(
        tmp_path / "analysis",
        processes=[
            {"process_key": "process_candidate_001"},
            {"process_key": "process_candidate_002"},
            {"process_key": "process_candidate_003"},
        ],
    )
    gaps = _of_type(_problems(analysis_dir), PROBLEM_TYPE_COVERAGE_GAP)

    assert len(gaps) == 1
    assert gaps[0]["scope_key"] == "process_candidate_003"
    assert gaps[0]["scope"] == "process"
    # 该 process 既无 fact 也无 grain/table 锚点 → 只有 PROCESS 一类证据。
    assert gaps[0]["evidence_strength"] == "weak"
    assert gaps[0]["status"] == PROBLEM_STATUS_REVIEW_REQUIRED


# ============================================================
# 6. Evidence First 与 status / 人工回填
# ============================================================


def test_every_problem_has_traceable_evidence(tmp_path: Path) -> None:
    """每条 problem ≥1 条证据、finding 可追溯、rationale 字段齐全。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    result = _run(analysis_dir)
    payload = result.problem.problems
    evidence = result.problem.evidence
    findings = {row["finding_id"] for row in result.findings["findings"]}
    rows = payload["problems"]

    assert len(evidence["problems"]) == len(rows)

    for row in rows:
        assert row["evidence_total"] >= 1, row["problem_id"]
        assert row["evidence_strength"] in {"strong", "moderate", "weak"}
        assert set(row["finding_ids"]) <= findings, row["problem_id"]
        assert row["impact_types"], row["problem_id"]
        assert row["root_cause"], row["problem_id"]
        assert row["description"] and row["unresolved_reason"], row["problem_id"]
        assert row["human_question"], row["problem_id"]
        rationale = row["rationale"]
        for key in ("current_state", "problem", "evidence", "impact", "why_change"):
            assert str(rationale.get(key) or "").strip(), (row["problem_id"], key)

    for item in evidence["problems"]:
        assert len(item["evidence"]) <= PROBLEM_EVIDENCE_ROW_LIMIT
        assert sum(item["evidence_type_counts"].values()) == len(item["evidence"])

    assert evidence["evidence_row_total"] >= sum(
        len(item["evidence"]) for item in evidence["problems"]
    )


def test_machine_status_then_human_carry_over(tmp_path: Path) -> None:
    """机器只写 candidate / review_required；回填产生 confirmed / rejected / needs_review。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    rows = _problems(analysis_dir)

    assert {row["status"] for row in rows} <= MACHINE_STATUSES

    ids = [row["problem_id"] for row in rows if row["status"] == PROBLEM_STATUS_CANDIDATE]
    confirmed_id, rejected_id, needs_review_id, unknown_value_id = ids[:4]

    _patch_problem_status(analysis_dir, confirmed_id, status="confirmed")
    _patch_problem_status(analysis_dir, rejected_id, status="rejected")
    _patch_problem_status(analysis_dir, needs_review_id, status="needs_review")
    _patch_problem_status(analysis_dir, unknown_value_id, status="banana")

    after = {row["problem_id"]: row for row in _problems(analysis_dir)}

    assert after[confirmed_id]["status"] == PROBLEM_STATUS_CONFIRMED
    assert after[confirmed_id]["human_validated"] is True
    assert after[rejected_id]["status"] == PROBLEM_STATUS_REJECTED
    assert after[rejected_id]["human_validated"] is False
    # 未识别取值 → 按未回填处理，保持机器阶段状态。
    assert after[unknown_value_id]["status"] == PROBLEM_STATUS_CANDIDATE
    assert after[needs_review_id]["status"] == PROBLEM_STATUS_REVIEW_REQUIRED


def test_checklist_machine_columns_preserved_after_rerun(tmp_path: Path) -> None:
    """重跑保留人工三列，机器列按新结果重算。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    _run(analysis_dir)
    target = next(
        row["problem_id"]
        for row in _problems(analysis_dir)
        if row["status"] == PROBLEM_STATUS_CANDIDATE
    )
    _patch_problem_status(analysis_dir, target, status="confirmed", note="第一批确认")
    _run(analysis_dir)
    carry_over = read_problem_carry_over(analysis_dir)

    assert carry_over[target]["human_status"] == "confirmed"
    assert carry_over[target]["human_name"] == "tester"
    assert carry_over[target]["note"] == "第一批确认"
    assert (
        {row["problem_id"] for row in _problems(analysis_dir)}
        == {row["problem_id"] for row in carry_over.values()}
    )


# ============================================================
# 7. 报告与清单渲染
# ============================================================


def test_summary_has_six_sections_and_top_problem_limit(tmp_path: Path) -> None:
    """summary 固定 6 节；Top Problems 最多 20 行；不写成已确认结论。"""

    result = _result(_write_inputs(tmp_path / "analysis"))
    summary = result.summary

    for title in (
        "## 1. Scope",
        "## 2. Problem Distribution",
        "## 3. Impact & Root Cause",
        "## 4. Priority & Evidence",
        "## 5. Top Problems",
        "## 6. Human Review & M4 Input",
    ):
        assert title in summary, title

    top = summary.split("## 5. Top Problems", 1)[1].split("## 6.", 1)[0]
    data_rows = [line for line in top.splitlines() if line.startswith("| problem_0")]
    assert 0 < len(data_rows) <= PROBLEM_SUMMARY_ROW_LIMIT
    assert "confirmed=0" in summary
    assert "Finding Count ≠ Problem Count" in summary


def test_checklist_sections_headers_and_row_limit() -> None:
    """清单按 13 类分区、列固定；分区 >50 行时注明截断。"""

    rows = [
        {
            "problem_id": f"problem_{index:04d}",
            "problem_type": PROBLEM_TYPE_GRAIN,
            "priority": "P0",
            "scope_key": f"proj.t{index}",
            "evidence_type_counts": {"TABLE": 1},
            "description": "描述",
            "human_question": "问题？",
        }
        for index in range(1, 52)
    ]
    text = render_current_state_problem_review_checklist(rows)

    assert "| " + " | ".join(PROBLEM_CHECKLIST_HEADERS) + " |" in text
    assert "只列出前 50 行，共 51 行" in text
    assert text.count("| problem_00") == 50
    assert "| problem_0051 " not in text

    for problem_type in PROBLEM_TYPE_ORDER:
        assert f"## {PROBLEM_TYPE_TITLE.get(problem_type, problem_type)}" in text


def test_checklist_written_with_all_problem_types(tmp_path: Path) -> None:
    """真实产物里 13 类分区齐全，行数与 problems.json 一致。"""

    analysis_dir = _write_inputs(tmp_path / "analysis")
    result = _result(analysis_dir)
    checklist = (analysis_dir / "business" / CHECKLIST_FILE).read_text(encoding="utf-8")

    for problem_type in PROBLEM_TYPE_ORDER:
        assert f"## {PROBLEM_TYPE_TITLE.get(problem_type, problem_type)}" in checklist

    for row in result.problems["problems"]:
        assert f"| {row['problem_id']} " in checklist

    evidence = _payload(analysis_dir, EVIDENCE_FILE)
    assert evidence["count"] == result.problems["count"]
    assert _payload(analysis_dir, PROBLEMS_FILE)["count"] == result.problems["count"]


def _default_inventory() -> list[dict[str, Any]]:
    """默认 7 张合成表（ghost 表之外的 inventory）。"""

    return [
        _table("proj.orders"),
        _table("proj.orders_bak"),
        _table("proj.wide"),
        _table("proj.result", is_view=True),
        _table("proj.sink"),
        _table("proj.dim_customer"),
        _table("proj.cal"),
    ]


# ============================================================
# 8. CLI
# ============================================================


def test_cli_prints_problem_counts(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """analyze-current-state-model 一次跑完 M3.6 v1 + v2 并打印 problem 计数。"""

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

    assert run_cli("analyze-current-state-model") == 0

    out = capsys.readouterr().out

    # rich console 按终端宽度折行，只断言不跨行的片段。
    assert "Current-State Problem Assessment" in out
    assert "problem=" in out
    assert "candidate=" in out
    assert Path("analysis/business/current-state-problems.json").exists()

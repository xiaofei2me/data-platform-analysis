from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from data_platform_analysis.analysis.review.coverage import (
    ARRAY_INPUTS,
    COVERAGE_FILE,
    OPTIONAL_INPUTS,
    ReviewCoverageError,
    _build_coverage,
    run_review_coverage_analysis,
)


def _input_rows() -> dict[str, list[dict[str, Any]]]:
    rows = {name: [] for _relative, _key, name in ARRAY_INPUTS}
    rows.update(
        {
            "inventory_files": [
                {"workspace_id": 1, "file_id": "1", "file_name": "valid.sql"},
                {"workspace_id": 1, "file_id": "2", "file_name": "empty.sql"},
                {"workspace_id": 1, "file_id": "3", "file_name": "broken.sql"},
                {"workspace_id": 1, "file_id": "4", "file_name": "excluded.py"},
            ],
            "inventory_tables": [
                {"workspace_id": 1, "project": "demo", "table": name, "table_key": f"demo.{name}"}
                for name in ("alpha", "beta", "gamma")
            ],
            "workspaces": [
                {"workspace_id": 1, "project": "demo"},
                {"workspace_id": 2, "project": "other"},
            ],
            "sql_candidates": [
                {"workspace_id": 1, "file_id": str(file_id), "sql_eligible": True}
                for file_id in (1, 2, 3)
            ],
            "excluded_tasks": [
                {"workspace_id": 1, "file_id": "4", "sql_eligible": False}
            ],
            "review_tasks": [
                {"workspace_id": 1, "file_id": "4", "review_required": True}
            ],
            "layer_assessments": [
                {
                    "table_identifier": "demo.alpha",
                    "status": "MATCH",
                    "candidate_layer": "DWD",
                },
                {
                    "table_identifier": "demo.beta",
                    "status": "UNKNOWN",
                    "candidate_layer": None,
                },
                {
                    "table_identifier": "demo.gamma",
                    "status": "MATCH",
                    "candidate_layer": "DWD",
                },
            ],
            "statements": [
                {"workspace_id": 1, "file_id": "1", "statement_id": 1, "sql": "select 1"}
            ],
            "references": [
                {
                    "workspace_id": 1,
                    "file_id": "1",
                    "statement_id": 1,
                    "source_tables": ["demo.alpha"],
                    "target_tables": ["demo.gamma", "other.missing"],
                    "extraction_method": "ast",
                }
            ],
            "parse_errors": [
                {"workspace_id": 1, "file_id": "3", "statement_id": 1}
            ],
            "technical_errors": [
                {"workspace_id": 1, "file_id": "3", "stage": "sql"},
                {"stage": "inventory", "error_type": "TABLE_RAW_MISSING"},
            ],
            "lineage_edges": [
                {
                    "source_key": "demo.alpha",
                    "target_key": "demo.gamma",
                    "source_workspace_id": 1,
                    "target_workspace_id": 1,
                    "source_layer_candidate": "DWD",
                    "target_layer_candidate": "DWD",
                    "evidence": [
                        {"workspace_id": 1, "file_id": "1", "statement_id": 1}
                    ],
                },
                {
                    "source_key": "demo.gamma",
                    "target_key": "outside.unindexed",
                    "source_workspace_id": 1,
                    "target_workspace_id": None,
                    "source_layer_candidate": "DWD",
                    "target_layer_candidate": None,
                    "evidence": [],
                },
            ],
            "table_profiles": [
                {
                    "table_key": f"demo.{name}",
                    "profile_status": "metadata_only",
                    "data_sample_available": False,
                }
                for name in ("alpha", "beta", "gamma")
            ],
            "column_profiles": [],
            "understanding_tables": [
                {"table_key": f"demo.{name}", "candidate_sub_layer": "DWD"}
                for name in ("alpha", "beta", "gamma")
            ],
            "grain_candidates": [],
            "fact_candidates": [],
            "dimension_candidates": [],
            "review_tables": [
                {
                    "table_key": "demo.alpha",
                    "current_role": "FACT",
                    "finding_ids": ["finding_alpha"],
                },
                {
                    "table_key": "demo.beta",
                    "current_role": "UNKNOWN",
                    "finding_ids": [],
                },
                {
                    "table_key": "demo.gamma",
                    "current_role": "FACT",
                    "finding_ids": [],
                },
            ],
            "findings": [
                {"finding_id": "finding_alpha", "finding_type": "grain_conflict"}
            ],
            "problems": [
                {
                    "problem_id": "problem_confirmed",
                    "table_keys": ["demo.alpha"],
                    "status": "confirmed",
                    "problem_type": "GRAIN_PROBLEM",
                },
                {
                    "problem_id": "problem_rejected",
                    "table_keys": ["demo.alpha"],
                    "status": "rejected",
                    "problem_type": "MODEL_OVERLAP",
                },
            ],
        }
    )
    return rows


def test_coverage_reports_scope_sql_and_review_states() -> None:
    coverage = _build_coverage(_input_rows())
    file_rows = {
        row["file_id"]: row for row in coverage["scope"]["files"]
    }
    table_rows = {
        row["table_key"]: row for row in coverage["review"]["tables"]
    }

    assert file_rows["1"]["sql_analysis_status"] == "analyzed"
    assert file_rows["2"]["sql_analysis_status"] == "analyzed_no_statements"
    assert file_rows["3"]["sql_analysis_status"] == "failed"
    assert file_rows["4"]["sql_analysis_status"] == "not_eligible"
    assert file_rows["4"]["review_required"] is True
    assert coverage["evidence"]["sql"]["failed_file_count"] == 1
    assert coverage["evidence"]["sql"]["cross_project_table_operand_count"] == 1
    assert coverage["evidence"]["sql"]["unresolved_reference_count"] == 1
    assert coverage["evidence"]["unattributed_technical_error_count"] == 1
    assert coverage["evidence"]["technical_error_stage_counts"]["inventory"] == 1
    assert (
        coverage["evidence"]["sql"]["unresolved_references"][0]["resolution_status"]
        == "external_or_unindexed_project_table"
    )
    assert coverage["evidence"]["lineage"]["unknown_endpoint_edge_count"] == 1
    assert table_rows["demo.alpha"]["review"]["status"] == "mixed_human_decisions"
    assert table_rows["demo.beta"]["review"]["status"] == "insufficient_evidence"
    assert (
        table_rows["demo.gamma"]["review"]["status"]
        == "no_finding_under_implemented_rules"
    )
    assert table_rows["demo.gamma"]["profiling"]["row_level_data_analyzed"] is False
    assert "row_level_data_not_profiled" in table_rows["demo.gamma"]["evidence_limitations"]


def test_sql_evidence_for_an_excluded_file_is_rejected() -> None:
    inputs = _input_rows()
    inputs["statements"].append(
        {"workspace_id": 1, "file_id": "4", "statement_id": 1, "sql": "select 1"}
    )

    with pytest.raises(ReviewCoverageError, match="不满足 sql_eligible"):
        _build_coverage(inputs)


def test_coverage_fails_fast_when_required_input_is_missing(tmp_path: Path) -> None:
    output_dir = tmp_path / "review"

    with pytest.raises(ReviewCoverageError, match="缺少必需输入"):
        run_review_coverage_analysis(analysis_dir=tmp_path / "analysis", output_dir=output_dir)

    assert not (output_dir / COVERAGE_FILE).exists()


def test_coverage_writer_persists_the_cross_stage_ledger(tmp_path: Path) -> None:
    analysis_dir = tmp_path / "analysis"
    rows = _input_rows()
    for relative, key, name in ARRAY_INPUTS:
        root = analysis_dir
        artifact_path = root / relative
        if relative.startswith("review/"):
            artifact_path = root / "review" / relative.removeprefix("review/")
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps({key: rows[name]}, ensure_ascii=False),
            encoding="utf-8",
        )

    output_path = run_review_coverage_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "review",
        review_output_dir=analysis_dir / "review",
    )
    ledger = json.loads(
        output_path.read_text(encoding="utf-8")
    )
    assert ledger["schema_version"] == "1.1"
    assert ledger["scope"]["inventory_file_count"] == 4
    assert ledger["review"]["inventory_table_count"] == 3
    assert ledger["review"]["review_table_record_count"] == 3
    assert sum(ledger["review"]["table_outcome_counts"].values()) == 3
    assert ledger["evidence"]["profiling"]["row_level_data_analyzed"] is False


def test_missing_optional_stages_are_reported_as_unavailable(tmp_path: Path) -> None:
    analysis_dir = tmp_path / "analysis"
    required_rows = {
        "inventory_tables": [
            {"workspace_id": 1, "project": "demo", "table": "alpha", "table_key": "demo.alpha"}
        ],
        "layer_assessments": [
            {
                "table_identifier": "demo.alpha",
                "status": "MATCH",
                "candidate_layer": "DWD",
            }
        ],
        "lineage_edges": [],
        "review_tables": [
            {"table_key": "demo.alpha", "current_role": "FACT", "finding_ids": []}
        ],
    }
    for relative, key, name in ARRAY_INPUTS:
        if relative in OPTIONAL_INPUTS:
            continue
        root = analysis_dir / "review" if relative.startswith("review/") else analysis_dir
        artifact_path = root / relative.removeprefix("review/")
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps({key: required_rows.get(name, [])}, ensure_ascii=False),
            encoding="utf-8",
        )

    output_path = run_review_coverage_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "review",
        review_output_dir=analysis_dir / "review",
    )
    ledger = json.loads(output_path.read_text(encoding="utf-8"))

    assert ledger["scope"]["status"] == "unavailable_missing_inputs"
    assert ledger["evidence"]["sql"]["status"] == "unavailable_missing_inputs"
    assert ledger["evidence"]["profiling"]["status"] == "unavailable_missing_inputs"
    assert ledger["review"]["tables"][0]["review"]["status"] == "insufficient_evidence"
    assert (
        ledger["input_artifact_statuses"]["scope/inputs/sql-candidates.json"]
        == "missing_optional_input"
    )
    assert (
        ledger["review"]["tables"][0]["profiling"]["artifact_status"]
        == "unavailable_missing_input"
    )

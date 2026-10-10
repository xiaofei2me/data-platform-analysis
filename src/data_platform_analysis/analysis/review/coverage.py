"""Cross-stage coverage and traceability for the current-state Review."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ...io_utils import ensure_dir, write_json
from ..naming import project_of, qualify_table_ref

COVERAGE_FILE = "evidence-coverage.json"
OUTPUT_FILES = (COVERAGE_FILE,)

ARRAY_INPUTS: tuple[tuple[str, str, str], ...] = (
    ("inventory/files.json", "files", "inventory_files"),
    ("inventory/tables.json", "tables", "inventory_tables"),
    ("inventory/workspaces.json", "workspaces", "workspaces"),
    ("scope/inputs/sql-candidates.json", "tasks", "sql_candidates"),
    ("scope/inputs/excluded-tasks.json", "tasks", "excluded_tasks"),
    ("scope/review-tasks.json", "tasks", "review_tasks"),
    ("evidence/layer/assessments.json", "assessments", "layer_assessments"),
    ("evidence/sql/statements.json", "statements", "statements"),
    ("evidence/sql/table-references.json", "references", "references"),
    ("evidence/sql/parse-errors.json", "errors", "parse_errors"),
    ("evidence/errors.json", "errors", "technical_errors"),
    ("evidence/lineage/table-lineage.json", "edges", "lineage_edges"),
    ("evidence/profiling/tables.json", "tables", "table_profiles"),
    ("evidence/profiling/columns.json", "columns", "column_profiles"),
    ("understanding/business/tables.json", "tables", "understanding_tables"),
    ("understanding/business/grain-candidates.json", "candidates", "grain_candidates"),
    ("understanding/modeling/fact-candidates.json", "candidates", "fact_candidates"),
    (
        "understanding/modeling/dimension-candidates.json",
        "candidates",
        "dimension_candidates",
    ),
    ("review/current-state-model-tables.json", "tables", "review_tables"),
    ("review/current-state-findings.json", "findings", "findings"),
    ("review/current-state-problems.json", "problems", "problems"),
)

OPTIONAL_INPUTS = frozenset(
    {
        "inventory/files.json",
        "inventory/workspaces.json",
        "scope/inputs/sql-candidates.json",
        "scope/inputs/excluded-tasks.json",
        "scope/review-tasks.json",
        "evidence/sql/statements.json",
        "evidence/sql/table-references.json",
        "evidence/sql/parse-errors.json",
        "evidence/errors.json",
        "evidence/profiling/tables.json",
        "evidence/profiling/columns.json",
        "understanding/business/tables.json",
        "understanding/business/grain-candidates.json",
    }
)


class ReviewCoverageError(RuntimeError):
    """Raised when required stage evidence is missing or structurally invalid."""


def _read_array(analysis_dir: Path, relative: str, key: str) -> list[dict[str, Any]]:
    path = analysis_dir / relative
    if not path.is_file():
        raise ReviewCoverageError(f"Review Coverage 缺少必需输入：{relative}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewCoverageError(
            f"Review Coverage 无法读取合法 JSON 输入：{relative}"
        ) from exc

    rows = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ReviewCoverageError(f"Review Coverage 输入结构非法：{relative} 中应包含数组 {key}")
    return rows


def _read_inputs(
    analysis_dir: Path,
    review_output_dir: Path | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    inputs: dict[str, list[dict[str, Any]]] = {}
    missing_inputs: list[str] = []
    for relative, key, name in ARRAY_INPUTS:
        root = (
            review_output_dir
            if relative.startswith("review/") and review_output_dir is not None
            else analysis_dir
        )
        artifact_path = (
            relative.removeprefix("review/")
            if relative.startswith("review/")
            else relative
        )
        if not (root / artifact_path).is_file() and relative in OPTIONAL_INPUTS:
            inputs[name] = []
            missing_inputs.append(relative)
        else:
            inputs[name] = _read_array(root, artifact_path, key)
    return inputs, missing_inputs


def _file_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("workspace_id") or "").strip().casefold(),
        str(row.get("file_id") or "").strip().casefold(),
    )


def _table_key(row: Mapping[str, Any]) -> str:
    explicit_key = row.get("table_key")
    if explicit_key:
        return str(explicit_key).strip()
    project = str(row.get("project") or "")
    name = str(row.get("table") or row.get("table_name") or "")
    return f"{project}.{name}" if project and name else ""


def _counter(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _index_by_key(
    rows: list[dict[str, Any]],
    key_function: Callable[[Mapping[str, Any]], str],
    label: str,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = key_function(row)
        if not key:
            raise ReviewCoverageError(f"Review Coverage 的 {label} 记录缺少身份键")
        normalized = str(key).casefold()
        if normalized in indexed:
            raise ReviewCoverageError(f"Review Coverage 的 {label} 存在重复身份：{key}")
        indexed[normalized] = row
    return indexed


def _append_index(
    index: dict[tuple[str, str], list[dict[str, Any]]],
    rows: list[dict[str, Any]],
    label: str,
    *,
    allow_unattributed: bool = False,
) -> list[dict[str, Any]]:
    unattributed: list[dict[str, Any]] = []
    for row in rows:
        key = _file_key(row)
        if not all(key):
            if allow_unattributed:
                unattributed.append(row)
                continue
            raise ReviewCoverageError(f"Review Coverage 的 {label} 记录缺少文件身份键")
        index[key].append(row)
    return unattributed


def _eligible_table_refs(
    references: list[dict[str, Any]],
    projects_by_workspace: dict[str, str],
    inventory_keys: set[str],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], int]:
    by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved: list[dict[str, Any]] = []
    cross_project_count = 0
    for reference in references:
        workspace_id = str(reference.get("workspace_id") or "").casefold()
        file_key = (
            workspace_id,
            str(reference.get("file_id") or "").strip().casefold(),
        )
        if not all(file_key):
            raise ReviewCoverageError("SQL Table Reference 缺少 workspace_id 或 file_id")
        project = projects_by_workspace.get(workspace_id, "")
        roles_by_table: dict[str, set[str]] = defaultdict(set)
        for role, field in (
            ("source", "source_tables"),
            ("target", "target_tables"),
        ):
            values = reference.get(field) or []
            if not isinstance(values, list):
                raise ReviewCoverageError(
                    f"SQL Table Reference 的 {field} 字段必须是数组"
                )
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    continue
                reference_project = project_of(value)
                is_cross_project = bool(
                    reference_project
                    and project
                    and reference_project.casefold() != project.casefold()
                )
                if is_cross_project:
                    cross_project_count += 1
                normalized = qualify_table_ref(value.strip(), project).casefold()
                if normalized not in inventory_keys:
                    unresolved.append(
                        {
                            "workspace_id": reference.get("workspace_id"),
                            "file_id": reference.get("file_id"),
                            "node_id": reference.get("node_id"),
                            "statement_id": reference.get("statement_id"),
                            "table_reference": value.strip(),
                            "qualified_table_key": normalized,
                            "role": role,
                            "resolution_status": (
                                "workspace_project_unknown"
                                if not project and reference_project is None
                                else "external_or_unindexed_project_table"
                                if is_cross_project
                                else "inventory_table_not_found"
                            ),
                        }
                    )
                    continue
                roles_by_table[normalized].add(role)
        for normalized, roles in roles_by_table.items():
            by_table[normalized].append(
                {
                    "workspace_id": reference.get("workspace_id"),
                    "file_id": reference.get("file_id"),
                    "node_id": reference.get("node_id"),
                    "statement_id": reference.get("statement_id"),
                    "roles": sorted(roles),
                    "extraction_method": reference.get("extraction_method"),
                    "table_key": normalized,
                }
            )
    return by_table, unresolved, cross_project_count


def _problem_outcome(
    *,
    has_review_row: bool,
    current_role: str | None,
    finding_ids: list[str],
    problem_statuses: list[str],
    evidence_complete: bool,
) -> str:
    confirmed = "confirmed" in problem_statuses
    rejected = "rejected" in problem_statuses
    open_candidates = any(
        status in {"candidate", "review_required", "needs_discussion"}
        for status in problem_statuses
    )
    if confirmed and rejected:
        return "mixed_human_decisions"
    if confirmed and open_candidates:
        return "confirmed_with_open_candidates"
    if confirmed:
        return "human_confirmed_problem"
    if rejected and open_candidates:
        return "rejected_with_open_candidates"
    if rejected:
        return "human_rejected"
    if open_candidates:
        return "problem_candidate"
    if problem_statuses:
        return "problem_status_needs_review"
    if finding_ids:
        return "finding_candidate"
    if not has_review_row:
        return "not_reviewed"
    if not evidence_complete or current_role == "UNKNOWN":
        return "insufficient_evidence"
    return "no_finding_under_implemented_rules"


def _build_coverage(
    inputs: dict[str, list[dict[str, Any]]],
    missing_inputs: list[str] | None = None,
) -> dict[str, Any]:
    missing = set(missing_inputs or [])
    scope_inputs = {
        "inventory/files.json",
        "scope/inputs/sql-candidates.json",
        "scope/inputs/excluded-tasks.json",
    }
    sql_inputs = {
        *scope_inputs,
        "scope/review-tasks.json",
        "evidence/sql/statements.json",
        "evidence/sql/table-references.json",
        "evidence/sql/parse-errors.json",
        "evidence/errors.json",
    }
    scope_available = not (scope_inputs & missing)
    sql_available = not (sql_inputs & missing)
    inventory_files = inputs["inventory_files"]
    inventory_tables = inputs["inventory_tables"]
    sql_candidates = inputs["sql_candidates"]
    excluded_tasks = inputs["excluded_tasks"]
    review_tasks = inputs["review_tasks"]

    scope_by_file: dict[tuple[str, str], dict[str, Any]] = {}
    for task in sql_candidates:
        file_identity = _file_key(task)
        if not all(file_identity):
            raise ReviewCoverageError("Scope 记录缺少 workspace_id 或 file_id")
        if file_identity in scope_by_file:
            raise ReviewCoverageError(f"Scope 存在重复 SQL 候选身份：{file_identity}")
        if task.get("sql_eligible") is not True:
            raise ReviewCoverageError(
                f"Scope SQL 候选未标记 sql_eligible=true：{file_identity}"
            )
        scope_by_file[file_identity] = task
    for task in excluded_tasks:
        file_identity = _file_key(task)
        if not all(file_identity):
            raise ReviewCoverageError("Scope 记录缺少 workspace_id 或 file_id")
        if file_identity in scope_by_file:
            raise ReviewCoverageError(
                f"Scope SQL 候选与排除记录身份冲突：{file_identity}"
            )
        if task.get("sql_eligible") is not False:
            raise ReviewCoverageError(
                f"Scope 排除记录未标记 sql_eligible=false：{file_identity}"
            )
        scope_by_file[file_identity] = task

    inventory_file_keys = {_file_key(row) for row in inventory_files}
    if any(not all(file_identity) for file_identity in inventory_file_keys):
        raise ReviewCoverageError("Inventory Files 存在缺少 workspace_id 或 file_id 的记录")
    if len(inventory_file_keys) != len(inventory_files):
        raise ReviewCoverageError("Inventory Files 存在重复身份")
    if scope_available and inventory_file_keys != set(scope_by_file):
        raise ReviewCoverageError("Scope 候选/排除输入未完整覆盖 Inventory Files")

    review_required_keys = {_file_key(row) for row in review_tasks}
    if scope_available and not review_required_keys.issubset(inventory_file_keys):
        raise ReviewCoverageError("Scope 待复核记录引用了不在 Inventory 中的 File")
    statements_by_file: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    parse_errors_by_file: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    technical_errors_by_file: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    _append_index(statements_by_file, inputs["statements"], "SQL Statement")
    _append_index(parse_errors_by_file, inputs["parse_errors"], "SQL Parse Error")
    unattributed_technical_errors = _append_index(
        technical_errors_by_file,
        inputs["technical_errors"],
        "Technical Error",
        allow_unattributed=True,
    )
    eligible_file_keys = {_file_key(row) for row in sql_candidates}
    if scope_available and any(key not in eligible_file_keys for key in statements_by_file):
        raise ReviewCoverageError("SQL Statements 包含不满足 sql_eligible 的 File")
    if scope_available and any(key not in eligible_file_keys for key in parse_errors_by_file):
        raise ReviewCoverageError("SQL Parse Errors 包含不满足 sql_eligible 的 File")

    file_assessments: list[dict[str, Any]] = []
    for inventory_file in inventory_files:
        file_identity = _file_key(inventory_file)
        scope = scope_by_file.get(file_identity, {})
        statements = statements_by_file[file_identity]
        parse_errors = parse_errors_by_file[file_identity]
        technical_errors = technical_errors_by_file[file_identity]
        is_sql_eligible = scope.get("sql_eligible") is True
        has_sql_error = any(error.get("stage") == "sql" for error in technical_errors)
        if scope.get("sql_eligible") is False:
            sql_status = "not_eligible"
        elif not scope_available or not sql_available:
            sql_status = "unavailable_missing_inputs"
        elif not is_sql_eligible:
            sql_status = "unavailable_missing_inputs"
        elif parse_errors or has_sql_error:
            sql_status = "failed"
        elif statements:
            sql_status = "analyzed"
        else:
            sql_status = "analyzed_no_statements"
        file_assessments.append(
            {
                "workspace_id": scope.get("workspace_id"),
                "workspace_name": scope.get("workspace_name"),
                "file_id": scope.get("file_id"),
                "node_id": scope.get("node_id"),
                "file_name": scope.get("file_name"),
                "task_type": scope.get("task_type"),
                "content_format": scope.get("content_format"),
                "content_state": scope.get("content_state"),
                "content_expectation": scope.get("content_expectation"),
                "identity_eligible": scope.get("identity_eligible"),
                "overall_eligible": scope.get("overall_eligible"),
                "sql_eligible": scope.get("sql_eligible"),
                "reason_codes": scope.get("reason_codes") or [],
                "sql_reason_code": scope.get("sql_reason_code"),
                "review_required": file_identity in review_required_keys
                or bool(scope.get("review_required")),
                "sql_analysis_status": sql_status,
                "statement_count": len(statements),
                "parse_error_count": len(parse_errors),
                "technical_errors_by_stage": _counter(
                    [str(error.get("stage") or "unknown") for error in technical_errors]
                ),
            }
        )

    _index_by_key(
        inputs["workspaces"],
        lambda row: str(row.get("workspace_id") or ""),
        "Workspace",
    )
    projects_by_workspace = {
        str(row.get("workspace_id") or "").casefold(): str(
            row.get("project") or row.get("name") or ""
        )
        for row in inputs["workspaces"]
    }
    table_index = _index_by_key(
        inventory_tables, _table_key, "Inventory Table"
    )
    inventory_keys = set(table_index)
    (
        references_by_table,
        unresolved_references,
        cross_project_reference_count,
    ) = _eligible_table_refs(
        inputs["references"],
        projects_by_workspace,
        inventory_keys,
    )
    layer_by_table = {
        str(row.get("table_identifier") or "").casefold(): row
        for row in inputs["layer_assessments"]
        if row.get("table_identifier")
    }
    profile_by_table = {
        _table_key(row).casefold(): row for row in inputs["table_profiles"] if _table_key(row)
    }
    understanding_by_table = {
        _table_key(row).casefold(): row
        for row in inputs["understanding_tables"]
        if _table_key(row)
    }
    model_by_table = {
        _table_key(row).casefold(): row for row in inputs["review_tables"] if _table_key(row)
    }

    grain_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in inputs["grain_candidates"]:
        candidate_table_key = _table_key(candidate).casefold()
        if candidate_table_key:
            grain_by_table[candidate_table_key].append(candidate)

    fact_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in inputs["fact_candidates"]:
        table_keys = candidate.get("table_keys") or [_table_key(candidate)]
        for candidate_table_key in set(
            str(value).casefold() for value in table_keys if value
        ):
            fact_by_table[candidate_table_key].append(candidate)

    dimension_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in inputs["dimension_candidates"]:
        table_keys = candidate.get("table_keys") or [_table_key(candidate)]
        for candidate_table_key in set(
            str(value).casefold() for value in table_keys if value
        ):
            dimension_by_table[candidate_table_key].append(candidate)

    findings_by_id = _index_by_key(
        inputs["findings"],
        lambda row: str(row.get("finding_id") or ""),
        "Finding",
    )
    problems_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for problem in inputs["problems"]:
        for problem_table_key in set(
            str(value).casefold() for value in problem.get("table_keys") or [] if value
        ):
            problems_by_table[problem_table_key].append(problem)

    incoming_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    outgoing_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unknown_endpoint_edge_count = 0
    cross_workspace_edge_count = 0
    unknown_layer_edge_count = 0
    for edge in inputs["lineage_edges"]:
        source_key = str(edge.get("source_key") or "").casefold()
        target_key = str(edge.get("target_key") or "").casefold()
        edge_summary = {
            "source_key": edge.get("source_key"),
            "target_key": edge.get("target_key"),
            "source_workspace_id": edge.get("source_workspace_id"),
            "target_workspace_id": edge.get("target_workspace_id"),
            "source_layer_candidate": edge.get("source_layer_candidate"),
            "target_layer_candidate": edge.get("target_layer_candidate"),
            "evidence": [
                {
                    "workspace_id": item.get("workspace_id"),
                    "file_id": item.get("file_id"),
                    "statement_id": item.get("statement_id"),
                }
                for item in edge.get("evidence") or []
            ],
        }
        if edge.get("source_workspace_id") is None or edge.get("target_workspace_id") is None:
            unknown_endpoint_edge_count += 1
        elif edge.get("source_workspace_id") != edge.get("target_workspace_id"):
            cross_workspace_edge_count += 1
        if (
            edge.get("source_layer_candidate") is None
            or edge.get("target_layer_candidate") is None
        ):
            unknown_layer_edge_count += 1
        if target_key in inventory_keys:
            incoming_by_table[target_key].append(edge_summary)
        if source_key in inventory_keys:
            outgoing_by_table[source_key].append(edge_summary)

    table_assessments: list[dict[str, Any]] = []
    table_layer: dict[str, str] = {}
    sql_status_by_file = {
        _file_key(row): row["sql_analysis_status"] for row in file_assessments
    }
    for table in inventory_tables:
        table_key = _table_key(table)
        normalized = table_key.casefold()
        layer = layer_by_table.get(normalized)
        profile = profile_by_table.get(normalized)
        understanding = understanding_by_table.get(normalized)
        model = model_by_table.get(normalized)
        finding_ids = [
            str(value) for value in (model or {}).get("finding_ids") or [] if value
        ]
        missing_finding_ids = [
            finding_id
            for finding_id in finding_ids
            if finding_id.casefold() not in findings_by_id
        ]
        if missing_finding_ids:
            raise ReviewCoverageError(
                f"Review Table {table_key} 引用了不存在的 Finding：{missing_finding_ids}"
            )
        table_problems = problems_by_table[normalized]
        problem_statuses = [str(problem.get("status") or "unknown") for problem in table_problems]
        table_references = references_by_table.get(normalized, [])
        failed_reference_files = sorted(
            {
                (str(reference.get("workspace_id") or "").casefold(),
                 str(reference.get("file_id") or "").casefold())
                for reference in table_references
                if sql_status_by_file.get(
                    (
                        str(reference.get("workspace_id") or "").casefold(),
                        str(reference.get("file_id") or "").casefold(),
                    )
                )
                != "analyzed"
            }
        )
        current_role = str((model or {}).get("current_role") or "") or None
        review_outcome = _problem_outcome(
            has_review_row=model is not None,
            current_role=current_role,
            finding_ids=finding_ids,
            problem_statuses=problem_statuses,
            evidence_complete=(
                sql_available
                and layer is not None
                and (layer or {}).get("status") != "UNKNOWN"
                and profile is not None
                and understanding is not None
                and bool(table_references)
                and not failed_reference_files
            ),
        )
        evidence_layer = str((layer or {}).get("candidate_layer") or "UNKNOWN")
        table_layer[normalized] = evidence_layer

        limitations: list[str] = []
        if (layer or {}).get("status") == "UNKNOWN":
            limitations.append("layer_assessment_unknown")
        if (profile or {}).get("profile_status") == "metadata_only":
            limitations.append("row_level_data_not_profiled")
        if not table_references:
            limitations.append("no_sql_table_reference_observed")
        if failed_reference_files:
            limitations.append("sql_reference_file_not_fully_analyzed")
        if profile is None:
            limitations.append("profiling_record_missing")
        if "evidence/profiling/tables.json" in missing:
            limitations.append("profiling_artifact_missing")
        if understanding is None:
            limitations.append("understanding_record_missing")
        if "understanding/business/tables.json" in missing:
            limitations.append("understanding_artifact_missing")
        if not sql_available:
            limitations.append("sql_evidence_inputs_missing")
        if current_role == "UNKNOWN":
            limitations.append("current_model_role_unknown")
        if model is None:
            limitations.append("current_state_review_missing")
        limitations.append("business_facts_not_machine_confirmed")

        table_assessments.append(
            {
                "table_key": table_key,
                "workspace_id": table.get("workspace_id"),
                "project": table.get("project"),
                "table": table.get("table"),
                "column_count": table.get("column_count"),
                "inventory_source": table.get("raw_file"),
                "layer": {
                    "assessment_status": (layer or {}).get("status", "missing"),
                    "candidate_layer": (layer or {}).get("candidate_layer"),
                    "workspace_layer": (layer or {}).get("workspace_layer"),
                },
                "profiling": {
                    "artifact_status": (
                        "unavailable_missing_input"
                        if "evidence/profiling/tables.json" in missing
                        else "available"
                    ),
                    "profile_status": (profile or {}).get("profile_status", "missing"),
                    "data_sample_available": (profile or {}).get(
                        "data_sample_available", False
                    ),
                    "row_count": (profile or {}).get("row_count"),
                    "row_level_data_analyzed": False,
                },
                "sql_references": table_references,
                "sql_reference_file_status_counts": _counter(
                    [
                        sql_status_by_file.get(
                            (
                                str(reference.get("workspace_id") or "").casefold(),
                                str(reference.get("file_id") or "").casefold(),
                            ),
                            "unavailable_missing_inputs",
                        )
                        for reference in table_references
                    ]
                ),
                "sql_reference_status": (
                    "unavailable_missing_inputs"
                    if not sql_available
                    else (
                        "references_observed"
                        if references_by_table.get(normalized)
                        else "no_reference_observed"
                    )
                ),
                "lineage": {
                    "incoming": incoming_by_table.get(normalized, []),
                    "outgoing": outgoing_by_table.get(normalized, []),
                },
                "understanding": {
                    "artifact_status": (
                        "unavailable_missing_input"
                        if "understanding/business/tables.json" in missing
                        else "available"
                    ),
                    "candidate_sub_layer": (understanding or {}).get("candidate_sub_layer"),
                    "is_core_candidate": (understanding or {}).get("is_core_candidate"),
                    "grain_candidate_ids": sorted(
                        str(item.get("grain_candidate_id") or "")
                        for item in grain_by_table.get(normalized, [])
                    ),
                    "fact_candidate_ids": sorted(
                        str(item.get("fact_key") or "")
                        for item in fact_by_table.get(normalized, [])
                    ),
                    "dimension_candidate_ids": sorted(
                        str(item.get("dimension_key") or "")
                        for item in dimension_by_table.get(normalized, [])
                    ),
                },
                "review": {
                    "status": review_outcome,
                    "current_role": current_role,
                    "model_shape": (model or {}).get("model_shape"),
                    "finding_ids": finding_ids,
                    "finding_types": _counter(
                        [
                            str(
                                findings_by_id[finding_id.casefold()].get("finding_type")
                                or "unknown"
                            )
                            for finding_id in finding_ids
                        ]
                    ),
                    "problem_ids": sorted(
                        str(problem.get("problem_id") or "") for problem in table_problems
                    ),
                    "problem_status_counts": _counter(problem_statuses),
                    "problem_type_counts": _counter(
                        [
                            str(problem.get("problem_type") or "unknown")
                            for problem in table_problems
                        ]
                    ),
                },
                "evidence_limitations": limitations,
            }
        )

    problem_by_layer: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: {
            "problem_type_counts": Counter(),
            "status_counts": Counter(),
            "priority_counts": Counter(),
            "severity_counts": Counter(),
        }
    )
    for problem in inputs["problems"]:
        affected_keys = set(
            str(value).casefold() for value in problem.get("table_keys") or [] if value
        )
        for problem_table_key in affected_keys:
            layer_name = table_layer.get(problem_table_key, "NOT_IN_INVENTORY")
            counts = problem_by_layer[layer_name]
            counts["problem_type_counts"][str(problem.get("problem_type") or "unknown")] += 1
            counts["status_counts"][str(problem.get("status") or "unknown")] += 1
            counts["priority_counts"][str(problem.get("priority") or "unknown")] += 1
            counts["severity_counts"][str(problem.get("severity") or "unknown")] += 1

    technical_error_stages = [
        str(error.get("stage") or "unknown") for error in inputs["technical_errors"]
    ]
    layer_statuses = [str(row.get("status") or "unknown") for row in inputs["layer_assessments"]]
    profile_statuses = [
        str(row.get("profile_status") or "unknown") for row in inputs["table_profiles"]
    ]
    sql_statuses = [row["sql_analysis_status"] for row in file_assessments]

    return {
        "schema_version": "1.1",
        "purpose": (
            "Coverage and evidence navigation only. No Finding means no issue was emitted "
            "by the implemented rule set; it does not assert model correctness."
        ),
        "input_artifacts": [relative for relative, _key, _name in ARRAY_INPUTS],
        "input_artifact_statuses": {
            relative: (
                "missing_optional_input" if relative in missing else "available"
            )
            for relative, _key, _name in ARRAY_INPUTS
        },
        "scope": {
            "status": (
                "available" if scope_available else "unavailable_missing_inputs"
            ),
            "inventory_file_count": len(inventory_files),
            "sql_eligible_file_count": len(sql_candidates),
            "not_sql_eligible_file_count": len(excluded_tasks),
            "review_required_file_count": len(review_required_keys),
            "sql_analysis_status_counts": _counter(sql_statuses),
            "files": file_assessments,
        },
        "evidence": {
            "layer": {
                "assessment_count": len(inputs["layer_assessments"]),
                "status_counts": _counter(layer_statuses),
            },
            "sql": {
                "status": (
                    "available" if sql_available else "unavailable_missing_inputs"
                ),
                "eligible_file_count": len(sql_candidates),
                "analyzed_file_count": sum(status == "analyzed" for status in sql_statuses),
                "failed_file_count": sum(status == "failed" for status in sql_statuses),
                "analyzed_no_statements_file_count": sum(
                    status == "analyzed_no_statements" for status in sql_statuses
                ),
                "statement_count": len(inputs["statements"]),
                "table_reference_count": len(inputs["references"]),
                "parse_error_count": len(inputs["parse_errors"]),
                "parse_error_file_count": len(
                    {_file_key(row) for row in inputs["parse_errors"]}
                ),
                "technical_error_count": sum(stage == "sql" for stage in technical_error_stages),
                "unresolved_reference_count": len(unresolved_references),
                "unresolved_references": unresolved_references,
                "cross_project_table_operand_count": cross_project_reference_count,
                "extraction_method_counts": _counter(
                    [
                        str(row.get("extraction_method") or "unknown")
                        for row in inputs["references"]
                    ]
                ),
            },
            "lineage": {
                "edge_count": len(inputs["lineage_edges"]),
                "cross_workspace_edge_count": cross_workspace_edge_count,
                "unknown_endpoint_edge_count": unknown_endpoint_edge_count,
                "unknown_layer_endpoint_edge_count": unknown_layer_edge_count,
            },
            "profiling": {
                "status": (
                    "available"
                    if "evidence/profiling/tables.json" not in missing
                    else "unavailable_missing_inputs"
                ),
                "table_profile_count": len(inputs["table_profiles"]),
                "column_profile_count": len(inputs["column_profiles"]),
                "status_counts": _counter(profile_statuses),
                "row_level_data_analyzed": False,
            },
            "technical_error_stage_counts": _counter(technical_error_stages),
            "unattributed_technical_error_count": len(unattributed_technical_errors),
            "unattributed_technical_errors": unattributed_technical_errors,
            "understanding_status": (
                "available"
                if "understanding/business/tables.json" not in missing
                else "unavailable_missing_inputs"
            ),
        },
        "review": {
            "inventory_table_count": len(inventory_tables),
            "review_table_record_count": len(inputs["review_tables"]),
            "table_outcome_counts": _counter(
                [row["review"]["status"] for row in table_assessments]
            ),
            "finding_count": len(inputs["findings"]),
            "problem_count": len(inputs["problems"]),
            "problem_type_counts": _counter(
                [str(row.get("problem_type") or "unknown") for row in inputs["problems"]]
            ),
            "problem_status_counts": _counter(
                [str(row.get("status") or "unknown") for row in inputs["problems"]]
            ),
            "problem_priority_counts": _counter(
                [str(row.get("priority") or "unknown") for row in inputs["problems"]]
            ),
            "problem_severity_counts": _counter(
                [str(row.get("severity") or "unknown") for row in inputs["problems"]]
            ),
            "problem_distribution_by_layer": {
                layer: {
                    name: dict(sorted(counts.items())) for name, counts in groups.items()
                }
                for layer, groups in sorted(problem_by_layer.items())
            },
            "tables": table_assessments,
        },
    }


def run_review_coverage_analysis(
    *,
    analysis_dir: Path,
    output_dir: Path,
    review_output_dir: Path | None = None,
) -> Path:
    """Build and write the cross-stage Review evidence coverage ledger.

    Core Inventory, Layer, Lineage, Understanding Model and Review inputs are
    required. Optional Scope / SQL / Profiling inputs missing from a standalone
    Review run are reported as unavailable; malformed present inputs always fail.
    """

    inputs, missing_inputs = _read_inputs(analysis_dir, review_output_dir)
    coverage = _build_coverage(inputs, missing_inputs)
    ensure_dir(output_dir)
    output_path = output_dir / COVERAGE_FILE
    write_json(output_path, coverage)
    return output_path

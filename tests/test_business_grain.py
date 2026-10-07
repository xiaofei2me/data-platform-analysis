"""M3.4 Grain Candidate Analysis 的测试。

覆盖任务要求的场景：输入缺失 / 非法 / 只读 / 形态级联 / 多候选全保留 /
空候选键 / 强度与未决原因 / 不伪造唯一性 / 人工确认不传递 / 产物结构与报告 /
确定性 / CLI 黑盒。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_business_objects import _prepare
from test_business_processes import _write_process_rules
from test_business_understanding import _table

from data_platform_analysis.analysis.business.grain import (
    CARRYOVER_CHECKLIST_INPUT_FILE,
    INPUT_FILES,
    OUTPUT_FILES,
    PROCESS_CHECKLIST_INPUT_FILE,
    BusinessGrainError,
    read_grain_inputs,
    run_business_grain_analysis,
)
from data_platform_analysis.analysis.business.objects import (
    run_business_object_analysis,
)
from data_platform_analysis.analysis.business.processes import (
    run_business_process_analysis,
)
from data_platform_analysis.analysis.models import (
    EVIDENCE_STRENGTH_MODERATE,
    EVIDENCE_STRENGTH_STRONG,
    EVIDENCE_STRENGTH_WEAK,
    GRAIN_CANDIDATE_NOTE,
    GRAIN_CHECKLIST_ROW_LIMIT,
    GRAIN_EVIDENCE_ORDER,
    GRAIN_PATTERN_AGGREGATION,
    GRAIN_PATTERN_EVENT,
    GRAIN_PATTERN_ORDER,
    GRAIN_PATTERN_PERIODIC,
    GRAIN_PATTERN_SNAPSHOT,
    GRAIN_PATTERN_TRANSACTION,
    GRAIN_PATTERN_UNKNOWN,
    GRAIN_REPORT_ROW_LIMIT,
    GRAIN_ROLE_ANCHOR,
    GRAIN_ROLE_ORDER,
    GRAIN_ROLE_SUPPORTING,
    GRAIN_SIGNAL_TYPE_ORDER,
    GRAIN_STATUS_CANDIDATE,
    GRAIN_STATUS_ORDER,
    GRAIN_UNRESOLVED_AGGREGATION,
    GRAIN_UNRESOLVED_INSUFFICIENT,
    GRAIN_UNRESOLVED_MULTIPLE_KEYS,
    GRAIN_UNRESOLVED_NO_IDENTIFIER,
    GRAIN_UNRESOLVED_ORDER,
    GRAIN_UNRESOLVED_TIME,
)

# ============================================================
# 测试数据
# ============================================================

CARRYOVER_TEMPLATE = """\
# M3.4 Grain Review Checklist

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength \
| unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{rows}
"""


def _column(
    workspace_id: int,
    project: str,
    table: str,
    column_name: str,
    ordinal: int,
    comment: str | None = None,
    is_partition: bool = False,
) -> dict[str, Any]:
    """构造 M2.1 columns.json 中的单条记录（可声明分区列）。"""

    return {
        "workspace_id": workspace_id,
        "project": project,
        "schema": "",
        "table": table,
        "ordinal": ordinal,
        "column_name": column_name,
        "data_type": "STRING",
        "comment": comment,
        "is_partition": is_partition,
        "table_key": f"{project}.{table}",
    }


def _grain_m2() -> dict[str, Any]:
    """M2 产物：覆盖六种候选形态所需的表与字段。

    - txn_order：事务标识 → T1 / T2；
    - daily_sales / daily_sales_bak：Object × 分区时间 → G1（含 supporting 表）；
    - cal_period / cust_snapshot / event_log / plain_tbl：{customer, product}
      这一组的四张表，分别落在 periodic / snapshot / event / 空候选键四种形态上。
    """

    return {
        "tables": [
            _table(9001, "proj", "txn_order", comment="订单"),
            _table(9001, "proj", "daily_sales", comment="客户订单日销售"),
            _table(9001, "proj", "daily_sales_bak", comment="客户订单日销售备份"),
            _table(9001, "proj", "cal_period", comment="客户商品月度统计"),
            _table(9001, "proj", "cust_snapshot", comment="客户商品快照"),
            _table(9001, "proj", "event_log", comment="客户商品事件日志"),
            _table(9001, "proj", "plain_tbl", comment="客户商品基础表"),
        ],
        "columns": [
            # 事务：标识 + 度量 + 时间 + 另一个标识。
            _column(9001, "proj", "txn_order", "order_id", 0),
            _column(9001, "proj", "txn_order", "amount", 1),
            _column(9001, "proj", "txn_order", "order_date", 2),
            _column(9001, "proj", "txn_order", "customer_id", 3, comment="客户编号"),
            # Object × 分区时间。
            _column(9001, "proj", "daily_sales", "customer_id", 0, comment="客户编号"),
            _column(9001, "proj", "daily_sales", "ds", 1, is_partition=True),
            _column(9001, "proj", "daily_sales", "amount", 2),
            _column(9001, "proj", "daily_sales_bak", "customer_id", 0, comment="客户编号"),
            _column(9001, "proj", "daily_sales_bak", "ds", 1, is_partition=True),
            _column(9001, "proj", "daily_sales_bak", "amount", 2),
            # 周期 / 快照 / 事件 / 空候选。
            _column(9001, "proj", "cal_period", "month", 0),
            _column(9001, "proj", "cal_period", "amount", 1),
            _column(9001, "proj", "cust_snapshot", "region_snapshot", 0),
            _column(9001, "proj", "cust_snapshot", "amount", 1),
            _column(9001, "proj", "event_log", "event_id", 0),
            _column(9001, "proj", "event_log", "amount", 1),
            _column(9001, "proj", "plain_tbl", "code", 0),
            _column(9001, "proj", "plain_tbl", "update_time", 1),
        ],
        "statements": [
            {
                "workspace_id": 9001,
                "file_id": "1",
                "statement_id": 1,
                "sql": "select 1 from proj.txn_order",
            }
        ],
        "references": [
            {
                "workspace_id": 9001,
                "file_id": "1",
                "statement_id": 1,
                "source_tables": [],
                "target_tables": ["proj.txn_order"],
            }
        ],
        "edges": [
            {
                "workspace_id": 9001,
                "source_table": "proj.txn_order",
                "target_table": "proj.daily_sales",
                "source_key": "proj.txn_order",
                "target_key": "proj.daily_sales",
            }
        ],
        "candidates": [
            {"table_key": "proj.txn_order", "workspace_id": 9001, "in_inventory": True},
        ],
        "assessments": [
            _assessment(table)
            for table in (
                "txn_order",
                "daily_sales",
                "daily_sales_bak",
                "cal_period",
                "cust_snapshot",
                "event_log",
                "plain_tbl",
            )
        ],
    }


def _assessment(table: str) -> dict[str, Any]:
    """构造 M2.2 assessments.json 中的单条记录。"""

    return {
        "workspace_id": 9001,
        "workspace_name": "proj",
        "workspace_layer": "CDM",
        "project": "proj",
        "table_name": table,
        "table_identifier": f"proj.{table}",
        "candidate_layer": "DWD",
        "status": "MATCH",
        "evidence": [],
    }


def _write_profiling(analysis_dir: Path) -> None:
    """写出 metadata-only 的 Profiling 产物（无样本、无唯一键判定）。"""

    tables = [
        {
            "table_key": f"proj.{table}",
            "profile_status": "metadata_only",
            "data_sample_available": False,
        }
        for table in (
            "txn_order",
            "daily_sales",
            "daily_sales_bak",
            "cal_period",
            "cust_snapshot",
            "event_log",
            "plain_tbl",
        )
    ]
    columns = [
        {
            "table_key": f"proj.{table}",
            "column_name": column,
            "profile_status": "metadata_only",
            "is_candidate_key": False,
        }
        for table, column in (
            ("txn_order", "order_id"),
            ("daily_sales", "customer_id"),
            ("daily_sales", "ds"),
            ("cal_period", "month"),
            ("cust_snapshot", "region_snapshot"),
            ("event_log", "event_id"),
            ("plain_tbl", "code"),
        )
    ]

    for relative, key, records in (
        ("profiling/tables.json", "tables", tables),
        ("profiling/columns.json", "columns", columns),
    ):
        path = analysis_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"count": len(records), key: records}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _pipeline(tmp_path: Path) -> Path:
    """M2 → M3 → M3.1 → M3.2 → M3.3 → Profiling，返回 analysis 目录。"""

    analysis_dir = _prepare(tmp_path, **_grain_m2())
    run_business_object_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )
    run_business_process_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
        rules_path=_write_process_rules(tmp_path / "config" / "process-rules.yaml"),
    )
    _write_profiling(analysis_dir)

    return analysis_dir


def _run(analysis_dir: Path) -> Any:
    return run_business_grain_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )


def _read(analysis_dir: Path, name: str) -> Any:
    return json.loads((analysis_dir / "business" / name).read_text(encoding="utf-8"))


def _candidates(analysis_dir: Path) -> list[dict[str, Any]]:
    return _read(analysis_dir, "grain-candidates.json")["candidates"]


def _for_table(rows: list[dict[str, Any]], table_key: str) -> list[dict[str, Any]]:
    """按 table_key 取出候选（大小写不敏感）。"""

    return [
        row
        for row in rows
        if str(row["table_key"]).casefold() == table_key.casefold()
    ]


def _one(rows: list[dict[str, Any]], table_key: str, keys: list[str]) -> dict[str, Any]:
    """取出唯一的指定候选键组合。"""

    matched = [
        row for row in _for_table(rows, table_key) if list(row["candidate_keys"]) == keys
    ]

    assert len(matched) == 1, (table_key, keys, len(matched))

    return matched[0]


def _write_carryover(analysis_dir: Path, *rows: str) -> None:
    """覆盖本阶段清单，用于回填测试。"""

    text = CARRYOVER_TEMPLATE.format(rows="\n".join(rows))
    (analysis_dir / CARRYOVER_CHECKLIST_INPUT_FILE).write_text(text, encoding="utf-8")


# ============================================================
# 1. 输入缺失 / 非法
# ============================================================


def test_missing_inputs_raise(tmp_path: Path) -> None:
    """必需产物缺失 → 明确报错，并提示先跑前置阶段。"""

    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    with pytest.raises(BusinessGrainError, match="产物缺失"):
        read_grain_inputs(analysis_dir)


def test_missing_single_input_reports_path(tmp_path: Path) -> None:
    """缺 profiling/columns.json → 报错信息点名该文件。"""

    analysis_dir = _pipeline(tmp_path)
    (analysis_dir / "profiling" / "columns.json").unlink()

    with pytest.raises(BusinessGrainError, match="profiling/columns.json"):
        read_grain_inputs(analysis_dir)


def test_invalid_json_raises(tmp_path: Path) -> None:
    """产物不是合法 JSON → 报错，不回退、不静默跳过。"""

    analysis_dir = _pipeline(tmp_path)
    (analysis_dir / "lineage" / "table-lineage.json").write_text("{", encoding="utf-8")

    with pytest.raises(BusinessGrainError, match="不是合法的 JSON"):
        read_grain_inputs(analysis_dir)


def test_array_payload_with_non_object_root_raises(tmp_path: Path) -> None:
    """产物根节点不是对象 → 明确报错。"""

    analysis_dir = _pipeline(tmp_path)
    (analysis_dir / "profiling" / "tables.json").write_text("[]", encoding="utf-8")

    with pytest.raises(BusinessGrainError, match="根节点不是对象"):
        read_grain_inputs(analysis_dir)


def test_optional_checklists_are_optional(tmp_path: Path) -> None:
    """两份清单都不存在时也能正常运行（只读、可选）。"""

    analysis_dir = _pipeline(tmp_path)

    for relative in (PROCESS_CHECKLIST_INPUT_FILE, CARRYOVER_CHECKLIST_INPUT_FILE):
        path = analysis_dir / relative
        if path.exists():
            path.unlink()

    result = _run(analysis_dir)

    assert result.candidate_count > 0


def test_checklist_without_required_columns_raises(tmp_path: Path) -> None:
    """grain 清单存在但缺必需列 → 明确报错。"""

    analysis_dir = _pipeline(tmp_path)
    (analysis_dir / CARRYOVER_CHECKLIST_INPUT_FILE).write_text(
        "# M3.4 Grain Review Checklist\n\n| grain_candidate_id | confirmed |\n"
        "| --- | --- |\n| grain_candidate_001 | true |\n",
        encoding="utf-8",
    )

    with pytest.raises(BusinessGrainError, match="缺少必需列"):
        _run(analysis_dir)


# ============================================================
# 2. 只读
# ============================================================


def test_inputs_are_read_only(tmp_path: Path) -> None:
    """M2 ~ M3.3 产物在 M3.4 前后字节不变。"""

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

    assert {path: path.read_bytes() for path in before} == before
    assert after == before


def test_input_file_list_matches_declared_files(tmp_path: Path) -> None:
    """全部必需输入都在声明的列表里（15 个数组型产物）。"""

    analysis_dir = _pipeline(tmp_path)

    assert len(INPUT_FILES) == 15

    for relative in INPUT_FILES:
        assert (analysis_dir / relative).exists(), relative

    assert set(OUTPUT_FILES) == {
        "grain-signals.json",
        "grain-candidates.json",
        "grain-tables.json",
        "grain-summary.md",
        "grain-review-checklist.md",
    }


# ============================================================
# 3. Grain Signal
# ============================================================


def test_signal_types_and_levels(tmp_path: Path) -> None:
    """信号只覆盖 7 类固定类型，列级 / 表级来源可区分。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    payload = _read(analysis_dir, "grain-signals.json")

    assert payload["count"] == len(payload["signals"])
    assert set(payload["type_counts"]) <= set(GRAIN_SIGNAL_TYPE_ORDER)

    for row in payload["signals"]:
        assert row["signal_type"] in set(GRAIN_SIGNAL_TYPE_ORDER)
        assert row["source"] in {"column", "table"}
        assert row["signal_type"] != "aggregation" or row["source"] == "table"
        assert row["evidence"], row


def test_signal_order_is_stable(tmp_path: Path) -> None:
    """信号按 (type, table, column) 稳定排序。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _read(analysis_dir, "grain-signals.json")["signals"]
    order = {item: index for index, item in enumerate(GRAIN_SIGNAL_TYPE_ORDER)}
    keys = [
        (
            order[row["signal_type"]],
            str(row["table_key"]).casefold(),
            str(row.get("column_name") or ""),
        )
        for row in rows
    ]

    assert keys == sorted(keys)


def test_signal_without_candidate_is_retained(tmp_path: Path) -> None:
    """plain_tbl 没有候选键，但它的字段信号仍然保留。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _read(analysis_dir, "grain-signals.json")["signals"]
    plain = [
        row
        for row in rows
        if str(row["table_key"]).casefold() == "proj.plain_tbl"
    ]

    assert {row["signal_type"] for row in plain} >= {"identifier", "time"}


# ============================================================
# 4. 形态级联与候选键
# ============================================================


def test_transaction_cascade_keeps_single_and_pairs(tmp_path: Path) -> None:
    """事务形态：T1 单键 + T2 事务 × Object，两个候选都保留。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _candidates(analysis_dir)

    single = _one(rows, "proj.txn_order", ["order_id"])
    pair = _one(rows, "proj.txn_order", ["customer_id", "order_id"])

    assert single["grain_pattern"] == GRAIN_PATTERN_TRANSACTION
    assert pair["grain_pattern"] == GRAIN_PATTERN_TRANSACTION
    # 不做笛卡尔积：只产生这两组键。
    assert len(_for_table(rows, "proj.txn_order")) == 2


def test_object_and_partition_time_form(tmp_path: Path) -> None:
    """Object × 分区时间 → aggregation 形态的两列候选键。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _candidates(analysis_dir)
    candidate = _one(rows, "proj.daily_sales", ["customer_id", "ds"])

    assert candidate["grain_pattern"] == GRAIN_PATTERN_AGGREGATION
    assert "ds" in candidate["time_columns"]
    assert "customer_id" in candidate["identifier_columns"]


def test_periodic_snapshot_event_forms(tmp_path: Path) -> None:
    """周期 / 快照 / 事件三种形态各自的单键候选。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _candidates(analysis_dir)

    assert (
        _one(rows, "proj.cal_period", ["month"])["grain_pattern"]
        == GRAIN_PATTERN_PERIODIC
    )
    assert (
        _one(rows, "proj.cust_snapshot", ["region_snapshot"])["grain_pattern"]
        == GRAIN_PATTERN_SNAPSHOT
    )
    assert (
        _one(rows, "proj.event_log", ["event_id"])["grain_pattern"]
        == GRAIN_PATTERN_EVENT
    )


def test_no_form_yields_empty_candidate_keys(tmp_path: Path) -> None:
    """没有任何可用形态 → 空候选键 + unknown，而不是编一个键。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _candidates(analysis_dir)
    empty = _for_table(rows, "proj.plain_tbl")

    assert len(empty) == 1
    assert empty[0]["candidate_keys"] == []
    assert empty[0]["grain_pattern"] == GRAIN_PATTERN_UNKNOWN
    assert GRAIN_UNRESOLVED_NO_IDENTIFIER in empty[0]["unresolved_reasons"]
    assert empty[0]["strength"] == EVIDENCE_STRENGTH_WEAK


def test_candidate_keys_exist_in_inventory(tmp_path: Path) -> None:
    """候选键全部是 inventory/columns.json 里真实存在的字段。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    columns = json.loads(
        (analysis_dir / "inventory" / "columns.json").read_text(encoding="utf-8")
    )["columns"]
    present: dict[str, set[str]] = {}

    for row in columns:
        present.setdefault(str(row["table_key"]).casefold(), set()).add(
            str(row["column_name"])
        )

    for candidate in _candidates(analysis_dir):
        names = present[str(candidate["table_key"]).casefold()]

        for key in candidate["candidate_keys"]:
            assert key in names, (candidate["grain_candidate_id"], key)


def test_only_one_form_per_table(tmp_path: Path) -> None:
    """每个 (process, table) 只走一种形态：不叠加多种展开方式。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    txn_patterns = {
        candidate["grain_pattern"]
        for candidate in _for_table(_candidates(analysis_dir), "proj.txn_order")
    }

    assert txn_patterns == {GRAIN_PATTERN_TRANSACTION}


# ============================================================
# 5. 多候选与未决原因
# ============================================================


def test_multiple_keys_are_all_kept(tmp_path: Path) -> None:
    """同一张表的多个候选键全部保留，并标记 multiple_possible_keys。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _for_table(_candidates(analysis_dir), "proj.txn_order")

    assert len(rows) == 2
    assert all(GRAIN_UNRESOLVED_MULTIPLE_KEYS in row["unresolved_reasons"] for row in rows)
    assert [row["grain_candidate_id"] for row in rows] == sorted(
        row["grain_candidate_id"] for row in rows
    )


def test_unresolved_reasons_follow_fixed_order(tmp_path: Path) -> None:
    """未决原因按固定顺序排列，且全部属于白名单。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    order = {item: index for index, item in enumerate(GRAIN_UNRESOLVED_ORDER)}

    for candidate in _candidates(analysis_dir):
        reasons = candidate["unresolved_reasons"]
        assert reasons
        assert set(reasons) <= set(GRAIN_UNRESOLVED_ORDER)
        assert [order[item] for item in reasons] == sorted(order[item] for item in reasons)


def test_missing_sql_and_lineage_evidence_reasons(tmp_path: Path) -> None:
    """没有 SQL / 血缘证据的表记录对应未决原因；有证据的不记录。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _candidates(analysis_dir)
    with_sql = _one(rows, "proj.txn_order", ["order_id"])
    without_sql = _one(rows, "proj.cal_period", ["month"])

    assert "missing_sql_evidence" not in with_sql["unresolved_reasons"]
    assert "missing_sql_evidence" in without_sql["unresolved_reasons"]
    assert "missing_lineage_evidence" not in with_sql["unresolved_reasons"]
    assert "missing_lineage_evidence" in without_sql["unresolved_reasons"]


def test_time_semantics_and_aggregation_level_reasons(tmp_path: Path) -> None:
    """只有名字像时间的字段 → time_semantics_unclear；有度量的聚合 → 层级未决。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _candidates(analysis_dir)

    # plain_tbl 的 update_time 只有名字形态证据，且是空候选。
    assert GRAIN_UNRESOLVED_TIME in _for_table(rows, "proj.plain_tbl")[0][
        "unresolved_reasons"
    ]

    # daily_sales 有度量且是 aggregation 形态 → 聚合层级未决。
    assert GRAIN_UNRESOLVED_AGGREGATION in _one(
        rows, "proj.daily_sales", ["customer_id", "ds"]
    )["unresolved_reasons"]


def test_insufficient_evidence_requires_two_sources(tmp_path: Path) -> None:
    """证据源少于 2 个或空候选键 → insufficient_evidence。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    for candidate in _candidates(analysis_dir):
        if not candidate["candidate_keys"] or len(candidate["evidence_sources"]) < 2:
            assert GRAIN_UNRESOLVED_INSUFFICIENT in candidate["unresolved_reasons"]
        else:
            assert GRAIN_UNRESOLVED_INSUFFICIENT not in candidate["unresolved_reasons"]


# ============================================================
# 6. 强度、状态与不伪造唯一性
# ============================================================


def test_strength_comes_from_evidence_diversity(tmp_path: Path) -> None:
    """strength 只反映证据源多样性，且空候选键恒为 weak。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)

    for candidate in _candidates(analysis_dir):
        diversity = len(candidate["evidence_sources"])

        if not candidate["candidate_keys"]:
            assert candidate["strength"] == EVIDENCE_STRENGTH_WEAK
        elif diversity >= 4:
            assert candidate["strength"] == EVIDENCE_STRENGTH_STRONG
        elif diversity >= 2:
            assert candidate["strength"] in {
                EVIDENCE_STRENGTH_MODERATE,
                EVIDENCE_STRENGTH_STRONG,
            }
        else:
            assert candidate["strength"] == EVIDENCE_STRENGTH_WEAK


def test_status_is_always_candidate(tmp_path: Path) -> None:
    """status 恒为 candidate，不产出 confirmed grain。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    payload = _read(analysis_dir, "grain-candidates.json")

    assert set(payload["status_counts"]) <= set(GRAIN_STATUS_ORDER)
    assert payload["status_counts"] == {GRAIN_STATUS_CANDIDATE: payload["count"]}

    for candidate in payload["candidates"]:
        assert candidate["status"] == GRAIN_STATUS_CANDIDATE


def test_no_uniqueness_is_invented(tmp_path: Path) -> None:
    """Profiling 全是 metadata_only → 不出现唯一性结论。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    text = (analysis_dir / "business" / "grain-summary.md").read_text(encoding="utf-8")

    assert "is_candidate_key=true 的列 0" in text
    assert "唯一" in text  # 说明不伪造唯一性
    assert "唯一性证明" in text

    for candidate in _candidates(analysis_dir):
        assert "unique" not in candidate["evidence_sources"]
        assert all(
            entry["source_type"] in set(GRAIN_EVIDENCE_ORDER)
            for entry in candidate["evidence"]
        )


def test_evidence_entries_are_traceable(tmp_path: Path) -> None:
    """证据条目带 source_type / source_id / reason，可回溯。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    candidate = _one(_candidates(analysis_dir), "proj.txn_order", ["order_id"])

    assert candidate["evidence_sources"] == sorted(
        candidate["evidence_sources"],
        key=lambda item: list(GRAIN_EVIDENCE_ORDER).index(item),
    )

    for entry in candidate["evidence"]:
        assert entry["source_type"] in set(GRAIN_EVIDENCE_ORDER)
        assert entry["source_id"]
        assert entry["reason"]


# ============================================================
# 7. 人工确认不传递
# ============================================================


def test_process_human_validated_is_recorded_only(tmp_path: Path) -> None:
    """Process 的人工确认只被记录，不改变 grain 的 candidate 状态。"""

    analysis_dir = _pipeline(tmp_path)
    (analysis_dir / PROCESS_CHECKLIST_INPUT_FILE).write_text(
        "# M3.3 Process Review Checklist\n\n"
        "| process_key | objects | tables | signals | evidence | human_process_name "
        "| confirmed | note |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| process_candidate_001 | - | 1 | - | - | 销售订单 | true | |\n",
        encoding="utf-8",
    )
    _run(analysis_dir)
    rows = _candidates(analysis_dir)
    validated = [row for row in rows if row["process_human_validated"]]

    assert validated
    assert all(row["status"] == GRAIN_STATUS_CANDIDATE for row in validated)


def test_checklist_carry_over_is_preserved(tmp_path: Path) -> None:
    """grain 清单里的人工回填在重跑后被带回去。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    first = _candidates(analysis_dir)[0]
    candidate_id = first["grain_candidate_id"]

    _write_carryover(
        analysis_dir,
        f"| {candidate_id} | {first['table_key']} | {first['grain_pattern']} "
        f"| - | {first['strength']} | - | 每日订单粒度 | true | 人工确认 |",
    )
    _run(analysis_dir)

    checklist = (analysis_dir / "business" / "grain-review-checklist.md").read_text(
        encoding="utf-8"
    )

    assert "每日订单粒度" in checklist
    assert "| true |" in checklist
    assert "人工确认" in checklist

    # 回填不改变 JSON 产物的 candidate 状态。
    assert _candidates(analysis_dir)[0]["status"] == GRAIN_STATUS_CANDIDATE


def test_checklist_defaults_to_false(tmp_path: Path) -> None:
    """未回填的行 confirmed 一律 false。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    checklist = (analysis_dir / "business" / "grain-review-checklist.md").read_text(
        encoding="utf-8"
    )
    lines = [
        line
        for line in checklist.splitlines()
        if line.startswith("| grain_candidate_")
        and not line.startswith("| grain_candidate_id |")
    ]

    assert lines
    assert all("| false |" in line for line in lines)
    assert "human_grain_name" in checklist


# ============================================================
# 8. grain → table 角色
# ============================================================


def test_anchor_and_supporting_roles(tmp_path: Path) -> None:
    """每个候选都有 anchor 行；同 process 同键的表成为 supporting 行。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    tables = _read(analysis_dir, "grain-tables.json")["tables"]
    anchor = _one(_candidates(analysis_dir), "proj.daily_sales", ["customer_id", "ds"])
    rows = [
        row for row in tables if row["grain_candidate_id"] == anchor["grain_candidate_id"]
    ]
    roles = {row["role"]: row for row in rows}

    assert set(roles) == {GRAIN_ROLE_ANCHOR, GRAIN_ROLE_SUPPORTING}
    assert roles[GRAIN_ROLE_ANCHOR]["table_key"] == "proj.daily_sales"
    assert roles[GRAIN_ROLE_SUPPORTING]["table_key"] == "proj.daily_sales_bak"
    assert roles[GRAIN_ROLE_ANCHOR]["supporting_table_count"] == 1
    assert roles[GRAIN_ROLE_SUPPORTING]["supporting_table_count"] == 0


def test_supporting_rows_are_capped(tmp_path: Path) -> None:
    """supporting 行每个候选最多 5 条（上限常量生效）。"""

    from data_platform_analysis.analysis.business.grain import (  # noqa: PLC0415
        GRAIN_SUPPORTING_ROW_LIMIT,
    )

    assert GRAIN_SUPPORTING_ROW_LIMIT == 5

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    tables = _read(analysis_dir, "grain-tables.json")["tables"]
    counts: dict[str, int] = {}

    for row in tables:
        if row["role"] == GRAIN_ROLE_SUPPORTING:
            counts[row["grain_candidate_id"]] = (
                counts.get(row["grain_candidate_id"], 0) + 1
            )

    assert counts
    assert max(counts.values()) <= 5


def test_role_vocabulary_has_no_fact_dimension(tmp_path: Path) -> None:
    """role 只用 anchor / supporting，不产出 Fact / Dimension 命名。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    payload = _read(analysis_dir, "grain-tables.json")
    text = (analysis_dir / "business" / "grain-summary.md").read_text(encoding="utf-8")

    assert set(payload["role_counts"]) <= set(GRAIN_ROLE_ORDER)
    assert set(payload["role_counts"]) == {GRAIN_ROLE_ANCHOR, GRAIN_ROLE_SUPPORTING}
    assert "role 只是技术角色" in text
    assert "不命名事实表 / 维度表" in text


def test_core_candidate_is_only_a_priority_marker(tmp_path: Path) -> None:
    """core_candidate 来自 M2.4 核心表候选，只作覆盖与复核优先级。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _candidates(analysis_dir)
    core = _one(rows, "proj.txn_order", ["order_id"])
    plain = _for_table(rows, "proj.plain_tbl")[0]

    assert core["core_candidate"] is True
    assert plain["core_candidate"] is False


# ============================================================
# 9. 产物结构与报告
# ============================================================


def test_output_structure_and_counts(tmp_path: Path) -> None:
    """5 个产物齐全，顶层计数与数组长度一致。"""

    analysis_dir = _pipeline(tmp_path)
    result = _run(analysis_dir)

    for name in OUTPUT_FILES:
        assert (analysis_dir / "business" / name).exists(), name

    signals = _read(analysis_dir, "grain-signals.json")
    candidates = _read(analysis_dir, "grain-candidates.json")
    tables = _read(analysis_dir, "grain-tables.json")

    assert signals["count"] == len(signals["signals"])
    assert candidates["count"] == len(candidates["candidates"]) == result.candidate_count
    assert tables["count"] == len(tables["tables"])
    assert sum(candidates["pattern_counts"].values()) == candidates["count"]
    assert sum(candidates["strength_counts"].values()) == candidates["count"]
    assert sum(tables["role_counts"].values()) == tables["count"]
    assert set(candidates["pattern_counts"]) <= set(GRAIN_PATTERN_ORDER)
    assert candidates["process_count"] >= 1
    assert candidates["table_count"] >= 1


def test_candidate_id_and_signature_are_deterministic(tmp_path: Path) -> None:
    """编号连续、signature 全局排序且唯一。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    rows = _candidates(analysis_dir)
    ids = [row["grain_candidate_id"] for row in rows]
    signatures = [row["canonical_signature"] for row in rows]

    assert ids == [f"grain_candidate_{index:03d}" for index in range(1, len(rows) + 1)]
    assert signatures == sorted(signatures)
    assert len(set(signatures)) == len(signatures)
    assert all(
        row["canonical_signature"].startswith(
            f"process={row['process_candidate_id']}|"
        )
        and "|table=" in row["canonical_signature"]
        and "|keys=" in row["canonical_signature"]
        and "|pattern=" in row["canonical_signature"]
        for row in rows
    )


def test_summary_has_required_sections(tmp_path: Path) -> None:
    """grain-summary.md 覆盖 9 个小节且给出候选 / 信号 / 缺口数字。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    summary = (analysis_dir / "business" / "grain-summary.md").read_text(encoding="utf-8")

    for heading in (
        "# M3.4 Grain Candidate Analysis",
        "## 1. Overview",
        "## 2. Grain Signals",
        "## 3. Grain Candidates",
        "## 4. Process → Grain",
        "## 5. Evidence Sources",
        "## 6. Evidence Gaps",
        "## 7. Human Review",
        "## 8. Limitations",
        "## 9. Next: Fact-Dimension Readiness",
    ):
        assert heading in summary, heading

    assert GRAIN_CANDIDATE_NOTE in summary
    assert "Signal ≠ Grain" in summary
    assert "grain-review-checklist.md" in summary


def test_summary_tables_are_truncated_with_note(tmp_path: Path) -> None:
    """候选明细表最多 GRAIN_REPORT_ROW_LIMIT 行并注明总数。"""

    analysis_dir = _pipeline(tmp_path)
    result = _run(analysis_dir)
    summary = (analysis_dir / "business" / "grain-summary.md").read_text(encoding="utf-8")
    candidate_lines = [
        line for line in summary.splitlines() if line.startswith("| grain_candidate_")
    ]

    assert len(candidate_lines) <= GRAIN_REPORT_ROW_LIMIT

    if result.candidate_count > GRAIN_REPORT_ROW_LIMIT:
        assert f"共 {result.candidate_count} 条" in summary
    else:
        assert "只列出前" not in summary

    assert "完整明细见 `analysis/business/grain-candidates.json`" in summary


def test_checklist_is_grouped_by_process_with_row_limit(tmp_path: Path) -> None:
    """grain 清单按 process 分组，每组最多 GRAIN_CHECKLIST_ROW_LIMIT 行。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    text = (analysis_dir / "business" / "grain-review-checklist.md").read_text(
        encoding="utf-8"
    )
    section_rows: list[int] = []
    current = 0

    for line in text.splitlines():
        if line.startswith("## "):
            section_rows.append(current)
            current = 0
        elif line.startswith("| grain_candidate_"):
            current += 1

    section_rows.append(current)

    assert any(count > 0 for count in section_rows)
    assert max(section_rows) <= GRAIN_CHECKLIST_ROW_LIMIT


def test_pattern_counts_cover_known_vocabulary(tmp_path: Path) -> None:
    """所有候选的 grain_pattern 都在固定词表内，且未出现的模式计数为 0。"""

    analysis_dir = _pipeline(tmp_path)
    _run(analysis_dir)
    payload = _read(analysis_dir, "grain-candidates.json")

    assert set(payload["pattern_counts"]) == set(GRAIN_PATTERN_ORDER)
    assert payload["pattern_counts"][GRAIN_PATTERN_UNKNOWN] == sum(
        1 for row in payload["candidates"] if not row["candidate_keys"]
    )


# ============================================================
# 10. 确定性
# ============================================================


def test_deterministic_across_runs(tmp_path: Path) -> None:
    """两次运行字节一致（无时间戳 / UUID / 随机抽样）。"""

    analysis_dir = _pipeline(tmp_path)
    business_dir = analysis_dir / "business"

    _run(analysis_dir)
    first = {name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)}

    _run(analysis_dir)
    second = {name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)}

    assert first == second


# ============================================================
# 11. CLI 黑盒
# ============================================================


def test_analyze_business_grain_command(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze-business-grain 产出 5 个文件，两次运行一致且不改前置产物。"""

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

    business_dir = Path("analysis/business")
    before = {path.name: path.read_bytes() for path in sorted(business_dir.iterdir())}

    assert run_cli("analyze-business-grain") == 0

    for name in OUTPUT_FILES:
        assert (business_dir / name).exists(), name

    for name, content in before.items():
        assert (business_dir / name).read_bytes() == content, name

    first = {name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)}

    assert run_cli("analyze-business-grain") == 0
    assert {
        name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)
    } == first


def test_analyze_business_grain_command_fails_without_inputs(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """缺 M3.3 产物 → 退出码 1，不写任何 M3.4 产物。"""

    assert run_cli("analyze-business-grain") == 1
    assert not Path("analysis/business/grain-candidates.json").exists()


def test_analyze_business_command_does_not_produce_grain_outputs(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze-business 只跑到 M3，不会顺带产出 M3.4 产物。"""

    from test_business_objects import (  # noqa: PLC0415
        OBJECT_RULES_TEXT,
        _write_m2,
        _write_rules,
    )
    from test_business_processes import _m2_payloads  # noqa: PLC0415

    monkeypatch.setenv(
        "BUSINESS_RULES_PATH",
        str(_write_rules(tmp_path / "config" / "business-rules.yaml", OBJECT_RULES_TEXT)),
    )
    _write_m2(Path("analysis"), **_m2_payloads())

    assert run_cli("analyze-business") == 0

    assert not Path("analysis/business/grain-candidates.json").exists()

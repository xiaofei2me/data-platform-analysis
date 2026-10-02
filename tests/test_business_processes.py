"""M3.3 Business Process Candidate Analysis 的测试。

覆盖任务要求的场景：配置与输入缺失 / 只读 / 分词子序列匹配 / 分组去重 /
Level 与强度映射 / 门槛（证据不足只留 signal）/ 人工确认 / 产物结构与报告 /
确定性 / CLI 黑盒。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from test_business_objects import _column, _prepare, _table, _write_checklist

from data_platform_analysis.analysis.business_objects import (
    run_business_object_analysis,
)
from data_platform_analysis.analysis.business_processes import (
    INPUT_FILES,
    OUTPUT_FILES,
    PROCESS_CHECKLIST_INPUT_FILE,
    BusinessProcessesError,
    load_process_rules,
    read_process_inputs,
    run_business_process_analysis,
)
from data_platform_analysis.analysis.models import (
    PROCESS_STRENGTH_MODERATE,
    PROCESS_STRENGTH_STRONG,
    PROCESS_STRENGTH_WEAK,
    process_evidence_strength,
)

# ============================================================
# 测试数据
# ============================================================

PROCESS_RULES_TEXT = """\
version: "1.0"

transaction_identifiers:
  - order_id
  - transaction_id

transaction_measures:
  - amount
  - quantity
  - price

event_time:
  - date
  - time

status:
  - status
  - state
"""

PROCESS_CHECKLIST_TEMPLATE = """\
# M3.3 Process Review Checklist

| process_key | objects | tables | signals | evidence | human_process_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
{rows}
"""


def _write_process_rules(path: Path, text: str = PROCESS_RULES_TEXT) -> Path:
    """写出 process-rules 配置。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    return path


def _m2_payloads() -> dict[str, Any]:
    """M2 产物：表、字段、SQL、血缘与核心表候选。

    表名刻意用中性命名（tbl_*），Object 只靠注释与字段名指定，
    避免 SQL / 血缘把业务关键词传播到别的表上，保证分组可预期。
    """

    return {
        "tables": [
            _table(9001, "proj", "tbl_a", comment="客户订单"),
            _table(9001, "proj", "tbl_b", comment="订单"),
            _table(9001, "proj", "tbl_c", comment="客户"),
            _table(9001, "proj", "tbl_d", comment="门店订单"),
            _table(9001, "proj", "tbl_e", comment="订单"),
            _table(9001, "proj", "tbl_f", comment="客户门店"),
            _table(9001, "proj", "tbl_g"),
        ],
        "columns": [
            # {customer, order}：只有度量与时间。
            _column(9001, "proj", "tbl_a", "amount", 0),
            _column(9001, "proj", "tbl_a", "order_date", 1),
            # {order, product}：四类列级信号齐全。
            _column(9001, "proj", "tbl_b", "order_id", 0),
            _column(9001, "proj", "tbl_b", "quantity", 1),
            _column(9001, "proj", "tbl_b", "amount", 2),
            _column(9001, "proj", "tbl_b", "order_date", 3),
            _column(9001, "proj", "tbl_b", "status", 4),
            _column(9001, "proj", "tbl_b", "product_name", 5, comment="product"),
            # {order}：只有事务标识与状态 → Level 1。
            _column(9001, "proj", "tbl_e", "order_id", 0),
            _column(9001, "proj", "tbl_e", "status", 1),
            # {order, store}：时间 + 状态。
            _column(9001, "proj", "tbl_d", "order_date", 0),
            _column(9001, "proj", "tbl_d", "status", 1),
            # {customer}：有信号但够不到任何 Level。
            _column(9001, "proj", "tbl_c", "update_time", 0),
            _column(9001, "proj", "tbl_c", "state", 1),
            # {customer, store}：没有任何列级信号。
            _column(9001, "proj", "tbl_f", "code", 0),
            _column(9001, "proj", "tbl_f", "name", 1),
            # runtime / customer_id 不命中任何规则。
            _column(9001, "proj", "tbl_g", "runtime", 0),
            _column(9001, "proj", "tbl_g", "customer_id", 1),
        ],
        "statements": [
            {
                "workspace_id": 9001,
                "file_id": "1",
                "statement_id": 1,
                "sql": "select 1 from proj.tbl_c join proj.tbl_f on 1 = 1",
            },
            {
                "workspace_id": 9001,
                "file_id": "2",
                "statement_id": 2,
                "sql": "select 1 from proj.tbl_f",
            },
            {
                "workspace_id": 9001,
                "file_id": "3",
                "statement_id": 3,
                "sql": "select 1 from proj.tbl_a",
            },
        ],
        "references": [
            {
                "workspace_id": 9001,
                "file_id": "1",
                "statement_id": 1,
                "source_tables": ["proj.tbl_c"],
                "target_tables": ["proj.tbl_f", "proj.tbl_b"],
            },
            {
                "workspace_id": 9001,
                "file_id": "2",
                "statement_id": 2,
                "source_tables": ["proj.tbl_f"],
                "target_tables": ["proj.tbl_e"],
            },
            {
                "workspace_id": 9001,
                "file_id": "3",
                "statement_id": 3,
                "source_tables": ["proj.tbl_a"],
                "target_tables": ["proj.tbl_b"],
            },
        ],
        "edges": [
            {
                "workspace_id": 9001,
                "source_table": "proj.tbl_c",
                "target_table": "proj.tbl_b",
                "source_key": "proj.tbl_c",
                "target_key": "proj.tbl_b",
            }
        ],
        "candidates": [
            {
                "table_key": "proj.tbl_b",
                "workspace_id": 9001,
                "in_inventory": True,
                "layer_candidate": "DWD",
                "upstream_count": 1,
                "downstream_count": 0,
                "evidence_count": 1,
            }
        ],
    }


def _pipeline(tmp_path: Path) -> tuple[Path, Path]:
    """M2 → M3 → M3.1 → M3.2，返回 (analysis 目录, process-rules 路径)。"""

    analysis_dir = _prepare(tmp_path, **_m2_payloads())
    run_business_object_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
    )

    rules_path = _write_process_rules(tmp_path / "config" / "process-rules.yaml")

    return analysis_dir, rules_path


def _run(analysis_dir: Path, rules_path: Path) -> Any:
    return run_business_process_analysis(
        analysis_dir=analysis_dir,
        output_dir=analysis_dir / "business",
        rules_path=rules_path,
    )


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _process(payload: dict[str, Any], *objects: str) -> dict[str, Any]:
    """按 objects 列表取出一条 process candidate。"""

    wanted = sorted(objects)

    for item in payload["processes"]:
        if sorted(item["objects"]) == wanted:
            return item

    raise AssertionError(f"missing process candidate: {wanted}")


def _signals_for(payload: dict[str, Any], table_key: str) -> list[dict[str, Any]]:
    return [
        item
        for item in payload["signals"]
        if str(item["table_key"]).casefold() == table_key.casefold()
    ]


def _write_process_checklist(analysis_dir: Path, *rows: str) -> None:
    """覆盖 M3.3 生成的清单，用于回填测试。"""

    text = PROCESS_CHECKLIST_TEMPLATE.format(rows="\n".join(rows))
    (analysis_dir / PROCESS_CHECKLIST_INPUT_FILE).write_text(
        text,
        encoding="utf-8",
    )


# ============================================================
# 1. 配置（config/process-rules.yaml）
# ============================================================


def test_missing_process_rules_raises(tmp_path: Path) -> None:
    """配置文件不存在 → BusinessProcessesError，不回退默认规则。"""

    with pytest.raises(BusinessProcessesError, match="不存在"):
        load_process_rules(tmp_path / "config" / "process-rules.yaml")


def test_invalid_yaml_process_rules_raises(tmp_path: Path) -> None:
    path = _write_process_rules(tmp_path / "process-rules.yaml", "version: [unclosed")

    with pytest.raises(BusinessProcessesError, match="YAML"):
        load_process_rules(path)


def test_missing_version_process_rules_raises(tmp_path: Path) -> None:
    path = _write_process_rules(
        tmp_path / "process-rules.yaml",
        "transaction_identifiers:\n  - order_id\n",
    )

    with pytest.raises(BusinessProcessesError, match="version"):
        load_process_rules(path)


def test_empty_section_process_rules_raises(tmp_path: Path) -> None:
    path = _write_process_rules(
        tmp_path / "process-rules.yaml",
        PROCESS_RULES_TEXT.replace("  - price", "  - "),
    )

    with pytest.raises(BusinessProcessesError, match="非空"):
        load_process_rules(path)


def test_cross_section_conflict_process_rules_raises(tmp_path: Path) -> None:
    path = _write_process_rules(
        tmp_path / "process-rules.yaml",
        PROCESS_RULES_TEXT.replace(
            "event_time:\n  - date",
            "event_time:\n  - date\n  - status",
        ),
    )

    with pytest.raises(BusinessProcessesError, match="跨段冲突"):
        load_process_rules(path)


# ============================================================
# 2. 输入读取
# ============================================================


def test_missing_inputs_raise(tmp_path: Path) -> None:
    analysis_dir, rules_path = _pipeline(tmp_path)
    (analysis_dir / "business" / "object-tables.json").unlink()

    with pytest.raises(BusinessProcessesError, match="business/object-tables.json"):
        _run(analysis_dir, rules_path)


def test_read_process_inputs_reports_missing_paths(tmp_path: Path) -> None:
    analysis_dir, _rules_path = _pipeline(tmp_path)
    (analysis_dir / "inventory" / "columns.json").unlink()

    with pytest.raises(BusinessProcessesError, match="inventory/columns.json"):
        read_process_inputs(analysis_dir)

    assert INPUT_FILES  # 输入清单非空，且 process 清单属于可选输入
    assert PROCESS_CHECKLIST_INPUT_FILE not in INPUT_FILES


def test_invalid_json_raises(tmp_path: Path) -> None:
    analysis_dir, rules_path = _pipeline(tmp_path)
    (analysis_dir / "business" / "terms.json").write_text("{oops", encoding="utf-8")

    with pytest.raises(BusinessProcessesError, match="terms.json"):
        _run(analysis_dir, rules_path)


def test_inputs_are_read_only(tmp_path: Path) -> None:
    """M3.3 只写自己的六个产物，不改写 M2 / M3 / M3.1 / M3.2 文件。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    before = {
        path.relative_to(analysis_dir).as_posix(): path.read_bytes()
        for path in sorted(analysis_dir.rglob("*"))
        if path.is_file() and path.name not in OUTPUT_FILES
    }

    _run(analysis_dir, rules_path)

    after = {
        path.relative_to(analysis_dir).as_posix(): path.read_bytes()
        for path in sorted(analysis_dir.rglob("*"))
        if path.is_file() and path.name not in OUTPUT_FILES
    }

    assert before == after


# ============================================================
# 3. Process Signal
# ============================================================


def test_signal_matching_uses_token_subsequence(tmp_path: Path) -> None:
    """order_date 命中 date、update_time 命中 time；runtime / customer_id 不命中。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    result = _run(analysis_dir, rules_path)
    payload = result.signals

    order_date = next(
        item
        for item in _signals_for(payload, "proj.tbl_b")
        if item["column_name"] == "order_date"
    )
    assert order_date["signal_type"] == "event_time"
    assert order_date["signal"] == "date"

    update_time = next(
        item
        for item in _signals_for(payload, "proj.tbl_c")
        if item["column_name"] == "update_time"
    )
    assert update_time["signal"] == "time"

    assert _signals_for(payload, "proj.tbl_g") == []


def test_signal_types_and_evidence_shape(tmp_path: Path) -> None:
    """六类信号齐全，每行都能回到 table / column 证据。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    result = _run(analysis_dir, rules_path)
    payload = result.signals

    assert list(payload) == [
        "count",
        "note",
        "rules_version",
        "table_count",
        "type_counts",
        "signals",
    ]
    assert payload["rules_version"] == "1.0"
    assert set(payload["type_counts"]) == {
        "transaction_id",
        "transaction_measure",
        "event_time",
        "status",
        "multi_object",
        "lifecycle",
    }
    assert payload["count"] == len(payload["signals"])
    assert payload["count"] == result.signal_count

    for row in payload["signals"]:
        assert row["source"] in {"column", "table"}
        assert row["evidence"][0]["table_key"] == row["table_key"]
        if row["source"] == "column":
            assert row["column_name"]
        else:
            assert row["column_name"] is None


def test_table_level_signals(tmp_path: Path) -> None:
    """multi_object 需要 ≥2 Object；lifecycle 需要 status + event_time。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    payload = _run(analysis_dir, rules_path).signals

    multi_objects = {
        str(item["table_key"])
        for item in payload["signals"]
        if item["signal_type"] == "multi_object"
    }
    assert "proj.tbl_b" in multi_objects
    assert "proj.tbl_f" in multi_objects
    assert "proj.tbl_c" not in multi_objects

    lifecycles = {
        str(item["table_key"])
        for item in payload["signals"]
        if item["signal_type"] == "lifecycle"
    }
    assert "proj.tbl_b" in lifecycles
    assert "proj.tbl_c" in lifecycles
    # 只有 status 没有 event_time 的表不是 lifecycle。
    assert "proj.tbl_e" not in lifecycles


def test_signals_without_candidate_are_retained(tmp_path: Path) -> None:
    """证据不足：只保留 signal，不生成 candidate。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    result = _run(analysis_dir, rules_path)

    # {customer, store} 的表只有 multi_object 表级信号，够不到任何 Level。
    assert _signals_for(result.signals, "proj.tbl_f")
    assert _process_or_none(result.processes, "customer", "store") is None

    # {customer} 只有列级信号，同样不生成 candidate。
    assert _signals_for(result.signals, "proj.tbl_c")
    assert _process_or_none(result.processes, "customer") is None


def _process_or_none(payload: dict[str, Any], *objects: str) -> dict[str, Any] | None:
    wanted = sorted(objects)

    for item in payload["processes"]:
        if sorted(item["objects"]) == wanted:
            return item

    return None


# ============================================================
# 4. 分组、Level 与强度
# ============================================================


def test_grouping_is_disjoint_and_deduplicated(tmp_path: Path) -> None:
    """按精确 Object 集合分组：一张表只进一个 candidate，重复信号不重复建候选。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    processes = _run(analysis_dir, rules_path).processes["processes"]

    seen_objects = [tuple(sorted(item["objects"])) for item in processes]
    assert len(seen_objects) == len(set(seen_objects))

    grouped = _process(_run(analysis_dir, rules_path).processes, "order", "product")
    measures = {
        item["signal"]
        for item in grouped["signals"]
        if item["signal_type"] == "transaction_measure"
    }
    assert measures == {"amount", "quantity"}

    # order_line 同时属于 {order, product}，不会另起一个 candidate。
    order_line_processes = [
        item
        for item in processes
        if "proj.tbl_b" in item["tables"]
    ]
    assert len(order_line_processes) == 1


def test_level_and_strength_mapping(tmp_path: Path) -> None:
    """Level 3 → strong，Level 1 → weak；process_evidence_strength 是确定性映射。"""

    assert process_evidence_strength(["level_3", "level_1"]) == PROCESS_STRENGTH_STRONG
    assert process_evidence_strength(["level_2"]) == PROCESS_STRENGTH_MODERATE
    assert process_evidence_strength(["level_1"]) == PROCESS_STRENGTH_WEAK

    analysis_dir, rules_path = _pipeline(tmp_path)
    result = _run(analysis_dir, rules_path)

    order_only = _process(result.processes, "order")
    assert order_only["levels"] == ["level_1"]
    assert order_only["process_evidence_strength"] == PROCESS_STRENGTH_WEAK
    assert order_only["evidence"]["object_relationship"] == 0
    assert "object relationship evidence missing" in order_only["unresolved_questions"]

    linked = _process(result.processes, "order", "product")
    assert linked["levels"] == ["level_1", "level_2", "level_3"]
    assert linked["process_evidence_strength"] == PROCESS_STRENGTH_STRONG
    assert linked["evidence"]["sql"] >= 1
    assert linked["evidence"]["lineage"] >= 1

    assert result.process_strength_counts[PROCESS_STRENGTH_WEAK] == 1
    assert result.process_strength_counts[PROCESS_STRENGTH_STRONG] == (
        result.process_count - 1
    )


def test_process_key_and_stable_ordering(tmp_path: Path) -> None:
    """process_key 形如 process_candidate_001，按 canonical signature 稳定编号。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    processes = _run(analysis_dir, rules_path).processes["processes"]

    keys = [item["process_key"] for item in processes]
    assert all(re.fullmatch(r"process_candidate_\d{3}", key) for key in keys)
    assert keys == sorted(keys)

    signatures = [item["canonical_signature"] for item in processes]
    assert signatures == sorted(signatures)
    assert all(
        signature.startswith("objects=") and "|signals=" in signature
        for signature in signatures
    )


def test_no_process_name_and_no_simple_object_mapping(tmp_path: Path) -> None:
    """不命名 Process、不做 Object ↔ Process 一对一映射。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    result = _run(analysis_dir, rules_path)

    for item in result.processes["processes"]:
        assert "process_name" not in item
        assert len(item["objects"]) >= 1
        assert len(item["signals"]) >= 1
        assert item["status"] == "candidate"
        assert item["human_validated"] is False

    report = result.summary
    assert "Sales Process" not in report
    assert "sales_process" not in report
    assert "不会产出某个 Object 对应一个 Process" in report

    # 同一个 Object（order）出现在多个 candidate 里，不是一对一映射。
    order_processes = [
        item for item in result.processes["processes"] if "order" in item["objects"]
    ]
    assert len(order_processes) >= 2


# ============================================================
# 5. 人工确认
# ============================================================


def test_human_validated_requires_confirmed_tables(tmp_path: Path) -> None:
    """只有组内全部表都在 review-checklist.md 里 confirmed 才算人工确认。"""

    analysis_dir, rules_path = _pipeline(tmp_path)

    # 只确认 order_master：{order} 这个单表 candidate 才成立。
    _write_checklist(analysis_dir, "| proj.tbl_e | 销售 | 订单 | confirmed |")
    result = _run(analysis_dir, rules_path)

    assert _process(result.processes, "order")["human_validated"] is True
    assert _process(result.processes, "order")["confirmed_table_count"] == 1
    assert _process(result.processes, "order", "product")["human_validated"] is False
    assert _process(result.processes, "order", "product")["confirmed_table_count"] == 0

    # 未进入清单的表不能视为 confirmed。
    _write_checklist(analysis_dir, "| proj.tbl_e | 销售 | 订单 | pending |")
    pending = _run(analysis_dir, rules_path)
    assert _process(pending.processes, "order")["human_validated"] is False


def test_process_checklist_carry_over(tmp_path: Path) -> None:
    """回填 process-review-checklist.md 后重跑：名称保留、confirmed 生效。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    first = _run(analysis_dir, rules_path)
    key = _process(first.processes, "order")["process_key"]

    _write_process_checklist(
        analysis_dir,
        f"| {key} | order | 1 | status | column=2 | 订单处理流程 | true | 人工确认 |",
    )

    second = _run(analysis_dir, rules_path)
    assert _process(second.processes, "order")["human_validated"] is True

    checklist = (analysis_dir / PROCESS_CHECKLIST_INPUT_FILE).read_text(
        encoding="utf-8"
    )
    assert "订单处理流程" in checklist
    assert "| true |" in checklist
    assert "人工确认" in checklist

    # 未回填的行保持 false，不会因为跑过一次就自动确认。
    assert checklist.count("| false |") == second.process_count - 1


# ============================================================
# 6. 产物结构与报告
# ============================================================


def test_output_structure_and_report(tmp_path: Path) -> None:
    """六个产物的顶层结构固定，报告 8 节且措辞只说 candidate 与信号。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    result = _run(analysis_dir, rules_path)
    business_dir = analysis_dir / "business"

    for name in OUTPUT_FILES:
        assert (business_dir / name).exists(), name

    assert list(result.processes) == [
        "count",
        "note",
        "rules_version",
        "status_counts",
        "strength_counts",
        "level_counts",
        "processes",
    ]
    assert list(result.process_tables) == ["count", "note", "status_counts", "tables"]
    assert list(result.process_objects) == ["count", "note", "objects"]

    assert result.process_count == 4
    assert result.process_table_count == 4
    assert result.process_object_count == 7
    assert set(result.process_status_counts) == {"candidate"}

    first = result.processes["processes"][0]
    assert set(first) >= {
        "process_key",
        "status",
        "human_validated",
        "canonical_signature",
        "objects",
        "tables",
        "signal_types",
        "signals",
        "candidate_terms",
        "evidence",
        "evidence_sources",
        "levels",
        "process_evidence_strength",
        "grain_signals",
        "unresolved_questions",
    }
    assert set(first["evidence"]) == {
        "column",
        "table",
        "sql",
        "lineage",
        "object_relationship",
    }

    table_row = result.process_tables["tables"][0]
    assert set(table_row) == {
        "process_key",
        "table_key",
        "table_name",
        "workspace_id",
        "project",
        "objects",
        "signals",
        "evidence",
        "core_candidate",
        "status",
    }

    object_row = result.process_objects["objects"][0]
    assert set(object_row) == {
        "process_key",
        "object",
        "role",
        "object_status",
        "status",
        "table_count",
        "core_table_count",
        "signal_types",
        "relationship_count",
    }
    assert object_row["role"] == "participant"

    report = result.summary
    assert report.startswith("# M3.3 Business Process Candidate Analysis")
    for index in range(1, 9):
        assert f"## {index}." in report

    assert "存在业务关系" not in report
    assert "Sales Process" not in report
    assert "sales_process" not in report
    assert "grain not determined" in report
    assert "candidate ≠ confirmed" in report
    assert "signal ≠ process" in report
    assert "M3.4 Input Readiness" in report

    assert _read(business_dir / "processes.json") == result.processes
    assert _read(business_dir / "process-signals.json") == result.signals


def test_grain_signals_record_only(tmp_path: Path) -> None:
    """只记录 grain 相关信号，不产出 grain 结论。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    result = _run(analysis_dir, rules_path)

    for item in result.processes["processes"]:
        grain = item["grain_signals"]
        assert grain["note"] == "grain not determined"
        assert "grain" not in item
        assert set(grain) == {
            "note",
            "transaction_identifier",
            "aggregation_columns",
            "time_grouping",
        }
        assert len(grain["transaction_identifier"]["examples"]) <= 5

    order_only = _process(result.processes, "order")
    assert order_only["grain_signals"]["transaction_identifier"]["table_count"] == 1
    assert "order_id" in order_only["grain_signals"]["transaction_identifier"]["examples"]


def test_unresolved_questions(tmp_path: Path) -> None:
    """固定四条未决问题，证据缺失时条件追加。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    result = _run(analysis_dir, rules_path)

    required = [
        "process name not confirmed",
        "process semantics not confirmed",
        "grain not determined",
        "business validation required",
    ]

    for item in result.processes["processes"]:
        questions = item["unresolved_questions"]
        assert questions[:4] == required

    order_only = _process(result.processes, "order")
    assert "object relationship evidence missing" in order_only["unresolved_questions"]
    assert "sql reference evidence missing" not in order_only["unresolved_questions"]

    strong = _process(result.processes, "order", "product")
    assert strong["unresolved_questions"] == required


def test_core_candidate_and_evidence_sources(tmp_path: Path) -> None:
    """core 沿用 M2.4 / M3 定义；evidence_sources 按固定顺序列出有证据的来源。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    result = _run(analysis_dir, rules_path)

    linked = _process(result.processes, "order", "product")
    assert linked["core_table_count"] == 1
    assert linked["evidence_sources"] == [
        "column",
        "table",
        "sql",
        "lineage",
        "object_relationship",
    ]
    assert result.core_process_count >= 1

    order_only = _process(result.processes, "order")
    assert "object_relationship" not in order_only["evidence_sources"]


def test_deterministic_across_runs(tmp_path: Path) -> None:
    """两次运行字节一致（无时间戳 / 随机抽样）。"""

    analysis_dir, rules_path = _pipeline(tmp_path)
    business_dir = analysis_dir / "business"

    _run(analysis_dir, rules_path)
    first_run = {
        name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)
    }

    _run(analysis_dir, rules_path)
    second_run = {
        name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)
    }

    assert first_run == second_run


# ============================================================
# 7. CLI 黑盒
# ============================================================


def test_analyze_business_processes_command(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze-business-processes 产出 6 个文件，且不改 M2 / M3 / M3.1 / M3.2 产物。"""

    rules_path = _write_process_rules(tmp_path / "config" / "process-rules.yaml")
    monkeypatch.setenv("PROCESS_RULES_PATH", str(rules_path))

    from test_business_objects import _write_m2  # noqa: PLC0415

    _write_m2(Path("analysis"), **_m2_payloads())

    assert run_cli("analyze-business") == 0
    assert run_cli("analyze-business-quality") == 0
    assert run_cli("analyze-business-objects") == 0

    business_dir = Path("analysis/business")
    before = {path.name: path.read_bytes() for path in sorted(business_dir.iterdir())}

    assert run_cli("analyze-business-processes") == 0

    for name in OUTPUT_FILES:
        assert (business_dir / name).exists(), name

    for name, content in before.items():
        assert (business_dir / name).read_bytes() == content, name

    first_run = {
        name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)
    }

    assert run_cli("analyze-business-processes") == 0
    assert {
        name: (business_dir / name).read_bytes() for name in sorted(OUTPUT_FILES)
    } == first_run


def test_analyze_business_processes_command_fails_without_inputs(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """缺 M3.2 产物或缺配置 → 退出码 1，不写任何 M3.3 产物。"""

    rules_path = _write_process_rules(tmp_path / "config" / "process-rules.yaml")
    monkeypatch.setenv("PROCESS_RULES_PATH", str(rules_path))

    assert run_cli("analyze-business-processes") == 1
    assert not Path("analysis/business/processes.json").exists()

    missing_rules = tmp_path / "config" / "nope.yaml"
    monkeypatch.setenv("PROCESS_RULES_PATH", str(missing_rules))

    assert run_cli("analyze-business-processes") == 1

"""M2.1 Inventory Summary（analysis/inventory/summary.md）的黑盒测试。

原则：

1. 所有数字来自当前 Snapshot 的动态计算，测试里不出现真实 Snapshot 的数字。
2. Excluded（规则不满足）与 Exception（技术失败）必须分开断言。
3. Content 缺失不等于采集失败。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import assert_sandbox, write_snapshot

SECTION_HEADINGS = (
    "## 1. Executive Summary",
    "## 2. Workspace Overview",
    "## 3. DataWorks File Inventory",
    "## 4. Downstream Analysis Eligibility",
    "## 5. MaxCompute Table Inventory",
    "## 6. Collection Completeness",
    "## 7. Collection Exceptions",
    "## 8. Conclusion",
    "## 9. Definitions",
)

HARD_CODED_SNAPSHOT_NUMBERS = (
    "4,651",
    "4651",
    "3,719",
    "3719",
    "102,603",
    "102603",
    "1,449",
    "1449",
    "466337",
    "466338",
    "466339",
)


def _summary() -> str:
    return Path("analysis/inventory/summary.md").read_text(encoding="utf-8")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    assert_sandbox(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ============================================================
# 1. Summary calculation
# ============================================================


def test_summary_totals_and_workspace_rows(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """多 Workspace：总数、分 Workspace 数字与 Total 行全部来自 Snapshot。"""

    write_snapshot(
        Path("source"),
        workspaces=[
            {"id": 9001, "name": "ws_a"},
            {"id": 9002, "name": "ws_b"},
        ],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": "7001",
                "content": "SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "draft_a",
                "node_id": None,
                "content": "SELECT 2;",
            },
            {
                "workspace_id": 9002,
                "file_id": "201",
                "file_name": "etl_b",
                "node_id": "7002",
                "content": "SELECT 3;",
            },
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            },
            {
                "workspace_id": 9002,
                "table": "ads_report",
                "columns": [
                    {"name": "id", "type": "BIGINT"},
                    {"name": "ds", "type": "STRING"},
                ],
            },
        ],
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| Workspaces | 2 |" in summary
    assert "| DataWorks Files | 3 |" in summary
    assert "| Files with valid Node ID | 2 |" in summary
    assert "| Files with content available | 3 |" in summary
    assert "| MaxCompute Tables | 2 |" in summary
    assert "| MaxCompute Columns | 3 |" in summary

    assert "| ws_a | 9001 | ws_a | 2 | 1 | 2 | 1 | 1 |" in summary
    assert "| ws_b | 9002 | ws_b | 1 | 1 | 1 | 1 | 2 |" in summary
    assert "| **Total** | — | — | 3 | 2 | 3 | 2 | 3 |" in summary

    # Workspace Overview 与 MaxCompute 分表的 Total 行
    assert "| **Total** | 2 | 3 |" in summary

    # 百分比：分母为 Total Files = 3
    assert "| Total Files (Discovered) | 3 | 100.0% |" in summary
    assert "| Files with valid Node ID | 2 | 66.7% |" in summary
    assert "| Files without / invalid Node ID | 1 | 33.3% |" in summary
    assert "| Files with retrievable content | 3 | 100.0% |" in summary
    assert "| Files without content | 0 | 0.0% |" in summary
    assert "| Files eligible for downstream analysis | 2 | 66.7% |" in summary
    assert "| Files excluded from downstream analysis | 1 | 33.3% |" in summary


def test_summary_stage_funnel_and_eligibility(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Discovered / Eligible / Analyzed / Excluded / Exception 分别计数。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "committed",
                "node_id": 123,
                "content": "SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "blank_node",
                "node_id": "   ",
                "content": "SELECT 2;",
            },
        ],
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| Discovered | 2 |" in summary
    assert "| Eligible | 1 |" in summary
    assert "| Analyzed | 2 |" in summary
    assert "| Excluded | 1 |" in summary

    # Exclusion Reasons 只有代码里真实存在的 reason；占比分母 = Excluded。
    assert "| Missing Node ID | 1 | 100.0% |" in summary
    reasons = summary.split("### Exclusion Reasons")[1].split("###")[0]
    rows = [
        line
        for line in reasons.splitlines()
        if line.startswith("| ") and not line.startswith(("| Reason", "| ---"))
    ]
    assert len(rows) == 1
    assert rows[0].startswith("| Missing Node ID |")
    # prose 明确声明这些不是排除原因
    assert "`Invalid Node ID`" in reasons
    assert "`Content unavailable`" in reasons
    assert "`Unsupported file type`" in reasons


def test_summary_empty_workspace_and_missing_snapshot(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """空 Workspace 不崩；缺 DataWorks Snapshot 的 Workspace 在 Key Findings 里点名。"""

    write_snapshot(
        Path("source"),
        workspaces=[
            {"id": 9001, "name": "ws_a"},
            {"id": 9002, "name": "ws_b"},
        ],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": 123,
                "content": "SELECT 1;",
            }
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )

    # 只删 DataWorks 侧快照，保留 workspaces-index.json 中的 identity。
    import shutil

    shutil.rmtree(assert_sandbox(Path("source/dataworks/workspaces/9002")))

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| ws_a | 9001 | ws_a | 1 | 1 | 1 | 1 | 1 |" in summary
    assert "| ws_b | 9002 | ws_b | 0 | 0 | 0 | 0 | 0 |" in summary
    assert "| **Total** | — | — | 1 | 1 | 1 | 1 | 1 |" in summary
    assert "缺少 DataWorks Snapshot：9002" in summary


def test_summary_without_files_or_tables(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """没有 File、没有 Table：分母为 0 时百分比用占位符，表格仍然产出。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[],
        tables=[],
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| Workspaces | 1 |" in summary
    assert "| DataWorks Files | 0 |" in summary
    assert "| MaxCompute Tables | 0 |" in summary
    assert "| MaxCompute Columns | 0 |" in summary
    assert "| Total Files (Discovered) | 0 | — |" in summary
    assert "| ws_a | 9001 | ws_a | 0 | 0 | 0 | 0 | 0 |" in summary
    assert "_（没有被排除的 File）_" in summary
    assert "| Tables with columns | 0 |" in summary
    assert "| Tables without columns | 0 |" in summary


def test_summary_table_without_column(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Table 没有列：计入 Tables without columns，Column 总数不变。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )

    # 让 raw metadata 的 columns 数组为空（真实存在的技术形态）。
    raw_path = Path("source/maxcompute/workspaces/9001/tables/dwd_order.json")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["columns"] = []
    _write_json(raw_path, raw)

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| Total Tables | 1 |" in summary
    assert "| Total Columns | 0 |" in summary
    assert "| Tables with columns | 0 |" in summary
    assert "| Tables without columns | 1 |" in summary
    assert "| ws_a | 1 | 0 |" in summary
    assert "| **Total** | 1 | 0 |" in summary


# ============================================================
# 2. Edge cases：Content
# ============================================================


def test_content_file_missing_is_exception(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """content_file 指向的文件不在 Snapshot 中：Content 不可用 + 计入 Exception。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": 123,
                "content": "SELECT 1;",
            }
        ],
    )

    assert_sandbox(Path("source/dataworks/workspaces/9001/content/101__etl_a.sql")).unlink()

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| Files with retrievable content | 0 | 0.0% |" in summary
    assert "| Files without content | 1 | 100.0% |" in summary
    assert "| Exception | 1 |" in summary
    assert "| Medium | content_file 指向的 Snapshot 文件缺失 | 1 |" in summary
    # Content 不可用不是采集失败。
    assert "| High | GetFile 采集失败（files-index.failed_files） | 0 |" in summary


def test_missing_content_file_field_is_not_exception(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """content_file 为空是采集结果事实，不计入 Collection Exception。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": 123,
                "content": "SELECT 1;",
            }
        ],
    )

    index_path = Path("source/dataworks/workspaces/9001/files-index.json")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["files"][0]["content_file"] = None
    _write_json(index_path, index)

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| Files with retrievable content | 0 | 0.0% |" in summary
    assert "| Files without content | 1 | 100.0% |" in summary
    assert "| Exception | 0 |" in summary
    assert "| Medium | content_file 指向的 Snapshot 文件缺失 | 0 |" in summary
    assert "API 未返回 Content" in summary


# ============================================================
# 3. Collection Exceptions
# ============================================================


def test_collection_exceptions_reflect_failed_files(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """files-index.failed_files 计入 High 级采集异常。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": 123,
                "content": "SELECT 1;",
            }
        ],
    )

    index_path = Path("source/dataworks/workspaces/9001/files-index.json")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["failed_files"] = [
        {
            "file_id": "999",
            "file_name": "broken",
            "node_id": None,
            "file_type": 10,
            "error": "get_file failed",
        }
    ]
    _write_json(index_path, index)

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| High | GetFile 采集失败（files-index.failed_files） | 1 |" in summary
    # 失败条目不进 files-index.files，不影响清单总数。
    assert "| DataWorks Files | 1 |" in summary
    assert "明细见 `analysis/evidence/errors.json`" in summary


def test_inventory_stage_errors_reported_as_exceptions(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Table raw 缺失：进入 Medium 异常，且 Inventory 阶段错误计数非 0。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )

    assert_sandbox(Path("source/maxcompute/workspaces/9001/tables/dwd_order.json")).unlink()

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| Medium | Table raw 元数据缺失或解析失败 | 1 |" in summary
    assert "Inventory 阶段可恢复错误合计：1 条" in summary

    errors = _read(Path("analysis/evidence/errors.json"))
    assert errors["count"] == 1
    assert errors["errors"][0]["stage"] == "inventory"
    assert errors["errors"][0]["error_type"] == "TABLE_RAW_MISSING"


# ============================================================
# 4. Markdown 结构
# ============================================================


def test_summary_has_all_sections_and_tables(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """9 个小节、表格分隔行与右对齐列都存在。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": 123,
                "content": "SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "draft_a",
                "node_id": None,
                "content": "SELECT 2;",
            },
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    for heading in SECTION_HEADINGS:
        assert heading in summary, heading

    assert "| --- | ---: |" in summary
    assert "| Severity | Exception | Count | Impact |" in summary
    assert "| Reason | Count | Share of Excluded |" in summary
    assert "| Stage | Count | Meaning |" in summary
    assert "| Term | Definition |" in summary


def test_summary_does_not_hardcode_snapshot_numbers(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Summary 中不得出现真实 Snapshot 的数字，只允许出现本次 fixture 的数字。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": 123,
                "content": "SELECT 1;",
            }
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    for number in HARD_CODED_SNAPSHOT_NUMBERS:
        assert number not in summary, number

    assert "| DataWorks Files | 1 |" in summary
    assert "| MaxCompute Tables | 1 |" in summary
    assert "| MaxCompute Columns | 1 |" in summary


def test_summary_stays_within_inventory_scope(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Summary 不做业务建模判断，也不把 finding 写成 problem。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": 123,
                "content": "SELECT 1;",
            }
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "不包含" in summary
    assert "本节不是 M3.6 Problem" in summary
    assert "Fact / Dimension" in summary
    assert "不代表业务结论" in summary


def test_summary_is_deterministic(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """连续两次分析产出完全一致的 summary.md。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_a",
                "node_id": 123,
                "content": "SELECT 1;",
            }
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )

    assert run_cli("analyze") == 0
    first = _summary()

    assert run_cli("analyze") == 0

    assert _summary() == first

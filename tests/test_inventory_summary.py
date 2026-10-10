"""M2.1 Inventory Summary（analysis/inventory/summary.md）的黑盒测试。

原则：

1. 所有数字来自当前 Snapshot 的动态计算，测试里不出现真实 Snapshot 的数字。
2. 三类关注项分开断言：UNKNOWN（正常但需要关注）、Node ID 缺失 /
   内容不可用（资产状态事实 / 采集结果事实）、技术异常（真正异常）。
3. Content 缺失不等于采集失败。
4. Inventory Summary 只做资产盘点：资格判定、排除原因与规则命中
   属于 Scope Summary（analysis/scope/），不得出现在本报告。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import assert_sandbox, write_snapshot

SECTION_HEADINGS = (
    "## 1. 当前定位",
    "## 2. 核心职责",
    "## 3. 资产总览",
    "## 4. 工作区资产分布",
    "## 5. DataWorks 开发资产",
    "## 6. MaxCompute 数据资产",
    "## 7. 资产覆盖与完整性",
    "## 8. 需要关注的资产与异常",
    "## 9. 当前分析边界",
    "## 10. 关键指标定义",
)

HARD_CODED_SNAPSHOT_NUMBERS = (
    "4,651",
    "4651",
    "3,724",
    "3724",
    "102,702",
    "102702",
    "1,706",
    "1706",
    "1,379",
    "1379",
    "4,617",
    "4617",
    "3,272",
    "3272",
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
    """多 Workspace：总览、分布、DataWorks 与 MaxCompute 数字全部来自 Snapshot。"""

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

    # 第 3 节 · 资产总览
    assert "| 工作区 | 2 |" in summary
    assert "| DataWorks 文件 | 3 |" in summary
    assert "| 有效 Node ID 文件 | 2 |" in summary
    assert "| 内容可用文件 | 3 |" in summary
    assert "| MaxCompute 表 | 2 |" in summary
    assert "| MaxCompute 字段 | 3 |" in summary

    # 第 4 节 · 分布与合计
    assert "| ws_a | 2 | 1 | 2 | 1 | 1 |" in summary
    assert "| ws_b | 1 | 1 | 1 | 1 | 2 |" in summary
    assert "| **合计** | 3 | 2 | 3 | 2 | 3 |" in summary

    # 第 5.1 节 · 文件规模
    assert "| 文件总数（发现） | 3 |" in summary
    assert "| 已登记文件 | 3 |" in summary
    assert "| 有效 Node ID | 2 |" in summary
    assert "| 缺失 Node ID | 1 |" in summary
    assert "| 内容可用 | 3 |" in summary
    assert "| 内容不可用 | 0 |" in summary

    # 第 5.2 节 · 登记情况（发现 ≠ 登记）
    assert "| 发现文件 | 3 |" in summary
    assert "| 登记缺口 | 0 |" in summary

    # 第 5.3 节 · 文件元数据完整性（分母：登记相关行用登记文件，其余用发现文件）
    assert "| 文件总数 | 3 |" in summary
    assert "| Raw JSON 可用 | 3 | 100.0% |" in summary
    assert "| 有效 Node ID | 2 | 66.7% |" in summary
    assert "| 缺失 Node ID | 1 | 33.3% |" in summary

    # 第 5.4 节 · 内容快照状态（六态互斥，合计 = 已登记文件）
    assert "| present | 3 | 100.0% |" in summary
    assert "| not_checked | 0 | 0.0% |" in summary
    assert "| **合计** | 3 | 100.0% | 已登记文件 |" in summary

    # 第 6 节 · MaxCompute
    assert "| 表总数 | 2 |" in summary
    assert "| 有原始元数据的表 | 2 |" in summary
    assert "| 缺失原始元数据的表 | 0 |" in summary
    assert "| 有字段的表 | 2 |" in summary
    assert "| 无字段的表 | 0 |" in summary
    assert "| 字段总数 | 3 |" in summary
    assert "| 平均字段数（有字段的表） | 1.5 |" in summary

    # 第 7 节 · 覆盖与完整性
    assert "| Snapshot 发现文件 | 3 |" in summary
    assert "| Inventory 已登记 | 3 |" in summary
    assert "| Raw JSON 可用 | 3 |" in summary
    assert "| 内容文件缺失 | 0 |" in summary
    assert "| GetFile 失败 | 0 |" in summary
    assert "| Snapshot 发现表 | 2 |" in summary
    assert "| 原始表元数据 | 2 |" in summary
    assert "| 字段元数据 | 2 |" in summary
    assert "| GetTable 失败 | 0 |" in summary
    assert "登记缺口为 0" in summary


def test_summary_registration_and_node_id_tables(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """空白 Node ID 不算有效；登记与身份两张表分别计数。"""

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

    assert "| 发现文件 | 2 |" in summary
    assert "| 已登记文件 | 2 |" in summary
    assert "| 登记缺口 | 0 |" in summary

    assert "| 文件总数 | 2 |" in summary
    assert "| 有效 Node ID | 1 |" in summary
    assert "| 缺失 Node ID | 1 |" in summary
    assert "| Raw JSON 可用 | 2 | 100.0% |" in summary

    # 分析候选 / 资格口径不属于 Inventory Summary，也不写成「排除」。
    assert "| 当前分析候选 |" not in summary
    assert "占分析候选" not in summary
    assert "分析候选（Eligible）" not in summary
    assert "| Excluded |" not in summary
    assert "有效 Node ID ≠ 已分析" in summary


def test_summary_empty_workspace_and_missing_snapshot(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """空 Workspace 不崩；缺 DataWorks Snapshot 的 Workspace 在覆盖节点名。"""

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

    assert "| ws_a | 1 | 1 | 1 | 1 | 1 |" in summary
    assert "| ws_b | 0 | 0 | 0 | 0 | 0 |" in summary
    assert "| **合计** | 1 | 1 | 1 | 1 | 1 |" in summary
    assert "缺少 DataWorks Snapshot 的工作区：9002" in summary
    assert "该工作区不产出 File 清单" in summary


def test_summary_without_files_or_tables(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """没有 File、没有 Table：分母为 0 时用占位符，零状态文案出现。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[],
        tables=[],
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "| 工作区 | 1 |" in summary
    assert "| DataWorks 文件 | 0 |" in summary
    assert "| MaxCompute 表 | 0 |" in summary
    assert "| MaxCompute 字段 | 0 |" in summary
    assert "| ws_a | 0 | 0 | 0 | 0 | 0 |" in summary

    # 百分比与平均值的分母为 0 → 占位符
    assert "| 文件总数 | 0 | — |" in summary
    assert "| **合计** | 0 | — |" in summary
    assert "| 平均字段数（有字段的表） | — |" in summary

    # 第 8 节零状态
    assert "当前未发现 content_format = UNKNOWN 的文件。" in summary
    assert "当前全部文件均具备有效 Node ID。" in summary
    assert "当前全部文件在 Snapshot 中均有对应内容。" in summary
    assert "以下类别本次已检查、当前未发现异常：" in summary
    assert "Inventory 阶段可恢复错误合计：0 条" in summary


def test_summary_table_without_column(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Table 没有列：计入无字段的表，字段总数不变。"""

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

    assert "| 表总数 | 1 |" in summary
    assert "| 字段总数 | 0 |" in summary
    assert "| 有字段的表 | 0 |" in summary
    assert "| 无字段的表 | 1 |" in summary
    assert "| 字段元数据 | 0 |" in summary
    assert "| 无字段元数据 | 1 |" in summary
    assert "| ws_a | 0 | 0 | 0 | 1 | 0 |" in summary


# ============================================================
# 2. UNKNOWN 文件类型（正常但需要关注）
# ============================================================


def test_unknown_format_groups_registered_and_unregistered(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """UNKNOWN 按 file_type 分类：已登记类型与未注册类型给出不同初步判断。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
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
                "file_name": "job_a",
                "node_id": "7002",
                "file_type": 11,
                "content": "job body",
            },
            {
                "workspace_id": 9001,
                "file_id": "103",
                "file_name": "job_b",
                "node_id": "7003",
                # 99（虚拟节点）已注册；这里需要一个真正未注册的编号。
                "file_type": 999,
                "content": "job body",
            },
        ],
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    # 数量与占比：2/3
    assert "### 8.1 文件类型 UNKNOWN（正常但需要关注）" in summary
    assert "- 数量：2（占全部 DataWorks 文件 66.7%）" in summary

    # 分类表：registered 判断
    assert (
        "| file_type=11（ODPS_MR） | 1 | 33.3% | "
        "FileType 已登记，内容格式映射为 UNKNOWN（通常为非 SQL 任务形态） |" in summary
    )
    assert (
        "| file_type=999（UNKNOWN） | 1 | 33.3% | "
        "FileType 未在类型注册表登记，需人工确认类型映射（类型映射缺口候选） |" in summary
    )

    # 代表案例：总数 < 10 全部展示
    assert "总数少于 10，全部案例均已展示" in summary
    assert "| ws_a | 102 | job_a | 11 | UNKNOWN | 7002 |" in summary
    assert "| ws_a | 103 | job_b | 999 | UNKNOWN | 7003 |" in summary

    # 不把 UNKNOWN 说成错误
    assert "UNKNOWN ≠ 一定是错误" in summary

    # UNKNOWN 文件不影响「有效 Node ID」，并在元数据完整性表里照实计数
    assert "| 有效 Node ID | 3 |" in summary
    assert "| content_format = UNKNOWN | 2 | 66.7% |" in summary


def test_unknown_cases_round_robin_by_file_type(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """UNKNOWN 超过 10 个：先按 file_type 分类，再轮转选取 5 个代表案例。"""

    files: list[dict[str, Any]] = [
        {
            "workspace_id": 9001,
            "file_id": str(200 + index),
            "file_name": f"job_{index}",
            "node_id": str(8000 + index),
            "file_type": 999,
            "content": "job body",
        }
        for index in range(1, 11)
    ]
    files += [
        {
            "workspace_id": 9001,
            "file_id": str(300 + index),
            "file_name": f"mr_{index}",
            "node_id": str(9000 + index),
            "file_type": 11,
            "content": "job body",
        }
        for index in range(1, 3)
    ]

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=files,
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "- 数量：12（占全部 DataWorks 文件 100.0%）" in summary
    assert "| file_type=999（UNKNOWN） | 10 | 83.3% |" in summary
    assert "| file_type=11（ODPS_MR） | 2 | 16.7% |" in summary

    # 代表案例 = 5，且覆盖两个类别（轮转取样，确定性）
    assert "共 5 个代表案例，按 file_type 分类轮转选取" in summary
    assert "| ws_a | 201 | job_1 | 999 | UNKNOWN |" in summary
    assert "| ws_a | 301 | mr_1 | 11 | UNKNOWN |" in summary
    assert summary.count("UNKNOWN |") >= 5


# ============================================================
# 3. Node ID 缺失与内容不可用（资产状态事实 / 采集结果事实）
# ============================================================


def test_missing_node_id_cases_trimmed_to_three(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """缺失 Node ID 的文件 ≥10：数量照实计数，只展示 3 个代表案例。"""

    files = [
        {
            "workspace_id": 9001,
            "file_id": str(100 + index),
            "file_name": f"draft_{index}",
            "node_id": None,
            "content": "SELECT 1;",
        }
        for index in range(1, 13)
    ]

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=files,
    )

    assert run_cli("analyze") == 0

    summary = _summary()

    assert "### 8.2 缺失 Node ID（调度身份缺口）" in summary
    assert "- 数量：12（占全部 DataWorks 文件 100.0%）" in summary
    # 代表案例 3 个（按 file_type 轮转，本例同类型 → 取前 3 个）
    assert summary.count("未提供 Node ID（node_id 为空）") == 3
    # 不把它们写成无效资产，也不写成采集失败
    assert "不是无效资产" in summary
    assert "| High | GetFile 采集失败（files-index.failed_files） | 0 |" in summary
    # 身份维度照实计数，不换算成任何候选口径
    assert "| 缺失 Node ID | 12 |" in summary


def test_content_file_missing_is_exception(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """content_file 指向的文件不在 Snapshot 中：内容不可用 + 计入技术异常。"""

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

    # 第 5.4 节 · 内容可用
    assert "| 内容可用 | 0 |" in summary
    assert "| 内容不可用 | 1 |" in summary

    # 第 7 节 · 覆盖
    assert "| 内容文件缺失 | 1 |" in summary

    # 第 8.3 节 · 案例与状态
    assert "- 数量：1（占全部 DataWorks 文件 100.0%）" in summary
    assert (
        "| ws_a | 101 | etl_a | dataworks/workspaces/9001/content/101__etl_a.sql "
        "| 路径缺失 | content_file 指向的 Snapshot 文件缺失 |" in summary
    )

    # 第 8.4 节 · 技术异常
    assert "| Medium | content_file 指向的 Snapshot 文件缺失 | 1 |" in summary
    assert "#### content_file 指向的 Snapshot 文件缺失（代表案例）" in summary
    # Content 不可用不是采集失败。
    assert "| High | GetFile 采集失败（files-index.failed_files） | 0 |" in summary
    # 内容缺失不是 ledger 错误。
    assert "Inventory 阶段可恢复错误合计：0 条" in summary


def test_missing_content_file_field_is_not_exception(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """content_file 为空是采集结果事实，不计入技术异常。"""

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

    assert "| 内容可用 | 0 |" in summary
    assert "| 内容不可用 | 1 |" in summary
    assert "| 内容文件缺失 | 0 |" in summary

    # 第 8.3 节：状态 = 未提供
    assert "| ws_a | 101 | etl_a | — | 未提供 | 未提供 Content（content_file 为空） |" in summary
    assert "API 未返回 Content" in summary

    # 第 8.4 节：不计入
    assert "| Medium | content_file 指向的 Snapshot 文件缺失 | 0 |" in summary
    assert "不计入**本节异常" in summary


# ============================================================
# 4. 技术异常（真正异常）
# ============================================================


def test_collection_exceptions_reflect_failed_files(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """files-index.failed_files 计入 High 级技术异常，并给出定位案例。"""

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
    assert "#### GetFile 采集失败（files-index.failed_files）（代表案例）" in summary
    assert "| 9001 | 999 | — | — | get_file failed |" in summary
    assert "| GetFile 失败 | 1 |" in summary
    # 失败条目不进 files-index.files，不影响清单总数。
    assert "| 文件总数（发现） | 1 |" in summary
    assert "明细见 `analysis/evidence/errors.json`" in summary


def test_inventory_stage_errors_reported_as_exceptions(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Table raw 缺失：进入 Medium 技术异常，且 Inventory 阶段错误计数非 0。"""

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
    assert "#### Table raw 元数据缺失或解析失败（代表案例）" in summary
    assert "| 9001 | — | dwd_order |" in summary
    assert "| 缺失原始元数据的表 | 1 |" in summary
    assert "| 原始表元数据 | 0 |" in summary
    assert "Inventory 阶段可恢复错误合计：1 条" in summary

    errors = _read(Path("analysis/evidence/errors.json"))
    assert errors["count"] == 1
    assert errors["errors"][0]["stage"] == "inventory"
    assert errors["errors"][0]["error_type"] == "TABLE_RAW_MISSING"


def test_zero_exceptions_have_no_cases(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """干净 Snapshot：10 类技术异常全部为 0，且不生成任何代表案例。"""

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

    assert "### 8.4 其他技术异常（真正技术异常）" in summary
    assert "以下类别本次已检查、当前未发现异常：" in summary
    assert "（代表案例）" not in summary.split("### 8.4")[1]
    assert "| High | GetFile 采集失败（files-index.failed_files） | 0 |" in summary
    assert "| Medium | Table raw 元数据缺失或解析失败 | 0 |" in summary
    assert "计数为 0 表示本次已检查、未发生该类异常" in summary
    assert "Inventory 阶段可恢复错误合计：0 条" in summary


# ============================================================
# 5. Markdown 结构与口径
# ============================================================


def test_summary_has_all_sections_and_tables(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """10 个小节、关键表头与流水线图都存在。"""

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

    # 关键表头
    assert "| 职责 | 说明 |" in summary
    assert "| 资产类型 | 数量 | 说明 |" in summary
    assert "| 工作区 | DataWorks 文件 | 有效 Node ID | 内容可用 | MaxCompute 表 | 字段 |" in summary
    assert "| 指标 | 数量 |" in summary
    assert "| 影响级别 | 异常类型 | 数量 | 影响 |" in summary
    assert "| 指标 | 定义 |" in summary

    # 对齐行（右对齐列）
    assert "| --- | ---: |" in summary

    # 阶段流水线图
    assert "```text" in summary
    assert "Collection" in summary
    assert "Understanding" in summary


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

    assert "| DataWorks 文件 | 1 |" in summary
    assert "| MaxCompute 表 | 1 |" in summary
    assert "| MaxCompute 字段 | 1 |" in summary


def test_summary_stays_within_inventory_scope(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """Summary 不做业务建模判断，不越界成 Evidence / Understanding，不写成 Problem。"""

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

    # 边界与口径
    assert "不代表业务结论" in summary
    assert "本节不是 M3.6 Problem" in summary
    assert "资产覆盖检查，不是数据质量检查" in summary
    assert "有效 Node ID ≠ 已分析" in summary
    assert "发现 ≠ 登记 ≠ 分析" in summary
    assert "Workspace 名称本身不能作为业务建模结论" in summary

    # 不负责清单：业务建模判断留给后续阶段
    assert "- 事实表 / 维度表判断" in summary
    assert "- DWD / DWS / ADS 建模判断" in summary
    assert "- SQL 语义分析" in summary
    assert "- 血缘关系分析" in summary

    # 旧的 Stage Funnel 不复存在
    assert "| Analyzed |" not in summary
    assert "| Excluded |" not in summary
    assert "Exclusion Reasons" not in summary

    # Scope 专属统计（资格 / 排除原因 / 规则命中）不进入 Inventory Summary。
    assert "分析范围规则分类" not in summary
    assert "| SQL 候选 |" not in summary
    assert "| SQL 分析排除 |" not in summary
    assert "sql_reason_counts" not in summary
    assert "| 整体分析资格 |" not in summary
    assert "| 资格排除 |" not in summary
    assert "| 当前分析候选 |" not in summary
    assert "占分析候选" not in summary


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

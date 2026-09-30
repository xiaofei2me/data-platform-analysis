"""Analysis Summary 报告生成。

只做纯渲染：所有数字都来自已经算好的分析结果，
不允许在这里推断新的业务结论。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .inventory import Inventory
from .lineage import LineageResult
from .models import (
    ColumnProfile,
    StatementRecord,
    TableProfile,
    TableReference,
)
from .sql_analysis import ParseErrorRecord


def render_inventory_summary(inventory: Inventory) -> str:
    """生成 analysis/inventory/summary.md。"""

    lines = [
        "# M2.1 Warehouse Inventory",
        "",
        f"- Workspace：{len(inventory.workspaces)}",
        f"- DataWorks File：{len(inventory.files)}",
        f"- MaxCompute Table：{len(inventory.tables)}",
        f"- Column：{len(inventory.columns)}",
        "",
        "## Workspace",
        "",
        _table(
            ["workspace_id", "workspace_name", "project", "files", "tables"],
            [
                [
                    item.workspace_id,
                    item.workspace_name,
                    item.project,
                    item.file_count,
                    item.table_count,
                ]
                for item in inventory.workspaces
            ],
        ),
        "",
        "## 层级候选",
        "",
        _table(
            ["layer_candidate", "table_count"],
            [
                [layer, count]
                for layer, count in sorted(
                    Counter(
                        table.layer_candidate or "(未识别)" for table in inventory.tables
                    ).items()
                )
            ],
        ),
        "",
        "层级依据 table_name_prefix 推断，属于候选，不是分层结论。",
        "",
    ]

    return "\n".join(lines)


def render_lineage_summary(lineage: LineageResult) -> str:
    """生成 analysis/lineage/summary.md。"""

    cross = lineage.cross_workspace_edges

    lines = [
        "# M2.3 Table Lineage",
        "",
        f"- 血缘边（去重后）：{len(lineage.edges)}",
        f"- 跨 Workspace 血缘：{len(cross)}",
        f"- 核心表候选：{len(lineage.candidates)}",
        "",
        "## 跨 Workspace 血缘",
        "",
        _table(
            ["source", "target", "evidence"],
            [[edge.source_key, edge.target_key, len(edge.evidence)] for edge in cross],
            limit=200,
        ),
        "",
        "## 下游数量 Top 20",
        "",
        _table(
            ["table_key", "downstream", "upstream", "evidence"],
            [
                [
                    candidate.table_key,
                    candidate.downstream_count,
                    candidate.upstream_count,
                    candidate.evidence_count,
                ]
                for candidate in lineage.candidates[:20]
            ],
        ),
        "",
        "排序依据 downstream_count 降序，只反映数据流向，不代表业务价值。",
        "",
    ]

    return "\n".join(lines)


def render_profiling_summary(
    tables: list[TableProfile],
    columns: list[ColumnProfile],
) -> str:
    """生成 analysis/profiling/summary.md。"""

    partitioned = sum(1 for item in tables if (item.partition_count or 0) > 0)
    commented = sum(1 for item in columns if item.comment)

    lines = [
        "# M2.4 Data Profiling",
        "",
        f"- 表级 Profiling：{len(tables)}",
        f"- 字段级 Profiling：{len(columns)}",
        f"- 分区表：{partitioned}",
        f"- 有注释字段：{commented}",
        "",
        "profile_status = metadata_only：当前 Snapshot 没有行级数据样本，",
        "row_count / distinct_count / min / max / sample_values 全部为 null，",
        "is_candidate_key 恒为 false。",
        "",
    ]

    return "\n".join(lines)


def render_analysis_summary(context: SummaryContext) -> str:
    """生成 analysis/Summary.md。"""

    inventory = context.inventory
    status_counts = Counter(item.parse_status for item in context.statements)
    layer_counts = Counter(table.layer_candidate or "(未识别)" for table in inventory.tables)
    error_counts = Counter(
        (error.get("stage"), error.get("error_type")) for error in context.errors
    )

    lines = [
        "# Phase 2 Analysis Summary",
        "",
        "> 只读 `source/` Snapshot，产物写入 `analysis/`。",
        "> 本报告只包含事实、Candidate 与证据，不含业务结论。",
        "",
        "## 1. 概览",
        "",
        _table(
            ["指标", "数值"],
            [
                ["Workspace", len(inventory.workspaces)],
                ["DataWorks File", len(inventory.files)],
                ["MaxCompute Table", len(inventory.tables)],
                ["Column", len(inventory.columns)],
                ["SQL 语句", len(context.statements)],
                ["表引用记录", len(context.references)],
                ["血缘边", len(context.lineage.edges)],
                ["可恢复错误", len(context.errors)],
            ],
        ),
        "",
        "## 2. Workspace Inventory",
        "",
        _table(
            ["workspace_id", "workspace_name", "project", "files", "tables"],
            [
                [
                    item.workspace_id,
                    item.workspace_name,
                    item.project,
                    item.file_count,
                    item.table_count,
                ]
                for item in inventory.workspaces
            ],
        ),
        "",
        "## 3. DataWorks File Inventory",
        "",
        _table(
            ["维度", "数量"],
            [
                ["File 总数", len(inventory.files)],
                [
                    "TASK 类 File",
                    sum(1 for item in inventory.files if item.category == "TASK"),
                ],
                [
                    "SQL 格式 File",
                    sum(1 for item in inventory.files if item.content_format.upper() == "SQL"),
                ],
                [
                    "已读取到内容的 File",
                    len({item.file_id for item in context.statements}),
                ],
            ],
        ),
        "",
        "## 4. MaxCompute Table Inventory",
        "",
        _table(
            ["workspace_id", "table_count", "column_count"],
            [
                [
                    item.workspace_id,
                    sum(1 for table in inventory.tables if table.workspace_id == item.workspace_id),
                    sum(
                        1
                        for column in inventory.columns
                        if column.workspace_id == item.workspace_id
                    ),
                ]
                for item in inventory.workspaces
            ],
        ),
        "",
        "## 5. 层级候选（Layer Candidate）",
        "",
        _table(
            ["layer_candidate", "table_count"],
            [[layer, count] for layer, count in sorted(layer_counts.items())],
        ),
        "",
        "依据 table_name_prefix 推断，只能写作 layer_candidate。",
        "",
        "## 6. SQL Analysis",
        "",
        _table(
            ["parse_status", "statement_count"],
            [
                [status, status_counts.get(status, 0)]
                for status in ("success", "unsupported", "error")
            ],
        ),
        "",
        f"- 解析语句的 File：{len({item.file_id for item in context.statements})}",
        f"- 解析错误 / 不支持语句：{len(context.parse_errors)}",
        "",
        "## 7. Table References",
        "",
        _table(
            ["指标", "数值"],
            [
                ["含 source 的语句", sum(1 for r in context.references if r.source_tables)],
                ["含 target 的语句", sum(1 for r in context.references if r.target_tables)],
                ["去重 source 表", len({s for r in context.references for s in r.source_tables})],
                ["去重 target 表", len({t for r in context.references for t in r.target_tables})],
            ],
        ),
        "",
        "## 8. Table Lineage",
        "",
        _table(
            ["指标", "数值"],
            [
                ["血缘边（去重）", len(context.lineage.edges)],
                [
                    "带多条证据的边",
                    sum(1 for edge in context.lineage.edges if len(edge.evidence) > 1),
                ],
                ["跨 Workspace 血缘", len(context.lineage.cross_workspace_edges)],
            ],
        ),
        "",
        "## 9. Core Table Candidates",
        "",
        _table(
            ["table_key", "downstream", "upstream", "evidence"],
            [
                [
                    candidate.table_key,
                    candidate.downstream_count,
                    candidate.upstream_count,
                    candidate.evidence_count,
                ]
                for candidate in context.lineage.candidates[:20]
            ],
        ),
        "",
        "排序依据 downstream_count 降序，属于候选，不代表业务优先级。",
        "完整列表见 `analysis/lineage/core-table-candidates.json`。",
        "",
        "## 10. Data Profiling",
        "",
        _table(
            ["指标", "数值"],
            [
                ["表级 Profiling", len(context.table_profiles)],
                ["字段级 Profiling", len(context.column_profiles)],
                [
                    "有行级样本的表",
                    sum(1 for item in context.table_profiles if item.data_sample_available),
                ],
            ],
        ),
        "",
        "全部为 metadata_only，未伪造任何行级统计量。",
        "",
        "## 11. 错误摘要",
        "",
        _table(
            ["stage", "error_type", "count"],
            [
                [stage, error_type, count]
                for (stage, error_type), count in sorted(error_counts.items())
            ],
        ),
        "",
        "完整错误见 `analysis/errors.json`，SQL 解析错误见 `analysis/sql/parse-errors.json`。",
        "",
        "## 12. Analysis Limitations",
        "",
        *LIMITATION_BULLETS,
        "",
    ]

    return "\n".join(lines)


LIMITATION_BULLETS: tuple[str, ...] = (
    "- 只读取 `source/` Snapshot，不访问 DataWorks / MaxCompute / QuickBI 等外部 API。",
    "- 表级血缘来自 SQL 文本解析，未做 Column Lineage。",
    "- 层级、核心表均为 Candidate，不构成业务结论。",
    "- 没有行级数据样本，因此不做 null / distinct / 唯一性判断。",
    "- 调度依赖（周期任务上下游）不在本阶段范围内。",
    "- 表名前缀未命中的表不给出 layer_candidate。",
    "- 语句级解析失败的表引用无法提取，对应语句记录在 parse-errors.json。",
)


@dataclass
class SummaryContext:
    """生成 analysis/Summary.md 所需的全部输入。"""

    inventory: Inventory
    lineage: LineageResult
    statements: list[StatementRecord] = field(default_factory=list)
    references: list[TableReference] = field(default_factory=list)
    parse_errors: list[ParseErrorRecord] = field(default_factory=list)
    table_profiles: list[TableProfile] = field(default_factory=list)
    column_profiles: list[ColumnProfile] = field(default_factory=list)
    errors: list[dict[str, object]] = field(default_factory=list)


def _table(
    headers: list[object],
    rows: list[list[object]],
    limit: int | None = None,
) -> str:
    """渲染 Markdown 表格。"""

    if limit is not None and len(rows) > limit:
        rows = rows[:limit]

    if not rows:
        return "_（无数据）_"

    header = "| " + " | ".join(str(item) for item in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(item) for item in row) + " |" for row in rows]

    return "\n".join([header, separator, *body])


__all__ = [
    "LIMITATION_BULLETS",
    "SummaryContext",
    "render_analysis_summary",
    "render_inventory_summary",
    "render_lineage_summary",
    "render_profiling_summary",
]

"""Analysis Summary 报告生成。

只做纯渲染：所有数字都来自已经算好的分析结果，
不允许在这里推断新的业务结论。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .inventory import Inventory
from .lineage import LineageResult
from .models import (
    EVIDENCE_TYPE_WORKSPACE,
    EXTRACTION_METHOD_AST,
    EXTRACTION_METHOD_FALLBACK,
    LAYER_STATUS_CONFLICT,
    LAYER_STATUS_MATCH,
    LAYER_STATUS_UNKNOWN,
    ColumnProfile,
    LayerAssessment,
    StatementRecord,
    TableProfile,
    TableReference,
    is_analysis_eligible,
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
    ]

    return "\n".join(lines)


def render_lineage_summary(lineage: LineageResult) -> str:
    """生成 analysis/lineage/summary.md。"""

    cross = lineage.cross_workspace_edges

    lines = [
        "# M2.4 Table Lineage",
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
        "# M2.5 Data Profiling",
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


def render_layer_summary(
    assessments: list[LayerAssessment],
    *,
    rules_path: str | Path,
    rules_version: str,
    inventory_path: str | Path,
) -> str:
    """生成 analysis/layer/summary.md。

    只做纯渲染：status / candidate_layer / evidence 都来自 M2.2 评估结果，
    这里不产生新的判断，也不把 UNKNOWN 写成违规。
    """

    unconfigured_label = "(未配置)"
    undetermined_label = "(未确定)"
    conflict_limit = 20
    unknown_limit = 20

    status_counts = Counter(item.status for item in assessments)
    candidate_counts = Counter(
        item.candidate_layer or undetermined_label for item in assessments
    )
    workspace_counts = Counter(
        (item.workspace_id, item.workspace_name, item.workspace_layer or unconfigured_label)
        for item in assessments
    )
    conflicts = [item for item in assessments if item.status == LAYER_STATUS_CONFLICT]
    unknowns = [item for item in assessments if item.status == LAYER_STATUS_UNKNOWN]
    cross_layer_items = [item for item in assessments if item.cross_layer_hits]

    ordered_status = [
        status
        for status in (LAYER_STATUS_MATCH, LAYER_STATUS_UNKNOWN, LAYER_STATUS_CONFLICT)
        if status in status_counts
    ]

    conflict_rows: list[list[object]] = [
        [
            item.table_identifier,
            ", ".join(
                dict.fromkeys(
                    str(hit.get("layer"))
                    for hit in item.evidence
                    if hit.get("type") != EVIDENCE_TYPE_WORKSPACE
                )
            ),
        ]
        for item in conflicts
    ]

    conflict_note = (
        f"只列出前 {conflict_limit} 条，"
        "完整明细见 `analysis/layer/assessments.json`。"
        if len(conflict_rows) > conflict_limit
        else "完整明细见 `analysis/layer/assessments.json`。"
    )

    unknown_rows: list[list[object]] = [
        [item.table_identifier, item.workspace_id, item.workspace_name]
        for item in unknowns
    ]

    unknown_note = (
        f"只列出前 {unknown_limit} 条，"
        "完整明细见 `analysis/layer/assessments.json`。"
        if len(unknown_rows) > unknown_limit
        else "完整明细见 `analysis/layer/assessments.json`。"
    )

    cross_rows: list[list[object]] = [
        [
            item.table_identifier,
            item.workspace_layer,
            ", ".join(
                dict.fromkeys(str(hit.get("layer")) for hit in item.cross_layer_hits)
            ),
        ]
        for item in cross_layer_items
    ]

    cross_note = (
        f"只列出前 {conflict_limit} 条，"
        "完整明细见 `analysis/layer/assessments.json`。"
        if len(cross_rows) > conflict_limit
        else "完整明细见 `analysis/layer/assessments.json`。"
    )

    lines = [
        "# M2.2 Layer Assessment",
        "",
        f"- 参与分析的表：{len(assessments)}",
        f"- 输入：`{inventory_path}`",
        f"- 规则配置：`{rules_path}`（version {rules_version}）",
        "",
        "## Workspace Layer",
        "",
        _table(
            ["workspace_id", "workspace_name", "workspace_layer", "table_count"],
            [
                [workspace_id, workspace_name, layer, count]
                for (workspace_id, workspace_name, layer), count in sorted(
                    workspace_counts.items()
                )
            ],
        ),
        "",
        "workspace_layer 由 workspace_id 查 `workspace_layers` 得到，是结构事实，不是候选。",
        "",
        "## 状态分布",
        "",
        _table(
            ["status", "table_count"],
            [[status, status_counts[status]] for status in ordered_status],
        ),
        "",
        "## candidate_layer 分布",
        "",
        _table(
            ["candidate_layer", "table_count"],
            [
                [candidate, count]
                for candidate, count in sorted(candidate_counts.items())
            ],
        ),
        "",
        "## 未配置 Workspace",
        "",
        _table(
            ["workspace_id", "workspace_name", "table_count"],
            [
                [workspace_id, workspace_name, count]
                for (workspace_id, workspace_name, layer), count in sorted(
                    workspace_counts.items()
                )
                if layer == unconfigured_label
            ],
        ),
        "",
        "未配置的 workspace_id 不做任何推断（不按 workspace_name 猜测），一律记为 UNKNOWN。",
        "",
        "## UNKNOWN 明细",
        "",
        _table(
            ["table_identifier", "workspace_id", "workspace_name"],
            unknown_rows,
            limit=unknown_limit,
        ),
        "",
        unknown_note,
        "",
        "## 跨层命名提示",
        "",
        _table(
            ["table_identifier", "workspace_layer", "命中其他层"],
            cross_rows,
            limit=conflict_limit,
        ),
        "",
        cross_note,
        "",
        "candidate_layer 仍按 workspace_layer 判定，这里只提示表名带其他层命名前缀。",
        "",
        "## CONFLICT 明细",
        "",
        _table(
            ["table_identifier", "命中的子层"],
            conflict_rows,
            limit=conflict_limit,
        ),
        "",
        conflict_note,
        "",
        "## 说明",
        "",
        "- workspace_layer 是配置事实；candidate_layer 是子层候选，两者都不是合规结论。",
        "- CDM 是 DIM / DWD / DWS 的公共层总称，与子层不是同一级 Layer。",
        "- UNKNOWN 只表示现有 Evidence 不足以判断 CDM 子层，不代表不符合命名规范；",
        "  是否构成命名规范问题由后续 Convention Assessment 判定。",
        "- CONFLICT 表示同时命中多个不同子层，candidate_layer 留空，不擅自选择。",
        "- 只有同一张表命中分属不同子层的规则时才判定 CONFLICT；",
        "  单条 prefix 规则或多个同层 prefix 不会产生 CONFLICT。",
        "- ODS / ADS 的 candidate_layer 直接等于 workspace_layer；其他层的",
        "  prefix / suffix 命中只记入 evidence（跨层命名提示），不改变 candidate。",
        "- 只读 Inventory 输出与规则配置，不读取 SQL / Lineage / Profiling，",
        "  也不修改 Inventory 与规则配置；Inventory 更新后需重新执行本阶段。",
        "",
    ]

    return "\n".join(lines)


def render_analysis_summary(context: SummaryContext) -> str:
    """生成 analysis/Summary.md。"""

    inventory = context.inventory
    status_counts = Counter(item.parse_status for item in context.statements)
    method_counts = Counter(item.extraction_method for item in context.statements)
    error_counts = Counter(
        (error.get("stage"), error.get("error_type")) for error in context.errors
    )
    eligible_files = [item for item in inventory.files if is_analysis_eligible(item)]
    excluded_files = [item for item in inventory.files if not is_analysis_eligible(item)]
    layer_status_counts = Counter(item.status for item in context.layer_assessments)
    layer_candidate_counts = Counter(
        item.candidate_layer or "(未确定)" for item in context.layer_assessments
    )
    unconfigured_table_count = sum(
        1 for item in context.layer_assessments if item.workspace_layer is None
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
                ["DataWorks File（Snapshot 总数）", len(inventory.files)],
                ["参与 Analysis 的 File（NodeId 有效）", len(eligible_files)],
                ["排除的 File（NodeId 缺失）", len(excluded_files)],
                ["MaxCompute Table", len(inventory.tables)],
                ["Column", len(inventory.columns)],
                ["SQL 语句", len(context.statements)],
                ["表引用记录", len(context.references)],
                ["血缘边", len(context.lineage.edges)],
                ["可恢复错误", len(context.errors)],
            ],
        ),
        "",
        "Snapshot File 全量保留；只有 NodeId 有效的 File 进入 SQL / Table Reference / "
        "Lineage Analysis，NodeId 缺失的 File 不产生 SQL Evidence，也不记为错误。",
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
                ["NodeId 有效（参与 SQL Analysis）", len(eligible_files)],
                ["NodeId 缺失（仅保留在 Snapshot）", len(excluded_files)],
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
        "## 5. SQL Analysis",
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
        f"- 表引用提取方式（按语句）：ast={method_counts.get(EXTRACTION_METHOD_AST, 0)}，"
        f"fallback={method_counts.get(EXTRACTION_METHOD_FALLBACK, 0)}",
        f"- Parser Compatibility Normalization 生效语句："
        f"{sum(1 for item in context.statements if item.normalization_applied)}",
        f"- 因 NodeId 缺失被排除的 File：{len(excluded_files)}",
        "",
        "只有 NodeId 有效的 File 进入 SQL Analysis；被排除的 File 不产生任何 "
        "statement / reference / lineage 证据。",
        "",
        "Parser Compatibility Normalization 只在 syntax context 替换全角括号，"
        "string literal 与 comment 原样保留；statement.sql 仍是 raw SQL。",
        "",
        "## 6. Table References",
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
        "## 7. Table Lineage",
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
        "## 8. Core Table Candidates",
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
        "## 9. Data Profiling",
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
        "## 10. Layer Assessment（M2.2）",
        "",
        _table(
            ["指标", "数值"],
            [
                ["参与评估的表", len(context.layer_assessments)],
                ["MATCH", layer_status_counts.get(LAYER_STATUS_MATCH, 0)],
                ["UNKNOWN", layer_status_counts.get(LAYER_STATUS_UNKNOWN, 0)],
                ["CONFLICT", layer_status_counts.get(LAYER_STATUS_CONFLICT, 0)],
                ["未配置 workspace 的表", unconfigured_table_count],
                [
                    "跨层命名提示",
                    sum(
                        1
                        for item in context.layer_assessments
                        if item.cross_layer_hits
                    ),
                ],
            ],
        ),
        "",
        _table(
            ["candidate_layer", "table_count"],
            [
                [layer, count]
                for layer, count in sorted(layer_candidate_counts.items())
            ],
        ),
        "",
        "workspace_layer 是配置事实，candidate_layer 是子层候选；UNKNOWN 只表示证据不足，",
        "不代表命名违规。跨层命名提示只提示表名带其他层前缀，不改变 candidate。",
        "完整明细见 `analysis/layer/summary.md`。",
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
    "- Analysis 输入只包含 NodeId 有效的 File；NodeId 缺失的 File 不产生 SQL Evidence。",
    "- 表级血缘来自 SQL 文本解析，未做 Column Lineage。",
    "- 层级、核心表均为 Candidate，不构成业务结论。",
    "- M2.2 的 UNKNOWN 只表示现有证据不足以判定 CDM 子层，不等于命名违规。",
    "- 没有行级数据样本，因此不做 null / distinct / 唯一性判断。",
    "- 调度依赖（周期任务上下游）不在本阶段范围内。",
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
    layer_assessments: list[LayerAssessment] = field(default_factory=list)
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
    "render_layer_summary",
    "render_lineage_summary",
    "render_profiling_summary",
]

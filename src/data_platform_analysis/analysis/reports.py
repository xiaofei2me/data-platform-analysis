"""Analysis Summary 报告生成。

只做纯渲染：所有数字都来自已经算好的分析结果，
不允许在这里推断新的业务结论。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .inventory import Inventory
from .lineage import LineageResult
from .models import (
    BUSINESS_CONFIDENCE_ORDER,
    EVIDENCE_STRENGTH_MODERATE,
    EVIDENCE_STRENGTH_ORDER,
    EVIDENCE_STRENGTH_STRONG,
    EVIDENCE_STRENGTH_WEAK,
    EVIDENCE_TYPE_WORKSPACE,
    EXTRACTION_METHOD_AST,
    EXTRACTION_METHOD_FALLBACK,
    GRAIN_CANDIDATE_NOTE,
    GRAIN_EVIDENCE_ORDER,
    GRAIN_PATTERN_ORDER,
    GRAIN_REPORT_ROW_LIMIT,
    GRAIN_ROLE_ORDER,
    GRAIN_SIGNAL_AGGREGATION,
    GRAIN_SIGNAL_TIME_GROUPING,
    GRAIN_SIGNAL_TRANSACTION_IDENTIFIER,
    GRAIN_SIGNAL_TYPE_ORDER,
    GRAIN_STATUS_ORDER,
    GRAIN_UNDETERMINED_NOTE,
    GRAIN_UNRESOLVED_ORDER,
    LAYER_STATUS_CONFLICT,
    LAYER_STATUS_MATCH,
    LAYER_STATUS_UNKNOWN,
    OBJECT_STATUS_ORDER,
    PROCESS_COLUMN_SIGNAL_ORDER,
    PROCESS_LEVEL_ORDER,
    PROCESS_REPORT_ROW_LIMIT,
    PROCESS_SIGNAL_EVENT_TIME,
    PROCESS_SIGNAL_STATUS,
    PROCESS_SIGNAL_TRANSACTION_ID,
    PROCESS_SIGNAL_TRANSACTION_MEASURE,
    PROCESS_SIGNAL_TYPE_ORDER,
    PROCESS_STATUS_ORDER,
    PROCESS_STRENGTH_ORDER,
    PROCESS_UNRESOLVED_REQUIRED,
    QUALITY_DIVERSITY_BUCKETS,
    QUALITY_REPORT_SAMPLE_LIMIT,
    RELATIONSHIP_EVIDENCE_ORDER,
    RELATIONSHIP_TYPE_CANDIDATE,
    BusinessTableUnderstanding,
    BusinessTerm,
    ColumnProfile,
    DomainSummary,
    LayerAssessment,
    ObjectSummary,
    QualityChecklistRow,
    StatementRecord,
    TableProfile,
    TableReference,
    evidence_type_sort_key,
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


def render_business_summary(
    *,
    tables: list[BusinessTableUnderstanding],
    terms: list[BusinessTerm],
    domains: list[DomainSummary],
    objects: list[ObjectSummary],
    rules_path: str | Path,
    rules_version: str,
    analysis_dir: str | Path,
) -> str:
    """生成 analysis/business/summary.md。

    只做纯渲染：全部数字来自 M3 构建结果，这里不产生新的业务判断，
    也不把候选写成结论。
    """

    domain_rule_count = len(domains)
    object_rule_count = len(objects)
    domain_with_tables = sum(1 for item in domains if item.table_count)
    object_with_tables = sum(1 for item in objects if item.table_count)
    covered_count = sum(
        1 for item in tables if item.domain_candidates or item.business_object_candidates
    )
    unknown_count = sum(1 for item in tables if item.is_unknown)
    ambiguous_count = sum(1 for item in tables if item.is_ambiguous)
    strong_count = sum(1 for item in tables if item.has_strong_evidence)
    coverage = covered_count / len(tables) * 100 if tables else 0.0

    evidence_type_counts: Counter[str] = Counter(
        str(entry.get("type")) for item in tables for entry in item.evidence
    )
    domain_confidence: Counter[str] = Counter(
        candidate.confidence for item in tables for candidate in item.domain_candidates
    )
    object_confidence: Counter[str] = Counter(
        candidate.confidence
        for item in tables
        for candidate in item.business_object_candidates
    )

    ambiguous_rows: list[list[object]] = [
        [
            item.table_key,
            item.warehouse_layer or "(未确定)",
            ", ".join(
                f"{candidate.domain}({candidate.confidence})"
                for candidate in item.domain_candidates
            ),
        ]
        for item in sorted(tables, key=lambda entry: entry.table_key)
        if item.is_ambiguous
    ]
    unknown_rows: list[list[object]] = [
        [
            item.table_key,
            item.warehouse_layer or "(未确定)",
            "yes" if item.is_core_candidate else "no",
        ]
        for item in sorted(tables, key=lambda entry: entry.table_key)
        if item.is_unknown
    ]

    detail_limit = 20
    term_limit = 30
    ambiguous_note = (
        f"只列出前 {detail_limit} 条，完整明细见 `analysis/business/tables.json`。"
        if len(ambiguous_rows) > detail_limit
        else "完整明细见 `analysis/business/tables.json`。"
    )
    unknown_note = (
        f"只列出前 {detail_limit} 条，完整明细见 `analysis/business/tables.json`。"
        if len(unknown_rows) > detail_limit
        else "完整明细见 `analysis/business/tables.json`。"
    )
    term_note = (
        f"只列出前 {term_limit} 条，完整列表见 `analysis/business/terms.json`。"
        if len(terms) > term_limit
        else f"完整列表见 `analysis/business/terms.json`（共 {len(terms)} 条）。"
    )

    def category_rows(
        summaries: list[DomainSummary] | list[ObjectSummary],
        key_name: str,
    ) -> list[list[object]]:
        rows: list[list[object]] = []

        for item in summaries:
            confidence_text = (
                "，".join(f"{key}={value}" for key, value in item.confidence_counts.items())
                or "-"
            )
            evidence_text = (
                "，".join(f"{key}={value}" for key, value in item.evidence_type_counts.items())
                or "-"
            )

            rows.append(
                [
                    getattr(item, key_name),
                    item.name,
                    item.table_count,
                    confidence_text,
                    evidence_text,
                ]
            )

        return rows

    lines = [
        "# M3 Business Understanding Summary",
        "",
        "## 1. Overview",
        "",
        f"- 参与分析的表：{len(tables)}",
        f"- 业务术语候选（terms）：{len(terms)}",
        f"- Domain 候选类别：{domain_with_tables}/{domain_rule_count} 有候选表",
        f"- Object 候选类别：{object_with_tables}/{object_rule_count} 有候选表",
        f"- 至少命中一个 Domain / Object 候选的表：{covered_count}（{coverage:.1f}%）",
        f"- UNKNOWN（无任何候选）的表：{unknown_count}",
        f"- AMBIGUOUS（同时命中多个 Domain）的表：{ambiguous_count}",
        f"- 存在 high 级别候选的表：{strong_count}",
        f"- 输入：`{analysis_dir}`",
        f"- 规则配置：`{rules_path}`（version {rules_version}）",
        "",
        "## 2. Domain Candidates",
        "",
        _table(
            ["domain", "name", "table_count", "confidence", "证据构成"],
            category_rows(domains, "domain"),
        ),
        "",
        "confidence 按独立证据来源数量计算（≥3=high，2=medium，",
        "唯一来源为表注释=medium，其余唯一来源=low）；",
        "只反映证据强度，不是业务结论；命中多个 Domain 时全部保留。",
        "",
        "## 3. Business Object Candidates",
        "",
        _table(
            ["object", "name", "table_count", "confidence", "证据构成"],
            category_rows(objects, "object"),
        ),
        "",
        "业务对象与 Domain 用同一套证据与 confidence 规则，两者独立计算。",
        "",
        "## 4. Business Terms",
        "",
        _table(
            ["term", "normalized", "count"],
            [
                [item.term, item.normalized_term, item.count]
                for item in terms[:term_limit]
            ],
        ),
        "",
        term_note,
        "",
        "term 是出现次数最多的原始写法；只统计表名 / 字段名分词后剔除 stopwords 的词，",
        "不包含注释与 SQL 中的词，也不代表已确认的业务术语。",
        "",
        "## 5. Evidence Composition",
        "",
        "### 表级证据类型分布",
        "",
        _table(
            ["evidence_type", "entry_count"],
            [
                [evidence_type, evidence_type_counts[evidence_type]]
                for evidence_type in sorted(
                    evidence_type_counts,
                    key=lambda item: (evidence_type_sort_key(item), item),
                )
            ],
        ),
        "",
        "### 候选 confidence 分布",
        "",
        _table(
            ["category", *BUSINESS_CONFIDENCE_ORDER],
            [
                [
                    "domain",
                    *[domain_confidence[key] for key in BUSINESS_CONFIDENCE_ORDER],
                ],
                [
                    "object",
                    *[object_confidence[key] for key in BUSINESS_CONFIDENCE_ORDER],
                ],
            ],
        ),
        "",
        "SQL / 血缘证据只补充名称与注释未覆盖的关键词，避免同一信号重复计数。",
        "",
        "## 6. Ambiguous / Unknown",
        "",
        "### AMBIGUOUS（多个 Domain 候选）",
        "",
        _table(
            ["table_key", "warehouse_layer", "domain(confidence)"],
            ambiguous_rows,
            limit=detail_limit,
        ),
        "",
        ambiguous_note,
        "",
        "### UNKNOWN（无候选）",
        "",
        _table(
            ["table_key", "warehouse_layer", "is_core_candidate"],
            unknown_rows,
            limit=detail_limit,
        ),
        "",
        unknown_note,
        "",
        "UNKNOWN 只表示现有词典与证据无法判断业务语义，不代表表没有业务含义；",
        "AMBIGUOUS 不擅自收敛成一个 Domain，需人工判定。",
        "",
        "## 7. Limitations",
        "",
        "- 本阶段只产出 Candidate 与 Evidence，不是业务结论，也不生成业务描述；",
        "  「这张表表达什么」的判断留给后续业务分析阶段。",
        "- 层级只读取 M2.2 Layer Assessment（warehouse_layer / candidate_sub_layer），",
        "  M3 不判定层级，也不修改层级结果。",
        "- 词典来自 `config/business-rules.yaml`，词典外的业务语义无法命中，",
        "  会表现为 UNKNOWN；扩词典需要人工评审后配置。",
        "- 血缘证据把邻居表名的关键词传播到本表，可能引入误报，",
        "  因此只在名称与注释都没覆盖该关键词时才记入。",
        "- 术语分词基于标识符字面（snake_case / camelCase），没有语义消歧；",
        "  同义词（如 order / po）不会自动合并。",
        "- 本命令只读 M2 产物，不会刷新自身；M2 产物变化后需重新执行",
        "  `analyze-business`，否则 `analysis/business/` 可能停留在旧输入上。",
        "",
    ]

    return "\n".join(lines)


def _signals_text(signals: Mapping[str, Any]) -> str:
    """UNKNOWN 样本的信号摘要。"""

    return (
        f"comment={'y' if signals.get('has_table_comment') else 'n'}"
        f"/column_comment={'y' if signals.get('has_column_comment') else 'n'}"
        f"/sql={'y' if signals.get('has_sql_reference') else 'n'}"
        f"/lineage={'y' if signals.get('has_lineage_edge') else 'n'}"
        f"/terms={signals.get('business_term_count', 0)}"
    )


def render_business_quality_report(
    *,
    summary: Mapping[str, Any],
    unknown: Mapping[str, Any],
    ambiguous: Mapping[str, Any],
    evidence_quality: Mapping[str, Any],
    confidence_review: Mapping[str, Any],
    core_table_review: Mapping[str, Any],
    analysis_dir: str | Path,
) -> str:
    """生成 analysis/business/quality-assessment.md。

    只做纯渲染：全部数字来自 M3.1 构建结果，这里不产生新的业务判断，
    也不把候选写成结论。
    """

    limit = QUALITY_REPORT_SAMPLE_LIMIT

    unknown_rows: list[list[object]] = [
        [
            item.get("table_key"),
            item.get("warehouse_layer") or "(未确定)",
            "yes" if item.get("is_core_candidate") else "no",
            item.get("unknown_reason"),
            _signals_text(item.get("signals") or {}),
        ]
        for item in (unknown.get("samples") or [])[:limit]
    ]
    ambiguous_rows: list[list[object]] = [
        [
            item.get("table_key"),
            item.get("warehouse_layer") or "(未确定)",
            "yes" if item.get("is_core_candidate") else "no",
            ", ".join(str(value) for value in item.get("candidate_domains") or []) or "-",
            item.get("ambiguous_reason"),
        ]
        for item in (ambiguous.get("samples") or [])[:limit]
    ]

    core_samples = core_table_review.get("samples") or {}
    core_unknown_rows: list[list[object]] = [
        [
            item.get("table_key"),
            item.get("warehouse_layer") or "(未确定)",
            item.get("unknown_reason"),
            _signals_text(item.get("signals") or {}),
        ]
        for item in (core_samples.get("core_unknown") or [])[:limit]
    ]
    core_ambiguous_rows: list[list[object]] = [
        [
            item.get("table_key"),
            ", ".join(str(value) for value in item.get("candidate_domains") or []) or "-",
            item.get("ambiguous_reason"),
        ]
        for item in (core_samples.get("core_ambiguous") or [])[:limit]
    ]
    mismatch_rows: list[list[object]] = [
        [
            item.get("table_key"),
            item.get("tables_flag"),
            item.get("core_file_flag"),
        ]
        for item in (core_samples.get("core_flag_mismatch") or [])[:limit]
    ]

    unknown_sample_note = (
        f"只列出前 {limit} 条，完整明细见 `analysis/business/quality-assessment.json`。"
        if len(unknown.get("samples") or []) > limit
        else "完整明细见 `analysis/business/quality-assessment.json`。"
    )
    ambiguous_sample_note = (
        f"只列出前 {limit} 条，完整明细见 `analysis/business/quality-assessment.json`。"
        if len(ambiguous.get("samples") or []) > limit
        else "完整明细见 `analysis/business/quality-assessment.json`。"
    )

    lines = [
        "# M3.1 Business Understanding Quality Assessment",
        "",
        "## 1. Overview",
        "",
        f"- 参与评估的表：{summary.get('table_count', 0)}",
        f"- 业务术语候选（terms）：{summary.get('term_count', 0)}",
        f"- Domain 候选类别 / Object 候选类别："
        f"{summary.get('domain_count', 0)} / {summary.get('object_count', 0)}",
        f"- 至少命中一个候选的表（covered）：{summary.get('covered_count', 0)}",
        f"- UNKNOWN 的表：{summary.get('unknown_count', 0)}",
        f"- AMBIGUOUS 的表：{summary.get('ambiguous_count', 0)}",
        f"- 核心表候选：{summary.get('core_count', 0)}"
        f"（UNKNOWN {summary.get('core_unknown_count', 0)}，"
        f"AMBIGUOUS {summary.get('core_ambiguous_count', 0)}）",
        f"- 输入：`{analysis_dir}`",
        "",
        "本报告只评估 M3 结果的证据质量，不重新识别业务语义，也不修改任何已有产物。",
        "",
        "## 2. UNKNOWN",
        "",
        f"- UNKNOWN 的表：{unknown.get('count', 0)}",
        f"- 其中核心表候选（core_unknown）：{unknown.get('core_unknown_count', 0)}",
        "",
        "### 主因分布（by_reason，级联首个命中）",
        "",
        _table(
            ["reason", "table_count"],
            [
                [reason, count]
                for reason, count in (unknown.get("by_reason") or {}).items()
            ],
        ),
        "",
        str(unknown.get("note") or ""),
        "",
        "### 数仓层 / 子层分布",
        "",
        _table(
            ["warehouse_layer", "table_count"],
            [[key, value] for key, value in (unknown.get("by_layer") or {}).items()],
        ),
        "",
        _table(
            ["candidate_sub_layer", "table_count"],
            [[key, value] for key, value in (unknown.get("by_sub_layer") or {}).items()],
        ),
        "",
        "### 高频业务词（top_terms）",
        "",
        _table(
            ["term", "table_count"],
            [
                [item.get("term"), item.get("table_count")]
                for item in (unknown.get("top_terms") or [])
            ],
        ),
        "",
        "统计口径是「包含该词的 UNKNOWN 表数量」，词序按（表数降序，词升序）。",
        "",
        "### 样本",
        "",
        _table(
            ["table_key", "warehouse_layer", "core", "reason", "signals"],
            unknown_rows,
        ),
        "",
        unknown_sample_note,
        "",
        "## 3. AMBIGUOUS",
        "",
        f"- AMBIGUOUS 的表：{ambiguous.get('count', 0)}",
        "",
        "### 主因分布（by_reason）",
        "",
        _table(
            ["reason", "table_count"],
            [
                [reason, count]
                for reason, count in (ambiguous.get("by_reason") or {}).items()
            ],
        ),
        "",
        str(ambiguous.get("note") or ""),
        "",
        "### 候选类型分布（by_type）",
        "",
        _table(
            ["type", "table_count"],
            [
                [key, value]
                for key, value in (ambiguous.get("by_type") or {}).items()
            ],
        ),
        "",
        "### 高频业务词（top_terms）",
        "",
        _table(
            ["term", "table_count"],
            [
                [item.get("term"), item.get("table_count")]
                for item in (ambiguous.get("top_terms") or [])
            ],
        ),
        "",
        "### 样本",
        "",
        _table(
            ["table_key", "warehouse_layer", "core", "domain candidates", "reason"],
            ambiguous_rows,
        ),
        "",
        ambiguous_sample_note,
        "",
        "AMBIGUOUS 不擅自收敛成一个 Domain / Object，全部候选保留待人工判定。",
        "",
        "## 4. Evidence Quality",
        "",
        str(evidence_quality.get("note") or ""),
        "",
        "### 汇总",
        "",
        "- 有证据的表："
        f"{evidence_quality.get('table_count_with_evidence', 0)}"
        f" / {summary.get('table_count', 0)}",
        f"- 只有命名类直接证据的表：{evidence_quality.get('direct_only_table_count', 0)}",
        f"- 同一关键词重复出现的表："
        f"{evidence_quality.get('repeated_keyword_table_count', 0)}",
        "",
        "### 证据类型构成（by_source_type）",
        "",
        _table(
            ["evidence_type", "entry_count", "source_count", "table_count"],
            [
                [
                    evidence_type,
                    value.get("entry_count", 0),
                    value.get("source_count", 0),
                    value.get("table_count", 0),
                ]
                for evidence_type, value in (
                    evidence_quality.get("by_source_type") or {}
                ).items()
            ],
        ),
        "",
        "### 证据类型数分桶（diversity）",
        "",
        _table(
            ["diversity", "table", "domain candidate", "object candidate"],
            [
                [
                    bucket,
                    (evidence_quality.get("by_diversity") or {}).get(bucket, 0),
                    (
                        (evidence_quality.get("candidate_by_diversity") or {})
                        .get("domain", {})
                        .get(bucket, 0)
                    ),
                    (
                        (evidence_quality.get("candidate_by_diversity") or {})
                        .get("object", {})
                        .get(bucket, 0)
                    ),
                ]
                for bucket in QUALITY_DIVERSITY_BUCKETS
            ],
        ),
        "",
        "## 5. Confidence Review",
        "",
        str(confidence_review.get("note") or ""),
        "",
        "### 候选 confidence 分布",
        "",
        _table(
            ["category", *BUSINESS_CONFIDENCE_ORDER],
            [
                [
                    category,
                    *[
                        (confidence_review.get(category) or {}).get(level, 0)
                        for level in BUSINESS_CONFIDENCE_ORDER
                    ],
                ]
                for category in ("domain", "object", "combined")
            ],
        ),
        "",
        "### high 候选拆解",
        "",
        _table(
            ["metric", "candidate_count"],
            [
                ["high_total", confidence_review.get("high_total", 0)],
                [
                    "high_diversity(3+)",
                    (confidence_review.get("high_diversity") or {}).get("3+", 0),
                ],
                ["high_naming_only", confidence_review.get("high_naming_only", 0)],
                ["high_with_sql", confidence_review.get("high_with_sql", 0)],
                ["high_with_lineage", confidence_review.get("high_with_lineage", 0)],
                [
                    "high_repeated_keyword",
                    confidence_review.get("high_repeated_keyword", 0),
                ],
                ["high_single_keyword", confidence_review.get("high_single_keyword", 0)],
            ],
        ),
        "",
        "high_naming_only 表示 high 候选只有命名类证据（无 SQL / 血缘）；",
        "high_single_keyword 表示 high 候选只由一个关键词支撑，是最容易被词典误命中的部分。",
        "",
        "## 6. Core Table Review",
        "",
        str(core_table_review.get("note") or ""),
        "",
        _table(
            ["metric", "value"],
            [
                ["core_count", core_table_review.get("core_count", 0)],
                [
                    "core_flag_mismatch_count",
                    core_table_review.get("core_flag_mismatch_count", 0),
                ],
                ["core_unknown_count", core_table_review.get("core_unknown_count", 0)],
                [
                    "core_ambiguous_count",
                    core_table_review.get("core_ambiguous_count", 0),
                ],
                ["core_high_count", core_table_review.get("core_high_count", 0)],
                [
                    "core_low_evidence_count",
                    core_table_review.get("core_low_evidence_count", 0),
                ],
            ],
        ),
        "",
        "### 核心表 + UNKNOWN 样本",
        "",
        _table(
            ["table_key", "warehouse_layer", "reason", "signals"],
            core_unknown_rows,
        ),
        "",
        "### 核心表 + AMBIGUOUS 样本",
        "",
        _table(
            ["table_key", "domain candidates", "reason"],
            core_ambiguous_rows,
        ),
        "",
        "### core 标记不一致样本",
        "",
        _table(
            ["table_key", "tables_flag", "core_file_flag"],
            mismatch_rows,
        ),
        "",
        "复核顺序见 `analysis/business/review-checklist.md`。",
        "",
        "## 7. Limitations",
        "",
        "- 本阶段只评估不识别：不修改 M3 提取规则，不选 winner，不产生业务结论，",
        "  也不输出「某表属于销售域 / 应改成 DWD」这类判断。",
        "- UNKNOWN 只表示词典与证据不足，不代表表没有业务含义；",
        "  AMBIGUOUS 不收敛成一个候选，必须人工判定。",
        "- confidence 是按证据类型数算出的规则等级，不是业务确认；",
        "  词典误命中同样会抬高 confidence。",
        "- UNKNOWN 主因来自注释 / SQL / 词 / 血缘信号的存在性，不解析其业务含义。",
        "- 样本按稳定排序截断（每类最多 "
        f"{limit} 条），清单每个 Priority 最多 50 行，完整数据以 JSON 为准。",
        "- 本命令只读 M2 / M3 产物，不自动回退执行 analyze / analyze-business；",
        "  输入变化后需先重跑对应阶段再重新评估。",
        "",
    ]

    return "\n".join(lines)


CHECKLIST_SECTIONS: tuple[tuple[int, str, str], ...] = (
    (
        1,
        "Priority 1 — 核心表 + UNKNOWN",
        "核心表却没有业务候选：优先补注释 / 扩词典 / 补 SQL 证据。",
    ),
    (
        2,
        "Priority 2 — 核心表 + AMBIGUOUS",
        "核心表的多候选需要人工收敛，先于非核心表处理。",
    ),
    (
        3,
        "Priority 3 — 非核心表 + AMBIGUOUS",
        "多候选待人工判定，可批量处理。",
    ),
)
"""review-checklist.md 的三个复核分区（优先级从高到低）。"""

CHECKLIST_HEADERS: tuple[str, ...] = (
    "table",
    "current domain candidates",
    "current object candidates",
    "evidence",
    "human domain",
    "human object",
    "status",
    "note",
)


def render_object_graph(
    *,
    registry: Mapping[str, Any],
    associations: Mapping[str, Any],
    relationships: Mapping[str, Any],
    matrix: Mapping[str, Any],
    quality_summary: Mapping[str, Any],
    statement_count: int,
    relationship_row_limit: int,
    analysis_dir: str | Path,
) -> str:
    """生成 analysis/business/object-graph.md。

    只做纯渲染：所有数字都来自 M3.2 构建结果。措辞严格停留在
    「当前证据显示 …candidate 之间存在 table co-occurrence / SQL reference /
    lineage evidence」，不写成业务关系结论，也不推导 Business Process / Grain。
    """

    objects = list(registry.get("objects") or [])
    matrix_by_object = {str(row.get("object")): row for row in matrix.get("objects") or []}
    relationship_rows = list(relationships.get("relationships") or [])
    distribution = relationships.get("evidence_distribution") or {}
    core_rows = [row for row in relationship_rows if row.get("core_related")]

    def status_text(counts: Mapping[str, Any]) -> str:
        return "，".join(
            f"{status}={int(counts.get(status) or 0)}" for status in OBJECT_STATUS_ORDER
        )

    def evidence_types_text(row: Mapping[str, Any]) -> str:
        return "+".join(str(item) for item in row.get("evidence_types") or []) or "-"

    evidence_counts = [
        f"{evidence_type} "
        f"{int((distribution.get(evidence_type) or {}).get('entry_count') or 0)} 条"
        for evidence_type in RELATIONSHIP_EVIDENCE_ORDER
    ]
    sql_statements = int(relationships.get("sql_statement_count") or 0)

    object_rows: list[list[object]] = [
        [item.get("object"), item.get("name") or "-", item.get("status")]
        for item in objects
    ]

    table_rows: list[list[object]] = []

    for item in objects:
        matrix_row = matrix_by_object.get(str(item.get("object"))) or {}
        table_rows.append(
            [
                item.get("object"),
                item.get("table_count", 0),
                item.get("core_table_count", 0),
                ", ".join(str(value) for value in matrix_row.get("candidate_layers") or [])
                or "-",
                ", ".join(str(value) for value in matrix_row.get("domains") or []) or "-",
            ]
        )

    relationship_table_rows: list[list[object]] = [
        [
            row.get("object_a"),
            row.get("object_b"),
            row.get("relationship_type"),
            row.get("evidence_diversity"),
            row.get("evidence_strength"),
            (row.get("evidence_count") or {}).get("co_occurrence", 0),
            (row.get("evidence_count") or {}).get("sql_reference", 0),
            (row.get("evidence_count") or {}).get("lineage", 0),
            "yes" if row.get("core_related") else "no",
        ]
        for row in relationship_rows[:relationship_row_limit]
    ]
    relationship_note = (
        f"只列出前 {relationship_row_limit} 条，共 {len(relationship_rows)} 条；"
        "完整明细见 `analysis/business/object-relationships.json`。"
        if len(relationship_rows) > relationship_row_limit
        else "完整明细见 `analysis/business/object-relationships.json`。"
    )

    core_rows_text: list[list[object]] = [
        [
            f"{row.get('object_a')} ↔ {row.get('object_b')}",
            evidence_types_text(row),
            row.get("evidence_strength"),
            row.get("evidence_diversity"),
        ]
        for row in core_rows[:relationship_row_limit]
    ]
    core_note = (
        f"只列出前 {relationship_row_limit} 条，共 {len(core_rows)} 条；"
        "完整明细见 `analysis/business/object-relationships.json`。"
        if len(core_rows) > relationship_row_limit
        else "完整明细见 `analysis/business/object-relationships.json`。"
    )

    distribution_rows: list[list[object]] = [
        [
            evidence_type,
            int((distribution.get(evidence_type) or {}).get("relationship_count") or 0),
            int((distribution.get(evidence_type) or {}).get("entry_count") or 0),
        ]
        for evidence_type in RELATIONSHIP_EVIDENCE_ORDER
    ]

    return "\n".join(
        [
            "# M3.2 Business Object & Relationship Analysis",
            "",
            "## 1. Overview",
            "",
            f"- Object 数量：{registry.get('count', 0)}"
            "（来自 `analysis/business/objects.json`，M3.2 不重新分类）",
            f"- Object ↔ Table association：{associations.get('count', 0)}"
            f"（{status_text(associations.get('status_counts') or {})}）",
            f"- Object relationship：{relationships.get('count', 0)}"
            f"（其中至少一端关联核心表候选：{len(core_rows)}）",
            f"- 关系证据条数：{'，'.join(evidence_counts)}"
            f"（sql_reference 覆盖 {sql_statements} / {statement_count} 条 SQL 语句）",
            f"- M3.1 质量基线：table={quality_summary.get('table_count', 0)}，"
            f"unknown={quality_summary.get('unknown_count', 0)}，"
            f"ambiguous={quality_summary.get('ambiguous_count', 0)}",
            f"- 输入：`{analysis_dir}`",
            "",
            "本报告只建立「Object → Table → Relationship → Evidence」的证据结构，"
            "供 M3.3 Business Process 候选分析作为机器输入；"
            "它不是业务模型、不是维度 / 事实表定义，也不包含 Grain 判断。",
            "",
            "## 2. Object count",
            "",
            _table(["object", "name", "status"], object_rows),
            "",
            "status 默认是 candidate：未出现在 `review-checklist.md` 的回填结果里"
            "不等于已确认。name 为空表示该 Object 只来自人工回填，没有 M3 词典条目。",
            "",
            "## 3. Object table count",
            "",
            _table(
                [
                    "object",
                    "tables",
                    "core tables",
                    "candidate_layers",
                    "domains",
                ],
                table_rows,
            ),
            "",
            "一个 Object 可以关联多张表；candidate_layers / domains 是这些表上的"
            "候选取值集合，不是「该 Object 属于该层 / 该域」的结论。",
            "",
            "## 4. Relationship count",
            "",
            f"- 关系数量：{len(relationship_rows)}（identity = (object_a, object_b) 排序对，"
            "同表 / SQL / 血缘证据合并进同一条记录）",
            f"- relationship_type 取值：{RELATIONSHIP_TYPE_CANDIDATE}（恒定，"
            "不产出 owns / contains / belongs_to / one-to-many）",
            "",
            _table(
                [
                    "object_a",
                    "object_b",
                    "type",
                    "diversity",
                    "strength",
                    "co_occurrence",
                    "sql_reference",
                    "lineage",
                    "core",
                ],
                relationship_table_rows,
            ),
            "",
            relationship_note,
            "",
            "## 5. Evidence distribution",
            "",
            _table(
                ["evidence_type", "relationship_count", "entry_count"],
                distribution_rows,
            ),
            "",
            "- 证据条目只引用稳定标识（table_key / statement_id / lineage edge identity），"
            "不保存 SQL 原文，避免 JSON 膨胀。",
            "- evidence_strength 是证据类型数的确定性映射"
            "（1=weak，2=moderate，3=strong），不是 confidence / probability / certainty。",
            "",
            "## 6. Core object relationships",
            "",
            "只展示至少一个 endpoint 关联核心表候选的关系；"
            "core_candidate 是 M2.4 / M3 的 lineage 上下游结构指标，不是业务价值判断。",
            "",
            "读法：当前证据显示下表的 …candidate 之间存在 table co-occurrence / "
            "SQL reference / lineage evidence —— 这不是「存在业务关系」的结论。",
            "",
            _table(
                ["relationship", "evidence", "strength", "diversity"],
                core_rows_text,
            ),
            "",
            core_note,
            "",
            "## 7. Status distribution",
            "",
            "### Object 级状态",
            "",
            _table(
                ["status", "object_count"],
                [
                    [status, int((registry.get("status_counts") or {}).get(status) or 0)]
                    for status in OBJECT_STATUS_ORDER
                ],
            ),
            "",
            "### Association 级状态",
            "",
            _table(
                ["status", "association_count"],
                [
                    [
                        status,
                        int((associations.get("status_counts") or {}).get(status) or 0),
                    ]
                    for status in OBJECT_STATUS_ORDER
                ],
            ),
            "",
            "状态只来自 `review-checklist.md` 的人工回填：confirmed 要求 human object "
            "显式列出该 Object；rejected / needs_discussion 在 human object 留空时作用于"
            "该表全部机器候选；清单里没出现的表一律是 candidate。",
            "",
            "## 8. Limitations",
            "",
            "- Object 词典缺口（candidate gap）：当前只有 "
            f"{registry.get('count', 0)} 个 Object 候选，"
            "M3.2 不扩词典、不建立第二套 Object classifier，"
            "词外语义仍落在 M3 的 UNKNOWN。",
            "- candidate ≠ confirmed：机器识别结果默认 candidate，"
            "人工确认必须回填 `review-checklist.md` 后重跑本阶段。",
            "- relationship ≠ 业务关系：co_occurrence / sql_reference / lineage "
            "只是表级证据，需要人工确认后才能解释为业务关系。",
            "- 本阶段不做 Business Process、不做 Grain 判断，"
            "也不产出正式业务模型 / 维度 / 事实表 / DWD / DWS / Semantic Layer。",
            "",
        ]
    )


def _signal_type_table_counts(signals: Mapping[str, Any]) -> dict[str, int]:
    """每个信号类型覆盖的表数量（table_key 去重）。"""

    counts: dict[str, int] = {}

    seen: dict[str, set[str]] = {}

    for row in signals.get("signals") or []:
        signal_type = str(row.get("signal_type") or "")
        seen.setdefault(signal_type, set()).add(str(row.get("table_key") or "").casefold())

    for signal_type, tables in seen.items():
        counts[signal_type] = len(tables)

    return counts


def _evidence_text(row: Mapping[str, Any]) -> str:
    evidence = row.get("evidence") or {}

    return (
        f"column={int(evidence.get('column') or 0)}，"
        f"table={int(evidence.get('table') or 0)}，"
        f"sql={int(evidence.get('sql') or 0)}，"
        f"lineage={int(evidence.get('lineage') or 0)}，"
        f"object_relationship={int(evidence.get('object_relationship') or 0)}"
    )


def render_process_summary(
    *,
    signals: Mapping[str, Any],
    processes: Mapping[str, Any],
    process_tables: Mapping[str, Any],
    process_objects: Mapping[str, Any],
    inventory_table_count: int,
    object_table_count: int,
    rules_version: str,
    analysis_dir: Path | str,
) -> str:
    """生成 analysis/business/process-summary.md（8 节）。

    只做纯渲染：所有数字都来自 M3.3 构建结果。措辞严格停留在
    「process candidate + 信号 + 证据」，不命名 Business Process、不判定 Grain、
    不把 signal 说成 process，也不做 Object ↔ Process 的一对一映射。
    """

    process_rows = list(processes.get("processes") or [])
    signal_type_counts = dict(signals.get("type_counts") or {})
    signal_table_counts = _signal_type_table_counts(signals)
    core_rows = [row for row in process_rows if int(row.get("core_table_count") or 0) > 0]
    validated_rows = [row for row in process_rows if row.get("human_validated")]
    object_names = sorted(
        {str(item.get("object") or "") for item in process_objects.get("objects") or []}
    )

    def candidate_row(row: Mapping[str, Any]) -> list[object]:
        return [
            row.get("process_key"),
            ", ".join(str(item) for item in row.get("objects") or []) or "-",
            row.get("table_count", 0),
            ", ".join(str(item) for item in row.get("signal_types") or []) or "-",
            _evidence_text(row),
            ", ".join(str(item) for item in row.get("levels") or []) or "-",
            row.get("process_evidence_strength"),
        ]

    candidate_headers: list[object] = [
        "process_key",
        "objects",
        "tables",
        "signal types",
        "evidence",
        "levels",
        "strength",
    ]

    candidate_rows = [candidate_row(row) for row in process_rows]
    candidate_note = (
        f"只列出前 {PROCESS_REPORT_ROW_LIMIT} 条，共 {len(process_rows)} 条；"
        "完整明细见 `analysis/business/processes.json`。"
        if len(process_rows) > PROCESS_REPORT_ROW_LIMIT
        else "完整明细见 `analysis/business/processes.json`。"
    )

    core_rows_text = [candidate_row(row) for row in core_rows]
    core_note = (
        f"只列出前 {PROCESS_REPORT_ROW_LIMIT} 条，共 {len(core_rows)} 条；"
        "完整明细见 `analysis/business/processes.json`。"
        if len(core_rows) > PROCESS_REPORT_ROW_LIMIT
        else "完整明细见 `analysis/business/processes.json`。"
    )

    signal_rows: list[list[object]] = [
        [
            signal_type,
            int(signal_type_counts.get(signal_type) or 0),
            int(signal_table_counts.get(signal_type) or 0),
            "column" if signal_type in PROCESS_COLUMN_SIGNAL_ORDER else "table",
        ]
        for signal_type in PROCESS_SIGNAL_TYPE_ORDER
    ]

    evidence_totals = {
        source: sum(
            int((row.get("evidence") or {}).get(source) or 0) for row in process_rows
        )
        for source in (
            "column",
            "table",
            "sql",
            "lineage",
            "object_relationship",
        )
    }

    missing_sql = sum(
        1 for row in process_rows if not int((row.get("evidence") or {}).get("sql") or 0)
    )
    missing_lineage = sum(
        1
        for row in process_rows
        if not int((row.get("evidence") or {}).get("lineage") or 0)
    )
    missing_relationship = sum(
        1
        for row in process_rows
        if not int((row.get("evidence") or {}).get("object_relationship") or 0)
    )

    grain_transaction = sum(
        1
        for row in process_rows
        if int(
            ((row.get("grain_signals") or {}).get(GRAIN_SIGNAL_TRANSACTION_IDENTIFIER) or {}).get(
                "table_count"
            )
            or 0
        )
        > 0
    )
    grain_time = sum(
        1
        for row in process_rows
        if int(
            ((row.get("grain_signals") or {}).get(GRAIN_SIGNAL_TIME_GROUPING) or {}).get(
                "table_count"
            )
            or 0
        )
        > 0
    )

    status_text = "，".join(
        f"{status}={int((processes.get('status_counts') or {}).get(status) or 0)}"
        for status in PROCESS_STATUS_ORDER
    )
    strength_text = "，".join(
        f"{strength}={int((processes.get('strength_counts') or {}).get(strength) or 0)}"
        for strength in PROCESS_STRENGTH_ORDER
    )
    level_counts = processes.get("level_counts") or {}
    level_text = "，".join(
        f"{level}={int(level_counts.get(level) or 0)}" for level in PROCESS_LEVEL_ORDER
    )

    return "\n".join(
        [
            "# M3.3 Business Process Candidate Analysis",
            "",
            "## 1. Overview",
            "",
            f"- Inventory 表数量：{inventory_table_count}",
            f"- 参与 Object 的表数量：{object_table_count}"
            "（来自 `analysis/business/object-tables.json`，M3.3 不重新识别 Object）",
            f"- Process Signal 行数：{signals.get('count', 0)}"
            f"（覆盖 {signals.get('table_count', 0)} 张表）",
            f"- Process candidate 数量：{processes.get('count', 0)}（{status_text}）",
            f"- 过程证据强度：{strength_text}（Level 分布：{level_text}）",
            f"- 参与的 Object 数量：{len(object_names)}"
            f"（{', '.join(object_names) or '-'}）",
            f"- Core 表候选：{sum(int(row.get('core_table_count') or 0) for row in process_rows)}"
            f"（含核心表候选的 candidate：{len(core_rows)}）",
            f"- 人工已确认的 candidate：{len(validated_rows)} / {len(process_rows)}",
            f"- Signal 规则版本：{rules_version}（`config/process-rules.yaml`）",
            f"- 输入：`{analysis_dir}`",
            "",
            "本报告只产出 **Business Process Candidate**：它由 Process Signal、"
            "Object 参与、SQL / 血缘 / 关系证据共同支撑，"
            "既不是已确认的业务过程，也不是 Object ↔ Process 的简单映射"
            "（不会产出某个 Object 对应一个 Process 这种一对一结论）。",
            "",
            "## 2. Process Signals",
            "",
            _table(
                ["signal_type", "signal rows", "tables", "source"],
                signal_rows,
            ),
            "",
            "- 列级信号来自 `config/process-rules.yaml` 的字段名匹配"
            "（分词后连续子序列，忽略大小写）；表级信号由 M3.2 association 与列级信号推导。",
            "- **Signal ≠ Process**：命中信号只说明字段 / 表上具备某类过程特征；"
            "证据不足时只保留信号，不生成 candidate。",
            "",
            "## 3. Process Candidates",
            "",
            _table(candidate_headers, candidate_rows, limit=PROCESS_REPORT_ROW_LIMIT),
            "",
            candidate_note,
            "",
            "读法：每个 candidate 是「一组精确 Object 集合 + 这组表上的信号 + 证据」；"
            "process_key 是机器编号，本阶段不产出 process name。",
            "",
            "## 4. Core Process Candidates",
            "",
            "只展示包含至少一张核心表候选的 candidate；"
            "core_candidate 是 M2.4 / M3 的 lineage 上下游结构指标，不是业务价值判断。",
            "",
            _table(candidate_headers, core_rows_text, limit=PROCESS_REPORT_ROW_LIMIT),
            "",
            core_note,
            "",
            "## 5. Evidence Sources",
            "",
            _table(
                ["evidence source", "total"],
                [
                    ["column（列级信号行）", evidence_totals["column"]],
                    ["table（表级信号行）", evidence_totals["table"]],
                    ["sql（被 SQL 引用的表）", evidence_totals["sql"]],
                    ["lineage（参与血缘的表）", evidence_totals["lineage"]],
                    [
                        "object_relationship（M3.2 关系对）",
                        evidence_totals["object_relationship"],
                    ],
                ],
            ),
            "",
            "SQL / 血缘证据按表归属到 candidate；关系证据来自 "
            "`analysis/business/object-relationships.json` 的排序 Object 对。",
            "",
            "## 6. Unresolved Questions",
            "",
            "每个 candidate 都固定带有以下未决问题（未决 ≠ 失败，必须人工回答）：",
            "",
            *[f"- {question}" for question in PROCESS_UNRESOLVED_REQUIRED],
            "",
            "按证据缺失条件追加：",
            "",
            f"- `sql reference evidence missing`：{missing_sql} / {len(process_rows)} 个 candidate",
            f"- `lineage evidence missing`：{missing_lineage} / {len(process_rows)} 个 candidate",
            "- `object relationship evidence missing`："
            f"{missing_relationship} / {len(process_rows)} 个 candidate",
            "",
            f"Grain 状态：{GRAIN_UNDETERMINED_NOTE} —— 本阶段只记录 grain signals，"
            "不给出 grain 结论。",
            "",
            "## 7. Limitations",
            "",
            "- candidate ≠ confirmed：process candidate 默认 candidate，"
            "机器阶段不产出 confirmed process；"
            "确认必须回填 `process-review-checklist.md` 后重跑本阶段。",
            "- signal ≠ process：字段命中 transaction / measure / time / status "
            "只是信号，多个信号叠加也仍需人工确认其是否构成一个业务过程。",
            "- core ≠ 业务重要性：core_table_count 只是 M2.4 / M3 的 lineage 结构指标。",
            "- object relationship ≠ 业务关系：M3.3 只把关系当作 candidate 之间的证据来源。",
            "- 未命名、未判 Grain、未做 Object ↔ Process 一对一映射："
            "本阶段不产出 process name、DWD / DWS / 事实表 / 维度表结论。",
            "",
            "## 8. M3.4 Input Readiness",
            "",
            "可直接作为 M3.4 Grain Candidate Analysis 的机器输入：",
            "",
            f"- `process-signals.json`：{signals.get('count', 0)} 条信号行，"
            f"其中 transaction 标识 "
            f"{int(signal_type_counts.get(PROCESS_SIGNAL_TRANSACTION_ID) or 0)} 行、"
            f"度量 {int(signal_type_counts.get(PROCESS_SIGNAL_TRANSACTION_MEASURE) or 0)} 行、"
            f"时间 {int(signal_type_counts.get(PROCESS_SIGNAL_EVENT_TIME) or 0)} 行、"
            f"状态 {int(signal_type_counts.get(PROCESS_SIGNAL_STATUS) or 0)} 行。",
            f"- `processes.json` 的 evidence / levels / grain_signals："
            f"{len(process_rows)} 个 candidate 已带证据来源与强度。",
            "",
            "必须人工确认后才能进入下一阶段：",
            "",
            "- process 命名：`process-review-checklist.md` 的 human_process_name"
            f"（当前已确认 {len(validated_rows)} / {len(process_rows)}）。",
            "- process 语义与边界：见第 6 节 unresolved_questions。",
            "- 表级口径：`analysis/business/review-checklist.md` 中仍为 candidate / "
            "未回填的表，不能当作已确认的过程范围。",
            "",
            f"当前数据是否足以支撑 Grain Candidate Analysis："
            f"{grain_transaction} 个 candidate 具备 transaction 标识信号、"
            f"{grain_time} 个具备时间分组信号；"
            "两者齐备的 candidate 可以从信号展开 grain 候选，"
            "其余 candidate 证据不足，必须先补证据或由人工确认。"
            f"无论哪一类，本阶段的结论都停留在 grain signals，"
            f"{GRAIN_UNDETERMINED_NOTE}。",
            "",
        ]
    )


def render_process_review_checklist(
    processes: Sequence[Mapping[str, Any]],
    carry_over: Mapping[str, Mapping[str, str]] | None = None,
) -> str:
    """生成 analysis/business/process-review-checklist.md（人工回填清单）。

    前六列由机器输出，重跑时会被覆盖；human_process_name / confirmed / note
    三列保留上一次的人工回填，未回填的一律是 false —— candidate 不会自动确认。
    """

    existing = carry_over or {}

    rows: list[list[object]] = []

    for row in processes:
        process_key = str(row.get("process_key") or "")
        previous = existing.get(process_key, {})
        confirmed = "true" if _flag(previous.get("confirmed", "")) else "false"

        rows.append(
            [
                process_key,
                ", ".join(str(item) for item in row.get("objects") or []) or "-",
                row.get("table_count", 0),
                ", ".join(str(item) for item in row.get("signal_types") or []) or "-",
                _evidence_text(row),
                previous.get("human_process_name", "").strip(),
                confirmed,
                previous.get("note", "").strip(),
            ]
        )

    return "\n".join(
        [
            "# M3.3 Process Review Checklist",
            "",
            "人工填写 human process name，并把 confirmed 从 false 改为 true 以确认该"
            " process candidate；未回填的行一律保持 false，candidate 不会自动变成"
            " confirmed process。",
            "",
            "前六列（process_key / objects / tables / signals / evidence）与 note 之外的"
            "机器列由 `analyze-business-processes` 生成，重跑会被覆盖；"
            "human_process_name / confirmed / note 三列会被保留。",
            "",
            "| process_key | objects | tables | signals | evidence | human_process_name "
            "| confirmed | note |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            *[
                "| " + " | ".join(str(item).replace("|", "\\|") for item in cells) + " |"
                for cells in rows
            ],
            "",
        ]
    )


def render_grain_summary(
    *,
    signals: Mapping[str, Any],
    candidates: Mapping[str, Any],
    grain_tables: Mapping[str, Any],
    processes: Sequence[Mapping[str, Any]],
    inventory_table_count: int,
    process_table_count: int,
    profiling: Mapping[str, Any],
    analysis_dir: Path | str,
) -> str:
    """生成 analysis/business/grain-summary.md（9 节）。

    只做纯渲染：所有数字都来自 M3.4 构建结果。措辞严格停留在
    「grain candidate + 信号 + 证据 + 未决问题」，不判 confirmed grain，
    不命名事实表 / 维度表，不把 Process 的人工确认传递成 Grain 结论。
    """

    candidate_rows = list(candidates.get("candidates") or [])
    type_counts = dict(signals.get("type_counts") or {})
    signal_table_counts = _signal_type_table_counts(signals)
    pattern_counts = dict(candidates.get("pattern_counts") or {})
    strength_counts = dict(candidates.get("strength_counts") or {})
    status_counts = dict(candidates.get("status_counts") or {})
    role_counts = dict(grain_tables.get("role_counts") or {})

    process_validated = {
        str(row.get("process_key") or ""): bool(row.get("human_validated"))
        for row in processes
    }
    validated_process_count = sum(1 for value in process_validated.values() if value)
    validated_candidate_count = sum(
        1 for row in candidate_rows if row.get("process_human_validated")
    )
    empty_key_rows = [row for row in candidate_rows if not row.get("candidate_keys")]
    strong_rows = [
        row for row in candidate_rows if row.get("strength") == EVIDENCE_STRENGTH_STRONG
    ]
    moderate_rows = [
        row for row in candidate_rows if row.get("strength") == EVIDENCE_STRENGTH_MODERATE
    ]
    weak_rows = [
        row for row in candidate_rows if row.get("strength") == EVIDENCE_STRENGTH_WEAK
    ]
    core_rows = [row for row in candidate_rows if row.get("core_candidate")]

    by_process: dict[str, list[Mapping[str, Any]]] = {}

    for row in candidate_rows:
        by_process.setdefault(str(row.get("process_candidate_id") or ""), []).append(row)

    def candidate_cell(row: Mapping[str, Any]) -> str:
        keys = [str(item) for item in row.get("candidate_keys") or []]
        return "、".join(keys) if keys else "-（空）"

    def truncated_note(total: int, name: str) -> str:
        if total > GRAIN_REPORT_ROW_LIMIT:
            return (
                f"只列出前 {GRAIN_REPORT_ROW_LIMIT} 条，共 {total} 条；"
                f"完整明细见 `analysis/business/{name}`。"
            )

        return f"完整明细见 `analysis/business/{name}`。"

    signal_table = _table(
        ["signal type", "signal rows", "tables", "source"],
        [
            [
                signal_type,
                int(type_counts.get(signal_type) or 0),
                int(signal_table_counts.get(signal_type) or 0),
                "table" if signal_type == GRAIN_SIGNAL_AGGREGATION else "column",
            ]
            for signal_type in GRAIN_SIGNAL_TYPE_ORDER
        ],
    )

    pattern_table = _table(
        ["grain_pattern", "candidates"],
        [
            [pattern, int(pattern_counts.get(pattern) or 0)]
            for pattern in GRAIN_PATTERN_ORDER
        ],
    )

    process_table = _table(
        ["process_key", "candidates", "patterns", "empty keys", "process confirmed"],
        [
            [
                process_key,
                len(rows),
                ", ".join(
                    sorted({str(row.get("grain_pattern") or "") for row in rows})
                )
                or "-",
                sum(1 for row in rows if not row.get("candidate_keys")),
                "true" if process_validated.get(process_key) else "false",
            ]
            for process_key, rows in sorted(by_process.items())
        ],
        limit=GRAIN_REPORT_ROW_LIMIT,
    )

    evidence_totals = {
        source: sum(
            sum(
                1
                for entry in row.get("evidence") or []
                if str(entry.get("source_type") or "") == source
            )
            for row in candidate_rows
        )
        for source in GRAIN_EVIDENCE_ORDER
    }
    unresolved_counts = {
        reason: sum(
            1
            for row in candidate_rows
            if reason in [str(item) for item in row.get("unresolved_reasons") or []]
        )
        for reason in GRAIN_UNRESOLVED_ORDER
    }

    strength_text = "，".join(
        f"{strength}={int(strength_counts.get(strength) or 0)}"
        for strength in EVIDENCE_STRENGTH_ORDER
    )
    status_text = "，".join(
        f"{status}={int(status_counts.get(status) or 0)}" for status in GRAIN_STATUS_ORDER
    )
    role_text = "，".join(
        f"{role}={int(role_counts.get(role) or 0)}" for role in GRAIN_ROLE_ORDER
    )

    return "\n".join(
        [
            "# M3.4 Grain Candidate Analysis",
            "",
            "## 1. Overview",
            "",
            f"- Inventory 表数量：{inventory_table_count}",
            f"- 参与 M3.3 的 (process, table) 数量：{process_table_count}",
            f"- Process candidate 数量：{len(processes)}"
            f"（人工已确认 {validated_process_count}）",
            f"- Grain Signal 行数：{signals.get('count', 0)}"
            f"（覆盖 {signals.get('table_count', 0)} 张表）",
            f"- Grain Candidate 数量：{candidates.get('count', 0)}（{status_text}）",
            "- grain_pattern 分布："
            + "，".join(
                f"{pattern}={int(pattern_counts.get(pattern) or 0)}"
                for pattern in GRAIN_PATTERN_ORDER
            ),
            f"- 证据强度：{strength_text}",
            f"- grain → table 行数：{grain_tables.get('count', 0)}（{role_text}）",
            f"- 覆盖 process 数量：{candidates.get('process_count', 0)}，"
            f"覆盖表数量：{candidates.get('table_count', 0)}",
            f"- 空 candidate_keys 的候选：{len(empty_key_rows)}"
            "（表示证据不足，不是「没有 grain」的结论）",
            f"- 绑定到已确认 process 的候选：{validated_candidate_count}",
            f"- Profiling：is_candidate_key=true 的列 "
            f"{int(profiling.get('candidate_key_count') or 0)}，"
            f"metadata_only 列 {int(profiling.get('metadata_only_column_count') or 0)}"
            f" / {int(profiling.get('column_count') or 0)}，"
            f"可用数据样本的表 {int(profiling.get('data_sample_table_count') or 0)}"
            f" / {int(profiling.get('table_count') or 0)}",
            f"- 输入：`{analysis_dir}`",
            "",
            "本报告只产出 **Grain Candidate**：它由字段形态信号、SQL / 血缘 / "
            "Object 证据共同支撑，"
            f"status 恒为 candidate（{GRAIN_CANDIDATE_NOTE}）。"
            "Process 的人工确认只作记录，不会传递成 Grain 结论。",
            "",
            "## 2. Grain Signals",
            "",
            signal_table,
            "",
            "- 列级信号来自 inventory 列名形态与 `config/process-rules.yaml` 的 "
            "process signal；表级 aggregation 信号 = 有度量信号且无事务标识信号。",
            "- **Signal ≠ Grain**：命中信号只说明字段 / 表上具备某类 grain 特征；"
            "证据不足时只保留信号，不生成候选键。",
            "",
            "## 3. Grain Candidates",
            "",
            pattern_table,
            "",
            _table(
                [
                    "grain_candidate_id",
                    "process",
                    "table",
                    "pattern",
                    "candidate keys",
                    "strength",
                    "unresolved",
                ],
                [
                    [
                        row.get("grain_candidate_id"),
                        row.get("process_candidate_id"),
                        row.get("table_key"),
                        row.get("grain_pattern"),
                        candidate_cell(row),
                        row.get("strength"),
                        ", ".join(
                            str(item) for item in row.get("unresolved_reasons") or []
                        )
                        or "-",
                    ]
                    for row in candidate_rows
                ],
                limit=GRAIN_REPORT_ROW_LIMIT,
            ),
            "",
            truncated_note(len(candidate_rows), "grain-candidates.json"),
            "",
            "读法：每个 candidate 是「一个 process 在一张表上的候选键 + 形态 + 证据」；"
            "同一 (process, table) 可能有多个候选键组合，全部保留，不挑 winner。",
            "",
            "## 4. Process → Grain",
            "",
            "按 process 汇总其 grain candidate；process 是否人工确认只作记录，"
            "不影响 grain 的 candidate 状态。",
            "",
            process_table,
            "",
            truncated_note(len(by_process), "grain-candidates.json"),
            "",
            "## 5. Evidence Sources",
            "",
            _table(
                ["evidence source", "total（候选证据条目）"],
                [
                    [source, evidence_totals[source]]
                    for source in GRAIN_EVIDENCE_ORDER
                ],
            ),
            "",
            _table(
                ["grain → table role", "rows"],
                [[role, int(role_counts.get(role) or 0)] for role in GRAIN_ROLE_ORDER],
            ),
            "",
            "- `anchor` = 候选键来自该表；`supporting` = 同一 process 下也包含全部"
            "候选键的表（每个候选最多列 5 张）。",
            "- role 只是技术角色，不是 Fact / Dimension 命名。",
            "",
            "## 6. Evidence Gaps",
            "",
            "每个候选都按固定顺序记录未决原因（未决 ≠ 失败，必须人工回答）：",
            "",
            _table(
                ["unresolved reason", "candidates"],
                [
                    [reason, unresolved_counts[reason]]
                    for reason in GRAIN_UNRESOLVED_ORDER
                ],
            ),
            "",
            f"- 空 candidate_keys：{len(empty_key_rows)} / {len(candidate_rows)}",
            f"- 空证据源（source_type 数 < 2）："
            f"{unresolved_counts.get('insufficient_evidence', 0)}",
            f"- 无 SQL 证据：{unresolved_counts.get('missing_sql_evidence', 0)}，"
            f"无血缘证据：{unresolved_counts.get('missing_lineage_evidence', 0)}",
            "",
            "## 7. Human Review",
            "",
            "回填 `analysis/business/grain-review-checklist.md` 的 "
            "human_grain_name / confirmed / note 后重跑本阶段即可保留人工输入；"
            "机器阶段不会把任何候选变成 confirmed。",
            "",
            f"- 待确认候选：{len(candidate_rows)}（其中绑定已确认 process 的 "
            f"{validated_candidate_count} 个，绑定未确认 process 的 "
            f"{len(candidate_rows) - validated_candidate_count} 个）",
            f"- Process 侧已确认：{validated_process_count} / {len(processes)}",
            f"- Core 表候选上的候选：{len(core_rows)}"
            "（core_candidate 只作证据覆盖与复核优先级）",
            "",
            "优先复核顺序建议：先看第 6 节缺口最少的候选，再看空 candidate_keys "
            "与 multiple_possible_keys 的候选。",
            "",
            "## 8. Limitations",
            "",
            f"- candidate ≠ confirmed：{GRAIN_CANDIDATE_NOTE}；"
            "机器阶段不产出 confirmed grain，确认必须回填清单后重跑。",
            "- 不伪造唯一性：Profiling 只有 metadata_only，"
            f"is_candidate_key=true 的列 "
            f"{int(profiling.get('candidate_key_count') or 0)}，"
            "因此候选键没有任何行级唯一性证明，strength 只反映证据源多样性。",
            "- 空 candidate_keys ≠ 没有 grain：它只表示当前证据不足以给出候选键。",
            "- 不命名事实表 / 维度表：role 只用 anchor / supporting，"
            "不产出 DWD / DWS / Fact / Dimension 结论。",
            "- Process 确认 ≠ Grain 确认：process_human_validated 只是记录。",
            "",
            "## 9. Next: Fact-Dimension Readiness",
            "",
            "进入 Fact-Dimension Readiness 之前需要补齐：",
            "",
            f"- 证据强度为 strong 的候选：{len(strong_rows)}，"
            f"moderate：{len(moderate_rows)}，weak：{len(weak_rows)}"
            "（strength 只是证据源数量，不代表业务正确）。",
            f"- 空 candidate_keys 的候选：{len(empty_key_rows)}，"
            "需要人工给出候选键或补充 SQL / 血缘证据。",
            f"- multiple_possible_keys 的候选："
            f"{unresolved_counts.get('multiple_possible_keys', 0)}，"
            "需要人工确认唯一形态。",
            f"- 时间语义未决：{unresolved_counts.get('time_semantics_unclear', 0)}，"
            f"聚合层级未决：{unresolved_counts.get('aggregation_level_unclear', 0)}。",
            "- 行级唯一性证据：当前 Profiling 无样本，"
            "任何「唯一」结论都必须由人工确认。",
            "",
        ]
    )


def render_grain_review_checklist(
    candidate_rows: Sequence[Mapping[str, Any]],
    *,
    carry_over: Mapping[str, Mapping[str, str]] | None = None,
    row_limit: int,
) -> str:
    """生成 analysis/business/grain-review-checklist.md（人工回填清单）。

    按 process 分组；每组最多 row_limit 行并注明总数。
    机器列由 `analyze-business-grain` 生成、重跑会被覆盖；
    human_grain_name / confirmed / note 三列保留上一次的人工回填。
    """

    existing = carry_over or {}
    lines: list[str] = [
        "# M3.4 Grain Review Checklist",
        "",
        "人工填写 human grain name，并把 confirmed 从 false 改为 true 以确认该"
        " grain candidate；未回填的行一律保持 false，candidate 不会自动变成"
        " confirmed grain。",
        "",
        "机器列（grain_candidate_id 起到 strength 为止）由 `analyze-business-grain` "
        "生成，重跑会被覆盖；human_grain_name / confirmed / note 三列会被保留。",
        "",
    ]

    grouped: dict[str, list[Mapping[str, Any]]] = {}

    for row in candidate_rows:
        grouped.setdefault(str(row.get("process_candidate_id") or ""), []).append(row)

    if not grouped:
        lines.extend(["_（无候选）_", ""])
        return "\n".join(lines)

    for process_key in sorted(grouped):
        rows = grouped[process_key]
        lines.append(f"## {process_key}")
        lines.append("")

        if len(rows) > row_limit:
            lines.append(
                f"只列出前 {row_limit} 行，共 {len(rows)} 行；"
                "其余行见 `analysis/business/grain-candidates.json`。"
            )
            lines.append("")

        lines.extend(
            [
                "| grain_candidate_id | table_key | grain_pattern | candidate_keys "
                "| strength | unresolved_reasons | human_grain_name | confirmed | note |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )

        for row in rows[:row_limit]:
            candidate_id = str(row.get("grain_candidate_id") or "")
            previous = existing.get(candidate_id, {})
            keys = [str(item) for item in row.get("candidate_keys") or []]
            cells = [
                candidate_id,
                row.get("table_key"),
                row.get("grain_pattern"),
                "、".join(keys) if keys else "-",
                row.get("strength"),
                ", ".join(str(item) for item in row.get("unresolved_reasons") or [])
                or "-",
                previous.get("human_grain_name", "").strip(),
                "true" if _flag(previous.get("confirmed", "")) else "false",
                previous.get("note", "").strip(),
            ]
            lines.append(
                "| " + " | ".join(str(item).replace("|", "\\|") for item in cells) + " |"
            )

        lines.append("")

    return "\n".join(lines)


def _flag(value: str) -> bool:
    return (value or "").strip().casefold() in {"true", "yes", "y", "1", "confirmed", "是"}


def render_review_checklist(
    *,
    rows: Sequence[QualityChecklistRow],
    row_limit: int,
) -> str:
    """生成 analysis/business/review-checklist.md。

    human domain / human object 留空待人工填写，status 初始为 pending；
    每个分区最多 row_limit 行并注明总数。
    """

    lines = [
        "# M3.1 Review Checklist",
        "",
        "人工填写 human domain / human object，确认后把 status 从 pending 改为 done；",
        "note 里的 unknown: / ambiguous: 是评估给出的主因，可在人工复核后追加说明。",
        "",
    ]

    for priority, title, hint in CHECKLIST_SECTIONS:
        section_rows = [row for row in rows if row.priority == priority]
        shown = section_rows[:row_limit]
        body: list[list[object]] = [
            [
                row.table,
                row.domain_candidates,
                row.object_candidates,
                row.evidence,
                "",
                "",
                "pending",
                row.note,
            ]
            for row in shown
        ]

        lines += [
            f"## {title}（共 {len(section_rows)} 条）",
            "",
            hint,
            "",
            _table(list(CHECKLIST_HEADERS), body),
        ]

        if len(section_rows) > row_limit:
            lines += [
                "",
                f"只列出前 {row_limit} 条，共 {len(section_rows)} 条；"
                "完整样本见 `analysis/business/quality-assessment.json`。",
            ]

        lines += [""]

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
    "CHECKLIST_HEADERS",
    "CHECKLIST_SECTIONS",
    "LIMITATION_BULLETS",
    "SummaryContext",
    "render_analysis_summary",
    "render_business_quality_report",
    "render_business_summary",
    "render_inventory_summary",
    "render_grain_review_checklist",
    "render_grain_summary",
    "render_layer_summary",
    "render_lineage_summary",
    "render_object_graph",
    "render_process_review_checklist",
    "render_process_summary",
    "render_profiling_summary",
    "render_review_checklist",
]

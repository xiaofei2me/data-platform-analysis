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

from .evidence.lineage.lineage import LineageResult
from .evidence.sql.sql_analysis import ParseErrorRecord
from .inventory.inventory import (
    AssetCase,
    Inventory,
    InventorySummary,
    UnknownFormatGroup,
    WorkspaceInventorySummary,
)
from .inventory.scope import FileScopeStats
from .models import (
    AGGREGATE_ASSESSMENT_ORDER,
    BUSINESS_CONFIDENCE_ORDER,
    CURRENT_MODEL_ROLE_ORDER,
    CURRENT_MODEL_SHAPE_ORDER,
    CURRENT_STATE_NOTE,
    DIMENSION_EVIDENCE_ORDER,
    EVIDENCE_STRENGTH_MODERATE,
    EVIDENCE_STRENGTH_ORDER,
    EVIDENCE_STRENGTH_STRONG,
    EVIDENCE_STRENGTH_WEAK,
    EVIDENCE_TYPE_WORKSPACE,
    EXTRACTION_METHOD_AST,
    EXTRACTION_METHOD_FALLBACK,
    FACT_EVIDENCE_ORDER,
    FINDING_CANDIDATE_NOTE,
    FINDING_TYPE_ORDER,
    FINDING_TYPE_PRIORITY,
    GRAIN_ASSESSMENT_ORDER,
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
    MODEL_ATTRIBUTE_LIMIT,
    MODEL_CANDIDATE_NOTE,
    MODEL_CANDIDATE_TYPE_DIMENSION,
    MODEL_CANDIDATE_TYPE_FACT,
    MODEL_CANDIDATE_TYPE_RELATIONSHIP,
    MODEL_CHECKLIST_HEADERS,
    MODEL_CHECKLIST_ROW_LIMIT,
    MODEL_DIMENSION_UNRESOLVED_ORDER,
    MODEL_FACT_UNRESOLVED_ORDER,
    MODEL_PRIORITY_HINT,
    MODEL_PRIORITY_ORDER,
    MODEL_PRIORITY_TITLE,
    MODEL_REL_EVIDENCE_ORDER,
    MODEL_REL_UNRESOLVED_ORDER,
    MODEL_REPORT_ROW_LIMIT,
    MODEL_ROLE_STATUS_ORDER,
    MODEL_STATUS_ORDER,
    OBJECT_STATUS_ORDER,
    OVERLAP_CLASS_ORDER,
    PROBLEM_CANDIDATE_NOTE,
    PROBLEM_CHECKLIST_HEADERS,
    PROBLEM_CHECKLIST_ROW_LIMIT,
    PROBLEM_EVIDENCE_ORDER,
    PROBLEM_IMPACT_ORDER,
    PROBLEM_IMPACT_TITLE,
    PROBLEM_ROOT_CAUSE_ORDER,
    PROBLEM_ROOT_CAUSE_TITLE,
    PROBLEM_STATUS_ORDER,
    PROBLEM_SUMMARY_ROW_LIMIT,
    PROBLEM_TYPE_ORDER,
    PROBLEM_TYPE_PRIORITY,
    PROBLEM_TYPE_TITLE,
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
    REVIEW_CHECKLIST_HEADERS,
    REVIEW_GROUP_HINT,
    REVIEW_GROUP_ORDER,
    REVIEW_GROUP_TITLE,
    REVIEW_PRIORITY_ORDER,
    REVIEW_PRIORITY_TITLE,
    REVIEW_REPORT_ROW_LIMIT,
    UNKNOWN_REASON_ORDER,
    BusinessTableUnderstanding,
    BusinessTerm,
    ColumnProfile,
    DomainSummary,
    LayerAssessment,
    ModelChecklistRow,
    ObjectSummary,
    QualityChecklistRow,
    StatementRecord,
    TableProfile,
    TableReference,
    evidence_type_sort_key,
    is_analysis_eligible,
    normalize_human_status,
)


def render_inventory_summary(summary: InventorySummary) -> str:
    """生成 analysis/inventory/summary.md（11 节 · 数据资产基线）。

    只做纯渲染：全部数字来自 InventorySummary，
    不在这里推断业务结论，也不把「登记」写成「分析」，
    更不把 Inventory 越界成 Evidence / Understanding。
    第 11 节的规则分类统计同样只是计数，不含处置结论。
    """

    dataworks = summary.dataworks
    maxcompute = summary.maxcompute
    workspaces = summary.workspaces

    lines = [
        "# M2.1 数据资产清单（Inventory）",
        "",
        "## 1. 当前定位",
        "",
        "**Inventory 是 Analysis 阶段的资产基线层。**",
        "",
        "它基于 Snapshot 中已经采集并固化的数据，建立当前数据平台的统一资产清单，",
        "回答当前有哪些数据资产、资产在哪里、资产规模是多少、",
        "资产是否完成登记等基础问题。",
        "",
        "Inventory 不负责解释资产的业务含义，也不负责判断 SQL、血缘、",
        "数据质量或目标数仓模型。后续 Evidence、Understanding 和 Review",
        "均以 Inventory 提供的资产身份和范围作为基础。",
        "",
        "```text",
        "Collection",
        "    ↓",
        "Snapshot",
        "    ↓",
        "Inventory",
        "    ↓",
        "Evidence",
        "    ↓",
        "Understanding",
        "    ↓",
        "Review",
        "```",
        "",
        "Inventory 的输出是后续分析阶段的资产输入和范围基线，不是最终分析结论。",
        "",
        "## 2. 核心职责",
        "",
        _table(
            ["职责", "说明"],
            [
                ["资产登记", "建立 DataWorks 文件、MaxCompute 表和字段的统一清单"],
                ["资产身份", "确定 Workspace、File、Table、Column 的稳定资产身份"],
                ["资产覆盖", "统计 Snapshot 中发现、登记与缺失的资产"],
                [
                    "分析范围",
                    "标明具备进入后续分析阶段基础条件的资产（当前规则 = 有效 Node ID）",
                ],
                ["异常记录", "记录 Inventory 构建过程中发现的技术性异常"],
            ],
            alignments=["left", "left"],
        ),
        "",
        "核心原则：Inventory 的职责是建立事实上的资产基线，而不是对资产进行业务解释或价值判断。",
        "",
        "## 3. 资产总览",
        "",
        _table(
            ["资产类型", "数量", "说明"],
            [
                ["工作区", _num(len(workspaces)), "当前 Snapshot 覆盖的 DataWorks 工作区"],
                [
                    "DataWorks 文件",
                    _num(dataworks.discovered_count),
                    "当前快照中的全部文件资产",
                ],
                [
                    "有效 Node ID 文件",
                    _num(dataworks.valid_node_id_count),
                    "当前具备后续节点级分析基础的文件",
                ],
                [
                    "内容可用文件",
                    _num(dataworks.content_available_count),
                    "Snapshot 中存在对应内容",
                ],
                [
                    "MaxCompute 表",
                    _num(maxcompute.registered_count),
                    "当前快照中的全部表资产",
                ],
                [
                    "MaxCompute 字段",
                    _num(maxcompute.column_count),
                    "当前快照中的全部字段资产",
                ],
            ],
            alignments=["left", "right", "left"],
        ),
        "",
        *_workspace_distribution(workspaces),
        "",
        *_dataworks_sections(summary),
        "",
        *_maxcompute_sections(summary),
        "",
        *_coverage_sections(summary),
        "",
        *_attention_sections(summary),
        "",
        "## 9. 当前分析边界",
        "",
        "### Inventory 负责",
        "",
        "- 资产发现与登记",
        "- 资产身份",
        "- 资产规模",
        "- Workspace / Project 分布",
        "- 基础内容可用性",
        "- 后续分析候选范围",
        "- Inventory 技术异常",
        "",
        "### Inventory 不负责",
        "",
        "- 业务域判断",
        "- 业务对象识别",
        "- 业务过程识别",
        "- Grain 判断",
        "- 事实表 / 维度表判断",
        "- DWD / DWS / ADS 建模判断",
        "- SQL 语义分析",
        "- 血缘关系分析",
        "- 数据质量评价",
        "- 业务正确性判断",
        "",
        "Inventory 的输出是后续 Evidence、Understanding 和 Review 的资产输入，",
        "而不是最终的数据分析或数据建模结论。",
        "",
        "## 10. 关键指标定义",
        "",
        _table(
            ["指标", "定义"],
            [
                [
                    "工作区（Workspace）",
                    "DataWorks 工作区，稳定身份为 workspace_id；"
                    "Workspace 名称本身不能作为业务建模结论。",
                ],
                [
                    "DataWorks 文件（File）",
                    "DataWorks 工作空间内的文件资产，稳定身份为 workspace_id + file_id。",
                ],
                [
                    "File ID",
                    "DataWorks 文件的稳定标识，与 workspace_id 共同构成 File 资产身份。",
                ],
                [
                    "Node ID",
                    "DataWorks 调度节点标识，只是调度属性，不是 File 主键。",
                ],
                [
                    "有效 Node ID",
                    "node_id 非 None 且去除空白后非空，表示该文件对应已提交的调度节点。",
                ],
                [
                    "内容可用",
                    "content_file 非空且该文件在 Snapshot 中存在"
                    "（只看路径是否存在，不读内容、不判断可解析性）。",
                ],
                [
                    "分析候选（Eligible）",
                    "满足后续分析前置条件的文件；当前实现 = 具备有效 Node ID。分析候选 ≠ 已分析。",
                ],
                [
                    "MaxCompute 表",
                    "MaxCompute 表资产，稳定身份为 project.table（table_key，不含 schema）。",
                ],
                [
                    "字段（Column）",
                    "MaxCompute 表的字段，按 table_key + ordinal 定位。",
                ],
                [
                    "发现（Discovered）",
                    "Snapshot 索引（files-index / tables-index）中被发现的资产条目。",
                ],
                [
                    "登记（Registered）",
                    "成功写入 Inventory 清单（files.json / tables.json / columns.json）的资产。",
                ],
                [
                    "异常",
                    "Inventory 构建过程中发现的技术性异常（见第 8.4 节）；不含范围限制与正常形态。",
                ],
            ],
            alignments=["left", "left"],
        ),
        "",
        "关键区别：",
        "",
        "- **发现 ≠ 登记 ≠ 分析**：发现是索引条目，登记是写入清单，分析属于后续阶段；",
        "- **内容可用 ≠ SQL 可解析**：内容可用只表示 Snapshot 中存在内容文件；",
        "- **有效 Node ID ≠ SQL 分析成功**：它只是进入后续节点级分析的基础条件；",
        "- **Inventory 异常 ≠ DataWorks / MaxCompute 采集失败**："
        "前者是本阶段构建清单时发现的技术问题，采集失败记录在索引的 failed_* 条目；",
        "- **UNKNOWN ≠ 一定是错误**：UNKNOWN 可能是非 SQL 文件、"
        "未映射的合法文件类型，或真正无法识别的文件。",
        "",
    ]

    lines.extend(_scope_section(summary.scope))

    lines.extend(
        [
            "> Inventory 指标描述技术资产与登记状态，不代表业务结论。",
            "",
        ]
    )

    return "\n".join(lines)


def _scope_section(scope: FileScopeStats | None) -> list[str]:
    """第 11 节：Analysis Scope Rules 的规则分类统计（纯计数）。"""

    if scope is None:
        return ["## 11. 分析范围规则分类", "", "_（本次运行未执行规则分类）_", ""]

    total = scope.total_count

    node_rows: list[list[object]] = [
        [
            "Node ID 状态",
            "valid（有效）",
            _num(scope.node_id_valid_count),
            _pct(scope.node_id_valid_count, total),
        ],
        [
            "Node ID 状态",
            "missing（缺失）",
            _num(scope.node_id_missing_count),
            _pct(scope.node_id_missing_count, total),
        ],
        [
            "Node ID 状态",
            "invalid（无效）",
            _num(scope.node_id_invalid_count),
            _pct(scope.node_id_invalid_count, total),
        ],
    ]
    node_rows.extend(
        [
            ["节点类型（task_type）", task_type, _num(count), _pct(count, total)]
            for task_type, count in scope.task_type_counts.items()
        ]
    )

    reason_rows: list[list[object]] = [
        ["分类主因", reason, _num(count)] for reason, count in scope.reason_counts.items()
    ]
    reason_rows.extend(
        [["SQL 阻断原因", reason, _num(count)] for reason, count in scope.sql_reason_counts.items()]
    )

    # 内容状态（互斥，合计 = 登记文件）与内容期望（对缺口对象的第二维度）。
    content_rows: list[list[object]] = [
        [
            "内容状态",
            "present",
            _num(scope.content_present_count),
            _pct(scope.content_present_count, total),
            "Content 可读且非空白",
        ],
        [
            "内容状态",
            "empty_text",
            _num(scope.content_empty_text_count),
            _pct(scope.content_empty_text_count, total),
            "Content 文件存在但内容为空白",
        ],
        [
            "内容状态",
            "not_collected",
            _num(scope.content_not_collected_count),
            _pct(scope.content_not_collected_count, total),
            "content_file 为空，采集结果事实",
        ],
        [
            "内容状态",
            "path_missing",
            _num(scope.content_path_missing_count),
            _pct(scope.content_path_missing_count, total),
            "content_file 指向的文件在 Snapshot 中不存在",
        ],
        [
            "内容状态",
            "read_error",
            _num(scope.content_read_error_count),
            _pct(scope.content_read_error_count, total),
            "Content 存在但读取失败",
        ],
        [
            "内容期望",
            "缺口 · 类型不要求",
            _num(scope.content_empty_allowed_count),
            _pct(scope.content_empty_allowed_count, total),
            "该类型预期不需要 Content，属正常形态",
        ],
        [
            "内容期望",
            "缺口 · 类型要求",
            _num(scope.content_empty_unexpected_count),
            _pct(scope.content_empty_unexpected_count, total),
            "该类型预期需要 Content，记录内容缺失原因",
        ],
        [
            "内容期望",
            "缺口 · 期望未知",
            _num(scope.content_gap_unknown_expectation_count),
            _pct(scope.content_gap_unknown_expectation_count, total),
            "content_format 未登记，不猜测内容期望",
        ],
        [
            "内容期望",
            "期望未知（全部）",
            _num(scope.content_expectation_unknown_count),
            _pct(scope.content_expectation_unknown_count, total),
            "含 Content 可读的对象，仍不推断类型语义",
        ],
    ]

    lines = [
        "## 11. 分析范围规则分类",
        "",
        f"Inventory 对全部登记文件执行一次 Analysis Scope Rules（version {scope.rules_version}），",
        "后续 Evidence / Understanding / Review 只消费判定结果，不在此重复过滤。",
        "",
        "### 11.1 资格与范围口径",
        "",
        _table(
            ["口径", "数量", "占比", "说明"],
            [
                ["登记文件", _num(total), _pct(total, total), "全部保留在 inventory/files.json"],
                [
                    "整体分析资格",
                    _num(scope.overall_eligible_count),
                    _pct(scope.overall_eligible_count, total),
                    "Node ID 有效，满足节点级分析的前置条件；分析资格 ≠ 已分析",
                ],
                [
                    "SQL 分析输入",
                    _num(scope.sql_eligible_count),
                    _pct(scope.sql_eligible_count, total),
                    "身份、任务、类型、内容四组规则全部通过，进入 M2.3",
                ],
                [
                    "明确排除",
                    _num(scope.excluded_total_count),
                    _pct(scope.excluded_total_count, total),
                    "主分类为身份不满足或非正式任务（互斥），见 inventory/excluded-tasks.json",
                ],
                [
                    "　其中：主分类为身份不满足",
                    _num(scope.identity_excluded_count),
                    _pct(scope.identity_excluded_count, total),
                    "NodeId 缺失或格式无效（优先于非正式任务计为主分类）",
                ],
                [
                    "　其中：主分类为非正式任务",
                    _num(scope.informal_excluded_count),
                    _pct(scope.informal_excluded_count, total),
                    "文件名整体命中非正式任务词；规则命中总数见 11.4",
                ],
                [
                    "待确认",
                    _num(scope.review_count),
                    _pct(scope.review_count, total),
                    "非正式任务弱证据，见 inventory/review-tasks.json",
                ],
                [
                    "清理候选",
                    _num(scope.cleanup_candidate_count),
                    _pct(scope.cleanup_candidate_count, total),
                    "值得后续人工核查；清理候选 ≠ 可以删除",
                ],
            ],
            alignments=["left", "right", "right", "left"],
        ),
        "",
        "### 11.2 节点身份与节点类型",
        "",
        _table(
            ["维度", "取值", "数量", "占比"],
            node_rows,
            alignments=["left", "left", "right", "right"],
        ),
        "",
        "### 11.3 内容状态与内容期望",
        "",
        _table(
            ["维度", "取值", "数量", "占比", "含义"],
            content_rows,
            alignments=["left", "left", "right", "right", "left"],
        ),
        "",
        "内容状态五行互斥，合计等于登记文件；内容期望是对缺口对象的第二维度，"
        "与状态行可能重叠，不参与合计。",
        "",
        "### 11.4 规则命中（可重叠）",
        "",
    ]

    rule_rows: list[list[object]] = [
        [
            rule_id,
            scope.rule_types.get(rule_id, "—"),
            scope.rule_descriptions.get(rule_id, "—"),
            _num(scope.rule_hit_counts.get(rule_id, 0)),
        ]
        for rule_id in scope.rule_types
    ]

    lines.extend(
        [
            _table(
                ["规则", "类型", "说明", "命中数"],
                rule_rows,
                alignments=["left", "left", "left", "right"],
            ),
            "",
            "同一文件可能命中多条规则，命中数之和大于等于对象数；下表的主因分布每个文件只计一次。",
            "",
            "### 11.5 主因分布（互斥）",
            "",
            _table(
                ["口径", "原因", "数量"],
                reason_rows,
                alignments=["left", "left", "right"],
            ),
            "",
            "### 11.6 产物与边界",
            "",
            "- `inventory/excluded-tasks.json`：明确排除出正式业务分析的资产，"
            "记录 workspace_id + file_id、命中规则与原因代码；",
            "- `inventory/review-tasks.json`：非正式任务弱证据的待确认资产，"
            "不计入确定排除，也不进入清理候选；",
            "- 两份清单都是分析范围判定的产物，不是删除、禁用或修改 DataWorks 资产的指令；",
            "- 排除分类 ≠ 无效资产：被排除的对象仍完整保留在 `inventory/files.json`。",
            "",
        ]
    )

    return lines


def _num(value: int) -> str:
    """千分位数字（标识类字段不要用它格式化）。"""

    return f"{value:,}"


def _pct(count: int, total: int) -> str:
    """百分比；分母为 0 时返回占位符。"""

    if not total:
        return "—"

    return f"{count / total * 100:.1f}%"


def _avg(total: int, count: int) -> str:
    """平均值；分母为 0 时返回占位符。"""

    if not count:
        return "—"

    return f"{total / count:.1f}"


def _workspace_distribution(
    workspaces: Sequence[WorkspaceInventorySummary],
) -> list[str]:
    """第 4 节：Workspace 资产分布表。"""

    if not workspaces:
        return ["## 4. 工作区资产分布", "", "_（无 Workspace）_", ""]

    rows: list[list[object]] = [
        [
            item.workspace_name,
            _num(item.discovered_file_count),
            _num(item.eligible_file_count),
            _num(item.content_available_count),
            _num(item.table_count),
            _num(item.column_count),
        ]
        for item in workspaces
    ]

    rows.append(
        [
            "**合计**",
            _num(sum(item.discovered_file_count for item in workspaces)),
            _num(sum(item.eligible_file_count for item in workspaces)),
            _num(sum(item.content_available_count for item in workspaces)),
            _num(sum(item.table_count for item in workspaces)),
            _num(sum(item.column_count for item in workspaces)),
        ]
    )

    return [
        "## 4. 工作区资产分布",
        "",
        _table(
            [
                "工作区",
                "DataWorks 文件",
                "有效 Node ID",
                "内容可用",
                "MaxCompute 表",
                "字段",
            ],
            rows,
            alignments=["left", "right", "right", "right", "right", "right"],
        ),
        "",
        "本节只展示当前 Workspace 的资产分布。Workspace 名称（如 dme_ods / dme_cdm / "
        "dme_ads）本身不能作为业务建模结论：它不证明其中的资产一定符合对应的分层定位。",
        "",
    ]


def _dataworks_sections(summary: InventorySummary) -> list[str]:
    """第 5 节：DataWorks 开发资产。"""

    dataworks = summary.dataworks
    total = dataworks.discovered_count

    return [
        "## 5. DataWorks 开发资产",
        "",
        "### 5.1 文件规模",
        "",
        _table(
            ["指标", "数量"],
            [
                ["文件总数（发现）", _num(total)],
                ["已登记文件", _num(dataworks.registered_count)],
                ["有效 Node ID", _num(dataworks.valid_node_id_count)],
                ["缺失 / 无效 Node ID", _num(dataworks.missing_node_id_count)],
                ["内容可用", _num(dataworks.content_available_count)],
                ["内容不可用", _num(dataworks.content_unavailable_count)],
            ],
            alignments=["left", "right"],
        ),
        "",
        "### 5.2 文件登记情况",
        "",
        _table(
            ["指标", "数量"],
            [
                ["发现文件", _num(dataworks.discovered_count)],
                ["已登记文件", _num(dataworks.registered_count)],
                ["登记缺口", _num(dataworks.discovered_count - dataworks.registered_count)],
            ],
            alignments=["left", "right"],
        ),
        "",
        "登记 = 成功写入 `analysis/inventory/files.json`。"
        "登记是 Inventory 本阶段的处理结果，与「已分析」无关。",
        "",
        "### 5.3 后续分析资格",
        "",
        _table(
            ["指标", "数量"],
            [
                ["文件总数", _num(total)],
                ["有效 Node ID", _num(dataworks.valid_node_id_count)],
                ["缺失 / 无效 Node ID", _num(dataworks.missing_node_id_count)],
                ["当前分析候选", _num(dataworks.eligible_count)],
            ],
            alignments=["left", "right"],
        ),
        "",
        "Node ID 是 DataWorks 文件与后续节点级分析之间的重要身份信息，",
        "但**有效 Node ID 不等于 SQL 分析一定成功**：解析是否成功由后续 SQL Analysis 阶段决定。",
        "",
        "缺失 / 无效 Node ID 的文件是「当前不满足节点级后续分析条件的文件」，",
        "不是无效资产：它们仍完整保留在 Inventory 清单中（见第 8.2 节）。",
        "",
        "### 5.4 内容可用",
        "",
        _table(
            ["指标", "数量"],
            [
                ["内容可用", _num(dataworks.content_available_count)],
                ["内容不可用", _num(dataworks.content_unavailable_count)],
            ],
            alignments=["left", "right"],
        ),
        "",
        "内容可用表示 Snapshot 中存在对应的文件内容，"
        "不等同于内容一定可以被 SQL Parser 解析；"
        "内容不可用是采集结果事实，不等于采集失败（见第 8.3 节）。",
        "",
        "### 5.5 后续分析候选",
        "",
        "当前 Inventory 的规则：**有效 Node ID 是当前定义的后续分析候选条件**"
        "（`is_analysis_eligible`）。Content 是否可用、内容格式是否为 SQL "
        "不改变这条候选判定，它们是下游阶段自己的前置条件。",
        "",
        "**分析候选 ≠ 已分析**：Inventory 只登记与标注候选范围，"
        "不对任何文件做 SQL 解析、血缘或业务判断。",
        "",
        _table(
            ["指标", "数量", "占分析候选"],
            [
                [
                    "当前分析候选",
                    _num(dataworks.eligible_count),
                    _pct(dataworks.eligible_count, dataworks.eligible_count),
                ],
                [
                    "分析候选且 content_format = SQL",
                    _num(dataworks.eligible_sql_format_count),
                    _pct(dataworks.eligible_sql_format_count, dataworks.eligible_count),
                ],
                [
                    "分析候选且内容可用",
                    _num(dataworks.eligible_content_available_count),
                    _pct(dataworks.eligible_content_available_count, dataworks.eligible_count),
                ],
                [
                    "分析候选且 SQL 格式且内容可用",
                    _num(dataworks.eligible_sql_content_count),
                    _pct(dataworks.eligible_sql_content_count, dataworks.eligible_count),
                ],
            ],
            alignments=["left", "right", "right"],
        ),
        "",
        f"后续 SQL 解析的实际输入还要求 `content_format = SQL` 且内容可用"
        f"（当前为 {_num(dataworks.eligible_sql_content_count)} 个文件），"
        "这是下游阶段的过滤行为，不属于 Inventory 的排除原因。",
        "",
    ]


def _maxcompute_sections(summary: InventorySummary) -> list[str]:
    """第 6 节：MaxCompute 数据资产。"""

    maxcompute = summary.maxcompute

    return [
        "## 6. MaxCompute 数据资产",
        "",
        "### 6.1 表资产",
        "",
        _table(
            ["指标", "数量"],
            [
                ["表总数", _num(maxcompute.registered_count)],
                ["有原始元数据的表", _num(maxcompute.tables_with_raw_metadata)],
                ["缺失原始元数据的表", _num(maxcompute.tables_without_raw_metadata)],
                ["有字段的表", _num(maxcompute.tables_with_columns)],
                ["无字段的表", _num(maxcompute.tables_without_columns)],
            ],
            alignments=["left", "right"],
        ),
        "",
        "### 6.2 字段资产",
        "",
        _table(
            ["指标", "数量"],
            [
                ["字段总数", _num(maxcompute.column_count)],
                [
                    "平均字段数（有字段的表）",
                    _avg(maxcompute.column_count, maxcompute.tables_with_columns),
                ],
            ],
            alignments=["left", "right"],
        ),
        "",
        "表身份保持当前约定：project.table（table_key，不含 schema）；"
        "字段按 table_key + ordinal 定位。"
        "本节不讨论事实表 / 维度表 / 宽表 / DWD / DWS / ADS 建模合理性，"
        "这些属于后续阶段。",
        "",
    ]


def _coverage_sections(summary: InventorySummary) -> list[str]:
    """第 7 节：资产覆盖与完整性。"""

    dataworks = summary.dataworks
    maxcompute = summary.maxcompute

    file_gap = dataworks.discovered_count - dataworks.registered_count
    table_gap = maxcompute.discovered_count - maxcompute.registered_count

    lines = [
        "## 7. 资产覆盖与完整性",
        "",
        "本节回答：Snapshot 中的资产是否完整进入 Inventory？"
        "**这是资产覆盖检查，不是数据质量检查。**",
        "",
        "### DataWorks",
        "",
        _table(
            ["检查项", "数量"],
            [
                ["Snapshot 发现文件", _num(dataworks.discovered_count)],
                ["Inventory 已登记", _num(dataworks.registered_count)],
                ["Raw JSON 可用", _num(dataworks.raw_available_count)],
                ["有效 Node ID", _num(dataworks.valid_node_id_count)],
                ["内容可用", _num(dataworks.content_available_count)],
                ["内容文件缺失", _num(dataworks.content_path_missing_count)],
                ["GetFile 失败", _num(dataworks.collect_failure_count)],
            ],
            alignments=["left", "right"],
        ),
        "",
        "### MaxCompute",
        "",
        _table(
            ["检查项", "数量"],
            [
                ["Snapshot 发现表", _num(maxcompute.discovered_count)],
                ["Inventory 已登记", _num(maxcompute.registered_count)],
                ["原始表元数据", _num(maxcompute.tables_with_raw_metadata)],
                ["字段元数据", _num(maxcompute.tables_with_columns)],
                ["无字段元数据", _num(maxcompute.tables_without_columns)],
                ["GetTable 失败", _num(maxcompute.collect_failure_count)],
            ],
            alignments=["left", "right"],
        ),
        "",
        "### 覆盖结论",
        "",
    ]

    if file_gap == 0 and table_gap == 0:
        lines.append(
            f"- Snapshot 发现的 {_num(dataworks.discovered_count)} 个文件与 "
            f"{_num(maxcompute.discovered_count)} 张表已全部登记进 Inventory，"
            "登记缺口为 0。"
        )
    else:
        lines.append(
            f"- 文件登记缺口 {_num(file_gap)}，表登记缺口 {_num(table_gap)}；"
            "缺口中每一条都对应第 8.4 节的一类技术异常。"
        )

    missing_dataworks = [
        item.workspace_id for item in summary.workspaces if not item.has_dataworks_snapshot
    ]
    missing_maxcompute = [
        item.workspace_id for item in summary.workspaces if not item.has_maxcompute_snapshot
    ]

    if missing_dataworks:
        lines.append(
            f"- 缺少 DataWorks Snapshot 的工作区：{_join_workspace_ids(missing_dataworks)}，"
            "该工作区不产出 File 清单。"
        )

    if missing_maxcompute:
        lines.append(
            f"- 缺少 MaxCompute Snapshot 的工作区：{_join_workspace_ids(missing_maxcompute)}，"
            "该工作区不产出 Table / Column 清单。"
        )

    lines.extend(
        [
            "- 内容可用性与 Node ID 覆盖见第 5 节；它们描述资产状态，"
            "不代表资产缺失或数据质量问题。",
            "- 清单只覆盖当前 Snapshot：新增采集后需要重新运行 Inventory 才会更新。",
            "",
        ]
    )

    return lines


def _join_workspace_ids(workspace_ids: Sequence[int]) -> str:
    """把 workspace_id 列表拼成可读文本。"""

    return "、".join(str(workspace_id) for workspace_id in workspace_ids)


def _attention_sections(summary: InventorySummary) -> list[str]:
    """第 8 节：需要关注的资产与异常。"""

    return [
        "## 8. 需要关注的资产与异常",
        "",
        "本节按三类分开呈现，不混成一个「异常数量」：",
        "",
        "1. **正常但需要关注**：例如文件类型 UNKNOWN，"
        "可能是非 SQL 文件或合法但未映射的类型，不一定是错误（见 8.1）；",
        "2. **当前不满足后续分析条件**：例如 Node ID 缺失、内容不可用，"
        "这是范围限制或采集结果事实，不一定是采集失败（见 8.2、8.3）；",
        "3. **真正技术异常**：采集失败、元数据缺失、content_file 指向文件缺失等（见 8.4）。",
        "",
        "代表案例展示规则：总数少于 10 全部展示；10～100 展示 3～5 个代表案例；",
        "超过 100 先按可解释特征分类，再按类别展示代表案例。"
        "完整数据以结构化产物为准"
        "（`analysis/inventory/files.json` / `tables.json` / "
        "`analysis/evidence/errors.json`）。",
        "",
        *_unknown_format_section(summary),
        *_missing_node_id_section(summary),
        *_content_unavailable_section(summary),
        *_technical_exception_section(summary),
    ]


def _unknown_format_section(summary: InventorySummary) -> list[str]:
    """第 8.1 节：文件类型 UNKNOWN 分类与代表案例。"""

    dataworks = summary.dataworks
    groups = dataworks.unknown_format_groups
    cases = dataworks.unknown_format_cases
    total = dataworks.discovered_count

    if not dataworks.unrecognized_format_count:
        return [
            "### 8.1 文件类型 UNKNOWN",
            "",
            "当前未发现 content_format = UNKNOWN 的文件。",
            "",
        ]

    group_rows: list[list[object]] = [
        [
            f"file_type={group.file_type}（{group.file_type_name}）",
            _num(group.count),
            _pct(group.count, total),
            (
                "FileType 已登记，内容格式映射为 UNKNOWN（通常为非 SQL 任务形态）"
                if group.registered
                else "FileType 未在类型注册表登记，需人工确认类型映射（类型映射缺口候选）"
            ),
        ]
        for group in groups
    ]

    judgement_by_file_type = {group.file_type: _group_judgement(group) for group in groups}

    case_rows: list[list[object]] = [
        [
            case.workspace_name,
            case.file_id,
            case.file_name or "—",
            case.file_type,
            case.content_format,
            case.node_id if case.node_id is not None else "null",
            judgement_by_file_type.get(case.file_type, ""),
        ]
        for case in cases
    ]

    all_shown = len(cases) >= dataworks.unrecognized_format_count
    case_note = (
        "总数少于 10，全部案例均已展示；"
        if all_shown
        else f"共 {len(cases)} 个代表案例，按 file_type 分类轮转选取；"
    )

    return [
        "### 8.1 文件类型 UNKNOWN（正常但需要关注）",
        "",
        f"- 数量：{_num(dataworks.unrecognized_format_count)}"
        f"（占全部 DataWorks 文件 {_pct(dataworks.unrecognized_format_count, total)}）",
        "",
        "UNKNOWN ≠ 一定是错误：它可能是非 SQL 文件、某些 DataWorks 文件类型"
        "尚未映射（SHELL / PYTHON / RESOURCE 等合法类型），"
        "或真正无法识别的文件。以下先分类，再给代表案例，供人工判断"
        "UNKNOWN 是合理的非 SQL 文件，还是 Inventory 的类型映射存在问题。",
        "",
        "#### 类型分布",
        "",
        _table(
            ["文件类型 / 特征", "数量", "占比", "初步判断"],
            group_rows,
            alignments=["left", "right", "right", "left"],
        ),
        "",
        "#### 代表案例",
        "",
        _table(
            ["Workspace", "File ID", "文件名称", "File Type", "Content Format", "Node ID", "说明"],
            case_rows,
            alignments=["left", "left", "left", "right", "left", "left", "left"],
        ),
        "",
        f"{case_note}完整分类与全量明细见 `analysis/inventory/files.json`。",
        "",
    ]


def _group_judgement(group: UnknownFormatGroup) -> str:
    """UNKNOWN 分类行的初步判断（事实性描述，不是结论）。"""

    if group.registered:
        return "FileType 已登记，内容格式映射为 UNKNOWN"

    return "FileType 未在类型注册表登记（类型映射缺口候选）"


def _missing_node_id_section(summary: InventorySummary) -> list[str]:
    """第 8.2 节：缺失 / 无效 Node ID 代表案例。"""

    dataworks = summary.dataworks

    if not dataworks.missing_node_id_count:
        return [
            "### 8.2 缺失 / 无效 Node ID",
            "",
            "当前全部文件均具备有效 Node ID。",
            "",
        ]

    case_rows = [_file_case_row(case) for case in dataworks.missing_node_id_cases]

    missing_node_pct = _pct(dataworks.missing_node_id_count, dataworks.discovered_count)

    return [
        "### 8.2 缺失 / 无效 Node ID（当前不满足节点级后续分析条件）",
        "",
        f"- 数量：{_num(dataworks.missing_node_id_count)}"
        f"（占全部 DataWorks 文件 {missing_node_pct}）",
        "",
        "这些文件是「当前不满足节点级后续分析条件的文件」，不是无效资产：",
        "它们仍完整保留在 Inventory 清单中，只是不进入后续节点级分析范围。",
        "",
        _table(
            ["Workspace", "File ID", "文件名称", "Node ID", "文件类型", "说明"],
            case_rows,
            alignments=["left", "left", "left", "left", "left", "left"],
        ),
        "",
        "完整列表见 `analysis/inventory/files.json`。",
        "",
    ]


def _content_unavailable_section(summary: InventorySummary) -> list[str]:
    """第 8.3 节：内容不可用代表案例。"""

    dataworks = summary.dataworks

    if not dataworks.content_unavailable_count:
        return [
            "### 8.3 内容不可用",
            "",
            "当前全部文件在 Snapshot 中均有对应内容。",
            "",
        ]

    case_rows: list[list[object]] = [
        [
            case.workspace_name,
            case.file_id,
            case.file_name or "—",
            case.content_file or "—",
            "未提供" if not case.content_file else "路径缺失",
            case.reason,
        ]
        for case in dataworks.content_unavailable_cases
    ]

    unavailable_pct = _pct(dataworks.content_unavailable_count, dataworks.discovered_count)

    return [
        "### 8.3 内容不可用",
        "",
        f"- 数量：{_num(dataworks.content_unavailable_count)}"
        f"（占全部 DataWorks 文件 {unavailable_pct}）",
        "",
        "content_file 为空（API 未返回 Content）是采集结果事实，不等于采集失败；",
        "只有 content_file 指向的文件在 Snapshot 中缺失才属于技术异常（见 8.4）。",
        "",
        _table(
            ["Workspace", "File ID", "文件名称", "Content File", "内容状态", "说明"],
            case_rows,
            alignments=["left", "left", "left", "left", "left", "left"],
        ),
        "",
        "完整列表见 `analysis/inventory/files.json`。",
        "",
    ]


def _technical_exception_section(summary: InventorySummary) -> list[str]:
    """第 8.4 节：其他技术异常。"""

    exceptions = summary.technical_exceptions

    lines = [
        "### 8.4 其他技术异常（真正技术异常）",
        "",
        _table(
            ["影响级别", "异常类型", "数量", "影响"],
            [[item.severity, item.exception, _num(item.count), item.impact] for item in exceptions],
            alignments=["left", "left", "right", "left"],
        ),
        "",
    ]

    zero_items = [item for item in exceptions if item.count == 0]

    if zero_items:
        zero_names = "、".join(item.exception for item in zero_items)
        lines.append(f"以下类别本次已检查、当前未发现异常：{zero_names}。")
        lines.append("")

    for item in exceptions:
        if not item.count or not item.cases:
            continue

        lines.extend(
            [
                f"#### {item.exception}（代表案例）",
                "",
                _table(
                    ["Workspace ID", "File ID", "Table", "路径", "说明"],
                    [
                        [
                            case.workspace_id if case.workspace_id is not None else "—",
                            case.file_id or "—",
                            case.table or "—",
                            case.path or "—",
                            case.reason,
                        ]
                        for case in item.cases
                    ],
                    alignments=["right", "left", "left", "left", "left"],
                ),
                "",
            ]
        )

    lines.extend(
        [
            "- 计数为 0 表示本次已检查、未发生该类异常；零异常时不会生成任何代表案例。",
            "- `content_file` 为空（API 未返回 Content）是采集结果事实，"
            "**不计入**本节异常；本节只统计 content_file 指向的文件在 Snapshot 中缺失。",
            "- 因不满足后续分析条件而未进入后续分析的文件不属于本节，见第 8.2、8.3 节。",
            "- 本节不是 M3.6 Problem，也不是数据质量或模型问题。",
            "",
            f"Inventory 阶段可恢复错误合计：{_num(summary.inventory_error_count)} 条，"
            "明细见 `analysis/evidence/errors.json`。",
            "",
        ]
    )

    return lines


def _file_case_row(case: AssetCase) -> list[object]:
    """资产案例的通用表格行。"""

    return [
        case.workspace_name,
        case.file_id or "—",
        case.file_name or "—",
        case.node_id if case.node_id is not None else "null",
        f"file_type={case.file_type}",
        case.reason,
    ]


def render_lineage_summary(lineage: LineageResult) -> str:
    """生成 analysis/evidence/lineage/summary.md。"""

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
    """生成 analysis/evidence/profiling/summary.md。"""

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
    """生成 analysis/evidence/layer/summary.md。

    只做纯渲染：status / candidate_layer / evidence 都来自 M2.2 评估结果，
    这里不产生新的判断，也不把 UNKNOWN 写成违规。
    """

    unconfigured_label = "(未配置)"
    undetermined_label = "(未确定)"
    conflict_limit = 20
    unknown_limit = 20

    status_counts = Counter(item.status for item in assessments)
    candidate_counts = Counter(item.candidate_layer or undetermined_label for item in assessments)
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
        f"只列出前 {conflict_limit} 条，完整明细见 `analysis/evidence/layer/assessments.json`。"
        if len(conflict_rows) > conflict_limit
        else "完整明细见 `analysis/evidence/layer/assessments.json`。"
    )

    unknown_rows: list[list[object]] = [
        [item.table_identifier, item.workspace_id, item.workspace_name] for item in unknowns
    ]

    unknown_note = (
        f"只列出前 {unknown_limit} 条，完整明细见 `analysis/evidence/layer/assessments.json`。"
        if len(unknown_rows) > unknown_limit
        else "完整明细见 `analysis/evidence/layer/assessments.json`。"
    )

    cross_rows: list[list[object]] = [
        [
            item.table_identifier,
            item.workspace_layer,
            ", ".join(dict.fromkeys(str(hit.get("layer")) for hit in item.cross_layer_hits)),
        ]
        for item in cross_layer_items
    ]

    cross_note = (
        f"只列出前 {conflict_limit} 条，完整明细见 `analysis/evidence/layer/assessments.json`。"
        if len(cross_rows) > conflict_limit
        else "完整明细见 `analysis/evidence/layer/assessments.json`。"
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
                for (workspace_id, workspace_name, layer), count in sorted(workspace_counts.items())
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
            [[candidate, count] for candidate, count in sorted(candidate_counts.items())],
        ),
        "",
        "## 未配置 Workspace",
        "",
        _table(
            ["workspace_id", "workspace_name", "table_count"],
            [
                [workspace_id, workspace_name, count]
                for (workspace_id, workspace_name, layer), count in sorted(workspace_counts.items())
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
    """生成 analysis/understanding/business/summary.md。

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
        candidate.confidence for item in tables for candidate in item.business_object_candidates
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
        f"只列出前 {detail_limit} 条，完整明细见 `analysis/understanding/business/tables.json`。"
        if len(ambiguous_rows) > detail_limit
        else "完整明细见 `analysis/understanding/business/tables.json`。"
    )
    unknown_note = (
        f"只列出前 {detail_limit} 条，完整明细见 `analysis/understanding/business/tables.json`。"
        if len(unknown_rows) > detail_limit
        else "完整明细见 `analysis/understanding/business/tables.json`。"
    )
    term_note = (
        f"只列出前 {term_limit} 条，完整列表见 `analysis/understanding/business/terms.json`。"
        if len(terms) > term_limit
        else f"完整列表见 `analysis/understanding/business/terms.json`（共 {len(terms)} 条）。"
    )

    def category_rows(
        summaries: list[DomainSummary] | list[ObjectSummary],
        key_name: str,
    ) -> list[list[object]]:
        rows: list[list[object]] = []

        for item in summaries:
            confidence_text = (
                "，".join(f"{key}={value}" for key, value in item.confidence_counts.items()) or "-"
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
            [[item.term, item.normalized_term, item.count] for item in terms[:term_limit]],
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
        "  `analyze --stage understanding`，否则 `analysis/understanding/business/`"
        "  可能停留在旧输入上。",
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
    """生成 analysis/understanding/business/quality-assessment.md。

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

    quality_report_note = "`analysis/understanding/business/quality-assessment.json`。"

    unknown_sample_note = (
        f"只列出前 {limit} 条，完整明细见 {quality_report_note}"
        if len(unknown.get("samples") or []) > limit
        else f"完整明细见 {quality_report_note}"
    )
    ambiguous_sample_note = (
        f"只列出前 {limit} 条，完整明细见 {quality_report_note}"
        if len(ambiguous.get("samples") or []) > limit
        else f"完整明细见 {quality_report_note}"
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
            [[reason, count] for reason, count in (unknown.get("by_reason") or {}).items()],
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
            [[reason, count] for reason, count in (ambiguous.get("by_reason") or {}).items()],
        ),
        "",
        str(ambiguous.get("note") or ""),
        "",
        "### 候选类型分布（by_type）",
        "",
        _table(
            ["type", "table_count"],
            [[key, value] for key, value in (ambiguous.get("by_type") or {}).items()],
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
        f"- 同一关键词重复出现的表：{evidence_quality.get('repeated_keyword_table_count', 0)}",
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
                for evidence_type, value in (evidence_quality.get("by_source_type") or {}).items()
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
        "复核顺序见 `analysis/understanding/business/review-checklist.md`。",
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
        "- 本命令只读 M2 / M3 产物，不自动回退执行 analyze；",
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
    """生成 analysis/understanding/business/object-graph.md。

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
        f"{evidence_type} {int((distribution.get(evidence_type) or {}).get('entry_count') or 0)} 条"
        for evidence_type in RELATIONSHIP_EVIDENCE_ORDER
    ]
    sql_statements = int(relationships.get("sql_statement_count") or 0)

    object_rows: list[list[object]] = [
        [item.get("object"), item.get("name") or "-", item.get("status")] for item in objects
    ]

    table_rows: list[list[object]] = []

    for item in objects:
        matrix_row = matrix_by_object.get(str(item.get("object"))) or {}
        table_rows.append(
            [
                item.get("object"),
                item.get("table_count", 0),
                item.get("core_table_count", 0),
                ", ".join(str(value) for value in matrix_row.get("candidate_layers") or []) or "-",
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
        "完整明细见 `analysis/understanding/business/object-relationships.json`。"
        if len(relationship_rows) > relationship_row_limit
        else "完整明细见 `analysis/understanding/business/object-relationships.json`。"
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
        "完整明细见 `analysis/understanding/business/object-relationships.json`。"
        if len(core_rows) > relationship_row_limit
        else "完整明细见 `analysis/understanding/business/object-relationships.json`。"
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
            "（来自 `analysis/understanding/business/objects.json`，M3.2 不重新分类）",
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
    """生成 analysis/understanding/business/process-summary.md（8 节）。

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
        "完整明细见 `analysis/understanding/business/processes.json`。"
        if len(process_rows) > PROCESS_REPORT_ROW_LIMIT
        else "完整明细见 `analysis/understanding/business/processes.json`。"
    )

    core_rows_text = [candidate_row(row) for row in core_rows]
    core_note = (
        f"只列出前 {PROCESS_REPORT_ROW_LIMIT} 条，共 {len(core_rows)} 条；"
        "完整明细见 `analysis/understanding/business/processes.json`。"
        if len(core_rows) > PROCESS_REPORT_ROW_LIMIT
        else "完整明细见 `analysis/understanding/business/processes.json`。"
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
        source: sum(int((row.get("evidence") or {}).get(source) or 0) for row in process_rows)
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
        1 for row in process_rows if not int((row.get("evidence") or {}).get("lineage") or 0)
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
            "（来自 `analysis/understanding/business/object-tables.json`，M3.3 不重新识别 Object）",
            f"- Process Signal 行数：{signals.get('count', 0)}"
            f"（覆盖 {signals.get('table_count', 0)} 张表）",
            f"- Process candidate 数量：{processes.get('count', 0)}（{status_text}）",
            f"- 过程证据强度：{strength_text}（Level 分布：{level_text}）",
            f"- 参与的 Object 数量：{len(object_names)}（{', '.join(object_names) or '-'}）",
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
            "`analysis/understanding/business/object-relationships.json` 的排序 Object 对。",
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
            "- 表级口径：`analysis/understanding/business/review-checklist.md` 中仍为 candidate / "
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
    """生成 analysis/understanding/business/process-review-checklist.md（人工回填清单）。

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

    # 即使没有数据也生成表头
    table_lines = [
        "# M3.3 Process Review Checklist",
        "",
        "人工填写 human process name，并把 confirmed 从 false 改为 true 以确认该"
        " process candidate；未回填的行一律保持 false，candidate 不会自动变成"
        " confirmed process。",
        "",
        "前六列（process_key / objects / tables / signals / evidence）与 note 之外的"
        "机器列由 `analyze --stage understanding` 生成，重跑会被覆盖；"
        "human_process_name / confirmed / note 三列会被保留。",
        "",
        "| process_key | objects | tables | signals | evidence | human_process_name "
        "| confirmed | note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    if not rows:
        table_lines.extend(
            [
                "_（无候选）_",
                "",
            ]
        )
    else:
        table_lines.extend(
            [
                *[
                    "| " + " | ".join(str(item).replace("|", "\\|") for item in cells) + " |"
                    for cells in rows
                ],
                "",
            ]
        )

    return "\n".join(table_lines)


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
    """生成 analysis/understanding/business/grain-summary.md（9 节）。

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
        str(row.get("process_key") or ""): bool(row.get("human_validated")) for row in processes
    }
    validated_process_count = sum(1 for value in process_validated.values() if value)
    validated_candidate_count = sum(
        1 for row in candidate_rows if row.get("process_human_validated")
    )
    empty_key_rows = [row for row in candidate_rows if not row.get("candidate_keys")]
    strong_rows = [row for row in candidate_rows if row.get("strength") == EVIDENCE_STRENGTH_STRONG]
    moderate_rows = [
        row for row in candidate_rows if row.get("strength") == EVIDENCE_STRENGTH_MODERATE
    ]
    weak_rows = [row for row in candidate_rows if row.get("strength") == EVIDENCE_STRENGTH_WEAK]
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
                f"完整明细见 `analysis/understanding/business/{name}`。"
            )

        return f"完整明细见 `analysis/understanding/business/{name}`。"

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
        [[pattern, int(pattern_counts.get(pattern) or 0)] for pattern in GRAIN_PATTERN_ORDER],
    )

    process_table = _table(
        ["process_key", "candidates", "patterns", "empty keys", "process confirmed"],
        [
            [
                process_key,
                len(rows),
                ", ".join(sorted({str(row.get("grain_pattern") or "") for row in rows})) or "-",
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
    role_text = "，".join(f"{role}={int(role_counts.get(role) or 0)}" for role in GRAIN_ROLE_ORDER)

    return "\n".join(
        [
            "# M3.4 Grain Candidate Analysis",
            "",
            "## 1. Overview",
            "",
            f"- Inventory 表数量：{inventory_table_count}",
            f"- 参与 M3.3 的 (process, table) 数量：{process_table_count}",
            f"- Process candidate 数量：{len(processes)}（人工已确认 {validated_process_count}）",
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
                        ", ".join(str(item) for item in row.get("unresolved_reasons") or []) or "-",
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
                [[source, evidence_totals[source]] for source in GRAIN_EVIDENCE_ORDER],
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
                [[reason, unresolved_counts[reason]] for reason in GRAIN_UNRESOLVED_ORDER],
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
            "回填 `analysis/understanding/business/grain-review-checklist.md` 的 "
            "human_grain_name / confirmed / note 后重跑本阶段即可保留人工输入；"
            "机器阶段不会把任何候选变成 confirmed。",
            "",
            f"- 待确认候选：{len(candidate_rows)}（其中绑定已确认 process 的 "
            f"{validated_candidate_count} 个，绑定未确认 process 的 "
            f"{len(candidate_rows) - validated_candidate_count} 个）",
            f"- Process 侧已确认：{validated_process_count} / {len(processes)}",
            f"- Core 表候选上的候选：{len(core_rows)}（core_candidate 只作证据覆盖与复核优先级）",
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
            "- 行级唯一性证据：当前 Profiling 无样本，任何「唯一」结论都必须由人工确认。",
            "",
        ]
    )


def render_grain_review_checklist(
    candidate_rows: Sequence[Mapping[str, Any]],
    *,
    carry_over: Mapping[str, Mapping[str, str]] | None = None,
    row_limit: int,
) -> str:
    """生成 analysis/understanding/business/grain-review-checklist.md（人工回填清单）。

    按 process 分组；每组最多 row_limit 行并注明总数。
    机器列由 `analyze --stage understanding` 生成、重跑会被覆盖；
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
        "机器列（grain_candidate_id 起到 strength 为止）由 `analyze --stage understanding` "
        "生成，重跑会被覆盖；human_grain_name / confirmed / note 三列会被保留。",
        "",
    ]

    grouped: dict[str, list[Mapping[str, Any]]] = {}

    for row in candidate_rows:
        grouped.setdefault(str(row.get("process_candidate_id") or ""), []).append(row)

    if not grouped:
        # 即使没有数据也生成表头，确保必需列存在
        lines.extend(
            [
                "| grain_candidate_id | table_key | grain_pattern | candidate_keys "
                "| strength | unresolved_reasons | human_grain_name | confirmed | note |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "_（无候选）_",
                "",
            ]
        )
        return "\n".join(lines)

    for process_key in sorted(grouped):
        rows = grouped[process_key]
        lines.append(f"## {process_key}")
        lines.append("")

        if len(rows) > row_limit:
            lines.append(
                f"只列出前 {row_limit} 行，共 {len(rows)} 行；"
                "其余行见 `analysis/understanding/business/grain-candidates.json`。"
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
                ", ".join(str(item) for item in row.get("unresolved_reasons") or []) or "-",
                previous.get("human_grain_name", "").strip(),
                "true" if _flag(previous.get("confirmed", "")) else "false",
                previous.get("note", "").strip(),
            ]
            lines.append("| " + " | ".join(str(item).replace("|", "\\|") for item in cells) + " |")

        lines.append("")

    return "\n".join(lines)


def _flag(value: str) -> bool:
    return (value or "").strip().casefold() in {"true", "yes", "y", "1", "confirmed", "是"}


def render_review_checklist(
    *,
    rows: Sequence[QualityChecklistRow],
    row_limit: int,
) -> str:
    """生成 analysis/understanding/business/review-checklist.md。

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
                "完整样本见 `analysis/understanding/business/quality-assessment.json`。",
            ]

        lines += [""]

    return "\n".join(lines)


def render_analysis_summary(context: SummaryContext) -> str:
    """生成 analysis/summary.md。"""

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
        "完整列表见 `analysis/evidence/lineage/core-table-candidates.json`。",
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
                    sum(1 for item in context.layer_assessments if item.cross_layer_hits),
                ],
            ],
        ),
        "",
        _table(
            ["candidate_layer", "table_count"],
            [[layer, count] for layer, count in sorted(layer_candidate_counts.items())],
        ),
        "",
        "workspace_layer 是配置事实，candidate_layer 是子层候选；UNKNOWN 只表示证据不足，",
        "不代表命名违规。跨层命名提示只提示表名带其他层前缀，不改变 candidate。",
        "完整明细见 `analysis/evidence/layer/summary.md`。",
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
        (
            "完整错误见 `analysis/evidence/errors.json`，"
            "SQL 解析错误见 `analysis/evidence/sql/parse-errors.json`。"
        ),
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
    """生成 analysis/summary.md 所需的全部输入。"""

    inventory: Inventory
    lineage: LineageResult
    statements: list[StatementRecord] = field(default_factory=list)
    references: list[TableReference] = field(default_factory=list)
    parse_errors: list[ParseErrorRecord] = field(default_factory=list)
    table_profiles: list[TableProfile] = field(default_factory=list)
    column_profiles: list[ColumnProfile] = field(default_factory=list)
    layer_assessments: list[LayerAssessment] = field(default_factory=list)
    errors: list[dict[str, object]] = field(default_factory=list)


def render_model_summary(
    *,
    fact_candidates: Mapping[str, Any],
    dimension_candidates: Mapping[str, Any],
    relationships: Mapping[str, Any],
    fact_tables: Mapping[str, Any],
    dimension_tables: Mapping[str, Any],
    evidence_matrix: Mapping[str, Any],
    processes: Sequence[Mapping[str, Any]],
    inventory_table_count: int,
    grain_candidate_count: int,
    priority_counts: Mapping[str, int],
    profiling: Mapping[str, Any],
    analysis_dir: Path | str,
) -> str:
    """生成 analysis/understanding/modeling/model-summary.md（8 节）。

    只做纯渲染：所有数字都来自 M3.5 构建结果。措辞停留在
    「fact / dimension / relationship candidate + 证据 + 未决问题」，
    不判 confirmed 模型，不命名 Fact / Dimension 表，不产出 DWD / DWS /
    Semantic Layer 结论。
    """

    fact_rows = list(fact_candidates.get("candidates") or [])
    dimension_rows = list(dimension_candidates.get("candidates") or [])
    relationship_rows = list(relationships.get("relationships") or [])
    matrix_rows = list(evidence_matrix.get("rows") or [])

    gate = fact_candidates.get("gate") or {}
    gate_reasons = gate.get("rejected_reason_counts") or {}
    validated_process_count = sum(1 for row in processes if row.get("human_validated"))

    fact_status = fact_candidates.get("status_counts") or {}
    fact_strength = fact_candidates.get("strength_counts") or {}
    dimension_status = dimension_candidates.get("status_counts") or {}
    dimension_strength = dimension_candidates.get("strength_counts") or {}
    dimension_role_status = dimension_candidates.get("role_status_counts") or {}
    relationship_status = relationships.get("status_counts") or {}
    relationship_strength = relationships.get("strength_counts") or {}
    pattern_counts = fact_candidates.get("pattern_counts") or {}
    fact_role_counts = fact_tables.get("role_counts") or {}
    dimension_role_counts = dimension_tables.get("role_counts") or {}

    fact_unresolved = fact_candidates.get("unresolved_counts") or {}
    dimension_unresolved = dimension_candidates.get("unresolved_counts") or {}
    relationship_unresolved = relationships.get("unresolved_counts") or {}

    fact_evidence_totals = {
        source: sum(
            int((row.get("evidence_counts") or {}).get(source) or 0)
            for row in matrix_rows
            if row.get("candidate_type") == MODEL_CANDIDATE_TYPE_FACT
        )
        for source in FACT_EVIDENCE_ORDER
    }
    dimension_evidence_totals = {
        source: sum(
            int((row.get("evidence_counts") or {}).get(source) or 0)
            for row in matrix_rows
            if row.get("candidate_type") == MODEL_CANDIDATE_TYPE_DIMENSION
        )
        for source in DIMENSION_EVIDENCE_ORDER
    }

    def status_text(counts: Mapping[str, Any], order: Sequence[str]) -> str:
        return "，".join(f"{status}={int(counts.get(status) or 0)}" for status in order)

    def unresolved_cell(row: Mapping[str, Any]) -> str:
        return ", ".join(str(item) for item in row.get("unresolved_reasons") or []) or "-"

    def joined_cell(value: Any) -> str:
        items = [str(item) for item in value or []]
        return "、".join(items) if items else "-"

    weak_fact = int(fact_strength.get(EVIDENCE_STRENGTH_WEAK) or 0)
    weak_dimension = int(dimension_strength.get(EVIDENCE_STRENGTH_WEAK) or 0)
    weak_relationship = int(relationship_strength.get(EVIDENCE_STRENGTH_WEAK) or 0)

    return "\n".join(
        [
            "# M3.5 Fact / Dimension Candidate Analysis",
            "",
            "## 1. Overview",
            "",
            f"- Inventory 表数量：{inventory_table_count}",
            f"- 输入 grain candidate 数量：{grain_candidate_count}",
            f"- Process candidate 数量：{len(processes)}（人工已确认 {validated_process_count}）",
            f"- Fact Gate：通过 {int(gate.get('qualified_count') or 0)}，"
            f"未通过 {int(gate.get('rejected_count') or 0)}"
            + (
                "（"
                + "，".join(
                    f"{reason}={int(count or 0)}" for reason, count in sorted(gate_reasons.items())
                )
                + "）"
                if gate_reasons
                else ""
            ),
            f"- Fact candidate 数量：{fact_candidates.get('count', 0)}"
            f"（{status_text(fact_status, MODEL_STATUS_ORDER)}）",
            "- fact 的 grain_pattern 分布："
            + "，".join(
                f"{pattern}={int(pattern_counts.get(pattern) or 0)}"
                for pattern in GRAIN_PATTERN_ORDER
            ),
            f"- Dimension candidate 数量：{dimension_candidates.get('count', 0)}"
            f"（{status_text(dimension_status, MODEL_STATUS_ORDER)}；"
            f"role：{status_text(dimension_role_status, MODEL_ROLE_STATUS_ORDER)}）",
            f"- Fact ↔ Dimension relationship 数量："
            f"{relationships.get('count', 0)}"
            f"（{status_text(relationship_status, MODEL_STATUS_ORDER)}）",
            f"- fact → table 行数：{fact_tables.get('count', 0)}"
            f"（{status_text(fact_role_counts, GRAIN_ROLE_ORDER)}）",
            f"- dimension → table 行数：{dimension_tables.get('count', 0)}"
            f"（{status_text(dimension_role_counts, GRAIN_ROLE_ORDER)}）",
            f"- evidence matrix 行数：{evidence_matrix.get('count', 0)}"
            "（fact + dimension，关系证据见 relationship 产物）",
            f"- 覆盖 process 数量：{fact_candidates.get('process_count', 0)}，"
            f"覆盖表数量：{fact_candidates.get('table_count', 0)}，"
            f"覆盖 Object 数量：{fact_candidates.get('object_count', 0)}",
            f"- Profiling：is_candidate_key=true 的列 "
            f"{int(profiling.get('candidate_key_count') or 0)}，"
            f"metadata_only 列 {int(profiling.get('metadata_only_column_count') or 0)}"
            f" / {int(profiling.get('column_count') or 0)}"
            "（metadata-only，不伪造行级唯一性）",
            f"- 输入：`{analysis_dir}`",
            "",
            "本报告只产出 **Fact / Dimension Candidate**：候选来自 M3.4 grain "
            "candidate 与 M3.1 Object，"
            f"status 恒为 candidate（{MODEL_CANDIDATE_NOTE}）。"
            "机器阶段不写 confirmed，确认必须回填清单后重跑。",
            "",
            "## 2. Fact Candidates",
            "",
            "- Fact Gate 规则：transaction / event / snapshot 直接通过；"
            "periodic / aggregation / unknown 必须有 measure 字段，"
            "否则记 `missing_measure_evidence`，该 grain candidate 不生成 fact。",
            "",
            _table(
                ["grain_pattern", "fact candidates"],
                [
                    [pattern, int(pattern_counts.get(pattern) or 0)]
                    for pattern in GRAIN_PATTERN_ORDER
                ],
            ),
            "",
            _table(
                [
                    "fact_key",
                    "process",
                    "grain",
                    "pattern",
                    "tables",
                    "objects",
                    "strength",
                    "unresolved",
                ],
                [
                    [
                        row.get("fact_key"),
                        row.get("process_candidate_id"),
                        row.get("grain_candidate_id"),
                        row.get("grain_pattern"),
                        len(row.get("table_keys") or []),
                        joined_cell(row.get("object_keys")),
                        row.get("evidence_strength"),
                        unresolved_cell(row),
                    ]
                    for row in fact_rows
                ],
                limit=MODEL_REPORT_ROW_LIMIT,
            ),
            "",
            _truncated_note(len(fact_rows), "fact-candidates.json"),
            "",
            "读法：每个 fact candidate = 「一个 grain candidate 在其候选表上的 "
            "fact 候选 + 7 类证据」；同一 grain 的多个候选表合并成一条候选，"
            "不挑 winner。",
            "",
            "## 3. Dimension Candidates",
            "",
            f"- dimension 按 M3.1 Object 逐个生成（{len(dimension_rows)} 个）；"
            "attributes 只是关联表里观察到的字段清单，"
            f"每条最多列出 {MODEL_ATTRIBUTE_LIMIT} 个。",
            "",
            _table(
                [
                    "dimension_key",
                    "object",
                    "tables",
                    "attributes",
                    "referenced facts",
                    "strength",
                    "unresolved",
                ],
                [
                    [
                        row.get("dimension_key"),
                        row.get("object_name"),
                        row.get("table_count"),
                        row.get("attribute_count"),
                        len(row.get("referenced_by_facts") or []),
                        row.get("evidence_strength"),
                        unresolved_cell(row),
                    ]
                    for row in dimension_rows
                ],
                limit=MODEL_REPORT_ROW_LIMIT,
            ),
            "",
            _truncated_note(len(dimension_rows), "dimension-candidates.json"),
            "",
            f"- role_status：{status_text(dimension_role_status, MODEL_ROLE_STATUS_ORDER)}"
            "；`ambiguous` = 同一 Object 同时出现在 fact 关系里，"
            "必须人工裁决主角色。",
            "- modeling_roles 可以多选：一个 Object 可以同时是 dimension "
            "candidate 与 fact related object。",
            "",
            "## 4. Fact ↔ Dimension Relationships",
            "",
            f"- relationship 行数：{relationships.get('count', 0)}；"
            "每行至少一类证据才生成，无证据的组合不产出关系候选。",
            "",
            _table(
                [
                    "relationship_key",
                    "fact",
                    "dimension",
                    "evidence sources",
                    "strength",
                    "unresolved",
                ],
                [
                    [
                        row.get("relationship_key"),
                        row.get("fact_key"),
                        row.get("dimension_key"),
                        joined_cell(row.get("evidence_sources")),
                        row.get("evidence_strength"),
                        unresolved_cell(row),
                    ]
                    for row in relationship_rows
                ],
                limit=MODEL_REPORT_ROW_LIMIT,
            ),
            "",
            _truncated_note(len(relationship_rows), "fact-dimension-relationships.json"),
            "",
            "- relationship ≠ 业务关系：它只说明 fact 候选与 dimension 候选之间"
            "存在可解释的引用 / 关联证据，确认前必须核对 source_id。",
            "",
            "## 5. Evidence Coverage",
            "",
            _table(
                ["fact evidence", "total"],
                [[source, fact_evidence_totals[source]] for source in FACT_EVIDENCE_ORDER],
            ),
            "",
            _table(
                ["dimension evidence", "total"],
                [
                    [source, dimension_evidence_totals[source]]
                    for source in DIMENSION_EVIDENCE_ORDER
                ],
            ),
            "",
            _table(
                ["relationship evidence", "total"],
                [
                    [
                        source,
                        int((relationships.get("evidence_source_counts") or {}).get(source) or 0),
                    ]
                    for source in MODEL_REL_EVIDENCE_ORDER
                ],
            ),
            "",
            _table(
                ["candidate type", *EVIDENCE_STRENGTH_ORDER],
                [
                    [
                        MODEL_CANDIDATE_TYPE_FACT,
                        *[
                            int(fact_strength.get(strength) or 0)
                            for strength in EVIDENCE_STRENGTH_ORDER
                        ],
                    ],
                    [
                        MODEL_CANDIDATE_TYPE_DIMENSION,
                        *[
                            int(dimension_strength.get(strength) or 0)
                            for strength in EVIDENCE_STRENGTH_ORDER
                        ],
                    ],
                    [
                        MODEL_CANDIDATE_TYPE_RELATIONSHIP,
                        *[
                            int(relationship_strength.get(strength) or 0)
                            for strength in EVIDENCE_STRENGTH_ORDER
                        ],
                    ],
                ],
            ),
            "",
            "- strength = 证据源类型的数量（weak=1，moderate=2，strong≥3），"
            "只反映证据多样性，不代表业务正确。",
            "- 计数口径：fact / dimension 按候选统计，relationship 按证据条目统计。",
            "",
            "## 6. Evidence Gaps",
            "",
            "每个候选都按固定顺序记录未决原因（未决 ≠ 失败，必须人工回答）：",
            "",
            _table(
                ["fact unresolved reason", "candidates"],
                [
                    [reason, int(fact_unresolved.get(reason) or 0)]
                    for reason in MODEL_FACT_UNRESOLVED_ORDER
                ],
            ),
            "",
            _table(
                ["dimension unresolved reason", "candidates"],
                [
                    [reason, int(dimension_unresolved.get(reason) or 0)]
                    for reason in MODEL_DIMENSION_UNRESOLVED_ORDER
                ],
            ),
            "",
            _table(
                ["relationship unresolved reason", "relationships"],
                [
                    [reason, int(relationship_unresolved.get(reason) or 0)]
                    for reason in MODEL_REL_UNRESOLVED_ORDER
                ],
            ),
            "",
            f"- weak 证据：fact {weak_fact}，dimension {weak_dimension}，"
            f"relationship {weak_relationship}",
            "- 未决原因只在对应证据缺失时出现；补证据后重跑本阶段即可更新。",
            "",
            "## 7. Human Review",
            "",
            "回填 `analysis/understanding/modeling/model-review-checklist.md` 的 "
            "human_status / human_name / note 后重跑本阶段即可保留人工输入；"
            "机器列由 `analyze --stage understanding` 生成，重跑会被覆盖。",
            "",
            "- human_status → status 映射：pending → candidate，"
            "confirmed → confirmed，rejected → rejected，"
            "needs_review / needs_discussion → needs_discussion；"
            "未识别的取值按未回填处理并输出警告。",
            f"- 机器 status 恒为 candidate；只有回填 confirmed 才会变成 "
            f"confirmed（{MODEL_CANDIDATE_NOTE}）。",
            "",
            _table(
                ["priority", "title", "rows"],
                [
                    [
                        priority,
                        MODEL_PRIORITY_TITLE[priority],
                        int(priority_counts.get(priority) or 0),
                    ]
                    for priority in MODEL_PRIORITY_ORDER
                ],
            ),
            "",
            "- 每个优先级分区最多列出 "
            f"{MODEL_CHECKLIST_ROW_LIMIT} 行，"
            "完整明细见 `analysis/understanding/modeling/model-review-checklist.md`。",
            f"- 证据强度为 weak 的候选：fact {weak_fact}，"
            f"dimension {weak_dimension}，relationship {weak_relationship}。",
            "",
            "## 8. Limitations",
            "",
            f"- candidate ≠ confirmed：{MODEL_CANDIDATE_NOTE}；"
            "机器阶段不产出 confirmed 模型，确认必须回填清单后重跑。",
            "- strength 只是证据源数量；Profiling 为 metadata-only，"
            "没有任何行级唯一性证明，候选键 ≠ 唯一键。",
            "- role 只用 anchor / supporting（fact 复用 M3.4 grain 的角色，"
            "dimension = 含命中标识字段且不是 fact 表），"
            "不是 Fact / Dimension / DWD / DWS 结论。",
            "- layer 只作 candidate_layer 结构证据；core_candidate 只作证据覆盖与"
            "复核优先级，不是业务价值判断。",
            "- 多角色与 UNKNOWN / AMBIGUOUS 一律保留，不合并不拆分不删表，不挑 winner。",
            "- relationship 是候选关系，不是业务关系；确认前必须核对 source_id。",
            "- 本阶段只读既有产物：不重解析原始数据，不重做 Object / Process / "
            "Grain classifier，不读 `source/`，不调用 LLM / 外部 API。",
            "",
        ]
    )


def _truncated_note(total: int, name: str) -> str:
    if total > MODEL_REPORT_ROW_LIMIT:
        return (
            f"只列出前 {MODEL_REPORT_ROW_LIMIT} 条，共 {total} 条；"
            f"完整明细见 `analysis/understanding/modeling/{name}`。"
        )

    return f"完整明细见 `analysis/understanding/modeling/{name}`。"


def render_model_review_checklist(
    rows: Sequence[ModelChecklistRow],
    *,
    carry_over: Mapping[str, Mapping[str, str]] | None = None,
    row_limit: int,
) -> str:
    """生成 analysis/understanding/modeling/model-review-checklist.md（人工回填清单）。

    按优先级 P1 → P4 分区；每区最多 row_limit 行并注明总数。
    机器列由 `analyze --stage understanding` 生成、重跑会被覆盖；
    human_status / human_name / note 三列保留上一次的人工回填。
    """

    existing = carry_over or {}
    lines: list[str] = [
        "# M3.5 Model Review Checklist",
        "",
        "人工回填 human_status（pending / confirmed / rejected / needs_review / "
        "needs_discussion）、human_name 与 note；"
        "未回填的行一律保持 candidate，candidate 不会自动变成 confirmed。",
        "",
        "candidate_key 起到 unresolved_reasons 为止的机器列由 "
        "`analyze --stage understanding` 生成，重跑会被覆盖；"
        "human_status / human_name / note 三列会被保留。",
        "",
    ]

    header = "| " + " | ".join(MODEL_CHECKLIST_HEADERS) + " |"
    separator = "| " + " | ".join("---" for _ in MODEL_CHECKLIST_HEADERS) + " |"

    if not rows:
        lines.extend([header, separator, "_（无候选）_", ""])
        return "\n".join(lines)

    lines.extend([header, separator])

    for priority in MODEL_PRIORITY_ORDER:
        section = [row for row in rows if row.priority == priority]
        lines.append(f"## {priority} {MODEL_PRIORITY_TITLE[priority]}")
        lines.append("")
        lines.append(MODEL_PRIORITY_HINT[priority])
        lines.append("")

        if not section:
            lines.extend(["_（本区无候选）_", ""])
            continue

        if len(section) > row_limit:
            lines.append(
                f"只列出前 {row_limit} 行，共 {len(section)} 行；"
                "其余行见 `analysis/understanding/modeling/fact-candidates.json`、"
                "`dimension-candidates.json` 与 `fact-dimension-relationships.json`。"
            )
            lines.append("")

        lines.extend([header, separator])

        for row in section[:row_limit]:
            previous = existing.get(row.candidate_key, {})
            raw_status = str(previous.get("human_status", "") or "").strip()
            cells = [
                row.candidate_key,
                row.candidate_type,
                row.priority,
                row.current_status,
                row.evidence_strength,
                ", ".join(row.unresolved_reasons) or "-",
                normalize_human_status(raw_status) or raw_status or "pending",
                str(previous.get("human_name", "") or "").strip(),
                str(previous.get("note", "") or "").strip(),
            ]
            lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |")

        lines.append("")

    return "\n".join(lines)


def render_current_state_summary(
    *,
    current_model: Mapping[str, Any],
    findings: Mapping[str, Any],
    analysis_dir: Path | str,
) -> str:
    """生成 analysis/review/current-state-model-summary.md（6 节）。

    只做纯渲染：所有数字都来自 M3.6 的构建结果。措辞停留在
    「当前模型形态 + 评审发现 + 人工问题」，不设计 Target DWD，
    不把 finding 写成已确认问题，不产出 DWD / DWS / Semantic Layer 结论。
    """

    scope = current_model.get("scope") or {}
    role_counts = current_model.get("role_counts") or {}
    shape_counts = current_model.get("shape_counts") or {}
    quality = current_model.get("model_quality") or {}
    gate = current_model.get("fact_gate_review") or {}
    strength = current_model.get("evidence_strength_review") or {}
    dimension = current_model.get("dimension_review") or {}
    relationship = current_model.get("relationship_review") or {}
    priority_counts = findings.get("priority_counts") or {}
    type_counts = findings.get("finding_type_counts") or {}
    group_counts = findings.get("review_group_counts") or {}
    status_counts = findings.get("status_counts") or {}
    severity_by_priority = findings.get("severity_by_priority") or {}
    finding_rows = list(findings.get("findings") or [])

    def count_text(counts: Mapping[str, Any], order: Sequence[str]) -> str:
        return "，".join(f"{key}={int(counts.get(key) or 0)}" for key in order)

    gate_reasons = gate.get("rejected_reason_counts") or {}
    strength_counts = strength.get("strength_counts") or {}
    dimension_role_status = dimension.get("role_status_counts") or {}
    relationship_strength = relationship.get("strength_counts") or {}
    workspace_ids = [str(item) for item in scope.get("workspace_ids") or []]

    return "\n".join(
        [
            "# M3.6 Current-State Model Review",
            "",
            "## 1. Scope",
            "",
            f"- Workspace：{_joined(workspace_ids) or '（未知）'}",
            f"- Inventory 表数量：{int(scope.get('inventory_table_count') or 0)}，"
            f"已分类表数量：{int(scope.get('classified_table_count') or 0)}",
            f"- Fact candidate：{int(scope.get('fact_count') or 0)}，"
            f"Dimension candidate：{int(scope.get('dimension_count') or 0)}，"
            f"Relationship：{int(scope.get('relationship_count') or 0)}",
            f"- Fact → table 行数：{int(scope.get('fact_table_row_count') or 0)}，"
            f"Dimension → table 行数：{int(scope.get('dimension_table_row_count') or 0)}",
            f"- Process candidate：{int(scope.get('process_count') or 0)}，"
            f"Grain candidate：{int(scope.get('grain_count') or 0)}，"
            f"Object：{int(scope.get('object_count') or 0)}",
            f"- Finding：{findings.get('count', 0)}"
            f"（{count_text(priority_counts, REVIEW_PRIORITY_ORDER)}）",
            f"- 输入：`{analysis_dir}`",
            "",
            f"- {CURRENT_STATE_NOTE}；{FINDING_CANDIDATE_NOTE}。",
            "- 本阶段只读 M2 / M3 / M3.5 产物：不读 `source/`，不调 LLM / 外部 API，"
            "不修改任何上游产物。",
            "",
            "## 2. Current Model Overview",
            "",
            _table(
                ["current_role", "tables"],
                [[role, int(role_counts.get(role) or 0)] for role in CURRENT_MODEL_ROLE_ORDER],
            ),
            "",
            _table(
                ["model_shape", "tables"],
                [[shape, int(shape_counts.get(shape) or 0)] for shape in CURRENT_MODEL_SHAPE_ORDER],
            ),
            "",
            "- `current_role` / `model_shape` 只描述当前平台已经存在的形态，"
            "不是 Target DWD 设计；UNKNOWN / AMBIGUOUS 一律保留。",
            "- 表级角色只由 fact anchor、dimension anchor、字段数与血缘形态推导，"
            "不按表名断言业务事实。",
            "",
            "## 3. Model Quality",
            "",
            _table(
                ["indicator", "count"],
                [[key, int(value or 0)] for key, value in quality.items()],
            ),
            "",
            f"- Fact Gate 复算：通过 {int(gate.get('qualified_count') or 0)}，"
            f"未通过 {int(gate.get('rejected_count') or 0)}"
            + (
                "（"
                + "，".join(
                    f"{reason}={int(count or 0)}" for reason, count in sorted(gate_reasons.items())
                )
                + "）"
                if gate_reasons
                else ""
            )
            + f"；与 M3.5 一致={gate.get('matches_m35')}",
            "",
            _table(
                ["grain_pattern", "rejected"],
                [
                    [pattern, int(count or 0)]
                    for pattern, count in (gate.get("rejected_by_pattern") or {}).items()
                ],
            ),
            "",
            f"- Evidence Strength 分布（fact）："
            f"{count_text(strength_counts, list(strength_counts) or [])}"
            f"；{strength.get('interpretation', '')}",
            f"- Dimension：{int(dimension.get('count') or 0)} 个，"
            f"role {count_text(dimension_role_status, list(dimension_role_status) or [])}"
            f"；{dimension.get('observation', '')}",
            f"- Relationship：{int(relationship.get('count') or 0)} 行，"
            f"strength {count_text(relationship_strength, list(relationship_strength) or [])}",
            f"；单证据 {int(relationship.get('single_evidence_count') or 0)}，"
            f"仅技术引用 {int(relationship.get('technical_only_count') or 0)}，"
            f"仅共现 {int(relationship.get('object_co_occurrence_only_count') or 0)}，"
            f"无共享表 {int(relationship.get('no_shared_table_count') or 0)}",
            "",
            _table(
                ["relationship evidence", "rows"],
                [
                    [source, int(count or 0)]
                    for source, count in (relationship.get("evidence_source_counts") or {}).items()
                ],
            ),
            "",
            "- 上述全部是评审观测：异常只标记 Review，不判定 Wrong。",
            "",
            "## 4. Priority Findings",
            "",
            _table(
                ["priority", "severity", "title", "findings"],
                [
                    [
                        priority,
                        severity_by_priority.get(priority, ""),
                        REVIEW_PRIORITY_TITLE[priority],
                        int(priority_counts.get(priority) or 0),
                    ]
                    for priority in REVIEW_PRIORITY_ORDER
                ],
            ),
            "",
            _table(
                ["review group", "findings"],
                [[group, int(group_counts.get(group) or 0)] for group in REVIEW_GROUP_ORDER],
            ),
            "",
            _table(
                ["finding_type", "priority", "findings"],
                [
                    [
                        finding_type,
                        FINDING_TYPE_PRIORITY.get(finding_type, "-"),
                        int(type_counts.get(finding_type) or 0),
                    ]
                    for finding_type in FINDING_TYPE_ORDER
                ],
            ),
            "",
            _table(
                [
                    "finding_id",
                    "priority",
                    "finding_type",
                    "scope",
                    "scope_key",
                    "description",
                ],
                [
                    [
                        row.get("finding_id"),
                        row.get("priority"),
                        row.get("finding_type"),
                        row.get("scope"),
                        row.get("scope_key"),
                        str(row.get("description") or "").replace("|", "\\|"),
                    ]
                    for row in finding_rows
                ],
                limit=REVIEW_REPORT_ROW_LIMIT,
            ),
            "",
            _review_truncated_note(len(finding_rows), "current-state-findings.json"),
            "",
            "## 5. Human Review",
            "",
            "回填 `analysis/review/current-state-review-checklist.md` 的 "
            "human_status / human_name / note 后重跑本阶段即可保留人工输入；"
            "机器列由 `analyze --stage review` 生成，重跑会被覆盖。",
            "",
            "- human_status → status 映射：pending → candidate，"
            "confirmed → confirmed，rejected → rejected，"
            "needs_review / needs_discussion → needs_discussion；"
            "未识别的取值按未回填处理并输出警告。",
            f"- 当前 finding 状态：{count_text(status_counts, list(status_counts) or [])}",
            "",
            "- 每个分区最多列出 "
            "50 行，完整明细见 "
            "`analysis/review/current-state-review-checklist.md`。",
            "- P0 未裁决前不要进入 M4 的事实 / 维度定稿。",
            "",
            "## 6. M4 Input",
            "",
            "可以带入 M4 的输入：",
            "",
            "- current-state 分类（role / shape）与逐表明细（`current-state-model-tables.json`）。",
            "- 带证据的 review finding 与优先级（`current-state-findings.json`）。",
            "- 回填后的人工结论（`current-state-review-checklist.md`）。",
            "",
            "不能带入 M4 的内容：",
            "",
            "- 未经人工裁决的 fact / dimension 最终角色；"
            "本阶段不合并、不拆分、不删表、不挑 winner。",
            "- 只有技术引用（SQL / 血缘 / 共现）的关系，不能直接当成业务维度关系。",
            "- `evidence_strength=strong` 不等于该表确定是事实表。",
            "",
            "- 建议顺序：先回答 P0（Fact Gate 排除、粒度冲突、多形态、角色歧义），"
            "再处理 P1（重复 / 重叠 / 关系证据），最后看 P2 / P3。",
            f"- 进入 M4 前至少需要：{FINDING_CANDIDATE_NOTE}；P0 finding 必须有人工结论。",
            "",
        ]
    )


def _joined(values: Sequence[Any]) -> str:
    return "、".join(str(value) for value in values)


def _review_truncated_note(total: int, name: str) -> str:
    if total > REVIEW_REPORT_ROW_LIMIT:
        return (
            f"只列出前 {REVIEW_REPORT_ROW_LIMIT} 条，共 {total} 条；"
            f"完整明细见 `analysis/review/{name}`。"
        )

    return f"完整明细见 `analysis/review/{name}`。"


def render_current_state_review_checklist(
    findings: Sequence[Mapping[str, Any]],
    *,
    carry_over: Mapping[str, Mapping[str, str]] | None = None,
    row_limit: int,
) -> str:
    """生成 analysis/review/current-state-review-checklist.md（人工回填清单）。

    按 review group（Fact / Dimension / Grain / Relationship / Model Issue）
    分区；每区最多 row_limit 行并注明总数。机器列由
    `analyze --stage review` 生成、重跑会被覆盖；
    human_status / human_name / note 三列保留上一次的人工回填。
    """

    existing = carry_over or {}
    lines: list[str] = [
        "# M3.6 Current-State Review Checklist",
        "",
        "人工回填 human_status（pending / confirmed / rejected / needs_review / "
        "needs_discussion）、human_name 与 note；"
        "未回填的行一律保持 candidate，finding 不会自动变成 confirmed。",
        "",
        "finding_id 起到 human_question 为止的机器列由 "
        "`analyze --stage review` 生成，重跑会被覆盖；"
        "human_status / human_name / note 三列会被保留。",
        "",
        "scope_key 起到 human_question 的内容是机器观测，"
        "不是已确认的模型错误；回复 human_question 才是人工结论。",
        "",
    ]

    if not findings:
        header = "| " + " | ".join(REVIEW_CHECKLIST_HEADERS) + " |"
        separator = "| " + " | ".join("---" for _ in REVIEW_CHECKLIST_HEADERS) + " |"
        lines.extend([header, separator, "_（无 finding）_", ""])
        return "\n".join(lines)

    header = "| " + " | ".join(REVIEW_CHECKLIST_HEADERS) + " |"
    separator = "| " + " | ".join("---" for _ in REVIEW_CHECKLIST_HEADERS) + " |"

    for group in REVIEW_GROUP_ORDER:
        section = [row for row in findings if row.get("review_group") == group]
        lines.append(f"## {REVIEW_GROUP_TITLE[group]}")
        lines.append("")
        lines.append(REVIEW_GROUP_HINT[group])
        lines.append("")

        if not section:
            lines.extend([header, separator, "_（本区无 finding）_", ""])
            continue

        if len(section) > row_limit:
            lines.append(
                f"只列出前 {row_limit} 行，共 {len(section)} 行；"
                "其余行见 `analysis/review/current-state-findings.json`。"
            )
            lines.append("")

        lines.extend([header, separator])

        for row in section[:row_limit]:
            finding_id = str(row.get("finding_id") or "")
            previous = existing.get(finding_id, {})
            raw_status = str(previous.get("human_status", "") or "").strip()
            cells = [
                finding_id,
                row.get("finding_type"),
                row.get("priority"),
                row.get("scope_key"),
                _joined(row.get("evidence_sources") or []) or "-",
                str(row.get("description") or ""),
                str(row.get("human_question") or ""),
                normalize_human_status(raw_status) or raw_status or "pending",
                str(previous.get("human_name", "") or "").strip(),
                str(previous.get("note", "") or "").strip(),
            ]
            lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |")

        lines.append("")

    return "\n".join(lines)


def render_current_state_problem_summary(
    *,
    problems: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> str:
    """生成 analysis/review/current-state-problem-summary.md（6 节）。

    只做纯渲染：所有数字都来自 M3.6 v2 的聚合结果。措辞停留在
    「问题 + 证据 + 影响 + 根因 + 重构理由 + 人工确认」，不设计 Target DWD，
    不把 problem 写成已确认问题，不产出 DWD / DWS / Semantic Layer 结论。
    """

    problem_rows = list(problems.get("problems") or [])
    type_counts = problems.get("problem_type_counts") or {}
    status_counts = problems.get("status_counts") or {}
    priority_counts = problems.get("priority_counts") or {}
    severity_by_priority = problems.get("severity_by_priority") or {}
    classification_counts = problems.get("classification_counts") or {}
    impact_counts = problems.get("impact_counts") or {}
    root_cause_counts = problems.get("root_cause_counts") or {}
    strength_counts = problems.get("evidence_strength_counts") or {}
    coverage = problems.get("finding_coverage") or {}
    evidence_counts = evidence.get("evidence_type_counts") or {}

    def count_text(counts: Mapping[str, Any], order: Sequence[str]) -> str:
        return "，".join(f"{key}={int(counts.get(key) or 0)}" for key in order)

    def clip(value: Any, limit: int = 80) -> str:
        text = str(value or "").replace("|", "\\|")
        return text if len(text) <= limit else text[:limit] + "…"

    classification_order = [
        *GRAIN_ASSESSMENT_ORDER,
        *OVERLAP_CLASS_ORDER,
        *AGGREGATE_ASSESSMENT_ORDER,
        *UNKNOWN_REASON_ORDER,
    ]

    return "\n".join(
        [
            "# M3.6 v2 Current-State Problem Assessment",
            "",
            "## 1. Scope",
            "",
            f"- Finding：{int(problems.get('finding_count') or 0)}",
            f"- Problem candidate：{int(problems.get('count') or 0)}"
            f"（{count_text(priority_counts, REVIEW_PRIORITY_ORDER)}）",
            f"- 受影响表（去重）：{int(problems.get('distinct_affected_table_count') or 0)}",
            f"- Finding 覆盖：进入 problem 的 finding "
            f"{int(coverage.get('covered_finding_count') or 0)} / "
            f"{int(coverage.get('finding_count') or 0)}"
            f"，未进入 problem {int(coverage.get('uncovered_finding_count') or 0)}",
            f"- 证据行：{int(evidence.get('evidence_row_total') or 0)}"
            f"（单 problem 上限见 evidence 产物）",
            f"- {PROBLEM_CANDIDATE_NOTE}。",
            "- 本阶段只读 M1–M3.6 产物：不读 `source/` / profiling / SQL 参考，"
            "不调 LLM / 外部 API，不修改任何上游产物。",
            "",
            "## 2. Problem Distribution",
            "",
            _table(
                ["problem_type", "title", "default priority", "problems"],
                [
                    [
                        problem_type,
                        PROBLEM_TYPE_TITLE.get(problem_type, ""),
                        PROBLEM_TYPE_PRIORITY.get(problem_type, "-"),
                        int(type_counts.get(problem_type) or 0),
                    ]
                    for problem_type in PROBLEM_TYPE_ORDER
                ],
            ),
            "",
            _table(
                ["status", "problems"],
                [[status, int(status_counts.get(status) or 0)] for status in PROBLEM_STATUS_ORDER],
            ),
            "",
            f"- 当前状态分布：{count_text(status_counts, PROBLEM_STATUS_ORDER)}；"
            "机器阶段只会写 candidate / review_required，"
            "confirmed / rejected 只能来自清单回填。",
            "",
            "## 3. Impact & Root Cause",
            "",
            _table(
                ["impact_type", "title", "problems"],
                [
                    [
                        impact,
                        PROBLEM_IMPACT_TITLE.get(impact, ""),
                        int(impact_counts.get(impact) or 0),
                    ]
                    for impact in PROBLEM_IMPACT_ORDER
                ],
            ),
            "",
            _table(
                ["root_cause", "title", "problems"],
                [
                    [
                        root_cause,
                        PROBLEM_ROOT_CAUSE_TITLE.get(root_cause, ""),
                        int(root_cause_counts.get(root_cause) or 0),
                    ]
                    for root_cause in PROBLEM_ROOT_CAUSE_ORDER
                ],
            ),
            "",
            "- impact / root_cause 是从问题类型与证据结构推导的候选结论，"
            "不是已确认的业务根因；裁决权在人工清单。",
            "",
            "## 4. Priority & Evidence",
            "",
            _table(
                ["priority", "severity", "title", "problems"],
                [
                    [
                        priority,
                        severity_by_priority.get(priority, ""),
                        REVIEW_PRIORITY_TITLE.get(priority, ""),
                        int(priority_counts.get(priority) or 0),
                    ]
                    for priority in REVIEW_PRIORITY_ORDER
                ],
            ),
            "",
            _table(
                ["evidence_strength", "problems"],
                [
                    [strength, int(strength_counts.get(strength) or 0)]
                    for strength in EVIDENCE_STRENGTH_ORDER
                ],
            ),
            "",
            _table(
                ["classification", "problems"],
                [
                    [
                        classification,
                        int(classification_counts.get(classification) or 0),
                    ]
                    for classification in classification_order
                    if int(classification_counts.get(classification) or 0)
                ],
            ),
            "",
            _table(
                ["evidence_type", "rows"],
                [
                    [evidence_type, int(evidence_counts.get(evidence_type) or 0)]
                    for evidence_type in PROBLEM_EVIDENCE_ORDER
                ],
            ),
            "",
            "- SQL 证据恒为 0：本阶段不读 SQL 产物。",
            "",
            "## 5. Top Problems",
            "",
            _table(
                [
                    "problem_id",
                    "priority",
                    "problem_type",
                    "scope_key",
                    "tables",
                    "evidence_strength",
                    "root_cause",
                    "status",
                ],
                [
                    [
                        row.get("problem_id"),
                        row.get("priority"),
                        row.get("problem_type"),
                        clip(row.get("scope_key")),
                        int(row.get("affected_table_count") or 0),
                        row.get("evidence_strength"),
                        row.get("root_cause"),
                        row.get("status"),
                    ]
                    for row in problem_rows
                ],
                limit=PROBLEM_SUMMARY_ROW_LIMIT,
            ),
            "",
            (
                f"只列出前 {PROBLEM_SUMMARY_ROW_LIMIT} 行，共 {len(problem_rows)} 行；"
                "完整明细见 `analysis/review/current-state-problems.json`。"
                if len(problem_rows) > PROBLEM_SUMMARY_ROW_LIMIT
                else "完整明细见 `analysis/review/current-state-problems.json`。"
            ),
            "",
            "- 排序依据：priority → problem_type → scope → scope_key（稳定排序，"
            "不含随机抽样）。每条 problem 的 current_state / problem / evidence / "
            "impact / why_change 见该文件的 `rationale` 字段。",
            "",
            "## 6. Human Review & M4 Input",
            "",
            "回填 `analysis/review/current-state-problem-review-checklist.md` 的 "
            "human_status / human_name / note 后重跑本阶段即可保留人工输入；"
            "机器列由 `analyze --stage review` 生成，重跑会被覆盖。",
            "",
            "- human_status → status 映射：pending → candidate，"
            "confirmed → confirmed，rejected → rejected，"
            "needs_review / needs_discussion → review_required；"
            "未识别的取值按未回填处理并输出警告。",
            "- 每个分区最多列出 "
            f"{PROBLEM_CHECKLIST_ROW_LIMIT} 行，完整明细见 "
            "`analysis/review/current-state-problems.json`。",
            "",
            "可以带入 M4 的输入：",
            "",
            "- 带证据链的 problem candidate 与优先级"
            "（`current-state-problems.json`）。"
            "每条含 evidence / impact / root_cause / rationale。",
            "- 逐条证据明细（`current-state-problem-evidence.json`）。",
            "- 回填后的人工结论（`current-state-problem-review-checklist.md`）。",
            "",
            "不能带入 M4 的内容：",
            "",
            "- 未经人工确认的 problem；finding ≠ problem ≠ confirmed，三者计数互不等价。",
            "- 机器推导的 root_cause 与 impact：它们是候选，不是已确认的业务根因。",
            "- 任何 Target DWD / DWS / Semantic Layer 结论：本阶段不设计目标模型。",
            "",
            f"- 建议顺序：先处理 "
            f"{count_text(priority_counts, REVIEW_PRIORITY_ORDER)} 中的 P0"
            "（粒度、角色、覆盖缺口），再处理 P1（重复 / 重叠 / 聚合），"
            "最后看 P2 / P3。",
            f"- 进入 M4 前至少需要：{PROBLEM_CANDIDATE_NOTE}；P0 problem 必须有人工结论。",
            "",
        ]
    )


def render_current_state_problem_review_checklist(
    rows: Sequence[Mapping[str, Any]],
    *,
    carry_over: Mapping[str, Mapping[str, str]] | None = None,
) -> str:
    """生成 analysis/review/current-state-problem-review-checklist.md（人工回填清单）。

    按 problem_type（13 类）分区；每区最多 PROBLEM_CHECKLIST_ROW_LIMIT 行并注明总数。
    机器列由 `analyze --stage review` 生成、重跑会被覆盖；
    human_status / human_name / note 三列保留上一次的人工回填。
    """

    existing = carry_over or {}
    lines: list[str] = [
        "# M3.6 v2 Current-State Problem Review Checklist",
        "",
        "人工回填 human_status（pending / confirmed / rejected / needs_review / "
        "needs_discussion）、human_name 与 note；"
        "未回填的行一律保持机器阶段的 status，problem 不会自动变成 confirmed。",
        "",
        f"{PROBLEM_CANDIDATE_NOTE}；Finding Count ≠ Problem Count ≠ Confirmed Problem Count。",
        "",
        "problem_id 起到 human_question 为止的机器列由 "
        "`analyze --stage review` 生成，重跑会被覆盖；"
        "human_status / human_name / note 三列会被保留。",
        "",
        "scope_key 起到 human_question 的内容是机器观测，"
        "不是已确认的模型错误；回复 human_question 才是人工结论。",
        "",
    ]

    header = "| " + " | ".join(PROBLEM_CHECKLIST_HEADERS) + " |"
    separator = "| " + " | ".join("---" for _ in PROBLEM_CHECKLIST_HEADERS) + " |"

    if not rows:
        lines.extend([header, separator, "_（无 problem）_", ""])
        return "\n".join(lines)

    lines.extend([header, separator])

    for problem_type in PROBLEM_TYPE_ORDER:
        section = [row for row in rows if row.get("problem_type") == problem_type]
        lines.append(f"## {PROBLEM_TYPE_TITLE.get(problem_type, problem_type)}")
        lines.append("")

        if not section:
            lines.extend(["_（本区无 problem）_", ""])
            continue

        if len(section) > PROBLEM_CHECKLIST_ROW_LIMIT:
            lines.append(
                f"只列出前 {PROBLEM_CHECKLIST_ROW_LIMIT} 行，共 {len(section)} 行；"
                "其余行见 `analysis/review/current-state-problems.json`。"
            )
            lines.append("")

        lines.extend([header, separator])

        for row in section[:PROBLEM_CHECKLIST_ROW_LIMIT]:
            problem_id = str(row.get("problem_id") or "")
            previous = existing.get(problem_id, {})
            raw_status = str(previous.get("human_status", "") or "").strip()
            scope_key = str(row.get("scope_key") or "")

            if len(scope_key) > 80:
                scope_key = scope_key[:80] + "…"

            evidence = "、".join(
                f"{evidence_type}×{int(count)}"
                for evidence_type, count in (row.get("evidence_type_counts") or {}).items()
                if int(count)
            )
            cells = [
                problem_id,
                row.get("problem_type"),
                row.get("priority"),
                scope_key,
                evidence or "-",
                str(row.get("description") or ""),
                str(row.get("human_question") or ""),
                normalize_human_status(raw_status) or raw_status or "pending",
                str(previous.get("human_name", "") or "").strip(),
                str(previous.get("note", "") or "").strip(),
            ]
            lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |")

        lines.append("")

    return "\n".join(lines)


def _table(
    headers: list[object],
    rows: list[list[object]],
    limit: int | None = None,
    alignments: Sequence[str] | None = None,
) -> str:
    """渲染 Markdown 表格。

    alignments 与 headers 对应，取值 "left" / "right"，决定分隔行是
    ``---`` 还是 ``---:``；缺省全部左对齐，既有产物保持不变。
    """

    if limit is not None and len(rows) > limit:
        rows = rows[:limit]

    if not rows:
        # 即使没有数据也生成表头，确保必需列存在
        cells = [
            "---:"
            if alignments is not None
            and index < len(alignments)
            and str(alignments[index]).lower() == "right"
            else "---"
            for index, _ in enumerate(headers)
        ]
        header = "| " + " | ".join(str(item) for item in headers) + " |"
        separator = "| " + " | ".join(cells) + " |"
        return "\n".join([header, separator, "_（无数据）_"])

    cells = [
        "---:"
        if alignments is not None
        and index < len(alignments)
        and str(alignments[index]).lower() == "right"
        else "---"
        for index, _ in enumerate(headers)
    ]

    header = "| " + " | ".join(str(item) for item in headers) + " |"
    separator = "| " + " | ".join(cells) + " |"
    body = ["| " + " | ".join(str(item) for item in row) + " |" for row in rows]

    return "\n".join([header, separator, *body])


__all__ = [
    "CHECKLIST_HEADERS",
    "CHECKLIST_SECTIONS",
    "LIMITATION_BULLETS",
    "SummaryContext",
    "render_current_state_problem_review_checklist",
    "render_current_state_problem_summary",
    "render_current_state_review_checklist",
    "render_current_state_summary",
    "render_analysis_summary",
    "render_business_quality_report",
    "render_business_summary",
    "render_inventory_summary",
    "render_grain_review_checklist",
    "render_grain_summary",
    "render_layer_summary",
    "render_lineage_summary",
    "render_model_review_checklist",
    "render_model_summary",
    "render_object_graph",
    "render_process_review_checklist",
    "render_process_summary",
    "render_profiling_summary",
    "render_review_checklist",
]

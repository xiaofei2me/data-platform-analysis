"""M2.1～M2.5 与 M3 Business Understanding 的分析记录模型。

设计原则：

1. 稳定身份优先：Workspace 用 workspace_id，File 用 workspace_id + file_id，
   Table 用 workspace_id + project + schema + table。
2. 记录里保留来源引用（raw_file / content_file / evidence），
   让每条结论都能回到 Snapshot 原文。
3. 只表达事实与 Candidate，不表达业务结论。
4. M3 记录同样只表达「业务候选 + 证据链」：每个 Candidate 都带 evidence，
   evidence 只能回到 M2 产物（表 / 字段名与注释、SQL、血缘、层级判定）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ============================================================
# M2.1 Inventory
# ============================================================


@dataclass
class WorkspaceInventory:
    """Workspace 级分析清单。"""

    workspace_id: int
    workspace_name: str
    project: str
    dataworks_snapshot: str | None
    maxcompute_snapshot: str | None
    file_count: int = 0
    task_count: int = 0
    resource_count: int = 0
    table_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FileInventory:
    """DataWorks File 级分析清单。

    稳定身份是 workspace_id + file_id。
    NodeId 只是调度属性，不是 File 主键。
    """

    workspace_id: int
    file_id: int | str
    file_name: str | None
    node_id: int | str | None
    use_type: str | None
    file_type: int | None
    file_type_name: str
    task_type: str
    category: str
    content_format: str
    raw_file: str | None
    content_file: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def has_valid_node_id(node_id: int | str | None) -> bool:
    """判断 NodeId 是否有效。

    有效 = 非 None，且字符串形态去除空白后非空。
    None / "" / "   " 都视为没有 NodeId。
    """

    if node_id is None:
        return False

    if isinstance(node_id, str):
        return bool(node_id.strip())

    return True


def is_analysis_eligible(file: FileInventory) -> bool:
    """判断 File 是否属于正式 Analysis 输入范围。

    只有存在有效 NodeId 的 File 才是已提交的 DataWorks 节点，
    才进入 SQL / Table Reference / Lineage Analysis。

    NodeId 为空的 File 仍然保留在 Snapshot Inventory 中，
    这是 Analysis Scope Filter，不是 Analysis Error。
    """

    return has_valid_node_id(file.node_id)


@dataclass
class TableInventory:
    """MaxCompute Table 级分析清单。

    稳定身份是 project.table（table_key）。
    workspace_id 用于跨 Workspace 边界识别，schema 字段目前保留但不参与 identity。
    """

    workspace_id: int
    workspace_name: str
    project: str
    schema: str
    table: str
    comment: str | None
    column_count: int | None
    partition_count: int | None
    size: int | None
    is_virtual_view: bool | None
    lifecycle: int | None
    creation_time: str | None
    last_modified_time: str | None
    table_key: str
    raw_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ColumnInventory:
    """MaxCompute Column 级分析清单。"""

    workspace_id: int
    project: str
    schema: str
    table: str
    ordinal: int
    column_name: str
    data_type: str | None
    comment: str | None
    is_partition: bool
    table_key: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# M2.3 SQL Analysis
# ============================================================

PARSE_STATUS_SUCCESS = "success"
"""语句解析成功，已提取表引用。"""

PARSE_STATUS_UNSUPPORTED = "unsupported"
"""语句被识别，但语法不受解析器支持，未提取表引用。"""

PARSE_STATUS_ERROR = "error"
"""语句解析失败，已记录到 parse-errors.json。"""

EXTRACTION_METHOD_AST = "ast"
"""表引用来自 AST 解析。"""

EXTRACTION_METHOD_FALLBACK = "fallback"
"""表引用来自 CTAS token scanner fallback（AST 解析为 Command）。"""

EXTRACTION_METHOD_NONE = "none"
"""未提取表引用（unsupported / error，或语句不产生表引用）。"""


@dataclass
class StatementRecord:
    """单条 SQL 语句。

    一个 DataWorks File 可以产生多条语句，statement_id 从 1 开始。

    sql 永远是 Snapshot content 切出来的 raw fragment；
    Parser Compatibility Normalization 只作用于 parser input，
    不改写这里的原文，因此 normalizations 是可追溯的派生信息。
    """

    workspace_id: int
    file_id: int | str
    node_id: int | str | None
    file_name: str | None
    statement_id: int
    sql: str
    dialect: str
    parse_status: str
    extraction_method: str
    content_file: str | None
    normalization_applied: bool = False
    """该语句交给 parser 前是否发生了 Parser Compatibility Normalization。"""

    normalizations: list[dict[str, Any]] = field(default_factory=list)
    """替换明细，例如 [{"from": "）", "to": ")", "count": 1}]；顺序确定。"""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TableReference:
    """单条语句的表引用。

    保留 source / target 与 content_file，作为后续回答
    「为什么认为这两个表存在上下游关系」的 Evidence。
    """

    workspace_id: int
    file_id: int | str
    node_id: int | str | None
    file_name: str | None
    statement_id: int
    source_tables: list[str]
    target_tables: list[str]
    extraction_method: str
    content_file: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# M2.4 Table Lineage
# ============================================================


@dataclass
class LineageEvidence:
    """支撑一条 lineage edge 的 SQL 证据。"""

    file_id: int | str
    file_name: str | None
    node_id: int | str | None
    statement_id: int
    extraction_method: str
    content_file: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LineageEdge:
    """去重后的 source → target 表级血缘。

    source_table / target_table 是 SQL 中的原始写法；
    source_key / target_key 是补齐 Project 后的规范标识，
    用于跨 Workspace 依赖识别与全局统计。
    """

    workspace_id: int
    source_table: str
    target_table: str
    source_key: str
    target_key: str
    source_workspace_id: int | None
    target_workspace_id: int | None
    source_layer_candidate: str | None
    target_layer_candidate: str | None
    evidence: list[LineageEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# M2.5 Data Profiling
# ============================================================

PROFILE_STATUS_METADATA_ONLY = "metadata_only"
"""当前 Snapshot 只有元数据，没有行级数据样本。"""


@dataclass
class TableProfile:
    """表级 Profiling 结果。

    没有行级数据时：

    - profile_status = metadata_only
    - data_sample_available = false
    - row_count 等统计量为 null（不伪造）
    """

    workspace_id: int
    project: str
    schema: str
    table: str
    table_key: str
    profile_status: str
    data_sample_available: bool
    row_count: int | None
    size: int | None
    column_count: int | None
    partition_count: int | None
    comment: str | None
    is_virtual_view: bool | None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ColumnProfile:
    """字段级 Profiling 结果。

    没有行级数据时不能产生 candidate_key 结论：
    is_candidate_key 恒为 false，并用 profile_status 说明原因。
    """

    workspace_id: int
    project: str
    schema: str
    table: str
    table_key: str
    ordinal: int
    column_name: str
    data_type: str | None
    comment: str | None
    is_partition: bool
    profile_status: str
    is_candidate_key: bool
    null_count: int | None
    null_ratio: float | None
    distinct_count: int | None
    min_value: Any | None
    max_value: Any | None
    sample_values: list[Any] | None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# Core Table Candidates
# ============================================================


@dataclass
class CoreTableCandidate:
    """核心表候选。

    这里的排序只依据明确的数据指标（默认 downstream_count 降序），
    不是业务价值评分，也不是「最好 / 最差」的主观排名。
    """

    table_key: str
    workspace_id: int | None
    in_inventory: bool
    layer_candidate: str | None
    upstream_count: int
    downstream_count: int
    evidence_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# M2.2 Layer Assessment
# ============================================================

LAYER_STATUS_MATCH = "MATCH"
"""唯一确定一个子层（或 Workspace Layer 本身就是终点层）。"""

LAYER_STATUS_UNKNOWN = "UNKNOWN"
"""Evidence 不足以判断子层；不代表不符合命名规范。"""

LAYER_STATUS_CONFLICT = "CONFLICT"
"""同时命中多个不同子层，不擅自选择。"""

EVIDENCE_TYPE_WORKSPACE = "workspace"
"""来自 workspace_layers 配置的 Workspace Layer 事实。"""

EVIDENCE_TYPE_PREFIX = "prefix"
"""命中某条 prefix 规则。"""

EVIDENCE_TYPE_SUFFIX = "suffix"
"""命中某条 suffix 规则。"""


@dataclass
class LayerAssessment:
    """单张表的 M2.2 Layer Assessment。

    1. workspace_layer 是 Observed / Configured Fact，来自 workspace_id 查表。
    2. candidate_layer 是唯一的层级候选：ODS / ADS 取 workspace_layer，
       CDM 取子层规则命中，未配置或未命中为 None。
    3. status=UNKNOWN 只表示 Evidence 不足，不产生 violation。
    4. evidence 保留全部命中规则，供后续 Convention Assessment 复用。
    """

    workspace_id: int
    workspace_name: str
    workspace_layer: str | None
    project: str
    table_name: str
    table_identifier: str

    candidate_layer: str | None
    status: str

    evidence: list[dict[str, Any]] = field(default_factory=list)

    @property
    def cross_layer_hits(self) -> list[dict[str, Any]]:
        """evidence 中与 candidate_layer 不一致的子层命中（跨层命名提示）。

        只提示，不改变 candidate_layer：candidate 按 workspace 事实判定，
        表名带其他层命名前缀（如 ODS workspace 里的 dim_ 表）在这里暴露。
        """

        if self.candidate_layer is None:
            return []

        return [
            hit
            for hit in self.evidence
            if hit.get("type") != EVIDENCE_TYPE_WORKSPACE
            and hit.get("layer") != self.candidate_layer
        ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# M3 Business Understanding
# ============================================================

BUSINESS_CONFIDENCE_HIGH = "high"
"""多个独立证据来源同时命中（≥3 种 evidence type）。"""

BUSINESS_CONFIDENCE_MEDIUM = "medium"
"""两个证据来源命中，或唯一的证据来源是表注释（强证据）。"""

BUSINESS_CONFIDENCE_LOW = "low"
"""只有一个非表注释的证据来源。"""

BUSINESS_CONFIDENCE_UNKNOWN = "unknown"
"""没有任何业务词命中，无法给出 Domain / Object 候选。"""

BUSINESS_CONFIDENCE_ORDER: tuple[str, ...] = (
    BUSINESS_CONFIDENCE_HIGH,
    BUSINESS_CONFIDENCE_MEDIUM,
    BUSINESS_CONFIDENCE_LOW,
    BUSINESS_CONFIDENCE_UNKNOWN,
)
"""confidence 的固定展示与排序顺序。"""

BUSINESS_EVIDENCE_TABLE_NAME = "table_name"
"""来自 inventory/tables.json 的表名分词命中。"""

BUSINESS_EVIDENCE_TABLE_COMMENT = "table_comment"
"""来自 inventory/tables.json 的表注释关键词命中（强证据）。"""

BUSINESS_EVIDENCE_COLUMN_NAME = "column_name"
"""来自 inventory/columns.json 的字段名分词命中。"""

BUSINESS_EVIDENCE_COLUMN_COMMENT = "column_comment"
"""来自 inventory/columns.json 的字段注释关键词命中。"""

BUSINESS_EVIDENCE_SQL = "sql"
"""来自 sql/statements.json + sql/table-references.json 的语句关键词命中。"""

BUSINESS_EVIDENCE_LINEAGE = "lineage"
"""来自 lineage/table-lineage.json 的上下游表名关键词传播命中。"""

BUSINESS_EVIDENCE_ORDER: tuple[str, ...] = (
    BUSINESS_EVIDENCE_TABLE_NAME,
    BUSINESS_EVIDENCE_TABLE_COMMENT,
    BUSINESS_EVIDENCE_COLUMN_NAME,
    BUSINESS_EVIDENCE_COLUMN_COMMENT,
    BUSINESS_EVIDENCE_SQL,
    BUSINESS_EVIDENCE_LINEAGE,
)
"""evidence type 的固定展示与排序顺序（证据强度从直接到派生）。"""

BUSINESS_TERM_SOURCE_TABLE_NAME = "table_name"
BUSINESS_TERM_SOURCE_COLUMN_NAME = "column_name"

BUSINESS_TERM_SOURCE_ORDER: tuple[str, ...] = (
    BUSINESS_TERM_SOURCE_TABLE_NAME,
    BUSINESS_TERM_SOURCE_COLUMN_NAME,
)
"""terms.json 中 source type 的固定排序顺序。"""


@dataclass
class BusinessTerm:
    """业务术语候选及来源。

    term 是出现次数最多的原始写法（并列取字典序最小），
    normalized_term 是 casefold 后的归一形态，用于跨大小写聚合。
    sources 保留每个来源位置，保证可追溯。
    """

    term: str
    normalized_term: str
    count: int
    sources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DomainCandidate:
    """单张表的业务 Domain 候选。

    同时命中多个 Domain 时全部保留，不擅自选择；
    evidence 是支撑该候选的证据子集（与表级 evidence 同源）。
    """

    domain: str
    name: str
    confidence: str
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessObjectCandidate:
    """单张表的业务对象候选（customer / product / order …）。

    业务对象是业务概念候选，不等于 DIM / DWD / DWS，
    不与数仓层混用。
    """

    object: str
    name: str
    confidence: str
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DomainTableRef:
    """domains.json 中的表引用。"""

    table_key: str
    confidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DomainSummary:
    """单个 Domain 的候选汇总（domains.json）。"""

    domain: str
    name: str
    table_count: int
    confidence_counts: dict[str, int] = field(default_factory=dict)
    evidence_type_counts: dict[str, int] = field(default_factory=dict)
    tables: list[DomainTableRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ObjectSummary:
    """单个业务对象的候选汇总（objects.json）。"""

    object: str
    name: str
    table_count: int
    confidence_counts: dict[str, int] = field(default_factory=dict)
    evidence_type_counts: dict[str, int] = field(default_factory=dict)
    tables: list[DomainTableRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessTableUnderstanding:
    """单张表的 M3 业务理解结果（analysis/business/tables.json）。

    1. warehouse_layer / candidate_sub_layer 只读取 M2.2 Layer Assessment，
       M3 不自行判定层级，也不因「像 DWD / DWS」而修改层级。
    2. domain_candidates / business_object_candidates 全是 Candidate，
       evidence 保留每条判断依据；表级 evidence 是全部证据的并集。
    3. business_terms 是表名 + 字段名分词后剔除 stopwords 的业务词，
       按（表内出现次数降序，词升序）稳定排序。
    """

    workspace_id: int
    project: str
    table: str
    table_key: str
    warehouse_layer: str | None
    candidate_sub_layer: str | None
    is_core_candidate: bool
    business_terms: list[str] = field(default_factory=list)
    domain_candidates: list[DomainCandidate] = field(default_factory=list)
    business_object_candidates: list[BusinessObjectCandidate] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_unknown(self) -> bool:
        """没有任何 Domain / Object 命中（业务语义不可判断）。"""

        return not self.domain_candidates and not self.business_object_candidates

    @property
    def is_ambiguous(self) -> bool:
        """同时命中多个 Domain，需要人工判定。"""

        return len(self.domain_candidates) > 1

    @property
    def has_strong_evidence(self) -> bool:
        """存在 high 级别的 Domain 或 Object 候选。"""

        return any(
            item.confidence == BUSINESS_CONFIDENCE_HIGH
            for item in self.domain_candidates
        ) or any(
            item.confidence == BUSINESS_CONFIDENCE_HIGH
            for item in self.business_object_candidates
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# M3.1 Business Understanding Quality Assessment
# ============================================================

QUALITY_UNKNOWN_COMMENT = "comment_evidence_present"
"""表注释 / 字段注释里存在可用信号，但没有业务词命中（词典缺口）。"""

QUALITY_UNKNOWN_SQL = "sql_evidence_present"
"""表被 SQL 语句引用，说明它参与业务流转，但名称与注释都没有业务词命中。"""

QUALITY_UNKNOWN_NAMING = "naming_evidence_present"
"""表名 / 字段名分词产出了业务词，但词典未覆盖（词典缺口）。"""

QUALITY_UNKNOWN_INSUFFICIENT = "insufficient_evidence"
"""只有血缘等间接信号，证据不足以给出 Domain / Object 候选。"""

QUALITY_UNKNOWN_SPARSE = "evidence_sparse"
"""没有任何可用信号：无注释、无 SQL 引用、无业务词、无血缘。"""

QUALITY_UNKNOWN_REASON_ORDER: tuple[str, ...] = (
    QUALITY_UNKNOWN_COMMENT,
    QUALITY_UNKNOWN_SQL,
    QUALITY_UNKNOWN_NAMING,
    QUALITY_UNKNOWN_INSUFFICIENT,
    QUALITY_UNKNOWN_SPARSE,
)
"""UNKNOWN 主因的级联判定顺序（首个命中生效），by_reason 固定按此顺序。"""

QUALITY_UNKNOWN_CORE = "core_unknown"
"""UNKNOWN 的重叠标记：该表同时是核心表候选，不计入 by_reason 合计。"""

QUALITY_AMBIGUOUS_MULTI_DOMAIN = "multi_domain_likely"
"""多个 Domain 各自证据充分且证据位置不重叠，可能确实跨多个业务主题。"""

QUALITY_AMBIGUOUS_DOMINANT = "dominant_domain"
"""一个 Domain 明显强于其余候选，但仍未收敛到唯一候选。"""

QUALITY_AMBIGUOUS_KEYWORD = "keyword_cooccurrence"
"""候选共享同一证据位置，关键词共现造成多候选。"""

QUALITY_AMBIGUOUS_CONFLICT = "evidence_conflict"
"""候选的证据类型集合互不相交，证据互相矛盾。"""

QUALITY_AMBIGUOUS_UNRESOLVED = "unresolved"
"""不满足以上任何规则，保持多候选等待人工判定。"""

QUALITY_AMBIGUOUS_REASON_ORDER: tuple[str, ...] = (
    QUALITY_AMBIGUOUS_MULTI_DOMAIN,
    QUALITY_AMBIGUOUS_DOMINANT,
    QUALITY_AMBIGUOUS_KEYWORD,
    QUALITY_AMBIGUOUS_CONFLICT,
    QUALITY_AMBIGUOUS_UNRESOLVED,
)
"""AMBIGUOUS 主因的固定展示与排序顺序。"""

QUALITY_CONFIDENCE_RANK: dict[str, int] = {
    BUSINESS_CONFIDENCE_HIGH: 3,
    BUSINESS_CONFIDENCE_MEDIUM: 2,
    BUSINESS_CONFIDENCE_LOW: 1,
}
"""AMBIGUOUS 分类用的 confidence 权重，未知 confidence 权重为 0。"""

QUALITY_STRONG_MIN_RANK = 2
"""「强候选」的最低 confidence 权重（medium 及以上）。"""

QUALITY_STRONG_MIN_DIVERSITY = 2
"""「强候选」的最低证据类型数。"""

BUSINESS_NAMING_EVIDENCE_TYPES: tuple[str, ...] = (
    BUSINESS_EVIDENCE_TABLE_NAME,
    BUSINESS_EVIDENCE_TABLE_COMMENT,
    BUSINESS_EVIDENCE_COLUMN_NAME,
    BUSINESS_EVIDENCE_COLUMN_COMMENT,
)
"""纯命名类证据（不含 SQL / 血缘），用于识别 high_naming_only。"""

QUALITY_DIVERSITY_BUCKETS: tuple[str, ...] = ("0", "1", "2", "3+")
"""证据类型数（diversity）的固定分桶。"""

QUALITY_SAMPLE_LIMIT = 20
"""quality-assessment.json 中每类样本的固定上限（稳定排序后截断）。"""

QUALITY_CHECKLIST_ROW_LIMIT = 50
"""review-checklist.md 中每个 Priority 分区的固定行数上限。"""

QUALITY_REPORT_SAMPLE_LIMIT = 10
"""quality-assessment.md 中每张样本表的固定行数上限。"""


def quality_diversity_bucket(value: int) -> str:
    """把证据类型数落到固定分桶（0 / 1 / 2 / 3+）。"""

    if value >= 3:
        return QUALITY_DIVERSITY_BUCKETS[3]

    if value <= 0:
        return QUALITY_DIVERSITY_BUCKETS[0]

    return QUALITY_DIVERSITY_BUCKETS[value]


@dataclass
class QualitySample:
    """质量评估抽样明细（UNKNOWN / AMBIGUOUS / 核心表复核共用）。

    candidate_domains / candidate_objects 是 `key(confidence)` 形式的紧凑写法，
    候选全量明细仍以 analysis/business/tables.json 为准。
    """

    table_key: str
    workspace_id: int
    project: str
    table: str
    warehouse_layer: str | None
    candidate_sub_layer: str | None
    is_core_candidate: bool
    candidate_domains: list[str] = field(default_factory=list)
    candidate_objects: list[str] = field(default_factory=list)
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    unknown_reason: str | None = None
    ambiguous_reason: str | None = None
    reason_tags: list[str] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualityChecklistRow:
    """review-checklist.md 的一行。

    human domain / human object 由人工填写、status 初始为 pending，
    渲染时统一输出，不在数据里占位。
    """

    priority: int
    table: str
    domain_candidates: str
    object_candidates: str
    evidence: str
    note: str


@dataclass
class BusinessQualityResult:
    """一次 M3.1 运行的结果。

    summary / unknown / ambiguous / evidence_quality / confidence_review /
    core_table_review 就是 quality-assessment.json 的六个顶层小节（固定顺序）；
    checklist 只用于渲染 review-checklist.md，不进 JSON。
    """

    summary: dict[str, Any] = field(default_factory=dict)
    unknown: dict[str, Any] = field(default_factory=dict)
    ambiguous: dict[str, Any] = field(default_factory=dict)
    evidence_quality: dict[str, Any] = field(default_factory=dict)
    confidence_review: dict[str, Any] = field(default_factory=dict)
    core_table_review: dict[str, Any] = field(default_factory=dict)
    checklist: list[QualityChecklistRow] = field(default_factory=list)
    analysis_dir: Path = field(default_factory=Path)

    def to_dict(self) -> dict[str, Any]:
        """只返回 JSON 的六个顶层小节，checklist 不进 JSON。"""

        return {
            "summary": self.summary,
            "unknown": self.unknown,
            "ambiguous": self.ambiguous,
            "evidence_quality": self.evidence_quality,
            "confidence_review": self.confidence_review,
            "core_table_review": self.core_table_review,
        }


# ============================================================
# M3.2 Business Object & Relationship Analysis
# ============================================================

OBJECT_STATUS_CANDIDATE = "candidate"
"""默认状态：机器识别出的候选，未出现在人工确认清单的回填结果里。"""

OBJECT_STATUS_CONFIRMED = "confirmed"
"""review-checklist.md 中人工显式确认的 Object。"""

OBJECT_STATUS_REJECTED = "rejected"
"""review-checklist.md 中人工显式否决的 Object。"""

OBJECT_STATUS_NEEDS_DISCUSSION = "needs_discussion"
"""review-checklist.md 中人工标记为待讨论的 Object。"""

OBJECT_STATUS_ORDER: tuple[str, ...] = (
    OBJECT_STATUS_CANDIDATE,
    OBJECT_STATUS_CONFIRMED,
    OBJECT_STATUS_REJECTED,
    OBJECT_STATUS_NEEDS_DISCUSSION,
)
"""Object 状态的固定展示与排序顺序；默认永远排在最前。"""

OBJECT_STATUS_SET: frozenset[str] = frozenset(OBJECT_STATUS_ORDER)
"""review-checklist.md 中被认可的 status 取值（其余一律视为未回填）。"""

RELATIONSHIP_TYPE_CANDIDATE = "candidate"
"""M3.2 只产出 candidate 关系，不产出 owns / contains / belongs_to / one-to-many。"""

RELATIONSHIP_EVIDENCE_CO_OCCURRENCE = "co_occurrence"
"""同一张表同时是两个 Object 的候选（Level 1）。"""

RELATIONSHIP_EVIDENCE_SQL = "sql_reference"
"""同一条 SQL 语句同时引用了两个表，两表分属两个 Object（Level 2）。"""

RELATIONSHIP_EVIDENCE_LINEAGE = "lineage"
"""一条表级血缘连接了两个表，两表分属两个 Object（Level 3）。"""

RELATIONSHIP_EVIDENCE_ORDER: tuple[str, ...] = (
    RELATIONSHIP_EVIDENCE_CO_OCCURRENCE,
    RELATIONSHIP_EVIDENCE_SQL,
    RELATIONSHIP_EVIDENCE_LINEAGE,
)
"""关系证据类型的固定展示与排序顺序（Level 1 → Level 3）。"""

EVIDENCE_STRENGTH_WEAK = "weak"
"""只有 1 类关系证据。"""

EVIDENCE_STRENGTH_MODERATE = "moderate"
"""有 2 类关系证据。"""

EVIDENCE_STRENGTH_STRONG = "strong"
"""有 3 类关系证据。"""


EVIDENCE_STRENGTH_ORDER: tuple[str, ...] = (
    EVIDENCE_STRENGTH_WEAK,
    EVIDENCE_STRENGTH_MODERATE,
    EVIDENCE_STRENGTH_STRONG,
)
"""evidence_strength 的固定展示与排序顺序。"""


def evidence_strength(evidence_diversity: int) -> str:
    """按关系证据类型数给出 evidence_strength（确定性规则）。

    只反映证据类型数，不是 confidence / probability / certainty：
    1 类 = weak，2 类 = moderate，3 类及以上 = strong；0 类按 weak 计。
    """

    if evidence_diversity >= 3:
        return EVIDENCE_STRENGTH_STRONG

    if evidence_diversity == 2:
        return EVIDENCE_STRENGTH_MODERATE

    return EVIDENCE_STRENGTH_WEAK


OBJECT_GRAPH_ROW_LIMIT = 100
"""object-graph.md 中关系明细表的固定行数上限（稳定排序后截断）。"""


@dataclass
class BusinessObjectResult:
    """一次 M3.2 运行的结果。

    registry / associations / relationships / matrix 就是四个 JSON 产物的
    顶层 payload（固定顺序），graph 是 object-graph.md 的正文；
    全部只表达候选与证据，不表达业务结论。
    """

    registry: dict[str, Any] = field(default_factory=dict)
    associations: dict[str, Any] = field(default_factory=dict)
    relationships: dict[str, Any] = field(default_factory=dict)
    matrix: dict[str, Any] = field(default_factory=dict)
    graph: str = ""
    analysis_dir: Path = field(default_factory=Path)

    @property
    def object_count(self) -> int:
        return int(self.registry.get("count") or 0)

    @property
    def association_count(self) -> int:
        return int(self.associations.get("count") or 0)

    @property
    def relationship_count(self) -> int:
        return int(self.relationships.get("count") or 0)

    @property
    def core_relationship_count(self) -> int:
        """至少一个 endpoint 关联核心表候选的关系数量。"""

        return sum(
            1
            for item in self.relationships.get("relationships") or []
            if item.get("core_related")
        )

    @property
    def object_status_counts(self) -> dict[str, int]:
        return dict(self.registry.get("status_counts") or {})

    @property
    def association_status_counts(self) -> dict[str, int]:
        return dict(self.associations.get("status_counts") or {})

    @property
    def evidence_distribution(self) -> dict[str, dict[str, int]]:
        return dict(self.relationships.get("evidence_distribution") or {})


# ============================================================
# M3.3 Business Process Candidate Analysis
# ============================================================

PROCESS_SIGNAL_TRANSACTION_ID = "transaction_id"
"""列级信号：字段具备事务标识语义（config/process-rules.yaml）。"""

PROCESS_SIGNAL_TRANSACTION_MEASURE = "transaction_measure"
"""列级信号：字段具备可聚合度量语义。"""

PROCESS_SIGNAL_EVENT_TIME = "event_time"
"""列级信号：字段具备事件时间语义。"""

PROCESS_SIGNAL_STATUS = "status"
"""列级信号：字段具备状态语义。"""

PROCESS_SIGNAL_MULTI_OBJECT = "multi_object"
"""表级信号：同一张表参与 ≥2 个 Business Object Candidate。"""

PROCESS_SIGNAL_LIFECYCLE = "lifecycle"
"""表级信号：同一张表同时出现 status 与 event_time 两类列级信号。"""

PROCESS_COLUMN_SIGNAL_ORDER: tuple[str, ...] = (
    PROCESS_SIGNAL_TRANSACTION_ID,
    PROCESS_SIGNAL_TRANSACTION_MEASURE,
    PROCESS_SIGNAL_EVENT_TIME,
    PROCESS_SIGNAL_STATUS,
)
"""列级过程信号的固定展示与排序顺序。"""

PROCESS_TABLE_SIGNAL_ORDER: tuple[str, ...] = (
    PROCESS_SIGNAL_MULTI_OBJECT,
    PROCESS_SIGNAL_LIFECYCLE,
)
"""表级过程信号的固定展示与排序顺序。"""

PROCESS_SIGNAL_TYPE_ORDER: tuple[str, ...] = (
    *PROCESS_COLUMN_SIGNAL_ORDER,
    *PROCESS_TABLE_SIGNAL_ORDER,
)
"""全部过程信号类型的固定展示与排序顺序（列级在前，表级在后）。"""

PROCESS_SIGNAL_TYPE_SET: frozenset[str] = frozenset(PROCESS_SIGNAL_TYPE_ORDER)
"""受支持的过程信号类型；其余一律视为配置 / 数据错误。"""

PROCESS_STATUS_CANDIDATE = "candidate"
"""M3.3 只产出 process candidate，不产出 confirmed process。"""

PROCESS_STATUS_ORDER: tuple[str, ...] = (PROCESS_STATUS_CANDIDATE,)
PROCESS_STATUS_SET: frozenset[str] = frozenset(PROCESS_STATUS_ORDER)

PROCESS_LEVEL_1 = "level_1"
"""Level 1：transaction signal + 至少一个
（Object participation / Measure / Event time / Status）。"""

PROCESS_LEVEL_2 = "level_2"
"""Level 2：参与 Object ≥2 + 至少一个（SQL reference / Lineage / Measure / Event time）。"""

PROCESS_LEVEL_3 = "level_3"
"""Level 3：Object 集合内存在 M3.2 relationship
+ 至少一个（transaction / event_time / measure / status）。"""

PROCESS_LEVEL_ORDER: tuple[str, ...] = (PROCESS_LEVEL_1, PROCESS_LEVEL_2, PROCESS_LEVEL_3)
"""形成门槛的固定展示与排序顺序（Level 1 → Level 3）。"""

PROCESS_STRENGTH_WEAK = "weak"
PROCESS_STRENGTH_MODERATE = "moderate"
PROCESS_STRENGTH_STRONG = "strong"

PROCESS_STRENGTH_ORDER: tuple[str, ...] = (
    PROCESS_STRENGTH_WEAK,
    PROCESS_STRENGTH_MODERATE,
    PROCESS_STRENGTH_STRONG,
)
"""process_evidence_strength 的固定展示与排序顺序。"""

PROCESS_STRENGTH_BY_LEVEL: dict[str, str] = {
    PROCESS_LEVEL_1: PROCESS_STRENGTH_WEAK,
    PROCESS_LEVEL_2: PROCESS_STRENGTH_MODERATE,
    PROCESS_LEVEL_3: PROCESS_STRENGTH_STRONG,
}
"""最强命中 Level → process_evidence_strength（确定性规则，不是 confidence）。"""


def process_evidence_strength(levels: Sequence[str]) -> str:
    """按命中的最高 Level 给出 process_evidence_strength。

    Level 3 → strong，Level 2 → moderate，只有 Level 1 → weak；
    空 Levels 不应出现在候选上，按 weak 计。
    """

    if PROCESS_LEVEL_3 in levels:
        return PROCESS_STRENGTH_STRONG

    if PROCESS_LEVEL_2 in levels:
        return PROCESS_STRENGTH_MODERATE

    return PROCESS_STRENGTH_WEAK


PROCESS_ROLE_PARTICIPANT = "participant"
"""process → object 的角色：只表达「参与」，不表达 fact / dimension / owner。"""

PROCESS_ROLE_ORDER: tuple[str, ...] = (PROCESS_ROLE_PARTICIPANT,)
PROCESS_ROLE_SET: frozenset[str] = frozenset(PROCESS_ROLE_ORDER)

PROCESS_UNRESOLVED_NAME = "process name not confirmed"
PROCESS_UNRESOLVED_SEMANTICS = "process semantics not confirmed"
PROCESS_UNRESOLVED_GRAIN = "grain not determined"
PROCESS_UNRESOLVED_VALIDATION = "business validation required"
PROCESS_UNRESOLVED_SQL = "sql reference evidence missing"
PROCESS_UNRESOLVED_LINEAGE = "lineage evidence missing"
PROCESS_UNRESOLVED_RELATIONSHIP = "object relationship evidence missing"
"""unresolved_questions 的固定取值（前四条恒在，后三条按证据缺失条件追加）。"""

PROCESS_UNRESOLVED_REQUIRED: tuple[str, ...] = (
    PROCESS_UNRESOLVED_NAME,
    PROCESS_UNRESOLVED_SEMANTICS,
    PROCESS_UNRESOLVED_GRAIN,
    PROCESS_UNRESOLVED_VALIDATION,
)

GRAIN_SIGNAL_TRANSACTION_IDENTIFIER = "transaction_identifier"
GRAIN_SIGNAL_AGGREGATION_COLUMNS = "aggregation_columns"
GRAIN_SIGNAL_TIME_GROUPING = "time_grouping"
"""只记录 grain 相关信号，不产出 grain 结论。"""

GRAIN_SIGNAL_ORDER: tuple[str, ...] = (
    GRAIN_SIGNAL_TRANSACTION_IDENTIFIER,
    GRAIN_SIGNAL_AGGREGATION_COLUMNS,
    GRAIN_SIGNAL_TIME_GROUPING,
)

GRAIN_UNDETERMINED_NOTE = "grain not determined"
"""grain_signals 里必须出现的固定措辞，避免下游误读为 grain 结论。"""

PROCESS_REPORT_ROW_LIMIT = 100
"""process-summary.md 中明细表的固定行数上限（稳定排序后截断）。"""

PROCESS_SIGNAL_EXAMPLE_LIMIT = 5
"""grain_signals.examples 的固定示例条数（稳定排序后截断）。"""

PROCESS_CANDIDATE_TERM_LIMIT = 20
"""candidate_terms 的固定条数上限。"""

PROCESS_TABLE_EXAMPLE_LIMIT = 10
"""grain_signals 中每个信号列出的表数量上限（稳定排序后截断）。"""


@dataclass
class BusinessProcessResult:
    """一次 M3.3 运行的结果。

    signals / processes / process_tables / process_objects 就是四个 JSON 产物的
    顶层 payload（固定顺序），summary 与 checklist 是两个 Markdown 产物正文；
    全部只表达 candidate 与证据，不表达已确认的业务过程。
    """

    signals: dict[str, Any] = field(default_factory=dict)
    processes: dict[str, Any] = field(default_factory=dict)
    process_tables: dict[str, Any] = field(default_factory=dict)
    process_objects: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    checklist: str = ""
    analysis_dir: Path = field(default_factory=Path)

    @property
    def signal_count(self) -> int:
        return int(self.signals.get("count") or 0)

    @property
    def process_count(self) -> int:
        return int(self.processes.get("count") or 0)

    @property
    def process_table_count(self) -> int:
        return int(self.process_tables.get("count") or 0)

    @property
    def process_object_count(self) -> int:
        return int(self.process_objects.get("count") or 0)

    @property
    def core_process_count(self) -> int:
        """包含至少一张核心表候选的 process candidate 数量。"""

        return sum(
            1
            for item in self.processes.get("processes") or []
            if int(item.get("core_table_count") or 0) > 0
        )

    @property
    def signal_type_counts(self) -> dict[str, int]:
        counts = {signal_type: 0 for signal_type in PROCESS_SIGNAL_TYPE_ORDER}

        for item in self.signals.get("signals") or []:
            signal_type = str(item.get("signal_type") or "")
            counts[signal_type] = counts.get(signal_type, 0) + 1

        return counts

    @property
    def process_status_counts(self) -> dict[str, int]:
        return dict(self.processes.get("status_counts") or {})

    @property
    def process_strength_counts(self) -> dict[str, int]:
        return dict(self.processes.get("strength_counts") or {})

    @property
    def object_count(self) -> int:
        """参与 process candidate 的 Business Object 数量（去重）。"""

        objects: dict[str, None] = {}

        for item in self.processes.get("processes") or []:
            for name in item.get("objects") or []:
                objects.setdefault(str(name), None)

        return len(objects)


# ============================================================
# M3.4 Grain Candidate Analysis
# ============================================================

GRAIN_SIGNAL_IDENTIFIER = "identifier"
"""Grain Signal：标识字段（M3.3 transaction_id 信号，或字段名的标识形态）。"""

GRAIN_SIGNAL_TIME = "time"
"""Grain Signal：时间字段（M3.3 event_time 信号，或字段名的日期 / 周期形态）。"""

GRAIN_SIGNAL_MEASURE = "measure"
"""Grain Signal：度量字段（M3.3 transaction_measure 信号）。"""

GRAIN_SIGNAL_SNAPSHOT = "snapshot"
"""Grain Signal：快照字段（字段名的快照形态）。"""

GRAIN_SIGNAL_EVENT = "event"
"""Grain Signal：事件字段（字段名的事件形态）。"""

GRAIN_SIGNAL_PERIODIC = "periodic"
"""Grain Signal：周期字段（字段名的年 / 月 / 季 / 周形态）。"""

GRAIN_SIGNAL_AGGREGATION = "aggregation"
"""Grain Signal：聚合形态（表上有度量信号但没有事务标识信号）。"""

GRAIN_SIGNAL_TYPE_ORDER: tuple[str, ...] = (
    GRAIN_SIGNAL_IDENTIFIER,
    GRAIN_SIGNAL_TIME,
    GRAIN_SIGNAL_MEASURE,
    GRAIN_SIGNAL_SNAPSHOT,
    GRAIN_SIGNAL_EVENT,
    GRAIN_SIGNAL_PERIODIC,
    GRAIN_SIGNAL_AGGREGATION,
)
"""M3.4 七类 Grain Signal 的固定展示与排序顺序。"""

GRAIN_SIGNAL_TYPE_SET: frozenset[str] = frozenset(GRAIN_SIGNAL_TYPE_ORDER)
"""受支持的 Grain Signal 类型；其余一律视为数据错误。"""

GRAIN_PATTERN_TRANSACTION = "transaction"
"""Grain Candidate 形态：候选键含事务标识字段（交易型证据）。"""

GRAIN_PATTERN_SNAPSHOT = "snapshot"
"""Grain Candidate 形态：候选键含快照字段（快照型证据）。"""

GRAIN_PATTERN_EVENT = "event"
"""Grain Candidate 形态：候选键含事件字段（事件型证据）。"""

GRAIN_PATTERN_PERIODIC = "periodic"
"""Grain Candidate 形态：候选键含周期字段（周期型证据）。"""

GRAIN_PATTERN_AGGREGATION = "aggregation"
"""Grain Candidate 形态：无事务标识的度量 + 时间分组（聚合型证据）。"""

GRAIN_PATTERN_UNKNOWN = "unknown"
"""Grain Candidate 形态：证据不足以判断形态（不猜）。"""

GRAIN_PATTERN_ORDER: tuple[str, ...] = (
    GRAIN_PATTERN_TRANSACTION,
    GRAIN_PATTERN_SNAPSHOT,
    GRAIN_PATTERN_EVENT,
    GRAIN_PATTERN_PERIODIC,
    GRAIN_PATTERN_AGGREGATION,
    GRAIN_PATTERN_UNKNOWN,
)
"""grain_pattern 的固定展示与排序顺序。"""

GRAIN_STATUS_CANDIDATE = "candidate"
"""M3.4 只产出 grain candidate，不产出 confirmed grain。"""

GRAIN_STATUS_ORDER: tuple[str, ...] = (GRAIN_STATUS_CANDIDATE,)
GRAIN_STATUS_SET: frozenset[str] = frozenset(GRAIN_STATUS_ORDER)

GRAIN_ROLE_ANCHOR = "anchor"
"""grain → table 角色：候选键来自该表（技术角色，不是 fact / dimension）。"""

GRAIN_ROLE_SUPPORTING = "supporting"
"""grain → table 角色：该表同样包含全部候选键，只作证据补充。"""

GRAIN_ROLE_ORDER: tuple[str, ...] = (GRAIN_ROLE_ANCHOR, GRAIN_ROLE_SUPPORTING)
GRAIN_ROLE_SET: frozenset[str] = frozenset(GRAIN_ROLE_ORDER)

GRAIN_EVIDENCE_PROCESS_SIGNAL = "process_signal"
GRAIN_EVIDENCE_COLUMN = "column"
GRAIN_EVIDENCE_TABLE = "table"
GRAIN_EVIDENCE_SQL = "sql"
GRAIN_EVIDENCE_LINEAGE = "lineage"
GRAIN_EVIDENCE_OBJECT = "object"
GRAIN_EVIDENCE_OBJECT_RELATIONSHIP = "object_relationship"

GRAIN_EVIDENCE_ORDER: tuple[str, ...] = (
    GRAIN_EVIDENCE_PROCESS_SIGNAL,
    GRAIN_EVIDENCE_COLUMN,
    GRAIN_EVIDENCE_TABLE,
    GRAIN_EVIDENCE_SQL,
    GRAIN_EVIDENCE_LINEAGE,
    GRAIN_EVIDENCE_OBJECT,
    GRAIN_EVIDENCE_OBJECT_RELATIONSHIP,
)
"""Grain Candidate evidence source_type 的固定展示与排序顺序。"""

GRAIN_EVIDENCE_SET: frozenset[str] = frozenset(GRAIN_EVIDENCE_ORDER)

GRAIN_UNRESOLVED_NO_IDENTIFIER = "no_identifier_signal"
GRAIN_UNRESOLVED_MULTIPLE_KEYS = "multiple_possible_keys"
GRAIN_UNRESOLVED_SQL = "missing_sql_evidence"
GRAIN_UNRESOLVED_LINEAGE = "missing_lineage_evidence"
GRAIN_UNRESOLVED_TIME = "time_semantics_unclear"
GRAIN_UNRESOLVED_AGGREGATION = "aggregation_level_unclear"
GRAIN_UNRESOLVED_INSUFFICIENT = "insufficient_evidence"
"""unresolved_reasons 的固定取值：只表示当前证据不足，不是业务结论。"""

GRAIN_UNRESOLVED_ORDER: tuple[str, ...] = (
    GRAIN_UNRESOLVED_NO_IDENTIFIER,
    GRAIN_UNRESOLVED_MULTIPLE_KEYS,
    GRAIN_UNRESOLVED_SQL,
    GRAIN_UNRESOLVED_LINEAGE,
    GRAIN_UNRESOLVED_TIME,
    GRAIN_UNRESOLVED_AGGREGATION,
    GRAIN_UNRESOLVED_INSUFFICIENT,
)
"""unresolved_reasons 的固定展示与排序顺序。"""

GRAIN_UNRESOLVED_SET: frozenset[str] = frozenset(GRAIN_UNRESOLVED_ORDER)

GRAIN_CANDIDATE_NOTE = "grain candidate 不是 confirmed grain"
"""所有 grain 产物里必须出现的固定措辞，避免下游误读成 Grain 结论。"""

GRAIN_REPORT_ROW_LIMIT = 50
"""grain-summary.md 中明细表的固定行数上限（稳定排序后截断）。"""

GRAIN_CHECKLIST_ROW_LIMIT = 50
"""grain-review-checklist.md 中每个 process 的固定行数上限。"""

GRAIN_SIGNAL_EXAMPLE_LIMIT = 5
"""grain signal reason / 聚合证据里列出的字段示例上限。"""


@dataclass
class BusinessGrainResult:
    """一次 M3.4 运行的结果。

    signals / candidates / grain_tables 就是三个 JSON 产物的顶层 payload
    （固定顺序），summary 与 checklist 是两个 Markdown 产物正文；
    全部只表达 candidate 与证据，不表达已确认的 Grain。
    """

    signals: dict[str, Any] = field(default_factory=dict)
    candidates: dict[str, Any] = field(default_factory=dict)
    grain_tables: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    checklist: str = ""
    analysis_dir: Path = field(default_factory=Path)

    @property
    def signal_count(self) -> int:
        return int(self.signals.get("count") or 0)

    @property
    def candidate_count(self) -> int:
        return int(self.candidates.get("count") or 0)

    @property
    def grain_table_count(self) -> int:
        return int(self.grain_tables.get("count") or 0)

    @property
    def signal_type_counts(self) -> dict[str, int]:
        counts = {signal_type: 0 for signal_type in GRAIN_SIGNAL_TYPE_ORDER}

        for item in self.signals.get("signals") or []:
            signal_type = str(item.get("signal_type") or "")
            counts[signal_type] = counts.get(signal_type, 0) + 1

        return counts

    @property
    def pattern_counts(self) -> dict[str, int]:
        return dict(self.candidates.get("pattern_counts") or {})

    @property
    def strength_counts(self) -> dict[str, int]:
        return dict(self.candidates.get("strength_counts") or {})

    @property
    def status_counts(self) -> dict[str, int]:
        return dict(self.candidates.get("status_counts") or {})

    @property
    def process_count(self) -> int:
        """产生 grain candidate 的 process candidate 数量（去重）。"""

        return int(self.candidates.get("process_count") or 0)

    @property
    def table_count(self) -> int:
        """出现 grain candidate 的表数量（去重）。"""

        return int(self.candidates.get("table_count") or 0)

    @property
    def object_count(self) -> int:
        """grain candidate 候选键命中的 Object 数量（去重）。"""

        objects: dict[str, None] = {}

        for item in self.candidates.get("candidates") or []:
            for name in item.get("matched_objects") or []:
                objects.setdefault(str(name), None)

        return len(objects)

    @property
    def unresolved_counts(self) -> dict[str, int]:
        counts = {reason: 0 for reason in GRAIN_UNRESOLVED_ORDER}

        for item in self.candidates.get("candidates") or []:
            for reason in item.get("unresolved_reasons") or []:
                counts[str(reason)] = counts.get(str(reason), 0) + 1

        return counts


# ============================================================
# 排序工具
# ============================================================


def confidence_sort_key(confidence: str) -> tuple[int, str]:
    """confidence 确定性排序键：high 在前，UNKNOWN 在后，未知值排最后。"""

    try:
        return (BUSINESS_CONFIDENCE_ORDER.index(confidence), confidence)

    except ValueError:
        return (len(BUSINESS_CONFIDENCE_ORDER), confidence)


def evidence_type_sort_key(evidence_type: str) -> tuple[int, str]:
    """evidence type 确定性排序键：直接证据在前，派生证据在后。"""

    try:
        return (BUSINESS_EVIDENCE_ORDER.index(evidence_type), evidence_type)

    except ValueError:
        return (len(BUSINESS_EVIDENCE_ORDER), evidence_type)


def numeric_id_sort_key(value: int | str | None) -> tuple[int, int, str]:
    """把可能为字符串的 ID 转成确定性排序键。

    数字 ID 按数值排序，非数字 ID 排在数字之后并按字典序排列。
    """

    text = "" if value is None else str(value)

    if text.isdigit():
        return (0, int(text), "")

    return (1, 0, text)

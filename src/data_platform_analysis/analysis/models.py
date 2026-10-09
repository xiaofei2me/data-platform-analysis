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

    这是历史兼容入口，只区分「有 / 没有 NodeId」。
    需要区分缺失与格式无效时使用 node_id_state()。
    """

    if node_id is None:
        return False

    if isinstance(node_id, str):
        return bool(node_id.strip())

    return True


NODE_ID_STATE_VALID = "valid"
"""NodeId 为正整数，节点身份成立。"""

NODE_ID_STATE_MISSING = "missing"
"""NodeId 为 None 或空白，属于分析范围限制，不是技术异常。"""

NODE_ID_STATE_INVALID = "invalid"
"""NodeId 非空白但格式不成立（不是正整数），节点身份无法确认。"""


def node_id_state(node_id: int | str | None) -> str:
    """NodeId 状态：valid（正整数）/ missing（空）/ invalid（格式不成立）。

    缺失与格式无效都是明确的分类原因（Analysis Scope Rules），
    不是技术异常，也不代表对象是测试任务或删除候选。
    """

    if node_id is None:
        return NODE_ID_STATE_MISSING

    if isinstance(node_id, str):
        text = node_id.strip()

        if not text:
            return NODE_ID_STATE_MISSING

        if not text.isdigit():
            return NODE_ID_STATE_INVALID

        return NODE_ID_STATE_VALID if int(text) > 0 else NODE_ID_STATE_INVALID

    if node_id <= 0:
        return NODE_ID_STATE_INVALID

    return NODE_ID_STATE_VALID


def is_analysis_eligible(file: FileInventory) -> bool:
    """判断 File 是否具备节点级分析的资产身份（兼容入口）。

    语义：NodeId 状态为 valid，即该 File 是已提交的 DataWorks 节点。
    这是「身份维度」的整体分析资格，不是 SQL 分析资格——
    SQL 分析资格由 Inventory 的 Analysis Scope Rules 统一判定
    （见 analysis/inventory/scope.py 的 FileScopeDecision.sql_eligible）。

    NodeId 缺失或格式无效的 File 仍然保留在 Snapshot Inventory 中，
    这是 Analysis Scope Rules 的分类结果，不是 Analysis Error。
    """

    return node_id_state(file.node_id) == NODE_ID_STATE_VALID


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
    """单张表的 M3 业务理解结果（analysis/understanding/business/tables.json）。

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
            item.confidence == BUSINESS_CONFIDENCE_HIGH for item in self.domain_candidates
        ) or any(
            item.confidence == BUSINESS_CONFIDENCE_HIGH for item in self.business_object_candidates
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
    候选全量明细仍以 analysis/understanding/business/tables.json 为准。
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
            1 for item in self.relationships.get("relationships") or [] if item.get("core_related")
        )

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
# M3.5 Fact / Dimension Candidate Analysis
# ============================================================

MODEL_CANDIDATE_NOTE = "fact / dimension candidate 不是 confirmed 模型"
"""M3.5 产物的统一口径：只产出候选与证据，不产出目标模型结论。"""

MODEL_STATUS_CANDIDATE = "candidate"
"""机器默认状态：只表达 fact / dimension candidate。"""

MODEL_STATUS_CONFIRMED = "confirmed"
"""model-review-checklist.md 中人工显式确认的候选。"""

MODEL_STATUS_REJECTED = "rejected"
"""model-review-checklist.md 中人工显式否决的候选。"""

MODEL_STATUS_NEEDS_DISCUSSION = "needs_discussion"
"""model-review-checklist.md 中人工标记为待讨论的候选。"""

MODEL_STATUS_ORDER: tuple[str, ...] = (
    MODEL_STATUS_CANDIDATE,
    MODEL_STATUS_CONFIRMED,
    MODEL_STATUS_REJECTED,
    MODEL_STATUS_NEEDS_DISCUSSION,
)
"""候选状态的固定展示与排序顺序；默认永远排在最前。"""

MODEL_STATUS_SET: frozenset[str] = frozenset(MODEL_STATUS_ORDER)
"""产物里被认可的 status 取值。"""

MODEL_HUMAN_STATUS_PENDING = "pending"
"""清单默认值：尚未人工回填。"""

MODEL_HUMAN_STATUS_CONFIRMED = "confirmed"
"""清单回填：人工确认该候选。"""

MODEL_HUMAN_STATUS_REJECTED = "rejected"
"""清单回填：人工否决该候选。"""

MODEL_HUMAN_STATUS_NEEDS_REVIEW = "needs_review"
"""清单回填：人工标记为待讨论（needs_discussion 同义）。"""

MODEL_HUMAN_STATUS_ORDER: tuple[str, ...] = (
    MODEL_HUMAN_STATUS_PENDING,
    MODEL_HUMAN_STATUS_CONFIRMED,
    MODEL_HUMAN_STATUS_REJECTED,
    MODEL_HUMAN_STATUS_NEEDS_REVIEW,
)
"""human_status 的固定展示与排序顺序。"""

MODEL_HUMAN_STATUS_SET: frozenset[str] = frozenset(MODEL_HUMAN_STATUS_ORDER) | {
    MODEL_STATUS_NEEDS_DISCUSSION,
}
"""human_status 被认可的取值（其余一律视为未回填）。"""

MODEL_STATUS_BY_HUMAN_STATUS: dict[str, str] = {
    MODEL_HUMAN_STATUS_PENDING: MODEL_STATUS_CANDIDATE,
    MODEL_HUMAN_STATUS_CONFIRMED: MODEL_STATUS_CONFIRMED,
    MODEL_HUMAN_STATUS_REJECTED: MODEL_STATUS_REJECTED,
    MODEL_HUMAN_STATUS_NEEDS_REVIEW: MODEL_STATUS_NEEDS_DISCUSSION,
    MODEL_STATUS_NEEDS_DISCUSSION: MODEL_STATUS_NEEDS_DISCUSSION,
}
"""human_status → status 的确定性映射；机器阶段永远不写 confirmed。"""


def normalize_human_status(value: str) -> str | None:
    """把 human_status 单元格归一化成受支持的取值，其余返回 None。"""

    text = (value or "").strip().casefold().replace(" ", "_").replace("-", "_")

    return text if text in MODEL_HUMAN_STATUS_SET else None


MODEL_ROLE_FACT = "fact_candidate"
"""fact 候选唯一允许的建模角色。"""

MODEL_ROLE_DIMENSION = "dimension_candidate"
"""dimension 候选的基础建模角色。"""

MODEL_ROLE_FACT_RELATED_OBJECT = "fact_related_object"
"""同一 Object 也出现在 fact candidate 里时的补充角色（表示歧义）。"""

MODEL_ROLE_ORDER: tuple[str, ...] = (
    MODEL_ROLE_FACT,
    MODEL_ROLE_DIMENSION,
    MODEL_ROLE_FACT_RELATED_OBJECT,
)
"""建模角色的固定展示与排序顺序。"""

MODEL_ROLE_SET: frozenset[str] = frozenset(MODEL_ROLE_ORDER)

MODEL_ROLE_STATUS_CANDIDATE = "candidate"
"""只有单一建模角色，角色未出现歧义。"""

MODEL_ROLE_STATUS_AMBIGUOUS = "ambiguous"
"""同一候选同时命中多个建模角色，必须人工裁决。"""

MODEL_ROLE_STATUS_ORDER: tuple[str, ...] = (
    MODEL_ROLE_STATUS_CANDIDATE,
    MODEL_ROLE_STATUS_AMBIGUOUS,
)
MODEL_ROLE_STATUS_SET: frozenset[str] = frozenset(MODEL_ROLE_STATUS_ORDER)

FACT_EVIDENCE_PROCESS = "process"
FACT_EVIDENCE_GRAIN = "grain"
FACT_EVIDENCE_TABLE = "table"
FACT_EVIDENCE_COLUMN = "column"
FACT_EVIDENCE_SQL = "sql"
FACT_EVIDENCE_LINEAGE = "lineage"
FACT_EVIDENCE_OBJECT = "object"

FACT_EVIDENCE_ORDER: tuple[str, ...] = (
    FACT_EVIDENCE_PROCESS,
    FACT_EVIDENCE_GRAIN,
    FACT_EVIDENCE_TABLE,
    FACT_EVIDENCE_COLUMN,
    FACT_EVIDENCE_SQL,
    FACT_EVIDENCE_LINEAGE,
    FACT_EVIDENCE_OBJECT,
)
"""fact candidate 证据词汇（固定顺序）；strength 按这里的 distinct source 计数。"""

FACT_EVIDENCE_SET: frozenset[str] = frozenset(FACT_EVIDENCE_ORDER)

DIMENSION_EVIDENCE_OBJECT = "object"
DIMENSION_EVIDENCE_COLUMN = "column"
DIMENSION_EVIDENCE_PROCESS = "process"
DIMENSION_EVIDENCE_FACT_REFERENCE = "fact_reference"
DIMENSION_EVIDENCE_SQL = "sql"
DIMENSION_EVIDENCE_LINEAGE = "lineage"

DIMENSION_EVIDENCE_ORDER: tuple[str, ...] = (
    DIMENSION_EVIDENCE_OBJECT,
    DIMENSION_EVIDENCE_COLUMN,
    DIMENSION_EVIDENCE_PROCESS,
    DIMENSION_EVIDENCE_FACT_REFERENCE,
    DIMENSION_EVIDENCE_SQL,
    DIMENSION_EVIDENCE_LINEAGE,
)
"""dimension candidate 证据词汇（固定顺序）。"""

DIMENSION_EVIDENCE_SET: frozenset[str] = frozenset(DIMENSION_EVIDENCE_ORDER)

MODEL_REL_EVIDENCE_PROCESS_OBJECT = "process_object"
MODEL_REL_EVIDENCE_OBJECT_RELATIONSHIP = "object_relationship"
MODEL_REL_EVIDENCE_TABLE_REFERENCE = "table_reference"
MODEL_REL_EVIDENCE_SQL_REFERENCE = "sql_reference"
MODEL_REL_EVIDENCE_LINEAGE = "lineage"

MODEL_REL_EVIDENCE_ORDER: tuple[str, ...] = (
    MODEL_REL_EVIDENCE_PROCESS_OBJECT,
    MODEL_REL_EVIDENCE_OBJECT_RELATIONSHIP,
    MODEL_REL_EVIDENCE_TABLE_REFERENCE,
    MODEL_REL_EVIDENCE_SQL_REFERENCE,
    MODEL_REL_EVIDENCE_LINEAGE,
)
"""fact ↔ dimension 关系的证据词汇（固定顺序）；至少一类证据才产出一行。"""

MODEL_REL_EVIDENCE_SET: frozenset[str] = frozenset(MODEL_REL_EVIDENCE_ORDER)

MODEL_FACT_UNRESOLVED_PROCESS = "insufficient_process_evidence"
MODEL_FACT_UNRESOLVED_GRAIN = "insufficient_grain_evidence"
MODEL_FACT_UNRESOLVED_AMBIGUOUS_GRAIN = "ambiguous_grain"
MODEL_FACT_UNRESOLVED_MEASURE = "missing_measure_evidence"
MODEL_FACT_UNRESOLVED_SQL = "missing_sql_evidence"
MODEL_FACT_UNRESOLVED_LINEAGE = "missing_lineage_evidence"
MODEL_FACT_UNRESOLVED_OBJECT = "missing_object_evidence"

MODEL_FACT_UNRESOLVED_ORDER: tuple[str, ...] = (
    MODEL_FACT_UNRESOLVED_PROCESS,
    MODEL_FACT_UNRESOLVED_GRAIN,
    MODEL_FACT_UNRESOLVED_AMBIGUOUS_GRAIN,
    MODEL_FACT_UNRESOLVED_MEASURE,
    MODEL_FACT_UNRESOLVED_SQL,
    MODEL_FACT_UNRESOLVED_LINEAGE,
    MODEL_FACT_UNRESOLVED_OBJECT,
)
"""fact candidate 未决原因的固定顺序（未决 ≠ 失败，必须人工回答）。"""

MODEL_FACT_UNRESOLVED_SET: frozenset[str] = frozenset(MODEL_FACT_UNRESOLVED_ORDER)

MODEL_DIMENSION_UNRESOLVED_OBJECT = "insufficient_object_evidence"
MODEL_DIMENSION_UNRESOLVED_ATTRIBUTE = "missing_attribute_evidence"
MODEL_DIMENSION_UNRESOLVED_PROCESS = "missing_process_reference"
MODEL_DIMENSION_UNRESOLVED_FACT = "missing_fact_reference"
MODEL_DIMENSION_UNRESOLVED_SQL = "missing_sql_evidence"
MODEL_DIMENSION_UNRESOLVED_LINEAGE = "missing_lineage_evidence"
MODEL_DIMENSION_UNRESOLVED_AMBIGUOUS = "fact_and_dimension_ambiguous"

MODEL_DIMENSION_UNRESOLVED_ORDER: tuple[str, ...] = (
    MODEL_DIMENSION_UNRESOLVED_OBJECT,
    MODEL_DIMENSION_UNRESOLVED_ATTRIBUTE,
    MODEL_DIMENSION_UNRESOLVED_PROCESS,
    MODEL_DIMENSION_UNRESOLVED_FACT,
    MODEL_DIMENSION_UNRESOLVED_SQL,
    MODEL_DIMENSION_UNRESOLVED_LINEAGE,
    MODEL_DIMENSION_UNRESOLVED_AMBIGUOUS,
)
"""dimension candidate 未决原因的固定顺序。"""

MODEL_DIMENSION_UNRESOLVED_SET: frozenset[str] = frozenset(MODEL_DIMENSION_UNRESOLVED_ORDER)

MODEL_REL_UNRESOLVED_INSUFFICIENT = "insufficient_evidence"
MODEL_REL_UNRESOLVED_OBJECT_LINK = "missing_object_link"
MODEL_REL_UNRESOLVED_SQL = "sql_evidence_missing"
MODEL_REL_UNRESOLVED_LINEAGE = "lineage_evidence_missing"

MODEL_REL_UNRESOLVED_ORDER: tuple[str, ...] = (
    MODEL_REL_UNRESOLVED_INSUFFICIENT,
    MODEL_REL_UNRESOLVED_OBJECT_LINK,
    MODEL_REL_UNRESOLVED_SQL,
    MODEL_REL_UNRESOLVED_LINEAGE,
)
"""fact ↔ dimension 关系未决原因的固定顺序。"""

MODEL_REL_UNRESOLVED_SET: frozenset[str] = frozenset(MODEL_REL_UNRESOLVED_ORDER)

MODEL_CANDIDATE_TYPE_FACT = "fact"
MODEL_CANDIDATE_TYPE_DIMENSION = "dimension"
MODEL_CANDIDATE_TYPE_RELATIONSHIP = "fact_dimension_relationship"

MODEL_CANDIDATE_TYPE_ORDER: tuple[str, ...] = (
    MODEL_CANDIDATE_TYPE_FACT,
    MODEL_CANDIDATE_TYPE_DIMENSION,
    MODEL_CANDIDATE_TYPE_RELATIONSHIP,
)
"""model-evidence-matrix.json 与 checklist 的候选类型顺序。"""

MODEL_PRIORITY_FACT_EVIDENCE = "P1"
MODEL_PRIORITY_FACT_AMBIGUOUS = "P2"
MODEL_PRIORITY_DIMENSION = "P3"
MODEL_PRIORITY_RELATIONSHIP = "P4"

MODEL_PRIORITY_ORDER: tuple[str, ...] = (
    MODEL_PRIORITY_FACT_EVIDENCE,
    MODEL_PRIORITY_FACT_AMBIGUOUS,
    MODEL_PRIORITY_DIMENSION,
    MODEL_PRIORITY_RELATIONSHIP,
)
"""model-review-checklist.md 的复核优先级顺序（最紧急在前）。"""

MODEL_PRIORITY_TITLE: dict[str, str] = {
    MODEL_PRIORITY_FACT_EVIDENCE: "Fact Candidate 证据不足",
    MODEL_PRIORITY_FACT_AMBIGUOUS: "Fact Candidate 粒度 / 血缘待裁决",
    MODEL_PRIORITY_DIMENSION: "Dimension Candidate 证据 / 角色待裁决",
    MODEL_PRIORITY_RELATIONSHIP: "Fact-Dimension Relationship 证据不足",
}
"""每个优先级分区的标题。"""

MODEL_PRIORITY_HINT: dict[str, str] = {
    MODEL_PRIORITY_FACT_EVIDENCE: (
        "证据强度为 weak，或缺 process / grain / 度量 / Object 证据；"
        "先补证据再确认，不要直接改 status。"
    ),
    MODEL_PRIORITY_FACT_AMBIGUOUS: (
        "grain 形态未定（unknown / multiple_possible_keys）或缺 SQL / 血缘证据；"
        "需要人工给出粒度裁决或补充上游证据。"
    ),
    MODEL_PRIORITY_DIMENSION: (
        "证据强度为 weak，或属性 / 过程 / 事实引用 / 角色存在歧义；"
        "Object 同时进入 fact 关系时必须人工裁决角色。"
    ),
    MODEL_PRIORITY_RELATIONSHIP: (
        "关系只有单一证据源或缺 Object 直接链接；"
        "relationship ≠ 业务关系，确认前必须核对 source_id。"
    ),
}
"""每个优先级分区的填写提示。"""

MODEL_CHECKLIST_HEADERS: tuple[str, ...] = (
    "candidate_key",
    "candidate_type",
    "priority",
    "current_status",
    "evidence_strength",
    "unresolved_reasons",
    "human_status",
    "human_name",
    "note",
)
"""model-review-checklist.md 的列（固定顺序）。"""

MODEL_CHECKLIST_REQUIRED_COLUMNS: tuple[str, ...] = (
    "candidate_key",
    "human_status",
    "human_name",
    "note",
)
"""model-review-checklist.md 的回填列：缺一即报错（其余列由机器生成）。"""

MODEL_REPORT_ROW_LIMIT = 50
"""model-summary.md 中每张明细表的固定行数上限。"""

MODEL_CHECKLIST_ROW_LIMIT = 50
"""model-review-checklist.md 中每个优先级分区的固定行数上限。"""

MODEL_ATTRIBUTE_LIMIT = 50
"""dimension candidate 里 attributes 的固定条数上限（attribute_count 仍是全量）。"""

MODEL_EXAMPLE_LIMIT = 5
"""evidence reason / 报告里列出的示例条目上限。"""


@dataclass
class ModelChecklistRow:
    """model-review-checklist.md 的一行（priority 已在 M3.5 侧算好）。"""

    candidate_key: str
    candidate_type: str
    priority: str
    current_status: str
    evidence_strength: str
    unresolved_reasons: list[str] = field(default_factory=list)


@dataclass
class BusinessModelResult:
    """一次 M3.5 运行的结果。

    六个 JSON 产物的顶层 payload（固定顺序）+ summary / checklist 两个
    Markdown 正文；全部只表达 fact / dimension candidate 与证据。
    """

    fact_candidates: dict[str, Any] = field(default_factory=dict)
    dimension_candidates: dict[str, Any] = field(default_factory=dict)
    relationships: dict[str, Any] = field(default_factory=dict)
    fact_tables: dict[str, Any] = field(default_factory=dict)
    dimension_tables: dict[str, Any] = field(default_factory=dict)
    evidence_matrix: dict[str, Any] = field(default_factory=dict)
    checklist_rows: list[ModelChecklistRow] = field(default_factory=list)
    summary: str = ""
    checklist: str = ""
    analysis_dir: Path = field(default_factory=Path)

    @property
    def fact_count(self) -> int:
        return int(self.fact_candidates.get("count") or 0)

    @property
    def dimension_count(self) -> int:
        return int(self.dimension_candidates.get("count") or 0)

    @property
    def relationship_count(self) -> int:
        return int(self.relationships.get("count") or 0)

    @property
    def fact_table_count(self) -> int:
        return int(self.fact_tables.get("count") or 0)

    @property
    def dimension_table_count(self) -> int:
        return int(self.dimension_tables.get("count") or 0)

    @property
    def status_counts(self) -> dict[str, int]:
        return dict(self.fact_candidates.get("status_counts") or {})

    @property
    def priority_counts(self) -> dict[str, int]:
        counts = {priority: 0 for priority in MODEL_PRIORITY_ORDER}

        for row in self.checklist_rows:
            counts[row.priority] = counts.get(row.priority, 0) + 1

        return counts


# ============================================================
# M3.6 Current-State Model Review
# ============================================================

CURRENT_STATE_NOTE = (
    "current-state model 只描述当前平台已经存在的模型形态与评审发现，不是 Target DWD Design"
)
"""M3.6 产物的统一口径：评审既有模型，不设计目标模型。"""

FINDING_CANDIDATE_NOTE = "review finding 是候选问题，finding ≠ confirmed 问题"
"""finding 与候选一样：机器只给证据与判断，确认必须人工回填。"""

REVIEW_PRIORITY_P0 = "P0"
REVIEW_PRIORITY_P1 = "P1"
REVIEW_PRIORITY_P2 = "P2"
REVIEW_PRIORITY_P3 = "P3"

REVIEW_PRIORITY_ORDER: tuple[str, ...] = (
    REVIEW_PRIORITY_P0,
    REVIEW_PRIORITY_P1,
    REVIEW_PRIORITY_P2,
    REVIEW_PRIORITY_P3,
)
"""findings 的优先级顺序（最紧急在前）。"""

REVIEW_PRIORITY_SET: frozenset[str] = frozenset(REVIEW_PRIORITY_ORDER)

REVIEW_PRIORITY_TITLE: dict[str, str] = {
    REVIEW_PRIORITY_P0: "直接影响后续模型设计，必须优先确认",
    REVIEW_PRIORITY_P1: "高价值模型问题",
    REVIEW_PRIORITY_P2: "一般模型问题",
    REVIEW_PRIORITY_P3: "信息性发现",
}
"""每个优先级分区的标题。"""

REVIEW_PRIORITY_HINT: dict[str, str] = {
    REVIEW_PRIORITY_P0: (
        "粒度冲突、角色歧义与 Fact Gate 排除项会直接改变 M4 的事实模型；先确认这些，再看其它问题。"
    ),
    REVIEW_PRIORITY_P1: (
        "疑似重复 / 重叠模型、缺度量的事实与关系证据不足；确认前不要合并、拆分或删除任何表。"
    ),
    REVIEW_PRIORITY_P2: (
        "宽表、结果表、聚合事实与 dimension 派生方式；属于需要说明但不一定改模型的问题。"
    ),
    REVIEW_PRIORITY_P3: "信息性记录，不构成问题判断。",
}
"""每个优先级分区的填写提示。"""

REVIEW_SEVERITY_BY_PRIORITY: dict[str, str] = {
    REVIEW_PRIORITY_P0: "critical",
    REVIEW_PRIORITY_P1: "high",
    REVIEW_PRIORITY_P2: "medium",
    REVIEW_PRIORITY_P3: "info",
}
"""priority → severity（只作展示口径，不参与判定）。"""

FINDING_TYPE_FACT_GATE_NO_MEASURE = "fact_gate_no_measure"
FINDING_TYPE_FACT_GATE_PATTERN = "fact_gate_pattern"
FINDING_TYPE_EVIDENCE_STRENGTH = "evidence_strength_semantics"
FINDING_TYPE_FACT_WITHOUT_MEASURE = "fact_without_measure"
FINDING_TYPE_AGGREGATE_FACT = "aggregate_fact"
FINDING_TYPE_GRAIN_CONFLICT = "grain_conflict"
FINDING_TYPE_MIXED_GRAIN = "mixed_grain"
FINDING_TYPE_SNAPSHOT_PERIODIC = "snapshot_periodic_ambiguous"
FINDING_TYPE_PROCESS_MULTIPLE_GRAINS = "process_multiple_grains"
FINDING_TYPE_DIMENSION_OBJECT_DERIVED = "dimension_object_derived"
FINDING_TYPE_ROLE_AMBIGUOUS = "role_ambiguous"
FINDING_TYPE_RELATIONSHIP_TECHNICAL = "relationship_technical_only"
FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE = "relationship_object_co_occurrence"
FINDING_TYPE_DUPLICATE_FACT = "duplicate_fact"
FINDING_TYPE_OVERLAPPING_FACT = "overlapping_fact"
FINDING_TYPE_MULTI_PROCESS_TABLE = "multi_process_table"
FINDING_TYPE_WIDE_ANALYTICAL_TABLE = "wide_analytical_table"
FINDING_TYPE_RESULT_TABLE = "result_table"

FINDING_TYPE_ORDER: tuple[str, ...] = (
    FINDING_TYPE_FACT_GATE_NO_MEASURE,
    FINDING_TYPE_FACT_GATE_PATTERN,
    FINDING_TYPE_EVIDENCE_STRENGTH,
    FINDING_TYPE_FACT_WITHOUT_MEASURE,
    FINDING_TYPE_AGGREGATE_FACT,
    FINDING_TYPE_GRAIN_CONFLICT,
    FINDING_TYPE_MIXED_GRAIN,
    FINDING_TYPE_SNAPSHOT_PERIODIC,
    FINDING_TYPE_PROCESS_MULTIPLE_GRAINS,
    FINDING_TYPE_DIMENSION_OBJECT_DERIVED,
    FINDING_TYPE_ROLE_AMBIGUOUS,
    FINDING_TYPE_RELATIONSHIP_TECHNICAL,
    FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE,
    FINDING_TYPE_DUPLICATE_FACT,
    FINDING_TYPE_OVERLAPPING_FACT,
    FINDING_TYPE_MULTI_PROCESS_TABLE,
    FINDING_TYPE_WIDE_ANALYTICAL_TABLE,
    FINDING_TYPE_RESULT_TABLE,
)
"""M3.6 finding 类型的固定顺序。"""

FINDING_TYPE_SET: frozenset[str] = frozenset(FINDING_TYPE_ORDER)

REVIEW_GROUP_FACT = "fact_review"
REVIEW_GROUP_DIMENSION = "dimension_review"
REVIEW_GROUP_GRAIN = "grain_review"
REVIEW_GROUP_RELATIONSHIP = "relationship_review"
REVIEW_GROUP_MODEL_ISSUE = "model_issue_review"

REVIEW_GROUP_ORDER: tuple[str, ...] = (
    REVIEW_GROUP_FACT,
    REVIEW_GROUP_DIMENSION,
    REVIEW_GROUP_GRAIN,
    REVIEW_GROUP_RELATIONSHIP,
    REVIEW_GROUP_MODEL_ISSUE,
)
"""current-state-review-checklist.md 的五个分区顺序。"""

REVIEW_GROUP_SET: frozenset[str] = frozenset(REVIEW_GROUP_ORDER)

REVIEW_GROUP_TITLE: dict[str, str] = {
    REVIEW_GROUP_FACT: "Fact Review",
    REVIEW_GROUP_DIMENSION: "Dimension Review",
    REVIEW_GROUP_GRAIN: "Grain Review",
    REVIEW_GROUP_RELATIONSHIP: "Relationship Review",
    REVIEW_GROUP_MODEL_ISSUE: "Model Issue Review",
}
"""每个清单分区的标题。"""

REVIEW_GROUP_HINT: dict[str, str] = {
    REVIEW_GROUP_FACT: (
        "回答：Fact Gate 是否误排除、strength 是否被误读、缺度量与聚合事实是否仍应算事实。"
    ),
    REVIEW_GROUP_DIMENSION: ("回答：dimension 是否只是 Object 的直接映射、同对象多角色由谁裁决。"),
    REVIEW_GROUP_GRAIN: ("回答：同表多组候选键 / 多种 grain 形态哪一个是业务事实。"),
    REVIEW_GROUP_RELATIONSHIP: ("回答：只有技术引用或只有共现证据的关系能否算业务关系。"),
    REVIEW_GROUP_MODEL_ISSUE: ("回答：疑似重复 / 重叠 / 宽表 / 结果表是否是真实模型问题。"),
}
"""每个清单分区的填写提示。"""

FINDING_TYPE_PRIORITY: dict[str, str] = {
    FINDING_TYPE_FACT_GATE_NO_MEASURE: REVIEW_PRIORITY_P0,
    FINDING_TYPE_FACT_GATE_PATTERN: REVIEW_PRIORITY_P0,
    FINDING_TYPE_GRAIN_CONFLICT: REVIEW_PRIORITY_P0,
    FINDING_TYPE_MIXED_GRAIN: REVIEW_PRIORITY_P0,
    FINDING_TYPE_ROLE_AMBIGUOUS: REVIEW_PRIORITY_P0,
    FINDING_TYPE_FACT_WITHOUT_MEASURE: REVIEW_PRIORITY_P1,
    FINDING_TYPE_EVIDENCE_STRENGTH: REVIEW_PRIORITY_P1,
    FINDING_TYPE_SNAPSHOT_PERIODIC: REVIEW_PRIORITY_P1,
    FINDING_TYPE_RELATIONSHIP_TECHNICAL: REVIEW_PRIORITY_P1,
    FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE: REVIEW_PRIORITY_P1,
    FINDING_TYPE_DUPLICATE_FACT: REVIEW_PRIORITY_P1,
    FINDING_TYPE_OVERLAPPING_FACT: REVIEW_PRIORITY_P1,
    FINDING_TYPE_MULTI_PROCESS_TABLE: REVIEW_PRIORITY_P1,
    FINDING_TYPE_DIMENSION_OBJECT_DERIVED: REVIEW_PRIORITY_P2,
    FINDING_TYPE_AGGREGATE_FACT: REVIEW_PRIORITY_P2,
    FINDING_TYPE_WIDE_ANALYTICAL_TABLE: REVIEW_PRIORITY_P2,
    FINDING_TYPE_RESULT_TABLE: REVIEW_PRIORITY_P2,
    FINDING_TYPE_PROCESS_MULTIPLE_GRAINS: REVIEW_PRIORITY_P3,
}
"""finding_type → priority（固定映射，不随数据变化）。"""

FINDING_TYPE_GROUP: dict[str, str] = {
    FINDING_TYPE_FACT_GATE_NO_MEASURE: REVIEW_GROUP_FACT,
    FINDING_TYPE_FACT_GATE_PATTERN: REVIEW_GROUP_FACT,
    FINDING_TYPE_EVIDENCE_STRENGTH: REVIEW_GROUP_FACT,
    FINDING_TYPE_FACT_WITHOUT_MEASURE: REVIEW_GROUP_FACT,
    FINDING_TYPE_AGGREGATE_FACT: REVIEW_GROUP_FACT,
    FINDING_TYPE_DIMENSION_OBJECT_DERIVED: REVIEW_GROUP_DIMENSION,
    FINDING_TYPE_ROLE_AMBIGUOUS: REVIEW_GROUP_DIMENSION,
    FINDING_TYPE_GRAIN_CONFLICT: REVIEW_GROUP_GRAIN,
    FINDING_TYPE_MIXED_GRAIN: REVIEW_GROUP_GRAIN,
    FINDING_TYPE_SNAPSHOT_PERIODIC: REVIEW_GROUP_GRAIN,
    FINDING_TYPE_PROCESS_MULTIPLE_GRAINS: REVIEW_GROUP_GRAIN,
    FINDING_TYPE_RELATIONSHIP_TECHNICAL: REVIEW_GROUP_RELATIONSHIP,
    FINDING_TYPE_RELATIONSHIP_CO_OCCURRENCE: REVIEW_GROUP_RELATIONSHIP,
    FINDING_TYPE_DUPLICATE_FACT: REVIEW_GROUP_MODEL_ISSUE,
    FINDING_TYPE_OVERLAPPING_FACT: REVIEW_GROUP_MODEL_ISSUE,
    FINDING_TYPE_MULTI_PROCESS_TABLE: REVIEW_GROUP_MODEL_ISSUE,
    FINDING_TYPE_WIDE_ANALYTICAL_TABLE: REVIEW_GROUP_MODEL_ISSUE,
    FINDING_TYPE_RESULT_TABLE: REVIEW_GROUP_MODEL_ISSUE,
}
"""finding_type → checklist 分区。"""

FINDING_SCOPE_STAGE = "stage"
FINDING_SCOPE_TABLE = "table"
FINDING_SCOPE_TABLE_PAIR = "table_pair"
FINDING_SCOPE_FACT = "fact"
FINDING_SCOPE_DIMENSION = "dimension"
FINDING_SCOPE_PROCESS = "process"
FINDING_SCOPE_FACT_GROUP = "fact_group"

FINDING_SCOPE_ORDER: tuple[str, ...] = (
    FINDING_SCOPE_STAGE,
    FINDING_SCOPE_TABLE,
    FINDING_SCOPE_TABLE_PAIR,
    FINDING_SCOPE_FACT,
    FINDING_SCOPE_DIMENSION,
    FINDING_SCOPE_PROCESS,
    FINDING_SCOPE_FACT_GROUP,
)
"""finding scope 的固定顺序。"""

FINDING_SCOPE_SET: frozenset[str] = frozenset(FINDING_SCOPE_ORDER)

CURRENT_MODEL_ROLE_FACT = "FACT"
CURRENT_MODEL_ROLE_DIMENSION = "DIMENSION"
CURRENT_MODEL_ROLE_AMBIGUOUS = "FACT_DIMENSION_AMBIGUOUS"
CURRENT_MODEL_ROLE_WIDE = "WIDE_ANALYTICAL"
CURRENT_MODEL_ROLE_RESULT = "RESULT_TABLE"
CURRENT_MODEL_ROLE_UNKNOWN = "UNKNOWN"

CURRENT_MODEL_ROLE_ORDER: tuple[str, ...] = (
    CURRENT_MODEL_ROLE_AMBIGUOUS,
    CURRENT_MODEL_ROLE_FACT,
    CURRENT_MODEL_ROLE_DIMENSION,
    CURRENT_MODEL_ROLE_WIDE,
    CURRENT_MODEL_ROLE_RESULT,
    CURRENT_MODEL_ROLE_UNKNOWN,
)
"""current_role 的固定顺序（同时是优先级：命中多个时取最靠前的）。"""

CURRENT_MODEL_ROLE_SET: frozenset[str] = frozenset(CURRENT_MODEL_ROLE_ORDER)

CURRENT_MODEL_SHAPE_TRANSACTION = "TRANSACTION"
CURRENT_MODEL_SHAPE_EVENT = "EVENT"
CURRENT_MODEL_SHAPE_PERIODIC = "PERIODIC"
CURRENT_MODEL_SHAPE_SNAPSHOT = "SNAPSHOT"
CURRENT_MODEL_SHAPE_AGGREGATE = "AGGREGATE"
CURRENT_MODEL_SHAPE_MIXED = "MIXED"
CURRENT_MODEL_SHAPE_UNKNOWN = "UNKNOWN"

CURRENT_MODEL_SHAPE_ORDER: tuple[str, ...] = (
    CURRENT_MODEL_SHAPE_TRANSACTION,
    CURRENT_MODEL_SHAPE_EVENT,
    CURRENT_MODEL_SHAPE_PERIODIC,
    CURRENT_MODEL_SHAPE_SNAPSHOT,
    CURRENT_MODEL_SHAPE_AGGREGATE,
    CURRENT_MODEL_SHAPE_MIXED,
    CURRENT_MODEL_SHAPE_UNKNOWN,
)
"""model_shape 的固定顺序（单一形态在前，混合与未知在后）。"""

CURRENT_MODEL_SHAPE_SET: frozenset[str] = frozenset(CURRENT_MODEL_SHAPE_ORDER)

GRAIN_PATTERN_TO_SHAPE: dict[str, str] = {
    GRAIN_PATTERN_TRANSACTION: CURRENT_MODEL_SHAPE_TRANSACTION,
    GRAIN_PATTERN_EVENT: CURRENT_MODEL_SHAPE_EVENT,
    GRAIN_PATTERN_PERIODIC: CURRENT_MODEL_SHAPE_PERIODIC,
    GRAIN_PATTERN_SNAPSHOT: CURRENT_MODEL_SHAPE_SNAPSHOT,
    GRAIN_PATTERN_AGGREGATION: CURRENT_MODEL_SHAPE_AGGREGATE,
    GRAIN_PATTERN_UNKNOWN: CURRENT_MODEL_SHAPE_UNKNOWN,
}
"""M3.4 grain_pattern → M3.6 model_shape（未登记形态按 UNKNOWN）。"""

REVIEW_EVIDENCE_TABLE = "table"
REVIEW_EVIDENCE_COLUMN = "column"
REVIEW_EVIDENCE_PROCESS = "process"
REVIEW_EVIDENCE_GRAIN = "grain"
REVIEW_EVIDENCE_OBJECT = "object"
REVIEW_EVIDENCE_SQL = "sql"
REVIEW_EVIDENCE_LINEAGE = "lineage"
REVIEW_EVIDENCE_PROFILING = "profiling"
REVIEW_EVIDENCE_LAYER = "layer"
REVIEW_EVIDENCE_FACT = "fact_candidate"
REVIEW_EVIDENCE_DIMENSION = "dimension_candidate"
REVIEW_EVIDENCE_RELATIONSHIP = "relationship"

REVIEW_EVIDENCE_ORDER: tuple[str, ...] = (
    REVIEW_EVIDENCE_TABLE,
    REVIEW_EVIDENCE_COLUMN,
    REVIEW_EVIDENCE_PROCESS,
    REVIEW_EVIDENCE_GRAIN,
    REVIEW_EVIDENCE_OBJECT,
    REVIEW_EVIDENCE_SQL,
    REVIEW_EVIDENCE_LINEAGE,
    REVIEW_EVIDENCE_PROFILING,
    REVIEW_EVIDENCE_LAYER,
    REVIEW_EVIDENCE_FACT,
    REVIEW_EVIDENCE_DIMENSION,
    REVIEW_EVIDENCE_RELATIONSHIP,
)
"""finding 证据的词汇（固定顺序）；finding 必须至少一条证据。"""

REVIEW_EVIDENCE_SET: frozenset[str] = frozenset(REVIEW_EVIDENCE_ORDER)

REVIEW_CHECKLIST_HEADERS: tuple[str, ...] = (
    "finding_id",
    "finding_type",
    "priority",
    "scope_key",
    "evidence",
    "system_interpretation",
    "human_question",
    "human_status",
    "human_name",
    "note",
)
"""current-state-review-checklist.md 的列（固定顺序）。"""

REVIEW_CHECKLIST_REQUIRED_COLUMNS: tuple[str, ...] = (
    "finding_id",
    "human_status",
    "human_name",
    "note",
)
"""current-state-review-checklist.md 的回填列：缺一即报错。"""

REVIEW_CHECKLIST_ROW_LIMIT = 50
"""current-state-review-checklist.md 中每个分区的固定行数上限。"""

REVIEW_REPORT_ROW_LIMIT = 50
"""current-state-model-summary.md 中每张明细表的固定行数上限。"""

REVIEW_EXAMPLE_LIMIT = 5
"""finding 证据 / 描述里列出的示例条目上限。"""

FINDING_ID_FORMAT = "model_finding_{index:04d}"
"""finding_id 的固定格式（按 canonical signature 排序后编号）。"""


# ============================================================
# M3.6 v2 Current-State Problem Assessment
# ============================================================

PROBLEM_CANDIDATE_NOTE = (
    "problem candidate 是 Finding 聚合后的候选问题：Finding Count ≠ Problem Count "
    "≠ Confirmed Problem Count；机器不自动把任何 problem 变成 confirmed"
)
"""Problem 的统一口径：聚合、证据、影响与根因，不替代人工确认。"""

PROBLEM_ID_FORMAT = "problem_{index:04d}"
"""problem_id 的固定格式（按 canonical signature 排序后编号）。"""

PROBLEM_OUTPUT_FILES: tuple[str, ...] = (
    "current-state-problems.json",
    "current-state-problem-evidence.json",
    "current-state-problem-summary.md",
    "current-state-problem-review-checklist.md",
)
"""M3.6 v2 新增的四个产物（固定顺序）；不改变已有五个 M3.6 产物。"""

PROBLEM_CARRYOVER_FILE = "review/current-state-problem-review-checklist.md"
"""问题清单的人工回填文件（可选输入，重跑带回）。"""

PROBLEM_TYPE_GRAIN = "GRAIN_PROBLEM"
PROBLEM_TYPE_OVERLAP = "MODEL_OVERLAP"
PROBLEM_TYPE_DUPLICATION = "MODEL_DUPLICATION"
PROBLEM_TYPE_MIXED_RESPONSIBILITY = "MIXED_RESPONSIBILITY"
PROBLEM_TYPE_ROLE_AMBIGUITY = "MODEL_ROLE_AMBIGUITY"
PROBLEM_TYPE_PROCESS_ALIGNMENT = "PROCESS_MODEL_ALIGNMENT"
PROBLEM_TYPE_AGGREGATION = "AGGREGATION_MODEL_PROBLEM"
PROBLEM_TYPE_FACT_IDENTIFICATION = "FACT_IDENTIFICATION_PROBLEM"
PROBLEM_TYPE_DIMENSION_IDENTIFICATION = "DIMENSION_IDENTIFICATION_PROBLEM"
PROBLEM_TYPE_SELECTION_AMBIGUITY = "MODEL_SELECTION_AMBIGUITY"
PROBLEM_TYPE_SEMANTIC_AMBIGUITY = "SEMANTIC_AMBIGUITY"
PROBLEM_TYPE_COVERAGE_GAP = "MODEL_COVERAGE_GAP"
PROBLEM_TYPE_UNKNOWN_MODEL = "UNKNOWN_MODEL"

PROBLEM_TYPE_ORDER: tuple[str, ...] = (
    PROBLEM_TYPE_GRAIN,
    PROBLEM_TYPE_OVERLAP,
    PROBLEM_TYPE_DUPLICATION,
    PROBLEM_TYPE_MIXED_RESPONSIBILITY,
    PROBLEM_TYPE_ROLE_AMBIGUITY,
    PROBLEM_TYPE_PROCESS_ALIGNMENT,
    PROBLEM_TYPE_AGGREGATION,
    PROBLEM_TYPE_FACT_IDENTIFICATION,
    PROBLEM_TYPE_DIMENSION_IDENTIFICATION,
    PROBLEM_TYPE_SELECTION_AMBIGUITY,
    PROBLEM_TYPE_SEMANTIC_AMBIGUITY,
    PROBLEM_TYPE_COVERAGE_GAP,
    PROBLEM_TYPE_UNKNOWN_MODEL,
)
"""problem taxonomy 的固定顺序（第一版 13 类；没有证据支撑的类型不产生问题）。"""

PROBLEM_TYPE_SET: frozenset[str] = frozenset(PROBLEM_TYPE_ORDER)

PROBLEM_TYPE_TITLE: dict[str, str] = {
    PROBLEM_TYPE_GRAIN: "粒度问题",
    PROBLEM_TYPE_OVERLAP: "模型重叠",
    PROBLEM_TYPE_DUPLICATION: "模型重复",
    PROBLEM_TYPE_MIXED_RESPONSIBILITY: "职责混杂",
    PROBLEM_TYPE_ROLE_AMBIGUITY: "角色歧义",
    PROBLEM_TYPE_PROCESS_ALIGNMENT: "过程与模型对齐",
    PROBLEM_TYPE_AGGREGATION: "聚合模型问题",
    PROBLEM_TYPE_FACT_IDENTIFICATION: "事实识别问题",
    PROBLEM_TYPE_DIMENSION_IDENTIFICATION: "维度识别问题",
    PROBLEM_TYPE_SELECTION_AMBIGUITY: "模型选择歧义",
    PROBLEM_TYPE_SEMANTIC_AMBIGUITY: "语义歧义",
    PROBLEM_TYPE_COVERAGE_GAP: "过程覆盖缺口",
    PROBLEM_TYPE_UNKNOWN_MODEL: "未定模型",
}
"""problem_type → 中文标题（报告与清单分区用）。"""

PROBLEM_SCOPE_TABLE = "table"
PROBLEM_SCOPE_TABLE_SET = "table_set"
PROBLEM_SCOPE_PROCESS = "process"
PROBLEM_SCOPE_DIMENSION = "dimension"
PROBLEM_SCOPE_STAGE = "stage"

PROBLEM_SCOPE_ORDER: tuple[str, ...] = (
    PROBLEM_SCOPE_STAGE,
    PROBLEM_SCOPE_PROCESS,
    PROBLEM_SCOPE_DIMENSION,
    PROBLEM_SCOPE_TABLE_SET,
    PROBLEM_SCOPE_TABLE,
)
"""problem scope 的固定顺序。"""

PROBLEM_SCOPE_SET: frozenset[str] = frozenset(PROBLEM_SCOPE_ORDER)

PROBLEM_STATUS_CANDIDATE = "candidate"
PROBLEM_STATUS_REVIEW_REQUIRED = "review_required"
PROBLEM_STATUS_CONFIRMED = "confirmed"
PROBLEM_STATUS_REJECTED = "rejected"

PROBLEM_STATUS_ORDER: tuple[str, ...] = (
    PROBLEM_STATUS_CANDIDATE,
    PROBLEM_STATUS_REVIEW_REQUIRED,
    PROBLEM_STATUS_CONFIRMED,
    PROBLEM_STATUS_REJECTED,
)
"""problem status 的固定顺序；机器阶段只会写前两个。"""

PROBLEM_STATUS_SET: frozenset[str] = frozenset(PROBLEM_STATUS_ORDER)

PROBLEM_STATUS_BY_HUMAN_STATUS: dict[str, str] = {
    MODEL_HUMAN_STATUS_PENDING: PROBLEM_STATUS_CANDIDATE,
    MODEL_HUMAN_STATUS_CONFIRMED: PROBLEM_STATUS_CONFIRMED,
    MODEL_HUMAN_STATUS_REJECTED: PROBLEM_STATUS_REJECTED,
    MODEL_HUMAN_STATUS_NEEDS_REVIEW: PROBLEM_STATUS_REVIEW_REQUIRED,
    PROBLEM_STATUS_REVIEW_REQUIRED: PROBLEM_STATUS_REVIEW_REQUIRED,
    PROBLEM_STATUS_CONFIRMED: PROBLEM_STATUS_CONFIRMED,
    PROBLEM_STATUS_REJECTED: PROBLEM_STATUS_REJECTED,
}
"""问题清单 human_status → problem status（未识别取值按未回填处理）。"""

GRAIN_ASSESSMENT_CONFIRMED_CONFLICT = "confirmed_conflict"
GRAIN_ASSESSMENT_POSSIBLE_CONFLICT = "possible_conflict"
GRAIN_ASSESSMENT_REVIEW_REQUIRED = "review_required"

GRAIN_ASSESSMENT_ORDER: tuple[str, ...] = (
    GRAIN_ASSESSMENT_CONFIRMED_CONFLICT,
    GRAIN_ASSESSMENT_POSSIBLE_CONFLICT,
    GRAIN_ASSESSMENT_REVIEW_REQUIRED,
)
"""GRAIN_PROBLEM 的证据分级：候选键互不包含 / 全部互为子集 / 证据不足。"""

OVERLAP_CLASS_STRUCTURAL = "structural_overlap"
OVERLAP_CLASS_DUPLICATION = "duplication_candidate"
OVERLAP_CLASS_TECHNICAL_COPY = "technical_copy_candidate"
OVERLAP_CLASS_DIVERGENT_STRUCTURE = "grain_identical_structure_divergent"

OVERLAP_CLASS_ORDER: tuple[str, ...] = (
    OVERLAP_CLASS_DUPLICATION,
    OVERLAP_CLASS_TECHNICAL_COPY,
    OVERLAP_CLASS_STRUCTURAL,
    OVERLAP_CLASS_DIVERGENT_STRUCTURE,
)
"""MODEL_OVERLAP / MODEL_DUPLICATION 的分类（重叠 ≠ 重复）。"""

AGGREGATE_ASSESSMENT_VALID = "valid_aggregate"
AGGREGATE_ASSESSMENT_REVIEW_REQUIRED = "review_required"
AGGREGATE_ASSESSMENT_MODEL_PROBLEM = "model_problem"

AGGREGATE_ASSESSMENT_ORDER: tuple[str, ...] = (
    AGGREGATE_ASSESSMENT_VALID,
    AGGREGATE_ASSESSMENT_REVIEW_REQUIRED,
    AGGREGATE_ASSESSMENT_MODEL_PROBLEM,
)
"""聚合表评估：有原子事实来源且无重复 / 证据不足 / 无原子来源且重复或粒度冲突。"""

UNKNOWN_REASON_NO_EVIDENCE = "NO_EVIDENCE"
UNKNOWN_REASON_NO_ANCHOR = "NO_ANCHOR"
UNKNOWN_REASON_TECHNICAL_TABLE = "TECHNICAL_TABLE"
UNKNOWN_REASON_NON_BUSINESS = "NON_BUSINESS"
UNKNOWN_REASON_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

UNKNOWN_REASON_ORDER: tuple[str, ...] = (
    UNKNOWN_REASON_NO_EVIDENCE,
    UNKNOWN_REASON_NO_ANCHOR,
    UNKNOWN_REASON_TECHNICAL_TABLE,
    UNKNOWN_REASON_NON_BUSINESS,
    UNKNOWN_REASON_INSUFFICIENT_EVIDENCE,
)
"""UNKNOWN 表的解释分类；证据不足时 UNKNOWN 就是合法结果，不自动转 FACT / DIMENSION。"""

PROBLEM_IMPACT_GRAIN_INCONSISTENCY = "GRAIN_INCONSISTENCY"
PROBLEM_IMPACT_DUPLICATED_MODEL = "DUPLICATED_MODEL"
PROBLEM_IMPACT_QUERY_COMPLEXITY = "QUERY_COMPLEXITY"
PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY = "MODEL_SELECTION_DIFFICULTY"
PROBLEM_IMPACT_METRIC_AMBIGUITY = "METRIC_AMBIGUITY"
PROBLEM_IMPACT_MAINTENANCE_COST = "MAINTENANCE_COST"
PROBLEM_IMPACT_REUSE_DIFFICULTY = "REUSE_DIFFICULTY"
PROBLEM_IMPACT_GOVERNANCE_DIFFICULTY = "GOVERNANCE_DIFFICULTY"
PROBLEM_IMPACT_ANALYTICAL_RISK = "ANALYTICAL_RISK"
PROBLEM_IMPACT_DATA_CONSUMER_CONFUSION = "DATA_CONSUMER_CONFUSION"
PROBLEM_IMPACT_AI_SEMANTIC_RISK = "AI_SEMANTIC_RISK"

PROBLEM_IMPACT_ORDER: tuple[str, ...] = (
    PROBLEM_IMPACT_GRAIN_INCONSISTENCY,
    PROBLEM_IMPACT_DUPLICATED_MODEL,
    PROBLEM_IMPACT_QUERY_COMPLEXITY,
    PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY,
    PROBLEM_IMPACT_METRIC_AMBIGUITY,
    PROBLEM_IMPACT_MAINTENANCE_COST,
    PROBLEM_IMPACT_REUSE_DIFFICULTY,
    PROBLEM_IMPACT_GOVERNANCE_DIFFICULTY,
    PROBLEM_IMPACT_ANALYTICAL_RISK,
    PROBLEM_IMPACT_DATA_CONSUMER_CONFUSION,
    PROBLEM_IMPACT_AI_SEMANTIC_RISK,
)
"""impact 词汇（固定顺序）；只有证据支持时才允许出现。"""

PROBLEM_IMPACT_TITLE: dict[str, str] = {
    PROBLEM_IMPACT_GRAIN_INCONSISTENCY: "同一语义存在多种粒度口径",
    PROBLEM_IMPACT_DUPLICATED_MODEL: "同一业务语义存在多个模型",
    PROBLEM_IMPACT_QUERY_COMPLEXITY: "取数需要在多个相似模型间判断",
    PROBLEM_IMPACT_MODEL_SELECTION_DIFFICULTY: "消费者难以选择正确模型",
    PROBLEM_IMPACT_METRIC_AMBIGUITY: "指标口径可能不一致",
    PROBLEM_IMPACT_MAINTENANCE_COST: "同一语义需多处维护",
    PROBLEM_IMPACT_REUSE_DIFFICULTY: "模型难以复用",
    PROBLEM_IMPACT_GOVERNANCE_DIFFICULTY: "治理与口径追踪困难",
    PROBLEM_IMPACT_ANALYTICAL_RISK: "分析结果可能基于错误模型",
    PROBLEM_IMPACT_DATA_CONSUMER_CONFUSION: "数据使用者认知负担高",
    PROBLEM_IMPACT_AI_SEMANTIC_RISK: "AI / 语义层消费时易误选模型",
}
"""impact → 中文说明（报告用）。"""

PROBLEM_ROOT_CAUSE_MULTIPLE_GRAINS = "MULTIPLE_GRAINS_IN_ONE_MODEL"
PROBLEM_ROOT_CAUSE_DUPLICATED_PIPELINES = "DUPLICATED_MODEL_PIPELINES"
PROBLEM_ROOT_CAUSE_LAYER_OVERLAP = "LAYER_RESPONSIBILITY_OVERLAP"
PROBLEM_ROOT_CAUSE_RESPONSIBILITY_MIX = "BUSINESS_AND_ANALYTICAL_RESPONSIBILITY_MIX"
PROBLEM_ROOT_CAUSE_SOURCE_REPLICATION = "MULTIPLE_SOURCE_SYSTEM_REPLICATION"
PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION = "INSUFFICIENT_BUSINESS_MODEL_STANDARDIZATION"
PROBLEM_ROOT_CAUSE_AGGREGATION_ATOMIC_MIX = "AGGREGATION_AND_ATOMIC_DATA_MIX"
PROBLEM_ROOT_CAUSE_UNRESOLVED_ROLE = "UNRESOLVED_MODEL_ROLE"
PROBLEM_ROOT_CAUSE_GATE_MEASURE_DEPENDENCY = "FACT_GATE_MEASURE_DEPENDENCY"
PROBLEM_ROOT_CAUSE_UNKNOWN = "UNKNOWN"

PROBLEM_ROOT_CAUSE_ORDER: tuple[str, ...] = (
    PROBLEM_ROOT_CAUSE_MULTIPLE_GRAINS,
    PROBLEM_ROOT_CAUSE_DUPLICATED_PIPELINES,
    PROBLEM_ROOT_CAUSE_LAYER_OVERLAP,
    PROBLEM_ROOT_CAUSE_RESPONSIBILITY_MIX,
    PROBLEM_ROOT_CAUSE_SOURCE_REPLICATION,
    PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION,
    PROBLEM_ROOT_CAUSE_AGGREGATION_ATOMIC_MIX,
    PROBLEM_ROOT_CAUSE_UNRESOLVED_ROLE,
    PROBLEM_ROOT_CAUSE_GATE_MEASURE_DEPENDENCY,
    PROBLEM_ROOT_CAUSE_UNKNOWN,
)
"""root cause 词汇（固定顺序）；证据不足时必须写 UNKNOWN，不写设计偏好。"""

PROBLEM_ROOT_CAUSE_TITLE: dict[str, str] = {
    PROBLEM_ROOT_CAUSE_MULTIPLE_GRAINS: "同一模型内存在多种粒度",
    PROBLEM_ROOT_CAUSE_DUPLICATED_PIPELINES: "同一业务口径存在重复加工链路",
    PROBLEM_ROOT_CAUSE_LAYER_OVERLAP: "分层职责重叠",
    PROBLEM_ROOT_CAUSE_RESPONSIBILITY_MIX: "业务与分析职责混杂",
    PROBLEM_ROOT_CAUSE_SOURCE_REPLICATION: "多来源系统复制",
    PROBLEM_ROOT_CAUSE_NO_STANDARDIZATION: "业务模型标准化不足",
    PROBLEM_ROOT_CAUSE_AGGREGATION_ATOMIC_MIX: "聚合与原子数据混放",
    PROBLEM_ROOT_CAUSE_UNRESOLVED_ROLE: "模型角色未裁决",
    PROBLEM_ROOT_CAUSE_GATE_MEASURE_DEPENDENCY: "事实闸门依赖度量字段",
    PROBLEM_ROOT_CAUSE_UNKNOWN: "现有证据不足以判断",
}
"""root cause → 中文说明（报告用）。"""

PROBLEM_EVIDENCE_FINDING = "FINDING"
PROBLEM_EVIDENCE_TABLE = "TABLE"
PROBLEM_EVIDENCE_COLUMN = "COLUMN"
PROBLEM_EVIDENCE_PROCESS = "PROCESS"
PROBLEM_EVIDENCE_GRAIN = "GRAIN"
PROBLEM_EVIDENCE_OBJECT = "OBJECT"
PROBLEM_EVIDENCE_SQL = "SQL"
PROBLEM_EVIDENCE_LINEAGE = "LINEAGE"
PROBLEM_EVIDENCE_RELATIONSHIP = "RELATIONSHIP"

PROBLEM_EVIDENCE_ORDER: tuple[str, ...] = (
    PROBLEM_EVIDENCE_FINDING,
    PROBLEM_EVIDENCE_TABLE,
    PROBLEM_EVIDENCE_COLUMN,
    PROBLEM_EVIDENCE_PROCESS,
    PROBLEM_EVIDENCE_GRAIN,
    PROBLEM_EVIDENCE_OBJECT,
    PROBLEM_EVIDENCE_SQL,
    PROBLEM_EVIDENCE_LINEAGE,
    PROBLEM_EVIDENCE_RELATIONSHIP,
)
"""问题证据类型（固定顺序）；SQL 证据本阶段不读 SQL 产物，因此恒为 0。"""

PROBLEM_EVIDENCE_SET: frozenset[str] = frozenset(PROBLEM_EVIDENCE_ORDER)

PROBLEM_EVIDENCE_ROW_LIMIT = 50
"""单个 problem 的证据行上限（超出截断并记录 evidence_total）。"""

PROBLEM_SUMMARY_ROW_LIMIT = 20
"""current-state-problem-summary.md 里 Top Problems 的行数上限。"""

PROBLEM_REPORT_ROW_LIMIT = 50
"""current-state-problem-summary.md 里其它明细表的行数上限。"""

PROBLEM_CHECKLIST_ROW_LIMIT = 50
"""current-state-problem-review-checklist.md 每个分区的行数上限。"""

PROBLEM_CHECKLIST_HEADERS: tuple[str, ...] = (
    "problem_id",
    "problem_type",
    "priority",
    "scope_key",
    "evidence",
    "system_interpretation",
    "human_question",
    "human_status",
    "human_name",
    "note",
)
"""current-state-problem-review-checklist.md 的列（固定顺序）。"""

PROBLEM_CHECKLIST_REQUIRED_COLUMNS: tuple[str, ...] = (
    "problem_id",
    "human_status",
    "human_name",
    "note",
)
"""问题清单的回填列：缺一即报错。"""

PROBLEM_TYPE_PRIORITY: dict[str, str] = {
    PROBLEM_TYPE_GRAIN: REVIEW_PRIORITY_P0,
    PROBLEM_TYPE_ROLE_AMBIGUITY: REVIEW_PRIORITY_P0,
    PROBLEM_TYPE_COVERAGE_GAP: REVIEW_PRIORITY_P0,
    PROBLEM_TYPE_DUPLICATION: REVIEW_PRIORITY_P1,
    PROBLEM_TYPE_OVERLAP: REVIEW_PRIORITY_P1,
    PROBLEM_TYPE_MIXED_RESPONSIBILITY: REVIEW_PRIORITY_P1,
    PROBLEM_TYPE_AGGREGATION: REVIEW_PRIORITY_P1,
    PROBLEM_TYPE_FACT_IDENTIFICATION: REVIEW_PRIORITY_P1,
    PROBLEM_TYPE_SELECTION_AMBIGUITY: REVIEW_PRIORITY_P1,
    PROBLEM_TYPE_SEMANTIC_AMBIGUITY: REVIEW_PRIORITY_P1,
    PROBLEM_TYPE_DIMENSION_IDENTIFICATION: REVIEW_PRIORITY_P2,
    PROBLEM_TYPE_UNKNOWN_MODEL: REVIEW_PRIORITY_P2,
    PROBLEM_TYPE_PROCESS_ALIGNMENT: REVIEW_PRIORITY_P2,
}
"""没有 finding 支撑时 problem 的默认 priority；有 finding 时取最靠前的 priority。"""

SELECTION_AMBIGUITY_MIN_DUPLICATION = 10
"""一个 process 要形成 MODEL_SELECTION_AMBIGUITY 所需的最小重复问题数。"""

AGGREGATE_MIN_UPSTREAM_FOR_VALID = 1
"""判断聚合表是否存在原子事实来源所需的最小上游血缘边数。"""


@dataclass
class CurrentStateProblemResult:
    """一次 M3.6 v2 Problem Assessment 的结果。

    两个 JSON payload + summary / checklist 两个 Markdown 正文；
    只表达 Finding 聚合后的候选问题、证据链、影响、根因与重构理由。
    """

    problems: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    checklist: str = ""
    analysis_dir: Path = field(default_factory=Path)

    @property
    def problem_count(self) -> int:
        return int(self.problems.get("count") or 0)

    @property
    def type_counts(self) -> dict[str, int]:
        return dict(self.problems.get("problem_type_counts") or {})

    @property
    def status_counts(self) -> dict[str, int]:
        return dict(self.problems.get("status_counts") or {})

    @property
    def priority_counts(self) -> dict[str, int]:
        return dict(self.problems.get("priority_counts") or {})

    @property
    def impact_counts(self) -> dict[str, int]:
        return dict(self.problems.get("impact_counts") or {})


@dataclass
class CurrentStateModelResult:
    """一次 M3.6 运行的结果。

    三个 JSON 产物的顶层 payload（固定顺序）+ summary / checklist 两个
    Markdown 正文；只表达当前模型形态、评审发现与人工问题。
    problem 挂载本次运行的 M3.6 v2 Problem Assessment 结果（可为 None）。
    """

    problem: CurrentStateProblemResult | None = None

    model: dict[str, Any] = field(default_factory=dict)
    tables: dict[str, Any] = field(default_factory=dict)
    findings: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    checklist: str = ""
    analysis_dir: Path = field(default_factory=Path)

    @property
    def table_count(self) -> int:
        return int(self.tables.get("count") or 0)

    @property
    def finding_count(self) -> int:
        return int(self.findings.get("count") or 0)

    @property
    def priority_counts(self) -> dict[str, int]:
        return dict(self.findings.get("priority_counts") or {})

    @property
    def finding_type_counts(self) -> dict[str, int]:
        return dict(self.findings.get("finding_type_counts") or {})

    @property
    def review_group_counts(self) -> dict[str, int]:
        return dict(self.findings.get("review_group_counts") or {})

    @property
    def status_counts(self) -> dict[str, int]:
        return dict(self.findings.get("status_counts") or {})

    @property
    def role_counts(self) -> dict[str, int]:
        return dict(self.tables.get("role_counts") or {})


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

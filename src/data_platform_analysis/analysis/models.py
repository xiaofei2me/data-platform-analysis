"""M2.1～M2.4 的分析记录模型。

设计原则：

1. 稳定身份优先：Workspace 用 workspace_id，File 用 workspace_id + file_id，
   Table 用 workspace_id + project + schema + table。
2. 记录里保留来源引用（raw_file / content_file / evidence），
   让每条结论都能回到 Snapshot 原文。
3. 只表达事实与 Candidate，不表达业务结论。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
    layer_candidate: str | None = None
    layer_candidate_evidence: str | None = None
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
# M2.2 SQL Analysis
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
# M2.3 Table Lineage
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
# M2.4 Data Profiling
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
# 排序工具
# ============================================================


def numeric_id_sort_key(value: int | str | None) -> tuple[int, int, str]:
    """把可能为字符串的 ID 转成确定性排序键。

    数字 ID 按数值排序，非数字 ID 排在数字之后并按字典序排列。
    """

    text = "" if value is None else str(value)

    if text.isdigit():
        return (0, int(text), "")

    return (1, 0, text)

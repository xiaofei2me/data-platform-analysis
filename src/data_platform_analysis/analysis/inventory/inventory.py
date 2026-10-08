"""M2.1 Warehouse Inventory。

目标：

    建立整个数据仓库的统一分析清单，作为后续 SQL Analysis、
    Table Reference、Lineage、Profiling 的唯一输入。

输入：
    source/dataworks/workspaces/<workspace_id>/files-index.json
    source/maxcompute/workspaces/<workspace_id>/tables-index.json
    source/maxcompute/workspaces/<workspace_id>/tables/<table>.json

输出：
    analysis/inventory/{workspaces,files,tables,columns}.json

约定：

1. 稳定身份：Workspace=workspace_id；File=workspace_id+file_id；
   Table=project.table（table_key），不包含 schema。
2. index 用于导航，raw JSON 是 Source of Truth；冲突时 raw 优先。
3. 层级判定不在 M2.1 范围：由 M2.2 Layer Assessment 依据 workspace 事实
   与 config/layer-rules.yaml 产出唯一层级候选（candidate_layer）。
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ...dataworks_types import get_file_type
from ..models import (
    ColumnInventory,
    FileInventory,
    TableInventory,
    WorkspaceInventory,
    is_analysis_eligible,
    numeric_id_sort_key,
)
from ..snapshot import SnapshotReader, WorkspaceIdentity, to_int

logger = logging.getLogger(__name__)


@dataclass
class Inventory:
    """M2.1 的全部清单。"""

    workspaces: list[WorkspaceInventory] = field(default_factory=list)
    files: list[FileInventory] = field(default_factory=list)
    tables: list[TableInventory] = field(default_factory=list)
    columns: list[ColumnInventory] = field(default_factory=list)


@dataclass
class WorkspaceSnapshot:
    """单个 Workspace 的 index 读取结果。"""

    identity: WorkspaceIdentity
    project: str
    schema: str
    file_entries: list[dict[str, Any]] | None
    table_entries: list[dict[str, Any]] | None


class InventoryBuilder:
    """从 Snapshot 构建 M2.1 清单。"""

    def __init__(
        self,
        reader: SnapshotReader,
        identities: list[WorkspaceIdentity],
    ) -> None:
        self.reader = reader
        self.identities = identities

    def build(self) -> Inventory:
        """构建全部 Inventory。"""

        logger.info(
            "M2.1 Inventory 开始构建：workspace=%s（index 用于导航，raw JSON 为 Source of Truth）",
            len(self.identities),
        )

        snapshots = [self._load_workspace(identity) for identity in self.identities]

        inventory = Inventory()

        for snapshot in snapshots:
            self._build_files(inventory, snapshot)
            self._build_tables(inventory, snapshot)

        self._build_workspaces(inventory, snapshots)

        inventory.workspaces.sort(key=lambda item: item.workspace_id)
        inventory.files.sort(
            key=lambda item: (item.workspace_id, numeric_id_sort_key(item.file_id))
        )
        inventory.tables.sort(
            key=lambda item: (
                item.workspace_id,
                item.project,
                item.schema,
                item.table,
            )
        )
        inventory.columns.sort(
            key=lambda item: (
                item.workspace_id,
                item.project,
                item.table,
                item.ordinal,
            )
        )

        inventory_errors = [
            record for record in self.reader.ledger.records() if record.get("stage") == "inventory"
        ]

        if inventory_errors:
            type_counts = Counter(
                str(record.get("error_type") or "UNKNOWN") for record in inventory_errors
            )
            logger.warning(
                "M2.1 检出 %s 条可恢复错误（缺索引 / 缺 raw / 解析失败，"
                "明细见 analysis/evidence/errors.json）：%s",
                len(inventory_errors),
                "，".join(f"{key}={value}" for key, value in sorted(type_counts.items())),
            )

        logger.info(
            "M2.1 Inventory 完成：workspace=%s，file=%s，table=%s，column=%s",
            len(inventory.workspaces),
            len(inventory.files),
            len(inventory.tables),
            len(inventory.columns),
        )

        return inventory

    # ==========================================================
    # Workspace
    # ==========================================================

    def _load_workspace(
        self,
        identity: WorkspaceIdentity,
    ) -> WorkspaceSnapshot:
        """读取单个 Workspace 的两个 index。"""

        file_entries: list[dict[str, Any]] | None = None
        table_entries: list[dict[str, Any]] | None = None

        if identity.dataworks_snapshot is not None:
            index_path = f"dataworks/workspaces/{identity.workspace_id}/files-index.json"

            if self.reader.resolve(index_path).exists():
                file_entries = self.reader.load_files_index(identity)
                logger.info(
                    "M2.1 files-index 已读取：%s（file=%s）",
                    index_path,
                    len(file_entries or []),
                )

            else:
                self.reader.ledger.add(
                    stage="inventory",
                    error_type="FILES_INDEX_MISSING",
                    message="files-index.json 不存在",
                    workspace_id=identity.workspace_id,
                    path=index_path,
                )
                logger.warning(
                    "M2.1 files-index.json 不存在，该 Workspace 不产出 File 清单：%s",
                    index_path,
                )

        if identity.maxcompute_snapshot is not None:
            index_path = f"maxcompute/workspaces/{identity.workspace_id}/tables-index.json"

            if self.reader.resolve(index_path).exists():
                table_entries = self.reader.load_tables_index(identity)
                logger.info(
                    "M2.1 tables-index 已读取：%s（table=%s）",
                    index_path,
                    len(table_entries or []),
                )

            else:
                self.reader.ledger.add(
                    stage="inventory",
                    error_type="TABLES_INDEX_MISSING",
                    message="tables-index.json 不存在",
                    workspace_id=identity.workspace_id,
                    path=index_path,
                )
                logger.warning(
                    "M2.1 tables-index.json 不存在，该 Workspace 不产出 Table / Column 清单：%s",
                    index_path,
                )

        project = identity.workspace_name
        schema = ""

        for entry in table_entries or []:
            project = str(entry.get("project") or project)
            schema = str(entry.get("schema") or "")
            break

        logger.info(
            "M2.1 Workspace 快照就绪：%s（name=%s，project=%s，schema=%s，file=%s，table=%s）",
            identity.workspace_id,
            identity.workspace_name,
            project,
            schema or "（空）",
            len(file_entries or []),
            len(table_entries or []),
        )

        return WorkspaceSnapshot(
            identity=identity,
            project=project,
            schema=schema,
            file_entries=file_entries,
            table_entries=table_entries,
        )

    def _build_workspaces(
        self,
        inventory: Inventory,
        snapshots: list[WorkspaceSnapshot],
    ) -> None:
        """汇总 Workspace 级清单与计数。"""

        for snapshot in snapshots:
            identity = snapshot.identity
            file_entries = snapshot.file_entries or []
            table_entries = snapshot.table_entries or []
            task_count = sum(1 for entry in file_entries if entry.get("category") == "TASK")
            resource_count = sum(1 for entry in file_entries if entry.get("category") == "RESOURCE")

            inventory.workspaces.append(
                WorkspaceInventory(
                    workspace_id=identity.workspace_id,
                    workspace_name=identity.workspace_name,
                    project=snapshot.project,
                    dataworks_snapshot=identity.dataworks_snapshot,
                    maxcompute_snapshot=identity.maxcompute_snapshot,
                    file_count=len(file_entries),
                    task_count=task_count,
                    resource_count=resource_count,
                    table_count=len(table_entries),
                )
            )

            logger.info(
                "M2.1 Workspace 清单：%s（name=%s，project=%s，file=%s，task=%s，"
                "resource=%s，table=%s）",
                identity.workspace_id,
                identity.workspace_name,
                snapshot.project,
                len(file_entries),
                task_count,
                resource_count,
                len(table_entries),
            )

    # ==========================================================
    # Files
    # ==========================================================

    def _build_files(
        self,
        inventory: Inventory,
        snapshot: WorkspaceSnapshot,
    ) -> None:
        """构建 FileInventory。"""

        workspace_id = snapshot.identity.workspace_id
        added = 0
        skipped = 0

        for entry in snapshot.file_entries or []:
            raw_file_id = entry.get("file_id")

            if raw_file_id is None or str(raw_file_id) == "":
                self.reader.ledger.add(
                    stage="inventory",
                    error_type="FILE_ID_MISSING",
                    message="files-index 条目缺少 file_id，无法建立稳定身份",
                    workspace_id=workspace_id,
                    path=str(entry.get("raw_file") or ""),
                )
                skipped += 1
                logger.warning(
                    "M2.1 files-index 条目缺少 file_id，无法建立稳定身份，已跳过："
                    "workspace=%s，raw_file=%s",
                    workspace_id,
                    str(entry.get("raw_file") or "（未知）"),
                )

                continue

            file_id_value = str(raw_file_id)

            node_id = to_int(entry.get("node_id"))
            node_id_value: int | str | None = (
                node_id if node_id is not None else _non_empty_str(entry.get("node_id"))
            )

            file_type = to_int(entry.get("file_type"))
            type_info = get_file_type(file_type)

            inventory.files.append(
                FileInventory(
                    workspace_id=workspace_id,
                    file_id=file_id_value,
                    file_name=_non_empty_str(entry.get("file_name")),
                    node_id=node_id_value,
                    use_type=_non_empty_str(entry.get("use_type")),
                    file_type=file_type,
                    file_type_name=str(entry.get("file_type_name") or type_info.name),
                    task_type=str(entry.get("task_type") or type_info.task_type),
                    category=str(entry.get("category") or type_info.category),
                    content_format=str(entry.get("content_format") or type_info.content_format),
                    raw_file=_non_empty_str(entry.get("raw_file")),
                    content_file=_non_empty_str(entry.get("content_file")),
                )
            )

            added += 1

        logger.info(
            "M2.1 File 清单构建完成：workspace=%s，新增=%s，跳过=%s",
            workspace_id,
            added,
            skipped,
        )

    # ==========================================================
    # Tables / Columns
    # ==========================================================

    def _build_tables(
        self,
        inventory: Inventory,
        snapshot: WorkspaceSnapshot,
    ) -> None:
        """构建 TableInventory 与 ColumnInventory。"""

        workspace_id = snapshot.identity.workspace_id
        added = 0
        skipped = 0
        raw_missing = 0
        columns_before = len(inventory.columns)

        for entry in snapshot.table_entries or []:
            table_name = _non_empty_str(entry.get("table"))

            if table_name is None:
                self.reader.ledger.add(
                    stage="inventory",
                    error_type="TABLE_NAME_MISSING",
                    message="tables-index 条目缺少 table，无法建立稳定身份",
                    workspace_id=workspace_id,
                    path=str(entry.get("raw_file") or ""),
                )
                skipped += 1
                logger.warning(
                    "M2.1 tables-index 条目缺少 table，无法建立稳定身份，已跳过："
                    "workspace=%s，raw_file=%s",
                    workspace_id,
                    str(entry.get("raw_file") or "（未知）"),
                )

                continue

            project = str(entry.get("project") or snapshot.project)
            schema = str(entry.get("schema") or snapshot.schema)
            table_key = f"{project}.{table_name}"

            raw_relative = _non_empty_str(entry.get("raw_file"))
            raw = self._load_table_raw(
                workspace_id=workspace_id,
                table=table_name,
                raw_file=raw_relative,
            )

            if raw is None:
                raw_missing += 1

            inventory.tables.append(
                TableInventory(
                    workspace_id=workspace_id,
                    workspace_name=snapshot.identity.workspace_name,
                    project=project,
                    schema=schema,
                    table=table_name,
                    comment=_first_str(
                        (raw or {}).get("comment"),
                        entry.get("comment"),
                    ),
                    column_count=_first_int(
                        _len_of((raw or {}).get("columns")),
                        entry.get("column_count"),
                    ),
                    partition_count=_first_int(
                        _len_of((raw or {}).get("partitions")),
                        entry.get("partition_count"),
                    ),
                    size=_first_int(
                        (raw or {}).get("size"),
                        entry.get("size"),
                    ),
                    is_virtual_view=(
                        (raw or {}).get("is_virtual_view")
                        if raw is not None and "is_virtual_view" in raw
                        else None
                    ),
                    lifecycle=_first_int((raw or {}).get("lifecycle"), None),
                    creation_time=_non_empty_str((raw or {}).get("creation_time")),
                    last_modified_time=_non_empty_str((raw or {}).get("last_modified_time")),
                    table_key=table_key,
                    raw_file=raw_relative,
                )
            )

            added += 1

            if raw is None:
                continue

            self._build_columns(
                inventory,
                workspace_id=workspace_id,
                project=project,
                schema=schema,
                table=table_name,
                table_key=table_key,
                raw=raw,
            )

        logger.info(
            "M2.1 Table / Column 清单构建完成：workspace=%s，table=%s"
            "（raw 缺失 / 解析失败=%s，跳过=%s），column=%s",
            workspace_id,
            added,
            raw_missing,
            skipped,
            len(inventory.columns) - columns_before,
        )

    def _build_columns(
        self,
        inventory: Inventory,
        *,
        workspace_id: int,
        project: str,
        schema: str,
        table: str,
        table_key: str,
        raw: dict[str, Any],
    ) -> None:
        """从 Table raw metadata 构建 ColumnInventory。"""

        columns = raw.get("columns")

        if not isinstance(columns, list):
            self.reader.ledger.add(
                stage="inventory",
                error_type="TABLE_COLUMNS_INVALID",
                message="Table raw metadata 缺少 columns 数组",
                workspace_id=workspace_id,
                table=table,
            )
            logger.warning(
                "M2.1 Table raw metadata 缺少 columns 数组，该表不产出列清单："
                "table=%s（workspace=%s）",
                table_key,
                workspace_id,
            )

            return

        partitions = raw.get("partitions")

        if not isinstance(partitions, list):
            partitions = []

        partition_names = {
            str(partition.get("name", "")).casefold()
            for partition in partitions
            if isinstance(partition, dict)
        }

        skipped = 0

        for ordinal, column in enumerate(columns):
            if not isinstance(column, dict):
                skipped += 1
                continue

            column_name = _non_empty_str(column.get("name"))

            if column_name is None:
                skipped += 1
                continue

            inventory.columns.append(
                ColumnInventory(
                    workspace_id=workspace_id,
                    project=project,
                    schema=schema,
                    table=table,
                    ordinal=ordinal,
                    column_name=column_name,
                    data_type=_non_empty_str(column.get("type")),
                    comment=_non_empty_str(column.get("comment")),
                    is_partition=column_name.casefold() in partition_names,
                    table_key=table_key,
                )
            )

        if skipped:
            logger.warning(
                "M2.1 列条目非对象或缺少列名，已跳过：table=%s（workspace=%s），跳过=%s",
                table_key,
                workspace_id,
                skipped,
            )

    def _load_table_raw(
        self,
        *,
        workspace_id: int,
        table: str,
        raw_file: str | None,
    ) -> dict[str, Any] | None:
        """读取 Table raw metadata；失败时记录可恢复错误。"""

        if raw_file is None:
            self.reader.ledger.add(
                stage="inventory",
                error_type="TABLE_RAW_MISSING",
                message="tables-index 条目缺少 raw_file",
                workspace_id=workspace_id,
                table=table,
            )
            logger.warning(
                "M2.1 tables-index 条目缺少 raw_file，该表仅有 index 侧字段："
                "table=%s（workspace=%s）",
                table,
                workspace_id,
            )

            return None

        if not self.reader.resolve(raw_file).exists():
            self.reader.ledger.add(
                stage="inventory",
                error_type="TABLE_RAW_MISSING",
                message="Table raw JSON 不存在",
                workspace_id=workspace_id,
                table=table,
                path=raw_file,
            )
            logger.warning(
                "M2.1 Table raw JSON 不存在，该表仅有 index 侧字段：table=%s，path=%s",
                table,
                raw_file,
            )

            return None

        raw = self.reader.read_json(
            raw_file,
            stage="inventory",
            error_type="TABLE_RAW_INVALID",
            workspace_id=workspace_id,
            table=table,
        )

        if raw is None:
            logger.warning(
                "M2.1 Table raw JSON 解析失败，该表仅有 index 侧字段：table=%s，path=%s",
                table,
                raw_file,
            )

        return raw


# ============================================================
# Inventory Summary（结构化统计：计算与展示分离）
#
# 这里只做计数与分类，不产生任何业务判断；
# 所有数字都来自当前 Inventory 与当前 Snapshot。
# ============================================================

SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_LOW = "Low"

STAGE_DISCOVERED = "Discovered"
STAGE_ELIGIBLE = "Eligible"
STAGE_ANALYZED = "Analyzed"
STAGE_EXCLUDED = "Excluded"
STAGE_EXCEPTION = "Exception"

REASON_MISSING_NODE_ID = "Missing Node ID"
"""当前实现里唯一真实存在的排除原因（见 is_analysis_eligible）。"""

ERROR_TYPE_FILES_INDEX = ("FILES_INDEX_MISSING", "FILES_INDEX_INVALID")
ERROR_TYPE_TABLES_INDEX = ("TABLES_INDEX_MISSING", "TABLES_INDEX_INVALID")
ERROR_TYPE_FILE_IDENTITY = ("FILE_ID_MISSING",)
ERROR_TYPE_TABLE_IDENTITY = ("TABLE_NAME_MISSING",)
ERROR_TYPE_TABLE_RAW = ("TABLE_RAW_MISSING", "TABLE_RAW_INVALID")
ERROR_TYPE_TABLE_COLUMNS = ("TABLE_COLUMNS_INVALID",)
ERROR_TYPE_WORKSPACE_INDEX = ("WORKSPACE_INDEX_INVALID", "MANIFEST_INVALID")


@dataclass(frozen=True)
class StatusCount:
    """一个「标签 → 计数」事实行。"""

    label: str
    count: int


@dataclass(frozen=True)
class ExclusionReason:
    """一条排除原因及其数量（只统计代码中真实存在的 reason）。"""

    reason: str
    count: int


@dataclass(frozen=True)
class CollectionException:
    """一条技术采集 / 处理异常（不含 Excluded，不含业务问题）。"""

    severity: str
    exception: str
    count: int
    impact: str


@dataclass
class WorkspaceInventorySummary:
    """单个 Workspace 的盘点汇总。"""

    workspace_id: int = 0
    workspace_name: str = ""
    project: str = ""
    has_dataworks_snapshot: bool = False
    has_maxcompute_snapshot: bool = False
    discovered_file_count: int = 0
    eligible_file_count: int = 0
    content_available_count: int = 0
    table_count: int = 0
    column_count: int = 0


@dataclass
class DataWorksInventorySummary:
    """DataWorks File 侧的盘点汇总。"""

    discovered_count: int = 0
    registered_count: int = 0
    raw_available_count: int = 0
    valid_node_id_count: int = 0
    missing_node_id_count: int = 0
    content_available_count: int = 0
    content_unavailable_count: int = 0
    content_path_missing_count: int = 0
    collect_failure_count: int = 0
    asset_exception_count: int = 0
    unrecognized_format_count: int = 0
    eligible_count: int = 0
    excluded_count: int = 0
    eligible_sql_format_count: int = 0
    eligible_content_available_count: int = 0
    eligible_sql_content_count: int = 0
    exclusion_reasons: list[ExclusionReason] = field(default_factory=list)


@dataclass
class MaxComputeInventorySummary:
    """MaxCompute Table / Column 侧的盘点汇总。"""

    discovered_count: int = 0
    registered_count: int = 0
    collect_failure_count: int = 0
    column_count: int = 0
    tables_with_columns: int = 0
    tables_without_columns: int = 0
    tables_with_raw_metadata: int = 0
    tables_without_raw_metadata: int = 0


@dataclass
class CollectionCompleteness:
    """采集完整性：DataWorks 与 MaxCompute 各自的状态计数行。"""

    dataworks: list[StatusCount] = field(default_factory=list)
    maxcompute: list[StatusCount] = field(default_factory=list)


@dataclass
class InventorySummary:
    """当前 Snapshot 的技术资产盘点与采集覆盖报告输入。"""

    workspaces: list[WorkspaceInventorySummary] = field(default_factory=list)
    dataworks: DataWorksInventorySummary = field(default_factory=DataWorksInventorySummary)
    maxcompute: MaxComputeInventorySummary = field(default_factory=MaxComputeInventorySummary)
    completeness: CollectionCompleteness = field(default_factory=CollectionCompleteness)
    exceptions: list[CollectionException] = field(default_factory=list)
    inventory_error_count: int = 0


def build_inventory_summary(
    inventory: Inventory,
    *,
    reader: SnapshotReader,
    errors: Sequence[Mapping[str, Any]] | None = None,
) -> InventorySummary:
    """从 Inventory 与当前 Snapshot 计算结构化盘点统计。

    输入：

    - ``inventory``：M2.1 清单（File / Table / Column / Workspace）；
    - ``reader``：只读 Snapshot，用于确认 content_file 是否真实存在，
      以及读取 index 里的采集失败条目；
    - ``errors``：可恢复错误记录，默认取当前 ledger。

    只统计，不判断：Excluded（规则不满足）与 Exception（技术失败）
    分开计数，Content 缺失不记作采集失败。
    """

    records = reader.ledger.records() if errors is None else list(errors)
    error_counts = Counter(
        str(record.get("error_type") or "UNKNOWN")
        for record in records
        if record.get("stage") == "inventory"
    )

    dataworks, files_by_workspace = _summarize_files(inventory, reader)
    maxcompute, tables_by_workspace = _summarize_tables(inventory, error_counts)

    dataworks.collect_failure_count, maxcompute.collect_failure_count = _collect_failures(
        inventory, reader
    )
    dataworks.asset_exception_count = (
        dataworks.collect_failure_count
        + dataworks.content_path_missing_count
        + _count_error_types(error_counts, ERROR_TYPE_FILE_IDENTITY)
    )

    workspace_summaries = [
        _workspace_summary(
            workspace,
            file_stats=file_stats,
            table_stats=table_stats,
        )
        for workspace, file_stats, table_stats in zip(
            inventory.workspaces,
            files_by_workspace,
            tables_by_workspace,
            strict=True,
        )
    ]

    summary = InventorySummary(
        workspaces=workspace_summaries,
        dataworks=dataworks,
        maxcompute=maxcompute,
        exceptions=_collection_exceptions(
            dataworks=dataworks,
            maxcompute=maxcompute,
            error_counts=error_counts,
            failed_files_total=dataworks.collect_failure_count,
            failed_tables_total=maxcompute.collect_failure_count,
            content_path_missing=dataworks.content_path_missing_count,
        ),
        inventory_error_count=sum(error_counts.values()),
    )

    summary.completeness = CollectionCompleteness(
        dataworks=_dataworks_completeness(dataworks),
        maxcompute=_maxcompute_completeness(maxcompute),
    )

    return summary


def _workspace_summary(
    workspace: WorkspaceInventory,
    *,
    file_stats: tuple[int, int, int],
    table_stats: tuple[int, int],
) -> WorkspaceInventorySummary:
    """组装单个 Workspace 的汇总行。

    file_stats = (registered, eligible, content_available)；
    table_stats = (tables, columns)。
    """

    _, eligible_count, content_count = file_stats
    table_count, column_count = table_stats

    return WorkspaceInventorySummary(
        workspace_id=workspace.workspace_id,
        workspace_name=workspace.workspace_name,
        project=workspace.project,
        has_dataworks_snapshot=workspace.dataworks_snapshot is not None,
        has_maxcompute_snapshot=workspace.maxcompute_snapshot is not None,
        discovered_file_count=workspace.file_count,
        eligible_file_count=eligible_count,
        content_available_count=content_count,
        table_count=table_count,
        column_count=column_count,
    )


def _summarize_files(
    inventory: Inventory,
    reader: SnapshotReader,
) -> tuple[DataWorksInventorySummary, list[tuple[int, int, int]]]:
    """统计 DataWorks File 侧指标。

    返回 (汇总, 每个 Workspace 的 (registered, eligible, content_available))，
    Workspace 顺序与 inventory.workspaces 一致。
    """

    summary = DataWorksInventorySummary(
        discovered_count=sum(workspace.file_count for workspace in inventory.workspaces),
    )

    registered_by_workspace: Counter[int] = Counter()
    eligible_by_workspace: Counter[int] = Counter()
    content_by_workspace: Counter[int] = Counter()

    for file in inventory.files:
        registered_by_workspace[file.workspace_id] += 1
        summary.registered_count += 1

        if file.raw_file:
            summary.raw_available_count += 1

        if str(file.content_format or "").upper() == "UNKNOWN":
            summary.unrecognized_format_count += 1

        content_available = _has_content(reader, file)

        if content_available:
            summary.content_available_count += 1
            content_by_workspace[file.workspace_id] += 1
        elif file.content_file:
            # content_file 指向的文件在 Snapshot 中不存在，属于技术异常。
            summary.content_path_missing_count += 1

        if not is_analysis_eligible(file):
            summary.excluded_count += 1
            continue

        summary.eligible_count += 1
        eligible_by_workspace[file.workspace_id] += 1

        if content_available:
            summary.eligible_content_available_count += 1

        if str(file.content_format or "").upper() == "SQL":
            summary.eligible_sql_format_count += 1

            if content_available:
                summary.eligible_sql_content_count += 1

    summary.valid_node_id_count = summary.eligible_count
    summary.missing_node_id_count = summary.excluded_count
    summary.content_unavailable_count = summary.registered_count - summary.content_available_count
    summary.exclusion_reasons = _exclusion_reasons(summary)

    file_stats = [
        (
            registered_by_workspace.get(workspace.workspace_id, 0),
            eligible_by_workspace.get(workspace.workspace_id, 0),
            content_by_workspace.get(workspace.workspace_id, 0),
        )
        for workspace in inventory.workspaces
    ]

    return summary, file_stats


def _summarize_tables(
    inventory: Inventory,
    error_counts: Counter[str],
) -> tuple[MaxComputeInventorySummary, list[tuple[int, int]]]:
    """统计 MaxCompute Table / Column 侧指标。

    返回 (汇总, 每个 Workspace 的 (tables, columns))，
    Workspace 顺序与 inventory.workspaces 一致。
    """

    summary = MaxComputeInventorySummary(
        discovered_count=sum(workspace.table_count for workspace in inventory.workspaces),
        registered_count=len(inventory.tables),
        column_count=len(inventory.columns),
    )

    tables_with_columns = {(item.workspace_id, item.table_key) for item in inventory.columns}
    summary.tables_with_columns = sum(
        1 for item in inventory.tables if (item.workspace_id, item.table_key) in tables_with_columns
    )
    summary.tables_without_columns = summary.registered_count - summary.tables_with_columns
    summary.tables_without_raw_metadata = _count_error_types(error_counts, ERROR_TYPE_TABLE_RAW)
    summary.tables_with_raw_metadata = (
        summary.registered_count - summary.tables_without_raw_metadata
    )

    table_counts: Counter[int] = Counter(item.workspace_id for item in inventory.tables)
    column_counts: Counter[int] = Counter(item.workspace_id for item in inventory.columns)

    table_stats = [
        (
            table_counts.get(workspace.workspace_id, 0),
            column_counts.get(workspace.workspace_id, 0),
        )
        for workspace in inventory.workspaces
    ]

    return summary, table_stats


def _collect_failures(
    inventory: Inventory,
    reader: SnapshotReader,
) -> tuple[int, int]:
    """读取 index 中的采集失败条目，返回 (failed_files, failed_tables)。"""

    failed_files_total = 0
    failed_tables_total = 0

    for workspace in inventory.workspaces:
        failed_files, failed_tables = reader.load_collection_failures(workspace.workspace_id)
        failed_files_total += len(failed_files)
        failed_tables_total += len(failed_tables)

    return failed_files_total, failed_tables_total


def _collection_exceptions(
    *,
    dataworks: DataWorksInventorySummary,
    maxcompute: MaxComputeInventorySummary,
    error_counts: Counter[str],
    failed_files_total: int,
    failed_tables_total: int,
    content_path_missing: int,
) -> list[CollectionException]:
    """组装 Collection Exceptions（只含技术异常，不含 Excluded）。"""

    rows = [
        (
            SEVERITY_HIGH,
            "GetFile 采集失败（files-index.failed_files）",
            failed_files_total,
            "该 File 没有 raw JSON 与 Content，无法进入任何分析",
        ),
        (
            SEVERITY_HIGH,
            "GetTable 采集失败（tables-index.failed_tables）",
            failed_tables_total,
            "该表没有元数据，不进入 Table / Column 清单",
        ),
        (
            SEVERITY_HIGH,
            "DataWorks files-index 缺失或解析失败",
            _count_error_types(error_counts, ERROR_TYPE_FILES_INDEX),
            "该 Workspace 不产出 File 清单",
        ),
        (
            SEVERITY_HIGH,
            "MaxCompute tables-index 缺失或解析失败",
            _count_error_types(error_counts, ERROR_TYPE_TABLES_INDEX),
            "该 Workspace 不产出 Table / Column 清单",
        ),
        (
            SEVERITY_MEDIUM,
            "files-index 条目缺少 file_id",
            _count_error_types(error_counts, ERROR_TYPE_FILE_IDENTITY),
            "无法建立稳定身份，该条目不进 File 清单",
        ),
        (
            SEVERITY_MEDIUM,
            "tables-index 条目缺少 table",
            _count_error_types(error_counts, ERROR_TYPE_TABLE_IDENTITY),
            "无法建立稳定身份，该条目不进 Table 清单",
        ),
        (
            SEVERITY_MEDIUM,
            "Table raw 元数据缺失或解析失败",
            _count_error_types(error_counts, ERROR_TYPE_TABLE_RAW),
            "该表只有 index 侧字段，列清单缺失",
        ),
        (
            SEVERITY_MEDIUM,
            "Table raw 缺少 columns 数组",
            _count_error_types(error_counts, ERROR_TYPE_TABLE_COLUMNS),
            "该表不产出列清单",
        ),
        (
            SEVERITY_MEDIUM,
            "Workspace 索引 / manifest 解析失败",
            _count_error_types(error_counts, ERROR_TYPE_WORKSPACE_INDEX),
            "Workspace 名称或身份可能退化",
        ),
        (
            SEVERITY_MEDIUM,
            "content_file 指向的 Snapshot 文件缺失",
            content_path_missing,
            "该 File 无法做内容级分析",
        ),
        (
            SEVERITY_LOW,
            "File 类型未登记（content_format = UNKNOWN）",
            dataworks.unrecognized_format_count,
            "无法判定内容格式，SQL Analysis 不处理该类 File；非采集失败",
        ),
    ]

    return [
        CollectionException(
            severity=severity,
            exception=exception,
            count=count,
            impact=impact,
        )
        for severity, exception, count, impact in rows
    ]


def _dataworks_completeness(dataworks: DataWorksInventorySummary) -> list[StatusCount]:
    """DataWorks 采集完整性状态行。"""

    return [
        StatusCount("Files discovered（files-index 条目）", dataworks.discovered_count),
        StatusCount("Files registered in inventory", dataworks.registered_count),
        StatusCount("Files with raw JSON", dataworks.raw_available_count),
        StatusCount("Files with valid Node ID", dataworks.valid_node_id_count),
        StatusCount("Files with content available", dataworks.content_available_count),
        StatusCount("Files without content", dataworks.content_unavailable_count),
        StatusCount("Files with content_file 指向文件缺失", dataworks.content_path_missing_count),
        StatusCount("GetFile 采集失败", dataworks.collect_failure_count),
    ]


def _maxcompute_completeness(maxcompute: MaxComputeInventorySummary) -> list[StatusCount]:
    """MaxCompute 采集完整性状态行。"""

    return [
        StatusCount("Tables discovered（tables-index 条目）", maxcompute.discovered_count),
        StatusCount("Tables registered in inventory", maxcompute.registered_count),
        StatusCount("Tables with raw metadata", maxcompute.tables_with_raw_metadata),
        StatusCount("Tables with column metadata", maxcompute.tables_with_columns),
        StatusCount("Tables without column metadata", maxcompute.tables_without_columns),
        StatusCount("Columns registered", maxcompute.column_count),
        StatusCount("GetTable 采集失败", maxcompute.collect_failure_count),
    ]


def _exclusion_reasons(summary: DataWorksInventorySummary) -> list[ExclusionReason]:
    """按代码中真实存在的 reason 汇总排除数量。"""

    if not summary.excluded_count:
        return []

    return [ExclusionReason(REASON_MISSING_NODE_ID, summary.excluded_count)]


def _has_content(reader: SnapshotReader, file: FileInventory) -> bool:
    """判断 File 的 Content 在 Snapshot 中是否可读（只看路径存在，不读内容）。"""

    if not file.content_file:
        return False

    return reader.resolve(file.content_file).exists()


def _count_error_types(
    error_counts: Counter[str],
    error_types: tuple[str, ...],
) -> int:
    """汇总若干 error_type 的计数。"""

    return sum(error_counts.get(error_type, 0) for error_type in error_types)


# ============================================================
# 工具
# ============================================================


def _non_empty_str(value: Any) -> str | None:
    """把值转成非空字符串，空值返回 None。"""

    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _first_str(*values: Any) -> str | None:
    """返回第一个可用的字符串值。"""

    for value in values:
        text = _non_empty_str(value)

        if text is not None:
            return text

    return None


def _first_int(*values: Any) -> int | None:
    """返回第一个可用的整数值。"""

    for value in values:
        converted = to_int(value)

        if converted is not None:
            return converted

    return None


def _len_of(value: Any) -> int | None:
    """返回序列长度，非序列返回 None。"""

    if isinstance(value, list):
        return len(value)

    return None

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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ...dataworks_types import FILE_TYPE_REGISTRY, get_file_type
from ..models import (
    ColumnInventory,
    FileInventory,
    TableInventory,
    WorkspaceInventory,
    is_analysis_eligible,
    numeric_id_sort_key,
)
from ..snapshot import SnapshotReader, WorkspaceIdentity, to_int
from .scope import FileScope, FileScopeStats

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

CASE_SHOW_ALL_LIMIT = 10
"""案例总数少于该值时全部展示。"""

CASE_REPRESENTATIVE_LIMIT = 5
"""案例总数超过全量展示阈值时的代表案例数量上限（3～5）。"""

NODE_ID_CASE_LIMIT = 3
"""缺失 / 无效 Node ID 的代表案例数量（大批量异常只展示少量定位案例）。"""

REASON_UNKNOWN_FORMAT = "content_format = UNKNOWN（类型未识别）"
REASON_MISSING_NODE_ID = "未提供 Node ID（node_id 为空）"
REASON_CONTENT_FILE_EMPTY = "未提供 Content（content_file 为空）"
REASON_CONTENT_PATH_MISSING = "content_file 指向的 Snapshot 文件缺失"

ERROR_TYPE_FILES_INDEX = ("FILES_INDEX_MISSING", "FILES_INDEX_INVALID")
ERROR_TYPE_TABLES_INDEX = ("TABLES_INDEX_MISSING", "TABLES_INDEX_INVALID")
ERROR_TYPE_FILE_IDENTITY = ("FILE_ID_MISSING",)
ERROR_TYPE_TABLE_IDENTITY = ("TABLE_NAME_MISSING",)
ERROR_TYPE_TABLE_RAW = ("TABLE_RAW_MISSING", "TABLE_RAW_INVALID")
ERROR_TYPE_TABLE_COLUMNS = ("TABLE_COLUMNS_INVALID",)
ERROR_TYPE_WORKSPACE_INDEX = ("WORKSPACE_INDEX_INVALID", "MANIFEST_INVALID")


@dataclass(frozen=True)
class AssetCase:
    """一条可回溯到 Snapshot 真实资产的代表案例。

    只保留定位所需的字段，不重新解释资产，也不生成虚构案例。
    """

    workspace_id: int
    workspace_name: str
    file_id: str | None
    node_id: int | str | None
    file_name: str | None
    file_type: int | None
    file_type_name: str
    content_format: str
    content_file: str | None
    reason: str


@dataclass(frozen=True)
class UnknownFormatGroup:
    """content_format = UNKNOWN 的一组文件（按 file_type 分类）。

    UNKNOWN ≠ 一定是错误：这里只按可观测特征分组，
    registered=False 表示该 file_type 未在类型注册表登记（类型映射缺口候选）。
    """

    file_type: int | None
    file_type_name: str
    task_type: str
    category: str
    registered: bool
    count: int


@dataclass(frozen=True)
class ExceptionCase:
    """一条技术异常的代表案例（只提供定位信息）。"""

    workspace_id: int | None
    file_id: str | None
    table: str | None
    path: str | None
    reason: str


@dataclass(frozen=True)
class TechnicalException:
    """一条技术异常检查项（只含技术异常，不含范围限制与正常形态）。"""

    severity: str
    exception: str
    count: int
    impact: str
    cases: list[ExceptionCase] = field(default_factory=list)


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
    unrecognized_format_count: int = 0
    eligible_count: int = 0
    eligible_sql_format_count: int = 0
    eligible_content_available_count: int = 0
    eligible_sql_content_count: int = 0
    unknown_format_groups: list[UnknownFormatGroup] = field(default_factory=list)
    unknown_format_cases: list[AssetCase] = field(default_factory=list)
    missing_node_id_cases: list[AssetCase] = field(default_factory=list)
    content_unavailable_cases: list[AssetCase] = field(default_factory=list)
    content_path_missing_cases: list[AssetCase] = field(default_factory=list)


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
class InventorySummary:
    """当前 Snapshot 的数据资产基线与异常报告输入。"""

    workspaces: list[WorkspaceInventorySummary] = field(default_factory=list)
    dataworks: DataWorksInventorySummary = field(default_factory=DataWorksInventorySummary)
    maxcompute: MaxComputeInventorySummary = field(default_factory=MaxComputeInventorySummary)
    technical_exceptions: list[TechnicalException] = field(default_factory=list)
    inventory_error_count: int = 0
    scope: FileScopeStats | None = None
    """规则分类统计（Analysis Scope Rules）；未执行分类时为 None。"""


def build_inventory_summary(
    inventory: Inventory,
    *,
    reader: SnapshotReader,
    errors: Sequence[Mapping[str, Any]] | None = None,
    scope: FileScope | None = None,
) -> InventorySummary:
    """从 Inventory 与当前 Snapshot 计算结构化盘点统计。

    输入：

    - ``inventory``：M2.1 清单（File / Table / Column / Workspace）；
    - ``reader``：只读 Snapshot，用于确认 content_file 是否真实存在，
      以及读取 index 里的采集失败条目；
    - ``errors``：可恢复错误记录，默认取当前 ledger；
    - ``scope``：规则分类结果，提供节点身份 / 内容状态 / 分析资格 /
      非正式任务的统计口径，缺省时 Summary 不含规则分类节。

    只统计，不判断：范围限制（缺 Node ID）与技术异常（采集失败 / 元数据缺失）
    分开计数，Content 缺失不记作采集失败；代表案例全部回指真实 Snapshot 资产。
    规则分类统计同样只计数：唯一对象数与规则命中数分开，避免重复计数。
    """

    records = reader.ledger.records() if errors is None else list(errors)
    inventory_errors = [record for record in records if record.get("stage") == "inventory"]
    error_counts = Counter(
        str(record.get("error_type") or "UNKNOWN") for record in inventory_errors
    )

    workspace_names = {
        workspace.workspace_id: workspace.workspace_name for workspace in inventory.workspaces
    }

    dataworks, files_by_workspace = _summarize_files(inventory, reader, workspace_names)
    maxcompute, tables_by_workspace = _summarize_tables(inventory, error_counts)

    failed_files, failed_tables = _collect_failures(inventory, reader)
    dataworks.collect_failure_count = len(failed_files)
    maxcompute.collect_failure_count = len(failed_tables)

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
        technical_exceptions=_technical_exceptions(
            dataworks=dataworks,
            maxcompute=maxcompute,
            error_counts=error_counts,
            inventory_errors=inventory_errors,
            failed_files=failed_files,
            failed_tables=failed_tables,
            content_path_missing=dataworks.content_path_missing_cases,
        ),
        inventory_error_count=sum(error_counts.values()),
        scope=scope.stats() if scope is not None else None,
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
    workspace_names: Mapping[int, str],
) -> tuple[DataWorksInventorySummary, list[tuple[int, int, int]]]:
    """统计 DataWorks File 侧指标，并挑选代表案例。

    返回 (汇总, 每个 Workspace 的 (registered, eligible, content_available))，
    Workspace 顺序与 inventory.workspaces 一致。
    """

    summary = DataWorksInventorySummary(
        discovered_count=sum(workspace.file_count for workspace in inventory.workspaces),
    )

    registered_by_workspace: Counter[int] = Counter()
    eligible_by_workspace: Counter[int] = Counter()
    content_by_workspace: Counter[int] = Counter()
    unknown_files: list[FileInventory] = []
    missing_node_files: list[FileInventory] = []
    content_unavailable: list[tuple[FileInventory, str]] = []
    content_path_missing: list[FileInventory] = []

    for file in inventory.files:
        registered_by_workspace[file.workspace_id] += 1
        summary.registered_count += 1

        if file.raw_file:
            summary.raw_available_count += 1

        if str(file.content_format or "").upper() == "UNKNOWN":
            summary.unrecognized_format_count += 1
            unknown_files.append(file)

        content_available = _has_content(reader, file)

        if content_available:
            summary.content_available_count += 1
            content_by_workspace[file.workspace_id] += 1

        elif file.content_file:
            # content_file 指向的文件在 Snapshot 中不存在，属于技术异常。
            # 在 Inventory 阶段记录：Content 是否可用已由规则分类判定，
            # 被排除出 SQL 分析的文件不再经过 SQL 阶段，也不能因此丢掉这条事实。
            reader.ledger.add(
                stage="inventory",
                error_type="CONTENT_FILE_MISSING",
                message="content_file 指向的文件在 Snapshot 中不存在",
                workspace_id=file.workspace_id,
                file_id=str(file.file_id),
                path=file.content_file,
            )
            summary.content_path_missing_count += 1
            content_path_missing.append(file)
            content_unavailable.append((file, REASON_CONTENT_PATH_MISSING))

        else:
            # content_file 为空是采集结果事实，不是技术异常。
            content_unavailable.append((file, REASON_CONTENT_FILE_EMPTY))

        if not is_analysis_eligible(file):
            missing_node_files.append(file)
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
    summary.missing_node_id_count = len(missing_node_files)
    summary.content_unavailable_count = summary.registered_count - summary.content_available_count
    summary.unknown_format_groups = _unknown_format_groups(unknown_files)
    summary.unknown_format_cases = _trim_examples(
        [_file_case(item, workspace_names, reason=REASON_UNKNOWN_FORMAT) for item in unknown_files],
        key=lambda case: case.file_type,
    )
    summary.missing_node_id_cases = _trim_examples(
        [
            _file_case(item, workspace_names, reason=REASON_MISSING_NODE_ID)
            for item in missing_node_files
        ],
        key=lambda case: case.file_type,
        limit=NODE_ID_CASE_LIMIT,
    )
    summary.content_unavailable_cases = _trim_examples(
        [_file_case(item, workspace_names, reason=reason) for item, reason in content_unavailable],
        key=lambda case: case.file_type,
    )
    summary.content_path_missing_cases = _trim_examples(
        [
            _file_case(item, workspace_names, reason=REASON_CONTENT_PATH_MISSING)
            for item in content_path_missing
        ],
        key=lambda case: case.file_type,
    )

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
) -> tuple[list[tuple[int, Mapping[str, Any]]], list[tuple[int, Mapping[str, Any]]]]:
    """读取 index 中的采集失败条目，返回 (failed_files, failed_tables)。

    每个元素是 ``(workspace_id, index 条目)``，供技术异常代表案例定位。
    """

    failed_files: list[tuple[int, Mapping[str, Any]]] = []
    failed_tables: list[tuple[int, Mapping[str, Any]]] = []

    for workspace in inventory.workspaces:
        files, tables = reader.load_collection_failures(workspace.workspace_id)
        failed_files.extend((workspace.workspace_id, entry) for entry in files)
        failed_tables.extend((workspace.workspace_id, entry) for entry in tables)

    return failed_files, failed_tables


def _technical_exceptions(
    *,
    dataworks: DataWorksInventorySummary,
    maxcompute: MaxComputeInventorySummary,
    error_counts: Counter[str],
    inventory_errors: Sequence[Mapping[str, Any]],
    failed_files: Sequence[tuple[int, Mapping[str, Any]]],
    failed_tables: Sequence[tuple[int, Mapping[str, Any]]],
    content_path_missing: Sequence[AssetCase],
) -> list[TechnicalException]:
    """组装技术异常检查项（只含技术异常，不含范围限制与正常形态）。

    缺失 Node ID（范围限制）与 content_format = UNKNOWN（正常但需要关注）
    不在本列表，它们由报告单独成节展示。
    """

    getfile_cases = _trim_examples(
        [
            ExceptionCase(
                workspace_id=workspace_id,
                file_id=_first_str(entry.get("file_id")),
                table=None,
                path=None,
                reason=str(entry.get("error") or "GetFile 采集失败"),
            )
            for workspace_id, entry in failed_files
        ],
        key=lambda case: case.workspace_id if case.workspace_id is not None else -1,
    )

    gettable_cases = _trim_examples(
        [
            ExceptionCase(
                workspace_id=workspace_id,
                file_id=None,
                table=_first_str(entry.get("table"), entry.get("name")),
                path=None,
                reason=str(entry.get("error") or "GetTable 采集失败"),
            )
            for workspace_id, entry in failed_tables
        ],
        key=lambda case: case.workspace_id if case.workspace_id is not None else -1,
    )

    content_path_cases = _trim_examples(
        [
            ExceptionCase(
                workspace_id=case.workspace_id,
                file_id=case.file_id,
                table=None,
                path=case.content_file,
                reason=REASON_CONTENT_PATH_MISSING,
            )
            for case in content_path_missing
        ],
        key=lambda case: case.workspace_id if case.workspace_id is not None else -1,
    )

    rows = [
        (
            SEVERITY_HIGH,
            "GetFile 采集失败（files-index.failed_files）",
            len(failed_files),
            "该 File 没有 raw JSON 与 Content，无法进入任何分析",
            getfile_cases,
        ),
        (
            SEVERITY_HIGH,
            "GetTable 采集失败（tables-index.failed_tables）",
            len(failed_tables),
            "该表没有元数据，不进入 Table / Column 清单",
            gettable_cases,
        ),
        (
            SEVERITY_HIGH,
            "DataWorks files-index 缺失或解析失败",
            _count_error_types(error_counts, ERROR_TYPE_FILES_INDEX),
            "该 Workspace 不产出 File 清单",
            _ledger_exception_cases(inventory_errors, ERROR_TYPE_FILES_INDEX),
        ),
        (
            SEVERITY_HIGH,
            "MaxCompute tables-index 缺失或解析失败",
            _count_error_types(error_counts, ERROR_TYPE_TABLES_INDEX),
            "该 Workspace 不产出 Table / Column 清单",
            _ledger_exception_cases(inventory_errors, ERROR_TYPE_TABLES_INDEX),
        ),
        (
            SEVERITY_MEDIUM,
            "files-index 条目缺少 file_id",
            _count_error_types(error_counts, ERROR_TYPE_FILE_IDENTITY),
            "无法建立稳定身份，该条目不进 File 清单",
            _ledger_exception_cases(inventory_errors, ERROR_TYPE_FILE_IDENTITY),
        ),
        (
            SEVERITY_MEDIUM,
            "tables-index 条目缺少 table",
            _count_error_types(error_counts, ERROR_TYPE_TABLE_IDENTITY),
            "无法建立稳定身份，该条目不进 Table 清单",
            _ledger_exception_cases(inventory_errors, ERROR_TYPE_TABLE_IDENTITY),
        ),
        (
            SEVERITY_MEDIUM,
            "Table raw 元数据缺失或解析失败",
            _count_error_types(error_counts, ERROR_TYPE_TABLE_RAW),
            "该表只有 index 侧字段，列清单缺失",
            _ledger_exception_cases(inventory_errors, ERROR_TYPE_TABLE_RAW),
        ),
        (
            SEVERITY_MEDIUM,
            "Table raw 缺少 columns 数组",
            _count_error_types(error_counts, ERROR_TYPE_TABLE_COLUMNS),
            "该表不产出列清单",
            _ledger_exception_cases(inventory_errors, ERROR_TYPE_TABLE_COLUMNS),
        ),
        (
            SEVERITY_MEDIUM,
            "Workspace 索引 / manifest 解析失败",
            _count_error_types(error_counts, ERROR_TYPE_WORKSPACE_INDEX),
            "Workspace 名称或身份可能退化",
            _ledger_exception_cases(inventory_errors, ERROR_TYPE_WORKSPACE_INDEX),
        ),
        (
            SEVERITY_MEDIUM,
            "content_file 指向的 Snapshot 文件缺失",
            len(content_path_missing),
            "该 File 无法做内容级分析",
            content_path_cases,
        ),
    ]

    return [
        TechnicalException(
            severity=severity,
            exception=exception,
            count=count,
            impact=impact,
            cases=cases,
        )
        for severity, exception, count, impact, cases in rows
    ]


def _unknown_format_groups(files: Sequence[FileInventory]) -> list[UnknownFormatGroup]:
    """把 content_format = UNKNOWN 的文件按 file_type 分类。

    只按可观测特征分组：file_type 是否已在类型注册表登记（registered）
    决定「已登记类型映射为 UNKNOWN」与「类型映射缺口候选」两类初步判断，
    具体判断留给人工。分组按数量降序、file_type 升序，确定性可复现。
    """

    buckets: dict[int | None, list[FileInventory]] = {}

    for file in files:
        buckets.setdefault(file.file_type, []).append(file)

    groups = [
        UnknownFormatGroup(
            file_type=file_type,
            file_type_name=bucket[0].file_type_name,
            task_type=bucket[0].task_type,
            category=bucket[0].category,
            registered=file_type in FILE_TYPE_REGISTRY,
            count=len(bucket),
        )
        for file_type, bucket in buckets.items()
    ]

    groups.sort(key=lambda item: (-item.count, item.file_type is None, item.file_type or 0))

    return groups


def _ledger_exception_cases(
    inventory_errors: Sequence[Mapping[str, Any]],
    error_types: tuple[str, ...],
) -> list[ExceptionCase]:
    """从 ledger 记录生成技术异常代表案例。"""

    return _trim_examples(
        [
            ExceptionCase(
                workspace_id=to_int(record.get("workspace_id")),
                file_id=_first_str(record.get("file_id")),
                table=_first_str(record.get("table")),
                path=_first_str(record.get("path")),
                reason=str(record.get("message") or record.get("error_type") or ""),
            )
            for record in inventory_errors
            if str(record.get("error_type") or "") in error_types
        ],
        key=lambda case: case.workspace_id if case.workspace_id is not None else -1,
    )


def _file_case(
    file: FileInventory,
    workspace_names: Mapping[int, str],
    *,
    reason: str,
) -> AssetCase:
    """把 File 转成可回溯到 Snapshot 的代表案例。"""

    return AssetCase(
        workspace_id=file.workspace_id,
        workspace_name=workspace_names.get(file.workspace_id) or str(file.workspace_id),
        file_id=str(file.file_id),
        node_id=file.node_id,
        file_name=file.file_name,
        file_type=file.file_type,
        file_type_name=file.file_type_name,
        content_format=file.content_format,
        content_file=file.content_file,
        reason=reason,
    )


def _trim_examples[ExampleT](
    examples: list[ExampleT],
    *,
    key: Callable[[ExampleT], object],
    limit: int = CASE_REPRESENTATIVE_LIMIT,
) -> list[ExampleT]:
    """按统一规则截断代表案例（确定性，不随机抽样）。

    - 总数少于 CASE_SHOW_ALL_LIMIT：全部保留，不隐藏少量异常；
    - 其余：先按 key 分类（数量多的类别优先），再轮转取样，
      保证代表案例覆盖不同类别。
    """

    if len(examples) < CASE_SHOW_ALL_LIMIT:
        return examples

    buckets: dict[object, list[ExampleT]] = {}

    for example in examples:
        buckets.setdefault(key(example), []).append(example)

    ordered = sorted(buckets.items(), key=lambda item: (-len(item[1]), str(item[0])))
    target = min(limit, len(examples))
    selected: list[ExampleT] = []

    while len(selected) < target:
        progressed = False

        for _, bucket in ordered:
            if bucket and len(selected) < target:
                selected.append(bucket.pop(0))
                progressed = True

        if not progressed:
            break

    return selected


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

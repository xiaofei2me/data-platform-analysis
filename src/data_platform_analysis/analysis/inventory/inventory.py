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
from dataclasses import dataclass, field
from typing import Any

from ...dataworks_types import get_file_type
from ..models import (
    ColumnInventory,
    FileInventory,
    TableInventory,
    WorkspaceInventory,
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

            else:
                self.reader.ledger.add(
                    stage="inventory",
                    error_type="FILES_INDEX_MISSING",
                    message="files-index.json 不存在",
                    workspace_id=identity.workspace_id,
                    path=index_path,
                )

        if identity.maxcompute_snapshot is not None:
            index_path = f"maxcompute/workspaces/{identity.workspace_id}/tables-index.json"

            if self.reader.resolve(index_path).exists():
                table_entries = self.reader.load_tables_index(identity)

            else:
                self.reader.ledger.add(
                    stage="inventory",
                    error_type="TABLES_INDEX_MISSING",
                    message="tables-index.json 不存在",
                    workspace_id=identity.workspace_id,
                    path=index_path,
                )

        project = identity.workspace_name
        schema = ""

        for entry in table_entries or []:
            project = str(entry.get("project") or project)
            schema = str(entry.get("schema") or "")
            break

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

            inventory.workspaces.append(
                WorkspaceInventory(
                    workspace_id=identity.workspace_id,
                    workspace_name=identity.workspace_name,
                    project=snapshot.project,
                    dataworks_snapshot=identity.dataworks_snapshot,
                    maxcompute_snapshot=identity.maxcompute_snapshot,
                    file_count=len(file_entries),
                    task_count=sum(1 for entry in file_entries if entry.get("category") == "TASK"),
                    resource_count=sum(
                        1 for entry in file_entries if entry.get("category") == "RESOURCE"
                    ),
                    table_count=len(table_entries),
                )
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

            return

        partitions = raw.get("partitions")

        if not isinstance(partitions, list):
            partitions = []

        partition_names = {
            str(partition.get("name", "")).casefold()
            for partition in partitions
            if isinstance(partition, dict)
        }

        for ordinal, column in enumerate(columns):
            if not isinstance(column, dict):
                continue

            column_name = _non_empty_str(column.get("name"))

            if column_name is None:
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

            return None

        return self.reader.read_json(
            raw_file,
            stage="inventory",
            error_type="TABLE_RAW_INVALID",
            workspace_id=workspace_id,
            table=table,
        )


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

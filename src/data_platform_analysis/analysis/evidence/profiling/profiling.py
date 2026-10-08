"""M2.5 Data Profiling：基于 Snapshot 元数据的 Metadata Profiling。

当前 Snapshot 只有表结构与文件元数据，没有行级数据样本，因此：

1. profile_status 恒为 metadata_only。
2. data_sample_available 恒为 false。
3. row_count / distinct_count / min / max / sample_values 等需要扫描
   数据才能得到的统计量一律为 null，不伪造。
4. is_candidate_key 恒为 false，因为缺少唯一性证据。
5. 不调用任何 MaxCompute / DataWorks API。
"""

from __future__ import annotations

import logging

from ...inventory.inventory import Inventory
from ...models import (
    PROFILE_STATUS_METADATA_ONLY,
    ColumnInventory,
    ColumnProfile,
    TableInventory,
    TableProfile,
    numeric_id_sort_key,
)

logger = logging.getLogger(__name__)

PROFILE_SOURCE = "maxcompute_table_metadata"
"""Profiling 的唯一数据来源。"""

INDEX_PATH_TEMPLATE = "maxcompute/workspaces/{workspace_id}/tables-index.json"


class MetadataProfiler:
    """从 Inventory 生成 Metadata Profiling 结果。"""

    def __init__(self, inventory: Inventory) -> None:
        self.inventory = inventory

        self.raw_files: dict[tuple[int, str], str | None] = {}

        for table in inventory.tables:
            self.raw_files.setdefault(
                (table.workspace_id, table.table_key.casefold()),
                table.raw_file,
            )

    def profile(self) -> tuple[list[TableProfile], list[ColumnProfile]]:
        """返回 (table_profiles, column_profiles)。"""

        tables = [self._table_profile(table) for table in self.inventory.tables]
        columns = [self._column_profile(column) for column in self.inventory.columns]

        tables.sort(
            key=lambda item: (
                numeric_id_sort_key(item.workspace_id),
                item.project,
                item.table,
            )
        )
        columns.sort(
            key=lambda item: (
                numeric_id_sort_key(item.workspace_id),
                item.project,
                item.table,
                item.ordinal,
            )
        )

        logger.info(
            "M2.5 Profiling 完成：table=%s，column=%s（metadata_only）",
            len(tables),
            len(columns),
        )

        return tables, columns

    def _table_profile(self, table: TableInventory) -> TableProfile:
        """生成单张表的 Profiling 结果。"""

        return TableProfile(
            workspace_id=table.workspace_id,
            project=table.project,
            schema=table.schema,
            table=table.table,
            table_key=table.table_key,
            profile_status=PROFILE_STATUS_METADATA_ONLY,
            data_sample_available=False,
            row_count=None,
            size=table.size,
            column_count=table.column_count,
            partition_count=table.partition_count,
            comment=table.comment,
            is_virtual_view=table.is_virtual_view,
            evidence={
                "source": PROFILE_SOURCE,
                "index": INDEX_PATH_TEMPLATE.format(workspace_id=table.workspace_id),
                "raw_file": table.raw_file,
            },
        )

    def _column_profile(self, column: ColumnInventory) -> ColumnProfile:
        """生成单个字段的 Profiling 结果。"""

        return ColumnProfile(
            workspace_id=column.workspace_id,
            project=column.project,
            schema=column.schema,
            table=column.table,
            table_key=column.table_key,
            ordinal=column.ordinal,
            column_name=column.column_name,
            data_type=column.data_type,
            comment=column.comment,
            is_partition=column.is_partition,
            profile_status=PROFILE_STATUS_METADATA_ONLY,
            is_candidate_key=False,
            null_count=None,
            null_ratio=None,
            distinct_count=None,
            min_value=None,
            max_value=None,
            sample_values=None,
            evidence={
                "source": PROFILE_SOURCE,
                "raw_file": self.raw_files.get((column.workspace_id, column.table_key.casefold())),
            },
        )

"""MaxCompute 数据采集。"""

from __future__ import annotations

import logging
from typing import Any

from odps import ODPS

from .config import settings

logger = logging.getLogger(__name__)


class MaxComputeClient:
    """MaxCompute 只读元数据客户端。"""

    def __init__(self) -> None:
        """初始化 MaxCompute 客户端。"""

        kwargs: dict[str, Any] = {}

        # 如果配置了 Schema，则传给 PyODPS。
        if settings.maxcompute_schema:
            kwargs["schema"] = (
                settings.maxcompute_schema
            )

        self.odps = ODPS(
            settings.alibaba_cloud_access_key_id,
            settings.alibaba_cloud_access_key_secret,
            project=settings.maxcompute_project,
            endpoint=settings.maxcompute_endpoint,
            **kwargs,
        )

    def list_tables(self) -> list[Any]:
        """获取 MaxCompute 项目中的全部表。"""

        logger.info(
            "开始获取 MaxCompute 表列表：project=%s",
            settings.maxcompute_project,
        )

        tables = list(
            self.odps.list_tables(
                extended=True,
            )
        )

        logger.info(
            "MaxCompute 表列表获取完成，共 %s 张表",
            len(tables),
        )

        return tables

    def get_table_metadata(
        self,
        table_name: str,
    ) -> dict[str, Any]:
        """
        获取单张 MaxCompute 表的完整元数据。

        当前主要采集：

        - 表名
        - 表注释
        - 创建时间
        - 修改时间
        - 数据大小
        - 生命周期
        - 是否 Virtual View
        - 普通字段
        - 分区字段
        """

        logger.debug(
            "获取 MaxCompute 表元数据：%s",
            table_name,
        )

        table = self.odps.get_table(
            table_name
        )

        # 重新从 MaxCompute 服务端加载最新元数据。
        table.reload()

        schema = table.schema

        # 普通字段。
        columns = [
            {
                "name": column.name,
                "type": str(column.type),
                "comment": column.comment,
            }
            for column in schema.columns
        ]

        # 分区字段。
        partitions = [
            {
                "name": partition.name,
                "type": str(partition.type),
                "comment": partition.comment,
            }
            for partition in schema.partitions
        ]

        metadata: dict[str, Any] = {
            "project": (
                settings.maxcompute_project
            ),
            "schema": (
                settings.maxcompute_schema
            ),
            "name": table.name,
            "comment": table.comment,
            "creation_time": (
                table.creation_time.isoformat()
                if table.creation_time
                else None
            ),
            "last_modified_time": (
                table.last_modified_time.isoformat()
                if table.last_modified_time
                else None
            ),
            "size": table.size,
            "lifecycle": table.lifecycle,
            "is_virtual_view": (
                table.is_virtual_view
            ),
            "columns": columns,
            "partitions": partitions,
        }

        # 实际分区数量可能非常大。
        # 默认关闭，只在明确需要时采集。
        if (
            settings.maxcompute_include_partitions
        ):
            metadata[
                "partition_instances"
            ] = self._get_partition_instances(
                table
            )

        return metadata

    @staticmethod
    def _get_partition_instances(
        table: Any,
    ) -> list[dict[str, Any]]:
        """
        获取表的实际分区实例。

        注意：
        对于大量分区表，这个操作可能产生较大的数据量。
        """

        result: list[dict[str, Any]] = []

        try:
            for partition in table.partitions:
                result.append(
                    {
                        "name": partition.name,
                        "creation_time": (
                            partition.creation_time.isoformat()
                            if partition.creation_time
                            else None
                        ),
                        "last_modified_time": (
                            partition.last_modified_time.isoformat()
                            if partition.last_modified_time
                            else None
                        ),
                        "size": partition.size,
                    }
                )

        except Exception:
            logger.exception(
                "获取表分区实例失败：table=%s",
                table.name,
            )

        return result
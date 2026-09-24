"""Snapshot 数据导出。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.progress import track

from .config import settings
from .dataworks import (
    DataWorksClient,
    extract_node_id,
    extract_node_name,
    extract_node_type,
    extract_sql_candidates,
)
from .io_utils import (
    ensure_dir,
    safe_filename,
    write_json,
    write_jsonl,
    write_sql,
)
from .maxcompute import MaxComputeClient

logger = logging.getLogger(__name__)


class SnapshotExporter:
    """
    Snapshot 导出器。

    当前版本只负责：

    DataWorks + MaxCompute
            ↓
        本地 Snapshot

    不在这里做 DWS / Semantic Layer 分析。
    """

    def __init__(
        self,
        source_dir: Path | None = None,
    ) -> None:
        self.source_dir = (
            source_dir
            if source_dir is not None
            else settings.source_dir
        )

        self.dataworks = DataWorksClient()
        self.maxcompute = MaxComputeClient()

    def export_all(self) -> None:
        """执行 DataWorks + MaxCompute 全量采集。"""

        logger.info(
            "开始执行完整 Snapshot 采集"
        )

        self.export_dataworks()
        self.export_maxcompute()
        self.write_manifest()

        logger.info(
            "完整 Snapshot 采集完成"
        )

    def export_dataworks(self) -> None:
        """
        采集 DataWorks 节点、SQL 和基础任务关系。
        """

        logger.info(
            "开始采集 DataWorks"
        )

        base_dir = (
            self.source_dir
            / "dataworks"
        )

        nodes_dir = (
            base_dir / "nodes"
        )

        sql_dir = (
            base_dir / "sql"
        )

        lineage_dir = (
            base_dir / "lineage"
        )

        ensure_dir(nodes_dir)
        ensure_dir(sql_dir)
        ensure_dir(lineage_dir)

        nodes = self.dataworks.list_nodes()

        node_index: list[
            dict[str, Any]
        ] = []

        lineage_records: list[
            dict[str, Any]
        ] = []

        for node in track(
            nodes,
            description="正在获取 DataWorks 节点",
        ):
            node_id = extract_node_id(
                node
            )

            if node_id is None:
                logger.warning(
                    "发现没有 Node ID 的节点，跳过：%s",
                    node,
                )
                continue

            node_name = extract_node_name(
                node
            )

            node_type = extract_node_type(
                node
            )

            try:
                # 获取节点完整详情。
                detail = (
                    self.dataworks.get_node(
                        node_id
                    )
                )

            except Exception:
                logger.exception(
                    "获取 DataWorks 节点详情失败：node_id=%s",
                    node_id,
                )
                continue

            # ==================================================
            # 保存原始节点 JSON
            # ==================================================

            raw_path = (
                nodes_dir
                / (
                    f"{safe_filename(node_id)}.json"
                )
            )

            write_json(
                raw_path,
                detail,
                overwrite=(
                    settings.export_overwrite
                ),
            )

            # ==================================================
            # 提取 SQL
            # ==================================================

            sql_candidates = (
                extract_sql_candidates(
                    detail
                )
            )

            sql_files: list[str] = []

            for index, sql in enumerate(
                sql_candidates,
                start=1,
            ):
                filename = (
                    f"{safe_filename(node_id)}"
                    f"_{index}.sql"
                )

                sql_path = (
                    sql_dir / filename
                )

                write_sql(
                    sql_path,
                    sql,
                    overwrite=(
                        settings.export_overwrite
                    ),
                )

                sql_files.append(
                    str(
                        sql_path.relative_to(
                            self.source_dir
                        )
                    )
                )

            # ==================================================
            # 保存节点索引
            # ==================================================

            node_index.append(
                {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_type": node_type,
                    "raw_file": str(
                        raw_path.relative_to(
                            self.source_dir
                        )
                    ),
                    "sql_files": sql_files,
                }
            )

            # ==================================================
            # 保存基础任务关系
            # ==================================================

            lineage_records.append(
                self._build_lineage_record(
                    node=node,
                    detail=detail,
                    sql_candidates=(
                        sql_candidates
                    ),
                )
            )

        # ======================================================
        # 保存节点索引
        # ======================================================

        write_json(
            base_dir
            / "nodes-index.json",
            {
                "generated_at": utc_now(),
                "project_id": (
                    settings.dataworks_project_id
                ),
                "count": len(node_index),
                "nodes": node_index,
            },
            overwrite=(
                settings.export_overwrite
            ),
        )

        # ======================================================
        # 保存基础任务关系
        # ======================================================

        write_jsonl(
            lineage_dir
            / "task-lineage.jsonl",
            lineage_records,
            overwrite=(
                settings.export_overwrite
            ),
        )

        logger.info(
            "DataWorks 采集完成：%s 个节点",
            len(node_index),
        )

    def export_maxcompute(self) -> None:
        """采集 MaxCompute 表结构和元数据。"""

        logger.info(
            "开始采集 MaxCompute"
        )

        base_dir = (
            self.source_dir
            / "maxcompute"
        )

        tables_dir = (
            base_dir / "tables"
        )

        metadata_dir = (
            base_dir / "metadata"
        )

        ensure_dir(tables_dir)
        ensure_dir(metadata_dir)

        tables = (
            self.maxcompute.list_tables()
        )

        table_index: list[
            dict[str, Any]
        ] = []

        for table in track(
            tables,
            description="正在获取 MaxCompute 表",
        ):
            table_name = table.name

            try:
                metadata = (
                    self.maxcompute
                    .get_table_metadata(
                        table_name
                    )
                )

            except Exception:
                logger.exception(
                    "获取 MaxCompute 表失败：table=%s",
                    table_name,
                )
                continue

            filename = (
                f"{safe_filename(table_name)}.json"
            )

            table_path = (
                tables_dir / filename
            )

            write_json(
                table_path,
                metadata,
                overwrite=(
                    settings.export_overwrite
                ),
            )

            table_index.append(
                {
                    "project": (
                        settings.maxcompute_project
                    ),
                    "schema": (
                        settings.maxcompute_schema
                    ),
                    "table": table_name,
                    "comment": metadata.get(
                        "comment"
                    ),
                    "column_count": len(
                        metadata.get(
                            "columns",
                            [],
                        )
                    ),
                    "partition_count": len(
                        metadata.get(
                            "partitions",
                            [],
                        )
                    ),
                    "size": metadata.get(
                        "size"
                    ),
                    "raw_file": str(
                        table_path.relative_to(
                            self.source_dir
                        )
                    ),
                }
            )

        # 保存所有 MaxCompute 表的索引。
        write_json(
            metadata_dir
            / "tables-index.json",
            {
                "generated_at": utc_now(),
                "project": (
                    settings.maxcompute_project
                ),
                "schema": (
                    settings.maxcompute_schema
                ),
                "count": len(table_index),
                "tables": table_index,
            },
            overwrite=(
                settings.export_overwrite
            ),
        )

        logger.info(
            "MaxCompute 采集完成：%s 张表",
            len(table_index),
        )

    def write_manifest(self) -> None:
        """
        生成 Snapshot 清单。

        用于记录本次 Snapshot 的来源和生成时间。
        """

        manifest = {
            "generated_at": utc_now(),
            "tool": "data-platform-analysis",
            "version": "0.1.0",
            "sources": {
                "dataworks": {
                    "api_version": "2024-05-18",
                    "region": (
                        settings.dataworks_region
                    ),
                    "project_id": (
                        settings.dataworks_project_id
                    ),
                },
                "maxcompute": {
                    "project": (
                        settings.maxcompute_project
                    ),
                    "schema": (
                        settings.maxcompute_schema
                    ),
                },
            },
        }

        write_json(
            self.source_dir
            / "manifest.json",
            manifest,
            overwrite=(
                settings.export_overwrite
            ),
        )

    @staticmethod
    def _build_lineage_record(
        *,
        node: dict[str, Any],
        detail: dict[str, Any],
        sql_candidates: list[str],
    ) -> dict[str, Any]:
        """
        构建基础任务关系记录。

        注意：

        当前这里只保存 DataWorks 节点级信息，
        还不是最终的表级血缘。

        后续需要结合：

        1. DataWorks 节点依赖
        2. SQL AST
        3. 输入表
        4. 输出表

        最终形成：

        source_table
            ↓
        task
            ↓
        target_table
        """

        return {
            "node_id": extract_node_id(
                node
            ),
            "node_name": extract_node_name(
                node
            ),
            "node_type": extract_node_type(
                node
            ),
            "sql_count": len(
                sql_candidates
            ),

            # 当前直接保存完整节点详情。
            # 后续分析阶段可以从这里提取更多字段。
            "raw_detail": detail,
        }


def utc_now() -> str:
    """返回当前 UTC 时间。"""

    return datetime.now(
        timezone.utc
    ).isoformat()
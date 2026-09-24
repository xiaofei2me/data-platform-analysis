"""Snapshot 数据导出。"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.progress import track

from .config import WorkspaceSettings, settings
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

        # 本次运行是否存在 Workspace / 节点级失败。
        self.had_failures: bool = False

    def export_all(
        self,
        workspace_id: int | None = None,
    ) -> None:
        """执行 DataWorks + MaxCompute 全量采集。"""

        logger.info(
            "开始执行完整 Snapshot 采集"
        )

        self.export_dataworks(workspace_id)
        self.export_maxcompute()

        # manifest 仅由全量 export 写入。
        if workspace_id is None:
            self.write_manifest()

        logger.info(
            "完整 Snapshot 采集完成"
        )

    def _select_workspaces(
        self,
        workspace_id: int | None,
    ) -> list[WorkspaceSettings]:
        """解析本次要采集的 Workspace 列表。"""

        if workspace_id is None:
            return list(
                settings.dataworks_workspaces
            )

        matched = [
            workspace
            for workspace in (
                settings.dataworks_workspaces
            )
            if workspace.id == workspace_id
        ]

        if not matched:
            raise ValueError(
                f"未配置的 Workspace id：{workspace_id}"
                "（不在 DATAWORKS_WORKSPACES 中）"
            )

        return matched

    def export_dataworks(
        self,
        workspace_id: int | None = None,
    ) -> None:
        """
        顺序采集全部 DataWorks Workspace 的节点、SQL 和基础任务关系。

        每个 Workspace 独立落盘（ADR-0001），
        采集层不做跨 Workspace 合并（ADR-0002）。
        """

        # 校验在任何采集动作之前完成（fail-fast）。
        workspaces = self._select_workspaces(
            workspace_id
        )

        logger.info(
            "开始采集 DataWorks（%s 个 Workspace）",
            len(workspaces),
        )

        index_entries: list[
            dict[str, Any]
        ] = []

        for workspace in workspaces:
            # Workspace 级错误边界：失败不阻断其余 Workspace。
            try:
                entry = (
                    self._export_dataworks_workspace(
                        workspace
                    )
                )

            except Exception as exc:
                logger.exception(
                    "Workspace 采集失败：workspace=%s",
                    workspace.id,
                )

                entry = {
                    "id": workspace.id,
                    "name": workspace.name,
                    "maxcompute_project": (
                        workspace.maxcompute_project
                    ),
                    "status": "failed",
                    "node_count": 0,
                    "failed_node_count": 0,
                    "generated_at": utc_now(),
                    "error": (
                        str(exc)
                        or type(exc).__name__
                    ),
                }

            if entry.get("status") == "failed":
                self.had_failures = True

            if entry.get("failed_node_count"):
                self.had_failures = True

            index_entries.append(entry)

        # 根级 Workspace 注册表（读-改-写 upsert）。
        self._write_workspaces_index(index_entries)

        logger.info(
            "DataWorks 采集完成：%s 个 Workspace",
            len(index_entries),
        )

    def _export_dataworks_workspace(
        self,
        workspace: WorkspaceSettings,
    ) -> dict[str, Any]:
        """
        采集单个 Workspace 并返回其注册表条目。
        """

        base_dir = (
            self.source_dir
            / "dataworks"
            / "workspaces"
            / str(workspace.id)
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

        nodes = self.dataworks.list_nodes(
            workspace.id
        )

        node_index: list[
            dict[str, Any]
        ] = []

        lineage_records: list[
            dict[str, Any]
        ] = []

        failed_nodes: list[
            dict[str, Any]
        ] = []

        for node in track(
            nodes,
            description=(
                f"正在采集 {workspace.name} 节点"
            ),
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
                        workspace.id,
                        node_id,
                    )
                )

            except Exception:
                logger.exception(
                    "获取 DataWorks 节点详情失败：workspace=%s，node_id=%s",
                    workspace.id,
                    node_id,
                )

                failed_nodes.append(
                    {"node_id": node_id}
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
                    "workspace_id": (
                        workspace.id
                    ),
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
                    workspace_id=(
                        workspace.id
                    ),
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
            base_dir / "nodes-index.json",
            {
                "generated_at": utc_now(),
                "workspace": {
                    "id": workspace.id,
                    "name": workspace.name,
                    "maxcompute_project": (
                        workspace.maxcompute_project
                    ),
                },
                "count": len(node_index),
                "nodes": node_index,
                "failed_nodes": failed_nodes,
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
            "Workspace %s 采集完成：%s 个节点",
            workspace.name,
            len(node_index),
        )

        # 采集完整跑完后，以权威节点集合清理幽灵文件。
        self._cleanup_workspace_files(
            nodes_dir=nodes_dir,
            sql_dir=sql_dir,
            authoritative_node_ids={
                node_id
                for node in nodes
                if (node_id := extract_node_id(node))
                is not None
            },
        )

        return {
            "id": workspace.id,
            "name": workspace.name,
            "maxcompute_project": (
                workspace.maxcompute_project
            ),
            "status": "ok",
            "node_count": len(node_index),
            "failed_node_count": len(failed_nodes),
            "generated_at": utc_now(),
        }

    def _cleanup_workspace_files(
        self,
        *,
        nodes_dir: Path,
        sql_dir: Path,
        authoritative_node_ids: set[str],
    ) -> None:
        """
        删除不属于权威节点集合的 nodes / sql 文件。

        权威集合 = 本次 ListNodes 返回的节点 id。
        仅在整个 Workspace 采集完整跑完后调用；
        failed 节点仍在权威集合内，其旧文件不会被删除。
        """

        keep_node_files = {
            f"{safe_filename(node_id)}.json"
            for node_id in authoritative_node_ids
        }

        keep_sql_prefixes = tuple(
            f"{safe_filename(node_id)}_"
            for node_id in authoritative_node_ids
        )

        for path in nodes_dir.glob("*.json"):
            if path.name not in keep_node_files:
                logger.info(
                    "清理幽灵节点文件：%s",
                    path.name,
                )
                path.unlink()

        for path in sql_dir.glob("*.sql"):
            if not path.name.startswith(keep_sql_prefixes):
                logger.info(
                    "清理幽灵 SQL 文件：%s",
                    path.name,
                )
                path.unlink()

    def _write_workspaces_index(
        self,
        entries: list[dict[str, Any]],
    ) -> None:
        """
        写入 Workspace 注册表（upsert 合并）。

        已有且未参与本次采集的条目原样保留；
        本次采集的条目按 id 更新或追加。
        """

        path = (
            self.source_dir
            / "dataworks"
            / "workspaces-index.json"
        )

        merged: dict[int, dict[str, Any]] = {}
        order: list[int] = []

        if path.exists():
            try:
                existing = json.loads(
                    path.read_text(encoding="utf-8")
                )
            except (
                json.JSONDecodeError,
                OSError,
            ):
                logger.warning(
                    "workspaces-index.json 无法解析，将从空注册表重建：%s",
                    path,
                )
                existing = {}

            for entry in existing.get(
                "workspaces", []
            ):
                entry_id = entry.get("id")
                if entry_id is not None:
                    merged[entry_id] = entry
                    order.append(entry_id)

        for entry in entries:
            entry_id = entry["id"]
            if entry_id not in merged:
                order.append(entry_id)
            merged[entry_id] = entry

        write_json(
            path,
            {
                "generated_at": utc_now(),
                "workspaces": [
                    merged[entry_id]
                    for entry_id in order
                ],
            },
            overwrite=(
                settings.export_overwrite
            ),
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
                    "workspaces": [
                        {
                            "id": workspace.id,
                            "name": workspace.name,
                            "maxcompute_project": (
                                workspace.maxcompute_project
                            ),
                        }
                        for workspace in (
                            settings.dataworks_workspaces
                        )
                    ],
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
        workspace_id: int,
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
            "workspace_id": workspace_id,
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
        UTC
    ).isoformat()
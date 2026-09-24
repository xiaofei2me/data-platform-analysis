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
    extract_file_content,
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


def _build_snapshot_filename(
    entity_id: str,
    entity_name: str,
    *,
    suffix: str,
) -> str:
    """
    构建 Snapshot 文件名。

    格式：

        <id>__<name>.<suffix>

    例如：

        505550697__tb_ec_paid_media_tm_live_streaming_df.json
        505550697__tb_ec_paid_media_tm_live_streaming_df.sql

    ID 用于保证稳定引用；
    Name 用于提高 Snapshot 的人工可读性。
    """

    safe_id = safe_filename(entity_id)
    safe_name = safe_filename(entity_name)

    if not safe_name:
        safe_name = safe_id

    return f"{safe_id}__{safe_name}.{suffix}"


def _workspace_identity(
    workspace: WorkspaceSettings,
) -> dict[str, Any]:
    """返回 Workspace 身份信息。"""

    return {
        "id": workspace.id,
        "name": workspace.name,
        "maxcompute_project": workspace.maxcompute_project,
    }


def _workspace_entry(
    workspace: WorkspaceSettings,
    *,
    status: str,
    file_count: int,
    failed_file_count: int,
    error: str | None = None,
) -> dict[str, Any]:
    """构建 workspaces-index 注册表条目。"""

    entry: dict[str, Any] = {
        **_workspace_identity(workspace),
        "status": status,
        "file_count": file_count,
        "failed_file_count": failed_file_count,
        "generated_at": utc_now(),
    }

    if error is not None:
        entry["error"] = error

    return entry


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

        # 本次运行是否存在 Workspace / File 级失败。
        self.had_failures: bool = False

    def export_all(
        self,
        workspace_id: int | None = None,
    ) -> None:
        """执行 DataWorks + MaxCompute 全量采集。"""

        logger.info("开始执行完整 Snapshot 采集")

        self.export_dataworks(workspace_id)
        self.export_maxcompute()

        # manifest 仅由全量 export 写入。
        if workspace_id is None:
            self.write_manifest()

        logger.info("完整 Snapshot 采集完成")

    def export_dataworks(
        self,
        workspace_id: int | None = None,
    ) -> None:
        """
        顺序采集全部 DataWorks Workspace 的文件、Content
        和基础任务关系。

        每个 Workspace 独立落盘（ADR-0001），
        采集层不做跨 Workspace 合并（ADR-0002）。
        """

        # 校验在任何采集动作之前完成（fail-fast）。
        workspaces = settings.select_workspaces(workspace_id)

        logger.info(
            "开始采集 DataWorks（%s 个 Workspace）",
            len(workspaces),
        )

        index_entries: list[dict[str, Any]] = []

        for workspace in workspaces:
            # Workspace 级错误边界：
            # 单个 Workspace 失败不阻断其余 Workspace。
            try:
                entry = self._export_dataworks_workspace(
                    workspace
                )
            except Exception as exc:
                logger.exception(
                    "Workspace 采集失败：workspace=%s",
                    workspace.id,
                )

                entry = _workspace_entry(
                    workspace,
                    status="failed",
                    file_count=0,
                    failed_file_count=0,
                    error=str(exc) or type(exc).__name__,
                )

            if entry.get("status") == "failed":
                self.had_failures = True

            if entry.get("failed_file_count"):
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

        采集流程：

            ListFiles
                ↓
            GetFile
                ↓
            raw file snapshot
                +
            Content snapshot
                +
            task lineage
                ↓
            cleanup stale files
        """

        base_dir = (
            self.source_dir
            / "dataworks"
            / "workspaces"
            / str(workspace.id)
        )

        files_dir = base_dir / "files"
        sql_dir = base_dir / "sql"
        lineage_dir = base_dir / "lineage"

        ensure_dir(files_dir)
        ensure_dir(sql_dir)
        ensure_dir(lineage_dir)

        # ======================================================
        # 1. 获取 Workspace 当前文件列表
        # ======================================================
        #
        # ListFiles 成功返回的数据集合是当前 Workspace 的
        # 权威 File ID 集合。
        #
        # 如果 ListFiles 本身失败，会直接抛出异常，
        # 外层 Workspace error boundary 会接管。
        #
        files = self.dataworks.list_files(workspace.id)

        file_index: list[dict[str, Any]] = []
        lineage_records: list[dict[str, Any]] = []
        failed_files: list[dict[str, Any]] = []

        # ======================================================
        # 当前 Workspace 的权威 File 快照
        # ======================================================
        #
        # file_id -> 当前 raw JSON 文件名
        #
        # 例如：
        #
        # {
        #     "505550697":
        #         "505550697__tb_xxx.json"
        # }
        #
        # 该集合来自成功的 ListFiles。
        authoritative_files: dict[str, str] = {}

        # ======================================================
        # 当前成功 GetFile 产生的 SQL 文件
        # ======================================================
        #
        # 只有 GetFile 成功，并且 Content 非空时，
        # 才会加入这个集合。
        #
        # cleanup 时可以据此判断旧 SQL 是否需要删除。
        authoritative_sql_files: set[str] = set()

        # ======================================================
        # GetFile 失败的 File ID
        # ======================================================
        #
        # GetFile 失败时：
        #
        # - 保留旧 JSON
        # - 保留旧 SQL
        #
        # 因此 cleanup 时必须知道哪些 File 失败了。
        failed_file_ids: set[str] = set()

        # ======================================================
        # 2. 逐个获取 File Detail
        # ======================================================

        for file in track(
            files,
            description=f"正在采集 {workspace.name} 文件",
        ):
            file_id = extract_node_id(file)

            if file_id is None:
                logger.warning(
                    "发现没有 File ID 的文件，跳过：%s",
                    file,
                )
                continue

            file_name = extract_node_name(file)
            file_type = extract_node_type(file)

            # ==================================================
            # File 属于当前 ListFiles 权威集合。
            # ==================================================

            raw_filename = _build_snapshot_filename(
                file_id,
                file_name,
                suffix="json",
            )

            authoritative_files[file_id] = raw_filename

            # ==================================================
            # 获取 File 完整详情
            # ==================================================

            try:
                detail = self.dataworks.get_file(
                    workspace.id,
                    file_id,
                )

            except Exception as exc:
                logger.exception(
                    "获取 DataWorks 文件详情失败："
                    "workspace=%s，file_id=%s",
                    workspace.id,
                    file_id,
                )

                failed_file_ids.add(file_id)

                failed_files.append(
                    {
                        "file_id": file_id,
                        "file_name": file_name,
                        "error": str(exc) or type(exc).__name__,
                    }
                )

                # GetFile 失败：
                #
                # 1. 不覆盖旧 JSON
                # 2. 不生成新的 SQL
                # 3. cleanup 时保留旧 JSON
                # 4. cleanup 时保留旧 SQL
                continue

            # ==================================================
            # 3. 保存原始 File JSON
            # ==================================================

            raw_path = files_dir / raw_filename

            write_json(
                raw_path,
                detail,
                overwrite=settings.export_overwrite,
            )

            # ==================================================
            # 4. 提取 File Content
            # ==================================================

            sql_content = extract_file_content(detail)

            sql_file: str | None = None

            if sql_content is not None:
                sql_filename = _build_snapshot_filename(
                    file_id,
                    file_name,
                    suffix="sql",
                )

                sql_path = sql_dir / sql_filename

                write_sql(
                    sql_path,
                    sql_content,
                    overwrite=settings.export_overwrite,
                )

                authoritative_sql_files.add(
                    sql_filename
                )

                sql_file = str(
                    sql_path.relative_to(
                        self.source_dir
                    )
                )

            # ==================================================
            # 5. 保存 File 索引
            # ==================================================

            file_index.append(
                {
                    "workspace_id": workspace.id,
                    "file_id": file_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "raw_file": str(
                        raw_path.relative_to(
                            self.source_dir
                        )
                    ),
                    "sql_file": sql_file,
                }
            )

            # ==================================================
            # 6. 保存基础任务关系
            # ==================================================

            lineage_records.append(
                self._build_lineage_record(
                    workspace_id=workspace.id,
                    file=file,
                    detail=detail,
                    has_sql=sql_content is not None,
                )
            )

        # ======================================================
        # 7. 保存 File 索引
        # ======================================================

        write_json(
            base_dir / "files-index.json",
            {
                "generated_at": utc_now(),
                "workspace": _workspace_identity(workspace),
                "count": len(file_index),
                "files": file_index,
                "failed_files": failed_files,
            },
            overwrite=settings.export_overwrite,
        )

        # ======================================================
        # 8. 保存基础任务关系
        # ======================================================

        write_jsonl(
            lineage_dir / "task-lineage.jsonl",
            lineage_records,
            overwrite=settings.export_overwrite,
        )

        logger.info(
            "Workspace %s 采集完成：%s 个文件，%s 个失败",
            workspace.name,
            len(file_index),
            len(failed_files),
        )

        # ======================================================
        # 9. 清理旧 Snapshot
        # ======================================================
        #
        # 只有 ListFiles 成功完成后才会走到这里。
        #
        # 因此 authoritative_files 是可信的。
        #
        # 如果 ListFiles 失败：
        #
        #   self.dataworks.list_files(...)
        #
        # 会直接抛异常，不会执行 cleanup。
        #
        self._cleanup_workspace_files(
            files_dir=files_dir,
            sql_dir=sql_dir,
            authoritative_files=authoritative_files,
            authoritative_sql_files=authoritative_sql_files,
            failed_file_ids=failed_file_ids,
        )

        return _workspace_entry(
            workspace,
            status="ok",
            file_count=len(file_index),
            failed_file_count=len(failed_files),
        )

    def _cleanup_workspace_files(
        self,
        *,
        files_dir: Path,
        sql_dir: Path,
        authoritative_files: dict[str, str],
        authoritative_sql_files: set[str],
        failed_file_ids: set[str],
    ) -> None:
        """
        清理 Workspace Snapshot 中已经失效的文件。

        JSON 清理规则：

        1. File ID 已经不存在
           -> 删除旧 JSON

        2. File ID 仍然存在，但 FileName 已经变化
           -> 删除旧 JSON

        3. File ID + FileName 都匹配
           -> 保留

        GetFile 失败：

        1. 保留旧 JSON
        2. 保留旧 SQL

        SQL 清理规则：

        1. File ID 已经不存在
           -> 删除旧 SQL

        2. File ID 当前存在且 GetFile 成功
           -> 只保留当前 SQL 文件

        3. File ID 当前存在但 GetFile 失败
           -> 保留该 File 的旧 SQL

        这样可以保证：

        ListFiles 成功 + GetFile 成功
            -> Snapshot 与当前 DataWorks 状态同步

        ListFiles 成功 + GetFile 失败
            -> 保留上一次可用 Snapshot

        ListFiles 失败
            -> 整个 Workspace 不执行 cleanup
        """

        # ======================================================
        # 1. 清理 JSON Snapshot
        # ======================================================

        keep_file_names = set(
            authoritative_files.values()
        )

        for path in files_dir.glob("*.json"):
            if path.name in keep_file_names:
                continue

            logger.info(
                "清理过期 DataWorks 文件 Snapshot：%s",
                path.name,
            )

            path.unlink()

        # ======================================================
        # 2. 清理 SQL Snapshot
        # ======================================================
        #
        # SQL 文件格式：
        #
        #   <file_id>__<file_name>.sql
        #
        # 需要根据 File ID 找到它属于哪个 DataWorks File。
        #
        # 当前文件 ID 使用 safe_filename 后作为前缀。
        #

        for path in sql_dir.glob("*.sql"):
            file_id = self._extract_file_id_from_sql_filename(
                path.name,
                authoritative_files,
            )

            # --------------------------------------------------
            # 无法匹配当前 File ID
            #
            # 说明该 SQL 对应的 File 已经不存在，
            # 属于幽灵 Snapshot。
            # --------------------------------------------------

            if file_id is None:
                logger.info(
                    "清理幽灵 SQL 文件：%s",
                    path.name,
                )
                path.unlink()
                continue

            # --------------------------------------------------
            # GetFile 失败
            #
            # 不确定当前 DataWorks 内容是否发生变化，
            # 所以保留旧 SQL。
            # --------------------------------------------------

            if file_id in failed_file_ids:
                logger.debug(
                    "保留 GetFile 失败的旧 SQL Snapshot：%s",
                    path.name,
                )
                continue

            # --------------------------------------------------
            # GetFile 成功
            #
            # 当前 SQL 不在 authoritative_sql_files 中，
            # 说明：
            #
            # - Content 从有变成无
            # - FileName 发生变化
            # - 旧 SQL 已经不存在
            #
            # 因此可以安全删除。
            # --------------------------------------------------

            if path.name not in authoritative_sql_files:
                logger.info(
                    "清理过期 SQL Snapshot：%s",
                    path.name,
                )
                path.unlink()

    @staticmethod
    def _extract_file_id_from_sql_filename(
        filename: str,
        authoritative_files: dict[str, str],
    ) -> str | None:
        """
        根据 SQL Snapshot 文件名识别对应的 File ID。

        当前文件名格式：

            <file_id>__<file_name>.sql

        例如：

            505550697__tb_xxx.sql

        返回当前 authoritative_files 中匹配的 File ID。

        如果找不到，则返回 None。
        """

        for file_id in authoritative_files:
            prefix = (
                f"{safe_filename(file_id)}__"
            )

            if filename.startswith(prefix):
                return file_id

        return None

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
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                json.JSONDecodeError,
                OSError,
            ):
                logger.warning(
                    "workspaces-index.json 无法解析，"
                    "将从空注册表重建：%s",
                    path,
                )
                existing = {}

            for entry in existing.get(
                "workspaces",
                [],
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
            overwrite=settings.export_overwrite,
        )

    def export_maxcompute(self) -> None:
        """采集 MaxCompute 表结构和元数据。"""

        logger.info("开始采集 MaxCompute")

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

        tables = self.maxcompute.list_tables()

        table_index: list[dict[str, Any]] = []

        for table in track(
            tables,
            description="正在获取 MaxCompute 表",
        ):
            table_name = table.name

            try:
                metadata = (
                    self.maxcompute.get_table_metadata(
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
                overwrite=settings.export_overwrite,
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
            metadata_dir / "tables-index.json",
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
            overwrite=settings.export_overwrite,
        )

        logger.info(
            "MaxCompute 采集完成：%s 张表",
            len(table_index),
        )

    def write_manifest(self) -> None:
        """生成 Snapshot 清单。"""

        manifest = {
            "generated_at": utc_now(),
            "tool": "data-platform-analysis",
            "version": "0.1.0",
            "sources": {
                "dataworks": {
                    "api_version": "2020-05-18",
                    "region": (
                        settings.dataworks_region
                    ),
                    "workspaces": [
                        _workspace_identity(workspace)
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
            self.source_dir / "manifest.json",
            manifest,
            overwrite=settings.export_overwrite,
        )

    @staticmethod
    def _build_lineage_record(
        *,
        workspace_id: int,
        file: dict[str, Any],
        detail: dict[str, Any],
        has_sql: bool,
    ) -> dict[str, Any]:
        """
        构建基础任务关系记录。

        注意：

        当前这里只保存 DataWorks 文件级信息，
        还不是最终的表级血缘。

        后续需要结合：

        1. DataWorks 任务依赖
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
            "file_id": extract_node_id(file),
            "file_name": extract_node_name(file),
            "file_type": extract_node_type(file),
            "has_sql": has_sql,
            # 当前直接保存完整 File 详情。
            # 后续分析阶段可以从这里提取更多字段。
            "raw_detail": detail,
        }


def utc_now() -> str:
    """返回当前 UTC 时间。"""
    return datetime.now(UTC).isoformat()
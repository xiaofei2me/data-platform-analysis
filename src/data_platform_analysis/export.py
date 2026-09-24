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
    extract_file_content,
    extract_file_id,
    extract_file_name,
    extract_file_type,
    extract_use_type,
)
from .dataworks_types import DataWorksFileType, get_file_type
from .io_utils import (
    ensure_dir,
    safe_filename,
    write_json,
    write_jsonl,
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
        505550698__sync_xxx.json

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
    """构建 Workspace 注册表条目。"""

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


def _write_content(
    path: Path,
    content: str,
    *,
    overwrite: bool,
) -> None:
    """
    写入 File Content Snapshot。

    Content 可能是：

    - SQL
    - JSON
    - Python
    - Shell
    - 其他文本

    因此这里不再使用 write_sql()。
    """

    if path.exists() and not overwrite:
        logger.debug(
            "Content Snapshot 已存在且禁止覆盖：%s",
            path,
        )
        return

    ensure_dir(path.parent)

    path.write_text(
        content,
        encoding="utf-8",
    )


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
        顺序采集全部 DataWorks Workspace 的 File、Content
        和基础任务关系。

        每个 Workspace 独立落盘（ADR-0001），
        采集层不做跨 Workspace 合并（ADR-0002）。
        """

        # 校验在任何采集动作之前完成。
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
            raw File snapshot
                +
            Content snapshot
                +
            task lineage
                ↓
            cleanup stale snapshots
        """

        base_dir = (
            self.source_dir
            / "dataworks"
            / "workspaces"
            / str(workspace.id)
        )

        files_dir = base_dir / "files"

        # File Content 不再限定为 SQL。
        content_dir = base_dir / "content"

        lineage_dir = base_dir / "lineage"

        ensure_dir(files_dir)
        ensure_dir(content_dir)
        ensure_dir(lineage_dir)

        # ======================================================
        # 1. 获取 Workspace 当前 File 列表
        # ======================================================

        files = self.dataworks.list_files(
            workspace.id
        )

        file_index: list[dict[str, Any]] = []
        lineage_records: list[dict[str, Any]] = []
        failed_files: list[dict[str, Any]] = []

        # ======================================================
        # 当前 Workspace 的权威 File 快照
        # ======================================================
        #
        # file_id -> 当前 raw JSON 文件名
        #

        authoritative_files: dict[str, str] = {}

        # ======================================================
        # 当前成功 GetFile 产生的 Content 文件
        # ======================================================

        authoritative_content_files: set[str] = set()

        # ======================================================
        # GetFile 失败的 File ID
        # ======================================================

        failed_file_ids: set[str] = set()

        # ======================================================
        # 2. 逐个获取 File Detail
        # ======================================================

        for file in track(
            files,
            description=f"正在采集 {workspace.name} 文件",
        ):
            file_id = extract_file_id(file)

            if file_id is None:
                logger.warning(
                    "发现没有 File ID 的文件，跳过：%s",
                    file,
                )
                continue

            file_name = extract_file_name(file)

            if not file_name:
                file_name = file_id

            # --------------------------------------------------
            # FileType 直接来自 ListFiles。
            #
            # 例如：
            #
            # FileType = 10
            #     -> ODPS SQL
            #     -> .sql
            #
            # FileType = 23
            #     -> Data Integration
            #     -> .json
            # --------------------------------------------------

            file_type = extract_file_type(file)
            use_type = extract_use_type(file)

            # ==================================================
            # File 属于当前 ListFiles 权威集合
            # ==================================================

            raw_filename = _build_snapshot_filename(
                file_id,
                file_name,
                suffix="json",
            )

            authoritative_files[file_id] = raw_filename

            # ==================================================
            # File Type 分类
            # ==================================================

            file_type_info = get_file_type(
                file_type
            )

            logger.debug(
                "DataWorks File："
                "workspace=%s，"
                "file_id=%s，"
                "file_name=%s，"
                "use_type=%s，"
                "file_type=%s，"
                "file_type_name=%s，"
                "task_type=%s，"
                "category=%s，"
                "content_format=%s，"
                "extension=%s",
                workspace.id,
                file_id,
                file_name,
                use_type,
                file_type,
                file_type_info.name,
                file_type_info.task_type,
                file_type_info.category,
                file_type_info.content_format,
                file_type_info.extension,
            )

            # ==================================================
            # 对未知 FileType 打出 warning
            # ==================================================

            if file_type_info.category == "unknown":
                logger.warning(
                    "发现未知 DataWorks FileType："
                    "workspace=%s，"
                    "file_id=%s，"
                    "file_name=%s，"
                    "file_type=%s",
                    workspace.id,
                    file_id,
                    file_name,
                    file_type,
                )

            # ==================================================
            # 获取 File 完整详情
            # ==================================================

            try:
                detail = self.dataworks.get_file(
                    workspace.id,
                    int(file_id),
                )

            except Exception as exc:
                logger.exception(
                    "获取 DataWorks 文件详情失败："
                    "workspace=%s，file_id=%s，file_name=%s",
                    workspace.id,
                    file_id,
                    file_name,
                )

                failed_file_ids.add(file_id)

                failed_files.append(
                    {
                        "file_id": file_id,
                        "file_name": file_name,
                        "file_type": file_type,
                        "error": (
                            str(exc)
                            or type(exc).__name__
                        ),
                    }
                )

                # GetFile 失败：
                #
                # 1. 不覆盖旧 JSON
                # 2. 不生成新的 Content
                # 3. cleanup 时保留旧 JSON
                # 4. cleanup 时保留旧 Content
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

            content = extract_file_content(
                detail
            )

            content_file: str | None = None

            if content is not None and content != "":
                # ------------------------------------------------
                # 根据 ListFiles.FileType 决定 Content 扩展名。
                #
                # 不根据 Content 内容猜测类型。
                # ------------------------------------------------

                extension = (
                    file_type_info.extension.lstrip(".")
                )

                content_filename = _build_snapshot_filename(
                    file_id,
                    file_name,
                    suffix=extension,
                )

                content_path = (
                    content_dir / content_filename
                )

                _write_content(
                    content_path,
                    content,
                    overwrite=(
                        settings.export_overwrite
                    ),
                )

                authoritative_content_files.add(
                    content_filename
                )

                content_file = str(
                    content_path.relative_to(
                        self.source_dir
                    )
                )

                logger.debug(
                    "保存 File Content："
                    "workspace=%s，"
                    "file_id=%s，"
                    "file_type=%s，"
                    "format=%s，"
                    "path=%s",
                    workspace.id,
                    file_id,
                    file_type,
                    file_type_info.content_format,
                    content_path,
                )

            else:
                logger.debug(
                    "File 没有 Content："
                    "workspace=%s，"
                    "file_id=%s，"
                    "file_type=%s",
                    workspace.id,
                    file_id,
                    file_type,
                )

            # ==================================================
            # 5. 保存 File 索引
            # ==================================================

            file_index.append(
                {
                    "workspace_id": workspace.id,
                    "file_id": file_id,
                    "file_name": file_name,
                    "use_type": use_type,
                    "file_type": file_type,
                    "task_type": (
                        file_type_info.task_type
                    ),
                    "file_type_name": (
                        file_type_info.name
                    ),
                    "category": (
                        file_type_info.category
                    ),
                    "content_format": (
                        file_type_info.content_format
                    ),
                    "raw_file": str(
                        raw_path.relative_to(
                            self.source_dir
                        )
                    ),
                    "content_file": content_file,
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
                    file_type_info=file_type_info,
                    content_file=content_file,
                )
            )

        # ======================================================
        # 7. 保存 File 索引
        # ======================================================

        write_json(
            base_dir / "files-index.json",
            {
                "generated_at": utc_now(),
                "workspace": _workspace_identity(
                    workspace
                ),
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

        self._cleanup_workspace_files(
            files_dir=files_dir,
            content_dir=content_dir,
            authoritative_files=authoritative_files,
            authoritative_content_files=(
                authoritative_content_files
            ),
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
        content_dir: Path,
        authoritative_files: dict[str, str],
        authoritative_content_files: set[str],
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
        2. 保留旧 Content

        Content 清理规则：

        1. File ID 已经不存在
           -> 删除旧 Content

        2. File ID 当前存在且 GetFile 成功
           -> 只保留当前 Content

        3. File ID 当前存在但 GetFile 失败
           -> 保留该 File 的旧 Content

        4. Content 从有变成无
           -> 删除旧 Content
        """

        # ======================================================
        # 1. 清理 JSON File Snapshot
        # ======================================================

        keep_file_names = set(
            authoritative_files.values()
        )

        for path in files_dir.glob("*.json"):
            if path.name in keep_file_names:
                continue

            logger.info(
                "清理过期 DataWorks File Snapshot：%s",
                path.name,
            )

            path.unlink()

        # ======================================================
        # 2. 清理 Content Snapshot
        # ======================================================

        for path in content_dir.iterdir():
            if not path.is_file():
                continue

            file_id = (
                self._extract_file_id_from_content_filename(
                    path.name,
                    authoritative_files,
                )
            )

            # --------------------------------------------------
            # 无法匹配当前 File ID
            #
            # 说明该 Content 对应的 File 已经不存在。
            # --------------------------------------------------

            if file_id is None:
                logger.info(
                    "清理幽灵 Content 文件：%s",
                    path.name,
                )

                path.unlink()
                continue

            # --------------------------------------------------
            # GetFile 失败
            #
            # 不确定当前 DataWorks 内容是否发生变化，
            # 所以保留旧 Content。
            # --------------------------------------------------

            if file_id in failed_file_ids:
                logger.debug(
                    "保留 GetFile 失败的旧 Content Snapshot：%s",
                    path.name,
                )
                continue

            # --------------------------------------------------
            # GetFile 成功
            #
            # 当前 Content 不在 authoritative_content_files 中，
            # 说明：
            #
            # - Content 从有变成无
            # - FileName 发生变化
            # - FileType 发生变化
            # - Content extension 发生变化
            #
            # 因此可以安全删除。
            # --------------------------------------------------

            if (
                path.name
                not in authoritative_content_files
            ):
                logger.info(
                    "清理过期 Content Snapshot：%s",
                    path.name,
                )

                path.unlink()

    @staticmethod
    def _extract_file_id_from_content_filename(
        filename: str,
        authoritative_files: dict[str, str],
    ) -> str | None:
        """
        根据 Content Snapshot 文件名识别对应的 File ID。

        当前文件名格式：

            <file_id>__<file_name>.<extension>

        例如：

            505550697__tb_xxx.sql
            505550698__sync_xxx.json
            505550699__xxx.py

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
        file_type_info: DataWorksFileType,
        content_file: str | None,
    ) -> dict[str, Any]:
        """
        构建基础任务关系记录。

        当前这里只保存 DataWorks File / Task 级信息，
        还不是最终的表级血缘。

        后续需要结合：

        1. DataWorks 任务依赖
        2. SQL AST
        3. 数据集成 Reader / Writer
        4. 输入表
        5. 输出表

        最终形成：

            source_table
                ↓
              task
                ↓
            target_table
        """

        return {
            "workspace_id": workspace_id,

            # --------------------------------------------------
            # File 基础身份
            # --------------------------------------------------

            "file_id": extract_file_id(file),
            "file_name": extract_file_name(file),
            "use_type": extract_use_type(file),
            "file_type": extract_file_type(file),

            # --------------------------------------------------
            # File Type 语义
            # --------------------------------------------------

            "task_type": file_type_info.task_type,
            "file_type_name": file_type_info.name,
            "category": file_type_info.category,
            "content_format": (
                file_type_info.content_format
            ),

            # --------------------------------------------------
            # Content Snapshot
            # --------------------------------------------------

            "content_file": content_file,

            # --------------------------------------------------
            # 原始 GetFile Detail
            #
            # 后续分析阶段可以从这里提取：
            #
            # - NodeId
            # - NodeConfiguration
            # - InputList
            # - OutputList
            # - DependentNodeIdList
            # - DependentType
            #
            # --------------------------------------------------

            "raw_detail": detail,
        }


def utc_now() -> str:
    """返回当前 UTC 时间。"""

    return datetime.now(UTC).isoformat()
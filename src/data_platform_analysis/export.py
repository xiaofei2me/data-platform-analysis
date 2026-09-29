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
    extract_node_id,
)
from .dataworks_types import get_file_type
from .io_utils import (
    ensure_dir,
    safe_filename,
    write_json,
)
from .maxcompute import MaxComputeClient

logger = logging.getLogger(__name__)


def utc_now() -> str:
    """返回当前 UTC 时间。"""

    return datetime.now(UTC).isoformat()


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
    }


def _workspace_entry(
    workspace: WorkspaceSettings,
    *,
    status: str,
    file_count: int,
    failed_file_count: int,
    error: str | None = None,
) -> dict[str, Any]:
    """构建 DataWorks Workspace 注册表条目。"""

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


def _log_limit_mode(
    limit: int | None,
    *,
    scope: str,
) -> None:
    """
    输出采集限制模式日志。

    Cleanup 安全原则：

        limit is None     -> 允许 Cleanup
        limit is not None -> 绝对禁止 Cleanup

    原因：limit 返回的是部分集合，
    不具有完整集合的权威性，
    不能据此判断远端对象已经删除。
    """

    if limit is None:
        return

    logger.info(
        "%s 采集限制模式：limit=%s，每个 Workspace 最多 %s 个对象，Cleanup=SKIP",
        scope,
        limit,
        limit,
    )


class SnapshotExporter:
    """
    Snapshot 导出器。

    当前版本只负责：

        DataWorks + MaxCompute
                ↓
            本地 Snapshot

    不在这里做：

    - DWS 分析
    - Semantic Layer
    - SQLGlot
    - LLM 分析
    - Task Dependency 派生
    - Table Lineage 派生
    - Column Lineage 派生

    这些属于后续 Analysis 阶段。
    """

    def __init__(
        self,
        source_dir: Path | None = None,
    ) -> None:
        self.source_dir = source_dir if source_dir is not None else settings.source_dir

        # DataWorks Client 不绑定 Workspace。
        # Workspace ID 在调用方法时传入。
        self.dataworks = DataWorksClient()

        # MaxCompute Client 必须绑定 Project。
        # 因此每个 Workspace 在采集时独立创建 Client。
        self.had_failures: bool = False

    # ==========================================================
    # Public API
    # ==========================================================

    def export_all(
        self,
        workspace_id: int | None = None,
        limit: int | None = None,
    ) -> None:
        """
        执行 DataWorks + MaxCompute 完整采集。

        workspace_id 为 None：
            采集全部 Workspace。

        workspace_id 不为 None：
            只采集指定 Workspace。

        limit 为 None：
            全量采集，允许 Snapshot Cleanup。

        limit 不为 None：
            采集限制模式，每个 Workspace 最多处理
            limit 个 File 和 limit 个 Table，
            并禁止 Snapshot Cleanup。

        manifest.json 仅在完整 Workspace 采集时生成。

        export_all 只做编排：

            export_all()
                ↓
            export_dataworks()
            export_maxcompute()
                ↓
            write_manifest()

        DataWorks / MaxCompute 的采集逻辑分别由两个子方法负责，
        这里不重复实现。
        """

        # 先校验 Workspace 选择，配置错误时在任何采集开始前失败。
        workspaces = settings.select_workspaces(workspace_id)

        logger.info(
            "开始执行完整 Snapshot 采集：%s 个 Workspace",
            len(workspaces),
        )

        self.export_dataworks(
            workspace_id=workspace_id,
            limit=limit,
        )

        self.export_maxcompute(
            workspace_id=workspace_id,
            limit=limit,
        )

        # manifest 仅由完整 export 写入。
        if workspace_id is None:
            self.write_manifest()

        logger.info(
            "完整 Snapshot 采集完成：%s 个 Workspace",
            len(workspaces),
        )

    def export_dataworks(
        self,
        workspace_id: int | None = None,
        limit: int | None = None,
    ) -> None:
        """
        采集 DataWorks。

        workspace_id 为 None：
            采集全部 Workspace。

        workspace_id 不为 None：
            只采集指定 Workspace。

        limit 不为 None：
            每个 Workspace 最多采集 limit 个 File，
            并禁止 Snapshot Cleanup。
        """

        workspaces = settings.select_workspaces(workspace_id)

        logger.info(
            "开始采集 DataWorks：%s 个 Workspace",
            len(workspaces),
        )

        _log_limit_mode(limit, scope="DataWorks")

        index_entries: list[dict[str, Any]] = []

        for workspace in workspaces:
            try:
                entry = self._export_dataworks_workspace(
                    workspace,
                    limit=limit,
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
                    error=(str(exc) or type(exc).__name__),
                )

                self.had_failures = True

            if entry.get("status") == "failed":
                self.had_failures = True

            if entry.get("failed_file_count"):
                self.had_failures = True

            index_entries.append(entry)

        self._write_workspaces_index(index_entries)

        logger.info(
            "DataWorks 采集完成：%s 个 Workspace",
            len(index_entries),
        )

    def export_maxcompute(
        self,
        workspace_id: int | None = None,
        limit: int | None = None,
    ) -> None:
        """
        采集 MaxCompute。

        workspace_id 为 None：
            采集全部 Workspace。

        workspace_id 不为 None：
            只采集指定 Workspace。

        limit 不为 None：
            每个 Workspace 最多采集 limit 个 Table，
            并禁止 Snapshot Cleanup。
        """

        workspaces = settings.select_workspaces(workspace_id)

        logger.info(
            "开始采集 MaxCompute：%s 个 Workspace",
            len(workspaces),
        )

        _log_limit_mode(limit, scope="MaxCompute")

        for workspace in workspaces:
            # --------------------------------------------------
            # Workspace 级错误边界：
            #
            # 单个 Workspace 的 MaxCompute 采集失败
            # （客户端初始化、写盘、元数据读取等）
            # 不能阻断其他 Workspace，
            # 也不能影响 manifest / index 的生成。
            #
            # ListTables / GetTable 失败已在
            # _export_maxcompute_workspace 内部处理，
            # 这里兜住其余异常。
            # --------------------------------------------------
            try:
                self._export_maxcompute_workspace(
                    workspace,
                    limit=limit,
                )

            except Exception:
                logger.exception(
                    "MaxCompute Workspace 采集失败：workspace=%s，project=%s",
                    workspace.id,
                    workspace.name,
                )

                self.had_failures = True

        logger.info(
            "MaxCompute 采集完成：%s 个 Workspace",
            len(workspaces),
        )

    # ==========================================================
    # DataWorks
    # ==========================================================

    def _export_dataworks_workspace(
        self,
        workspace: WorkspaceSettings,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        采集单个 DataWorks Workspace。

        采集流程：

            ListFiles
                ↓
            GetFile
                ↓
            Raw File Snapshot
                +
            Content Snapshot
                ↓
            files-index.json
                ↓
            清理失效 Snapshot

        limit 不为 None：

            ListFiles 只返回前 limit 个 File，
            并跳过最后一步 Cleanup。

        Collection 阶段只保存 Raw / Content。
        不在这里生成派生 Task Lineage。
        """

        base_dir = self.source_dir / "dataworks" / "workspaces" / str(workspace.id)

        files_dir = base_dir / "files"
        content_dir = base_dir / "content"

        ensure_dir(files_dir)
        ensure_dir(content_dir)

        # ======================================================
        # 1. 获取当前 Workspace 的权威 File 列表
        # ======================================================

        files = self.dataworks.list_files(workspace.id, limit=limit)

        # ======================================================
        # 保存 ListFiles 最终 File Inventory Snapshot
        # files 已经经过：
        # - 多页分页
        # - 多 UseType 合并
        # - limit 截断
        #
        # 因此这里保存的是当前 Workspace 本次采集看到的
        # 最终 File 集合，而不是单个 API Page。
        # ======================================================
        write_json(
            base_dir / "files-list.json",
            {
                "generated_at": utc_now(),
                "workspace": _workspace_identity(workspace),
                "limit": limit,
                "count": len(files),
                "complete": limit is None,
                "use_types": settings.dataworks_use_types or None,
                "files": files,
            },
            overwrite=settings.export_overwrite,
        )

        file_index: list[dict[str, Any]] = []
        failed_files: list[dict[str, Any]] = []

        # ======================================================
        # 当前 Workspace 的权威 File Snapshot
        # ======================================================

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
            node_id = extract_node_id(file)

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
            # 不根据 Content 猜测类型。
            # --------------------------------------------------

            file_type = extract_file_type(file)
            use_type = extract_use_type(file)

            # ==================================================
            # File Type 分类
            # ==================================================

            file_type_info = get_file_type(file_type)

            logger.debug(
                "DataWorks File："
                "workspace=%s，"
                "file_id=%s，"
                "file_name=%s，"
                "node_id=%s，"
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
                node_id,
                use_type,
                file_type,
                file_type_info.name,
                file_type_info.task_type,
                file_type_info.category,
                file_type_info.content_format,
                file_type_info.extension,
            )

            # ==================================================
            # 未知 FileType
            # ==================================================
            if file_type_info.category == "unknown":
                logger.warning(
                    "发现未知 DataWorks FileType："
                    "workspace=%s，"
                    "file_id=%s，"
                    "file_name=%s，"
                    "node_id=%s，"
                    "file_type=%s",
                    workspace.id,
                    file_id,
                    file_name,
                    node_id,
                    file_type,
                )

            # ==================================================
            # 获取 File 完整详情
            # ==================================================

            try:
                detail = self.dataworks.get_file(
                    workspace.id, int(file_id),
                )
            except Exception as exc:
                logger.exception(
                    "获取 DataWorks 文件详情失败：workspace=%s，file_id=%s，file_name=%s, node_id=%s",
                    workspace.id,
                    file_id,
                    file_name,
                    node_id,
                )

                failed_file_ids.add(file_id)

                failed_files.append(
                    {
                        "file_id": file_id,
                        "file_name": file_name,
                        "node_id": node_id,
                        "file_type": file_type,
                        "error": (str(exc) or type(exc).__name__),
                    }
                )

                # GetFile 失败：
                #
                # 1. 不覆盖旧 JSON
                # 2. 不生成新的 Content
                # 3. cleanup 保留旧 JSON
                # 4. cleanup 保留旧 Content
                continue

            # ==================================================
            # GetFile 成功
            #
            # 从这里开始，这个 File 才属于本次权威 Snapshot。
            # ==================================================

            raw_filename = _build_snapshot_filename(
                file_id,
                file_name,
                suffix="json",
            )

            authoritative_files[file_id] = raw_filename

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
            content = extract_file_content(detail)

            content_file: str | None = None

            if content is not None and content != "":
                # ------------------------------------------------
                # 根据 ListFiles.FileType 决定扩展名。
                # ------------------------------------------------
                extension = file_type_info.extension.lstrip(".")

                if not extension:
                    extension = "txt"

                content_filename = _build_snapshot_filename(
                    file_id,
                    file_name,
                    suffix=extension,
                )

                content_path = content_dir / content_filename

                _write_content(
                    content_path,
                    content,
                    overwrite=(settings.export_overwrite),
                )

                authoritative_content_files.add(content_filename)

                content_file = str(content_path.relative_to(self.source_dir))

                logger.debug(
                    "保存 File Content：workspace=%s，file_id=%s，file_type=%s，format=%s，path=%s",
                    workspace.id,
                    file_id,
                    file_type,
                    file_type_info.content_format,
                    content_path,
                )

            else:
                logger.debug(
                    "File 没有 Content：workspace=%s，file_id=%s，node_id=%s，file_type=%s",
                    workspace.id,
                    file_id,
                    node_id,
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
                    "node_id": node_id,
                    "use_type": use_type,
                    "file_type": file_type,
                    "task_type": file_type_info.task_type,
                    "file_type_name": file_type_info.name,
                    "category": file_type_info.category,
                    "content_format": file_type_info.content_format,
                    "raw_file": str(raw_path.relative_to(self.source_dir)),
                    "content_file": content_file,
                }
            )

        # ======================================================
        # 6. 保存 File 索引
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

        logger.info(
            "Workspace %s 采集完成：%s 个文件，%s 个失败",
            workspace.name,
            len(file_index),
            len(failed_files),
        )

        # ======================================================
        # 7. 清理旧 Snapshot
        # ======================================================

        # Cleanup 安全原则：
        #
        # limit 模式拿到的是部分集合，
        # 不具有完整集合的权威性，
        # 不能据此判断远端对象已删除，因此绝对禁止 Cleanup。
        if limit is not None:
            logger.info(
                "limit 模式跳过 DataWorks Snapshot Cleanup：workspace=%s，limit=%s，Cleanup=SKIP",
                workspace.id,
                limit,
            )

        else:
            self._cleanup_workspace_files(
                files_dir=files_dir,
                content_dir=content_dir,
                authoritative_files=(authoritative_files),
                authoritative_content_files=(authoritative_content_files),
                failed_file_ids=failed_file_ids,
            )

        return _workspace_entry(
            workspace,
            status=("failed" if failed_files else "ok"),
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

        1. File ID 当前 GetFile 成功：
           只保留当前 raw filename。

        2. File ID 当前不存在：
           删除旧 JSON。

        3. File ID 当前存在但 GetFile 失败：
           保留旧 JSON。

        Content 清理规则：

        1. File 已经不存在：
           删除旧 Content。

        2. File 当前 GetFile 成功：
           只保留当前 Content。

        3. File 当前 GetFile 失败：
           保留旧 Content。

        4. Content 从有变成无：
           删除旧 Content。
        """

        # ======================================================
        # 1. 清理 JSON File Snapshot
        # ======================================================

        keep_file_names = set(authoritative_files.values())

        failed_file_snapshot_ids = {safe_filename(file_id) for file_id in failed_file_ids}

        for path in files_dir.glob("*.json"):
            if path.name in keep_file_names:
                continue

            file_id = self._extract_entity_id_from_filename(path.name)

            # GetFile 失败：
            # 保留旧 Snapshot。
            if file_id in failed_file_snapshot_ids:
                logger.debug(
                    "保留 GetFile 失败的旧 File Snapshot：%s",
                    path.name,
                )
                continue

            logger.info(
                "清理过期 DataWorks File Snapshot：%s",
                path.name,
            )

            path.unlink()

        # ======================================================
        # 2. 清理 Content Snapshot
        # ======================================================

        authoritative_file_ids = {safe_filename(file_id) for file_id in authoritative_files}

        for path in content_dir.iterdir():
            if not path.is_file():
                continue

            file_id = self._extract_entity_id_from_filename(path.name)

            if file_id is None:
                logger.info(
                    "清理幽灵 Content 文件：%s",
                    path.name,
                )
                path.unlink()
                continue

            # --------------------------------------------------
            # File 已经不存在于当前 ListFiles。
            # --------------------------------------------------

            if file_id not in authoritative_file_ids and file_id not in failed_file_snapshot_ids:
                logger.info(
                    "清理已删除 File 对应的 Content Snapshot：%s",
                    path.name,
                )
                path.unlink()
                continue

            # --------------------------------------------------
            # GetFile 失败：
            # 保留旧 Content。
            # --------------------------------------------------

            if file_id in failed_file_snapshot_ids:
                logger.debug(
                    "保留 GetFile 失败的旧 Content Snapshot：%s",
                    path.name,
                )
                continue

            # --------------------------------------------------
            # GetFile 成功：
            # 当前 Content 不在权威集合中，
            # 可以安全删除。
            # --------------------------------------------------

            if path.name not in authoritative_content_files:
                logger.info(
                    "清理过期 Content Snapshot：%s",
                    path.name,
                )
                path.unlink()

    @staticmethod
    def _extract_entity_id_from_filename(
        filename: str,
    ) -> str | None:
        """
        从 Snapshot 文件名提取实体 ID。

        当前格式：

            <id>__<name>.<extension>

        例如：

            505550697__tb_xxx.sql
            505550698__sync_xxx.json

        返回：

            505550697
            505550698

        如果无法解析，则返回 None。
        """

        if "__" not in filename:
            return None

        entity_id = filename.split(
            "__",
            maxsplit=1,
        )[0]

        return entity_id if entity_id else None

    # ==========================================================
    # Workspace Index
    # ==========================================================

    def _write_workspaces_index(
        self,
        entries: list[dict[str, Any]],
    ) -> None:
        """
        写入 DataWorks Workspace 注册表。

        使用读-改-写 upsert。

        已有但未参与本次采集的 Workspace：
            原样保留。

        本次采集的 Workspace：
            按 id 更新或追加。
        """

        path = self.source_dir / "dataworks" / "workspaces-index.json"

        merged: dict[int, dict[str, Any]] = {}
        order: list[int] = []

        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))

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
                "workspaces": [merged[entry_id] for entry_id in order],
            },
            overwrite=settings.export_overwrite,
        )

    # ==========================================================
    # MaxCompute
    # ==========================================================

    def _export_maxcompute_workspace(
        self,
        workspace: WorkspaceSettings,
        limit: int | None = None,
    ) -> None:
        """
        采集单个 Workspace 对应的 MaxCompute Project。

        当前约定：

            Workspace.name
                ↓
            MaxCompute Project.name

        例如：

            Workspace ID   = 123456
            Workspace Name = ods

            MaxCompute Project = ods

        Snapshot 按 Workspace ID 隔离。

        limit 不为 None：

            完整 ListTables 结果获取后，
            只对前 limit 张表执行 GetTable，
            并跳过最后一步 Cleanup。
        """

        project = workspace.name

        base_dir = self.source_dir / "maxcompute" / "workspaces" / str(workspace.id)

        tables_dir = base_dir / "tables"

        ensure_dir(tables_dir)

        logger.info(
            "开始采集 MaxCompute：workspace=%s，workspace_name=%s，project=%s",
            workspace.id,
            workspace.name,
            project,
        )

        # 每个 Workspace 使用独立 MaxCompute Client。
        client = MaxComputeClient(project=project)

        # ======================================================
        # 1. 获取当前 Project 的权威 Table 列表
        # ======================================================

        try:
            tables = client.list_tables()

        except Exception:
            logger.exception(
                "获取 MaxCompute 表列表失败：workspace=%s，project=%s",
                workspace.id,
                project,
            )

            self.had_failures = True

            # ListTables 失败时不能 cleanup。
            return

        # ======================================================
        # 1.1 采集限制模式
        #
        # 不修改 MaxComputeClient.list_tables()，
        # 在拿到完整 ListTables 结果后、GetTable 之前截断。
        # ======================================================

        if limit is not None:
            logger.info(
                "MaxCompute 采集限制模式：workspace=%s，project=%s，"
                "全量表数=%s，limit=%s，只处理前 %s 张表，Cleanup=SKIP",
                workspace.id,
                project,
                len(tables),
                limit,
                limit,
            )

            tables = tables[:limit]

        table_index: list[dict[str, Any]] = []

        # 当前成功获取到的 Table Snapshot。
        authoritative_tables: set[str] = set()

        # 当前获取失败的 Table。
        failed_tables: set[str] = set()

        # ======================================================
        # 2. 获取每张表的完整元数据
        # ======================================================

        for table in track(
            tables,
            description=(f"正在获取 MaxCompute 表 [{workspace.name}]"),
        ):
            table_name = str(table.name)

            filename = f"{safe_filename(table_name)}.json"

            table_path = tables_dir / filename

            try:
                metadata = client.get_table_metadata(table_name)

            except Exception:
                logger.exception(
                    "获取 MaxCompute 表失败：workspace=%s，project=%s，table=%s",
                    workspace.id,
                    project,
                    table_name,
                )

                self.had_failures = True

                failed_tables.add(table_name)

                # GetTable 失败：
                # 不覆盖旧 Snapshot。
                continue

            # --------------------------------------------------
            # 只有 GetTable 成功后，
            # 才将 Table 加入权威 Snapshot 集合。
            # --------------------------------------------------

            authoritative_tables.add(table_name)

            write_json(
                table_path,
                metadata,
                overwrite=settings.export_overwrite,
            )

            table_index.append(
                {
                    "workspace_id": workspace.id,
                    "workspace_name": workspace.name,
                    "project": project,
                    "schema": (settings.maxcompute_schema),
                    "table": table_name,
                    "comment": metadata.get("comment"),
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
                    "size": metadata.get("size"),
                    "raw_file": str(table_path.relative_to(self.source_dir)),
                }
            )

        # ======================================================
        # 3. 保存 Table Index
        # ======================================================

        write_json(
            base_dir / "tables-index.json",
            {
                "generated_at": utc_now(),
                "workspace": _workspace_identity(workspace),
                "project": project,
                "schema": (settings.maxcompute_schema),
                "count": len(table_index),
                "tables": table_index,
                "failed_tables": [
                    {
                        "table": table_name,
                    }
                    for table_name in sorted(failed_tables)
                ],
            },
            overwrite=settings.export_overwrite,
        )

        logger.info(
            "MaxCompute Workspace 采集完成：workspace=%s，project=%s，成功=%s，失败=%s",
            workspace.id,
            project,
            len(table_index),
            len(failed_tables),
        )

        # ======================================================
        # 4. 清理失效 Table Snapshot
        # ======================================================

        # Cleanup 安全原则：
        #
        # limit 模式拿到的是部分集合，
        # 不具有完整集合的权威性，
        # 不能据此判断远端表已删除，因此绝对禁止 Cleanup。
        if limit is not None:
            logger.info(
                "limit 模式跳过 MaxCompute Snapshot Cleanup：workspace=%s，limit=%s，Cleanup=SKIP",
                workspace.id,
                limit,
            )

        else:
            self._cleanup_maxcompute_tables(
                tables_dir=tables_dir,
                authoritative_tables=(authoritative_tables),
                failed_tables=failed_tables,
            )

    def _cleanup_maxcompute_tables(
        self,
        *,
        tables_dir: Path,
        authoritative_tables: set[str],
        failed_tables: set[str],
    ) -> None:
        """
        清理 MaxCompute 旧 Table Snapshot。

        前提：

        ListTables 必须成功。

        清理规则：

        1. Table 当前存在 + GetTable 成功
           -> 保留当前 Snapshot。

        2. Table 当前存在 + GetTable 失败
           -> 保留旧 Snapshot。

        3. Table 已经不存在
           -> 删除旧 Snapshot。
        """

        authoritative_table_names = {
            safe_filename(table_name) for table_name in authoritative_tables
        }

        failed_table_names = {safe_filename(table_name) for table_name in failed_tables}

        for path in tables_dir.glob("*.json"):
            table_name = path.stem

            # GetTable 失败：
            # 保留旧 Snapshot。
            if table_name in failed_table_names:
                logger.debug(
                    "保留 MaxCompute 获取失败的旧 Table Snapshot：%s",
                    path.name,
                )
                continue

            # 当前成功获取：
            # 保留。
            if table_name in authoritative_table_names:
                continue

            # ListTables 成功，但当前 Table 已不存在：
            # 删除旧 Snapshot。
            logger.info(
                "清理过期 MaxCompute Table Snapshot：%s",
                path.name,
            )

            path.unlink()

    # ==========================================================
    # Manifest
    # ==========================================================

    def write_manifest(self) -> None:
        """
        生成 Snapshot 清单。

        manifest 只描述当前配置和采集来源，
        不保存具体 Table / File 明细。
        """

        manifest = {
            "generated_at": utc_now(),
            "tool": "data-platform-analysis",
            "version": "0.1.0",
            "sources": {
                "dataworks": {
                    "api_version": "2020-05-18",
                    "region": (settings.dataworks_region),
                    "workspaces": [
                        _workspace_identity(workspace) for workspace in (settings.workspaces)
                    ],
                },
                "maxcompute": {
                    "endpoint": (settings.maxcompute_endpoint),
                    "schema": (settings.maxcompute_schema),
                    "workspaces": [
                        {
                            **_workspace_identity(workspace),
                            "project": (workspace.name),
                        }
                        for workspace in (settings.workspaces)
                    ],
                },
            },
        }

        write_json(
            self.source_dir / "manifest.json",
            manifest,
            overwrite=settings.export_overwrite,
        )

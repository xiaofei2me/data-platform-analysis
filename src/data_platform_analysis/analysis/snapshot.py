"""只读访问 source/ Snapshot。

约束：

1. 只读：任何方法都不修改 source/。
2. raw JSON 是 Source of Truth，index 只用于导航。
3. 单个对象失败记录为可恢复错误，整体失败才抛 AnalysisFatalError。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import AnalysisFatalError, ErrorLedger


@dataclass(frozen=True)
class WorkspaceIdentity:
    """从 Snapshot 中读取的 Workspace identity。"""

    workspace_id: int
    workspace_name: str

    dataworks_snapshot: str | None
    """dataworks/workspaces/<workspace_id>，不存在则为 None。"""

    maxcompute_snapshot: str | None
    """maxcompute/workspaces/<workspace_id>，不存在则为 None。"""


class SnapshotReader:
    """source/ Snapshot 的只读访问入口。"""

    def __init__(
        self,
        source_dir: Path,
        ledger: ErrorLedger,
    ) -> None:
        self.source_dir = source_dir
        self.ledger = ledger

    # ==========================================================
    # 基础读取
    # ==========================================================

    def resolve(self, relative_path: str) -> Path:
        """把 Snapshot 相对路径解析成绝对路径。"""

        return self.source_dir / relative_path

    def exists(self, relative_path: str | None) -> bool:
        """判断 Snapshot 相对路径是否存在。"""

        if not relative_path:
            return False

        return self.resolve(relative_path).exists()

    def read_text(
        self,
        relative_path: str,
        *,
        stage: str,
        error_type: str,
        workspace_id: int | None = None,
        file_id: int | str | None = None,
        table: str | None = None,
    ) -> str | None:
        """读取文本文件；失败时记录可恢复错误并返回 None。"""

        path = self.resolve(relative_path)

        try:
            return path.read_text(encoding="utf-8", errors="replace")

        except OSError as exc:
            self.ledger.add(
                stage=stage,
                error_type=error_type,
                message=str(exc),
                workspace_id=workspace_id,
                file_id=file_id,
                table=table,
                path=relative_path,
            )

            return None

    def read_json(
        self,
        relative_path: str,
        *,
        stage: str,
        error_type: str,
        workspace_id: int | None = None,
        file_id: int | str | None = None,
        table: str | None = None,
    ) -> dict[str, Any] | None:
        """读取 JSON 对象文件；失败时记录可恢复错误并返回 None。"""

        text = self.read_text(
            relative_path,
            stage=stage,
            error_type=error_type,
            workspace_id=workspace_id,
            file_id=file_id,
            table=table,
        )

        if text is None:
            return None

        try:
            data = json.loads(text)

        except json.JSONDecodeError as exc:
            self.ledger.add(
                stage=stage,
                error_type=error_type,
                message=f"JSON 解析失败：{exc}",
                workspace_id=workspace_id,
                file_id=file_id,
                table=table,
                path=relative_path,
            )

            return None

        if not isinstance(data, dict):
            self.ledger.add(
                stage=stage,
                error_type=error_type,
                message="JSON 顶层不是对象",
                workspace_id=workspace_id,
                file_id=file_id,
                table=table,
                path=relative_path,
            )

            return None

        return data

    # ==========================================================
    # Workspace identity
    # ==========================================================

    def load_workspace_identities(self) -> list[WorkspaceIdentity]:
        """
        从 Snapshot 中读取全部 Workspace identity。

        identity 来源（按优先级）：

        1. dataworks/workspaces-index.json
        2. dataworks/workspaces/<workspace_id>/ 目录扫描
        3. maxcompute/workspaces/<workspace_id>/ 目录扫描
        4. manifest.json（仅用于补充 name）

        如果 source/ 不存在，或任何来源都无法给出 Workspace identity，
        抛出 AnalysisFatalError。
        """

        if not self.source_dir.exists():
            raise AnalysisFatalError(
                f"source/ 目录不存在：{self.source_dir}（请先执行 export 采集 Snapshot）"
            )

        names: dict[int, str] = {}
        dataworks_ids: set[int] = set()
        maxcompute_ids: set[int] = set()

        # --------------------------------------------------
        # 1. DataWorks Workspace 索引
        # --------------------------------------------------
        index_path = "dataworks/workspaces-index.json"

        if self.resolve(index_path).exists():
            data = self.read_json(
                index_path,
                stage="inventory",
                error_type="WORKSPACE_INDEX_INVALID",
            )

            if data is not None:
                entries = data.get("workspaces")

                if not isinstance(entries, list):
                    entries = []

                for entry in entries:
                    if not isinstance(entry, dict):
                        continue

                    workspace_id = to_int(entry.get("id"))

                    if workspace_id is None:
                        continue

                    names.setdefault(workspace_id, str(entry.get("name") or ""))
                    dataworks_ids.add(workspace_id)

        # --------------------------------------------------
        # 2. DataWorks 目录扫描
        # --------------------------------------------------
        for workspace_id, workspace_name in self._scan_workspace_dirs("dataworks"):
            dataworks_ids.add(workspace_id)

            if workspace_id not in names or not names[workspace_id]:
                names[workspace_id] = workspace_name

        # --------------------------------------------------
        # 3. MaxCompute 目录扫描
        # --------------------------------------------------
        for workspace_id, workspace_name in self._scan_workspace_dirs("maxcompute"):
            maxcompute_ids.add(workspace_id)

            if workspace_id not in names or not names[workspace_id]:
                names[workspace_id] = workspace_name

        # --------------------------------------------------
        # 4. manifest.json 补充 name
        # --------------------------------------------------
        if self.resolve("manifest.json").exists():
            manifest = self.read_json(
                "manifest.json",
                stage="inventory",
                error_type="MANIFEST_INVALID",
            )

            if manifest is not None:
                for entry in self._manifest_workspaces(manifest):
                    workspace_id = to_int(entry.get("id"))

                    if workspace_id is None:
                        continue

                    if not names.get(workspace_id):
                        names[workspace_id] = str(entry.get("name") or "")

        all_ids = dataworks_ids | maxcompute_ids

        if not all_ids:
            raise AnalysisFatalError(
                f"无法从 {self.source_dir} 读取任何 Workspace identity"
                "（dataworks / maxcompute Snapshot 均不存在）"
            )

        identities: list[WorkspaceIdentity] = []

        for workspace_id in sorted(all_ids):
            dataworks_snapshot = f"dataworks/workspaces/{workspace_id}"
            maxcompute_snapshot = f"maxcompute/workspaces/{workspace_id}"

            identities.append(
                WorkspaceIdentity(
                    workspace_id=workspace_id,
                    workspace_name=names.get(workspace_id) or str(workspace_id),
                    dataworks_snapshot=(
                        dataworks_snapshot if self.resolve(dataworks_snapshot).exists() else None
                    ),
                    maxcompute_snapshot=(
                        maxcompute_snapshot if self.resolve(maxcompute_snapshot).exists() else None
                    ),
                )
            )

        return identities

    def select_identities(
        self,
        identities: list[WorkspaceIdentity],
        workspace_id: int | None,
    ) -> list[WorkspaceIdentity]:
        """
        按 --workspace 过滤 Workspace identity。

        指定的 Workspace 不在 Snapshot 中：
            抛出 AnalysisFatalError（workspace identity 无法读取）。
        """

        if workspace_id is None:
            return identities

        matched = [identity for identity in identities if identity.workspace_id == workspace_id]

        if not matched:
            raise AnalysisFatalError(
                f"Snapshot 中不存在 Workspace {workspace_id}（source/ 未采集该 Workspace）"
            )

        return matched

    # ==========================================================
    # Index 读取
    # ==========================================================

    def load_files_index(
        self,
        workspace: WorkspaceIdentity,
    ) -> list[dict[str, Any]] | None:
        """读取单个 Workspace 的 files-index.json。"""

        relative_path = f"dataworks/workspaces/{workspace.workspace_id}/files-index.json"

        if not self.resolve(relative_path).exists():
            return None

        data = self.read_json(
            relative_path,
            stage="inventory",
            error_type="FILES_INDEX_INVALID",
            workspace_id=workspace.workspace_id,
        )

        if data is None:
            return None

        files = data.get("files")

        if not isinstance(files, list):
            self.ledger.add(
                stage="inventory",
                error_type="FILES_INDEX_INVALID",
                message="files 字段缺失或不是数组",
                workspace_id=workspace.workspace_id,
                path=relative_path,
            )

            return None

        return [entry for entry in files if isinstance(entry, dict)]

    def load_tables_index(
        self,
        workspace: WorkspaceIdentity,
    ) -> list[dict[str, Any]] | None:
        """读取单个 Workspace 的 tables-index.json。"""

        relative_path = f"maxcompute/workspaces/{workspace.workspace_id}/tables-index.json"

        if not self.resolve(relative_path).exists():
            return None

        data = self.read_json(
            relative_path,
            stage="inventory",
            error_type="TABLES_INDEX_INVALID",
            workspace_id=workspace.workspace_id,
        )

        if data is None:
            return None

        tables = data.get("tables")

        if not isinstance(tables, list):
            self.ledger.add(
                stage="inventory",
                error_type="TABLES_INDEX_INVALID",
                message="tables 字段缺失或不是数组",
                workspace_id=workspace.workspace_id,
                path=relative_path,
            )

            return None

        return [entry for entry in tables if isinstance(entry, dict)]

    # ==========================================================
    # Content 读取
    # ==========================================================

    def load_file_content(
        self,
        workspace_id: int,
        file_id: int | str,
        content_file: str | None,
    ) -> tuple[str | None, bool]:
        """
        读取 DataWorks File 的 SQL 内容。

        返回 (content, ok)：

        - ok 为 True：content 是文件内容（可能为空字符串）。
        - ok 为 False：内容不可用，已记录可恢复错误。
        """

        if not content_file:
            self.ledger.add(
                stage="sql",
                error_type="CONTENT_FILE_MISSING",
                message="files-index 条目缺少 content_file",
                workspace_id=workspace_id,
                file_id=str(file_id),
            )

            return None, False

        path = self.resolve(content_file)

        if not path.exists():
            self.ledger.add(
                stage="sql",
                error_type="CONTENT_FILE_MISSING",
                message="SQL content 文件不存在",
                workspace_id=workspace_id,
                file_id=str(file_id),
                path=content_file,
            )

            return None, False

        try:
            return path.read_text(encoding="utf-8", errors="replace"), True

        except OSError as exc:
            self.ledger.add(
                stage="sql",
                error_type="CONTENT_MISSING",
                message=str(exc),
                workspace_id=workspace_id,
                file_id=str(file_id),
                path=content_file,
            )

            return None, False

    # ==========================================================
    # 内部工具
    # ==========================================================

    def _scan_workspace_dirs(
        self,
        subsystem: str,
    ) -> list[tuple[int, str]]:
        """扫描 source/<subsystem>/workspaces/<workspace_id>。"""

        root = self.source_dir / subsystem / "workspaces"

        if not root.exists():
            return []

        result: list[tuple[int, str]] = []

        for workspace_dir in sorted(root.iterdir()):
            if not workspace_dir.is_dir():
                continue

            workspace_id = to_int(workspace_dir.name)

            if workspace_id is None:
                continue

            result.append((workspace_id, self._read_workspace_dir_name(subsystem, workspace_dir)))

        return result

    def _read_workspace_dir_name(
        self,
        subsystem: str,
        workspace_dir: Path,
    ) -> str:
        """从 Workspace 目录内的 index 读取 name。"""

        index_name = "files-index.json" if subsystem == "dataworks" else "tables-index.json"

        index_path = workspace_dir / index_name

        if index_path.exists():
            relative_path = str(index_path.relative_to(self.source_dir))

            data = self.read_json(
                relative_path,
                stage="inventory",
                error_type="WORKSPACE_INDEX_INVALID",
                workspace_id=to_int(workspace_dir.name),
            )

            if data is not None:
                workspace = data.get("workspace")

                if isinstance(workspace, dict):
                    name = workspace.get("name")

                    if name:
                        return str(name)

        return workspace_dir.name

    @staticmethod
    def _manifest_workspaces(
        manifest: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """从 manifest.json 提取 DataWorks / MaxCompute Workspace 条目。"""

        sources = manifest.get("sources")

        if not isinstance(sources, dict):
            return []

        entries: list[dict[str, Any]] = []

        for key in ("dataworks", "maxcompute"):
            source = sources.get(key)

            if not isinstance(source, dict):
                continue

            workspaces = source.get("workspaces")

            if not isinstance(workspaces, list):
                continue

            entries.extend(entry for entry in workspaces if isinstance(entry, dict))

        return entries


def to_int(value: Any) -> int | None:
    """把 id 安全转换成 int。"""

    if isinstance(value, int):
        return value

    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())

    return None

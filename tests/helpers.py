"""测试共享构造器：Workspace 配置与 DataWorks File 的 JSON 形状。

这些形状由 spec（WORKSPACES 数组与 ListFiles / GetFile 返回对象）
决定，集中一处避免各测试文件各写一份。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from data_platform_analysis.dataworks_types import get_file_type


def make_workspace(
    workspace_id: int,
    name: str,
) -> dict[str, Any]:
    """构造 WORKSPACES 环境变量中的单个条目。

    Workspace name 即对应 MaxCompute Project 名称，
    不再单独维护 maxcompute_project。
    """

    return {
        "id": workspace_id,
        "name": name,
    }


def workspaces_env(*entries: dict[str, Any]) -> str:
    """把 Workspace 条目序列化为 WORKSPACES 环境变量值。"""

    return json.dumps(list(entries))


def make_file(
    file_id: str,
    name: str,
    *,
    file_type: int = 10,
    use_type: str = "NORMAL",
    content: str | None = None,
) -> dict[str, Any]:
    """构造 ListFiles / GetFile 返回的单个 File 对象。

    file_type 默认 10（ODPS SQL），content 默认有值。
    """

    file: dict[str, Any] = {
        "FileId": file_id,
        "FileName": name,
        "FileType": file_type,
        "UseType": use_type,
    }

    if content is None:
        content = f"SELECT {file_id};"

    file["Content"] = content

    return file


def make_files(
    first_id: int,
    count: int,
    *,
    use_type: str = "NORMAL",
    file_type: int = 10,
) -> list[dict[str, Any]]:
    """批量构造 File。

    FileId 是从 first_id 开始的数字串——
    真实 DataWorks FileId 为整数，
    export 流程会把它转成 int 调用 GetFile。
    """

    return [
        make_file(
            str(first_id + index),
            f"file_{first_id + index}",
            file_type=file_type,
            use_type=use_type,
        )
        for index in range(count)
    ]


# ============================================================
# Snapshot fixture（Analysis 测试用）
# ============================================================


def write_snapshot(
    source_dir: Path,
    *,
    workspaces: list[dict[str, Any]],
    files: list[dict[str, Any]] | None = None,
    tables: list[dict[str, Any]] | None = None,
) -> None:
    """在临时目录里直接构造一份只读 Snapshot。

    Analysis 只依赖 export 的产物形状，因此这里直接写
    index + raw + content 文件，不需要走采集流程。

    workspaces：
        [{"id": 9001, "name": "ws-a"}]

    files：
        [{"workspace_id": 9001, "file_id": "101", "file_name": "daily",
          "content": "INSERT ...;", "content_format": "SQL",
          "file_type": 10, "node_id": "7001"}]

    tables：
        [{"workspace_id": 9001, "table": "dwd_order",
          "comment": "订单明细", "columns": [{"name": "id", "type": "STRING"}],
          "partitions": ["ds"]}]
    """

    files = list(files or [])
    tables = list(tables or [])

    _write_json(
        source_dir / "dataworks" / "workspaces-index.json",
        {
            "workspaces": [
                {"id": workspace["id"], "name": workspace["name"]} for workspace in workspaces
            ]
        },
    )

    for workspace in workspaces:
        workspace_id = int(workspace["id"])
        workspace_name = str(workspace["name"])

        _write_dataworks_workspace(
            source_dir=source_dir,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            files=[file for file in files if int(file.get("workspace_id", -1)) == workspace_id],
        )

        _write_maxcompute_workspace(
            source_dir=source_dir,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            tables=[
                table for table in tables if int(table.get("workspace_id", -1)) == workspace_id
            ],
        )


def source_tree_hash(source_dir: Path) -> dict[str, str]:
    """返回 Snapshot 内全部文件的相对路径 → 内容哈希。"""

    result: dict[str, str] = {}

    if not source_dir.exists():
        return result

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue

        result[str(path.relative_to(source_dir))] = hashlib.sha256(path.read_bytes()).hexdigest()

    return result


def _write_dataworks_workspace(
    *,
    source_dir: Path,
    workspace_id: int,
    workspace_name: str,
    files: list[dict[str, Any]],
) -> None:
    """写入单个 DataWorks Workspace 的 index / raw / content。"""

    root = source_dir / "dataworks" / "workspaces" / str(workspace_id)
    prefix = f"dataworks/workspaces/{workspace_id}"

    entries: list[dict[str, Any]] = []

    for file in files:
        file_id = str(file["file_id"])
        file_name = str(file["file_name"])
        file_type = file.get("file_type", 10)
        info = get_file_type(file_type)
        content_format = str(file.get("content_format") or info.content_format)

        raw_file = f"{prefix}/files/{file_id}__{file_name}.json"
        content_file = f"{prefix}/content/{file_id}__{file_name}.sql"

        _write_json(
            source_dir / raw_file,
            {
                "File": {
                    "FileId": file_id,
                    "FileName": file_name,
                    "FileType": file_type,
                }
            },
        )
        _write_text(
            source_dir / content_file,
            str(file.get("content", "")),
        )

        entries.append(
            {
                "workspace_id": workspace_id,
                "file_id": file_id,
                "file_name": file_name,
                "node_id": file.get("node_id"),
                "use_type": file.get("use_type", "NORMAL"),
                "file_type": file_type,
                "task_type": info.task_type,
                "file_type_name": info.name,
                "category": info.category,
                "content_format": content_format,
                "raw_file": raw_file,
                "content_file": content_file,
            }
        )

    _write_json(
        root / "files-index.json",
        {
            "workspace": {"id": workspace_id, "name": workspace_name},
            "count": len(entries),
            "files": entries,
        },
    )


def _write_maxcompute_workspace(
    *,
    source_dir: Path,
    workspace_id: int,
    workspace_name: str,
    tables: list[dict[str, Any]],
) -> None:
    """写入单个 MaxCompute Workspace 的 index 与 raw metadata。"""

    root = source_dir / "maxcompute" / "workspaces" / str(workspace_id)
    prefix = f"maxcompute/workspaces/{workspace_id}"

    entries: list[dict[str, Any]] = []

    for table in tables:
        table_name = str(table["table"])
        project = str(table.get("project") or workspace_name)
        columns = list(table.get("columns") or [{"name": "id", "type": "STRING", "comment": None}])
        partitions = [
            {"name": name, "type": "STRING", "comment": None}
            for name in table.get("partitions", [])
        ]
        raw_file = f"{prefix}/tables/{table_name}.json"

        _write_json(
            source_dir / raw_file,
            {
                "project": project,
                "schema": table.get("schema", ""),
                "name": table_name,
                "comment": table.get("comment", ""),
                "creation_time": "2024-01-01T00:00:00",
                "last_modified_time": "2024-01-02T00:00:00",
                "size": table.get("size", 1024),
                "lifecycle": table.get("lifecycle", 30),
                "is_virtual_view": table.get("is_virtual_view", False),
                "columns": columns,
                "partitions": partitions,
            },
        )

        entries.append(
            {
                "workspace_id": workspace_id,
                "workspace_name": workspace_name,
                "project": project,
                "schema": table.get("schema", ""),
                "table": table_name,
                "comment": table.get("comment", ""),
                "column_count": len(columns),
                "partition_count": len(partitions),
                "size": table.get("size", 1024),
                "raw_file": raw_file,
            }
        )

    _write_json(
        root / "tables-index.json",
        {
            "workspace": {"id": workspace_id, "name": workspace_name},
            "project": workspace_name,
            "schema": "",
            "count": len(entries),
            "tables": entries,
        },
    )


def _write_json(path: Path, data: Any) -> None:
    """写入格式化 JSON。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_text(path: Path, content: str) -> None:
    """写入文本。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

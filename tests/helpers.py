"""测试共享构造器：Workspace 配置与 DataWorks File 的 JSON 形状。

这些形状由 spec（WORKSPACES 数组与 ListFiles / GetFile 返回对象）
决定，集中一处避免各测试文件各写一份。
"""

from __future__ import annotations

import json
from typing import Any


def make_workspace(
    workspace_id: int,
    name: str,
    maxcompute_project: str = "mc_demo",
) -> dict[str, Any]:
    """构造 WORKSPACES 环境变量中的单个条目。"""

    return {
        "id": workspace_id,
        "name": name,
        "maxcompute_project": maxcompute_project,
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

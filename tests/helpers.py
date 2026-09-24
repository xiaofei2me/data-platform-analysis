"""测试共享构造器：Workspace 配置与 DataWorks 节点的 JSON 形状。

这些形状由 spec（DATAWORKS_WORKSPACES 数组与 OpenAPI 节点对象）
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
    """构造 DATAWORKS_WORKSPACES 数组中的单个条目。"""

    return {
        "id": workspace_id,
        "name": name,
        "maxcompute_project": maxcompute_project,
    }


def workspaces_env(*entries: dict[str, Any]) -> str:
    """把 Workspace 条目序列化为 DATAWORKS_WORKSPACES 环境变量值。"""

    return json.dumps(list(entries))


def make_node(
    node_id: str,
    script: str,
    *,
    name: str | None = None,
    node_type: str = "Shell",
) -> dict[str, Any]:
    """构造 ListNodes 返回的单个节点对象。"""

    return {
        "NodeId": node_id,
        "NodeName": name or f"node_{node_id}",
        "NodeType": node_type,
        "Script": script,
    }

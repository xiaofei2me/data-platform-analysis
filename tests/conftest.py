"""CLI 黑盒测试接缝的共享 fixture。

约定（见 spec Testing Decisions）：
- 只在 SDK 调用边界 stub（DataWorks OpenAPI Client、PyODPS ODPS）；
- 不 mock export 流程、内部 helper 或私有方法；
- 每个测试使用临时目录作为工作目录与 source_dir，最小 env 提供配置。
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from data_platform_analysis import cli as cli_module
from data_platform_analysis import config as config_module
from data_platform_analysis import dataworks as dataworks_module
from data_platform_analysis import maxcompute as maxcompute_module


class _FakeBody:
    """模拟 OpenAPI 响应体。"""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def to_map(self) -> dict[str, Any]:
        return self._data


class _FakeResponse:
    """模拟 OpenAPI 响应对象（提供 .body）。"""

    def __init__(self, data: dict[str, Any]) -> None:
        self.body = _FakeBody(data)


class FakeDataWorksSDK:
    """DataWorks SDK 边界的假实现。

    测试通过 nodes_by_project / failing_projects / failing_node_ids
    声明每个 Workspace 的节点集合与故障行为。
    """

    def __init__(self) -> None:
        self.nodes_by_project: dict[int, list[dict[str, Any]]] = {}
        self.failing_projects: set[int] = set()
        self.failing_node_ids: dict[int, set[str]] = {}

    def client_factory(self, config: Any) -> FakeDataWorksClient:
        return FakeDataWorksClient(self)


class FakeDataWorksClient:
    def __init__(self, api: FakeDataWorksSDK) -> None:
        self._api = api

    def list_nodes(self, request: Any) -> _FakeResponse:
        project_id = int(request.project_id)

        if project_id in self._api.failing_projects:
            raise RuntimeError(
                f"list_nodes failed for project {project_id}"
            )

        nodes = self._api.nodes_by_project.get(project_id, [])
        page_size = int(request.page_size)
        page_number = int(request.page_number)
        start = (page_number - 1) * page_size
        page = nodes[start : start + page_size]

        return _FakeResponse(
            {
                "Data": {
                    "Nodes": page,
                    "TotalCount": len(nodes),
                }
            }
        )

    def get_node(self, request: Any) -> _FakeResponse:
        project_id = int(request.project_id)
        node_id = str(request.id)

        if project_id in self._api.failing_projects:
            raise RuntimeError(
                f"get_node failed for project {project_id}"
            )

        if node_id in self._api.failing_node_ids.get(
            project_id, set()
        ):
            raise RuntimeError(
                f"get_node failed for node {node_id}"
            )

        for node in self._api.nodes_by_project.get(
            project_id, []
        ):
            if str(node.get("NodeId")) == node_id:
                return _FakeResponse({"Data": dict(node)})

        raise RuntimeError(
            f"node {node_id} not found in project {project_id}"
        )


class FakeTable:
    def __init__(self, name: str) -> None:
        self.name = name
        self.comment = "demo table"
        self.creation_time = None
        self.last_modified_time = None
        self.size = 1024
        self.lifecycle = 7
        self.is_virtual_view = False
        self.schema = SimpleNamespace(
            columns=[
                SimpleNamespace(
                    name="id",
                    type="bigint",
                    comment="pk",
                )
            ],
            partitions=[],
        )

    def reload(self) -> None:
        return None


class FakeODPS:
    """PyODPS SDK 边界的假实现。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.tables: dict[str, FakeTable] = {
            "ods_users": FakeTable("ods_users"),
        }

    def list_tables(self, extended: bool = False) -> list[Any]:
        return list(self.tables.values())

    def get_table(self, name: str) -> FakeTable:
        if name not in self.tables:
            self.tables[name] = FakeTable(name)
        return self.tables[name]


@pytest.fixture
def fake_dataworks() -> FakeDataWorksSDK:
    return FakeDataWorksSDK()


@pytest.fixture
def fake_odps() -> FakeODPS:
    return FakeODPS()


@pytest.fixture
def cli_env(
    tmp_path: Any,
    monkeypatch: Any,
    fake_dataworks: FakeDataWorksSDK,
    fake_odps: FakeODPS,
) -> Iterator[FakeDataWorksSDK]:
    """临时工作目录 + 最小 env + SDK 边界 stub。"""

    monkeypatch.chdir(tmp_path)

    for key, value in {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "test-ak",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "test-sk",
        "DATAWORKS_REGION": "cn-shanghai",
        "DATAWORKS_MAX_RETRIES": "0",
        "DATAWORKS_WORKSPACES": (
            '[{"id": 9001, "name": "ws-a",'
            ' "maxcompute_project": "mc_demo"}]'
        ),
        "MAXCOMPUTE_PROJECT": "mc_demo",
        "MAXCOMPUTE_ENDPOINT": "http://localhost/api",
        "MAXCOMPUTE_SCHEMA": "",
        "SOURCE_DIR": "source",
        "EXPORT_OVERWRITE": "true",
    }.items():
        monkeypatch.setenv(key, value)

    config_module.reset_settings()

    monkeypatch.setattr(
        dataworks_module,
        "Client",
        fake_dataworks.client_factory,
    )
    monkeypatch.setattr(
        maxcompute_module,
        "ODPS",
        lambda *args, **kwargs: fake_odps,
    )

    yield fake_dataworks

    config_module.reset_settings()


@pytest.fixture
def run_cli(monkeypatch: Any) -> Any:
    """以 CLI 黑盒方式执行子命令，返回进程退出码。"""

    def _run(*argv: str) -> int:
        # 每次 CLI 调用模拟一个新进程：重新加载配置。
        config_module.reset_settings()

        monkeypatch.setattr(
            sys,
            "argv",
            ["data-platform-analysis", *argv],
        )

        try:
            cli_module.main()
        except SystemExit as exc:
            code = exc.code
            if code is None:
                return 0
            if isinstance(code, int):
                return code
            return 1

        return 0

    return _run

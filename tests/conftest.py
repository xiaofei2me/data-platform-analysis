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

    测试通过 files_by_project / failing_projects / failing_file_ids /
    malformed_projects 声明每个 Workspace 的文件集合与故障行为。

    page_size_cap 模拟服务端每页上限小于请求 page_size 的情况。

    list_files_calls 记录每一次 ListFiles 分页调用，
    用于断言 limit 模式是否提前停止分页。
    """

    def __init__(self) -> None:
        self.files_by_project: dict[int, list[dict[str, Any]]] = {}
        self.failing_projects: set[int] = set()
        self.failing_file_ids: dict[int, set[str]] = {}
        # 返回「有 TotalCount 但没有文件列表」的异常响应结构。
        self.malformed_projects: set[int] = set()
        # 服务端实际每页上限；None 表示完全按请求返回。
        self.page_size_cap: int | None = None
        self.list_files_calls: list[dict[str, Any]] = []
        self.get_file_calls: list[dict[str, Any]] = []

    def client_factory(self, config: Any) -> FakeDataWorksClient:
        return FakeDataWorksClient(self)


class FakeDataWorksClient:
    """模拟 DataWorks OpenAPI Client 的 ListFiles / GetFile。"""

    def __init__(self, api: FakeDataWorksSDK) -> None:
        self._api = api

    def list_files(self, request: Any) -> _FakeResponse:
        project_id = int(request.project_id)
        page_number = int(request.page_number)
        use_type = getattr(request, "use_type", None)

        self._api.list_files_calls.append(
            {
                "project_id": project_id,
                "page_number": page_number,
                "use_type": use_type,
            }
        )

        if project_id in self._api.failing_projects:
            raise RuntimeError(f"list_files failed for project {project_id}")

        if project_id in self._api.malformed_projects:
            return _FakeResponse(
                {
                    "Data": {
                        "TotalCount": 5,
                    }
                }
            )

        files = [
            file
            for file in self._api.files_by_project.get(project_id, [])
            if use_type is None or file.get("UseType") == use_type
        ]

        page_size = int(request.page_size)

        if self._api.page_size_cap is not None:
            page_size = min(page_size, self._api.page_size_cap)

        start = (page_number - 1) * page_size
        page = files[start : start + page_size]

        return _FakeResponse(
            {
                "Data": {
                    "Files": page,
                    "TotalCount": len(files),
                }
            }
        )

    def get_file(self, request: Any) -> _FakeResponse:
        project_id = int(request.project_id)
        file_id = str(request.file_id)

        self._api.get_file_calls.append(
            {
                "project_id": project_id,
                "file_id": file_id,
            }
        )

        if project_id in self._api.failing_projects:
            raise RuntimeError(f"get_file failed for project {project_id}")

        if file_id in self._api.failing_file_ids.get(project_id, set()):
            raise RuntimeError(f"get_file failed for file {file_id}")

        for file in self._api.files_by_project.get(project_id, []):
            if str(file.get("FileId")) == file_id:
                return _FakeResponse({"Data": {"File": dict(file)}})

        raise RuntimeError(f"file {file_id} not found in project {project_id}")


class FakeTable:
    """模拟 PyODPS Table 对象。"""

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
    """PyODPS SDK 边界的假实现。

    get_table_calls 记录每一次 GetTable 调用，
    用于断言 limit 模式下的 GetTable 次数。

    project 由 ODPS 构造参数注入，用于按 Workspace（= MaxCompute
    Project）声明故障：failing_projects（ListTables 失败）、
    failing_table_names（单表 GetTable 失败）。
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.project: str | None = kwargs.get("project")
        self.tables: dict[str, FakeTable] = {
            "ods_users": FakeTable("ods_users"),
        }
        self.get_table_calls: list[str] = []
        self.list_tables_calls: list[str] = []
        self.failing_projects: set[str] = set()
        self.failing_table_names: set[str] = set()
        # ODPS 客户端构造阶段失败（早于 ListTables）。
        self.failing_init_projects: set[str] = set()

    def set_table_names(self, *names: str) -> None:
        """替换当前 Project 的表集合。"""

        self.tables = {name: FakeTable(name) for name in names}

    def list_tables(self, extended: bool = False) -> list[Any]:
        self.list_tables_calls.append(self.project or "")

        if self.project in self.failing_projects:
            raise RuntimeError(f"list_tables failed for project {self.project}")

        return list(self.tables.values())

    def get_table(self, name: str) -> FakeTable:
        self.get_table_calls.append(name)

        if name in self.failing_table_names:
            raise RuntimeError(f"get_table failed for {name}")

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
        "DATAWORKS_PAGE_SIZE": "100",
        # 默认不按 UseType 过滤，测试按需覆盖。
        "DATAWORKS_USE_TYPES": "",
        "WORKSPACES": '[{"id": 9001, "name": "ws-a"}]',
        "MAXCOMPUTE_ENDPOINT": "http://localhost/api",
        "MAXCOMPUTE_SCHEMA": "",
        "MAXCOMPUTE_INCLUDE_PARTITIONS": "false",
        # 输出目录必须是绝对路径，避免写进项目根目录。
        "SOURCE_DIR": str(tmp_path / "source"),
        "ANALYSIS_DIR": str(tmp_path / "analysis"),
        "EXPORT_OVERWRITE": "true",
    }.items():
        monkeypatch.setenv(key, value)

    config_module.reset_settings()

    monkeypatch.setattr(
        dataworks_module,
        "Client",
        fake_dataworks.client_factory,
    )

    # MaxCompute Client 每个 Workspace 独立构造：
    # 这里记录当前构造使用的 project，并支持构造期故障注入。
    def _odps_factory(*args: Any, **kwargs: Any) -> FakeODPS:
        project = kwargs.get("project")

        if project in fake_odps.failing_init_projects:
            raise RuntimeError(f"odps init failed for project {project}")

        fake_odps.project = project

        return fake_odps

    monkeypatch.setattr(
        maxcompute_module,
        "ODPS",
        _odps_factory,
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

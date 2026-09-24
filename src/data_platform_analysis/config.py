"""项目配置。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

class WorkspaceSettings(BaseModel):
    """单个 DataWorks Workspace 配置。"""

    # DataWorks Workspace ID（稳定主键）。
    id: int

    # 人类可读名称（数组内唯一）。
    name: str = Field(
        ...,
        min_length=1,
    )

    # 1:1 绑定的 MaxCompute 项目（仅作环境映射元数据）。
    maxcompute_project: str = Field(
        ...,
        min_length=1,
    )

class Settings(BaseSettings):
    """项目运行配置。"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================================
    # 阿里云认证
    # ========================================================

    # 阿里云 AccessKey ID。
    alibaba_cloud_access_key_id: str = Field(
        ...,
        min_length=1,
    )

    # 阿里云 AccessKey Secret。
    alibaba_cloud_access_key_secret: str = Field(
        ...,
        min_length=1,
    )

    # ========================================================
    # DataWorks
    # ========================================================

    # DataWorks 所在地域。
    dataworks_region: str = "cn-shanghai"

    # DataWorks Workspace 列表（JSON 数组）。
    #
    # 单 Workspace 即长度为 1 的数组，不存在单独模式。
    dataworks_workspaces: list[WorkspaceSettings] = Field(
        ...,
        min_length=1,
    )

    @model_validator(mode="after")
    def _validate_workspaces(self) -> Settings:
        """Workspace id 与 name 在列表内必须唯一。"""

        ids = [
            workspace.id
            for workspace in self.dataworks_workspaces
        ]

        names = [
            workspace.name
            for workspace in self.dataworks_workspaces
        ]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "DATAWORKS_WORKSPACES 中存在重复的 id"
            )

        if len(names) != len(set(names)):
            raise ValueError(
                "DATAWORKS_WORKSPACES 中存在重复的 name"
            )

        return self

    def select_workspaces(
        self,
        workspace_id: int | None = None,
    ) -> list[WorkspaceSettings]:
        """
        解析本次要采集的 Workspace 列表。

        workspace_id 为 None 时返回全部；
        指定但未配置的 id 直接报错（fail-fast）。
        """
        if workspace_id is None:
            return list(self.dataworks_workspaces)

        matched = [
            workspace
            for workspace in self.dataworks_workspaces
            if workspace.id == workspace_id
        ]

        if not matched:
            raise ValueError(f"未配置的 Workspace id：{workspace_id}（不在 DATAWORKS_WORKSPACES 中）")

        return matched

    # DataWorks API 每页返回的数据量。
    dataworks_page_size: int = Field(
        default=100,
        ge=1,
        le=1000,
    )

    # DataWorks API 最大重试次数。
    dataworks_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
    )

    # ========================================================
    # MaxCompute
    # ========================================================

    # MaxCompute 项目名称。
    maxcompute_project: str

    # MaxCompute Endpoint。
    maxcompute_endpoint: str

    # MaxCompute Schema。
    #
    # 如果使用默认 Schema，可以为空。
    maxcompute_schema: str | None = None

    # 是否采集实际分区实例。
    #
    # 第一阶段默认关闭。
    maxcompute_include_partitions: bool = False

    # ========================================================
    # Export
    # ========================================================

    # Snapshot 输出目录。
    source_dir: Path = Path("source")

    # 是否覆盖已经存在的文件。
    export_overwrite: bool = True


_instance: Settings | None = None


def get_settings() -> Settings:
    """返回全局配置实例，首次访问时从环境加载。"""

    global _instance

    if _instance is None:
        _instance = Settings()  # type: ignore[call-arg]

    return _instance


def reset_settings() -> None:
    """丢弃已缓存的配置实例，供测试在切换环境后重新加载。"""

    global _instance

    _instance = None


class _SettingsProxy:
    """惰性配置代理：属性访问时才触发加载。"""

    __slots__ = ()

    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)


# 全局配置实例（惰性）。
settings = _SettingsProxy()
"""项目配置。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    SettingsConfigDict,
)

# ============================================================
# Project paths
# ============================================================

# 当前文件：
#
#   project-root/
#   └── src/
#       └── data_platform_analysis/
#           └── config.py
#
# parents[0] -> data_platform_analysis/
# parents[1] -> src/
# parents[2] -> project-root/
#
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 项目根目录下的 .env。
# 不依赖当前 Working Directory。
ENV_FILE = PROJECT_ROOT / ".env"


def resolve_project_path(path: Path | str) -> Path:
    """
    将项目路径解析为绝对路径。

    相对路径：
        相对于项目根目录解析。

    绝对路径：
        保持原路径不变。
    """
    path = Path(path)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


class WorkspaceSettings(BaseModel):
    """单个 DataWorks Workspace 配置。"""

    # Workspace ID（稳定主键）。
    id: int

    # Workspace 名称。
    #
    # 当前约定：
    # Workspace name 与对应 MaxCompute Project name 1:1 对应。
    name: str = Field(
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

    # DataWorks Workspace 列表。
    #
    # Workspace 同时作为：
    # 1. DataWorks 采集上下文
    # 2. 对应 MaxCompute Project 的映射上下文
    #
    # 单 Workspace 即长度为 1 的数组，
    # 不存在单独的 single / multi 模式。
    workspaces: list[WorkspaceSettings] = Field(
        ...,
        min_length=1,
    )

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

    # DataWorks ListFiles 支持按 UseType 查询。
    #
    # 空值：
    # DATAWORKS_USE_TYPES=
    # 表示不传 UseType，获取 Workspace 全量文件。
    #
    # 单个：
    # DATAWORKS_USE_TYPES=NORMAL
    #
    # 多个：
    # DATAWORKS_USE_TYPES=NORMAL,MANUAL,MANUAL_BIZ
    #
    # 多个 UseType 会分别调用 ListFiles，最终合并结果。
    dataworks_use_types: Annotated[
        list[str],
        NoDecode,
    ] = Field(
        default_factory=list,
    )

    # ========================================================
    # MaxCompute
    # ========================================================

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
    #
    # 相对路径：
    #   相对于项目根目录解析。
    #
    # 绝对路径：
    #   保持原路径不变。
    source_dir: Path = Path("source")

    # Analysis 输出目录。
    #
    # Analysis 只读 source_dir，写入 analysis_dir。
    #
    # 相对路径：
    #   相对于项目根目录解析。
    #
    # 绝对路径：
    #   保持原路径不变。
    analysis_dir: Path = Path("analysis")

    # M2.2 Layer Rules 配置文件。
    #
    # 只读配置，Analysis 不会修改该文件。
    #
    # 相对路径：
    #   相对于项目根目录解析。
    #
    # 绝对路径：
    #   保持原路径不变。
    layer_rules_path: Path = Path("config/layer-rules.yaml")

    # M3 Business Rules 词典配置文件。
    #
    # 只读配置，Analysis 不会修改该文件。
    #
    # 相对路径：
    #   相对于项目根目录解析。
    #
    # 绝对路径：
    #   保持原路径不变。
    business_rules_path: Path = Path("config/business-rules.yaml")

    # M3.3 Process Signal 规则配置文件。
    #
    # 只读配置，Analysis 不会修改该文件。
    #
    # 相对路径：
    #   相对于项目根目录解析。
    #
    # 绝对路径：
    #   保持原路径不变。
    process_rules_path: Path = Path("config/process-rules.yaml")

    # 是否覆盖已经存在的文件。
    export_overwrite: bool = True

    # ========================================================
    # Validators
    # ========================================================

    @model_validator(mode="before")
    @classmethod
    def _parse_json_environment_values(
        cls,
        values: Any,
    ) -> Any:
        """
        解析通过环境变量传入的配置。

        WORKSPACES：
            使用 JSON 数组。

        例如：
            WORKSPACES='[
                {"id": 123, "name": "workspace-a"}
            ]'

        DATAWORKS_USE_TYPES：
            使用逗号分隔字符串。
        """
        if not isinstance(values, dict):
            return values

        # ----------------------------------------------------
        # WORKSPACES
        # ----------------------------------------------------
        workspaces = values.get("workspaces")

        if isinstance(workspaces, str):
            try:
                values["workspaces"] = json.loads(workspaces)
            except json.JSONDecodeError as exc:
                raise ValueError(f"WORKSPACES 不是合法的 JSON：{exc}") from exc

        # ----------------------------------------------------
        # DATAWORKS_USE_TYPES
        # ----------------------------------------------------
        use_types = values.get("dataworks_use_types")

        if isinstance(use_types, str):
            values["dataworks_use_types"] = [
                item.strip().upper() for item in use_types.split(",") if item.strip()
            ]

        return values

    @model_validator(mode="after")
    def _validate_workspaces(self) -> Settings:
        """
        校验 Workspace 配置。

        校验：
        1. Workspace ID 不能重复。
        2. Workspace name 不能重复。
        """
        workspace_ids = [workspace.id for workspace in self.workspaces]

        duplicate_ids = {
            workspace_id for workspace_id in workspace_ids if workspace_ids.count(workspace_id) > 1
        }

        if duplicate_ids:
            raise ValueError(
                f"WORKSPACES 存在重复的 Workspace id：{', '.join(map(str, sorted(duplicate_ids)))}"
            )

        workspace_names = [workspace.name for workspace in self.workspaces]

        duplicate_names = {
            workspace_name
            for workspace_name in workspace_names
            if workspace_names.count(workspace_name) > 1
        }

        if duplicate_names:
            raise ValueError(
                f"WORKSPACES 存在重复的 Workspace name：{', '.join(sorted(duplicate_names))}"
            )

        return self

    @model_validator(mode="after")
    def _validate_dataworks_use_types(
        self,
    ) -> Settings:
        """校验 DataWorks UseType 配置。"""

        allowed_use_types = {
            "NORMAL",
            "MANUAL",
            "MANUAL_BIZ",
            "SKIP",
            "ADHOCQUERY",
            "COMPONENT",
        }

        self.dataworks_use_types = [
            use_type.strip().upper() for use_type in self.dataworks_use_types if use_type.strip()
        ]

        # 空配置表示获取全部 UseType，
        # 不进行过滤。
        if not self.dataworks_use_types:
            return self

        invalid_use_types = [
            use_type for use_type in self.dataworks_use_types if use_type not in allowed_use_types
        ]

        if invalid_use_types:
            raise ValueError(
                "DATAWORKS_USE_TYPES 包含不支持的 UseType："
                f"{', '.join(invalid_use_types)}；"
                "支持的值："
                f"{', '.join(sorted(allowed_use_types))}"
            )

        # 去重，同时保持配置顺序。
        self.dataworks_use_types = list(dict.fromkeys(self.dataworks_use_types))

        return self

    @model_validator(mode="after")
    def _resolve_paths(self) -> Settings:
        """
        将项目相关路径统一解析为绝对路径。

        这样业务代码拿到的 settings.source_dir
        永远是绝对路径，不再依赖当前 Working Directory。
        """
        self.source_dir = resolve_project_path(self.source_dir)
        self.analysis_dir = resolve_project_path(self.analysis_dir)
        self.layer_rules_path = resolve_project_path(self.layer_rules_path)
        self.business_rules_path = resolve_project_path(self.business_rules_path)
        self.process_rules_path = resolve_project_path(self.process_rules_path)

        return self

    # ========================================================
    # Workspace selection
    # ========================================================

    def select_workspaces(
        self,
        workspace_id: int | None = None,
    ) -> list[WorkspaceSettings]:
        """
        解析本次要采集的 Workspace 列表。

        workspace_id 为 None：
            返回全部 Workspace。

        workspace_id 不为 None：
            返回指定 Workspace。

        指定但未配置的 Workspace：
            直接报错（fail-fast）。
        """

        if workspace_id is None:
            return list(self.workspaces)

        matched = [workspace for workspace in self.workspaces if workspace.id == workspace_id]

        if not matched:
            raise ValueError(f"未配置的 Workspace id：{workspace_id}（不在 WORKSPACES 中）")

        return matched


# ============================================================
# Settings lifecycle
# ============================================================

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
        return getattr(
            get_settings(),
            name,
        )


# 全局配置实例（惰性）。
settings = _SettingsProxy()

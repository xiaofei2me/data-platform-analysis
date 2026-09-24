"""项目配置。"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """项目运行配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
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

    # DataWorks 工作空间 / 项目 ID。
    dataworks_project_id: int

    # DataWorks 工作空间标识。
    #
    # 当前版本暂时保留，后续如果某些 API 需要 ProjectIdentifier，
    # 可以直接使用这个配置。
    dataworks_project_identifier: str | None = None

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


# 全局配置实例。
settings = Settings()
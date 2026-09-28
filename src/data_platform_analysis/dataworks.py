"""DataWorks 数据采集。"""

from __future__ import annotations

import logging
from typing import Any

from alibabacloud_dataworks_public20200518 import models
from alibabacloud_dataworks_public20200518.client import Client
from alibabacloud_tea_openapi.models import Config
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    wait_exponential,
)
from tenacity.stop import stop_base

from .config import get_settings, settings

logger = logging.getLogger(__name__)


class _stop_after_configured_retries(stop_base):
    """按当前配置的最大重试次数停止。"""

    def __call__(
        self,
        retry_state: RetryCallState,
    ) -> bool:
        return (
            retry_state.attempt_number
            >= get_settings().dataworks_max_retries + 1
        )


_stop_after_configured_retries_instance = (
    _stop_after_configured_retries()
)


class DataWorksClient:
    """
    DataWorks OpenAPI 客户端。

    当前版本负责：

    1. 获取 Workspace 下的 File 列表
    2. 获取单个 File 详情

    使用 DataWorks Public API 2020-05-18。

    原始 API Response 会完整保存，
    后续可以基于 Snapshot 重新分析。
    """

    def __init__(self) -> None:
        """初始化 DataWorks OpenAPI 客户端。"""

        config = Config(
            access_key_id=(
                settings.alibaba_cloud_access_key_id
            ),
            access_key_secret=(
                settings.alibaba_cloud_access_key_secret
            ),
            region_id=settings.dataworks_region,
        )

        self.client = Client(config)

    # ========================================================
    # ListFiles
    # ========================================================

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=_stop_after_configured_retries_instance,
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=8,
        ),
        reraise=True,
    )
    def _list_files_page(
            self,
            workspace_id: int,
            page_number: int,
            use_type: str | None = None,
    ) -> dict[str, Any]:
        request = models.ListFilesRequest(
            project_id=workspace_id,
            page_number=page_number,
            page_size=settings.dataworks_page_size,
        )

        if use_type:
            request.use_type = use_type

        logger.debug(
            "调用 DataWorks ListFiles："
            "workspace_id=%s，page=%s，page_size=%s，use_type=%s",
            workspace_id,
            page_number,
            settings.dataworks_page_size,
            use_type or "ALL",
        )

        response = self.client.list_files(request)

        return response.body.to_map()

    # ========================================================
    # GetFile
    # ========================================================

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=_stop_after_configured_retries_instance,
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=8,
        ),
        reraise=True,
    )
    def get_file(
        self,
        workspace_id: int,
        file_id: int,
    ) -> dict[str, Any]:
        """获取 DataWorks 单个文件的完整详情。"""

        request = models.GetFileRequest(
            project_id=workspace_id,
            file_id=file_id,
        )

        logger.debug(
            "调用 DataWorks GetFile："
            "workspace_id=%s，"
            "file_id=%s",
            workspace_id,
            file_id,
        )

        response = self.client.get_file(
            request
        )

        return response.body.to_map()

    def list_files(
            self,
            workspace_id: int,
    ) -> list[dict[str, Any]]:
        """
        获取指定 DataWorks Workspace 下的 File。

        DATAWORKS_USE_TYPES 为空：
            不传 UseType，一次获取全部文件。

        DATAWORKS_USE_TYPES 有值：
            按 UseType 分别调用 ListFiles，
            将各 UseType 返回的文件直接合并。
        """
        all_files: list[dict[str, Any]] = []

        # 未配置 UseType 时，不传 UseType，获取全部文件。
        use_types: list[str | None] = (
            settings.dataworks_use_types
            if settings.dataworks_use_types
            else [None]
        )

        for use_type in use_types:
            page_number = 1
            use_type_file_count = 0

            while True:
                response = self._list_files_page(
                    workspace_id=workspace_id,
                    page_number=page_number,
                    use_type=use_type,
                )

                data = self._find_first_dict(
                    response,
                    keys={"Data", "data"},
                )

                if data is None:
                    data = response

                page_files = self._extract_file_list(data)

                logger.info(
                    "DataWorks Workspace %s "
                    "UseType=%s 第 %s 页获取到 %s 个文件",
                    workspace_id,
                    use_type or "ALL",
                    page_number,
                    len(page_files),
                )

                if not page_files:
                    break

                all_files.extend(page_files)
                use_type_file_count += len(page_files)

                total_count = self._extract_int(
                    data,
                    keys={
                        "TotalCount",
                        "totalCount",
                        "Total",
                        "total",
                    },
                )

                # 当前 UseType 已经获取完成。
                if (
                        total_count is not None
                        and use_type_file_count >= total_count
                ):
                    break

                # 当前页不足 page_size，说明已经是最后一页。
                if len(page_files) < settings.dataworks_page_size:
                    break

                page_number += 1

        logger.info(
            "DataWorks Workspace %s 文件采集完成："
            "UseType=%s，共 %s 个文件",
            workspace_id,
            ",".join(settings.dataworks_use_types)
            if settings.dataworks_use_types
            else "ALL",
            len(all_files),
        )

        return all_files

    @staticmethod
    def _extract_file_list(
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """从 DataWorks Response 中提取 File 列表。"""

        candidate_keys = (
            "Files",
            "files",
            "FileList",
            "fileList",
            "Items",
            "items",
        )

        for key in candidate_keys:
            value = data.get(key)

            if isinstance(value, list):
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

        result = DataWorksClient._find_list_of_dicts(
            data,
            required_any_keys={
                "FileId",
                "fileId",
                "FileName",
                "fileName",
            },
        )

        return result or []

    @staticmethod
    def _find_first_dict(
        value: Any,
        *,
        keys: set[str],
    ) -> dict[str, Any] | None:
        """递归查找第一个包含目标字段的字典。"""

        if isinstance(value, dict):
            if any(
                key in value
                for key in keys
            ):
                return value

            for child in value.values():
                result = (
                    DataWorksClient._find_first_dict(
                        child,
                        keys=keys,
                    )
                )

                if result is not None:
                    return result

        elif isinstance(value, list):
            for child in value:
                result = (
                    DataWorksClient._find_first_dict(
                        child,
                        keys=keys,
                    )
                )

                if result is not None:
                    return result

        return None

    @staticmethod
    def _find_list_of_dicts(
        value: Any,
        *,
        required_any_keys: set[str],
    ) -> list[dict[str, Any]] | None:
        """递归寻找可能的 File 对象列表。"""

        if isinstance(value, dict):
            for child in value.values():
                result = (
                    DataWorksClient._find_list_of_dicts(
                        child,
                        required_any_keys=required_any_keys,
                    )
                )

                if result is not None:
                    return result

        elif isinstance(value, list):
            dictionaries = [
                item
                for item in value
                if isinstance(item, dict)
            ]

            if dictionaries:
                if any(
                    any(
                        key in item
                        for key in required_any_keys
                    )
                    for item in dictionaries
                ):
                    return dictionaries

            for child in value:
                result = (
                    DataWorksClient._find_list_of_dicts(
                        child,
                        required_any_keys=required_any_keys,
                    )
                )

                if result is not None:
                    return result

        return None

    @staticmethod
    def _extract_int(
        data: dict[str, Any],
        *,
        keys: set[str],
    ) -> int | None:
        """从字典中提取整数值。"""

        for key in keys:
            value = data.get(key)

            if isinstance(value, int):
                return value

            if (
                isinstance(value, str)
                and value.isdigit()
            ):
                return int(value)

        return None


# ============================================================
# File 字段提取
# ============================================================


def extract_file_id(
    file: dict[str, Any],
) -> str | None:
    """从 DataWorks File 对象中提取 File ID。"""

    value = file.get("FileId")

    if value is not None:
        return str(value)

    return None


def extract_file_name(
    file: dict[str, Any],
) -> str | None:
    """从 DataWorks File 对象中提取 File Name。"""

    value = file.get("FileName")

    if value is not None:
        return str(value)

    return None


def extract_file_type(
    file: dict[str, Any],
) -> int | None:
    """从 DataWorks File 对象中提取 FileType。"""

    value = file.get("FileType")

    if isinstance(value, int):
        return value

    if (
        isinstance(value, str)
        and value.isdigit()
    ):
        return int(value)

    return None


def extract_use_type(
    file: dict[str, Any],
) -> str | None:
    """从 DataWorks File 对象中提取 UseType。"""

    value = file.get("UseType")

    if value is None:
        return None

    return str(value)


# ============================================================
# File Content
# ============================================================


def extract_file_content(
    file_detail: dict[str, Any],
) -> str | None:
    """
    从 GetFile 返回结果中提取 File.Content。

    兼容：

        Data.File.Content
        File.Content
        Content
    """

    data = file_detail.get("Data")

    if isinstance(data, dict):
        file_data = data.get("File")

        if isinstance(file_data, dict):
            content = file_data.get("Content")

            if isinstance(content, str):
                return content

    file_data = file_detail.get("File")

    if isinstance(file_data, dict):
        content = file_data.get("Content")

        if isinstance(content, str):
            return content

    content = file_detail.get("Content")

    if isinstance(content, str):
        return content

    return None
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
    """按当前配置的最大重试次数停止。

    在调用时读取配置，而不是 import 时读取，
    以配合惰性配置加载。
    """

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

    这里不会过早对 DataWorks 数据做业务分析。

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
    ) -> dict[str, Any]:
        """获取 DataWorks 指定页的文件。"""

        request = models.ListFilesRequest(
            project_id=workspace_id,
            page_number=page_number,
            page_size=settings.dataworks_page_size,
        )

        logger.debug(
            "调用 DataWorks ListFiles："
            "workspace_id=%s，page=%s，page_size=%s",
            workspace_id,
            page_number,
            settings.dataworks_page_size,
        )

        response = self.client.list_files(request)

        return response.body.to_map()

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
            "workspace_id=%s，file_id=%s",
            workspace_id,
            file_id,
        )

        response = self.client.get_file(request)

        return response.body.to_map()

    def list_files(
        self,
        workspace_id: int,
    ) -> list[dict[str, Any]]:
        """
        获取指定 DataWorks Workspace 的全部 File。

        这里统一处理分页，调用方不需要关心分页逻辑。
        """

        all_files: list[dict[str, Any]] = []
        page_number = 1

        while True:
            response = self._list_files_page(
                workspace_id,
                page_number,
            )

            # 不同 API Response 结构可能存在差异。
            # 优先寻找 Data/data，如果不存在则直接使用 Response。
            data = self._find_first_dict(
                response,
                keys={
                    "Data",
                    "data",
                },
            )

            if data is None:
                data = response

            page_files = self._extract_file_list(data)

            logger.info(
                "DataWorks 第 %s 页获取到 %s 个文件",
                page_number,
                len(page_files),
            )

            if not page_files:
                break

            all_files.extend(page_files)

            total_count = self._extract_int(
                data,
                keys={
                    "TotalCount",
                    "totalCount",
                    "Total",
                    "total",
                },
            )

            # 如果 API 返回总数量，并且已经获取完毕，
            # 则不需要继续请求下一页。
            if (
                total_count is not None
                and len(all_files) >= total_count
            ):
                break

            # 如果当前页不足 page_size，
            # 说明已经到最后一页。
            if (
                len(page_files)
                < settings.dataworks_page_size
            ):
                break

            page_number += 1

        logger.info(
            "DataWorks Workspace %s 文件采集完成，共 %s 个文件",
            workspace_id,
            len(all_files),
        )

        return all_files

    @staticmethod
    def _extract_file_list(
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        从 DataWorks Response 中提取 File 列表。

        优先使用常见字段。
        如果没有找到，则进行递归搜索。
        """

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

        # 兼容实际 API 返回的其它结构。
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


def extract_file_content(
    file_detail: dict[str, Any],
) -> str | None:
    """
    从 GetFile 返回结果中提取 File.Content。

    兼容不同 Response 包装结构：

    1. Data.File.Content
    2. File.Content
    3. Content
    """

    # ========================================================
    # 结构 1
    #
    # {
    #     "Data": {
    #         "File": {
    #             "Content": "..."
    #         }
    #     }
    # }
    # ========================================================

    data = file_detail.get("Data")

    if isinstance(data, dict):
        file_data = data.get("File")

        if isinstance(file_data, dict):
            content = file_data.get("Content")

            if isinstance(content, str):
                return content

    # ========================================================
    # 结构 2
    #
    # {
    #     "File": {
    #         "Content": "..."
    #     }
    # }
    # ========================================================

    file_data = file_detail.get("File")

    if isinstance(file_data, dict):
        content = file_data.get("Content")

        if isinstance(content, str):
            return content

    # ========================================================
    # 结构 3
    #
    # {
    #     "Content": "..."
    # }
    # ========================================================

    content = file_detail.get("Content")

    if isinstance(content, str):
        return content

    return None
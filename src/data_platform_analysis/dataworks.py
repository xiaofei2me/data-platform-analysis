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

    在调用时读取配置（而非 import 时），
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

    当前版本只负责：

    1. 获取节点列表
    2. 获取节点详情

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
            "调用 DataWorks ListFiles：workspace_id=%s，page=%s，page_size=%s",
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
            "调用 DataWorks GetFile：workspace_id=%s，file_id=%s",
            workspace_id,
            file_id,
        )

        response = self.client.get_file(
            request
        )

        return response.body.to_map()

    def list_files(
        self,
        project_id: int,
    ) -> list[dict[str, Any]]:
        """
        获取指定 DataWorks Workspace 的全部节点。
        这里统一处理分页，调用方不需要关心分页逻辑。
        """

        all_nodes: list[dict[str, Any]] = []
        page_number = 1

        while True:
            response = self._list_files_page(project_id, page_number,)

            # 不同接口返回结构可能存在差异。
            # 优先寻找 Data/data，如果不存在则直接使用 Response。
            data = self._find_first_dict(
                response,
                keys={"Data", "data",},
            )

            if data is None:
                data = response

            page_nodes = self._extract_node_list(
                data
            )

            logger.info("DataWorks 第 %s 页获取到 %s 个节点", page_number, len(page_nodes),)

            if not page_nodes:
                break

            all_nodes.extend(page_nodes)

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
                and len(all_nodes) >= total_count
            ):
                break

            # 如果当前页不足 page_size，
            # 说明已经到最后一页。
            if (
                len(page_nodes)
                < settings.dataworks_page_size
            ):
                break

            page_number += 1

            logger.info(
                "DataWorks Workspace %s 节点采集完成，共 %s 个节点",
                project_id,
                len(all_nodes),
            )

            return all_nodes

    @staticmethod
    def _extract_node_list(
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        从 DataWorks Response 中提取节点列表。

        优先使用常见字段。
        如果没有找到，则进行递归搜索。
        """

        candidate_keys = (
            "Nodes",
            "nodes",
            "NodeList",
            "nodeList",
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

        # 兜底：递归寻找包含节点特征字段的对象列表。
        result = DataWorksClient._find_list_of_dicts(
            data,
            required_any_keys={
                "NodeId",
                "nodeId",
                "NodeName",
                "nodeName",
                "Name",
                "name",
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
        """递归寻找可能的节点对象列表。"""

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
                # 只要列表中的对象有一个包含节点特征字段，
                # 就认为它可能是节点列表。
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


def extract_node_id(
    node: dict[str, Any],
) -> str | None:
    """从节点对象中提取 Node ID。"""

    for key in (
        "FileId",
    ):
        value = node.get(key)

        if value is not None:
            return str(value)
    return None


def extract_node_name(
    node: dict[str, Any],
) -> str | None:
    """从节点对象中提取节点名称。"""

    for key in (
        "FileName",
    ):
        value = node.get(key)
        if value is not None:
            return str(value)

    return None


def extract_node_type(
    node: dict[str, Any],
) -> str | None:
    """从节点对象中提取节点类型。"""

    for key in (
        "NodeType",
        "nodeType",
        "Type",
        "type",
    ):
        value = node.get(key)

        if value is not None:
            return str(value)

    return None


def recursively_find_strings(
    value: Any,
    target_keys: set[str],
) -> list[str]:
    """
    递归查找指定字段下面的字符串。

    主要用于寻找 DataWorks 节点中的 SQL、Script、Code 等内容。
    """

    results: list[str] = []

    normalized_target_keys = {
        item.lower()
        for item in target_keys
    }

    if isinstance(value, dict):
        for key, child in value.items():
            if (
                key.lower()
                in normalized_target_keys
            ):
                if (
                    isinstance(child, str)
                    and child.strip()
                ):
                    results.append(child)

            results.extend(
                recursively_find_strings(
                    child,
                    target_keys,
                )
            )

    elif isinstance(value, list):
        for child in value:
            results.extend(
                recursively_find_strings(
                    child,
                    target_keys,
                )
            )

    return results


def extract_sql_candidates(
    node_detail: dict[str, Any],
) -> list[str]:
    """
    从节点详情中提取 SQL / Script 候选内容。

    不同 DataWorks 节点类型的代码字段可能不同，
    所以这里采用多个候选字段进行递归搜索。

    注意：
    原始节点 JSON 会完整保存。
    即使这里没有成功提取 SQL，
    后续也可以重新基于原始 JSON 进行分析。
    """

    candidates = recursively_find_strings(
        node_detail,
        {
            "Script",
            "script",
            "Sql",
            "sql",
            "Code",
            "code",
            "Content",
            "content",
            "ScriptContent",
            "scriptContent",
            "SqlScript",
            "sqlScript",
        },
    )

    # 去重，同时保持原始出现顺序。
    seen: set[str] = set()

    result: list[str] = []

    for candidate in candidates:
        normalized = candidate.strip()

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        result.append(normalized)

    return result
"""DataWorks FileType 类型注册表的单元测试。

覆盖四件事：
1. 本次新增的 file_type 都能查到，且各字段符合官方节点定义与本地证据；
2. file_type=23 等既有映射保持不变（防止新增覆盖旧定义）；
3. 注册表不重复注册同一个 file_type；
4. 未注册类型与 None 仍然安全降级为 UNKNOWN。

预期值直接写字符串字面量，不引用 dataworks_types 的常量，
避免常量被改写时测试跟着一起错。
"""

from __future__ import annotations

import pytest

from data_platform_analysis.dataworks_types import (
    FILE_TYPE_REGISTRY,
    UNKNOWN_FILE_TYPE,
    get_file_type,
    get_file_type_info,
)

# ============================================================
# 本次新增（官方节点文档核实 + 当前 Snapshot 样本证据）
# ============================================================

NEW_FILE_TYPES: list[tuple[int, str, str, str, str, str]] = [
    # file_type, name, task_type, category, content_format, extension
    (99, "VIRTUAL", "VIRTUAL", "TASK", "NONE", "txt"),
    (241, "CHECK", "CHECK", "TASK", "JSON", "json"),
    (1101, "BRANCH", "BRANCH", "TASK", "JSON", "json"),
    (1103, "DO_WHILE", "DO_WHILE", "TASK", "NONE", "txt"),
    (1106, "FOR_EACH", "FOR_EACH", "TASK", "NONE", "txt"),
    (1115, "PARAM_HUB", "PARAM_HUB", "TASK", "NONE", "txt"),
    # 官方节点类型已确认，当前 Snapshot 无样本 → content_format 保持 UNKNOWN
    (1102, "MERGE", "MERGE", "TASK", "UNKNOWN", "txt"),
    (1114, "HTTP_TRIGGER", "HTTP_TRIGGER", "TASK", "UNKNOWN", "txt"),
    (1331, "DATA_COMPARISON", "DATA_COMPARISON", "TASK", "UNKNOWN", "txt"),
    (1333, "DATA_QUALITY_MONITOR", "DATA_QUALITY_MONITOR", "TASK", "UNKNOWN", "txt"),
]

# ============================================================
# 既有映射（修改前已注册，不得被新增覆盖或改写语义）
# ============================================================

EXISTING_FILE_TYPES: list[tuple[int, str, str, str, str, str]] = [
    (6, "SHELL", "SHELL", "TASK", "SHELL", "sh"),
    (10, "ODPS_SQL", "ODPS_SQL", "TASK", "SQL", "sql"),
    (11, "ODPS_MR", "ODPS_MR", "TASK", "UNKNOWN", "txt"),
    (23, "OFFLINE_SYNC", "OFFLINE_SYNC", "TASK", "JSON", "json"),
    (24, "ODPS_SCRIPT", "ODPS_SCRIPT", "TASK", "SQL", "sql"),
    (12, "PYTHON", "RESOURCE", "RESOURCE", "PYTHON", "py"),
    (13, "JAR", "RESOURCE", "RESOURCE", "BINARY", "jar"),
    (14, "ZIP", "RESOURCE", "RESOURCE", "BINARY", "zip"),
    (15, "FILE", "RESOURCE", "RESOURCE", "BINARY", "txt"),
    (17, "UDF", "RESOURCE", "RESOURCE", "JSON", "json"),
    (221, "PYODPS2", "PYODPS2", "TASK", "PYTHON", "py"),
    (225, "ODPS_SPARK", "ODPS_SPARK", "TASK", "UNKNOWN", "txt"),
    (227, "EMR_HIVE", "EMR_HIVE", "TASK", "SQL", "sql"),
    (228, "EMR_SPARK", "EMR_SPARK", "TASK", "UNKNOWN", "txt"),
    (229, "EMR_SPARK_SQL", "EMR_SPARK_SQL", "TASK", "SQL", "sql"),
    (230, "EMR_MR", "EMR_MR", "TASK", "UNKNOWN", "txt"),
    (239, "OSS_OBJECT_CHECK", "OSS_OBJECT_CHECK", "TASK", "NONE", "txt"),
    (257, "EMR_SHELL", "EMR_SHELL", "TASK", "SHELL", "sh"),
    (258, "EMR_SPARK_SHELL", "EMR_SPARK_SHELL", "TASK", "SHELL", "sh"),
    (259, "EMR_PRESTO", "EMR_PRESTO", "TASK", "SQL", "sql"),
    (260, "EMR_IMPALA", "EMR_IMPALA", "TASK", "SQL", "sql"),
    (267, "EMR_TRINO", "EMR_TRINO", "TASK", "SQL", "sql"),
    (900, "REALTIME_SYNC", "REALTIME_SYNC", "TASK", "JSON", "json"),
    (1026, "TASK_FLOW", "TASK_FLOW", "TASK", "NONE", "txt"),
    (1089, "CROSS_TENANT", "CROSS_TENANT", "TASK", "JSON", "json"),
    (1091, "HOLOGRES_DEVELOPMENT", "HOLOGRES_DEVELOPMENT", "TASK", "UNKNOWN", "txt"),
    (1093, "HOLOGRES_SQL", "HOLOGRES_SQL", "TASK", "SQL", "sql"),
    (1100, "ASSIGNMENT", "ASSIGNMENT", "TASK", "JSON", "json"),
    (1221, "PYODPS3", "PYODPS3", "TASK", "PYTHON", "py"),
    (1301, "CLICKHOUSE_SQL", "CLICKHOUSE_SQL", "TASK", "SQL", "sql"),
    (1330, "FUNCTION_COMPUTE", "FUNCTION_COMPUTE", "TASK", "JSON", "json"),
]


# ============================================================
# 1. 新增类型可查，字段符合核实后的定义
# ============================================================


@pytest.mark.parametrize(
    ("file_type", "name", "task_type", "category", "content_format", "extension"),
    NEW_FILE_TYPES,
    ids=[str(item[0]) for item in NEW_FILE_TYPES],
)
def test_new_file_types_registered(
    file_type: int,
    name: str,
    task_type: str,
    category: str,
    content_format: str,
    extension: str,
) -> None:
    """本次新增的 file_type 能查到，且五个字段与核实结果一致。"""

    info = get_file_type(file_type)

    assert info is FILE_TYPE_REGISTRY[file_type]
    assert info.file_type == file_type
    assert info.name == name
    assert info.task_type == task_type
    assert info.category == category
    assert info.content_format == content_format
    assert info.extension == extension
    assert info.description


@pytest.mark.parametrize(
    "file_type",
    [item[0] for item in NEW_FILE_TYPES],
    ids=[str(item[0]) for item in NEW_FILE_TYPES],
)
def test_new_file_types_are_not_unknown(file_type: int) -> None:
    """新增类型不再落到 UNKNOWN 兜底。"""

    info = get_file_type(file_type)

    assert info is not UNKNOWN_FILE_TYPE
    assert info.name != "UNKNOWN"
    assert info.task_type != "UNKNOWN"
    assert info.category == "TASK"


def test_new_file_types_use_official_node_task_types() -> None:
    """新增类型复用 TASK_TYPE_* 常量，且与官方 TaskType 语义一致。"""

    from data_platform_analysis.dataworks_types import (
        TASK_TYPE_BRANCH,
        TASK_TYPE_CHECK,
        TASK_TYPE_DATA_COMPARISON,
        TASK_TYPE_DATA_QUALITY_MONITOR,
        TASK_TYPE_DO_WHILE,
        TASK_TYPE_FOR_EACH,
        TASK_TYPE_HTTP_TRIGGER,
        TASK_TYPE_MERGE,
        TASK_TYPE_PARAM_HUB,
        TASK_TYPE_VIRTUAL,
    )

    assert FILE_TYPE_REGISTRY[99].task_type == TASK_TYPE_VIRTUAL
    assert FILE_TYPE_REGISTRY[241].task_type == TASK_TYPE_CHECK
    assert FILE_TYPE_REGISTRY[1101].task_type == TASK_TYPE_BRANCH
    assert FILE_TYPE_REGISTRY[1102].task_type == TASK_TYPE_MERGE
    assert FILE_TYPE_REGISTRY[1103].task_type == TASK_TYPE_DO_WHILE
    assert FILE_TYPE_REGISTRY[1106].task_type == TASK_TYPE_FOR_EACH
    assert FILE_TYPE_REGISTRY[1114].task_type == TASK_TYPE_HTTP_TRIGGER
    assert FILE_TYPE_REGISTRY[1115].task_type == TASK_TYPE_PARAM_HUB
    assert FILE_TYPE_REGISTRY[1331].task_type == TASK_TYPE_DATA_COMPARISON
    assert FILE_TYPE_REGISTRY[1333].task_type == TASK_TYPE_DATA_QUALITY_MONITOR


# ============================================================
# 2. 既有映射不回归（含 file_type=23）
# ============================================================


@pytest.mark.parametrize(
    ("file_type", "name", "task_type", "category", "content_format", "extension"),
    EXISTING_FILE_TYPES,
    ids=[str(item[0]) for item in EXISTING_FILE_TYPES],
)
def test_existing_file_types_unchanged(
    file_type: int,
    name: str,
    task_type: str,
    category: str,
    content_format: str,
    extension: str,
) -> None:
    """修改前已注册的类型保持原语义，未被新增条目覆盖。"""

    info = get_file_type(file_type)

    assert info is FILE_TYPE_REGISTRY[file_type]
    assert info.file_type == file_type
    assert info.name == name
    assert info.task_type == task_type
    assert info.category == category
    assert info.content_format == content_format
    assert info.extension == extension


def test_file_type_23_offline_sync_preserved() -> None:
    """file_type=23 的既有 OFFLINE_SYNC 定义必须保持正确。"""

    info = get_file_type(23)

    assert info.file_type == 23
    assert info.name == "OFFLINE_SYNC"
    assert info.task_type == "OFFLINE_SYNC"
    assert info.category == "TASK"
    assert info.content_format == "JSON"
    assert info.extension == "json"


# ============================================================
# 3. 注册表完整性：不重复、键值一致
# ============================================================


def test_registry_has_no_duplicate_file_type() -> None:
    """注册表不重复注册同一个 file_type，键与 FileTypeInfo.file_type 一致。"""

    file_types = [info.file_type for info in FILE_TYPE_REGISTRY.values()]

    assert len(file_types) == len(set(file_types))
    assert all(key == info.file_type for key, info in FILE_TYPE_REGISTRY.items())


def test_registry_has_no_duplicate_name() -> None:
    """注册表不存在两个 file_type 共用同一个 name。"""

    names = [info.name for info in FILE_TYPE_REGISTRY.values()]

    assert len(names) == len(set(names))


def test_new_file_types_do_not_collide_with_existing_keys() -> None:
    """新增编号不与既有编号冲突（dict 字面量重复键会静默覆盖）。"""

    existing_keys = {item[0] for item in EXISTING_FILE_TYPES}
    new_keys = {item[0] for item in NEW_FILE_TYPES}

    assert existing_keys.isdisjoint(new_keys)
    assert existing_keys | new_keys <= set(FILE_TYPE_REGISTRY)


# ============================================================
# 4. UNKNOWN 兜底保留
# ============================================================


@pytest.mark.parametrize("file_type", [999, 123456, -2, 264, 1010])
def test_unregistered_file_type_returns_unknown(file_type: int) -> None:
    """未注册的 file_type 仍然返回约定的 UNKNOWN 结果。"""

    info = get_file_type(file_type)

    assert info is UNKNOWN_FILE_TYPE
    assert info.file_type == -1
    assert info.name == "UNKNOWN"
    assert info.task_type == "UNKNOWN"
    assert info.category == "UNKNOWN"
    assert info.content_format == "UNKNOWN"
    assert info.extension == "txt"


@pytest.mark.parametrize("file_type", [None])
def test_none_file_type_returns_unknown(file_type: int | None) -> None:
    """file_type 缺失（None）不抛异常，返回 UNKNOWN。"""

    assert get_file_type(file_type) is UNKNOWN_FILE_TYPE
    assert get_file_type_info(file_type) is UNKNOWN_FILE_TYPE


def test_get_file_type_info_matches_get_file_type() -> None:
    """两个查询接口对已注册与未注册类型的行为一致。"""

    for file_type in (10, 99, 1101, 999999):
        assert get_file_type_info(file_type) is get_file_type(file_type)

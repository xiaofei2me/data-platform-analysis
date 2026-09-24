"""DataWorks File 类型定义。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataWorksFileType:
    """DataWorks File 类型。"""

    file_type: int
    name: str
    task_type: str | None
    category: str
    content_format: str
    extension: str


# ============================================================
# DataWorks FileType Registry
# ============================================================
#
# FileType 来自 DataWorks API。
#
# 这里额外维护分析层需要的语义：
#
# FileType
#     ↓
# TaskType
#     ↓
# Category
#     ↓
# Content Format
#     ↓
# File Extension
#
# 注意：
#
# 1. 原始 FileType 永远保留
# 2. 未知 FileType 不应该导致 Snapshot 失败
# 3. 未知 FileType 不使用 .txt，避免掩盖类型识别问题
# 4. Content 是否存在与 FileType 是两个独立概念
#

DATAWORKS_FILE_TYPES: dict[int, DataWorksFileType] = {
    # ========================================================
    # Shell
    # ========================================================

    6: DataWorksFileType(
        file_type=6,
        name="Shell",
        task_type="SHELL",
        category="general",
        content_format="shell",
        extension=".sh",
    ),

    # ========================================================
    # MaxCompute / ODPS
    # ========================================================

    10: DataWorksFileType(
        file_type=10,
        name="ODPS SQL",
        task_type="ODPS_SQL",
        category="engine",
        content_format="sql",
        extension=".sql",
    ),

    11: DataWorksFileType(
        file_type=11,
        name="ODPS MR",
        task_type="ODPS_MR",
        category="engine",
        content_format="java",
        extension=".java",
    ),

    24: DataWorksFileType(
        file_type=24,
        name="ODPS Script",
        task_type="ODPS_SCRIPT",
        category="engine",
        content_format="script",
        extension=".py",
    ),

    # ========================================================
    # Data Integration
    # ========================================================

    23: DataWorksFileType(
        file_type=23,
        name="离线同步",
        task_type="DI",
        category="data_integration",
        content_format="json",
        extension=".json",
    ),

    900: DataWorksFileType(
        file_type=900,
        name="实时同步",
        task_type="RI",
        category="data_integration",
        content_format="json",
        extension=".json",
    ),

    # ========================================================
    # PyODPS
    # ========================================================

    221: DataWorksFileType(
        file_type=221,
        name="PyODPS 2",
        task_type="PYODPS2",
        category="engine",
        content_format="python",
        extension=".py",
    ),

    1221: DataWorksFileType(
        file_type=1221,
        name="PyODPS 3",
        task_type="PYODPS3",
        category="engine",
        content_format="python",
        extension=".py",
    ),

    # ========================================================
    # EMR
    # ========================================================

    227: DataWorksFileType(
        file_type=227,
        name="EMR Hive",
        task_type="EMR_HIVE",
        category="engine",
        content_format="sql",
        extension=".sql",
    ),

    228: DataWorksFileType(
        file_type=228,
        name="EMR Spark",
        task_type="EMR_SPARK",
        category="engine",
        content_format="python",
        extension=".py",
    ),

    229: DataWorksFileType(
        file_type=229,
        name="EMR Spark SQL",
        task_type="EMR_SPARK_SQL",
        category="engine",
        content_format="sql",
        extension=".sql",
    ),

    257: DataWorksFileType(
        file_type=257,
        name="EMR Shell",
        task_type="EMR_SHELL",
        category="engine",
        content_format="shell",
        extension=".sh",
    ),

    259: DataWorksFileType(
        file_type=259,
        name="EMR Presto",
        task_type="EMR_PRESTO",
        category="engine",
        content_format="sql",
        extension=".sql",
    ),

    260: DataWorksFileType(
        file_type=260,
        name="EMR Impala",
        task_type="EMR_IMPALA",
        category="engine",
        content_format="sql",
        extension=".sql",
    ),

    267: DataWorksFileType(
        file_type=267,
        name="EMR Trino",
        task_type="EMR_TRINO",
        category="engine",
        content_format="sql",
        extension=".sql",
    ),

    # ========================================================
    # Other SQL Engines
    # ========================================================

    1093: DataWorksFileType(
        file_type=1093,
        name="Hologres SQL",
        task_type="HOLOGRES_SQL",
        category="engine",
        content_format="sql",
        extension=".sql",
    ),

    1301: DataWorksFileType(
        file_type=1301,
        name="ClickHouse SQL",
        task_type="CLICKHOUSE_SQL",
        category="engine",
        content_format="sql",
        extension=".sql",
    ),
}


def get_file_type(
    file_type: int | None,
) -> DataWorksFileType:
    """
    根据 DataWorks FileType 获取类型定义。

    未知 FileType 不抛异常。

    未知类型使用 .unknown，而不是 .txt，
    防止类型识别失败被错误地当成普通文本。
    """

    if file_type is None:
        return DataWorksFileType(
            file_type=-1,
            name="Unknown",
            task_type=None,
            category="unknown",
            content_format="unknown",
            extension=".unknown",
        )

    return DATAWORKS_FILE_TYPES.get(
        file_type,
        DataWorksFileType(
            file_type=file_type,
            name=f"Unknown ({file_type})",
            task_type=None,
            category="unknown",
            content_format="unknown",
            extension=".unknown",
        ),
    )
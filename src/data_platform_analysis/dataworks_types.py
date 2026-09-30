"""DataWorks FileType 语义定义。

本模块负责定义 DataWorks FileType 的语义信息。

设计原则：
1. FileType 是 DataWorks 文件/任务的类型编码。
2. File 不等于 Task，ListFiles 返回的数据可能同时包含 Task 和 Resource。
3. category 用于区分 TASK / RESOURCE / UNKNOWN。
4. task_type 用于提供稳定的分析层任务类型。
5. content_format 用于描述 GetFile 返回的 Content 应如何理解。
6. extension 始终为字符串，保证现有 export.py 可以直接调用 lstrip()。
7. 未知 FileType 必须安全降级，不阻断整个 Workspace 采集。
"""

from dataclasses import dataclass

# ============================================================================
# Category
# ============================================================================

CATEGORY_TASK = "TASK"
"""DataWorks 任务文件。"""

CATEGORY_RESOURCE = "RESOURCE"
"""DataWorks 资源文件。"""

CATEGORY_UNKNOWN = "UNKNOWN"
"""未知类型。"""


# ============================================================================
# Task Type
# ============================================================================

TASK_TYPE_SHELL = "SHELL"
TASK_TYPE_ODPS_SQL = "ODPS_SQL"
TASK_TYPE_ODPS_MR = "ODPS_MR"
TASK_TYPE_ODPS_SCRIPT = "ODPS_SCRIPT"
TASK_TYPE_PYODPS2 = "PYODPS2"
TASK_TYPE_PYODPS3 = "PYODPS3"
TASK_TYPE_ODPS_SPARK = "ODPS_SPARK"

TASK_TYPE_EMR_HIVE = "EMR_HIVE"
TASK_TYPE_EMR_SPARK = "EMR_SPARK"
TASK_TYPE_EMR_SPARK_SQL = "EMR_SPARK_SQL"
TASK_TYPE_EMR_MR = "EMR_MR"
TASK_TYPE_EMR_SHELL = "EMR_SHELL"
TASK_TYPE_EMR_SPARK_SHELL = "EMR_SPARK_SHELL"
TASK_TYPE_EMR_PRESTO = "EMR_PRESTO"
TASK_TYPE_EMR_IMPALA = "EMR_IMPALA"
TASK_TYPE_EMR_TRINO = "EMR_TRINO"

TASK_TYPE_OSS_OBJECT_CHECK = "OSS_OBJECT_CHECK"
TASK_TYPE_REALTIME_SYNC = "REALTIME_SYNC"
TASK_TYPE_CROSS_TENANT = "CROSS_TENANT"

TASK_TYPE_HOLOGRES_DEVELOPMENT = "HOLOGRES_DEVELOPMENT"
TASK_TYPE_HOLOGRES_SQL = "HOLOGRES_SQL"
TASK_TYPE_CLICKHOUSE_SQL = "CLICKHOUSE_SQL"

TASK_TYPE_TASK_FLOW = "TASK_FLOW"
TASK_TYPE_ASSIGNMENT = "ASSIGNMENT"
TASK_TYPE_FUNCTION_COMPUTE = "FUNCTION_COMPUTE"

TASK_TYPE_RESOURCE = "RESOURCE"
TASK_TYPE_UNKNOWN = "UNKNOWN"


# ============================================================================
# Content Format
# ============================================================================

CONTENT_NONE = "NONE"
CONTENT_SQL = "SQL"
CONTENT_SHELL = "SHELL"
CONTENT_PYTHON = "PYTHON"
CONTENT_JAVA = "JAVA"
CONTENT_JSON = "JSON"
CONTENT_BINARY = "BINARY"
CONTENT_UNKNOWN = "UNKNOWN"


# ============================================================================
# FileTypeInfo
# ============================================================================


@dataclass(frozen=True)
class FileTypeInfo:
    """DataWorks FileType 的语义信息。"""

    file_type: int
    """DataWorks FileType 编码。"""

    name: str
    """项目内部使用的 FileType 名称。"""

    task_type: str
    """分析层使用的任务类型。"""

    category: str
    """数据类别：TASK / RESOURCE / UNKNOWN。"""

    content_format: str
    """GetFile Content 的语义格式。"""

    extension: str
    """导出 Content 时使用的文件扩展名。

    注意：
    这里不能使用 None，因为当前 export.py 会直接调用：
        file_type_info.extension.lstrip(".")
    """

    description: str = ""
    """FileType 的说明。"""


# ============================================================================
# FileType Registry
# ============================================================================

FILE_TYPE_REGISTRY: dict[int, FileTypeInfo] = {
    # ------------------------------------------------------------------------
    # MaxCompute / ODPS
    # ------------------------------------------------------------------------
    6: FileTypeInfo(
        file_type=6,
        name="SHELL",
        task_type=TASK_TYPE_SHELL,
        category=CATEGORY_TASK,
        content_format=CONTENT_SHELL,
        extension="sh",
        description="Shell 调度任务。",
    ),
    10: FileTypeInfo(
        file_type=10,
        name="ODPS_SQL",
        task_type=TASK_TYPE_ODPS_SQL,
        category=CATEGORY_TASK,
        content_format=CONTENT_SQL,
        extension="sql",
        description="MaxCompute / ODPS SQL 任务。",
    ),
    11: FileTypeInfo(
        file_type=11,
        name="ODPS_MR",
        task_type=TASK_TYPE_ODPS_MR,
        category=CATEGORY_TASK,
        content_format=CONTENT_UNKNOWN,
        extension="txt",
        description="MaxCompute / ODPS MapReduce 任务。",
    ),
    24: FileTypeInfo(
        file_type=24,
        name="ODPS_SCRIPT",
        task_type=TASK_TYPE_ODPS_SCRIPT,
        category=CATEGORY_TASK,
        content_format=CONTENT_SQL,
        extension="sql",
        description="MaxCompute / ODPS Script 任务。",
    ),
    221: FileTypeInfo(
        file_type=221,
        name="PYODPS2",
        task_type=TASK_TYPE_PYODPS2,
        category=CATEGORY_TASK,
        content_format=CONTENT_PYTHON,
        extension="py",
        description="PyODPS 2 任务。",
    ),
    1221: FileTypeInfo(
        file_type=1221,
        name="PYODPS3",
        task_type=TASK_TYPE_PYODPS3,
        category=CATEGORY_TASK,
        content_format=CONTENT_PYTHON,
        extension="py",
        description="PyODPS 3 任务。",
    ),
    225: FileTypeInfo(
        file_type=225,
        name="ODPS_SPARK",
        task_type=TASK_TYPE_ODPS_SPARK,
        category=CATEGORY_TASK,
        content_format=CONTENT_UNKNOWN,
        extension="txt",
        description="MaxCompute / ODPS Spark 任务。",
    ),
    # ------------------------------------------------------------------------
    # EMR
    # ------------------------------------------------------------------------
    227: FileTypeInfo(
        file_type=227,
        name="EMR_HIVE",
        task_type=TASK_TYPE_EMR_HIVE,
        category=CATEGORY_TASK,
        content_format=CONTENT_SQL,
        extension="sql",
        description="EMR Hive 任务。",
    ),
    228: FileTypeInfo(
        file_type=228,
        name="EMR_SPARK",
        task_type=TASK_TYPE_EMR_SPARK,
        category=CATEGORY_TASK,
        content_format=CONTENT_UNKNOWN,
        extension="txt",
        description="EMR Spark 任务。",
    ),
    229: FileTypeInfo(
        file_type=229,
        name="EMR_SPARK_SQL",
        task_type=TASK_TYPE_EMR_SPARK_SQL,
        category=CATEGORY_TASK,
        content_format=CONTENT_SQL,
        extension="sql",
        description="EMR Spark SQL 任务。",
    ),
    230: FileTypeInfo(
        file_type=230,
        name="EMR_MR",
        task_type=TASK_TYPE_EMR_MR,
        category=CATEGORY_TASK,
        content_format=CONTENT_UNKNOWN,
        extension="txt",
        description="EMR MapReduce 任务。",
    ),
    257: FileTypeInfo(
        file_type=257,
        name="EMR_SHELL",
        task_type=TASK_TYPE_EMR_SHELL,
        category=CATEGORY_TASK,
        content_format=CONTENT_SHELL,
        extension="sh",
        description="EMR Shell 任务。",
    ),
    258: FileTypeInfo(
        file_type=258,
        name="EMR_SPARK_SHELL",
        task_type=TASK_TYPE_EMR_SPARK_SHELL,
        category=CATEGORY_TASK,
        content_format=CONTENT_SHELL,
        extension="sh",
        description="EMR Spark Shell 任务。",
    ),
    259: FileTypeInfo(
        file_type=259,
        name="EMR_PRESTO",
        task_type=TASK_TYPE_EMR_PRESTO,
        category=CATEGORY_TASK,
        content_format=CONTENT_SQL,
        extension="sql",
        description="EMR Presto 任务。",
    ),
    260: FileTypeInfo(
        file_type=260,
        name="EMR_IMPALA",
        task_type=TASK_TYPE_EMR_IMPALA,
        category=CATEGORY_TASK,
        content_format=CONTENT_SQL,
        extension="sql",
        description="EMR Impala 任务。",
    ),
    267: FileTypeInfo(
        file_type=267,
        name="EMR_TRINO",
        task_type=TASK_TYPE_EMR_TRINO,
        category=CATEGORY_TASK,
        content_format=CONTENT_SQL,
        extension="sql",
        description="EMR Trino 任务。",
    ),
    # ------------------------------------------------------------------------
    # 其他任务类型
    # ------------------------------------------------------------------------
    239: FileTypeInfo(
        file_type=239,
        name="OSS_OBJECT_CHECK",
        task_type=TASK_TYPE_OSS_OBJECT_CHECK,
        category=CATEGORY_TASK,
        content_format=CONTENT_NONE,
        extension="txt",
        description="OSS 对象检查任务。",
    ),
    900: FileTypeInfo(
        file_type=900,
        name="REALTIME_SYNC",
        task_type=TASK_TYPE_REALTIME_SYNC,
        category=CATEGORY_TASK,
        content_format=CONTENT_JSON,
        extension="json",
        description="实时同步任务。",
    ),
    1089: FileTypeInfo(
        file_type=1089,
        name="CROSS_TENANT",
        task_type=TASK_TYPE_CROSS_TENANT,
        category=CATEGORY_TASK,
        content_format=CONTENT_JSON,
        extension="json",
        description="跨租户任务。",
    ),
    1091: FileTypeInfo(
        file_type=1091,
        name="HOLOGRES_DEVELOPMENT",
        task_type=TASK_TYPE_HOLOGRES_DEVELOPMENT,
        category=CATEGORY_TASK,
        content_format=CONTENT_UNKNOWN,
        extension="txt",
        description="Hologres 开发任务。",
    ),
    1093: FileTypeInfo(
        file_type=1093,
        name="HOLOGRES_SQL",
        task_type=TASK_TYPE_HOLOGRES_SQL,
        category=CATEGORY_TASK,
        content_format=CONTENT_SQL,
        extension="sql",
        description="Hologres SQL 任务。",
    ),
    1301: FileTypeInfo(
        file_type=1301,
        name="CLICKHOUSE_SQL",
        task_type=TASK_TYPE_CLICKHOUSE_SQL,
        category=CATEGORY_TASK,
        content_format=CONTENT_SQL,
        extension="sql",
        description="ClickHouse SQL 任务。",
    ),
    # ------------------------------------------------------------------------
    # 当前 Workspace 实际验证的任务类型
    # ------------------------------------------------------------------------
    1026: FileTypeInfo(
        file_type=1026,
        name="TASK_FLOW",
        task_type=TASK_TYPE_TASK_FLOW,
        category=CATEGORY_TASK,
        content_format=CONTENT_NONE,
        extension="txt",
        description=(
            "DataWorks 任务流节点。"
            "当前实际 GetFile 数据中 Content 为空，"
            "任务信息主要位于 NodeConfiguration。"
        ),
    ),
    1100: FileTypeInfo(
        file_type=1100,
        name="ASSIGNMENT",
        task_type=TASK_TYPE_ASSIGNMENT,
        category=CATEGORY_TASK,
        content_format=CONTENT_JSON,
        extension="json",
        description=(
            "DataWorks Assignment 节点。"
            "实际 GetFile Content 为 JSON，"
            "其中可能包含实际执行语言，例如 shell。"
        ),
    ),
    1330: FileTypeInfo(
        file_type=1330,
        name="FUNCTION_COMPUTE",
        task_type=TASK_TYPE_FUNCTION_COMPUTE,
        category=CATEGORY_TASK,
        content_format=CONTENT_JSON,
        extension="json",
        description="Function Compute 函数计算节点。",
    ),
    # ------------------------------------------------------------------------
    # Resource
    # ------------------------------------------------------------------------
    12: FileTypeInfo(
        file_type=12,
        name="PYTHON",
        task_type=TASK_TYPE_RESOURCE,
        category=CATEGORY_RESOURCE,
        content_format=CONTENT_PYTHON,
        extension="py",
        description="Python 资源文件，Content 为 Python 源代码。",
    ),
    13: FileTypeInfo(
        file_type=13,
        name="JAR",
        task_type=TASK_TYPE_RESOURCE,
        category=CATEGORY_RESOURCE,
        content_format=CONTENT_BINARY,
        extension="jar",
        description=(
            "JAR 资源文件。当前实际 GetFile Content 为 OSS Object Key，不是 JAR 二进制内容。"
        ),
    ),
    14: FileTypeInfo(
        file_type=14,
        name="ZIP",
        task_type=TASK_TYPE_RESOURCE,
        category=CATEGORY_RESOURCE,
        content_format=CONTENT_BINARY,
        extension="zip",
        description=(
            "ZIP 资源文件。当前实际 GetFile Content 为 OSS Object Key，不是 ZIP 二进制内容。"
        ),
    ),
    15: FileTypeInfo(
        file_type=15,
        name="FILE",
        task_type=TASK_TYPE_RESOURCE,
        category=CATEGORY_RESOURCE,
        content_format=CONTENT_BINARY,
        extension="txt",
        description=(
            "普通资源文件。当前实际 GetFile Content 为 OSS Object Key，不是实际文件内容。"
        ),
    ),
    17: FileTypeInfo(
        file_type=17,
        name="UDF",
        task_type=TASK_TYPE_RESOURCE,
        category=CATEGORY_RESOURCE,
        content_format=CONTENT_JSON,
        extension="json",
        description="用户自定义函数资源，Content 为 UDF JSON 元数据。",
    ),
}


# ============================================================================
# Unknown
# ============================================================================

UNKNOWN_FILE_TYPE = FileTypeInfo(
    file_type=-1,
    name="UNKNOWN",
    task_type=TASK_TYPE_UNKNOWN,
    category=CATEGORY_UNKNOWN,
    content_format=CONTENT_UNKNOWN,
    extension="txt",
    description="未知或暂不支持的 DataWorks FileType。",
)


# ============================================================================
# Public Functions
# ============================================================================


def get_file_type_info(file_type: int | None) -> FileTypeInfo:
    """获取 DataWorks FileType 对应的语义信息。

    未知 FileType 返回 UNKNOWN，不抛出异常。
    """
    if file_type is None:
        return UNKNOWN_FILE_TYPE

    return FILE_TYPE_REGISTRY.get(file_type, UNKNOWN_FILE_TYPE)


def get_file_type(file_type: int | None) -> FileTypeInfo:
    """兼容现有代码的 FileType 查询接口。"""
    return get_file_type_info(file_type)


def is_task_type(file_type: int | None) -> bool:
    """判断 FileType 是否属于任务类型。"""
    return get_file_type_info(file_type).category == CATEGORY_TASK


def is_resource_type(file_type: int | None) -> bool:
    """判断 FileType 是否属于资源类型。"""
    return get_file_type_info(file_type).category == CATEGORY_RESOURCE


def is_known_file_type(file_type: int | None) -> bool:
    """判断 FileType 是否已经在 Registry 中定义。"""
    if file_type is None:
        return False

    return file_type in FILE_TYPE_REGISTRY

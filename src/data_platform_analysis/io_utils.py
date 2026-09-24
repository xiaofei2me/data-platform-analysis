"""文件读写工具。"""

import json
import re
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> None:
    """确保目录存在，不存在时自动创建。"""

    path.mkdir(
        parents=True,
        exist_ok=True,
    )


def safe_filename(
    value: str,
    max_length: int = 180,
) -> str:
    """
    将字符串转换成安全的文件名。

    DataWorks Node ID、MaxCompute 表名等内容可能包含
    文件系统不适合使用的特殊字符，因此这里统一清理。
    """

    value = str(value).strip()

    if not value:
        value = "unknown"

    # 替换文件系统中的特殊字符。
    value = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        "_",
        value,
    )

    # 连续空白转换成下划线。
    value = re.sub(
        r"\s+",
        "_",
        value,
    )

    return value[:max_length]


def write_json(
    path: Path,
    data: Any,
    *,
    overwrite: bool = True,
) -> None:
    """将对象保存为格式化 JSON 文件。"""

    if path.exists() and not overwrite:
        return

    ensure_dir(path.parent)

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def write_jsonl(
    path: Path,
    records: list[dict[str, Any]],
    *,
    overwrite: bool = True,
) -> None:
    """
    将多个对象保存成 JSON Lines 文件。

    每一行对应一条独立 JSON 记录，
    适合保存大量任务或关系数据。
    """

    if path.exists() and not overwrite:
        return

    ensure_dir(path.parent)

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        for record in records:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                )
            )
            file.write("\n")


def write_text(
    path: Path,
    content: str,
    *,
    overwrite: bool = True,
) -> None:
    """将文本内容保存到文件。"""

    if path.exists() and not overwrite:
        return

    ensure_dir(path.parent)

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(content)


def write_sql(
    path: Path,
    sql: str,
    *,
    overwrite: bool = True,
) -> None:
    """将 SQL 保存成独立的 .sql 文件。"""

    sql = sql.strip()

    if not sql:
        return

    write_text(
        path,
        sql + "\n",
        overwrite=overwrite,
    )
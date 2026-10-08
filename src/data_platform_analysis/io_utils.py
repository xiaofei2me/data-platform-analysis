"""文件读写工具。"""

import json
import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def ensure_dir(path: Path) -> None:
    """确保目录存在，不存在时自动创建。"""
    path.mkdir(
        parents=True,
        exist_ok=True,
    )


def relocate_legacy_artifacts(
    analysis_dir: Path,
    output_dir: Path,
    *,
    legacy_dir: str,
    output_files: Sequence[str],
    carryover_files: Sequence[str] = (),
) -> None:
    """
    清理本阶段在旧目录布局下遗留的产物，避免同一阶段的文件散落两处。

    - 回填清单（carryover_files）：目标缺失时整体搬迁，保留人工回填列；
      目标已存在则以目标为准，丢弃遗留副本。
    - 其余机器产物：一律丢弃（本次运行会在 output_dir 重新生成）。

    output_dir 不在 analysis_dir 下、或仍指向旧目录时直接跳过，
    不会误删自己即将写出的产物。
    """

    try:
        target_dir = output_dir.relative_to(analysis_dir).as_posix()

    except ValueError:
        return

    if target_dir == legacy_dir:
        return

    legacy_root = analysis_dir / legacy_dir

    if not legacy_root.is_dir():
        return

    target_root = output_dir
    carryover = set(carryover_files)

    for name in output_files:
        legacy_path = legacy_root / name

        if not legacy_path.exists():
            continue

        target_path = target_root / name

        if name in carryover and not target_path.exists():
            ensure_dir(target_root)
            legacy_path.replace(target_path)
            logger.info("已迁移遗留清单：%s → %s", legacy_path, target_path)

        else:
            legacy_path.unlink()
            logger.info("已清理遗留产物：%s", legacy_path)


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

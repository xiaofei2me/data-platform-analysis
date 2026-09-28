"""命令行入口。"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table

from .config import settings
from .export import SnapshotExporter
from .logging_utils import setup_logging

logger = logging.getLogger(__name__)

console = Console()


def build_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        prog="data-platform-analysis",
        description=(
            "采集 DataWorks 和 MaxCompute 数据资产，"
            "生成本地 Snapshot。"
        ),
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=[
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
        ],
        help="日志级别，默认 INFO。",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # ========================================================
    # DataWorks
    # ========================================================

    # 只采集 DataWorks。
    sub_dataworks = subparsers.add_parser(
        "dataworks",
        help="采集 DataWorks 文件和任务信息。",
    )

    sub_dataworks.add_argument(
        "--workspace",
        type=int,
        default=None,
        help="只采集指定 Workspace（id 必须已在配置中）。",
    )

    # ========================================================
    # MaxCompute
    # ========================================================

    # 只采集 MaxCompute。
    sub_maxcompute = subparsers.add_parser(
        "maxcompute",
        help="采集 MaxCompute 表结构和元数据。",
    )

    sub_maxcompute.add_argument(
        "--workspace",
        type=int,
        default=None,
        help="只采集指定 Workspace（id 必须已在配置中）。",
    )

    # ========================================================
    # Export
    # ========================================================

    # 同时采集 DataWorks 和 MaxCompute。
    sub_export = subparsers.add_parser(
        "export",
        help="同时采集 DataWorks 和 MaxCompute。",
    )

    sub_export.add_argument(
        "--workspace",
        type=int,
        default=None,
        help="只采集指定 Workspace（id 必须已在配置中）。",
    )

    # ========================================================
    # Config
    # ========================================================

    # 查看当前配置。
    subparsers.add_parser(
        "config",
        help="查看当前生效的非敏感配置。",
    )

    return parser


def print_config() -> None:
    """打印当前生效配置，不输出敏感信息。"""

    table = Table(
        title="当前配置"
    )

    table.add_column("配置项")
    table.add_column("值")

    values = {
        "DATAWORKS_REGION": (
            settings.dataworks_region
        ),
        "WORKSPACES": ", ".join(
            f"{workspace.id} ({workspace.name})"
            for workspace in settings.workspaces
        ),
        "DATAWORKS_PAGE_SIZE": str(
            settings.dataworks_page_size
        ),
        "DATAWORKS_MAX_RETRIES": str(
            settings.dataworks_max_retries
        ),
        "DATAWORKS_USE_TYPES": ", ".join(
            settings.dataworks_use_types
        ),
        "MAXCOMPUTE_ENDPOINT": (
            settings.maxcompute_endpoint
        ),
        "MAXCOMPUTE_SCHEMA": (
            settings.maxcompute_schema
            or ""
        ),
        "MAXCOMPUTE_INCLUDE_PARTITIONS": str(
            settings.maxcompute_include_partitions
        ),
        "SOURCE_DIR": str(
            settings.source_dir
        ),
        "EXPORT_OVERWRITE": str(
            settings.export_overwrite
        ),
    }

    for key, value in values.items():
        table.add_row(
            key,
            value,
        )

    console.print(table)


def _exit_on_failures(
    exporter: SnapshotExporter,
) -> None:
    """存在 Workspace / 文件级失败时以非零码退出。"""

    if exporter.had_failures:
        sys.exit(1)


def run_dataworks(
    workspace_id: int | None = None,
) -> None:
    """执行 DataWorks 数据采集。"""

    exporter = SnapshotExporter()

    exporter.export_dataworks(
        workspace_id
    )

    _exit_on_failures(exporter)


def run_maxcompute(
    workspace_id: int | None = None,
) -> None:
    """执行 MaxCompute 数据采集。"""

    exporter = SnapshotExporter()

    exporter.export_maxcompute(
        workspace_id
    )

    _exit_on_failures(exporter)


def run_export(
    workspace_id: int | None = None,
) -> None:
    """执行完整 Snapshot 采集。"""

    exporter = SnapshotExporter()

    exporter.export_all(
        workspace_id
    )

    _exit_on_failures(exporter)


def main() -> None:
    """CLI 程序入口。"""

    parser = build_parser()

    args = parser.parse_args()

    setup_logging(
        args.log_level
    )

    try:
        if args.command == "config":
            print_config()
            return

        if args.command == "dataworks":
            run_dataworks(
                args.workspace
            )
            return

        if args.command == "maxcompute":
            run_maxcompute(
                args.workspace
            )
            return

        if args.command == "export":
            run_export(
                args.workspace
            )
            return

        parser.error(
            f"未知命令：{args.command}"
        )

    except KeyboardInterrupt:
        logger.warning(
            "用户中断操作。"
        )

        sys.exit(130)

    except Exception:
        logger.exception(
            "命令执行失败。"
        )

        sys.exit(1)
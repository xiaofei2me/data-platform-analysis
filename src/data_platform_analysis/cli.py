"""命令行入口。"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table

from .analysis import AnalysisPipeline
from .analysis.errors import AnalysisFatalError
from .config import settings
from .export import SnapshotExporter
from .logging_utils import setup_logging
from .summary import SnapshotSummaryGenerator

logger = logging.getLogger(__name__)

console = Console()


def _positive_int(value: str) -> int:
    """解析必须大于 0 的整数参数。"""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--limit 必须是整数：{value}") from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"--limit 必须大于 0：{value}")

    return parsed


def _add_limit_argument(
    parser: argparse.ArgumentParser,
) -> None:
    """为采集类子命令增加 --limit。"""
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=None,
        help=(
            "采集限制模式：每个 Workspace 最多处理 N 个对象"
            "（DataWorks N 个 File、MaxCompute N 个 Table）；"
            "必须是大于 0 的整数；不传则全量采集。"
            "限制模式下禁止 Snapshot Cleanup。"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="data-platform-analysis",
        description=("采集 DataWorks 和 MaxCompute 数据资产，生成本地 Snapshot。"),
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

    sub_dataworks = subparsers.add_parser(
        "dataworks",
        help="采集 DataWorks 文件、Raw 详情与内容。",
    )

    sub_dataworks.add_argument(
        "--workspace",
        type=int,
        default=None,
        help="只采集指定 Workspace（id 必须已在配置中）。",
    )

    _add_limit_argument(sub_dataworks)

    # ========================================================
    # MaxCompute
    # ========================================================

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

    _add_limit_argument(sub_maxcompute)

    # ========================================================
    # Export
    # ========================================================

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

    _add_limit_argument(sub_export)

    # ========================================================
    # Summary
    # ========================================================

    subparsers.add_parser(
        "summary",
        help="根据已有 Snapshot 重新生成 Summary.md。",
    )

    # ========================================================
    # Analyze
    # ========================================================

    sub_analyze = subparsers.add_parser(
        "analyze",
        help="基于已有 Snapshot 生成 analysis/ Evidence Chain。",
    )

    sub_analyze.add_argument(
        "--stage",
        choices=["inventory", "evidence", "understanding", "review"],
        default=None,
        help="只执行指定 Stage（inventory/evidence/understanding/review），默认执行全部。",
    )

    sub_analyze.add_argument(
        "--workspace",
        type=int,
        default=None,
        help="只分析 Snapshot 中的指定 Workspace（必须已存在于 source/）。",
    )

    # ========================================================
    # Config
    # ========================================================

    subparsers.add_parser(
        "config",
        help="查看当前生效的非敏感配置。",
    )

    return parser


def print_config() -> None:
    """打印当前生效配置，不输出敏感信息。"""
    table = Table(title="当前配置")

    table.add_column("配置项")
    table.add_column("值")

    values = {
        "DATAWORKS_REGION": (settings.dataworks_region),
        "WORKSPACES": ", ".join(
            f"{workspace.id} ({workspace.name})" for workspace in settings.workspaces
        ),
        "DATAWORKS_PAGE_SIZE": str(settings.dataworks_page_size),
        "DATAWORKS_MAX_RETRIES": str(settings.dataworks_max_retries),
        "DATAWORKS_USE_TYPES": ", ".join(settings.dataworks_use_types),
        "MAXCOMPUTE_ENDPOINT": (settings.maxcompute_endpoint),
        "MAXCOMPUTE_SCHEMA": (settings.maxcompute_schema or ""),
        "MAXCOMPUTE_INCLUDE_PARTITIONS": str(settings.maxcompute_include_partitions),
        "SOURCE_DIR": str(settings.source_dir),
        "ANALYSIS_DIR": str(settings.analysis_dir),
        "LAYER_RULES_PATH": str(settings.layer_rules_path),
        "BUSINESS_RULES_PATH": str(settings.business_rules_path),
        "EXPORT_OVERWRITE": str(settings.export_overwrite),
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
    limit: int | None = None,
) -> None:
    """执行 DataWorks 数据采集。"""
    exporter = SnapshotExporter()
    exporter.export_dataworks(
        workspace_id=workspace_id,
        limit=limit,
    )
    _exit_on_failures(exporter)


def run_maxcompute(
    workspace_id: int | None = None,
    limit: int | None = None,
) -> None:
    """执行 MaxCompute 数据采集。"""
    exporter = SnapshotExporter()
    exporter.export_maxcompute(
        workspace_id=workspace_id,
        limit=limit,
    )
    _exit_on_failures(exporter)


def run_summary() -> None:
    """根据已有 Snapshot 重新生成 Summary.md。"""
    summary_path = SnapshotSummaryGenerator(
        source_dir=settings.source_dir,
    ).generate()
    console.print(f"[green]Summary 已生成：[/green]{summary_path}")


def run_export(
    workspace_id: int | None = None,
    limit: int | None = None,
) -> None:
    """执行完整 Snapshot 采集。"""
    exporter = SnapshotExporter()
    exporter.export_all(
        workspace_id=workspace_id,
        limit=limit,
    )
    _exit_on_failures(exporter)


def run_analyze(
    stage: str | None = None,
    workspace_id: int | None = None,
) -> None:
    """基于已有 Snapshot 执行 Analysis。

    stage 参数控制执行的 Stage：
    - None: 执行全部四个阶段
    - "inventory": 只执行 Stage 01（Inventory）
    - "evidence": 执行 Stage 01-05（Evidence）
    - "understanding": 执行 Stage 01-11（Understanding）
    - "review": 执行全部四个阶段
    """
    try:
        pipeline = AnalysisPipeline(
            source_dir=settings.source_dir,
            analysis_dir=settings.analysis_dir,
            layer_rules_path=settings.layer_rules_path,
            workspace_id=workspace_id,
        )

        if stage == "inventory":
            pipeline.run_stage_inventory()
        elif stage == "evidence":
            pipeline.run_stage_evidence()
        elif stage == "understanding":
            pipeline.run_stage_understanding()
        elif stage == "review":
            pipeline.run_stage_review()
        else:
            pipeline.run()

    except AnalysisFatalError as exc:
        logger.error("Analysis 无法继续：%s", exc)
        sys.exit(1)


def main() -> None:
    """CLI 程序入口。"""
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(args.log_level)

    try:
        if args.command == "config":
            print_config()
            return

        if args.command == "dataworks":
            run_dataworks(
                workspace_id=args.workspace,
                limit=args.limit,
            )
            return

        if args.command == "maxcompute":
            run_maxcompute(
                workspace_id=args.workspace,
                limit=args.limit,
            )
            return

        if args.command == "export":
            run_export(
                workspace_id=args.workspace,
                limit=args.limit,
            )
            return

        if args.command == "summary":
            run_summary()
            return

        if args.command == "analyze":
            run_analyze(
                stage=args.stage,
                workspace_id=args.workspace,
            )
            return

        parser.error(f"未知命令：{args.command}")

    except KeyboardInterrupt:
        logger.warning("用户中断操作。")
        sys.exit(130)

    except Exception:
        logger.exception("命令执行失败。")
        sys.exit(1)


if __name__ == "__main__":
    main()

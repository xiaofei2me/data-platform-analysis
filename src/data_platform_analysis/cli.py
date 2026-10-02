"""命令行入口。"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table

from .analysis import AnalysisPipeline
from .analysis.errors import AnalysisFatalError
from .analysis.layer_assessment import LayerAssessmentError, run_layer_assessment
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

    # 只采集 DataWorks。
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

    _add_limit_argument(sub_maxcompute)

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

    _add_limit_argument(sub_export)

    # ========================================================
    # Summary
    # ========================================================

    # 基于已有 Snapshot 重新生成 Summary.md。
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
        "--workspace",
        type=int,
        default=None,
        help="只分析 Snapshot 中的指定 Workspace（必须已存在于 source/）。",
    )

    # ========================================================
    # Analyze Layer
    # ========================================================

    # 基于已有 Inventory 输出执行 M2.5，不重跑 SQL / Lineage / Profiling。
    subparsers.add_parser(
        "analyze-layer",
        help="基于已有 analysis/inventory 输出执行 M2.5 Layer Assessment。",
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
    workspace_id: int | None = None,
) -> None:
    """基于已有 Snapshot 执行 Analysis。"""

    try:
        result = AnalysisPipeline(
            source_dir=settings.source_dir,
            analysis_dir=settings.analysis_dir,
            layer_rules_path=settings.layer_rules_path,
            workspace_id=workspace_id,
        ).run()

    except AnalysisFatalError as exc:
        logger.error("Analysis 无法继续：%s", exc)

        sys.exit(1)

    console.print(
        "[green]Analysis 完成：[/green]"
        f"workspace={len(result.workspace_ids)}，"
        f"file={result.file_count}（eligible={result.eligible_file_count}，"
        f"excluded={result.excluded_file_count}），"
        f"table={result.table_count}，"
        f"statement={result.statement_count}，"
        f"edge={result.edge_count}，"
        f"error={result.error_count}"
    )

    if result.summary_path is not None:
        console.print(f"[green]Summary：[/green]{result.summary_path}")


def run_analyze_layer() -> None:
    """基于已有 Inventory 输出执行 M2.5 Layer Assessment。"""

    try:
        result = run_layer_assessment(
            inventory_path=settings.analysis_dir / "inventory" / "tables.json",
            rules_path=settings.layer_rules_path,
            output_dir=settings.analysis_dir / "layer",
        )

    except LayerAssessmentError as exc:
        logger.error("Layer Assessment 无法继续：%s", exc)

        sys.exit(1)

    status_text = "，".join(f"{key}={value}" for key, value in result.status_counts.items())

    console.print(
        "[green]Layer Assessment 完成：[/green]"
        f"table={len(result.assessments)}，{status_text}，"
        f"未配置 workspace={len(result.unconfigured_workspace_ids)}"
    )
    console.print(f"[green]产物：[/green]{settings.analysis_dir / 'layer'}")


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
                workspace_id=args.workspace,
            )
            return

        if args.command == "analyze-layer":
            run_analyze_layer()
            return

        parser.error(f"未知命令：{args.command}")

    except KeyboardInterrupt:
        logger.warning("用户中断操作。")

        sys.exit(130)

    except Exception:
        logger.exception("命令执行失败。")

        sys.exit(1)

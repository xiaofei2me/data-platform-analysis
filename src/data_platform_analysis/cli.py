"""命令行入口。"""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table

from .analysis import AnalysisPipeline
from .analysis.business.grain import (
    BusinessGrainError,
    run_business_grain_analysis,
)
from .analysis.business.objects import (
    BusinessObjectsError,
    run_business_object_analysis,
)
from .analysis.business.processes import (
    BusinessProcessesError,
    run_business_process_analysis,
)
from .analysis.business.quality import (
    BusinessQualityError,
    run_business_quality_assessment,
)
from .analysis.business.understanding import (
    BusinessUnderstandingError,
    run_business_understanding,
)
from .analysis.errors import AnalysisFatalError
from .analysis.layer.layer_assessment import LayerAssessmentError, run_layer_assessment
from .analysis.model.business_model import (
    BusinessModelError,
    run_business_model_analysis,
)
from .analysis.review.findings import (
    CurrentStateModelError,
    run_current_state_model_analysis,
)
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

    # 基于已有 Inventory 输出执行 M2.2，不重跑 SQL / Lineage / Profiling。
    subparsers.add_parser(
        "analyze-layer",
        help="基于已有 analysis/inventory 输出执行 M2.2 Layer Assessment。",
    )

    # ========================================================
    # Analyze Business
    # ========================================================

    # 基于已有 M2 产物执行 M3 Business Understanding，只产出候选与证据。
    subparsers.add_parser(
        "analyze-business",
        help="基于已有 M2 产物执行 M3 Business Understanding（候选 + 证据）。",
    )

    # ========================================================
    # Analyze Business Quality
    # ========================================================

    # 基于已有 M2 / M3 产物执行 M3.1 质量评估，只评估不识别。
    subparsers.add_parser(
        "analyze-business-quality",
        help="基于已有 M2 / M3 产物执行 M3.1 业务理解质量评估（只评估，不识别）。",
    )

    # ========================================================
    # Analyze Business Objects
    # ========================================================

    # 基于已有 M2 / M3 / M3.1 产物执行 M3.2 Object & Relationship 证据结构。
    subparsers.add_parser(
        "analyze-business-objects",
        help=(
            "基于已有 M2 / M3 / M3.1 产物执行 M3.2 Business Object & "
            "Relationship Analysis（只建证据结构，不重新分类）。"
        ),
    )

    # ========================================================
    # Analyze Business Processes
    # ========================================================

    # 基于已有 M2 / M3 / M3.1 / M3.2 产物执行 M3.3 Process Candidate 分析。
    subparsers.add_parser(
        "analyze-business-processes",
        help=(
            "基于已有 M2 / M3 / M3.1 / M3.2 产物执行 M3.3 Business Process "
            "Candidate Analysis（只产出 process candidate 与信号，不命名、不判 Grain）。"
        ),
    )

    # ========================================================
    # Analyze Business Grain
    # ========================================================

    # 基于已有 M2 / M3 / M3.1 / M3.2 / M3.3 产物执行 M3.4 Grain Candidate 分析。
    subparsers.add_parser(
        "analyze-business-grain",
        help=(
            "基于已有 M2 / M3 / M3.1 / M3.2 / M3.3 产物执行 M3.4 Grain "
            "Candidate Analysis（只产出 grain candidate 与信号，"
            "不产出 confirmed grain，不命名事实表 / 维度表）。"
        ),
    )

    # ========================================================
    # Analyze Business Model
    # ========================================================

    # 基于已有 M2 / M3 / M3.1 / M3.2 / M3.3 / M3.4 产物执行 M3.5 候选分析。
    subparsers.add_parser(
        "analyze-business-model",
        help=(
            "基于已有 M2 / M3 / M3.1 / M3.2 / M3.3 / M3.4 产物执行 M3.5 Fact / "
            "Dimension Candidate Analysis（只产出 fact / dimension / relationship "
            "candidate 与证据，不产出 DWD / DWS / Semantic Layer）。"
        ),
    )

    # ========================================================
    # Analyze Current-State Model
    # ========================================================

    # 基于已有 M2 / M3 / M3.5 产物执行 M3.6 评审（只读，不改上游）。
    subparsers.add_parser(
        "analyze-current-state-model",
        help=(
            "基于已有 M2 / M3 / M3.5 产物执行 M3.6 Current-State Model Review"
            "（只评审候选、产出形态分类 / finding / 人工清单，"
            "不设计 Target DWD、不产出 DWD / DWS / Semantic Layer）。"
        ),
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
    """基于已有 Inventory 输出执行 M2.2 Layer Assessment。"""

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


def run_analyze_business() -> None:
    """基于已有 M2 产物执行 M3 Business Understanding。"""

    try:
        result = run_business_understanding(
            analysis_dir=settings.analysis_dir,
            rules_path=settings.business_rules_path,
            output_dir=settings.analysis_dir / "business",
        )

    except BusinessUnderstandingError as exc:
        logger.error("Business Understanding 无法继续：%s", exc)

        sys.exit(1)

    console.print(
        "[green]Business Understanding 完成：[/green]"
        f"table={len(result.tables)}，term={len(result.terms)}，"
        f"domain={sum(1 for item in result.domains if item.table_count)}，"
        f"object={sum(1 for item in result.objects if item.table_count)}，"
        f"unknown={result.unknown_table_count}，ambiguous={result.ambiguous_table_count}"
    )
    console.print(f"[green]产物：[/green]{settings.analysis_dir / 'business'}")


def run_analyze_business_quality() -> None:
    """基于已有 M2 / M3 产物执行 M3.1 Business Quality Assessment。"""

    try:
        result = run_business_quality_assessment(
            analysis_dir=settings.analysis_dir,
            output_dir=settings.analysis_dir / "business",
        )

    except BusinessQualityError as exc:
        logger.error("Business Quality Assessment 无法继续：%s", exc)

        sys.exit(1)

    summary = result.summary

    console.print(
        "[green]Business Quality Assessment 完成：[/green]"
        f"table={summary.get('table_count')}，"
        f"unknown={summary.get('unknown_count')}，"
        f"ambiguous={summary.get('ambiguous_count')}，"
        f"core_unknown={summary.get('core_unknown_count')}，"
        f"core_ambiguous={summary.get('core_ambiguous_count')}"
    )
    console.print(f"[green]产物：[/green]{settings.analysis_dir / 'business'}")


def run_analyze_business_objects() -> None:
    """基于已有 M2 / M3 / M3.1 产物执行 M3.2 Business Object Analysis。"""

    try:
        result = run_business_object_analysis(
            analysis_dir=settings.analysis_dir,
            output_dir=settings.analysis_dir / "business",
        )

    except BusinessObjectsError as exc:
        logger.error("Business Object Analysis 无法继续：%s", exc)

        sys.exit(1)

    status_text = "，".join(
        f"{key}={value}" for key, value in result.association_status_counts.items()
    )

    console.print(
        "[green]Business Object Analysis 完成：[/green]"
        f"object={result.object_count}，association={result.association_count}"
        f"（{status_text}），"
        f"relationship={result.relationship_count}"
        f"（core={result.core_relationship_count}）"
    )
    console.print(f"[green]产物：[/green]{settings.analysis_dir / 'business'}")


def run_analyze_business_processes() -> None:
    """基于已有 M2 / M3 / M3.1 / M3.2 产物执行 M3.3 Process Candidate Analysis。"""

    try:
        result = run_business_process_analysis(
            analysis_dir=settings.analysis_dir,
            output_dir=settings.analysis_dir / "business",
            rules_path=settings.process_rules_path,
        )

    except BusinessProcessesError as exc:
        logger.error("Business Process Candidate Analysis 无法继续：%s", exc)

        sys.exit(1)

    strength_text = "，".join(
        f"{key}={value}" for key, value in result.process_strength_counts.items()
    )

    console.print(
        "[green]Business Process Candidate Analysis 完成：[/green]"
        f"signal={result.signal_count}，"
        f"process candidate={result.process_count}（{strength_text}），"
        f"process table={result.process_table_count}"
    )
    console.print(f"[green]产物：[/green]{settings.analysis_dir / 'business'}")


def run_analyze_business_grain() -> None:
    """基于已有 M2 / M3 / M3.1 / M3.2 / M3.3 产物执行 M3.4 Grain Candidate Analysis。"""

    try:
        result = run_business_grain_analysis(
            analysis_dir=settings.analysis_dir,
            output_dir=settings.analysis_dir / "business",
        )

    except BusinessGrainError as exc:
        logger.error("Grain Candidate Analysis 无法继续：%s", exc)

        sys.exit(1)

    pattern_text = "，".join(
        f"{key}={value}" for key, value in result.pattern_counts.items()
    )
    status_text = "，".join(
        f"{key}={value}" for key, value in result.status_counts.items()
    )

    console.print(
        "[green]Grain Candidate Analysis 完成：[/green]"
        f"signal={result.signal_count}，"
        f"grain candidate={result.candidate_count}（{pattern_text}；{status_text}），"
        f"grain table={result.grain_table_count}"
    )
    console.print(f"[green]产物：[/green]{settings.analysis_dir / 'business'}")


def run_analyze_business_model() -> None:
    """基于已有 M2 / M3 / M3.1 / M3.2 / M3.3 / M3.4 产物执行 M3.5 候选分析。"""

    try:
        result = run_business_model_analysis(
            analysis_dir=settings.analysis_dir,
            output_dir=settings.analysis_dir / "model",
        )

    except BusinessModelError as exc:
        logger.error("Fact / Dimension Candidate Analysis 无法继续：%s", exc)

        sys.exit(1)

    fact_text = "，".join(
        f"{key}={value}" for key, value in result.fact_strength_counts.items()
    )

    console.print(
        "[green]Fact / Dimension Candidate Analysis 完成：[/green]"
        f"fact={result.fact_count}（{fact_text}），"
        f"dimension={result.dimension_count}，"
        f"relationship={result.relationship_count}，"
        f"fact table={result.fact_table_count}，"
        f"dimension table={result.dimension_table_count}"
    )
    console.print(f"[green]产物：[/green]{settings.analysis_dir / 'model'}")


def run_analyze_current_state_model() -> None:
    """基于已有 M2 / M3 / M3.5 产物执行 M3.6 Current-State Model Review。"""

    try:
        result = run_current_state_model_analysis(
            analysis_dir=settings.analysis_dir,
            output_dir=settings.analysis_dir / "review",
        )

    except CurrentStateModelError as exc:
        logger.error("Current-State Model Review 无法继续：%s", exc)

        sys.exit(1)

    priority_text = "，".join(
        f"{key}={value}" for key, value in result.priority_counts.items()
    )

    console.print(
        "[green]Current-State Model Review 完成：[/green]"
        f"table={result.table_count}，finding={result.finding_count}"
        f"（{priority_text}）"
    )

    if result.problem is not None:
        problem_status_text = "，".join(
            f"{key}={value}" for key, value in result.problem.status_counts.items()
        )
        console.print(
            "[green]Current-State Problem Assessment 完成：[/green]"
            f"problem={result.problem.problem_count}"
            f"（{problem_status_text}）"
        )

    console.print(f"[green]产物：[/green]{settings.analysis_dir / 'review'}")


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

        if args.command == "analyze-business":
            run_analyze_business()
            return

        if args.command == "analyze-business-quality":
            run_analyze_business_quality()
            return

        if args.command == "analyze-business-objects":
            run_analyze_business_objects()
            return

        if args.command == "analyze-business-processes":
            run_analyze_business_processes()
            return

        if args.command == "analyze-business-grain":
            run_analyze_business_grain()
            return

        if args.command == "analyze-business-model":
            run_analyze_business_model()
            return

        if args.command == "analyze-current-state-model":
            run_analyze_current_state_model()
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

"""Phase 2 Analysis 编排：M2.1 → M2.2 → M2.3 → M2.4 → M2.5。

输入：source/ Snapshot（只读）
输出：analysis/ Evidence Chain（每次全量重写，可重复执行）

执行顺序：

    1. 读取 Workspace identity（失败即 Fatal Error）
    2. M2.1 Inventory（Snapshot 全量 File，不做任何过滤；同时执行
       Analysis Scope Rules 分类，产出 excluded / review 清单与统计）
    3. M2.2 Layer Assessment（依赖 M2.1 的 Inventory 输出与 layer-rules 配置，
       产出唯一层级判定 candidate_layer，供 Lineage 引用）
    4. M2.3 SQL Analysis（只接受统一资格判定 sql_eligible 的 File）
    5. M2.4 Table Reference / Lineage（层级标注取自 M2.2 candidate_layer）
    6. M2.5 Metadata Profiling
    7. 写出 Summary 与错误账本

Analysis 输入范围（Analysis Scope Rules，规则在 Inventory 内部执行）：

    Inventory 对每个 File 计算一次规则分类结果（FileScope），
    SQL Analysis 只接受 sql_eligible = true 的 File；
    NodeId 缺失、格式无效、明确的非正式任务、类型不适用 SQL、
    Content 不可用都会记录明确的原因代码，保留在 Inventory 全量清单中，
    不产生 SQL Evidence，也不记录为 Analysis Error。
    整体分析资格（identity）与 SQL 分析资格（sql_eligible）分别统计，
    分类规则配置在 config/analysis-scope-rules.yaml。
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import settings
from ..io_utils import ensure_dir, write_json, write_text
from .errors import AnalysisFatalError, ErrorLedger
from .evidence.layer.layer_assessment import (
    LayerAssessmentError,
    LayerAssessmentResult,
    run_layer_assessment,
)
from .evidence.lineage.lineage import LineageBuilder, LineageResult
from .evidence.profiling.profiling import MetadataProfiler
from .evidence.sql.sql_analysis import ParseErrorRecord, SqlAnalyzer
from .inventory.inventory import (
    Inventory,
    InventoryBuilder,
    InventorySummary,
    build_inventory_summary,
)
from .inventory.scope import (
    FileScope,
    ScopeRulesError,
    build_file_scope,
    excluded_tasks_payload,
    load_scope_rules,
    review_tasks_payload,
)
from .models import (
    ColumnProfile,
    FileInventory,
    LayerAssessment,
    StatementRecord,
    TableProfile,
    TableReference,
    is_analysis_eligible,
    numeric_id_sort_key,
)

if TYPE_CHECKING:
    from .understanding.business.understanding import BusinessUnderstandingResult


from .reports import (
    SummaryContext,
    render_analysis_summary,
    render_inventory_summary,
    render_lineage_summary,
    render_profiling_summary,
)
from .snapshot import SnapshotReader

logger = logging.getLogger(__name__)

PRODUCTION_DIRS: tuple[str, ...] = (
    "inventory",
    "evidence",
    "understanding",
    "review",
)
PRODUCTION_FILES: tuple[str, ...] = ("evidence/errors.json", "summary.md")

LOG_INTERVAL = 500
"""SQL 文件分析进度日志间隔。"""


@dataclass
class AnalysisResult:
    """一次 Analysis 运行的汇总结果。"""

    analysis_dir: Path
    workspace_ids: list[int] = field(default_factory=list)
    file_count: int = 0
    eligible_file_count: int = 0
    excluded_file_count: int = 0
    table_count: int = 0
    column_count: int = 0
    statement_count: int = 0
    reference_count: int = 0
    edge_count: int = 0
    error_count: int = 0
    summary_path: Path | None = None


class AnalysisPipeline:
    """Analysis 流水线。"""

    def __init__(
        self,
        *,
        source_dir: Path,
        analysis_dir: Path,
        layer_rules_path: Path,
        scope_rules_path: Path,
        workspace_id: int | None = None,
    ) -> None:
        self.source_dir = source_dir
        self.analysis_dir = analysis_dir
        self.layer_rules_path = layer_rules_path
        self.scope_rules_path = scope_rules_path
        self.workspace_id = workspace_id
        self.ledger = ErrorLedger()
        self.reader = SnapshotReader(
            source_dir=self.source_dir,
            ledger=self.ledger,
        )

    def run(self) -> AnalysisResult:
        """执行完整 Analysis。"""

        identities = self.reader.select_identities(
            self.reader.load_workspace_identities(),
            self.workspace_id,
        )

        self._reset_outputs()

        inventory = InventoryBuilder(
            reader=self.reader,
            identities=identities,
        ).build()

        # 规则分类在 Inventory 内部执行一次，后续阶段只消费判定结果。
        scope = self._build_scope(inventory)

        self._write_inventory(inventory, scope)

        # 盘点统计只依赖刚构建的 Inventory 与只读 Snapshot，
        # 在 SQL / Lineage 之前算好，保证它只反映 M2.1 的事实。
        inventory_summary = build_inventory_summary(
            inventory,
            reader=self.reader,
            scope=scope,
        )

        # M2.2：只依赖 M2.1 的 Inventory 输出与 layer-rules 配置，
        # 先于 SQL / Lineage 执行，Lineage 的层级标注直接引用其 candidate_layer。
        layer_result = self._run_layer_assessment()

        # 资产身份口径（整体分析资格）与 SQL 分析口径分开：
        # eligible_files 用于报告统计，sql_files 是 SQL Analysis 的实际输入。
        eligible_files = [item for item in inventory.files if is_analysis_eligible(item)]
        excluded_file_count = len(inventory.files) - len(eligible_files)
        sql_files = scope.sql_eligible_files(inventory.files)

        statements, references, parse_errors = self._analyze_sql(sql_files)

        self._write_sql(statements, references, parse_errors)

        lineage = LineageBuilder(
            references,
            inventory,
            layer_result.assessments,
        ).build()

        self._write_lineage(lineage)

        table_profiles, column_profiles = MetadataProfiler(inventory).profile()

        self._write_profiling(table_profiles, column_profiles)

        errors = self.ledger.records()

        summary_path = self._write_reports(
            inventory=inventory,
            inventory_summary=inventory_summary,
            statements=statements,
            references=references,
            parse_errors=parse_errors,
            lineage=lineage,
            table_profiles=table_profiles,
            column_profiles=column_profiles,
            layer_assessments=layer_result.assessments,
            errors=errors,
        )

        write_json(
            self.analysis_dir / "evidence" / "errors.json",
            {
                "count": len(errors),
                "errors": errors,
            },
        )

        result = AnalysisResult(
            analysis_dir=self.analysis_dir,
            workspace_ids=[identity.workspace_id for identity in identities],
            file_count=len(inventory.files),
            eligible_file_count=len(eligible_files),
            excluded_file_count=excluded_file_count,
            table_count=len(inventory.tables),
            column_count=len(inventory.columns),
            statement_count=len(statements),
            reference_count=len(references),
            edge_count=len(lineage.edges),
            error_count=len(errors),
            summary_path=summary_path,
        )

        logger.info(
            "Analysis 完成：workspace=%s，file=%s（eligible=%s，excluded=%s），table=%s，"
            "statement=%s，reference=%s，edge=%s，error=%s",
            len(identities),
            result.file_count,
            result.eligible_file_count,
            result.excluded_file_count,
            result.table_count,
            result.statement_count,
            result.reference_count,
            result.edge_count,
            result.error_count,
        )

        # 执行 M3 业务理解（Stage 06-11）与 M3.6 Review（Stage 12-14）；
        # run_stage_review 内部会先执行 run_stage_understanding，
        # 这里不再重复调用，保证 Understanding 每次运行只执行一遍。
        # 两者只产生阶段产物，run() 的返回值仍是 Evidence 阶段的 AnalysisResult。
        self.run_stage_review()

        return result

    # ==========================================================
    # 四阶段 Pipeline 支持
    # ==========================================================

    def run_stage_inventory(self) -> AnalysisResult:
        """只执行 Stage 01（Inventory）。"""
        identities = self.reader.select_identities(
            self.reader.load_workspace_identities(),
            self.workspace_id,
        )

        self._reset_outputs()

        inventory = InventoryBuilder(
            reader=self.reader,
            identities=identities,
        ).build()

        scope = self._build_scope(inventory)

        self._write_inventory(inventory, scope)

        inventory_summary = build_inventory_summary(
            inventory,
            reader=self.reader,
            scope=scope,
        )

        errors = self.ledger.records()

        summary_path = self._write_reports_stage_inventory(
            inventory=inventory,
            inventory_summary=inventory_summary,
            errors=errors,
        )

        eligible_count = sum(1 for item in inventory.files if is_analysis_eligible(item))

        result = AnalysisResult(
            analysis_dir=self.analysis_dir,
            workspace_ids=[identity.workspace_id for identity in identities],
            file_count=len(inventory.files),
            eligible_file_count=eligible_count,
            excluded_file_count=len(inventory.files) - eligible_count,
            table_count=len(inventory.tables),
            column_count=len(inventory.columns),
            statement_count=0,
            reference_count=0,
            edge_count=0,
            error_count=len(errors),
            summary_path=summary_path,
        )

        return result

    def _write_reports_stage_inventory(
        self,
        *,
        inventory: Inventory,
        inventory_summary: InventorySummary,
        errors: list[dict[str, object]],
    ) -> Path:
        """写出 Inventory 阶段 Summary。"""

        write_text(
            self.analysis_dir / "inventory" / "summary.md",
            render_inventory_summary(inventory_summary),
        )

        summary_path = self.analysis_dir / "summary.md"

        from .evidence.lineage.lineage import LineageResult
        from .reports import SummaryContext, render_analysis_summary

        write_text(
            summary_path,
            render_analysis_summary(
                SummaryContext(
                    inventory=inventory,
                    lineage=LineageResult(edges=[], candidates=[]),
                    statements=[],
                    references=[],
                    parse_errors=[],
                    table_profiles=[],
                    column_profiles=[],
                    layer_assessments=[],
                    errors=errors,
                )
            ),
        )

        return summary_path

    def run_stage_evidence(self) -> AnalysisResult:
        """执行 Stage 01-05（Evidence）。"""
        # 先运行 inventory
        identities = self.reader.select_identities(
            self.reader.load_workspace_identities(),
            self.workspace_id,
        )

        self._reset_outputs()

        inventory = InventoryBuilder(
            reader=self.reader,
            identities=identities,
        ).build()

        scope = self._build_scope(inventory)

        self._write_inventory(inventory, scope)

        # 盘点统计
        inventory_summary = build_inventory_summary(
            inventory,
            reader=self.reader,
            scope=scope,
        )

        # 执行 M2.2
        layer_result = self._run_layer_assessment()

        eligible_files = [item for item in inventory.files if is_analysis_eligible(item)]
        sql_files = scope.sql_eligible_files(inventory.files)

        statements, references, parse_errors = self._analyze_sql(sql_files)
        self._write_sql(statements, references, parse_errors)

        from .evidence.lineage.lineage import LineageBuilder

        lineage = LineageBuilder(
            references,
            inventory,
            layer_result.assessments,
        ).build()

        self._write_lineage(lineage)

        table_profiles, column_profiles = MetadataProfiler(inventory).profile()
        self._write_profiling(table_profiles, column_profiles)

        errors = self.ledger.records()

        # Evidence stage 的报告契约与全量 Analysis 完全一致：
        # 复用 _write_reports()，用上面刚算好的真实 Layer / SQL /
        # Lineage / Profiling 结果渲染，不制造空 LineageResult，
        # 也不重复计算任何 M2 输入。
        summary_path = self._write_reports(
            inventory=inventory,
            inventory_summary=inventory_summary,
            statements=statements,
            references=references,
            parse_errors=parse_errors,
            lineage=lineage,
            table_profiles=table_profiles,
            column_profiles=column_profiles,
            layer_assessments=layer_result.assessments,
            errors=errors,
        )

        write_json(
            self.analysis_dir / "evidence" / "errors.json",
            {
                "count": len(errors),
                "errors": errors,
            },
        )

        return AnalysisResult(
            analysis_dir=self.analysis_dir,
            workspace_ids=[identity.workspace_id for identity in identities],
            file_count=len(inventory.files),
            eligible_file_count=len(eligible_files),
            excluded_file_count=len(inventory.files) - len(eligible_files),
            table_count=len(inventory.tables),
            column_count=len(inventory.columns),
            statement_count=len(statements),
            reference_count=len(references),
            edge_count=len(lineage.edges),
            error_count=len(errors),
            summary_path=summary_path,
        )

    def run_stage_understanding(self) -> BusinessUnderstandingResult:
        """执行 Stage 01-11（Understanding）。"""
        # 先检查 evidence 是否存在，如果不存在则执行 run_stage_evidence

        if not (self.analysis_dir / "evidence" / "layer" / "assessments.json").exists():
            print("Evidence 阶段未完成，执行 run_stage_evidence")
            self.run_stage_evidence()

        # 执行 M3 业务理解
        try:
            from .understanding.business.understanding import (
                run_business_understanding,
            )
        except ImportError as exc:
            raise AnalysisFatalError(f"导入 Understanding 模块失败：{exc}") from exc

        try:
            understanding_result = run_business_understanding(
                analysis_dir=self.analysis_dir,
                rules_path=settings.business_rules_path,
                output_dir=self.analysis_dir / "understanding" / "business",
            )
        except Exception as exc:
            raise AnalysisFatalError(f"M3 Business Understanding 无法继续：{exc}") from exc

        try:
            from .understanding.business.quality import (
                run_business_quality_assessment,
            )

            run_business_quality_assessment(
                analysis_dir=self.analysis_dir,
                output_dir=self.analysis_dir / "understanding" / "business",
            )
        except Exception as exc:
            raise AnalysisFatalError(f"M3.1 Business Quality Assessment 无法继续：{exc}") from exc

        try:
            from .understanding.business.objects import (
                run_business_object_analysis,
            )

            run_business_object_analysis(
                analysis_dir=self.analysis_dir,
                output_dir=self.analysis_dir / "understanding" / "business",
            )
        except Exception as exc:
            raise AnalysisFatalError(f"M3.2 Business Object Analysis 无法继续：{exc}") from exc

        try:
            from .understanding.business.processes import (
                run_business_process_analysis,
            )

            run_business_process_analysis(
                analysis_dir=self.analysis_dir,
                output_dir=self.analysis_dir / "understanding" / "business",
                rules_path=settings.process_rules_path,
            )
        except Exception as exc:
            raise AnalysisFatalError(f"M3.3 Business Process Analysis 无法继续：{exc}") from exc

        try:
            from .understanding.business.grain import (
                run_business_grain_analysis,
            )

            run_business_grain_analysis(
                analysis_dir=self.analysis_dir,
                output_dir=self.analysis_dir / "understanding" / "business",
            )
        except Exception as exc:
            raise AnalysisFatalError(f"M3.4 Grain Analysis 无法继续：{exc}") from exc

        try:
            from .understanding.modeling.business_model import (
                run_business_model_analysis,
            )

            run_business_model_analysis(
                analysis_dir=self.analysis_dir,
                output_dir=self.analysis_dir / "understanding" / "modeling",
            )
        except Exception as exc:
            raise AnalysisFatalError(f"M3.5 Business Model 分析无法继续：{exc}") from exc

        return understanding_result

    def run_stage_review(self) -> BusinessUnderstandingResult:
        """执行 Stage 01-14（Review）。"""
        understanding_result = self.run_stage_understanding()

        # 执行 M3.6 Review
        try:
            from .review.findings import run_current_state_model_analysis
        except ImportError as exc:
            raise AnalysisFatalError(f"导入 Review 模块失败：{exc}") from exc

        try:
            run_current_state_model_analysis(
                analysis_dir=self.analysis_dir,
                output_dir=self.analysis_dir / "review",
            )
        except Exception as exc:
            raise AnalysisFatalError(f"M3.6 Review 无法继续：{exc}") from exc

        return understanding_result

    # ==========================================================
    # M2.1 Analysis Scope Rules
    # ==========================================================

    def _build_scope(self, inventory: Inventory) -> FileScope:
        """执行 Inventory 内部的规则化分类（Analysis Scope Rules）。

        分类只依赖 Inventory 全量清单与只读 Snapshot；
        配置缺失或非法视为 Fatal Error，不回退默认规则，也不静默忽略。
        """

        try:
            rules = load_scope_rules(self.scope_rules_path)

        except ScopeRulesError as exc:
            raise AnalysisFatalError(f"M2.1 Analysis Scope Rules 无法继续：{exc}") from exc

        workspace_names = {
            workspace.workspace_id: workspace.workspace_name for workspace in inventory.workspaces
        }

        return build_file_scope(
            inventory.files,
            workspace_names,
            rules=rules,
            reader=self.reader,
        )

    # ==========================================================
    # M2.3 SQL Analysis
    # ==========================================================

    def _analyze_sql(
        self,
        files: list[FileInventory],
    ) -> tuple[list[StatementRecord], list[TableReference], list[ParseErrorRecord]]:
        """分析统一资格判定选出的 SQL 文件。

        入参由 FileScope.sql_eligible_files() 给出；
        Inventory 不在此处再叠加任何范围规则。
        """

        analyzer = SqlAnalyzer(
            reader=self.reader,
            ledger=self.ledger,
        )

        statements: list[StatementRecord] = []
        references: list[TableReference] = []
        parse_errors: list[ParseErrorRecord] = []

        for position, file in enumerate(files, start=1):
            if position % LOG_INTERVAL == 0:
                logger.info("SQL 分析进度：%s / %s", position, len(files))

            result = analyzer.analyze_file(file)

            statements.extend(result.statements)
            references.extend(result.references)
            parse_errors.extend(result.parse_errors)

        statements.sort(
            key=lambda item: (
                numeric_id_sort_key(item.workspace_id),
                numeric_id_sort_key(item.file_id),
                item.statement_id,
            )
        )
        references.sort(
            key=lambda item: (
                numeric_id_sort_key(item.workspace_id),
                numeric_id_sort_key(item.file_id),
                item.statement_id,
            )
        )
        parse_errors.sort(
            key=lambda item: (
                numeric_id_sort_key(item.workspace_id),
                numeric_id_sort_key(item.file_id),
                item.statement_id,
            )
        )

        return statements, references, parse_errors

    # ==========================================================
    # M2.2 Layer Assessment
    # ==========================================================

    def _run_layer_assessment(self) -> LayerAssessmentResult:
        """执行 M2.2 Layer Assessment，写出 analysis/evidence/layer 产物。

        输入固定为刚写出的 inventory/tables.json 与 layer-rules 配置；
        配置缺失或非法视为 Fatal Error，不静默跳过。
        """

        try:
            return run_layer_assessment(
                inventory_path=self.analysis_dir / "inventory" / "tables.json",
                rules_path=self.layer_rules_path,
                output_dir=self.analysis_dir / "evidence" / "layer",
            )

        except LayerAssessmentError as exc:
            raise AnalysisFatalError(f"M2.2 Layer Assessment 无法继续：{exc}") from exc

    # ==========================================================
    # 产物写出
    # ==========================================================

    def _write_inventory(self, inventory: Inventory, scope: FileScope) -> None:
        """写出 M2.1 产物：全量资产清单 + 规则分类的排除 / 待确认清单。

        files.json 始终包含全部登记文件，分类规则不会从中删除任何记录；
        excluded-tasks.json 与 review-tasks.json 是分析范围判定的产物，
        用 workspace_id + file_id 关联回 files.json，不是删除指令清单。
        """

        self._write(
            "inventory/workspaces.json",
            {
                "count": len(inventory.workspaces),
                "workspaces": [item.to_dict() for item in inventory.workspaces],
            },
        )
        self._write(
            "inventory/files.json",
            {
                "count": len(inventory.files),
                "files": [item.to_dict() for item in inventory.files],
            },
        )
        self._write(
            "inventory/tables.json",
            {
                "count": len(inventory.tables),
                "tables": [item.to_dict() for item in inventory.tables],
            },
        )
        self._write(
            "inventory/columns.json",
            {
                "count": len(inventory.columns),
                "columns": [item.to_dict() for item in inventory.columns],
            },
        )
        self._write("inventory/excluded-tasks.json", excluded_tasks_payload(scope))
        self._write("inventory/review-tasks.json", review_tasks_payload(scope))

    def _write_sql(
        self,
        statements: list[StatementRecord],
        references: list[TableReference],
        parse_errors: list[ParseErrorRecord],
    ) -> None:
        """写出 M2.3 产物。"""

        self._write(
            "evidence/sql/statements.json",
            {
                "count": len(statements),
                "statements": [item.to_dict() for item in statements],
            },
        )
        self._write(
            "evidence/sql/table-references.json",
            {
                "count": len(references),
                "references": [item.to_dict() for item in references],
            },
        )
        self._write(
            "evidence/sql/parse-errors.json",
            {
                "count": len(parse_errors),
                "errors": [item.to_dict() for item in parse_errors],
            },
        )

    def _write_lineage(self, lineage: LineageResult) -> None:
        """写出 M2.4 产物。"""

        self._write(
            "evidence/lineage/table-lineage.json",
            {
                "count": len(lineage.edges),
                "edges": [item.to_dict() for item in lineage.edges],
            },
        )
        self._write(
            "evidence/lineage/core-table-candidates.json",
            {
                "count": len(lineage.candidates),
                "sort_by": "downstream_count_desc",
                "candidates": [item.to_dict() for item in lineage.candidates],
            },
        )

    def _write_profiling(
        self,
        table_profiles: list[TableProfile],
        column_profiles: list[ColumnProfile],
    ) -> None:
        """写出 M2.5 产物。"""

        self._write(
            "evidence/profiling/tables.json",
            {
                "count": len(table_profiles),
                "tables": [item.to_dict() for item in table_profiles],
            },
        )
        self._write(
            "evidence/profiling/columns.json",
            {
                "count": len(column_profiles),
                "columns": [item.to_dict() for item in column_profiles],
            },
        )

    def _write_reports(
        self,
        *,
        inventory: Inventory,
        inventory_summary: InventorySummary,
        statements: list[StatementRecord],
        references: list[TableReference],
        parse_errors: list[ParseErrorRecord],
        lineage: LineageResult,
        table_profiles: list[TableProfile],
        column_profiles: list[ColumnProfile],
        layer_assessments: list[LayerAssessment],
        errors: list[dict[str, object]],
    ) -> Path:
        """写出各阶段 Summary 与总 Summary。"""

        write_text(
            self.analysis_dir / "inventory" / "summary.md",
            render_inventory_summary(inventory_summary),
        )
        write_text(
            self.analysis_dir / "evidence" / "lineage" / "summary.md",
            render_lineage_summary(lineage),
        )
        write_text(
            self.analysis_dir / "evidence" / "profiling" / "summary.md",
            render_profiling_summary(table_profiles, column_profiles),
        )

        summary_path = self.analysis_dir / "summary.md"

        write_text(
            summary_path,
            render_analysis_summary(
                SummaryContext(
                    inventory=inventory,
                    lineage=lineage,
                    statements=statements,
                    references=references,
                    parse_errors=parse_errors,
                    table_profiles=table_profiles,
                    column_profiles=column_profiles,
                    layer_assessments=layer_assessments,
                    errors=errors,
                )
            ),
        )

        return summary_path

    # ==========================================================
    # 内部工具
    # ==========================================================

    def _reset_outputs(self) -> None:
        """清空 Analysis 自有产物，保证每次运行结果确定。"""

        ensure_dir(self.analysis_dir)

        for name in PRODUCTION_DIRS:
            shutil.rmtree(self.analysis_dir / name, ignore_errors=True)

        for name in PRODUCTION_FILES:
            (self.analysis_dir / name).unlink(missing_ok=True)

        for name in LEGACY_PRODUCTION_FILES:
            (self.analysis_dir / name).unlink(missing_ok=True)

    def _write(self, relative_path: str, data: object) -> None:
        """写出单个 JSON 产物。"""

        write_json(
            self.analysis_dir / relative_path,
            data,
            overwrite=True,
        )


# 旧的生产文件定义，用于兼容性和清理逻辑
LEGACY_PRODUCTION_FILES = ("errors.json", "Summary.md")
"""旧的生产文件定义（用于兼容性检查和清理）。"""

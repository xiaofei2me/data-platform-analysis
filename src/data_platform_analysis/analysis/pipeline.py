"""Phase 2 Analysis 编排：M2.1 → M2.2 → M2.3 → M2.4。

输入：source/ Snapshot（只读）
输出：analysis/ Evidence Chain（每次全量重写，可重复执行）

执行顺序：

    1. 读取 Workspace identity（失败即 Fatal Error）
    2. M2.1 Inventory
    3. M2.2 SQL Analysis
    4. M2.3 Table Reference / Lineage
    5. M2.4 Metadata Profiling
    6. 写出 Summary 与错误账本
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..io_utils import ensure_dir, write_json, write_text
from .errors import ErrorLedger
from .inventory import Inventory, InventoryBuilder
from .lineage import LineageBuilder, LineageResult
from .models import (
    ColumnProfile,
    StatementRecord,
    TableProfile,
    TableReference,
    numeric_id_sort_key,
)
from .profiling import MetadataProfiler
from .reports import (
    SummaryContext,
    render_analysis_summary,
    render_inventory_summary,
    render_lineage_summary,
    render_profiling_summary,
)
from .snapshot import SnapshotReader
from .sql_analysis import ParseErrorRecord, SqlAnalyzer

logger = logging.getLogger(__name__)

PRODUCTION_DIRS: tuple[str, ...] = ("inventory", "sql", "lineage", "profiling")
PRODUCTION_FILES: tuple[str, ...] = ("errors.json", "Summary.md")

LOG_INTERVAL = 500
"""SQL 文件分析进度日志间隔。"""


@dataclass
class AnalysisResult:
    """一次 Analysis 运行的汇总结果。"""

    analysis_dir: Path
    workspace_ids: list[int] = field(default_factory=list)
    file_count: int = 0
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
        workspace_id: int | None = None,
    ) -> None:
        self.source_dir = source_dir
        self.analysis_dir = analysis_dir
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

        self._write_inventory(inventory)

        statements, references, parse_errors = self._analyze_sql(inventory)

        self._write_sql(statements, references, parse_errors)

        lineage = LineageBuilder(references, inventory).build()

        self._write_lineage(lineage)

        table_profiles, column_profiles = MetadataProfiler(inventory).profile()

        self._write_profiling(table_profiles, column_profiles)

        errors = self.ledger.records()

        summary_path = self._write_reports(
            inventory=inventory,
            statements=statements,
            references=references,
            parse_errors=parse_errors,
            lineage=lineage,
            table_profiles=table_profiles,
            column_profiles=column_profiles,
            errors=errors,
        )

        write_json(
            self.analysis_dir / "errors.json",
            {
                "count": len(errors),
                "errors": errors,
            },
        )

        result = AnalysisResult(
            analysis_dir=self.analysis_dir,
            workspace_ids=[identity.workspace_id for identity in identities],
            file_count=len(inventory.files),
            table_count=len(inventory.tables),
            column_count=len(inventory.columns),
            statement_count=len(statements),
            reference_count=len(references),
            edge_count=len(lineage.edges),
            error_count=len(errors),
            summary_path=summary_path,
        )

        logger.info(
            "Analysis 完成：workspace=%s，file=%s，table=%s，statement=%s，"
            "reference=%s，edge=%s，error=%s",
            len(result.workspace_ids),
            result.file_count,
            result.table_count,
            result.statement_count,
            result.reference_count,
            result.edge_count,
            result.error_count,
        )

        return result

    # ==========================================================
    # M2.2 SQL Analysis
    # ==========================================================

    def _analyze_sql(
        self,
        inventory: Inventory,
    ) -> tuple[list[StatementRecord], list[TableReference], list[ParseErrorRecord]]:
        """分析全部 SQL 文件。"""

        analyzer = SqlAnalyzer(
            reader=self.reader,
            ledger=self.ledger,
        )

        statements: list[StatementRecord] = []
        references: list[TableReference] = []
        parse_errors: list[ParseErrorRecord] = []

        for position, file in enumerate(inventory.files, start=1):
            if position % LOG_INTERVAL == 0:
                logger.info("SQL 分析进度：%s / %s", position, len(inventory.files))

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
    # 产物写出
    # ==========================================================

    def _write_inventory(self, inventory: Inventory) -> None:
        """写出 M2.1 产物。"""

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

    def _write_sql(
        self,
        statements: list[StatementRecord],
        references: list[TableReference],
        parse_errors: list[ParseErrorRecord],
    ) -> None:
        """写出 M2.2 产物。"""

        self._write(
            "sql/statements.json",
            {
                "count": len(statements),
                "statements": [item.to_dict() for item in statements],
            },
        )
        self._write(
            "sql/table-references.json",
            {
                "count": len(references),
                "references": [item.to_dict() for item in references],
            },
        )
        self._write(
            "sql/parse-errors.json",
            {
                "count": len(parse_errors),
                "errors": [item.to_dict() for item in parse_errors],
            },
        )

    def _write_lineage(self, lineage: LineageResult) -> None:
        """写出 M2.3 产物。"""

        self._write(
            "lineage/table-lineage.json",
            {
                "count": len(lineage.edges),
                "edges": [item.to_dict() for item in lineage.edges],
            },
        )
        self._write(
            "lineage/core-table-candidates.json",
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
        """写出 M2.4 产物。"""

        self._write(
            "profiling/tables.json",
            {
                "count": len(table_profiles),
                "tables": [item.to_dict() for item in table_profiles],
            },
        )
        self._write(
            "profiling/columns.json",
            {
                "count": len(column_profiles),
                "columns": [item.to_dict() for item in column_profiles],
            },
        )

    def _write_reports(
        self,
        *,
        inventory: Inventory,
        statements: list[StatementRecord],
        references: list[TableReference],
        parse_errors: list[ParseErrorRecord],
        lineage: LineageResult,
        table_profiles: list[TableProfile],
        column_profiles: list[ColumnProfile],
        errors: list[dict[str, object]],
    ) -> Path:
        """写出各阶段 Summary 与总 Summary。"""

        write_text(
            self.analysis_dir / "inventory" / "summary.md",
            render_inventory_summary(inventory),
        )
        write_text(
            self.analysis_dir / "lineage" / "summary.md",
            render_lineage_summary(lineage),
        )
        write_text(
            self.analysis_dir / "profiling" / "summary.md",
            render_profiling_summary(table_profiles, column_profiles),
        )

        summary_path = self.analysis_dir / "Summary.md"

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

    def _write(self, relative_path: str, data: object) -> None:
        """写出单个 JSON 产物。"""

        write_json(
            self.analysis_dir / relative_path,
            data,
            overwrite=True,
        )

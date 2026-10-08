"""M2.3 SQL Analysis：把 DataWorks SQL 文件拆成语句并解析成 AST。

处理流程：

    content 文本
      → 按顶层分号切分语句（基于 tokenizer，字符串里的分号不会被切开）
      → Parser Compatibility Normalization（只改 syntax context，见 normalization.py）
      → 逐条解析（dialect=odps）
      → 记录 parse_status、normalization_applied 与语句原文
      → 对解析成功的语句提取 source / target 表引用

失败处理：

    单条语句失败只影响该条语句，文件级与分析级继续执行；
    失败语句写入 analysis/evidence/sql/parse-errors.json 与 analysis/evidence/errors.json。
    归一化不会把真正的 parse error 伪装成 success。

CTAS Fallback：

    AST 解析为 unsupported（Command）且语句具备 CTAS 特征时，
    交给 token scanner 提取 source / target；
    提取成功则按 success 记录，extraction_method = fallback，
    scanner 无结果时保持 unsupported（SQL_UNSUPPORTED_STATEMENT）。
    fallback 属于 Fallback Extraction，与 Parser Compatibility Normalization
    是两个独立阶段：全角括号走 normalization，CTAS 走 fallback，互不混用。

输入范围：

    只有 NodeId 有效的 File 才进入 SQL Analysis；
    NodeId 为空的 File 直接跳过，不产生 statement / reference / parse error。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import sqlglot
from sqlglot import Dialect, exp
from sqlglot.errors import ParseError, TokenError
from sqlglot.tokens import TokenType

from ...errors import ErrorLedger
from ...models import (
    EXTRACTION_METHOD_AST,
    EXTRACTION_METHOD_FALLBACK,
    EXTRACTION_METHOD_NONE,
    PARSE_STATUS_ERROR,
    PARSE_STATUS_SUCCESS,
    PARSE_STATUS_UNSUPPORTED,
    FileInventory,
    StatementRecord,
    TableReference,
    is_analysis_eligible,
)
from ...snapshot import SnapshotReader
from ..lineage.references import extract_table_references
from .dialect import DIALECT, register_dialect
from .fallback import extract_ctas_references, is_ctas_statement
from .normalization import normalize_for_parser

register_dialect()

logger = logging.getLogger(__name__)

for _logger_name in ("sqlglot", "sqlglot.parser", "sqlglot.transpiler"):
    logging.getLogger(_logger_name).setLevel(logging.ERROR)

MAX_MESSAGE_LENGTH = 300
"""错误信息截断长度，避免把整段 SQL 写进错误账本。"""


@dataclass
class ParseErrorRecord:
    """写入 analysis/evidence/sql/parse-errors.json 的单条记录。"""

    workspace_id: int
    file_id: int | str
    node_id: int | str | None
    statement_id: int
    error_type: str
    message: str
    content_file: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "workspace_id": self.workspace_id,
            "file_id": self.file_id,
            "node_id": self.node_id,
            "statement_id": self.statement_id,
            "error_type": self.error_type,
            "message": self.message,
            "content_file": self.content_file,
        }


@dataclass
class SqlFileResult:
    """单个 DataWorks File 的 SQL 分析结果。"""

    statements: list[StatementRecord] = field(default_factory=list)
    references: list[TableReference] = field(default_factory=list)
    parse_errors: list[ParseErrorRecord] = field(default_factory=list)


def split_statements(content: str) -> tuple[list[str], str | None]:
    """按顶层分号切分语句。

    返回 (fragments, error_message)：
    只含注释或空白的片段不会返回；
    tokenizer 失败时返回空列表与错误信息。
    """

    tokenizer = Dialect.get_or_raise(DIALECT).tokenizer()

    try:
        tokens = tokenizer.tokenize(content)
    except TokenError as exc:
        return [], _truncate(str(exc))
    except Exception as exc:
        return [], _truncate(str(exc))

    fragments: list[str] = []
    start = 0
    has_tokens = False

    for token in tokens:
        if token.token_type is TokenType.SEMICOLON:
            if has_tokens:
                fragments.append(content[start : token.start])

            start = token.end + 1
            has_tokens = False

        else:
            has_tokens = True

    if has_tokens:
        fragments.append(content[start:])

    return [fragment.strip() for fragment in fragments if fragment.strip()], None


def parse_statement(parser_sql: str) -> tuple[str, list[exp.Expression], str | None]:
    """解析单条语句，返回 (parse_status, expressions, message)。

    入参是 parser input（raw fragment 或其归一化副本），
    原始 SQL 由调用方另行保留。
    """

    try:
        parsed = sqlglot.parse(parser_sql, dialect=DIALECT)

    except ParseError as exc:
        return PARSE_STATUS_ERROR, [], _truncate(str(exc))

    except Exception as exc:
        return PARSE_STATUS_ERROR, [], _truncate(str(exc))

    expressions = [
        node
        for node in parsed
        if isinstance(node, exp.Expression) and not isinstance(node, exp.Semicolon)
    ]

    if not expressions:
        return PARSE_STATUS_ERROR, [], "语句未产生任何 AST"

    if all(isinstance(node, exp.Command) for node in expressions):
        return PARSE_STATUS_UNSUPPORTED, [], "语句被解析为 Command，无法提取表引用"

    return PARSE_STATUS_SUCCESS, expressions, None


class SqlAnalyzer:
    """SQL 文件分析器。"""

    def __init__(
        self,
        reader: SnapshotReader,
        ledger: ErrorLedger,
    ) -> None:
        self.reader = reader
        self.ledger = ledger

    def analyze_file(self, file: FileInventory) -> SqlFileResult:
        """分析单个 DataWorks File，返回语句、表引用与解析错误。"""

        result = SqlFileResult()

        if not is_analysis_eligible(file):
            return result

        if file.content_format.upper() != "SQL":
            return result

        content, ok = self.reader.load_file_content(
            workspace_id=file.workspace_id,
            file_id=file.file_id,
            content_file=file.content_file,
        )

        if not ok or content is None or not content.strip():
            return result

        fragments, split_error = split_statements(content)

        if split_error is not None:
            self.ledger.add(
                stage="sql",
                error_type="SQL_TOKENIZE_ERROR",
                message=split_error,
                workspace_id=file.workspace_id,
                file_id=file.file_id,
                path=file.content_file,
            )

            return result

        for statement_id, fragment in enumerate(fragments, start=1):
            self._analyze_statement(result, file, statement_id, fragment)

        return result

    def _analyze_statement(
        self,
        result: SqlFileResult,
        file: FileInventory,
        statement_id: int,
        fragment: str,
    ) -> None:
        """分析单条语句并把结果追加到 SqlFileResult。

        fragment 是 raw SQL；归一化只产生 parser input，
        StatementRecord.sql 始终记录 fragment。
        """

        normalized = normalize_for_parser(fragment)
        parser_sql = normalized.sql

        status, expressions, message = parse_statement(parser_sql)

        extraction_method = (
            EXTRACTION_METHOD_AST if status == PARSE_STATUS_SUCCESS else EXTRACTION_METHOD_NONE
        )
        fallback_sources: list[str] = []
        fallback_targets: list[str] = []

        if status == PARSE_STATUS_UNSUPPORTED and is_ctas_statement(parser_sql):
            fallback_sources, fallback_targets = extract_ctas_references(parser_sql)

            if fallback_sources or fallback_targets:
                # CTAS fallback 命中：按解析成功记录，只在 extraction_method 上留痕。
                status = PARSE_STATUS_SUCCESS
                extraction_method = EXTRACTION_METHOD_FALLBACK
            else:
                message = "语句被解析为 Command，CTAS fallback 未提取到表引用"

        result.statements.append(
            StatementRecord(
                workspace_id=file.workspace_id,
                file_id=file.file_id,
                node_id=file.node_id,
                file_name=file.file_name,
                statement_id=statement_id,
                sql=fragment,
                dialect=DIALECT,
                parse_status=status,
                extraction_method=extraction_method,
                content_file=file.content_file,
                normalization_applied=normalized.applied,
                normalizations=[change.to_dict() for change in normalized.changes],
            )
        )

        if status == PARSE_STATUS_SUCCESS:
            if extraction_method == EXTRACTION_METHOD_FALLBACK:
                self._append_reference(
                    result,
                    file,
                    statement_id,
                    fallback_sources,
                    fallback_targets,
                    EXTRACTION_METHOD_FALLBACK,
                )
            else:
                self._extract_references(result, file, statement_id, expressions)

            return

        error_type = (
            "SQL_UNSUPPORTED_STATEMENT" if status == PARSE_STATUS_UNSUPPORTED else "SQL_PARSE_ERROR"
        )

        record = ParseErrorRecord(
            workspace_id=file.workspace_id,
            file_id=file.file_id,
            node_id=file.node_id,
            statement_id=statement_id,
            error_type=error_type,
            message=message or status,
            content_file=file.content_file,
        )

        result.parse_errors.append(record)

        self.ledger.add(
            stage="sql",
            error_type=error_type,
            message=record.message,
            workspace_id=file.workspace_id,
            file_id=file.file_id,
            statement_id=statement_id,
            path=file.content_file,
        )

    @classmethod
    def _extract_references(
        cls,
        result: SqlFileResult,
        file: FileInventory,
        statement_id: int,
        expressions: list[exp.Expression],
    ) -> None:
        """从解析成功的语句中提取表引用。"""

        sources: list[str] = []
        targets: list[str] = []

        for expression in expressions:
            statement_sources, statement_targets = extract_table_references(expression)

            sources.extend(item for item in statement_sources if item not in sources)
            targets.extend(item for item in statement_targets if item not in targets)

        cls._append_reference(
            result,
            file,
            statement_id,
            sources,
            targets,
            EXTRACTION_METHOD_AST,
        )

    @staticmethod
    def _append_reference(
        result: SqlFileResult,
        file: FileInventory,
        statement_id: int,
        sources: list[str],
        targets: list[str],
        extraction_method: str,
    ) -> None:
        """追加一条表引用记录；source 与 target 都为空时不记录。"""

        if not sources and not targets:
            return

        result.references.append(
            TableReference(
                workspace_id=file.workspace_id,
                file_id=file.file_id,
                node_id=file.node_id,
                file_name=file.file_name,
                statement_id=statement_id,
                source_tables=sorted(set(sources)),
                target_tables=sorted(set(targets)),
                extraction_method=extraction_method,
                content_file=file.content_file,
            )
        )


def _truncate(message: str, limit: int = MAX_MESSAGE_LENGTH) -> str:
    """截断超长错误信息。"""

    message = message.strip()

    if len(message) <= limit:
        return message

    return message[:limit]

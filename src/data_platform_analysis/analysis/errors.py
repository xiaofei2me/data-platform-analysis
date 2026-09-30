"""Analysis 阶段的错误分类与错误账本。

错误分成两类：

Fatal Error
    分析无法继续，必须以非零码退出。当前定义：

    1. source/ 目录不存在。
    2. 无法从任何 Snapshot 来源确定 Workspace identity。
    3. 用户指定的 --workspace 在 Snapshot 中不存在。

Recoverable Error
    单个对象级别的失败，记录后继续分析，最终写入
    analysis/errors.json（SQL 解析错误同时写入
    analysis/sql/parse-errors.json）。当前覆盖：

    1. 单个 index / raw JSON 损坏或缺失。
    2. 单条 SQL 语句解析失败或语法不受支持。
    3. 单个 content 文件缺失。
    4. 单张表的 metadata 缺失。

原则：

    一个对象失败 → 记录错误 → 继续分析，
    而不是整个 Analysis 失败。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class AnalysisFatalError(RuntimeError):
    """Analysis 无法继续的致命错误。"""


@dataclass(frozen=True)
class RecoverableError:
    """单个对象级别的可恢复错误。"""

    stage: str
    """产生错误的阶段：inventory / sql / lineage / profiling。"""

    error_type: str
    """错误类型，例如 PARSE_ERROR、CONTENT_MISSING。"""

    message: str
    """人类可读的错误说明。"""

    workspace_id: int | None = None

    file_id: int | str | None = None

    statement_id: int | None = None

    table: str | None = None

    path: str | None = None
    """与错误相关的 Snapshot / Content 相对路径。"""

    def to_dict(self) -> dict[str, Any]:
        """转换成稳定的 JSON 结构。"""

        return {
            "stage": self.stage,
            "error_type": self.error_type,
            "message": self.message,
            "workspace_id": self.workspace_id,
            "file_id": self.file_id,
            "statement_id": self.statement_id,
            "table": self.table,
            "path": self.path,
        }

    @property
    def sort_key(self) -> tuple[str, str, str, str, str, str]:
        """确定性排序键。"""

        return (
            self.stage,
            str(self.workspace_id or ""),
            str(self.file_id or ""),
            str(self.statement_id or ""),
            self.error_type,
            self.message,
        )


class ErrorLedger:
    """可恢复错误账本。

    账本只负责收集与排序，不决定退出码：
    是否致命由调用方通过 AnalysisFatalError 表达。
    """

    def __init__(self) -> None:
        self._errors: list[RecoverableError] = []

    def add(
        self,
        *,
        stage: str,
        error_type: str,
        message: str,
        workspace_id: int | None = None,
        file_id: int | str | None = None,
        statement_id: int | None = None,
        table: str | None = None,
        path: str | None = None,
    ) -> RecoverableError:
        """记录一条可恢复错误并返回它。"""

        error = RecoverableError(
            stage=stage,
            error_type=error_type,
            message=message,
            workspace_id=workspace_id,
            file_id=file_id,
            statement_id=statement_id,
            table=table,
            path=path,
        )

        self._errors.append(error)

        return error

    @property
    def errors(self) -> list[RecoverableError]:
        """按确定性顺序返回全部可恢复错误。"""

        return sorted(
            self._errors,
            key=lambda error: error.sort_key,
        )

    def __len__(self) -> int:
        return len(self._errors)

    def records(self) -> list[dict[str, Any]]:
        """返回可直接写出的 JSON 记录。"""

        return [error.to_dict() for error in self.errors]

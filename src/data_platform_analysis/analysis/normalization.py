"""Parser Compatibility Normalization：分析阶段专用的解析器兼容归一化。

定位（三层原则）：

    Raw Snapshot           = Source of Truth
    Normalized SQL         = Parser Input Only
    Analysis Output        = Derived Evidence

因此本模块：

1. 只在 Analysis 阶段运行，输入是 raw SQL 片段，输出是交给 parser 的副本；
   永远不写回 source/，也永远不改写 StatementRecord.sql。
2. 只做字符级等价替换，不做任何语法改写——
   真正的 unsupported / parse error 照常上报，不允许为了 errors=0 吞错。
3. 只在 SQL syntax context 替换；string literal 与 comment 里的字符保持原样。
4. 归一化只服务于解析器，因此不新增 extraction method：
   归一化后仍然走 AST extraction。

覆盖范围（第一阶段，不再自行扩展）：

    （ U+FF08 → ( U+0028
    ） U+FF09 → ) U+0029

这些全角括号是 DataWorks / MaxCompute 实际支持的写法，
属于 Parser Compatibility Gap，不是源 SQL 错误。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PAREN_NORMALIZATIONS: tuple[tuple[str, str], ...] = (
    ("（", "("),
    ("）", ")"),
)
"""第一阶段唯一允许替换的字符对。"""

_NORMALIZATIONS: dict[str, str] = dict(PAREN_NORMALIZATIONS)

_CANDIDATES: frozenset[str] = frozenset(_NORMALIZATIONS)

_STRING_QUOTES: tuple[str, ...] = ("'", '"')


@dataclass(frozen=True)
class NormalizationChange:
    """一次字符替换的统计。"""

    source: str
    target: str
    count: int

    def to_dict(self) -> dict[str, Any]:
        """转换成 StatementRecord.normalizations 里的稳定结构。"""

        return {"from": self.source, "to": self.target, "count": self.count}


@dataclass(frozen=True)
class NormalizationResult:
    """归一化结果。"""

    sql: str
    """可直接交给 parser 的 SQL；未命中时与输入完全相同。"""

    changes: tuple[NormalizationChange, ...]
    """按 PAREN_NORMALIZATIONS 顺序排列的替换统计。"""

    @property
    def applied(self) -> bool:
        """是否真的发生了替换（字符串 / 注释里的字符不算）。"""

        return bool(self.changes)


def normalize_for_parser(sql: str) -> NormalizationResult:
    """把 raw SQL 归一化成 parser input，只处理 syntax context。

    返回的 sql 只用于解析；调用方必须继续把 raw SQL 作为 Evidence 保留。
    """

    if not any(char in sql for char in _CANDIDATES):
        return NormalizationResult(sql=sql, changes=())

    pieces: list[str] = []
    counts: dict[str, int] = {}
    index = 0
    limit = len(sql)

    while index < limit:
        char = sql[index]

        if char == "-" and sql.startswith("--", index):
            end = _line_comment_end(sql, index)
            pieces.append(sql[index:end])
            index = end
            continue

        if char == "/" and sql.startswith("/*", index):
            end = _block_comment_end(sql, index)
            pieces.append(sql[index:end])
            index = end
            continue

        if char in _STRING_QUOTES or char == "`":
            end = _quoted_end(sql, index, char)
            pieces.append(sql[index:end])
            index = end
            continue

        replacement = _NORMALIZATIONS.get(char)

        if replacement is None:
            pieces.append(char)
            index += 1
            continue

        pieces.append(replacement)
        counts[char] = counts.get(char, 0) + 1
        index += 1

    changes = tuple(
        NormalizationChange(source, _NORMALIZATIONS[source], counts[source])
        for source, _ in PAREN_NORMALIZATIONS
        if source in counts
    )

    return NormalizationResult(sql="".join(pieces), changes=changes)


# ============================================================
# 状态机边界
# ============================================================


def _line_comment_end(sql: str, start: int) -> int:
    """返回 `--` 行注释结束位置（不含换行符）。"""

    end = sql.find("\n", start)

    return len(sql) if end == -1 else end


def _block_comment_end(sql: str, start: int) -> int:
    """返回 `/* ... */` 块注释结束位置；未闭合时到输入末尾。"""

    end = sql.find("*/", start + 2)

    return len(sql) if end == -1 else end + 2


def _quoted_end(sql: str, start: int, quote: str) -> int:
    """返回从 start 开始的引号区间结束位置（不含）。

    转义规则对齐 sqlglot ODPS/Hive tokenizer：

    - `'...'` 与 `"..."`：只认反斜杠转义，`''` 是两个独立字符串，
      因此这里也不把 `''` 当作转义；
    - `` `...` ``：只认引号重复（`` `a``b` ``）。

    未闭合时返回 len(sql)：后续字符整体按字面量保护，
    这样既不会误改内容，也不会掩盖真正需要上报的解析错误。
    """

    index = start + 1
    limit = len(sql)
    backslash_escapes = quote in _STRING_QUOTES

    while index < limit:
        char = sql[index]

        if backslash_escapes and char == "\\" and index + 1 < limit:
            index += 2
            continue

        if char == quote:
            if index + 1 < limit and sql[index + 1] == quote:
                index += 2
                continue

            return index + 1

        index += 1

    return limit

"""M2.3 SQL Fallback：AST 解析失败时，用 token scanner 提取 CTAS 的表引用。

原则：

1. 只在 AST 解析为 unsupported（exp.Command）且语句具备 CTAS 特征时使用。
2. scanner 是单向前扫描：每一轮循环游标都必须严格前进。
   任何分支都不允许停在同一个 token 上继续下一轮，否则会死循环。
3. sqlglot tokenizer 不产出 SPACE token，代码不得依赖空白跳过。
4. `${...}` DataWorks 参数整体收集，之后统一交给
   normalize_scheduler_variables 归一化成 project.table 形式。
5. LATERAL VIEW 是 function call，不是 subquery，也不产生表引用。
6. 输出 (sources, targets) 均已去重、排序，保持 project.table 原始写法。

历史缺陷（本次重写修复）：

- 旧 `_extract_from_joins` 的 FROM 分支末尾 `continue` 却从不前进游标，
  外层提取循环每次看到的第一个 token 仍是 FROM，命中 `else: break` 后
  外层 `continue` 回到同一索引，形成无限循环。
"""

from __future__ import annotations

import re

from sqlglot.tokens import Token, Tokenizer, TokenType

from ..naming import normalize_scheduler_variables
from .dialect import DIALECT, register_dialect

register_dialect()

TokenList = list[Token]

# CTAS 特征：CREATE TABLE ... AS <query>。
#
# 语句片段常带行首注释，AS 与 SELECT 之间也可能夹注释，
# 因此这些位置用 _GAP 允许空白与注释。
_GAP = r"(?:\s|--[^\n]*(?:\n|$)|/\*[\s\S]*?\*/)*"
_CTAS_PATTERN = re.compile(
    r"^" + _GAP + r"create\s+(?:or\s+replace\s+)?(?:temp(?:orary)?\s+|external\s+)?table\b"
    r"[\s\S]*?\bas\b" + _GAP + r"\(?" + _GAP + r"(?:with|select)\b",
    re.IGNORECASE,
)

# 可以出现在表名里的 token。
# STRING 不在其中：它是字面量（例如 max_pt('...') 的参数），不是表名。
_NAME_TOKENS = frozenset(
    {
        TokenType.VAR,
        TokenType.IDENTIFIER,
        TokenType.PARAMETER,
    }
)

# CREATE 与 TABLE 之间允许的修饰词。
# keyword 的 token 类型不统一（OR / REPLACE / TEMPORARY / VAR），按文本判断。
_CREATE_MODIFIERS = frozenset({"OR", "REPLACE", "TEMP", "TEMPORARY", "EXTERNAL", "GLOBAL", "LOCAL"})

# CREATE TABLE 之后可能出现的 IF NOT EXISTS。
_IF_NOT_EXISTS = frozenset({"IF", "NOT", "EXISTS"})

# 触发 relation 扫描的 keyword。
_RELATION_KEYWORDS = (TokenType.FROM, TokenType.JOIN)


def is_ctas_statement(fragment: str) -> bool:
    """判断语句是否具备 CTAS 特征（CREATE TABLE ... AS <query>）。

    用于给 fallback 加门槛：只有 CTAS 才交给 token scanner，
    其他 unsupported 语句（例如 MSCK REPAIR TABLE）保持原有行为。
    """

    return _CTAS_PATTERN.match(fragment) is not None


def extract_ctas_references(raw_sql: str) -> tuple[list[str], list[str]]:
    """从 CTAS 的 raw SQL 中提取 (sources, targets)。

    两个列表都已去重、排序；`${...}` 已归一化，
    目标表不会同时出现在 sources 里。

    tokenizer 失败时返回 ([], [])，由调用方决定是否保留 unsupported 状态。
    """

    try:
        tokens = list(Tokenizer(dialect=DIALECT).tokenize(raw_sql))
    except Exception:
        return [], []

    targets = _extract_ctas_target(tokens)
    target_set = set(targets)
    cte_names = _cte_names(tokens)
    sources = [name for name in _extract_sources(tokens, cte_names) if name not in target_set]

    return sorted(set(sources)), sorted(set(targets))


# ============================================================
# CREATE TABLE <target>
# ============================================================


def _extract_ctas_target(tokens: TokenList) -> list[str]:
    """提取 CREATE TABLE <target> 的 target 表，最多返回一个。"""

    i = 0
    n = len(tokens)

    while i < n:
        if tokens[i].token_type is not TokenType.CREATE:
            i += 1
            continue

        name = _target_after_create(tokens, i, n)

        if name:
            return [normalize_scheduler_variables(name)]

        # 该 CREATE 不是 CREATE TABLE（例如 CREATE VIEW），继续找下一个。
        i += 1

    return []


def _target_after_create(tokens: TokenList, create_index: int, stop: int) -> str | None:
    """从 CREATE 开始读取 target 表名，读不到返回 None。"""

    i = create_index + 1

    while i < stop and tokens[i].text.upper() in _CREATE_MODIFIERS:
        i += 1

    if i >= stop or tokens[i].token_type is not TokenType.TABLE:
        return None

    i += 1

    while i < stop and tokens[i].text.upper() in _IF_NOT_EXISTS:
        i += 1

    name, _ = _collect_table_name(tokens, i, stop)

    return name


# ============================================================
# FROM / JOIN
# ============================================================


def _extract_sources(tokens: TokenList, cte_names: frozenset[str]) -> list[str]:
    """扫描全部 FROM / JOIN 后的物理表，排除 CTE 与 table function。"""

    sources: list[str] = []
    _scan_range(tokens, 0, len(tokens), sources, cte_names)

    return sources


def _scan_range(
    tokens: TokenList,
    i: int,
    stop: int,
    sources: list[str],
    cte_names: frozenset[str],
) -> int:
    """扫描 [i, stop) 区间内的 FROM / JOIN，返回结束游标。

    每轮循环游标严格前进：命中 keyword 后交给 _scan_relation（保证前进），
    否则 i += 1，不存在停在同一 token 上的分支。
    """

    while i < stop:
        if tokens[i].token_type in _RELATION_KEYWORDS:
            i = _scan_relation(tokens, i + 1, stop, sources, cte_names)
            continue

        i += 1

    return i


def _scan_relation(
    tokens: TokenList,
    i: int,
    stop: int,
    sources: list[str],
    cte_names: frozenset[str],
) -> int:
    """处理 FROM / JOIN 之后的一个 relation，返回游标。

    返回值严格大于入参 i（入参 < stop 时），这是不产生死循环的关键。
    """

    # 子查询：先递归收集括号内部的 FROM / JOIN，再回到外层处理 alias 与逗号列表。
    if i >= stop:
        return i

    from_subquery = False

    while i < stop and tokens[i].token_type is TokenType.L_PAREN:
        close = _matching_paren(tokens, i, stop)
        _scan_range(tokens, i + 1, close, sources, cte_names)
        i = close + 1
        from_subquery = True

    name: str | None = None

    if not from_subquery and i < stop:
        name, i = _collect_table_name(tokens, i, stop)

        if name is None:
            # 未识别的 token（例如 LATERAL）：跳过一个，交给外层继续扫描。
            return i

        # table function，例如 explode(...)：不是物理表。
        if i < stop and tokens[i].token_type is TokenType.L_PAREN:
            i = _matching_paren(tokens, i, stop) + 1
            name = None

    # alias：`as x` 或隐式 `x`，最多跳过一个名字 token。
    # 子查询与 table function 之后只有 alias，没有物理表名。
    if i < stop and tokens[i].token_type is TokenType.ALIAS:
        i += 1

        if i < stop and tokens[i].token_type in _NAME_TOKENS:
            i += 1

    elif i < stop and tokens[i].token_type in _NAME_TOKENS:
        i += 1

    if name is not None and name.casefold() not in cte_names:
        sources.append(normalize_scheduler_variables(name))

    # FROM 子句的逗号列表：from a, b
    if i < stop and tokens[i].token_type is TokenType.COMMA:
        return _scan_relation(tokens, i + 1, stop, sources, cte_names)

    return i


def _collect_table_name(tokens: TokenList, i: int, stop: int) -> tuple[str | None, int]:
    """从 i 开始收集一个 dotted table reference。

    返回 (name, next_i)；当 i < stop 时 next_i 严格大于 i，
    保证调用方无论是否收集到表名都能前进。
    """

    start = i
    parts: list[str] = []
    expect_name = True

    while i < stop:
        token = tokens[i]

        if expect_name:
            if token.token_type not in _NAME_TOKENS:
                break

            if token.text == "$":
                # ${param} 整体收集；裸 $ 不构成表名。
                if i + 1 >= stop or tokens[i + 1].token_type is not TokenType.L_BRACE:
                    break

                buffer = ["$"]
                j = i + 1

                while j < stop and tokens[j].token_type is not TokenType.R_BRACE:
                    buffer.append(tokens[j].text)
                    j += 1

                if j >= stop:
                    # 未闭合参数：游标已推进到 stop。
                    parts.append("".join(buffer))
                    i = j
                    break

                buffer.append(tokens[j].text)
                parts.append("".join(buffer))
                i = j + 1

            else:
                parts.append(token.text)
                i += 1

            expect_name = False
            continue

        if token.token_type is TokenType.DOT:
            parts.append(".")
            i += 1
            expect_name = True
            continue

        break

    if not parts:
        return None, (i if i > start else start + 1)

    name = "".join(parts)

    # `a.` 这类不完整的引用去掉结尾的点。
    if expect_name and name.endswith("."):
        name = name[:-1]

    if not name:
        return None, (i if i > start else start + 1)

    return name, i


def _matching_paren(tokens: TokenList, i: int, stop: int) -> int:
    """返回 i 处 L_PAREN 的配对 R_PAREN 下标；未闭合时返回 stop。"""

    depth = 0

    while i < stop:
        token_type = tokens[i].token_type

        if token_type is TokenType.L_PAREN:
            depth += 1

        elif token_type is TokenType.R_PAREN:
            depth -= 1

            if depth == 0:
                return i

        i += 1

    return stop


def _cte_names(tokens: TokenList) -> frozenset[str]:
    """收集 `<name> as (` 形式的 CTE 名称（仅当语句包含 WITH 时）。"""

    if not any(token.token_type is TokenType.WITH for token in tokens):
        return frozenset()

    names: set[str] = set()
    i = 0
    limit = len(tokens) - 2

    while i < limit:
        if (
            tokens[i].token_type in _NAME_TOKENS
            and tokens[i + 1].token_type is TokenType.ALIAS
            and tokens[i + 2].token_type is TokenType.L_PAREN
        ):
            names.add(tokens[i].text.casefold())

        i += 1

    return frozenset(names)

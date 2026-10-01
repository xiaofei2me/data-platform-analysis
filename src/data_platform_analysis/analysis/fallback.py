"""M2.2 SQL Fallback：当 AST 解析失败时，使用简单 scanner 提取表引用。

原则：

1. 仅在 AST 解析为 Command 或其他 unsupported 类型时使用 fallback。
2. 使用简单的 scanner 提取 FROM/JOIN 后的表名（只在必要时使用）。
3. 排除 alias、CTE、subquery。
4. 支持 CTAS target 提取（CREATE TABLE <target> AS）。
5. 保持现有的 project.table 格式，不做转换。

问题修复：

1. ${...} DataWorks 参数必须完整保留，不能拆成 $ { xxx }
2. LATERAL VIEW 是 function call，不是 subquery
3. Physical table + alias 必须正确识别边界
"""

from __future__ import annotations

from sqlglot import exp
from sqlglot.tokens import Tokenizer, TokenType

from .dialect import DIALECT, register_dialect
from .naming import normalize_scheduler_variables

register_dialect()


def extract_ctas_references(
    raw_sql: str,
) -> tuple[list[str], list[str]]:
    """从 CTAS (CREATE TABLE AS SELECT) 的 raw SQL 中提取 target 和 source 表。

    当 sqlglot 将语句解析为 Command 时调用此函数。

    返回 (sources, targets)，结果已去重并保持原始 project.table 格式。
    """

    try:
        tokenizer = Tokenizer(dialect=DIALECT)
        tokens = list(tokenizer.tokenize(raw_sql))
    except Exception:
        return [], []

    target = _extract_ctas_target(tokens)
    targets = [target] if target else []
    sources = _extract_from_joins(tokens)

    # 目标表不计入 source
    targets_set = set(targets)
    sources = [s for s in sources if s not in targets_set]

    return sorted(set(sources)), sorted(targets)


def _extract_ctas_target(tokens: list) -> str | None:
    """从 token 流中提取 CREATE TABLE 的 target 表。"""

    for i, token in enumerate(tokens):
        if token.token_type == TokenType.CREATE:
            j = i + 1
            while j < len(tokens) and tokens[j].token_type == TokenType.SPACE:
                j += 1
            if j < len(tokens) and tokens[j].token_type == TokenType.TABLE:
                j += 1

            while j < len(tokens) and tokens[j].token_type == TokenType.SPACE:
                j += 1

            if j < len(tokens) and tokens[j].text.upper() == "IF":
                while j < len(tokens) and tokens[j].token_type in (TokenType.SPACE, TokenType.VAR):
                    j += 1

            while j < len(tokens) and tokens[j].token_type == TokenType.SPACE:
                j += 1

            if j >= len(tokens):
                return None

            parts = []
            while j < len(tokens) and tokens[j].token_type in (
                TokenType.VAR,
                TokenType.PARAMETER,
                TokenType.DOT,
                TokenType.L_BRACE,
                TokenType.R_BRACE,
            ):
                parts.append(tokens[j].text)
                j += 1

            if not parts:
                return None

            table_ref = "".join(parts)

            while j < len(tokens) and tokens[j].token_type != TokenType.ALIAS:
                if tokens[j].token_type == TokenType.SPACE:
                    j += 1
                    continue
                if tokens[j].token_type == TokenType.VAR and tokens[j].text.upper() == "AS":
                    break
                parts.append(tokens[j].text)
                j += 1

            table_ref = "".join(parts).split(" AS ")[0].strip()

            return normalize_scheduler_variables(table_ref)

    return None


def _is_alias_context(tokens: list, i: int) -> bool:
    """判断位置 i 的 VAR token 是否是 alias 上下文。
    
    alias 通常在以下场景出现：
    - FROM/JOIN 后的表名后面（implicit 或 AS）
    - Subquery 闭合括号后
    - LATERAL VIEW function call 后
    """
    
    if i <= 0:
        return False
    
    prev = tokens[i - 1]
    
    # 如果前一个 token 是 ) 或 R_BRACE，当前可能是 subquery alias
    if prev.token_type in (TokenType.R_PAREN, TokenType.R_BRACE):
        return True
    
    # 如果前一个 token 是 whitespace，当前可能是 alias
    if prev.token_type == TokenType.SPACE:
        # 查看前前 token 是否是 table name end
        if i >= 2:
            prev_prev = tokens[i - 2]
            # 如果前前 token 是 VAR（表名的一部分）或 R_PAREN，当前可能是 alias
            if prev_prev.token_type in (TokenType.VAR, TokenType.R_PAREN):
                return True
    
    # 如果前一个 token 是 LATERAL VIEW，当前是 lateral view alias
    if prev.token_type == TokenType.VIEW or (
        prev.token_type == TokenType.VAR and prev.text.upper() == "LATERAL"
    ):
        return True
    
    return False


def _extract_from_joins(tokens: list) -> list[str]:
    """从 token 流中提取所有 FROM 和 JOIN 后的物理表。

    使用状态机判断 alias，只提取 physical table。
    """

    sources: list[str] = []
    seen_aliases: set[str] = set()

    i = 0
    while i < len(tokens):
        token = tokens[i]

        # 跳过 WITH (CTE)
        if token.token_type == TokenType.WITH:
            i += 1
            depth = 0
            while i < len(tokens):
                if tokens[i].token_type == TokenType.VAR:
                    i += 1
                    while i < len(tokens) and tokens[i].token_type != TokenType.ALIAS:
                        if tokens[i].token_type == TokenType.L_PAREN:
                            break
                        i += 1
                    continue
                if tokens[i].token_type == TokenType.ALIAS:
                    i += 1
                    while i < len(tokens) and tokens[i].token_type == TokenType.VAR:
                        i += 1
                    continue
                if tokens[i].token_type == TokenType.L_PAREN:
                    depth += 1
                elif tokens[i].token_type == TokenType.R_PAREN:
                    depth -= 1
                if tokens[i].token_type == TokenType.SELECT and depth == 0:
                    break
                i += 1
            continue

        # 检查 FROM 或 JOIN
        if token.token_type in (TokenType.FROM, TokenType.JOIN):
            # 处理 LEFT JOIN
            if token.token_type == TokenType.LEFT:
                i += 1
                # 跳过空白
                while i < len(tokens) and tokens[i].token_type == TokenType.SPACE:
                    i += 1
                # 检查下一个是 JOIN
                if i < len(tokens) and tokens[i].token_type == TokenType.JOIN:
                    # 这是 LEFT JOIN，跳过整个 JOIN
                    i += 1
                else:
                    # 单独的 LEFT，当成未知 token
                    i += 1
                    continue

            # 跳过空白
            while i < len(tokens) and tokens[i].token_type == TokenType.SPACE:
                i += 1

            if i >= len(tokens):
                break

            # 检查是否是子查询（用 L_PAREN）
            if tokens[i].token_type == TokenType.L_PAREN:
                depth = 1
                i += 1

                while i < len(tokens) and depth > 0:
                    if tokens[i].token_type == TokenType.L_PAREN:
                        depth += 1
                    elif tokens[i].token_type == TokenType.R_PAREN:
                        depth -= 1
                    i += 1

                # 跳过空白
                while i < len(tokens) and tokens[i].token_type == TokenType.SPACE:
                    i += 1

                # 检查 alias (AS name 或 just name)
                if i < len(tokens) and tokens[i].token_type == TokenType.VAR:
                    alias = tokens[i].text
                    seen_aliases.add(alias.lower())

                continue

            # 提取表名（直到空白、逗号、JOIN 或 WHERE）
            parts = []

            while i < len(tokens):
                t = tokens[i]

                # 跳过空白
                if t.token_type == TokenType.SPACE:
                    i += 1
                    continue

                # 检查是否是 JOIN/WHERE/COMMA（停止）
                if t.token_type in (TokenType.COMMA, TokenType.JOIN, TokenType.WHERE):
                    break
                # LEFT JOIN 处理（上面已经处理了）
                if t.token_type == TokenType.LEFT:
                    # 这是另一个 LEFT JOIN，停止当前提取
                    break

                # LATERAL VIEW 处理：跳过整个 LATERAL VIEW，不提取 alias
                if t.token_type == TokenType.LATERAL or (
                    t.token_type == TokenType.VAR and t.text.upper() == "LATERAL"
                ):
                    # 跳过 LATERAL
                    i += 1
                    while i < len(tokens) and tokens[i].token_type != TokenType.VIEW:
                        i += 1
                    if i < len(tokens):
                        i += 1  # 跳过 VIEW

                    # 跳过 function name (例如 explode)
                    while i < len(tokens) and tokens[i].token_type == TokenType.VAR:
                        i += 1

                    # 跳过 function call (例如 (...) 内容)
                    while i < len(tokens):
                        if tokens[i].token_type == TokenType.L_PAREN:
                            depth = 1
                            i += 1
                            while i < len(tokens) and depth > 0:
                                if tokens[i].token_type == TokenType.L_PAREN:
                                    depth += 1
                                elif tokens[i].token_type == TokenType.R_PAREN:
                                    depth -= 1
                                i += 1
                        elif tokens[i].token_type in (TokenType.COMMA, TokenType.SPACE):
                            i += 1
                        else:
                            break

                    # 跳过 lateral view alias (例如 tt)
                    while i < len(tokens) and tokens[i].token_type == TokenType.SPACE:
                        i += 1

                    if i < len(tokens) and tokens[i].token_type == TokenType.VAR:
                        seen_aliases.add(tokens[i].text.lower())

                    # 继续处理，但不 break（可能后面还有 JOIN）
                    continue

                # 检查 alias
                if t.token_type == TokenType.ALIAS:
                    i += 1
                    # 跳过 AS 后的 alias 名称
                    if i < len(tokens) and tokens[i].token_type == TokenType.VAR:
                        seen_aliases.add(tokens[i].text.lower())
                    # 停止提取当前表名
                    break
                
                # 处理 implicit alias (没有 AS 关键字)
                if t.token_type == TokenType.VAR and _is_alias_context(tokens, i):
                    # 这是 alias，停止提取
                    seen_aliases.add(t.text.lower())
                    i += 1
                    break

                # ON 子句：跳过整个 ON 条件
                if t.token_type == TokenType.ON:
                    i += 1
                    while i < len(tokens):
                        if tokens[i].token_type in (
                            TokenType.COMMA,
                            TokenType.JOIN,
                            TokenType.WHERE,
                        ):
                            break
                        i += 1
                    i += 1
                    continue

                # 收集表名部分（VAR, PARAMETER, DOT）
                if t.token_type in (
                    TokenType.VAR,
                    TokenType.PARAMETER,
                    TokenType.DOT,
                    TokenType.IDENTIFIER,
                ):
                    parts.append(t.text)
                    i += 1
                elif t.token_type == TokenType.L_BRACE:
                    # ${...} 参数：收集整个参数表达式
                    parts.append(t.text)
                    i += 1
                    # 收集直到 R_BRACE
                    while i < len(tokens) and tokens[i].token_type != TokenType.R_BRACE:
                        parts.append(tokens[i].text)
                        i += 1
                    if i < len(tokens):
                        parts.append(tokens[i].text)
                        i += 1
                else:
                    # 其他 token，停止提取
                    break

            if parts:
                table_ref = "".join(parts)

                # 排除 alias
                if table_ref.lower() not in seen_aliases:
                    sources.append(normalize_scheduler_variables(table_ref))

            # continue 回主循环，不执行 i += 1
            continue

        # UNION 处理
        if token.token_type == TokenType.UNION:
            i += 1
            # 跳过 ALL
            while i < len(tokens) and tokens[i].token_type == TokenType.ALL:
                i += 1
            # 跳过空白
            while i < len(tokens) and tokens[i].token_type == TokenType.SPACE:
                i += 1
            # 检查 SELECT
            if i < len(tokens) and tokens[i].token_type == TokenType.SELECT:
                # 这是一个 UNION SELECT，继续处理
                continue
            continue

        i += 1

    return sources


def should_fallback(expression: exp.Expression) -> bool:
    """判断语句是否应该使用 fallback 提取表引用。"""

    return isinstance(expression, exp.Command)

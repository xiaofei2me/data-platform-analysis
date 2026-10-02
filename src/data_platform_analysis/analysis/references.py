"""M2.4 Table Reference：从 SQL AST 提取 source / target 表引用。

提取规则：

1. target = 写入目标（INSERT / CREATE TABLE / CREATE VIEW / MERGE /
   UPDATE / DELETE 的目标表）。
2. source = 语句读取的表，只在“可读语句根类型”上提取，
   避免 DROP / ALTER / SET / USE 这类语句产生虚假引用。
3. 以下表不算 source：
   - 与 target 是同一个表（原地重写不构成血缘）；
   - CTE 别名（WITH ... AS）；
   - CREATE TABLE ... LIKE 中的模板表（只复制结构，不读数据）。
4. 表名先从 AST 还原，再做 ${scheduler_variable} 归一化，
   原始 SQL 文本不被改写。
"""

from __future__ import annotations

from sqlglot import exp

from .dialect import DIALECT, register_dialect
from .naming import normalize_scheduler_variables

register_dialect()

READ_ROOT_TYPES: tuple[type[exp.Expression], ...] = (
    exp.Select,
    exp.Insert,
    exp.Create,
    exp.Union,
    exp.Merge,
    exp.Update,
    exp.Delete,
    exp.With,
    exp.Subquery,
    exp.Values,
)
"""允许提取 source 的语句根类型。"""

TARGET_TYPES: tuple[type[exp.Expression], ...] = (
    exp.Insert,
    exp.Create,
    exp.Merge,
    exp.Update,
    exp.Delete,
)
"""产生 target 的语句节点类型。"""

CREATE_TARGET_KINDS = frozenset({"TABLE", "VIEW"})
"""只有 CREATE TABLE / CREATE VIEW 产生 target。"""


def table_ref_of(table: exp.Table) -> str:
    """把 AST 中的表节点还原成 SQL 书写形式的表标识。

    例：`${dme_cdm}.dwd_order` → `dme_cdm.dwd_order`。
    """

    parts: list[str] = []

    for part in table.parts:
        if isinstance(part, exp.Identifier):
            parts.append(part.name)
        else:
            parts.append(part.sql(dialect=DIALECT))

    reference = ".".join(part for part in parts if part)

    return normalize_scheduler_variables(reference)


def extract_table_references(
    expression: exp.Expression,
) -> tuple[list[str], list[str]]:
    """提取单条语句的 (sources, targets)，结果已排序去重。"""

    if not isinstance(expression, exp.Expression):
        return [], []

    targets = _target_tables(expression)
    target_set = set(targets)

    if not isinstance(expression, READ_ROOT_TYPES):
        return [], sorted(target_set)

    cte_names = {cte.alias_or_name.casefold() for cte in expression.find_all(exp.CTE)}

    structural = _structural_tables(expression)
    sources: list[str] = []

    for table in expression.find_all(exp.Table):
        if id(table) in structural:
            continue

        reference = table_ref_of(table)

        if not reference or reference in target_set:
            continue

        if table.name.casefold() in cte_names:
            continue

        if reference not in sources:
            sources.append(reference)

    return sorted(sources), sorted(target_set)


# ============================================================
# 内部工具
# ============================================================


def _target_tables(expression: exp.Expression) -> list[str]:
    """收集语句的写入目标表。"""

    targets: list[str] = []

    for node in expression.find_all(*TARGET_TYPES):
        table = _target_table(node)

        if table is None:
            continue

        reference = table_ref_of(table)

        if reference and reference not in targets:
            targets.append(reference)

    return targets


def _target_table(node: exp.Expression) -> exp.Table | None:
    """返回单个写入节点的目标表。"""

    if isinstance(node, exp.Create):
        kind = str(node.args.get("kind") or "").upper()

        if kind not in CREATE_TARGET_KINDS:
            return None

    target = node.this

    if isinstance(target, exp.Schema):
        target = target.this

    return target if isinstance(target, exp.Table) else None


def _structural_tables(expression: exp.Expression) -> set[int]:
    """返回只用于结构复制的表节点（CREATE TABLE ... LIKE）。"""

    structural: set[int] = set()

    for node in expression.find_all(exp.Create):
        properties = node.args.get("properties")

        if not isinstance(properties, exp.Expression):
            continue

        structural.update(id(table) for table in properties.find_all(exp.Table))

    return structural

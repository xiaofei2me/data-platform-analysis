"""ODPS SQL 方言注册。

sqlglot 官方方言列表没有 ODPS / MaxCompute，因此这里注册一个
基于 Hive 的 ODPS 方言别名，使所有解析调用统一使用 dialect="odps"。

与 Hive 的差异：

1. 支持 MaxCompute 的 `LIFECYCLE <days>` 表属性，否则
   `CREATE TABLE ... LIFECYCLE 1095` 会退化成 Command。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from sqlglot import Dialect, exp
from sqlglot.dialects.hive import Hive, HiveParser

DIALECT = "odps"


class ODPS(Hive):
    """MaxCompute SQL，按 Hive 方言解析。"""

    class Parser(HiveParser):
        PROPERTY_PARSERS: ClassVar[dict[str, Callable[..., Any]]] = {
            **HiveParser.PROPERTY_PARSERS,
            "LIFECYCLE": lambda self: self.expression(
                exp.Property(
                    this=exp.Var(this="LIFECYCLE"),
                    value=self._parse_number(),
                )
            ),
        }


def register_dialect() -> str:
    """确认 ODPS 方言已注册，返回方言名。

    ODPS 类定义时 sqlglot 会自动登记，这里只做一次显式校验。
    """

    Dialect.get_or_raise(DIALECT)

    return DIALECT

"""表名归一化与表标识工具。

本阶段的硬性原则：

    命名规则只能产生 Candidate，不能当作事实。

因此这里只提供：

1. 调度变量归一化（只作用于提取出来的表名，不改写原始 SQL）。
2. 表标识（project.table）的补齐与拆解，用于保留跨 Project 信息。

层级候选（candidate_layer）由 M2.5 Layer Assessment 依据 workspace 事实
与 config/layer-rules.yaml 产出，不在本模块范围内。

禁止在这里做业务推断，例如 business_domain / grain / fact。
"""

from __future__ import annotations

import re

# DataWorks 调度变量，例如 ${dme_cdm}、${bizdate}。
SCHEDULER_VARIABLE_RE = re.compile(r"\$\{([^{}]*)\}")


def normalize_scheduler_variables(text: str) -> str:
    """把 ${name} 归一化成 name。

    作用对象是提取出来的表名，不是原始 SQL 文本：

        ${dme_cdm}.dwd_order  →  dme_cdm.dwd_order

    这样才能保留 project.table 形式，识别跨 Project 引用。
    """

    return SCHEDULER_VARIABLE_RE.sub(
        lambda match: match.group(1),
        text,
    )


def split_table_ref(table_ref: str) -> list[str]:
    """按 . 拆分表标识。"""

    return [part for part in table_ref.split(".") if part]


def table_name_of(table_ref: str) -> str:
    """返回表标识中的表名部分。"""

    parts = split_table_ref(table_ref)

    return parts[-1] if parts else table_ref


def project_of(table_ref: str) -> str | None:
    """返回表标识中的 Project 部分，没有限定符时返回 None。"""

    parts = split_table_ref(table_ref)

    if len(parts) < 2:
        return None

    return parts[0]


def qualify_table_ref(table_ref: str, project: str | None) -> str:
    """把裸表名补齐成 project.table。

    MaxCompute 中未限定的表名指向当前 Project，
    因此裸名可以用当前 Workspace 对应的 Project 补齐。
    已经带限定符的引用保持原样，跨 Project 信息不会丢失。
    """

    if not table_ref:
        return table_ref

    if project_of(table_ref) is not None:
        return table_ref

    if not project:
        return table_ref

    return f"{project}.{table_ref}"

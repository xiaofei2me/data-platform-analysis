"""Parser Compatibility Normalization 的单元测试与黑盒测试。

背景：

    DataWorks / MaxCompute 实际支持全角括号（（ U+FF08、） U+FF09），
    但 sqlglot ODPS parser 不接受，因此需要一个只发生在 Analysis 阶段的
    Parser Compatibility Normalization 层。

硬性约束：

1. 只在 syntax context 替换；string literal、comment、quoted identifier 原样保留。
2. 归一化不改写 raw SQL：StatementRecord.sql 必须仍是 Snapshot 原文。
3. 归一化不吞真错误：真正的 parse error / unsupported 语句照常上报。
4. 归一化后仍然走 AST extraction，不新增 extraction method。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from helpers import source_tree_hash, write_snapshot

from data_platform_analysis.analysis.normalization import normalize_for_parser
from data_platform_analysis.analysis.sql_analysis import parse_statement


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_raw(raw: str) -> tuple[str, bool]:
    """按真实分析顺序归一化 + 解析，返回 (parse_status, normalization_applied)。"""

    normalized = normalize_for_parser(raw)
    status, _, _ = parse_statement(normalized.sql)

    return status, normalized.applied


# ============================================================
# 1. 全角右括号
# ============================================================


def test_full_width_right_paren_is_normalized() -> None:
    """syntax context 的 ） 被替换，解析成功，仍走 AST extraction。"""

    result = normalize_for_parser("SELECT IF(a = 1, 1, 0）")

    assert result.applied is True
    assert result.sql == "SELECT IF(a = 1, 1, 0)"
    assert [change.to_dict() for change in result.changes] == [
        {"from": "）", "to": ")", "count": 1}
    ]
    assert _parse_raw("SELECT IF(a = 1, 1, 0）") == ("success", True)


# ============================================================
# 2. 全角左括号
# ============================================================


def test_full_width_left_paren_is_normalized() -> None:
    """syntax context 的 （ 被替换，解析成功，仍走 AST extraction。"""

    result = normalize_for_parser("SELECT IF（a = 1, 1, 0)")

    assert result.applied is True
    assert result.sql == "SELECT IF(a = 1, 1, 0)"
    assert [change.to_dict() for change in result.changes] == [
        {"from": "（", "to": "(", "count": 1}
    ]
    assert _parse_raw("SELECT IF（a = 1, 1, 0)") == ("success", True)


# ============================================================
# 3. String literal 中的全角括号
# ============================================================


@pytest.mark.parametrize(
    "raw",
    [
        "SELECT '测试）字符串'",
        'SELECT "测试（字符串"',
        "SELECT 'a\\')b'",
        "SELECT `col）x` FROM p.t",
    ],
)
def test_string_and_identifier_literals_are_protected(raw: str) -> None:
    """string literal 与 quoted identifier 里的全角括号完全不变。"""

    result = normalize_for_parser(raw)

    assert result.applied is False
    assert result.sql == raw
    assert _parse_raw(raw)[1] is False


# ============================================================
# 4. Comment 中的全角括号
# ============================================================


@pytest.mark.parametrize(
    "raw",
    [
        "SELECT 1 -- 测试）",
        "SELECT 1 -- 测试（",
        "SELECT 1 /* 测试（） */ + 2",
        "SELECT 'a' -- 注释里的 '） 不影响\n, 'b'",
    ],
)
def test_comment_is_protected(raw: str) -> None:
    """line / block comment 里的全角括号完全不变。"""

    result = normalize_for_parser(raw)

    assert result.applied is False
    assert result.sql == raw


def test_comment_content_survives_analysis() -> None:
    """注释内容在 statements.sql 里逐字保留。"""

    raw = "SELECT 1 -- 测试）"

    result = normalize_for_parser(raw)

    assert result.sql.endswith("-- 测试）")


# ============================================================
# 5. 普通 ASCII SQL
# ============================================================


def test_ascii_sql_is_untouched() -> None:
    """ASCII SQL 不触发归一化，内容不变，AST 正常成功。"""

    raw = "SELECT IF(a = 1, 1, 0)"
    result = normalize_for_parser(raw)

    assert result.applied is False
    assert result.changes == ()
    assert result.sql == raw
    assert _parse_raw(raw) == ("success", False)


def test_normalization_does_not_swallow_real_errors() -> None:
    """归一化不掩盖真正的 parse error / unsupported 语句。"""

    error_status, error_applied = _parse_raw("SELECT FROM WHERE（")
    assert error_status == "error"
    assert error_applied is True

    unsupported_status, unsupported_applied = _parse_raw("MSCK REPAIR TABLE p.t1")
    assert unsupported_status == "unsupported"
    assert unsupported_applied is False


def test_unterminated_string_protects_rest_of_input() -> None:
    """未闭合字符串整体按字面量保护，不产生半截替换。"""

    raw = "SELECT 'unterminated）"
    result = normalize_for_parser(raw)

    assert result.applied is False
    assert result.sql == raw


# ============================================================
# 黑盒：statements.json 的 normalization 字段
# ============================================================


NORMALIZATION_CONTENT = (
    "SELECT IF(a = 1, 1, 0）;\n"
    "SELECT IF（a = 1, 1, 0);\n"
    "SELECT '测试）字符串';\n"
    "SELECT 1 -- 测试）\n"
    ";\n"
    "SELECT IF(a = 1, 1, 0)\n"
)


def test_statements_record_normalization(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """statements.json 记录 normalization_applied / normalizations，sql 仍是 raw。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "501",
                "file_name": "fullwidth",
                "node_id": "8501",
                "content": NORMALIZATION_CONTENT,
            }
        ],
    )

    before = source_tree_hash(Path("source"))

    assert run_cli("analyze") == 0

    assert source_tree_hash(Path("source")) == before

    statements = _read(Path("analysis/sql/statements.json"))
    assert statements["count"] == 5

    by_id = {item["statement_id"]: item for item in statements["statements"]}

    # 1 / 2：syntax context 的全角括号被归一化，仍走 AST。
    for statement_id in (1, 2):
        item = by_id[statement_id]
        assert item["parse_status"] == "success"
        assert item["extraction_method"] == "ast"
        assert item["normalization_applied"] is True

    # 3 / 4：string literal 与 comment 受保护，不记录归一化。
    for statement_id in (3, 4):
        item = by_id[statement_id]
        assert item["parse_status"] == "success"
        assert item["extraction_method"] == "ast"
        assert item["normalization_applied"] is False
        assert item["normalizations"] == []

    # 5：ASCII SQL 完全不受影响。
    ascii_statement = by_id[5]
    assert ascii_statement["parse_status"] == "success"
    assert ascii_statement["extraction_method"] == "ast"
    assert ascii_statement["normalization_applied"] is False
    assert ascii_statement["sql"] == "SELECT IF(a = 1, 1, 0)"

    # raw SQL 逐字保留。
    assert by_id[1]["sql"] == "SELECT IF(a = 1, 1, 0）"
    assert by_id[2]["sql"] == "SELECT IF（a = 1, 1, 0)"
    assert by_id[3]["sql"] == "SELECT '测试）字符串'"
    assert by_id[4]["sql"] == "SELECT 1 -- 测试）"
    assert by_id[1]["normalizations"] == [{"from": "）", "to": ")", "count": 1}]
    assert by_id[2]["normalizations"] == [{"from": "（", "to": "(", "count": 1}]

    # 归一化不产生新的错误。
    assert _read(Path("analysis/sql/parse-errors.json"))["count"] == 0
    assert _read(Path("analysis/errors.json"))["count"] == 0

    summary = Path("analysis/Summary.md").read_text(encoding="utf-8")
    assert "Parser Compatibility Normalization 生效语句：2" in summary

"""Cross-stage Technical Error Ledger 路径与契约测试。

验证点：

1. 账本写出路径为 analysis/evidence/errors.json，旧位置 analysis/errors.json 不再产生。
2. 重跑时旧位置残留文件被清理，不会新旧并存。
3. 账本 stage 覆盖 inventory / sql / lineage / profiling，schema 仍为 {"count", "errors"}。
4. 根 summary / inventory summary 的错误计数与账本 count 一致，且指向新路径。
5. analysis/evidence/sql/parse-errors.json 保持独立，不与账本合并。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helpers import assert_sandbox, write_snapshot

from data_platform_analysis.analysis.errors import (
    ERROR_LEDGER_RELATIVE_PATH,
    ERROR_LEDGER_SCOPE,
    ErrorLedger,
)
from data_platform_analysis.analysis.pipeline import LEGACY_PRODUCTION_FILES, PRODUCTION_FILES


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _broken_snapshot() -> None:
    """构造一次会产生可恢复错误的 Snapshot（table raw 缺失 → stage=inventory）。

    只能在 `cli_env`（`chdir(tmp_path)`）生效时调用。
    """

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )
    assert_sandbox(Path("source/maxcompute/workspaces/9001/tables/dwd_order.json")).unlink()


# ============================================================
# 1. 路径
# ============================================================


def test_ledger_path_constant() -> None:
    """账本路径常量是唯一来源，且属于 PRODUCTION_FILES 而非 legacy。"""

    assert ERROR_LEDGER_RELATIVE_PATH == "evidence/errors.json"
    assert ERROR_LEDGER_RELATIVE_PATH in PRODUCTION_FILES
    assert "errors.json" in LEGACY_PRODUCTION_FILES
    assert "evidence/errors.json" not in LEGACY_PRODUCTION_FILES


def test_analyze_writes_ledger_under_evidence(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """analyze 后新路径存在、旧路径不存在。"""

    _broken_snapshot()

    assert run_cli("analyze") == 0

    assert Path("analysis/evidence/errors.json").exists()
    assert not Path("evidence/errors.json").exists()

    errors = _read(Path("analysis/evidence/errors.json"))
    assert errors["count"] == 1
    assert errors["errors"][0]["stage"] == "inventory"


def test_legacy_root_ledger_is_removed(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """旧位置残留文件在重跑时被删除，不会与新位置并存。"""

    _broken_snapshot()
    Path("analysis").mkdir(exist_ok=True)
    Path("analysis/errors.json").write_text(
        json.dumps({"count": 9, "errors": []}), encoding="utf-8"
    )

    assert run_cli("analyze") == 0

    assert not Path("analysis/errors.json").exists()
    assert _read(Path("analysis/evidence/errors.json"))["count"] == 1


# ============================================================
# 2. stage 覆盖与 schema
# ============================================================


def test_ledger_payload_covers_all_stages() -> None:
    """inventory / sql / lineage / profiling 四类 stage 均可写入且不被过滤。"""

    stages = ("inventory", "sql", "lineage", "profiling")
    ledger = ErrorLedger()
    for stage in stages:
        ledger.add(stage=stage, error_type="T", message="m")

    payload = {"count": len(ledger), "errors": ledger.records()}

    assert set(payload) == {"count", "errors"}
    assert payload["count"] == len(stages) == 4
    assert {item["stage"] for item in payload["errors"]} == set(stages)
    # 账本整体归属 evidence stage（四阶段契约），与单条记录的 stage 字段不同。
    assert ERROR_LEDGER_SCOPE == "evidence"


def test_ledger_payload_is_deterministic() -> None:
    """同一组错误的写出顺序稳定，与 stage 分布无关。"""

    ledger = ErrorLedger()
    ledger.add(stage="profiling", error_type="B", message="b")
    ledger.add(stage="inventory", error_type="A", message="a")

    first = ledger.records()
    second = ErrorLedger()

    assert len(second) == 0
    assert [item["stage"] for item in first] == ["inventory", "profiling"]


# ============================================================
# 3. summary 口径
# ============================================================


def test_summaries_agree_with_ledger(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """根 summary 与 inventory summary 的错误计数 = 账本 count，且指向新路径。"""

    _broken_snapshot()

    assert run_cli("analyze") == 0

    count = _read(Path("analysis/evidence/errors.json"))["count"]

    root = Path("analysis/summary.md").read_text(encoding="utf-8")
    assert "完整错误见 `analysis/evidence/errors.json`" in root
    assert "analysis/errors.json" not in root

    inventory = Path("analysis/inventory/summary.md").read_text(encoding="utf-8")
    assert "明细见 `analysis/evidence/errors.json`" in inventory
    assert f"Inventory 阶段可恢复错误合计：{count} 条" in inventory
    assert "analysis/errors.json" not in inventory


def test_parse_errors_artifact_stays_separate(
    cli_env: Any,
    run_cli: Any,
) -> None:
    """parse-errors.json 是独立 SQL artifact，不与账本合并。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "301",
                "file_name": "bad",
                "node_id": "8001",
                "content": "MSCK REPAIR TABLE ${ws_a}.t1;\n",
            }
        ],
    )

    assert run_cli("analyze") == 0

    parse_errors = _read(Path("analysis/evidence/sql/parse-errors.json"))
    ledger = _read(Path("analysis/evidence/errors.json"))

    assert parse_errors["count"] >= 1
    assert "stage" not in parse_errors["errors"][0]
    assert {item["error_type"] for item in parse_errors["errors"]} == {"SQL_UNSUPPORTED_STATEMENT"}

    assert ledger["count"] >= 1
    assert {item["stage"] for item in ledger["errors"]} == {"sql"}

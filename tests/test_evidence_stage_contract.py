"""Evidence stage 输出契约的回归测试。

契约：`analyze --stage evidence` 必须自洽——独立执行时产出它所承诺的全部
Evidence 产物，且与全量 `analyze` 的 Evidence 输出逐文件一致；不制造空的
Lineage / Profiling 结果，也不越界产出 Understanding / Review 产物。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from helpers import write_snapshot


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _tree(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}

    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


RULES_TEXT = """\
version: "1.0"

workspace_layers:
  - workspace_id: 9001
    workspace_name: ws_a
    layer: CDM

  - workspace_id: 9002
    workspace_name: ws_b
    layer: ADS

sub_layers:
  CDM:
    DWD:
      prefixes:
        - "dwd_"
      suffixes: []
    DIM:
      prefixes:
        - "dim_"
      suffixes: []

matching:
  case_sensitive: false
"""

# Evidence stage 必须落盘的正式产物（docs/STAGE_INDEX.md 的 12 份阶段报告里
# 属于 Evidence 的三份 summary.md 也在其中）。
EVIDENCE_REPORT_FILES = (
    "errors.json",
    "layer/assessments.json",
    "layer/summary.md",
    "lineage/table-lineage.json",
    "lineage/core-table-candidates.json",
    "lineage/summary.md",
    "profiling/tables.json",
    "profiling/columns.json",
    "profiling/summary.md",
    "sql/statements.json",
    "sql/table-references.json",
    "sql/parse-errors.json",
)

INVENTORY_FILES = (
    "workspaces.json",
    "files.json",
    "tables.json",
    "columns.json",
    "excluded-tasks.json",
    "review-tasks.json",
    "summary.md",
)

LEGACY_ROOT_DIRS = ("layer", "lineage", "profiling", "sql", "business", "model")


def _prepare(tmp_path: Path, monkeypatch: Any) -> None:
    """写出 layer rules 与一份带血缘、带表的 Snapshot。"""

    rules_path = tmp_path / "config" / "layer-rules.yaml"
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text(RULES_TEXT, encoding="utf-8")
    monkeypatch.setenv("LAYER_RULES_PATH", str(rules_path))

    write_snapshot(
        Path("source"),
        workspaces=[
            {"id": 9001, "name": "ws_a"},
            {"id": 9002, "name": "ws_b"},
        ],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "load_order",
                "node_id": "9101",
                "content": ("INSERT INTO ${ws_a}.dwd_order SELECT * FROM ${ws_a}.ods_order;"),
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "load_x",
                "node_id": "9102",
                "content": "INSERT INTO ${ws_a}.dwd_x SELECT * FROM ws_b.dim_y;",
            },
        ],
        tables=[
            {
                "workspace_id": 9001,
                "table": "dwd_order",
                "columns": [{"name": "id", "type": "STRING"}],
                "partitions": ["ds"],
            },
            {
                "workspace_id": 9001,
                "table": "ods_order",
                "columns": [{"name": "id", "type": "STRING"}],
            },
            {
                "workspace_id": 9002,
                "table": "dim_y",
                "columns": [{"name": "id", "type": "STRING"}],
            },
        ],
    )


# ============================================================
# Test 1：Evidence 独立运行产出完整 Evidence 输出
# ============================================================


def test_evidence_stage_writes_full_evidence_artifacts(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """analyze --stage evidence 写出全部正式 Evidence 产物（含两份 summary.md）。"""

    _prepare(tmp_path, monkeypatch)
    monkeypatch.setenv("ANALYSIS_DIR", str(tmp_path / "analysis_evidence"))

    assert run_cli("analyze", "--stage", "evidence") == 0

    analysis_dir = tmp_path / "analysis_evidence"

    for name in EVIDENCE_REPORT_FILES:
        assert (analysis_dir / "evidence" / name).exists(), name

    for name in INVENTORY_FILES:
        assert (analysis_dir / "inventory" / name).exists(), name

    assert (analysis_dir / "summary.md").exists()

    # 旧目录 / 旧文件名不复活（按字面名比对，避免 macOS 大小写不敏感误判）。
    root_names = {path.name for path in analysis_dir.iterdir()}
    for legacy in LEGACY_ROOT_DIRS:
        assert legacy not in root_names
    assert "Summary.md" not in root_names
    assert "errors.json" not in root_names

    # 两份 Evidence 报告必须有真实内容，而不是空模板。
    lineage_summary = (analysis_dir / "evidence" / "lineage" / "summary.md").read_text(
        encoding="utf-8"
    )
    assert "# M2.4 Table Lineage" in lineage_summary

    profiling_summary = (analysis_dir / "evidence" / "profiling" / "summary.md").read_text(
        encoding="utf-8"
    )
    assert "# M2.5 Data Profiling" in profiling_summary


# ============================================================
# Test 2：Evidence stage 与 full analyze 的 Evidence 输出一致
# ============================================================


def test_evidence_stage_matches_full_analyze(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """同一批 Snapshot 下，stage evidence 与 full analyze 的 Evidence 产物逐字节一致。"""

    _prepare(tmp_path, monkeypatch)

    # 两次运行共用同一个 analysis/：报告里的「输入」行会渲染 analysis_dir
    # 绝对路径，目录不同会造成与契约无关的字节差异。
    analysis_dir = tmp_path / "analysis"
    monkeypatch.setenv("ANALYSIS_DIR", str(analysis_dir))

    assert run_cli("analyze", "--stage", "evidence") == 0

    stage_evidence = _tree(analysis_dir / "evidence")
    stage_inventory = _tree(analysis_dir / "inventory")
    stage_summary = (analysis_dir / "summary.md").read_bytes()

    assert stage_evidence, "Evidence stage 必须真的产出 evidence/"
    assert "lineage/summary.md" in stage_evidence
    assert "profiling/summary.md" in stage_evidence

    shutil.rmtree(analysis_dir)

    assert run_cli("analyze") == 0

    full_evidence = _tree(analysis_dir / "evidence")

    # 文件集合一致。
    assert sorted(stage_evidence) == sorted(full_evidence)
    # 每个文件字节一致（JSON 内容与 Markdown 内容一并覆盖）。
    assert stage_evidence == full_evidence

    # Evidence stage 同时重建 Inventory，两者的 Inventory 产物也必须一致。
    assert sorted(stage_inventory) == sorted(_tree(analysis_dir / "inventory"))
    assert stage_inventory == _tree(analysis_dir / "inventory")

    # 根 summary.md 同样一致：render_analysis_summary 只吃 Evidence 段输入，
    # full analyze 多出的 Understanding / Review 不进入该上下文。
    assert stage_summary == (analysis_dir / "summary.md").read_bytes()


# ============================================================
# Test 3：Evidence stage 后根 summary 的 lineage 段非空
# ============================================================


def test_evidence_stage_summary_has_lineage(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """Evidence stage 的 analysis/summary.md 必须用真实血缘数据渲染。"""

    _prepare(tmp_path, monkeypatch)
    monkeypatch.setenv("ANALYSIS_DIR", str(tmp_path / "analysis_evidence"))

    assert run_cli("analyze", "--stage", "evidence") == 0

    analysis_dir = tmp_path / "analysis_evidence"

    edge_count = _read(analysis_dir / "evidence" / "lineage" / "table-lineage.json")["count"]
    assert edge_count > 0, "测试快照必须产生血缘边，否则本测试无意义"

    summary = (analysis_dir / "summary.md").read_text(encoding="utf-8")
    assert "## 7. Table Lineage" in summary
    assert f"| 血缘边（去重） | {edge_count} |" in summary

    lineage_summary = (analysis_dir / "evidence" / "lineage" / "summary.md").read_text(
        encoding="utf-8"
    )
    assert f"- 血缘边（去重后）：{edge_count}" in lineage_summary
    assert "- 跨 Workspace 血缘：" in lineage_summary


# ============================================================
# Test 4：Evidence stage 不越界产出其他 stage 产物
# ============================================================


def test_evidence_stage_does_not_produce_other_stage_outputs(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """Evidence stage 只产出 inventory + evidence + 根 summary.md。"""

    _prepare(tmp_path, monkeypatch)
    monkeypatch.setenv("ANALYSIS_DIR", str(tmp_path / "analysis_evidence"))

    assert run_cli("analyze", "--stage", "evidence") == 0

    analysis_dir = tmp_path / "analysis_evidence"
    root_names = {path.name for path in analysis_dir.iterdir()}

    assert root_names == {"inventory", "evidence", "summary.md"}
    assert not (analysis_dir / "understanding").exists()
    assert not (analysis_dir / "review").exists()

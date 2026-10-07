"""M2.2 Layer Assessment 的测试。

覆盖任务要求的 11 个场景：ODS / ADS / CDM 子层命中 / UNKNOWN / CONFLICT /
同层多规则 evidence / 大小写 / 排序确定性 / 未配置 workspace / 错误路径 /
不修改 Inventory。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from helpers import write_snapshot

from data_platform_analysis.analysis.layer.layer_assessment import (
    LayerAssessmentError,
    _display_path,
    assess_tables,
    load_layer_rules,
    run_layer_assessment,
)
from data_platform_analysis.analysis.models import (
    LAYER_STATUS_CONFLICT,
    LAYER_STATUS_MATCH,
    LAYER_STATUS_UNKNOWN,
    LayerAssessment,
)
from data_platform_analysis.config import PROJECT_ROOT

# ============================================================
# 测试数据
# ============================================================

RULES_TEXT = """\
version: "1.0"

workspace_layers:
  - workspace_id: 466338
    workspace_name: dme_ods
    layer: ODS

  - workspace_id: 466337
    workspace_name: dme_cdm
    layer: CDM

  - workspace_id: 466339
    workspace_name: dme_ads
    layer: ADS

sub_layers:
  CDM:
    DIM:
      prefixes: [dim_]
      suffixes: []
    DWD:
      prefixes: [dwd_]
      suffixes: [_dwd]
    DWS:
      prefixes: [dws_]
      suffixes: [_dws]

matching:
  case_sensitive: false
"""

CASE_SENSITIVE_RULES_TEXT = RULES_TEXT.replace(
    "case_sensitive: false",
    "case_sensitive: true",
)

DUPLICATE_RULES_TEXT = """\
version: "1.0"

workspace_layers:
  - workspace_id: 466338
    workspace_name: dme_ods
    layer: ODS

  - workspace_id: 466338
    workspace_name: dme_ods_copy
    layer: ADS

matching:
  case_sensitive: false
"""


def _write_rules(path: Path, text: str = RULES_TEXT) -> Path:
    """写出 layer-rules 配置。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    return path


def _table(
    workspace_id: int,
    workspace_name: str,
    table: str,
    project: str | None = None,
) -> dict[str, Any]:
    """构造 M2.1 tables.json 中的单条记录。"""

    project = project or workspace_name

    return {
        "workspace_id": workspace_id,
        "workspace_name": workspace_name,
        "project": project,
        "table": table,
        "table_key": f"{project}.{table}",
    }


def _assess(
    tmp_path: Path,
    tables: list[dict[str, Any]],
    rules_text: str = RULES_TEXT,
) -> list[LayerAssessment]:
    """加载规则并识别，返回排序后的结果。"""

    rules = load_layer_rules(_write_rules(tmp_path / "layer-rules.yaml", rules_text))

    return assess_tables(rules, tables)


def _by_table(assessments: list[LayerAssessment]) -> dict[str, LayerAssessment]:
    return {item.table_name: item for item in assessments}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ============================================================
# 1. ODS / ADS：candidate 取 workspace_layer
# ============================================================


def test_ods_workspace_matches(tmp_path: Path) -> None:
    """ODS Workspace 直接给出 ODS MATCH，evidence 只有 workspace。"""

    item = _assess(tmp_path, [_table(466338, "dme_ods", "ods_order")])[0]

    assert item.workspace_layer == "ODS"
    assert item.candidate_layer == "ODS"
    assert item.status == LAYER_STATUS_MATCH
    assert item.evidence == [
        {"type": "workspace", "layer": "ODS", "configured": True},
    ]


def test_ads_workspace_matches(tmp_path: Path) -> None:
    """ADS Workspace 直接给出 ADS MATCH，不伪造 table_name 规则。"""

    item = _assess(tmp_path, [_table(466339, "dme_ads", "ads_report")])[0]

    assert item.workspace_layer == "ADS"
    assert item.candidate_layer == "ADS"
    assert item.status == LAYER_STATUS_MATCH
    assert item.evidence == [
        {"type": "workspace", "layer": "ADS", "configured": True},
    ]


def test_ods_workspace_records_cross_layer_prefix(tmp_path: Path) -> None:
    """ODS Workspace 里的 dwd_ 表：candidate 仍是 ODS，命中记入 evidence。"""

    item = _assess(tmp_path, [_table(466338, "dme_ods", "dwd_master_data")])[0]

    assert item.workspace_layer == "ODS"
    assert item.candidate_layer == "ODS"
    assert item.status == LAYER_STATUS_MATCH
    assert item.evidence == [
        {"type": "workspace", "layer": "ODS", "configured": True},
        {"type": "prefix", "layer": "DWD", "pattern": "dwd_"},
    ]
    assert item.cross_layer_hits == [
        {"type": "prefix", "layer": "DWD", "pattern": "dwd_"},
    ]


def test_ads_workspace_dim_prefix_is_cross_layer_hint(tmp_path: Path) -> None:
    """ADS Workspace 里的 dim_ 表：candidate 是 ADS，dim_ 只作跨层提示。"""

    item = _assess(tmp_path, [_table(466339, "dme_ads", "dim_day")])[0]

    assert item.candidate_layer == "ADS"
    assert item.status == LAYER_STATUS_MATCH
    assert [hit["layer"] for hit in item.cross_layer_hits] == ["DIM"]


def test_cdm_match_has_no_cross_layer_hint(tmp_path: Path) -> None:
    """CDM 子层命中属于本层，不产生跨层提示。"""

    item = _assess(tmp_path, [_table(466337, "dme_cdm", "dwd_sales")])[0]

    assert item.candidate_layer == "DWD"
    assert item.cross_layer_hits == []


# ============================================================
# 2. CDM 子层命中
# ============================================================


@pytest.mark.parametrize(
    ("table_name", "expected_layer", "expected_pattern"),
    [
        ("dwd_sales", "DWD", "dwd_"),
        ("dws_sales", "DWS", "dws_"),
        ("dim_product", "DIM", "dim_"),
    ],
)
def test_cdm_prefix_matches_sub_layer(
    tmp_path: Path,
    table_name: str,
    expected_layer: str,
    expected_pattern: str,
) -> None:
    """CDM + 子层 prefix → 对应子层 MATCH。"""

    item = _assess(tmp_path, [_table(466337, "dme_cdm", table_name)])[0]

    assert item.workspace_layer == "CDM"
    assert item.status == LAYER_STATUS_MATCH
    assert item.candidate_layer == expected_layer
    assert item.evidence[0] == {"type": "workspace", "layer": "CDM", "configured": True}
    assert {
        "type": "prefix",
        "layer": expected_layer,
        "pattern": expected_pattern,
    } in item.evidence


def test_cdm_without_rule_hit_is_unknown(tmp_path: Path) -> None:
    """CDM + 无规则命中 → UNKNOWN，candidate_layer 为空。"""

    item = _assess(tmp_path, [_table(466337, "dme_cdm", "sales_detail")])[0]

    assert item.workspace_layer == "CDM"
    assert item.status == LAYER_STATUS_UNKNOWN
    assert item.candidate_layer is None
    assert item.evidence == [{"type": "workspace", "layer": "CDM", "configured": True}]


def test_cdm_multiple_sub_layers_is_conflict(tmp_path: Path) -> None:
    """同时命中两个不同子层 → CONFLICT，不擅自选择，evidence 全保留。"""

    item = _assess(tmp_path, [_table(466337, "dme_cdm", "dwd_sales_dws")])[0]

    assert item.status == LAYER_STATUS_CONFLICT
    assert item.candidate_layer is None

    hits = {(hit["type"], hit["layer"], hit.get("pattern")) for hit in item.evidence}

    assert ("prefix", "DWD", "dwd_") in hits
    assert ("suffix", "DWS", "_dws") in hits


def test_cdm_same_layer_keeps_all_evidence(tmp_path: Path) -> None:
    """同一子层多条规则同时命中 → 仍是 MATCH，evidence 保留全部命中规则。"""

    item = _assess(tmp_path, [_table(466337, "dme_cdm", "dwd_sales_dwd")])[0]

    assert item.status == LAYER_STATUS_MATCH
    assert item.candidate_layer == "DWD"

    hits = [
        (hit["type"], hit["layer"], hit["pattern"])
        for hit in item.evidence
        if hit["type"] != "workspace"
    ]

    assert hits == [
        ("prefix", "DWD", "dwd_"),
        ("suffix", "DWD", "_dwd"),
    ]


# ============================================================
# 3. 大小写
# ============================================================


def test_matching_is_case_insensitive(tmp_path: Path) -> None:
    """case_sensitive=false 时忽略大小写，evidence 保留配置原文 pattern。"""

    item = _assess(tmp_path, [_table(466337, "dme_cdm", "DWD_Sales")])[0]

    assert item.status == LAYER_STATUS_MATCH
    assert item.candidate_layer == "DWD"
    assert {
        "type": "prefix",
        "layer": "DWD",
        "pattern": "dwd_",
    } in item.evidence


def test_case_sensitive_rejects_other_case(tmp_path: Path) -> None:
    """case_sensitive=true 时大小写不一致不命中 → UNKNOWN；同名精确命中。"""

    mismatched = _assess(
        tmp_path,
        [_table(466337, "dme_cdm", "DWD_Sales")],
        rules_text=CASE_SENSITIVE_RULES_TEXT,
    )[0]

    assert mismatched.status == LAYER_STATUS_UNKNOWN
    assert mismatched.candidate_layer is None

    exact = _assess(
        tmp_path,
        [_table(466337, "dme_cdm", "dwd_sales")],
        rules_text=CASE_SENSITIVE_RULES_TEXT,
    )[0]

    assert exact.status == LAYER_STATUS_MATCH
    assert exact.candidate_layer == "DWD"


# ============================================================
# 4. 未配置 workspace
# ============================================================


def test_unconfigured_workspace_is_explicit_unknown(tmp_path: Path) -> None:
    """workspace_id 未配置 → 显式 UNKNOWN，不按 workspace_name 静默推断。"""

    item = _assess(tmp_path, [_table(999999, "dme_ods", "dwd_sales")])[0]

    assert item.workspace_layer is None
    assert item.status == LAYER_STATUS_UNKNOWN
    assert item.candidate_layer is None
    assert item.evidence == [
        {"type": "workspace", "layer": None, "configured": False},
    ]


# ============================================================
# 5. 排序与确定性
# ============================================================


def test_assessments_sorted_by_workspace_project_table(tmp_path: Path) -> None:
    """输入乱序也按 (workspace_id, project, table_name) 稳定排序。"""

    tables = [
        _table(466338, "dme_ods", "ods_x"),
        _table(466337, "dme_cdm", "dwd_b"),
        _table(466337, "dme_cdm", "dwd_a"),
    ]

    ordered = _assess(tmp_path, tables)
    reversed_ordered = _assess(tmp_path, list(reversed(tables)))

    keys = [(item.workspace_id, item.project, item.table_name) for item in ordered]

    assert keys == sorted(keys)
    assert keys == [
        (466337, "dme_cdm", "dwd_a"),
        (466337, "dme_cdm", "dwd_b"),
        (466338, "dme_ods", "ods_x"),
    ]
    assert [item.table_name for item in reversed_ordered] == [
        item.table_name for item in ordered
    ]


# ============================================================
# 6. 错误路径
# ============================================================


def test_missing_rules_file_raises(tmp_path: Path) -> None:
    """规则文件缺失 → 明确报错，不回退默认规则。"""

    with pytest.raises(LayerAssessmentError, match="配置文件不存在"):
        load_layer_rules(tmp_path / "missing.yaml")


def test_duplicate_workspace_id_raises(tmp_path: Path) -> None:
    """workspace_id 重复 → 明确报错。"""

    with pytest.raises(LayerAssessmentError, match="重复的 workspace_id"):
        load_layer_rules(_write_rules(tmp_path / "layer-rules.yaml", DUPLICATE_RULES_TEXT))


def test_missing_inventory_record_field_raises(tmp_path: Path) -> None:
    """Inventory 记录缺少 table → 明确报错，不猜字段。"""

    with pytest.raises(LayerAssessmentError, match="缺少合法的 table"):
        _assess(
            tmp_path,
            [
                {
                    "workspace_id": 466337,
                    "workspace_name": "dme_cdm",
                    "project": "dme_cdm",
                }
            ],
        )


def test_missing_inventory_file_raises(tmp_path: Path) -> None:
    """Inventory 输入缺失 → 明确报错。"""

    rules_path = _write_rules(tmp_path / "layer-rules.yaml")

    with pytest.raises(LayerAssessmentError, match="Inventory 输入不存在"):
        run_layer_assessment(
            inventory_path=tmp_path / "analysis" / "inventory" / "tables.json",
            rules_path=rules_path,
            output_dir=tmp_path / "analysis" / "layer",
        )


# ============================================================
# 7. CLI 黑盒：analyze-layer
# ============================================================


def _write_inventory(path: Path, tables: list[dict[str, Any]]) -> Path:
    """写出 M2.1 的 tables.json。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"count": len(tables), "tables": tables},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def test_analyze_layer_command_writes_outputs(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze-layer 产出 assessments.json / summary.md，且不修改 Inventory。"""

    rules_path = _write_rules(tmp_path / "config" / "layer-rules.yaml")
    monkeypatch.setenv("LAYER_RULES_PATH", str(rules_path))

    _write_inventory(
        Path("analysis/inventory/tables.json"),
        [
            _table(466338, "dme_ods", "ods_order"),
            _table(466338, "dme_ods", "dwd_master_data"),
            _table(466337, "dme_cdm", "dwd_sales"),
            _table(466337, "dme_cdm", "sales_detail"),
            _table(466337, "dme_cdm", "dwd_sales_dws"),
            _table(999999, "dme_unconfigured", "whatever"),
        ],
    )

    inventory_bytes = Path("analysis/inventory/tables.json").read_bytes()

    assert run_cli("analyze-layer") == 0

    data = _read(Path("analysis/layer/assessments.json"))
    assert data["count"] == 6

    by_table = {item["table_name"]: item for item in data["assessments"]}

    ods_order = by_table["ods_order"]
    assert set(ods_order) == {
        "workspace_id",
        "workspace_name",
        "workspace_layer",
        "project",
        "table_name",
        "table_identifier",
        "candidate_layer",
        "status",
        "evidence",
    }
    assert ods_order["workspace_layer"] == "ODS"
    assert ods_order["candidate_layer"] == "ODS"
    assert ods_order["status"] == LAYER_STATUS_MATCH

    # ODS 里的 dwd_ 表：candidate 仍是 ODS，前缀命中只进 evidence。
    cross = by_table["dwd_master_data"]
    assert cross["candidate_layer"] == "ODS"
    assert cross["status"] == LAYER_STATUS_MATCH
    assert {"type": "prefix", "layer": "DWD", "pattern": "dwd_"} in cross["evidence"]

    dwd_sales = by_table["dwd_sales"]
    assert dwd_sales["table_identifier"] == "dme_cdm.dwd_sales"
    assert dwd_sales["status"] == LAYER_STATUS_MATCH
    assert dwd_sales["candidate_layer"] == "DWD"

    assert by_table["sales_detail"]["status"] == LAYER_STATUS_UNKNOWN
    assert by_table["sales_detail"]["candidate_layer"] is None

    conflict = by_table["dwd_sales_dws"]
    assert conflict["status"] == LAYER_STATUS_CONFLICT
    assert conflict["candidate_layer"] is None

    unconfigured = by_table["whatever"]
    assert unconfigured["workspace_layer"] is None
    assert unconfigured["status"] == LAYER_STATUS_UNKNOWN
    assert unconfigured["evidence"][0]["configured"] is False

    summary = Path("analysis/layer/summary.md").read_text(encoding="utf-8")
    assert "# M2.2 Layer Assessment" in summary
    assert "999999" in summary
    assert "未配置 Workspace" in summary
    assert "## 跨层命名提示" in summary
    assert "dme_ods.dwd_master_data" in summary
    assert "## UNKNOWN 明细" in summary
    assert "dme_cdm.sales_detail" in summary
    assert "## CONFLICT 明细" in summary
    assert "dme_cdm.dwd_sales_dws" in summary

    # 排序 deterministic。
    keys = [
        (item["workspace_id"], item["project"], item["table_name"])
        for item in data["assessments"]
    ]
    assert keys == sorted(keys)

    first_run = Path("analysis/layer/assessments.json").read_bytes()

    # 不修改 Inventory。
    assert Path("analysis/inventory/tables.json").read_bytes() == inventory_bytes

    assert run_cli("analyze-layer") == 0
    assert Path("analysis/layer/assessments.json").read_bytes() == first_run


def test_analyze_layer_command_fails_without_inventory(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """Inventory 输入缺失 → 退出码 1，不写产物。"""

    rules_path = _write_rules(tmp_path / "config" / "layer-rules.yaml")
    monkeypatch.setenv("LAYER_RULES_PATH", str(rules_path))

    assert run_cli("analyze-layer") == 1
    assert not Path("analysis/layer/assessments.json").exists()


# ============================================================
# 8. Analysis Pipeline 集成
# ============================================================


def test_analyze_produces_layer_outputs(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Any,
    monkeypatch: Any,
) -> None:
    """analyze 一并产出 analysis/layer（M2.2 步骤已接入流水线）。"""

    rules_path = _write_rules(tmp_path / "config" / "layer-rules.yaml")
    monkeypatch.setenv("LAYER_RULES_PATH", str(rules_path))

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 466337, "name": "dme_cdm"}],
        tables=[
            {
                "workspace_id": 466337,
                "table": "dwd_sales",
                "columns": [{"name": "id", "type": "BIGINT"}],
            }
        ],
    )

    assert run_cli("analyze") == 0

    data = _read(Path("analysis/layer/assessments.json"))
    assert data["count"] == 1
    assert data["assessments"][0]["candidate_layer"] == "DWD"
    assert data["assessments"][0]["status"] == LAYER_STATUS_MATCH

    assert Path("analysis/layer/summary.md").exists()

    # 总 Summary 包含 M2.2 一节。
    summary = Path("analysis/Summary.md").read_text(encoding="utf-8")
    assert "Layer Assessment（M2.2）" in summary
    assert "| MATCH | 1 |" in summary
    assert "| UNKNOWN | 0 |" in summary
    assert "| 参与评估的表 | 1 |" in summary


# ============================================================
# 9. 报告与日志展示
# ============================================================


def test_display_path_relative_inside_project_root(tmp_path: Path) -> None:
    """日志与报告中的路径：项目根内显示相对路径，根外保持绝对。"""

    inside = PROJECT_ROOT / "config" / "layer-rules.yaml"
    outside = tmp_path / "assessments.json"

    assert _display_path(inside) == "config/layer-rules.yaml"
    assert _display_path(outside) == str(outside.resolve())

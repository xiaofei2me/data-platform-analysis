"""analysis/scope 独立包与本轮契约变更的测试。

覆盖：包迁移与旧路径兼容、Node ID 状态二值化、Identity 默认资格、
cleanup_candidate 全量删除、Content 检查开关、sql-candidates / excluded-tasks
互补清单契约，以及 content_check 配置非法时的 fail-fast。
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest
import yaml
from helpers import assert_sandbox, write_snapshot

from data_platform_analysis.analysis import models as models_module
from data_platform_analysis.analysis import scope as scope_pkg
from data_platform_analysis.analysis.inventory import scope as legacy_scope
from data_platform_analysis.analysis.models import (
    NODE_ID_STATE_MISSING,
    NODE_ID_STATE_VALID,
    FileInventory,
    is_analysis_eligible,
    node_id_state,
)
from data_platform_analysis.analysis.scope import (
    CONTENT_STATE_NOT_CHECKED,
    CONTENT_STATE_PRESENT,
    CONTENT_STATES,
    ContentCheckConfig,
    FileScopeStats,
    ScopeResult,
    ScopeRules,
    ScopeRulesError,
    classify_file,
    load_scope_rules,
)

_REPO_CONFIG = Path(__file__).resolve().parent.parent / "config" / "analysis-scope-rules.yaml"


def _base_rules() -> dict[str, Any]:
    data = yaml.safe_load(_REPO_CONFIG.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return deepcopy(data)


def _write_rules(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _file(
    *,
    file_id: str = "101",
    node_id: int | str | None = "7001",
    file_name: str = "etl_a",
    content_format: str = "SQL",
) -> FileInventory:
    return FileInventory(
        workspace_id=9001,
        file_id=file_id,
        file_name=file_name,
        node_id=node_id,
        use_type="NORMAL",
        file_type=10,
        file_type_name="ODPS SQL",
        task_type="SQL",
        category="DEVELOP",
        content_format=content_format,
        raw_file=None,
        content_file=None,
    )


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ============================================================
# 1. 包迁移：唯一实现 + 旧路径兼容层
# ============================================================


def test_scope_package_is_the_single_implementation() -> None:
    """旧路径只是重新导出，实现只有一份，且不再携带已删除的词表。"""

    assert legacy_scope.build_file_scope is scope_pkg.build_file_scope
    assert legacy_scope.load_scope_rules is scope_pkg.load_scope_rules
    assert legacy_scope.classify_file is scope_pkg.classify_file
    assert legacy_scope.FileScope is scope_pkg.FileScope
    assert legacy_scope.FileScopeDecision is scope_pkg.FileScopeDecision
    assert legacy_scope.FileScopeStats is scope_pkg.FileScopeStats
    assert legacy_scope.excluded_tasks_payload is scope_pkg.excluded_tasks_payload
    assert legacy_scope.sql_candidates_payload is scope_pkg.sql_candidates_payload

    cleanup_names = (
        "CLEANUP_NEVER",
        "CLEANUP_ALWAYS",
        "CLEANUP_WHEN_NODE_ID_MISSING",
        "CLEANUP_POLICIES",
        "_resolve_cleanup",
    )
    for name in cleanup_names:
        assert not hasattr(scope_pkg, name)
        assert not hasattr(legacy_scope, name)

    assert "node_id_invalid" not in scope_pkg.CONDITION_KINDS
    assert "node_id_valid" not in scope_pkg.CONDITION_KINDS
    assert not hasattr(models_module, "NODE_ID_STATE_INVALID")


def test_shipped_rules_config_loads() -> None:
    """仓库自带配置是合法的（含 content_check），且不再含已删除字段。"""

    rules = load_scope_rules(_REPO_CONFIG)

    assert rules.content_check == ContentCheckConfig(
        enabled=True, enabled_formats=frozenset({"SQL"})
    )
    assert rules.rule_by_id("NODE_ID_MISSING") is not None
    assert rules.rule_by_id("NODE_ID_INVALID") is None
    assert rules.rule_by_id("NODE_ID_VALID") is None
    assert "cleanup_candidate" not in {item.name for item in fields(ScopeResult)}
    assert "not_checked" in CONTENT_STATES


# ============================================================
# 2. Node ID 状态二值化
# ============================================================


@pytest.mark.parametrize(
    ("node_id", "expected"),
    [
        (None, NODE_ID_STATE_MISSING),
        ("", NODE_ID_STATE_MISSING),
        ("   ", NODE_ID_STATE_MISSING),
        (123, NODE_ID_STATE_VALID),
        ("7001", NODE_ID_STATE_VALID),
        (" 7001 ", NODE_ID_STATE_VALID),
        ("abc", NODE_ID_STATE_VALID),
        (0, NODE_ID_STATE_VALID),
    ],
)
def test_node_id_state_is_two_valued(node_id: Any, expected: str) -> None:
    """Node ID 状态只有 missing / valid：存在即 valid，与报告口径一致。"""

    assert node_id_state(node_id) == expected


@pytest.mark.parametrize("node_id", [None, "", "   "])
def test_missing_node_id_is_not_eligible(node_id: Any) -> None:
    assert is_analysis_eligible(_file(node_id=node_id)) is False


@pytest.mark.parametrize("node_id", [123, "7001", "abc", 0])
def test_present_node_id_is_eligible(node_id: Any) -> None:
    """is_analysis_eligible 与 node_id_state 同口径：非空即具备身份资格。"""

    file = _file(node_id=node_id)
    assert is_analysis_eligible(file) is True
    assert node_id_state(file.node_id) == NODE_ID_STATE_VALID


# ============================================================
# 3. Identity 默认资格
# ============================================================


def _identity_only_rules() -> ScopeRules:
    """只保留 NODE_ID_MISSING 规则的规则集（用于观察默认值）。"""

    full = load_scope_rules(_REPO_CONFIG)

    return ScopeRules(
        version=full.version,
        source_path=full.source_path,
        rules=tuple(rule for rule in full.rules if rule.id == "NODE_ID_MISSING"),
        content_expectations=full.content_expectations,
        content_check=full.content_check,
        sql_capable_content_formats=full.sql_capable_content_formats,
        informal_tokens=full.informal_tokens,
    )


def test_identity_eligible_defaults_to_true_without_identity_rule() -> None:
    """未命中任何身份规则 → identity_eligible 默认 True；命中且声明 false 才排除。"""

    rules = _identity_only_rules()

    present = classify_file(
        _file(node_id="7001"),
        rules=rules,
        workspace_name="ws_a",
        content_state=CONTENT_STATE_PRESENT,
    )
    assert "NODE_ID_MISSING" not in present.matched_rule_ids
    assert present.identity_eligible is True
    assert present.overall_eligible is True

    missing = classify_file(
        _file(file_id="102", node_id=None),
        rules=rules,
        workspace_name="ws_a",
        content_state=CONTENT_STATE_PRESENT,
    )
    assert "NODE_ID_MISSING" in missing.matched_rule_ids
    assert missing.identity_eligible is False
    assert missing.overall_eligible is False


def test_not_checked_content_state_does_not_block_sql_eligibility() -> None:
    """not_checked 既不是 Content 缺口，也不阻断 sql_eligible。"""

    rules = load_scope_rules(_REPO_CONFIG)

    decision = classify_file(
        _file(),
        rules=rules,
        workspace_name="ws_a",
        content_state=CONTENT_STATE_NOT_CHECKED,
    )

    assert decision.content_state == CONTENT_STATE_NOT_CHECKED
    assert decision.sql_eligible is True
    assert decision.sql_reason_code == "SQL_ANALYSIS_ELIGIBLE"


# ============================================================
# 4. cleanup_candidate 全量删除
# ============================================================


def test_cleanup_candidate_in_config_is_rejected(tmp_path: Path) -> None:
    """旧配置里的 cleanup_candidate 字段现在是未知字段 → fail-fast。"""

    data = _base_rules()

    for rule in data["rules"]:
        if rule["id"] == "INFORMAL_TASK_STRONG":
            rule["result"]["cleanup_candidate"] = "when_node_id_missing"

    with pytest.raises(ScopeRulesError, match="cleanup_candidate"):
        load_scope_rules(_write_rules(tmp_path / "rules.yaml", data))


def test_cleanup_candidate_removed_from_models_and_products() -> None:
    """模型、统计与产物字段都不再携带清理候选概念。"""

    assert "cleanup_candidate" not in {item.name for item in fields(ScopeResult)}
    assert not hasattr(FileScopeStats(), "cleanup_candidate_count")

    decision = classify_file(
        _file(file_id="105", node_id=None, file_name="test_001"),
        rules=load_scope_rules(_REPO_CONFIG),
        workspace_name="ws_a",
        content_state=CONTENT_STATE_PRESENT,
    )

    assert "cleanup_candidate" not in decision.to_dict()
    assert "INFORMAL_TASK_STRONG" in decision.matched_rule_ids


# ============================================================
# 5. content_check 配置 fail-fast
# ============================================================


def _drop_content_check(data: dict[str, Any]) -> None:
    del data["content_check"]


def _content_check_as_text(data: dict[str, Any]) -> None:
    data["content_check"] = "true"


def _drop_enabled(data: dict[str, Any]) -> None:
    del data["content_check"]["enabled"]


def _enabled_as_text(data: dict[str, Any]) -> None:
    data["content_check"]["enabled"] = "true"


def _drop_enabled_formats(data: dict[str, Any]) -> None:
    del data["content_check"]["enabled_formats"]


def _unknown_format(data: dict[str, Any]) -> None:
    data["content_check"]["enabled_formats"] = ["SQL", "JAVA"]


def _unknown_field(data: dict[str, Any]) -> None:
    data["content_check"]["dry_run"] = True


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (_drop_content_check, "content_check 必须是映射"),
        (_content_check_as_text, "content_check 必须是映射"),
        (_drop_enabled, "content_check.enabled 必须是布尔值"),
        (_enabled_as_text, "content_check.enabled 必须是布尔值"),
        (_drop_enabled_formats, "content_check.enabled_formats 必须是非空列表"),
        (_unknown_format, "未登记的格式"),
        (_unknown_field, "包含未知字段"),
    ],
    ids=[
        "missing",
        "not-a-mapping",
        "enabled-missing",
        "enabled-not-bool",
        "formats-missing",
        "unknown-format",
        "unknown-field",
    ],
)
def test_invalid_content_check_fails_fast(
    tmp_path: Path,
    mutate: Any,
    match: str,
) -> None:
    data = _base_rules()
    mutate(data)

    with pytest.raises(ScopeRulesError, match=match):
        load_scope_rules(_write_rules(tmp_path / "rules.yaml", data))


def test_content_check_disabled_flag() -> None:
    disabled = ContentCheckConfig(enabled=False, enabled_formats=frozenset({"SQL"}))

    assert disabled.is_enabled("SQL") is False
    assert ContentCheckConfig(enabled=True, enabled_formats=frozenset({"SQL"})).is_enabled("sql")
    assert (
        ContentCheckConfig(enabled=True, enabled_formats=frozenset({"SQL"})).is_enabled("PYTHON")
        is False
    )


# ============================================================
# 6. Content 检查开关与三份清单契约（黑盒）
# ============================================================


def test_content_check_switch_changes_content_state_and_candidates(
    cli_env: Any,
    run_cli: Any,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """启用时读 Snapshot 并阻断缺失内容；关闭时全部 not_checked 且不阻断。"""

    write_snapshot(
        Path("source"),
        workspaces=[{"id": 9001, "name": "ws_a"}],
        files=[
            {
                "workspace_id": 9001,
                "file_id": "101",
                "file_name": "etl_ok",
                "node_id": "7001",
                "content": "INSERT INTO ${ws_a}.t1 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "102",
                "file_name": "etl_gone",
                "node_id": "7002",
                "content": "INSERT INTO ${ws_a}.t2 SELECT 1;",
            },
            {
                "workspace_id": 9001,
                "file_id": "103",
                "file_name": "py_job",
                "node_id": "7003",
                "content": "print('x')",
                "file_type": 22,
                "content_format": "PYTHON",
            },
        ],
    )
    assert_sandbox(Path("source/dataworks/workspaces/9001/content/102__etl_gone.sql")).unlink()

    # ---- 默认配置：content_check 启用，只有 SQL 被检查 ----
    assert run_cli("analyze", "--stage", "inventory") == 0

    files = _read(Path("analysis/inventory/files.json"))
    candidates = _read(Path("analysis/scope/inputs/sql-candidates.json"))
    excluded = _read(Path("analysis/scope/inputs/excluded-tasks.json"))
    review = _read(Path("analysis/scope/review-tasks.json"))

    # 清单不因分类减少任何记录，且两份资格清单互补。
    assert files["count"] == 3
    assert {item["file_id"] for item in candidates["tasks"]} == {"101"}
    assert {item["file_id"] for item in excluded["tasks"]} == {"102", "103"}
    assert excluded["count"] + candidates["count"] == files["count"]
    assert review["count"] == 0

    scope_summary = Path("analysis/scope/summary.md").read_text(encoding="utf-8")
    assert "| 内容状态 | present | 1 |" in scope_summary
    assert "| 内容状态 | path_missing | 1 |" in scope_summary
    assert "| 内容状态 | not_checked | 1 |" in scope_summary

    summary = Path("analysis/inventory/summary.md").read_text(encoding="utf-8")
    assert "| 内容不可用 | 1 |" in summary
    assert "| 未启用 Content 检查 | 1 |" in summary
    assert "| Medium | content_file 指向的 Snapshot 文件缺失 | 1 |" in summary

    # ---- 关闭 Content 检查：全部 not_checked，既不计缺口也不阻断 ----
    data = _base_rules()
    data["content_check"]["enabled"] = False
    monkeypatch.setenv("SCOPE_RULES_PATH", str(_write_rules(tmp_path / "rules.yaml", data)))

    assert run_cli("analyze", "--stage", "inventory") == 0

    candidates = _read(Path("analysis/scope/inputs/sql-candidates.json"))
    excluded = _read(Path("analysis/scope/inputs/excluded-tasks.json"))

    assert {item["file_id"] for item in candidates["tasks"]} == {"101", "102"}
    assert {item["file_id"] for item in excluded["tasks"]} == {"103"}

    scope_summary = Path("analysis/scope/summary.md").read_text(encoding="utf-8")
    assert "| 内容状态 | not_checked | 3 |" in scope_summary
    assert "| 内容状态 | present | 0 |" in scope_summary

    summary = Path("analysis/inventory/summary.md").read_text(encoding="utf-8")
    assert "| 内容可用 | 0 |" in summary
    assert "| 内容不可用 | 0 |" in summary
    assert "| 未启用 Content 检查 | 3 |" in summary
    # 未检查 → 不读 Snapshot，也就不会记录 path_missing 技术异常。
    assert "| Medium | content_file 指向的 Snapshot 文件缺失 | 0 |" in summary
    assert "当前未发现异常" in summary

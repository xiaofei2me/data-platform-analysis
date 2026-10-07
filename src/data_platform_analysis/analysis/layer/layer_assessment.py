"""M2.2 Layer Assessment。

目标：

    基于 Workspace Layer 配置事实 + CDM 子层候选规则，为每张表给出
    candidate_layer、status 与 evidence。

输入：

    analysis/inventory/tables.json（M2.1 Inventory 输出）
    config/layer-rules.yaml（Layer 规则配置）

输出：

    analysis/layer/assessments.json
    analysis/layer/summary.md

约定：

1. workspace_layer 按 workspace_id 查 workspace_layers 得到，
   是 Observed / Configured Fact，不叫 candidate。
2. 只有 CDM 才做子层识别（DIM / DWD / DWS），依据 table_name 的
   prefix / suffix；ODS / ADS 的 candidate_layer 直接等于
   workspace_layer，其他层的 prefix / suffix 命中只记入 evidence
   作为跨层命名提示（cross_layer_hits），不改变 candidate。
3. UNKNOWN 只表示现有 Evidence 不足以判断子层，不产生 violation；
   是否属于命名规范问题由后续 Convention Assessment 判定。
4. workspace_id 未配置时不做任何静默推断（尤其是不按 workspace_name 猜），
   记为 UNKNOWN，并在 evidence 与 summary 中显式标注。
5. 只读 Inventory 输出与规则配置：不调用外部 API，不依赖 LLM / SQLGlot /
   SQL 内容 / Lineage / Profiling，不修改 Inventory 与规则配置。
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ...config import PROJECT_ROOT
from ...io_utils import ensure_dir, write_json, write_text
from ..models import (
    EVIDENCE_TYPE_PREFIX,
    EVIDENCE_TYPE_SUFFIX,
    EVIDENCE_TYPE_WORKSPACE,
    LAYER_STATUS_CONFLICT,
    LAYER_STATUS_MATCH,
    LAYER_STATUS_UNKNOWN,
    LayerAssessment,
)
from ..reports import render_layer_summary

logger = logging.getLogger(__name__)

CDM_LAYER = "CDM"
"""唯一需要做子层识别的 Workspace Layer。"""

INVENTORY_TABLE_KEY = "tables"
"""Inventory tables.json 中的表数组字段。"""


def _display_path(path: Path) -> str:
    """日志与报告中展示的路径：项目根内用相对路径，其余保持绝对。"""

    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))

    except ValueError:
        return str(path)


class LayerAssessmentError(RuntimeError):
    """M2.2 无法继续的配置 / 输入错误。"""


# ============================================================
# 规则配置模型
# ============================================================


@dataclass(frozen=True)
class WorkspaceLayerRule:
    """单个 Workspace 的 Layer 配置事实。"""

    workspace_id: int
    workspace_name: str
    layer: str


@dataclass(frozen=True)
class SubLayerRule:
    """单个 CDM 子层的 prefix / suffix 识别规则。

    prefix / suffix 保持配置原文，大小写匹配在比较阶段处理。
    """

    layer: str
    prefixes: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class LayerRules:
    """layer-rules.yaml 的内存表示。"""

    version: str
    source_path: Path
    workspace_layers: dict[int, WorkspaceLayerRule]
    sub_layers: dict[str, tuple[SubLayerRule, ...]]
    case_sensitive: bool


def load_layer_rules(path: Path) -> LayerRules:
    """读取并严格校验 layer-rules 配置。

    Layer 名称统一归一化为大写（ODS / CDM / ADS / DIM / DWD / DWS），
    校验失败一律抛 LayerAssessmentError，不静默回退默认值。
    """

    if not path.exists():
        raise LayerAssessmentError(f"Layer Rules 配置文件不存在：{path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    except yaml.YAMLError as exc:
        raise LayerAssessmentError(f"Layer Rules 配置不是合法的 YAML：{path}（{exc}）") from exc

    if raw is None:
        raise LayerAssessmentError(f"Layer Rules 配置为空：{path}")

    if not isinstance(raw, dict):
        raise LayerAssessmentError(f"Layer Rules 配置根节点必须是映射：{path}")

    version = raw.get("version")

    if not isinstance(version, str) or not version.strip():
        raise LayerAssessmentError(f"Layer Rules 配置缺少 version：{path}")

    rules = LayerRules(
        version=version.strip(),
        source_path=path,
        workspace_layers=_parse_workspace_layers(raw.get("workspace_layers"), path),
        sub_layers=_parse_sub_layers(raw.get("sub_layers"), path),
        case_sensitive=_parse_matching(raw.get("matching"), path),
    )

    sub_layer_summary = "，".join(
        f"{layer}={sum(len(rule.prefixes) + len(rule.suffixes) for rule in entries)}"
        for layer, entries in rules.sub_layers.items()
    )

    logger.info(
        "Layer Rules 已加载：%s（version=%s，workspace=%s，子层规则数：%s，case_sensitive=%s）",
        _display_path(rules.source_path),
        rules.version,
        len(rules.workspace_layers),
        sub_layer_summary or "无",
        rules.case_sensitive,
    )

    return rules


# ============================================================
# 规则配置解析
# ============================================================


def _parse_workspace_layers(value: Any, path: Path) -> dict[int, WorkspaceLayerRule]:
    """解析 workspace_layers：必须非空、workspace_id 不可重复。"""

    if not isinstance(value, list) or not value:
        raise LayerAssessmentError(f"workspace_layers 必须是非空列表：{path}")

    rules: dict[int, WorkspaceLayerRule] = {}

    for position, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise LayerAssessmentError(f"workspace_layers[{position}] 必须是映射：{path}")

        workspace_id = _as_int(entry.get("workspace_id"))

        if workspace_id is None:
            raise LayerAssessmentError(
                f"workspace_layers[{position}] 缺少合法的 workspace_id：{path}"
            )

        if workspace_id in rules:
            raise LayerAssessmentError(
                f"workspace_layers 存在重复的 workspace_id：{workspace_id}（{path}）"
            )

        workspace_name = _required_text(entry.get("workspace_name"), path)
        layer = _required_text(entry.get("layer"), path)

        rules[workspace_id] = WorkspaceLayerRule(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            layer=layer.upper(),
        )

    return rules


def _parse_sub_layers(value: Any, path: Path) -> dict[str, tuple[SubLayerRule, ...]]:
    """解析 sub_layers；保持配置文件中的声明顺序。"""

    if value is None:
        return {}

    if not isinstance(value, dict):
        raise LayerAssessmentError(f"sub_layers 必须是映射：{path}")

    result: dict[str, tuple[SubLayerRule, ...]] = {}

    for layer_name, entries in value.items():
        layer_key = str(layer_name).strip().upper()

        if not layer_key:
            raise LayerAssessmentError(f"sub_layers 包含空的 layer 名称：{path}")

        if not isinstance(entries, dict):
            raise LayerAssessmentError(f"sub_layers.{layer_name} 必须是映射：{path}")

        rules: list[SubLayerRule] = []

        for sub_name, spec in entries.items():
            sub_layer = str(sub_name).strip().upper()

            if not sub_layer:
                raise LayerAssessmentError(f"sub_layers.{layer_name} 包含空的子层名称：{path}")

            if spec is None:
                spec = {}

            if not isinstance(spec, dict):
                raise LayerAssessmentError(
                    f"sub_layers.{layer_name}.{sub_name} 必须是映射：{path}"
                )

            rules.append(
                SubLayerRule(
                    layer=sub_layer,
                    prefixes=_parse_patterns(
                        spec.get("prefixes"),
                        label=f"sub_layers.{layer_name}.{sub_name}.prefixes",
                        path=path,
                    ),
                    suffixes=_parse_patterns(
                        spec.get("suffixes"),
                        label=f"sub_layers.{layer_name}.{sub_name}.suffixes",
                        path=path,
                    ),
                )
            )

        result[layer_key] = tuple(rules)

    return result


def _parse_patterns(value: Any, *, label: str, path: Path) -> tuple[str, ...]:
    """解析 prefix / suffix 列表：只接受非空字符串。"""

    if value is None:
        return ()

    if not isinstance(value, list):
        raise LayerAssessmentError(f"{label} 必须是列表：{path}")

    patterns: list[str] = []

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise LayerAssessmentError(f"{label} 只能包含非空字符串：{path}")

        patterns.append(item.strip())

    return tuple(patterns)


def _parse_matching(value: Any, path: Path) -> bool:
    """解析 matching.case_sensitive；缺省为 false（忽略大小写）。"""

    if value is None:
        return False

    if not isinstance(value, dict):
        raise LayerAssessmentError(f"matching 必须是映射：{path}")

    case_sensitive = value.get("case_sensitive", False)

    if not isinstance(case_sensitive, bool):
        raise LayerAssessmentError(f"matching.case_sensitive 必须是布尔值：{path}")

    return case_sensitive


def _required_text(value: Any, path: Path) -> str:
    """取非空字符串，否则报配置错误。"""

    if isinstance(value, str) and value.strip():
        return value.strip()

    raise LayerAssessmentError(f"配置字段必须是非空字符串：{value!r}（{path}）")


def _as_int(value: Any) -> int | None:
    """把整数 / 数字字符串转成 int，其余返回 None。"""

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())

    return None


# ============================================================
# 识别
# ============================================================


def assess_tables(
    rules: LayerRules,
    tables: Sequence[Mapping[str, Any]],
) -> list[LayerAssessment]:
    """对全部 Inventory 表记录执行 M2.2 识别。

    结果按 (workspace_id, project, table_name) 稳定排序，
    保证重复运行 deterministic。
    """

    assessments = [
        _assess_table(rules, entry, position) for position, entry in enumerate(tables)
    ]

    assessments.sort(key=lambda item: (item.workspace_id, item.project, item.table_name))

    return assessments


def _assess_table(
    rules: LayerRules,
    entry: Mapping[str, Any],
    position: int,
) -> LayerAssessment:
    """识别单张表的 Workspace Layer 与 CDM 子层候选。"""

    workspace_id = _as_int(entry.get("workspace_id"))

    if workspace_id is None:
        raise LayerAssessmentError(f"inventory tables[{position}] 缺少合法的 workspace_id")

    workspace_name = _inventory_text(entry, "workspace_name", position)
    project = _inventory_text(entry, "project", position)
    table_name = _inventory_text(entry, "table", position)

    table_identifier_value = entry.get("table_key")
    table_identifier = (
        table_identifier_value.strip()
        if isinstance(table_identifier_value, str) and table_identifier_value.strip()
        else f"{project}.{table_name}"
    )

    rule = rules.workspace_layers.get(workspace_id)

    # ----------------------------------------------------
    # workspace_id 未配置：不做任何推断。
    # ----------------------------------------------------
    if rule is None:
        return LayerAssessment(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            workspace_layer=None,
            project=project,
            table_name=table_name,
            table_identifier=table_identifier,
            candidate_layer=None,
            status=LAYER_STATUS_UNKNOWN,
            evidence=[
                {
                    "type": EVIDENCE_TYPE_WORKSPACE,
                    "layer": None,
                    "configured": False,
                }
            ],
        )

    layer = rule.layer

    evidence: list[dict[str, Any]] = [
        {
            "type": EVIDENCE_TYPE_WORKSPACE,
            "layer": layer,
            "configured": True,
        }
    ]

    # ----------------------------------------------------
    # ODS / ADS 等终点层：candidate 直接等于 workspace_layer。
    # 其他层的 prefix / suffix 命中只记入 evidence 作为跨层命名提示，
    # 不改变 candidate（仓库现状按 workspace 分层）。
    # ----------------------------------------------------
    if layer != CDM_LAYER and layer not in rules.sub_layers:
        evidence.extend(
            _match_sub_layers(rules, table_name, _all_sub_layer_rules(rules))
        )

        return LayerAssessment(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            workspace_layer=layer,
            project=project,
            table_name=table_name,
            table_identifier=table_identifier,
            candidate_layer=layer,
            status=LAYER_STATUS_MATCH,
            evidence=evidence,
        )

    # ----------------------------------------------------
    # CDM：按 prefix / suffix 收集全部命中规则。
    # ----------------------------------------------------
    hits = _match_sub_layers(rules, table_name, rules.sub_layers.get(layer, ()))

    evidence.extend(hits)

    matched_layers = list(dict.fromkeys(str(hit["layer"]) for hit in hits))

    if not matched_layers:
        candidate_layer = None
        status = LAYER_STATUS_UNKNOWN

    elif len(matched_layers) == 1:
        candidate_layer = matched_layers[0]
        status = LAYER_STATUS_MATCH

    else:
        candidate_layer = None
        status = LAYER_STATUS_CONFLICT

    return LayerAssessment(
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        workspace_layer=layer,
        project=project,
        table_name=table_name,
        table_identifier=table_identifier,
        candidate_layer=candidate_layer,
        status=status,
        evidence=evidence,
    )


def _all_sub_layer_rules(rules: LayerRules) -> tuple[SubLayerRule, ...]:
    """全部子层规则，按配置顺序展平，用于 ODS / ADS 的跨层命名提示。"""

    return tuple(
        rule for entries in rules.sub_layers.values() for rule in entries
    )


def _match_sub_layers(
    rules: LayerRules,
    table_name: str,
    sub_layer_rules: Sequence[SubLayerRule],
) -> list[dict[str, Any]]:
    """按配置顺序收集全部命中的 prefix / suffix 规则。

    prefix OR suffix：同一子层多条规则任意命中即算命中；
    evidence 保留所有命中项，包括跨子层冲突时的全部规则。
    """

    name = table_name if rules.case_sensitive else table_name.lower()
    hits: list[dict[str, Any]] = []

    for sub_rule in sub_layer_rules:
        for pattern in sub_rule.prefixes:
            probe = pattern if rules.case_sensitive else pattern.lower()

            if name.startswith(probe):
                hits.append(
                    {
                        "type": EVIDENCE_TYPE_PREFIX,
                        "layer": sub_rule.layer,
                        "pattern": pattern,
                    }
                )

        for pattern in sub_rule.suffixes:
            probe = pattern if rules.case_sensitive else pattern.lower()

            if name.endswith(probe):
                hits.append(
                    {
                        "type": EVIDENCE_TYPE_SUFFIX,
                        "layer": sub_rule.layer,
                        "pattern": pattern,
                    }
                )

    return hits


def _inventory_text(entry: Mapping[str, Any], key: str, position: int) -> str:
    """取 Inventory 记录中的非空字符串字段。"""

    value = entry.get(key)

    if isinstance(value, str) and value.strip():
        return value.strip()

    raise LayerAssessmentError(f"inventory tables[{position}] 缺少合法的 {key}")


# ============================================================
# 运行与写出
# ============================================================


@dataclass
class LayerAssessmentResult:
    """一次 M2.2 运行的结果。"""

    rules_path: Path
    rules_version: str
    inventory_path: Path
    assessments: list[LayerAssessment] = field(default_factory=list)

    @property
    def status_counts(self) -> dict[str, int]:
        """status → 表数量，按固定状态顺序返回。"""

        counter = Counter(item.status for item in self.assessments)

        ordered = [LAYER_STATUS_MATCH, LAYER_STATUS_UNKNOWN, LAYER_STATUS_CONFLICT]

        return {status: counter[status] for status in ordered if status in counter}

    @property
    def unconfigured_workspace_ids(self) -> list[int]:
        """未在 layer-rules.yaml 中配置的 workspace_id，升序。"""

        return sorted(
            {
                item.workspace_id
                for item in self.assessments
                if item.workspace_layer is None
            }
        )


def read_inventory_tables(path: Path) -> list[dict[str, Any]]:
    """读取 M2.1 的 tables.json，只做结构校验。"""

    if not path.exists():
        raise LayerAssessmentError(f"Inventory 输入不存在：{path}（请先执行 analyze）")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))

    except json.JSONDecodeError as exc:
        raise LayerAssessmentError(f"Inventory 输入不是合法的 JSON：{path}（{exc}）") from exc

    if not isinstance(raw, dict) or not isinstance(raw.get(INVENTORY_TABLE_KEY), list):
        raise LayerAssessmentError(f"Inventory 输入缺少 {INVENTORY_TABLE_KEY} 数组：{path}")

    tables: list[dict[str, Any]] = []

    for position, entry in enumerate(raw[INVENTORY_TABLE_KEY]):
        if not isinstance(entry, dict):
            raise LayerAssessmentError(
                f"Inventory {INVENTORY_TABLE_KEY}[{position}] 不是对象：{path}"
            )

        tables.append(entry)

    logger.info(
        "Inventory 输入已读取：%s（table=%s）", _display_path(path), len(tables)
    )

    return tables


def run_layer_assessment(
    *,
    inventory_path: Path,
    rules_path: Path,
    output_dir: Path,
) -> LayerAssessmentResult:
    """执行 M2.2 并写出 analysis/layer 产物。

    CLI 子命令与 AnalysisPipeline 共用这一个入口，保证两条路径行为一致。
    """

    rules = load_layer_rules(rules_path)
    tables = read_inventory_tables(inventory_path)

    result = LayerAssessmentResult(
        rules_path=rules_path,
        rules_version=rules.version,
        inventory_path=inventory_path,
        assessments=assess_tables(rules, tables),
    )

    unconfigured = result.unconfigured_workspace_ids

    if unconfigured:
        logger.warning(
            "layer-rules.yaml 未配置的 workspace_id：%s；"
            "这些表不做任何推断，一律记为 UNKNOWN",
            ", ".join(str(item) for item in unconfigured),
        )

    conflicts = result.status_counts.get(LAYER_STATUS_CONFLICT, 0)

    if conflicts:
        logger.warning(
            "M2.2 检出 %s 条 CONFLICT（prefix 与 suffix 命中不同子层），"
            "需人工判定，明细见 %s",
            conflicts,
            _display_path(output_dir / "summary.md"),
        )

    cross_layer = sum(
        1 for item in result.assessments if item.cross_layer_hits
    )

    if cross_layer:
        logger.warning(
            "M2.2 检出 %s 张表带其他层命名前缀（跨层命名提示），"
            "candidate_layer 仍按 workspace_layer 判定，明细见 %s",
            cross_layer,
            _display_path(output_dir / "summary.md"),
        )

    write_layer_assessment(result, output_dir)

    logger.info(
        "M2.2 Layer Assessment 完成：table=%s，%s，未配置 workspace=%s",
        len(result.assessments),
        "，".join(f"{key}={value}" for key, value in result.status_counts.items()),
        len(unconfigured),
    )

    return result


def write_layer_assessment(
    result: LayerAssessmentResult,
    output_dir: Path,
) -> tuple[Path, Path]:
    """写出 assessments.json 与 summary.md，返回两个路径。"""

    ensure_dir(output_dir)

    assessments_path = output_dir / "assessments.json"
    summary_path = output_dir / "summary.md"

    write_json(
        assessments_path,
        {
            "count": len(result.assessments),
            "assessments": [item.to_dict() for item in result.assessments],
        },
    )

    write_text(
        summary_path,
        render_layer_summary(
            result.assessments,
            rules_path=_display_path(result.rules_path),
            rules_version=result.rules_version,
            inventory_path=_display_path(result.inventory_path),
        ),
    )

    logger.info(
        "M2.2 产物已写出：%s，%s",
        _display_path(assessments_path),
        _display_path(summary_path),
    )

    return assessments_path, summary_path

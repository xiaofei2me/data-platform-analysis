"""M2.4 Table Lineage：把表引用汇总成去重的表级血缘。

输出：

    analysis/lineage/table-lineage.json
    analysis/lineage/core-table-candidates.json
    analysis/lineage/summary.md

原则：

1. edge = (workspace_id, source_key, target_key)，同一条边只保留一次，
   多条 SQL 证据全部收进 evidence。
2. source_table / target_table 保留 SQL 原始写法；
   source_key / target_key 是补齐 Project 后的规范标识。
3. 只描述数据流向，不推断业务含义。
4. source / target_layer_candidate 取自 M2.2 Layer Assessment 的
   candidate_layer（唯一层级判定），M2.4 不自行判定层级。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .inventory import Inventory
from .models import (
    CoreTableCandidate,
    LayerAssessment,
    LineageEdge,
    LineageEvidence,
    TableReference,
    numeric_id_sort_key,
)
from .naming import project_of, qualify_table_ref

logger = logging.getLogger(__name__)


@dataclass
class LineageResult:
    """M2.4 的血缘结果。"""

    edges: list[LineageEdge] = field(default_factory=list)
    candidates: list[CoreTableCandidate] = field(default_factory=list)
    project_workspace_ids: dict[str, int] = field(default_factory=dict)

    @property
    def cross_workspace_edges(self) -> list[LineageEdge]:
        """两端 Workspace 都能识别、且不在同一个 Workspace 的边。"""

        return [
            edge
            for edge in self.edges
            if edge.source_workspace_id is not None
            and edge.target_workspace_id is not None
            and edge.source_workspace_id != edge.target_workspace_id
        ]


class LineageBuilder:
    """从 TableReference 构建表级血缘。"""

    def __init__(
        self,
        references: list[TableReference],
        inventory: Inventory,
        layer_assessments: list[LayerAssessment],
    ) -> None:
        self.references = references
        self.inventory = inventory

        self.project_workspace_ids: dict[str, int] = {}
        self.workspace_projects: dict[int, str] = {}
        self.workspace_table_keys: dict[int, str] = {}

        for workspace in inventory.workspaces:
            self.workspace_projects[workspace.workspace_id] = workspace.project
            self.project_workspace_ids.setdefault(
                workspace.project.casefold(),
                workspace.workspace_id,
            )

        self.layer_by_key: dict[str, str | None] = {}
        self.workspace_by_key: dict[str, int] = {}
        self.key_by_casefold: dict[str, str] = {}

        # 层级来自 M2.2 Layer Assessment 的 candidate_layer（唯一层级判定）。
        for item in layer_assessments:
            self.layer_by_key[item.table_identifier] = item.candidate_layer

        for table in inventory.tables:
            self.workspace_by_key[table.table_key] = table.workspace_id
            self.key_by_casefold.setdefault(
                table.table_key.casefold(),
                table.table_key,
            )

    def build(self) -> LineageResult:
        """构建去重后的血缘边与核心表候选。"""

        edges: dict[tuple[int, str, str], LineageEdge] = {}

        for reference in self.references:
            own_project = self.workspace_projects.get(reference.workspace_id)

            evidence = LineageEvidence(
                file_id=reference.file_id,
                file_name=reference.file_name,
                node_id=reference.node_id,
                statement_id=reference.statement_id,
                extraction_method=reference.extraction_method,
                content_file=reference.content_file,
            )

            for source in reference.source_tables:
                for target in reference.target_tables:
                    source_key = qualify_table_ref(source, own_project)
                    target_key = qualify_table_ref(target, own_project)

                    if source_key == target_key:
                        continue

                    key = (reference.workspace_id, source_key, target_key)
                    edge = edges.get(key)

                    if edge is None:
                        edges[key] = LineageEdge(
                            workspace_id=reference.workspace_id,
                            source_table=source,
                            target_table=target,
                            source_key=source_key,
                            target_key=target_key,
                            source_workspace_id=self._workspace_of(source_key),
                            target_workspace_id=self._workspace_of(target_key),
                            source_layer_candidate=self._layer_of(source_key),
                            target_layer_candidate=self._layer_of(target_key),
                            evidence=[evidence],
                        )

                    else:
                        edge.evidence.append(evidence)

        sorted_edges = sorted(
            edges.values(),
            key=lambda edge: (
                numeric_id_sort_key(edge.workspace_id),
                edge.source_key,
                edge.target_key,
            ),
        )

        for edge in sorted_edges:
            edge.evidence.sort(
                key=lambda item: (
                    numeric_id_sort_key(item.file_id),
                    item.statement_id,
                )
            )

        candidates = self._build_candidates(sorted_edges)

        logger.info(
            "M2.4 Lineage 完成：edge=%s，cross_workspace=%s，candidate=%s",
            len(sorted_edges),
            len([edge for edge in sorted_edges if self._is_cross_workspace(edge)]),
            len(candidates),
        )

        return LineageResult(
            edges=sorted_edges,
            candidates=candidates,
            project_workspace_ids=dict(sorted(self.project_workspace_ids.items())),
        )

    # ==========================================================
    # 反查
    # ==========================================================

    def _workspace_of(self, table_key: str) -> int | None:
        """按规范标识反查 Workspace。"""

        workspace_id = self.workspace_by_key.get(table_key)

        if workspace_id is not None:
            return workspace_id

        canonical = self.key_by_casefold.get(table_key.casefold())

        if canonical is not None:
            return self.workspace_by_key.get(canonical)

        project = project_of(table_key)

        if not project:
            return None

        return self.project_workspace_ids.get(project.casefold())

    def _layer_of(self, table_key: str) -> str | None:
        """按规范标识反查层级候选（来自 M2.2 candidate_layer）。"""

        layer = self.layer_by_key.get(table_key)

        if layer is not None:
            return layer

        canonical = self.key_by_casefold.get(table_key.casefold())

        if canonical is None:
            return None

        return self.layer_by_key.get(canonical)

    @staticmethod
    def _is_cross_workspace(edge: LineageEdge) -> bool:
        """判断是否跨 Workspace。"""

        return (
            edge.source_workspace_id is not None
            and edge.target_workspace_id is not None
            and edge.source_workspace_id != edge.target_workspace_id
        )

    # ==========================================================
    # Core table candidates
    # ==========================================================

    def _build_candidates(
        self,
        edges: list[LineageEdge],
    ) -> list[CoreTableCandidate]:
        """按明确指标计算核心表候选。"""

        upstream: dict[str, set[str]] = {}
        downstream: dict[str, set[str]] = {}
        evidence_count: dict[str, int] = {}

        for edge in edges:
            downstream.setdefault(edge.source_key, set()).add(edge.target_key)
            upstream.setdefault(edge.target_key, set()).add(edge.source_key)

            for key in (edge.source_key, edge.target_key):
                evidence_count[key] = evidence_count.get(key, 0) + len(edge.evidence)

        candidates: list[CoreTableCandidate] = []

        for key in sorted(set(upstream) | set(downstream)):
            canonical = self.key_by_casefold.get(key.casefold(), key)
            workspace_id = self.workspace_by_key.get(canonical)

            candidates.append(
                CoreTableCandidate(
                    table_key=key,
                    workspace_id=workspace_id,
                    in_inventory=canonical in self.workspace_by_key,
                    layer_candidate=self.layer_by_key.get(canonical),
                    upstream_count=len(upstream.get(key, set())),
                    downstream_count=len(downstream.get(key, set())),
                    evidence_count=evidence_count.get(key, 0),
                )
            )

        candidates.sort(
            key=lambda item: (-item.downstream_count, -item.upstream_count, item.table_key)
        )

        return candidates

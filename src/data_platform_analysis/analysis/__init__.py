"""Phase 2 Analysis：把 source/ Snapshot 转换成可机器读取的 Evidence。

阶段边界：

    source/ Snapshot
          ↓
    M2.1 Warehouse Inventory
          ↓
    M2.5 Layer Assessment（只依赖 M2.1 输出与 config/layer-rules.yaml，
                          产出唯一层级判定 candidate_layer）
          ↓
    M2.2 SQL Analysis
          ↓
    M2.3 Table Reference / Table Lineage（层级标注取自 M2.5 candidate_layer）
          ↓
    M2.4 Data Profiling（当前为 Metadata Profiling）
          ↓
    analysis/ Evidence

硬性约束：

1. 只读 source/，禁止调用 DataWorks / MaxCompute / QuickBI 等外部 API。
2. 不修改 source/，所有产物写入 analysis/。
3. raw Snapshot 是 Source of Truth，index 只用于导航。
4. 本阶段只产出 Candidate 与 Evidence，不产出业务结论。
"""

from __future__ import annotations

from .pipeline import AnalysisPipeline, AnalysisResult

__all__ = [
    "AnalysisPipeline",
    "AnalysisResult",
]

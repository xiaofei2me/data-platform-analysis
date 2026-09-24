# Data Platform Analysis

采集 DataWorks 与 MaxCompute 的数据资产，形成时点快照，为当前数仓现状分析以及后续 DWS、Semantic Layer 设计提供数据基础。

## Language

**Workspace（工作空间）**:
DataWorks 的工作空间，是节点调度与开发的边界。由 ProjectId 唯一标识，具有人类可读名称，并与一个 MaxCompute 项目保持 1:1 绑定。
_Avoid_: 项目、Project（与 MaxCompute 项目混淆）

**Node（节点）**:
DataWorks 工作空间内的调度任务单元，承载 SQL 或脚本，是采集与血缘分析的基本对象。
_Avoid_: Job、任务（与「任务级依赖」中的调度关系混淆）

**Snapshot（快照）**:
某一时点从 DataWorks 与 MaxCompute 采集得到的本地数据副本，是后续所有分析阶段的输入。
_Avoid_: 导出结果、备份

**Raw（原始响应）**:
完整保存的 DataWorks / MaxCompute API 响应，是快照中的唯一真相源；任何未预先索引的字段都应从 Raw 提取，而不是重新调用 API。
_Avoid_: 源数据、原始数据（易与业务源表混淆）

**Table-level Lineage（表级血缘）**:
source_table → task → target_table 的表间加工关系，允许跨 Workspace、跨 MaxCompute 项目。
_Avoid_: 数据血缘（泛称，不区分层级）

**Task-level Dependency（任务级依赖）**:
DataWorks 节点之间的调度依赖关系；当前分析边界按单 Workspace 内理解，不主动建模跨 Workspace 任务依赖。
_Avoid_: 血缘（不区分任务级与表级时禁用）

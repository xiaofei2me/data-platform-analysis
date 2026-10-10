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

**Candidate（候选）**:
机器基于只读证据产出、尚未经过人工回填的判定；M3 ～ M3.6 v2 的 Domain、Process、Grain、Fact、Dimension、Finding、Problem 一律停留在候选口径。
_Avoid_: 结论、结论模型（机器阶段禁止使用）

**Finding（评审发现）**:
M3.6 对当前模型的一次结构观测（18 类，逐条记录现象并提出人工问题），不包含对错判断。
_Avoid_: 问题、错误、缺陷

**Problem（问题候选）**:
M3.6 v2 把同一根因下的若干 finding 聚合成的候选问题（13 类），携带证据、影响、根因与重构理由，仍待人工确认。
_Avoid_: 已确认问题、缺陷清单

**Confirmed Problem（已确认问题）**:
唯一由 `current-state-problem-review-checklist.md` 人工回填 `confirmed` 产生的状态；机器永远不会写入。
_Avoid_: 机器确认、自动确认

**Human Adjudication（人工裁决）**:
对 finding 与 problem 清单回填 `human_status` 的过程，是 candidate 变成 confirmed / rejected 的唯一通道；两个清单各自独立、互不替代。
_Avoid_: 自动裁决、审核通过

**UNKNOWN（模型角色未定）**:
表的 `current_role` 无法判定的合法结果，分 `NO_ANCHOR`（无锚点无血缘）与 `NO_EVIDENCE`（血缘证据不足）两种解释；证据不足时 UNKNOWN 即正确答案。
_Avoid_: 坏模型、无效模型、待修复

**Analysis Scope Rules（分析范围规则）**:
`config/analysis-scope-rules.yaml` 声明、由 Scope 阶段通过源码包 `analysis/scope/` 对 Inventory 全量 File 执行一次的分类规则，产出 `overall_eligible`（Node ID 有效）与 `sql_eligible`（M2.3 输入）两个口径；正式产物统一归属 `analysis/scope/`：`inputs/sql-candidates.json`（`sql_eligible = true`）、`inputs/excluded-tasks.json`（`sql_eligible = false`）、`review-tasks.json`（弱证据待确认）与 `summary.{json,md}`。前两份互斥且合计 = 登记文件，被排除的对象仍完整保留在 `inventory/files.json`；规则发现（`scope/findings/`）尚未实现，不产出整改问题，Summary 标注 `status = not_implemented`、`count = 0`。Content 是否读取由 `content_check` 开关控制，未启用的格式状态为 `not_checked`（既非可用也非缺口，不阻断资格）。
_Avoid_: 删除清单、清理脚本、清理候选（`cleanup_candidate`）、失效资产（分类结果不授权任何删除或修改操作）

**Inventory Summary / Scope Summary（盘点报告 / 资格评估报告）**:
两份 `summary.md` 职责互斥：Inventory Summary 只报**事实**（文件登记、元数据完整性、内容快照状态、缺失 Node ID、资产覆盖），不出现资格判定、排除分类与规则命中；Scope Summary 承接全部**资格口径**（整体分析资格、SQL 分析范围、资格排除、弱证据待确认、规则命中、规则发现状态）。内容状态由 `scope/content.py::content_state_of()` 单点实现，两份报告共用同一口径。
_Avoid_: 在 Inventory 报告里谈「分析候选 / 资格排除」、两处各写一套内容状态统计

**Overlap / Duplication（重叠 / 重复）**:
Overlap 只表示字段与结构重合；Duplication 还要求共享 process 与共享 grain 签名。二者是两类问题，重合度不是删除依据。
_Avoid_: 把 overlap 说成重复表、可删除表

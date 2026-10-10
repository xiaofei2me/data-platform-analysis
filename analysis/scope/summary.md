# M2.1 分析范围规则分类（Scope Summary）

Scope 对 Inventory 全量登记文件执行一次 Analysis Scope Rules（version 1.0），
只消费资产、不修改资产；后续 Evidence / Understanding / Review
只消费判定结果，不在此重复过滤。本报告的每个数字都直接来自
FileScope.stats()，渲染层不重新执行资格判断。

## 1. 评估概览

| 口径 | 数量 | 占比 | 说明 |
| --- | ---: | ---: | --- |
| 登记文件 | 4,657 | 100.0% | 全部保留在 inventory/files.json |
| 整体分析资格 | 1,379 | 29.6% | overall_eligible = true；分析资格 ≠ 已分析（明细见第 2 节） |
| SQL 候选 | 541 | 11.6% | sql_eligible = true，见 scope/inputs/sql-candidates.json，进入 M2.3 |
| SQL 分析排除 | 4,116 | 88.4% | sql_eligible = false，见 scope/inputs/excluded-tasks.json；与 SQL 候选互斥且合计 = 登记文件 |
| 待确认 | 70 | 1.5% | 非正式任务弱证据，见 scope/review-tasks.json；独立维度，不与资格清单相加 |

两份资格清单互斥且合计等于登记文件；review-tasks.json 是独立的待确认维度，与两份资格清单都可以重叠，不参与上面的加总。

## 2. 整体分析资格

| 口径 | 数量 | 占比 | 说明 |
| --- | ---: | ---: | --- |
| 整体分析资格 | 1,379 | 29.6% | 身份有效且非明确非正式任务 |
| 未通过整体分析资格 | 3,278 | 70.4% | 构成见第 4 节「资格排除情况」 |

资格输入维度（资产事实，只列计数，不重复判定）：

| 维度 | 取值 | 数量 | 占比 |
| --- | --- | ---: | ---: |
| Node ID 状态 | valid（有效） | 1,379 | 29.6% |
| Node ID 状态 | missing（缺失） | 3,278 | 70.4% |
| 节点类型（task_type） | ASSIGNMENT | 14 | 0.3% |
| 节点类型（task_type） | BRANCH | 1 | 0.0% |
| 节点类型（task_type） | CHECK | 3 | 0.1% |
| 节点类型（task_type） | DO_WHILE | 3 | 0.1% |
| 节点类型（task_type） | FOR_EACH | 1 | 0.0% |
| 节点类型（task_type） | FUNCTION_COMPUTE | 9 | 0.2% |
| 节点类型（task_type） | ODPS_SQL | 2,826 | 60.7% |
| 节点类型（task_type） | OFFLINE_SYNC | 1,683 | 36.1% |
| 节点类型（task_type） | PARAM_HUB | 1 | 0.0% |
| 节点类型（task_type） | PYODPS2 | 2 | 0.0% |
| 节点类型（task_type） | PYODPS3 | 32 | 0.7% |
| 节点类型（task_type） | REALTIME_SYNC | 1 | 0.0% |
| 节点类型（task_type） | RESOURCE | 46 | 1.0% |
| 节点类型（task_type） | SHELL | 19 | 0.4% |
| 节点类型（task_type） | TASK_FLOW | 1 | 0.0% |
| 节点类型（task_type） | VIRTUAL | 15 | 0.3% |

## 3. SQL 分析范围

| 口径 | 数量 | 占比 | 说明 |
| --- | ---: | ---: | --- |
| SQL 候选 | 541 | 11.6% | M2.3 SQL Analysis 的唯一输入来源 |
| SQL 分析排除 | 4,116 | 88.4% | 只记录与分类，不删除、不禁用、不修改资产 |

阻断优先级：identity → informal → node_type → content，同一文件只取首个阻断原因；SQL 候选与 SQL 分析排除互斥且合计 = 登记文件。

SQL 资格原因分通过与阻断两类，互斥且合计 = 登记文件：

| 口径 | 原因 | 数量 | 占比 |
| --- | --- | ---: | ---: |
| SQL 通过原因 | SQL_ANALYSIS_ELIGIBLE | 541 | 11.6% |

| 口径 | 原因 | 数量 | 占比 |
| --- | --- | ---: | ---: |
| SQL 阻断原因 | NODE_ID_MISSING | 3,278 | 70.4% |
| SQL 阻断原因 | SQL_FORMAT_NOT_APPLICABLE | 838 | 18.0% |

## 4. 资格排除情况

| 口径 | 排除分类 | 数量 | 占比 |
| --- | --- | ---: | ---: |
| 资格排除 | 身份不满足（NodeId 缺失） | 3,278 | 70.4% |

排除分类描述的是整体分析资格（overall_eligible）的构成；SQL 层面的阻断原因见第 3 节，两者是不同维度，不能互相替代。

三个口径互不相同：规则命中数（第 7 节，可重叠）、最终排除分类数（本节上方表格，互斥）、分类主因数（本节下方表格，互斥）。同一文件可能命中多条规则，但只属于一个排除分类、只有一个分类主因；本节数字不能由命中数相减推导，均直接来自文件级判定结果。

排除 ≠ 删除：命中任何规则都只记录与分类，不调用 DataWorks 删除 / 禁用 / 修改接口，被排除的对象仍完整保留在 `inventory/files.json`。

分类主因（互斥，每个文件只计一次，合计 = 登记文件）：

| 口径 | 原因 | 数量 | 占比 |
| --- | --- | ---: | ---: |
| 分类主因 | CONTENT_PRESENT | 541 | 11.6% |
| 分类主因 | NODE_ID_MISSING | 3,278 | 70.4% |
| 分类主因 | SQL_FORMAT_NOT_APPLICABLE | 838 | 18.0% |

## 5. 弱证据待确认

| 口径 | 数量 | 占比 | 说明 |
| --- | ---: | ---: | --- |
| 待确认 | 70 | 1.5% | 命中弱证据规则（如 INFORMAL_TASK_WEAK），见 scope/review-tasks.json |

弱证据只标记 review_required：不改变 overall_eligible，也不改变 sql_eligible，不计入确定排除；可与 SQL 候选或 SQL 分析排除同时存在，需人工复核。

## 6. 内容状态与内容期望

| 维度 | 取值 | 数量 | 占比 | 含义 |
| --- | --- | ---: | ---: | --- |
| 内容状态 | present | 2,826 | 60.7% | Content 可读且非空白 |
| 内容状态 | not_checked | 1,831 | 39.3% | 未启用 Content 检查的格式，不读 Snapshot、不计为缺口 |
| 内容状态 | empty_text | 0 | 0.0% | Content 文件存在但内容为空白 |
| 内容状态 | not_collected | 0 | 0.0% | content_file 为空，采集结果事实 |
| 内容状态 | path_missing | 0 | 0.0% | content_file 指向的文件在 Snapshot 中不存在 |
| 内容状态 | read_error | 0 | 0.0% | Content 存在但读取失败 |
| 内容期望 | 缺口 · 类型不要求 | 0 | 0.0% | 该类型预期不需要 Content，属正常形态 |
| 内容期望 | 缺口 · 类型要求 | 0 | 0.0% | 该类型预期需要 Content，记录内容缺失原因 |
| 内容期望 | 缺口 · 期望未知 | 0 | 0.0% | content_format 未登记，不猜测内容期望 |
| 内容期望 | 期望未知（全部） | 0 | 0.0% | 含 Content 可读的对象，仍不推断类型语义 |

内容状态六行互斥，合计等于登记文件（not_checked 未启用 Content 检查，既不计入可用也不计入缺口）；内容期望是对缺口对象的第二维度，与状态行可能重叠，不参与合计。同一组状态也出现在 Inventory Summary 第 5.4 节，两边共用 analysis/scope/content.py 的同一实现，数字必然一致。

## 7. 规则命中（可重叠）

| 规则 | 类型 | 说明 | 命中数 |
| --- | --- | --- | ---: |
| NODE_ID_MISSING | node_identity | NodeId 缺失（None 或空白字符串），无法定位已提交的调度节点。 | 3,278 |
| INFORMAL_TASK_STRONG | informal_task | 文件名整体命中 informal token，判定为明确的测试 / 临时 / 演示任务。 | 24 |
| INFORMAL_TASK_WEAK | informal_task | 文件名 token 命中 informal 词但名称仍含业务结构，标记为待确认。 | 70 |
| CONTENT_PRESENT | content_state | Content 在 Snapshot 中可读且非空白。 | 2,826 |
| CONTENT_GAP_NOT_REQUIRED | content_state | Content 缺失，但该节点类型不要求 Content（虚拟 / 控制流节点属正常形态）。 | 0 |
| CONTENT_GAP_REQUIRED | content_state | Content 缺失，但该节点类型预期需要 Content，记录内容缺失原因。 | 0 |
| CONTENT_EXPECTATION_UNKNOWN | content_state | Content 缺失且节点类型的内容期望未知，保持 unknown，不猜测。 | 0 |
| SQL_BLOCKED_BY_IDENTITY | sql_eligibility | 节点身份不成立，不适合作为 SQL 分析输入。 | 3,278 |
| SQL_BLOCKED_BY_INFORMAL | sql_eligibility | 明确的非正式任务不进入正式业务 SQL 分析。 | 0 |
| SQL_BLOCKED_BY_TYPE | sql_eligibility | 节点类型 / content_format 不适用 SQL 分析（不代表不适用于其他分析）。 | 838 |
| SQL_BLOCKED_BY_CONTENT | sql_eligibility | 格式适用 SQL，但 Content 当前不可用，无法作为 SQL 分析输入。 | 0 |
| SQL_ANALYSIS_ELIGIBLE | sql_eligibility | 节点身份有效、非非正式任务、content_format 适用 SQL 且 Content 可用。 | 541 |

同一文件可能命中多条规则，命中数之和大于等于对象数；第 4 节的分类主因分布每个文件只计一次。

其中 24 个命中会排除整体资格的 informal 规则（如 INFORMAL_TASK_STRONG）的文件同时被 identity 分类排除（exclusion_class = identity，身份排除优先），因此不出现在第 4 节的非正式任务排除行中。

## 8. 规则发现及实现状态

| 项目 | 状态 / 数量 | 说明 |
| --- | --- | --- |
| findings.status | not_implemented | `scope/findings/` 尚未实现，如实标注而不是省略该字段 |
| findings.count | 0 | 未实现 = 无发现产物，不能解释为「已检查、无问题」 |

当前规则只做资格分类与审核标记，不产出整改问题，因此不生成发现产物；本行与 `scope/summary.json` 的 `findings.status` 共用同一常量，两边不会不一致。

## 9. 产物与边界

- `scope/inputs/sql-candidates.json`：通过 SQL 分析资格（sql_eligible = true）的资产，M2.3 SQL Analysis 的候选输入；
- `scope/inputs/excluded-tasks.json`：未通过 SQL 分析资格（sql_eligible = false）的资产，记录 workspace_id + file_id、命中规则与原因代码；
- `scope/review-tasks.json`：非正式任务弱证据的待确认资产，不计入确定排除，也不改变 sql_eligible；
- `scope/summary.json`：本报告的机器可读统计（同一份 FileScopeStats）；
- 三份清单都是分析范围判定的产物，不是删除、禁用或修改 DataWorks 资产的指令；前两份互斥且合计覆盖全部登记文件；
- 排除分类 ≠ 无效资产：被排除的对象仍完整保留在 `inventory/files.json`；
- 规则发现（`scope/findings/`）状态见第 8 节，如实标注为 not_implemented，不虚构发现数量。

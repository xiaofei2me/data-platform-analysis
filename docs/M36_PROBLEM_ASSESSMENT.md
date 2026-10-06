# M3.6 v2 Problem Assessment 方法论

面向未参与开发的读者：本文档说明 `M3.6 → M3.6 v2 → Human Adjudication → Refactoring Evidence → M4` 的完整链路、Finding 与 Problem 的方法论、13 类 Problem Taxonomy、四条不可违反的原则、人工裁决流程与重构证据要求。读完本文即可开始人工裁决 `current-state-problem-review-checklist.md`，而不必先读代码。

- 代码实现：`src/data_platform_analysis/analysis/problem_assessment.py`（v2）、`analysis/model_review.py`（M3.6）、常量与契约在 `analysis/models.py`
- 阶段逻辑分析：[docs/CODE_LOGIC_ANALYSIS.md](CODE_LOGIC_ANALYSIS.md) §3.14、§4 产物地图、§8 局限（第 13、14 条）
- 命令：`uv run data-platform-analysis analyze-current-state-model`（M3.6 与 v2 同一次运行，写出 9 个产物）
- 数据基准：本仓库 `analysis/` 的当前快照（3719 张表、4439 条 finding、1190 条 problem）

---

## 一、阶段链路总览

```
当前数据平台（DataWorks + MaxCompute，source/ 时点快照）
        ↓
   M3.1  Business Understanding        Domain / Object 候选 + 术语
        ↓
   M3.2  Object & Relationship         Object ↔ Table ↔ 关系证据结构
        ↓
   M3.3  Process                       Process Candidate + 六类过程信号
        ↓
   M3.4  Grain                         Grain Candidate + 七类粒度信号
        ↓
   M3.5  Business Model                Fact / Dimension Candidate + 关系候选
        ↓
   M3.6  Current-State Model Review    当前形态分类 + 18 类 Finding（逐条观测）
        ↓
   M3.6 v2 Problem Assessment          Finding 聚合为 13 类 Problem candidate
        ↓
   Human Adjudication                  人工裁决：candidate → confirmed / rejected
        ↓
   Refactoring Evidence                重构证据矩阵（问题 → 证据 → 根因 → 方向）
        ↓
   M4  Target Model                    Target DWD Design（尚未开始）
```

**编号对照（两套编号必须分清）**：上图采用阶段任务书的编号；本仓库代码与 `docs/` 使用另一套编号，二者只差一个 M3.1 Quality：

| 任务书编号 | 本仓库编号 | 阶段 | 主产物 |
| --- | --- | --- | --- |
| M3.1 | **M3** | Business Understanding | `business/tables.json`、`business/summary.md` |
| （无，任务书未列） | **M3.1** | Quality Assessment（只评估不识别） | `business/quality-assessment.{json,md}`、`review-checklist.md` |
| M3.2 | **M3.2** | Object & Relationship | `objects-registry.json`、`object-relationships.json`、`object-graph.md` |
| M3.3 | **M3.3** | Process | `processes.json`、`process-summary.md`、`process-review-checklist.md` |
| M3.4 | **M3.4** | Grain | `grain-candidates.json`、`grain-summary.md`、`grain-review-checklist.md` |
| M3.5 | **M3.5** | Business Model（Fact / Dimension Candidate） | `fact-candidates.json`、`dimension-candidates.json`、`model-review-checklist.md` |
| M3.6 | **M3.6** | Current-State Model Review | `current-state-model*.json`、`model-review-findings.json`、`current-state-review-checklist.md` |
| M3.6 v2 | **M3.6 v2** | Problem Assessment | `current-state-problems.json`、`current-state-problem-evidence.json`、`current-state-problem-summary.md`、`current-state-problem-review-checklist.md` |

除 M3.1 Quality 外，两套编号在 Object 及之后完全一致。本文以下一律使用仓库编号。

链路上的每个阶段都遵守同一条铁律：**只产出候选、证据与评审发现，不产出结论模型**。M3.6 v2 的目的不是设计新模型，而是**证明当前模型存在哪些值得重构的问题，并为每个问题提供可追溯的证据**。

## 二、M3.6 与 M3.6 v2 的分工

| | M3.6 Current-State Model Review | M3.6 v2 Problem Assessment |
| --- | --- | --- |
| 产出单位 | **Finding**（逐条观测） | **Problem**（同一根因下的聚合候选问题） |
| 粒度 | 一条 finding 观察一个现象 | 一个问题聚合若干条 finding |
| 类型 | 18 类 finding | 13 类 problem |
| 实测数量 | 4439 | 1190 |
| 载体 | `model-review-findings.json` + `current-state-review-checklist.md`（5 个分区） | `current-state-problems.json` + `current-state-problem-review-checklist.md`（13 个分区） |
| 回答的问题 | 现在的模型长什么样、有哪些结构现象 | 这些现象里**哪些值得改、证据够不够、先改什么** |
| 边界 | 只评审不改模 | 只评审不改模，不设计 Target DWD |

两者共用一条命令 `analyze-current-state-model`：同一次运行先写 5 个 M3.6 产物，再把 finding 聚合成 problem，追加 4 个 v2 产物，合计 9 个。v2 只读本次 M3.6 的 finding 与表级行 + 同一批 13 个上游产物，不读 `source/`、profiling、SQL 参考，不调 LLM / 外部 API，不改写任何已有产物。

13 个上游输入（只读）：`business/fact-candidates.json`、`dimension-candidates.json`、`fact-dimension-relationships.json`、`fact-tables.json`、`dimension-tables.json`、`grain-candidates.json`、`processes.json`、`objects-registry.json`、`inventory/tables.json`、`inventory/columns.json`、`lineage/table-lineage.json`、`lineage/core-table-candidates.json`、`layer/assessments.json`；另有可选回填文件 `business/current-state-problem-review-checklist.md`。

---

## 三、Finding 与 Problem 的方法论

### 3.1 定义

| | Finding | Problem |
| --- | --- | --- |
| 是什么 | 对当前模型的一次**结构观测**，机器可复算 | 若干条同根因 finding 聚合后的**候选问题** |
| 例 | `grain_conflict`：这张表的候选键与落表不一致 | `GRAIN_PROBLEM`：这张表的行级含义不唯一，需要人工定粒度 |
| 是否含判断 | 否，只描述现象并提出人工问题 | 否，含「问题陈述 + 证据 + 影响 + 根因 + 重构理由」，仍待人工确认 |
| 状态 | `candidate`（回填前恒为 candidate） | `candidate` / `review_required`（机器只写这两个） |

### 3.2 三个计数永远不相等

```
Finding Count (4439)  ≠  Problem Count (1190)  ≠  Confirmed Problem Count (0)
```

- **4439 → 1190**：同一张表的多条粒度 finding 聚合成 1 条 `GRAIN_PROBLEM`；字段重合的表对先 union-find 成分量、再落成 1 条 `MODEL_OVERLAP` / `MODEL_DUPLICATION`；聚合表按 `(process, assessment)` 分组。**计数下降是聚合，不是删除。**
- **1190 → 0**：`confirmed` 只能由 `current-state-problem-review-checklist.md` 人工回填产生，机器永远不会写。今天打开任何产物看到的 confirmed 都是 0，这是设计结果，不是数据缺失。
- **反向也可能发生**：一条 finding 可以进入多条 problem（例如同一张表既进 `GRAIN_PROBLEM` 又进 `MIXED_RESPONSIBILITY`），因此**问题数不是 finding 数的任何简单比例**。

### 3.3 Finding 覆盖账目

`current-state-problems.json` 的 `finding_coverage` 字段记录账目：本轮 **4427 / 4439** 条 finding 进入了 problem，未进入的 **12 条全部是 `aggregate_fact`**。原因见 §5.3：它们被评估为 `valid_aggregate`（有原子事实上游、无重复），**有意不产生问题**。覆盖不到 100% 是正确行为，不是漏算。

### 3.4 聚合维度（scope）

| scope | 含义 | 实测条数 |
| --- | --- | --- |
| `table` | 一张表一个问题 | 786 |
| `table_set` | 一组表（连通分量 / 重复组 / UNKNOWN 桶） | 346 |
| `process` | 一个 process 候选一个问题 | 47 |
| `dimension` | 一个 Object 的角色问题 | 4 |
| `stage` | 全阶段级问题（Fact Gate 排除、语义证据不足） | 7 |

同一 scope 内以 `canonical_signature = problem_type|scope|scope_key` 唯一编号（`problem_0001` 起），展示按 priority → problem_type → scope → scope_key 稳定排序。

---

## 四、13 类 Problem Taxonomy

固定顺序即 `PROBLEM_TYPE_ORDER`（报告与清单的分区顺序）；**没有证据支撑的类型不产生问题**。每类固定回答 7 个问题：① 解决什么 ② 触发依据 ③ scope ④ evidence ⑤ 为何可能是问题 ⑥ 为何不等于错误 ⑦ 人工要判断什么。

### 4.1 GRAIN_PROBLEM 粒度问题（559 条）

1. **解决什么**：一张表呈现多组候选键 / 多种 grain 形态，行级含义不唯一，指标口径无法锁定。
2. **触发依据**：M3.6 粒度类 finding `grain_conflict`（559）、`mixed_grain`（130）、`snapshot_periodic_ambiguous`（0）的表级 scope_key；该表必须有 grain candidate，否则不产出（Evidence First）。
3. **scope**：`table`（一表一问题，不同表不合并）。
4. **evidence**：TABLE（1 条）+ GRAIN（每个 grain candidate 1 条，含 pattern 与候选键）+ PROCESS（归属）+ COLUMN（候选键字段）+ FINDING（粒度类 finding）。
5. **为何可能是问题**：多组键意味着同一张表可被解读成多种行级口径，下游可能重复计数或漏计。
6. **为何不等于错误**：候选键由字段名形态级联推出，无行级样本（Profiling 全是 `metadata_only`）；分类只有 `confirmed_conflict`（键互不包含，548）与 `possible_conflict`（互为子集，11）两级，559 条全部 `strong`、全部 `candidate`——它说明「候选键不唯一」，不说明「这 559 张表都要改」。
7. **人工要判断**：该表唯一的业务粒度是哪一组键？其余 grain candidate 作废还是并存？哪些 `possible_conflict` 实为同一键的大小写 / 顺序差异？

### 4.2 MODEL_OVERLAP 模型重叠（27 条）

1. **解决什么**：字段与结构高度重合的表簇，需要人判断它们是不是同一逻辑模型的多份表达。
2. **触发依据**：`overlapping_fact` finding（2605 条表对）经 union-find 连通分量；分量内**不同时**满足「共享 process + 共享 grain 签名」时归入 OVERLAP（否则是 DUPLICATION）。
3. **scope**：`table_set`（scope_key = 分量内表名排序后 `|` 连接）。
4. **evidence**：TABLE（每表 1 条，含字段数）+ PROCESS + GRAIN（共享签名样例）+ LINEAGE（分量内部血缘边）+ COLUMN（最优对共享字段，带 Jaccard）+ FINDING（字段重合 finding）。
5. **为何可能是问题**：取数需要在多个相似模型之间选择，口径容易漂移。
6. **为何不等于错误**：机器只证明字段与结构重合，**不判断哪张是权威版本**；大宽表之间的高重合可能源于同源复制或有意的分区副本，`structural_overlap`（17）与 `technical_copy_candidate`（10）都只是分类，不是判决。
7. **人工要判断**：这 N 张表是否同一逻辑模型的多份表达？权威表是哪一张？先收敛哪一张？

### 4.3 MODEL_DUPLICATION 模型重复（317 条）

1. **解决什么**：同一逻辑事实的候选落在多张表上，存在重复建模与重复计数风险。
2. **触发依据**：两条路径——① 连通分量内**同时**共享 process 与共享 grain 签名的重复组（`duplication_candidate`，108）；② 连通分量之外的 `duplicate_fact` 组（489 条 finding，去重后 `grain_identical_structure_divergent`，122）。另有跨层或 Jaccard ≥0.9 的 `technical_copy_candidate`（87）。
3. **scope**：`table_set`。
4. **evidence**：TABLE + GRAIN + PROCESS + LINEAGE（判断是否技术副本）+ COLUMN（共享字段与 Jaccard）+ FINDING（`duplicate_fact`）。
5. **为何可能是问题**：同一业务口径存在多份表达与多条加工链路，维护成本与选错模型的概率同步上升。
6. **为何不等于错误**：机器不判断权威版本；「结构分歧」可能来自有意的区域 / 渠道副本。重叠 ≠ 重复，重复 ≠ 可删（见 §5.1）。
7. **人工要判断**：权威表是哪一张？哪些是副本、哪些是独立口径？收敛顺序是什么？

### 4.4 MIXED_RESPONSIBILITY 职责混杂（204 条）

1. **解决什么**：一张表同时承担多种模型职责，无法用单一职责描述它。
2. **触发依据**：表级职责信号 ≥2 个，或命中自足信号（`WIDE` / `RESULT` 单信号即构成），且该表有形态类 finding（`aggregate_fact` / `mixed_grain` / `result_table` / `wide_analytical_table`）。信号口径固定为 `DIMENSION`、`AGGREGATE`、`MIXED_GRAIN`、`PERIODIC_FACT`、`SNAPSHOT_FACT`、`WIDE`、`RESULT`；**`FACT` 是基线角色，不算信号**（否则所有聚合事实都会被判成混杂）。
3. **scope**：`table`。
4. **evidence**：TABLE（含 model_shape / roles / signals）+ FINDING（形态类）+ PROCESS + GRAIN（≤5 条样例）。
5. **为何可能是问题**：职责边界不清的表在改造时难以归位，拆分与合并都缺少依据。
6. **为何不等于错误**：信号来自当前平台已存在的形态（M3.6 的 `model_shape` / `current_roles`），是描述不是评价；`PERIODIC_FACT` 142、`AGGREGATE` 164、`MIXED_GRAIN` 130、`WIDE` 39、`RESULT` 37、`SNAPSHOT_FACT` 3（信号可共存）。
7. **人工要判断**：该表实际承担哪一种职责？是否需要拆分？拆分边界在哪里？

### 4.5 MODEL_ROLE_AMBIGUITY 角色歧义（4 条）

1. **解决什么**：一个 Object 的模型角色未解析，M4 无法确定它的建模位置。
2. **触发依据**：`role_ambiguous` finding（4 条）。
3. **scope**：`dimension`（scope_key = Object key）。
4. **evidence**：沿用 finding 的证据链（`_finding_evidence` 原样搬运）。
5. **为何可能是问题**：同一对象既被当维度又被其它角色引用，会让事实与维度的边界出现双解。
6. **为何不等于错误**：角色来自锚点关系的推导，不是业务定义；4 条全部证据类型 ≤2 → `weak` → 状态自动抬为 `review_required`，正是「证据不足，必须人工看」的信号。
7. **人工要判断**：该 Object 的唯一模型角色是什么？谁有资格裁决它？

### 4.6 PROCESS_MODEL_ALIGNMENT 过程与模型对齐（15 条）

1. **解决什么**：过程职责与模型粒度没有对齐关系。
2. **触发依据**：`multi_process_table` finding（0 条，表 scope）+ `process_multiple_grains` finding（15 条，process scope）；本轮 15 条全部来自后者。
3. **scope**：`table`（表被多过程共用）或 `process`（过程内多粒度）；本轮全为 `process`。
4. **evidence**：FINDING + TABLE（该 process 下带 grain 候选的表）+ PROCESS。
5. **为何可能是问题**：过程与模型没有唯一对应，目标模型不知道该按哪个过程的口径建。
6. **为何不等于错误**：process 本身是候选（`processes.json` 全部 `candidate`、`human_validated` = 0），过程分组由 Object 集合精确匹配得到，同一 Object 会出现在多个 candidate 中；15 条 priority 全为 P3（来自 finding 的 `process_multiple_grains` = P3），`moderate`，说明它是「待对齐」而非「已错配」。
7. **人工要判断**：这张表归属哪个 process、是否应共享？该 process 内多粒度表如何对齐？

### 4.7 AGGREGATION_MODEL_PROBLEM 聚合模型问题（22 条）

1. **解决什么**：聚合表的上游原子事实来源未确认，聚合口径无法回溯。
2. **触发依据**：有 `aggregate_fact` finding 的表，评估结果 ≠ `valid_aggregate`——`model_problem`（有 `grain_conflict` / `mixed_grain`，或落在 `duplicate_fact` 组内，13 条）或 `review_required`（血缘里找不到 fact-anchor 上游，9 条）；**`valid_aggregate` 不发问题**（见 §5.3）。
3. **scope**：`process`（按首 process 分组；本轮 22 条全为 process scope，无 process 的表退化为 `table` scope）。
4. **evidence**：TABLE（含 assessment 与字段数）+ PROCESS + GRAIN（上游粒度）+ FINDING（`aggregate_fact`）。
5. **为何可能是问题**：口径无法回溯到原子事实，指标复核与重新计算都缺少依据。
6. **为何不等于错误**：聚合层本身是合法形态；只有「无事实上游 + 自身带粒度或重复问题」才是 `model_problem`。`review_required` 的 9 条只说明血缘证据不够。
7. **人工要判断**：这些聚合表的上游事实是什么？聚合口径能否回溯到原子事实？该聚合层是否应保留？

### 4.8 FACT_IDENTIFICATION_PROBLEM 事实识别问题（26 条）

1. **解决什么**：Fact Gate 把一部分表排除在事实模型之外，事实覆盖存在缺口。
2. **触发依据**：两条路径——① Fact Gate 排除项按 `grain_pattern` 分组（`fact_gate_no_measure` 3 条 finding → 3 条 stage 问题，patterns = `aggregation` / `periodic` / `unknown`）；② `fact_without_measure` finding 按表（50 条 finding → 23 条 table 问题）。
3. **scope**：`stage`（闸门口径）或 `table`（单表缺度量）。
4. **evidence**：stage 侧沿用 finding 证据 + 被排除的 GRAIN / TABLE / PROCESS；table 侧 TABLE（含 `measure_count`）+ FINDING。
5. **为何可能是问题**：事实识别依赖显式 measure 字段，缺度量的表可能被漏建。
6. **为何不等于错误**：闸门结论 ≠ 业务结论（见 §5.4）。stage 侧 3 条 `moderate` / `candidate` / P0，table 侧 23 条 `weak` / `review_required` / P1——后者证据类型少，正是「机器不敢下结论」的体现。
7. **人工要判断**：被闸门排除的表是否仍应作为事实？没有 measure 字段的表，度量在哪里计算？

### 4.9 DIMENSION_IDENTIFICATION_PROBLEM 维度识别问题（1 条）

1. **解决什么**：维度候选的定义来自 Object 派生证据，而非显式维度表声明，维度边界与权威来源未确认。
2. **触发依据**：`dimension_object_derived` finding（1 条）。
3. **scope**：`stage`。
4. **evidence**：finding 自带证据链。
5. **为何可能是问题**：维度来源不是显式声明，目标维度模型的边界会漂。
6. **为何不等于错误**：Object 派生是 M3.2 的既定方法（证据结构而非语义识别）；1 条 `weak` / `review_required`，说明证据薄而不是维度错。
7. **人工要判断**：该 Object 是否构成正式维度？权威来源是哪张表？

### 4.10 MODEL_SELECTION_AMBIGUITY 模型选择歧义（8 条）

1. **解决什么**：同一 process 下重复模型过多，模型选择没有唯一入口，消费者只能靠猜。
2. **触发依据**：同一 process 下重复组（`MODEL_DUPLICATION` 问题）数量 ≥ **10**（`SELECTION_AMBIGUITY_MIN_DUPLICATION` = 10）。
3. **scope**：`process`。
4. **evidence**：PROCESS（N 个重复组落在该 process）+ TABLE（重复组涉及的表）+ FINDING（重复组 finding）+ GRAIN（该 process 的 grain 样例 ≤5）。
5. **为何可能是问题**：选择成本与选错概率随重复组数量超线性上升。
6. **为何不等于错误**：它是 `MODEL_DUPLICATION` 的**派生视图**（8 条全部 P1 / strong / candidate），重复组本身仍待裁决；阈值 10 是常量，不是业务定律。
7. **人工要判断**：该 process 的 N 个重复组应收敛成几个模型？权威入口是哪个？

### 4.11 SEMANTIC_AMBIGUITY 语义歧义（3 条）

1. **解决什么**：关系与强度结论只由技术引用或共现证据支撑，缺少业务语义证据，语义结论存在误读风险。
2. **触发依据**：`evidence_strength_semantics`（1）、`relationship_technical_only`（1）、`relationship_object_co_occurrence`（1）三类 finding。
3. **scope**：`stage`。
4. **evidence**：finding 自带证据链。
5. **为何可能是问题**：把技术引用当业务关系读，会让语义层建立在错误的关联上。
6. **为何不等于错误**：技术证据是当前唯一可用证据（血缘 / SQL 参考），缺的是业务语义补强；3 条全 `weak` / `review_required` / P1。
7. **人工要判断**：只有技术引用或只有共现证据的关系，能否算业务关系？需要补什么业务证据？

### 4.12 MODEL_COVERAGE_GAP 过程覆盖缺口（2 条）

1. **解决什么**：过程存在，但没有任何事实进入模型——要么事实被闸门排除，要么事实识别存在缺口。
2. **触发依据**：`processes.json` 里的 process（按 `process_key`，缺失回退 `process_candidate_id`）没有任何 fact candidate。
3. **scope**：`process`。
4. **evidence**：PROCESS（无 fact candidate）+ GRAIN（未产出 fact 的 grain 样例）+ TABLE（带 grain 候选的表）。
5. **为何可能是问题**：目标模型可能静默遗漏一整个业务过程。
6. **为何不等于错误**：`root_cause` 恒为 `UNKNOWN`——证据只说明「没有事实进入模型」，不说明「这个过程不该有事实」；2 条 `moderate` / P0 / candidate，`affected_table_count` 合计仅 4。
7. **人工要判断**：这个 process 真的没有事实需要建模吗？它的事实应该来自哪里？

### 4.13 UNKNOWN_MODEL 未定模型（2 条）

1. **解决什么**：一批表既没有事实 / 维度锚点，也没有足够血缘证据，是否属于可建模范围当前无法判定。
2. **触发依据**：`current_role == UNKNOWN` 的表（2041 张）按原因分桶：`NO_ANCHOR`（无锚点且无血缘入边 / 出边，463 张）、`NO_EVIDENCE`（有血缘但不足以判定角色，1578 张）。
3. **scope**：`table_set`（scope_key = reason）。
4. **evidence**：TABLE（含 reason 与字段数）+ LINEAGE（仅有血缘的表）。
5. **为何可能是问题**：范围归属不明确时，目标模型会静默遗漏或错误纳入这些表。
6. **为何不等于错误**：UNKNOWN 是合法结果，不是「坏模型」标签（见 §5.2）；两条均 `weak` / `review_required` / P2，证据只有 1–2 类。
7. **人工要判断**：这些表是否属于可建模的业务模型范围？纳入 / 排除 / 补证据，如何处置？

---

## 五、四条不可违反的原则

### 5.1 Overlap ≠ Duplication

字段与结构重合（overlap）只证明「长得像」；重复（duplication）还要求「共享 process + 共享 grain 签名」。二者用 `MODEL_OVERLAP` 与 `MODEL_DUPLICATION` 两个类型分开表达，并用 `classification` 进一步细分：

| classification | 含义 | 实测 |
| --- | --- | --- |
| `structural_overlap` | 结构重合，未满足重复条件 | 17 |
| `duplication_candidate` | 共享 process 与 grain 签名的重复候选 | 108 |
| `technical_copy_candidate` | 跨层 + 血缘方向或 Jaccard ≥0.9，疑似技术副本 | 97（OVERLAP 10 + DUPLICATION 87） |
| `grain_identical_structure_divergent` | 重复组未进连通分量、结构已分歧 | 122 |

**禁止**：把 `MODEL_OVERLAP` 直接说成「重复表」，把重合度当删除依据。

### 5.2 UNKNOWN ≠ BAD MODEL

UNKNOWN 有两个互不替代的解释，**不得为了让 UNKNOWN 归零而强制分类**：

- `NO_ANCHOR`：没有事实 / 维度锚点，也没有血缘入边 / 出边（463 张）——问题在**证据覆盖**。
- `NO_EVIDENCE`：有血缘但仍不足以判定角色（1578 张）——问题在**证据强度**。

正确处置是人工决定「纳入 / 排除 / 补证据」，而不是把 UNKNOWN 改写成 FACT 或 DIMENSION。`UNKNOWN_MODEL` 问题的 `root_cause` 在 `NO_ANCHOR` 侧写 `INSUFFICIENT_BUSINESS_MODEL_STANDARDIZATION`、在 `NO_EVIDENCE` 侧写 `UNKNOWN`，都是刻意保留的不确定表达。

### 5.3 Aggregate Fact ≠ Problem

聚合事实是合法形态，不是问题。`_aggregate_assessment()` 的三态：

- **`valid_aggregate`**：血缘里 ≥1 个 fact-anchor 上游，且自身无粒度 / 重复问题 → **不产生 problem**。本轮 12 条 `aggregate_fact` finding 落在这里，正是 `finding_coverage` 4427 / 4439 的全部差额。
- **`review_required`**：找不到事实上游 → 证据不足，状态抬为 `review_required`（9 条）。
- **`model_problem`**：自身带 `grain_conflict` / `mixed_grain` 或落在重复组内（13 条）。

**禁止**：把「存在聚合表」写成问题，把 `valid_aggregate` 强行纳入 problem 清单。

### 5.4 Fact Gate Failure ≠ Fact Invalid

Fact Gate 复算（`current-state-model.json` → `fact_gate_review`）：

| 指标 | 值 |
| --- | --- |
| qualified_count | **3364** |
| rejected_count | **2315** |
| rejected_reason_counts | `no_measure_evidence` = **2315**（唯一原因） |
| matches_m35 | `true`（与 M3.5 闸门一致） |
| gate_rule | transaction / event / snapshot 直接通过；periodic / aggregation / unknown 必须有 `measure_columns` |

2315 条全部是 `no_measure_evidence`——**「没有显式度量证据」不是「不是事实」**。本阶段只复算并评审，不修改闸门、不改写 M3.5 结果；被排除表是否仍是事实，由 `FACT_IDENTIFICATION_PROBLEM` 交给人工裁决。

**禁止**：把 `rejected_count` 说成「2315 张非事实表」。

---

## 六、M3.6 → M4 Decision Boundary

**本阶段（M3.6 + v2）允许做的事**：

- 对当前模型做形态分类与结构评审，产出 finding 与 problem candidate
- 为每个 problem 建立 `Problem → Evidence → Impact → Root Cause → Why Change → Human Decision` 证据链
- 给出 priority / severity / strength，供人工排定裁决与改造顺序
- 输出两份人工清单（finding 5 分区、problem 13 分区），作为唯一回填入口
- 把「机器已确认的边界」写清楚：什么没证据、什么待人工

**本阶段明确不做的事（M4 之前一律禁止）**：

- 不设计 Target DWD / DWS / Semantic Layer，不出 DDL，不产出目标表名与字段设计
- 不合并 / 不拆分 / 不删除 / 不改名任何表，不自动决定权威表与收敛顺序
- 不自动裁决粒度、事实与维度归属；不把 candidate 改写为 confirmed
- 不调 LLM / 外部 API，不引入人工业务知识，不按表名断言业务事实
- 不把 SQL JOIN 等同业务关系，不把 finding 与 problem 的未决状态互相替代
- 不改写上游 13 个输入产物与 M3.6 已有 5 个产物

**进入 M4 的前置条件**：

1. `current-state-problem-review-checklist.md` 中 `priority` = P0 / P1 的行完成回填，`confirmed` / `rejected` 不再为 0
2. `current-state-review-checklist.md`（finding 侧）同步回填——两个清单**各自独立**，一个完成不等于另一个完成
3. 权威表、收敛顺序、粒度唯一键、UNKNOWN 表范围归属这四类判断由人给出
4. 重构证据矩阵（§十）逐行填完 `Human Decision` 列

**在上述条件满足前，任何「按 problem 清单直接设计 DWD」的做法都越界。**

---

## 七、Human Adjudication（人工裁决）

### 7.1 生命周期

```
机器阶段                          人工阶段
─────────                        ─────────
candidate ────────────────────→  confirmed（人工确认这是真问题）
   │                             rejected （人工否决，证据不成立）
   ├─ weak 证据 ────────────────→ （自动抬为）
   ├─ GRAIN/AGGREGATION 判 review_required ─→ review_required（必须人看）
   └──────────────────────────   pending / needs_review（尚未裁决或待讨论）
```

**机器只写 `candidate` 与 `review_required`；`confirmed` / `rejected` 只能由清单回填产生。** 当前 1190 条 problem = candidate 1148 + review_required 42 + confirmed 0 + rejected 0。

42 条 `review_required` 的来源（合计 = 23 + 9 + 4 + 3 + 1 + 2）：

| 来源 | 条数 |
| --- | --- |
| `FACT_IDENTIFICATION_PROBLEM` 表级（weak） | 23 |
| `AGGREGATION_MODEL_PROBLEM`（classification = `review_required`） | 9 |
| `MODEL_ROLE_AMBIGUITY`（weak） | 4 |
| `SEMANTIC_AMBIGUITY`（weak） | 3 |
| `DIMENSION_IDENTIFICATION_PROBLEM`（weak） | 1 |
| `UNKNOWN_MODEL`（weak） | 2 |

### 7.2 唯一回填入口

清单文件：`analysis/business/current-state-problem-review-checklist.md`，按 13 类分区，每区 ≤50 行并注明总数（全量见 `current-state-problems.json`）。

固定 10 列（`PROBLEM_CHECKLIST_HEADERS`）：`problem_id`、`problem_type`、`priority`、`scope_key`、`evidence`、`system_interpretation`、`human_question`、`human_status`、`human_name`、`note`。

回填只需填后 4 列；缺 `problem_id` / `human_status` / `human_name` / `note` 任一列即报错退出（退出码 1）。

### 7.3 状态映射

| 清单 `human_status` | 问题 `status` | `human_validated` |
| --- | --- | --- |
| `pending`（默认未回填） | `candidate`（或机器判的 `review_required`） | false |
| `confirmed` | `confirmed` | **true** |
| `rejected` | `rejected` | false |
| `needs_review` / `needs_discussion` | `review_required` | false |
| 无法识别的取值 | 按未回填处理（记 warning） | false |

只有 `confirmed` 才算人工已裁决（与 M3.6 finding 口径一致）。回填结果在重跑时原样带回（carry-over），人工三列永不被机器覆盖。

### 7.4 两个清单，各自独立

| 清单 | 裁决对象 | 分区 | 回填状态 |
| --- | --- | --- | --- |
| `current-state-review-checklist.md` | 4439 条 finding | 5 个 review group | 157 行全部 `pending` |
| `current-state-problem-review-checklist.md` | 1190 条 problem | 13 类 | 13 区全部 `pending` |

**finding 裁决与 problem 裁决互不替代**：确认一条 finding 不会把对应 problem 变成 confirmed，反之亦然。

---

## 八、人工裁决优先级

### 8.1 三档优先级建议

| 档 | 类型 | 条数 | 理由 |
| --- | --- | --- | --- |
| **P0（先裁决）** | `GRAIN_PROBLEM`、`MODEL_ROLE_AMBIGUITY`、`MODEL_COVERAGE_GAP`（类型默认 P0），外加被 finding 抬到 P0 的 `MIXED_RESPONSIBILITY` 130 条与 `FACT_IDENTIFICATION_PROBLEM` stage 侧 3 条 | 698 | 粒度、角色与过程覆盖是目标模型的骨架，未裁决则 M4 无法起步 |
| **P1（随后）** | `MODEL_DUPLICATION`、`MODEL_OVERLAP`、`MIXED_RESPONSIBILITY`、`AGGREGATION_MODEL_PROBLEM`、`FACT_IDENTIFICATION_PROBLEM`、`MODEL_SELECTION_AMBIGUITY`、`SEMANTIC_AMBIGUITY` | 607 | 决定收敛范围、职责边界与事实覆盖，影响改造工作量 |
| **特殊审计（并行）** | `FACT_IDENTIFICATION_PROBLEM` 的闸门排除侧（stage）、`UNKNOWN_MODEL` | 3 + 2 | 事实闸门与范围归属属审计性质，须人工验证但不阻塞 |

上表第二行的 607 是这 7 个类型的问题总数，不等于 priority = P1 的 378 条（`MIXED_RESPONSIBILITY` 与 `AGGREGATION`、`FACT_IDENTIFICATION` 的部分行会因关联 finding 落到 P0 / P2，见 8.2）。**按清单行内 `priority` 列排期，不按类型推断。**

### 8.2 priority 的实际计算规则

problem 的 `priority` **取其关联 finding 中最靠前的值**；没有 finding 支撑时才用类型默认值（`PROBLEM_TYPE_PRIORITY`）。因此实测分布与「类型默认」并不一致：

| priority | 条数 | 主要构成 |
| --- | --- | --- |
| P0 | 698 | GRAIN 559 + MIXED 130 + FACT_ID stage 3 + ROLE 4 + COVERAGE_GAP 2 |
| P1 | 378 | DUPLICATION 317 + OVERLAP 27 + FACT_ID table 23 + SELECTION 8 + SEMANTIC 3 |
| P2 | 99 | AGGREGATION 22 + UNKNOWN 2 + DIMENSION 1 + MIXED 74 |
| P3 | 15 | PROCESS_ALIGNMENT 15 |

**注意**：`MIXED_RESPONSIBILITY` 的类型默认是 P1，但 130 条因关联 `mixed_grain` finding（P0）被抬到 P0、74 条落到 P2；`AGGREGATION` 类型默认 P1，实测全为 P2（`aggregate_fact` finding 是 P2）。**看清单以行内 priority 为准，不要按类型推断。**

### 8.3 裁决时的证据强度提示

| strength | 条数 | 含义 | 建议 |
| --- | --- | --- | --- |
| `strong` | 1137 | ≥4 类证据类型 | 可按 priority 批量裁决，重点看 `human_question` |
| `moderate` | 20 | 3 类证据 | 需要核对证据行再决定 |
| `weak` | 33 | ≤2 类证据 | 必须人工补证据后才能定性（已自动 `review_required`） |

---

## 九、重构证据模板

每条进入重构讨论的 problem，必须按固定七段填写；**前六段机器给出，第七段只能由人写**：

```text
Current State   当前是什么样（描述，不是评价）
    ↓  取自 problem.description
Problem         这构成什么问题（问题陈述）
    ↓  取自 problem.rationale.problem
Evidence        凭什么这么说（可追溯证据）
    ↓  取自 problem.rationale.evidence + current-state-problem-evidence.json
Impact          会造成什么后果（结构影响）
    ↓  取自 problem.rationale.impact（impact_types 及其中文说明）
Root Cause      根因是什么（或明确写 UNKNOWN）
    ↓  取自 problem.root_cause
Why Change      为什么现在要改（重构理由）
    ↓  取自 problem.rationale.why_change
Human Decision  人工裁决：确认 / 否决 + 理由 + 决定的范围与顺序
    ↓  只能来自清单回填与评审记录，机器不填
```

约束：

- 七段缺一不可；没有 `Evidence` 的条目直接被 Evidence First 拦截（构造阶段即报错）。
- `Root Cause` 证据不足时必须写 `UNKNOWN`（12 条），**禁止写设计偏好**（如「应该分层」「应该拆表」）。
- `Human Decision` 未填写前，该 problem 一律按 candidate 对待，不得进入实施排期。
- 全量机器字段见 `current-state-problems.json` 的 `rationale` 对象（`current_state` / `problem` / `evidence` / `impact` / `why_change` 五键）。

---

## 十、重构证据矩阵

矩阵列固定为四列；**`Potential Refactoring Direction` 只写方向，不写具体表设计**（不出现目标表名、字段、DDL、分层落位）：

| Current Problem | Evidence | Root Cause | Potential Refactoring Direction |
| --- | --- | --- | --- |
| `GRAIN_PROBLEM`（表 A，`confirmed_conflict`） | grain candidate 3 组互不包含的候选键 + 12 条候选键字段证据 + `grain_conflict` finding | `MULTIPLE_GRAINS_IN_ONE_MODEL` | 先裁决唯一业务粒度，再评估是否需要按粒度拆分表达 |
| `MODEL_DUPLICATION`（表 B、C，`technical_copy_candidate`） | 共享 process + 共享 grain 签名 + Jaccard 0.94 + 跨层血缘边 | `MULTIPLE_SOURCE_SYSTEM_REPLICATION` | 先确认权威表与副本关系，再决定收敛范围与迁移顺序 |
| `AGGREGATION_MODEL_PROBLEM`（process D，`review_required`） | 2 张聚合表 + 无 fact-anchor 上游血缘 + `aggregate_fact` finding | `UNKNOWN` | 先补齐上游事实来源证据，再决定该聚合层是否保留 |
| `MODEL_COVERAGE_GAP`（process E） | process 无任何 fact candidate + 3 个未产出事实的 grain 候选 | `UNKNOWN` | 先确认该过程是否需要事实建模，再决定覆盖方式 |

使用规则：

1. 每行必须能从 `problem_id` 追溯到 `current-state-problem-evidence.json` 的证据行。
2. `Root Cause` 为 `UNKNOWN` 的行，`Direction` 只能是「补证据 / 定范围」类动作，不能是「拆分 / 合并 / 下线」类动作。
3. 方向描述停留在**动作类型**（裁决、收敛、补证据、拆分评估），不落到**具体对象**（某张表、某个字段、某套 DWD 设计）。
4. 矩阵整体是 M4 的输入，不是 M4 的产出——**矩阵完成后才允许开始 Target DWD Design**。

---

## 十一、真实数据摘要

数据基准：当前 `analysis/` 快照，3719 张表 / 102603 字段 / 4439 条 finding。

### 11.1 计数与状态

| 指标 | 值 |
| --- | --- |
| Finding | 4439（status 全部 `candidate`；P0 696 / P1 3147 / P2 581 / P3 15） |
| Problem | **1190** = candidate 1148 + review_required 42 + confirmed 0 + rejected 0 |
| priority | P0 698 / P1 378 / P2 99 / P3 15 |
| evidence_strength | strong 1137 / moderate 20 / weak 33 |
| 受影响表（去重） | 3345 |
| Finding 覆盖 | 4427 / 4439（未进入 12 条，全部 `aggregate_fact`） |
| 证据行 | 30201（TABLE 9177、GRAIN 8059、FINDING 6313、COLUMN 4219、PROCESS 1210、LINEAGE 1202、RELATIONSHIP 12、OBJECT 9、SQL 0） |
| 证据截断 | 53 条 problem 超过单条 50 行上限被截断（全量看 `current-state-problem-evidence.json`） |
| Fact Gate 复算 | qualified 3364 / rejected 2315（全部 `no_measure_evidence`），`matches_m35 = true` |

### 11.2 13 类分布

| problem_type | 中文 | 条数 | scope | priority | status | strength |
| --- | --- | --- | --- | --- | --- | --- |
| `GRAIN_PROBLEM` | 粒度问题 | 559 | table | P0 | candidate | strong |
| `MODEL_DUPLICATION` | 模型重复 | 317 | table_set | P1 | candidate | strong |
| `MIXED_RESPONSIBILITY` | 职责混杂 | 204 | table | P0 130 / P2 74 | candidate | strong |
| `MODEL_OVERLAP` | 模型重叠 | 27 | table_set | P1 | candidate | strong |
| `FACT_IDENTIFICATION_PROBLEM` | 事实识别问题 | 26 | stage 3 / table 23 | P0 3 / P1 23 | candidate 3 / review_required 23 | moderate 3 / weak 23 |
| `AGGREGATION_MODEL_PROBLEM` | 聚合模型问题 | 22 | process | P2 | candidate 13 / review_required 9 | strong |
| `PROCESS_MODEL_ALIGNMENT` | 过程与模型对齐 | 15 | process | P3 | candidate | moderate |
| `MODEL_SELECTION_AMBIGUITY` | 模型选择歧义 | 8 | process | P1 | candidate | strong |
| `MODEL_ROLE_AMBIGUITY` | 角色歧义 | 4 | dimension | P0 | review_required | weak |
| `SEMANTIC_AMBIGUITY` | 语义歧义 | 3 | stage | P1 | review_required | weak |
| `MODEL_COVERAGE_GAP` | 过程覆盖缺口 | 2 | process | P0 | candidate | moderate |
| `UNKNOWN_MODEL` | 未定模型 | 2 | table_set | P2 | review_required | weak |
| `DIMENSION_IDENTIFICATION_PROBLEM` | 维度识别问题 | 1 | stage | P2 | review_required | weak |

### 11.3 classification 分布

`confirmed_conflict` 548、`grain_identical_structure_divergent` 122、`duplication_candidate` 108、`technical_copy_candidate` 97、`structural_overlap` 17、`model_problem` 13、`possible_conflict` 11、`review_required` 9、`NO_ANCHOR` 1、`NO_EVIDENCE` 1、`unclassified` 263（未分类 = 无 classification 的类型，如 MIXED / PROCESS_ALIGNMENT）。

### 11.4 18 类 Finding 分布（v2 的输入）

`overlapping_fact` 2605、`grain_conflict` 559、`aggregate_fact` 504、`duplicate_fact` 489、`fact_without_measure` 50、`wide_analytical_table` 39、`result_table` 37、`mixed_grain` 130、`process_multiple_grains` 15、`role_ambiguous` 4、`fact_gate_no_measure` 3、`dimension_object_derived` 1、`relationship_technical_only` 1、`relationship_object_co_occurrence` 1、`evidence_strength_semantics` 1，`fact_gate_pattern` / `snapshot_periodic_ambiguous` / `multi_process_table` 为 0。

---

## 十二、当前阶段完成标准

### 12.1 Machine side —— 已完成（可验证）

- [x] 一条命令 `analyze-current-state-model` 写出 9 个产物（5 个 M3.6 + 4 个 v2），不改上游 13 个输入与更早阶段产物
- [x] 4439 条 finding → 1190 条 problem，`finding_coverage` 账目自洽（未覆盖 12 条全部为 `valid_aggregate`）
- [x] 每条 problem ≥1 条证据；无证据即报错，不产出「只有结论没有证据」的行
- [x] 机器状态只出现 `candidate` / `review_required`，`confirmed` = 0
- [x] 确定性：连续两次运行 9 个产物 SHA256 一致；无时间戳 / UUID / 随机抽样
- [x] 截断契约：单 problem 证据 ≤50 行、报告 Top Problems ≤20 行、清单每区 ≤50 行，均注明总数
- [x] 门禁通过：`uv run pytest -q && uv run ruff check . && uv run mypy`（368 tests）

### 12.2 Human side —— 未开始（当前卡点）

- [ ] `current-state-problem-review-checklist.md` 13 个分区回填（当前全部 `pending`）
- [ ] `current-state-review-checklist.md` 5 个分区回填（当前 157 行全部 `pending`）
- [ ] P0 698 条 + P1 378 条按 priority 完成裁决，`confirmed` / `rejected` 出现非零值
- [ ] 权威表、收敛顺序、唯一粒度键、UNKNOWN 表范围归属四类判断落档
- [ ] 重构证据矩阵（§十）逐行填完 `Human Decision`
- [ ] M4 Target DWD Design **尚未开始**（前置条件见 §6）

**结论：机器侧完成、人工侧待办。1190 条 problem 是待裁决的候选，不是已确认的重构清单。**

---

## 十三、禁用表达清单

| 禁用表达 | 正确表达 |
| --- | --- |
| 「4439 个问题」 | 「4439 条 finding（观测）」 |
| 「1190 个已确认问题」 | 「1190 条 problem candidate（其中 confirmed = 0）」 |
| 「559 张表粒度错误」 | 「559 条 GRAIN_PROBLEM：候选键不唯一，待人工定粒度」 |
| 「2315 张表不是事实」 | 「Fact Gate 因 `no_measure_evidence` 排除 2315 个 grain candidate」 |
| 「存在 12 条漏报」 | 「12 条 `aggregate_fact` 评估为 `valid_aggregate`，有意不成问题」 |
| 「UNKNOWN 表是坏模型」 | 「UNKNOWN 表证据不足：`NO_ANCHOR` 463 / `NO_EVIDENCE` 1578，需人工定范围」 |
| 「overlap 就是重复表」 | 「重叠与重复是两类问题：`MODEL_OVERLAP` 27 / `MODEL_DUPLICATION` 317」 |
| 「聚合表本身就是问题」 | 「`valid_aggregate` 不发问题；只有无上游或自带粒度 / 重复问题才算」 |
| 「按 problem 清单直接设计 DWD」 | 「先完成人工裁决与重构证据矩阵，再进入 M4」 |
| 「strong = 正确」 | 「strong = 证据类型 ≥4，仍需人工确认」 |
| 「candidate 可以直接改表」 | 「candidate / review_required 都未获人工确认，不产生任何改表动作」 |
| 「finding 裁决了，problem 也就裁决了」 | 「两个清单各自独立，回填互不替代」 |
| 「证据不足就先强制分类降 UNKNOWN」 | 「证据不足时 UNKNOWN 就是合法结果，不得为降 UNKNOWN 强制分类」 |
| 「root cause 应该写设计判断」 | 「证据不足时 root cause 必须写 `UNKNOWN`，不写设计偏好」 |
| 「M3.6 v2 产出目标模型」 | 「M3.6 v2 只产出问题、证据、影响、根因与重构理由，目标模型属 M4」 |

---

## 附录：文档与代码索引

| 需要查什么 | 去哪里 |
| --- | --- |
| 13 类常量、状态机、词汇表 | `src/data_platform_analysis/analysis/models.py`（`PROBLEM_*`、`GRAIN_ASSESSMENT_*`、`OVERLAP_CLASS_*`） |
| 各类 problem 的构造与证据 | `src/data_platform_analysis/analysis/problem_assessment.py` |
| Finding 生成、Fact Gate 复算 | `src/data_platform_analysis/analysis/model_review.py` |
| 报告 6 节与清单 13 分区渲染 | `src/data_platform_analysis/analysis/reports.py` |
| 23 条行为测试 | `tests/test_problem_assessment.py` |
| 全量 problem 数据 | `analysis/business/current-state-problems.json` |
| 全量证据行 | `analysis/business/current-state-problem-evidence.json` |
| 人工入口报告 | `analysis/business/current-state-problem-summary.md` |
| 人工回填台账 | `analysis/business/current-state-problem-review-checklist.md` |
| 阶段逻辑与产物地图 | [docs/CODE_LOGIC_ANALYSIS.md](CODE_LOGIC_ANALYSIS.md) |
| 命令与退出码 | [docs/COMMANDS.md](COMMANDS.md) |

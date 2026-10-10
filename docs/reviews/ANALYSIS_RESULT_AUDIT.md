# 当前 Snapshot 分析结果审查

> 本报告是基于现存文件的只读审查，不是一次新的 Pipeline 运行，不构成业务裁决或目标模型设计。除本文件外，本轮没有修改代码、配置、Snapshot、生产 `analysis/` 产物或人工评审清单。

## 1. 审查基准与结论摘要

| 项目 | 当前核对结果 |
|---|---|
| 分支 / HEAD | `main` / `2d7edfe50a0b144553e31d38920395337dc374e0` |
| 最近提交 | `2d7edfe chore: 纳入 analysis 下的 Markdown 产物`；其前为 `b28faf3 feat: 增加跨阶段证据覆盖账本` |
| 上游状态 | HEAD 与 upstream 同步，ahead/behind `0/0` |
| 工作区异常（审查开始时及完成时保留） | `analysis/scope/summary.json` 同时显示 staged deletion 与 untracked file；未 add、unstage、删除或还原 |
| Snapshot | `source/manifest.json`：生成时间 `2026-10-09T12:40:13.475581+00:00`，DataWorks / MaxCompute 三个 workspace |
| 产物时间 | 本地分析产物 mtime 约为 2026-10-10 21:02；晚于 Snapshot 采集时间 |
| 运行 provenance | `analysis/` 没有 run manifest 或 Snapshot 内容哈希，无法严格证明 Understanding / Review 所有文件由同一代码版本、同一份 Snapshot 原文一次性生成 |
| 整体判断 | Inventory 身份和当前 Snapshot 索引吻合；Scope → Evidence 的主要计数与身份链吻合；Understanding / Review 能追溯到表身份，但有规则能力边界、证据裁剪和无运行 provenance 等限制。Review 全部仍为机器状态，没有已确认或已驳回问题。 |

### 审查边界

- 只读检查了当前 Git 状态、Snapshot manifest/index、`analysis/` 阶段产物、相关方法论文档、命令安全说明和样本 SQL。
- 未运行 `analyze`、测试、生产 pipeline 或任何清理命令；没有用旧报告替代本地 JSON 明细。
- `analysis/scope/summary.json` 的 Git 删除/未跟踪状态意味着工作区文件与 HEAD 的关系不寻常，但当前文件可读；此审查按磁盘上的当前文件计算，不改变该状态。

## 2. Snapshot 与阶段统计一致性矩阵

下表的“明细重算”依据当前 JSON 明细数组、Snapshot 索引或明确的跨产物身份关联。行数、边数、端点数、表数和候选数是不同统计粒度，不应互相相加。

| 检查项 / 来源 | 文件声明值 | 明细计算值 | 是否一致 | 差异 / 风险 |
|---|---:|---:|---|---|
| Snapshot DataWorks File indexes | 4,657 files；failed 0 | 三 workspace 索引合计 4,657 | 是 | 采集快照时点为 2026-10-09；不能据此推断此后平台状态 |
| Snapshot MaxCompute Table indexes | 3,724 tables；failed 0 | 三 workspace 索引合计 3,724 | 是 | Snapshot 原文与当前 Inventory 身份匹配 |
| Inventory Files / Tables | 4,657 / 3,724 | File identity 与 Snapshot 完全匹配；Table identity 与 Snapshot 完全匹配 | 是 | 未发现重复或未匹配身份 |
| Inventory Columns | 102,703 | Columns 明细 102,703；逐表 `column_count` 与列明细一致 | 是 | 元数据字段数不等于业务行数据检查覆盖 |
| Scope 全部 File | evaluated 4,657 | SQL eligible 541 + SQL excluded 4,116 = 4,657 | 是 | SQL 分类构成完整互斥分区 |
| Scope overall eligibility | 1,379 eligible；3,278 identity excluded | Node ID valid 1,379；missing 3,278 | 是 | 当前 `informal_excluded=0`；review-required 70 是重叠审核标记，不是额外排除类别 |
| Scope SQL qualification | eligible 541；ineligible 4,116 | reason：`SQL_ANALYSIS_ELIGIBLE` 541、`NODE_ID_MISSING` 3,278、`SQL_FORMAT_NOT_APPLICABLE` 838 | 是 | Node ID 身份、SQL 类型适用性和内容可用性是不同维度 |
| Scope review-required | 70 | 70 个对象均属于 SQL excluded 集合 | 是 | 该审核标记不改变 SQL 资格，也不应计为额外 File |
| 当前 Scope content states | present 2,826；not_checked 1,831；其余状态 0 | 内容路径缺失、空文本和读取错误均为 0 | 是 | 541 个 SQL eligible 文件内容均可用；`not_checked` 不能解释成采集失败 |
| SQL Statements | count 1,917 | statements 明细 1,917；均来自 SQL eligible Files，`parse_status=success` | 是 | 解析成功不证明 SQL 业务语义或结果正确 |
| SQL Table References | count 1,241 | reference 明细 1,241；statement 与 SQL eligible File 身份可追溯 | 是 | 676 个 Statement 无 Table Reference 行；可能是无表引用语句，不应按缺失引用直接判错 |
| SQL parse errors / Evidence error ledger | 0 / 0 | errors 明细均为空 | 是 | “零技术错误”只表示错误账本没有记录，不证明数据完整或业务正确 |
| SQL 未解析引用 / 跨项目引用 | 未解析 32 个 operand；跨 Project operand 1,574 | 32 = 外部/未登记 Project 27 + Inventory 找不到的表身份 5 | 是 | 这是 operand / endpoint 粒度，不是 32 条 Lineage 边或 32 张唯一表 |
| Layer assessments | 3,724；MATCH 3,663、UNKNOWN 61、CONFLICT 0 | assessments 明细 3,724；状态重新计数吻合 | 是 | UNKNOWN 是证据不足；MATCH 也仅为规则匹配，不是业务层级合规认证 |
| Table Lineage | 3,384 edges；跨 Workspace 1,534 | edge 明细 3,384；由 Table Reference source×target pair 重算的唯一边对与明细完全匹配 | 是 | 表级 SQL 引用血缘，不是调度 DAG 或字段级血缘 |
| Lineage unknown endpoint | Coverage 记 38 条 `unknown_endpoint_edge_count` | Coverage 实现按 source/target workspace ID 缺失计数；按端点 table key 对照 Inventory，另有 43 条边至少包含一个未索引端点 | 不可直接比较 | 两个口径不是同一指标：38 是 Workspace ID 缺失的边；43 是边中出现 Inventory 外端点的边；应分开报告 |
| Profiling | 3,724 tables / 102,703 columns | JSON 明细分别重算吻合；全部 `metadata_only` | 是 | 无 row-level 样本；不能判断唯一性、空值、分布或指标数值质量 |
| Understanding | Grain 5,678；Fact 3,363；Dimension 5；Process 17 | 各候选明细重算吻合，均为机器 candidate | 是 | 候选数量不等于确认对象数；字段/键命名模式不是业务定义 |
| Review Findings | 4,425 | 明细 4,425；状态全部 `candidate`；类型分布重算吻合 | 是 | Finding 表达机器观察，不是已确认缺陷 |
| Review Problems | 1,186；candidate 1,144、review_required 42 | 明细 1,186；confirmed 0、rejected 0；priority P0/P1/P2/P3 = 698/379/94/15 | 是 | 分类 `confirmed_conflict` 是机器分类标签，不是 human confirmed |
| Finding → Problem 关联 | Finding coverage 4,414 / 4,425 | Problem 引用共 6,376 次、涉及 4,414 个唯一 Finding；未关联 11 个，全部 `aggregate_fact` | 是 | 一个 Finding 可进入多个 Problem；引用次数不等于 Finding 数 |
| Problem Evidence | 汇总声称 30,132 evidence rows | `evidence_row_total=30,132`；文件只序列化 17,362 行 evidence 样本 | 总数一致，明细不全 | 每个 Problem 最多保留 50 行，53 个 Problem 达到裁剪上限；不能用样本明细行数替代总 evidence 数 |
| Coverage 输入产物 | 21 项标记 available | Review Coverage Ledger 有 4,657 File rows、3,724 Table rows；File analyzed 541、not_eligible 4,116 | 是 | available 仅表示产物存在/被读取，不代表每张表对每个模块都有充分证据 |
| Coverage Table outcomes | problem_candidate 3,345；insufficient_evidence 294；no_finding_under_implemented_rules 85 | 三类合计 3,724；Table Key 与 Inventory 一一对应 | 是 | 无 Finding 只代表实现规则未发现，不是模型正确；`problem_candidate` 包括机器候选而非确认问题 |
| 无 File 身份错误 | Coverage orphan/unattributed technical errors 0 | 错误账本当前为空 | 是 | 当前没有此类错误记录；不是对未来错误保留机制的覆盖保证 |

### 报告数字与旧文档差异

- `analysis/summary.md` 的 Inventory、Scope、SQL、Lineage、Layer、Profiling 数字与本地 JSON 明细一致。
- `analysis/review/current-state-problem-summary.md` 与当前 Review JSON 的 Finding 4,425、Problem 1,186、状态分布、Problem type 和 30,132 evidence 总量吻合；证据类型汇总是 Evidence 总量口径，不等于 JSON 中被截断的实际序列化行数。
- [M36_PROBLEM_ASSESSMENT.md](../M36_PROBLEM_ASSESSMENT.md) 和 [M36_HUMAN_ADJUDICATION_GUIDE.md](../M36_HUMAN_ADJUDICATION_GUIDE.md) 仍以 3,719 tables、4,439 findings、1,190 problems、30,201 evidence 等旧基线为当前数据基准；其优先级和聚合统计也不完全等于当前 JSON。属于 **Documentation inconsistency**，不能拿作最新运行结果。
- `docs/CURRENT_STATE_EVIDENCE_MAP.md` 标明 Understanding / Review 未在文档提及的隔离运行中重跑；它的样本规模只是只读抽查。本文的 Review 数值直接来自当前 JSON，不从该文档沿用。

## 3. Review 规则及真实样本核验

### Review 当前判断能力

- Finding 是结构信号；Problem 是规则聚合后的问题候选。自动状态仅为 `candidate` / `review_required`；人工确认与驳回数当前均为 0。
- Review v2 的方法文档明确其输入不包括 SQL references、Profiling 或 `source/`；Problem Evidence 当前 SQL 类型为 0。因此 Coverage 可以提供 SQL / Profiling / Lineage 导航，但 Problem 本身并未把这些证据逐条加入其问题论证。不要把一个可导航的证据引用说成 Review 规则已验证了 SQL。
- `priority`、`severity`、`evidence_strength`、机器 `classification`、人工 `status` 是不同维度。P0 不代表已发生事故；`confirmed_conflict` 不代表人工确认；`strong` 不代表业务语义已验证。

| Problem type / 样本 | 实际观察到的规则信号 | 能支持的判断 | 不能支持 / 需要的复核 |
|---|---|---|---|
| `GRAIN_PROBLEM` — `problem_0327` / `model_finding_1325` | 目标 DWD 表有 4 个 Fact Candidate，候选键分别为 `customer_code+order_no`、`customer_code+sub_order_no`、`order_no`、`sub_order_no`；机器记 `confirmed_conflict` | 一个 Table 存在多个互不相同的候选键签名 | 不证明行的业务粒度冲突或任一键有效；需业务定义与行级唯一性检查 |
| `MODEL_DUPLICATION` — `problem_0877` / `model_finding_2020`–`2028` | 六张订单链表组成重复/相似候选簇；Findings 比较 process、grain 和字段重合 | 这些表的结构/候选特征高度接近，值得检查职责边界 | 临时 staging、BU 分支、不同来源或历史版本可能是有意区分；需逐表查 SQL 转换和消费者 |
| `MODEL_OVERLAP` — `problem_1128` / `model_finding_0911` | 该候选聚合多个结构相似 Finding 和七张表 | 规则观察到跨表角色/结构重叠信号 | 不等于同一业务对象或可合并表；需层级职责、数据来源和生命周期确认 |
| `MIXED_RESPONSIBILITY` — `problem_0609` / `model_finding_0001` | 单表有多个 aggregation grain candidate 等结构信号 | 值得调查模型是否混合原子与聚合职责 | 不证明设计违反约定；业务消费需求可能要求汇总输出 |
| `FACT_IDENTIFICATION_PROBLEM` — `problem_0024` / `model_finding_0995` | Fact Gate 对 aggregation grain candidates 以 `no_measure_evidence` 排除；覆盖范围较大 | 当前规则未在相当一部分候选中找到可识别的度量字段证据 | 不证明模型缺少业务事实或实际无度量；字段命名、派生度量和规则覆盖需评估 |
| `AGGREGATION_MODEL_PROBLEM` — `problem_0001` / `model_finding_0039` | 找到 aggregation 形态、8 个度量候选字段等信号 | 表可进入聚合层次复核 | 不证明聚合粒度、指标口径、去重或可回溯性有误；需查看 SQL 和已确认指标定义 |
| `PROCESS_MODEL_ALIGNMENT` — `problem_1167` / `model_finding_4334` | 一个 Process Candidate 下 Fact Candidate 出现 aggregation、transaction、unknown 三种 grain 形态 | 候选过程关联了不同形态的模型 | 不证明这些模型违反同一过程要求；过程候选本身不是已确认的业务边界 |
| `MODEL_SELECTION_AMBIGUITY` — `problem_1159` / `model_finding_0507` 等 | process 候选及共享键等信号扩展至 151 张表、298 Findings | 这是一组跨表选择歧义的宽泛候选，需要先分解和抽样 | 不表示 151 张表都重复或错误；当前 Problem 缺 SQL / Lineage 证据且范围过宽，不能据此改造 |
| `MODEL_ROLE_AMBIGUITY` — `problem_1155` / `model_finding_4383` | `customer` Object 同时命中 Dimension Candidate 和 fact-related Object | 机器识别的对象角色不唯一 | 不足以判断 Object 或表角色错误；需业务主数据角色/使用方式确认 |
| `DIMENSION_IDENTIFICATION_PROBLEM` — `problem_0023` / `model_finding_0502` | 多个 Dimension Candidate 与 Object 一一对应，但没有独立 suitability 判断 | 识别到候选来自对象映射的规则边界 | 不证明维度缺失或维度设计不当；需 dimension 适用性准则及业务责任方裁定 |
| `SEMANTIC_AMBIGUITY` — `problem_1182` / `model_finding_0994` | `evidence_strength` 在 3,363 个 Fact Candidate 中全为 strong；信号指出构造规则可能使该字段成为必然值 | 证据强度字段存在区分度/语义解释风险 | 不等于事实模型都有强证据；应校准评分定义，避免候选构造特征循环证明候选 |
| `MODEL_COVERAGE_GAP` — `problem_0808` | 两张表组成候选，但 Problem 没有 Finding ID | 当前聚合规则生成一个模型覆盖候选 | 仅凭当前聚合证据难还原“缺覆盖”的业务边界；需查看完整 Problem Evidence 和 process 定义 |
| `UNKNOWN_MODEL` — `problem_1185` / `problem_1186` | `NO_ANCHOR` 涉及 471 表；`NO_EVIDENCE` 涉及 1,572 表 | 机器标记 Understanding 证据锚点/关联不足 | 不代表无效模型或问题不存在；需看模块实际执行范围、缺失映射与资产用途 |

### 跨类型 Finding 样本和边界

当前 15 类实际 Finding 类型：`overlapping_fact` 2,597、`grain_conflict` 559、`aggregate_fact` 501、`duplicate_fact` 491、`mixed_grain` 130、`fact_without_measure` 50、`wide_analytical_table` 39、`result_table` 32、`process_multiple_grains` 15、`role_ambiguous` 4、`fact_gate_no_measure` 3，以及各 1 条 `evidence_strength_semantics`、`relationship_technical_only`、`relationship_object_co_occurrence`、`dimension_object_derived`。合计 4,425。

- 对粒度、重复、重叠、聚合、Fact Gate、角色和过程类上述代表性 Finding 已逐条按其 `evidence_sources` 和描述对照样本复核；它们主要使用 table / column / candidate、process / grain 等信号，未证明业务键唯一性。
- `result_table` / `wide_analytical_table` 是形态描述，不能独立成为模型缺陷；`aggregate_fact` 既可能是合理汇总，也可能提示口径风险。`relationship_technical_only` / `relationship_object_co_occurrence` / `dimension_object_derived` 是技术关系或对象映射信号，不等于已确认业务关系。
- 规则适用的共同前提是候选提取和映射覆盖足以支撑相关结构对比。相同字段名、键候选或字段 Jaccard 重合都可能因来源系统、BU、时效、处理阶段和消费者不同而合理。
- Review 报告将若干 `aggregate_fact` 评为 `valid_aggregate` 并不产出 Problem；当前未进入 Problem 的 11 条 `aggregate_fact` 与该规则意图一致。仍应理解为实现规则下不建问题，不是业务批准。
- **Data validation required**：唯一键、JOIN 基数、重复率、过滤影响、金额/数量对账，以及时间/退货处理均需真实行数据或受控查询；解析成功和结构候选不能替代。

## 4. DWD 样本：端到端证据链

样本：`dme_cdm.dwd_ecom_order_detail_info_bu`。本节追踪到 Review Coverage 和 Problem 候选；这是一条可导航的技术证据链，不是业务结论。

### 身份与模块结果

| 环节 | 当前证据 |
|---|---|
| Snapshot / Inventory | Workspace `466337`（`dme_cdm`）；Table Key `dme_cdm.dwd_ecom_order_detail_info_bu`；MaxCompute Inventory 来源 `source/maxcompute/workspaces/466337/tables/dwd_ecom_order_detail_info_bu.json`；70 columns；表注释 `ec订单明细表` |
| Layer | `analysis/evidence/layer/assessments.json` 为 `MATCH`，`workspace_layer=CDM`、`candidate_layer=DWD`。这是配置和命名规则的匹配，不是业务职责确认 |
| Profiling | `metadata_only`；`row_count=null`；没有行级唯一性/空值/分布检查 |
| SQL | 目标写入语句是 File `504340559` / Node `700006513464` / Statement `7`；整个目标表关联到 29 条 SQL Table Reference records，文件状态为 analyzed |
| Lineage | `analysis/evidence/lineage/table-lineage.json` 中 31 条边：4 incoming、27 outgoing；边证据携带 File / Statement ID。是 SQL 表级引用，不包含字段级传播或调度任务 DAG |
| Understanding | `grain_candidate_419`–`grain_candidate_422` 分别提出四种候选键；多个 Fact Candidate 均为候选，不含人工确认 |
| Review | Coverage 将样本标为 `problem_candidate`，关联 8 个 Problem ID、10 个 Finding ID；Problems 均为 candidate，没有 SQL 类 Problem Evidence |

### 可直接观察的 SQL 事实

`source/dataworks/workspaces/466337/content/504340559__dwd_ecom_order_detail_info_bu.sql` 的目标写入为 `insert overwrite ... partition(ds)`（Statement 7）。目标加工链引用 `_temp_02`、`_temp_03`、`dwd_master_data_store_bu`、`dwd_master_data_customer_bu` 等。候选路径中还存在 `dwd_ka_pos_data_sales_daily_mid` 读取：SQL 按 `order_no`、`sub_order_no`、商品条码等分组，计算 quantity / 金额（表达式含 `return_*` 与 `base_*` 字段），过滤 `upper(first_channel_name)='ECOM'`，并剔除销量和销额都为零/空的记录。SQL 中可见 customer / geography / region mapping joins、多处 `NVL` 默认值和 `ds` 投影。此处只记录 SQL 形态，不能推导业务正确性。

可用于业务/技术评审的字段名包括 `order_no`、`sub_order_no`、`commodity_sku`、`quantity`、`payment_actual`、`total_price_tax`、`customer_code`、`shop_id`、`ds`。注释和字段名是 Snapshot 的技术事实，不等于正式业务定义。

### 样本关联的 8 个 Problem 候选

| Problem | 类型 / 优先级 / 状态 | 范围及证据 | 解释边界 |
|---|---|---|---|
| `problem_0327` | `GRAIN_PROBLEM` / P0 / candidate | 目标表；`model_finding_1325`；4 个 Grain Candidate；10 条 Problem evidence | `confirmed_conflict` 是机器 classification，不是业务确认 |
| `problem_0877` | `MODEL_DUPLICATION` / P1 / candidate | 六张订单链表；15 Findings；38 evidence | 候选重复组；仍可能代表处理阶段或来源差异 |
| `problem_0992` | `MODEL_DUPLICATION` / P1 / candidate | 5 表；`model_finding_0588`；20 evidence；候选键 `customer_code+order_no` | 规则观察到相同候选签名，不证明行级重复或业务等价 |
| `problem_0993` | `MODEL_DUPLICATION` / P1 / candidate | 5 表；`model_finding_0591`；20 evidence；候选键 `customer_code+sub_order_no` | 同上 |
| `problem_1000` | `MODEL_DUPLICATION` / P1 / candidate | 5 表；`model_finding_0609`；20 evidence；候选键 `order_no` | 同上 |
| `problem_1003` | `MODEL_DUPLICATION` / P1 / candidate | 5 表；`model_finding_0616`；20 evidence；候选键 `sub_order_no` | 同上 |
| `problem_1159` | `MODEL_SELECTION_AMBIGUITY` / P1 / candidate | 151 表；298 Findings；455 evidence；关联 `process_candidate_004` | 过宽候选；需先拆成有 SQL / 业务边界的子问题，不可将 151 张表整体认作问题 |
| `problem_1169` | `PROCESS_MODEL_ALIGNMENT` / P3 / candidate | 491 表；1 个 Finding；494 evidence | 过程对齐范围极宽，样本表属于其成员不等于该表是缺陷原因；建议低于订单链专项核查 |

特别注意：前四个 `technical_copy_candidate` Problem 分别比较不同候选键；它们并非四个独立的已确认重复缺陷。`problem_0877`、`problem_0992` 至 `problem_1003` 的表集合有重合，计数不能解释为八种可累加的模型问题。

### 待验证问题清单

| 问题 | 已有证据 | 还缺什么 / 验证方法 | 需要责任人 |
|---|---|---|---|
| 一行究竟代表订单、子订单、商品行还是加工记录？ | SQL 有订单号、子订单号、商品 SKU 的分组字段；四组候选键 | 正式事件定义、不同来源字段对应关系；抽样并按所有键计数/去重 | 电商业务流程负责人 + DWD 模型负责人 |
| 业务键及 JOIN 键是否唯一？是否放大？ | 文件 `504340559` Statement 7 的 customer / store / mapping joins 与键条件 | 检查每个输入分区键唯一性；对每次 JOIN 比较行数及目标键 distinct 数 | 数据工程师 + 主数据负责人 |
| `NVL(...,'Others')`、`'-110'` 等 fallback 是否改变语义？ | SQL 投影可见默认值和空值分支 | 目标字段的缺失含义、枚举/未知/不适用的区分和下游消费；比较默认化前后分布 | 电商业务 + 主数据治理 |
| `ds` 代表业务时间还是装载/处理分区？ | `ds` 从 `pay_time` / `a.ds` 投影，读取逻辑使用最大分区 | 来源系统时区、事件时间定义、迟到/重跑策略，跨日期样本对账 | 电商业务 + 数据平台 |
| 退货、取消、退款、更正如何表达？ | 聚合表达式同时使用 `return_*`、`base_*` 数量/金额字段 | 源记录状态定义、冲正逻辑；选择已知订单做金额/数量端到端对账 | 电商业务 + 财务/指标负责人 |
| 指标口径是否一致？ | `quantity`、`payment_actual`、`total_price_tax` 等计算在 SQL 中可见 | 经批准的销售/订单/商品数量定义及排除条件；按业务样例重新计算对账 | 指标 owner + 财务/电商业务 |
| 临时表、BU 表和非 BU 表是否重复职责？ | 六表候选组及上下游 SQL edges | 对比来源、转换、数据生命周期和实际消费者；确认哪个是正式消费接口 | DWD owner + 下游 ADS/报表 owner |

业务定义未确认、行级验证未完成前，本样本**不具备进入目标 DWD 结构设计的充分条件**；可以开始证据/业务评审，但不能直接批准保留、合并、拆分或删除。

## 5. 人工评审优先队列

顺序综合业务指标潜在影响、可访问 SQL 证据、问题候选宽度、待确认依赖和是否可快速验证。Priority 为审查建议，不替换 JSON 中的机器 priority。

| 顺序 | Problem / 类型 | 表与证据锚点 | 置信度 / 不确定性 | 业务确认 / 技术验证 | 建议责任角色 | 排序理由 / 进入设计条件 |
|---:|---|---|---|---|---|---|
| 1 | `problem_0327` — `GRAIN_PROBLEM`（P0 candidate） | `dme_cdm.dwd_ecom_order_detail_info_bu`；`model_finding_1325`；SQL File `504340559` Statement `7`；Grain `419`–`422`；Inventory 70 columns；31 lineage edges | **技术候选中高、业务结论低**：多键信号清晰，键唯一性/业务粒度未知 | 确认订单/子订单/订单商品行定义；在受控样本测四种键唯一性、JOIN 放大和退货影响 | 电商流程 owner、DWD owner、数据 QA | 最聚焦的 P0 且 SQL 可追踪。业务 grain、键与指标定义经确认并且行级检查完成后，才可进入设计 |
| 2 | `problem_0877` — `MODEL_DUPLICATION`（P1 candidate） | 六张订单详情 / BU / mid / temp 表；15 Findings（`model_finding_2014`–`2028`）；Lineage 5 条相关 evidence | **结构重合证据中等，是否冗余不明**：加工层/来源版本可能解释差异 | 对比每张表 SQL、上下游和消费者；确认正式接口、生命周期、BU 范围 | DWD 领域 owner + ETL owner + ADS consumer | 可与队列 1 共用同一业务确认和 SQL 检查；能决定保留/收敛前需确认不同层次职责 |
| 3 | `problem_0992`、`0993`、`1000`、`1003` — `MODEL_DUPLICATION` | 五表候选集；Finding 分别为 `0588`、`0591`、`0609`、`0616`；process candidate `004` | **签名一致性高、真实复制判断低**：每组候选键定义不同，Problem 集合重叠 | 与业务确认候选键组成及其含义；同一业务分区进行重复率和跨表记录对账 | 电商业务 owner + 模型治理 + 数据 QA | 可并入订单样本评审，避免重复开四个独立问题；完成键/流程解释之前不进入合并设计 |
| 4 | `problem_1159` — `MODEL_SELECTION_AMBIGUITY`（151 表 / 298 Findings） | `process_candidate_004`；其中含订单样本表；Problem Evidence 无 SQL / Lineage 行 | **候选规模证据高、可行动归因低**：表群宽泛且缺直接 SQL 归因 | 先切分成具体 process、表簇和消费场景；抽取 representative SQL / dependencies，再问每簇的权威模型 | 电商域业务 owner + Data Architecture + 各域模型 owner | 影响范围可能大但存在过度聚合风险；先做候选拆分，不能把全 151 表作为整改清单 |
| 5 | `problem_1185` / `problem_1186` — `UNKNOWN_MODEL` | NO_ANCHOR 471 tables；NO_EVIDENCE 1,572 tables | **覆盖缺口明确、问题方向未知** | 选关键 DWD/高消费表核实未锚定原因；识别缺失产物、对象映射还是非适用资产 | 数据治理 + 对应域 owner | 它们表示当前推理锚点/证据不足，不等于低风险或坏模型；按核心消费影响抽样补证据 |
| 6 | `problem_1155`–`1158` — `MODEL_ROLE_AMBIGUITY`（review_required） | Object 同时命中 Dimension 与 fact-related roles；`model_finding_4383` 为代表 | **规则冲突可见、业务角色未定** | 业务确认对象与维度角色，核对相关候选表用途和消费 | 主数据负责人 + 业务数据 owner | 属显式 review_required；先确认对象角色再评价模型 |
| 7 | `problem_1182`–`1184` — `SEMANTIC_AMBIGUITY`（review_required） | `model_finding_0994` 指出所有 Fact Candidate 的 evidence_strength 都为 strong | **字段区分度问题高、语义影响待校准** | 由 Review 方法 owner 确认 evidence strength 的含义、是否循环依赖候选构造 | 分析平台 / Review 方法 owner | 可在业务裁决前校准解释；不应把“strong”用作业务确认依据 |
| 8 | `problem_0808` 等 `MODEL_COVERAGE_GAP`（P0 candidate）与 `problem_0001`、`1167` 等过程/聚合样本 | Problem type 样本见第 3 节 | **结构触发可复算、业务适用性有限** | 查看完整 Problem Evidence、SQL 及业务过程定义；评估 `no_finding_under_implemented_rules` 表的抽样覆盖 | Review owner + 域模型 owner | 在订单专项之外按受影响指标/核心模型筛选，不按 P0/type 批量改造 |

### 优先业务问题清单

1. 电商订单、子订单、商品明细分别是什么业务事件，源系统之间是否同义？
2. `order_no`、`sub_order_no`、`commodity_sku` 的业务键组合是什么？允许同键多行、拆包、退货或更正吗？
3. `quantity`、`payment_actual`、`total_price_tax` 的正式定义、税口径、退款/退货/取消排除规则是什么？
4. `ds` 是业务事件日期、支付日期还是加工分区日期？迟到数据和重跑怎样处理？
5. 主数据/地理映射的未匹配值是未知、其他、不适用还是待修复？默认值可否进入指标统计？
6. BU、mid、temp、非 BU 表间哪些差异是刻意的？谁拥有权威消费接口？
7. 哪些下游报表或经营指标使用目标表及候选重复表？它们需要什么粒度和延迟？

## 6. 误报、漏报与证据缺口风险

| 分类 | 审查发现 |
|---|---|
| **Documentation inconsistency** | M36 方法论文档沿用旧表数、Finding / Problem / Evidence 数，可能导致裁决者对全量和清单覆盖形成错误预期 |
| **Evidence gap** | Review Problem 当前没有 SQL evidence；需从 Coverage / SQL refs / 原始 SQL 手动串联，判断理由本身可能缺少关键加工逻辑 |
| **Evidence gap** | Problem Evidence 每个 Problem 最多序列化 50 条；53 个 Problem 的展示 evidence 是截断样本，需以 `evidence_row_total` 和规则生成详情为准 |
| **Evidence gap** | 当前 `analysis/` 没有 run manifest / Snapshot hash。Inventory 对 Snapshot identities 一致，但这不能证明理解和 Review 全部输入的内容版本完全一致 |
| **Likely false-positive risk** | 相同候选键、字段重合或 process candidate 可能混合临时层、BU 分支、来源系统和不同生命周期；宽泛表簇尤需人工拆分 |
| **Likely false-negative / coverage risk** | SQL parse success 不代表字段语义、JOIN cardinality 或时间逻辑正确；没有行数据，实际数据质量问题无法识别 |
| **Coverage semantics risk** | `no_finding_under_implemented_rules` 是规则没有触发；`insufficient_evidence` 是 Coverage 的技术状态。二者都不等于模型已验证正确 |
| **Unknown reference risk** | 32 unresolved operands、43 Inventory 外端点边以及 38 Workspace-ID-null edges 是三个不同口径；需要按业务关键程度核实外部/别名 Project 和 Inventory 缺口 |
| **Boundary limitation** | Lineage 是表级引用关系，不是 DataWorks 调度 DAG；Profiling 是元数据画像，不含行数据；不适合据此证明任务顺序或数据质量 |

## 7. 是否可以进入 DWD 改造 / DWS 设计

**可以进入有业务和数据责任人的评审与补证阶段；目前不应据此批准具体 DWD 改造或 DWS 设计。**

原因：

1. 当前 1,186 个 Problem 全部是候选状态，人工确认 0，人工驳回 0。
2. Understanding 中所有 Grain、Fact、Dimension、Process 仍为候选，缺少已确认业务事实及定义的配置消费路径。
3. 样本表尚无行级 grain 唯一性、JOIN 基数、金额/数量对账或时间语义验证。
4. Problem 聚合与 SQL 证据分离；高优先级问题仍需回到 SQL、Coverage 和业务责任人形成逐项证据闭环。
5. 关键文档含过期统计，正式开展全量人工裁决前应以当前 JSON / checklist 覆盖说明为准。

允许的下一步是基于队列 1–3 组织定向评审并记录确认/驳回理由；这不等同于开始设计目标模型。

## 8. 下一阶段最小可执行计划与验收条件

1. **固定审查基线**：为一轮分析记录 Snapshot manifest/hash、代码 HEAD、配置版本、开始结束时间与实际输入产物；验收：能证明所有阶段产物的生成基线。
2. **先评订单 DWD**：围绕 `problem_0327`、`0877`、`0992`、`0993`、`1000`、`1003`，用 File / Statement / Table Key 串联 SQL 与上下游；验收：每个判断可指出规则、具体字段/语句、支持与反例。
3. **业务事实确认**：由电商 owner 填写订单事件、键、金额、退货、状态、`ds`、默认值和权威表定义；验收：事实来源、责任人、版本/生效日期、确认状态明确，候选假设不混为事实。
4. **执行受控数据验证**：业务批准访问后，对业务键唯一性、维表 JOIN 基数、目标写入前后记录数和指标对账作受控查询；验收：明确验证分区/样本、结果、SQL 和责任人。
5. **分开裁决 Problem 与 Finding**：在人工清单填写支持/反例、业务依据与状态；验收：机器 candidate 不自动变成 confirmed，未检查与因证据不足保持独立。
6. **文档基线更新**：修正文档中过期统计并明确每个数字对应哪份产物/基线；验收：方法和执行文档不把旧数字宣称为当前值。

## 9. 审查引用索引

- Snapshot：`source/manifest.json`、`source/dataworks/workspaces-index.json`、`source/dataworks/workspaces/*/files-index.json`、`source/maxcompute/workspaces/*/tables-index.json`
- Inventory / Scope：`analysis/inventory/{workspaces,files,tables,columns}.json`、`analysis/scope/summary.json`、`analysis/scope/inputs/{sql-candidates,excluded-tasks}.json`、`analysis/scope/review-tasks.json`
- Evidence：`analysis/evidence/sql/{statements,table-references,parse-errors}.json`、`analysis/evidence/errors.json`、`analysis/evidence/layer/assessments.json`、`analysis/evidence/lineage/table-lineage.json`、`analysis/evidence/profiling/{tables,columns}.json`
- Understanding：`analysis/understanding/business/{tables,grain-candidates,processes,objects-registry}.json`、`analysis/understanding/modeling/{fact-candidates,dimension-candidates,fact-dimension-relationships}.json`
- Review / Coverage：`analysis/review/current-state-findings.json`、`analysis/review/current-state-problems.json`、`analysis/review/current-state-problem-evidence.json`、`analysis/review/evidence-coverage.json`
- 人工状态：`analysis/review/current-state-problem-review-checklist.md`、`analysis/review/current-state-review-checklist.md`、`analysis/understanding/business/grain-review-checklist.md`、`analysis/understanding/modeling/model-review-checklist.md`
- DWD 原始 SQL：`source/dataworks/workspaces/466337/content/504340559__dwd_ecom_order_detail_info_bu.sql`
- 阶段、安全与旧基线说明：`docs/STAGE_INDEX.md`、`docs/CURRENT_STATE_EVIDENCE_MAP.md`、`docs/COMMANDS.md`、`docs/M36_PROBLEM_ASSESSMENT.md`、`docs/M36_HUMAN_ADJUDICATION_GUIDE.md`

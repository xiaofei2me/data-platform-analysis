# Data Platform Analysis：模型问题识别差距矩阵

## 目的与证据口径

目标链路为 Inventory → Scope → Evidence → Understanding → Review。最终问题必须保持机器候选、业务确认事实和人工裁决之间的边界；“未产生 Finding”不代表模型正确。

本矩阵依据当前代码、契约、测试及本地 `analysis/` 产物只读核查。下文产物数量是核查时磁盘上已有文件的统计，不是本轮重新运行的结果，也没有可证明这些文件由当前代码版本生成的 run manifest。`source/` 未修改，生产 `analysis/` 未清场、未覆盖。

## 差距矩阵

| # | 问题类别 | 需要的证据 | 当前实现与产物 | 能识别到什么 | 主要缺口 / 所需输入 | 优先级与验收标准 |
|---|---|---|---|---|---|---|
| 1 | 分层职责及跨层依赖 | 已批准的层级职责、表层级、边方向、任务依赖 | Layer 对 3,724 张表给出 MATCH/UNKNOWN；Lineage 有 3,384 条表级边 | 可发现未知层级、跨层候选依赖和来源/目标；不能仅凭层级或命名判错 | 需业务/数仓团队确认层级职责；补充任务级依赖证据以区别 SQL 引用与调度依赖 | P1；跨层规则有来源、责任人和测试，确认前只标记候选 |
| 2 | 业务过程建模 | 已确认的过程定义、输入/输出对象、事件边界及生命周期 | Understanding 产出过程、对象及关系候选，依赖规则词汇和技术信号 | 可形成可解释候选，不能确认过程边界完整或模型确实承载该过程 | 收集正式过程定义和责任人；把确认事实与机器候选分开 | P1；候选有来源证据，业务确认前不得升级为事实 |
| 3 | 事实粒度 | 业务事件定义、主业务键、时间语义、重复/更正规则 | Grain 候选使用字段、SQL、Lineage 等信号；当前有 5,678 条候选 | 能发现候选键组合差异和潜在粒度冲突 | 无已确认的业务粒度、主键约束及行级样本；候选组合不等于冲突结论 | P0；输出候选及证据，确认后才能判定 grain 问题 |
| 4 | 重复建模与逻辑重复 | 同义对象定义、SQL 表达式/过滤/聚合等语义、消费场景 | Review 有 MODEL_DUPLICATION / MODEL_OVERLAP 等 Finding 与 Problem 候选 | 能按对象、字段、过程、候选粒度和结构相似性发现待复核组 | 缺少 SQL 语义归一与确认业务等价关系；高相似不等于重复 | P1；候选保留被比较表、规则理由、SQL 及人工裁决 |
| 5 | 字段、类型、业务键和结构 | Schema、约束、字段定义、键唯一性、NULL/取值域及版本变化 | Inventory 有 102,703 个字段的元数据；Understanding 可形成角色/键候选 | 可对照当前结构和字段元数据，提出业务键/度量等候选 | 无约束目录、业务字段定义与行级验证；数据类型存在不等于业务语义成立 | P1；问题需定位表/字段并引用 Schema 与已确认定义 |
| 6 | JOIN、过滤、聚合、去重、时间处理 | SQL AST、连接键与基数、过滤条件、聚合粒度、去重顺序、时区/有效期语义 | SQL 解析当前产出语句及表级引用；Lineage 可追踪表输入/输出 | 能确认哪些 SQL 语句引用哪些表；不能可靠判断加工逻辑正确性或字段级影响 | 需要逐步扩展 SQL AST 语义提取、列级血缘及规则测试；依赖业务定义解释口径 | P0；选定 SQL 方言样本逐项验证 JOIN/WHERE/GROUP BY/去重/时间语义和失败状态 |
| 7 | 业务口径、状态与指标一致性 | 已确认业务事实、指标公式、状态生命周期、排除条件、有效期 | `config/business-rules.yaml` / `process-rules.yaml` 是候选词汇规则；已有业务事实模板，无配置消费入口 | 能形成语义候选，不能证明不同 SQL 的指标口径一致 | 需要业务责任方确认事实；部分事实适合结构化供 Understanding 消费，其他事实仅用于人工评审 | P0；仅已确认且有版本/责任人的事实进入配置；候选不得伪装为正式口径 |
| 8 | 上下游依赖、来源缺失和血缘异常 | SQL 引用、Inventory 身份、跨项目映射、任务调度依赖及外部资产目录 | 表级 Lineage 由 SQL Table References 与 Inventory/Layer 对齐；可保留未知端点和跨 Workspace 身份 | 可追踪已解析表级引用及部分异常；不等于完整调度 DAG，未解析引用不能直接归因业务缺失 | 需补充任务级依赖/外部表身份，并把未解析与技术失败传递到 Review | P1；未知引用、未知层级、跨项目和缺输入都有独立状态与原始引用 |
| 9 | 实际数据质量 | 行级分布、空值率、唯一性、合法值域、时效性及历史波动 | Profiling 明确为 `metadata_only`，覆盖表/字段元数据，不读取业务行 | 可核对元数据、字段注释及分区等技术信息 | 不能发现实际行数据重复、空值、异常分布或口径污染；需授权的安全样本/画像输入 | P1（依赖数据访问审批）；明确数据来源与隐私边界，增加合成及受控样本测试 |
| 10 | 证据不足、未检查与技术失败 | 各阶段输入资格、完成/失败状态、未知引用、产物身份/版本、Review 关联 | Scope 区分整体与 SQL 资格；Evidence 有错误账本；本轮新增只读 Coverage Ledger，连接逐 File SQL 状态和逐 Table 证据 / Review 状态 | 能区别排除、分析完成、无语句、技术失败、未解析引用、证据不足及人工裁决；可选阶段输入缺失会显示不可用，不计作 0 或已检查 | 当前无自动运行 provenance；部分传统 Finding 未直接携带 SQL Reference / Profiling 引用；Ledger 尚未内建代码版本 / Snapshot 哈希 provenance | P0；小型契约测试与临时真实全链路均通过；后续补充可复核的运行 provenance |
| 11 | 业务理解与可解释性 | 可追溯的表用途、来源与去向、SQL 转换、对象 / 过程 / 粒度候选、关键字段角色和未知项 | Understanding 有对象 / 关系 / 过程 / 粒度 / Fact / Dimension 候选；证据主要由 Schema、SQL table reference、Lineage 和词典规则提供 | 可生成技术依据支持的候选及待确认信号；不能证明业务对象 / 过程 / 粒度、字段含义或指标口径已被确认 | 缺少逐表面向非业务专家的解释、SQL 字段级转换说明、反例 / 替代解释和明确可回答的业务未知项；词典命中不能作正式业务事实 | P0/B；先对一张真实 DWD 样本编制证据导航和未知项，不新增猜测规则；验收时明确事实 / 推断 / 未知三类 |

## Evidence 模块现状与具体工作

以下数量来自核查时本地已有产物，只用于定位覆盖情况：

| 模块 | 当前输入 / 产物 | 当前统计 | 主要验收缺口 |
|---|---|---:|---|
| Layer | Inventory Tables + `config/layer-rules.yaml` → `evidence/layer/assessments.json` | 3,724 assessments；3,663 MATCH、61 UNKNOWN | 保留 UNKNOWN 原因；跨层使用已批准的职责规则，而不是把 UNKNOWN 或前缀差异变成问题结论 |
| SQL | Scope `sql_eligible` Files → Statements、Table References、Parse Errors | 541 个 SQL 候选；1,917 statements；1,241 references；当前 parse error 产物为空 | 补充加工语义和字段级证据；汇总每个 eligible File 是否完成及错误，而不是只有总数 |
| Lineage | SQL Table References + Inventory 身份 + Layer candidate → 表级 edges | 3,384 edges | 把 unresolved / cross-project / unknown-layer 分开统计并保留语句身份；明确不是任务级 DAG |
| Profiling | Inventory Tables / Columns → metadata-only profiles | 3,724 tables、102,703 columns | 报告持续声明未读取行数据；不得据此声称数据质量已通过 |

本地已有 Understanding 产物包括 3,724 张表记录、5,678 个 Grain Candidate、3,363 个 Fact Candidate 和 5 个 Dimension Candidate。Review 产物包括 3,724 张表、4,425 个 Finding、1,186 个 Problem Candidate（1,144 candidate、42 review_required）；这些均不是人工确认问题。核查时 `evidence/errors.json` 及 SQL parse errors 为空，但并不证明其他时间/版本也无错误。

以上数量是实现前只读查看的本地分析文件快照，只用于说明本轮实现前的检查基线；不能替代本轮运行结果。真实验收数字记录在下方隔离运行表中。除分析表格和候选外，Coverage 不改变 Evidence 模块的既有算法。

## Review 问题识别能力与缺口

- Current-State Model Review 将 Table/Column、Layer、Lineage、Understanding 候选组合为 Finding；Problem Assessment 聚合 Finding、保留 Problem Evidence 并写候选/人工回填状态。
- 当前机器产物使用 candidate / review_required；确认或驳回来自人工清单。Problem severity、priority、evidence strength 是不同维度，不应合并成“置信分”。
- Finding 可追溯表和候选信号；但 Review 的输入契约未直接读取 SQL Table References 或 Profiling。因此目前不能保证每条 Problem 都携带具体 SQL 语句，也不能把 metadata-only profile 描述为数据质量验证。
- 单条 Problem 的 Evidence 有样本上限；`evidence_total` / `evidence_truncated` 必须继续与样例一起展示，完整证据需能从源产物定位。
- 本轮新增 `analysis/review/evidence-coverage.json`：逐文件呈现 Scope / SQL 完成状态，逐表关联 Layer、SQL 引用、Lineage、metadata-only Profiling、Understanding 候选及 Finding / Problem ID。Coverage 由 `pipeline.run_stage_review()` 在 Review 输出完成后写出；必须输入缺失显式失败，可选上游文件缺失则记录不可用状态。它不推断业务事实、不改变 Finding / Problem 规则。
- Coverage 目前提供表级 SQL Table Reference 导航，不会将 Reference 自动复制成 Problem Evidence；单条 Problem 的既有证据内容及 50 行截断契约保持不变。真实运行还需确认 statement 身份与原始产物可定位。

## 业务解释能力：已有 / 缺失 / 确认依赖

| 能力 | 当前具备 | 尚缺 / 需要的输入 | 本轮边界 |
|---|---|---|---|
| 表对象 / 过程 / 粒度 / Fact / Dimension 候选 | Understanding 对已有技术产物与候选词典生成候选；Candidate 带候选来源 | SQL 字段级变换、反例 / 替代解释、实际数据验证与责任方确认 | 不将名称 / 词典命中改写成业务事实 |
| 关键字段、源头、下游 | Inventory Schema、Table References、表级 Lineage 可关联 | 业务键约束、字段语义、DataWorks 调度 DAG、消费场景 / 指标使用 | Coverage 补充定位，不声称字段级血缘或调度依赖 |
| 业务未知项 | 业务事实采集模板和已知事实清单已有入口 | 业务团队提供正式定义、范围、指标口径、例外、责任人和生效版本 | 未确认输入不进入规则结论；本轮不伪填事实 |
| 面向不熟悉业务者的解释 | 当前报告解释机器候选和技术信号 | 一张样本表的用途假设、SQL 转换、记录粒度候选及具体未知问题仍需人工整理 | 本轮以真实 DWD 追溯检查现有解释，不扩建通用解释框架 |

业务事实应在有事实 ID、责任团队、确认状态和有效版本之后，再逐项决定是否以已确认配置供 Understanding 消费；仅适合人工裁决的例外或上下文可留作评审依据。配置接入不得改变 Snapshot，也不引入新的配置引擎。

## DWD 端到端验证样本

本轮在隔离目录使用当前代码及当前 `source/` Snapshot 重新生成链路，选择 `dme_cdm.dwd_ecom_order_detail_info_bu`；选择标准是有目标写入 SQL、输入 / 输出引用、上游与下游边以及 Review 候选可追踪。选择不代表认定该模型存在问题。下表统计均来自本轮临时产物。

| 阶段 | 当前可追溯证据 | 限制 / 需要确认 |
|---|---|---|
| Inventory / Scope | Workspace `466337`；70 字段；全局 4,657 Files；541 个 SQL eligible Files。目标表关联到本表的 29 条 Table Reference | Inventory Schema 是 Snapshot 技术元数据，不提供受约束业务键 |
| SQL | File `504340559`、statement 7 以 `insert overwrite` 写入目标；选择 `temp_02` / `temp_03`、客户与门店主数据，通过 `shop_id`、`store_code`、`customer_code`、`bu_2` 关联，并执行字段映射、`NVL` 默认值及 `ds` 分区写入 | 该 SQL 证明实现表达式，不证明 JOIN 基数、过滤完整性、源数据唯一性或业务口径正确；源代码注释只是技术/业务线索，仍需确认 |
| Layer / Lineage | 本轮 Layer `MATCH`，Candidate Layer=`DWD`、Workspace Layer=`CDM`；31 边（4 入、27 出），含 4 个上游和跨 Workspace `dme_ads` 消费者 | 命名/规则给出候选分层，不等于正式层级职责验收；Lineage 是 SQL 表级引用而不是 DataWorks 调度 DAG |
| Profiling | 70 列 profile，`metadata_only`、无数据样本，`row_level_data_analyzed=false` | 未检查真实行级空值、重复、金额分布及键唯一性 |
| Understanding | DWD 子层、Core、FACT / TRANSACTION 均为机器候选；4 个 grain candidates：`order_no`、`sub_order_no`、`customer_code + order_no`、`customer_code + sub_order_no`；有 33 个 Fact Candidate 引用该表 | 候选来自 Schema/规则信号；键不能直接认定主键或业务粒度 |
| Review | 10 Findings（1 grain conflict、4 duplicate_fact、5 overlapping_fact），8 个关联 Problem Candidate；状态全为 candidate，无 confirmed/rejected | 为粒度、模型相似和重复关系候选；不得视作已确认问题；其中 Problem 聚合范围可含多表、多条 SQL/候选，需要人工核对其证据定位 |

### 对不熟悉业务使用者的证据化解释

- **可能用途**：一条实现 SQL 将电商订单来源字段、商品/客户/门店属性映射到 DWD 候选表，供若干 DWD / ADS SQL 引用。依据是目标写入语句、70 列 schema 与 4 入 / 27 出表级 Lineage；这只是技术用途候选。
- **可能记录含义**：候选为交易 / 订单明细，但当前候选键冲突覆盖订单号与子订单号等组合。SQL 是投影加 JOIN，没有 `GROUP BY` 或 `DISTINCT`；仅凭 SQL 不能证明实际行粒度或某个键唯一。
- **SQL 转换观察**：目标 statement 7 将 `temp_02` 的别名 `a` 作为主要字段来源；左连接 `temp_03 b` 补充业务线字段；从分区快照选取门店 / 客户主数据；将 `store_code` 投影为 `shop_id`，并对门店、平台及权限字段使用 `NVL` 默认值；把 `ds` 写入目标分区。由于目标和部分 join 字段映射依赖宏及上游 SQL，仍需追溯完整作业链及实际数据检查。
- **现有技术事实**：目标表和 70 个字段存在；有明确目标写入 SQL、源 / 目标 Table References、上游 / 下游 SQL 引用；Lineage 31 条；Profiling metadata-only。
- **推断候选**：DWD、Core、Fact、transaction 明细以及重复 / 粒度风险；没有一项是业务团队已确认事实。
- **未知 / 验证问题**：`order_no` 与 `sub_order_no` 哪个定义业务事件唯一性，客户码是否参与粒度；`temp_02` 是否已按订单明细去重；`temp_03` 和客户 / 门店维表连接键是否唯一；`NVL(..., 'Others')` 是否掩盖未知主数据；金额、退货与更正如何定义净额 / 历史状态；`ds` 表示业务日还是装载分区。可先检查上游 SQL 与受控样本的 JOIN 前后基数、键重复和金额对账，再请订单过程与指标责任方确认口径。
- **当前决策**：证据足以开展业务评审与技术调查，不足以批准保留 / 修正 / 拆分 / 合并 / 重建，也不足以设计正式 DWS 粒度或指标。

### 本轮 Coverage Ledger 验收（临时隔离运行）

运行顺序为 `analyze --stage inventory` → `evidence` → `understanding` → `review`；4 条命令均退出码 0。输出留在会话隔离目录，不是生产 `analysis/`。

| 统计 | 本轮实际结果 | 来源与口径 |
|---|---:|---|
| Inventory Files / Tables / Columns | 4,657 / 3,724 / 102,703 | 本轮临时 `inventory/*.json` |
| Scope SQL eligible / excluded / review required | 541 / 4,116 / 70 | 本轮 `scope/inputs/*.json` 与 `scope/review-tasks.json` |
| SQL analyzed / failed / no statements | 541 / 0 / 0 | 逐 File Ledger 状态；排除 4,116 不计失败 |
| SQL statements / Table References | 1,917 / 1,241 | 本轮 `evidence/sql/*.json` |
| SQL technical / parse errors / unresolved table operands / cross-project table operands | 0 / 0 / 32 / 1,574 | 错误账本与逐引用 Inventory 对齐结果；跨 Project 数字按 source/target 引用端点计数（同一 SQL reference 可计多端点），含可解析与未解析引用 |
| Lineage edges / cross-Workspace / unknown endpoint / unknown layer endpoint | 3,384 / 1,534 / 38 / 43 | 本轮 `evidence/lineage/table-lineage.json` |
| Layer MATCH / UNKNOWN | 3,663 MATCH / 61 UNKNOWN | 本轮 `evidence/layer/assessments.json`；与只读旧产物摘要一致，以当前代码运行结果为准 |
| Profiling | 3,724 tables / 102,703 columns，全为 `metadata_only` | 不读取行数据，`row_level_data_analyzed=false` |
| Review Tables / Findings / Problems | 3,724 / 4,425 / 1,186 | 本轮 Review JSON；Problem：1,144 candidate、42 review_required、confirmed=0、rejected=0 |
| Review 表状态（3,724 张 Inventory Table 为分母） | 3,345 problem_candidate / 294 insufficient_evidence / 85 no_finding_under_implemented_rules | 本轮 Coverage Ledger；最后一类只表示当前实现规则未产生 finding/problem，不能视为模型正确 |
| DWD 样本 Review | 10 Findings / 8 Problem Candidates | Ledger 与原始 Finding / Problem 通过 ID 连接；零确认问题 |

Coverage Ledger 当前版本能显式区分 Scope 排除、SQL 分析/失败/无语句/缺输入、未知引用、Lineage 未知端点、metadata-only Profiling、Finding/Problem 与人工状态。它不把每一条 SQL Reference 强行附加为 Problem Evidence，也不生成字段级血缘或调度 DAG；Problem 如需 SQL 级因果判断，仍须从其 Finding / 表范围人工导航到 Ledger 中 statement identity 与 SQL 原文。这里的“已检查无 Finding”只能解释为“现有实现规则未产出”，不能据此判断模型正确。

## 分阶段实施与验收标准

1. **P0：覆盖账本（当前实施）** — 输出逐文件资格与 SQL 完成/失败状态、逐表证据引用和 Review 状态；每个计数来自明确产物；空 Finding 只能标记为“当前规则未产出”，未知/失败/未纳入各自独立。用小型隔离 fixture 测试，并在临时输出完整跑通。
2. **P0：真实 DWD 复核** — 在隔离目录用当前代码生成完整阶段产物；核对样本身份、字段、SQL statement/ref、边、候选、Finding、Problem。验收：引用可双向定位，所有候选有理由和状态，无业务事实臆断。
3. **P0：业务事实输入接线** — 业务负责人先填写已知事实模板；评估逐条事实由配置供 Understanding 消费或只供 Review 人工参考。验收：事实 ID/版本/责任人/确认状态可追溯；未确认事实不会改变规则结论。
4. **P1：SQL 加工语义证据** — 先覆盖当前方言下 JOIN、条件、聚合、去重、时间函数及 CTAS；对无法解析部分产生明确状态。验收：statement / table / column 身份可追溯，针对每类写正反例和 parse failure 测试。
5. **P1：问题与影响报告** — 输出逐条 Problem 的分类、severity、priority、evidence strength、状态、上下游影响及前置业务确认问题；统计 confirmed / candidate / insufficient / rejected 分开。验收：候选不升级为确认，Finding 聚合不丢证据，截断提示完整。
6. **P1/P2：依赖和数据质量** — 先由平台/安全团队批准任务 DAG 和受控行级数据来源，再实现任务级依赖与数据质量画像。验收：未获授权时明确“不具备证据”；样本/分布结果能回溯输入范围且不改 Snapshot。

## 产物安全约束与本轮运行隔离

代码中的 `pipeline._reset_outputs()` 会删除 `inventory/`、`scope/`、`evidence/`、`understanding/`、`review/` 和根 `summary.md`；目前只将 `PRESERVED_CHECKLIST_FILES` 中登记的 5 份人工清单快照恢复。其他机器产物会被重建；不属于保护清单的人工内容不能假定安全。Stage 06–14 单独重跑不清场，但 Review 会覆盖当前 Review 的机器产物并 carry over 两份正式清单的人工列。

因此真实全链路验收使用独立 `ANALYSIS_DIR`，明确指向当前仓库 `source/` 只读 Snapshot；不对生产 `analysis/` 执行清场，不把新生成 Ledger 写回生产目录。运行前后将对 `source/` 与生产 `analysis/` 做只读校验，临时结果仅作为本轮代码的实测产物。

## 可进入业务验收的判断

可以开始 Understanding / Review 的**业务事实与候选逐条评审**，不能将当前产物称为完成了业务问题验收，也不能据此批准 DWD 改造或 DWS 指标口径。最短下一步是：由订单过程与指标责任方确认该表的事件粒度、业务键、时间含义、退货/更正规则和销售指标口径，并按事实模板记录；数仓团队并行核验上游 JOIN 键唯一性、`temp_02` 去重和目标分区语义。确认前，当前 8 条仍为 Problem Candidate，不应作为 DWD 整改决定。

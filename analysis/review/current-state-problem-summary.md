# M3.6 v2 Current-State Problem Assessment

## 1. Scope

- Finding：4425
- Problem candidate：1186（P0=698，P1=379，P2=94，P3=15）
- 受影响表（去重）：3345
- Finding 覆盖：进入 problem 的 finding 4414 / 4425，未进入 problem 11
- 证据行：30132（单 problem 上限见 evidence 产物）
- problem candidate 是 Finding 聚合后的候选问题：Finding Count ≠ Problem Count ≠ Confirmed Problem Count；机器不自动把任何 problem 变成 confirmed。
- 本阶段只读 M1–M3.6 产物：不读 `source/` / profiling / SQL 参考，不调 LLM / 外部 API，不修改任何上游产物。

## 2. Problem Distribution

| problem_type | title | default priority | problems |
| --- | --- | --- | --- |
| GRAIN_PROBLEM | 粒度问题 | P0 | 559 |
| MODEL_OVERLAP | 模型重叠 | P1 | 27 |
| MODEL_DUPLICATION | 模型重复 | P1 | 318 |
| MIXED_RESPONSIBILITY | 职责混杂 | P1 | 199 |
| MODEL_ROLE_AMBIGUITY | 角色歧义 | P0 | 4 |
| PROCESS_MODEL_ALIGNMENT | 过程与模型对齐 | P2 | 15 |
| AGGREGATION_MODEL_PROBLEM | 聚合模型问题 | P1 | 22 |
| FACT_IDENTIFICATION_PROBLEM | 事实识别问题 | P1 | 26 |
| DIMENSION_IDENTIFICATION_PROBLEM | 维度识别问题 | P2 | 1 |
| MODEL_SELECTION_AMBIGUITY | 模型选择歧义 | P1 | 8 |
| SEMANTIC_AMBIGUITY | 语义歧义 | P1 | 3 |
| MODEL_COVERAGE_GAP | 过程覆盖缺口 | P0 | 2 |
| UNKNOWN_MODEL | 未定模型 | P2 | 2 |

| status | problems |
| --- | --- |
| candidate | 1144 |
| review_required | 42 |
| confirmed | 0 |
| rejected | 0 |

- 当前状态分布：candidate=1144，review_required=42，confirmed=0，rejected=0；机器阶段只会写 candidate / review_required，confirmed / rejected 只能来自清单回填。

## 3. Impact & Root Cause

| impact_type | title | problems |
| --- | --- | --- |
| GRAIN_INCONSISTENCY | 同一语义存在多种粒度口径 | 559 |
| DUPLICATED_MODEL | 同一业务语义存在多个模型 | 318 |
| QUERY_COMPLEXITY | 取数需要在多个相似模型间判断 | 50 |
| MODEL_SELECTION_DIFFICULTY | 消费者难以选择正确模型 | 374 |
| METRIC_AMBIGUITY | 指标口径可能不一致 | 610 |
| MAINTENANCE_COST | 同一语义需多处维护 | 539 |
| REUSE_DIFFICULTY | 模型难以复用 | 1 |
| GOVERNANCE_DIFFICULTY | 治理与口径追踪困难 | 201 |
| ANALYTICAL_RISK | 分析结果可能基于错误模型 | 28 |
| DATA_CONSUMER_CONFUSION | 数据使用者认知负担高 | 7 |
| AI_SEMANTIC_RISK | AI / 语义层消费时易误选模型 | 3 |

| root_cause | title | problems |
| --- | --- | --- |
| MULTIPLE_GRAINS_IN_ONE_MODEL | 同一模型内存在多种粒度 | 559 |
| DUPLICATED_MODEL_PIPELINES | 同一业务口径存在重复加工链路 | 117 |
| LAYER_RESPONSIBILITY_OVERLAP | 分层职责重叠 | 17 |
| BUSINESS_AND_ANALYTICAL_RESPONSIBILITY_MIX | 业务与分析职责混杂 | 26 |
| MULTIPLE_SOURCE_SYSTEM_REPLICATION | 多来源系统复制 | 97 |
| INSUFFICIENT_BUSINESS_MODEL_STANDARDIZATION | 业务模型标准化不足 | 142 |
| AGGREGATION_AND_ATOMIC_DATA_MIX | 聚合与原子数据混放 | 186 |
| UNRESOLVED_MODEL_ROLE | 模型角色未裁决 | 4 |
| FACT_GATE_MEASURE_DEPENDENCY | 事实闸门依赖度量字段 | 26 |
| UNKNOWN | 现有证据不足以判断 | 12 |

- impact / root_cause 是从问题类型与证据结构推导的候选结论，不是已确认的业务根因；裁决权在人工清单。

## 4. Priority & Evidence

| priority | severity | title | problems |
| --- | --- | --- | --- |
| P0 | critical | 直接影响后续模型设计，必须优先确认 | 698 |
| P1 | high | 高价值模型问题 | 379 |
| P2 | medium | 一般模型问题 | 94 |
| P3 | info | 信息性发现 | 15 |

| evidence_strength | problems |
| --- | --- |
| weak | 33 |
| moderate | 20 |
| strong | 1133 |

| classification | problems |
| --- | --- |
| confirmed_conflict | 548 |
| possible_conflict | 11 |
| review_required | 9 |
| duplication_candidate | 109 |
| technical_copy_candidate | 97 |
| structural_overlap | 17 |
| grain_identical_structure_divergent | 122 |
| review_required | 9 |
| model_problem | 13 |
| NO_EVIDENCE | 1 |
| NO_ANCHOR | 1 |

| evidence_type | rows |
| --- | --- |
| FINDING | 6300 |
| TABLE | 9158 |
| COLUMN | 4223 |
| PROCESS | 1206 |
| GRAIN | 8052 |
| OBJECT | 9 |
| SQL | 0 |
| LINEAGE | 1172 |
| RELATIONSHIP | 12 |

- SQL 证据恒为 0：本阶段不读 SQL 产物。

## 5. Top Problems

| problem_id | priority | problem_type | scope_key | tables | evidence_strength | root_cause | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| problem_0050 | P0 | GRAIN_PROBLEM | dme_ads.dwd_crm_member_item | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0051 | P0 | GRAIN_PROBLEM | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0052 | P0 | GRAIN_PROBLEM | dme_ads.dwd_pg_online_pos_douyin_temp00 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0053 | P0 | GRAIN_PROBLEM | dme_ads.dwd_pg_online_pos_tms_temp00 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0054 | P0 | GRAIN_PROBLEM | dme_ads.ke24_data_tmp_test | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0055 | P0 | GRAIN_PROBLEM | dme_ads.pro_sell_out_temp | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0056 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0057 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts1 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0058 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts1_tmp | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0059 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts_v2 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0060 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts_v2_tmp1 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0061 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts_v2_tmp2 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0062 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts_v2_tmp5 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0063 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts_v2_tmp8 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0064 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts_v3_tmp1 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0065 | P0 | GRAIN_PROBLEM | dme_ads.tb_actual_data_bts_v3_tmp2 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0066 | P0 | GRAIN_PROBLEM | dme_ads.tb_competitor_ecom_promotion_detail_info | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0067 | P0 | GRAIN_PROBLEM | dme_ads.tb_consumer_ecom_sku_order_sales | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0068 | P0 | GRAIN_PROBLEM | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp3 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |
| problem_0069 | P0 | GRAIN_PROBLEM | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp4 | 1 | strong | MULTIPLE_GRAINS_IN_ONE_MODEL | candidate |

只列出前 20 行，共 1186 行；完整明细见 `analysis/review/current-state-problems.json`。

- 排序依据：priority → problem_type → scope → scope_key（稳定排序，不含随机抽样）。每条 problem 的 current_state / problem / evidence / impact / why_change 见该文件的 `rationale` 字段。

## 6. Human Review & M4 Input

回填 `analysis/review/current-state-problem-review-checklist.md` 的 human_status / human_name / note 后重跑本阶段即可保留人工输入；机器列由 `analyze --stage review` 生成，重跑会被覆盖。

- human_status → status 映射：pending → candidate，confirmed → confirmed，rejected → rejected，needs_review / needs_discussion → review_required；未识别的取值按未回填处理并输出警告。
- 每个分区最多列出 50 行，完整明细见 `analysis/review/current-state-problems.json`。

可以带入 M4 的输入：

- 带证据链的 problem candidate 与优先级（`current-state-problems.json`）。每条含 evidence / impact / root_cause / rationale。
- 逐条证据明细（`current-state-problem-evidence.json`）。
- 回填后的人工结论（`current-state-problem-review-checklist.md`）。

不能带入 M4 的内容：

- 未经人工确认的 problem；finding ≠ problem ≠ confirmed，三者计数互不等价。
- 机器推导的 root_cause 与 impact：它们是候选，不是已确认的业务根因。
- 任何 Target DWD / DWS / Semantic Layer 结论：本阶段不设计目标模型。

- 建议顺序：先处理 P0=698，P1=379，P2=94，P3=15 中的 P0（粒度、角色、覆盖缺口），再处理 P1（重复 / 重叠 / 聚合），最后看 P2 / P3。
- 进入 M4 前至少需要：problem candidate 是 Finding 聚合后的候选问题：Finding Count ≠ Problem Count ≠ Confirmed Problem Count；机器不自动把任何 problem 变成 confirmed；P0 problem 必须有人工结论。

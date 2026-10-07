# M3.5 Fact / Dimension Candidate Analysis

## 1. Overview

- Inventory 表数量：3719
- 输入 grain candidate 数量：5679
- Process candidate 数量：17（人工已确认 0）
- Fact Gate：通过 3364，未通过 2315（no_measure_evidence=2315）
- Fact candidate 数量：3364（candidate=3364，confirmed=0，rejected=0，needs_discussion=0）
- fact 的 grain_pattern 分布：transaction=476，snapshot=43，event=0，periodic=934，aggregation=1730，unknown=181
- Dimension candidate 数量：5（candidate=5，confirmed=0，rejected=0，needs_discussion=0；role：candidate=1，ambiguous=4）
- Fact ↔ Dimension relationship 数量：15979（candidate=15979，confirmed=0，rejected=0，needs_discussion=0）
- fact → table 行数：15697（anchor=3364，supporting=12333）
- dimension → table 行数：7195（anchor=695，supporting=6500）
- evidence matrix 行数：3369（fact + dimension，关系证据见 relationship 产物）
- 覆盖 process 数量：15，覆盖表数量：1282，覆盖 Object 数量：4
- Profiling：is_candidate_key=true 的列 0，metadata_only 列 102603 / 102603（metadata-only，不伪造行级唯一性）
- 输入：`/Users/flynnho/Work/active/002-henkel/02.technical-service-project/03-projects/data-platform-analysis/analysis`

本报告只产出 **Fact / Dimension Candidate**：候选来自 M3.4 grain candidate 与 M3.1 Object，status 恒为 candidate（fact / dimension candidate 不是 confirmed 模型）。机器阶段不写 confirmed，确认必须回填清单后重跑。

## 2. Fact Candidates

- Fact Gate 规则：transaction / event / snapshot 直接通过；periodic / aggregation / unknown 必须有 measure 字段，否则记 `missing_measure_evidence`，该 grain candidate 不生成 fact。

| grain_pattern | fact candidates |
| --- | --- |
| transaction | 476 |
| snapshot | 43 |
| event | 0 |
| periodic | 934 |
| aggregation | 1730 |
| unknown | 181 |

| fact_key | process | grain | pattern | tables | objects | strength | unresolved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fact_candidate_001 | process_candidate_001 | grain_candidate_001 | aggregation | 2 | product | strong | - |
| fact_candidate_002 | process_candidate_001 | grain_candidate_002 | unknown | 1 | - | strong | insufficient_grain_evidence, ambiguous_grain, missing_object_evidence |
| fact_candidate_003 | process_candidate_001 | grain_candidate_003 | aggregation | 2 | product | strong | - |
| fact_candidate_004 | process_candidate_001 | grain_candidate_004 | transaction | 1 | order | strong | ambiguous_grain |
| fact_candidate_005 | process_candidate_001 | grain_candidate_005 | transaction | 1 | order | strong | ambiguous_grain |
| fact_candidate_006 | process_candidate_001 | grain_candidate_006 | aggregation | 1 | product | strong | - |
| fact_candidate_007 | process_candidate_001 | grain_candidate_008 | unknown | 1 | - | strong | insufficient_grain_evidence, ambiguous_grain, missing_object_evidence |
| fact_candidate_008 | process_candidate_002 | grain_candidate_011 | aggregation | 2 | customer | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence |
| fact_candidate_009 | process_candidate_002 | grain_candidate_012 | aggregation | 2 | customer | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence |
| fact_candidate_010 | process_candidate_002 | grain_candidate_013 | aggregation | 2 | customer | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence |
| fact_candidate_011 | process_candidate_002 | grain_candidate_014 | aggregation | 2 | customer | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence |
| fact_candidate_012 | process_candidate_002 | grain_candidate_015 | transaction | 1 | order | strong | ambiguous_grain |
| fact_candidate_013 | process_candidate_002 | grain_candidate_016 | transaction | 1 | order | strong | ambiguous_grain |
| fact_candidate_014 | process_candidate_004 | grain_candidate_021 | transaction | 5 | customer、order | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_015 | process_candidate_004 | grain_candidate_022 | transaction | 5 | customer、order | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_016 | process_candidate_004 | grain_candidate_023 | transaction | 1 | order、product | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_017 | process_candidate_004 | grain_candidate_024 | transaction | 1 | order、store | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_018 | process_candidate_004 | grain_candidate_025 | transaction | 6 | order | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_019 | process_candidate_004 | grain_candidate_026 | transaction | 1 | order、product | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_020 | process_candidate_004 | grain_candidate_027 | transaction | 1 | order、store | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_021 | process_candidate_004 | grain_candidate_028 | transaction | 6 | order | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_022 | process_candidate_004 | grain_candidate_030 | snapshot | 3 | customer | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_023 | process_candidate_004 | grain_candidate_031 | snapshot | 3 | customer | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_024 | process_candidate_004 | grain_candidate_032 | snapshot | 2 | customer | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_025 | process_candidate_004 | grain_candidate_033 | snapshot | 2 | - | strong | ambiguous_grain, missing_measure_evidence, missing_object_evidence |
| fact_candidate_026 | process_candidate_004 | grain_candidate_034 | snapshot | 2 | - | strong | ambiguous_grain, missing_measure_evidence, missing_object_evidence |
| fact_candidate_027 | process_candidate_004 | grain_candidate_035 | snapshot | 2 | - | strong | ambiguous_grain, missing_measure_evidence, missing_object_evidence |
| fact_candidate_028 | process_candidate_004 | grain_candidate_036 | snapshot | 3 | customer | strong | ambiguous_grain |
| fact_candidate_029 | process_candidate_004 | grain_candidate_037 | snapshot | 3 | customer | strong | ambiguous_grain |
| fact_candidate_030 | process_candidate_004 | grain_candidate_038 | snapshot | 2 | customer | strong | ambiguous_grain |
| fact_candidate_031 | process_candidate_004 | grain_candidate_039 | snapshot | 2 | - | strong | ambiguous_grain, missing_object_evidence |
| fact_candidate_032 | process_candidate_004 | grain_candidate_040 | snapshot | 2 | - | strong | ambiguous_grain, missing_object_evidence |
| fact_candidate_033 | process_candidate_004 | grain_candidate_041 | snapshot | 2 | - | strong | ambiguous_grain, missing_object_evidence |
| fact_candidate_034 | process_candidate_004 | grain_candidate_052 | periodic | 6 | customer | strong | ambiguous_grain |
| fact_candidate_035 | process_candidate_004 | grain_candidate_053 | periodic | 6 | store | strong | ambiguous_grain |
| fact_candidate_036 | process_candidate_004 | grain_candidate_056 | periodic | 1 | customer | strong | ambiguous_grain |
| fact_candidate_037 | process_candidate_004 | grain_candidate_057 | periodic | 6 | customer | strong | ambiguous_grain |
| fact_candidate_038 | process_candidate_004 | grain_candidate_058 | periodic | 1 | store | strong | ambiguous_grain |
| fact_candidate_039 | process_candidate_004 | grain_candidate_059 | periodic | 6 | store | strong | ambiguous_grain |
| fact_candidate_040 | process_candidate_004 | grain_candidate_060 | aggregation | 1 | customer | strong | ambiguous_grain |
| fact_candidate_041 | process_candidate_004 | grain_candidate_061 | periodic | 6 | customer | strong | ambiguous_grain |
| fact_candidate_042 | process_candidate_004 | grain_candidate_062 | aggregation | 1 | store | strong | ambiguous_grain |
| fact_candidate_043 | process_candidate_004 | grain_candidate_063 | periodic | 6 | store | strong | ambiguous_grain |
| fact_candidate_044 | process_candidate_004 | grain_candidate_067 | aggregation | 6 | customer | strong | ambiguous_grain |
| fact_candidate_045 | process_candidate_004 | grain_candidate_068 | aggregation | 6 | product | strong | ambiguous_grain |
| fact_candidate_046 | process_candidate_004 | grain_candidate_069 | aggregation | 6 | store | strong | ambiguous_grain |
| fact_candidate_047 | process_candidate_004 | grain_candidate_070 | snapshot | 1 | - | strong | ambiguous_grain, missing_measure_evidence, missing_object_evidence |
| fact_candidate_048 | process_candidate_004 | grain_candidate_071 | snapshot | 1 | - | strong | ambiguous_grain, missing_measure_evidence, missing_object_evidence |
| fact_candidate_049 | process_candidate_004 | grain_candidate_072 | snapshot | 3 | customer | strong | ambiguous_grain, missing_measure_evidence |
| fact_candidate_050 | process_candidate_004 | grain_candidate_073 | snapshot | 3 | customer | strong | ambiguous_grain, missing_measure_evidence |

只列出前 50 条，共 3364 条；完整明细见 `analysis/model/fact-candidates.json`。

读法：每个 fact candidate = 「一个 grain candidate 在其候选表上的 fact 候选 + 7 类证据」；同一 grain 的多个候选表合并成一条候选，不挑 winner。

## 3. Dimension Candidates

- dimension 按 M3.1 Object 逐个生成（5 个）；attributes 只是关联表里观察到的字段清单，每条最多列出 50 个。

| dimension_key | object | tables | attributes | referenced facts | strength | unresolved |
| --- | --- | --- | --- | --- | --- | --- |
| dimension_candidate_001 | 客户 | 1848 | 7795 | 352 | strong | fact_and_dimension_ambiguous |
| dimension_candidate_002 | 员工 | 20 | 694 | 0 | strong | missing_fact_reference |
| dimension_candidate_003 | 订单 | 1416 | 7918 | 545 | strong | fact_and_dimension_ambiguous |
| dimension_candidate_004 | 产品 | 2170 | 10036 | 529 | strong | fact_and_dimension_ambiguous |
| dimension_candidate_005 | 门店 | 1741 | 7453 | 1747 | strong | fact_and_dimension_ambiguous |

完整明细见 `analysis/model/dimension-candidates.json`。

- role_status：candidate=1，ambiguous=4；`ambiguous` = 同一 Object 同时出现在 fact 关系里，必须人工裁决主角色。
- modeling_roles 可以多选：一个 Object 可以同时是 dimension candidate 与 fact related object。

## 4. Fact ↔ Dimension Relationships

- relationship 行数：15979；每行至少一类证据才生成，无证据的组合不产出关系候选。

| relationship_key | fact | dimension | evidence sources | strength | unresolved |
| --- | --- | --- | --- | --- | --- |
| fact_dimension_relationship_001 | fact_candidate_001 | dimension_candidate_001 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_002 | fact_candidate_001 | dimension_candidate_002 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_003 | fact_candidate_001 | dimension_candidate_003 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_004 | fact_candidate_001 | dimension_candidate_004 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_005 | fact_candidate_001 | dimension_candidate_005 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_006 | fact_candidate_002 | dimension_candidate_001 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_007 | fact_candidate_002 | dimension_candidate_002 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_008 | fact_candidate_002 | dimension_candidate_003 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_009 | fact_candidate_002 | dimension_candidate_004 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_010 | fact_candidate_002 | dimension_candidate_005 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_011 | fact_candidate_003 | dimension_candidate_001 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_012 | fact_candidate_003 | dimension_candidate_002 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_013 | fact_candidate_003 | dimension_candidate_003 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_014 | fact_candidate_003 | dimension_candidate_004 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_015 | fact_candidate_003 | dimension_candidate_005 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_016 | fact_candidate_004 | dimension_candidate_001 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_017 | fact_candidate_004 | dimension_candidate_002 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_018 | fact_candidate_004 | dimension_candidate_003 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_019 | fact_candidate_004 | dimension_candidate_004 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_020 | fact_candidate_004 | dimension_candidate_005 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_021 | fact_candidate_005 | dimension_candidate_001 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_022 | fact_candidate_005 | dimension_candidate_002 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_023 | fact_candidate_005 | dimension_candidate_003 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_024 | fact_candidate_005 | dimension_candidate_004 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_025 | fact_candidate_005 | dimension_candidate_005 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_026 | fact_candidate_006 | dimension_candidate_001 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_027 | fact_candidate_006 | dimension_candidate_002 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_028 | fact_candidate_006 | dimension_candidate_003 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_029 | fact_candidate_006 | dimension_candidate_004 | process_object、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_030 | fact_candidate_006 | dimension_candidate_005 | process_object、object_relationship、table_reference、sql_reference、lineage | strong | - |
| fact_dimension_relationship_031 | fact_candidate_007 | dimension_candidate_001 | process_object、table_reference、sql_reference | strong | lineage_evidence_missing |
| fact_dimension_relationship_032 | fact_candidate_007 | dimension_candidate_002 | process_object、table_reference、sql_reference | strong | lineage_evidence_missing |
| fact_dimension_relationship_033 | fact_candidate_007 | dimension_candidate_003 | process_object、table_reference、sql_reference | strong | lineage_evidence_missing |
| fact_dimension_relationship_034 | fact_candidate_007 | dimension_candidate_004 | process_object、table_reference、sql_reference | strong | lineage_evidence_missing |
| fact_dimension_relationship_035 | fact_candidate_007 | dimension_candidate_005 | process_object、table_reference、sql_reference | strong | lineage_evidence_missing |
| fact_dimension_relationship_036 | fact_candidate_008 | dimension_candidate_001 | process_object、table_reference | moderate | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_037 | fact_candidate_008 | dimension_candidate_002 | process_object、object_relationship、table_reference | strong | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_038 | fact_candidate_008 | dimension_candidate_003 | process_object、object_relationship、table_reference | strong | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_039 | fact_candidate_008 | dimension_candidate_004 | object_relationship | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_040 | fact_candidate_008 | dimension_candidate_005 | process_object、object_relationship、table_reference | strong | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_041 | fact_candidate_009 | dimension_candidate_001 | process_object、table_reference | moderate | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_042 | fact_candidate_009 | dimension_candidate_002 | process_object、object_relationship、table_reference | strong | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_043 | fact_candidate_009 | dimension_candidate_003 | process_object、object_relationship、table_reference | strong | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_044 | fact_candidate_009 | dimension_candidate_004 | object_relationship | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_045 | fact_candidate_009 | dimension_candidate_005 | process_object、object_relationship、table_reference | strong | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_046 | fact_candidate_010 | dimension_candidate_001 | process_object、table_reference | moderate | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_047 | fact_candidate_010 | dimension_candidate_002 | process_object、object_relationship、table_reference | strong | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_048 | fact_candidate_010 | dimension_candidate_003 | process_object、object_relationship、table_reference | strong | sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_049 | fact_candidate_010 | dimension_candidate_004 | object_relationship | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing |
| fact_dimension_relationship_050 | fact_candidate_010 | dimension_candidate_005 | process_object、object_relationship、table_reference | strong | sql_evidence_missing, lineage_evidence_missing |

只列出前 50 条，共 15979 条；完整明细见 `analysis/model/fact-dimension-relationships.json`。

- relationship ≠ 业务关系：它只说明 fact 候选与 dimension 候选之间存在可解释的引用 / 关联证据，确认前必须核对 source_id。

## 5. Evidence Coverage

| fact evidence | total |
| --- | --- |
| process | 10644 |
| grain | 3364 |
| table | 1244 |
| column | 9095 |
| sql | 1507 |
| lineage | 1507 |
| object | 3537 |

| dimension evidence | total |
| --- | --- |
| object | 5 |
| column | 5 |
| process | 5 |
| fact_reference | 4 |
| sql | 5 |
| lineage | 5 |

| relationship evidence | total |
| --- | --- |
| process_object | 9741 |
| object_relationship | 12692 |
| table_reference | 9741 |
| sql_reference | 6604 |
| lineage | 9341 |

| candidate type | weak | moderate | strong |
| --- | --- | --- | --- |
| fact | 0 | 0 | 3364 |
| dimension | 0 | 0 | 5 |
| fact_dimension_relationship | 3821 | 3641 | 8517 |

- strength = 证据源类型的数量（weak=1，moderate=2，strong≥3），只反映证据多样性，不代表业务正确。
- 计数口径：fact / dimension 按候选统计，relationship 按证据条目统计。

## 6. Evidence Gaps

每个候选都按固定顺序记录未决原因（未决 ≠ 失败，必须人工回答）：

| fact unresolved reason | candidates |
| --- | --- |
| insufficient_process_evidence | 0 |
| insufficient_grain_evidence | 181 |
| ambiguous_grain | 3107 |
| missing_measure_evidence | 50 |
| missing_sql_evidence | 1857 |
| missing_lineage_evidence | 1857 |
| missing_object_evidence | 525 |

| dimension unresolved reason | candidates |
| --- | --- |
| insufficient_object_evidence | 0 |
| missing_attribute_evidence | 0 |
| missing_process_reference | 0 |
| missing_fact_reference | 1 |
| missing_sql_evidence | 0 |
| missing_lineage_evidence | 0 |
| fact_and_dimension_ambiguous | 4 |

| relationship unresolved reason | relationships |
| --- | --- |
| insufficient_evidence | 3821 |
| missing_object_link | 358 |
| sql_evidence_missing | 9375 |
| lineage_evidence_missing | 6638 |

- weak 证据：fact 0，dimension 0，relationship 3821
- 未决原因只在对应证据缺失时出现；补证据后重跑本阶段即可更新。

## 7. Human Review

回填 `analysis/model/model-review-checklist.md` 的 human_status / human_name / note 后重跑本阶段即可保留人工输入；机器列由 `analyze-business-model` 生成，重跑会被覆盖。

- human_status → status 映射：pending → candidate，confirmed → confirmed，rejected → rejected，needs_review / needs_discussion → needs_discussion；未识别的取值按未回填处理并输出警告。
- 机器 status 恒为 candidate；只有回填 confirmed 才会变成 confirmed（fact / dimension candidate 不是 confirmed 模型）。

| priority | title | rows |
| --- | --- | --- |
| P1 | Fact Candidate 证据不足 | 563 |
| P2 | Fact Candidate 粒度 / 血缘待裁决 | 2672 |
| P3 | Dimension Candidate 证据 / 角色待裁决 | 5 |
| P4 | Fact-Dimension Relationship 证据不足 | 3821 |

- 每个优先级分区最多列出 50 行，完整明细见 `analysis/model/model-review-checklist.md`。
- 证据强度为 weak 的候选：fact 0，dimension 0，relationship 3821。

## 8. Limitations

- candidate ≠ confirmed：fact / dimension candidate 不是 confirmed 模型；机器阶段不产出 confirmed 模型，确认必须回填清单后重跑。
- strength 只是证据源数量；Profiling 为 metadata-only，没有任何行级唯一性证明，候选键 ≠ 唯一键。
- role 只用 anchor / supporting（fact 复用 M3.4 grain 的角色，dimension = 含命中标识字段且不是 fact 表），不是 Fact / Dimension / DWD / DWS 结论。
- layer 只作 candidate_layer 结构证据；core_candidate 只作证据覆盖与复核优先级，不是业务价值判断。
- 多角色与 UNKNOWN / AMBIGUOUS 一律保留，不合并不拆分不删表，不挑 winner。
- relationship 是候选关系，不是业务关系；确认前必须核对 source_id。
- 本阶段只读既有产物：不重解析原始数据，不重做 Object / Process / Grain classifier，不读 `source/`，不调用 LLM / 外部 API。

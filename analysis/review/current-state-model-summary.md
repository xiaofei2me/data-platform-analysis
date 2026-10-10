# M3.6 Current-State Model Review

## 1. Scope

- Workspace：466337、466338、466339
- Inventory 表数量：3724，已分类表数量：3724
- Fact candidate：3363，Dimension candidate：5，Relationship：15972
- Fact → table 行数：15680，Dimension → table 行数：7190
- Process candidate：17，Grain candidate：5678，Object：5
- Finding：4425（P0=696，P1=3141，P2=573，P3=15）
- 输入：`/Users/flynnho/Work/active/002-henkel/02.technical-service-project/03-projects/data-platform-analysis/analysis`

- current-state model 只描述当前平台已经存在的模型形态与评审发现，不是 Target DWD Design；review finding 是候选问题，finding ≠ confirmed 问题。
- 本阶段只读 M2 / M3 / M3.5 产物：不读 `source/`，不调 LLM / 外部 API，不修改任何上游产物。

## 2. Current Model Overview

| current_role | tables |
| --- | --- |
| FACT_DIMENSION_AMBIGUOUS | 0 |
| FACT | 993 |
| DIMENSION | 634 |
| WIDE_ANALYTICAL | 52 |
| RESULT_TABLE | 2 |
| UNKNOWN | 2043 |

| model_shape | tables |
| --- | --- |
| TRANSACTION | 144 |
| EVENT | 0 |
| PERIODIC | 152 |
| SNAPSHOT | 16 |
| AGGREGATE | 371 |
| MIXED | 130 |
| UNKNOWN | 2911 |

- `current_role` / `model_shape` 只描述当前平台已经存在的形态，不是 Target DWD 设计；UNKNOWN / AMBIGUOUS 一律保留。
- 表级角色只由 fact anchor、dimension anchor、字段数与血缘形态推导，不按表名断言业务事实。

## 3. Model Quality

| indicator | count |
| --- | --- |
| grain_conflict | 559 |
| mixed_grain | 130 |
| role_ambiguity | 4 |
| duplicate_fact | 491 |
| overlapping_fact | 2597 |
| multi_process_table | 0 |
| wide_analytical | 39 |
| aggregate_fact | 501 |
| snapshot_periodic | 0 |
| result_table | 32 |
| fact_without_measure | 50 |
| relationship_technical_only | 353 |
| relationship_object_co_occurrence | 5880 |

- Fact Gate 复算：通过 3363，未通过 2315（no_measure_evidence=2315）；与 M3.5 一致=True

| grain_pattern | rejected |
| --- | --- |
| aggregation | 808 |
| periodic | 1043 |
| unknown | 464 |

- Evidence Strength 分布（fact）：weak=0，moderate=0，strong=3363；Evidence Strength（证据源多样性）≠ Candidate Confidence（候选可信度）
- Dimension：5 个，role candidate=1，ambiguous=4；dimension candidate 按 M3.2 Object 一一映射生成，没有独立的 Dimension Suitability 判定；attributes 只是关联表字段清单（上限 50 条），不是维度属性结论
- Relationship：15972 行，strength weak=3813，moderate=3647，strong=8512
；单证据 3813，仅技术引用 353，仅共现 5880，无共享表 6233

| relationship evidence | rows |
| --- | --- |
| process_object | 9739 |
| object_relationship | 11690 |
| table_reference | 9739 |
| sql_reference | 6598 |
| lineage | 9368 |

- 上述全部是评审观测：异常只标记 Review，不判定 Wrong。

## 4. Priority Findings

| priority | severity | title | findings |
| --- | --- | --- | --- |
| P0 | critical | 直接影响后续模型设计，必须优先确认 | 696 |
| P1 | high | 高价值模型问题 | 3141 |
| P2 | medium | 一般模型问题 | 573 |
| P3 | info | 信息性发现 | 15 |

| review group | findings |
| --- | --- |
| fact_review | 555 |
| dimension_review | 5 |
| grain_review | 704 |
| relationship_review | 2 |
| model_issue_review | 3159 |

| finding_type | priority | findings |
| --- | --- | --- |
| fact_gate_no_measure | P0 | 3 |
| fact_gate_pattern | P0 | 0 |
| evidence_strength_semantics | P1 | 1 |
| fact_without_measure | P1 | 50 |
| aggregate_fact | P2 | 501 |
| grain_conflict | P0 | 559 |
| mixed_grain | P0 | 130 |
| snapshot_periodic_ambiguous | P1 | 0 |
| process_multiple_grains | P3 | 15 |
| dimension_object_derived | P2 | 1 |
| role_ambiguous | P0 | 4 |
| relationship_technical_only | P1 | 1 |
| relationship_object_co_occurrence | P1 | 1 |
| duplicate_fact | P1 | 491 |
| overlapping_fact | P1 | 2597 |
| multi_process_table | P1 | 0 |
| wide_analytical_table | P2 | 39 |
| result_table | P2 | 32 |

| finding_id | priority | finding_type | scope | scope_key | description |
| --- | --- | --- | --- | --- | --- |
| model_finding_0995 | P0 | fact_gate_no_measure | stage | aggregation | Fact Gate 因 no_measure_evidence 排除 808 / 2536 个 grain_pattern=aggregation 的 grain candidate（未产出 fact candidate） |
| model_finding_0996 | P0 | fact_gate_no_measure | stage | periodic | Fact Gate 因 no_measure_evidence 排除 1043 / 1979 个 grain_pattern=periodic 的 grain candidate（未产出 fact candidate） |
| model_finding_0997 | P0 | fact_gate_no_measure | stage | unknown | Fact Gate 因 no_measure_evidence 排除 464 / 644 个 grain_pattern=unknown 的 grain candidate（未产出 fact candidate） |
| model_finding_1048 | P0 | grain_conflict | table | dme_ads.dwd_crm_member_item | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1049 | P0 | grain_conflict | table | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | 同一张表被 16 个 fact candidate 用 16 组互不相同的候选键定义粒度（形态：aggregation、periodic） |
| model_finding_1050 | P0 | grain_conflict | table | dme_ads.dwd_pg_online_pos_douyin_temp00 | 同一张表被 4 个 fact candidate 用 4 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1051 | P0 | grain_conflict | table | dme_ads.dwd_pg_online_pos_tms_temp00 | 同一张表被 4 个 fact candidate 用 4 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1052 | P0 | grain_conflict | table | dme_ads.ke24_data_tmp_test | 同一张表被 10 个 fact candidate 用 10 组互不相同的候选键定义粒度（形态：aggregation、periodic） |
| model_finding_1053 | P0 | grain_conflict | table | dme_ads.pro_sell_out_temp | 同一张表被 6 个 fact candidate 用 6 组互不相同的候选键定义粒度（形态：aggregation、periodic） |
| model_finding_1054 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1055 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts1 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1056 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts1_tmp | 同一张表被 4 个 fact candidate 用 4 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1057 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts_v2 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1058 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts_v2_tmp1 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1059 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts_v2_tmp2 | 同一张表被 4 个 fact candidate 用 4 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1060 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts_v2_tmp5 | 同一张表被 6 个 fact candidate 用 6 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1061 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts_v2_tmp8 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1062 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts_v3_tmp1 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1063 | P0 | grain_conflict | table | dme_ads.tb_actual_data_bts_v3_tmp2 | 同一张表被 4 个 fact candidate 用 4 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1064 | P0 | grain_conflict | table | dme_ads.tb_competitor_ecom_promotion_detail_info | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：aggregation） |
| model_finding_1065 | P0 | grain_conflict | table | dme_ads.tb_consumer_ecom_sku_order_sales | 同一张表被 8 个 fact candidate 用 8 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1066 | P0 | grain_conflict | table | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp3 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1067 | P0 | grain_conflict | table | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp4 | 同一张表被 4 个 fact candidate 用 4 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1068 | P0 | grain_conflict | table | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_tmp3 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1069 | P0 | grain_conflict | table | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_tmp4 | 同一张表被 4 个 fact candidate 用 4 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1070 | P0 | grain_conflict | table | dme_ads.tb_controlling_reports_database_by_customer_mf | 同一张表被 5 个 fact candidate 用 5 组互不相同的候选键定义粒度（形态：snapshot） |
| model_finding_1071 | P0 | grain_conflict | table | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | 同一张表被 6 个 fact candidate 用 6 组互不相同的候选键定义粒度（形态：snapshot） |
| model_finding_1072 | P0 | grain_conflict | table | dme_ads.tb_controlling_reports_database_by_customer_mf_v2_tmp1 | 同一张表被 6 个 fact candidate 用 6 组互不相同的候选键定义粒度（形态：snapshot） |
| model_finding_1073 | P0 | grain_conflict | table | dme_ads.tb_controlling_reports_database_by_month_mf | 同一张表被 5 个 fact candidate 用 5 组互不相同的候选键定义粒度（形态：snapshot） |
| model_finding_1074 | P0 | grain_conflict | table | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | 同一张表被 6 个 fact candidate 用 6 组互不相同的候选键定义粒度（形态：snapshot） |
| model_finding_1075 | P0 | grain_conflict | table | dme_ads.tb_controlling_reports_database_by_month_mf_v2_tmp1 | 同一张表被 4 个 fact candidate 用 4 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1076 | P0 | grain_conflict | table | dme_ads.tb_crm_customer_analysis_info_mid | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1077 | P0 | grain_conflict | table | dme_ads.tb_crm_member_item | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1078 | P0 | grain_conflict | table | dme_ads.tb_crm_member_item_list1 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1079 | P0 | grain_conflict | table | dme_ads.tb_crm_member_item_list2 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1080 | P0 | grain_conflict | table | dme_ads.tb_crm_member_item_list3 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1081 | P0 | grain_conflict | table | dme_ads.tb_crm_member_item_list4 | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1082 | P0 | grain_conflict | table | dme_ads.tb_crm_member_item_summary | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：transaction） |
| model_finding_1083 | P0 | grain_conflict | table | dme_ads.tb_customer_product_pl_m_bu | 同一张表被 3 个 fact candidate 用 3 组互不相同的候选键定义粒度（形态：aggregation） |
| model_finding_1084 | P0 | grain_conflict | table | dme_ads.tb_dashboard_annual_sales_summary | 同一张表被 5 个 fact candidate 用 5 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1085 | P0 | grain_conflict | table | dme_ads.tb_dashboard_annual_sales_summary_v2 | 同一张表被 5 个 fact candidate 用 5 组互不相同的候选键定义粒度（形态：periodic） |
| model_finding_1086 | P0 | grain_conflict | table | dme_ads.tb_dashboard_mpd_sale_summary_pos_add_vs | 同一张表被 2 个 fact candidate 用 2 组互不相同的候选键定义粒度（形态：aggregation） |
| model_finding_1087 | P0 | grain_conflict | table | dme_ads.tb_dashboard_mpd_sale_summary_pos_mid | 同一张表被 2 个 fact candidate 用 2 组互不相同的候选键定义粒度（形态：aggregation） |
| model_finding_1088 | P0 | grain_conflict | table | dme_ads.tb_dashboard_mpd_sale_summary_pos_mid_temp_01 | 同一张表被 2 个 fact candidate 用 2 组互不相同的候选键定义粒度（形态：aggregation） |
| model_finding_1089 | P0 | grain_conflict | table | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | 同一张表被 10 个 fact candidate 用 10 组互不相同的候选键定义粒度（形态：aggregation、periodic） |
| model_finding_1090 | P0 | grain_conflict | table | dme_ads.tb_dashboard_mpd_sale_summary_pos_quarter_temp_add_vs | 同一张表被 10 个 fact candidate 用 10 组互不相同的候选键定义粒度（形态：aggregation、periodic） |
| model_finding_1091 | P0 | grain_conflict | table | dme_ads.tb_dashboard_mpd_sale_summary_pos_temp_03_add_vs | 同一张表被 22 个 fact candidate 用 22 组互不相同的候选键定义粒度（形态：aggregation、periodic） |
| model_finding_1092 | P0 | grain_conflict | table | dme_ads.tb_dashboard_mpd_sale_summary_pos_year_temp_add_vs | 同一张表被 20 个 fact candidate 用 20 组互不相同的候选键定义粒度（形态：aggregation、periodic） |
| model_finding_1093 | P0 | grain_conflict | table | dme_ads.tb_dashboard_nka_sale_summary_pos_mid_temp_01 | 同一张表被 2 个 fact candidate 用 2 组互不相同的候选键定义粒度（形态：aggregation） |
| model_finding_1094 | P0 | grain_conflict | table | dme_ads.tb_dashboard_nka_sale_summary_pos_temp_01_add_vs | 同一张表被 2 个 fact candidate 用 2 组互不相同的候选键定义粒度（形态：aggregation） |

只列出前 50 条，共 4425 条；完整明细见 `analysis/review/current-state-findings.json`。

## 5. Human Review

回填 `analysis/review/current-state-review-checklist.md` 的 human_status / human_name / note 后重跑本阶段即可保留人工输入；机器列由 `analyze --stage review` 生成，重跑会被覆盖。

- human_status → status 映射：pending → candidate，confirmed → confirmed，rejected → rejected，needs_review / needs_discussion → needs_discussion；未识别的取值按未回填处理并输出警告。
- 当前 finding 状态：candidate=4425，confirmed=0，rejected=0，needs_discussion=0

- 每个分区最多列出 50 行，完整明细见 `analysis/review/current-state-review-checklist.md`。
- P0 未裁决前不要进入 M4 的事实 / 维度定稿。

## 6. M4 Input

可以带入 M4 的输入：

- current-state 分类（role / shape）与逐表明细（`current-state-model-tables.json`）。
- 带证据的 review finding 与优先级（`current-state-findings.json`）。
- 回填后的人工结论（`current-state-review-checklist.md`）。

不能带入 M4 的内容：

- 未经人工裁决的 fact / dimension 最终角色；本阶段不合并、不拆分、不删表、不挑 winner。
- 只有技术引用（SQL / 血缘 / 共现）的关系，不能直接当成业务维度关系。
- `evidence_strength=strong` 不等于该表确定是事实表。

- 建议顺序：先回答 P0（Fact Gate 排除、粒度冲突、多形态、角色歧义），再处理 P1（重复 / 重叠 / 关系证据），最后看 P2 / P3。
- 进入 M4 前至少需要：review finding 是候选问题，finding ≠ confirmed 问题；P0 finding 必须有人工结论。

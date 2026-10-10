# M3.4 Grain Candidate Analysis

## 1. Overview

- Inventory 表数量：3724
- 参与 M3.3 的 (process, table) 数量：2303
- Process candidate 数量：17（人工已确认 0）
- Grain Signal 行数：22396（覆盖 2255 张表）
- Grain Candidate 数量：5678（candidate=5678）
- grain_pattern 分布：transaction=476，snapshot=43，event=0，periodic=1979，aggregation=2536，unknown=644
- 证据强度：weak=673，moderate=257，strong=4748
- grain → table 行数：25011（anchor=5678，supporting=19333）
- 覆盖 process 数量：17，覆盖表数量：2303
- 空 candidate_keys 的候选：644（表示证据不足，不是「没有 grain」的结论）
- 绑定到已确认 process 的候选：0
- Profiling：is_candidate_key=true 的列 0，metadata_only 列 102703 / 102703，可用数据样本的表 0 / 3724
- 输入：`/Users/flynnho/Work/active/002-henkel/02.technical-service-project/03-projects/data-platform-analysis/analysis`

本报告只产出 **Grain Candidate**：它由字段形态信号、SQL / 血缘 / Object 证据共同支撑，status 恒为 candidate（grain candidate 不是 confirmed grain）。Process 的人工确认只作记录，不会传递成 Grain 结论。

## 2. Grain Signals

| signal type | signal rows | tables | source |
| --- | --- | --- | --- |
| identifier | 7641 | 1837 | column |
| time | 7911 | 2177 | column |
| measure | 3471 | 970 | column |
| snapshot | 43 | 16 | column |
| event | 17 | 9 | column |
| periodic | 2473 | 1107 | column |
| aggregation | 840 | 840 | table |

- 列级信号来自 inventory 列名形态与 `config/process-rules.yaml` 的 process signal；表级 aggregation 信号 = 有度量信号且无事务标识信号。
- **Signal ≠ Grain**：命中信号只说明字段 / 表上具备某类 grain 特征；证据不足时只保留信号，不生成候选键。

## 3. Grain Candidates

| grain_pattern | candidates |
| --- | --- |
| transaction | 476 |
| snapshot | 43 |
| event | 0 |
| periodic | 1979 |
| aggregation | 2536 |
| unknown | 644 |

| grain_candidate_id | process | table | pattern | candidate keys | strength | unresolved |
| --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_001 | process_candidate_001 | dme_ads.tb_direct_sale_store_pos | aggregation | ds、henkel_product_code | strong | aggregation_level_unclear |
| grain_candidate_002 | process_candidate_001 | dme_cdm.dwd_direct_sale_order_detail_info_temp | unknown | -（空） | weak | no_identifier_signal, aggregation_level_unclear, insufficient_evidence |
| grain_candidate_003 | process_candidate_001 | dme_cdm.dwd_direct_sale_order_detail_info | aggregation | ds、henkel_product_code | strong | aggregation_level_unclear |
| grain_candidate_004 | process_candidate_001 | dme_cdm.dwd_direct_sale_order_info | transaction | external_order_no | strong | multiple_possible_keys |
| grain_candidate_005 | process_candidate_001 | dme_cdm.dwd_direct_sale_order_info | transaction | web_order_no | strong | multiple_possible_keys |
| grain_candidate_006 | process_candidate_001 | dme_cdm.dwd_master_data_product_pos_bu | aggregation | ds、product_code | strong | aggregation_level_unclear |
| grain_candidate_007 | process_candidate_001 | dme_ods.s_product_sample_mapping | unknown | -（空） | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |
| grain_candidate_008 | process_candidate_001 | dme_ods.s_qdpos_data_receipts_all | unknown | -（空） | weak | no_identifier_signal, time_semantics_unclear, aggregation_level_unclear, insufficient_evidence |
| grain_candidate_009 | process_candidate_001 | dme_ods.s_service_revenue_mapping | unknown | -（空） | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |
| grain_candidate_010 | process_candidate_002 | dme_cdm.dwd_direct_store_info | unknown | -（空） | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |
| grain_candidate_011 | process_candidate_002 | dme_ods.s_htdk_order_delta | aggregation | customer_id、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear |
| grain_candidate_012 | process_candidate_002 | dme_ods.s_htdk_order_delta | aggregation | customer_no、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear |
| grain_candidate_013 | process_candidate_002 | dme_ods.s_htdk_order | aggregation | customer_id、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear |
| grain_candidate_014 | process_candidate_002 | dme_ods.s_htdk_order | aggregation | customer_no、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear |
| grain_candidate_015 | process_candidate_002 | dme_ods.s_yinbao_data_receipts_all | transaction | external_order_no | strong | multiple_possible_keys |
| grain_candidate_016 | process_candidate_002 | dme_ods.s_yinbao_data_receipts_all | transaction | web_order_no | strong | multiple_possible_keys |
| grain_candidate_017 | process_candidate_003 | dme_ods.s_04sd_customer_sap_his | unknown | -（空） | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |
| grain_candidate_018 | process_candidate_003 | dme_ods.s_04sd_customer_sap | unknown | -（空） | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |
| grain_candidate_019 | process_candidate_004 | dme_ads.ads_crm_member_tag | unknown | -（空） | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |
| grain_candidate_020 | process_candidate_004 | dme_ads.tb_city_attack_city_group_list | unknown | -（空） | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |
| grain_candidate_021 | process_candidate_004 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | customer_code、order_no | strong | multiple_possible_keys |
| grain_candidate_022 | process_candidate_004 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | customer_code、sub_order_no | strong | multiple_possible_keys |
| grain_candidate_023 | process_candidate_004 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | order_no、product_line_id | strong | multiple_possible_keys |
| grain_candidate_024 | process_candidate_004 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | order_no、store_id | strong | multiple_possible_keys |
| grain_candidate_025 | process_candidate_004 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | order_no | strong | multiple_possible_keys |
| grain_candidate_026 | process_candidate_004 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | product_line_id、sub_order_no | strong | multiple_possible_keys |
| grain_candidate_027 | process_candidate_004 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | store_id、sub_order_no | strong | multiple_possible_keys |
| grain_candidate_028 | process_candidate_004 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | sub_order_no | strong | multiple_possible_keys |
| grain_candidate_029 | process_candidate_004 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_foc_tmp1 | periodic | customer_code、month | strong | - |
| grain_candidate_030 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | customer_idh_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_031 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | customer_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_032 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | customer_type_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_033 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | region_cn_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_034 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | region_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_035 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | system_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_036 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | customer_idh_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_037 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | customer_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_038 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | customer_type_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_039 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | region_cn_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_040 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | region_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_041 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | system_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_042 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_region_mf_v2 | periodic | month_en | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_043 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_region_mf_v2 | periodic | month | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_044 | process_candidate_004 | dme_ads.tb_controlling_reports_database_by_region_mf_v2 | periodic | year | strong | no_identifier_signal, multiple_possible_keys |
| grain_candidate_045 | process_candidate_004 | dme_ads.tb_controlling_sku_nes_report_prof | aggregation | customer_code、ds | strong | - |
| grain_candidate_046 | process_candidate_004 | dme_ads.tb_crm_member_tag_wide | unknown | -（空） | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |
| grain_candidate_047 | process_candidate_004 | dme_ads.tb_dashboard_nka_sale_summary_pos_add_vs | aggregation | ds、henkel_store_code | strong | - |
| grain_candidate_048 | process_candidate_004 | dme_ads.tb_dme_pos_inventory_data_source | aggregation | customer_code、ds | strong | - |
| grain_candidate_049 | process_candidate_004 | dme_ads.tb_dme_read_log_info | unknown | -（空） | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |
| grain_candidate_050 | process_candidate_004 | dme_ads.tb_dme_sku_ecom_pos_maizhi_temp01 | unknown | -（空） | weak | no_identifier_signal, insufficient_evidence |

只列出前 50 条，共 5678 条；完整明细见 `analysis/understanding/business/grain-candidates.json`。

读法：每个 candidate 是「一个 process 在一张表上的候选键 + 形态 + 证据」；同一 (process, table) 可能有多个候选键组合，全部保留，不挑 winner。

## 4. Process → Grain

按 process 汇总其 grain candidate；process 是否人工确认只作记录，不影响 grain 的 candidate 状态。

| process_key | candidates | patterns | empty keys | process confirmed |
| --- | --- | --- | --- | --- |
| process_candidate_001 | 9 | aggregation, transaction, unknown | 4 | false |
| process_candidate_002 | 7 | aggregation, transaction, unknown | 1 | false |
| process_candidate_003 | 2 | unknown | 2 | false |
| process_candidate_004 | 1086 | aggregation, periodic, snapshot, transaction, unknown | 169 | false |
| process_candidate_005 | 291 | aggregation, periodic, snapshot, transaction, unknown | 50 | false |
| process_candidate_006 | 542 | aggregation, periodic, unknown | 31 | false |
| process_candidate_007 | 173 | aggregation, periodic, snapshot, unknown | 33 | false |
| process_candidate_008 | 1046 | aggregation, periodic, unknown | 47 | false |
| process_candidate_009 | 397 | aggregation, periodic, snapshot, unknown | 38 | false |
| process_candidate_010 | 310 | aggregation, periodic, snapshot, unknown | 18 | false |
| process_candidate_011 | 4 | aggregation, transaction | 0 | false |
| process_candidate_012 | 2 | aggregation, unknown | 1 | false |
| process_candidate_013 | 556 | aggregation, periodic, snapshot, transaction, unknown | 61 | false |
| process_candidate_014 | 190 | aggregation, periodic, snapshot, transaction, unknown | 54 | false |
| process_candidate_015 | 84 | aggregation, periodic, transaction, unknown | 22 | false |
| process_candidate_016 | 154 | aggregation, periodic, snapshot, transaction, unknown | 56 | false |
| process_candidate_017 | 825 | aggregation, periodic, unknown | 57 | false |

完整明细见 `analysis/understanding/business/grain-candidates.json`。

## 5. Evidence Sources

| evidence source | total（候选证据条目） |
| --- | --- |
| process_signal | 8761 |
| column | 8888 |
| table | 2298 |
| sql | 3137 |
| lineage | 3130 |
| object | 4490 |
| object_relationship | 350 |

| grain → table role | rows |
| --- | --- |
| anchor | 5678 |
| supporting | 19333 |

- `anchor` = 候选键来自该表；`supporting` = 同一 process 下也包含全部候选键的表（每个候选最多列 5 张）。
- role 只是技术角色，不是 Fact / Dimension 命名。

## 6. Evidence Gaps

每个候选都按固定顺序记录未决原因（未决 ≠ 失败，必须人工回答）：

| unresolved reason | candidates |
| --- | --- |
| no_identifier_signal | 1587 |
| multiple_possible_keys | 4378 |
| missing_sql_evidence | 2541 |
| missing_lineage_evidence | 2548 |
| time_semantics_unclear | 1951 |
| aggregation_level_unclear | 1908 |
| insufficient_evidence | 673 |

- 空 candidate_keys：644 / 5678
- 空证据源（source_type 数 < 2）：673
- 无 SQL 证据：2541，无血缘证据：2548

## 7. Human Review

回填 `analysis/understanding/business/grain-review-checklist.md` 的 human_grain_name / confirmed / note 后重跑本阶段即可保留人工输入；机器阶段不会把任何候选变成 confirmed。

- 待确认候选：5678（其中绑定已确认 process 的 0 个，绑定未确认 process 的 5678 个）
- Process 侧已确认：0 / 17
- Core 表候选上的候选：3130（core_candidate 只作证据覆盖与复核优先级）

优先复核顺序建议：先看第 6 节缺口最少的候选，再看空 candidate_keys 与 multiple_possible_keys 的候选。

## 8. Limitations

- candidate ≠ confirmed：grain candidate 不是 confirmed grain；机器阶段不产出 confirmed grain，确认必须回填清单后重跑。
- 不伪造唯一性：Profiling 只有 metadata_only，is_candidate_key=true 的列 0，因此候选键没有任何行级唯一性证明，strength 只反映证据源多样性。
- 空 candidate_keys ≠ 没有 grain：它只表示当前证据不足以给出候选键。
- 不命名事实表 / 维度表：role 只用 anchor / supporting，不产出 DWD / DWS / Fact / Dimension 结论。
- Process 确认 ≠ Grain 确认：process_human_validated 只是记录。

## 9. Next: Fact-Dimension Readiness

进入 Fact-Dimension Readiness 之前需要补齐：

- 证据强度为 strong 的候选：4748，moderate：257，weak：673（strength 只是证据源数量，不代表业务正确）。
- 空 candidate_keys 的候选：644，需要人工给出候选键或补充 SQL / 血缘证据。
- multiple_possible_keys 的候选：4378，需要人工确认唯一形态。
- 时间语义未决：1951，聚合层级未决：1908。
- 行级唯一性证据：当前 Profiling 无样本，任何「唯一」结论都必须由人工确认。

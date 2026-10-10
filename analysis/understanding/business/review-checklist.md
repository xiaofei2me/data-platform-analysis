# M3.1 Review Checklist

人工填写 human domain / human object，确认后把 status 从 pending 改为 done；
note 里的 unknown: / ambiguous: 是评估给出的主因，可在人工复核后追加说明。

## Priority 1 — 核心表 + UNKNOWN（共 44 条）

核心表却没有业务候选：优先补注释 / 扩词典 / 补 SQL 证据。

| table | current domain candidates | current object candidates | evidence | human domain | human object | status | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dme_cdm.dim_mgm_mapping_time | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=5 |  |  | pending | unknown:comment_evidence_present |
| dme_cdm.dim_mgm_mapping_time_01 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=6 |  |  | pending | unknown:sql_evidence_present |
| dme_cdm.dim_mgm_mapping_time_02 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=5 |  |  | pending | unknown:sql_evidence_present |
| dme_cdm.dim_mgm_mapping_time_03 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=5 |  |  | pending | unknown:sql_evidence_present |
| dme_cdm.dim_watsons_mapping_time | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=5 |  |  | pending | unknown:comment_evidence_present |
| dme_cdm.dwd_data_source_list_fetch_date_monitor_v2 | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=7 |  |  | pending | unknown:comment_evidence_present |
| dme_cdm.dwd_data_source_list_pre_processing_monitor_v2 | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=41 |  |  | pending | unknown:comment_evidence_present |
| dme_cdm.dwd_data_source_list_table_timeliness_monitor_v2 | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=8 |  |  | pending | unknown:comment_evidence_present |
| dme_cdm.dwd_data_source_list_update_monitor | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=21 |  |  | pending | unknown:comment_evidence_present |
| dme_cdm.dwd_l17_digital_wide_tb | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=17 |  |  | pending | unknown:comment_evidence_present |
| dme_cdm.dwd_l17_digital_wide_tb_tmp2 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=15 |  |  | pending | unknown:sql_evidence_present |
| dme_cdm.dwd_pl_sti_mapping_professional | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=17 |  |  | pending | unknown:comment_evidence_present |
| dme_ods.s_04sd_businessaddressservices_sap | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=65 |  |  | pending | unknown:comment_evidence_present |
| dme_ods.s_04sd_businessaddressservices_sap_his | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=66 |  |  | pending | unknown:comment_evidence_present |
| dme_ods.s_area_trans | - | - | signals: table_comment=n, column_comment=y, sql=y, lineage=y, terms=3 |  |  | pending | unknown:comment_evidence_present |
| dme_ods.s_data_source_list_monitor | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=23 |  |  | pending | unknown:comment_evidence_present |
| dme_ods.s_pl_sti_mapping_professional | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=17 |  |  | pending | unknown:comment_evidence_present |
| dme_ods.s_target_budget_bu | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=11 |  |  | pending | unknown:comment_evidence_present |
| dme_ods.s_target_sell_in_target_budget | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=12 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_city_attack_city_l17 | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=21 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_city_attack_data_update_info | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=13 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_competition_nielsen_time | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=7 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_consumer_mapping_time_day | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=6 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_controlling_blue_table_mapping_time | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=9 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_data_source_list_update_monitor | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=21 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_data_source_list_update_monitor_v2 | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=21 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_dept_user_detail | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=6 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_ecom_pos_mapping_time | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=6 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_ecom_pos_mapping_time_all | - | - | signals: table_comment=n, column_comment=y, sql=y, lineage=y, terms=7 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_mediabb_reach_performance | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=10 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_monitor_filter_data_detail | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=6 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_mtk_si_drs_tmp2 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=12 |  |  | pending | unknown:sql_evidence_present |
| dme_ads.tb_mtk_si_drs_tmp3 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=12 |  |  | pending | unknown:sql_evidence_present |
| dme_ads.tb_mtk_si_drs_tmp4 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=9 |  |  | pending | unknown:sql_evidence_present |
| dme_ads.tb_mtk_si_drs_tmp5 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=9 |  |  | pending | unknown:sql_evidence_present |
| dme_ads.tb_mtk_si_drs_tmp6 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=7 |  |  | pending | unknown:sql_evidence_present |
| dme_ads.tb_pl_sti_mapping_professional | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=17 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_price_mapping_time | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=5 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_social_content_salon_trend_by_content_df | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=40 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_social_content_salon_trend_by_hashtags_df | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=22 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_social_content_salon_trend_by_keywords_df | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=25 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_tpm_activity_mapping_time | - | - | signals: table_comment=y, column_comment=y, sql=y, lineage=y, terms=7 |  |  | pending | unknown:comment_evidence_present |
| dme_ads.tb_tpm_activity_mapping_time_tmp1 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=5 |  |  | pending | unknown:sql_evidence_present |
| dme_ads.tb_tpm_activity_mapping_time_tmp2 | - | - | signals: table_comment=n, column_comment=n, sql=y, lineage=y, terms=7 |  |  | pending | unknown:sql_evidence_present |

## Priority 2 — 核心表 + AMBIGUOUS（共 1533 条）

核心表的多候选需要人工收敛，先于非核心表处理。

| table | current domain candidates | current object candidates | evidence | human domain | human object | status | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dme_cdm.dim_area_trans | customer(low), inventory(low), product(low), sales(low) | customer(low), order(low), product(low), store(low) | entries=17, diversity=1, types=sql×17 |  |  | pending | ambiguous:unresolved |
| dme_cdm.dim_controlling_blue_table_exchange_rate | customer(low), inventory(low), product(low), sales(low) | customer(low), order(low), product(low), store(low) | entries=17, diversity=1, types=sql×17 |  |  | pending | ambiguous:unresolved |
| dme_cdm.dim_day | customer(low), inventory(low), product(low), sales(low) | customer(low), order(low), product(low), store(low) | entries=22, diversity=1, types=sql×22 |  |  | pending | ambiguous:keyword_cooccurrence |
| dme_cdm.dim_direct_pay_method_dictionary | customer(low), product(low), sales(low) | customer(low), order(low), product(low), store(low) | entries=9, diversity=1, types=sql×9 |  |  | pending | ambiguous:keyword_cooccurrence |
| dme_cdm.dim_dt_small_customer_info | customer(high), inventory(low), product(low), sales(low) | customer(high), order(low), product(low), store(low) | entries=20, diversity=3, types=table_name×1+column_name×2+sql×17 |  |  | pending | ambiguous:keyword_cooccurrence |
| dme_cdm.dim_ec_douyin_product_mapping | product(high), sales(high) | product(high), store(high), order(low) | entries=15, diversity=5, types=table_name×1+table_comment×1+column_name×3+column_comment×6+sql×4 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_ec_douyin_product_mapping_temp_01 | product(high), sales(medium) | product(high), order(low), store(low) | entries=7, diversity=3, types=table_name×1+column_name×4+sql×2 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dim_ec_douyin_product_mapping_temp_02 | product(low), sales(low) | product(low), store(low) | entries=5, diversity=2, types=table_name×1+column_name×4 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dim_ec_tm_key_product_line_mapping | product(high), sales(low) | product(high), order(low), store(low) | entries=21, diversity=5, types=table_name×1+table_comment×1+column_name×4+column_comment×3+sql×12 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_ec_tm_launch_channel_mapping | customer(low), sales(low) | customer(low), order(low), store(low) | entries=8, diversity=1, types=sql×8 |  |  | pending | ambiguous:unresolved |
| dme_cdm.dim_ec_tm_product_mapping | product(high), sales(medium) | product(high), store(high), order(low) | entries=27, diversity=5, types=table_name×1+table_comment×1+column_name×11+column_comment×9+sql×5 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_ec_tm_product_mapping_temp_01 | product(high), sales(medium) | product(high), order(low), store(low) | entries=13, diversity=3, types=table_name×1+column_name×10+sql×2 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dim_ec_tm_product_mapping_temp_02 | product(high), sales(medium) | product(high), store(medium), order(low) | entries=16, diversity=3, types=table_name×1+column_name×11+sql×4 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_ec_tm_product_mapping_temp_lily_14 | product(medium), sales(medium) | product(medium), order(low), store(low) | entries=5, diversity=3, types=table_name×1+column_name×3+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dim_ec_tm_product_mapping_temp_lily_446 | product(medium), sales(medium) | product(medium), order(low), store(low) | entries=5, diversity=3, types=table_name×1+column_name×3+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dim_ec_tm_traffic_channel_mapping | customer(low), sales(low) | customer(low), order(low), store(low) | entries=7, diversity=1, types=sql×7 |  |  | pending | ambiguous:unresolved |
| dme_cdm.dim_ecom_product_prop_mapping | product(high), customer(low), sales(low) | product(high), store(high), customer(low), order(low) | entries=19, diversity=5, types=table_name×1+table_comment×1+column_name×2+column_comment×5+sql×10 |  |  | pending | ambiguous:keyword_cooccurrence |
| dme_cdm.dim_ecom_product_prop_mapping_temp_00 | product(medium), sales(low) | product(medium), store(medium), order(low) | entries=7, diversity=3, types=table_name×1+column_name×4+sql×2 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dim_ecom_product_prop_mapping_temp_01 | product(high), sales(low) | product(high), order(low), store(low) | entries=7, diversity=3, types=table_name×1+column_name×4+sql×2 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dim_ecom_product_prop_mapping_temp_02 | product(high), sales(low) | product(high), order(low), store(low) | entries=5, diversity=3, types=table_name×1+column_name×2+sql×2 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dim_master_data_product_pos_bu_price_his | product(high), sales(low) | product(high) | entries=6, diversity=4, types=table_name×1+table_comment×1+column_name×2+sql×2 |  |  | pending | ambiguous:keyword_cooccurrence |
| dme_cdm.dim_master_data_product_price | product(high), sales(low) | product(high), order(low) | entries=8, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×2+sql×3 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_master_data_product_price_temp_01 | product(medium), sales(low) | product(medium), order(low) | entries=4, diversity=2, types=table_name×1+sql×3 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_must_sale_sku_rule_list_info | product(high), sales(medium), customer(low) | product(high), store(high), customer(low) | entries=14, diversity=5, types=table_name×2+table_comment×3+column_name×2+column_comment×2+sql×5 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_deduction | customer(high), product(low) | customer(high), product(low) | entries=5, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_detail_ttl_index | customer(high), product(medium) | customer(high), product(medium), store(medium) | entries=11, diversity=4, types=table_name×1+table_comment×1+column_name×4+column_comment×5 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_allocation_customer_detail_ttl_index_temp01 | customer(high), product(low) | customer(high), product(low), store(low) | entries=5, diversity=3, types=table_name×1+column_name×2+sql×2 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_ges_ytd_proportion | customer(high), product(low), sales(low) | customer(high), product(low) | entries=5, diversity=4, types=table_name×1+column_name×1+column_comment×1+sql×2 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_ges_ytd_proportion_temp01 | customer(medium), sales(low) | customer(medium), order(low) | entries=4, diversity=3, types=table_name×1+column_name×1+sql×2 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_ges_ytd_proportion_temp02 | customer(high), sales(medium) | customer(high), order(low) | entries=5, diversity=3, types=table_name×1+column_name×2+sql×2 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_allocation_customer_ges_ytd_proportion_temp03 | customer(high), sales(low) | customer(high) | entries=4, diversity=3, types=table_name×1+column_name×2+sql×1 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_allocation_customer_ke24 | customer(high), sales(high), product(low) | customer(high), order(low), product(low) | entries=13, diversity=5, types=table_name×1+table_comment×1+column_name×2+column_comment×4+sql×5 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l10_dsr | customer(high), product(low) | customer(high), product(low) | entries=5, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l10_surtax | customer(high), product(low) | customer(high), product(low) | entries=5, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l11 | customer(high), product(low) | customer(high), product(low) | entries=5, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l12_l13_l14_16 | customer(high), product(medium) | customer(high), product(medium) | entries=6, diversity=4, types=table_name×1+table_comment×1+column_name×2+column_comment×2 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_allocation_customer_l17_ba | customer(high), product(low) | customer(high), product(low), store(low) | entries=6, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×1+sql×2 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_digital | customer(high), product(low) | customer(high), product(low) | entries=5, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_digital_commitment_temp01 | customer(low), sales(low) | customer(low), order(low) | entries=2, diversity=2, types=table_name×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_digital_commitment_temp02 | customer(low), sales(low) | customer(low), order(low) | entries=2, diversity=2, types=table_name×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_digital_commitment_temp03 | customer(low), sales(low) | customer(low), order(low) | entries=2, diversity=2, types=table_name×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_digital_kob1_temp | customer(low), sales(low) | customer(low), order(low) | entries=2, diversity=2, types=table_name×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_mkt | customer(high), product(low) | customer(high), product(low) | entries=5, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_mkt_commitment_temp01 | customer(low), sales(low) | customer(low), order(low) | entries=2, diversity=2, types=table_name×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_mkt_commitment_temp02 | customer(low), sales(low) | customer(low), order(low) | entries=2, diversity=2, types=table_name×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_mkt_commitment_temp03 | customer(low), sales(low) | customer(low), order(low) | entries=2, diversity=2, types=table_name×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_mkt_kob1_temp | customer(low), sales(low) | customer(low), order(low) | entries=2, diversity=2, types=table_name×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_o2o | customer(high), product(low) | customer(high), product(low) | entries=11, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×7+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_po | customer(high), product(low) | customer(high), product(low) | entries=5, diversity=5, types=table_name×1+table_comment×1+column_name×1+column_comment×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_allocation_customer_l17_po_commitment_temp01 | customer(medium), sales(low) | customer(medium), order(low) | entries=3, diversity=3, types=table_name×1+column_name×1+sql×1 |  |  | pending | ambiguous:evidence_conflict |

只列出前 50 条，共 1533 条；完整样本见 `analysis/understanding/business/quality-assessment.json`。

## Priority 3 — 非核心表 + AMBIGUOUS（共 1043 条）

多候选待人工判定，可批量处理。

| table | current domain candidates | current object candidates | evidence | human domain | human object | status | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dme_cdm.dim_ec_comment_ms_manual_standard_product_hierarchy | product(high) | product(high), store(medium) | entries=20, diversity=4, types=table_name×1+table_comment×1+column_name×5+column_comment×13 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_ecom_channel_core_od001_v1 | customer(low) | store(medium), customer(low) | entries=5, diversity=2, types=column_name×3+column_comment×2 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dim_ecom_product_prop_mapping_kunc_temp_01 | product(medium) | product(medium), store(low) | entries=5, diversity=2, types=table_name×1+column_name×4 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_ecom_product_prop_mapping_kunc_temp_02 | product(medium) | product(medium), store(low) | entries=3, diversity=2, types=table_name×1+column_name×2 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_sellin_missing_product_core_od001_v1 | product(high), sales(low) | product(high) | entries=11, diversity=4, types=table_name×1+table_comment×1+column_name×5+column_comment×4 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_sellin_product_core_od001_v1 | product(high), sales(low) | product(high) | entries=14, diversity=4, types=table_name×1+table_comment×1+column_name×6+column_comment×6 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dim_store_core_od001_v1 | customer(medium), product(medium), sales(low) | store(high), customer(medium), product(medium) | entries=57, diversity=4, types=table_name×1+table_comment×1+column_name×29+column_comment×26 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_allocation_customer_detail_l12_l13_l14_16 | customer(medium), product(low) | customer(medium), product(low) | entries=3, diversity=2, types=table_name×1+column_name×2 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_allocation_customer_detail_ngs | customer(medium), sales(low) | customer(medium) | entries=3, diversity=2, types=table_name×1+column_name×2 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_controlling_target_mf | customer(medium), sales(low) | customer(medium) | entries=7, diversity=2, types=column_name×4+column_comment×3 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_controlling_target_mf_tmp1 | customer(low), sales(low) | customer(low) | entries=4, diversity=1, types=column_name×4 |  |  | pending | ambiguous:unresolved |
| dme_cdm.dwd_crm_customer_analysis_info | customer(medium), product(medium), sales(medium) | customer(medium), order(medium), product(medium) | entries=29, diversity=3, types=table_name×1+column_name×13+column_comment×15 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_crm_customer_analysis_info_tmp | customer(low), product(low), sales(low) | customer(low), order(low), product(low) | entries=15, diversity=2, types=table_name×1+column_name×14 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_crm_member | customer(medium), sales(low) | customer(medium) | entries=28, diversity=2, types=table_comment×1+column_comment×27 |  |  | pending | ambiguous:keyword_cooccurrence |
| dme_cdm.dwd_crm_member_tag_wide | customer(low), product(low), sales(low) | customer(low), order(low), product(low), store(low) | entries=8, diversity=1, types=column_comment×8 |  |  | pending | ambiguous:unresolved |
| dme_cdm.dwd_crm_product_info | product(high), sales(low) | product(high) | entries=12, diversity=4, types=table_name×1+table_comment×1+column_name×5+column_comment×5 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_crm_product_sku | product(high), sales(low) | product(high) | entries=17, diversity=4, types=table_name×2+table_comment×1+column_name×7+column_comment×7 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_crm_trade | sales(medium), product(low) | order(medium), store(medium), employee(low), product(low) | entries=33, diversity=2, types=column_name×16+column_comment×17 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_crm_trade_goods_detail | product(high), sales(high) | product(high), order(medium) | entries=22, diversity=3, types=table_comment×2+column_name×4+column_comment×16 |  |  | pending | ambiguous:keyword_cooccurrence |
| dme_cdm.dwd_customer_product_pl_m_bu_29769996_dirtydata_dw_system_dqc | customer(low), product(low) | customer(low), product(low) | entries=2, diversity=1, types=table_name×2 |  |  | pending | ambiguous:keyword_cooccurrence |
| dme_cdm.dwd_customer_product_pl_m_bu_29769997_dirtydata_dw_system_dqc | customer(low), product(low) | customer(low), product(low) | entries=2, diversity=1, types=table_name×2 |  |  | pending | ambiguous:keyword_cooccurrence |
| dme_cdm.dwd_direct_sale_store_pos | sales(high), product(medium) | store(high), order(medium), product(medium), employee(low) | entries=54, diversity=3, types=table_name×2+column_name×10+column_comment×42 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_dms_data_sale_bu_20250313 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=13, diversity=2, types=table_name×1+column_name×12 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_add_vs | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=16, diversity=2, types=table_name×1+column_name×15 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_cut_off_temp_01 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=10, diversity=2, types=table_name×1+column_name×9 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_cut_off_temp_02 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=10, diversity=2, types=table_name×1+column_name×9 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_cut_off_temp_03 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=12, diversity=2, types=table_name×1+column_name×11 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_cutoff | sales(high), customer(medium), inventory(medium), product(low) | customer(medium), order(medium), store(medium), product(low) | entries=51, diversity=4, types=table_name×1+table_comment×1+column_name×12+column_comment×37 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_dms_data_sale_bu_cutoff_his | sales(high), customer(medium), inventory(medium), product(low) | customer(medium), order(medium), store(medium), product(low) | entries=51, diversity=4, types=table_name×1+table_comment×1+column_name×12+column_comment×37 |  |  | pending | ambiguous:multi_domain_likely |
| dme_cdm.dwd_dms_data_sale_bu_cutoff_temp_01 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=10, diversity=2, types=table_name×1+column_name×9 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_cutoff_temp_02 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=15, diversity=2, types=table_name×1+column_name×14 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_cutoff_temp_03 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=16, diversity=2, types=table_name×1+column_name×15 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_temp_011 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=16, diversity=2, types=table_name×1+column_name×15 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_temp_01_add_vs | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=10, diversity=2, types=table_name×1+column_name×9 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_bu_temp_02_add_vs | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=15, diversity=2, types=table_name×1+column_name×14 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_temp | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=10, diversity=2, types=table_name×1+column_name×9 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_temp_00 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=10, diversity=2, types=table_name×1+column_name×9 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_temp_01 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=10, diversity=2, types=table_name×1+column_name×9 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_sale_temp_04 | sales(medium), customer(low), inventory(low) | customer(low), order(low), store(low) | entries=10, diversity=2, types=table_name×1+column_name×9 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock | inventory(high), customer(medium), product(low), sales(low) | customer(medium), product(low) | entries=33, diversity=4, types=table_name×1+table_comment×1+column_name×5+column_comment×26 |  |  | pending | ambiguous:evidence_conflict |
| dme_cdm.dwd_dms_data_stock_backup_20241115_chendong | inventory(medium), customer(low), sales(low) | customer(low) | entries=6, diversity=2, types=table_name×1+column_name×5 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock_beifen_20240126 | inventory(medium), customer(low), sales(low) | customer(low) | entries=6, diversity=2, types=table_name×1+column_name×5 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock_bu_add_vs | inventory(medium), customer(low), sales(low) | customer(low) | entries=7, diversity=2, types=table_name×1+column_name×6 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock_bu_add_vs_temp_01 | inventory(medium), customer(low), sales(low) | customer(low) | entries=7, diversity=2, types=table_name×1+column_name×6 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock_bu_add_vs_temp_02 | inventory(medium), customer(low), sales(low) | customer(low) | entries=7, diversity=2, types=table_name×1+column_name×6 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock_bu_add_vs_temp_04 | inventory(medium), customer(low), sales(low) | customer(low) | entries=7, diversity=2, types=table_name×1+column_name×6 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock_bu_add_vs_temp_05 | inventory(medium), customer(low), sales(low) | customer(low) | entries=7, diversity=2, types=table_name×1+column_name×6 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock_bu_add_vs_temp_06 | inventory(medium), customer(low), sales(low) | customer(low) | entries=7, diversity=2, types=table_name×1+column_name×6 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock_bu_backup_20241115_chendong | inventory(medium), customer(low), sales(low) | customer(low) | entries=6, diversity=2, types=table_name×1+column_name×5 |  |  | pending | ambiguous:dominant_domain |
| dme_cdm.dwd_dms_data_stock_bu_cut_off_temp_01 | inventory(medium), customer(low), sales(low) | customer(low) | entries=7, diversity=2, types=table_name×1+column_name×6 |  |  | pending | ambiguous:dominant_domain |

只列出前 50 条，共 1043 条；完整样本见 `analysis/understanding/business/quality-assessment.json`。

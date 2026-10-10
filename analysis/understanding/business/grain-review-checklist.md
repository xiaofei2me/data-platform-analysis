# M3.4 Grain Review Checklist

人工填写 human grain name，并把 confirmed 从 false 改为 true 以确认该 grain candidate；未回填的行一律保持 false，candidate 不会自动变成 confirmed grain。

机器列（grain_candidate_id 起到 strength 为止）由 `analyze --stage understanding` 生成，重跑会被覆盖；human_grain_name / confirmed / note 三列会被保留。

## process_candidate_001

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_001 | dme_ads.tb_direct_sale_store_pos | aggregation | ds、henkel_product_code | strong | aggregation_level_unclear |  | false |  |
| grain_candidate_002 | dme_cdm.dwd_direct_sale_order_detail_info_temp | unknown | - | weak | no_identifier_signal, aggregation_level_unclear, insufficient_evidence |  | false |  |
| grain_candidate_003 | dme_cdm.dwd_direct_sale_order_detail_info | aggregation | ds、henkel_product_code | strong | aggregation_level_unclear |  | false |  |
| grain_candidate_004 | dme_cdm.dwd_direct_sale_order_info | transaction | external_order_no | strong | multiple_possible_keys |  | false |  |
| grain_candidate_005 | dme_cdm.dwd_direct_sale_order_info | transaction | web_order_no | strong | multiple_possible_keys |  | false |  |
| grain_candidate_006 | dme_cdm.dwd_master_data_product_pos_bu | aggregation | ds、product_code | strong | aggregation_level_unclear |  | false |  |
| grain_candidate_007 | dme_ods.s_product_sample_mapping | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_008 | dme_ods.s_qdpos_data_receipts_all | unknown | - | weak | no_identifier_signal, time_semantics_unclear, aggregation_level_unclear, insufficient_evidence |  | false |  |
| grain_candidate_009 | dme_ods.s_service_revenue_mapping | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |

## process_candidate_002

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_010 | dme_cdm.dwd_direct_store_info | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_011 | dme_ods.s_htdk_order_delta | aggregation | customer_id、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear |  | false |  |
| grain_candidate_012 | dme_ods.s_htdk_order_delta | aggregation | customer_no、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear |  | false |  |
| grain_candidate_013 | dme_ods.s_htdk_order | aggregation | customer_id、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear |  | false |  |
| grain_candidate_014 | dme_ods.s_htdk_order | aggregation | customer_no、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear |  | false |  |
| grain_candidate_015 | dme_ods.s_yinbao_data_receipts_all | transaction | external_order_no | strong | multiple_possible_keys |  | false |  |
| grain_candidate_016 | dme_ods.s_yinbao_data_receipts_all | transaction | web_order_no | strong | multiple_possible_keys |  | false |  |

## process_candidate_003

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_017 | dme_ods.s_04sd_customer_sap_his | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_018 | dme_ods.s_04sd_customer_sap | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |

## process_candidate_004

只列出前 50 行，共 1086 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_019 | dme_ads.ads_crm_member_tag | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_020 | dme_ads.tb_city_attack_city_group_list | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_021 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | customer_code、order_no | strong | multiple_possible_keys |  | false |  |
| grain_candidate_022 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | customer_code、sub_order_no | strong | multiple_possible_keys |  | false |  |
| grain_candidate_023 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | order_no、product_line_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_024 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | order_no、store_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_025 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | order_no | strong | multiple_possible_keys |  | false |  |
| grain_candidate_026 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | product_line_id、sub_order_no | strong | multiple_possible_keys |  | false |  |
| grain_candidate_027 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | store_id、sub_order_no | strong | multiple_possible_keys |  | false |  |
| grain_candidate_028 | dme_ads.tb_consumer_ecom_sku_order_sales | transaction | sub_order_no | strong | multiple_possible_keys |  | false |  |
| grain_candidate_029 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_foc_tmp1 | periodic | customer_code、month | strong | - |  | false |  |
| grain_candidate_030 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | customer_idh_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_031 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | customer_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_032 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | customer_type_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_033 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | region_cn_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_034 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | region_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_035 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2 | snapshot | system_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_036 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | customer_idh_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_037 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | customer_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_038 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | customer_type_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_039 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | region_cn_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_040 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | region_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_041 | dme_ads.tb_controlling_reports_database_by_month_mf_v2 | snapshot | system_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_042 | dme_ads.tb_controlling_reports_database_by_region_mf_v2 | periodic | month_en | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_043 | dme_ads.tb_controlling_reports_database_by_region_mf_v2 | periodic | month | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_044 | dme_ads.tb_controlling_reports_database_by_region_mf_v2 | periodic | year | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_045 | dme_ads.tb_controlling_sku_nes_report_prof | aggregation | customer_code、ds | strong | - |  | false |  |
| grain_candidate_046 | dme_ads.tb_crm_member_tag_wide | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_047 | dme_ads.tb_dashboard_nka_sale_summary_pos_add_vs | aggregation | ds、henkel_store_code | strong | - |  | false |  |
| grain_candidate_048 | dme_ads.tb_dme_pos_inventory_data_source | aggregation | customer_code、ds | strong | - |  | false |  |
| grain_candidate_049 | dme_ads.tb_dme_read_log_info | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_050 | dme_ads.tb_dme_sku_ecom_pos_maizhi_temp01 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_051 | dme_ads.tb_dme_sku_ecom_pos_maizhi_temp02 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_052 | dme_ads.tb_ecom_gtm_pl_cp_tmp00 | periodic | customer_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_053 | dme_ads.tb_ecom_gtm_pl_cp_tmp00 | periodic | months、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_054 | dme_ads.tb_ecom_gtm_pl_cp_tmp0 | periodic | customer_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_055 | dme_ads.tb_ecom_gtm_pl_cp_tmp0 | periodic | months、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_056 | dme_ads.tb_ecom_gtm_pl_cp_tmp11 | periodic | customer_code、month_cnt | strong | multiple_possible_keys |  | false |  |
| grain_candidate_057 | dme_ads.tb_ecom_gtm_pl_cp_tmp11 | periodic | customer_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_058 | dme_ads.tb_ecom_gtm_pl_cp_tmp11 | periodic | month_cnt、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_059 | dme_ads.tb_ecom_gtm_pl_cp_tmp11 | periodic | months、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_060 | dme_ads.tb_ecom_gtm_pl_cp_tmp1 | aggregation | customer_code、date_type | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_061 | dme_ads.tb_ecom_gtm_pl_cp_tmp1 | periodic | customer_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_062 | dme_ads.tb_ecom_gtm_pl_cp_tmp1 | aggregation | date_type、store_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_063 | dme_ads.tb_ecom_gtm_pl_cp_tmp1 | periodic | months、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_064 | dme_ads.tb_ecom_gtm_pl_cp_tmp2 | periodic | data_year、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_065 | dme_ads.tb_ecom_gtm_pl_cp_tmp2 | periodic | end_month、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_066 | dme_ads.tb_ecom_gtm_pl_cp_tmp2 | periodic | months、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_067 | dme_ads.tb_ecom_pos_sku_sales_summary_bu | aggregation | customer_code、ds | strong | multiple_possible_keys, aggregation_level_unclear |  | false |  |
| grain_candidate_068 | dme_ads.tb_ecom_pos_sku_sales_summary_bu | aggregation | ds、product_line_id | strong | multiple_possible_keys, aggregation_level_unclear |  | false |  |

## process_candidate_005

只列出前 50 行，共 291 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_1105 | dme_ads.dwd_crm_member_item | transaction | order_id、product_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1106 | dme_ads.dwd_crm_member_item | transaction | order_id、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1107 | dme_ads.dwd_crm_member_item | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1108 | dme_ads.tb_actual_data_bts_v2_tmp1 | periodic | month_en | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1109 | dme_ads.tb_actual_data_bts_v2_tmp1 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1110 | dme_ads.tb_actual_data_bts_v2_tmp1 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1111 | dme_ads.tb_actual_data_bts_v2 | periodic | month_en | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1112 | dme_ads.tb_actual_data_bts_v2 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1113 | dme_ads.tb_actual_data_bts_v2 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1114 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2_tmp1 | snapshot | customer_idh_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1115 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2_tmp1 | snapshot | customer_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1116 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2_tmp1 | snapshot | customer_type_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1117 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2_tmp1 | snapshot | region_cn_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1118 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2_tmp1 | snapshot | region_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1119 | dme_ads.tb_controlling_reports_database_by_customer_mf_v2_tmp1 | snapshot | system_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1120 | dme_ads.tb_controlling_sku_nes_report_prof_temp_01 | periodic | customer_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1121 | dme_ads.tb_controlling_sku_nes_report_prof_temp_01 | periodic | customer_code、years | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1122 | dme_ads.tb_crm_customer_analysis_info_mid | transaction | order_id、product_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1123 | dme_ads.tb_crm_customer_analysis_info_mid | transaction | order_id、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1124 | dme_ads.tb_crm_customer_analysis_info_mid | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1125 | dme_ads.tb_crm_member_item_summary | transaction | order_id、product_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1126 | dme_ads.tb_crm_member_item_summary | transaction | order_id、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1127 | dme_ads.tb_crm_member_item_summary | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1128 | dme_ads.tb_crm_member_item | transaction | order_id、product_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1129 | dme_ads.tb_crm_member_item | transaction | order_id、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1130 | dme_ads.tb_crm_member_item | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1131 | dme_ads.tb_dme_sellin_maizhi_temp01 | transaction | customer_id、order_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1132 | dme_ads.tb_dme_sellin_maizhi_temp01 | transaction | order_id、product_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1133 | dme_ads.tb_dme_sellin_maizhi_temp01 | transaction | order_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1134 | dme_ads.tb_dme_sellin_maizhi_temp02 | transaction | customer_id、order_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1135 | dme_ads.tb_dme_sellin_maizhi_temp02 | transaction | order_id、product_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1136 | dme_ads.tb_dme_sellin_maizhi_temp02 | transaction | order_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1137 | dme_ads.tb_dme_sellin_maizhi_temp03 | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_1138 | dme_ads.tb_dme_sellin_maizhi_temp04 | transaction | customer_id、order_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1139 | dme_ads.tb_dme_sellin_maizhi_temp04 | transaction | order_id、product_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1140 | dme_ads.tb_dme_sellin_maizhi_temp04 | transaction | order_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1141 | dme_ads.tb_dme_sellin_maizhi_tmp_20260916 | transaction | customer_id、order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1142 | dme_ads.tb_dme_sellin_maizhi_tmp_20260916 | transaction | order_id、product_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1143 | dme_ads.tb_dme_sellin_maizhi_tmp_20260916 | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1144 | dme_ads.tb_dme_sellin_maizhi | transaction | customer_id、order_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1145 | dme_ads.tb_dme_sellin_maizhi | transaction | order_id、product_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1146 | dme_ads.tb_dme_sellin_maizhi | transaction | order_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1147 | dme_ads.tb_dme_sellout_inventory_data_source | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_1148 | dme_ads.tb_fcst_actual_bts_detail_v2_fcst_total_title | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_1149 | dme_ads.tb_fcst_actual_bts_detail_v2_fcst_total | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1150 | dme_ads.tb_fcst_actual_bts_detail_v2_fcst_total | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1151 | dme_ads.tb_fcst_actual_bts_detail_v2_tmp1 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1152 | dme_ads.tb_fcst_actual_bts_detail_v2_tmp1 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1153 | dme_ads.tb_fcst_actual_bts_detail_v2 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1154 | dme_ads.tb_fcst_actual_bts_detail_v2 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |

## process_candidate_006

只列出前 50 行，共 542 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_1396 | dme_ads.tb_actual_data_bts_v3 | periodic | gr55_month_max | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1397 | dme_ads.tb_actual_data_bts_v3 | periodic | ke24_month_max | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1398 | dme_ads.tb_actual_data_bts_v3 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1399 | dme_ads.tb_actual_data_bts_v3 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1400 | dme_ads.tb_actual_data_bts_v4 | periodic | ke24_month_max | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1401 | dme_ads.tb_actual_data_bts_v4 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1402 | dme_ads.tb_actual_data_bts_v4 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1403 | dme_ads.tb_ecom_pos_data_source | aggregation | customer_code、ds | strong | - |  | false |  |
| grain_candidate_1404 | dme_ads.tb_fcst_data_update_to_bts_v3_tmp03 | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_1405 | dme_ads.tb_fcst_data_update_to_bts_v3_tmp06 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_1406 | dme_ads.tb_fcst_data_update_to_bts_v4_tmp03 | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_1407 | dme_ads.tb_fcst_data_update_to_bts_v4_tmp06 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_1408 | dme_ads.tb_master_data_customer_tpm | aggregation | customer_code、ds | strong | - |  | false |  |
| grain_candidate_1409 | dme_ads.tb_monitor_master_data_store_bu_loss_ecom_temp_01 | aggregation | dist_store_code、max_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_1410 | dme_ads.tb_monitor_master_data_store_bu_loss_ecom_temp_01 | aggregation | dist_store_code、min_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_1411 | dme_ads.tb_monitor_master_data_store_bu_loss_ecom_temp_01 | aggregation | henkel_store_code、max_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_1412 | dme_ads.tb_monitor_master_data_store_bu_loss_ecom_temp_01 | aggregation | henkel_store_code、min_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_1413 | dme_ads.tb_npd_shelves_schedule_info | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_1414 | dme_ads.tb_sales_city_attack_customer_tmp3_02 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1415 | dme_ads.tb_sales_city_attack_customer_tmp3_02 | periodic | year | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1416 | dme_ads.tb_sales_city_attack_customer_tmp8 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1417 | dme_ads.tb_sales_city_attack_customer_tmp8 | periodic | year | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1418 | dme_ads.tb_sales_daliy_report_ka_store_sop_tmp1 | aggregation | customer_code、data_date | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_1419 | dme_ads.tb_sales_daliy_report_ka_store_sop_tmp1 | periodic | customer_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1420 | dme_ads.tb_sales_daliy_report_ka_store_sop_tmp1 | periodic | customer_code、quarter | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1421 | dme_ads.tb_sales_daliy_report_ka_store_sop_tmp1 | periodic | customer_code、years | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1422 | dme_ads.tb_sales_daliy_report_ka_store_sop_tmp1 | aggregation | data_date、store_code | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_1423 | dme_ads.tb_sales_daliy_report_ka_store_sop_tmp1 | periodic | months、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1424 | dme_ads.tb_sales_daliy_report_ka_store_sop_tmp1 | periodic | quarter、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1425 | dme_ads.tb_sales_daliy_report_ka_store_sop_tmp1 | periodic | store_code、years | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1426 | dme_ads.tb_so_pos_data_bts_v3_tmp10 | periodic | months | strong | no_identifier_signal |  | false |  |
| grain_candidate_1427 | dme_ads.tb_so_pos_data_bts_v3_tmp9 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_1428 | dme_ads.vs_ks_pos_test | periodic | balance_month、dist_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1429 | dme_ads.vs_ks_pos_test | periodic | balance_month、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_1430 | dme_ads.vs_ks_pos_test | aggregation | bill_date、dist_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1431 | dme_ads.vs_ks_pos_test | aggregation | bill_date、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1432 | dme_ads.vs_ks_pos_test | aggregation | created_at、dist_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1433 | dme_ads.vs_ks_pos_test | aggregation | created_at、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1434 | dme_ads.vs_ks_pos_test | aggregation | dist_store_code、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1435 | dme_ads.vs_ks_pos_test | aggregation | dist_store_code、expire_date | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1436 | dme_ads.vs_ks_pos_test | aggregation | dist_store_code、order_payment_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1437 | dme_ads.vs_ks_pos_test | aggregation | dist_store_code、transfer_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1438 | dme_ads.vs_ks_pos_test | aggregation | dist_store_code、txn_date | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1439 | dme_ads.vs_ks_pos_test | aggregation | dist_store_code、update_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1440 | dme_ads.vs_ks_pos_test | aggregation | ds、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1441 | dme_ads.vs_ks_pos_test | aggregation | expire_date、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1442 | dme_ads.vs_ks_pos_test | aggregation | order_payment_time、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1443 | dme_ads.vs_ks_pos_test | aggregation | store_code、transfer_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1444 | dme_ads.vs_ks_pos_test | aggregation | store_code、txn_date | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_1445 | dme_ads.vs_ks_pos_test | aggregation | store_code、update_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |

## process_candidate_007

只列出前 50 行，共 173 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_1938 | dme_ads.tb_actual_data_bts_v3_tmp3 | periodic | gr55_month_max | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1939 | dme_ads.tb_actual_data_bts_v3_tmp3 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1940 | dme_ads.tb_actual_data_bts_v3_tmp3 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1941 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp3 | periodic | customer_code、month | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1942 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp3 | periodic | customer_code、quarter | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1943 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp3 | periodic | customer_code、year | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1944 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp4 | periodic | customer_code、month_type | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1945 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp4 | periodic | customer_code、month | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1946 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp4 | periodic | customer_code、quarter | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1947 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_bu_tmp4 | periodic | customer_code、year | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1948 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_tmp3 | periodic | customer_code、month | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1949 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_tmp3 | periodic | customer_code、quarter | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1950 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_tmp3 | periodic | customer_code、year | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1951 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_tmp4 | periodic | customer_code、month_type | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1952 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_tmp4 | periodic | customer_code、month | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1953 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_tmp4 | periodic | customer_code、quarter | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1954 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_tmp4 | periodic | customer_code、year | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1955 | dme_ads.tb_controlling_reports_database_by_customer_mf | snapshot | customer_idh_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1956 | dme_ads.tb_controlling_reports_database_by_customer_mf | snapshot | customer_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1957 | dme_ads.tb_controlling_reports_database_by_customer_mf | snapshot | customer_type_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1958 | dme_ads.tb_controlling_reports_database_by_customer_mf | snapshot | region_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1959 | dme_ads.tb_controlling_reports_database_by_customer_mf | snapshot | system_name_snapshot | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1960 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp1 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1961 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp1 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1962 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp3 | periodic | ke24_month_max | strong | no_identifier_signal |  | false |  |
| grain_candidate_1963 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp4 | periodic | inv_month_wts | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1964 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp4 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1965 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp4 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1966 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp5 | periodic | months | strong | no_identifier_signal |  | false |  |
| grain_candidate_1967 | dme_ads.tb_fcst_actual_bts_detail_v4_tmp1 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1968 | dme_ads.tb_fcst_actual_bts_detail_v4_tmp1 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1969 | dme_ads.tb_fcst_actual_bts_detail_v4_tmp3 | periodic | ke24_month_max | strong | no_identifier_signal |  | false |  |
| grain_candidate_1970 | dme_ads.tb_fcst_actual_bts_detail_v4_tmp4 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1971 | dme_ads.tb_fcst_actual_bts_detail_v4_tmp4 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1972 | dme_ads.tb_fcst_actual_bts_detail_v4_tmp5 | periodic | months | strong | no_identifier_signal |  | false |  |
| grain_candidate_1973 | dme_ads.tb_fcst_ar_allowance_bts_v2_tmp0 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1974 | dme_ads.tb_fcst_ar_allowance_bts_v2_tmp0 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1975 | dme_ads.tb_fcst_ar_allowance_bts_v2_tmp1 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1976 | dme_ads.tb_fcst_ar_allowance_bts_v2_tmp1 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1977 | dme_ads.tb_monitor_results_diff_data_source_temp_3 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_1978 | dme_ads.tb_monitor_results_diff_data_source | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_1979 | dme_ads.tb_sales_city_attack_customer_tmp0 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1980 | dme_ads.tb_sales_city_attack_customer_tmp0 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1981 | dme_ads.tb_sales_city_attack_customer_tmp1_01 | periodic | customer_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1982 | dme_ads.tb_sales_city_attack_customer_tmp1_01 | periodic | customer_code、years | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1983 | dme_ads.tb_sales_city_attack_customer_tmp1_01 | periodic | customer_id、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1984 | dme_ads.tb_sales_city_attack_customer_tmp1_01 | periodic | customer_id、years | strong | multiple_possible_keys |  | false |  |
| grain_candidate_1985 | dme_ads.tb_sales_city_attack_customer_tmp1 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1986 | dme_ads.tb_sales_city_attack_customer_tmp1 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_1987 | dme_ads.tb_sales_city_attack_customer_tmp2 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |

## process_candidate_008

只列出前 50 行，共 1046 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_2111 | dme_ads.dim_tb_inventore_sku_sale_dt_monthly | periodic | henkel_store_code、months | moderate | missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_2112 | dme_ads.dim_tb_inventore_sku_sale_dt_weekly | aggregation | day_id、henkel_store_code | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_2113 | dme_ads.dim_tb_inventore_sku_sale_dt_weekly | aggregation | henkel_store_code、min_day_id | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_2114 | dme_ads.dim_tb_inventore_sku_sale_dt_weekly | periodic | henkel_store_code、months | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_2115 | dme_ads.dim_tb_inventore_sku_sale_dt_weekly | periodic | henkel_store_code、week_id | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_2116 | dme_ads.dim_tb_inventore_sku_sale_dt | periodic | henkel_store_code、months | moderate | missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_2117 | dme_ads.dim_tb_inventory_sku_distributor_sale_ws | periodic | henkel_store_code、months | moderate | missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_2118 | dme_ads.dim_tb_inventory_sku_sale_dt_monthly | periodic | henkel_store_code、months | moderate | missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_2119 | dme_ads.dim_tb_inventory_sku_sale_dt_weekly | aggregation | day_id、henkel_store_code | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_2120 | dme_ads.dim_tb_inventory_sku_sale_dt_weekly | aggregation | henkel_store_code、min_day_id | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_2121 | dme_ads.dim_tb_inventory_sku_sale_dt_weekly | periodic | henkel_store_code、months | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_2122 | dme_ads.dim_tb_inventory_sku_sale_dt_weekly | periodic | henkel_store_code、week_id | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_2123 | dme_ads.dt_sellout_data_tmp | aggregation | customer_code、dt_date | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2124 | dme_ads.dt_sellout_data_tmp | aggregation | customer_code、min_day_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2125 | dme_ads.dt_sellout_data_tmp | aggregation | customer_code、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2126 | dme_ads.dt_sellout_data_tmp | aggregation | dt_date、henkel_store_code | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2127 | dme_ads.dt_sellout_data_tmp | aggregation | dt_date、product_line_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2128 | dme_ads.dt_sellout_data_tmp | aggregation | henkel_store_code、min_day_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2129 | dme_ads.dt_sellout_data_tmp | aggregation | henkel_store_code、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2130 | dme_ads.dt_sellout_data_tmp | aggregation | min_day_id、product_line_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2131 | dme_ads.dt_sellout_data_tmp | aggregation | product_line_id、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2132 | dme_ads.dt_sellout_dim_tmp | aggregation | customer_code、dt_date | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2133 | dme_ads.dt_sellout_dim_tmp | aggregation | customer_code、min_day_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2134 | dme_ads.dt_sellout_dim_tmp | aggregation | customer_code、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2135 | dme_ads.dt_sellout_dim_tmp | aggregation | dt_date、henkel_store_code | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2136 | dme_ads.dt_sellout_dim_tmp | aggregation | dt_date、product_line_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2137 | dme_ads.dt_sellout_dim_tmp | aggregation | henkel_store_code、min_day_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2138 | dme_ads.dt_sellout_dim_tmp | aggregation | henkel_store_code、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2139 | dme_ads.dt_sellout_dim_tmp | aggregation | min_day_id、product_line_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2140 | dme_ads.dt_sellout_dim_tmp | aggregation | product_line_id、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2141 | dme_ads.ecom_sellout_month_data_tmp | periodic | customer_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_2142 | dme_ads.ecom_sellout_month_data_tmp | aggregation | customer_code、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2143 | dme_ads.ecom_sellout_month_data_tmp | periodic | henkel_store_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_2144 | dme_ads.ecom_sellout_month_data_tmp | aggregation | henkel_store_code、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2145 | dme_ads.ecom_sellout_month_data_tmp | periodic | months、product_line_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_2146 | dme_ads.ecom_sellout_month_data_tmp | aggregation | product_line_id、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2147 | dme_ads.ecom_sellout_month_dim_tmp | periodic | customer_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_2148 | dme_ads.ecom_sellout_month_dim_tmp | aggregation | customer_code、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2149 | dme_ads.ecom_sellout_month_dim_tmp | periodic | henkel_store_code、months | strong | multiple_possible_keys |  | false |  |
| grain_candidate_2150 | dme_ads.ecom_sellout_month_dim_tmp | aggregation | henkel_store_code、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2151 | dme_ads.ecom_sellout_month_dim_tmp | periodic | months、product_line_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_2152 | dme_ads.ecom_sellout_month_dim_tmp | aggregation | product_line_id、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2153 | dme_ads.nka_sellout_data_tmp | aggregation | dt_date、henkel_store_code | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2154 | dme_ads.nka_sellout_data_tmp | aggregation | dt_date、product_line_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2155 | dme_ads.nka_sellout_data_tmp | aggregation | henkel_store_code、min_day_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2156 | dme_ads.nka_sellout_data_tmp | aggregation | henkel_store_code、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2157 | dme_ads.nka_sellout_data_tmp | aggregation | min_day_id、product_line_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2158 | dme_ads.nka_sellout_data_tmp | aggregation | product_line_id、time_type | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2159 | dme_ads.nka_sellout_dim_tmp | aggregation | dt_date、henkel_store_code | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_2160 | dme_ads.nka_sellout_dim_tmp | aggregation | dt_date、product_line_id | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |

## process_candidate_009

只列出前 50 行，共 397 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_3157 | dme_ads.ads_sellin_brandcomparison_d | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_3158 | dme_ads.ads_sellin_report_d | periodic | tracking_period | strong | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3159 | dme_ads.ads_tb_sku_sale_summary_prof_by_customer | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, insufficient_evidence |  | false |  |
| grain_candidate_3160 | dme_ads.dim_tb_inventory_sku_sale_ecom_monthly | periodic | customer_code、months | moderate | missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3161 | dme_ads.ecom_sale_data_tmp_test | aggregation | customer_code、dt_date | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_3162 | dme_ads.ecom_sale_data_tmp_test | aggregation | customer_code、dt_type | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_3163 | dme_ads.ecom_sale_data_tmp_test | periodic | customer_code、months | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3164 | dme_ads.ecom_sale_data_tmp_test | aggregation | customer_code、time_type | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_3165 | dme_ads.ecom_stock_data_tmp_test | periodic | customer_code、month | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3166 | dme_ads.ecom_stock_data_tmp_test | periodic | month、product_id | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3167 | dme_ads.ke24_data_tmp_test | aggregation | customer_id、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3168 | dme_ads.ke24_data_tmp_test | periodic | customer_id、month | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3169 | dme_ads.ke24_data_tmp_test | periodic | customer_id、quarter | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3170 | dme_ads.ke24_data_tmp_test | periodic | customer_id、week | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3171 | dme_ads.ke24_data_tmp_test | periodic | customer_id、year | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3172 | dme_ads.ke24_data_tmp_test | aggregation | ds、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3173 | dme_ads.ke24_data_tmp_test | periodic | month、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3174 | dme_ads.ke24_data_tmp_test | periodic | product_line_code、quarter | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3175 | dme_ads.ke24_data_tmp_test | periodic | product_line_code、week | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3176 | dme_ads.ke24_data_tmp_test | periodic | product_line_code、year | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3177 | dme_ads.tb_actual_data_bts1_tmp | periodic | month_en | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3178 | dme_ads.tb_actual_data_bts1_tmp | periodic | month | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3179 | dme_ads.tb_actual_data_bts1_tmp | periodic | quarter | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3180 | dme_ads.tb_actual_data_bts1_tmp | periodic | year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3181 | dme_ads.tb_actual_data_bts1 | periodic | month_en | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3182 | dme_ads.tb_actual_data_bts1 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3183 | dme_ads.tb_actual_data_bts1 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3184 | dme_ads.tb_actual_data_bts_v2_tmp2 | periodic | ke24_month_max | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3185 | dme_ads.tb_actual_data_bts_v2_tmp2 | periodic | month_en | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3186 | dme_ads.tb_actual_data_bts_v2_tmp2 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3187 | dme_ads.tb_actual_data_bts_v2_tmp2 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3188 | dme_ads.tb_actual_data_bts_v2_tmp5 | periodic | foc_month_max | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3189 | dme_ads.tb_actual_data_bts_v2_tmp5 | periodic | gr55_month_max | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3190 | dme_ads.tb_actual_data_bts_v2_tmp5 | periodic | ke24_month_max | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3191 | dme_ads.tb_actual_data_bts_v2_tmp5 | periodic | month_en | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3192 | dme_ads.tb_actual_data_bts_v2_tmp5 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3193 | dme_ads.tb_actual_data_bts_v2_tmp5 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3194 | dme_ads.tb_actual_data_bts_v2_tmp8 | periodic | month_en | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3195 | dme_ads.tb_actual_data_bts_v2_tmp8 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3196 | dme_ads.tb_actual_data_bts_v2_tmp8 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3197 | dme_ads.tb_actual_data_bts_v3_tmp1 | periodic | month_en | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3198 | dme_ads.tb_actual_data_bts_v3_tmp1 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3199 | dme_ads.tb_actual_data_bts_v3_tmp1 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3200 | dme_ads.tb_actual_data_bts_v3_tmp2 | periodic | ke24_month_max | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3201 | dme_ads.tb_actual_data_bts_v3_tmp2 | periodic | month_en | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3202 | dme_ads.tb_actual_data_bts_v3_tmp2 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3203 | dme_ads.tb_actual_data_bts_v3_tmp2 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3204 | dme_ads.tb_actual_data_bts | periodic | month_en | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3205 | dme_ads.tb_actual_data_bts | periodic | months | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3206 | dme_ads.tb_actual_data_bts | periodic | years | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |

## process_candidate_010

只列出前 50 行，共 310 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_3554 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | periodic | balance_month、delivery_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3555 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | periodic | balance_month、dist_store_code_orig | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3556 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | periodic | balance_month、dist_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3557 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | periodic | balance_month、henkel_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3558 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | periodic | bill_month、delivery_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3559 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | periodic | bill_month、dist_store_code_orig | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3560 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | periodic | bill_month、dist_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3561 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | periodic | bill_month、henkel_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3562 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | aggregation | delivery_store_code、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3563 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | aggregation | delivery_store_code、transfer_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3564 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | aggregation | dist_store_code、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3565 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | aggregation | dist_store_code、transfer_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3566 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | aggregation | dist_store_code_orig、ds | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3567 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | aggregation | dist_store_code_orig、transfer_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3568 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | aggregation | ds、henkel_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3569 | dme_ads.dwd_ka_pos_data_sales_monthly_temp_111 | aggregation | henkel_store_code、transfer_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3570 | dme_ads.tb_actual_data_bts_v2_tmp6 | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, insufficient_evidence |  | false |  |
| grain_candidate_3571 | dme_ads.tb_actual_data_bts_v3_temp01 | snapshot | customer_idh_snapshot | strong | no_identifier_signal |  | false |  |
| grain_candidate_3572 | dme_ads.tb_actual_data_bts_v3_tmp5 | periodic | gr55_month_max | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3573 | dme_ads.tb_actual_data_bts_v3_tmp5 | periodic | ke24_month_max | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3574 | dme_ads.tb_actual_data_bts_v3_tmp5 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3575 | dme_ads.tb_actual_data_bts_v3_tmp5 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3576 | dme_ads.tb_actual_data_bts_v4_temp01 | snapshot | customer_idh_snapshot | strong | no_identifier_signal |  | false |  |
| grain_candidate_3577 | dme_ads.tb_actual_data_bts_v4_tmp5 | periodic | ke24_month_max | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3578 | dme_ads.tb_actual_data_bts_v4_tmp5 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3579 | dme_ads.tb_actual_data_bts_v4_tmp5 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3580 | dme_ads.tb_dashboard_mpd_sellout_summary_new_customer_flag_month_temp_add_vs | periodic | data_month | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3581 | dme_ads.tb_dashboard_mpd_sellout_summary_new_customer_flag_month_temp_add_vs | periodic | data_quarter | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3582 | dme_ads.tb_dashboard_mpd_sellout_summary_new_customer_flag_month_temp_add_vs | periodic | data_year | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3583 | dme_ads.tb_dashboard_mpd_sellout_summary_new_customer_flag_month_temp_add_vs | periodic | month_end | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3584 | dme_ads.tb_dashboard_mpd_sellout_summary_new_customer_flag_month_temp_add_vs | periodic | month_start | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3585 | dme_ads.tb_dashboard_mpd_sellout_summary_new_customer_flag_quarter_temp_add_vs | periodic | month_id | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3586 | dme_ads.tb_dashboard_mpd_sellout_summary_new_customer_flag_quarter_temp_add_vs | periodic | quarter_id | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3587 | dme_ads.tb_ecom_gtm_pl_cp | aggregation | ds、store_code | strong | - |  | false |  |
| grain_candidate_3588 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp0 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3589 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp0 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3590 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp2 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3591 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp2 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3592 | dme_ads.tb_fcst_actual_bts_detail_v3_tmp4_01 | periodic | months | moderate | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3593 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp0 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3594 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp0 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3595 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp1 | periodic | half_year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3596 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp1 | periodic | months_dis | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3597 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp1 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3598 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp1 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3599 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp2 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3600 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp2 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3601 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp3 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3602 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp3 | periodic | years | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3603 | dme_ads.tb_fcst_actual_ec_store_btsup_tmp4 | periodic | half_year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |

## process_candidate_011

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_3864 | dme_cdm.dwd_crm_trade | transaction | order_id、store_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3865 | dme_cdm.dwd_crm_trade | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3866 | dme_cdm.dwd_direct_sale_store_pos | aggregation | ds、henkel_product_code | strong | missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear |  | false |  |
| grain_candidate_3867 | dme_ods.s_pg_douyin_pos_order_logistics_info | transaction | order_id | strong | missing_sql_evidence, missing_lineage_evidence |  | false |  |

## process_candidate_012

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_3868 | dme_ods.s_sfa_ms_acvt | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_3869 | dme_ods.s_sfa_visit_inout_store | aggregation | ds、store_id | strong | missing_sql_evidence, missing_lineage_evidence |  | false |  |

## process_candidate_013

只列出前 50 行，共 556 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_3870 | dme_ads.dwd_pg_online_pos_douyin_temp00 | transaction | dist_product_code、order_no | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3871 | dme_ads.dwd_pg_online_pos_douyin_temp00 | transaction | dist_product_code、sub_order_no | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3872 | dme_ads.dwd_pg_online_pos_douyin_temp00 | transaction | order_no | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3873 | dme_ads.dwd_pg_online_pos_douyin_temp00 | transaction | sub_order_no | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3874 | dme_ads.dwd_pg_online_pos_tms_temp00 | transaction | dist_product_code、order_no | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3875 | dme_ads.dwd_pg_online_pos_tms_temp00 | transaction | dist_product_code、sub_order_no | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3876 | dme_ads.dwd_pg_online_pos_tms_temp00 | transaction | order_no | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3877 | dme_ads.dwd_pg_online_pos_tms_temp00 | transaction | sub_order_no | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_3878 | dme_ads.product_listing_date_temp | periodic | years | strong | no_identifier_signal |  | false |  |
| grain_candidate_3879 | dme_ads.tb_consumer_ecom_sku_sales | aggregation | ds、product_line_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3880 | dme_ads.tb_consumer_ecom_sku_sales | aggregation | ds、store_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3881 | dme_ads.tb_consumer_ecom_sku_user_sales | aggregation | ds、product_line_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3882 | dme_ads.tb_consumer_ecom_sku_user_sales | aggregation | ds、store_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3883 | dme_ads.tb_dashboard_pos_sale_activity_nka_temp00 | aggregation | day_id、store_code | strong | time_semantics_unclear |  | false |  |
| grain_candidate_3884 | dme_ads.tb_dashboard_pos_sale_activity_nka_temp01 | periodic | months、store_code | strong | - |  | false |  |
| grain_candidate_3885 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp01 | aggregation | bill_date、delivery_store_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3886 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp01 | aggregation | bill_date、dist_store_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3887 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp01 | aggregation | bill_date、henkel_store_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3888 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp01 | periodic | bill_month、delivery_store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3889 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp01 | periodic | bill_month、dist_store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3890 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp01 | periodic | bill_month、henkel_store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3891 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp02 | periodic | month_end | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3892 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp02 | periodic | month_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3893 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp02 | periodic | month_start | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3894 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp02 | periodic | quarter_end | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3895 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp02 | periodic | quarter_start | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3896 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp02 | periodic | year_end | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3897 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp02 | periodic | year_start | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_3898 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | aggregation | bill_date、delivery_store_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3899 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | aggregation | bill_date、dist_store_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3900 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | aggregation | bill_date、henkel_store_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_3901 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | bill_month、delivery_store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3902 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | bill_month、dist_store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3903 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | bill_month、henkel_store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3904 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | delivery_store_code、month_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3905 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | delivery_store_code、month_start | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3906 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | delivery_store_code、quarter_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3907 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | delivery_store_code、quarter_start | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3908 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | delivery_store_code、year_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3909 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | delivery_store_code、year_start | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3910 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | dist_store_code、month_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3911 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | dist_store_code、month_start | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3912 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | dist_store_code、quarter_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3913 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | dist_store_code、quarter_start | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3914 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | dist_store_code、year_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3915 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | dist_store_code、year_start | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3916 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | henkel_store_code、month_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3917 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | henkel_store_code、month_start | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3918 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | henkel_store_code、quarter_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_3919 | dme_ads.tb_dashboard_pos_sale_summary_nka_temp03 | periodic | henkel_store_code、quarter_start | strong | multiple_possible_keys |  | false |  |

## process_candidate_014

只列出前 50 行，共 190 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_4426 | dme_ads.ads_media_kol_for_conversion_d | periodic | month | strong | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4427 | dme_ads.ads_media_tik_tok_video_idea_d | periodic | month | strong | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4428 | dme_ads.ads_media_tik_tok_video_product_d | periodic | month | strong | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4429 | dme_ads.dim_tb_controlling_analysis_03_temp | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_4430 | dme_ads.tb_controlling_analysis_01_temp | periodic | months | strong | no_identifier_signal |  | false |  |
| grain_candidate_4431 | dme_ads.tb_controlling_analysis_02_temp | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_4432 | dme_ads.tb_crm_member_item_list1 | transaction | order_id、product_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4433 | dme_ads.tb_crm_member_item_list1 | transaction | order_id、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4434 | dme_ads.tb_crm_member_item_list1 | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4435 | dme_ads.tb_crm_member_item_list2 | transaction | order_id、product_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4436 | dme_ads.tb_crm_member_item_list2 | transaction | order_id、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4437 | dme_ads.tb_crm_member_item_list2 | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4438 | dme_ads.tb_crm_member_item_list3 | transaction | order_id、product_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4439 | dme_ads.tb_crm_member_item_list3 | transaction | order_id、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4440 | dme_ads.tb_crm_member_item_list3 | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4441 | dme_ads.tb_crm_member_item_list4 | transaction | order_id、product_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4442 | dme_ads.tb_crm_member_item_list4 | transaction | order_id、product_line_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4443 | dme_ads.tb_crm_member_item_list4 | transaction | order_id | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4444 | dme_ads.tb_dim_product_nka_mapping_bu_hsa | aggregation | ds、product_code | strong | - |  | false |  |
| grain_candidate_4445 | dme_ads.tb_ecom_daily_report_order_analysis_temp_02 | transaction | order_no | strong | missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4446 | dme_ads.tb_mediabb_hierarchy | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4447 | dme_ads.tb_mediabb_media_social_performance | aggregation | ds、key_id_product_line | strong | aggregation_level_unclear |  | false |  |
| grain_candidate_4448 | dme_ads.tb_monitor_master_data_product_others_info | aggregation | ds、product_code | strong | - |  | false |  |
| grain_candidate_4449 | dme_ads.tb_mtk_pos_drs_temp08 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4450 | dme_ads.tb_mtk_pos_drs_temp08 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4451 | dme_ads.tb_mtk_pos_drs_temp09 | periodic | months | strong | no_identifier_signal |  | false |  |
| grain_candidate_4452 | dme_ads.tb_mtk_pos_drs_temp10_1 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_4453 | dme_ads.tb_mtk_so_drs_temp08 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4454 | dme_ads.tb_mtk_so_drs_temp08 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4455 | dme_ads.tb_mtk_so_drs_temp09 | periodic | months | strong | no_identifier_signal |  | false |  |
| grain_candidate_4456 | dme_ads.tb_mtk_so_drs_temp10_1 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_4457 | dme_ads.tb_mtk_stock_drs_temp04 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4458 | dme_ads.tb_mtk_stock_drs_temp04 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4459 | dme_ads.tb_mtk_stock_drs_temp05 | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4460 | dme_ads.tb_mtk_stock_drs_temp05 | periodic | quarter_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4461 | dme_ads.tb_mtk_stock_drs_temp05 | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4462 | dme_ads.tb_mtk_stock_drs_temp07 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_4463 | dme_ads.tb_yangshi_master_data_product_info | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4464 | dme_cdm.dim_master_data_product_price_temp_01 | unknown | - | weak | no_identifier_signal, time_semantics_unclear, aggregation_level_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4465 | dme_cdm.dim_master_data_product_price | unknown | - | weak | no_identifier_signal, time_semantics_unclear, aggregation_level_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4466 | dme_cdm.dwd_competitor_offline_promotion_detail_info | aggregation | ds、is_new_product_code | strong | aggregation_level_unclear |  | false |  |
| grain_candidate_4467 | dme_cdm.dwd_crm_trade_goods_detail | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4468 | dme_cdm.dwd_ecom_lily_product_prod_prop_mapping_temp | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, aggregation_level_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4469 | dme_cdm.dwd_ecom_order_detail_info_lily_temp | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4470 | dme_cdm.dwd_master_data_product_bu_temp_01 | aggregation | billing_date、product_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4471 | dme_cdm.dwd_master_data_product_bu_temp_01 | aggregation | create_time、product_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4472 | dme_cdm.dwd_master_data_product_bu_temp_01 | aggregation | modify_time、product_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4473 | dme_cdm.dwd_master_data_product_bu_temp_02 | aggregation | billing_date、product_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4474 | dme_cdm.dwd_master_data_product_bu_temp_02 | aggregation | create_time、product_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4475 | dme_cdm.dwd_master_data_product_bu_temp_02 | aggregation | ds、product_code | strong | multiple_possible_keys, time_semantics_unclear, aggregation_level_unclear |  | false |  |

## process_candidate_015

只列出前 50 行，共 84 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_4616 | dme_ads.tb_dashboard_annual_sales_summary_v2 | periodic | inventory_cycle_monthly_mom | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4617 | dme_ads.tb_dashboard_annual_sales_summary_v2 | periodic | inventory_cycle_monthly_yoy | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4618 | dme_ads.tb_dashboard_annual_sales_summary_v2 | periodic | inventory_cycle_monthly | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4619 | dme_ads.tb_dashboard_annual_sales_summary_v2 | periodic | month | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4620 | dme_ads.tb_dashboard_annual_sales_summary_v2 | periodic | year | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4621 | dme_ads.tb_dashboard_annual_sales_summary | periodic | inventory_cycle_monthly_mom | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4622 | dme_ads.tb_dashboard_annual_sales_summary | periodic | inventory_cycle_monthly_yoy | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4623 | dme_ads.tb_dashboard_annual_sales_summary | periodic | inventory_cycle_monthly | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4624 | dme_ads.tb_dashboard_annual_sales_summary | periodic | month | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4625 | dme_ads.tb_dashboard_annual_sales_summary | periodic | year | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4626 | dme_ads.tb_ecom_order_detail_info_mid | periodic | month | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, insufficient_evidence |  | false |  |
| grain_candidate_4627 | dme_ads.tb_keywords_type_mapping_kunchi | aggregation | ds、store_id | strong | - |  | false |  |
| grain_candidate_4628 | dme_ads.tb_monitor_master_data_store_bu_loss_dms_temp_02 | aggregation | dist_store_code、max_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4629 | dme_ads.tb_monitor_master_data_store_bu_loss_dms_temp_02 | aggregation | dist_store_code、min_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4630 | dme_ads.tb_monitor_master_data_store_bu_loss_dms_temp_02 | aggregation | henkel_store_code、max_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4631 | dme_ads.tb_monitor_master_data_store_bu_loss_dms_temp_02 | aggregation | henkel_store_code、min_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4632 | dme_ads.tb_monitor_master_data_store_bu_loss_ka_temp_03 | aggregation | dist_store_code、max_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4633 | dme_ads.tb_monitor_master_data_store_bu_loss_ka_temp_03 | aggregation | dist_store_code、min_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4634 | dme_ads.tb_monitor_master_data_store_bu_loss_ka_temp_03 | aggregation | henkel_store_code、max_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4635 | dme_ads.tb_monitor_master_data_store_bu_loss_ka_temp_03 | aggregation | henkel_store_code、min_sales_day | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4636 | dme_ads.tb_monitor_master_data_store_bu_loss_remark | aggregation | ds、store_code | strong | - |  | false |  |
| grain_candidate_4637 | dme_ads.tb_monitor_master_data_store_bu_loss | aggregation | ds、store_code | strong | - |  | false |  |
| grain_candidate_4638 | dme_ads.tb_order_sell_in_tpm_temp1 | aggregation | end_date、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4639 | dme_ads.tb_order_sell_in_tpm_temp1 | aggregation | expire_date、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4640 | dme_ads.tb_order_sell_in_tpm_temp1 | aggregation | extract_time、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4641 | dme_ads.tb_order_sell_in_tpm_temp1 | periodic | month、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4642 | dme_ads.tb_order_sell_in_tpm_temp1 | aggregation | start_date、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4643 | dme_ads.tb_order_sell_in_tpm_temp1 | aggregation | store_code、update_time | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4644 | dme_ads.tb_order_sellout_crm_20240819 | aggregation | bill_date、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_4645 | dme_ads.tb_order_sellout_crm_20240819 | aggregation | data_date、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_4646 | dme_ads.tb_order_sellout_crm_20240819 | aggregation | ds、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_4647 | dme_ads.tb_order_sellout_crm_temp01 | aggregation | bill_date、store_code | strong | missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_4648 | dme_ads.tb_order_sellout_crm_temp02 | aggregation | bill_date、store_code | strong | missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_4649 | dme_ads.tb_order_sellout_crm_temp03 | aggregation | bill_date、store_code | strong | missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_4650 | dme_cdm.dwd_ec_douyin_account_launch | periodic | data_month | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4651 | dme_cdm.dwd_ec_douyin_account_launch | periodic | data_quarter | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4652 | dme_cdm.dwd_ec_douyin_account_launch | periodic | data_year | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4653 | dme_cdm.dwd_ec_paid_media_tm_traffic_df_temp1 | aggregation | create_time、store_code | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4654 | dme_cdm.dwd_ec_paid_media_tm_traffic_df_temp1 | aggregation | modify_time、store_code | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4655 | dme_cdm.dwd_ec_paid_media_tm_traffic_df_temp1 | periodic | months、store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4656 | dme_cdm.dwd_ecom_order_detail_info_bu_28705986_dirtydata_dw_system_dqc_1755291356130 | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4657 | dme_cdm.dwd_ecom_order_detail_info_bu_28705986_dirtydata_dw_system_dqc | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4658 | dme_cdm.dwd_ecom_order_detail_info_bu_28842618_dirtydata_dw_system_dqc | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4659 | dme_cdm.dwd_ecom_order_detail_info_bu_29694526_dirtydata_dw_system_dqc | aggregation | dqc_task_run_dt、ec_store_code_tp | moderate | missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4660 | dme_cdm.dwd_ecom_order_detail_info_bu_29694527_dirtydata_dw_system_dqc_1767616095345 | periodic | last_month_sales_day_cnt | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, insufficient_evidence |  | false |  |
| grain_candidate_4661 | dme_cdm.dwd_ecom_order_detail_info_bu_29694527_dirtydata_dw_system_dqc_1768846554471 | periodic | last_month_sales_day_cnt | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, insufficient_evidence |  | false |  |
| grain_candidate_4662 | dme_cdm.dwd_ecom_order_detail_info_bu_29694527_dirtydata_dw_system_dqc_1768932042345 | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4663 | dme_cdm.dwd_ecom_order_detail_info_bu_29694527_dirtydata_dw_system_dqc_1770258973537 | periodic | last_month_sales_day_cnt | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, insufficient_evidence |  | false |  |
| grain_candidate_4664 | dme_cdm.dwd_ecom_order_detail_info_bu_29694527_dirtydata_dw_system_dqc_1770710438205 | periodic | last_month_sales_day_cnt | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, insufficient_evidence |  | false |  |
| grain_candidate_4665 | dme_cdm.dwd_ecom_order_detail_info_bu_29694527_dirtydata_dw_system_dqc | aggregation | dqc_task_run_dt、ec_store_code_tp | moderate | missing_sql_evidence, missing_lineage_evidence |  | false |  |

## process_candidate_016

只列出前 50 行，共 154 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_4700 | dme_ads.ads_media_tik_tok_talent_d | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4701 | dme_ads.ads_media_tmall_insite_d | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4702 | dme_ads.ads_rfm_category_1yr | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4703 | dme_ads.ads_rfm_category_3yr | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4704 | dme_ads.tb_consumer_mapping_time_month | periodic | month_mom | strong | no_identifier_signal, multiple_possible_keys, missing_lineage_evidence |  | false |  |
| grain_candidate_4705 | dme_ads.tb_consumer_mapping_time_month | periodic | month_now | strong | no_identifier_signal, multiple_possible_keys, missing_lineage_evidence |  | false |  |
| grain_candidate_4706 | dme_ads.tb_consumer_mapping_time_month | periodic | month_yoy | strong | no_identifier_signal, multiple_possible_keys, missing_lineage_evidence |  | false |  |
| grain_candidate_4707 | dme_ads.tb_crm_channel | aggregation | ds、order_channel_id | strong | missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4708 | dme_ads.tb_dashboard_mid_channel_manual_order_monthly | periodic | dt_forecast_accuracy_last_year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4709 | dme_ads.tb_dashboard_mid_channel_manual_order_monthly | periodic | ecom_forecast_accuracy_last_year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4710 | dme_ads.tb_dashboard_mid_channel_manual_order_monthly | periodic | month | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4711 | dme_ads.tb_dashboard_mid_channel_manual_order_monthly | periodic | nka_forecast_accuracy_last_year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4712 | dme_ads.tb_dashboard_mid_channel_manual_order_monthly | periodic | walmart_satisfying_rate_last_year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4713 | dme_ads.tb_dashboard_mid_channel_manual_order_monthly | periodic | watsons_satisfying_rate_last_year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4714 | dme_ads.tb_dashboard_mid_channel_manual_order_monthly | periodic | ws_forecast_accuracy_last_year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4715 | dme_ads.tb_dashboard_mid_channel_manual_order_monthly | periodic | year | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4716 | dme_ads.tb_dept_user_log_info | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4717 | dme_ads.tb_l17_pure_mkt_detail_tmp0 | periodic | years | moderate | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4718 | dme_ads.tb_l17_pure_mkt_detail_tmp | periodic | years | moderate | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4719 | dme_ads.tb_l17_pure_mkt_detail | periodic | years | strong | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4720 | dme_ads.tb_l17_pure_mkt_summary | periodic | month_en | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4721 | dme_ads.tb_l17_pure_mkt_summary | periodic | months | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4722 | dme_ads.tb_l17_pure_mkt_summary | periodic | quarter | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4723 | dme_ads.tb_l17_pure_mkt_summary | periodic | years | strong | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4724 | dme_ads.tb_mediabb_mapping_time_temp_01 | periodic | time_now_week | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4725 | dme_ads.tb_mediabb_mapping_time_temp_01 | periodic | time_pop_week | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4726 | dme_ads.tb_mediabb_mapping_time_temp_01 | periodic | time_yoy_week | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4727 | dme_ads.tb_mediabb_mapping_time | periodic | time_now_week | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4728 | dme_ads.tb_mediabb_mapping_time | periodic | time_pop_week | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4729 | dme_ads.tb_mediabb_mapping_time | periodic | time_yoy_week | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4730 | dme_ads.tb_mediabb_social_retainer_performance | periodic | months | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4731 | dme_ads.tb_mediabb_social_retainer_performance | periodic | quarter | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4732 | dme_ads.tb_mediabb_social_retainer_performance | periodic | years | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4733 | dme_ads.tb_mpd_ngs_target_info | periodic | years | strong | no_identifier_signal |  | false |  |
| grain_candidate_4734 | dme_ads.tb_mtk_pos_drs_temp10 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_4735 | dme_ads.tb_mtk_so_drs_temp10 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_4736 | dme_ads.tb_mtk_stock_drs_temp06 | unknown | - | weak | no_identifier_signal, insufficient_evidence |  | false |  |
| grain_candidate_4737 | dme_ads.tb_ngs_mapping_time_temp | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4738 | dme_ads.tb_pl_mapping_time | periodic | month_mom | strong | no_identifier_signal, multiple_possible_keys, missing_lineage_evidence |  | false |  |
| grain_candidate_4739 | dme_ads.tb_pl_mapping_time | periodic | month_now | strong | no_identifier_signal, multiple_possible_keys, missing_lineage_evidence |  | false |  |
| grain_candidate_4740 | dme_ads.tb_pl_mapping_time | periodic | month_yoy | strong | no_identifier_signal, multiple_possible_keys, missing_lineage_evidence |  | false |  |
| grain_candidate_4741 | dme_ads.tb_social_content_database_by_hashtag_df | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4742 | dme_ads.tb_social_content_database_by_keywords_df | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4743 | dme_cdm.dwd_allocation_l17_o2o_temp01 | periodic | month | strong | no_identifier_signal |  | false |  |
| grain_candidate_4744 | dme_cdm.dwd_city_attack_gmv_city_share | periodic | begin_month | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4745 | dme_cdm.dwd_city_attack_gmv_city_share | periodic | end_month | strong | no_identifier_signal, multiple_possible_keys |  | false |  |
| grain_candidate_4746 | dme_cdm.dwd_delivery_schedule_control_cp_temp01 | unknown | - | weak | no_identifier_signal, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4747 | dme_cdm.dwd_ec_tm_channel_brand_sales_data | periodic | data_month | strong | no_identifier_signal |  | false |  |
| grain_candidate_4748 | dme_cdm.dwd_ec_tm_channel_category_sales_data | periodic | data_month | strong | no_identifier_signal |  | false |  |
| grain_candidate_4749 | dme_cdm.dwd_ecom_order_detail_info_bu_28705986_dirtydata_dw_system_dqc_1756882046029 | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |

## process_candidate_017

只列出前 50 行，共 825 行；其余行见 `analysis/understanding/business/grain-candidates.json`。

| grain_candidate_id | table_key | grain_pattern | candidate_keys | strength | unresolved_reasons | human_grain_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grain_candidate_4854 | dme_ads.ads_sampling_tmall_d | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, insufficient_evidence |  | false |  |
| grain_candidate_4855 | dme_ads.dim_tb_inventory_sku_sale_nka_daily | aggregation | day_id、henkel_store_code | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_4856 | dme_ads.dim_tb_inventory_sku_sale_nka_daily | periodic | henkel_store_code、months | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4857 | dme_ads.dim_tb_inventory_sku_sale_nka_monthly | periodic | henkel_store_code、months | moderate | missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4858 | dme_ads.dim_tb_inventory_sku_sale_nka_weekly | aggregation | day_id、henkel_store_code | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_4859 | dme_ads.dim_tb_inventory_sku_sale_nka_weekly | aggregation | henkel_store_code、min_day_id | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear |  | false |  |
| grain_candidate_4860 | dme_ads.dim_tb_inventory_sku_sale_nka_weekly | periodic | henkel_store_code、months | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4861 | dme_ads.dim_tb_inventory_sku_sale_nka_weekly | periodic | henkel_store_code、week_id | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4862 | dme_ads.pro_sell_out_temp | periodic | activity_month、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4863 | dme_ads.pro_sell_out_temp | aggregation | activity_time、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4864 | dme_ads.pro_sell_out_temp | aggregation | change_price_start_time、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4865 | dme_ads.pro_sell_out_temp | aggregation | day、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4866 | dme_ads.pro_sell_out_temp | periodic | month、store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4867 | dme_ads.pro_sell_out_temp | periodic | store_code、year | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4868 | dme_ads.tb_consumer_ecom_sku_sales_tmp | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, insufficient_evidence |  | false |  |
| grain_candidate_4869 | dme_ads.tb_consumer_nka_sku_sales_tmp | unknown | - | weak | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence, insufficient_evidence |  | false |  |
| grain_candidate_4870 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_v2_temp00 | periodic | dt_year、henkel_store_code | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4871 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_v2_temp00 | periodic | henkel_store_code、months | moderate | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4872 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_v2_temp06 | periodic | diff_month_cnt_12 | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4873 | dme_ads.tb_controlling_blue_table_clannel_collect_by_month_mf_v2_temp06 | periodic | months | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4874 | dme_ads.tb_dashboard_mid_pos_channel_sale_monthly | periodic | pos_amt_month | moderate | no_identifier_signal, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4875 | dme_ads.tb_dashboard_mid_store_monthly | periodic | category_rsp_sale_amt_month | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4876 | dme_ads.tb_dashboard_mid_store_monthly | periodic | category_total_sale_amt_month | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4877 | dme_ads.tb_dashboard_mid_store_monthly | periodic | new_sale_amt_month | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4878 | dme_ads.tb_dashboard_mid_store_monthly | periodic | old_sale_amt_month | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4879 | dme_ads.tb_dashboard_mid_store_monthly | periodic | rsp_sale_amt_month | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4880 | dme_ads.tb_dashboard_mid_store_monthly | periodic | total_sale_amt_month | moderate | no_identifier_signal, multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4881 | dme_ads.tb_dashboard_mpd_sale_summary_pos_close_store_flag_month_temp_add_vs | periodic | data_month、henkel_store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4882 | dme_ads.tb_dashboard_mpd_sale_summary_pos_close_store_flag_month_temp_add_vs | periodic | henkel_store_code、month_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4883 | dme_ads.tb_dashboard_mpd_sale_summary_pos_close_store_flag_month_temp_add_vs | periodic | henkel_store_code、month_start | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4884 | dme_ads.tb_dashboard_mpd_sale_summary_pos_close_store_recent_sales_date_temp_add_vs | periodic | data_month、henkel_store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4885 | dme_ads.tb_dashboard_mpd_sale_summary_pos_close_store_recent_sales_date_temp_add_vs | aggregation | henkel_store_code、max_data_date | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4886 | dme_ads.tb_dashboard_mpd_sale_summary_pos_close_store_recent_sales_date_temp_add_vs | periodic | henkel_store_code、month_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4887 | dme_ads.tb_dashboard_mpd_sale_summary_pos_close_store_recent_sales_date_temp_add_vs | periodic | henkel_store_code、month_start | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4888 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | aggregation | close_store_sales_date、henkel_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4889 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | periodic | data_month、henkel_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4890 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | aggregation | date_end、henkel_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4891 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | aggregation | date_type、henkel_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4892 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | aggregation | date_value、henkel_store_code | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4893 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | periodic | henkel_store_code、month_detail | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence |  | false |  |
| grain_candidate_4894 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | aggregation | henkel_store_code、new_store_first_sales_date | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4895 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | aggregation | henkel_store_code、oldprod_offshelves_recent_sales_date | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4896 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | aggregation | henkel_store_code、oldprod_onshelves_date | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4897 | dme_ads.tb_dashboard_mpd_sale_summary_pos_month_temp_add_vs | aggregation | henkel_store_code、product_listing_date | strong | multiple_possible_keys, missing_sql_evidence, missing_lineage_evidence, time_semantics_unclear, aggregation_level_unclear |  | false |  |
| grain_candidate_4898 | dme_ads.tb_dashboard_mpd_sale_summary_pos_new_store_flag_year_temp_add_vs | aggregation | data_date_min、henkel_store_code | strong | multiple_possible_keys, time_semantics_unclear |  | false |  |
| grain_candidate_4899 | dme_ads.tb_dashboard_mpd_sale_summary_pos_new_store_flag_year_temp_add_vs | periodic | henkel_store_code、month_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4900 | dme_ads.tb_dashboard_mpd_sale_summary_pos_new_store_flag_year_temp_add_vs | periodic | henkel_store_code、year_id | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4901 | dme_ads.tb_dashboard_mpd_sale_summary_pos_oldprod_offshelves_flag_month_temp_add_vs | periodic | data_month、henkel_store_code | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4902 | dme_ads.tb_dashboard_mpd_sale_summary_pos_oldprod_offshelves_flag_month_temp_add_vs | periodic | henkel_store_code、month_end | strong | multiple_possible_keys |  | false |  |
| grain_candidate_4903 | dme_ads.tb_dashboard_mpd_sale_summary_pos_oldprod_offshelves_flag_month_temp_add_vs | periodic | henkel_store_code、month_start | strong | multiple_possible_keys |  | false |  |

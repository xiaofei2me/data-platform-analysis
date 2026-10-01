# M2.3 Table Lineage

- 血缘边（去重后）：3432
- 跨 Workspace 血缘：1556
- 核心表候选：1789

## 跨 Workspace 血缘

| source | target | evidence |
| --- | --- | --- |
| dme_ods.S_COMPETITOR_ECOM_PROMOTION_DETAIL_INFO | dme_cdm.dwd_competitor_ecom_promotion_detail_info | 1 |
| dme_ods.S_COMPETITOR_O2O_PROMOTION_DETAIL_INFO | dme_cdm.dwd_competitor_o2o_promotion_detail_info | 1 |
| dme_ods.S_COMPETITOR_OFFLINE_PROMOTION_DETAIL_INFO | dme_cdm.dwd_competitor_offline_promotion_detail_info | 1 |
| dme_ods.S_JD_SEARCH_INDEX_INFO | dme_cdm.dwd_jd_search_index_01 | 1 |
| dme_ods.dim_area_trans | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_act_cnwc_sales_controlling | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_customer_not_require_info | dme_cdm.dwd_allocation_customer_not_require_info | 1 |
| dme_ods.s_allocation_customer_not_require_info | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_deduction_mapping_info | dme_cdm.dwd_allocation_deduction_mapping_info_temp01 | 1 |
| dme_ods.s_allocation_deduction_mapping_info | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_ke30_rawdata | dme_cdm.dwd_allocation_ke30_rawdata | 1 |
| dme_ods.s_allocation_ke30_rawdata | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l10_bdp | dme_cdm.dwd_allocation_l10_bdp | 1 |
| dme_ods.s_allocation_l10_bdp | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l10_dsr | dme_cdm.dwd_allocation_l10_dsr | 1 |
| dme_ods.s_allocation_l10_dsr | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l10_dsr_mapping | dme_cdm.dwd_allocation_l10_dsr_mapping_temp01 | 1 |
| dme_ods.s_allocation_l10_dsr_mapping | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l17_ba | dme_cdm.dwd_allocation_l17_ba | 1 |
| dme_ods.s_allocation_l17_ba | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l17_commitment_report | dme_cdm.dwd_allocation_l17_commitment_report | 1 |
| dme_ods.s_allocation_l17_commitment_report | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l17_kob1 | dme_cdm.dwd_allocation_l17_kob1 | 1 |
| dme_ods.s_allocation_l17_kob1 | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l17_o2o | dme_cdm.dwd_allocation_l17_o2o_temp01 | 1 |
| dme_ods.s_allocation_l17_o2o | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l17_order_mapping | dme_cdm.dwd_allocation_l17_order_mapping | 1 |
| dme_ods.s_allocation_l17_order_mapping | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l17_py_release | dme_cdm.dwd_allocation_l17_py_release | 1 |
| dme_ods.s_allocation_l17_py_release | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l6_accruals_cy_dt | dme_cdm.dwd_allocation_l6_accruals_cy | 1 |
| dme_ods.s_allocation_l6_accruals_cy_dt | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l6_accruals_cy_ecom | dme_cdm.dwd_allocation_l6_accruals_cy | 1 |
| dme_ods.s_allocation_l6_accruals_cy_ecom | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l6_accruals_cy_nka | dme_cdm.dwd_allocation_l6_accruals_cy | 1 |
| dme_ods.s_allocation_l6_accruals_cy_nka | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l6_copa_ke24 | dme_cdm.dwd_allocation_l6_copa_ke24 | 1 |
| dme_ods.s_allocation_l6_copa_ke24 | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_l6_py | dme_cdm.dwd_allocation_l6_accruals_py | 1 |
| dme_ods.s_allocation_l6_py | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_allocation_ttl_by_month | dme_cdm.dwd_allocation_ttl_by_month | 1 |
| dme_ods.s_allocation_ttl_by_month | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_ar_rawdata_sop | dme_cdm.dwd_ar_rawdata_temp | 1 |
| dme_ods.s_area_trans | dme_cdm.dim_area_trans | 1 |
| dme_ods.s_bdp_rawdata_sop | dme_cdm.dwd_bdp_rawdata_temp | 1 |
| dme_ods.s_bdp_rawdata_sop | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_blue_table_foc_sell_in | dme_cdm.dwd_blue_table_foc_sell_in | 1 |
| dme_ods.s_blue_table_foc_sell_in | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_blue_table_foc_sell_out_inventory | dme_cdm.dwd_blue_table_foc_sell_out_inventory | 1 |
| dme_ods.s_blue_table_foc_sell_out_inventory | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_brand_contract_campaign_kunchi | dme_cdm.dwd_ecom_daily_report_campaign | 1 |
| dme_ods.s_campaign_channel_mapping_kunchi | dme_cdm.dwd_ecom_daily_report_campaign | 1 |
| dme_ods.s_category_mapping_kunchi | dme_cdm.dwd_ecom_daily_report_traded_df | 1 |
| dme_ods.s_category_mapping_kunchi | dme_cdm.dwd_industry_index_merchantv | 1 |
| dme_ods.s_category_traded_brandv_kunchi | dme_cdm.dwd_ecom_daily_report_traded_df | 1 |
| dme_ods.s_city_attack_bc_gmv_ecom | dme_cdm.dwd_city_attack_bc_gmv_ecom | 1 |
| dme_ods.s_city_attack_bc_gmv_ecom | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_city_group_list | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_city_group_list | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_city_l17_mkt | dme_cdm.dwd_city_attack_city_l17 | 1 |
| dme_ods.s_city_attack_city_l17_mkt | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_city_l17_mkt | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_city_l17_tmkt | dme_cdm.dwd_city_attack_city_l17 | 1 |
| dme_ods.s_city_attack_city_l17_tmkt | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_city_l17_tmkt | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_discount_rate_ecom | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_discount_rate_ecom | dme_cdm.dwd_city_attack_discount_rate_ecom | 1 |
| dme_ods.s_city_attack_discount_rate_ecom | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_dist_list | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_dist_list | dme_cdm.dwd_city_attack_dist_list | 1 |
| dme_ods.s_city_attack_dist_list | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_gmv_city_share | dme_cdm.dwd_city_attack_gmv_city_share | 1 |
| dme_ods.s_city_attack_gmv_city_share_mpd | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_gmv_city_share_mpd | dme_cdm.dwd_city_attack_gmv_city_share_mpd | 1 |
| dme_ods.s_city_attack_gmv_city_share_mpd | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_rebate_contract_rate | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_rebate_contract_rate | dme_cdm.dwd_city_attack_rebate_contract_rate | 1 |
| dme_ods.s_city_attack_rebate_contract_rate | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_return_rsp_rate_ecom | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_return_rsp_rate_ecom | dme_cdm.dwd_city_attack_return_rsp_rate_ecom | 1 |
| dme_ods.s_city_attack_return_rsp_rate_ecom | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_store_gmv_ecom | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_store_gmv_ecom | dme_cdm.dwd_city_attack_store_gmv_ecom | 1 |
| dme_ods.s_city_attack_store_gmv_ecom | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_attack_weight_base_price_rate | dme_cdm.dwd_city_attack_data_update_info | 1 |
| dme_ods.s_city_attack_weight_base_price_rate | dme_cdm.dwd_city_attack_weight_base_price_rate | 1 |
| dme_ods.s_city_attack_weight_base_price_rate | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_city_attack_city_l17 | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_city_attack_gmv_city_share | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_city_attack_gmv_city_share_mpd | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_city_attack_store_gmv_ecom | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_direct_store_info | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_ecom_order_detail_info_bu_mid_temp_01 | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_ecom_order_detail_info_bu_temp_01 | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_ecom_order_detail_info_bu_woyi_temp_03 | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_ecom_order_return_info | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_ecom_order_return_info_bu_temp_01 | 1 |
| dme_ods.s_city_province_mapping | dme_cdm.dwd_ka_pos_data_sales_daily_temp1 | 1 |
| dme_ods.s_cnr_ar_simulation_sop | dme_cdm.dwd_cnr_ar_simulation_sop | 1 |
| dme_ods.s_competitor_ecom_promotion_detail_info | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_competitor_o2o_promotion_detail_info | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_competitor_offline_promotion_detail_info | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_controlling_blue_table_exchange_rate | dme_cdm.dim_controlling_blue_table_exchange_rate | 1 |
| dme_ods.s_controlling_blue_table_exchange_rate | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_controlling_channel_changes | dme_cdm.dwd_controlling_channel_changes_mf | 1 |
| dme_ods.s_controlling_channel_changes | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_controlling_kp_dt_target | dme_cdm.dwd_controlling_target_mf_v2_tmp1 | 1 |
| dme_ods.s_controlling_kp_ecom_target | dme_cdm.dwd_controlling_target_mf_v2_tmp1 | 1 |
| dme_ods.s_controlling_kp_nka_target | dme_cdm.dwd_controlling_target_mf_v2_tmp1 | 1 |
| dme_ods.s_controlling_kp_ws_target | dme_cdm.dwd_controlling_target_mf_v2_tmp1 | 1 |
| dme_ods.s_controlling_nes_report_lhc | dme_cdm.dwd_controlling_reports_database_mf | 1 |
| dme_ods.s_controlling_reports_database | dme_cdm.dwd_controlling_reports_database_mf | 1 |
| dme_ods.s_cp_controller_index_data | dme_cdm.dwd_fcst_data_bts_v4_tmp07 | 1 |
| dme_ods.s_cp_kp_data | dme_cdm.dwd_fcst_data_bts_v4_fcst_sales_temp00 | 1 |
| dme_ods.s_cp_mp_data | dme_cdm.dwd_fcst_data_bts_v4_fcst_sales_temp00 | 1 |
| dme_ods.s_cp_new_distributor_info | dme_cdm.dwd_customer_mapping_bts_v4_tmp | 1 |
| dme_ods.s_cp_new_distributor_info | dme_cdm.dwd_fcst_data_bts_v4_fcst_sales_temp00 | 1 |
| dme_ods.s_cp_new_distributor_info | dme_cdm.dwd_fcst_data_bts_v4_tmp07 | 1 |
| dme_ods.s_crm_member | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_crm_member_event_log | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_crm_member_social | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_crm_member_tag | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_crm_trade | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_crm_trade_goods_detail | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_cs_sell_in_henkel_calendar_mapping | dme_cdm.dwd_sales_report_cnr_data_tmp1 | 1 |
| dme_ods.s_cs_sell_in_henkel_calendar_mapping | dme_cdm.dwd_sales_report_va05_detail | 1 |
| dme_ods.s_cs_sell_in_ngs_target | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_cs_sell_in_ngs_target | dme_cdm.dwd_sales_report_ngs_target_tmp2 | 1 |
| dme_ods.s_cs_sell_in_ngs_target_prof_dt | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_cs_sell_in_ngs_target_prof_non_dt | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_cs_sell_in_order_status_mapping | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_cs_sell_in_order_status_mapping | dme_cdm.dwd_sales_report_cnr_data_tmp0 | 1 |
| dme_ods.s_cs_sell_in_order_status_mapping | dme_cdm.dwd_sales_report_cnr_data_tmp1 | 1 |
| dme_ods.s_cs_sell_in_order_status_mapping | dme_cdm.dwd_sales_report_va05_detail | 1 |
| dme_ods.s_cs_sell_in_product_bu_mapping | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_cs_sell_in_product_con_mapping | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_cs_sell_in_remaining_orders_mapping | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_cs_sell_in_target_prof | dme_cdm.dwd_sales_report_ngs_target_tmp0 | 1 |
| dme_ods.s_cs_sell_in_working_days_mapping | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_cs_sell_in_working_days_mapping | dme_cdm.dwd_sales_report_cnr_data_tmp0 | 1 |
| dme_ods.s_cs_sell_in_working_days_mapping | dme_cdm.dwd_sales_report_cnr_data_tmp1 | 1 |
| dme_ods.s_cs_sell_in_working_days_mapping | dme_cdm.dwd_sales_report_va05_detail | 1 |
| dme_ods.s_customer_mapping_info_bts | dme_cdm.dwd_customer_mapping_bts_v3 | 1 |
| dme_ods.s_customer_mapping_info_bts | dme_cdm.dwd_customer_mapping_bts_v4 | 1 |
| dme_ods.s_customer_master_mapping_sop | dme_cdm.dwd_customer_sales_head_mapping_sop | 1 |
| dme_ods.s_customer_nka_sell_out_target_sop | dme_cdm.dwd_customer_ka_sell_out_target_sop | 1 |
| dme_ods.s_customer_profitability_bts_kp_lhc | dme_cdm.dwd_controlling_target_mf_v2_tmp1 | 1 |
| dme_ods.s_customer_profitability_bts_kp_lhc | dme_cdm.dwd_kp_sales_controlling_bts | 1 |
| dme_ods.s_customer_profitability_bts_kp_lhc | dme_cdm.dwd_kp_sales_controlling_bts_v2 | 1 |
| dme_ods.s_data_source_cs_sell_in_info | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_data_source_cs_sell_in_info | dme_cdm.dwd_sales_report_cnr_data_tmp0 | 1 |
| dme_ods.s_data_source_cs_sell_in_info | dme_cdm.dwd_sales_report_cnr_data_tmp1 | 1 |
| dme_ods.s_data_source_cs_sell_in_info | dme_cdm.dwd_sales_report_va05_detail | 1 |
| dme_ods.s_data_source_list_monitor | dme_cdm.dwd_data_source_list_update_monitor | 1 |
| dme_ods.s_delivery_schedule_control_cp | dme_cdm.dwd_delivery_schedule_control_cp_temp01 | 1 |
| dme_ods.s_demand_demonstration_rawdata | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_demand_demonstration_rawdata | dme_cdm.dwd_demand_demonstration_data | 1 |
| dme_ods.s_dist_prod_code_henkel_barcode_mapping | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_dist_prod_code_henkel_barcode_mapping | dme_cdm.dwd_ka_pos_data_sales_daily_mid_temp3 | 1 |
| dme_ods.s_dme_read_log_detail | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_dme_read_log_detail | dme_cdm.dwd_dme_read_log_info | 1 |
| dme_ods.s_dms_dms_data_sale | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_dms_dms_data_sale | dme_cdm.dwd_dms_data_sale_bu | 1 |
| dme_ods.s_dms_dms_data_sale | dme_cdm.dwd_dms_data_sale_bu_temp_02 | 1 |
| dme_ods.s_dms_dms_data_sale_maizhi | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_dms_dms_data_sale_maizhi | dme_cdm.dwd_dms_data_sale_bu_temp_01 | 1 |
| dme_ods.s_dms_dms_data_sale_manual | dme_cdm.dwd_dms_data_sale_bu_temp_02 | 1 |
| dme_ods.s_dms_dms_data_stock | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_dms_dms_data_stock | dme_cdm.dwd_dms_data_stock_bu_temp_01 | 1 |
| dme_ods.s_dms_dms_data_stock | dme_cdm.dwd_dms_data_stock_bu_temp_06 | 1 |
| dme_ods.s_dms_dms_data_stock_maizhi | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_dms_dms_data_stock_maizhi | dme_cdm.dwd_dms_data_stock_bu_temp_02 | 1 |
| dme_ods.s_dms_dms_data_stock_manual | dme_cdm.dwd_dms_data_stock_bu_temp_01 | 1 |
| dme_ods.s_dms_mdm_distributor | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_dms_mdm_store | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_dms_mdm_store | dme_cdm.dwd_dms_mdm_store | 1 |
| dme_ods.s_dt_dealercode_mapping_professional | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_dt_dealercode_mapping_professional | dme_cdm.dwd_dt_dealercode_mapping_professional | 1 |
| dme_ods.s_dt_month_target_professional | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_ec_aoxuncai_sales_info | dme_cdm.dwd_dms_data_sale_bu_temp_02 | 1 |
| dme_ods.s_ec_aoxuncai_stock_info | dme_cdm.dwd_dms_data_stock_bu_temp_01 | 1 |
| dme_ods.s_ec_core_product_line | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_ec_core_product_line | dme_cdm.dwd_ecom_core_product_line | 1 |
| dme_ods.s_ec_core_product_line | dme_cdm.dwd_master_data_product_bu | 1 |
| dme_ods.s_ec_douyin_activity_type | dme_cdm.dwd_ec_douyin_activity_type_temp_01 | 1 |
| dme_ods.s_ec_duomi_purchase_sales_inventory_info | dme_cdm.dwd_dms_data_sale_bu_temp_02 | 1 |
| dme_ods.s_ec_duomi_purchase_sales_inventory_info | dme_cdm.dwd_dms_data_stock_bu_temp_01 | 1 |
| dme_ods.s_ec_inventory_info_laundry | dme_cdm.dwd_data_source_list_update_monitor_temp_01 | 1 |
| dme_ods.s_ec_inventory_info_laundry | dme_cdm.dwd_dms_data_stock_bu_temp_06 | 1 |
| dme_ods.s_ec_kunc_inventory_info_laundry | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_ec_kunc_order_merge_info | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_ec_kunc_order_merge_info | dme_cdm.dwd_ecom_order_detail_info_kunc_temp | 1 |
| dme_ods.s_ec_kunc_order_merge_info | dme_cdm.dwd_ecom_order_info | 1 |
| dme_ods.s_ec_kunc_product_hierarchy_mapping_info | dme_cdm.dim_ecom_product_prop_mapping_temp_00 | 1 |
| dme_ods.s_ec_kunc_product_info | dme_cdm.dwd_ecom_standard_product_mapping_kunc_temp_00 | 1 |
| dme_ods.s_ec_kunc_product_mapping_info | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |
| dme_ods.s_ec_kunc_product_mapping_info | dme_cdm.dwd_ecom_standard_product_mapping_kunc_temp_01 | 1 |
| dme_ods.s_ec_kunc_product_sub_sku | dme_cdm.dwd_ecom_standard_product_mapping_kunc_temp_01 | 1 |
| dme_ods.s_ec_kunc_sales_daily | dme_cdm.dwd_data_source_list_update_monitor_temp_02 | 1 |

## 下游数量 Top 20

| table_key | downstream | upstream | evidence |
| --- | --- | --- | --- |
| dme_cdm.dwd_master_data_product_pos_bu | 115 | 1 | 120 |
| dme_cdm.dwd_master_data_customer_bu | 99 | 4 | 104 |
| dme_cdm.dwd_master_data_store_bu | 98 | 8 | 106 |
| dme_cdm.dim_day | 90 | 0 | 90 |
| dme_cdm.dwd_master_data_product_bu | 65 | 6 | 71 |
| dme_cdm.dwd_master_data_ka | 42 | 1 | 43 |
| dme_cdm.dwd_sap_ke24_sale_info_bu | 40 | 1 | 41 |
| dme_ads.tb_dashboard_mpd_sale_summary_date | 28 | 2 | 30 |
| dme_cdm.dwd_ecom_order_detail_info_bu | 27 | 4 | 31 |
| dme_ads.tb_inventory_sku_sale_allchannel_mid | 26 | 0 | 26 |
| dme_cdm.dwd_customer_mapping_bts_v3 | 24 | 2 | 26 |
| dme_cdm.dwd_customer_mapping_bts_v4 | 22 | 2 | 24 |
| dme_ods.s_city_province_mapping | 19 | 0 | 19 |
| dme_cdm.dwd_ka_pos_data_sales_monthly_bu | 18 | 3 | 21 |
| dme_ads.tb_dashboard_pos_sale_summary_nka | 17 | 5 | 22 |
| dme_cdm.dwd_ka_pos_data_sales_daily | 16 | 3 | 19 |
| dme_ads.tb_dashboard_mpd_sale_summary_pos_mid | 16 | 2 | 18 |
| dme_cdm.dwd_dms_data_stock_bu | 15 | 4 | 19 |
| dme_ads.tb_fcst_ar_allowance_bts_v2_tmp0 | 15 | 1 | 16 |
| dme_cdm.dwd_watsons_mapping_time_df | 15 | 0 | 15 |

排序依据 downstream_count 降序，只反映数据流向，不代表业务价值。

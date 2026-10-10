# M2.2 Layer Assessment

- 参与分析的表：3724
- 输入：`analysis/inventory/tables.json`
- 规则配置：`config/layer-rules.yaml`（version 1.0）

## Workspace Layer

| workspace_id | workspace_name | workspace_layer | table_count |
| --- | --- | --- | --- |
| 466337 | dme_cdm | CDM | 1072 |
| 466338 | dme_ods | ODS | 1175 |
| 466339 | dme_ads | ADS | 1477 |

workspace_layer 由 workspace_id 查 `workspace_layers` 得到，是结构事实，不是候选。

## 状态分布

| status | table_count |
| --- | --- |
| MATCH | 3663 |
| UNKNOWN | 61 |

## candidate_layer 分布

| candidate_layer | table_count |
| --- | --- |
| (未确定) | 61 |
| ADS | 1477 |
| DIM | 49 |
| DWD | 901 |
| DWS | 61 |
| ODS | 1175 |

## 未配置 Workspace

| workspace_id | workspace_name | table_count |
| --- | --- | --- |
_（无数据）_

未配置的 workspace_id 不做任何推断（不按 workspace_name 猜测），一律记为 UNKNOWN。

## UNKNOWN 明细

| table_identifier | workspace_id | workspace_name |
| --- | --- | --- |
| dme_cdm.active_data_month_tmp | 466337 | dme_cdm |
| dme_cdm.active_month_diff_tmp | 466337 | dme_cdm |
| dme_cdm.cd_test_20260506_column | 466337 | dme_cdm |
| dme_cdm.cd_test_20260506_table | 466337 | dme_cdm |
| dme_cdm.fct_adv_channel_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_adv_people_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_adv_product_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_ec_order_detail_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_ec_order_detail_df_temp | 466337 | dme_cdm |
| dme_cdm.fct_ec_order_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_jd_sampling_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_ka_pos_data_info_di_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_ke24_order_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_kol_branding_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_kol_conversion_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_pos_data_info_di_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_student_yewu_test_di_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_test_zsy_yewugocheng_di_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_tik_tok_talent_df_od000_v1 | 466337 | dme_cdm |
| dme_cdm.fct_tik_tok_video_idea_df_od000_v1 | 466337 | dme_cdm |

只列出前 20 条，完整明细见 `analysis/evidence/layer/assessments.json`。

## 跨层命名提示

| table_identifier | workspace_layer | 命中其他层 |
| --- | --- | --- |
| dme_ods.dim_area_trans | ODS | DIM |
| dme_ods.dim_area_trans_30055033_dirtydata_dw_system_dqc | ODS | DIM |
| dme_ods.dim_area_trans_30055034_dirtydata_dw_system_dqc | ODS | DIM |
| dme_ods.dim_crm_district_divide | ODS | DIM |
| dme_ods.dim_ed01_core_od001_v1 | ODS | DIM |
| dme_ods.dim_gd01_ch_core_od001_v1 | ODS | DIM |
| dme_ods.dim_gd01_core_od001_v1 | ODS | DIM |
| dme_ods.dim_hd01_core_od001_v1 | ODS | DIM |
| dme_ods.dim_hd01_leaf_core_od001_v1 | ODS | DIM |
| dme_ods.dim_hd01_lvl1_core_od001_v1 | ODS | DIM |
| dme_ods.dim_hd01_lvl2_core_od001_v1 | ODS | DIM |
| dme_ods.dim_hd01_lvl3_core_od001_v1 | ODS | DIM |
| dme_ods.dwd_master_data_customer_temp01 | ODS | DWD |
| dme_ods.dws_ed01_od000_v1 | ODS | DWS |
| dme_ods.dws_gd01_od000_v1 | ODS | DWS |
| dme_ods.dws_gd01_od001_v1 | ODS | DWS |
| dme_ads.dim_customer_trans | ADS | DIM |
| dme_ads.dim_day | ADS | DIM |
| dme_ads.dim_province | ADS | DIM |
| dme_ads.dim_tb_controlling_analysis_03_temp | ADS | DIM |

只列出前 20 条，完整明细见 `analysis/evidence/layer/assessments.json`。

candidate_layer 仍按 workspace_layer 判定，这里只提示表名带其他层命名前缀。

## CONFLICT 明细

| table_identifier | 命中的子层 |
| --- | --- |
_（无数据）_

完整明细见 `analysis/evidence/layer/assessments.json`。

## 说明

- workspace_layer 是配置事实；candidate_layer 是子层候选，两者都不是合规结论。
- CDM 是 DIM / DWD / DWS 的公共层总称，与子层不是同一级 Layer。
- UNKNOWN 只表示现有 Evidence 不足以判断 CDM 子层，不代表不符合命名规范；
  是否构成命名规范问题由后续 Convention Assessment 判定。
- CONFLICT 表示同时命中多个不同子层，candidate_layer 留空，不擅自选择。
- 只有同一张表命中分属不同子层的规则时才判定 CONFLICT；
  单条 prefix 规则或多个同层 prefix 不会产生 CONFLICT。
- ODS / ADS 的 candidate_layer 直接等于 workspace_layer；其他层的
  prefix / suffix 命中只记入 evidence（跨层命名提示），不改变 candidate。
- 只读 Inventory 输出与规则配置，不读取 SQL / Lineage / Profiling，
  也不修改 Inventory 与规则配置；Inventory 更新后需重新执行本阶段。

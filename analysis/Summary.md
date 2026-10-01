# Phase 2 Analysis Summary

> 只读 `source/` Snapshot，产物写入 `analysis/`。
> 本报告只包含事实、Candidate 与证据，不含业务结论。

## 1. 概览

| 指标 | 数值 |
| --- | --- |
| Workspace | 3 |
| DataWorks File（Snapshot 总数） | 4651 |
| 参与 Analysis 的 File（NodeId 有效） | 1449 |
| 排除的 File（NodeId 缺失） | 3202 |
| MaxCompute Table | 3719 |
| Column | 102603 |
| SQL 语句 | 1963 |
| 表引用记录 | 1273 |
| 血缘边 | 3442 |
| 可恢复错误 | 0 |

Snapshot File 全量保留；只有 NodeId 有效的 File 进入 SQL / Table Reference / Lineage Analysis，NodeId 缺失的 File 不产生 SQL Evidence，也不记为错误。

## 2. Workspace Inventory

| workspace_id | workspace_name | project | files | tables |
| --- | --- | --- | --- | --- |
| 466337 | dme_cdm | dme_cdm | 741 | 1069 |
| 466338 | dme_ods | dme_ods | 2236 | 1175 |
| 466339 | dme_ads | dme_ads | 1674 | 1475 |

## 3. DataWorks File Inventory

| 维度 | 数量 |
| --- | --- |
| File 总数 | 4651 |
| TASK 类 File | 2899 |
| SQL 格式 File | 2821 |
| NodeId 有效（参与 SQL Analysis） | 1449 |
| NodeId 缺失（仅保留在 Snapshot） | 3202 |
| 已读取到内容的 File | 559 |

## 4. MaxCompute Table Inventory

| workspace_id | table_count | column_count |
| --- | --- | --- |
| 466337 | 1069 | 29399 |
| 466338 | 1175 | 34803 |
| 466339 | 1475 | 38401 |

## 5. 层级候选（Layer Candidate）

| layer_candidate | table_count |
| --- | --- |
| (未识别) | 2626 |
| ADS | 47 |
| DIM | 76 |
| DWD | 903 |
| DWS | 64 |
| ODS | 3 |

依据 table_name_prefix 推断，只能写作 layer_candidate。

## 6. SQL Analysis

| parse_status | statement_count |
| --- | --- |
| success | 1963 |
| unsupported | 0 |
| error | 0 |

- 解析语句的 File：559
- 解析错误 / 不支持语句：0
- 表引用提取方式（按语句）：ast=1962，fallback=1
- Parser Compatibility Normalization 生效语句：1
- 因 NodeId 缺失被排除的 File：3202

只有 NodeId 有效的 File 进入 SQL Analysis；被排除的 File 不产生任何 statement / reference / lineage 证据。

Parser Compatibility Normalization 只在 syntax context 替换全角括号，string literal 与 comment 原样保留；statement.sql 仍是 raw SQL。

## 7. Table References

| 指标 | 数值 |
| --- | --- |
| 含 source 的语句 | 1264 |
| 含 target 的语句 | 1272 |
| 去重 source 表 | 1573 |
| 去重 target 表 | 1260 |

## 8. Table Lineage

| 指标 | 数值 |
| --- | --- |
| 血缘边（去重） | 3442 |
| 带多条证据的边 | 7 |
| 跨 Workspace 血缘 | 1560 |

## 9. Core Table Candidates

| table_key | downstream | upstream | evidence |
| --- | --- | --- | --- |
| dme_cdm.dwd_master_data_product_pos_bu | 116 | 1 | 121 |
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

排序依据 downstream_count 降序，属于候选，不代表业务优先级。
完整列表见 `analysis/lineage/core-table-candidates.json`。

## 10. Data Profiling

| 指标 | 数值 |
| --- | --- |
| 表级 Profiling | 3719 |
| 字段级 Profiling | 102603 |
| 有行级样本的表 | 0 |

全部为 metadata_only，未伪造任何行级统计量。

## 11. 错误摘要

_（无数据）_

完整错误见 `analysis/errors.json`，SQL 解析错误见 `analysis/sql/parse-errors.json`。

## 12. Analysis Limitations

- 只读取 `source/` Snapshot，不访问 DataWorks / MaxCompute / QuickBI 等外部 API。
- Analysis 输入只包含 NodeId 有效的 File；NodeId 缺失的 File 不产生 SQL Evidence。
- 表级血缘来自 SQL 文本解析，未做 Column Lineage。
- 层级、核心表均为 Candidate，不构成业务结论。
- 没有行级数据样本，因此不做 null / distinct / 唯一性判断。
- 调度依赖（周期任务上下游）不在本阶段范围内。
- 表名前缀未命中的表不给出 layer_candidate。
- 语句级解析失败的表引用无法提取，对应语句记录在 parse-errors.json。

# Phase 2 Analysis Summary

> 只读 `source/` Snapshot，产物写入 `analysis/`。
> 本报告只包含事实、Candidate 与证据，不含业务结论。

## 1. 概览

| 指标 | 数值 |
| --- | --- |
| Workspace | 3 |
| DataWorks File | 4651 |
| MaxCompute Table | 3719 |
| Column | 102603 |
| SQL 语句 | 8254 |
| 表引用记录 | 4775 |
| 血缘边 | 6501 |
| 可恢复错误 | 126 |

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
| 已读取到内容的 File | 2804 |

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
| success | 8128 |
| unsupported | 48 |
| error | 78 |

- 解析语句的 File：2804
- 解析错误 / 不支持语句：126

## 7. Table References

| 指标 | 数值 |
| --- | --- |
| 含 source 的语句 | 2557 |
| 含 target 的语句 | 4690 |
| 去重 source 表 | 2822 |
| 去重 target 表 | 3336 |

## 8. Table Lineage

| 指标 | 数值 |
| --- | --- |
| 血缘边（去重） | 6501 |
| 带多条证据的边 | 149 |
| 跨 Workspace 血缘 | 2330 |

## 9. Core Table Candidates

| table_key | downstream | upstream | evidence |
| --- | --- | --- | --- |
| dme_cdm.dim_day | 144 | 1 | 148 |
| dme_cdm.dwd_master_data_product_pos_bu | 144 | 1 | 159 |
| dme_cdm.dwd_master_data_customer_bu | 117 | 4 | 129 |
| dme_cdm.dwd_master_data_store_bu | 108 | 8 | 119 |
| dme_cdm.dwd_master_data_product_bu | 78 | 6 | 85 |
| dme_cdm.dwd_master_data_product_pos | 51 | 1 | 72 |
| dme_cdm.dwd_sap_ke24_sale_info_bu | 50 | 1 | 53 |
| dme_ads.tb_dashboard_mpd_sale_summary_date | 44 | 2 | 46 |
| dme_cdm.dwd_master_data_ka | 43 | 1 | 44 |
| dme_cdm.dwd_ka_pos_data_sales_daily | 42 | 3 | 47 |
| dme_cdm.dwd_master_data_store_pos | 40 | 1 | 61 |
| dme_cdm.dwd_ecom_order_detail_info_bu | 35 | 4 | 39 |
| dme_cdm.dwd_master_data_customer | 33 | 1 | 34 |
| dme_cdm.dwd_customer_mapping_bts_v3 | 30 | 2 | 32 |
| dme_ads.tb_inventory_sku_sale_allchannel_mid | 30 | 0 | 31 |
| dme_cdm.dwd_ka_pos_data_sales_monthly_bu | 27 | 3 | 31 |
| dme_cdm.dwd_master_data_product | 24 | 1 | 25 |
| dme_cdm.dwd_customer_mapping_bts_v4 | 22 | 2 | 24 |
| dme_cdm.dwd_ka_pos_data_sales_monthly | 21 | 5 | 28 |
| dme_cdm.dwd_sap_ke24_sale_info | 20 | 4 | 24 |

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

| stage | error_type | count |
| --- | --- | --- |
| sql | SQL_PARSE_ERROR | 78 |
| sql | SQL_UNSUPPORTED_STATEMENT | 48 |

完整错误见 `analysis/errors.json`，SQL 解析错误见 `analysis/sql/parse-errors.json`。

## 12. Analysis Limitations

- 只读取 `source/` Snapshot，不访问 DataWorks / MaxCompute / QuickBI 等外部 API。
- 表级血缘来自 SQL 文本解析，未做 Column Lineage。
- 层级、核心表均为 Candidate，不构成业务结论。
- 没有行级数据样本，因此不做 null / distinct / 唯一性判断。
- 调度依赖（周期任务上下游）不在本阶段范围内。
- 表名前缀未命中的表不给出 layer_candidate。
- 语句级解析失败的表引用无法提取，对应语句记录在 parse-errors.json。

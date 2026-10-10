# Phase 2 Analysis Summary

> 只读 `source/` Snapshot，产物写入 `analysis/`。
> 本报告只包含事实、Candidate 与证据，不含业务结论。

## 1. 概览

| 指标 | 数值 |
| --- | --- |
| Workspace | 3 |
| DataWorks File（Snapshot 总数） | 4657 |
| 整体分析资格 File（overall_eligible） | 1379 |
| SQL 候选 File（sql_eligible） | 541 |
| SQL 分析排除 File（sql_eligible = false） | 4116 |
| MaxCompute Table | 3724 |
| Column | 102703 |
| SQL 语句 | 1917 |
| 表引用记录 | 1241 |
| 血缘边 | 3384 |
| 可恢复错误 | 0 |

Snapshot File 全量保留；整体分析资格与 SQL 分析资格是不同口径：整体分析资格 = 身份有效且非明确非正式任务；SQL 候选 = 通过 SQL 分析资格的 File，是 SQL / Table Reference / Lineage Analysis 的唯一输入，不产生 SQL Evidence 的 File 也不记为错误。明细见 `analysis/scope/summary.md`。

## 2. Workspace Inventory

| workspace_id | workspace_name | project | files | tables |
| --- | --- | --- | --- | --- |
| 466337 | dme_cdm | dme_cdm | 741 | 1072 |
| 466338 | dme_ods | dme_ods | 2239 | 1175 |
| 466339 | dme_ads | dme_ads | 1677 | 1477 |

## 3. DataWorks File Inventory

| 维度 | 数量 |
| --- | --- |
| File 总数 | 4657 |
| TASK 类 File | 4611 |
| SQL 格式 File | 2826 |
| NodeId 有效（身份维度） | 1379 |
| NodeId 缺失（仅保留在 Snapshot） | 3278 |
| 整体分析资格（overall_eligible） | 1379 |
| SQL 候选（sql_eligible） | 541 |
| 内容可用（content present） | 2826 |

## 4. MaxCompute Table Inventory

| workspace_id | table_count | column_count |
| --- | --- | --- |
| 466337 | 1072 | 29475 |
| 466338 | 1175 | 34803 |
| 466339 | 1477 | 38425 |

## 5. SQL Analysis

| parse_status | statement_count |
| --- | --- |
| success | 1917 |
| unsupported | 0 |
| error | 0 |

- 解析语句的 File：541
- 解析错误 / 不支持语句：0
- 表引用提取方式（按语句）：ast=1916，fallback=1
- Parser Compatibility Normalization 生效语句：1
- SQL 分析排除 File（sql_eligible = false）：4116

SQL Analysis 只接受 Scope 判定为 SQL 候选（sql_eligible = true）的 File（541 个，与第 1 节「SQL 候选 File」同源）；被排除的 File 不产生任何 statement / reference / lineage 证据，排除原因（含 NodeId 缺失、类型不适用等）见 `analysis/scope/summary.md`。

Parser Compatibility Normalization 只在 syntax context 替换全角括号，string literal 与 comment 原样保留；statement.sql 仍是 raw SQL。

## 6. Table References

| 指标 | 数值 |
| --- | --- |
| 含 source 的语句 | 1232 |
| 含 target 的语句 | 1240 |
| 去重 source 表 | 1543 |
| 去重 target 表 | 1232 |

## 7. Table Lineage

| 指标 | 数值 |
| --- | --- |
| 血缘边（去重） | 3384 |
| 带多条证据的边 | 6 |
| 跨 Workspace 血缘 | 1534 |

## 8. Core Table Candidates

| table_key | downstream | upstream | evidence |
| --- | --- | --- | --- |
| dme_cdm.dwd_master_data_product_pos_bu | 115 | 1 | 116 |
| dme_cdm.dwd_master_data_store_bu | 98 | 8 | 106 |
| dme_cdm.dwd_master_data_customer_bu | 98 | 4 | 103 |
| dme_cdm.dim_day | 89 | 0 | 89 |
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
| dme_ads.tb_dashboard_mpd_sale_summary_pos_mid | 16 | 2 | 18 |
| dme_cdm.dwd_ka_pos_data_sales_daily | 15 | 3 | 18 |
| dme_ads.tb_fcst_ar_allowance_bts_v2_tmp0 | 15 | 1 | 16 |
| dme_cdm.dwd_watsons_mapping_time_df | 15 | 0 | 15 |
| dme_cdm.dwd_dms_data_sale_bu | 14 | 10 | 24 |

排序依据 downstream_count 降序，属于候选，不代表业务优先级。
完整列表见 `analysis/evidence/lineage/core-table-candidates.json`。

## 9. Data Profiling

| 指标 | 数值 |
| --- | --- |
| 表级 Profiling | 3724 |
| 字段级 Profiling | 102703 |
| 有行级样本的表 | 0 |

全部为 metadata_only，未伪造任何行级统计量。

## 10. Layer Assessment（M2.2）

| 指标 | 数值 |
| --- | --- |
| 参与评估的表 | 3724 |
| MATCH | 3663 |
| UNKNOWN | 61 |
| CONFLICT | 0 |
| 未配置 workspace 的表 | 0 |
| 跨层命名提示 | 35 |

| candidate_layer | table_count |
| --- | --- |
| (未确定) | 61 |
| ADS | 1477 |
| DIM | 49 |
| DWD | 901 |
| DWS | 61 |
| ODS | 1175 |

workspace_layer 是配置事实，candidate_layer 是子层候选；UNKNOWN 只表示证据不足，
不代表命名违规。跨层命名提示只提示表名带其他层前缀，不改变 candidate。
完整明细见 `analysis/evidence/layer/summary.md`。

## 11. 错误摘要

| stage | error_type | count |
| --- | --- | --- |
_（无数据）_

完整错误见 `analysis/evidence/errors.json`，SQL 解析错误见 `analysis/evidence/sql/parse-errors.json`。

## 12. Analysis Limitations

- 只读取 `source/` Snapshot，不访问 DataWorks / MaxCompute / QuickBI 等外部 API。
- SQL Analysis 输入只包含 Scope 判定的 SQL 候选（sql_eligible = true）的 File；被排除的 File 不产生 SQL Evidence。
- 表级血缘来自 SQL 文本解析，未做 Column Lineage。
- 层级、核心表均为 Candidate，不构成业务结论。
- M2.2 的 UNKNOWN 只表示现有证据不足以判定 CDM 子层，不等于命名违规。
- 没有行级数据样本，因此不做 null / distinct / 唯一性判断。
- 调度依赖（周期任务上下游）不在本阶段范围内。
- 语句级解析失败的表引用无法提取，对应语句记录在 parse-errors.json。

# M3 Business Understanding Summary

## 1. Overview

- 参与分析的表：3724
- 业务术语候选（terms）：6033
- Domain 候选类别：4/4 有候选表
- Object 候选类别：5/5 有候选表
- 至少命中一个 Domain / Object 候选的表：3368（90.4%）
- UNKNOWN（无任何候选）的表：356
- AMBIGUOUS（同时命中多个 Domain）的表：2449
- 存在 high 级别候选的表：1379
- 输入：`analysis`
- 规则配置：`config/business-rules.yaml`（version 1.0）

## 2. Domain Candidates

| domain | name | table_count | confidence | 证据构成 |
| --- | --- | --- | --- | --- |
| customer | 客户 | 1843 | high=175，medium=683，low=985 | table_name=298，table_comment=107，column_name=3572，column_comment=2043，sql=933 |
| inventory | 库存 | 1095 | high=140，medium=256，low=699 | table_name=350，table_comment=101，column_name=1196，column_comment=757，sql=1177 |
| product | 产品 | 2169 | high=521，medium=681，low=967 | table_name=562，table_comment=323，column_name=6335，column_comment=5664，sql=1466 |
| sales | 销售 | 2608 | high=610，medium=777，low=1221 | table_name=970，table_comment=394，column_name=6399，column_comment=3212，sql=2691 |

confidence 按独立证据来源数量计算（≥3=high，2=medium，
唯一来源为表注释=medium，其余唯一来源=low）；
只反映证据强度，不是业务结论；命中多个 Domain 时全部保留。

## 3. Business Object Candidates

| object | name | table_count | confidence | 证据构成 |
| --- | --- | --- | --- | --- |
| customer | 客户 | 1843 | high=175，medium=683，low=985 | table_name=298，table_comment=107，column_name=3572，column_comment=2043，sql=933 |
| employee | 员工 | 20 | high=1，low=19 | table_name=1，column_name=2，column_comment=23，sql=5 |
| order | 订单 | 1414 | high=135，medium=223，low=1056 | table_name=218，table_comment=136，column_name=1322，column_comment=1305，sql=922 |
| product | 产品 | 2169 | high=521，medium=681，low=967 | table_name=562，table_comment=323，column_name=6335，column_comment=5664，sql=1466 |
| store | 门店 | 1744 | high=296，medium=639，low=809 | table_name=242，table_comment=168，column_name=4476，column_comment=2477，sql=1069 |

业务对象与 Domain 用同一套证据与 confidence 规则，两者独立计算。

## 4. Business Terms

| term | normalized | count |
| --- | --- | --- |
| channel | channel | 5466 |
| product | product | 5138 |
| store | store | 4133 |
| dist | dist | 3264 |
| sales | sales | 3250 |
| amt | amt | 3187 |
| customer | customer | 3182 |
| prod | prod | 3149 |
| category | category | 2390 |
| l17 | l17 | 2312 |
| bu | bu | 2293 |
| henkel | henkel | 2118 |
| brand | brand | 2027 |
| price | price | 1874 |
| base | base | 1777 |
| pos | pos | 1755 |
| py | py | 1614 |
| sku | sku | 1601 |
| order | order | 1541 |
| ka | ka | 1460 |
| amount | amount | 1410 |
| region | region | 1287 |
| untax | untax | 1283 |
| month | month | 1269 |
| first | first | 1265 |
| barcode | barcode | 1248 |
| rate | rate | 1204 |
| qty | qty | 1171 |
| stock | stock | 1169 |
| sale | sale | 1166 |

只列出前 30 条，完整列表见 `analysis/understanding/business/terms.json`。

term 是出现次数最多的原始写法；只统计表名 / 字段名分词后剔除 stopwords 的词，
不包含注释与 SQL 中的词，也不代表已确认的业务术语。

## 5. Evidence Composition

### 表级证据类型分布

| evidence_type | entry_count |
| --- | --- |
| table_name | 2423 |
| table_comment | 1093 |
| column_name | 21980 |
| column_comment | 14176 |
| sql | 7341 |

### 候选 confidence 分布

| category | high | medium | low | unknown |
| --- | --- | --- | --- | --- |
| domain | 1446 | 2397 | 3872 | 0 |
| object | 1128 | 2226 | 3836 | 0 |

SQL / 血缘证据只补充名称与注释未覆盖的关键词，避免同一信号重复计数。

## 6. Ambiguous / Unknown

### AMBIGUOUS（多个 Domain 候选）

| table_key | warehouse_layer | domain(confidence) |
| --- | --- | --- |
| dme_ads.ads_crm_member_tag | ADS | customer(low), product(low), sales(low) |
| dme_ads.ads_media_kol_for_conversion_d | ADS | product(high), sales(medium) |
| dme_ads.ads_media_tik_tok_video_idea_d | ADS | product(high), sales(medium) |
| dme_ads.ads_media_tik_tok_video_product_d | ADS | product(high), sales(medium) |
| dme_ads.ads_sampling_jd_d | ADS | sales(medium), product(low) |
| dme_ads.ads_sellin_brandcomparison_d | ADS | customer(medium), product(medium) |
| dme_ads.ads_sellin_missing_product | ADS | product(high), sales(low) |
| dme_ads.ads_sellin_report_d | ADS | customer(medium), product(medium) |
| dme_ads.ads_tb_sku_sale_summary_prof_by_customer | ADS | customer(low), product(low), sales(low) |
| dme_ads.dim_tb_controlling_analysis_03_temp | ADS | product(low), sales(low) |
| dme_ads.dim_tb_inventore_sku_sale_dt | ADS | customer(low), product(low), sales(low) |
| dme_ads.dim_tb_inventore_sku_sale_dt_monthly | ADS | customer(low), product(low), sales(low) |
| dme_ads.dim_tb_inventore_sku_sale_dt_weekly | ADS | customer(low), product(low), sales(low) |
| dme_ads.dim_tb_inventory_sku_distributor_sale_ws | ADS | customer(low), inventory(low), product(low), sales(low) |
| dme_ads.dim_tb_inventory_sku_sale_dt_monthly | ADS | customer(low), inventory(low), product(low), sales(low) |
| dme_ads.dim_tb_inventory_sku_sale_dt_weekly | ADS | customer(low), inventory(low), product(low), sales(low) |
| dme_ads.dim_tb_inventory_sku_sale_ecom_monthly | ADS | product(medium), customer(low), inventory(low), sales(low) |
| dme_ads.dim_tb_inventory_sku_sale_nka_daily | ADS | inventory(low), product(low), sales(low) |
| dme_ads.dim_tb_inventory_sku_sale_nka_monthly | ADS | inventory(low), product(low), sales(low) |
| dme_ads.dim_tb_inventory_sku_sale_nka_weekly | ADS | inventory(low), product(low), sales(low) |

只列出前 20 条，完整明细见 `analysis/understanding/business/tables.json`。

### UNKNOWN（无候选）

| table_key | warehouse_layer | is_core_candidate |
| --- | --- | --- |
| dme_ads.ads_aipl | ADS | no |
| dme_ads.ads_customer360_deep_analysis_d | ADS | no |
| dme_ads.ads_customer360_market_performance_d | ADS | no |
| dme_ads.ads_customer360_purchase_penetration_d | ADS | no |
| dme_ads.ads_data_update_monitor_d | ADS | no |
| dme_ads.ads_dme_read_log_info | ADS | no |
| dme_ads.ads_indicator_15d_d_001 | ADS | no |
| dme_ads.ads_indicator_1d_d_001 | ADS | no |
| dme_ads.ads_indicator_1d_d_002 | ADS | no |
| dme_ads.ads_indicator_1d_d_003 | ADS | no |
| dme_ads.ads_indicator_1d_d_004 | ADS | no |
| dme_ads.ads_indicator_1d_d_005 | ADS | no |
| dme_ads.ads_indicator_1m_d_001 | ADS | no |
| dme_ads.ads_indicator_1m_d_002 | ADS | no |
| dme_ads.ads_indicator_1m_d_003 | ADS | no |
| dme_ads.ads_indicator_1m_d_004 | ADS | no |
| dme_ads.ads_indicator_1m_d_005 | ADS | no |
| dme_ads.ads_indicator_1q_d_001 | ADS | no |
| dme_ads.ads_indicator_1q_d_002 | ADS | no |
| dme_ads.ads_indicator_1td_d_001 | ADS | no |

只列出前 20 条，完整明细见 `analysis/understanding/business/tables.json`。

UNKNOWN 只表示现有词典与证据无法判断业务语义，不代表表没有业务含义；
AMBIGUOUS 不擅自收敛成一个 Domain，需人工判定。

## 7. Limitations

- 本阶段只产出 Candidate 与 Evidence，不是业务结论，也不生成业务描述；
  「这张表表达什么」的判断留给后续业务分析阶段。
- 层级只读取 M2.2 Layer Assessment（warehouse_layer / candidate_sub_layer），
  M3 不判定层级，也不修改层级结果。
- 词典来自 `config/business-rules.yaml`，词典外的业务语义无法命中，
  会表现为 UNKNOWN；扩词典需要人工评审后配置。
- 血缘证据把邻居表名的关键词传播到本表，可能引入误报，
  因此只在名称与注释都没覆盖该关键词时才记入。
- 术语分词基于标识符字面（snake_case / camelCase），没有语义消歧；
  同义词（如 order / po）不会自动合并。
- 本命令只读 M2 产物，不会刷新自身；M2 产物变化后需重新执行
  `analyze --stage understanding`，否则 `analysis/understanding/business/`  可能停留在旧输入上。

# M3.1 Business Understanding Quality Assessment

## 1. Overview

- 参与评估的表：3719
- 业务术语候选（terms）：6032
- Domain 候选类别 / Object 候选类别：4 / 5
- 至少命中一个候选的表（covered）：3367
- UNKNOWN 的表：352
- AMBIGUOUS 的表：2587
- 核心表候选：1753（UNKNOWN 48，AMBIGUOUS 1560）
- 输入：`analysis`

本报告只评估 M3 结果的证据质量，不重新识别业务语义，也不修改任何已有产物。

## 2. UNKNOWN

- UNKNOWN 的表：352
- 其中核心表候选（core_unknown）：48

### 主因分布（by_reason，级联首个命中）

| reason | table_count |
| --- | --- |
| comment_evidence_present | 213 |
| sql_evidence_present | 11 |
| naming_evidence_present | 128 |
| insufficient_evidence | 0 |
| evidence_sparse | 0 |

UNKNOWN 只表示现有词典与证据无法给出 Domain / Object 候选，不代表表没有业务含义；core_unknown_count 是与核心表候选的重叠标记，不计入 by_reason 合计。

### 数仓层 / 子层分布

| warehouse_layer | table_count |
| --- | --- |
| ADS | 175 |
| CDM | 70 |
| ODS | 107 |

| candidate_sub_layer | table_count |
| --- | --- |
| (未确定) | 14 |
| ADS | 175 |
| DIM | 12 |
| DWD | 37 |
| DWS | 7 |
| ODS | 107 |

### 高频业务词（top_terms）

| term | table_count |
| --- | --- |
| system | 63 |
| channel | 58 |
| month | 52 |
| category | 44 |
| mapping | 43 |
| table | 42 |
| mom | 41 |
| rule | 41 |
| months | 40 |
| task | 39 |
| yoy | 39 |
| dirtydata | 37 |
| dqc | 37 |
| run | 37 |
| end | 35 |
| bht | 34 |
| year | 33 |
| upload | 32 |
| brand | 29 |
| d | 29 |

统计口径是「包含该词的 UNKNOWN 表数量」，词序按（表数降序，词升序）。

### 样本

| table_key | warehouse_layer | core | reason | signals |
| --- | --- | --- | --- | --- |
| dme_cdm.active_data_month_tmp | CDM | no | naming_evidence_present | comment=n/column_comment=n/sql=n/lineage=n/terms=2 |
| dme_cdm.active_month_diff_tmp | CDM | no | naming_evidence_present | comment=n/column_comment=n/sql=n/lineage=n/terms=4 |
| dme_cdm.cd_test_20260506_column | CDM | no | naming_evidence_present | comment=n/column_comment=n/sql=n/lineage=n/terms=13 |
| dme_cdm.cd_test_20260506_table | CDM | no | naming_evidence_present | comment=n/column_comment=n/sql=n/lineage=n/terms=21 |
| dme_cdm.dim_banji_weidu_core_od001_v1 | CDM | no | comment_evidence_present | comment=y/column_comment=y/sql=n/lineage=n/terms=4 |
| dme_cdm.dim_brand_core_od001_v1 | CDM | no | comment_evidence_present | comment=y/column_comment=y/sql=n/lineage=n/terms=1 |
| dme_cdm.dim_category_core_od001_v1 | CDM | no | comment_evidence_present | comment=y/column_comment=y/sql=n/lineage=n/terms=2 |
| dme_cdm.dim_data_update_monitor_v | CDM | no | naming_evidence_present | comment=n/column_comment=n/sql=n/lineage=n/terms=25 |
| dme_cdm.dim_hk_exchange_rate_v | CDM | no | naming_evidence_present | comment=n/column_comment=n/sql=n/lineage=n/terms=4 |
| dme_cdm.dim_mgm_mapping_time | CDM | yes | comment_evidence_present | comment=y/column_comment=y/sql=y/lineage=y/terms=5 |

只列出前 10 条，完整明细见 `analysis/business/quality-assessment.json`。

## 3. AMBIGUOUS

- AMBIGUOUS 的表：2587

### 主因分布（by_reason）

| reason | table_count |
| --- | --- |
| multi_domain_likely | 800 |
| dominant_domain | 417 |
| keyword_cooccurrence | 360 |
| evidence_conflict | 734 |
| unresolved | 276 |

AMBIGUOUS = 同时存在多个 Domain 或多个 Object 候选，全部保留待人工判定；count = domain + object − domain_and_object（by_type 可重叠）；M3 summary.md 的 AMBIGUOUS 只统计多个 Domain 候选。

### 候选类型分布（by_type）

| type | table_count |
| --- | --- |
| domain | 2460 |
| object | 2203 |
| domain_and_object | 2076 |

### 高频业务词（top_terms）

| term | table_count |
| --- | --- |
| channel | 1244 |
| product | 1058 |
| bu | 1034 |
| sales | 1019 |
| customer | 1017 |
| barcode | 948 |
| store | 947 |
| brand | 905 |
| category | 875 |
| amt | 821 |
| price | 813 |
| base | 714 |
| pos | 677 |
| month | 646 |
| sku | 614 |
| region | 610 |
| months | 601 |
| first | 597 |
| dist | 560 |
| ka | 557 |

### 样本

| table_key | warehouse_layer | core | domain candidates | reason |
| --- | --- | --- | --- | --- |
| dme_cdm.dim_area_trans | CDM | yes | customer(low), inventory(low), product(low), sales(low) | unresolved |
| dme_cdm.dim_controlling_blue_table_exchange_rate | CDM | yes | customer(low), inventory(low), product(low), sales(low) | unresolved |
| dme_cdm.dim_day | CDM | yes | customer(low), inventory(low), product(low), sales(low) | keyword_cooccurrence |
| dme_cdm.dim_direct_pay_method_dictionary | CDM | yes | customer(low), product(low), sales(low) | keyword_cooccurrence |
| dme_cdm.dim_dt_small_customer_info | CDM | yes | customer(high), inventory(low), product(low), sales(low) | keyword_cooccurrence |
| dme_cdm.dim_ec_comment_ms_manual_standard_product_hierarchy | CDM | no | product(high) | multi_domain_likely |
| dme_cdm.dim_ec_douyin_product_mapping | CDM | yes | product(high), sales(high) | multi_domain_likely |
| dme_cdm.dim_ec_douyin_product_mapping_temp_01 | CDM | yes | product(high), sales(medium) | evidence_conflict |
| dme_cdm.dim_ec_douyin_product_mapping_temp_02 | CDM | yes | product(low), sales(low) | evidence_conflict |
| dme_cdm.dim_ec_tm_key_product_line_mapping | CDM | yes | product(high), sales(low) | multi_domain_likely |

只列出前 10 条，完整明细见 `analysis/business/quality-assessment.json`。

AMBIGUOUS 不擅自收敛成一个 Domain / Object，全部候选保留待人工判定。

## 4. Evidence Quality

diversity 是证据类型数（0 / 1 / 2 / 3+），不等于 confidence；source_count 是该类型下去重后的证据位置数；entry_count 保留同一关键词被多个来源命中的重复计数。

### 汇总

- 有证据的表：3367 / 3719
- 只有命名类直接证据的表：1899
- 同一关键词重复出现的表：2685

### 证据类型构成（by_source_type）

| evidence_type | entry_count | source_count | table_count |
| --- | --- | --- | --- |
| table_name | 2422 | 2005 | 2005 |
| table_comment | 1093 | 1001 | 1001 |
| column_name | 21962 | 20930 | 2874 |
| column_comment | 14176 | 13366 | 1568 |
| sql | 7403 | 903 | 1468 |
| lineage | 0 | 0 | 0 |

### 证据类型数分桶（diversity）

| diversity | table | domain candidate | object candidate |
| --- | --- | --- | --- |
| 0 | 352 | 0 | 0 |
| 1 | 638 | 3923 | 3853 |
| 2 | 1104 | 2365 | 2208 |
| 3+ | 1625 | 1448 | 1134 |

## 5. Confidence Review

confidence 是 M3 按证据类型数算出的候选证据等级（≥3=high，2=medium，表注释单独命中=medium，其余=low），不是业务确认；high 必然 diversity ≥ 3。

### 候选 confidence 分布

| category | high | medium | low | unknown |
| --- | --- | --- | --- | --- |
| domain | 1448 | 2406 | 3882 | 0 |
| object | 1134 | 2228 | 3833 | 0 |
| combined | 2582 | 4634 | 7715 | 0 |

### high 候选拆解

| metric | candidate_count |
| --- | --- |
| high_total | 2582 |
| high_diversity(3+) | 2582 |
| high_naming_only | 1358 |
| high_with_sql | 1224 |
| high_with_lineage | 0 |
| high_repeated_keyword | 2395 |
| high_single_keyword | 17 |

high_naming_only 表示 high 候选只有命名类证据（无 SQL / 血缘）；
high_single_keyword 表示 high 候选只由一个关键词支撑，是最容易被词典误命中的部分。

## 6. Core Table Review

core 口径是 analysis/business/tables.json 的 is_core_candidate；core_low_evidence_count（diversity ≤ 1）与 core_unknown_count 有重叠：UNKNOWN 的表证据必然为空。

| metric | value |
| --- | --- |
| core_count | 1753 |
| core_flag_mismatch_count | 0 |
| core_unknown_count | 48 |
| core_ambiguous_count | 1560 |
| core_high_count | 913 |
| core_low_evidence_count | 274 |

### 核心表 + UNKNOWN 样本

| table_key | warehouse_layer | reason | signals |
| --- | --- | --- | --- |
| dme_cdm.dim_mgm_mapping_time | CDM | comment_evidence_present | comment=y/column_comment=y/sql=y/lineage=y/terms=5 |
| dme_cdm.dim_mgm_mapping_time_01 | CDM | sql_evidence_present | comment=n/column_comment=n/sql=y/lineage=y/terms=6 |
| dme_cdm.dim_mgm_mapping_time_02 | CDM | sql_evidence_present | comment=n/column_comment=n/sql=y/lineage=y/terms=5 |
| dme_cdm.dim_mgm_mapping_time_03 | CDM | sql_evidence_present | comment=n/column_comment=n/sql=y/lineage=y/terms=5 |
| dme_cdm.dim_watsons_mapping_time | CDM | comment_evidence_present | comment=y/column_comment=y/sql=y/lineage=y/terms=5 |
| dme_cdm.dwd_data_source_list_fetch_date_monitor_v2 | CDM | comment_evidence_present | comment=y/column_comment=y/sql=y/lineage=y/terms=7 |
| dme_cdm.dwd_data_source_list_pre_processing_monitor_v2 | CDM | comment_evidence_present | comment=y/column_comment=y/sql=y/lineage=y/terms=41 |
| dme_cdm.dwd_data_source_list_table_timeliness_monitor_v2 | CDM | comment_evidence_present | comment=y/column_comment=y/sql=y/lineage=y/terms=8 |
| dme_cdm.dwd_data_source_list_update_monitor | CDM | comment_evidence_present | comment=y/column_comment=y/sql=y/lineage=y/terms=21 |
| dme_cdm.dwd_l17_digital_wide_tb | CDM | comment_evidence_present | comment=y/column_comment=y/sql=y/lineage=y/terms=17 |

### 核心表 + AMBIGUOUS 样本

| table_key | domain candidates | reason |
| --- | --- | --- |
| dme_cdm.dim_area_trans | customer(low), inventory(low), product(low), sales(low) | unresolved |
| dme_cdm.dim_controlling_blue_table_exchange_rate | customer(low), inventory(low), product(low), sales(low) | unresolved |
| dme_cdm.dim_day | customer(low), inventory(low), product(low), sales(low) | keyword_cooccurrence |
| dme_cdm.dim_direct_pay_method_dictionary | customer(low), product(low), sales(low) | keyword_cooccurrence |
| dme_cdm.dim_dt_small_customer_info | customer(high), inventory(low), product(low), sales(low) | keyword_cooccurrence |
| dme_cdm.dim_ec_douyin_product_mapping | product(high), sales(high) | multi_domain_likely |
| dme_cdm.dim_ec_douyin_product_mapping_temp_01 | product(high), sales(medium) | evidence_conflict |
| dme_cdm.dim_ec_douyin_product_mapping_temp_02 | product(low), sales(low) | evidence_conflict |
| dme_cdm.dim_ec_tm_key_product_line_mapping | product(high), sales(low) | multi_domain_likely |
| dme_cdm.dim_ec_tm_launch_channel_mapping | customer(low), sales(low) | unresolved |

### core 标记不一致样本

_（无数据）_

复核顺序见 `analysis/business/review-checklist.md`。

## 7. Limitations

- 本阶段只评估不识别：不修改 M3 提取规则，不选 winner，不产生业务结论，
  也不输出「某表属于销售域 / 应改成 DWD」这类判断。
- UNKNOWN 只表示词典与证据不足，不代表表没有业务含义；
  AMBIGUOUS 不收敛成一个候选，必须人工判定。
- confidence 是按证据类型数算出的规则等级，不是业务确认；
  词典误命中同样会抬高 confidence。
- UNKNOWN 主因来自注释 / SQL / 词 / 血缘信号的存在性，不解析其业务含义。
- 样本按稳定排序截断（每类最多 10 条），清单每个 Priority 最多 50 行，完整数据以 JSON 为准。
- 本命令只读 M2 / M3 产物，不自动回退执行 analyze / analyze-business；
  输入变化后需先重跑对应阶段再重新评估。

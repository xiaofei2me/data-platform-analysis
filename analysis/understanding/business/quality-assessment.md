# M3.1 Business Understanding Quality Assessment

## 1. Overview

- 参与评估的表：3724
- 业务术语候选（terms）：6033
- Domain 候选类别 / Object 候选类别：4 / 5
- 至少命中一个候选的表（covered）：3368
- UNKNOWN 的表：356
- AMBIGUOUS 的表：2576
- 核心表候选：1710（UNKNOWN 44，AMBIGUOUS 1533）
- 输入：`analysis`

本报告只评估 M3 结果的证据质量，不重新识别业务语义，也不修改任何已有产物。

## 2. UNKNOWN

- UNKNOWN 的表：356
- 其中核心表候选（core_unknown）：44

### 主因分布（by_reason，级联首个命中）

| reason | table_count |
| --- | --- |
| comment_evidence_present | 214 |
| sql_evidence_present | 11 |
| naming_evidence_present | 131 |
| insufficient_evidence | 0 |
| evidence_sparse | 0 |

UNKNOWN 只表示现有词典与证据无法给出 Domain / Object 候选，不代表表没有业务含义；core_unknown_count 是与核心表候选的重叠标记，不计入 by_reason 合计。

### 数仓层 / 子层分布

| warehouse_layer | table_count |
| --- | --- |
| ADS | 177 |
| CDM | 70 |
| ODS | 109 |

| candidate_sub_layer | table_count |
| --- | --- |
| (未确定) | 14 |
| ADS | 177 |
| DIM | 12 |
| DWD | 37 |
| DWS | 7 |
| ODS | 109 |

### 高频业务词（top_terms）

| term | table_count |
| --- | --- |
| system | 65 |
| channel | 58 |
| month | 54 |
| category | 44 |
| mapping | 43 |
| rule | 43 |
| mom | 41 |
| table | 41 |
| task | 41 |
| months | 40 |
| dirtydata | 39 |
| dqc | 39 |
| run | 39 |
| yoy | 39 |
| end | 37 |
| bht | 34 |
| year | 34 |
| upload | 32 |
| source | 30 |
| brand | 29 |

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

只列出前 10 条，完整明细见 `analysis/understanding/business/quality-assessment.json`。

## 3. AMBIGUOUS

- AMBIGUOUS 的表：2576

### 主因分布（by_reason）

| reason | table_count |
| --- | --- |
| multi_domain_likely | 800 |
| dominant_domain | 417 |
| keyword_cooccurrence | 356 |
| evidence_conflict | 725 |
| unresolved | 278 |

AMBIGUOUS = 同时存在多个 Domain 或多个 Object 候选，全部保留待人工判定；count = domain + object − domain_and_object（by_type 可重叠）；M3 summary.md 的 AMBIGUOUS 只统计多个 Domain 候选。

### 候选类型分布（by_type）

| type | table_count |
| --- | --- |
| domain | 2449 |
| object | 2196 |
| domain_and_object | 2069 |

### 高频业务词（top_terms）

| term | table_count |
| --- | --- |
| channel | 1243 |
| product | 1052 |
| bu | 1034 |
| sales | 1019 |
| customer | 1014 |
| store | 947 |
| barcode | 945 |
| brand | 902 |
| category | 871 |
| amt | 820 |
| price | 810 |
| base | 708 |
| pos | 676 |
| month | 647 |
| sku | 614 |
| region | 609 |
| months | 597 |
| first | 594 |
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

只列出前 10 条，完整明细见 `analysis/understanding/business/quality-assessment.json`。

AMBIGUOUS 不擅自收敛成一个 Domain / Object，全部候选保留待人工判定。

## 4. Evidence Quality

diversity 是证据类型数（0 / 1 / 2 / 3+），不等于 confidence；source_count 是该类型下去重后的证据位置数；entry_count 保留同一关键词被多个来源命中的重复计数。

### 汇总

- 有证据的表：3368 / 3724
- 只有命名类直接证据的表：1928
- 同一关键词重复出现的表：2687

### 证据类型构成（by_source_type）

| evidence_type | entry_count | source_count | table_count |
| --- | --- | --- | --- |
| table_name | 2423 | 2006 | 2006 |
| table_comment | 1093 | 1001 | 1001 |
| column_name | 21980 | 20948 | 2877 |
| column_comment | 14176 | 13366 | 1568 |
| sql | 7341 | 882 | 1440 |
| lineage | 0 | 0 | 0 |

### 证据类型数分桶（diversity）

| diversity | table | domain candidate | object candidate |
| --- | --- | --- | --- |
| 0 | 356 | 0 | 0 |
| 1 | 642 | 3913 | 3856 |
| 2 | 1108 | 2356 | 2206 |
| 3+ | 1618 | 1446 | 1128 |

## 5. Confidence Review

confidence 是 M3 按证据类型数算出的候选证据等级（≥3=high，2=medium，表注释单独命中=medium，其余=low），不是业务确认；high 必然 diversity ≥ 3。

### 候选 confidence 分布

| category | high | medium | low | unknown |
| --- | --- | --- | --- | --- |
| domain | 1446 | 2397 | 3872 | 0 |
| object | 1128 | 2226 | 3836 | 0 |
| combined | 2574 | 4623 | 7708 | 0 |

### high 候选拆解

| metric | candidate_count |
| --- | --- |
| high_total | 2574 |
| high_diversity(3+) | 2574 |
| high_naming_only | 1360 |
| high_with_sql | 1214 |
| high_with_lineage | 0 |
| high_repeated_keyword | 2387 |
| high_single_keyword | 17 |

high_naming_only 表示 high 候选只有命名类证据（无 SQL / 血缘）；
high_single_keyword 表示 high 候选只由一个关键词支撑，是最容易被词典误命中的部分。

## 6. Core Table Review

core 口径是 analysis/understanding/business/tables.json 的 is_core_candidate；core_low_evidence_count（diversity ≤ 1）与 core_unknown_count 有重叠：UNKNOWN 的表证据必然为空。

| metric | value |
| --- | --- |
| core_count | 1710 |
| core_flag_mismatch_count | 0 |
| core_unknown_count | 44 |
| core_ambiguous_count | 1533 |
| core_high_count | 890 |
| core_low_evidence_count | 265 |

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

| table_key | tables_flag | core_file_flag |
| --- | --- | --- |
_（无数据）_

复核顺序见 `analysis/understanding/business/review-checklist.md`。

## 7. Limitations

- 本阶段只评估不识别：不修改 M3 提取规则，不选 winner，不产生业务结论，
  也不输出「某表属于销售域 / 应改成 DWD」这类判断。
- UNKNOWN 只表示词典与证据不足，不代表表没有业务含义；
  AMBIGUOUS 不收敛成一个候选，必须人工判定。
- confidence 是按证据类型数算出的规则等级，不是业务确认；
  词典误命中同样会抬高 confidence。
- UNKNOWN 主因来自注释 / SQL / 词 / 血缘信号的存在性，不解析其业务含义。
- 样本按稳定排序截断（每类最多 10 条），清单每个 Priority 最多 50 行，完整数据以 JSON 为准。
- 本命令只读 M2 / M3 产物，不自动回退执行 analyze；
  输入变化后需先重跑对应阶段再重新评估。

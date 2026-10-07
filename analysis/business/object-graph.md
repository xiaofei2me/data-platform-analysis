# M3.2 Business Object & Relationship Analysis

## 1. Overview

- Object 数量：5（来自 `analysis/business/objects.json`，M3.2 不重新分类）
- Object ↔ Table association：7195（candidate=7195，confirmed=0，rejected=0，needs_discussion=0）
- Object relationship：10（其中至少一端关联核心表候选：10）
- 关系证据条数：co_occurrence 6344 条，sql_reference 13478 条，lineage 13363 条（sql_reference 覆盖 1107 / 1963 条 SQL 语句）
- M3.1 质量基线：table=3719，unknown=352，ambiguous=2587
- 输入：`/Users/flynnho/Work/active/002-henkel/02.technical-service-project/03-projects/data-platform-analysis/analysis`

本报告只建立「Object → Table → Relationship → Evidence」的证据结构，供 M3.3 Business Process 候选分析作为机器输入；它不是业务模型、不是维度 / 事实表定义，也不包含 Grain 判断。

## 2. Object count

| object | name | status |
| --- | --- | --- |
| customer | 客户 | candidate |
| employee | 员工 | candidate |
| order | 订单 | candidate |
| product | 产品 | candidate |
| store | 门店 | candidate |

status 默认是 candidate：未出现在 `review-checklist.md` 的回填结果里不等于已确认。name 为空表示该 Object 只来自人工回填，没有 M3 词典条目。

## 3. Object table count

| object | tables | core tables | candidate_layers | domains |
| --- | --- | --- | --- | --- |
| customer | 1848 | 1209 | (未确定), ADS, DIM, DWD, DWS, ODS | customer, inventory, product, sales |
| employee | 20 | 12 | ADS, DWD, ODS | customer, inventory, product, sales |
| order | 1416 | 1082 | (未确定), ADS, DIM, DWD, DWS, ODS | customer, inventory, product, sales |
| product | 2170 | 1245 | (未确定), ADS, DIM, DWD, DWS, ODS | customer, inventory, product, sales |
| store | 1741 | 1044 | (未确定), ADS, DIM, DWD, DWS, ODS | customer, inventory, product, sales |

一个 Object 可以关联多张表；candidate_layers / domains 是这些表上的候选取值集合，不是「该 Object 属于该层 / 该域」的结论。

## 4. Relationship count

- 关系数量：10（identity = (object_a, object_b) 排序对，同表 / SQL / 血缘证据合并进同一条记录）
- relationship_type 取值：candidate（恒定，不产出 owns / contains / belongs_to / one-to-many）

| object_a | object_b | type | diversity | strength | co_occurrence | sql_reference | lineage | core |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| customer | employee | candidate | 3 | strong | 14 | 102 | 98 | yes |
| customer | order | candidate | 3 | strong | 879 | 2210 | 2191 | yes |
| customer | product | candidate | 3 | strong | 1134 | 2325 | 2306 | yes |
| customer | store | candidate | 3 | strong | 1007 | 2133 | 2115 | yes |
| employee | order | candidate | 3 | strong | 17 | 94 | 94 | yes |
| employee | product | candidate | 3 | strong | 11 | 135 | 131 | yes |
| employee | store | candidate | 3 | strong | 17 | 116 | 116 | yes |
| order | product | candidate | 3 | strong | 1022 | 2182 | 2163 | yes |
| order | store | candidate | 3 | strong | 911 | 1957 | 1943 | yes |
| product | store | candidate | 3 | strong | 1332 | 2224 | 2206 | yes |

完整明细见 `analysis/business/object-relationships.json`。

## 5. Evidence distribution

| evidence_type | relationship_count | entry_count |
| --- | --- | --- |
| co_occurrence | 10 | 6344 |
| sql_reference | 10 | 13478 |
| lineage | 10 | 13363 |

- 证据条目只引用稳定标识（table_key / statement_id / lineage edge identity），不保存 SQL 原文，避免 JSON 膨胀。
- evidence_strength 是证据类型数的确定性映射（1=weak，2=moderate，3=strong），不是 confidence / probability / certainty。

## 6. Core object relationships

只展示至少一个 endpoint 关联核心表候选的关系；core_candidate 是 M2.4 / M3 的 lineage 上下游结构指标，不是业务价值判断。

读法：当前证据显示下表的 …candidate 之间存在 table co-occurrence / SQL reference / lineage evidence —— 这不是「存在业务关系」的结论。

| relationship | evidence | strength | diversity |
| --- | --- | --- | --- |
| customer ↔ employee | co_occurrence+sql_reference+lineage | strong | 3 |
| customer ↔ order | co_occurrence+sql_reference+lineage | strong | 3 |
| customer ↔ product | co_occurrence+sql_reference+lineage | strong | 3 |
| customer ↔ store | co_occurrence+sql_reference+lineage | strong | 3 |
| employee ↔ order | co_occurrence+sql_reference+lineage | strong | 3 |
| employee ↔ product | co_occurrence+sql_reference+lineage | strong | 3 |
| employee ↔ store | co_occurrence+sql_reference+lineage | strong | 3 |
| order ↔ product | co_occurrence+sql_reference+lineage | strong | 3 |
| order ↔ store | co_occurrence+sql_reference+lineage | strong | 3 |
| product ↔ store | co_occurrence+sql_reference+lineage | strong | 3 |

完整明细见 `analysis/business/object-relationships.json`。

## 7. Status distribution

### Object 级状态

| status | object_count |
| --- | --- |
| candidate | 5 |
| confirmed | 0 |
| rejected | 0 |
| needs_discussion | 0 |

### Association 级状态

| status | association_count |
| --- | --- |
| candidate | 7195 |
| confirmed | 0 |
| rejected | 0 |
| needs_discussion | 0 |

状态只来自 `review-checklist.md` 的人工回填：confirmed 要求 human object 显式列出该 Object；rejected / needs_discussion 在 human object 留空时作用于该表全部机器候选；清单里没出现的表一律是 candidate。

## 8. Limitations

- Object 词典缺口（candidate gap）：当前只有 5 个 Object 候选，M3.2 不扩词典、不建立第二套 Object classifier，词外语义仍落在 M3 的 UNKNOWN。
- candidate ≠ confirmed：机器识别结果默认 candidate，人工确认必须回填 `review-checklist.md` 后重跑本阶段。
- relationship ≠ 业务关系：co_occurrence / sql_reference / lineage 只是表级证据，需要人工确认后才能解释为业务关系。
- 本阶段不做 Business Process、不做 Grain 判断，也不产出正式业务模型 / 维度 / 事实表 / DWD / DWS / Semantic Layer。

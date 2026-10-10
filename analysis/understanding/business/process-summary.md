# M3.3 Business Process Candidate Analysis

## 1. Overview

- Inventory 表数量：3724
- 参与 Object 的表数量：3183（来自 `analysis/understanding/business/object-tables.json`，M3.3 不重新识别 Object）
- Process Signal 行数：12714（覆盖 3008 张表）
- Process candidate 数量：17（candidate=17）
- 过程证据强度：weak=1，moderate=0，strong=16（Level 分布：level_1=9，level_2=16，level_3=16）
- 参与的 Object 数量：5（customer, employee, order, product, store）
- Core 表候选：1455（含核心表候选的 candidate：15）
- 人工已确认的 candidate：0 / 17
- Signal 规则版本：1.0（`config/process-rules.yaml`）
- 输入：`/Users/flynnho/Work/active/002-henkel/02.technical-service-project/03-projects/data-platform-analysis/analysis`

本报告只产出 **Business Process Candidate**：它由 Process Signal、Object 参与、SQL / 血缘 / 关系证据共同支撑，既不是已确认的业务过程，也不是 Object ↔ Process 的简单映射（不会产出某个 Object 对应一个 Process 这种一对一结论）。

## 2. Process Signals

| signal_type | signal rows | tables | source |
| --- | --- | --- | --- |
| transaction_id | 214 | 144 | column |
| transaction_measure | 4268 | 1250 | column |
| event_time | 5033 | 2146 | column |
| status | 618 | 443 | column |
| multi_object | 2196 | 2196 | table |
| lifecycle | 385 | 385 | table |

- 列级信号来自 `config/process-rules.yaml` 的字段名匹配（分词后连续子序列，忽略大小写）；表级信号由 M3.2 association 与列级信号推导。
- **Signal ≠ Process**：命中信号只说明字段 / 表上具备某类过程特征；证据不足时只保留信号，不生成 candidate。

## 3. Process Candidates

| process_key | objects | tables | signal types | evidence | levels | strength |
| --- | --- | --- | --- | --- | --- | --- |
| process_candidate_001 | customer, employee, order, product, store | 8 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=43，table=10，sql=8，lineage=8，object_relationship=10 | level_1, level_2, level_3 | strong |
| process_candidate_002 | customer, employee, order, store | 4 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=49，table=6，sql=2，lineage=2，object_relationship=6 | level_1, level_2, level_3 | strong |
| process_candidate_003 | customer, employee, order | 2 | event_time, multi_object | column=4，table=2，sql=2，lineage=2，object_relationship=3 | level_2, level_3 | strong |
| process_candidate_004 | customer, order, product, store | 491 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=2103，table=561，sql=469，lineage=469，object_relationship=6 | level_1, level_2, level_3 | strong |
| process_candidate_005 | customer, order, product | 150 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=490，table=160，sql=127，lineage=126，object_relationship=3 | level_1, level_2, level_3 | strong |
| process_candidate_006 | customer, order, store | 109 | transaction_measure, event_time, status, multi_object, lifecycle | column=623，table=117，sql=75，lineage=75，object_relationship=3 | level_2, level_3 | strong |
| process_candidate_007 | customer, order | 115 | transaction_measure, event_time, status, multi_object, lifecycle | column=178，table=121，sql=112，lineage=112，object_relationship=1 | level_2, level_3 | strong |
| process_candidate_008 | customer, product, store | 290 | transaction_measure, event_time, status, multi_object, lifecycle | column=686，table=307，sql=166，lineage=166，object_relationship=3 | level_2, level_3 | strong |
| process_candidate_009 | customer, product | 189 | transaction_measure, event_time, status, multi_object, lifecycle | column=354，table=208，sql=88，lineage=88，object_relationship=1 | level_2, level_3 | strong |
| process_candidate_010 | customer, store | 106 | transaction_measure, event_time, status, multi_object, lifecycle | column=175，table=109，sql=33，lineage=33，object_relationship=1 | level_2, level_3 | strong |
| process_candidate_011 | employee, order, product, store | 3 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=20，table=4，sql=0，lineage=0，object_relationship=6 | level_1, level_2, level_3 | strong |
| process_candidate_012 | employee, store | 2 | event_time, status, multi_object, lifecycle | column=15，table=3，sql=0，lineage=0，object_relationship=1 | level_2, level_3 | strong |
| process_candidate_013 | order, product, store | 240 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=1494，table=315，sql=152，lineage=152，object_relationship=3 | level_1, level_2, level_3 | strong |
| process_candidate_014 | order, product | 128 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=495，table=147，sql=49，lineage=49，object_relationship=1 | level_1, level_2, level_3 | strong |
| process_candidate_015 | order, store | 57 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=209，table=69，sql=19，lineage=19，object_relationship=1 | level_1, level_2, level_3 | strong |
| process_candidate_016 | order | 107 | transaction_id, transaction_measure, event_time, status, lifecycle | column=155，table=4，sql=61，lineage=59，object_relationship=0 | level_1 | weak |
| process_candidate_017 | product, store | 302 | transaction_measure, event_time, status, multi_object, lifecycle | column=650，table=317，sql=95，lineage=95，object_relationship=1 | level_2, level_3 | strong |

完整明细见 `analysis/understanding/business/processes.json`。

读法：每个 candidate 是「一组精确 Object 集合 + 这组表上的信号 + 证据」；process_key 是机器编号，本阶段不产出 process name。

## 4. Core Process Candidates

只展示包含至少一张核心表候选的 candidate；core_candidate 是 M2.4 / M3 的 lineage 上下游结构指标，不是业务价值判断。

| process_key | objects | tables | signal types | evidence | levels | strength |
| --- | --- | --- | --- | --- | --- | --- |
| process_candidate_001 | customer, employee, order, product, store | 8 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=43，table=10，sql=8，lineage=8，object_relationship=10 | level_1, level_2, level_3 | strong |
| process_candidate_002 | customer, employee, order, store | 4 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=49，table=6，sql=2，lineage=2，object_relationship=6 | level_1, level_2, level_3 | strong |
| process_candidate_003 | customer, employee, order | 2 | event_time, multi_object | column=4，table=2，sql=2，lineage=2，object_relationship=3 | level_2, level_3 | strong |
| process_candidate_004 | customer, order, product, store | 491 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=2103，table=561，sql=469，lineage=469，object_relationship=6 | level_1, level_2, level_3 | strong |
| process_candidate_005 | customer, order, product | 150 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=490，table=160，sql=127，lineage=126，object_relationship=3 | level_1, level_2, level_3 | strong |
| process_candidate_006 | customer, order, store | 109 | transaction_measure, event_time, status, multi_object, lifecycle | column=623，table=117，sql=75，lineage=75，object_relationship=3 | level_2, level_3 | strong |
| process_candidate_007 | customer, order | 115 | transaction_measure, event_time, status, multi_object, lifecycle | column=178，table=121，sql=112，lineage=112，object_relationship=1 | level_2, level_3 | strong |
| process_candidate_008 | customer, product, store | 290 | transaction_measure, event_time, status, multi_object, lifecycle | column=686，table=307，sql=166，lineage=166，object_relationship=3 | level_2, level_3 | strong |
| process_candidate_009 | customer, product | 189 | transaction_measure, event_time, status, multi_object, lifecycle | column=354，table=208，sql=88，lineage=88，object_relationship=1 | level_2, level_3 | strong |
| process_candidate_010 | customer, store | 106 | transaction_measure, event_time, status, multi_object, lifecycle | column=175，table=109，sql=33，lineage=33，object_relationship=1 | level_2, level_3 | strong |
| process_candidate_013 | order, product, store | 240 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=1494，table=315，sql=152，lineage=152，object_relationship=3 | level_1, level_2, level_3 | strong |
| process_candidate_014 | order, product | 128 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=495，table=147，sql=49，lineage=49，object_relationship=1 | level_1, level_2, level_3 | strong |
| process_candidate_015 | order, store | 57 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=209，table=69，sql=19，lineage=19，object_relationship=1 | level_1, level_2, level_3 | strong |
| process_candidate_016 | order | 107 | transaction_id, transaction_measure, event_time, status, lifecycle | column=155，table=4，sql=61，lineage=59，object_relationship=0 | level_1 | weak |
| process_candidate_017 | product, store | 302 | transaction_measure, event_time, status, multi_object, lifecycle | column=650，table=317，sql=95，lineage=95，object_relationship=1 | level_2, level_3 | strong |

完整明细见 `analysis/understanding/business/processes.json`。

## 5. Evidence Sources

| evidence source | total |
| --- | --- |
| column（列级信号行） | 7743 |
| table（表级信号行） | 2460 |
| sql（被 SQL 引用的表） | 1458 |
| lineage（参与血缘的表） | 1455 |
| object_relationship（M3.2 关系对） | 50 |

SQL / 血缘证据按表归属到 candidate；关系证据来自 `analysis/understanding/business/object-relationships.json` 的排序 Object 对。

## 6. Unresolved Questions

每个 candidate 都固定带有以下未决问题（未决 ≠ 失败，必须人工回答）：

- process name not confirmed
- process semantics not confirmed
- grain not determined
- business validation required

按证据缺失条件追加：

- `sql reference evidence missing`：2 / 17 个 candidate
- `lineage evidence missing`：2 / 17 个 candidate
- `object relationship evidence missing`：1 / 17 个 candidate

Grain 状态：grain not determined —— 本阶段只记录 grain signals，不给出 grain 结论。

## 7. Limitations

- candidate ≠ confirmed：process candidate 默认 candidate，机器阶段不产出 confirmed process；确认必须回填 `process-review-checklist.md` 后重跑本阶段。
- signal ≠ process：字段命中 transaction / measure / time / status 只是信号，多个信号叠加也仍需人工确认其是否构成一个业务过程。
- core ≠ 业务重要性：core_table_count 只是 M2.4 / M3 的 lineage 结构指标。
- object relationship ≠ 业务关系：M3.3 只把关系当作 candidate 之间的证据来源。
- 未命名、未判 Grain、未做 Object ↔ Process 一对一映射：本阶段不产出 process name、DWD / DWS / 事实表 / 维度表结论。

## 8. M3.4 Input Readiness

可直接作为 M3.4 Grain Candidate Analysis 的机器输入：

- `process-signals.json`：12714 条信号行，其中 transaction 标识 214 行、度量 4268 行、时间 5033 行、状态 618 行。
- `processes.json` 的 evidence / levels / grain_signals：17 个 candidate 已带证据来源与强度。

必须人工确认后才能进入下一阶段：

- process 命名：`process-review-checklist.md` 的 human_process_name（当前已确认 0 / 17）。
- process 语义与边界：见第 6 节 unresolved_questions。
- 表级口径：`analysis/understanding/business/review-checklist.md` 中仍为 candidate / 未回填的表，不能当作已确认的过程范围。

当前数据是否足以支撑 Grain Candidate Analysis：9 个 candidate 具备 transaction 标识信号、17 个具备时间分组信号；两者齐备的 candidate 可以从信号展开 grain 候选，其余 candidate 证据不足，必须先补证据或由人工确认。无论哪一类，本阶段的结论都停留在 grain signals，grain not determined。

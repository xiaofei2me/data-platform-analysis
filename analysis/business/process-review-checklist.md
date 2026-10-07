# M3.3 Process Review Checklist

人工填写 human process name，并把 confirmed 从 false 改为 true 以确认该 process candidate；未回填的行一律保持 false，candidate 不会自动变成 confirmed process。

前六列（process_key / objects / tables / signals / evidence）与 note 之外的机器列由 `analyze-business-processes` 生成，重跑会被覆盖；human_process_name / confirmed / note 三列会被保留。

| process_key | objects | tables | signals | evidence | human_process_name | confirmed | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| process_candidate_001 | customer, employee, order, product, store | 8 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=43，table=10，sql=8，lineage=8，object_relationship=10 |  | false |  |
| process_candidate_002 | customer, employee, order, store | 4 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=49，table=6，sql=2，lineage=2，object_relationship=6 |  | false |  |
| process_candidate_003 | customer, employee, order | 2 | event_time, multi_object | column=4，table=2，sql=2，lineage=2，object_relationship=3 |  | false |  |
| process_candidate_004 | customer, order, product, store | 490 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=2098，table=560，sql=468，lineage=468，object_relationship=6 |  | false |  |
| process_candidate_005 | customer, order, product | 151 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=491，table=161，sql=130，lineage=129，object_relationship=3 |  | false |  |
| process_candidate_006 | customer, order, store | 109 | transaction_measure, event_time, status, multi_object, lifecycle | column=623，table=117，sql=75，lineage=75，object_relationship=3 |  | false |  |
| process_candidate_007 | customer, order | 115 | transaction_measure, event_time, status, multi_object, lifecycle | column=178，table=121，sql=112，lineage=112，object_relationship=1 |  | false |  |
| process_candidate_008 | customer, product, store | 290 | transaction_measure, event_time, status, multi_object, lifecycle | column=686，table=307，sql=167，lineage=167，object_relationship=3 |  | false |  |
| process_candidate_009 | customer, product | 195 | transaction_measure, event_time, status, multi_object, lifecycle | column=361，table=214，sql=96，lineage=96，object_relationship=1 |  | false |  |
| process_candidate_010 | customer, store | 106 | transaction_measure, event_time, status, multi_object, lifecycle | column=175，table=109，sql=33，lineage=33，object_relationship=1 |  | false |  |
| process_candidate_011 | employee, order, product, store | 3 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=20，table=4，sql=0，lineage=0，object_relationship=6 |  | false |  |
| process_candidate_012 | employee, store | 2 | event_time, status, multi_object, lifecycle | column=15，table=3，sql=0，lineage=0，object_relationship=1 |  | false |  |
| process_candidate_013 | order, product, store | 240 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=1494，table=315，sql=152，lineage=152，object_relationship=3 |  | false |  |
| process_candidate_014 | order, product | 130 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=527，table=152，sql=55，lineage=55，object_relationship=1 |  | false |  |
| process_candidate_015 | order, store | 57 | transaction_id, transaction_measure, event_time, status, multi_object, lifecycle | column=212，table=69，sql=20，lineage=20，object_relationship=1 |  | false |  |
| process_candidate_016 | order | 107 | transaction_id, transaction_measure, event_time, status, lifecycle | column=155，table=4，sql=61，lineage=59，object_relationship=0 |  | false |  |
| process_candidate_017 | product, store | 301 | transaction_measure, event_time, status, multi_object, lifecycle | column=644，table=316，sql=96，lineage=96，object_relationship=1 |  | false |  |

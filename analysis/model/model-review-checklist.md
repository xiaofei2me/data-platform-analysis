# M3.5 Model Review Checklist

人工回填 human_status（pending / confirmed / rejected / needs_review / needs_discussion）、human_name 与 note；未回填的行一律保持 candidate，candidate 不会自动变成 confirmed。

candidate_key 起到 unresolved_reasons 为止的机器列由 `analyze-business-model` 生成，重跑会被覆盖；human_status / human_name / note 三列会被保留。

## P1 Fact Candidate 证据不足

证据强度为 weak，或缺 process / grain / 度量 / Object 证据；先补证据再确认，不要直接改 status。

只列出前 50 行，共 563 行；其余行见 `analysis/model/fact-candidates.json`、`dimension-candidates.json` 与 `fact-dimension-relationships.json`。

| candidate_key | candidate_type | priority | current_status | evidence_strength | unresolved_reasons | human_status | human_name | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fact_candidate_1251 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1252 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1256 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1258 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1280 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1281 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1873 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1878 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1879 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1884 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1885 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_1886 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2077 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2078 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2126 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2127 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2128 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2129 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2285 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2419 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2420 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2421 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2455 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2615 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2616 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2642 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2662 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2677 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2678 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2722 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2724 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2738 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2739 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2773 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2774 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2814 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2817 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2818 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2831 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2832 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2856 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2857 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2868 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2870 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2871 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2894 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2895 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2902 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2903 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2913 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |

## P2 Fact Candidate 粒度 / 血缘待裁决

grain 形态未定（unknown / multiple_possible_keys）或缺 SQL / 血缘证据；需要人工给出粒度裁决或补充上游证据。

只列出前 50 行，共 2672 行；其余行见 `analysis/model/fact-candidates.json`、`dimension-candidates.json` 与 `fact-dimension-relationships.json`。

| candidate_key | candidate_type | priority | current_status | evidence_strength | unresolved_reasons | human_status | human_name | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fact_candidate_008 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_009 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_010 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_011 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1000 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1001 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1002 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1003 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1004 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1005 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1006 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1007 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1008 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1009 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1010 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1011 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1012 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1013 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1014 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1015 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1016 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1017 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1018 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1019 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1020 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1021 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1022 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1023 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1024 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1025 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1026 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1027 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1028 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1029 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1030 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1031 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1032 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1033 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1034 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1035 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1036 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1037 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1038 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1039 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1040 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1041 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1042 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1043 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1044 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |
| fact_candidate_1045 | fact | P2 | candidate | strong | ambiguous_grain, missing_sql_evidence, missing_lineage_evidence | pending |  |  |

## P3 Dimension Candidate 证据 / 角色待裁决

证据强度为 weak，或属性 / 过程 / 事实引用 / 角色存在歧义；Object 同时进入 fact 关系时必须人工裁决角色。

| candidate_key | candidate_type | priority | current_status | evidence_strength | unresolved_reasons | human_status | human_name | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dimension_candidate_001 | dimension | P3 | candidate | strong | fact_and_dimension_ambiguous | pending |  |  |
| dimension_candidate_002 | dimension | P3 | candidate | strong | missing_fact_reference | pending |  |  |
| dimension_candidate_003 | dimension | P3 | candidate | strong | fact_and_dimension_ambiguous | pending |  |  |
| dimension_candidate_004 | dimension | P3 | candidate | strong | fact_and_dimension_ambiguous | pending |  |  |
| dimension_candidate_005 | dimension | P3 | candidate | strong | fact_and_dimension_ambiguous | pending |  |  |

## P4 Fact-Dimension Relationship 证据不足

关系只有单一证据源或缺 Object 直接链接；relationship ≠ 业务关系，确认前必须核对 source_id。

只列出前 50 行，共 3821 行；其余行见 `analysis/model/fact-candidates.json`、`dimension-candidates.json` 与 `fact-dimension-relationships.json`。

| candidate_key | candidate_type | priority | current_status | evidence_strength | unresolved_reasons | human_status | human_name | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fact_dimension_relationship_039 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_044 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_049 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_054 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_077 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_082 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_092 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_097 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_1000 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10001 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10004 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10007 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10008 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10011 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10016 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10017 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_1002 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10020 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10026 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10027 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10030 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10031 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10032 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10035 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10036 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10037 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10040 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10041 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10042 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10045 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10046 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10047 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_1005 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10050 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10051 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10052 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10055 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10056 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10057 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10060 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10061 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10062 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10065 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10066 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10067 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_1007 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10070 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10071 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10074 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10080 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |

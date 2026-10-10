# M3.5 Model Review Checklist

人工回填 human_status（pending / confirmed / rejected / needs_review / needs_discussion）、human_name 与 note；未回填的行一律保持 candidate，candidate 不会自动变成 confirmed。

candidate_key 起到 unresolved_reasons 为止的机器列由 `analyze --stage understanding` 生成，重跑会被覆盖；human_status / human_name / note 三列会被保留。

| candidate_key | candidate_type | priority | current_status | evidence_strength | unresolved_reasons | human_status | human_name | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
## P1 Fact Candidate 证据不足

证据强度为 weak，或缺 process / grain / 度量 / Object 证据；先补证据再确认，不要直接改 status。

只列出前 50 行，共 562 行；其余行见 `analysis/understanding/modeling/fact-candidates.json`、`dimension-candidates.json` 与 `fact-dimension-relationships.json`。

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
| fact_candidate_2080 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2081 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2083 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2128 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2129 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2130 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2131 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2287 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2421 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2422 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2423 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2457 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2617 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2618 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2644 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2664 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2679 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2680 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2724 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2726 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2740 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2741 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2774 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2775 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2814 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2817 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2818 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2831 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2832 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2855 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2856 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2867 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2869 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2870 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2893 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2894 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2900 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |
| fact_candidate_2901 | fact | P1 | candidate | strong | insufficient_grain_evidence, ambiguous_grain, missing_sql_evidence, missing_lineage_evidence, missing_object_evidence | pending |  |  |

## P2 Fact Candidate 粒度 / 血缘待裁决

grain 形态未定（unknown / multiple_possible_keys）或缺 SQL / 血缘证据；需要人工给出粒度裁决或补充上游证据。

只列出前 50 行，共 2676 行；其余行见 `analysis/understanding/modeling/fact-candidates.json`、`dimension-candidates.json` 与 `fact-dimension-relationships.json`。

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

只列出前 50 行，共 3813 行；其余行见 `analysis/understanding/modeling/fact-candidates.json`、`dimension-candidates.json` 与 `fact-dimension-relationships.json`。

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
| fact_dimension_relationship_10002 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10005 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10006 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10009 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10014 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10015 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10018 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_1002 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10024 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10025 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10028 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10029 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10030 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10033 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10034 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10035 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10038 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10039 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10040 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10043 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10044 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10045 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10048 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10049 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_1005 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10050 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10053 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10054 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10055 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10058 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10059 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10060 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10063 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10064 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10065 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10068 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10069 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_1007 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, sql_evidence_missing, lineage_evidence_missing | pending |  |  |
| fact_dimension_relationship_10072 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10078 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |
| fact_dimension_relationship_10081 | fact_dimension_relationship | P4 | candidate | weak | insufficient_evidence, missing_object_link, sql_evidence_missing | pending |  |  |

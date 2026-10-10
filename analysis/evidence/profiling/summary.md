# M2.5 Data Profiling

- 表级 Profiling：3724
- 字段级 Profiling：102703
- 分区表：2169
- 有注释字段：53215

profile_status = metadata_only：当前 Snapshot 没有行级数据样本，
row_count / distinct_count / min / max / sample_values 全部为 null，
is_candidate_key 恒为 false。

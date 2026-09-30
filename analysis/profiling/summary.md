# M2.4 Data Profiling

- 表级 Profiling：3719
- 字段级 Profiling：102603
- 分区表：2164
- 有注释字段：53208

profile_status = metadata_only：当前 Snapshot 没有行级数据样本，
row_count / distinct_count / min / max / sample_values 全部为 null，
is_candidate_key 恒为 false。

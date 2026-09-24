# 采集 / 分析边界

采集阶段只产出各 Workspace 独立、互不合并的 Snapshot：不做跨 Workspace lineage 合并，不预先将 DWS 分析字段（owner、调度、cron、status 等）提升到 index，不提前采集依赖 API 与表级血缘 API；raw API 响应是唯一真相源。跨 Workspace 表级血缘的识别与聚合、index 字段扩充、依赖与表级血缘采集均属后续分析阶段职责——明确禁止把分析逻辑逐步回流到采集层，以保持 Snapshot 的职责边界。

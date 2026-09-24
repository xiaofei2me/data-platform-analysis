# 快照布局与 Workspace 身份契约

Snapshot 以稳定的 ProjectId 作为 Workspace 目录标识（`workspaces/<project_id>/`，而非可变的 `name`），根级 `workspaces-index.json` 承载 Workspace 元数据（name、MaxCompute 项目映射、运行状态），所有节点与血缘记录通过 `workspace_id` 建立明确关联。放弃「按 name 命名」是因为 name 可变会导致目录漂移，放弃「平铺 + 前缀」是因为无法天然隔离 node_id 碰撞与单 Workspace 重跑；一旦后续分析代码依赖该目录布局，再修改将涉及 Snapshot 迁移，因此在此固化。

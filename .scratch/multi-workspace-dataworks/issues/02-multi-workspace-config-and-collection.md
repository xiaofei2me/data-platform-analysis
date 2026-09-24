# 02: 多 Workspace 配置与顺序采集骨架

**What to build:** 作为数据平台分析人员，我配置多个 DataWorks Workspace 后，一次全量采集即可获得全部 Workspace 的完整 Snapshot：配置以 JSON 数组声明（id、name、maxcompute_project 1:1），启动时 fail-fast；采集顺序遍历每个 Workspace，落盘到以稳定 workspace_id 命名的独立目录（ADR-0001），每条节点索引与血缘记录携带 workspace_id；根级 workspaces-index.json 创建并写入全部 Workspace 元数据与状态；manifest 列出全部 Workspace；`config` 子命令打印新配置视图；进度条显示当前 Workspace name。单 Workspace 即长度为 1 的数组，无模式分支。删除废弃配置项 DATAWORKS_PROJECT_ID 与 DATAWORKS_PROJECT_IDENTIFIER。

**Blocked by:** 01: 建立 CLI 黑盒测试接缝（prefactor）

**Status:** ready-for-agent

- [x] `DATAWORKS_WORKSPACES` JSON 数组解析成功；非法 JSON、缺字段、重复 id、重复 name → 启动即报错、非零退出
- [x] 旧配置项 DATAWORKS_PROJECT_ID、DATAWORKS_PROJECT_IDENTIFIER 从配置模型与 .env.example 中移除
- [x] ListNodes / GetNode 按方法参数传入 project_id；分页与重试行为不变
- [x] 顺序遍历全部 Workspace，每个 Workspace 的 nodes / sql / lineage 落盘在 `workspaces/<project_id>/` 独立目录下
- [x] nodes-index 条目与 lineage 记录均含 workspace_id；name、maxcompute_project 仅在 index 顶层
- [x] workspaces-index.json 创建并含每个 Workspace 的 id、name、maxcompute_project、状态、计数、generated_at
- [x] 全量 export 的 manifest 列出全部 Workspace；MaxCompute 采集与布局零改动
- [x] `config` 子命令展示多 Workspace 配置；进度条文案携带当前 Workspace name
- [x] CLI 黑盒测试：双 Workspace stub → 完整目录树 + 关键 JSON 内容 + exit 0；非法配置 → fail-fast
- [x] 单 Workspace（长度 1）行为与多 Workspace 走同一代码路径

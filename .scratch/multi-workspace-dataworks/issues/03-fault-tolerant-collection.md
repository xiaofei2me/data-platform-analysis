# 03: 容错采集与失败可观测

**What to build:** 作为数据平台分析人员，某个 Workspace 或节点的采集失败不再中断整体流程：失败 Workspace 在 workspaces-index.json 中标记 status=failed 并附错误信息，其余 Workspace 与 MaxCompute 照常采集，manifest 依然生成（修复「失败即无 manifest、后半段全丢」的旧行为），获取详情失败的节点记入 nodes-index 的 failed_nodes；只要存在任何 Workspace/节点级失败，进程以退出码 1 告知快照不完整。

**Blocked by:** 02: 多 Workspace 配置与顺序采集骨架

**Status:** ready-for-agent

- [x] Workspace 级异常被错误边界捕获：记 status=failed + 错误信息，继续采集下一个 Workspace
- [x] 节点级 GetNode 失败：记入 failed_nodes，不中断当前 Workspace
- [x] DataWorks 部分失败时 MaxCompute 采集与 manifest 生成照常执行
- [x] manifest 在 DataWorks 部分失败的全量 export 中仍然生成且内容符合多 Workspace 结构
- [x] 存在任何失败 → exit 1；全部成功 → exit 0；KeyboardInterrupt → 130
- [x] CLI 黑盒测试必须覆盖：单 Workspace stub 抛错 → 其余照采 + status=failed + **manifest 仍生成** + exit 1
- [x] CLI 黑盒测试覆盖：部分节点 GetNode 失败 → failed_nodes 记录 + exit 1

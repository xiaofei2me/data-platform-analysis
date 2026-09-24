# 04: 重复执行语义（权威清理 + 注册表 upsert）

**What to build:** 作为数据平台分析人员，我重复采集时快照始终反映权威真实状态：以本次 ListNodes 返回的节点集合为权威，Workspace 采集完整跑完后清理该目录中已不存在的节点旧文件（幽灵节点不再污染后续分析）；采集失败的 Workspace 不清理、failed_nodes 对应旧文件保留，上一次成功数据仍可用；workspaces-index.json 作为「注册表 + 各 Workspace 最近状态」执行读-改-写 upsert，条目含 generated_at；从配置移除的 Workspace 其目录与条目不自动删除，清理由人工执行。

**Blocked by:** 03: 容错采集与失败可观测

**Status:** ready-for-agent

- [x] Workspace 采集完整跑完后，nodes/ 与 sql/ 中不属于本次权威节点集合的文件被删除
- [x] status=failed 的 Workspace 不执行任何清理
- [x] failed_nodes 对应的旧文件保留
- [x] workspaces-index.json 读取已有内容后 upsert：本次条目更新，已有且未涉及的条目原样保留
- [x] 每个条目含 generated_at 用于判断新鲜度
- [x] 文件不存在时创建并只写入本次 Workspace
- [x] 从配置移除的 Workspace 不被自动删除（目录与 index 条目留存）
- [x] CLI 黑盒测试：fixture 删除节点后重采 → 幽灵文件清除、其余文件不变
- [x] CLI 黑盒测试：失败 Workspace 重采失败 → 目录与旧文件原样

# 05: `--workspace` 单 Workspace 精准采集

**What to build:** 作为数据平台分析人员，某个 Workspace 采集失败后，我用 `dataworks --workspace <id>` 或 `export --workspace <id>` 只重跑它，不必 3 个全部重扫：id 必须存在于 DATAWORKS_WORKSPACES 配置中，否则直接报错退出（不允许绕过配置的临时 Workspace）；过滤是纯运行时行为，不写入配置、不引入单/多模式；部分采集仅 upsert 选中 Workspace 的注册表条目，其他 Workspace 的状态、目录与历史文件完全不受影响；manifest 仍仅由全量 export 写入。

**Blocked by:** 04: 重复执行语义（权威清理 + 注册表 upsert）

**Status:** ready-for-agent

- [x] `dataworks` 与 `export` 子命令接受可选 `--workspace <id>`
- [x] id 未在配置中 → 报错、非零退出，不发起任何采集
- [x] 缺省时采集全部 Workspace（行为与 02-04 一致）
- [x] 过滤仅为采集前列表过滤，无新增采集流程或模式分支
- [x] 部分采集时 workspaces-index.json 仅 upsert 选中条目，未涉及条目字节级不变
- [x] `dataworks` 子命令不写 manifest；全量 export 语义不受影响
- [x] CLI 黑盒测试：3 配置中只采 123 → 仅 123 目录更新、456/789 条目不变
- [x] CLI 黑盒测试：未配置 id → 报错退出

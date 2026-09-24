# 01: 建立 CLI 黑盒测试接缝（prefactor）

**What to build:** 让后续多 Workspace 改造可以在一个稳定、可注入的测试接缝上开发：配置实例惰性初始化（生产行为完全不变），并用首批 CLI 黑盒冒烟测试锁定当前单 Workspace 行为基径——从子命令调用到 Snapshot 落盘与退出码的全链路。测试 fixture 惯例（仅在 DataWorks/MaxCompute 的 SDK 调用边界 stub、临时 source_dir、最小 env）在此确立，后续所有 ticket 复用。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] 配置实例改为惰性初始化，生产运行行为与改前一致（正常读取 `.env`、缺必填项仍启动失败）
- [x] `tests/` 目录建立，pytest 可运行
- [x] 冒烟测试以 CLI 黑盒方式跑通现有单 Workspace 采集：断言退出码 0、Snapshot 目录与文件按现状生成
- [x] stub 只打在 SDK 调用边界；未 mock 任何内部函数、私有方法或 export 流程
- [x] 不修改任何生产采集逻辑（本 ticket 仅惰性初始化 + 测试）

## Comments

- 2026-09-24: 冒烟测试暴露存量 bug：`GetNodeRequest` 的参数为 `id` 而非 `node_id`，现实现对真实 SDK 不可用，已随本 ticket 修复（否则无法建立绿色基线）。另将重试停止条件改为调用时读取配置（配合惰性加载）。

Status: ready-for-agent

# Spec: DataWorks 多 Workspace 数据采集

## Problem Statement

当前数据采集工具只支持一个 DataWorks Workspace（通过单值 `DATAWORKS_PROJECT_ID` 配置）。实际环境中存在 3 个 DataWorks Workspace，分析人员无法通过本工具获得完整的节点、SQL 与任务快照——只能覆盖其中一个 Workspace 的资产，导致后续的数仓现状分析、DWS 设计缺少另外两个 Workspace 的数据基础。

同时，现有实现在失败场景下存在可靠性缺口：单 Workspace 路径上一旦 API 重试耗尽，异常会中断整个采集流程，后续数据源不采集、`manifest.json` 不生成，且采集失败的节点会从索引中无声消失——产出的快照「看起来完整、实际缺数」，对后续分析是隐性污染。

## Solution

将采集演进为多 Workspace 模型：在一个 `.env` 配置中以结构化 JSON 数组声明全部 Workspace（id、name、MaxCompute 项目映射），采集时顺序遍历、逐个独立落盘到按稳定 `workspace_id` 组织的 Snapshot 目录中；每个 Workspace 的元数据与最近一次采集状态汇总在根级注册表 `workspaces-index.json` 中。

对使用者而言：

- 一次 `export` 即可获得全部 3 个 Workspace + MaxCompute 的完整 Snapshot；
- 任一 Workspace 或节点的失败不会阻断其余采集，失败被显式记录（`status` / `failed_nodes`），`manifest.json` 始终生成，进程以非零退出码告知「本次快照不完整」；
- 可用 `--workspace <id>` 只重跑单个 Workspace，注册表以 upsert 方式更新，不影响其他 Workspace 的状态与文件；
- 重复采集以 API 返回的节点集合为权威清理已删除节点的幽灵文件，失败对象保留上一次成功数据。

## User Stories

1. As a 数据平台分析人员, I want 在 `.env` 中用一个 JSON 数组配置全部 DataWorks Workspace, so that 我不再被单值 `DATAWORKS_PROJECT_ID` 限制在一个 Workspace。
2. As a 数据平台分析人员, I want 每个 Workspace 配置包含稳定的 `id`、可读的 `name` 和 1:1 绑定的 `maxcompute_project`, so that 快照中的每个 Workspace 都有明确身份与环境映射。
3. As a 数据平台分析人员, I want 配置在启动时 fail-fast（非法 JSON、缺字段、重复 id/name 立即报错退出）, so that 我不会带着错误配置跑完一次漫长采集才发现问题。
4. As a 数据平台分析人员, I want 一次 `export` 顺序采集全部已配置的 Workspace, so that 我能得到覆盖所有 Workspace 的完整时点快照。
5. As a 数据平台分析人员, I want 每个 Workspace 的节点、SQL、血缘文件落在以 `workspace_id` 命名的独立目录中, so that 不同 Workspace 的同名/同号节点不会互相覆盖，单个 Workspace 可独立重跑。
6. As a 数据平台分析人员, I want 根级 `workspaces-index.json` 记录每个 Workspace 的元数据（name、maxcompute_project）与最近采集状态, so that 我无需遍历目录就能总览全部 Workspace 的采集结果。
7. As a 数据平台分析人员, I want `nodes-index.json` 与 `task-lineage.jsonl` 的每条记录显式携带 `workspace_id`, so that 记录被扁平化合并后归属关系不会丢失。
8. As a 数据平台分析人员, I want `workspace_name` 只出现在 index 顶层而不复制进每条记录, so that name 修改后不存在多份陈旧副本。
9. As a 数据平台分析人员, I want 某个 Workspace 采集失败时其余 Workspace 继续采集, so that 一次 API 抖动不会让我拿不到另外两个 Workspace 的数据。
10. As a 数据平台分析人员, I want 失败的 Workspace 在 `workspaces-index.json` 中标记 `status: failed` 并附错误信息, so that 我能确切知道快照缺了哪一块。
11. As a 数据平台分析人员, I want 获取详情失败的节点记入 `nodes-index.json` 的 `failed_nodes`, so that 快照不会把缺数伪装成完整。
12. As a 数据平台分析人员, I want 只要存在 Workspace 或节点级失败，进程最终以非零码退出, so that 我的调度脚本能感知到本次快照不完整。
13. As a 数据平台分析人员, I want DataWorks 采集部分失败时 `manifest.json` 依然生成且 `maxcompute` 照常采集, so that 修复后不再出现「失败即无 manifest、后半段全丢」的旧行为。
14. As a 数据平台分析人员, I want 重复采集时以本次 `list_nodes` 返回集合为权威清理已删除节点的旧文件, so that 上游删掉的幽灵节点不会永远污染后续分析。
15. As a 数据平台分析人员, I want 采集失败的 Workspace 不执行清理、失败节点的旧文件保留, so that 我至少还有上一次成功采集的数据可用。
16. As a 数据平台分析人员, I want `dataworks --workspace <id>` 只重跑指定 Workspace, so that 单个失败的 Workspace 不必连累另外两个全量重扫。
17. As a 数据平台分析人员, I want `--workspace` 指定未配置的 id 时直接报错, so that 不会出现绕过配置的「临时 Workspace」快照。
18. As a 数据平台分析人员, I want `--workspace` 部分采集时 `workspaces-index.json` 只 upsert 本次条目, so that 其他 Workspace 的状态与历史快照不受影响。
19. As a 数据平台分析人员, I want `manifest.json` 仅由全量 `export` 写入并列出全部 Workspace, so that manifest 始终代表整个快照的全貌而非某次局部运行。
20. As a 数据平台分析人员, I want MaxCompute 采集与目录布局完全保持现状, so that 本次改动的风险面收敛在 DataWorks 侧。
21. As a 数据平台分析人员, I want raw API JSON 继续全量保存为唯一真相源, so that owner、调度、cron、status 等字段无需预先索引即可在分析期提取。
22. As a 数据平台分析人员, I want `nodes-index.json` 只承担导航（id、name、type、文件路径、workspace_id、failed_nodes）, so that index 与 raw 之间不存在双份业务字段，避免不一致。
23. As a 数据平台分析人员, I want 快照目录用稳定 `id` 命名而非可读 `name`, so that Workspace 改名不会造成目录漂移。
24. As a 数据平台分析人员, I want 采集进度条显示当前 Workspace 的 name, so that 长时间采集时我知道正在处理哪一个。
25. As a 数据平台分析人员, I want `config` 子命令打印出多 Workspace 配置概览（不含密钥）, so that 我能在采集前核对配置是否生效。
26. As a 后续血缘分析阶段的分析人员, I want 每个 Workspace 的 lineage 文件独立落盘且记录带 `workspace_id`, so that 分析期可以自主决定是否跨 Workspace 聚合，而采集层不强加合并语义。
27. As a 后续血缘分析阶段的分析人员, I want 每个 Workspace 条目保存 `maxcompute_project` 映射, so that 解析 `other_project.table` 引用时能判断表归属于哪个 MaxCompute 项目。
28. As a 后续血缘分析阶段的分析人员, I want 采集层不预判分析所需字段, so that 分析需求变化时只需重读 raw 而非重新采集。
29. As an 实现该功能的 agent, I want spec 明确「单 Workspace 只是列表长度为 1，不存在模式分支」, so that 我不会写出 single/multi 双路径代码。
30. As an 实现该功能的 agent, I want ADR-0001/0002 固化目录契约与采集/分析边界, so that 我不会「好心地」在采集层加入跨 Workspace 合并或分析字段提升。
31. As an 实现该功能的 agent, I want 测试接缝固定为 CLI 黑盒、stub 只打在 SDK 边界, so that 我不会为可测性大幅重构生产代码或 mock 内部实现细节。
32. As a 调用本工具的脚本维护者, I want 退出码语义清晰（0 = 完整成功，1 = 存在失败，130 = 用户中断）, so that 我可以在调度系统中可靠地编排重试与告警。
33. As a 数据平台分析人员, I want 从配置中移除某个 Workspace 后其历史目录与 index 条目不被自动删除, so that 误操作配置不会连带销毁已采集的数据（清理由人工执行）。
34. As a 数据平台分析人员, I want 不再存在 `DATAWORKS_PROJECT_IDENTIFIER`、`DATAWORKS_PROJECT_ID` 等废弃配置项, so that 配置面只剩一条路径，没有无效变量误导后来者。

## Implementation Decisions

**配置模型（D-1 / D-2 / D-6 / D-7）**

- `.env` 中 `DATAWORKS_WORKSPACES` 为 JSON 数组，每个条目：`id`（int，主键）、`name`（str，数组内唯一）、`maxcompute_project`（str，与 Workspace 1:1）。
- 用 pydantic-settings 解析为 Workspace 设置模型列表；配置解析 fail-fast：非法 JSON、缺字段、重复 `id` 或 `name` → 启动即报错退出。
- 删除单值 `DATAWORKS_PROJECT_ID` 与预留变量 `DATAWORKS_PROJECT_IDENTIFIER`；单 Workspace 即长度为 1 的数组，代码中无 single/multi 模式分支。
- DataWorks region 保持全局单值配置（默认 3 个 Workspace 同地域；出现跨地域时再扩展）。
- MaxCompute 配置（project/endpoint/schema）与采集实现完全不动；`maxcompute_project` 仅作为 Workspace 的环境映射元数据写入 index，不驱动任何 MaxCompute 采集行为。

**执行模型（D-3）**

- 顺序遍历 Workspace 列表；复用单个 `DataWorksClient` 实例，`project_id` 由全局配置下沉为方法参数（ListNodes / GetNode 调用时传入）。
- 现有分页、tenacity 指数退避重试逻辑保持不变。
- 进度展示沿用 rich 单进度条，文案携带当前 Workspace 的 `name`。

**Snapshot 布局（D-4，见 ADR-0001）**

```
source/
  manifest.json                          # 仅全量 export 写入
  dataworks/
    workspaces-index.json                # Workspace 注册表 + 最近状态（upsert）
    workspaces/<project_id>/
      nodes-index.json                   # 含 workspace 元数据头 + 条目 + failed_nodes
      nodes/<node_id>.json               # raw 全量真相源
      sql/<node_id>_<n>.sql
      lineage/task-lineage.jsonl
  maxcompute/                            # 布局与实现不变
```

- 目录名用稳定 `id`（非 `name`，避免改名漂移）。
- 现有单 Workspace 内的写入逻辑仅需更换 base 目录。

**身份与关联（D-5 / D-6）**

- `nodes-index.json` 每个条目、`task-lineage.jsonl` 每条记录显式写入 `workspace_id`。
- `workspace_name`、`maxcompute_project` 等展示/映射属性只出现在 `workspaces-index.json` 与 `nodes-index.json` 顶层，不逐条复制。
- `workspaces-index.json` 条目含 `generated_at`，用于判断新鲜度。

**失败与退出码（D-8）**

- Workspace 级：逐个包错误边界，失败记 `status: failed` + 错误信息，继续下一个 Workspace；MaxCompute 采集与 manifest 生成不被 DataWorks 失败阻断。
- 节点级：`get_node` 失败 continue 并记入 `failed_nodes`。
- 存在任何 Workspace/节点级失败 → 进程 exit 1；全部成功 → 0；KeyboardInterrupt → 130（维持现状）。

**重复执行与清理（D-9）**

- 覆盖语义维持（`EXPORT_OVERWRITE`），无增量状态文件。
- Workspace 采集完整跑完后，以本次 `list_nodes` 权威集合清理该目录中不在集合内的 `nodes/`、`sql/` 文件。
- `status: failed` 的 Workspace 不清理；`failed_nodes` 对应旧文件保留。
- 从配置移除的 Workspace：目录与 index 条目不自动删除，人工清理。

**`--workspace` 过滤（D-12 / D-13）**

- `dataworks` 与 `export` 子命令支持可选 `--workspace <id>`；id 必须存在于配置，否则报错退出；缺省 = 全部。
- 纯运行时列表过滤，不写入配置、不引入模式、不新增采集流程。
- `workspaces-index.json` 为「注册表 + 各 Workspace 最近状态」：部分采集时读取-合并-写回，只 upsert 本次条目，未涉及条目原样保留；文件不存在则创建。
- `manifest.json` 仅由全量 `export` 写入，`dataworks` 子命令不修改；manifest 内 `sources.dataworks` 记录全部 Workspace 列表。

**血缘与分析边界（D-10 / D-11，见 ADR-0002）**

- 采集期各 Workspace 独立落盘，不做跨 Workspace lineage 合并，不生成全局合并文件。
- 表级血缘允许跨 Workspace / 跨 MaxCompute 项目，聚合与识别属后续分析阶段；SQL 表引用解析须支持 `other_project.table`。
- 任务级 DataWorks 依赖当前按 Workspace 内理解。
- raw 为唯一真相源；index 只导航，不预提 owner/调度/cron/status 等业务字段。
- 不新增依赖 API、表级血缘 API。

**模块改动范围**

- `config`：Settings 改为多 Workspace 模型 + 校验 + 删除废弃变量；若模块级 `settings = Settings()` 阻碍 CLI 测试，可调整为惰性初始化，**生产行为保持不变**。
- `dataworks`：`project_id` 参数化；提取函数与响应解析逻辑不动。
- `export`：遍历 Workspace、目录切换、index/注册表写入、upsert、清理、失败记录、manifest 多 Workspace 化。
- `cli`：新增 `--workspace` 参数、`config` 打印多 Workspace 视图、退出码语义。
- `maxcompute`：不改动。
- `.env.example`：同步新配置面（移除废弃项、增加 `DATAWORKS_WORKSPACES` 示例）。

**测试实现约束（用户明确补充）**

- 不为测试大幅重构生产代码。
- `DataWorksClient` 只允许在 SDK 调用边界 stub；禁止 mock `export_dataworks()`、内部 helper、私有方法等实现细节。
- 惰性初始化 `settings` 仅在确实阻碍 CLI 测试时采用，且生产行为不变。

## Testing Decisions

- **唯一测试接缝 = CLI 黑盒**：以子命令调用 CLI 入口，经真实参数解析 → 配置加载 → 采集 → 文件落盘全链路，只断言外部可观察结果。
- 一个好的测试只验证外部行为：退出码、stdout/stderr 中必要的错误信息、Snapshot 文件与目录结构、JSON 内容、旧文件保留/清理与否、`workspaces-index.json` 的 upsert 行为、`manifest.json` 是否生成——不验证内部调用次数、私有方法状态或控制流细节。
- **Stub 位置**：`DataWorksClient` 的 SDK 调用边界（`list_nodes` / `get_node` 返回固定 fixture）；MaxCompute 在其 client 边界 stub 或不触发；测试使用临时目录作为 `source_dir` 与最小 env。
- **测试矩阵**：

  | 场景 | 断言重点 |
  |---|---|
  | 非法 JSON / 重复 id / 重复 name | fail-fast，非零退出 |
  | 多 Workspace 正常全量 | 目录布局、`workspace_id` 入记录、`workspaces-index.json` 结构、manifest 含全部 Workspace、exit 0 |
  | 某 Workspace stub 抛错 | 其余照采、`status: failed`、**manifest 仍生成**、exit 1（本改造明确修复的行为，必须覆盖） |
  | 部分节点 `get_node` 失败 | `failed_nodes` 记录、旧文件保留、exit 1 |
  | fixture 中删除节点后重采 | 幽灵文件被清理；失败 Workspace 不清理 |
  | `--workspace 123` | 仅该目录更新；index 中 456/789 原样、123 upsert |
  | `--workspace` 未配置 id | 报错、非零退出 |
  | `config` 子命令 | 打印多 Workspace 配置、exit 0 |
- **先例**：仓库当前无任何测试（`tests/` 不存在），本批测试同时建立 fixture 惯例；不拆分 `DataWorksClient` 单元测试或 `export_dataworks()` 内部单元测试——矩阵以 CLI 接缝为限。

## Out of Scope

- DWS 设计、Semantic Layer 设计及其任何相关逻辑。
- SQLGlot、LLM 或复杂 SQL 分析逻辑。
- 跨 Workspace lineage 合并、全局合并文件生成（属分析阶段）。
- DataWorks 依赖 API、表级血缘 API、列级血缘采集。
- MaxCompute 采集实现与目录布局的任何修改（多 MaxCompute 项目采集亦不做）。
- 增量采集 / fingerprint 状态机制。
- 并行（多线程）采集多 Workspace。
- 跨地域 Workspace 的按条目 region 配置（当前假设同地域）。
- Workspace 从配置移除后的自动清理。
- 自动删除 `failed_nodes` 之外任何未经 API 权威集合确认的文件。
- GitHub/GitLab 等外部 issue tracker 集成。

## Further Notes

- 本 spec 固化的 shared understanding 来源于完整设计访谈（决策编号 D-1～D-13 已逐条确认）；实现前如发现决策冲突，以 `docs/adr/0001`、`docs/adr/0002` 与本 spec 的 Implementation Decisions 为准。
- 领域术语见根目录 `CONTEXT.md`（Workspace / Node / Snapshot / Raw / 表级血缘 / 任务级依赖）；实现与测试命名应使用 glossary 词汇。
- 已代为拍板并获接受的 4 项小事：删除 `DATAWORKS_PROJECT_IDENTIFIER`；配置 fail-fast；移除配置不自动删历史快照；rich 单进度条显示当前 Workspace name。
- 实现阶段入口建议：先配置模型与 fail-fast（可独立验证），再 client 参数化，再 export 布局/失败/清理，最后 CLI 参数与测试收口——顺序非强制，以 tracer-bullet 拆票（`to-tickets`）为准。
- 测试环境注意：模块级 `settings` 实例化与 `.env` 读取是 CLI 测试的主要摩擦点，惰性初始化是被允许的最小生产改动。

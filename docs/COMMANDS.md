# 命令参考

```bash
uv run data-platform-analysis [--log-level LEVEL] <command> [options]
```

全局参数：

| 参数 | 说明 |
| --- | --- |
| `--log-level` | `DEBUG` / `INFO` / `WARNING` / `ERROR`，默认 `INFO`；须写在子命令之前 |

退出码：

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部成功 |
| 1 | 存在 Workspace / File / Table 级失败，或命令执行失败（含配置错误、未配置的 `--workspace`） |
| 130 | 用户中断（Ctrl-C） |

## 子命令总览

| 命令 | 作用 |
| --- | --- |
| `dataworks` | 只采集 DataWorks（File → Raw GetFile → Content → files-index） |
| `maxcompute` | 只采集 MaxCompute（Table → Metadata → tables-index） |
| `export` | `dataworks` + `maxcompute` 组合；全量时额外写入 `manifest.json` |
| `summary` | 根据已有 Snapshot 重新生成 `Summary.md` |
| `config` | 打印当前生效的非敏感配置（不含密钥），不发起任何采集 |

分析命令（只读 Snapshot / 上一阶段产物，不发起任何采集）：

| 命令 | 作用 |
| --- | --- |
| `analyze` | 基于已有 Snapshot 生成 `analysis/` Evidence Chain（M2.1–M2.5）；可选 `--workspace <id>` |
| `analyze-layer` | 基于已有 `analysis/inventory` 执行 M2.2 Layer Assessment，不重跑 SQL / Lineage / Profiling |
| `analyze-business` | 基于已有 M2 产物执行 M3 Business Understanding（Domain / Object 候选 + 证据） |
| `analyze-business-quality` | 基于已有 M2 / M3 产物执行 M3.1 质量评估（只评估，不识别） |
| `analyze-business-objects` | 基于已有 M2 / M3 / M3.1 产物执行 M3.2 Object & Relationship 证据结构 |
| `analyze-business-processes` | 基于已有 M2 ~ M3.1 产物执行 M3.3 Process Candidate Analysis |
| `analyze-business-grain` | 基于已有 M2 ~ M3.2 产物执行 M3.4 Grain Candidate Analysis |
| `analyze-business-model` | 基于已有 M2 ~ M3.4 产物执行 M3.5 Fact / Dimension Candidate Analysis（candidate + 证据，不产出 DWD / DWS / Semantic Layer） |
| `analyze-current-state-model` | 基于已有 M2 ~ M3.5 产物执行 M3.6 Current-State Model Review（只评审：当前形态分类 + 18 类 finding + 人工清单），并附带 M3.6 v2 Problem Assessment（finding → problem candidate + 13 类 taxonomy + 证据 / 影响 / 根因 + 人工清单），一次写出 9 个产物，不设计 Target DWD、不改上游产物；方法论与人工裁决流程见 [M36_PROBLEM_ASSESSMENT.md](M36_PROBLEM_ASSESSMENT.md)，人工裁决实操见 [M36_HUMAN_ADJUDICATION_GUIDE.md](M36_HUMAN_ADJUDICATION_GUIDE.md) |

### 人工裁决回填（M3.6 Human Adjudication）

1. 编辑 `analysis/business/current-state-problem-review-checklist.md`（Problem 侧，13 分区）与 / 或 `analysis/business/current-state-review-checklist.md`（Finding 侧，5 分区），**只填 `human_status` / `human_name` / `note` 三列**，取值 `pending` / `confirmed` / `rejected` / `needs_review` / `needs_discussion`；
2. 重跑 `uv run data-platform-analysis analyze-current-state-model`，人工三列原样保留，`current-state-problems.json` 的 `status` 与 `confirmed` 计数随之更新；机器列会被重新生成，勿手改列名或删列（必需列缺失 → 退出码 1）；
3. 清单每分区最多渲染 50 行（Problem 侧合计 260 行 / 1190 条），全量见 `current-state-problems.json`，实操见 [M36_HUMAN_ADJUDICATION_GUIDE.md](M36_HUMAN_ADJUDICATION_GUIDE.md)。

分析命令共性：无参数、无专用配置，只读上游产物并写 `analysis/`；上游缺失或跨文件引用未知即退出码 1（不回退执行前置阶段）。等价入口：`uv run python -m data_platform_analysis.cli <子命令>`。

`dataworks` / `maxcompute` / `export` 都接受：

| 参数 | 说明 |
| --- | --- |
| `--workspace <id>` | 只采集该 Workspace；`id` 必须已在 `WORKSPACES` 中配置，否则直接报错退出（退出码 1）；缺省为全部 Workspace |
| `--limit <n>` | 采集限制模式；`n` 必须是大于 0 的整数，`0`、负数、非整数直接拒绝（退出码 1）；缺省为全量采集 |

## 示例

```bash
# 全部 Workspace 的 DataWorks 采集
uv run data-platform-analysis dataworks

# 指定 Workspace
uv run data-platform-analysis dataworks --workspace 123456

# 指定 Workspace + 限制模式
uv run data-platform-analysis dataworks --workspace 123456 --limit 10

# MaxCompute
uv run data-platform-analysis maxcompute
uv run data-platform-analysis maxcompute --workspace 123456
uv run data-platform-analysis maxcompute --limit 10

# DataWorks + MaxCompute
uv run data-platform-analysis export
uv run data-platform-analysis export --workspace 123456
uv run data-platform-analysis export --limit 10
uv run data-platform-analysis export --workspace 123456 --limit 10

# 查看配置
uv run data-platform-analysis config

# 根据已有 Snapshot 重新生成 Summary
uv run data-platform-analysis summary

# 分析链（按阶段，逐级只读上一阶段产物）
uv run data-platform-analysis analyze
uv run data-platform-analysis analyze-layer
uv run data-platform-analysis analyze-business
uv run data-platform-analysis analyze-business-quality
uv run data-platform-analysis analyze-business-objects
uv run data-platform-analysis analyze-business-processes
uv run data-platform-analysis analyze-business-grain
uv run data-platform-analysis analyze-business-model
uv run data-platform-analysis analyze-current-state-model
```

## `--limit` 语义

`--limit N` 表示**每个 Workspace** 最多处理 N 个对象：

- DataWorks：最多 N 个 File；分页过程中一旦达到 limit 立即停止后续分页，不会为了拿总数继续请求。
- MaxCompute：`ListTables` 正常获取完整表列表，然后只对前 N 张表执行 `GetTable`。
- 多 `UseType` 场景下，limit 是整个 Workspace 的总配额（A/B/C 三类合计 N 个），不是每类各 N 个。

## Cleanup 安全规则

```
limit is None     → 完整集合 → 允许 Cleanup
limit is not None → 部分集合 → 禁止 Cleanup（日志输出 Cleanup=SKIP）
```

- 成功的 `ListFiles` / `ListTables` 返回值是当前对象集合的权威来源，据此删除远端已不存在的本地 Snapshot。
- 单个对象获取失败：不覆盖旧 Snapshot，成功对象正常更新，失败对象记入 index（`failed_files` / `failed_tables`）。
- 整个 List API 失败或响应结构异常：不 Cleanup、不覆盖旧 index，Workspace 标记失败。
- 不提供 `--no-cleanup` 开关。

## 多 Workspace 行为

- 缺省 `--workspace` 时顺序采集全部已配置 Workspace。
- 每个 Workspace 独立落盘到 `source/<dataworks|maxcompute>/workspaces/<workspace_id>/`，互不覆盖。
- 单个 Workspace 失败不会阻断其他 Workspace；只要存在失败，最终退出码为 1。
- `dataworks` 的 `workspaces-index.json` 采用读-改-写 upsert：本次未采集的 Workspace 条目原样保留。
- `manifest.json` 仅由全量 `export`（不带 `--workspace`）写入。

# Current-State Evidence Execution Chain

本章给出从 Snapshot 采集到 M3.6 人工裁决的**完整可重复命令链**：每个阶段的输入、命令、输出与依赖。所有条目均按当前代码实测核对（见 [实测验证](#实测验证)），不依赖既有文档描述。

约定：

- 除采集阶段外，路径若无前缀均相对 `analysis/`（由 `ANALYSIS_DIR` 决定，默认 `analysis`）。
- **`source/` 对第 4 阶段起的所有命令只读**：分析链只写 `analysis/`，不改写 Snapshot。
- 每条命令只覆盖自己声明的产物；未涉及的上游产物保持原样（`business/` 不在 `analyze` 的清理范围内）。
- 任何阶段上游缺失 → 退出码 1、不回退执行前置阶段、不留下半成品文件。

## 阶段命令矩阵

| # | 阶段 | 命令 | 写出的产物（相对 `analysis/`） | 数量 |
| --- | --- | --- | --- | --- |
| 1 | M1 DataWorks 采集 | `dataworks`（或 `export`） | `source/dataworks/workspaces/<id>/**`、`source/dataworks/workspaces/<id>/files-index.json`、`source/dataworks/workspaces-index.json` | — |
| 2 | M1 MaxCompute 采集 | `maxcompute`（或 `export`） | `source/maxcompute/workspaces/<id>/**`、`source/maxcompute/workspaces/<id>/tables-index.json`；全量 `export` 另写 `source/manifest.json` | — |
| 3 | M1 Snapshot Summary | `summary` | `source/Summary.md` | 1 |
| 4 | M2.1–M2.5 Evidence Chain | `analyze` | `inventory/{workspaces,files,tables,columns}.json`、`inventory/summary.md`、`layer/{assessments.json,summary.md}`、`sql/{statements,table-references,parse-errors}.json`、`lineage/{table-lineage,core-table-candidates}.json`、`lineage/summary.md`、`profiling/{tables,columns}.json`、`profiling/summary.md`、`errors.json`、`Summary.md` | **18** |
| 5 | M2.2 Layer Assessment 单独重跑 | `analyze-layer` | `layer/{assessments.json,summary.md}`（仅覆盖这 2 个） | 2 |
| 6 | M3 Business Understanding | `analyze-business` | `business/{terms,tables,domains,objects}.json`、`business/summary.md` | **5** |
| 7 | M3.1 Quality Assessment | `analyze-business-quality` | `business/{quality-assessment.json,quality-assessment.md,review-checklist.md}` | **3** |
| 8 | M3.2 Object & Relationship | `analyze-business-objects` | `business/{objects-registry,object-tables,object-relationships,object-evidence-matrix}.json`、`business/object-graph.md` | **5** |
| 9 | M3.3 Process Candidate | `analyze-business-processes` | `business/{process-signals,processes,process-tables,process-objects}.json`、`business/process-summary.md`、`business/process-review-checklist.md` | **6** |
| 10 | M3.4 Grain Candidate | `analyze-business-grain` | `business/{grain-signals,grain-candidates,grain-tables}.json`、`business/grain-summary.md`、`business/grain-review-checklist.md` | **5** |
| 11 | M3.5 Fact / Dimension Candidate | `analyze-business-model` | `business/{fact-candidates,dimension-candidates,fact-dimension-relationships,fact-tables,dimension-tables,model-evidence-matrix}.json`、`business/model-summary.md`、`business/model-review-checklist.md` | **8** |
| 12 | M3.6 Current-State Model Review + Problem Assessment | `analyze-current-state-model` | **Finding 侧 5 个**：`business/{current-state-model,current-state-model-tables,model-review-findings}.json`、`business/current-state-model-summary.md`、`business/current-state-review-checklist.md`；**Problem 侧 4 个**：`business/{current-state-problems,current-state-problem-evidence}.json`、`business/current-state-problem-summary.md`、`business/current-state-problem-review-checklist.md` | **9** |
| 13 | M3.6 Human Adjudication | 无命令（人工） | 编辑上述两个 checklist → 重跑第 12 行命令（人工三列原样带回） | — |
| 14 | M3.6 Workbench | 无 Python 命令 | `python3 -m http.server 8787`（或 `cd workbench && npm run serve`） | — |

`18 + 5 + 3 + 5 + 6 + 5 + 8 + 9 = 59`，即 `analysis/` 当前的 59 个产物文件。

**Evidence 与 Finding / Problem 的关系**：Evidence 不是独立命令或独立阶段。第 12 行一次运行内先产出 Finding（`model-review-findings.json`），再把 finding 聚合成 problem candidate 并写出 `current-state-problems.json` + `current-state-problem-evidence.json`；Problem Assessment 是同一次运行的附带步骤，无独立入口。

## 输入依赖（必需 / 可选）

必需输入缺任一 → 退出码 1，不回退执行前置阶段。错误信息分两种：`analyze-layer` 报 `输入不存在：<路径>（请先执行 analyze）`；其余阶段报 `<上游> 产物缺失，无法执行 <阶段>：<缺失文件列表>`。

| 命令 | 必需输入（相对 `analysis/`） | 可选输入（重跑时带回人工状态） |
| --- | --- | --- |
| `analyze` | `source/**` + `config/layer-rules.yaml` | — |
| `analyze-layer` | `inventory/tables.json` + `config/layer-rules.yaml` | — |
| `analyze-business` | `inventory/{tables,columns}.json`、`sql/{statements,table-references}.json`、`lineage/{table-lineage,core-table-candidates}.json`、`layer/assessments.json` | — |
| `analyze-business-quality` | `business/{tables,domains,objects,terms}.json`、`inventory/{tables,columns}.json`、`sql/table-references.json`、`lineage/{table-lineage,core-table-candidates}.json` | — |
| `analyze-business-objects` | `business/{objects,tables,domains}.json`、`business/{quality-assessment.json,review-checklist.md}`（M3.1 产物，必需）、`inventory/{tables,columns}.json`、`sql/{statements,table-references}.json`、`lineage/{table-lineage,core-table-candidates}.json`、`layer/assessments.json` | — |
| `analyze-business-processes` | `business/{objects-registry,object-tables,object-relationships,tables,terms}.json`、`inventory/{tables,columns}.json`、`sql/{statements,table-references}.json`、`lineage/{table-lineage,core-table-candidates}.json`、`business/review-checklist.md` | `business/process-review-checklist.md` |
| `analyze-business-grain` | `business/{process-signals,processes,process-tables,process-objects,objects-registry,object-tables,object-relationships}.json`、`inventory/{tables,columns}.json`、`sql/{statements,table-references}.json`、`lineage/{table-lineage,core-table-candidates}.json`、`profiling/{tables,columns}.json` | `business/{process-review-checklist.md,grain-review-checklist.md}` |
| `analyze-business-model` | `business/{grain-candidates,grain-tables,processes,process-objects,objects-registry,object-tables,object-relationships}.json`、`inventory/{tables,columns}.json`、`sql/table-references.json`、`lineage/{table-lineage,core-table-candidates}.json`、`profiling/{tables,columns}.json`、`layer/assessments.json` | `business/{process-review-checklist.md,grain-review-checklist.md,model-review-checklist.md}` |
| `analyze-current-state-model` | `business/{fact-candidates,dimension-candidates,fact-dimension-relationships,fact-tables,dimension-tables,grain-candidates,processes,objects-registry}.json`、`inventory/{tables,columns}.json`、`lineage/{table-lineage,core-table-candidates}.json`、`layer/assessments.json` | `business/{current-state-review-checklist.md,current-state-problem-review-checklist.md}` |

## Recommended Execution Order

### A. 全新环境（从零到 Workbench）

```bash
# 0) 一次性准备：复制 .env.example → .env 并填写 Workspaces / 阿里云凭证
uv run data-platform-analysis config        # 核对生效配置（不含密钥）

# 1) 采集 Snapshot（唯一会写 source/ 的阶段）
uv run data-platform-analysis export        # 或分开跑 dataworks / maxcompute
uv run data-platform-analysis summary       # 可选：重生成 source/Summary.md

# 2) M2 Evidence Chain（18 个产物）
uv run data-platform-analysis analyze

# 3) M3 → M3.6，严格按序，不得跳级
uv run data-platform-analysis analyze-layer
uv run data-platform-analysis analyze-business
uv run data-platform-analysis analyze-business-quality
uv run data-platform-analysis analyze-business-objects
uv run data-platform-analysis analyze-business-processes
uv run data-platform-analysis analyze-business-grain
uv run data-platform-analysis analyze-business-model
uv run data-platform-analysis analyze-current-state-model

# 4) 人工裁决（见下一小节）+ Workbench
python3 -m http.server 8787                # 或 cd workbench && npm run serve
open http://localhost:8787/workbench/
```

### B. Snapshot 已存在（本仓库常态）

跳过第 1 组，从 `analyze` 开始执行 A 的第 2、3、4 组。

### C. 只重跑单个阶段

按「输入依赖」表确认上游产物齐备，只执行该命令即可；它仅覆盖自己的输出文件。想清空重跑 M2 用 `analyze`（会删 `inventory/ sql/ lineage/ profiling/ layer/ errors.json Summary.md`，**不动 `business/`**）；只重跑分层用 `analyze-layer`。

### D. 人工清单回填之后

只重跑对应阶段的命令，人工三列（`human_status` / `human_name` / `note`）原样带回，机器列重新生成：

| 改动的清单 | 重跑 |
| --- | --- |
| `business/review-checklist.md` | `analyze-business-objects` → `analyze-business-processes`（二者均必需它；若 `processes.json` 变化，再依次重跑 grain / model / current-state） |
| `business/process-review-checklist.md` | `analyze-business-grain` → `analyze-business-model` → `analyze-current-state-model` |
| `business/grain-review-checklist.md` | `analyze-business-model` → `analyze-current-state-model` |
| `business/model-review-checklist.md` | `analyze-current-state-model` |
| `business/current-state-review-checklist.md`、`business/current-state-problem-review-checklist.md` | `analyze-current-state-model` |

## M3.6 Human Decision → Workbench

1. **人工填清单**：`analysis/business/current-state-problem-review-checklist.md`（Problem 侧）与 / 或 `analysis/business/current-state-review-checklist.md`（Finding 侧），只填 `human_status` / `human_name` / `note` 三列。
2. **重跑** `uv run data-platform-analysis analyze-current-state-model`，人工三列带回、`current-state-problems.json` 的 `status` 与 `confirmed` 计数更新；必需列缺失 → 退出码 1。
3. **Workbench 载入同一批产物**（只读，不写回任何文件）：

   | 文件 | 用途 | 必需 |
   | --- | --- | --- |
   | `analysis/business/current-state-problems.json` | Problem 列表 / Detail / 汇总数字 | 是 |
   | `analysis/business/current-state-problem-evidence.json` | Evidence Explorer 全量证据行 | 是 |
   | `analysis/business/current-state-model-tables.json` | Affected Tables 的 role / shape / process / grain | 否（缺失降级） |
   | `analysis/layer/assessments.json` | Affected Tables 的 Layer | 否（缺失降级） |

   启动：`python3 -m http.server 8787`（仓库根）→ `http://localhost:8787/workbench/`；浏览器冒烟 `http://localhost:8787/workbench/smoke.html` 期望末行 `PASS=true`；Node 测试 `cd workbench && npm test`。
4. 人工裁决状态存 `localStorage["m36-human-adjudication"]`，「重新加载产物」只重新 fetch JSON，不覆盖 localStorage。

## 实测验证

> 验证环境：macOS，2026-10-07，`uv run data-platform-analysis`（HEAD = `c61fcb3`）。

| 检查项 | 结果 |
| --- | --- |
| 14 个子命令 `--help` | 全部 exit 0；参数与本文件「子命令总览」一致（`dataworks` / `maxcompute` / `export`：`--workspace` `--limit`；`analyze`：`--workspace`；其余无参数） |
| `config` | exit 0，打印非敏感配置，不发起采集 |
| Clean-room 全链（`ANALYSIS_DIR=<临时目录>`，9 条分析命令） | 全部 exit 0，产出 59 个文件；与生产 `analysis/` 逐字节一致（唯一差异是报告里「输入」一行的路径写法，归一化后 **59/59 相同**） |
| 生产 `analysis/` 原地重跑全链 | exit 0，**59/59 SHA256 与重跑前完全一致** |
| 上游缺失（`ANALYSIS_DIR` 指向空目录） | 8 条下游命令全部 exit 1：`analyze-layer` 报 `输入不存在：…（请先执行 analyze）`，其余 7 条报 `<上游> 产物缺失，无法执行 <阶段>：<文件列表>`；**残留文件数 = 0**（原子写出，无半成品） |
| `analyze --workspace 466338` | exit 0，临时目录仅 18 个 M2 产物（无 `business/`），生产 `analysis/` 未受影响 |
| `summary` | exit 0，仅改写 `source/Summary.md`；其余 12998 个 Snapshot 文件哈希不变。注意：该文件含「Summary 生成时间」时间戳，**连续两次运行哈希不同**，属预期非确定性 |
| `uv run pytest` | 368 passed |
| `cd workbench && npm test` | 48 passed |
| `dataworks` / `maxcompute` / `export` | **未实际执行**（需阿里云凭证且会改写 `source/`）；仅验证 `--help` exit 0 与参数签名 |

干跑提示：给任何分析命令加 `ANALYSIS_DIR=<自定义目录>` 即可在不影响生产 `analysis/` 的前提下跑全链；报告中的「输入」一行会显示该目录绝对路径，因此跨目录比较哈希时需先归一化该行。

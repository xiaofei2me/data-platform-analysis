# 命令参考

> 阶段总账（Stage 00 ～ 20 ↔ Milestone ↔ 命令 ↔ 代码 ↔ 产物 ↔ 文档、读序、产物分类与命名规范）见 [STAGE_INDEX.md](STAGE_INDEX.md)。

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
| `summary` | 根据已有 Snapshot 重新生成 `source/Summary.md` |
| `config` | 打印当前生效的非敏感配置（不含密钥），不发起任何采集 |

分析命令（只读 Snapshot / 上一阶段产物，不发起任何采集）：

| 命令 | 作用 |
| --- | --- |
| `analyze` | 基于已有 Snapshot 执行完整 Analysis Chain（Stage 01–14：Inventory → Evidence → Understanding → Review） |
| `analyze --stage inventory` | 只执行 Stage 01（Inventory），支持 `--workspace` |
| `analyze --stage evidence` | 只执行 Stage 02–05（Evidence：Layer + SQL + Lineage + Profiling），不支持 `--workspace` |
| `analyze --stage understanding` | 只执行 Stage 06–11（Understanding：Business + Modeling），不支持 `--workspace` |
| `analyze --stage review` | 只执行 Stage 12–14（Review：Findings → Problem Evidence），不支持 `--workspace` |

### 人工裁决回填（M3.6 Human Adjudication）

1. 编辑 `analysis/review/current-state-problem-review-checklist.md`（Problem 侧，13 分区）与 / 或 `analysis/review/current-state-review-checklist.md`（Finding 侧，5 分区），**只填 `human_status` / `human_name` / `note` 三列**，取值 `pending` / `confirmed` / `rejected` / `needs_review` / `needs_discussion`；
2. 重跑 `uv run data-platform-analysis analyze --stage review`，人工三列原样保留，`current-state-problems.json` 的 `status` 与 `confirmed` 计数随之更新；机器列会被重新生成，勿手改列名或删列（必需列缺失 → 退出码 1）；
3. 清单每分区最多渲染 50 行（Problem 侧合计 260 行 / 1190 条），全量见 `current-state-problems.json`，实操见 [M36_HUMAN_ADJUDICATION_GUIDE.md](M36_HUMAN_ADJUDICATION_GUIDE.md)。

分析命令共性：无参数、无专用配置，只读 Snapshot / 上一阶段产物并写 `analysis/`。阶段内模块缺输入（跨文件引用未知、必需 JSON 缺失、配置非法）→ 退出码 1 且不回退；但流水线层面 `analyze --stage understanding` / `--stage review` 在 `evidence/layer/assessments.json` 缺失时会先自动补跑 evidence，`--stage inventory` / `--stage evidence` 只依赖 `source/`、空 `analysis/` 下照常 exit 0。等价入口：`uv run python -m data_platform_analysis.cli <子命令>`。

## 分析命令共性

- 无专用配置，只读 Snapshot / 上游产物并写 `analysis/`
- 阶段内模块缺必需输入 → 退出码 1、模块自身不回退执行前置阶段
- 流水线层面：`understanding` / `review` 缺 `evidence/layer/assessments.json` → 自动先补跑 evidence；`inventory` / `evidence` 只读 `source/`
- 等价入口：`uv run python -m data_platform_analysis.cli <子命令>`

## 采集命令参数

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

# 完整 Analysis Chain（推荐）
uv run data-platform-analysis analyze
```

分阶段执行（仅用于重跑单阶段，不推荐）：

```bash
uv run data-platform-analysis analyze --stage inventory      # Stage 01 (Inventory)
uv run data-platform-analysis analyze --stage evidence       # Stage 02-05 (Evidence)
uv run data-platform-analysis analyze --stage understanding  # Stage 06-11 (Understanding)
uv run data-platform-analysis analyze --stage review         # Stage 12-14 (Review)
```

# Cleanup 安全规则

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
- 清场范围分两类：`analyze`、`analyze --stage inventory`、`analyze --stage evidence` 先执行 `pipeline._reset_outputs()`，清空 `inventory/`、`evidence/`、`understanding/`、`review/` 与根 `summary.md`（所以**未声明的 `understanding/`、`review/` 也会被删**，两份人工回填清单一并丢失）；`analyze --stage understanding`、`analyze --stage review` 不清场，上游产物保持原样。
- 上游缺失的三种情况：阶段内模块缺必需输入 → 退出码 1、模块自身不回退、不留半成品；`understanding` / `review` 缺 `evidence/layer/assessments.json` → 流水线先自动补跑 `run_stage_evidence()`（该步会清场）；`inventory` / `evidence` 只依赖 `source/`，空 `analysis/` 下照常 exit 0。

## 阶段命令矩阵

Stage 号与 Milestone 的完整映射（含每阶段的代码模块、产物目录与阅读顺序）见 [STAGE_INDEX.md](STAGE_INDEX.md)；Stage 只追加不回改，Milestone（M1 / M2.x / M3.x）保持只读。

| # | Stage | 阶段 | 命令 | 写出的产物（相对 `analysis/`） | 数量 | 产物分类 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 00 | M1 DataWorks 采集 | `dataworks`（或 `export`） | `source/dataworks/workspaces/<id>/**`、`source/dataworks/workspaces/<id>/files-index.json`、`source/dataworks/workspaces-index.json` | — | 机器事实（Snapshot） |
| 2 | 00 | M1 MaxCompute 采集 | `maxcompute`（或 `export`） | `source/maxcompute/workspaces/<id>/**`、`source/maxcompute/workspaces/<id>/tables-index.json`；全量 `export` 另写 `source/manifest.json` | — | 机器事实（Snapshot）+ 辅助（`manifest.json`） |
| 3 | 00 | M1 Snapshot Summary | `summary` | `source/Summary.md` | 1 | 辅助（生成报告，含时间戳） |
| 4 | 01–14 | M2–M3.6 完整 Analysis Chain | `analyze` | `inventory/{workspaces,files,tables,columns,excluded-tasks,review-tasks}.json`、`inventory/summary.md`、`evidence/{layer,sql,lineage,profiling}/*`、`evidence/errors.json`、`understanding/business/*`、`understanding/modeling/*`、`review/*`、`summary.md` | **61** | 机器事实（inventory / sql / profiling）+ 规则推导（layer / lineage）+ 机器候选（business / modeling）+ 辅助（summary / errors） |
| 5 | 01 | Inventory 单独重跑 | `analyze --stage inventory` | `inventory/{workspaces,files,tables,columns,excluded-tasks,review-tasks}.json`、`inventory/summary.md` | **7** | 机器事实（inventory） |
| 6 | 02–05 | Evidence 单独重跑 | `analyze --stage evidence` | `evidence/{layer,sql,lineage,profiling}/*` + `errors.json` | **20** | 机器事实（sql / profiling）+ 规则推导（layer / lineage） |
| 7 | 06–11 | Understanding 单独重跑 | `analyze --stage understanding` | `understanding/business/*` + `understanding/modeling/*` | **23** | 机器候选（business / modeling）+ 辅助 |
| 8 | 12–14 | Review 单独重跑 | `analyze --stage review` | `review/*`（同时重跑 Stage 06–11 刷新 `understanding/**`，不写根 `summary.md`） | **13** | 机器候选（finding / problem）+ 证据 + 辅助 |

`61 = 7 + 18 + 23 + 13`，即 `analysis/` 当前的 61 个产物文件。

### Evidence Stage Contract

`analyze --stage evidence` 必须自洽，且与全量 `analyze` 的 Evidence 输出完全一致：

| 检查 | 契约 |
| --- | --- |
| 产物范围 | 同一个 `ANALYSIS_DIR` 下，`evidence/**`（12 个文件）、`inventory/**`（7 个文件）、`summary.md` 与全量 `analyze` 的对应产物**逐文件字节一致**（20/20 相同） |
| Evidence 报告 | `evidence/{layer,lineage,profiling}/summary.md` 是 Evidence 正式产物，由 `run_stage_evidence()` 与 `run()` 共用的 `_write_reports()` 写出 |
| 数据来源 | 报告用 Evidence stage 刚算完的 Layer / SQL / Lineage / Profiling 结果渲染；**不制造空 `LineageResult`，不重复计算任何 M2 输入** |
| 阶段边界 | 只产出 `inventory/` + `evidence/` + `summary.md`；**不产出** `understanding/**`、`review/**` |
| 阶段链 | `--stage inventory → evidence → understanding → review` 四条命令跑完后，`analysis/` 与全量 `analyze` **61/61 SHA256 完全一致** |

回归测试：`tests/test_evidence_stage_contract.py`。

## 输入依赖（必需 / 可选）

| 命令 | 必需输入 | 可选输入（重跑时带回人工状态） |
| --- | --- | --- |
| `analyze` | `source/**` + `config/{analysis-scope-rules,layer-rules,business-rules,process-rules}.yaml` | — |
| `analyze --stage inventory` | `source/**` + `config/{layer-rules,analysis-scope-rules}.yaml`（清场重建，不读已有 `analysis/`） | — |
| `analyze --stage evidence` | `source/**` + `config/{layer-rules,analysis-scope-rules}.yaml`（清场后自行重建 `inventory/`，不读已有 `inventory/`） | — |
| `analyze --stage understanding` | `inventory/{tables,columns}.json` + `evidence/{sql/statements,sql/table-references,lineage/table-lineage,lineage/core-table-candidates,layer/assessments}.json` + `config/{business-rules,process-rules}.yaml`；`evidence/layer/assessments.json` 缺失时流水线先自动补跑 evidence（此时改需 `source/**` + `config/layer-rules.yaml`） | `understanding/business/{process-review-checklist,grain-review-checklist}.md`、`understanding/modeling/model-review-checklist.md` |
| `analyze --stage review` | 上一行的全部输入 + `understanding/modeling/{fact-candidates,dimension-candidates,fact-dimension-relationships,fact-tables,dimension-tables}.json`（共 13 个必需 JSON，定义见 `review/findings.py::INPUT_FILES`） | `review/{current-state-review-checklist.md,current-state-problem-review-checklist.md}` |

## Recommended Execution Order

### A. 全新环境（从零到 Workbench）

```bash
# 0) 一次性准备：复制 .env.example → .env 并填写 Workspaces / 阿里云凭证
uv run data-platform-analysis config        # 核对生效配置（不含密钥）

# 1) 采集 Snapshot（唯一会写 source/ 的阶段）
uv run data-platform-analysis export        # 或分开跑 dataworks / maxcompute
uv run data-platform-analysis summary       # 可选：重生成 source/Summary.md

# 2) M2–M3.6 完整 Analysis Chain（61 个产物）
uv run data-platform-analysis analyze
```

### B. Snapshot 已存在（本仓库常态）

跳过第 1 组，从 `analyze` 开始执行 A 的第 2 组。

### C. 只重跑单个阶段

按「输入依赖」表确认上游产物齐备，只执行该命令即可。清场范围不同：

| 命令 | 是否清场 | 实际覆盖 |
| --- | --- | --- |
| `analyze` | 清空 `inventory/ evidence/ understanding/ review/ summary.md` | 全部 61 个产物 |
| `analyze --stage inventory` | **同样清空**（连 `understanding/`、`review/` 一起删） | `inventory/**`（7）+ 根 `summary.md` |
| `analyze --stage evidence` | **同样清空**（连 `understanding/`、`review/` 一起删） | `inventory/**` + `evidence/**` + 根 `summary.md`（20） |
| `analyze --stage understanding` | 不清场 | `understanding/**` |
| `analyze --stage review` | 不清场 | `understanding/**`（总是先重跑一遍）+ `review/**`，**不写**根 `summary.md` |

清空重跑 M2–M3.6 用 `analyze`（**不动 `source/`**）。人工回填过的两份 checklist 位于 `review/`，因此**不要**在生产 `analysis/` 上用 `--stage inventory` / `--stage evidence` 重跑——那会连清单一起删掉。

### D. 人工清单回填之后

只重跑 `analyze --stage review`，人工三列（`human_status` / `human_name` / `note`）原样带回，机器列重新生成：

| 改动的清单 | 重跑 |
| --- | --- |
| `understanding/business/review-checklist.md`、`process-review-checklist.md`、`grain-review-checklist.md`、`understanding/modeling/model-review-checklist.md` | `analyze --stage understanding` → `analyze --stage review` |
| `review/current-state-review-checklist.md`、`review/current-state-problem-review-checklist.md` | `analyze --stage review` |

## M3.6 Human Decision → Workbench

1. **人工填清单**：`analysis/review/current-state-problem-review-checklist.md`（Problem 侧）与 / 或 `analysis/review/current-state-review-checklist.md`（Finding 侧），只填 `human_status` / `human_name` / `note` 三列。
2. **重跑** `uv run data-platform-analysis analyze --stage review`，人工三列带回、`current-state-problems.json` 的 `status` 与 `confirmed` 计数更新；必需列缺失 → 退出码 1。
3. **Workbench 载入同一批产物**（只读，不写回任何文件）：

   | 文件 | 用途 | 必需 |
   | --- | --- | --- |
   | `analysis/review/current-state-problems.json` | Problem 列表 / Detail / 汇总数字 | 是 |
   | `analysis/review/current-state-problem-evidence.json` | Evidence Explorer 全量证据行 | 是 |
   | `analysis/review/current-state-model-tables.json` | Affected Tables 的 role / shape / process / grain | 否（缺失降级） |
   | `analysis/evidence/layer/assessments.json` | Affected Tables 的 Layer | 否（缺失降级） |

   启动：`python3 -m http.server 8787`（仓库根）→ `http://localhost:8787/workbench/`；浏览器冒烟 `http://localhost:8787/workbench/smoke.html` 期望末行 `PASS=true`；Node 测试 `cd workbench && npm test`。
4. 人工裁决状态存 `localStorage["m36-human-adjudication"]`，「重新加载产物」只重新 fetch JSON，不覆盖 localStorage。

## 实测验证

> 验证环境：macOS，2026-10-08，`uv run data-platform-analysis`（HEAD = `c61fcb3`）。其中「阶段清场范围」「上游缺失」「`uv run pytest`」三行已于 2026-10-09 在 HEAD = `cdff915` 重新实测并订正；其余行沿用 2026-10-08 的结果。

| 检查项 | 结果 |
| --- | --- |
| 5 个分析子命令 `--help` | 全部 exit 0；参数与本文件「子命令总览」一致（`analyze --stage inventory/evidence/understanding/review`：无参数；`dataworks` / `maxcompute` / `export`：`--workspace` `--limit`） |
| `config` | exit 0，打印非敏感配置，不发起采集 |
| Clean-room 全链（`ANALYSIS_DIR=<临时目录>`，4 条分析命令） | 全部 exit 0，产出 61 个文件；与生产 `analysis/` 逐字节一致（唯一差异是报告里「输入」一行的路径写法，归一化后 **61/61 相同**） |
| 生产 `analysis/` 原地重跑全链 | exit 0，**61/61 SHA256 与重跑前完全一致** |
| 阶段清场范围 | `analyze` / `--stage inventory` / `--stage evidence` 先执行 `_reset_outputs()` 清空 `inventory/` `evidence/` `understanding/` `review/` 与根 `summary.md`：生产 `analysis/` 的副本跑 `--stage inventory` 只剩 **8** 个文件、跑 `--stage evidence` 只剩 **20** 个；`--stage understanding` / `--stage review` **不清场**，副本 61 个文件全部保留（根 `summary.md` 哈希不变） |
| 上游缺失（`ANALYSIS_DIR` 指向空目录，`source/` 正常） | 4 条阶段命令**全部 exit 0 并补齐上游**：`--stage inventory` → 8 个文件、`--stage evidence` → 20 个、`--stage understanding` → 先打印 `Evidence 阶段未完成，执行 run_stage_evidence` 再产出 52 个、`--stage review` → 同样补跑后产出 61 个；只有阶段内模块缺必需输入时才报 `<上游> 产物缺失，无法执行 <阶段>` 并 exit 1 |
| `analyze --stage inventory --workspace 466338` | exit 0，临时目录仅 7 个 Inventory 产物 + 根 `summary.md`（无 `evidence/`、`understanding/`、`review/`），生产 `analysis/` 未受影响 |
| `summary` | exit 0，仅改写 `source/Summary.md`；其余 12998 个 Snapshot 文件哈希不变。注意：该文件含「Summary 生成时间」时间戳，**连续两次运行哈希不同**，属预期非确定性 |
| `uv run pytest` | 471 passed |
| `uv run ruff check src tests` / `uv run ruff format --check src tests` / `uv run -m mypy` | 全绿（0 errors） |
| `cd workbench && npm test` | 38 passed · 10 failed（golden 期望值早于当前 source 快照，待刷新） |
| `dataworks` / `maxcompute` / `export` | **未实际执行**（需阿里云凭证且会改写 `source/`）；仅验证 `--help` exit 0 与参数签名 |

干跑提示：给任何分析命令加 `ANALYSIS_DIR=<自定义目录>` 即可在不影响生产 `analysis/` 的前提下跑全链；报告中的「输入」一行会显示该目录绝对路径，因此跨目录比较哈希时需先归一化该行。

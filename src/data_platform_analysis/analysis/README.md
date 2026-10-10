# analysis/ —— Analysis 包

把只读的 `source/` Snapshot 转换成机器可读的 Evidence，再推导出 Understanding 与供人工裁决的 Review 产物。**本包只做提取与渲染，不做业务裁决**：结论类字段一律是 Candidate，`confirmed` 只能由人带回。

- 阶段总账（Stage ↔ Milestone ↔ 命令 ↔ 产物）：[docs/STAGE_INDEX.md](../../../docs/STAGE_INDEX.md)
- 逐字段证据链：[docs/CURRENT_STATE_EVIDENCE_MAP.md](../../../docs/CURRENT_STATE_EVIDENCE_MAP.md)
- 逐文件代码逻辑：[docs/CODE_LOGIC_ANALYSIS.md](../../../docs/CODE_LOGIC_ANALYSIS.md)
- 命令与输入依赖：[docs/COMMANDS.md](../../../docs/COMMANDS.md)

## 1. 四阶段目录地图

产物根为 `analysis/`（由 `ANALYSIS_DIR` 决定，相对当前工作目录）。本包写出的全部路径：

```
source/  (只读 Snapshot，不在本包内生成)
   ↓ analyze
analysis/
├── inventory/                      # Stage 01 · Inventory（机器事实 · 资产盘点）
│   ├── workspaces.json  files.json  tables.json  columns.json
│   └── summary.md                  # 资产盘点报告（10 节，不含资格 / 规则统计）
├── scope/                          # M2.1 Scope · 分析资格评估（消费 Inventory 全量资产）
│   ├── inputs/
│   │   ├── sql-candidates.json     # SQL 资格清单（互斥且合计 = 登记文件）
│   │   └── excluded-tasks.json
│   ├── review-tasks.json           # 弱证据待确认（非删除清单）
│   ├── summary.json  summary.md    # Scope Summary（机器统计 + 人读报告）
│   └── findings/                   # 规则发现（预留；当前未实现，不生成产物）
├── evidence/                       # Stage 02–05 · Evidence（技术证据）
│   ├── layer/       assessments.json + summary.md     # 02 Layer Assessment
│   ├── sql/         statements.json  table-references.json
│   │                parse-errors.json                 # 03 SQL 专属解析错误
│   ├── lineage/     table-lineage.json  core-table-candidates.json + summary.md  # 04
│   ├── profiling/   tables.json  columns.json + summary.md                       # 05
│   └── errors.json                 # 跨阶段技术错误账本（Stage 01–05）
├── understanding/                  # Stage 06–11 · Understanding（业务/模型候选）
│   ├── business/    quality-assessment.json  objects*.json  process*.json
│   │                grain*.json  summary.md  object-graph.md  ...
│   └── modeling/    fact-*.json  dimension-*.json  model-*.json
│                    model-summary.md  model-review-checklist.md  ...
├── review/                         # Stage 12–14 · Review（评审输入 + 人工台账）
│   ├── current-state-model.json  current-state-model-tables.json
│   ├── current-state-findings.json  current-state-problems.json
│   ├── current-state-problem-evidence.json
│   ├── current-state-model-summary.md              # M3.6 报告
│   ├── current-state-problem-summary.md            # M3.6 v2 报告
│   ├── current-state-review-checklist.md           # Finding 裁决台账
│   └── current-state-problem-review-checklist.md   # Problem 裁决台账
└── summary.md                      # 根入口报告（12 节，纯磁盘重建）
```

要点：

- **一个 Stage 对应一个子目录**，不出现跨阶段共用文件；旧布局残留由重跑时的 legacy 清理逻辑删除（`pipeline.PRODUCTION_DIRS` / `LEGACY_PRODUCTION_FILES`）。
- **Inventory 与 Scope 职责分离**：`inventory/` 只放资产索引与盘点报告（`summary.md` 10 节，只报事实——文件元数据完整性、内容快照状态、缺失 Node ID，不含资格判定与规则统计）；资格判定清单（`inputs/`）、待确认清单与 Scope Summary（`summary.json` / `summary.md` 9 节）统一归属 `scope/`。Scope 只消费 Inventory 全量资产，不反向修改或删减；`build_inventory_summary()` 不接收 `FileScope`。
- **`scope/inputs/` 与 `scope/findings/` 的区别**：`inputs/` 是后续分析的输入契约（候选 / 排除，互斥且合计覆盖评估集合）；`findings/` 预留给规则发现（对象级问题、规则命中事实、审核状态），当前规则只做资格分类与审核标记，未实现发现产物，Summary 如实标注 `status = not_implemented`、count = 0。
- **根 `summary.md` 不计算任何指标**：由 `reports.render_analysis_summary(SummaryContext(...))` 纯渲染，输入全部来自当前阶段刚产出的结果。上游阶段没跑时该段为空输入（血缘边渲染为 0）；Evidence stage 与全量 `analyze` 传入同一份真实 Layer / SQL / Lineage / Profiling 结果，因此两者根 `summary.md` 逐字节一致。旧 `Summary.md` 已废弃。本仓库没有 analysis 级 `manifest.json`（`source/manifest.json` 属于 Snapshot）。
- `errors.json` 与 `parse-errors.json` 是**两个独立文件**，见第 4 节。

## 2. 模块导览

| 模块 | 职责 |
| --- | --- |
| `pipeline.py` | `AnalysisPipeline` 编排四阶段：`run_stage_inventory` → `run_stage_evidence` → `run_stage_understanding` → `run_stage_review`（清场 → Inventory → Layer → SQL → Lineage → Profiling → 业务/模型候选 → 评审 → 账本 → 报告）。`run()` 与 `run_stage_evidence()` 共用 `_write_reports()`，保证 Evidence 报告契约一致 |
| `snapshot.py` | `SnapshotReader` 只读访问 `source/`；raw JSON 是 Source of Truth，index 只用于导航 |
| `inventory/` | Stage 01：Workspace / File / Table / Column 清单与盘点报告；不承载资格清单或 Scope 统计 |
| `scope/` | 分析资格评估的唯一实现（`rules.py` 配置加载与校验、`decision.py` 判定、`content.py` Content 状态、`outputs.py` 产物路径常量与清单 / Summary payload）；产物写入 `analysis/scope/`（清单在 `inputs/`，规则发现在 `findings/` 预留）；`inventory/scope.py` 只是兼容层 re-export，新代码请直接导入 `data_platform_analysis.analysis.scope` |
| `evidence/layer/` | Stage 02：按 `config/layer-rules.yaml` 判定 `candidate_layer`（唯一层级来源，见 ADR-0003） |
| `evidence/sql/` | Stage 03：语句切分 → 归一化 → AST 解析（`fallback.py` CTAS token scanner 承接 unsupported）；输入由 `FileScope.sql_eligible_files()` 统一给出，不重复过滤 |
| `evidence/lineage/` | Stage 04：表引用归并与血缘边；层级标注直接引用 Stage 02 结果 |
| `evidence/profiling/` | Stage 05：元数据画像，`profile_status` 恒为 `metadata_only`，不伪造行级统计 |
| `understanding/business/` | Stage 06–10：业务理解（quality / objects / processes / grain） |
| `understanding/modeling/` | Stage 11：当前形态业务模型 |
| `review/` | Stage 12–14：Findings → Problem Candidates → Evidence，同一次 `analyze --stage review` 原子写出 |
| `reports.py` | 纯渲染：所有数字来自既有产物，不推断新结论 |
| `errors.py` | 错误分类、`ErrorLedger` 与账本路径常量 |
| `models.py` / `naming.py` | 记录模型（稳定身份 + 来源引用）；表名归一化只产生 Candidate |

## 3. 入口与重跑顺序

| `analyze` | Stage 01–14 | 先清空 `inventory/`、`scope/`、`evidence/`、`understanding/`、`review/` 与根 `summary.md`（含旧布局残留）再全量重建；清场时原样保留 5 份含人工回填列的 checklist（见下） |
| `analyze --stage inventory` | Stage 01 | **同样先清空上述全部目录**，然后只重建 `inventory/`（5 个）+ `scope/`（5 个）+ 根 `summary.md`；跑完后 `evidence/`、`understanding/`、`review/` 已被删除（checklist 除外），支持 `--workspace` |
| `analyze --stage evidence` | Stage 02–05 | **同样先清空上述全部目录**，然后重建 `inventory/` + `scope/` + `evidence/` + 根 `summary.md`（共 23 个文件，与全量 `analyze` 的对应产物逐字节一致）；跑完后 `understanding/`、`review/` 已被删除（checklist 除外）；不支持 `--workspace` |
| `analyze --stage understanding` | Stage 06–11 | **不清场**，只重建 `understanding/`；`evidence/layer/assessments.json` 缺失时先自动补跑 `run_stage_evidence()`（含清场），不支持 `--workspace` |
| `analyze --stage review` | Stage 12–14 | **不清场**，重建 `understanding/`（review 依赖它，总是先重跑）与 `review/`，读两份 checklist 的 `human_*` 列并保留，不写根 `summary.md`；evidence 缺失时同上自动补跑，不支持 `--workspace` |

人工回填保护：`pipeline.PRESERVED_CHECKLIST_FILES` 登记了 5 份含人工列的 checklist
（`review/current-state-review-checklist.md`、`review/current-state-problem-review-checklist.md`、
`understanding/business/process-review-checklist.md`、`understanding/business/grain-review-checklist.md`、
`understanding/modeling/model-review-checklist.md`）。全量 / `--stage inventory` / `--stage evidence`
清场时它们被原样快照并恢复，随后各阶段重算机器列、经 carry-over 合并人工列——
人工回填不再因清场丢失。`understanding/business/review-checklist.md`（M3.1）无 carry-over，
重跑即清零，不在保护之列。

推荐顺序（上游产物缺失时按此补齐）：
```
analyze
```


## 4. 错误模型（`errors.py`）

- **Fatal Error**：`source/` 不存在、无法确定 Workspace identity、`--workspace` 不在 Snapshot 中、Layer 规则配置非法、Analysis Scope Rules 配置非法（缺失 / 字段非法 / 未知字段（如已删除的 `cleanup_candidate`）/ `content_check` 非法 / 必需规则组为空）→ 立即非零退出，不回退默认规则。
- **Recoverable Error**：单个 index/raw 损坏、单条 SQL 解析失败、content 缺失、单表 metadata 缺失 → 记录后继续，最终写入 **`analysis/evidence/errors.json`**（常量 `ERROR_LEDGER_RELATIVE_PATH`）。
  - 账本 schema 固定为 `{"count", "errors"}`，`stage ∈ {inventory, sql, lineage, profiling}`，一次运行一份，是跨 Stage 的技术运行错误总账。
  - SQL 解析失败**同时**写入 `analysis/evidence/sql/parse-errors.json`：那是 SQL 专属的解析产物（无 `stage` 字段），与账本不合并。
- 原则：一个对象失败 → 记录 → 继续；**不允许为了 errors=0 吞错**。

## 5. Review 口径（Stage 12–15）

- 机器只能产出 `candidate` / `review_required`（另有 `needs_discussion` / `rejected`），**`confirmed` 恒为 0**，除非人工回填清单后重跑 `analyze --stage review`。
- 每个 Problem 必须能回指 ≥1 条 evidence，evidence 再回指 finding；三者 ID 互不复用（Finding ≠ Problem ≠ Confirmed）。
- 人工只改两份 checklist 的 `human_status` / `human_name` / `note` 三列（全仓库唯一被人工直接编辑的文件），改完重跑 `analyze --stage review` 读回。
- 浏览器侧 `localStorage["m36-human-adjudication"]` 不回写产物，须导出后回填清单。

## 6. 验证

```bash
uv run -m pytest -q          # 本包测试
uv run -m ruff check src tests
uv run -m mypy
cd workbench && npm test               # 前端只读渲染测试
```

当前基线：pytest 506 passed、ruff / format / mypy 全绿；workbench 38 passed · 10 failed（golden 期望值早于当前 source 快照，待刷新，见收口报告）；真实数据下 `analyze` 产出 table 3724 / statement 1917 / edge 3384 / finding 4425 / problem 1186 / error 0。

## 7. 相关约定

- 两套编号：M\*（Milestone，永不重命名）与 NN（Stage，只追加），见 [docs/STAGE_INDEX.md §1](../../../docs/STAGE_INDEX.md)。
- 领域词汇与 ADR：仓库根 [CONTEXT.md](../../../CONTEXT.md)、[docs/adr/](../../../docs/adr/)。
- `source/`、`analysis/`、`output/` 均 gitignore；本文件随源码入库。

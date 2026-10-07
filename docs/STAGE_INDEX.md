# 阶段索引（Stage Index）

从 Snapshot 到 M4 的**阶段总账**：每个 Stage 对应的 Milestone、命令、代码、产物目录与文档。回答三个问题：*我该按什么顺序走 / 这个产物从哪来 / 这个阶段归谁*。

- 逐阶段的输入依赖与可复制命令：[COMMANDS.md → Current-State Evidence Execution Chain](COMMANDS.md#current-state-evidence-execution-chain)
- 逐字段的证据链与人工动作：[CURRENT_STATE_EVIDENCE_MAP.md](CURRENT_STATE_EVIDENCE_MAP.md)
- 人工裁决实操：[M36_HUMAN_ADJUDICATION_GUIDE.md](M36_HUMAN_ADJUDICATION_GUIDE.md)

约定：

- **代码**列省略公共前缀 `src/data_platform_analysis/`。
- **产物**列相对 `analysis/`（由 `ANALYSIS_DIR` 决定，默认 `analysis`）；采集阶段写 `source/`。
- `source/`、`analysis/`、`output/` 均被 gitignore（各保留 `.gitkeep`），本文件是入库文档，不受影响。

## 1. 两套编号：M*（Milestone）与 NN（Stage）

| | M* Milestone | NN Stage |
| --- | --- | --- |
| 分组什么 | 研发 / 架构里程碑（"我们做了哪一批工作"） | 执行与阅读顺序（"我该先看什么、后看什么"） |
| 现存引用 | **1229 处**（src 453、README + docs + tests + workbench 776） | 仅本文档与 [COMMANDS.md](COMMANDS.md) 阶段矩阵 |
| 规则 | **永不重命名、永不回收** | 只追加、不回改；可预留号 |

- 映射关系：一个 Milestone ↔ 1..N 个 Stage（`M2.1 → 01`，`M3.6 → 12/13/14`）。
- 历史教训：M2 子编号曾在 2026-10-02 重排过一次（Layer 原 M2.5 → M2.2），因此 Milestone 保持只读，Stage 才是可演进的那一层。
- 两侧互不改名：不因引入 Stage 而改文档里的 M 编号，也不因保留 M 编号而给源码加数字前缀。

## 2. Stage Registry

状态：**已实现** / **规划**（规划项不建目录、不建文件）。

| Stage | 名称 | Milestone | 命令 | 产物目录（相对 `analysis/`，采集为 `source/`） | 代码 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| **00** | Raw Snapshot | M1 | `export` / `dataworks` / `maxcompute` / `summary` | `dataworks/**`、`maxcompute/**`、`manifest.json`、`Summary.md` | `export.py`、`dataworks.py`、`maxcompute.py`、`summary.py` | 已实现 |
| **01** | Inventory | M2.1 | `analyze` | `inventory/` | `analysis/pipeline.py` + `analysis/inventory/` | 已实现 |
| **02** | Layer Assessment | M2.2 | `analyze` 或 `analyze-layer` | `layer/` | `analysis/layer/layer_assessment.py` + `config/layer-rules.yaml` | 已实现 |
| **03** | SQL Analysis | M2.3 | `analyze` | `sql/` | `analysis/sql/` | 已实现 |
| **04** | Lineage | M2.4 | `analyze` | `lineage/` | `analysis/lineage/` | 已实现 |
| **05** | Profiling | M2.5 | `analyze` | `profiling/` | `analysis/profiling/` | 已实现 |
| **06** | Business Understanding | M3 | `analyze-business` | `business/` | `analysis/business/understanding.py` + `config/business-rules.yaml` | 已实现 |
| **07** | Business Quality | M3.1 | `analyze-business-quality` | `business/` | `analysis/business/quality.py` | 已实现 |
| **08** | Business Objects | M3.2 | `analyze-business-objects` | `business/` | `analysis/business/objects.py` | 已实现 |
| **09** | Business Processes | M3.3 | `analyze-business-processes` | `business/` | `analysis/business/processes.py` + `config/process-rules.yaml` | 已实现 |
| **10** | Business Grain | M3.4 | `analyze-business-grain` | `business/` | `analysis/business/grain.py` | 已实现 |
| **11** | Business Model | M3.5 | `analyze-business-model` | `model/` | `analysis/model/business_model.py` | 已实现 |
| **12** | Current-State Findings | M3.6a | `analyze-current-state-model` | `review/` | `analysis/review/findings.py` | 已实现 |
| **13** | Current-State Problems | M3.6b | `analyze-current-state-model` | `review/` | `analysis/review/problems.py` | 已实现 |
| **14** | Current-State Evidence | M3.6b | `analyze-current-state-model`（**同一次运行，无独立入口**） | `review/` | `analysis/review/problems.py`（与 13 原子写出） | 已实现 |
| **15** | Human Adjudication | — | **无命令**：编辑两份 checklist → 重跑 12/13 | 清单 `human_*` 三列 + `localStorage["m36-human-adjudication"]` | 无 Python 写入方 | 已实现（confirmed = 0） |
| **16** | Confirmed Current-State Evidence | — | 未实现 | **不存在** | — | 规划 |
| **17** | Refactoring Evidence | — | 未实现 | **不存在** | — | 规划 |
| **18** | Target DWD | M4+ | 未实现 | **不存在** | — | 规划 |
| **19** | Target DWS | M4+ | 未实现 | **不存在** | — | 规划 |
| **20** | Target Semantic Layer | M4+ | 未实现 | **不存在** | — | 规划 |

目录拆分已随 Phase 2 落地：Stage 11 → `analysis/model/`、Stage 12–14 → `analysis/review/`，产物目录与源码模块（`analysis/model/`、`analysis/review/`）同构。旧布局残留在 `business/` 的 18 个文件由重跑对应命令时的 legacy 清理逻辑（`io_utils.relocate_legacy_artifacts`）删除 / 搬迁，`business/` 最终只含 Stage 06–10。

### 2.1 Stage 判定规则（用于未来追加）

一个 Stage 成立当且仅当满足**产物组独立 + 下游消费者独立 + 人工评审动作独立**三者；**不要求有独立命令**：

- Stage 01–05 共享一条 `analyze`，但产物与消费者各自独立。
- Stage 12/13/14 共享一条 `analyze-current-state-model`，且 13 与 14 是同一次运行的原子写出——Registry 的"命令"列如实暴露这一点，不假装它们有独立入口。
- 辅助文件（`manifest.json`、`*-index.json`、`Summary.md`、`summary.md`、`errors.json`、`parse-errors.json`）只索引 / 汇总 / 记账，**不授予 Stage 号**。

### 2.2 阅读顺序（新人 30 分钟路径）

1. [README.md](../README.md) §1 项目目标、§4 命令
2. **本文档 §2 总表**（知道自己在 Stage 几）
3. [COMMANDS.md](COMMANDS.md) 执行链（每个 Stage 的输入 / 命令 / 输出 / 依赖）
4. [M36_PROBLEM_ASSESSMENT.md](M36_PROBLEM_ASSESSMENT.md)（方法论）→ [M36_HUMAN_ADJUDICATION_GUIDE.md](M36_HUMAN_ADJUDICATION_GUIDE.md)（实操）
5. [CURRENT_STATE_EVIDENCE_MAP.md](CURRENT_STATE_EVIDENCE_MAP.md)（逐字段证据链）
6. [CODE_LOGIC_ANALYSIS.md](CODE_LOGIC_ANALYSIS.md)（代码与阶段逻辑，工程向）

## 3. 产物分类（Fact / 规则推导 / 候选 / 回填 / 辅助）

| 类别 | 谁能写 | 典型产物 | 判据 |
| --- | --- | --- | --- |
| **机器事实 Fact** | 仅机器 | `source/**`、`inventory/*.json`、`sql/{statements,table-references}.json`、`profiling/*.json`、`errors.json` | 可回指原始位置；`profile_status` 恒为 `metadata_only` |
| **规则推导** | 仅机器（确定性规则） | `layer/assessments.json`、`lineage/{table-lineage,core-table-candidates}.json` | 规则 / 引用归并，`status = MATCH/UNKNOWN/CONFLICT`，不含业务判断 |
| **机器候选 Candidate** | 仅机器 | `business/*.json`（Stage 06–10）、`model/*.json`（Stage 11）、`review/*.json`（Stage 12–13） | `status ∈ {candidate, review_required, needs_discussion, rejected}`；**confirmed 只能由人工带来** |
| **证据 Evidence** | 仅机器 | `current-state-problem-evidence.json`（每组 ≤ 50 行截断） | 由 problem 聚合时生成，不独立重算 |
| **回填工件（双向）** | 机器写列 + **人写 `human_*` 三列** + 机器重跑读回 | 6 份 `*-review-checklist.md` | 全仓库**唯一被人工直接编辑**的文件；改后重跑对应命令 |
| **人工裁决数据** | 仅人 | 清单 `human_status` / `human_name` / `note`；`localStorage["m36-human-adjudication"]` | 浏览器侧数据不回写产物，须导出后回填清单 |
| **最终报告 / 辅助** | 机器 | 生成式 Markdown 共 13 份（12 份阶段报告：`inventory/layer/lineage/profiling/business` 的 `summary.md`、`quality-assessment.md`、`object-graph.md`、`process/grain/model-summary.md`、`current-state-{model,problem}-summary.md`，加 `analysis/Summary.md`）、`manifest.json`、`*-index.json`、`errors.json` | 生成式、非 Source of Truth、不授予 Stage 号 |

### 3.1 Candidate → Confirmed 状态机（`models.py` 强制）

```text
机器（唯一能写 status）            人（唯一能给 human_status）      重跑后（确定性映射）
status = candidate          →     confirmed            →   status = confirmed,   human_validated = true
status = review_required    →     rejected             →   status = rejected,    human_validated = false
（其余一律保持 candidate）          needs_review /
                                   needs_discussion     →   needs_discussion → review_required（problem 侧）
                                                          无法识别的取值 → 按未回填处理（warning，不猜测）
```

**禁止表达**：

- `current-state-findings.json`、`current-state-problems.json` 是**候选**，文件名与字段不得出现 `confirmed` / `final` / `authoritative`。
- `classification = confirmed_conflict` 是**证据分级名**（同组候选键互不包含），**不是**"人工已确认"。
- `confirmed-*` 类产物只能属于 Stage 16，且必须由 `status = confirmed` **派生生成**，不可手工编辑。

## 4. 文档地图

| 类别 | 规则 | 文件 |
| --- | --- | --- |
| **Analysis Documentation** | 手写、面向"分析读什么"；**新增才编号**，编号 = Stage 号；不拆成逐 Stage 空壳文档（`analysis/*-summary.md` 已是逐阶段生成报告） | [CURRENT_STATE_EVIDENCE_MAP.md](CURRENT_STATE_EVIDENCE_MAP.md)（01–14 逐阶段说明）、[EVIDENCE_LAYER_AUDIT_CHECKLIST.md](EVIDENCE_LAYER_AUDIT_CHECKLIST.md)、[EVIDENCE_LAYER_FREEZE_REPORT.md](EVIDENCE_LAYER_FREEZE_REPORT.md)、[SQL_ANALYSIS_LIMITATION.md](SQL_ANALYSIS_LIMITATION.md)、[M36_PROBLEM_ASSESSMENT.md](M36_PROBLEM_ASSESSMENT.md) |
| **User Guide** | 按"谁在用"命名，不按 Stage 编号 | [COMMANDS.md](COMMANDS.md)、[M36_HUMAN_ADJUDICATION_GUIDE.md](M36_HUMAN_ADJUDICATION_GUIDE.md)（= Stage 15 操作指南）、[../README.md](../README.md) |
| **Engineering Documentation** | **永不编号** | [CODE_LOGIC_ANALYSIS.md](CODE_LOGIC_ANALYSIS.md)、[../CONTEXT.md](../CONTEXT.md)、[../AGENTS.md](../AGENTS.md)、本文件 |
| **Architecture / ADR** | 序号制，与 Stage 号无冲突 | [adr/](adr/)、[agents/](agents/) |

- 本文档（Stage Registry + 读序 + 产物分类 + 命名规范）是**唯一总索引**；逐 Stage 不再新增独立 md。
- 相对链接共 13 条，改文档文件名会断链——`M36_*`、`COMMANDS.md`、`CURRENT_STATE_EVIDENCE_MAP.md` 保持现名。

## 5. 产物命名规范

### 5.1 目录

- **产物目录 = 生产它的源码模块**：`inventory/`、`layer/`、`sql/`、`lineage/`、`profiling/`、`business/`（06–10）、`model/`（11）、`review/`（12–14）全部满足；Stage 15 无产物目录（回填工件与所属阶段同目录）。
- **不给现有 59 个产物加 `NN-` 前缀**：全仓字面 `analysis/` 引用 540 处（src 252 / tests 93 / workbench 24 / docs 164 / README 7），换不到顺序信息（`analysis/` 本身被 gitignore，真正入口是 §2.2 的阅读链）。
- **新增阶段**：新目录可带 Stage 号（如 `analysis/16-confirmed/`），**旧文件不补号**——避免混合风格蔓延。

### 5.2 文件名

```text
<限定词>-<对象>.<ext>

后缀约定（保持现状，新增照此）：
  *.json                   机器产物
  *-summary.md             阶段报告（生成、只读）
  *-review-checklist.md    回填工件（机器写 + 人写 + 机器读，与阶段产物同目录）
  *-assessment.*           规则 / 质量评估
  *-candidates.* / *-signals.* / *-relationships.* / *-matrix.*   候选层

禁区：
  ① 非 Stage 16 的文件名不得含 confirmed / final / authoritative
  ② manifest / index / summary / errors 不参与 Stage 编号
  ③ 同一 Stage 的回填工件必须与该 Stage 产物同目录（carryover 读写就近）
  ④ Python 源码 / 测试 / 文档文件名不加数字前缀
```

### 5.3 明确不做的三件事

1. 不给 `src/` 源码加数字前缀（按职责组织是正确设计）。
2. 不给现有 59 个产物 basename 加 `NN-`（540 处引用，零算法收益）。
3. 不预建 Stage 16–20 的目录或空文件（会把规划伪装成已实现）。

## 6. 已知不一致与待办

| 项 | 现状 | 归属 |
| --- | --- | --- |
| `output/` 目录无任何代码写入，README §6 标注"导出产物" | 文档与实现不符 | 待确认是否删除 |
| Stage 16 / 17 无产物 | `confirmed = 0` | 待 M3.6 人工裁决产生数据后设计派生产物 |

已修正（本文件随附的文档勘误）：README §1 原写「M3 业务候选，M3.1 ～ M3.5」（Domain / Object 实为 M3）→ 改为「M3 ～ M3.5」；[CODE_LOGIC_ANALYSIS.md](CODE_LOGIC_ANALYSIS.md) §3.9 原写「输入（11 个）」但实际列举 12 个 → 改为 12（与 [COMMANDS.md](COMMANDS.md) 输入依赖表一致）。

已随 Phase 2 关闭：① `model-review-findings.json` → `current-state-findings.json`（M3.6 九件套命名统一，src / tests / workbench / docs 全量引用已迁移）；② `business/` 混装 06–14 → 拆出 `model/`（Stage 11）与 `review/`（Stage 12–14），`business/` 只留 Stage 06–10。

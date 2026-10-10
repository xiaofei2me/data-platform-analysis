# data-platform-analysis

基于 Alibaba Cloud DataWorks + MaxCompute 的数据平台现状分析项目。

## 1. 项目目标

本项目用于对现有数据仓库进行反向分析，为后续 DWS 和 Semantic Layer 设计提供数据基础。

当前整体目标：

```
DataWorks + MaxCompute
        ↓
    Collection（采集）
        ↓
   Raw Snapshot（时点快照）
        ↓
    数据仓库现状分析（Analysis）
        ↓
       DWS 设计
        ↓
  Semantic Layer 设计
```

**Collection** 阶段负责：

- DataWorks 文件采集（ListFiles / GetFile）
- MaxCompute 表元数据采集（ListTables / GetTable）
- Raw 响应与 Content 原样保存为本地 Snapshot
- Snapshot 索引（files-index / tables-index）与重复采集清理

**Analysis** 阶段（`analyze` 子命令与 4 种 `--stage` 变体，只读已有 Snapshot / 上一阶段产物，写 `analysis/`）按 Milestone 划分已实现内容：M2 证据链（inventory → layer → sql → lineage → profiling）、M3 业务候选（Domain / Object / Quality / Process / Grain / Fact-Dimension Candidate，M3 ～ M3.5）与 M3.6 Current-State Model Review（当前形态分类 + 结构化 finding + 人工清单），以及 M3.6 v2 Problem Assessment（finding 聚合成 problem candidate + 证据 / 影响 / 根因 / 重构理由 + 人工清单），只产出候选、证据与评审发现，不产出结论模型、不设计 Target DWD，详见 [docs/CODE_LOGIC_ANALYSIS.md](docs/CODE_LOGIC_ANALYSIS.md)。

### Analysis 四阶段

按阶段（Stage 01 ～ 14）划分，与 `--stage` 一一对应，阶段职责以 [src/data_platform_analysis/analysis/README.md](src/data_platform_analysis/analysis/README.md) 为准：

```text
Inventory
    ↓
Evidence
    ↓
Understanding
    ↓
Review
```

对应职责：

```text
Inventory
    统一盘点数据资产和元数据

Evidence
    基于 SQL、Lineage、Profiling、Layer 等证据进行分析

Understanding
    从证据进一步形成业务理解和建模理解

Review
    汇总当前问题、证据、模型判断，并进入人工审查
```

要理解 `M3.6 → M3.6 v2 → 人工裁决 → 重构证据 → M4` 的方法论（Finding ≠ Problem、13 类 Problem Taxonomy、四条原则、裁决优先级、重构证据模板），见 [docs/M36_PROBLEM_ASSESSMENT.md](docs/M36_PROBLEM_ASSESSMENT.md)——人工裁决从那份文档开始。

要实际组织人工裁决（数据团队 / 业务专家视角：看哪些文件、按什么顺序、每类 Problem 怎么问、什么时候 confirmed / rejected、一周怎么排），见 [docs/M36_HUMAN_ADJUDICATION_GUIDE.md](docs/M36_HUMAN_ADJUDICATION_GUIDE.md)——干活从那份文档开始。

**不知道从哪读起**：先看 [docs/STAGE_INDEX.md](docs/STAGE_INDEX.md)——Stage 00 ～ 20 与 Milestone（M1 / M2.x / M3.x）的映射、每阶段的命令 / 代码 / 产物 / 文档、产物四分类（事实 / 规则推导 / 候选 / 回填）与推荐阅读顺序。

仍明确不负责（边界约束）：

- Task Dependency（任务级依赖）分析
- ODS / DWD / ADS 自动分类、DWS Candidate、Target DWD Design
- Semantic Layer
- LLM / AI Agent / MCP
- QuickBI
- 数据迁移

## 2. 当前采集范围

### DataWorks

```
DataWorks Workspace
        ↓  ListFiles
      File 列表
        ↓  GetFile（逐个）
Raw File Detail（完整响应）
   +
File Content（SQL / Script / JSON …）
        ↓
   files-index.json
```

采集内容：

- Workspace 列表（`WORKSPACES` 配置）
- File 列表（分页合并，支持 `DATAWORKS_USE_TYPES` 过滤）
- 单个 File 的完整 Raw GetFile 响应
- File Content（按 `FileType` 决定扩展名）
- `files-index.json`（导航信息 + `failed_files`）

### MaxCompute

```
DataWorks Workspace.name
        ↓
  MaxCompute Project
        ↓  ListTables
      Table 列表
        ↓  GetTable（逐个）
   Table Metadata
        ↓
   tables-index.json
```

采集内容：

- Workspace 与 MaxCompute Project 的映射（`Workspace.name` 即 Project 名称）
- 表列表与单表完整元数据（注释、字段、分区字段、大小、生命周期、创建/修改时间等）
- `tables-index.json`（导航信息 + `failed_tables`）
- 默认不采集实际分区实例（`MAXCOMPUTE_INCLUDE_PARTITIONS=false`）

## 3. Snapshot 布局

```
source/
├── manifest.json                              # 仅全量 export 写入
├── Summary.md                                 # 人工阅读的 Snapshot 目录说明（summary 子命令生成，非 Source of Truth）
├── dataworks/
│   ├── workspaces-index.json                  # Workspace 注册表（upsert）
│   └── workspaces/<workspace_id>/
│       ├── files-index.json
│       ├── files/<file_id>__<file_name>.json  # Raw GetFile 响应
│       └── content/<file_id>__<file_name>.<ext>
└── maxcompute/
    └── workspaces/<workspace_id>/
        ├── tables-index.json
        └── tables/<table_name>.json           # Table Metadata
```

- 目录使用稳定的 Workspace `id`（不是可变的 `name`）。
- Raw 文件是唯一真相源，index 只承担导航。

## 4. 命令

一次性准备（每个新环境执行一次）：

```bash
uv sync                              # 安装依赖
cp .env.example .env                 # 配置模板，需填写 WORKSPACES 与阿里云凭证
uv run data-platform-analysis config # 核对生效配置（不含密钥）
```

```bash
# 全部 Workspace：DataWorks + MaxCompute
uv run data-platform-analysis export

# 单个 Workspace
uv run data-platform-analysis export --workspace 123456

# 只采集 DataWorks / 只采集 MaxCompute
uv run data-platform-analysis dataworks
uv run data-platform-analysis maxcompute

# 限制模式：每个 Workspace 最多 N 个对象
uv run data-platform-analysis dataworks --limit 10
uv run data-platform-analysis maxcompute --limit 10
uv run data-platform-analysis export --limit 10

# 查看当前生效的非敏感配置
uv run data-platform-analysis config

# 重新生成 source/Summary.md（人工阅读的 Snapshot 目录说明）
uv run data-platform-analysis summary

# 分析链（只读已有 Snapshot / 上一阶段产物，写 `analysis/`）

# 一次性完整分析：
uv run data-platform-analysis analyze

# 分阶段执行（不推荐，仅用于重跑单阶段）：
uv run data-platform-analysis analyze --stage inventory      # Stage 01 (Inventory)
uv run data-platform-analysis analyze --stage evidence       # Stage 02-05 (Evidence)
uv run data-platform-analysis analyze --stage understanding  # Stage 06-11 (Understanding)
uv run data-platform-analysis analyze --stage review         # Stage 12-14 (Review)

# 重跑前注意：--stage inventory / --stage evidence 会先清空 analysis/
# （含 understanding/、review/；5 份人工回填清单经快照恢复不丢失）；
# --stage understanding / --stage review 不清场，但 evidence/ 缺失时会自动先补跑 evidence。

# M3.6 评审（一次性完整分析或单独执行 review 阶段）：
uv run data-platform-analysis analyze --stage review
```

Analysis 输出目录（`ANALYSIS_DIR` 默认为 `analysis/`，gitignore；完整契约见 [src/data_platform_analysis/analysis/README.md](src/data_platform_analysis/analysis/README.md)）：

```text
analysis/
├── summary.md                     # 根入口报告（12 节）
├── inventory/                     # Inventory · Stage 01（资产索引）
│   └── workspaces / files / tables / columns.json + summary.md（10 节盘点报告）
├── scope/                         # Scope · M2.1 资格评估（消费 Inventory 全量资产）
│   ├── inputs/                    #   sql-candidates / excluded-tasks.json（互斥且合计 = 登记文件）
│   ├── review-tasks.json          #   弱证据待确认（非删除清单）
│   ├── summary.json + summary.md  #   Scope Summary（机器统计 + 人读报告）
│   └── findings/                  #   规则发现预留（当前未实现，不生成产物）
├── evidence/                      # Evidence · Stage 02–05
│   ├── errors.json                # 正式 Error Ledger（跨阶段错误账本）
│   ├── layer/                     #   02 层级判定
│   ├── sql/                       #   03 语句 / 表引用 / 解析错误
│   ├── lineage/                   #   04 表引用与血缘
│   └── profiling/                 #   05 元数据画像
├── understanding/                 # Understanding · Stage 06–11
│   ├── business/                  #   06–10 业务理解（quality / objects / processes / grain）
│   └── modeling/                  #   11 Fact / Dimension 候选
└── review/                        # Review · Stage 12–14（评审产物 + 两份人工回填清单）
```

已废弃的旧产物 `analysis/errors.json`、`analysis/Summary.md` 在重跑时由 `pipeline._reset_outputs()` 删除；`analysis/business/` 等旧布局残留由各阶段的 `io_utils.relocate_legacy_artifacts()` 清理或搬迁（回填清单会保留人工列）。当前实现不再写出扁平的 `layer/`、`sql/`、`lineage/`、`profiling/`、`business/`、`model/` 目录。

退出码：

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部成功 |
| 1 | 存在 Workspace / 文件 / 表级失败，或命令执行失败 |
| 130 | 用户中断 |

详细参数说明见 [docs/COMMANDS.md](docs/COMMANDS.md)；从采集到 M3.6 人工裁决 / Workbench 的完整阶段链（每阶段输入、命令、输出、依赖与推荐执行顺序）见 [Current-State Evidence Execution Chain](docs/COMMANDS.md#current-state-evidence-execution-chain)。

## 5. Cleanup 安全规则

```
limit is None     → 完整集合 → 允许 Cleanup
limit is not None → 部分集合 → 禁止 Cleanup（Cleanup = SKIP）
```

- 成功的 `ListFiles` / `ListTables` 是当前对象集合的权威来源，据此清理远端已删除的本地 Snapshot。
- 单个对象（File / Table）获取失败：保留旧 Snapshot，成功对象正常更新。
- 整个 List API 失败：不执行 Cleanup，不覆盖旧 index。
- 不提供 `--no-cleanup`，limit 模式下 Cleanup 一律跳过。

## 6. 项目结构

```text
data-platform-analysis/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── config/                      # Analysis 规则配置（analysis-scope-rules / layer-rules / business-rules / process-rules）
├── CONTEXT.md                   # 领域词汇与 ADR 索引
│
├── src/
│   └── data_platform_analysis/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py              # CLI 入口与子命令
│       ├── config.py           # WORKSPACES 等配置与校验
│       ├── logging_utils.py    # Rich 日志
│       ├── io_utils.py         # 文件读写
│       ├── dataworks.py        # DataWorks OpenAPI 客户端与字段提取
│       ├── dataworks_types.py  # DataWorks FileType 注册表（说明见 docs/DATAWORKS_FILE_TYPE_REGISTRY.md）
│       ├── maxcompute.py       # MaxCompute 只读元数据客户端
│       ├── export.py           # Snapshot 导出与 Cleanup
│       ├── summary.py          # 生成 source/Summary.md（人工阅读的目录说明）
│       └── analysis/           # 分析链源码（与根目录 analysis/ 产物目录同名不同物，四阶段目录同构）
│           ├── README.md       # 包内说明（四阶段目录地图 / 模块导览 / 入口与重跑顺序 / 错误模型）
│           ├── pipeline.py     # 四阶段编排（inventory → evidence → understanding → review）
│           ├── inventory/      # Stage 01 资产清单
│           ├── scope/          # M2.1 资格评估（rules / decision / content / outputs）
│           ├── evidence/       # Stage 02–05 技术证据
│           │   ├── layer/      #   Stage 02 层级判定（唯一口径）
│           │   ├── sql/        #   Stage 03 SQL 解析 / 归一化 / 方言 / CTAS 兜底
│           │   ├── lineage/    #   Stage 04 表引用与血缘
│           │   └── profiling/  #   Stage 05 元数据画像
│           ├── understanding/  # Stage 06–11 业务 / 模型候选
│           │   ├── business/   #   Stage 06–10 业务理解（Understand → Object → Process → Grain）
│           │   └── modeling/   #   Stage 11 Fact / Dimension 候选
│           ├── review/         # Stage 12–14 Finding / Current-State Problem 评审
│           ├── models.py       # 数据结构（analysis = 如何分析，models = 数据结构是什么）
│           ├── reports.py      # JSON / Markdown 报告渲染
│           ├── snapshot.py     # Snapshot 只读访问
│           ├── errors.py       # 错误账本
│           └── naming.py       # 表名 / 引用工具
│
├── source/                     # Snapshot 输出目录（gitignore）
├── analysis/                   # Analysis 产物（inventory / scope / evidence / understanding / review，gitignore）
├── output/                     # 导出产物
│
├── docs/
│   ├── STAGE_INDEX.md          # 阶段索引（Stage 00 ～ 20 ↔ Milestone ↔ 命令 ↔ 产物 ↔ 文档，读序入口）
│   ├── COMMANDS.md             # 命令参考（含 Current-State Evidence Execution Chain 执行链）
│   ├── CURRENT_STATE_EVIDENCE_MAP.md  # 逐阶段证据链地图（输入 / 产物 / 人工动作）
│   ├── CODE_LOGIC_ANALYSIS.md  # 代码与阶段逻辑分析（M2 ~ M3.6）
│   ├── M36_PROBLEM_ASSESSMENT.md  # M3.6 v2 方法论（Finding/Problem、taxonomy、人工裁决）
│   ├── M36_HUMAN_ADJUDICATION_GUIDE.md  # M3.6 人工裁决工作指南（面向数据团队 / 业务专家）
│   ├── EVIDENCE_LAYER_AUDIT_CHECKLIST.md  # M2 证据层收尾审计清单
│   ├── EVIDENCE_LAYER_FREEZE_REPORT.md    # M2 证据层冻结报告
│   ├── SQL_ANALYSIS_LIMITATION.md  # M2.3 SQL 解析能力边界
│   ├── DATAWORKS_FILE_TYPE_REGISTRY.md  # DataWorks FileType 注册表（编号依据 / 字段约定 / UNKNOWN 兜底 / 已核实映射）
│   ├── adr/                    # 架构决策记录
│   └── agents/                 # Agent 工作流说明
│
├── workbench/                  # M3.6 Current-State Model Review Workbench（静态 Web UI，零依赖）
│
└── tests/                      # CLI 黑盒测试（只在 SDK 边界 stub）
```

## 7. 配置

配置来源是项目根目录的 `.env`，模板见 `.env.example`。

关键配置：

```bash
# Workspace 列表（唯一 Workspace 配置来源）
# id 唯一、name 唯一、至少一个；name 同时是对应 MaxCompute Project 名称
WORKSPACES=[{"id": 123456, "name": "ods"}, {"id": 234567, "name": "dwd"}]

# DataWorks UseType 过滤（空 = 全部）
DATAWORKS_USE_TYPES=NORMAL

# MaxCompute（无需单独配置 Project）
MAXCOMPUTE_ENDPOINT=https://service.cn-shanghai.maxcompute.aliyun.com/api
```

不存在 `DATAWORKS_PROJECT_ID`、`DATAWORKS_PROJECT_IDENTIFIER`、`MAXCOMPUTE_PROJECT` 等废弃配置项。

## 8. 开发

```bash
uv run ruff format .
uv run ruff check .
uv run mypy
uv run pytest
```

测试约定：唯一测试接缝是 CLI 黑盒，只在 SDK 调用边界（DataWorks OpenAPI Client、PyODPS ODPS）打桩。

## 9. M3.6 Review Workbench（人工裁决工作台）

`workbench/` 是一个**只读消费 M3.6 产物**的静态 Web 工作台，用于替代手工翻 JSON / Markdown / Checklist：

```bash
python3 -m http.server 8787        # 在仓库根目录启动静态服务
open http://localhost:8787/workbench/
```

- 读取 `analysis/review/current-state-problems.json`、`current-state-problem-evidence.json`（必需）与 `analysis/review/current-state-model-tables.json`、`analysis/evidence/layer/assessments.json`（可降级），**不写回任何产物**。
- 人工裁决写入浏览器 `localStorage`（key `m36-human-adjudication`），通过「导出裁决」导出 `m36-human-adjudication.json`，再按 [人工裁决指南](docs/M36_HUMAN_ADJUDICATION_GUIDE.md) 回填。
- 无构建、无运行时依赖，界面为中文（保留 `problem_id` / 类型枚举 / `P0`–`P3` 等技术标识）；测试：`cd workbench && npm test`（Node 内置 `node --test`）。

细节见 [workbench/README.md](workbench/README.md)。

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

**Analysis** 阶段（`analyze*` 子命令，只读已有 Snapshot / 上一阶段产物，写 `analysis/`）已实现：M2 证据链（inventory → layer → sql → lineage → profiling）、M3 业务候选（Domain / Object / Quality / Process / Grain / Fact-Dimension Candidate，M3.1 ～ M3.5）与 M3.6 Current-State Model Review（当前形态分类 + 结构化 finding + 人工清单），以及 M3.6 v2 Problem Assessment（finding 聚合成 problem candidate + 证据 / 影响 / 根因 / 重构理由 + 人工清单），只产出候选、证据与评审发现，不产出结论模型、不设计 Target DWD，详见 [docs/CODE_LOGIC_ANALYSIS.md](docs/CODE_LOGIC_ANALYSIS.md)。

要理解 `M3.6 → M3.6 v2 → 人工裁决 → 重构证据 → M4` 的方法论（Finding ≠ Problem、13 类 Problem Taxonomy、四条原则、裁决优先级、重构证据模板），见 [docs/M36_PROBLEM_ASSESSMENT.md](docs/M36_PROBLEM_ASSESSMENT.md)——人工裁决从那份文档开始。

要实际组织人工裁决（数据团队 / 业务专家视角：看哪些文件、按什么顺序、每类 Problem 怎么问、什么时候 confirmed / rejected、一周怎么排），见 [docs/M36_HUMAN_ADJUDICATION_GUIDE.md](docs/M36_HUMAN_ADJUDICATION_GUIDE.md)——干活从那份文档开始。

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

# 分析链（只读已有 Snapshot / 上一阶段产物，写 analysis/）
uv run data-platform-analysis analyze
uv run data-platform-analysis analyze-layer
uv run data-platform-analysis analyze-business
uv run data-platform-analysis analyze-business-quality
uv run data-platform-analysis analyze-business-objects
uv run data-platform-analysis analyze-business-processes
uv run data-platform-analysis analyze-business-grain
uv run data-platform-analysis analyze-business-model   # M3.5 Fact / Dimension Candidate
uv run data-platform-analysis analyze-current-state-model  # M3.6 Current-State Model Review + v2 Problem Assessment
```

退出码：

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部成功 |
| 1 | 存在 Workspace / 文件 / 表级失败，或命令执行失败 |
| 130 | 用户中断 |

详细参数说明见 [docs/COMMANDS.md](docs/COMMANDS.md)。

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
│       ├── dataworks_types.py  # DataWorks FileType 注册表
│       ├── maxcompute.py       # MaxCompute 只读元数据客户端
│       └── export.py           # Snapshot 导出与 Cleanup
│
├── source/                     # Snapshot 输出目录（gitignore）
├── analysis/                   # Analysis 产物（M2 ~ M3.6，gitignore）
├── output/                     # 导出产物
│
├── docs/
│   ├── COMMANDS.md             # 命令参考
│   ├── CODE_LOGIC_ANALYSIS.md  # 代码与阶段逻辑分析（M2 ~ M3.6）
│   ├── M36_PROBLEM_ASSESSMENT.md  # M3.6 v2 方法论（Finding/Problem、taxonomy、人工裁决）
│   ├── M36_HUMAN_ADJUDICATION_GUIDE.md  # M3.6 人工裁决工作指南（面向数据团队 / 业务专家）
│   └── adr/                    # 架构决策记录
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

- 读取 `analysis/business/current-state-problems.json`、`current-state-problem-evidence.json`（必需）与 `current-state-model-tables.json`、`analysis/layer/assessments.json`（可降级），**不写回任何产物**。
- 人工裁决写入浏览器 `localStorage`（key `m36-human-adjudication`），通过「导出裁决」导出 `m36-human-adjudication.json`，再按 [人工裁决指南](docs/M36_HUMAN_ADJUDICATION_GUIDE.md) 回填。
- 无构建、无运行时依赖，界面为中文（保留 `problem_id` / 类型枚举 / `P0`–`P3` 等技术标识）；测试：`cd workbench && npm test`（Node 内置 `node --test`）。

细节见 [workbench/README.md](workbench/README.md)。

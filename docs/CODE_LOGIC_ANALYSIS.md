# 现有代码逻辑分析：数仓反向识别与改造的分析底座

> 编写日期：2026-10-02
> 对应代码：`main` @ `70a5777`（其后含 M2.2 层级收敛改动，见 ADR-0003）
> 文档定位：把**当前代码做了什么、怎么做的、产出什么、边界在哪**讲清楚，作为"从现有数仓实际情况反向识别业务 → 完成数仓改造优化"这一目标的分析底座。不含未来的目标分层设计与业务域定义（属后续阶段）。

---

## 1. 总体架构与数据流

```
DataWorks Workspace + MaxCompute Project
        ↓  Collection（CLI: export / dataworks / maxcompute）
source/  Raw Snapshot（时点快照，只读真相源）
        ↓  Analysis（CLI: analyze / analyze-layer）
analysis/  Evidence Chain（证据链：事实 + 候选 + 证据，不含业务结论）
        ↓  （本项目边界在此）
Convention Assessment → 目标分层设计 → DWS / Semantic Layer  → 数仓改造
```

### 1.1 两阶段硬边界

- **Collection 只采集**：调 DataWorks / MaxCompute 只读 API，把 raw 响应与文件内容原样落盘，建 index 导航。不做任何分析逻辑（ADR-0002 明确禁止分析逻辑回流到采集层）。
- **Analysis 只读 Snapshot**：`source/` 全程只读，不调用任何外部 API，产物全部写入 `analysis/`。每次运行全量重写（`_reset_outputs` 清空自有产物），保证可重复、确定性。

### 1.2 贯穿全局的硬性约束

| 约束 | 落点 |
| --- | --- |
| raw Snapshot 是唯一真相源，index 只用于导航 | `snapshot.py`、ADR-0001 |
| 只产出事实 / Candidate / 证据，**不下业务结论** | 各模块 docstring、Summary 报告抬头 |
| 目录以稳定 `workspace_id` 标识，不以可变 name | ADR-0001 |
| 所有列表有确定性排序键，连续运行产物一致 | `numeric_id_sort_key` + 各阶段 sort |
| 单对象失败 → 记录可恢复错误 → 继续；只有致命错误才中断 | `errors.py` |
| 不伪造数据（没有行级样本就不给行级统计量） | `profiling.py` |

---

## 2. 采集层（Collection）代码逻辑

### 2.1 命令入口（`cli.py`）

| 命令 | 作用 |
| --- | --- |
| `export` | DataWorks + MaxCompute 一次性全量采集 |
| `dataworks` / `maxcompute` | 分别采集 |
| `summary` | 由 Snapshot 重新生成 `source/Summary.md` |
| `analyze` | 基于已有 Snapshot 生成 `analysis/` 证据链（全流程） |
| `analyze-layer` | 基于已有 `analysis/inventory` 单独执行 M2.2 |
| `config` | 打印生效的非敏感配置 |

### 2.2 DataWorks 采集（`dataworks.py` + `export.py`）

```
配置 WORKSPACES → ListFiles（分页合并，tenacity 指数退避重试）
     → 逐个 GetFile：raw 完整响应 + content（按 FileType 定扩展名）
     → files-index.json（导航 + failed_files）
```

- `DATAWORKS_PAGE_SIZE` / `DATAWORKS_MAX_RETRIES` / `DATAWORKS_USE_TYPES` 控制分页、重试与文件类型过滤。
- **Cleanup 安全规则**：只有"完整集合"（未加 `--limit`）才允许清理远端已删除的本地文件；limit 模式一律跳过 Cleanup，防止部分采集误删。

### 2.3 MaxCompute 采集（`maxcompute.py`）

```
Workspace.name（即 MaxCompute Project） → ListTables → 逐个 GetTable
     → tables-index.json（+ failed_tables）
```

- 只读元数据（PyODPS）：注释、字段、分区字段、大小、生命周期、创建/修改时间。
- 默认不采集分区实例（`MAXCOMPUTE_INCLUDE_PARTITIONS=false`）；**不采集行级数据**——这决定了 M2.5 只能是 Metadata Profiling。

### 2.4 Snapshot 布局与身份契约（ADR-0001）

```
source/
├── manifest.json                          # 仅全量 export 写入
├── dataworks/workspaces/<workspace_id>/
│   ├── files-index.json
│   ├── files/<file_id>__<file_name>.json  # Raw GetFile 响应（真相源）
│   └── content/<file_id>__<file_name>.<ext>
└── maxcompute/workspaces/<workspace_id>/
    ├── tables-index.json
    └── tables/<table_name>.json           # Table Metadata
```

身份契约：Workspace = `workspace_id`；File = `workspace_id + file_id`；Table = `project.table`。目录用稳定 id 而非可变 name，避免目录漂移。

---

## 3. 分析层（Analysis）逐阶段逻辑

**编排**：`cli.analyze` → `AnalysisPipeline.run()`（`analysis/pipeline.py`）

```
读 Workspace identity（失败即 Fatal）
  → 清空 analysis/ 自有产物
  → M2.1 Inventory            写 inventory/*.json
  → M2.2 Layer Assessment     写 layer/*          （只依赖 M2.1 + 规则配置）
  → M2.3 SQL Analysis         写 sql/*            （只吃 NodeId 有效 File）
  → M2.4 Reference / Lineage  写 lineage/*        （层级标注取 M2.2）
  → M2.5 Metadata Profiling   写 profiling/*
  → 写 Summary.md + errors.json
```

执行顺序 `M2.1 → M2.2 → M2.3 → M2.4 → M2.5` 是刻意的：M2.2 只依赖表清单与规则配置，必须先于 M2.4 完成，血缘才能直接引用 `candidate_layer`（见 ADR-0003）。

### 3.1 M2.1 Warehouse Inventory（`inventory.py`）

**输入**：`files-index.json` / `tables-index.json` + raw JSON。

**逻辑**：

1. index 导航、raw 优先：`raw` 与 `index` 冲突时以 raw 为准（约定 2）。
2. 身份与排序：workspaces 按 `workspace_id`；files 按 `(workspace_id, file_id)`；tables 按 workspace + table_key；columns 按 workspace + 表 + 序号，全部用 `numeric_id_sort_key`（数字 id 数值排序、字符串 id 其后字典序）。
3. **Analysis Scope Filter**：`is_analysis_eligible(file)` = NodeId 有效。只有已提交的 DataWorks 节点才进入后续 SQL / Reference / Lineage；NodeId 缺失的 File 保留在 Inventory 但**不产生证据、也不记错误**。
4. 层级判定**不在** M2.1 范围（`layer_candidate` 字段已删除，见 ADR-0003），M2.1 回归纯清单。

**产出字段（tables.json）**：`workspace_id / workspace_name / project / schema / table / table_key / comment / column_count / partition_count / size / is_virtual_view / lifecycle / creation_time / last_modified_time / raw_file`。

### 3.2 M2.2 Layer Assessment（`layer_assessment.py`）——唯一的层级判定

**输入**：`analysis/inventory/tables.json` + `config/layer-rules.yaml`（外部配置，改规则不用改代码）。

**规则模型（两层语义，不可混用）**：

```yaml
workspace_layers:            # Workspace Layer = 配置事实（Observed/Configured Fact）
  - {workspace_id: 466337, layer: CDM}
  - {workspace_id: 466338, layer: ODS}
  - {workspace_id: 466339, layer: ADS}
sub_layers:                  # CDM 内 DIM / DWD / DWS 的现状识别规则
  CDM: { DWD: {prefixes: [dwd_], suffixes: []}, ... }
matching: {case_sensitive: false}
```

**判定算法（单表）**：

| 情形 | candidate_layer | status | evidence |
| --- | --- | --- | --- |
| `workspace_id` 未配置 | `None` | UNKNOWN | 仅 workspace 且 `configured: false`（**显式标注，绝不按 workspace_name 猜**） |
| ODS / ADS（终点层） | = `workspace_layer` | MATCH | workspace + 其他层前缀命中（仅作提示） |
| CDM 命中唯一子层 | DWD/DWS/DIM | MATCH | workspace + prefix/suffix 命中 |
| CDM 无命中 | `None` | UNKNOWN | 仅 workspace |
| CDM 跨子层多命中 | `None` | CONFLICT | 保留全部命中，不擅自选择 |

- **跨层命名提示**：ODS/ADS 表命中 `dwd_/dws_/dim_` 等其他层前缀时，candidate 仍按 workspace 事实判定，命中写入 evidence 并通过 `cross_layer_hits` 暴露 → WARNING 日志 + `layer/summary.md`「跨层命名提示」节。这是"表放错层"的信号，留给后续 Convention Assessment。
- **状态语义**：UNKNOWN = 证据不足，**不是**违规；CONFLICT = 需人工判定。
- 双入口：`analyze-layer` 子命令与 pipeline 内步骤共用 `run_layer_assessment()`，行为一致；配置缺失/非法是 Fatal Error，不静默跳过。
- 排序：`(workspace_id, project, table_name)`；JSON 信封 `{count, assessments[]}`。
- **历史决策**：取代 M2.1 的 `naming.layer_candidate`（纯表名前缀、不看 workspace，对本项目 69% 表失效且有 35 条错判），见 `docs/adr/0003-layer-candidate-single-source.md`。

### 3.3 M2.3 SQL Analysis（`sql_analysis.py` + `normalization.py` + `dialect.py` + `fallback.py`）

**处理流水**：

```
content（只取 NodeId 有效 File）
  → 按顶层分号切分语句（基于 tokenizer，字符串内分号不切）
  → Parser Compatibility Normalization（只替换 syntax context 的全角括号（），string/comment 原样）
  → sqlglot 解析 dialect="odps"（基于 Hive 注册，支持 LIFECYCLE 表属性）
  → 记录 parse_status / extraction_method / normalization_applied / sql 原文
  → 解析成功则提取 source / target 表引用
```

**关键设计**：

- **三层原则**：raw SQL = 真相源；normalized SQL = 只给 parser 的副本；分析输出 = 派生证据。`StatementRecord.sql` 永远是原文，归一化明细在 `normalizations` 里可追溯，**不允许为了 errors=0 吞错**。
- **CTAS Fallback**：AST 解析为 `unsupported`（Command）且具备 CTAS 特征时，交给 token scanner（`fallback.py`，单向前扫描、游标必须严格前进）提取引用；提取成功记 `extraction_method=fallback`，失败保持 unsupported。与 Normalization 是两个独立阶段，互不混用。
- **失败处理**：单条语句失败只影响该条，写入 `sql/parse-errors.json` 与 `errors.json`，文件级与分析级继续。

**当前实测**：1963 条语句全部 `success`（ast=1962、fallback=1），归一化生效 1 条，unsupported=0、error=0。

### 3.4 M2.4 Table Reference / Lineage（`references.py` + `lineage.py`）

**引用提取规则（`references.py`）**：

1. `target` = 写入目标（INSERT / CREATE TABLE / CREATE VIEW / MERGE / UPDATE / DELETE）。
2. `source` = 只在"可读语句根类型"（SELECT / INSERT / CREATE / UNION / MERGE / UPDATE / DELETE / WITH / SUBQUERY / VALUES）上提取，避免 DROP / ALTER / SET / USE 产生虚假引用。
3. 排除：与 target 同表（原地重写不构成血缘）、CTE 别名、`CREATE TABLE ... LIKE` 的模板表。
4. 表名先从 AST 还原，再把 `${scheduler_variable}` 归一化成 `project.table`，原始 SQL 不改写。

**血缘构建（`lineage.py`）**：

- edge 身份 = `(workspace_id, source_key, target_key)`，同一条边只保留一次，多条 SQL 证据收进 `evidence[]`（带 file_id / statement_id / extraction_method），可回答"为什么认为这两张表有上下游关系"。
- `source_key/target_key` 是补齐 Project 后的规范标识，据此识别**跨 Workspace** 血缘。
- `source_layer_candidate / target_layer_candidate` 与核心表 `layer_candidate` **取自 M2.2 的 `candidate_layer`**，M2.4 不自行判定层级。
- 核心表候选排序：`downstream_count` 降序 → `upstream_count` → `table_key`；只反映数据流向，不代表业务价值。
- 引用了但不在 Inventory 的表也保留（`in_inventory=false`），不静默丢弃。

### 3.5 M2.5 Metadata Profiling（`profiling.py`）

- 唯一来源是 Inventory 元数据，`profile_status` 恒为 `metadata_only`。
- `row_count / distinct_count / min / max / sample_values` 一律 `null`；`is_candidate_key` 恒为 false（缺唯一性证据）——**不伪造统计量**。
- 当前产出：3719 张表级 profiling，其中分区表 2164；102603 字段级记录。

### 3.6 错误模型（`errors.py`）

| 类型 | 触发条件 | 处理 |
| --- | --- | --- |
| Fatal Error | `source/` 不存在；无法确定 Workspace identity；`--workspace` 不在 Snapshot 中；M2.2 规则配置非法 | 立即非零退出 |
| Recoverable Error | 单个 index/raw 损坏、单条 SQL 解析失败、content 缺失、单表 metadata 缺失 | 记录后继续，最终进 `errors.json`（SQL 同时进 `parse-errors.json`） |

当前实测可恢复错误 = 0。

---

## 4. 产物地图（`analysis/`）

| 产物 | 内容 | 关键字段 / 说明 | 下游用途 |
| --- | --- | --- | --- |
| `inventory/workspaces.json` | 3 个 Workspace | workspace_id / project / file_count / table_count | 资产总账 |
| `inventory/files.json` | 4651 个 DataWorks File | node_id、category、content_format、`is_analysis_eligible` | 任务目录、范围过滤依据 |
| `inventory/tables.json` | 3719 张表 | 身份 + 注释 + 分区/大小/生命周期 | 一切分析的输入 |
| `inventory/columns.json` | 102603 字段 | 类型、注释、分区标记 | 字段级分析输入 |
| `layer/assessments.json` | 3719 条层级判定 | workspace_layer / candidate_layer / status / evidence | **分层现状的唯一口径** |
| `layer/summary.md` | 层级报告 | 状态分布、UNKNOWN 明细、跨层提示、CONFLICT 明细 | 现状分层评审 |
| `sql/statements.json` | 1963 条语句 | sql 原文、parse_status、extraction_method | 业务逻辑反读的语料 |
| `sql/table-references.json` | 1273 条引用 | source_tables / target_tables / content_file | 血缘的证据层 |
| `sql/parse-errors.json` | 0 条 | — | 解析质量监控 |
| `lineage/table-lineage.json` | 3442 条去重边 | 两端 key、workspace、layer_candidate、evidence[] | **加工链路的核心产物** |
| `lineage/core-table-candidates.json` | 1789 个核心表候选 | upstream/downstream/evidence 计数 | 改造优先级参考 |
| `profiling/tables.json`、`columns.json` | 元数据画像 | metadata_only | 结构体检 |
| `errors.json` | 可恢复错误账本（0） | stage / error_type | 可信度证明 |
| `Summary.md` | 总报告（12 节） | 见下 | 一屏看全貌 |

**Summary.md 章节**：1 概览 → 2 Workspace → 3 File Inventory → 4 Table Inventory → 5 SQL Analysis → 6 Table References → 7 Table Lineage → 8 Core Table Candidates → 9 Data Profiling → 10 Layer Assessment（M2.2）→ 11 错误摘要 → 12 Analysis Limitations。

---

## 5. 数据模型与确定性契约（`models.py`）

记录一览：`WorkspaceInventory` / `FileInventory` / `TableInventory` / `ColumnInventory`（M2.1）→ `LayerAssessment` + 状态与 evidence 常量（M2.2）→ `StatementRecord` / `TableReference`（M2.3/2.4）→ `LineageEvidence` / `LineageEdge` / `CoreTableCandidate`（M2.4）→ `TableProfile` / `ColumnProfile`（M2.5）。

- 所有记录 `to_dict()`（`asdict`），字段顺序稳定。
- ID 可能是数字也可能是字符串，统一用 `numeric_id_sort_key` 归一，保证排序确定。
- 每个阶段的排序键在上文各节已列；`tests/test_rerun_semantics.py` 与 `test_inventory_is_deterministic` 等测试把"连续两次运行产物完全一致"钉死。

---

## 6. 配置与运行

- 配置中心：`config.py`（pydantic-settings + `.env`）。关键项：`WORKSPACES`（workspace_id/name/project 映射）、阿里云 AK、`DATAWORKS_*`、`MAXCOMPUTE_*`、`SOURCE_DIR=source`、`ANALYSIS_DIR=analysis`、`LAYER_RULES_PATH=config/layer-rules.yaml`。
- 层级规则：`config/layer-rules.yaml`（**唯一**层级规则来源，历史硬编码前缀已删除）。
- 常用命令：

```bash
uv run data-platform-analysis export          # 采集（需外部 API）
uv run data-platform-analysis analyze         # 全量分析（只读 source/）
uv run data-platform-analysis analyze-layer   # 仅重跑 M2.2
uv run pytest -q && uv run ruff check . && uv run mypy   # 126 tests / lint / types
```

---

## 7. 当前 Snapshot 的数据画像（实测，反向识别的原料）

### 7.1 规模

| 维度 | 数值 |
| --- | --- |
| Workspace | 3（dme_cdm / dme_ods / dme_ads） |
| DataWorks File（快照总量） | 4651（TASK 2899、SQL 格式 2821） |
| **参与分析的 File（NodeId 有效）** | **1449**（排除 3202） |
| 读取到内容并解析的 File | 559 |
| MaxCompute Table / Column | 3719 / 102603 |
| SQL 语句 | 1963（success 100%） |
| 表引用 / 去重血缘边 | 1273 / 3442（跨 Workspace 1560） |
| 核心表候选 | 1789 |
| 可恢复错误 | 0 |

### 7.2 分层现状（M2.2）

| 指标 | 数值 |
| --- | --- |
| MATCH / UNKNOWN / CONFLICT | 3658 / 61 / 0 |
| candidate 分布 | ADS 1475、ODS 1175、DWD 898、DWS 61、DIM 49、未确定 61 |
| 跨层命名提示 | 35（`dme_ads.dim_*`15、`dme_ods.dim_*`12、`dme_ods.dws_*`3、`dme_ads.dwd_*`4、`dme_ods.dwd_*`1） |
| 未配置 workspace | 0 |

### 7.3 命名族分布（决定分层策略的硬事实）

| workspace | 主导命名 | 含层前缀比例* |
| --- | --- | --- |
| dme_ads（1475） | `tb_*` 1373（93.1%） | 4.5%（66 张） |
| dme_ods（1175） | `s_*` 1136（96.7%） | 1.6%（19 张） |
| dme_cdm（1069） | `dwd_`898 / `dws_`61 / `dim_`49 | 94.3%（1008 张） |

\* 层前缀 = `ods_ / ads_ / dwd_ / dws_ / dim_`（大小写不敏感）；CDM 的 94.3% 全部来自 `dwd_/dws_/dim_`。

**读法**：本仓库的现实是 **workspace 即分层**；每个 workspace 有自己的命名族（ADS=`tb_*`、ODS=`s_*`、CDM=层前缀），层前缀只在 CDM 内部对子层有判定意义；CDM 内还有 61 张无层前缀可判的表（`fct_*`25、`tmp_*`11、`tb_*`7、`ka_*`3、`test_*`3、`information_schema_*`2 等）等待后续规则补充。ODS/ADS 中命中 `dwd_/dws_/dim_` 的 35 张即 §7.2 的跨层提示来源（ADS 19 + ODS 16）。

---

## 8. 局限与风险（必须知道的边界）

1. **分析覆盖率**：4651 个 File 中只有 1449 个（31%）有有效 NodeId 进入 SQL/血缘分析，559 个真正解析到内容。血缘只覆盖"已提交节点"，**不覆盖草稿/无节点文件**——引用现状时必须带上这个口径。
2. **只有表级血缘**：无列级血缘、无调度任务级依赖、无字段级加工逻辑。
3. **无行级数据**：Profiling 是 `metadata_only`，无法支撑唯一性/分布/质量判断。
4. **解析能力**：ODPS 方言基于 Hive 注册，未覆盖的语法会走 unsupported/fallback；当前 unsupported=0 属健康状态，但新增 SQL 写法需回归 `test_golden_*`。
5. **层级是配置事实**：新增/改名 workspace 必须同步 `layer-rules.yaml`，否则整表落入 UNKNOWN（有显式告警，不会静默）。
6. **文档漂移**：`README.md` 仍写"当前阶段只负责 Collection"，`临时想法.md` 的 P0–P10 排期已滞后于实际进度，引用时以本文档与 `docs/` 为准。
7. **冻结状态**：`docs/EVIDENCE_LAYER_FREEZE_REPORT.md` 收尾/冻结范围为现 M2.1～M2.4（Inventory / Layer / SQL / Lineage，2026-10-02 重编号后对齐），其中 Inventory / Lineage 曾因 ADR-0003 部分解冻并重新审计；M2.5 Profiling 不在本轮收尾范围。

---

## 9. 对"反向识别业务 → 数仓改造"的支撑度

### 9.1 现有产物已经能回答的问题

| 改造中的问题 | 可用产物 |
| --- | --- |
| 仓库里到底有什么资产 | `inventory/*`（含注释、分区、生命周期） |
| 数据是怎么加工流转的 | `lineage/table-lineage.json`（3442 边 + 证据链） |
| 哪些表是枢纽（改造优先级） | `core-table-candidates.json`（downstream 排序） |
| 现在的分层是否名副其实 | `layer/assessments.json`（事实 vs 候选 vs 证据） |
| 有没有放错层的表 | `layer/summary.md` 跨层命名提示（35 条） |
| SQL 里用了哪些业务概念 | `sql/statements.json`（1963 条 raw SQL 语料） |
| 结构体检（分区/注释覆盖） | `profiling/*` |

### 9.2 尚未覆盖、需后续分析阶段补齐

1. **Convention Assessment**：命名规范是否成立（61 条 UNKNOWN、35 条跨层的定性）。
2. **业务域 / 主题域识别**：目前只有表注释与字段注释原始值，没有主题聚类；SQL 语料已就绪但未做业务词抽取。
3. **任务级依赖与调度**：Snapshot 未采集依赖 API（ADR-0002 划归分析阶段）。
4. **DWS Candidate 与 Semantic Layer**：完全未开始，依赖上述 1–3 的结论。

### 9.3 建议的推进顺序（衔接现有代码）

```
现有 analysis/ 证据链（已完成）
  → ① 命名/层级现状评估：assessments + 跨层 35 条 + UNKNOWN 61 条 → Convention 规则草案
  → ② 业务域识别：tables/columns 注释 + statements 语料 → 主题域聚类（人工评审）
  → ③ 目标分层映射：现状 candidate_layer + 核心表候选 → 目标 ODS/DWD/DWS/ADS 差距清单
  → ④ 血缘驱动的迁移排序：跨层边、核心表优先
  → ⑤ DWS / Semantic Layer 设计
```

---

## 10. 代码索引（按阅读顺序）

| 关注点 | 文件 |
| --- | --- |
| 编排与执行顺序 | `src/data_platform_analysis/analysis/pipeline.py` |
| 快照只读访问 | `analysis/snapshot.py` |
| 资产清单 | `analysis/inventory.py` |
| **层级判定（唯一口径）** | `analysis/layer_assessment.py` + `config/layer-rules.yaml` |
| SQL 解析 / 归一化 / 方言 / CTAS 兜底 | `analysis/sql_analysis.py`、`normalization.py`、`dialect.py`、`fallback.py` |
| 引用与血缘 | `analysis/references.py`、`lineage.py` |
| 元数据画像 | `analysis/profiling.py` |
| 数据模型 / 排序契约 | `analysis/models.py` |
| 报告渲染 | `analysis/reports.py` |
| 错误账本 | `analysis/errors.py` |
| 表名工具 | `analysis/naming.py` |
| CLI / 配置 | `cli.py`、`config.py` |
| 关键决策 | `docs/adr/0001`（快照身份）、`0002`（采集/分析边界）、`0003`（层级唯一来源） |

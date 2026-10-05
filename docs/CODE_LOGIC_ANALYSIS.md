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
        ↓  Analysis（CLI: analyze / analyze-layer / analyze-business / analyze-business-quality / analyze-business-objects / analyze-business-processes / analyze-business-grain / analyze-business-model / analyze-current-state-model）
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
| `analyze-business` | 基于已有 M2 产物单独执行 M3 Business Understanding（候选 + 证据） |
| `analyze-business-quality` | 基于已有 M2 / M3 产物单独执行 M3.1 质量评估（只评估，不识别） |
| `analyze-business-objects` | 基于已有 M2 / M3 / M3.1 产物单独执行 M3.2 Object & Relationship 证据结构（只建结构，不重新分类） |
| `analyze-business-processes` | 基于已有 M2 / M3 / M3.1 / M3.2 产物单独执行 M3.3 Business Process Candidate Analysis（只产出 process candidate 与信号，不命名、不判 Grain） |
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

### 3.7 M3 Business Understanding（`business_understanding.py`，独立命令）

**入口**：`cli.analyze-business` → `run_business_understanding()`。**不在 `AnalysisPipeline.run()` 里**：`analyze` 不产出 `analysis/business/`，M3 也不会顺带跑 M2；M2 产物更新后需重新执行 `analyze-business`（否则 `analysis/business/` 停留在旧输入上）。

**输入（全部只读，不调 API、不读 `source/`）**：M2.1 `inventory/{tables,columns}.json`、M2.3 `sql/{statements,table-references}.json`、M2.4 `lineage/{table-lineage,core-table-candidates}.json`、M2.2 `layer/assessments.json`，加外部词典 `config/business-rules.yaml`。任一输入缺失直接报错退出，**不回退去跑 M2**。

**产出**：`analysis/business/{terms.json, tables.json, domains.json, objects.json, summary.md}`，只含 Candidate + Evidence：不产出业务结论，不生成「这是××表」这类描述（无 LLM）。

**逻辑**：

1. **分词**：`snake_case / camelCase / PascalCase` → token，剔除 stopwords（技术 token：`dwd/dws/ods/ads/dim/id/name/...`）与纯数字 → 业务词；表内按出现次数降序进 `tables.json.business_terms`，全局按 (count desc, normalized asc) 汇总进 `terms.json`。
2. **关键词匹配**：英文按词边界（`wholesale` 不命中 `sales`），中文按子串，大小写不敏感；词典与 stopwords 冲突时配置直接报错。
3. **证据分两类，顺序固定**：
   - Direct：`table_name` / `table_comment` / `column_name` / `column_comment`——同一关键词被多个来源命中属于「多来源独立证据」，**不去重**；
   - 派生：`sql`（语句原文命中，取首条语句标识）/ `lineage`（邻居表名关键词传播，取首条边）——**只补充 Direct 未覆盖的关键词**，避免同一信号重复计数抬高 confidence。
4. **confidence**：≥3 种独立来源 = high，2 种 = medium，唯一来源为表注释 = medium，其余唯一来源 = low，0 种不产生候选（UNKNOWN）。同时命中多个 Domain / Object **全部保留**，按 confidence 降序，不擅自收敛。
5. **层级只读 M2.2**：`workspace_layer` → `warehouse_layer`、`candidate_layer` → `candidate_sub_layer`，缺失留空；M3 不判定层级。
6. **确定性**：无时间戳 / UUID；表按 (workspace, project, table_key)、术语按 (count desc, normalized asc)、类别按 key asc、候选按 (confidence, key) 排序；连续两次运行字节一致（`test_analyze_business_command_writes_outputs` 钉死）。

**当前实测（3 workspace / 3719 表）**：术语候选 6032 条（出现 201486 次、来源位置 201182 个）；有 Domain 候选的表 3285、有 Object 候选的表 3182、两者至少其一 3367（90.5%）；UNKNOWN 352（9.5%）、AMBIGUOUS（≥2 Domain）2460、存在 high 候选的表 1383、核心表标记 1753；表级证据 47056 条（column_name 21962、column_comment 14176、sql 7403、table_name 2422、table_comment 1093、**lineage 0**）。lineage=0 的原因：血缘邻居表名的关键词在本数据集上**总是**已经被本表名称 / 注释或引用它的 SQL 覆盖（SQL 里通常就写着邻居表名），按防膨胀规则不再重复记入。

### 3.8 M3.1 Business Understanding Quality Assessment（`business_quality.py`，独立命令）

**入口**：`cli.analyze-business-quality` → `run_business_quality_assessment()`。**同样不在 `AnalysisPipeline.run()` 里**：只评估已有结果，不回退跑 M2 / `analyze-business`。

**输入（全部只读）**：M3 的 `business/{tables,domains,objects,terms}.json` + M2 的 `inventory/{tables,columns}.json`、`sql/table-references.json`、`lineage/{table-lineage,core-table-candidates}.json`。任一缺失 / 非法 JSON 直接报错退出（不自动补齐）；**不修改任何已有 M3 产物**，只新增三个文件。

**产出**：`analysis/business/{quality-assessment.json, quality-assessment.md, review-checklist.md}`。

**逻辑（只评估不识别，不选 winner、不产生业务结论）**：

1. **UNKNOWN 主因级联**（首个命中生效，`by_reason` 五项合计 = UNKNOWN 总数）：`comment_evidence_present`（有表 / 字段注释）→ `sql_evidence_present`（被 SQL 引用）→ `naming_evidence_present`（表 / 字段名分词有业务词，词典未覆盖）→ `insufficient_evidence`（仅血缘）→ `evidence_sparse`（全无）；`core_unknown` 是与核心表的**重叠标记**，单列不进合计。信号从 inventory 注释、table-references、lineage edges、`business_terms` 重新推导（UNKNOWN 的 evidence 必为空，无法从候选倒推）。
2. **AMBIGUOUS 五类分类**（口径 = 多 Domain **或** 多 Object 候选；`by_type` 可重叠，`count = domain + object − both`）：候选按 confidence 加权（high=3/medium=2/low=1），「强候选」= 权重 ≥2 且证据类型数 ≥2；级联 `multi_domain_likely`（≥2 强候选、证据位置不重叠、类型不互斥）→ `dominant_domain`（唯一强候选且领先）→ `keyword_cooccurrence`（候选共享证据位置）→ `evidence_conflict`（候选类型互斥）→ `unresolved`。
3. **证据质量**：按类型的 entry / 去重位置 / 表数计数（六类固定顺序，缺失补 0）、表级与候选级 diversity 分桶（0/1/2/3+）、`direct_only`（无 SQL / 血缘）、`repeated_keyword`（同词多条证据）。
4. **confidence 复核**：domain / object / combined 的 high/medium/low 分布 + high 候选拆解（`high_naming_only` 无 SQL / 血缘、`high_with_sql`、`high_with_lineage`、`high_repeated_keyword`、`high_single_keyword` 只由一个词支撑）。high 必然 diversity ≥ 3（与 M3 规则互为校验）。
5. **核心表优先级**：`core_flag_mismatch`（tables.json 标记 vs core 文件）、core ∩ UNKNOWN / AMBIGUOUS / high / 低证据计数；`review-checklist.md` 三区 P1 核心+UNKNOWN、P2 核心+AMBIGUOUS、P3 非核心+AMBIGUOUS，每区最多 50 行并注明总数，human 列留空、status=pending。
6. **确定性**：无时间戳 / UUID / 随机抽样；样本按 M3 的表稳定排序截断到每类 20 条，报告每表最多 10 条；连续两次运行字节一致。

**当前实测（3719 表）**：UNKNOWN 352（comment 213 / sql 11 / naming 128 / 血缘 0 / 稀疏 0，core_unknown 48）；AMBIGUOUS 2587 = 多 Domain 2460 + 多 Object 2203 − 两者兼有 2076（multi_domain_likely 800、evidence_conflict 734、dominant_domain 417、keyword_cooccurrence 360、unresolved 276）；core 1753（flag 不一致 0、UNKNOWN 48、AMBIGUOUS 1560、有 high 候选 913、diversity ≤1 的 274）；high 候选 2582 个全部落在 diversity 3+（naming_only 1358、含 SQL 1224、含血缘 0、单关键词 17）；diversity 分桶 352/638/1104/1625。清单三区 48 / 1560 / 1027 条。

---

### 3.9 M3.2 Business Object & Relationship Analysis（`business_objects.py`，独立命令）

**入口**：`cli.analyze-business-objects` → `run_business_object_analysis()`。**不在 `AnalysisPipeline.run()` 里**：只把已有的 M2 / M3 / M3.1 产物整理成「Object → Table → Relationship → Evidence」的证据结构，不回退跑 `analyze` / `analyze-business` / `analyze-business-quality`，也不改写它们。

**输入（11 个，全部只读）**：M3 的 `business/{objects,tables,domains}.json`、M3.1 的 `business/{quality-assessment.json, review-checklist.md}`、M2 的 `inventory/{tables,columns}.json`、`sql/{statements,table-references}.json`、`lineage/{table-lineage,core-table-candidates}.json`、`layer/assessments.json`。任一缺失 / 非法 JSON → `BusinessObjectsError` + 退出码 1（明确点名缺失文件，不自动补齐）。

**产出（5 个，固定顺序）**：`analysis/business/{objects-registry.json, object-tables.json, object-relationships.json, object-evidence-matrix.json, object-graph.md}`；只新增这五个文件，M2 / M3 / M3.1 产物字节不变。

**逻辑（只建结构，不产生业务结论）**：

1. **association**：`object-tables.json`，一条 = 一个 Object candidate × 一张表；evidence 按 M3 的 evidence type 分组（`table_name / table_comment / column_name / column_comment / sql / lineage`），只引用 statement_id / table_key / column_name；`candidate_layer` 来自 M2.2 assessments（缺失回退 `candidate_sub_layer`），`core_candidate` = M2.4 core 文件 ∪ tables.json 标记。
2. **状态规则（唯一来源是 `review-checklist.md`）**：认可值 `confirmed / rejected / needs_discussion`（`pending`、`done`、空 → `candidate`）；**confirmed 只作用于 human object 显式列出的 Object**，只填 human domain 不推断；`rejected` / `needs_discussion` 在 human object 留空时作用于该表全部机器候选；human 回填出的、不在机器候选里的 Object 直接新建 association（不经分类器）；Object 级聚合 = 全 confirmed → confirmed、全 rejected → rejected、含 needs_discussion → needs_discussion、否则 candidate；**未出现在清单中 ≠ confirmed**；`rejected` 的 association 不参与关系推导。
3. **关系推导只允许三级**：Level1 `co_occurrence`（同一张表同时是两个 Object 的候选）、Level2 `sql_reference`（同一条语句的 source × target 表跨 Object）、Level3 `lineage`（血缘边两端跨 Object）；跳过 `source == target` 与同 Object，**不允许第四级**（模糊匹配 / embedding / 猜外键）。
4. **关系身份与合并**：identity = `sorted((object_a, object_b))`，三种证据按类型合并进同一条记录并各自计数；`relationship_type` 恒为 `candidate`（不产出 owns / contains / belongs_to / one-to-many / many-to-many）；`evidence_strength` = 证据类型数的确定性映射（1=weak、2=moderate、3=strong），**不叫 confidence**；证据条目只留稳定标识（`co:<table>` / `sql:<ws>:<file>:<stmt>:<src>-><tgt>` / `lineage:<ws>:<src>-><tgt>`），不复制 SQL 原文。
5. **matrix**：`object-evidence-matrix.json` 按 Object 汇总事实口径（表数 / 核心表数 / candidate_layers / domains / evidence_types / unknown / ambiguous / 状态计数 / 关系数），unknown 与 ambiguous 沿用 M3.1 口径。
6. **报告 `object-graph.md`（8 节）**：Overview → Object count → Object table count → Relationship count → Evidence distribution → Core object relationships → Status distribution → Limitations；措辞固定为「当前证据显示 …candidate 之间存在 table co-occurrence / SQL reference / lineage evidence」，**不写成业务关系结论**，并显式声明不做 Business Process、不做 Grain。
7. **确定性**：全部稳定排序（Object 升序、关系按排序对、证据按 id），无时间戳 / UUID / 随机抽样；连续运行字节一致。

**当前实测（3719 表）**：Object 5（product 2170 / customer 1848 / store 1741 / order 1416 / employee 20），association 7195（全部 candidate，`review-checklist.md` 尚未人工回填），关系 10（= 5 个 Object 的两两组合，全部 core_related、全部 diversity 3 / strong）；证据条数 co_occurrence 6344 / sql_reference 13478 / lineage 13363，sql_reference 覆盖 1107 / 1963 条语句。

**边界（必须记住）**：Object 词典只有 5 个 → **candidate gap** 是当前最大 limitation（M3.2 不扩词典、不建第二套 Object 分类器，词外语义仍落 M3 的 UNKNOWN）；candidate ≠ confirmed；table ≠ Object（一个 Object 关联多张表，一张表也可以是多个 Object 的候选）；relationship ≠ 业务关系（需人工确认后才能解释）；core_candidate 是 lineage 上下游结构指标，不是业务价值判断。

---

### 3.10 M3.3 Business Process Candidate Analysis（`business_processes.py`，独立命令）

**入口**：`cli.analyze-business-processes` → `run_business_process_analysis()`。**不在 `AnalysisPipeline.run()` 里**：只把已有 M2 / M3 / M3.1 / M3.2 产物与 `config/process-rules.yaml` 组合成 process candidate，不回退跑前置阶段，也不改写它们。

**输入（13 个必需 + 1 个可选，全部只读）**：M3.2 的 `business/{objects-registry,object-tables,object-relationships}.json`、M3 的 `business/{tables,terms}.json`、M3.1 的 `business/review-checklist.md`、M2 的 `inventory/{tables,columns}.json`、`sql/{statements,table-references}.json`、`lineage/{table-lineage,core-table-candidates}.json`，外加 `config/process-rules.yaml`；可选输入 `business/process-review-checklist.md`（人工回填，重跑时带回）。任一必需输入缺失 / 非法 JSON / 配置非法 → `BusinessProcessesError` + 退出码 1（点名缺失文件或配置段，不自动回退执行前置阶段）。

**产出（6 个，固定顺序）**：`analysis/business/{process-signals.json, processes.json, process-tables.json, process-objects.json, process-summary.md, process-review-checklist.md}`；只新增这六个文件，M2 / M3 / M3.1 / M3.2 产物字节不变。

**逻辑（信号 + 分组 + 门槛，不产生业务结论）**：

1. **Process Signal（六类）**：列级四类来自 `process-rules.yaml` 的字段名匹配——`transaction_id / transaction_measure / event_time / status`；匹配用 `business_understanding.tokenize_identifier` 分词后做**连续子序列**比较（`order_date` 命中 `date`，`runtime` 不命中 `time`），同一列在同一类型内取「最早 + 最长 + 规则文本升序」的一条；表级两类由既有产物推导——`multi_object`（该表参与 ≥2 个 Object）、`lifecycle`（该表同时有 status 与 event_time 列级信号）。
2. **分组（去重核心）**：按**精确 Object 集合**（排序元组）分组，一张表只进一个 candidate，因此 `amount` / `quantity` 等重复信号不会各自生成一个 candidate。
3. **形成门槛（Level 1/2/3 + 列级信号）**：Level1 = transaction 信号 + 至少一个（Object participation / Measure / Event time / Status）；Level2 = 参与 Object ≥2 + 至少一个（SQL reference / Lineage / Measure / Event time）；Level3 = 组内存在 M3.2 relationship + 至少一个（transaction / event_time / measure / status）。**必须命中至少一个 Level，且组内至少有一条列级信号**，否则只保留 signal、不生成 candidate。`process_evidence_strength` = Level3→strong、Level2→moderate、Level1→weak（确定性映射，不是 confidence）。
4. **身份与编号**：`canonical_signature` = `objects=…|signals=…`（列级信号类型排序拼接），`process_key` = `process_candidate_%03d` 按 canonical signature 字典序编号；**没有 `process_name` 字段**，命名属于人工确认环节。
5. **证据与未决**：`evidence` = column / table / sql / lineage / object_relationship 五类计数（SQL 与血缘按表归属，关系来自 M3.2 排序对），`evidence_sources` 只列有证据的来源；`unresolved_questions` 固定四条（`process name not confirmed` / `process semantics not confirmed` / `grain not determined` / `business validation required`）+ 按证据缺失条件追加三条。
6. **Grain 只记信号**：`grain_signals` 聚合 `transaction_identifier / aggregation_columns / time_grouping`（每项含 table_count 与 ≤5 个示例），顶层固定写 `grain not determined`；**不产出 grain 结论**。
7. **人工确认**：`human_validated` 只有在组内全部表都在 `review-checklist.md` 里 `confirmed`、或 `process-review-checklist.md` 里该 `process_key` 回填 `confirmed=true` 时才为 true；Object 已 confirmed 不会使 process 自动 confirmed；process 清单的 `human_process_name / confirmed / note` 三列在重跑时保留。
8. **报告 `process-summary.md`（8 节）**：Overview → Process Signals → Process Candidates → Core Process Candidates → Evidence Sources → Unresolved Questions → Limitations → M3.4 Input Readiness；措辞固定为 candidate 与信号，**不命名 Business Process、不判 Grain、不做 Object ↔ Process 一对一映射**。
9. **确定性**：全部稳定排序（组按 canonical signature、表按 table_key、信号按 table_key + 类型 + 列名 + 规则），无时间戳 / UUID / 随机抽样；连续运行字节一致。

**当前实测（3719 表）**：signal 12712 条（transaction_id 214 / transaction_measure 4262 / event_time 5030 / status 618 / multi_object 2203 / lifecycle 385，覆盖 3009 张表），process candidate **17** 个（weak 1 / moderate 0 / strong 16；Level 分布 level_1=9、level_2=16、level_3=16），process table 2310 行、process object 47 行，human_validated 0 / 17（清单尚未人工回填）；4 个 Object 集合（customer 单独、product 单独、store 单独、employee 单独等）因没有 transaction 信号或够不到任何 Level 只保留 signal 不生成 candidate，2 个 candidate 缺 sql / lineage 证据、1 个缺关系证据（已写入 unresolved_questions）。

**边界（必须记住）**：Signal ≠ Process（命中规则只是信号）；candidate ≠ confirmed（机器不产出 confirmed process，也不产出 process name）；不判定 Grain（只记录 grain signals）；不做 Object ↔ Process 简单映射；core_table_count 沿用 M2.4 / M3 的 lineage 结构指标，不是业务价值判断；`analyze` / `analyze-business` / `analyze-business-quality` / `analyze-business-objects` 都不刷新 M3.3 产物，上游变化后需重跑 `analyze-business-processes`。

---

### 3.11 M3.4 Grain Candidate Analysis（`business_grain.py`，独立命令）

**入口**：`cli.analyze-business-grain` → `run_business_grain_analysis()`。**不在 `AnalysisPipeline.run()` 里**：只读已有 M2 / M3 / M3.1 / M3.2 / M3.3 产物，组合成 grain candidate，不回退跑前置阶段，也不改写它们；**不新增任何配置**。

**输入（15 个必需 + 2 个可选，全部只读）**：M3.3 的 `business/{process-signals,processes,process-tables,process-objects}.json`、M3.2 的 `business/{objects-registry,object-tables,object-relationships}.json`、M2 的 `inventory/{tables,columns}.json`、`sql/{statements,table-references}.json`、`lineage/{table-lineage,core-table-candidates}.json`、`profiling/{tables,columns}.json`；可选输入 `business/process-review-checklist.md`（只记录 Process 是否人工确认）与 `business/grain-review-checklist.md`（本阶段清单的人工回填，重跑带回）。任一必需输入缺失 / 非法 JSON → `BusinessGrainError` + 退出码 1（点名缺失文件，不调 API、不读 `source/`、不回退执行前置阶段）。

**产出（5 个，固定顺序）**：`analysis/business/{grain-signals.json, grain-candidates.json, grain-tables.json, grain-summary.md, grain-review-checklist.md}`；只新增这五个文件，M2 ~ M3.3 产物字节不变。

**逻辑（形态级联 + 证据 + 未决，不产生业务结论）**：

1. **Grain Signal（7 类）**：列级 6 类来自**字段名形态标记**——`identifier / time / measure / snapshot / event / periodic`（M3.3 process signal 命中时优先用规则文本作 `signal`，否则用命中的形态 token），表级 `aggregation` = 有度量信号但无事务标识信号；信号只覆盖 2310 张 process 表，按 `(signal_type, table, column)` 稳定排序。**Signal ≠ Grain**。
2. **候选键形态级联（每个 (process, table) 只走一种形态，不做笛卡尔积）**：事务证据存在 → T1 单键 + T2 `[事务标识, Object 标识]`（排除事务字段已命中的 Object）→ `transaction`；否则 Object × 分区时间 → `aggregation`；否则 Object × 时间列 → `aggregation`；否则快照列 → `snapshot`；否则周期列 → `periodic`；否则「事件 + 标识」列 → `event`；否则**空候选键 + `unknown`**（证据不足，不是「没有 grain」）。
3. **候选键必须真实存在**：键只能取自 `inventory/columns.json` 里该表的字段；supporting 表的判定同样只认真实存在的字段。
4. **多候选全保留**：同一 (process, table) 的多个键组合全部输出并标记 `multiple_possible_keys`，按 `process=…|table=…|keys=…|pattern=…` 的 canonical signature 全局排序后编号 `grain_candidate_%03d`；**不挑 winner、不打分**。
5. **strength = 证据源多样性**（复用 M3.2 的 `evidence_strength(diversity)`，7 类 `source_type`：process_signal / column / table / sql / lineage / object / object_relationship）；**空候选键恒为 `weak`**。Profiling 全是 `metadata_only`（`is_candidate_key` 全为 false），因此**不伪造任何行级唯一性**。
6. **`grain_pattern` 只看候选键上的形态证据**（事务 > 快照 > 周期 > 事件 > 标识×时间 → `aggregation`），空键 → `unknown`。
7. **`unresolved_reasons` 固定 7 项顺序**：`no_identifier_signal`（无任何键列带标识形态；空键恒加）→ `multiple_possible_keys` → `missing_sql_evidence` → `missing_lineage_evidence` → `time_semantics_unclear`（键里的时间列只有名字形态证据，或空键但存在时间列）→ `aggregation_level_unclear`（表有度量且形态为 aggregation / unknown）→ `insufficient_evidence`（空键或证据源 <2）。
8. **`grain-tables` 的角色只有技术含义**：每候选 1 行 `anchor`（键来自该表）+ ≤5 行 `supporting`（同 process 下也含全部键的表），锚行额外记录 `supporting_table_count`（未截断总数）；`evidence` 是 7 类计数。**不命名 Fact / Dimension**，`core_candidate` 只作证据覆盖与复核优先级。
9. **人工确认不传递**：`process_human_validated` 只记录 `processes.json` 的 `human_validated` 或 process 清单回填的 `confirmed`；**status 恒为 `candidate`**，任何位置都不产出 `confirmed` grain；grain 清单的 `human_grain_name / confirmed / note` 三列在重跑时保留，缺列 → 报错。
10. **报告**：`grain-summary.md` 9 节（Overview → Grain Signals → Grain Candidates → Process → Grain → Evidence Sources → Evidence Gaps → Human Review → Limitations → Next: Fact-Dimension Readiness），每张明细表 ≤50 行并注明总数；`grain-review-checklist.md` 按 process 分组，每组 ≤50 行。
11. **确定性**：全部稳定排序，无时间戳 / UUID / 随机抽样；连续运行字节一致。

**当前实测（3719 表 / 17 个 process candidate / 2310 张 process 表）**：Grain Signal **22436** 条（identifier 7647、time 7928、measure 3484、periodic 2473、aggregation 844、snapshot 43、event 17，覆盖 2262 张表）；Grain Candidate **5679** 个（pattern：aggregation 2534、periodic 1978、transaction 476、unknown 648、snapshot 43、event 0；strength：strong 4745 / moderate 257 / weak 677；空候选键 648）；grain → table **25011** 行（anchor 5679、supporting 19332）；未决：multiple_possible_keys 4371、missing_lineage 2529、missing_sql 2522、time_semantics_unclear 1948、aggregation_level_unclear 1911、no_identifier_signal 1591、insufficient_evidence 677；`process_human_validated` 0 / 5679（Process 侧 0 / 17 已确认）。

**边界（必须记住）**：Grain Signal ≠ Grain Candidate；Grain Candidate ≠ Confirmed Grain（status 恒 candidate）；空 `candidate_keys` ≠ 没有 grain；不伪造唯一性（Profiling 无样本，strength 只是证据源数量）；role 只用 `anchor / supporting`，不产出 DWD / DWS / Fact / Dimension 命名；`analyze` 及所有前置阶段都不刷新 M3.4 产物，上游变化后需重跑 `analyze-business-grain`。

### 3.12 M3.5 Fact / Dimension Candidate Analysis（`business_model.py`，独立命令）

**入口**：`cli.analyze-business-model` → `run_business_model_analysis()`。**不在 `AnalysisPipeline.run()` 里**：只读已有 M2 / M3 / M3.1 / M3.2 / M3.3 / M3.4 产物，组合成 fact / dimension / relationship candidate，不回退跑前置阶段，也不改写它们；**不新增任何配置**。

**输入（15 个必需 + 3 个可选，全部只读）**：M3.4 的 `business/{grain-candidates,grain-tables}.json`、M3.3 的 `business/{processes,process-objects}.json`、M3.2 的 `business/{objects-registry,object-tables,object-relationships}.json`、M2 的 `inventory/{tables,columns}.json`、`sql/table-references.json`、`lineage/{table-lineage,core-table-candidates}.json`、`profiling/{tables,columns}.json`、M2.2 的 `layer/assessments.json`（任务书口径写作 M2.5，仓库内实为 M2.2 Layer Assessment，只作 `candidate_layer` 结构证据）；可选输入 `business/process-review-checklist.md` / `business/grain-review-checklist.md`（只刷新 Process / Grain 的人工确认记录）与 `business/model-review-checklist.md`（本阶段清单回填，重跑带回）。**刻意不读** `grain-signals / process-signals / process-tables`、`business/{tables,terms,domains}.json`、`quality-assessment.json`、`sql/statements.json`（避免重做 Object / Process / Grain 判定与 SQL 解析）。任一必需输入缺失 / 非法 JSON / 根节点非对象 / 跨文件引用未知 process candidate 或 Object → `BusinessModelError` + 退出码 1（点名缺失文件，不调 API、不读 `source/`、不回退执行前置阶段）。

**产出（8 个，固定顺序）**：`analysis/business/{fact-candidates.json, dimension-candidates.json, fact-dimension-relationships.json, fact-tables.json, dimension-tables.json, model-evidence-matrix.json, model-summary.md, model-review-checklist.md}`；只新增这八个文件，M2 ~ M3.4 产物字节不变。

**逻辑（候选 + 证据 + 未决，不产生业务结论）**：

1. **Fact Gate**：`transaction / event / snapshot` 直接通过；`periodic / aggregation / unknown` 必须 `measure_columns` 非空，否则记 `no_measure_evidence`、该 grain candidate 不生成 fact；词表之外记 `pattern_not_in_vocabulary`。gate 只写非零原因计数。
2. **fact candidate = 通过闸门的 grain candidate**（签名 `process=…|grain=…|objects=…|tables=…` → 稳定排序后编号 `fact_candidate_%03d`）：表集合 = M3.4 anchor 表 + supporting 表，`role` 复用 `anchor / supporting`。
3. **fact 证据 7 类**：`process / grain / table / column / sql / lineage / object`——M3.4 grain 证据按 `process_signal→process`、`object_relationship→object`、同名直通映射，再补 process 候选、grain 候选与度量字段证据；`strength = 证据源类型数`（1 / 2 / ≥3 → weak / moderate / strong），因此 fact 结构上不会是 weak。
4. **fact 未决 7 项固定顺序**：`insufficient_process_evidence` → `insufficient_grain_evidence` → `ambiguous_grain`（pattern=unknown 或 grain 带 `multiple_possible_keys`）→ `missing_measure_evidence` → `missing_sql_evidence` → `missing_lineage_evidence` → `missing_object_evidence`。
5. **dimension 按 M3.1 Object 逐个生成**（签名 `object=…` → `dimension_candidate_%03d`）：`attributes` = 关联表字段清单（按覆盖表数倒序、最多 50 条，`attribute_count` 仍是全量）；证据 6 类 `object / column / process / fact_reference / sql / lineage`；`modeling_roles` 可多选 `dimension_candidate` + `fact_related_object`，两者都有 → `role_status=ambiguous`。
6. **dimension → table 的 anchor**：含命中该 Object 的标识字段、且**不是任何 fact candidate 表**的表才算 `anchor`，其余 `supporting`；role 不是 Fact / Dimension / DWD / DWS 结论。
7. **relationship（fact ↔ dimension）5 类证据**：`process_object / object_relationship / table_reference / sql_reference / lineage`，每类至多一条，**至少一类证据才成行**（签名 `fact=…|dimension=…` → `fact_dimension_relationship_%03d`）；relationship ≠ 业务关系，确认前必须核对 source_id。
8. **evidence matrix**：只含 fact + dimension 行，逐候选记录证据源、计数与关联实体数量；关系证据只存在于 relationship 产物。
9. **人工状态回填**：清单必需列 `candidate_key / human_status / human_name / note`（缺列报错）；映射 `pending→candidate`、`confirmed→confirmed`、`rejected→rejected`、`needs_review / needs_discussion→needs_discussion`，未识别取值输出警告并按未回填处理；机器 status 恒为 `candidate`，只有回填 `confirmed` 才变 confirmed。
10. **清单优先级 P1 → P4**（每区 ≤50 行，按 `candidate_key` 回填）：P1 = fact weak 或缺 process / grain / 度量 / Object 证据；P2 = 非 P1 且 grain 形态未定或缺 SQL / 血缘；P3 = dimension weak 或任一未决；P4 = relationship weak 或缺 Object 直接链接；区内按（优先级 → weak 在前 → 未决多在前 → key）排序。
11. **报告**：`model-summary.md` 8 节（Overview → Fact Candidates → Dimension Candidates → Fact ↔ Dimension Relationships → Evidence Coverage → Evidence Gaps → Human Review → Limitations），每张明细表 ≤50 行并注明总数。
12. **确定性**：全部稳定排序，无时间戳 / UUID / 随机抽样；连续运行字节一致。

**当前实测（3719 表 / 5679 grain candidate / 5 Object / 17 process）**：Fact Gate 通过 **3364**、未通过 **2315**（全部 `no_measure_evidence`）；fact candidate **3364**（pattern：aggregation 1730、periodic 934、transaction 476、unknown 181、snapshot 43、event 0；strength 全 strong；覆盖 15 个 process / 3364 个 grain / 1282 张表 / 4 个 Object）；dimension candidate **5**（role_status：ambiguous 4、candidate 1，涉及 3182 张关联表）；relationship **15979**（strong 8517 / moderate 3641 / weak 3821）；fact → table **15697** 行（anchor 3364、supporting 12333）、dimension → table **7195** 行（anchor 695、supporting 6500）；evidence matrix **3369** 行；未决：fact 侧 `ambiguous_grain` 3107、`missing_sql_evidence` / `missing_lineage_evidence` 各 1857、`missing_object_evidence` 525、`insufficient_grain_evidence` 181、`missing_measure_evidence` 50，dimension 侧 `fact_and_dimension_ambiguous` 4、`missing_fact_reference` 1，relationship 侧 `sql_evidence_missing` 9375、`lineage_evidence_missing` 6638、`insufficient_evidence` 3821、`missing_object_link` 358；清单分区 P1 563 / P2 2672 / P3 5 / P4 3821。

**边界（必须记住）**：fact / dimension / relationship candidate ≠ confirmed 模型（机器阶段不写 confirmed，只有人工回填才会变 confirmed）；strength 只是证据源数量，Profiling 是 metadata-only、不伪造唯一性；`layer` 只作 `candidate_layer`，`core_candidate` 只作证据覆盖与复核优先级；多角色与 UNKNOWN / AMBIGUOUS 一律保留，不合并、不拆分、不删表、不挑 winner；不读 `source/`、不重解析原始数据、不重做 Object / Process / Grain classifier、不调用 LLM / 外部 API；**不产出 DWD / DWS / Semantic Layer / DDL**（那是后续 Target DWD Design 阶段）；上游变化后需重跑 `analyze-business-model` 才刷新本阶段产物。

### 3.13 M3.6 Current-State Model Review（`model_review.py`，独立命令）

**入口**：`cli.analyze-current-state-model` → `run_current_state_model_analysis()`；同时支持 `uv run python -m data_platform_analysis.cli analyze-current-state-model`（`cli.py` 末尾的 `if __name__ == "__main__": main()` 守卫）。**不在 `AnalysisPipeline.run()` 里**：只读已有 M2 / M3 / M3.5 产物做评审，不回退跑前置阶段，也不改写它们；**不新增任何配置**。

**输入（13 个必需 + 1 个可选，全部只读）**：M3.5 的 `business/{fact-candidates,dimension-candidates,fact-dimension-relationships,fact-tables,dimension-tables}.json`、M3.4 的 `business/grain-candidates.json`、M3.3 的 `business/processes.json`、M3.2 的 `business/objects-registry.json`、M2 的 `inventory/{tables,columns}.json`、`lineage/{table-lineage,core-table-candidates}.json`、M2.2 的 `layer/assessments.json`（任务书口径写作 M2.5）；可选 `business/current-state-review-checklist.md`（本阶段清单回填，重跑带回）。**刻意不读** `profiling/`、`sql/table-references.json`、`source/`。任一必需输入缺失 / 非法 JSON / 根节点非对象 / 跨文件引用未知 process·grain·fact·dimension·Object → `CurrentStateModelError` + 退出码 1（点名缺失文件，不调 API、不回退执行前置阶段）。

**产出（5 个，固定顺序）**：`analysis/business/{current-state-model.json, current-state-model-tables.json, model-review-findings.json, current-state-model-summary.md, current-state-review-checklist.md}`；只新增这五个文件，M2 ~ M3.5 产物字节不变。同一次运行里还会接着跑 M3.6 v2 Problem Assessment（§3.14），再写出 4 个 problem 产物，合计 9 个 M3.6 产物。

**逻辑（Evidence First，只评审不改模）**：

1. **18 类 finding → priority / review group / scope 固定映射**：P0 = `fact_gate_no_measure` / `fact_gate_pattern` / `grain_conflict` / `mixed_grain` / `role_ambiguous`；P1 = `fact_without_measure` / `evidence_strength_semantics` / `snapshot_periodic_ambiguous` / `relationship_technical_only` / `relationship_object_co_occurrence` / `duplicate_fact` / `overlapping_fact` / `multi_process_table`；P2 = `dimension_object_derived` / `aggregate_fact` / `wide_analytical_table` / `result_table`；P3 = `process_multiple_grains`（唯一 `human_review_required=False`）。review group 固定 5 个：`fact_review / dimension_review / grain_review / relationship_review / model_issue_review`；scope 只取 `stage / table / table_pair / fact / dimension / process / fact_group`；每条 finding 必带 table / column / lineage / object / process / grain / M3.5 candidate 级证据。
2. **Fact Gate 复算**：复用 M3.5 的 `fact_gate`（`transaction/event/snapshot` 直过、`periodic/aggregation/unknown` 必须有度量、词表外记 `pattern_not_in_vocabulary`）重算闸门，与 M3.5 `gate` payload 对照产出 `matches_m35`；排除样本按 `(reason, pattern)` 分桶，各记一条 finding。
3. **Evidence Strength ≠ Confidence**：strength 只由证据源类型数算出（`process / grain` 由候选构造本身必然携带），无论分布如何都记一条 stage 级 `evidence_strength_semantics`。
4. **粒度 / 事实评审**：同表多组候选键 → `grain_conflict`；同表多形态 → `mixed_grain`（并检查 `snapshot/periodic` 混用 → `snapshot_periodic_ambiguous`）；一个 process 多形态 → `process_multiple_grains`；fact 无度量 → `fact_without_measure`；聚合形态 → `aggregate_fact`（按表）。
5. **维度 / 关系评审**：dimension 由 M3.2 Object 一一映射生成 → `dimension_object_derived`（stage）；`role_status=ambiguous` → `role_ambiguous`；relationship 只有技术引用（`table_reference / sql_reference / lineage`）→ `relationship_technical_only`；只有 `object_relationship` 共现 → `relationship_object_co_occurrence`（均 stage 级，回溯到 fact / dimension / 表集合）。
6. **反模式阈值（常量固定）**：宽表 ≥100 字段 → `wide_analytical_table`；同逻辑事实（同 process + 同形态 + 同候选键 + 同 Object）落在多张表 → `duplicate_fact`（scope=fact_group）；两表字段交集 ≥10 且 Jaccard ≥0.5 → `overlapping_fact`（scope=table_pair）；一个表出现在多个 process → `multi_process_table`；只有入边没有出边的表或视图 → `result_table`。
7. **current-state 分类**：`current_role` 按固定优先级 `FACT_DIMENSION_AMBIGUOUS > FACT > DIMENSION > WIDE_ANALYTICAL > RESULT_TABLE > UNKNOWN` 取首个命中；`model_shape` 由 anchor fact 的形态汇总（多种 → `MIXED`，无 fact → `UNKNOWN`）；机器状态恒 `candidate`；每张 inventory 表都有分类行，finding_id 回链到表行。
8. **报告与清单**：`current-state-model-summary.md` 6 节（Scope / Current Model Overview / Model Quality / Priority Findings / Human Review / M4 Input），明细表 ≤50 行并注明总数；`current-state-review-checklist.md` 按 5 个 review group 分区、列固定（`finding_id / finding_type / priority / scope_key / evidence / system_interpretation / human_question / human_status / human_name / note`），每区 ≤50 行，human 三列重跑保留（scope_key 里的竖线转义为 `\|`，回填不串列）；回填 `confirmed` 后 finding `status=confirmed`、`human_validated=true`。
9. **确定性**：全部稳定排序，无时间戳 / UUID / 随机抽样；连续运行字节一致，清单回填幂等。

**当前实测（3719 表 / 3364 fact / 5 dimension / 15979 relationship）**：finding **4439**（P0 696、P1 3147、P2 581、P3 15；18 类命中 15 类，`fact_gate_pattern / snapshot_periodic_ambiguous / multi_process_table` 为 0）；review group：model_issue_review 3170、grain_review 704、fact_review 558、dimension_review 5、relationship_review 2；scope：table_pair 2605、table 1269、fact_group 489、fact 50、process 15、stage 7、dimension 4。`current_role`：FACT 997、DIMENSION 627、WIDE_ANALYTICAL 52、RESULT_TABLE 2、UNKNOWN 2041、AMBIGUOUS 0；`model_shape`：AGGREGATE 374、PERIODIC 152、TRANSACTION 144、MIXED 130、SNAPSHOT 16、UNKNOWN 2903。Fact Gate 复算：通过 **3364**、未通过 **2315**（全部 `no_measure_evidence`，按形态 periodic 1044 / aggregation 804 / unknown 467），`matches_m35=True`；fact strength 全 strong（证据源 presence：process / grain / column 3364、object 2839、table 1244、sql / lineage 1507）；dimension 5（role candidate 1 / ambiguous 4）；relationship 15979（strong 8517 / moderate 3641 / weak 3821；单证据 3821、仅技术引用 358、仅共现 5880、无共享表 6238）；清单 **157 行**（每区 ≤50：Fact 50 / Dimension 5 / Grain 50 / Relationship 2 / Model Issue 50），全部 `pending`。两次连续运行 5 个产物 SHA256 一致、13 个输入文件字节不变，单次约 2s。

**边界（必须记住）**：finding ≠ 已确认问题（状态恒 candidate，只有清单回填才变）；异常只标记 Review，不判定 Wrong；不设计 Target DWD、不建 DWD / DWS、不出 DDL、不合并 / 不拆分 / 不删表 / 不改表、不自动决定最终事实与维度、不把 candidate 改 confirmed；不调 LLM / 外部 API、不引入人工业务知识、不按表名断言业务事实、不把 SQL JOIN 等同业务关系；`current_role / model_shape` 只描述当前平台已存在的形态，**不是 Target DWD Design**；上游变化后需重跑 `analyze-current-state-model` 才刷新本阶段产物。

---

### 3.14 M3.6 v2 Current-State Problem Assessment（`problem_assessment.py`，同命令附带）

**入口**：仍是 `cli.analyze-current-state-model` → `run_current_state_model_analysis()`，**不新增子命令**：写完 5 个 M3.6 产物后在同一次运行里把 finding 聚合成 problem candidate，结果挂到 `CurrentStateModelResult.problem`。循环依赖处理：`problem_assessment.py` 顶层 import `model_review`，`model_review` 在函数体内 lazy import `problem_assessment`。**不新增配置**，阈值全部是常量。

**输入（只读）**：本次运行的 M3.6 finding 与表级行 + 同一批 13 个上游产物 + 可选 `business/current-state-problem-review-checklist.md`（v2 清单回填，重跑带回）。

**产出（4 个，固定顺序）**：`analysis/business/{current-state-problems.json, current-state-problem-evidence.json, current-state-problem-summary.md, current-state-problem-review-checklist.md}`（`PROBLEM_OUTPUT_FILES`）；只新增这四个文件，M3.6 已有 5 个产物与 M2 ~ M3.5 产物字节不变。

**13 类 taxonomy（`PROBLEM_TYPE_ORDER` 固定顺序，没有证据支撑的类型不产生问题）**：`GRAIN_PROBLEM / MODEL_OVERLAP / MODEL_DUPLICATION / MIXED_RESPONSIBILITY / MODEL_ROLE_AMBIGUITY / PROCESS_MODEL_ALIGNMENT / AGGREGATION_MODEL_PROBLEM / FACT_IDENTIFICATION_PROBLEM / DIMENSION_IDENTIFICATION_PROBLEM / MODEL_SELECTION_AMBIGUITY / SEMANTIC_AMBIGUITY / MODEL_COVERAGE_GAP / UNKNOWN_MODEL`。

**逻辑（Evidence First，Finding → Problem 聚合）**：

1. **聚合边界**：粒度类 finding 按表聚合成 1 个 GRAIN_PROBLEM（多 finding → 1 problem，不同表不合并）；`overlapping_fact` 表对走 union-find 连通分量（分量内重复组并入分量问题，分量外重复组单独 MODEL_DUPLICATION）；聚合类按 `(process, assessment)` 分组（无 process 的表退化为表 scope，`valid_aggregate` 不发问题）；职责 / 角色 / 识别 / 语义 / UNKNOWN / 覆盖缺口按各自固定 scope 聚合；`MODEL_SELECTION_AMBIGUITY` 需要同 process ≥10 个 duplication 组（`SELECTION_AMBIGUITY_MIN_DUPLICATION`）；`MODEL_COVERAGE_GAP` 按 process（`processes.json` 用 `process_key`，缺失时回退 `process_candidate_id`）。
2. **三态与四分类**：grain assessment = `confirmed_conflict`（键互不包含）/ `possible_conflict`（键互为子集）/ `review_required`（跨 process 或空键）；overlap classification = `structural_overlap` / `duplication_candidate` / `technical_copy_candidate`（跨层 + 血缘方向或 Jaccard ≥0.9）/ `grain_identical_structure_divergent`（重复组未进连通分量）。
3. **职责信号口径**：`DIMENSION / AGGREGATE / MIXED_GRAIN / PERIODIC_FACT / SNAPSHOT_FACT / WIDE / RESULT`（`FACT` 是基线角色、不算信号），≥2 个信号或命中自足信号（WIDE / RESULT）→ MIXED_RESPONSIBILITY。
4. **Evidence First**：每条 problem ≥1 条证据且 finding 可追溯，没有可用证据直接抛 `CurrentStateModelError`；证据类型固定 9 类（FINDING / TABLE / COLUMN / PROCESS / GRAIN / OBJECT / SQL / LINEAGE / RELATIONSHIP）；问题级 strength 按证据类型数算（≥4 strong、3 moderate、≤2 weak），比关系证据口径更严。
5. **status 机器规则**：机器只写 `candidate` / `review_required`（weak，或 GRAIN / AGGREGATION 判为 `review_required` 时置 review_required）；`confirmed` / `rejected` 只由清单回填产生（`needs_discussion → review_required`，未识别取值按未回填处理）；`human_validated` 只在 `confirmed` 时为 true（与 finding 口径一致）。
6. **priority / 编号 / 排序**：priority 取关联 finding 的最靠前值，否则用 `PROBLEM_TYPE_PRIORITY` 默认；problem_id 按 canonical signature 排序编号（`problem_%04d`），展示按 priority → problem_type → scope → scope_key。
7. **报告与清单**：`current-state-problem-summary.md` 6 节（Scope / Problem Distribution / Impact & Root Cause / Priority & Evidence / Top Problems ≤20 行 / Human Review & M4 Input）；`current-state-problem-review-checklist.md` 按 13 类分区、10 列固定（`PROBLEM_CHECKLIST_HEADERS`）、每区 ≤50 行并注明总数，human 三列重跑保留。
8. **确定性**：全部稳定排序、无时间戳 / UUID / 随机抽样；单 problem 证据行 ≤50 行（超出截断并保留 `evidence_total` / `evidence_truncated`），problems.json 只放 5 条样例。

**当前实测（3719 表 / 4439 finding）**：problem **1190** = candidate 1148 + review_required 42 + confirmed 0 + rejected 0；priority P0 698 / P1 378 / P2 99 / P3 15；strength strong 1137 / moderate 20 / weak 33。13 类全部命中：GRAIN_PROBLEM 559、MODEL_DUPLICATION 317、MIXED_RESPONSIBILITY 204、MODEL_OVERLAP 27、FACT_IDENTIFICATION_PROBLEM 26、AGGREGATION_MODEL_PROBLEM 22、PROCESS_MODEL_ALIGNMENT 15、MODEL_SELECTION_AMBIGUITY 8、MODEL_ROLE_AMBIGUITY 4、SEMANTIC_AMBIGUITY 3、MODEL_COVERAGE_GAP 2、UNKNOWN_MODEL 2、DIMENSION_IDENTIFICATION_PROBLEM 1。classification：confirmed_conflict 548、grain_identical_structure_divergent 122、duplication_candidate 108、technical_copy_candidate 97、structural_overlap 17、model_problem 13、possible_conflict 11、review_required 9、NO_ANCHOR 1、NO_EVIDENCE 1、unclassified 263。finding 覆盖 **4427 / 4439**（12 条 `aggregate_fact` 评估为合法聚合、有意不成问题）；证据行 30201（TABLE 9177、GRAIN 8059、FINDING 6313、COLUMN 4219、PROCESS 1210、LINEAGE 1202、OBJECT 9、RELATIONSHIP 12、SQL 0），53 条 problem 证据被截断；受影响表 3345。两次连续运行 9 个产物 SHA256 一致，13 个输入与 5 个旧 M3.6 产物字节不变。

**边界（必须记住）**：problem candidate ≠ 已确认问题（`confirmed` 恒为 0，只有回填才变）；Finding Count ≠ Problem Count ≠ Confirmed Problem Count；不设计 Target DWD / DWS / Semantic Layer、不出 DDL、不合并 / 不删表 / 不改表、不自动裁决粒度、权威表与收敛顺序；UNKNOWN / 覆盖缺口只说明证据不足，不等于「表不该存在」；finding 与 problem 的未决状态互不替代（回填两个清单各自独立）。

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
| `business/terms.json` | 6032 个业务术语候选 | term / normalized_term / count / sources[] | 业务词典评审、同义词归并 |
| `business/tables.json` | 3719 张表的业务理解 | warehouse_layer / business_terms / domain_candidates / business_object_candidates / evidence | **业务候选的主产物** |
| `business/domains.json`、`objects.json` | 4 个 Domain、5 个业务对象汇总 | table_count / confidence_counts / evidence_type_counts / tables[] | 主题域现状盘点 |
| `business/summary.md` | M3 报告（7 节） | Overview → 候选 → 术语 → 证据构成 → Ambiguous/Unknown → Limitations | 人工评审入口 |
| `business/quality-assessment.json` | M3.1 质量评估（6 小节） | summary / unknown / ambiguous / evidence_quality / confidence_review / core_table_review | **M3.2 的质量基线（机器可读）** |
| `business/quality-assessment.md` | M3.1 报告（7 节） | UNKNOWN/AMBIGUOUS 主因 → 证据质量 → confidence 复核 → 核心表复核 → Limitations | 质量评审入口 |
| `business/review-checklist.md` | 人工复核清单 | P1 核心+UNKNOWN / P2 核心+AMBIGUOUS / P3 非核心+AMBIGUOUS（每区 ≤50 行，注明总数） | 人工确认台账 |
| `business/objects-registry.json` | M3.2 Object 清单（顶层 count / note / status_counts / objects） | object / name / table_count / core_table_count / status_counts / status / evidence_summary / tables | **M3.3 的 Object 主数据（candidate 口径）** |
| `business/object-tables.json` | M3.2 Object ↔ Table association | object × table_key、candidate_layer、core_candidate、confidence、evidence（按 M3 类型分组）、status、human | 人工确认台账的机器侧 |
| `business/object-relationships.json` | M3.2 关系证据候选 | object_a/object_b、relationship_type=candidate、evidence_types/diversity/strength、evidence_count、core_related、evidence（三类分桶） | M3.3 关系输入 |
| `business/object-evidence-matrix.json` | M3.2 Object 证据矩阵 | table_count / candidate_layers / domains / evidence_types / unknown / ambiguous / relationship_count | 事实口径汇总 |
| `business/object-graph.md` | M3.2 报告（8 节） | Overview → Object count → Object table count → Relationship count → Evidence distribution → Core relationships → Status → Limitations | 人工评审入口 |
| `business/process-signals.json` | M3.3 六类 Process Signal | count / rules_version / table_count / type_counts / signals[]（table_key、signal_type、signal、column_name、source、evidence、core_candidate） | **M3.4 Grain 候选的字段级输入** |
| `business/processes.json` | M3.3 process candidate（顶层 count / note / status_counts / strength_counts / level_counts） | process_key、canonical_signature、objects、tables、signals、candidate_terms、evidence、levels、grain_signals、unresolved_questions（**无 process_name**） | **M3.4 的候选主体（candidate 口径）** |
| `business/process-tables.json` | M3.3 process ↔ table 证据行 | process_key × table_key、objects、signals、evidence、core_candidate、status | 过程范围的人工核对 |
| `business/process-objects.json` | M3.3 process ↔ object 参与行 | process_key × object、role=participant、table_count、relationship_count | 参与关系台账（非 fact/dimension/owner） |
| `business/process-summary.md` | M3.3 报告（8 节） | Overview → Process Signals → Candidates → Core → Evidence Sources → Unresolved → Limitations → **M3.4 Input Readiness** | 人工评审入口 |
| `business/process-review-checklist.md` | M3.3 人工确认清单 | process_key / objects / tables / signals / evidence / human_process_name / confirmed / note（后三列重跑保留） | **Process 命名与确认的唯一台账** |
| `business/grain-signals.json` | M3.4 七类 Grain Signal | count / rules_version / table_count / type_counts / signals[]（table_key、signal_type、signal、column_name、source、evidence、core_candidate） | Grain 候选的字段级输入 |
| `business/grain-candidates.json` | M3.4 grain candidate（顶层 count / note / status_counts / pattern_counts / strength_counts / process_count / table_count） | grain_candidate_id、canonical_signature、process_key、table_key、candidate_keys、strength、grain_pattern、evidence（7 类计数）、evidence_sources、unresolved_reasons、status=candidate、process_human_validated（**无 confirmed grain、无命名**） | **M3.4 的候选主体** |
| `business/grain-tables.json` | M3.4 grain ↔ table 证据行 | grain_candidate_id × table_key、role=anchor/supporting、is_anchor、supporting_table_count、evidence、core_candidate | Grain 覆盖范围的人工核对 |
| `business/grain-summary.md` | M3.4 报告（9 节） | Overview → Grain Signals → Candidates → Process → Grain → Evidence Sources → Evidence Gaps → Human Review → Limitations → Next: Fact-Dimension Readiness | 人工评审入口 |
| `business/grain-review-checklist.md` | M3.4 人工确认清单 | 按 process 分组（每组 ≤50 行）：grain_candidate_id / table_key / grain_pattern / candidate_keys / strength / unresolved_reasons / human_grain_name / confirmed / note（后三列重跑保留） | **Grain 命名与确认的唯一台账** |
| `business/fact-candidates.json` | M3.5 fact candidate（顶层 count / note / status_counts / strength_counts / pattern_counts / unresolved_counts / gate / process_count / table_count / object_count） | fact_key、canonical_signature、process/grain id、table_keys、object_keys、grain_pattern、candidate_keys、measures、evidence（7 类）、evidence_sources、unresolved_reasons、status=candidate（**无 confirmed 模型、无命名**） | **M3.5 的 fact 候选主体** |
| `business/dimension-candidates.json` | M3.5 dimension candidate（顶层 count / note / status_counts / strength_counts / role_status_counts / unresolved_counts / table_count） | dimension_key、canonical_signature、object_key/name、table_keys、attributes（≤50）/attribute_count、referenced_by_processes/facts、modeling_roles、role_status、evidence（6 类）、unresolved_reasons、status=candidate | **M3.5 的 dimension 候选主体** |
| `business/fact-dimension-relationships.json` | M3.5 关系候选（顶层 count / note / status_counts / strength_counts / unresolved_counts / evidence_source_counts） | relationship_key、canonical_signature、fact_key、dimension_key、evidence（5 类，每类至多一条）、evidence_sources、strength、unresolved_reasons、status | 事实↔维度关系的人工核对 |
| `business/fact-tables.json` | M3.5 fact → table 证据行 | table_key × fact_key、role=anchor/supporting、candidate_layer、core_candidate、evidence 计数 | 技术角色台账（非 Fact 表命名） |
| `business/dimension-tables.json` | M3.5 dimension → table 证据行 | table_key × dimension_key、role=anchor/supporting（anchor 排除 fact 表）、candidate_layer、core_candidate | 技术角色台账（非 Dimension 表命名） |
| `business/model-evidence-matrix.json` | M3.5 证据矩阵（只含 fact + dimension） | candidate_type / candidate_key / status / evidence_strength / evidence_sources / evidence_counts / table·process·grain·object·relationship·unresolved count | 证据覆盖汇总 |
| `business/model-summary.md` | M3.5 报告（8 节） | Overview → Fact → Dimension → Relationships → Evidence Coverage → Evidence Gaps → Human Review → Limitations | 人工评审入口 |
| `business/model-review-checklist.md` | M3.5 人工回填清单（P1 → P4，每区 ≤50 行） | candidate_key / candidate_type / priority / current_status / evidence_strength / unresolved_reasons / human_status / human_name / note（后三列重跑保留） | **fact / dimension / relationship 确认的唯一台账** |
| `business/current-state-model.json` | M3.6 当前模型形态总览（count / role_counts / shape_counts / priority_counts / finding_type_counts / review_group_counts / status_counts / model_quality / fact_gate_review / evidence_strength_review / dimension_review / relationship_review） | 18 类质量指标、gate 复算与 `matches_m35`、strength ≠ confidence 解读 | **M4 Target DWD Design 的机器可读输入** |
| `business/current-state-model-tables.json` | M3.6 表级形态分类（3719 行） | table_key / current_roles / current_role / model_shape / fact_·dimension_anchor·supporting / is_view / in·out_degree / finding_ids / status=candidate | 表角色与形态的评审台账 |
| `business/model-review-findings.json` | M3.6 结构化评审发现（4439 条） | finding_id / finding_type / priority / severity / review_group / scope / scope_key / related_keys / description / impact / unresolved_reason / human_question / evidence[] / status / human_validated / human_review_required | **Finding 的唯一机器出口（M3.6 v2 聚合成 problem）** |
| `business/current-state-model-summary.md` | M3.6 报告（6 节） | Scope → Current Model Overview → Model Quality → Priority Findings → Human Review → M4 Input（明细 ≤50 行并注明总数） | 人工评审入口 |
| `business/current-state-review-checklist.md` | M3.6 人工回填清单（5 个 review group，每区 ≤50 行） | finding_id / finding_type / priority / scope_key / evidence / system_interpretation / human_question / human_status / human_name / note（后三列重跑保留） | **Finding 裁决的唯一台账** |
| `business/current-state-problems.json` | M3.6 v2 problem candidate（1190 条，顶层 count / note / finding_count / problem_type·status·priority·classification·impact·root_cause·evidence_strength_counts / distinct_affected_table_count / finding_coverage / problems[]） | problem_id / canonical_signature / problem_type / classification / priority / severity / status / human_validated / scope·scope_key / table_keys / finding_ids / evidence_strength / evidence_total / impact_types / root_cause / description / human_question / rationale{current_state, problem, evidence, impact, why_change} | **M4 的问题输入（候选口径，Finding≠Problem≠Confirmed）** |
| `business/current-state-problem-evidence.json` | M3.6 v2 全量证据行（30201 条；单 problem ≤50 行） | problem_id / evidence_type_counts / evidence_total / evidence_truncated / evidence_row_limit / evidence[]（9 类固定键） | Problem 证据可追溯层 |
| `business/current-state-problem-summary.md` | M3.6 v2 报告（6 节） | Scope → Problem Distribution → Impact & Root Cause → Priority & Evidence → Top Problems（≤20 行并注明总数）→ Human Review & M4 Input | 人工评审入口 |
| `business/current-state-problem-review-checklist.md` | M3.6 v2 人工回填清单（13 类分区，每区 ≤50 行） | problem_id / problem_type / priority / scope_key / evidence / system_interpretation / human_question / human_status / human_name / note（后三列重跑保留，也是 v2 回填输入） | **Problem 裁决的唯一台账** |
| `errors.json` | 可恢复错误账本（0） | stage / error_type | 可信度证明 |
| `Summary.md` | 总报告（12 节） | 见下 | 一屏看全貌 |

**Summary.md 章节**：1 概览 → 2 Workspace → 3 File Inventory → 4 Table Inventory → 5 SQL Analysis → 6 Table References → 7 Table Lineage → 8 Core Table Candidates → 9 Data Profiling → 10 Layer Assessment（M2.2）→ 11 错误摘要 → 12 Analysis Limitations。

---

## 5. 数据模型与确定性契约（`models.py`）

记录一览：`WorkspaceInventory` / `FileInventory` / `TableInventory` / `ColumnInventory`（M2.1）→ `LayerAssessment` + 状态与 evidence 常量（M2.2）→ `StatementRecord` / `TableReference`（M2.3/2.4）→ `LineageEvidence` / `LineageEdge` / `CoreTableCandidate`（M2.4）→ `TableProfile` / `ColumnProfile`（M2.5）→ `BusinessTerm` / `DomainCandidate` / `BusinessObjectCandidate` / `DomainSummary` / `ObjectSummary` / `BusinessTableUnderstanding`（M3）→ `QualitySample` / `QualityChecklistRow` / `BusinessQualityResult` + UNKNOWN/AMBIGUOUS 主因与 diversity 分桶常量（M3.1）→ `BusinessObjectResult` + `OBJECT_STATUS_*` / `RELATIONSHIP_EVIDENCE_*` / `EVIDENCE_STRENGTH_*` 常量（M3.2，结果对象按 registry / associations / relationships / matrix / graph 顺序持有四个 JSON payload 与报告正文）→ `BusinessProcessResult` + `PROCESS_SIGNAL_*` / `PROCESS_LEVEL_*` / `PROCESS_STRENGTH_*` / `GRAIN_SIGNAL_*` 常量（M3.3，结果对象按 signals / processes / process_tables / process_objects / summary / checklist 顺序持有四个 JSON payload 与两个 Markdown 正文）→ `BusinessGrainResult` + `GRAIN_PATTERN_*` / `GRAIN_ROLE_*` / `GRAIN_STRENGTH_*` / `GRAIN_UNRESOLVED_*` 常量（M3.4，结果对象按 signals / candidates / tables / summary / checklist 顺序持有三个 JSON payload 与两个 Markdown 正文）→ `ModelChecklistRow` / `BusinessModelResult` + `MODEL_STATUS_*` / `MODEL_HUMAN_STATUS_*` / `MODEL_ROLE_*` / `FACT_EVIDENCE_*` / `DIMENSION_EVIDENCE_*` / `MODEL_REL_EVIDENCE_*` / `MODEL_*_UNRESOLVED_*` / `MODEL_PRIORITY_*` / `MODEL_CHECKLIST_*` 常量（M3.5，结果对象按 fact / dimension / relationships / fact_tables / dimension_tables / evidence_matrix / checklist_rows / summary / checklist 顺序持有六个 JSON payload 与两个 Markdown 正文）→ `CurrentStateModelResult` + `CURRENT_MODEL_ROLE_*` / `CURRENT_MODEL_SHAPE_*` / `FINDING_TYPE_*` / `FINDING_SCOPE_*` / `REVIEW_GROUP_*` / `REVIEW_EVIDENCE_*` / `REVIEW_CHECKLIST_*` 常量（M3.6，结果对象按 model / tables / findings / summary / checklist 顺序持有三个 JSON payload 与两个 Markdown 正文）→ `CurrentStateProblemResult` + `PROBLEM_TYPE_*` / `PROBLEM_SCOPE_*` / `PROBLEM_STATUS_*` / `GRAIN_ASSESSMENT_*` / `OVERLAP_CLASS_*` / `PROBLEM_ROOT_CAUSE_*` / `PROBLEM_EVIDENCE_*` / `PROBLEM_PRIORITY_*` / `PROBLEM_OUTPUT_FILES` / `PROBLEM_CHECKLIST_*` 常量（M3.6 v2，结果对象按 problems / evidence payload 与 summary / checklist 正文持有四个产物，挂在 `CurrentStateModelResult.problem`）。

- 所有记录 `to_dict()`（`asdict`），字段顺序稳定。
- ID 可能是数字也可能是字符串，统一用 `numeric_id_sort_key` 归一，保证排序确定。
- 每个阶段的排序键在上文各节已列；`tests/test_rerun_semantics.py` 与 `test_inventory_is_deterministic` 等测试把"连续两次运行产物完全一致"钉死。

---

## 6. 配置与运行

- 配置中心：`config.py`（pydantic-settings + `.env`）。关键项：`WORKSPACES`（workspace_id/name/project 映射）、阿里云 AK、`DATAWORKS_*`、`MAXCOMPUTE_*`、`SOURCE_DIR=source`、`ANALYSIS_DIR=analysis`、`LAYER_RULES_PATH=config/layer-rules.yaml`、`BUSINESS_RULES_PATH=config/business-rules.yaml`、`PROCESS_RULES_PATH=config/process-rules.yaml`。
- 层级规则：`config/layer-rules.yaml`（**唯一**层级规则来源，历史硬编码前缀已删除）。
- 业务词典：`config/business-rules.yaml`（stopwords / domains / objects；**只被 `analyze-business` 读取**，关键词与 stopwords 冲突直接报错）。
- 过程信号规则：`config/process-rules.yaml`（transaction_identifiers / transaction_measures / event_time / status；**只被 `analyze-business-processes` 读取**，段缺失、空列表、跨段冲突直接报错，配置里不得出现业务过程命名）。
- Grain 规则：**无专用配置**，`analyze-business-grain` 只读上一阶段产物；候选键来自形态级联与 `inventory/columns.json` 实际字段。
- Fact / Dimension 候选：**无专用配置**，`analyze-business-model` 只读上一阶段产物（含 `layer/assessments.json` 的 `candidate_layer`），不读规则文件、不新增配置项。
- Current-State Model Review：**无专用配置**，`analyze-current-state-model` 只读 M2 / M3 / M3.5 产物，阈值全部是 `model_review.py` 里的常量（宽表 ≥100 字段、重合 ≥10 字段且 Jaccard ≥0.5、结果表入边 ≥1、报告 / 清单每区 ≤50 行）。
- Problem Assessment（M3.6 v2）：**无专用配置**，与 M3.6 同一命令一次跑完，阈值全部是 `problem_assessment.py` / `models.py` 的常量（问题级证据 ≥4 strong、3 moderate、≤2 weak；选择歧义 ≥10 个重复组；单 problem 证据行 ≤50、报告 Top Problems ≤20、清单每区 ≤50）。
- 常用命令：

```bash
uv run data-platform-analysis export           # 采集（需外部 API）
uv run data-platform-analysis analyze          # 全量分析（只读 source/）
uv run data-platform-analysis analyze-layer    # 仅重跑 M2.2
uv run data-platform-analysis analyze-business # 仅重跑 M3（只读 M2 产物）
uv run data-platform-analysis analyze-business-quality  # 仅重跑 M3.1（只读 M2 / M3 产物）
uv run data-platform-analysis analyze-business-objects  # 仅重跑 M3.2（只读 M2 / M3 / M3.1 产物）
uv run data-platform-analysis analyze-business-processes  # 仅重跑 M3.3（只读 M2 / M3 / M3.1 / M3.2 产物）
uv run data-platform-analysis analyze-business-grain  # 仅重跑 M3.4（只读 M2 / M3 / M3.1 / M3.2 / M3.3 产物）
uv run data-platform-analysis analyze-business-model  # 仅重跑 M3.5（只读 M2 ~ M3.4 产物）
uv run data-platform-analysis analyze-current-state-model  # 仅重跑 M3.6 + v2 Problem Assessment（只读 M2 ~ M3.5 产物，写出 9 个产物）
uv run python -m data_platform_analysis.cli analyze-current-state-model  # M3.6 的等价入口
uv run pytest -q && uv run ruff check . && uv run mypy   # 368 tests / lint / types
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
8. **M3 是候选不是结论**：Domain / Object 候选完全由 `config/business-rules.yaml` 词典驱动，词典外语义落在 UNKNOWN（352 张表）；AMBIGUOUS 2460 张表只做标记不收敛；血缘证据在当前数据上为 0（邻居关键词总已被名称 / SQL 覆盖）；`analyze` 不刷新 `analysis/business/`，M2 产物变化后必须重跑 `analyze-business`。
9. **M3.1 只评估不识别**：UNKNOWN 主因只判断信号存在性（注释 / SQL / 词 / 血缘），不解析其业务含义；AMBIGUOUS 主因是规则分类不是结论，五类里 `multi_domain_likely` / `unresolved` 必须人工判定；confidence 是证据类型数算出的规则等级，词典误命中同样会抬高它（`high_single_keyword` 17 个 high 候选只由一个词支撑）；`analyze` 同样不刷新质量产物，M3 变化后需重跑 `analyze-business-quality`；`review-checklist.md` 每区只列 50 行（全量见 JSON），human 列与 status 等人工回填。
10. **M3.2 只建结构不解释**：Object 只有 5 个（candidate gap：词典外语义仍落 M3 的 UNKNOWN），机器候选默认 `candidate`、`review-checklist.md` 未回填前 `confirmed` 恒为 0；关系只允许 co_occurrence / sql_reference / lineage 三级表级证据，`relationship_type` 恒为 `candidate`，**不能当业务关系用**，也不推导 Business Process 与 Grain；`rejected` 的 association 不参与关系推导；`analyze` / `analyze-business` / `analyze-business-quality` 都不刷新 M3.2 产物，上游变化后需重跑 `analyze-business-objects`。
11. **M3.3 只出候选不命名不判 Grain**：17 个 process candidate 全部是 `candidate`、`human_validated` 恒为 0（`process-review-checklist.md` 未回填）；信号全部来自 `config/process-rules.yaml` 的字段名匹配（词法规则，不是语义识别），信号缺失时只保留 signal 不生成 candidate；按精确 Object 集合分组意味着**同一个 Object 会出现在多个 candidate 里**，不能当唯一业务过程；`grain_signals` 只是 grain 相关信号的聚合，任何位置都是 `grain not determined`；`core_table_count` 是 lineage 结构指标；`analyze` 及所有前置阶段都不刷新 M3.3 产物，上游变化后需重跑 `analyze-business-processes`。
12. **M3.4 只出候选不确认不命名**：5679 个 grain candidate 全部 `status=candidate`（`grain-review-checklist.md` 未回填前 `confirmed` 恒为 0）；候选键由**字段名形态**级联推出（无语义解析、无行级样本，Profiling 全是 `metadata_only`），648 个空候选键是「证据不足」而不是「没有 grain」；`strength` 是证据源数量不是正确率（`multiple_possible_keys` 4371 条同时保留全部键，机器不挑 winner）；`role=anchor/supporting` 只是键归属的技术含义，**不产出 Fact / Dimension / DWD / DWS 判断**；`grain_pattern` 只看键上的形态证据，`event` 形态当前为 0；`process_human_validated` 只是上游确认状态的搬运；`analyze` 及所有前置阶段都不刷新 M3.4 产物，上游变化后需重跑 `analyze-business-grain`。
13. **M3.6 只评审不改模**：4439 条 finding 全部 `status=candidate`（`current-state-review-checklist.md` 未回填前 `confirmed` 恒为 0），finding 是候选问题、不是 Wrong 结论；`overlapping_fact` 2605 条几乎全部来自大宽表的字段高重合（阈值固定，不区分是否同源复制），`grain_conflict` 559 / `duplicate_fact` 489 只说明候选键与落表不一致，不能直接当重复表删除依据；Fact Gate 复算未通过的 2315 条是「无度量证据」而不是「没有事实」；`current_role` 的 FACT 997 / DIMENSION 627 只由 anchor 关系推导，2041 张 UNKNOWN 与 0 张 AMBIGUOUS 表示多数表还没有 fact / dimension anchor 覆盖，不等于它们不属于模型；`strength` 全 strong 是因为 process / grain 证据由候选构造自带；报告与清单每区只列 50 行（全量见 `model-review-findings.json`）；`analyze` 及所有前置阶段都不刷新 M3.6 产物，上游变化后需重跑 `analyze-current-state-model`。
14. **M3.6 v2 同样只评审不改模**：1190 条 problem 全部 `candidate` / `review_required`（`current-state-problem-review-checklist.md` 未回填前 `confirmed` 恒为 0），problem 是 finding 聚合后的候选问题，Finding Count ≠ Problem Count ≠ Confirmed Problem Count；`grain_conflict` 559 条聚合成 559 个表级 GRAIN_PROBLEM 只说明候选键不唯一，不等于 559 张表都要改；`MODEL_DUPLICATION` 317 与 `MODEL_OVERLAP` 27 只证明字段 / 结构重合，权威表与收敛顺序必须人工裁决；`MODEL_COVERAGE_GAP` 2、`UNKNOWN_MODEL` 2、只有 33 条 weak 证据说明证据不足，不是「表 / process 不该存在」；4439 条 finding 里 12 条 `aggregate_fact` 评估为合法聚合、有意不成 problem（这就是 4427 / 4439 的覆盖差）；单 problem 证据 ≤50 行（53 条被截断，全量看 `current-state-problem-evidence.json`），报告 Top Problems 只列 20 行、清单每区 50 行（全量看 `current-state-problems.json`）；`analyze` 与其它前置阶段同样不刷新这 4 个产物。

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
| 这张表可能属于什么业务主题 | `business/tables.json`（Domain / Object 候选 + 证据链）、`business/terms.json`（6032 个术语候选） |
| 哪些业务判断可以信任、哪些必须人工确认 | `business/quality-assessment.json`（UNKNOWN/AMBIGUOUS 主因、证据与 confidence 复核）、`business/review-checklist.md`（P1–P3 人工台账） |
| Object 之间有哪些表级证据关联 | `business/objects-registry.json`（5 个 Object 口径）、`business/object-relationships.json`（10 对 candidate 关系 × 三类证据）、`business/object-graph.md`（8 节评审入口） |
| 哪些表组成了可能的业务过程候选 | `business/processes.json`（17 个 candidate）、`business/process-signals.json`（12712 条信号）、`business/process-summary.md`（8 节，含 M3.4 Input Readiness） |
| 每个过程候选下各表的 grain 形态与候选键 | `business/grain-candidates.json`（5679 个候选、空键 648）、`business/grain-signals.json`（22436 条）、`business/grain-tables.json`（25011 行）、`business/grain-summary.md`（9 节）、`business/grain-review-checklist.md`（命名与确认台账） |
| 当前模型是什么形态、有哪些结构问题 | `business/current-state-model.json`（角色 / 形态 / 质量指标 / gate 复算）、`business/current-state-model-tables.json`（3719 表分类）、`business/model-review-findings.json`（4439 条 finding）、`business/current-state-model-summary.md`（6 节）、`business/current-state-review-checklist.md`（5 区人工台账） |
| 哪些问题值得改、证据够不够、先改什么 | `business/current-state-problems.json`（1190 条 problem candidate，含 priority / severity / root_cause / impact / rationale）、`business/current-state-problem-evidence.json`（30201 条证据行，可追溯到 finding / 表 / 字段 / process / 血缘）、`business/current-state-problem-summary.md`（6 节报告）、`business/current-state-problem-review-checklist.md`（13 区人工台账） |
| 结构体检（分区/注释覆盖） | `profiling/*` |

### 9.2 尚未覆盖、需后续分析阶段补齐

1. **Convention Assessment**：命名规范是否成立（61 条 UNKNOWN、35 条跨层的定性）。
2. **业务域 / 主题域识别**：M3 第一阶段已产出 Domain / Object 候选（3367 表有候选、352 表 UNKNOWN、2460 表命中多个 Domain 待人工评审），M3.1 已给出质量基线（主因分类 + P1–P3 复核清单），M3.2 已把 Object → Table → Relationship → Evidence 整理成结构化证据（5 个 Object、7195 条 association、10 对 candidate 关系），M3.3 已产出 17 个 process candidate 与 12712 条 Process Signal（含 grain_signals 与 unresolved_questions），M3.4 已把 grain 形态与候选键落到 5679 个 grain candidate（25011 行 grain→table 覆盖），M3.5 已把候选形态落到 3364 个 fact candidate、5 个 dimension candidate 与 15979 条关系候选（15697 行 fact→table、7195 行 dimension→table 覆盖）；但仍是候选而非结论，**process 命名、grain 确认、fact / dimension 角色裁决、同义词归并与主题聚类未开始**，人工回填也尚未发生（Object / Process / Grain 的 `confirmed` / `human_validated` 均为 0，`model-review-checklist.md` 全部 `pending`）；M3.6 已把现状形态与结构问题固化成 4439 条 finding（P0 696 / P1 3147 / P2 581 / P3 15，`current-state-review-checklist.md` 157 行全部 `pending`），M3.6 v2 再把 finding 聚合成 1190 条 problem candidate（P0 698 / P1 378 / P2 99 / P3 15，candidate 1148 / review_required 42，`current-state-problem-review-checklist.md` 13 个分区全部 `pending`），但 finding 与 problem 都只是候选，P0 / P1 的人工裁决与 M4 Target DWD Design 尚未开始。
3. **任务级依赖与调度**：Snapshot 未采集依赖 API（ADR-0002 划归分析阶段）。
4. **DWS Candidate 与 Semantic Layer**：完全未开始，依赖上述 1–3 的结论。

### 9.3 建议的推进顺序（衔接现有代码）

```
现有 analysis/ 证据链（已完成）
  → ① 命名/层级现状评估：assessments + 跨层 35 条 + UNKNOWN 61 条 → Convention 规则草案
  → ② 业务域识别：M3 候选（business/domains|objects|summary.md）+ terms 术语表 + M3.1 质量清单（review-checklist.md，P1→P3）+ M3.2 Object↔表↔关系证据（objects-registry|object-relationships|object-graph.md）+ M3.3 过程候选与信号（processes|process-signals|process-summary.md|process-review-checklist.md）+ M3.4 Grain 候选与形态（grain-candidates|grain-signals|grain-summary.md|grain-review-checklist.md）+ M3.5 Fact / Dimension 候选与证据（fact-candidates|dimension-candidates|fact-dimension-relationships|model-summary.md|model-review-checklist.md）+ M3.6 Current-State Model Review（current-state-model|current-state-model-tables|model-review-findings|current-state-model-summary.md|current-state-review-checklist.md）+ M3.6 v2 Problem Assessment（current-state-problems|current-state-problem-evidence|current-state-problem-summary.md|current-state-problem-review-checklist.md）→ 人工评审与主题域收敛（含 process 命名、grain 确认、fact / dimension 角色裁决、finding 裁决、problem 裁决）
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
| **业务候选（M3）** | `analysis/business_understanding.py` + `config/business-rules.yaml` |
| **质量评估（M3.1）** | `analysis/business_quality.py` |
| **Object / Relationship 证据结构（M3.2）** | `analysis/business_objects.py`（+ `reports.py::render_object_graph`） |
| **Process 候选与信号（M3.3）** | `analysis/business_processes.py` + `config/process-rules.yaml`（+ `reports.py::render_process_summary` / `render_process_review_checklist`） |
| **Grain 候选与形态（M3.4）** | `analysis/business_grain.py`（无专用配置；+ `reports.py::render_grain_summary` / `render_grain_review_checklist`） |
| **Fact / Dimension 候选（M3.5）** | `analysis/business_model.py`（无专用配置；+ `reports.py::render_model_summary` / `render_model_review_checklist`） |
| **Current-State Model Review（M3.6）** | `analysis/model_review.py`（无专用配置；+ `reports.py::render_current_state_summary` / `render_current_state_review_checklist`） |
| **Problem Assessment（M3.6 v2）** | `analysis/problem_assessment.py`（无专用配置，与 M3.6 同一命令；+ `reports.py::render_current_state_problem_summary` / `render_current_state_problem_review_checklist`） |
| 数据模型 / 排序契约 | `analysis/models.py` |
| 报告渲染 | `analysis/reports.py` |
| 错误账本 | `analysis/errors.py` |
| 表名工具 | `analysis/naming.py` |
| CLI / 配置 | `cli.py`、`config.py` |
| 关键决策 | `docs/adr/0001`（快照身份）、`0002`（采集/分析边界）、`0003`（层级唯一来源） |

---

## 11. 测试索引（368 个）

| 测试文件 | 数量 | 覆盖对象 |
| --- | --- | --- |
| `tests/test_problem_assessment.py` | 23 | M3.6 v2：4 个新产物与「不越界」、两跑字节一致 + 13 输入与 5 个旧产物不变、计数自洽、finding 覆盖账目、多 finding→1 problem 与不误合并、grain 三态、overlap 四分类（structural / technical copy / 结构分歧）、职责信号、process 对齐与选择歧义阈值、UNKNOWN 分组与证据截断、覆盖缺口、Evidence First 与四态 status 回填、报告 6 节与 Top ≤20、清单 13 分区与每区 ≤50、CLI 打印 problem 计数 |
| `tests/test_model_review.py` | 37 | M3.6：读入缺失 / 非法 / 只读、Fact Gate 复算与强度口径、粒度与事实评审、维度与关系评审、9 类反模式、current-state 分类、5 个 M3.6 产物结构与报告 6 节、清单分区与行数上限、回填（含转义竖线）、确定性、CLI 黑盒 |
| `tests/test_business_model.py` | 46 | M3.5：读入校验与跨文件引用、Fact Gate、证据与未决词表、候选键 / 签名确定性、role 非层级、状态回填映射、产物结构与报告、清单 P1–P4、确定性、CLI 黑盒 |
| `tests/test_business_grain.py` | 43 | M3.4：读入校验、7 类信号、候选键级联与「键必须真实存在」、多候选全保留、strength / grain_pattern / unresolved、grain-tables 角色、报告 9 节、清单分组与人工回填保留、确定性 |
| `tests/test_business_objects.py` | 27 | M3.2：Object / 关系 / 证据矩阵 / 报告与清单 |
| `tests/test_business_processes.py` | 26 | M3.3：六类信号、分组去重、Level 门槛、grain_signals、报告与清单 |
| `tests/test_business_understanding.py` | 25 | M3：词典匹配、Domain / Object 候选、summary |
| `tests/test_analysis_layer_assessment.py` | 23 | M2.2：层级规则、UNKNOWN / CONFLICT、ADR-0003 唯一口径 |
| `tests/test_ctas_fallback.py` | 22 | M2.3 CTAS 兜底与降级路径 |
| `tests/test_parser_normalization.py` | 16 | SQL 解析、归一化、ODPS 方言 |
| `tests/test_limit.py` | 15 | 各阶段 row limit 截断与「注明总数」契约 |
| `tests/test_business_quality_assessment.py` | 15 | M3.1：UNKNOWN / AMBIGUOUS 主因、confidence 复核、P1–P3 清单 |
| `tests/test_workspace_config.py` | 9 | workspace 身份 / layer-rules 配置契约 |
| `tests/test_rerun_semantics.py` | 8 | 重跑确定性、清单回填保留、产物不互相覆盖 |
| `tests/test_analysis_node_eligibility.py` | 6 | NodeId 有效过滤（is_analysis_eligible） |
| `tests/test_workspace_filter.py` | 5 | workspace 过滤 |
| `tests/test_fault_tolerance.py` | 5 | 可恢复错误账本、单对象失败不中断 |
| `tests/test_list_files_pagination.py` | 4 | 采集分页 |
| `tests/test_golden_504340939.py` | 4 | 真实语句 golden 回归 |
| `tests/test_analysis_sql.py` | 3 | M2.3 语句产物 |
| `tests/test_cli_smoke.py` | 2 | CLI 冒烟 |
| `tests/test_analysis_lineage.py` | 2 | M2.4 血缘去重 |
| `tests/test_analysis_inventory.py` | 2 | M2.1 清单与排序 |

配套：`tests/conftest.py` / `tests/helpers.py` / `tests/fixtures/`（内置快照夹具）。门禁命令 `uv run pytest -q && uv run ruff check . && uv run mypy`。

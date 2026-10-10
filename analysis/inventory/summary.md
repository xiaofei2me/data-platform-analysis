# M2.1 数据资产清单（Inventory）

## 1. 当前定位

**Inventory 是 Analysis 阶段的资产基线层。**

它基于 Snapshot 中已经采集并固化的数据，建立当前数据平台的统一资产清单，
回答当前有哪些数据资产、资产在哪里、资产规模是多少、
资产是否完成登记等基础问题。

Inventory 不负责解释资产的业务含义，也不负责判断 SQL、血缘、
数据质量或目标数仓模型。后续 Evidence、Understanding 和 Review
均以 Inventory 提供的资产身份与资产事实作为基础。

```text
Collection
    ↓
Snapshot
    ↓
Inventory
    ↓
Evidence
    ↓
Understanding
    ↓
Review
```

Inventory 的输出是后续分析阶段的资产输入与事实基线，不是最终分析结论。

## 2. 核心职责

| 职责 | 说明 |
| --- | --- |
| 资产登记 | 建立 DataWorks 文件、MaxCompute 表和字段的统一清单 |
| 资产身份 | 确定 Workspace、File、Table、Column 的稳定资产身份 |
| 资产覆盖 | 统计 Snapshot 中发现、登记与缺失的资产 |
| 内容快照状态 | 记录 Content 是否存在、是否空白、是否被检查过的采集事实（口径唯一实现：analysis/scope/content.py 的 content_state_of） |
| 异常记录 | 记录 Inventory 构建过程中发现的技术性异常 |

核心原则：Inventory 的职责是建立事实上的资产基线，而不是对资产进行业务解释或价值判断。

## 3. 资产总览

| 资产类型 | 数量 | 说明 |
| --- | ---: | --- |
| 工作区 | 3 | 当前 Snapshot 覆盖的 DataWorks 工作区 |
| DataWorks 文件 | 4,657 | 当前快照中的全部文件资产 |
| 有效 Node ID 文件 | 1,379 | node_id 非 None 且去除空白后非空的文件（调度身份事实） |
| 内容可用文件 | 2,826 | 已启用 Content 检查且内容非空白 |
| MaxCompute 表 | 3,724 | 当前快照中的全部表资产 |
| MaxCompute 字段 | 102,703 | 当前快照中的全部字段资产 |

## 4. 工作区资产分布

| 工作区 | DataWorks 文件 | 有效 Node ID | 内容可用 | MaxCompute 表 | 字段 |
| --- | ---: | ---: | ---: | ---: | ---: |
| dme_cdm | 741 | 243 | 717 | 1,072 | 29,475 |
| dme_ods | 2,239 | 492 | 1,052 | 1,175 | 34,803 |
| dme_ads | 1,677 | 644 | 1,057 | 1,477 | 38,425 |
| **合计** | 4,657 | 1,379 | 2,826 | 3,724 | 102,703 |

本节只展示当前 Workspace 的资产分布。Workspace 名称（如 dme_ods / dme_cdm / dme_ads）本身不能作为业务建模结论：它不证明其中的资产一定符合对应的分层定位。


## 5. DataWorks 开发资产

### 5.1 文件规模

| 指标 | 数量 |
| --- | ---: |
| 文件总数（发现） | 4,657 |
| 已登记文件 | 4,657 |
| 有效 Node ID | 1,379 |
| 缺失 Node ID | 3,278 |
| 内容可用 | 2,826 |
| 内容不可用 | 0 |
| 未启用 Content 检查 | 1,831 |

### 5.2 文件登记情况

| 指标 | 数量 |
| --- | ---: |
| 发现文件 | 4,657 |
| 已登记文件 | 4,657 |
| 登记缺口 | 0 |

登记 = 成功写入 `analysis/inventory/files.json`。登记是 Inventory 本阶段的处理结果，与「已分析」无关。

### 5.3 文件元数据完整性

| 指标 | 数量 | 占登记文件 |
| --- | ---: | ---: |
| 文件总数 | 4,657 | 100.0% |
| Raw JSON 可用 | 4,657 | 100.0% |
| 有效 Node ID | 1,379 | 29.6% |
| 缺失 Node ID | 3,278 | 70.4% |
| content_format = UNKNOWN | 0 | 0.0% |

Node ID 是 DataWorks 文件的调度身份属性（models.node_id_state()），
本节只统计它存在与否，不判断它是否满足某项分析的前置条件——
哪些文件进入哪项分析由 Scope Summary（`analysis/scope/summary.md`）说明。

缺失 Node ID 的文件不是无效资产：它们仍完整保留在 Inventory 清单中（代表案例见第 8.2 节）。

### 5.4 文件内容快照状态

| 内容状态 | 数量 | 占登记文件 | 含义 |
| --- | ---: | ---: | --- |
| present | 2,826 | 60.7% | 已检查，Content 存在且非空白 |
| not_checked | 1,831 | 39.3% | 未启用 Content 检查，不读 Snapshot、不计为缺失 |
| empty_text | 0 | 0.0% | 已检查，Content 文件存在但内容为空白 |
| not_collected | 0 | 0.0% | 已检查，content_file 为空（API 未返回 Content） |
| path_missing | 0 | 0.0% | 已检查，content_file 指向的文件在 Snapshot 中不存在 |
| read_error | 0 | 0.0% | 已检查，Content 存在但读取失败 |
| **合计** | 4,657 | 100.0% | 已登记文件 |

六个状态行互斥，合计等于已登记文件；状态由唯一权威实现`analysis/scope/content.py` 的 `content_state_of()` 给出（Scope 与 Inventory 共用同一实现，两边数字必然一致）。

三桶口径（便于与历史统计对照）：

| 口径 | 数量 | 占登记文件 |
| --- | ---: | ---: |
| 内容可用 | 2,826 | 60.7% |
| 内容不可用 | 0 | 0.0% |
| 未启用 Content 检查 | 1,831 | 39.3% |

三桶互斥，合计等于已登记文件：内容可用 = 已检查且非空白；内容不可用 = 已检查但存在缺口（empty_text / not_collected / path_missing / read_error）；未启用 Content 检查的状态为 not_checked，既不计入可用也不计入不可用，**不记作缺失**。

内容可用不等同于内容一定可以被 SQL Parser 解析；内容不可用是采集结果事实，不等于采集失败（见第 8.3 节）。


## 6. MaxCompute 数据资产

### 6.1 表资产

| 指标 | 数量 |
| --- | ---: |
| 表总数 | 3,724 |
| 有原始元数据的表 | 3,724 |
| 缺失原始元数据的表 | 0 |
| 有字段的表 | 3,724 |
| 无字段的表 | 0 |

### 6.2 字段资产

| 指标 | 数量 |
| --- | ---: |
| 字段总数 | 102,703 |
| 平均字段数（有字段的表） | 27.6 |

表身份保持当前约定：project.table（table_key，不含 schema）；字段按 table_key + ordinal 定位。本节不讨论事实表 / 维度表 / 宽表 / DWD / DWS / ADS 建模合理性，这些属于后续阶段。


## 7. 资产覆盖与完整性

本节回答：Snapshot 中的资产是否完整进入 Inventory？**这是资产覆盖检查，不是数据质量检查。**

### DataWorks

| 检查项 | 数量 |
| --- | ---: |
| Snapshot 发现文件 | 4,657 |
| Inventory 已登记 | 4,657 |
| Raw JSON 可用 | 4,657 |
| 有效 Node ID | 1,379 |
| 内容可用 | 2,826 |
| 内容文件缺失 | 0 |
| GetFile 失败 | 0 |

### MaxCompute

| 检查项 | 数量 |
| --- | ---: |
| Snapshot 发现表 | 3,724 |
| Inventory 已登记 | 3,724 |
| 原始表元数据 | 3,724 |
| 字段元数据 | 3,724 |
| 无字段元数据 | 0 |
| GetTable 失败 | 0 |

### 覆盖结论

- Snapshot 发现的 4,657 个文件与 3,724 张表已全部登记进 Inventory，登记缺口为 0。
- 内容可用性与 Node ID 覆盖见第 5 节；它们描述资产状态，不代表资产缺失或数据质量问题。
- 清单只覆盖当前 Snapshot：新增采集后需要重新运行 Inventory 才会更新。


## 8. 需要关注的资产与异常

本节按三类分开呈现，不混成一个「异常数量」：

1. **正常但需要关注**：例如文件类型 UNKNOWN，可能是非 SQL 文件或合法但未映射的类型，不一定是错误（见 8.1）；
2. **资产状态事实**：例如 Node ID 缺失、内容不可用，属于身份缺口或采集结果事实，不一定是采集失败（见 8.2、8.3）；
3. **真正技术异常**：采集失败、元数据缺失、content_file 指向文件缺失等（见 8.4）。

代表案例展示规则：总数少于 10 全部展示；10～100 展示 3～5 个代表案例；
超过 100 先按可解释特征分类，再按类别展示代表案例。完整数据以结构化产物为准（`analysis/inventory/files.json` / `tables.json` / `analysis/evidence/errors.json`）。

### 8.1 文件类型 UNKNOWN

当前未发现 content_format = UNKNOWN 的文件。

### 8.2 缺失 Node ID（调度身份缺口）

- 数量：3,278（占全部 DataWorks 文件 70.4%）

这些文件的 node_id 为 None 或空白，无法定位已提交的调度节点；这是**资产身份事实**，不是无效资产：
它们仍完整保留在 Inventory 清单中，Inventory 只记录这个状态，
是否因此排除出某项分析由 Scope Summary 说明（`analysis/scope/summary.md`）。

| Workspace | File ID | 文件名称 | Node ID | 文件类型 | 说明 |
| --- | --- | --- | --- | --- | --- |
| dme_cdm | 504340472 | dim_day | null | file_type=10 | 未提供 Node ID（node_id 为空） |
| dme_cdm | 504348391 | imp_dwd_ke24_watsons_sales_daily | null | file_type=23 | 未提供 Node ID（node_id 为空） |
| dme_cdm | 504869725 | 脚本测试 | null | file_type=1221 | 未提供 Node ID（node_id 为空） |

完整列表见 `analysis/inventory/files.json`。

### 8.3 内容不可用

当前全部文件在 Snapshot 中均有对应内容。

### 8.4 其他技术异常（真正技术异常）

| 影响级别 | 异常类型 | 数量 | 影响 |
| --- | --- | ---: | --- |
| High | GetFile 采集失败（files-index.failed_files） | 0 | 该 File 没有 raw JSON 与 Content，无法进入任何分析 |
| High | GetTable 采集失败（tables-index.failed_tables） | 0 | 该表没有元数据，不进入 Table / Column 清单 |
| High | DataWorks files-index 缺失或解析失败 | 0 | 该 Workspace 不产出 File 清单 |
| High | MaxCompute tables-index 缺失或解析失败 | 0 | 该 Workspace 不产出 Table / Column 清单 |
| Medium | files-index 条目缺少 file_id | 0 | 无法建立稳定身份，该条目不进 File 清单 |
| Medium | tables-index 条目缺少 table | 0 | 无法建立稳定身份，该条目不进 Table 清单 |
| Medium | Table raw 元数据缺失或解析失败 | 0 | 该表只有 index 侧字段，列清单缺失 |
| Medium | Table raw 缺少 columns 数组 | 0 | 该表不产出列清单 |
| Medium | Workspace 索引 / manifest 解析失败 | 0 | Workspace 名称或身份可能退化 |
| Medium | content_file 指向的 Snapshot 文件缺失 | 0 | 该 File 无法做内容级分析 |

以下类别本次已检查、当前未发现异常：GetFile 采集失败（files-index.failed_files）、GetTable 采集失败（tables-index.failed_tables）、DataWorks files-index 缺失或解析失败、MaxCompute tables-index 缺失或解析失败、files-index 条目缺少 file_id、tables-index 条目缺少 table、Table raw 元数据缺失或解析失败、Table raw 缺少 columns 数组、Workspace 索引 / manifest 解析失败、content_file 指向的 Snapshot 文件缺失。

- 计数为 0 表示本次已检查、未发生该类异常；零异常时不会生成任何代表案例。
- `content_file` 为空（API 未返回 Content）是采集结果事实，**不计入**本节异常；本节只统计 content_file 指向的文件在 Snapshot 中缺失。
- Node ID 缺失与内容不可用是资产状态事实，不属于本节，见第 8.2、8.3 节。
- 本节不是 M3.6 Problem，也不是数据质量或模型问题。

Inventory 阶段可恢复错误合计：0 条，明细见 `analysis/evidence/errors.json`。


## 9. 当前分析边界

### Inventory 负责

- 资产发现与登记
- 资产身份（Workspace / File / Table / Column 与 Node ID 状态）
- 资产规模
- Workspace / Project 分布
- 内容快照状态（Content 六态采集事实）
- Inventory 技术异常

### Inventory 不负责

- 整体分析资格 / SQL 分析资格判定
- 分析候选与资格排除清单
- 资格排除原因与规则命中统计（规则发现见 `scope/findings/`，当前未实现）
- 业务域判断
- 业务对象识别
- 业务过程识别
- Grain 判断
- 事实表 / 维度表判断
- DWD / DWS / ADS 建模判断
- SQL 语义分析
- 血缘关系分析
- 数据质量评价
- 业务正确性判断

Inventory 的输出是后续 Evidence、Understanding 和 Review 的资产输入，
而不是最终的数据分析或数据建模结论。

## 10. 关键指标定义

| 指标 | 定义 |
| --- | --- |
| 工作区（Workspace） | DataWorks 工作区，稳定身份为 workspace_id；Workspace 名称本身不能作为业务建模结论。 |
| DataWorks 文件（File） | DataWorks 工作空间内的文件资产，稳定身份为 workspace_id + file_id。 |
| File ID | DataWorks 文件的稳定标识，与 workspace_id 共同构成 File 资产身份。 |
| Node ID | DataWorks 调度节点标识，只是调度属性，不是 File 主键。 |
| 有效 Node ID | node_id 非 None 且去除空白后非空，表示该文件对应已提交的调度节点。 |
| 内容快照状态 | Content 的六态事实（present / not_checked / empty_text / not_collected / path_missing / read_error），互斥且合计等于已登记文件；由 analysis/scope/content.py 的 content_state_of() 唯一判定，Scope 与 Inventory 共用同一实现。 |
| 内容可用 | 已启用 Content 检查的格式中，content_file 非空、指向的文件存在且内容非空白（不判断可解析性）；未启用检查的格式状态为 not_checked，不计入可用。 |
| MaxCompute 表 | MaxCompute 表资产，稳定身份为 project.table（table_key，不含 schema）。 |
| 字段（Column） | MaxCompute 表的字段，按 table_key + ordinal 定位。 |
| 发现（Discovered） | Snapshot 索引（files-index / tables-index）中被发现的资产条目。 |
| 登记（Registered） | 成功写入 Inventory 清单（files.json / tables.json / columns.json）的资产。 |
| 异常 | Inventory 构建过程中发现的技术性异常（见第 8.4 节）；不含范围限制与正常形态。 |

关键区别：

- **发现 ≠ 登记 ≠ 分析**：发现是索引条目，登记是写入清单，分析属于后续阶段；
- **内容可用 ≠ SQL 可解析**：内容可用只表示 Snapshot 中存在内容文件；
- **有效 Node ID ≠ 已分析**：它只是调度身份事实；哪项分析接受哪些文件由 `analysis/scope/summary.md` 说明；
- **Inventory 异常 ≠ DataWorks / MaxCompute 采集失败**：前者是本阶段构建清单时发现的技术问题，采集失败记录在索引的 failed_* 条目；
- **UNKNOWN ≠ 一定是错误**：UNKNOWN 可能是非 SQL 文件、未映射的合法文件类型，或真正无法识别的文件。

> Inventory 指标描述技术资产与登记状态，不代表业务结论。

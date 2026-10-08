# M2.1～M2.4 Evidence Layer 质量审计清单

> **阶段重编号与收尾范围（2026-10-02）**：阶段按执行顺序重编号——
> Inventory=M2.1、Layer Assessment=M2.2（原 M2.5）、SQL=M2.3（原 M2.2）、
> Lineage=M2.4（原 M2.3）、Profiling=M2.5（原 M2.4）。
> 本文档 `M2.1～M2.4` 的收尾范围 = **Inventory / Layer / SQL / Lineage**；
> Profiling（现 M2.5）**不在本轮收尾范围**，其检查清单以附录形式保留。

## 一、M2.1 Warehouse Inventory 检查清单

### Workspace 边界
- [x] Workspace 独立存储 - 每个 workspace_id 有独立目录
- [x] workspaces-index.json 正确生成
- [x] manifest.json 正确记录所有 workspace

### File Inventory
- [x] File 身份 = `workspace_id + file_id`
- [x] NodeId 保留（即使为 null）
- [x] FileType 正确区分 RESOURCE/TASK
- [x] content_format 正确标识 SQL/PYTHON/BINARY

### Table Inventory
- [x] Table 身份 = `project.table` (table_key)
- [x] project 正确提取
- [x] schema 字段存在但不参与 identity
- [x] 表层级判定不在 M2.1（layer_candidate 已删除，见 ADR-0003），由 M2.2 产出

### 确定性
- [x] 连续运行两次产出完全一致
- [x] 排序键明确（workspace_id, file_id, table_key）
- [x] 去重逻辑正确

### 错误处理
- [x] 单个 File 失败不影响整体
- [x] 错误记录到 files-index.failed_files
- [x] 单个 Table 失败不影响整体

## 二、M2.2 Layer Assessment 检查清单（2026-10-02 新增）

### 规则配置
- [x] 层级规则唯一来源 = `config/layer-rules.yaml`（无硬编码前缀）
- [x] 配置缺失 / 语法非法 / 目标目录不存在 → Fatal Error，不静默跳过
- [x] 未配置 workspace 的表整体 UNKNOWN，evidence 带 `configured: false`（不按 workspace_name 猜）

### 判定语义
- [x] ODS / ADS（终点层）candidate = workspace_layer，其他层前缀命中仅记入 evidence
- [x] CDM 唯一子层命中 → MATCH；无命中 → UNKNOWN；跨子层多命中 → CONFLICT 且 candidate 留空
- [x] 跨层命名提示 cross_layer_hits 输出 WARNING 日志与 summary 明细
- [x] `matching.case_sensitive` 配置生效

### 证据与产物
- [x] evidence 含 workspace_layer / rule / hits 结构，可回答「为什么这样判」
- [x] `evidence/layer/{assessments.json, summary.md}` 产出（UNKNOWN 明细、CONFLICT 明细）
- [x] 排序 `(workspace_id, project, table_name)` 确定性
- [x] Lineage / CoreTable 的 layer_candidate 读自 `candidate_layer`（唯一口径，见 ADR-0003）

### 测试
- [x] 126 passed 含 M2.2 专项测试与跨层提示用例

## 三、M2.3 SQL Analysis 检查清单

### 多语句支持
- [x] 按分号切分（基于 tokenizer）
- [x] 字符串内的分号不被切开
- [x] statement_id 从 1 开始连续编号

### CTE 处理
- [x] WITH x AS (...) 中的 x 不算 source
- [x] 使用 `table.name.casefold() in cte_names` 过滤

### Subquery 处理
- [x] 子查询别名不算 source
- [x] 只提取物理表引用

### 表引用识别
- [x] INSERT INTO tableA SELECT FROM tableB ✓
- [x] INSERT OVERWRITE TABLE tableA SELECT FROM tableB ✓
- [x] CREATE TABLE tableA AS SELECT ... ✓
- [x] DROP TABLE (不产生引用) ✓

### 解析错误隔离
- [x] 单条语句失败不影响同文件后续语句
- [x] parse-errors.json 记录所有错误

## 四、M2.4 Table Lineage 检查清单

### 去重逻辑
- [x] 相同 source→target 只保留一条边
- [x] 多条 SQL 证据全部记录在 evidence

### Cross-Workspace 支持
- [x] source_workspace_id / target_workspace_id 正确识别
- [x] cross_workspace_edges 计算正确
- [x] 表名跨 Project 归一化保留原写法

### Core Table Candidates
- [x] upstream_count 计算正确
- [x] downstream_count 计算正确
- [x] evidence_count 统计全部证据

## 五、证据链完整性检查清单

### StatementRecord
- [x] content_file 字段存在
- [x] file_id / node_id 字段存在

### TableReference
- [x] source_tables 为列表（可能为空）
- [x] target_tables 为列表（可能为空）
- [x] content_file 字段存在

### LineageEdge
- [x] evidence: list[LineageEvidence]
- [x] source_key / target_key 为规范标识

### Profiling
- [x] evidence.source / index / raw_file 完整

## 六、确定性检查清单

### 运行验证
- [x] uv run pytest - 126 passed（2026-09-30 审计时为 55 passed）
- [x] ruff check . - All checks passed
- [x] mypy - Success

### 确定性保障
- [x] 排序键明确（numeric_id_sort_key）
- [x] 去重逻辑正确
- [x] overwrite 模式清空旧产物
- [x] 无外部 API 调用

## 七、冻结前最终检查清单

### 检查项
- [x] 审计完整仓库状态
- [x] 检查 M2.1～M2.4 全部模块
- [x] 验证证据链完整性
- [x] 运行全部测试

### 问题修复
- [x] Table Identity 注释不一致 → 已修正
- [x] 阶段重编号（Layer=M2.2 / SQL=M2.3 / Lineage=M2.4 / Profiling=M2.5）→ 2026-10-02 已同步

### 冻结建议
- [x] 可以冻结

## 附录 A、M2.5 Data Profiling 检查清单（不在本轮收尾范围）

> 2026-09-30 首轮审计时的检查项存档，编号为现 M2.5；留待其自身收尾时复审。

### Metadata Only 标记
- [x] profile_status = "metadata_only"
- [x] data_sample_available = false
- [x] row_count / null_count 等为 null

### Column Profile
- [x] ordinal 正确序号
- [x] is_partition 判断正确
- [x] is_candidate_key = false

### Evidence 链
- [x] evidence.source / index / raw_file 完整

---

审计日期: 2026-09-30
审计人: AI Agent
审计结果: ✅ 通过
更新日期: 2026-10-02（阶段重编号 + M2.2 Layer 纳入收尾范围）

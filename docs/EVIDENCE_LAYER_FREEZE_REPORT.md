# Evidence Layer 冻结报告

> **解冻说明（2026-10-02）**：依据 [ADR-0003](adr/0003-layer-candidate-single-source.md)，
> M2.1 的 `layer_candidate` 已删除、层级判定收敛到 M2.2，本次变更涉及冻结范围内的
> `inventory/inventory.py` / `lineage/lineage.py` / `pipeline.py` 及产物 `tables.json` / `table-lineage.json` /
> `Summary.md`。上述范围**自该 ADR 起部分解冻并重新审计**，其余冻结项维持有效。
>
> **阶段重编号与收尾范围（2026-10-02）**：阶段按执行顺序重编号——
> Inventory=M2.1、Layer Assessment=M2.2（原 M2.5）、SQL=M2.3（原 M2.2）、
> Lineage=M2.4（原 M2.3）、Profiling=M2.5（原 M2.4）。
> 本报告 `M2.1～M2.4` 的收尾/冻结范围 = **Inventory / Layer / SQL / Lineage**；
> Profiling（现 M2.5）**移出本轮范围**，留待其收尾时另行审计。

## 1. 审计概要

### 目标
将 M2.1～M2.4 加固为可冻结的 Evidence Layer

### 质量标准
- 可信：数据来源明确，每条结论可追溯到 Snapshot
- 完整：覆盖 Workspace/File/Table/Column 的全部元数据
- 可追溯：证据链从结论到 Snapshot 完整可查
- 确定性：连续运行两次产出完全一致
- 可重复：不依赖外部 API，只读取 Snapshot

### 审计范围（收尾对象）
- M2.1 Warehouse Inventory
- M2.2 Layer Assessment（2026-10-02 纳入，原为 M2.5）
- M2.3 SQL Analysis
- M2.4 Table Reference / Lineage

> 2026-09-30 首轮审计范围为当时的 M2.1～M2.4（Inventory / SQL / Lineage / Profiling）；
> 本轮按重编号后的收尾目标调整，Profiling（现 M2.5）不再列入。

## 2. 质量检查结果

### ✅ M2.1 Warehouse Inventory

**正确实现：**
- ✅ Workspace 独立性 - 每个 workspace_id 独立存储
- ✅ File 身份 - `workspace_id + file_id` 稳定标识
- ✅ NodeId 保留 - 即使为空（null）也保留，不丢弃
- ✅ 类型区分 - RESOURCE/TASK 正确区分（file_type 值）
- ✅ Table 身份 - `project.table` (table_key)，符合要求
- ✅ 确定性排序 - 所有列表都有明确的 sort key
- ✅ 错误可恢复 - 单个失败不影响整体

**修复问题：**
- ⚠️ Table Identity 注释不一致 → 已修正
  - 旧注释：Table=workspace_id+project+schema+table
  - 新注释：Table=project.table（table_key），不包含 schema

### ✅ M2.2 Layer Assessment（2026-10-02 纳入）

**正确实现：**
- ✅ 规则唯一来源 `config/layer-rules.yaml`，无硬编码前缀（原 M2.1 `layer_candidate` 已删除）
- ✅ 未配置 workspace → UNKNOWN + `configured: false` 显式证据，不按 workspace_name 猜
- ✅ ODS / ADS 按 workspace 事实判定；CDM 子层唯一命中 MATCH、无命中 UNKNOWN、跨子层命中 CONFLICT（candidate 留空）
- ✅ 跨层命名提示 cross_layer_hits 输出 WARNING 与 summary 明细，不改变 candidate
- ✅ 确定性排序 `(workspace_id, project, table_name)`；配置非法即 Fatal Error
- ✅ 血缘 / 核心表候选的层级标注统一读自 `candidate_layer`（唯一口径）

### ✅ M2.3 SQL Analysis

**正确实现：**
- ✅ 按分号切分多语句（基于 tokenizer）
- ✅ CTE 别名排除（WITH x AS (...) 中的 x 不算 source）
- ✅ Subquery 别名排除（SELECT * FROM (SELECT ...) t 中的 t 不算 source）
- ✅ 多语句支持（一个文件多条语句独立分析）
- ✅ 解析错误隔离（单条失败不影响同文件后续语句）

### ✅ M2.4 Table Lineage

**正确实现：**
- ✅ 去重边 - 相同 source→target 只保留一条，多条证据全部记录
- ✅ source_key / target_key 使用 project.table
- ✅ 跨 Workspace 识别 - source_workspace_id / target_workspace_id
- ✅ 只描述数据流向，不推断业务含义

### ⏭ M2.5 Data Profiling（移出本轮收尾范围）

> 2026-09-30 首轮审计时的检查结论如下，编号为现 M2.5；不在本轮 M2.1～M2.4 收尾范围，
> 留待其自身收尾时复审。

**首轮正确实现（存档）：**
- ✅ profile_status = metadata_only
- ✅ data_sample_available = false
- ✅ row_count 等统计量为 null（不伪造）
- ✅ is_candidate_key = false
- ✅ Evidence 链完整 - index / raw_file / source

## 3. 证据链完整性

**可追溯路径：**
```
Lineage Edge (dwd_order → ads_sales)
    ↓
TableReferenceEvidence { file_id, statement_id }
    ↓
SQL Content File (content/xxx.sql)
    ↓
DataWorks File (files/xxx.json)
    ↓
Snapshot (source/dataworks/workspaces/466337/)
```

## 4. 确定性验证

**测试结果：**
126 passed（2026-10-02；2026-09-30 首轮为 55 passed），ruff / mypy 全绿

## 5. 冻结建议

### ✅ 可以冻结的依据
1. M2.1～M2.4 全部实现符合质量标准（含 2026-10-02 新纳入的 M2.2 Layer Assessment）
2. 证据链完整，每条结论都有 SQL 证据
3. 测试覆盖充分（126 个测试全部通过）
4. 无重大缺陷

### 🚫 不冻结的理由（无）

暂未发现阻止冻结的重大缺陷。

## 6. 结论

### ✅ 建议：批准冻结

Evidence Layer（M2.1～M2.4）当前已达到：
- ✅ 可信：数据来源明确，证据链完整
- ✅ 完整：覆盖全部元数据
- ✅ 可追溯：从结论到 Snapshot 路径清晰
- ✅ 确定性：连续运行产出一致
- ✅ 可重复：不依赖外部 API

**冻结范围（M2.1～M2.4）：**
- src/data_platform_analysis/analysis/inventory/inventory.py
- src/data_platform_analysis/analysis/layer/layer_assessment.py
- src/data_platform_analysis/analysis/sql/sql_analysis.py
- src/data_platform_analysis/analysis/lineage/references.py
- src/data_platform_analysis/analysis/lineage/lineage.py
- src/data_platform_analysis/analysis/pipeline.py

> `profiling/profiling.py`（M2.5）不列入本轮范围；首轮已审状态见 §2 ⏭ 小节。

**冻结产物（M2.1～M2.4）：**
- analysis/inventory/{workspaces,files,tables,columns}.json
- analysis/layer/{assessments,summary}
- analysis/sql/{statements,table-references,parse-errors}.json
- analysis/lineage/{table-lineage,core-table-candidates}.json
- analysis/Summary.md

---

审计日期: 2026-09-30  
审计人: AI Agent  
审计结果: ✅ 通过  

更新日期: 2026-10-02（阶段重编号 + ADR-0003 解冻重审 + M2.2 Layer 纳入、M2.5 Profiling 移出）

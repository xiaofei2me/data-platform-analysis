# 分析范围规则唯一来源：Inventory 内部一次分类，下游只消费判定结果

> 产物路径已被 [ADR-0005](0005-scope-artifact-directory-and-checklist-preservation.md) 修订：
> 三份清单迁入 `analysis/scope/`（`inputs/` + `review-tasks.json`），Scope 统计改写
> `scope/summary.{json,md}`，本文「决定 7」与「后果」中的 `inventory/` 路径与文件计数以 0005 为准；
> 判定口径与配置契约（本文其余决定）不变。

## 背景

「哪些 File 参与后续分析」此前不是一个统一的概念，而是散落在三处各自的过滤：

- `models.is_analysis_eligible()`：只看 NodeId 是否有效（身份维度）；
- `sql_analysis.SqlAnalyzer.analyze_file()`：再次检查 `is_analysis_eligible` 与 `content_format.upper() == "SQL"`，并把 Content 缺失记成 `stage=sql` 的可恢复错误；
- `inventory` 的 Summary 各处自行统计 eligible / content_available，无法回答「某个 File 为什么不在分析范围内」。

由此产生三个问题：

1. **同一问题有多个答案**：M2.1 报告的「分析候选」、M2.3 实际输入、Content 可用统计口径互不一致，读者无法交叉核对。
2. **范围不可解释**：没有产物记录被排除对象的身份、命中规则与原因代码，也没有「待确认」而非「确定排除」的出口。
3. **Content 状态粒度不足**：`content_file` 为空、指向的文件不存在、读取失败混在一个「内容不可用」里，无法区分采集事实与 Snapshot 完整性问题；文件名匹配（测试 / 临时任务）没有规则来源，只能硬编码或事后人工筛。

## 决定

1. **`config/analysis-scope-rules.yaml` 是分析范围的唯一判定来源**：节点身份状态、内容状态与内容期望、非正式任务命名（强 / 弱证据）、`content_format` 是否适用 SQL、四个口径的资格结论，全部在该文件声明。配置缺失、字段非法、必需规则组为空 → 直接 Fatal Error（exit 1），**不回退默认规则、不静默忽略**。
2. **分类在 M2.1 Inventory 内部执行一次**（`analysis/scope/` → `FileScope`；`inventory/scope.py` 只是兼容层 re-export）：对全量登记 File 逐个产出 `FileScopeDecision`，输出与输入同序、数量一致，`inventory/files.json` 不因分类减少任何记录。
3. **三个资格口径分开、互不混用**：
   - `identity_eligible` = 资产身份维度（Node ID 非空）；`is_analysis_eligible()` 是该维度的兼容入口；
   - `overall_eligible` = 身份有效且未被明确非正式任务规则排除，供整体分析范围与报告统计；
   - `sql_eligible` = M2.3 输入维度（身份有效 + 未被明确非正式任务规则排除 + 类型适用 + Content 可用）。
   身份有效但命中明确非正式任务规则的 File，`identity_eligible = true`、`overall_eligible = false`、`sql_eligible = false`。`node_id_state` 只有 `missing` / `valid` 两个取值（存在 = 非 None 且去除空白后非空），不存在「格式无效」这一状态。
4. **下游不再自行过滤**：`SqlAnalyzer.analyze_file()` 的 identity / 格式检查删除，SQL 输入统一由 `FileScope.sql_eligible_files()` 给出；SQL Analysis 只消费判定结果。
5. **只有两个概念**：资产有效性（是否是可追溯资产）与分析资格（是否适合某项分析），另有「弱证据待确认」这一独立出口。**没有清理候选概念**：`cleanup_candidate` 与 YAML 里的清理候选字段已全量删除，配置里出现即被拒绝。命中任何规则都只记录与分类，**不调用任何 DataWorks 删除 / 禁用 / 修改接口**，也不删除 Snapshot 或 Inventory 记录。
6. **Content 检查由 `content_check` 开关控制**：`config/analysis-scope-rules.yaml` 的 `content_check.enabled` / `content_check.enabled_formats` 决定哪些 `content_format` 读 Snapshot、匹配内容规则并可能产生缺口；未启用的格式状态恒为 `not_checked`，既不计入内容可用、不计入内容缺口，也不阻断 `sql_eligible`。`content_check` 是必需根键，缺失、类型错误、字段未登记、格式未在 `content_expectations` 登记都会被加载器拒绝。
7. **产物**：`inventory/sql-candidates.json`（`sql_eligible = true` 的全部文件，M2.3 的候选输入）、`inventory/excluded-tasks.json`（`sql_eligible = false` 的全部文件，含 `exclusion_class` / `matched_rule_ids` / `reason_code` / `sql_reason_code`）、`inventory/review-tasks.json`（弱证据待确认，独立维度、不改变 `sql_eligible`）、`inventory/summary.md` 第 11 节（资格口径、节点身份与类型、内容状态与期望、规则命中、主因分布）。前两份清单互斥且合计 = 登记文件；规则命中可重叠，主因互斥，两者分开计数。三份清单都只是分析范围判定的产物，**不是删除清单**。

## 后果

- 口径保持不变（真实 Snapshot 实测，迁移前后逐条 diff）：4657 登记、1379 `overall_eligible`、541 `sql_eligible`、4116 SQL 分析排除、70 待确认、1917 语句——`overall_eligible` / `sql_eligible` / `review_required` / `exclusion_class` / `node_id_state` 在迁移前后**完全一致**；变化只发生在解释层（`reason_code` 中 541 条由 `NODE_ID_VALID` 改为 `CONTENT_PRESENT`，1831 个非 SQL 文件的 `content_state` 变为 `not_checked`）。
- 产物新增 1 个：`inventory/` 从 7 个文件变为 8 个，`analysis/` 全量从 61 变为 62（`62 = 8 + 12 + 32 + 9 + 1`），`--stage inventory` 后剩 9 个、`--stage evidence` 后剩 21 个、`--stage understanding` 后 53 个、`--stage review` 后 62 个。
- `excluded-tasks.json` 的口径由「`overall_eligible = false`」改为「`sql_eligible = false`」（真实数据 3272 → 4116），`sql-candidates.json` 承接其互补集（541）；`review-tasks.json` 仍是独立的弱证据维度。
- `CONTENT_FILE_MISSING` 从 `stage=sql` 改为 `stage=inventory` 记账：Content 不可用的文件在分类阶段就被阻断，不再靠 SQL 阶段「顺带」暴露 Snapshot 完整性问题。
- `inventory/summary.md` 从 10 节扩到 11 节，`is_analysis_eligible` 不再出现在 SQL 输入链路，测试契约同步更新（`SECTION_HEADINGS` / `INVENTORY_FILES`）。
- 改范围规则只改 YAML、不改代码；规则 ID 重复、条件 `kind` 不认识、组内条件重复、未知字段（含旧的 `cleanup_candidate`）都会被加载器拒绝。

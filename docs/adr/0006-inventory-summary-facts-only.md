# Inventory Summary 只报事实，资格口径单点归 Scope Summary

## 背景

[ADR-0005](0005-scope-artifact-directory-and-checklist-preservation.md) 把资格清单与 Scope 统计
迁入 `analysis/scope/` 后，仍有两处职责越界残留：

1. **同一事实两处统计**：`inventory/summary.md` 第 5.3 / 5.5 节与第 10 节仍回答
   「哪些文件在分析范围内 / 当前分析候选」，与 `scope/summary.md` 的资格章节口径重叠；
   模型侧 `WorkspaceInventorySummary.eligible_file_count`、
   `DataWorksInventorySummary.eligible_*` 四个字段也是 Inventory 自算的资格结论。
2. **内容状态两套实现**：`build_inventory_summary(..., scope)` 拿到 `FileScope` 后，
   自己再统计一遍内容可用 / 内容缺口，与 `scope/content.py` 的判定存在漂移风险——
   报告里出现两个「内容可用」的数字就无法交叉核对。
3. **Inventory 依赖 Scope 对象**：盘点报告的构造函数要求传入 `FileScope`，
   源码上「先有资产清单、再做资格评估」的单向关系被破坏。

## 决定

1. **模型字段迁移（Inventory 只留事实）**
   - `WorkspaceInventorySummary.eligible_file_count` → `valid_node_id_count`
     （事实：Node ID 有效的文件数）；
   - `DataWorksInventorySummary` 删除 4 个 `eligible_*` 字段，新增
     `content_state_counts: dict[str, int]`（事实：内容快照状态分布）。
2. **`build_inventory_summary(inventory, *, reader, content_check, errors=None)` 不再接收 `FileScope`**
   内容状态统一调用 `scope.content.content_state_of()`（唯一权威实现），节点身份统一调用
   `models.node_id_state()`；`content_check` 由 `scope.rules.ContentCheckConfig` 提供。
3. **两份 Summary 的章节互斥**
   - Inventory Summary 保持 10 节，只报事实：§5.3 文件元数据完整性、§5.4 文件内容快照状态
     （删除原 §5.5），§8.2 改为「缺失 Node ID（调度身份缺口）」，§10 删除「当前分析候选」行；
   - 资格口径（整体分析资格、SQL 分析范围、资格排除、弱证据待确认、规则命中、规则发现）
     全部归 Scope Summary，结构整理为 9 节。
4. **规则发现状态显式化**：`scope/outputs.py` 新增
   `FINDINGS_STATUS_NOT_IMPLEMENTED = "not_implemented"`，`scope/summary.json` 的 `findings`
   与 `scope/summary.md` 第 8 节共用该常量，`count` 仍为 0。
5. **写盘顺序**：`pipeline._load_scope_rules()` 在写盘前 fail-fast 加载规则，
   规则非法时 exit 1 且不写 `inventory/files.json`；随后 build inventory → 写 `inventory/` →
   `build_inventory_summary(...)` → `_build_scope(inventory, rules)` → 写 `scope/`。
6. **阶段契约不变（逃生条款外的硬约束）**：`docs/STAGE_INDEX.md` Stage 01 定义
   `analyze --stage inventory` 同时产出 `inventory/`、`scope/` 与根 `summary.md`，
   本次只做「同一阶段内的职责隔离」，不拆 CLI 入口——`--stage inventory` 不会变成只出 `inventory/`。

## 后果

- Inventory Summary 不再回答「哪些文件参与分析」；该问题的唯一答案是
  `scope/summary.{json,md}`。两份报告的数字交叉核对时，内容状态必然一致
  （同源 `content_state_of()`）。
- 口径零变化：4657 登记 / 541 SQL 候选 / 4116 排除 / 70 弱证据待确认、
  `overall_eligible = 1379`，资格清单字段契约与人工 checklist 均未改动。
- 新增 `tests/test_inventory_scope_boundary.py`（13 项）锁死边界：构造签名不含 `scope`、
  源码不含资格标识、内容状态与 `scope/content.py` 同源、两份 Summary 数字一致、
  阶段契约说明。
- 生产 `analysis/` 仍是重构前产物（含资格章节），需人工重跑
  `uv run data-platform-analysis analyze` 才会刷新；本次未触碰生产目录与 `source/`。

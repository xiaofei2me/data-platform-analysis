# Scope 产物迁入 analysis/scope/，Inventory 只留资产索引；清场保留人工回填清单

## 背景

ADR-0004 把分析范围规则收敛为单一来源后，资格清单仍写在 `analysis/inventory/` 下
（`sql-candidates.json` / `excluded-tasks.json` / `review-tasks.json`），Scope 统计塞在
`inventory/summary.md` 第 11 节。这带来三个问题：

1. **目录语义混杂**：`inventory/` 既装资产索引又装资格判定产物，读者无法从目录名判断
   「这是盘点事实还是范围结论」；源码包 `analysis/scope/` 与产物目录 `analysis/inventory/`
   不同构。
2. **规则发现无处安放**：ADR-0004 只实现了资格分类与审核标记，对象级「规则发现
   （整改问题）」尚未实现，但需要一个与 `inputs/`（输入契约）语义不同的落点。
3. **人工回填会被清场吞掉**：`analyze` / `--stage inventory` / `--stage evidence` 的
   `_reset_outputs()` 无差别清空 `analysis/`，5 份含 `human_*` 列的 checklist
   （两份 M3.6 review checklist + M3.3/M3.4/M3.5 三份 understanding checklist）一并丢失，
   人工裁决成果只能靠备份文件恢复。

## 决定

1. **Inventory 与 Scope 产物分离**：`analysis/inventory/` 只保留资产索引
   （`workspaces/files/tables/columns.json`）与 10 节 `summary.md`（资格与规则统计移出）；
   Scope 正式产物统一写入 `analysis/scope/`：
   - `scope/inputs/sql-candidates.json`、`scope/inputs/excluded-tasks.json`——后续分析的输入契约；
   - `scope/review-tasks.json`——弱证据待确认（独立维度，不改变 `sql_eligible`）；
   - `scope/summary.json` + `scope/summary.md`——机器统计与人读报告（原 Inventory 第 11 节迁入）；
   - `scope/findings/`——规则发现预留目录；当前未实现，不生成产物，Summary 如实标注 count = 0。
2. **路径常量唯一来源**：`analysis/scope/outputs.py` 声明
   `SQL_CANDIDATES_RELATIVE_PATH` / `EXCLUDED_TASKS_RELATIVE_PATH` /
   `REVIEW_TASKS_RELATIVE_PATH` / `SCOPE_SUMMARY_*_RELATIVE_PATH`，全仓库（含测试）只从这里取路径。
3. **契约不变**：`sql-candidates.json` ⇔ `sql_eligible == true`，`excluded-tasks.json` ⇔ `false`，
   互斥且合计覆盖全部登记文件；`review-tasks.json` 独立；被排除对象仍完整保留在
   `inventory/files.json`；口径（4657 / 1379 / 541 / 4116 / 70）与 ADR-0004 完全一致，只搬目录不改判定。
4. **清场保留人工清单**：`pipeline.PRESERVED_CHECKLIST_FILES` 登记 5 份含人工列的 checklist；
   `_reset_outputs()` 先快照再清场、清场后原样恢复，随后各阶段 carry-over 合并人工列。
   `understanding/business/review-checklist.md`（M3.1）无 carry-over，不在保护之列。
5. **流水线拆分写盘**：`pipeline._write_inventory()`（资产盘点）与 `_write_scope()`（资格评估）分开，
   `_write_reports*()` 同时写 `inventory/summary.md`、`scope/summary.md` 与根 `summary.md`。

## 后果

- 产物计数：`inventory/` 8 → 5、新增 `scope/` 5 个，`analysis/` 全量 62 → 64
  （`64 = 10 + 12 + 32 + 9 + 1`）；`--stage inventory` 后 11 个、`--stage evidence` 后 23 个、
  `--stage understanding` 后 55 个、`--stage review` 后 64 个。
- 旧 `inventory/{sql-candidates,excluded-tasks,review-tasks}.json` 随 `inventory/` 整目录清场
  消失，不再作为权威来源；生产 `analysis/` 在重跑前仍是旧布局。
- 清场语义变化：`--stage inventory` / `--stage evidence` / 全量 `analyze` 不再丢失人工三列，
  但 `understanding/`、`review/` 的其余机器产物照删——生产上仍不建议随意清场重跑。
- 产物目录与源码模块同构：`analysis/scope/`（产物）↔ `src/.../analysis/scope/`（源码），
  引用时靠前缀区分。
- 测试契约同步：`tests/test_evidence_stage_contract.py` 的 `SCOPE_FILES`、
  `tests/test_scope_artifacts.py` 的路径 / 结构 / 回填保留断言，
  `SECTION_HEADINGS` 回到 10 节。

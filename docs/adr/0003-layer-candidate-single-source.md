# 层级候选唯一来源：M2.2 取代 M2.1 layer_candidate

> **阶段编号注记（2026-10-02）**：本 ADR 撰写时 Layer Assessment 编号为 M2.5；后按
> 执行顺序重编号为 M2.2，SQL=M2.3（原 M2.2）、Lineage=M2.4（原 M2.3）、
> Profiling=M2.5（原 M2.4）。正文编号已同步为新编号，决策内容与历史关系不变。

## 背景

层级候选此前有两个互相独立的实现：

- M2.1 `layer_candidate`：`analysis/naming.py` 硬编码 `ods_ / dwd_ / dws_ / ads_ / dim_` 前缀，只看表名，**不看 workspace**。
- M2.2 `candidate_layer`：`config/layer-rules.yaml` 的 workspace_layers（配置事实）+ CDM 子层规则（prefix / suffix），按 workspace_id 判定。

对真实 Snapshot（3719 表）的核查表明 M2.1 的前提不成立：

1. 仓库现状按 Workspace 分层：`dme_ads` 93% 表为 `tb_*`、`dme_ods` 98% 为无前缀裸表名，前缀法对 2565 张表（69%）给不出任何答案；前缀只在 `dme_cdm` 内部有效（94.3% 命中）。
2. 35 张表被判错：`dme_ads.dim_*`、`dme_ods.dws_*` 等物理上属于 ADS / ODS Workspace，M2.1 却按表名判成 DIM / DWD / DWS。
3. M2.1 的输出喂给 M2.4 后信息量不足：血缘边 source 56%、target 63.5% 与核心表候选 74% 的 `layer_candidate` 为空。

即：M2.1 与 M2.2 不是互补关系，而是同一问题的新旧两套答案，旧答案在本项目输入上是错的。

## 决定

1. **M2.2 是本项目唯一的层级判定**：`candidate_layer` 由 workspace_layers 配置事实 + CDM 子层规则产出。
2. **删除 M2.1 的层级产出**：移除 `TableInventory.layer_candidate` / `layer_candidate_evidence` 字段、`naming.LAYER_PREFIXES` 与 `naming.layer_candidate()`；M2.1 回归纯清单。
3. **M2.4 血缘层级标注改读 M2.2**：`LineageEdge.source/target_layer_candidate` 与 `CoreTableCandidate.layer_candidate` 字段保留，值来源改为 M2.2 的 `candidate_layer`；M2.4 不自行判定层级。
4. **执行顺序调整**：M2.1 → M2.2 → M2.3 → M2.4 → M2.5 → Summary（M2.2 只依赖 M2.1 输出与规则配置，先于血缘执行）。
5. **跨层命名提示保留**：ODS / ADS 中命中其他层前缀的表（如 `dme_ads.dim_day`），candidate 仍按 workspace_layer 判定，命中记入 evidence（`cross_layer_hits`）并输出告警日志与 summary 明细，作为「放错层」信号留给后续 Convention Assessment。
6. **UNKNOWN 暂不补规则**：CDM 内 61 张未命中表（`fct_*` 25、`tmp_*` 11、`tb_*` 7 等）保持 UNKNOWN，待后续分析确认归属后再向 `layer-rules.yaml` 追加规则。

## 后果

- 原 `docs/EVIDENCE_LAYER_FREEZE_REPORT.md` 的冻结范围包含 `inventory/inventory.py` / `lineage/lineage.py` / `pipeline.py` 与 `tables.json` / `table-lineage.json` / `Summary.md` 产物，本次决策使这部分**解冻并重新审计**（本 ADR 即记录）。
- 产物格式变化：`inventory/tables.json` 不再含 `layer_candidate` 字段；`Summary.md` 删除原「层级候选（Layer Candidate）」一节，其余章节重编号；`inventory/summary.md` 不再输出层级节；`layer/summary.md` 新增「跨层命名提示」。
- 规则来源从两处收敛为一处：`naming.py` 不再持有任何层级规则，改规则只改 `config/layer-rules.yaml`。
- 层级语义变更的下游：血缘边两端的层级标注在 ODS / ADS 表上从「前缀猜测」变为「Workspace 事实」，覆盖率从约 40% 提升到 100%（除 UNKNOWN 与不在 Inventory 的表）。

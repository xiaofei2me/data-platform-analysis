# Analysis 测试恢复：180 失败只读审计

Status: needs-triage
审计时间：2026-10-08
审计性质：**只读**。本轮未修改 `src/`、`tests/`、`cli.py`、`pipeline.py`、`source/`，未 skip/xfail 任何测试。
唯一新增文件：本文件。

---

## 1. 测试基线

### 1.1 实测数据

| 项 | 值 |
| --- | --- |
| `pytest --collect-only -q` | **390 tests collected** |
| `pytest -q` | **210 passed / 180 failed / 0 skipped** |
| 测试文件数 | 25（16 个有失败，9 个全绿） |

### 1.2 「365 passed」的考证结论：该数字在 Git 历史中不存在

用 `git worktree` 在**独立临时目录**逐个 checkout 历史 commit 实跑 pytest（不触碰当前工作区，不触碰 `source/`）：

| Commit | 主题 | 实测结果 |
| --- | --- | --- |
| `70a5777` | 补充连续引号归一化测试 | 103 passed |
| `00393cd` | 新增 M2.5 层级评估 | 126 passed |
| `cd939f4` | 阶段按执行顺序重编号 | 126 passed |
| `c3d2d27` | 新增 M3～M3.4 业务理解分析链 | 262 passed |
| `a2be05f` | 新增 M3.5～M3.6 分析链 | 368 passed |
| `c61fcb3` | 按 M2/M3/M3.5/M3.6 领域重组源码 | 368 passed |
| `b3d6faa` | 迁移 M3.5/M3.6 产物至 analysis/model 与 review | 370 passed |
| **`b768a0b`（HEAD）** | 重构 M2.1 Inventory Summary 为 9 节报告 | **383 passed / 0 failed** |

**每一个历史 commit 都是全绿的，0 failed。** 最接近 365 的是 `368`（`a2be05f` / `c61fcb3`）。

> **结论：365 不是可复现的 Git 状态**，最可能是对 368/370 的近似记忆，或来自某次未提交的工作区状态。**无法从当前 Git 历史确认 365 这一数字**——但可以确认的是：**历史全绿这一性质是真实的**，且 **HEAD (`b768a0b`) 全绿（383 passed）**。

### 1.3 测试总数为何变化（383 → 390）

| 变化 | 数量 | 说明 |
| --- | ---: | --- |
| 新增未跟踪文件 `tests/test_error_ledger.py` | +7 | 新写的 Technical Error Ledger 测试（4 失败 / 3 通过） |
| 已跟踪测试文件的函数增删 | 0 | `git diff -- tests` 中 `+def test_` = **0**，`-def test_` = **0** |
| **合计** | **+7** | 383 + 7 = 390 ✅ |

**测试总数的全部增量来自一个新增文件，没有任何测试被删除或合并。**

---

## 2. 核心诊断：失败是「工作区未提交的半截重构」造成的，不是历史遗留

### 2.1 决定性证据：交叉实验

在 `/tmp` 建立两个**只读拷贝**（`git archive` + 局部覆盖），分别跑全量测试：

| 实验 | 组合 | 结果 |
| --- | --- | --- |
| 基准 | HEAD 原样 | **383 passed / 0 failed** |
| **A** | HEAD 的 `tests/` + **工作区的 `src/`** | **44 failed / 339 passed** |
| **B** | HEAD 的 `src/` + **工作区的 `tests/`** | **13 errors（collection 阶段即崩）** |
| 现状 | 工作区 `src/` + 工作区 `tests/` | **180 failed / 210 passed** |

**实验 B 的 13 个 collection error**：

```
ModuleNotFoundError: No module named 'data_platform_analysis.analysis.evidence'
ModuleNotFoundError: No module named 'data_platform_analysis.analysis.understanding'
```

→ 工作区 `tests/` 的 **import 已经迁到新包**（`evidence`、`understanding`），在旧 `src` 上直接收集失败。

**实验 A 的 44 个失败**根因分布：

```
11 × 'analysis/sql/statements.json'          ← 旧路径，src 已迁 evidence/
10 × assert 2 == 0                           ← CLI invalid choice
 8 × assert 2 == 1                           ← CLI invalid choice
 2 × 'analysis/lineage/table-lineage.json'   ← 旧路径
 1 × assert 'evidence/layer/assessments.json' == 'layer/assessments.json'
 1 × assert 'analyze-current-state-model' in <cli source>
 1 × assert '完整明细见 analysis/model/fact-candidates.json'
 1 × assert '完整明细见 analysis/business/grain-candidates.json'
 3 × M2/M3/M3.5 产物缺失（understanding/ 新路径）
 ...
```

### 2.2 因果链

工作区处于**四阶段重构的半截状态**：

- **`src/` 已完成迁移**（staged 的 20 个纯重命名 + 957 insertions / 1086 deletions）：
  `analysis/{sql,lineage,profiling,layer}` → `analysis/evidence/*`；
  `analysis/{business,model}` → `analysis/understanding/*`；
  废弃 CLI 子命令已从 `cli.py` 删除。
- **`tests/` 只完成了一半迁移**：
  - ✅ **import 已迁**（所以 collection 能过）
  - ✅ 读产物的断言**部分已迁**（`test_analysis_sql`、`test_analysis_lineage`、`test_analysis_node_eligibility` 等用 `analysis/evidence/...`）
  - ❌ **fixture 写入路径未迁**（仍写 `analysis/sql/`、`analysis/lineage/`、`analysis/layer/`）
  - ❌ **legacy 错误账本断言未迁**（仍读 `analysis/errors.json`）
  - ❌ **CLI 调用未迁**（仍调 `analyze-business` 等已删除子命令）

> **180 = `src/` 迁移领先 × `tests/` 迁移滞后 产生的缺口。**
> 既不是「180 个失败只是因为测试需要迁移」这么简单，也不是 production 逻辑坏了。

### 2.3 9 个全绿测试文件（旁证）

```
✓ tests/test_analysis_inventory.py
✓ tests/test_analysis_lineage.py
✓ tests/test_cli_smoke.py
✓ tests/test_fault_tolerance.py
✓ tests/test_limit.py
✓ tests/test_list_files_pagination.py
✓ tests/test_rerun_semantics.py
✓ tests/test_workspace_config.py
✓ tests/test_workspace_filter.py
```

采集链（export/dataworks/maxcompute）、容错、limit、workspace filter、**rerun semantics** 全部通过——**说明底层 Pipeline 与采集语义完好**。

---

## 3. 180 个失败分类

| 分类 | 数量 | 主要原因 | 需要改 src | 需要改 tests |
| --- | ---: | --- | --- | --- |
| **A. PATH_MIGRATION** | **157** | fixture 写旧路径 / 断言读旧路径，`src` 已迁 `evidence/` | 否（3 处文案见 §4） | **是** |
| **B. CLI_MIGRATION** | **20** | 调用已删除的 `analyze-*` 子命令 | 否 | **是** |
| **C. ASSERTION_FIXTURE_MIGRATION** | **3** | API 形状变化（`ErrorLedger.payload`）+ 1 处 src 文案未迁 | **1 处** | 2 处 |
| D. IMPORT_PACKAGE_REGRESSION | **0** | 完整工作区无任何 import 错误 | — | — |
| E. PIPELINE_REGRESSION | **0** | pipeline 正常执行；210 测试通过 | — | — |
| F. RERUN_SEMANTICS_REGRESSION | **0** | `test_rerun_semantics.py` **全绿** | — | — |
| G. LOGIC_REGRESSION | **0**（未发现，见 §3.1 盲区警告） | 未发现数据计算型失败 | — | — |
| H. TEST_ENVIRONMENT_REGRESSION | **0** | 无 fixture/monkeypatch/cwd/env 问题 | — | — |
| I. TEST_LOSS_OR_UNCLEAR | **0** | 无测试丢失（见 §6） | — | — |
| **合计** | **180** | | | |

### 3.1 A 类细分（157）

| 数量 | 细分 |
| ---: | --- |
| **143** | fixture 构造 M2 输入用旧目录（`sql`/`lineage`/`layer`/`profiling`，缺 `evidence/` 前缀），而 `M2_INPUT_FILES` 读 `evidence/…` → 抛 `BusinessUnderstandingError: M2 产物缺失` |
| 9 | 断言 legacy `analysis/errors.json`（production 已迁至 `analysis/evidence/errors.json`） |
| 3 | 断言 `evidence/errors.json`（缺 `analysis/` 前缀） |
| 1 | 读不存在产物 `model/fact-candidates.json`（应为 `understanding/modeling/…`） |
| 1 | `assert INPUT_FILES[-1] == "layer/assessments.json"`（应为 `evidence/layer/…`） |

**143 个的集中根因是单一 helper**：`tests/test_business_understanding.py` 的 `_write_m2()` 中

```python
payloads = [
    ("sql", "references", ...),
    ("lineage", "edges", ...),
    ("lineage", "candidates", ...),
    ("layer", "assessments", ...),
]
...
path = analysis_dir / folder / names[key]  # ← 缺 evidence/ 前缀
```

→ 写入 `analysis/sql/…`，而 `src/.../understanding/business/understanding.py:95` 的 `M2_INPUT_FILES` 读 `analysis/evidence/sql/…`。

**全仓库没有任何测试使用 `analysis_dir / "evidence"`**（实测 `rg 'analysis_dir / "evidence"'` 零命中）。

### 3.2 B 类细分（20）

| 数量 | 已删除 CLI |
| ---: | --- |
| 12 | `analyze-business` |
| 1 | `analyze-layer` |
| 1 | `analyze-business-grain` |
| 1 | `analyze-business-model` |
| 1 | `analyze-business-objects` |
| 1 | `analyze-business-processes` |
| 1 | `analyze-business-quality` |
| 2 | `analyze-current-state-model`（1 次 `run_cli` + 1 次断言 `cli.py` 源码含该字符串） |

当前 `cli.py` 只接受 6 个子命令：

```
dataworks, maxcompute, export, summary, analyze, config
```

### 3.3 ⚠️ 盲区警告（必须写进修复计划）

**143 个测试在 fixture 阶段就抛 `BusinessUnderstandingError`，M3/M3.5/M3.6 的全部业务逻辑断言根本没有执行到。**

因此「0 个 LOGIC_REGRESSION」的正确解读是：

> **未观察到**数据计算型失败，**而不是已证明**业务逻辑正确。这 143 个测试覆盖的 business understanding / modeling / review 逻辑目前处于**完全未被验证**的状态。

修复 P4（路径迁移）之前，这些区域的逻辑回归是**不可见的**。修复后必须预期可能暴露新的 G 类失败。

---

## 4. 最严重的真实 Regression（production 侧）

这一类与「tests 滞后」不同：是 **`src/` 自身的迁移没做完**，导致**生成的报告包含指向不存在文件的链接**。

### 4.1 决定性事实

`src/data_platform_analysis/analysis/pipeline.py` 实际写入的目录**只有 4 个**：

```
analysis_dir / "evidence"       ← sql, lineage, profiling, layer, errors.json
analysis_dir / "inventory"
analysis_dir / "understanding"  ← business, modeling
analysis_dir / "review"
```

**`analysis/sql`、`analysis/lineage`、`analysis/profiling`、`analysis/layer` 这四个目录 production 根本不再写入**（旧目录已从文件系统消失，实测 `gone`）。

### 4.2 失效引用清单

| # | 位置 | 内容 | 应为 | 性质 |
| --- | --- | --- | --- | --- |
| 1 | `inventory/inventory.py:128` | `"明细见 analysis/errors.json）"` | `analysis/evidence/errors.json` | **logger 文案指向错误文件** |
| 2 | `reports.py:414` | ``"明细见 `analysis/errors.json`。"`` | `analysis/evidence/errors.json` | **M2.1 报告正文链接失效** |
| 3 | `reports.py:856,858,866,868,881,883` | `` `analysis/layer/assessments.json` ``（6 处） | `analysis/evidence/layer/…` | 报告正文链接失效 |
| 4 | `reports.py:2812` | `` `analysis/lineage/core-table-candidates.json` `` | `analysis/evidence/lineage/…` | 报告正文链接失效 |
| 5 | `reports.py:2854` | `` `analysis/layer/summary.md` `` | `analysis/evidence/layer/summary.md` | 报告正文链接失效 |
| 6 | `reports.py:2866` | `` `analysis/evidence/errors.json`，…`analysis/sql/parse-errors.json` `` | 后半段应为 `analysis/evidence/sql/…` | **同一行内新旧混用** |
| 7 | `reports.py:740,785,814,2644,2891` | docstring 声称生成 `analysis/{lineage,profiling,layer,Summary.md}` | 实际写 `evidence/…` | 文档性，但会误导 agent |

`rg` 统计：`reports.py` 含 `analysis/(sql|lineage|profiling|layer)/` 共 **12 处**。

### 4.3 唯一被测试捕获的一例

```
tests/test_error_ledger.py::test_summaries_agree_with_ledger
  >  assert "明细见 `analysis/evidence/errors.json`" in inventory
  E  AssertionError: assert '明细见 `analysis/evidence/errors.json`' in '# M2.1 Warehouse Inventory...'
```

- production（`reports.py:414`）输出**旧** `analysis/errors.json`
- ledger 实际写在 `analysis/evidence/errors.json`
- → 报告指向的文件**不存在**

**同时存在反向矛盾**：

| 测试 | 期望 | 结果 |
| --- | --- | --- |
| `test_error_ledger.py:158` | `明细见 analysis/evidence/errors.json` | ❌ 失败（production 未迁） |
| `test_inventory_summary.py:425` | `明细见 analysis/errors.json` | ✅ 通过（与 production 的旧值一致） |

**两个测试对同一行文案的期望互相冲突**，其中一个是错的。修复时必须先裁定：**以 ledger 的实际落盘位置 `analysis/evidence/errors.json` 为准**（`pipeline.py:181,363` + `PRODUCTION_FILES = ("evidence/errors.json", ...)`）。

| 字段 | 内容 |
| --- | --- |
| 测试 | `test_summaries_agree_with_ledger` |
| 文件 | `src/data_platform_analysis/analysis/reports.py:414`（及 §4.2 全表） |
| 错误 | 报告正文引用 `analysis/errors.json`，文件实际在 `analysis/evidence/errors.json` |
| 根因 | 错误账本迁移时未同步更新报告文案与 logger 文案 |
| 影响范围 | **所有生成的 `inventory/summary.md` 与 Summary 报告**都含失效链接；§4.2 中第 3–6 项**尚无任何测试覆盖** |
| 建议修复方向 | 统一以 `pipeline.py` 的 `PRODUCTION_FILES` 为路径唯一来源，让 reports/inventory 引用同一常量，而非硬编码字符串 |

### 4.4 次级：`ErrorLedger` API 不一致（2 例）

```
tests/test_error_ledger.py::test_ledger_payload_covers_all_stages
tests/test_error_ledger.py::test_ledger_payload_is_deterministic
  E  AttributeError: 'ErrorLedger' object has no attribute 'payload'
```

测试调用 `ledger.payload()`，该方法已不存在。需确认是 `src` 删了该方法还是改名为别的——**属于 API 契约变更，未记录**。

---

## 5. 测试迁移问题（路径）

| 旧路径 | 新路径 | 受影响测试 | 建议修改方式 |
| --- | --- | --- | --- |
| `analysis/sql/` | `analysis/evidence/sql/` | `test_business_understanding`(helper `_write_m2`)、`test_business_objects`、`test_business_grain`、`test_business_model` 等 | **改 `_write_m2()` 的 folder 元组**（`sql`→`evidence/sql`），预期一次覆盖 143 中的大部分 |
| `analysis/lineage/` | `analysis/evidence/lineage/` | 同上 + `test_business_objects:299`、`test_business_grain:338`、`test_business_model:165` | 同上 |
| `analysis/layer/` | `analysis/evidence/layer/` | `test_business_understanding`(assessments)、`test_model_review:702` | 同上 |
| `analysis/profiling/` | `analysis/evidence/profiling/` | `test_business_grain`、`test_business_model` | 同上 |
| `analysis/errors.json` | `analysis/evidence/errors.json` | `test_analysis_node_eligibility`×5、`test_analysis_sql`×2、`test_ctas_fallback`、`test_golden_504340939`、`test_inventory_summary`、`test_analysis_layer_assessment`、`test_error_ledger`（9 例断言） | 断言路径改新值 |
| `evidence/errors.json` | `analysis/evidence/errors.json` | `test_analysis_sql::test_parse_error_isolation` 等 3 例 | 补 `analysis/` 前缀 |
| `analysis/model/` | `analysis/understanding/modeling/` | `test_model_review`、`test_business_model` | 路径改新值 |
| `analysis/business/` | `analysis/understanding/business/` | `test_business_*` 多处（部分**已迁**，如 `analysis/understanding/business` 断言已存在） | 核对剩余未迁点 |

**注意**：`test_business_*` 中已经存在 `Path("analysis/understanding/business")` 形式的断言（说明 output 路径已迁），但**输入 fixture 未迁**——同一个文件里新旧并存。

---

## 6. CLI 迁移问题

| 旧 CLI | 新 CLI | 受影响测试（数） |
| --- | --- | --- |
| `analyze-layer` | 并入 `analyze` | `test_analysis_layer_assessment` (1) |
| `analyze-business` | 并入 `analyze` | `test_business_understanding`(3)、`test_business_grain`(2)、`test_business_model`(2)、`test_business_objects`(2)、`test_business_processes`(2)、`test_business_quality_assessment`(2)、`test_model_review`(1)、`test_problem_assessment`(1) = **12** |
| `analyze-business-grain` | 并入 `analyze` | `test_business_grain` (1) |
| `analyze-business-model` | 并入 `analyze` | `test_business_model` (1) |
| `analyze-business-objects` | 并入 `analyze` | `test_business_objects` (1) |
| `analyze-business-processes` | 并入 `analyze` | `test_business_processes` (1) |
| `analyze-business-quality` | 并入 `analyze` | `test_business_quality_assessment` (1) |
| `analyze-current-state-model` | 并入 `analyze` | `test_model_review` (2) |

**不要恢复旧 CLI。** 当前正式 CLI 为：`dataworks | maxcompute | export | summary | analyze | config`。

⚠️ 需要**先裁定**的语义问题：旧设计里 `analyze` 只跑 M2、`analyze-business` 跑 M3，测试 `test_analyze_command_does_not_run_business_stage` 断言 `analyze` **不产出** `analysis/understanding/business`。若新设计是 `analyze` 一次跑完 M2–M3.6，则这两条测试的**语义期望本身要重写**（不只是改命令名）。这属于**设计决策**，应交人工确认，不在机械迁移范围内。

---

## 7. 测试丢失情况

> **365 个历史通过测试是否仍然全部存在？**

**是——且比 365 更多。没有丢失任何测试。**

证据：

1. 测试文件数**单调递增**：7 → 10 → 11 → 12 → 14 → 15 → 20 → 23 → 24 → 25（+1 个未跟踪新文件）。
2. `git diff -- tests` 中 `-def test_` = **0**，`+def test_` = **0**——已跟踪文件里**没有任何测试函数被删除或新增**，只有一行内容修改（327 insertions / 414 deletions）。
3. `rg -n "skip|xfail" tests/` **零命中**——没有测试被改成 skip 或 xfail。
4. 逐 commit 实跑：103 → 126 → 126 → 262 → 368 → 368 → 370 → **383**，全部 passed。
5. 新增 `tests/test_error_ledger.py`（7 个测试，未跟踪）使总数达到 390。

**「365」本身无法在 Git 历史中定位**（最近的是 368），但**测试丢失不存在**这一结论是确定的。

`git diff -- tests` 的改动性质（抽样）：

```
-from data_platform_analysis.analysis.layer.layer_assessment import (
-    data = _read(Path("analysis/layer/assessments.json"))
-    summary = Path("analysis/layer/summary.md").read_text(...)
-    assert Path("analysis/layer/assessments.json").exists()
-    lineage = _read(Path("analysis/lineage/table-lineage.json"))
```

→ 改动是**路径与 import 迁移**，不是删除测试或削弱断言。改动量最大的文件：

| 文件 | +/- |
| --- | --- |
| `test_business_objects.py` | +42 / −61 |
| `test_business_grain.py` | +41 / −72 |
| `test_model_review.py` | +33 / −69 |
| `helpers.py` | +32 / −0 |
| `test_business_model.py` | +26 / −30 |

---

## 8. Source 安全

| 项 | 值 |
| --- | --- |
| `source/` 文件数 | **13004**（审计前后一致） |
| `/tmp/source-files.txt` 校验 | **零差异** ✅ |
| `/tmp/source-checksums.txt`（全量 shasum）校验 | **零差异** ✅ |
| `source/` 是否被修改 | **否** |
| `source/` 是否被删除 | **否** |
| `git status --short -- source` | 空（注意：`source/*` 被 `.gitignore:40` 忽略，**Git 看不到它的变化，必须靠 checksum**） |

本轮所有 pytest 运行均未触及真实 `source/`。

### 8.1 `source/` 写操作扫描

**A. 直接写/删 `source/` 的位置（4 处，全部已被 `assert_sandbox` 保护）：**

```
tests/test_error_ledger.py:49           assert_sandbox(...dwd_order.json).unlink()
tests/test_inventory_summary.py:229     shutil.rmtree(assert_sandbox(...9002))
tests/test_inventory_summary.py:330     assert_sandbox(...101__etl_a.sql).unlink()
tests/test_inventory_summary.py:446     assert_sandbox(...dwd_order.json).unlink()
```

**B. `assert_sandbox` 覆盖点：**

| 文件 | 次数 |
| --- | ---: |
| `tests/helpers.py`（定义 + `write_snapshot` 入口） | 2 |
| `tests/test_inventory_summary.py`（本地 `_write_json` + 3 处直接操作） | 5 |
| `tests/test_golden_504340939.py`（`prepare_snapshot` 的 `rmtree`） | 3 |
| `tests/test_analysis_sql.py` | 2 |
| `tests/test_error_ledger.py` | 2 |

**C. `write_snapshot(Path("source"), ...)` 调用点**：分布于 11 个测试文件，全部经 `helpers.write_snapshot` 入口的 `assert_sandbox` 拦截。

**D. 结论**：当前**不存在**未受保护的 `source/` 写路径。所有写操作依赖 `cli_env` 的 `chdir(tmp_path)`（隐式），`assert_sandbox` 是显式的最后一道闸门。读取操作（`.exists()` / `.read_text()` / `source_tree_hash`）全部只读，符合规则。

**E. 未执行的危险命令**：本轮未执行 `rm -rf source`、`git clean -fd(-x)`、`git reset --hard`。

---

## 9. Analysis 四阶段结构核查

**目标结构完全达成，旧目录已不存在：**

```
src/data_platform_analysis/analysis/
├── inventory/
├── evidence/
│   ├── layer/          ✅
│   ├── lineage/        ✅
│   ├── profiling/      ✅
│   └── sql/            ✅
├── understanding/
│   ├── business/       ✅
│   └── modeling/       ✅
└── review/             ✅
```

| 旧目录 | 状态 |
| --- | --- |
| `analysis/layer` | **gone** |
| `analysis/lineage` | **gone** |
| `analysis/profiling` | **gone** |
| `analysis/sql` | **gone** |

**但 `src/` 内部仍残留 30+ 处旧路径字符串**（§4.2 已列运行时文案 12 处 + 大量 docstring）。旧目录名虽已删除，**字符串引用未同步清理**。

---

## 10. Runtime 输出（`analysis/`）

```
find analysis  →  No such file or directory
```

| 项 | 状态 |
| --- | --- |
| `analysis/` 目录 | **当前不存在**（0 个文件） |
| 是否在 HEAD 中 | 否（`git ls-tree HEAD -- analysis` 为空） |
| 历史 | `089d593 chore: 移出 analysis/ 产物并恢复 gitignore 忽略`、`3a7079a chore: analysis 生成产物移出仓库并启用 gitignore` |

因此本轮**无法读取现存 `analysis/` 产物**。所有对 runtime 输出的判断均来自测试内 `tmp_path` 的实际执行日志（如 `analysis/evidence/layer/assessments.json`、`analysis/understanding/business/…`、`analysis/review/…` 的 `INFO 产物已写出` 日志），这些日志证明 **pipeline 在 tmp 沙盒中完整跑通了四阶段**。

---

## 11. 备份文件污染

```
src/data_platform_analysis/analysis/pipeline.py.backup
src/data_platform_analysis/analysis/pipeline.py.bak
src/data_platform_analysis/analysis/cli 相关 → src/data_platform_analysis/cli.py.backup
src/data_platform_analysis/cli_old_backup.py          ← 唯一的 .py
```

| 问题 | 结论 |
| --- | --- |
| 1. 是否被 Python package/import 加载？ | **不会自动加载**。`data_platform_analysis/__init__.py` 为空，`rg "cli_old_backup"` 在 `src`+`tests` **零命中**。3 个 `.backup`/`.bak` 非 `.py` 后缀，不可 import。**但 `cli_old_backup.py` 是合法模块，任何 `import` 都能加载它**。 |
| 2. 是否可能被 AI 当成当前实现参考？ | **是，高风险**。文件名带 `backup`/`old` 且内容是**旧版 CLI 完整实现**，与现行 `cli.py` 并存于同一包内，极易被搜索/读取时误认为现行实现。 |
| 3. 是否影响 pytest collection？ | **否**。`pytest --collect-only` 中零命中 backup。 |
| 4. 是否影响 ruff/mypy？ | **部分是**。`mypy`（`files=["src"]`）报告中 **0 处** backup；但 **`ruff check` 默认扫描到 `cli_old_backup.py` 并报 2 errors**——项目整体 `ruff check` 42 errors 中有 2 个来自该备份文件（纯噪音）。 |
| 5. 是否存在重复实现造成误判？ | **是**。`pipeline.py` / `pipeline.py.bak` / `pipeline.py.backup` 三份实现，`cli.py` / `cli.py.backup` / `cli_old_backup.py` 三份实现。 |

**本轮未删除任何备份文件**，仅记录。

---

## 12. 修复优先级（下一阶段建议顺序）

| 优先级 | 项目 | 动作 | 预期消除失败数 | 需改 |
| --- | --- | --- | ---: | --- |
| **P0** | 真实 production regression：报告文案指向失效路径 | 让 `reports.py` / `inventory.py` 引用 `pipeline.PRODUCTION_FILES` 等同一路径常量，消除 §4.2 全部 12 处硬编码；同时**裁定** `test_error_ledger` 与 `test_inventory_summary` 对同一文案的冲突期望 | 1（并消除**无测试覆盖**的隐患） | **src** |
| **P1** | `ErrorLedger.payload` API 缺失 | 确认 API 去向，恢复方法或改测试 | 2 | src 或 tests |
| **P2** | pipeline / rerun regression | **无需修复**——`test_rerun_semantics`、`test_analysis_inventory`、`test_analysis_lineage`、采集链 9 文件全绿 | 0 | — |
| **P3** | test environment regression | **无需修复**——0 例 | 0 | — |
| **P4** | 路径迁移（**最大头**） | 修 `test_business_understanding._write_m2()` 的 folder 元组（`sql`→`evidence/sql` 等），再逐文件修剩余 fixture 与断言 | **157** | tests |
| **P5** | CLI 迁移 | 把 20 处 `analyze-*` 调用改为 `analyze`；**先裁定** §6 末尾的语义问题（`analyze` 是否跑 M3） | 20 | tests |
| **P6** | assertion / fixture 迁移 | 与 P4 合并处理（A 类已并入 P4，C 类余量并入 P1/P0） | 0 | tests |

### 执行顺序建议

```
第 1 步  P0 + P1（src 侧，先把 production 自身的迁移补完）
第 2 步  P5 的语义裁定（人工决策：analyze 是否一站式跑 M2–M3.6）
第 3 步  P4（改 _write_m2 单点 → 观察 143 失败的坍缩，再清剩余）
第 4 步  P5 机械替换
第 5 步  重新全量跑测，预期会出现新的失败——那是 §3.1 盲区里
         首次真正被执行到的业务逻辑断言，属正常暴露，逐个评估
```

### 风险提示

1. **P4 之后不要假定回到 0 failed。** 143 个测试此前从未跑到业务断言，路径修好后很可能暴露真正的 LOGIC_REGRESSION（G 类）。届时的失败才是有价值的新信息。
2. **P5 涉及产品语义**，不是纯机械替换，必须先有人拍板 `analyze` 的阶段覆盖范围。
3. **`source/` 在任何步骤中都只读**；每轮修复后重新执行 §8 的 checksum 校验。

---

## 13. 本轮成功判据自评

| 判据 | 状态 |
| --- | --- |
| 准确解释 180 失败来自哪里 | ✅ 157 路径 + 20 CLI + 3 API/文案 = 180 |
| 与「测试需要迁移」的朴素判断的区别 | ✅ 定位到**单点根因** `_write_m2()` 的 folder 元组，并用交叉实验证明是 `src` 领先 / `tests` 滞后的半截重构 |
| 是否发现真 production regression | ✅ §4 报告文案指向失效路径（12 处，仅 1 处有测试） |
| 是否给出可执行修复计划 | ✅ §12 P0–P6 |
| `src/` 未修改 | ✅ |
| `tests/` 未修改 | ✅ |
| `source/` 未修改 | ✅ 13004 文件，checksum 零差异 |
| CLI / Pipeline 未修改 | ✅ |
| 未 skip/xfail/删除测试 | ✅ |
| 未执行 `git clean` / `git reset --hard` | ✅ |

**本轮交付的是诊断结果，不是修复完成结论。**

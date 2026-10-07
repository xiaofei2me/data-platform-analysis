# M3.6 Human Adjudication 工作指南

> **这份文档给谁看**：数据团队、业务专家、数据仓库负责人。不需要读代码，不需要装环境，只需要能打开 Markdown 文件和问业务问题。
>
> **这份文档要达成什么**：读完之后，你可以拿着 `analysis/review/current-state-problem-review-checklist.md` 直接组织第一轮人工裁决，把机器产出的 **Problem Candidate** 变成有业务含义的 **Confirmed Problem / Rejected Problem**。
>
> **关联文档**：方法论（为什么这样设计）见 [docs/M36_PROBLEM_ASSESSMENT.md](M36_PROBLEM_ASSESSMENT.md)；本指南只讲**怎么干活**。
>
> **数据基准**：本仓库 `analysis/` 当前快照 —— 3719 张表 / 4439 条 Finding / 1190 条 Problem Candidate。

---

## 阅读方式

| 你现在的状态 | 先读哪几章 |
| --- | --- |
| 第一次接触，想知道「这跟我有什么关系」 | 第一章、第二章 |
| 要开始组织人干活 | 第三章、第四章、第五章 |
| 手上已经有一条 Problem，要下结论 | 第六章（标准流程）、第七章（模板） |
| 遇到某一类问题不会判 | 第八章（13 类逐一对照） |
| 遇到容易吵起来的争议 | 第九章（Grain / Overlap / Duplication / Aggregate） |
| 遇到 UNKNOWN 或 Fact Gate | 第十章、第十一章 |
| 要汇报进度、准备进入 M4 | 第十二章、第十四章 |
| 要排班 | 第十五章 |
| 想看完整示例 | 第十六章（三个案例） |

---

## 第一章 我现在到底在干什么

### 1.1 系统已经替你做完的事

当前平台的分析链（M3.1 ～ M3.6 v2）已经完成以下工作，全部是只读、自动、可重复运行的：

| 系统已经做了 | 说明 |
| --- | --- |
| 发现候选问题 | 从 3719 张表的元数据、字段、血缘、SQL 中提取结构现象，产出 **4439 条 Finding** |
| 整理证据 | 每条问题都挂上可追溯的证据（表、字段、粒度候选、过程、血缘边），共 **30201 行证据** |
| 计算影响 | 按固定词汇推导影响类型（指标口径、查询复杂度、维护成本……） |
| 推测根因 | 按固定词汇给出候选根因（同一模型多粒度、重复加工链路……），证据不足时写 `UNKNOWN` |
| 生成重构理由 | 每条问题都写好「为什么现在要改」的候选表述 |
| 排优先级 | 按关联 Finding 的优先级给出 P0 / P1 / P2 / P3 |

### 1.2 系统不能替你做的事

以下问题**机器没有能力回答，也刻意不回答**：

| 系统不能决定 | 为什么 |
| --- | --- |
| 这个问题在业务上是否真实存在？ | 机器只有结构证据，没有业务语义 |
| 这个模型是不是合法的设计？ | 合法性是业务约定，不是字段统计 |
| 两个相似表是不是**故意**存在的？ | 可能是不同源系统、不同 BU、不同生命周期 |
| 一个聚合表是不是合理的？ | 取决于它的口径是否稳定、能否回溯 |
| 这个 grain 到底哪个才是业务 grain？ | 候选键由字段名形态推出，无行级样本 |
| 哪一张是权威表、先收敛哪一张？ | 权威性是组织与治理判断 |

### 1.3 一句话定位

> **Human Adjudication 的目的不是找更多问题，而是确认机器已经发现的问题。**

整个流程是单向的：

```text
Machine Analysis（机器分析）
        ↓
Problem Candidate（问题候选）
        ↓
Human Adjudication（人工裁决）   ← 你现在在这里
        ↓
Confirmed / Rejected（确认 / 否决）
        ↓
Refactoring Evidence（重构证据）
        ↓
M4 Target Model（目标模型，尚未开始）
```

**人工裁决不是重新做一次机器分析。** 你的工作只有一件事：

> **判断机器发现的候选问题，是否真的代表当前数据模型中的业务 / 建模问题。**

---

## 第二章 三个数字：4439 / 1190 / 0

打开任何 M3.6 v2 产物，你都会看到这三个数字。它们**永远不相等，也永远不会相等**。

```text
4439
↓
机器观察到的 Finding（一条 = 一次结构观测）

1190
↓
机器聚合出来的 Problem Candidate（一条 = 一个候选问题）

0
↓
目前还没有经过人工确认的 Problem
```

### 2.1 逐个解释

**4439 —— Finding（评审发现）**

- 一条 Finding 只记录一个现象，例如「这张表的候选键与落表不一致」「这两张表字段重合 0.98」。
- Finding **不含对错判断**，全部是 `candidate` 状态。
- 4439 里包含大量同一问题的多个侧面（一张表可以有 3 条粒度 finding）。

**1190 —— Problem Candidate（问题候选）**

- 机器把同一根因下的多条 Finding 聚合成一条 Problem，所以数字下降。
- 聚合规则举例：同表多条粒度 finding → 1 条 `GRAIN_PROBLEM`；字段重合的表对先连成表簇 → 1 条 `MODEL_OVERLAP` / `MODEL_DUPLICATION`。
- 状态分布：`candidate` 1148 + `review_required` 42 + `confirmed` 0 + `rejected` 0。

**0 —— Confirmed（已确认问题）**

- `confirmed` **只能由人在清单里回填产生**，机器永远不会写。
- 今天看到 0 是**设计结果**，不是数据缺失、不是分析失败。

### 2.2 必须避免的三句错话

| 错误说法 | 正确说法 |
| --- | --- |
| 「平台有 1190 个错误」 | 「平台有 1190 条问题候选，尚无人工确认」 |
| 「平台必须整改 1190 个问题」 | 「裁决后才知道哪些要改、哪些是合理设计」 |
| 「4439 个问题」 | 「4439 条观测（Finding），已聚合成 1190 条候选」 |

> **只有人工确认后，Problem Candidate 才成为 Confirmed Problem。**

### 2.3 一并要记住的账目

| 指标 | 值 | 含义 |
| --- | --- | --- |
| Finding → Problem 覆盖 | 4427 / 4439 | 未进入 Problem 的 12 条全部是 `aggregate_fact`，被评估为合法聚合、**有意不成问题** |
| Problem 优先级 | P0 698 / P1 378 / P2 99 / P3 15 | 按行内 `priority` 列排期，不按类型推断 |
| 证据强度 | strong 1137 / moderate 20 / weak 33 | strong = 证据类型 ≥4，**仍需人工确认** |
| 受影响表（去重） | 3345 | 不是「3345 张表都有问题」 |
| Finding 清单回填 | 157 行（5 个分区） | 与 Problem 清单**各自独立、互不替代** |
| Problem 清单回填 | 260 行（13 个分区） | 清单每区最多显示 50 行，全量 1190 条见 JSON |

---

## 第三章 人工裁决的状态机

### 3.1 状态流转

```text
candidate            机器认为存在问题，但还没有人工确认
    ↓
review_required      机器证据不足，或问题依赖较强语义，必须人工重点看
    ↓  （人来判断）
confirmed            人工确认：当前确实存在该模型问题
    或
rejected             人工确认：当前模型设计是合理的，机器判断不成立
```

> 说明：`candidate` 与 `review_required` 都是**机器阶段**的状态——机器会直接把证据不足的条目标成 `review_required`（当前 42 条），不是先变成 candidate 再升级。二者的共同点是：**都还没有人工结论**。

### 3.2 每个状态的含义

| 状态 | 谁能产生 | 含义 | 你可以怎么处理 |
| --- | --- | --- | --- |
| `candidate` | 机器 | 有问题嫌疑，证据已齐，等人工表态 | 按标准流程审，给 `confirmed` / `rejected` / `needs_review` |
| `review_required` | 机器（证据弱，或粒度 / 聚合类判为存疑） | 机器自己都不敢下结论，**必须人看** | 补证据后再定，不要强行 `confirmed` |
| `confirmed` | **只能由人** | 当前确实存在该模型问题 | 记录证据与业务解释，进入重构证据 |
| `rejected` | **只能由人** | 模型设计合理，机器判断不成立 | 在 note 里写清「合理解释」，防止下轮重复讨论 |

### 3.3 清单里怎么填（`human_status` 列）

清单只认以下取值（大小写、空格、连字符不敏感）：

| 你填的 `human_status` | 重跑后 Problem 的 `status` | 说明 |
| --- | --- | --- |
| `pending` | `candidate` | 默认值，未回填 |
| `confirmed` | `confirmed` | 唯一算「人工已裁决」的值（`human_validated = true`） |
| `rejected` | `rejected` | 人工否决 |
| `needs_review` | `review_required` | 还需补证据 / 还没想清楚 |
| `needs_discussion` | `review_required` | 需要开会讨论 |
| 其它任何取值 | 按未回填处理 | 系统会输出 warning，不会报错 |

### 3.4 当前 42 条 `review_required` 的来源

机器已经主动标出「我看不准」的 42 条，第一批应该处理它们：

| 来源类型 | 条数 | 为什么机器看不准 |
| --- | --- | --- |
| `FACT_IDENTIFICATION_PROBLEM` 表级 | 23 | 只有 1–2 类证据（weak），缺度量但形态可能是合法事实 |
| `AGGREGATION_MODEL_PROBLEM` | 9 | 血缘里找不到事实上游，聚合口径无法回溯 |
| `MODEL_ROLE_AMBIGUITY` | 4 | Object 角色由锚点关系推导，非业务定义 |
| `SEMANTIC_AMBIGUITY` | 3 | 只有技术引用 / 共现证据，缺业务语义 |
| `UNKNOWN_MODEL` | 2 | 证据类型只有 1–2 类 |
| `DIMENSION_IDENTIFICATION_PROBLEM` | 1 | 维度来自 Object 派生，证据薄 |

### 3.5 铁律

> **机器不得自动产生 `confirmed`。** 任何时候你在产物里看到 `confirmed > 0`，那一定是人回填过。

---

## 第四章 人工到底应该看哪些文件

### 4.1 文件清单

以下路径均以仓库根目录为起点，实际路径**以仓库实现为准**（M3.6 v2 产物都在 `analysis/review/` 下）。

| 文件 | 用途 | 人工是否需要看 |
| --- | --- | --- |
| `analysis/review/current-state-problem-review-checklist.md` | **人工裁决唯一入口**，13 类分区、可回填 | **是（主战场）** |
| `analysis/review/current-state-problems.json` | 完整 Problem 数据（1190 条，含 priority / root_cause / rationale） | **是（查全量时）** |
| `analysis/review/current-state-problem-evidence.json` | 完整证据链（30201 行，可追溯到表 / 字段 / 粒度 / 血缘） | **是（深挖时）** |
| `analysis/review/current-state-problem-summary.md` | 总体统计（分布、影响、根因、Top 20） | **是（看全局）** |
| `analysis/review/current-state-review-checklist.md` | Finding 侧人工清单（5 个分区、157 行） | 是（与 Problem 清单**独立**，要单独回填） |
| `analysis/review/current-state-findings.json` | 全量 4439 条 Finding | 需要追某条 finding 时 |
| `docs/M36_PROBLEM_ASSESSMENT.md` | 方法论：Finding ≠ Problem、13 类 taxonomy、四条原则 | **第一次阅读** |
| `source/` | 原始平台快照（DataWorks 文件内容、表元数据） | 必要时 |
| `analysis/sql/statements.json`、`analysis/lineage/table-lineage.json` | SQL 原文与表级血缘 | 深入验证时 |

### 4.2 三个必须知道的展示限制

**限制一：清单每区最多 50 行**

```text
current-state-problem-review-checklist.md  →  13 个分区，每区 ≤50 行，合计 260 行
current-state-problems.json                →  全量 1190 条
```

清单顶部会明确写「只列出前 50 行，共 N 行；其余行见 ……」。**这不代表只有这些问题。**

**限制二：清单的行顺序是固定的**

排序规则 = `priority → problem_type → scope → scope_key`，稳定排序、不含抽样。也就是说：

- 不在清单里的 930 条问题（1190 − 260），**在当前数据下不会自动轮换出现**；
- 对这些问题，结论要记在团队自己的裁决台账里（用第七章模板），不要指望重跑后自动保留。

> **进阶注意（涉及重跑行为，务必理解）**：如果确实要把清单外问题的结论写进系统，可以按清单同样的 10 列格式在文件末尾追加一行（`problem_id` 必须是真实存在的编号，列数与表头对齐）。下次运行会读到它并把状态写进 `current-state-problems.json`；但运行后清单会被**重新生成**，只渲染每区前 50 行，**你追加的行会消失**，再下一次运行状态就会回退成 `candidate`。所以：
> - **外部裁决台账才是主记录**；
> - 清单是系统识别的入口，两者都要维护。

**限制三：单条 Problem 的证据在 JSON 里只放 5 条样例**

- `current-state-problems.json` 每条只留 5 条证据样例 + `evidence_total` 总数；
- 完整证据（每条 ≤50 行）在 `current-state-problem-evidence.json`；
- 有 53 条 Problem 的证据超过 50 行被截断（看 `evidence_truncated`），全量以 evidence 文件为准。

### 4.3 两个清单，各自独立

| 清单 | 裁决对象 | 分区 | 当前状态 |
| --- | --- | --- | --- |
| `current-state-review-checklist.md` | 4439 条 Finding | 5 个 review group | 157 行全部 `pending` |
| `current-state-problem-review-checklist.md` | 1190 条 Problem | 13 类 | 13 区全部 `pending` |

> **确认一条 Finding 不会把对应 Problem 变成 confirmed，反之亦然。两个清单互不替代。**

### 4.4 回填操作步骤（照做即可）

1. 打开 `analysis/review/current-state-problem-review-checklist.md`；
2. **只改后三列**：`human_status` / `human_name` / `note`（前面的机器列由系统生成）；
3. **不要改列名、不要删列、不要改表结构**——清单必需列是 `problem_id` / `human_status` / `human_name` / `note`，缺一列系统会直接报错（退出码 1）；
4. 保存后重跑一次：

   ```bash
   uv run data-platform-analysis analyze-current-state-model
   ```

5. 重跑后 `current-state-problems.json` 与 `current-state-problem-summary.md` 里的 `status`、`confirmed` 计数才会更新；
6. 人工三列在重跑时会被原样保留；机器列会被覆盖（所以不要手改机器列）；
7. **重跑前建议先备份清单**（提交到 git 或复制一份），避免误操作丢失回填。

---

## 第五章 不要一次处理 1190 个

1190 条不是让你逐条从头看到尾。按优先级分三批，**第一批只做 698 条 P0 里的核心议题，而且第一周只做清单可见部分**。

### 5.1 第一优先级：P0（698 条）

| 类型 | P0 条数 | 关注点 |
| --- | --- | --- |
| `GRAIN_PROBLEM` 粒度问题 | 559 | 哪一组键才是业务粒度 |
| `MIXED_RESPONSIBILITY` 职责混杂（被 finding 抬到 P0 的部分） | 130 | 一张表到底承担几种职责、要不要拆 |
| `MODEL_ROLE_AMBIGUITY` 角色歧义 | 4 | Object 的唯一模型角色 |
| `FACT_IDENTIFICATION_PROBLEM`（stage 侧，闸门口径） | 3 | Fact Gate 排除是否合理 |
| `MODEL_COVERAGE_GAP` 过程覆盖缺口 | 2 | 过程存在但没有事实进入模型 |

P0 是目标模型的骨架：**粒度、角色、过程覆盖不裁决，M4 无法起步。**

重点类型：

```text
GRAIN_PROBLEM
MIXED_RESPONSIBILITY
MODEL_ROLE_AMBIGUITY
```

### 5.2 第二优先级：P1（378 条）

| 类型 | 条数 | 关注点 |
| --- | --- | --- |
| `MODEL_DUPLICATION` 模型重复 | 317 | 权威表是哪一张、哪些是副本 |
| `MODEL_OVERLAP` 模型重叠 | 27 | 是否同一逻辑模型的多份表达 |
| `FACT_IDENTIFICATION_PROBLEM` 表级 | 23 | 缺 measure 的表是否仍是事实 |
| `MODEL_SELECTION_AMBIGUITY` 模型选择歧义 | 8 | 一个过程下该收敛成几个模型 |
| `SEMANTIC_AMBIGUITY` 语义歧义 | 3 | 只有技术证据的关系能不能当业务关系 |

P1 决定**收敛范围、职责边界与事实覆盖**，直接影响改造工作量。

### 5.3 第三批：特殊审计（并行，不阻塞）

| 类型 | 条数 | 性质 |
| --- | --- | --- |
| `FACT_IDENTIFICATION_PROBLEM` stage 侧 | 3 | 审计：验证**分析规则**是否存在语义盲区 |
| `UNKNOWN_MODEL` 未定模型 | 2 | 审计：确定范围归属，不是判错 |

配套的两个审计数字：

```text
Fact Gate:
3364 pass
2315 fail（全部 no_measure_evidence）

UNKNOWN:
NO_ANCHOR = 463
NO_EVIDENCE = 1578
```

> **不要直接 confirm 这两批。** 它们要回答的是「分析规则是否盲区」，不是「表是否有错」。做法见第十章、第十一章。

### 5.4 P2 / P3

| 优先级 | 条数 | 构成 | 建议 |
| --- | --- | --- | --- |
| P2 | 99 | `AGGREGATION_MODEL_PROBLEM` 22 + `MIXED_RESPONSIBILITY` 74 + `UNKNOWN_MODEL` 2 + `DIMENSION_IDENTIFICATION_PROBLEM` 1 | P0/P1 之后处理 |
| P3 | 15 | `PROCESS_MODEL_ALIGNMENT` 15（信息性） | 可批量处理，问「是否需要区分过程与子过程」 |

> **排期只看清单行内的 `priority` 列**，不要按类型推断——`MIXED_RESPONSIBILITY` 类型默认 P1，但实测 130 条落在 P0、74 条落在 P2。

---

## 第六章 每个 Problem 应该怎么审（标准流程）

拿到一条 Problem 后，按顺序回答 Q1–Q7。**任何一问答不上来，都不要强行 `confirmed`。**

### Q1：Finding 本身成立吗？

系统说「存在 grain conflict」「这两张表字段重合 0.98」——**证据是否真实**？

- 打开 `current-state-problem-evidence.json`（或 JSON 里的 evidence 样例），核对表名、字段、候选键是否真的存在；
- 看 `evidence` 列的构成（如 `FINDING×1、TABLE×1、COLUMN×3、PROCESS×1、GRAIN×3`）；
- 若证据指向的表 / 字段根本不存在或明显对不上 → **Finding 不成立**，后续问题不用问了。

### Q2：这些 Finding 是否属于同一个问题？

机器把多条 finding 聚成一条 Problem。例如「10 张表高度相似」被聚成 1 条 `MODEL_OVERLAP`。

- 这 10 张表真的属于**同一个业务模型问题**吗？
- 还是碰巧字段命名相似、被连通分量算法串在一起？
- 如果其中几张明显无关 → 记录在 note，裁决时按「部分成立」处理，优先 `needs_review`。

### Q3：业务上这个模型到底是什么？

这是人工不可替代的部分，必须能回答：

- 业务过程是什么？
- 业务对象是什么？
- **一行代表什么？**
- 数据怎么产生（源系统写入？加工任务算出来的？每日快照？）
- 谁在用、怎么用（取数、报表、下游加工）？

### Q4：这个现象是不是有合理解释？

常见合理解释（**存在合理解释时不能直接 Confirmed**）：

```text
不同来源系统        不同业务 BU        不同生命周期
不同服务消费者      历史兼容          技术复制
分层加工链路（ODS → DWD）             临时 / 测试 / 备份表
```

### Q5：它是否造成实际影响？

对照固定影响词汇，勾选真实存在的：

```text
Grain Inconsistency / Metric Ambiguity / Query Complexity /
Model Selection Difficulty / Maintenance Cost / Governance Difficulty /
Reuse Difficulty / Analytical Risk / Data Consumer Confusion / AI Semantic Risk
```

> 如果找不到任何真实影响，需要谨慎：可能只是结构现象，不是问题。

### Q6：Root Cause 是否合理？

机器给出的根因只是候选。例如机器写 `MULTIPLE_GRAINS_IN_ONE_MODEL`（同一模型内多粒度），你必须确认：

- 真的是**一个模型混合多个业务粒度**？
- 还是**不同业务过程共享同一张技术表**（根因其实是职责混杂或历史兼容）？

证据不足时，机器已经写了 `UNKNOWN`——**你也不要在没有证据时替它补一个「设计偏好」式根因**。

### Q7：最终决定

只能三选一，写进清单 `human_status`：

```text
CONFIRMED          当前确实存在该模型问题
REJECTED           当前模型设计合理，机器判断不成立
REVIEW_REQUIRED    证据不足或需要业务讨论（填 needs_review / needs_discussion）
```

**证据不足不要强行 Confirmed。** `needs_review` 是完全合法、受支持的结论。

---

## 第七章 统一人工问题模板

每个 Problem 用同一份模板记录（可复制到团队台账 / 会议纪要 / 清单 note 中）：

```text
Problem ID:

Problem Type:

Business Process:

Business Object:

Affected Tables:

Current Grain:

Expected Grain:

Finding 是否成立：
□ 是
□ 否
□ 不确定

Problem 是否真实存在：
□ 是
□ 否
□ 不确定

是否存在合理业务解释：
□ 是
□ 否
□ 不确定

实际影响：
□ Grain Inconsistency
□ Metric Ambiguity
□ Query Complexity
□ Model Selection Difficulty
□ Maintenance Cost
□ Governance Difficulty
□ Reuse Difficulty
□ Analytical Risk
□ Data Consumer Confusion
□ AI Semantic Risk

Root Cause 是否成立：
□ 是
□ 否
□ 不确定

Human Decision:
□ CONFIRMED
□ REJECTED
□ REVIEW_REQUIRED

Human Evidence:

Business Explanation:

Refactoring Rationale:

Reviewer:

Review Date:
```

### 使用约定

- **不要重复填写机器已经可靠提供的内容**：`problem_type`、`priority`、`scope_key`、`evidence` 计数、机器推导的 `impact` / `root_cause` 都在 JSON 里，直接引用 problem_id 即可。
- 模板里真正要人写的是：**业务过程 / 一行代表什么 / 合理解释 / Human Evidence / Business Explanation / Refactoring Rationale**。
- 清单 `note` 列空间有限：写结论要点 + 台账编号；完整叙述放外部台账。
- 同一位Reviewer 必须署名（`human_name` 列），便于追溯与复审。

---

## 第八章 13 类 Problem 分别怎么问

每一类给六项：**机器发现什么 → 人工要验证什么 → 问业务什么 → 何时 Confirmed → 何时 Rejected → 何时继续 Review**。

### 8.1 `GRAIN_PROBLEM` 粒度问题（559 条，P0，table scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | 一张表有多组候选键且互不包含（`confirmed_conflict` 548 / `possible_conflict` 11），行级含义不唯一；触发 finding `grain_conflict` |
| 人工要验证什么 | 候选键是否真的互斥（有些只是大小写 / 顺序 / 前后缀差异）；这张表是否被多种口径写入 |
| 应该问业务什么 | ① 这张表一行代表什么？② 唯一的业务粒度是哪一组键？③ 其余 grain candidate 是作废还是并存？④ 谁往这张表写数、有几个任务在写？ |
| 何时 `confirmed` | 业务确认「行级含义确实不唯一 / 确实存在多套口径写入同一张表」，且影响成立（指标口径、重复计数风险） |
| 何时 `rejected` | 业务确认只有一套粒度，其它候选键是机器误判（例如候选键只是同一键的不同写法，或某列并非键） |
| 何时继续 `review` | 键的真实唯一性需要查数据样本 / 需要问任务负责人；填 `needs_review` |

**注意**：559 条全部 `strong`、全部 `candidate` —— 它说明「候选键不唯一」，**不说明「这 559 张表都要改」**。

### 8.2 `MODEL_OVERLAP` 模型重叠（27 条，P1，table_set scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | 字段与结构高度重合的表簇（`overlapping_fact` 2605 条表对经连通分量聚合）；`structural_overlap` 17、`technical_copy_candidate` 10 |
| 人工要验证什么 | 高字段重合是否具有**不同业务语义**；簇内的表是否真属于同一逻辑模型 |
| 应该问业务什么 | ① 这 N 张表是不是同一逻辑模型的多份表达？② 权威表是哪一张？③ 先收敛哪一张？④ 是否有意的分区 / 区域副本？ |
| 何时 `confirmed` | 业务确认它们表达同一逻辑模型、且多份并存造成选型困难 / 口径漂移 |
| 何时 `rejected` | 语义不同（字段同名不同义）、或属不同服务消费者 / 不同口径的有意设计 |
| 何时继续 `review` | 无法确认权威表，或簇内混入无关表 → `needs_discussion` |

**机器不判断哪张是权威版本，也从不说「可删除」。**

### 8.3 `MODEL_DUPLICATION` 模型重复（317 条，P1，table_set scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | 同一逻辑事实的候选落在多张表：`duplication_candidate` 108（共享 process + 共享 grain 签名）、`grain_identical_structure_divergent` 122、`technical_copy_candidate` 87 |
| 人工要验证什么 | 是**语义重复**还是**技术复制**（源系统复制 / BU 复制 / 历史 / 备份 / 临时 / 兼容 / 分层加工） |
| 应该问业务什么 | ① 权威表是哪一张？② 哪些是副本、哪些是独立口径？③ 收敛顺序？④ 下游各有多少任务在用？ |
| 何时 `confirmed` | 同一业务口径存在多份表达与多条加工链路，维护成本 / 选错概率真实上升 |
| 何时 `rejected` | 属分层正常加工（如 ODS→DWD）、源系统不同、或有意的历史 / 区域副本 |
| 何时继续 `review` | 只能确认部分表是副本，权威表未定 → `needs_review` |

### 8.4 `MIXED_RESPONSIBILITY` 职责混杂（204 条，P0 130 / P2 74，table scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | 表级职责信号 ≥2 个，或命中自足信号（WIDE / RESULT）；信号计数 `AGGREGATE` 164、`PERIODIC_FACT` 142、`MIXED_GRAIN` 130、`WIDE` 39、`RESULT` 37、`SNAPSHOT_FACT` 3（`FACT` 是基线角色不算信号） |
| 人工要验证什么 | 这些信号是**描述**而非评价：一张表同时有周期指标与明细行，是否真的是职责混杂？ |
| 应该问业务什么 | ① 这张表实际承担哪一种职责？② 是否需要拆分？③ 拆分边界在哪里？④ 谁在用它的哪一部分？ |
| 何时 `confirmed` | 无法用单一职责描述该表，拆 / 合都缺少依据，且改造时确实无法归位 |
| 何时 `rejected` | 单一职责清楚（例如就是一张周期汇总表），其它信号来自字段命名巧合 |
| 何时继续 `review` | 需要先裁决粒度再判职责（与 `GRAIN_PROBLEM` 关联）→ `needs_review` |

### 8.5 `MODEL_ROLE_AMBIGUITY` 角色歧义（4 条，P0，dimension scope，已 `review_required`）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | Object 同时命中 `dimension_candidate` 与 `fact_related_object`，角色不唯一（customer / order / product / store 4 个） |
| 人工要验证什么 | 角色来自锚点关系推导，不是业务定义；4 条全是 weak 证据 |
| 应该问业务什么 | ① 该 Object 究竟是维度、退化维度，还是事实的一部分？② 谁有资格裁决它？③ 它在目标模型中的唯一位置是什么？ |
| 何时 `confirmed` | 业务确认角色确实存在双解且会导致事实 / 维度边界模糊 |
| 何时 `rejected` | 业务给出唯一角色，另一角色是推导副产物 |
| 何时继续 `review` | 证据类型 ≤2，通常需要补业务定义 → 保持 `needs_review` 直到有业务结论 |

### 8.6 `PROCESS_MODEL_ALIGNMENT` 过程与模型对齐（15 条，P3，process scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | 一个 process 下的 fact 覆盖多种 grain 形态（finding `process_multiple_grains`，15 条，全部 P3 / moderate） |
| 人工要验证什么 | process 本身还是 candidate（17 个过程候选、命名与语义都未确认）；同一 Object 会出现在多个过程候选中 |
| 应该问业务什么 | ① 这些粒度是否都属于同一业务过程？② 是否需要区分过程与子过程？③ 该过程下表是否应共享？ |
| 何时 `confirmed` | 业务确认过程与模型没有唯一对应关系，目标模型不知道按哪个口径建 |
| 何时 `rejected` | 这些粒度确实属于同一过程的不同合理阶段（明细 / 汇总），无需拆过程 |
| 何时继续 `review` | 需要先完成 process 命名与确认 → `needs_review` |

### 8.7 `AGGREGATION_MODEL_PROBLEM` 聚合模型问题（22 条，P2，process scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | 有 `aggregate_fact` finding 且评估 ≠ `valid_aggregate`：`model_problem` 13（自身带粒度冲突或落在重复组）、`review_required` 9（血缘找不到事实上游） |
| 人工要验证什么 | 聚合口径能否回溯到原子事实；**合法聚合不发问题**（12 条 `valid_aggregate` 已被有意排除） |
| 应该问业务什么 | ① 这些聚合表的上游事实是什么？② 聚合口径能否回溯到原子事实？③ 该聚合层是否应该保留？ |
| 何时 `confirmed` | 口径无法回溯到任何原子事实，指标复核 / 重算没有依据 |
| 何时 `rejected` | 上游事实清楚（血缘只是没采到），聚合层是合法且必要的 |
| 何时继续 `review` | 9 条 `review_required` 天生证据不足 → 补血缘 / 问任务负责人 |

### 8.8 `FACT_IDENTIFICATION_PROBLEM` 事实识别问题（26 条：stage 3 条 P0、table 23 条 P1 已 `review_required`）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | ① Fact Gate 排除按形态分组：`aggregation` 804、`periodic` 1044、`unknown` 467（共 2315 个 grain candidate，全部 `no_measure_evidence`）；② 50 条 `fact_without_measure` finding → 23 条表级问题 |
| 人工要验证什么 | **闸门结论 ≠ 业务结论**：是否存在合法事实因为没有传统 measure 字段被排除 |
| 应该问业务什么 | ① 这些表是否仍应作为事实？② 没有 measure 字段时，度量在哪里计算（差分、状态快照、下游算）？③ 抽样的表一行代表什么？ |
| 何时 `confirmed` | 抽样证实：合法事实确实因规则盲区被系统性排除，且这会导致事实模型漏建 |
| 何时 `rejected` | 抽样证实：这些表本来就不是事实（纯配置、纯维度、纯日志清单） |
| 何时继续 `review` | 单表证据只有 1–2 类（23 条 weak）→ 保持 `needs_review`，逐表补证据 |

**具体做法见第十一章（Fact Gate 抽样）。**

### 8.9 `DIMENSION_IDENTIFICATION_PROBLEM` 维度识别问题（1 条，P2，stage scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | 5 个 dimension candidate 与 5 个 Object 一一对应（`dimension_object_derived`），未经独立的维度适格性判断 |
| 人工要验证什么 | Object 派生是既定方法（证据结构而非语义识别）；1 条 weak / `review_required` |
| 应该问业务什么 | ① 这 5 类 Object 是否覆盖真实维度集合？② 哪些维度缺失（时间、渠道、活动…）？③ 权威维度表是哪一张？ |
| 何时 `confirmed` | 确认维度来源只是派生、边界会漂，且缺失维度确实存在 |
| 何时 `rejected` | 5 类维度覆盖充分、权威来源清晰 |
| 何时继续 `review` | 需要业务盘点维度清单 → `needs_review` |

### 8.10 `MODEL_SELECTION_AMBIGUITY` 模型选择歧义（8 条，P1，process scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | 同一 process 下重复组 ≥10 个。例：`process_candidate_004` 有 **79 个重复组、151 张表**；`process_candidate_013` 59 组 143 表 |
| 人工要验证什么 | 它是 `MODEL_DUPLICATION` 的**派生视图**——重复组本身还没裁决；阈值 10 是常量不是业务定律 |
| 应该问业务什么 | ① 该过程的 N 个重复组应收敛成几个模型？② 权威入口是哪个？③ 消费者现在怎么选？ |
| 何时 `confirmed` | 业务确认消费者确实在多模型之间靠猜、选错过 |
| 何时 `rejected` | 重复组裁决后大幅减少，或消费者有明确选型规则 |
| 何时继续 `review` | 等 8.3 的重复组裁决完成再定 → `needs_review` |

### 8.11 `SEMANTIC_AMBIGUITY` 语义歧义（3 条，P1，stage scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | ① `fact_evidence_strength`：3364 个 fact 的 strength 全是 strong（process / grain 由构造自带，不能当置信度）；② `object_co_occurrence`：5880 / 15979 行关系只来自共现；③ `technical_only`：358 / 15979 行关系只有技术引用 |
| 人工要验证什么 | 把技术引用当业务关系读，会让语义层建立在错误关联上 |
| 应该问业务什么 | ① 只有技术引用 / 只有共现的关系，能不能算业务关系？② 需要补什么业务证据？③ 是否需要独立的 Candidate Confidence 口径？ |
| 何时 `confirmed` | 业务确认这些关系会被误当业务关系使用，且风险真实存在 |
| 何时 `rejected` | 团队已有明确约定：技术证据只作参考，不进语义层 |
| 何时继续 `review` | 3 条全是 weak / `review_required`，通常需要讨论 → `needs_discussion` |

### 8.12 `MODEL_COVERAGE_GAP` 过程覆盖缺口（2 条，P0，process scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | `process_candidate_003`、`process_candidate_012` 各有 2 个 grain candidate、2 张表，但**没有任何 fact candidate**；`root_cause` 恒为 `UNKNOWN` |
| 人工要验证什么 | 证据只说明「没有事实进入模型」，不说明「这个过程不该有事实」 |
| 应该问业务什么 | ① 这个过程真的没有事实需要建模吗？② 它的事实应该来自哪里？③ 是不是被 Fact Gate 排除了？ |
| 何时 `confirmed` | 业务确认该过程应有事实、但当前模型确实遗漏 |
| 何时 `rejected` | 该过程确实无事实（例如纯配置 / 纯主数据维护过程） |
| 何时继续 `review` | 需要回溯到 Fact Gate 或源系统 → `needs_review` |

### 8.13 `UNKNOWN_MODEL` 未定模型（2 条，P2，table_set scope）

| 项 | 内容 |
| --- | --- |
| 机器发现什么 | `current_role = UNKNOWN` 的表按原因分桶：`NO_ANCHOR` 463 张、`NO_EVIDENCE` 1578 张（两条 problem 各对应一个桶） |
| 人工要验证什么 | UNKNOWN 是**合法结果**，不是坏模型标签；两条都是 weak / `review_required` |
| 应该问业务什么 | ① 这些表是否属于可建模的业务模型范围？② 纳入 / 排除 / 补证据，如何处置？③ 哪些是技术表、临时表、已废弃表？ |
| 何时 `confirmed` | 确认「范围归属不明确」本身构成风险（会被静默遗漏或错误纳入） |
| 何时 `rejected` | 业务能给出明确范围说明，例如这批全是技术 / 中间 / 废弃表 |
| 何时继续 `review` | 大多数情况——**保持 UNKNOWN 就是正确答案**（见第十章） |

---

## 第九章 四个最容易误判的问题

这四类最容易在评审会上吵起来，先把判断标准定死。

### 9.1 Grain：不要问「有多个 grain 是不是错误」

**错误问法**：

> 「这张表有 3 个 grain，是不是错了？」

**正确问法**：

> 「这些 grain 是否代表**同一个业务过程 / 同一个模型职责**？」

判断示例：

| 情形 | 判断 |
| --- | --- |
| 订单明细 / 订单日汇总 / 订单月汇总**分属三张表** | 合理，不是问题 |
| 上述三种粒度**写在同一张表里**（不同任务混写） | 才是 `GRAIN_PROBLEM` |
| 候选键只是同一键的大小写 / 顺序 / 前后缀差异 | 机器误判 → `rejected` |
| 一张表被两条加工链路按不同口径写入 | → `confirmed` |

> **多粒度本身不是错误，同一模型内口径不唯一才是错误。**

### 9.2 Overlap：`Overlap ≠ Duplication`

```text
字段与结构重合（overlap）     只证明「长得像」
重复（duplication）           还要求「共享 process + 共享 grain 签名」
```

人工必须确认：

> **高字段重合是否具有不同业务语义？**

| classification | 含义 | 条数 |
| --- | --- | --- |
| `structural_overlap` | 结构重合，未满足重复条件 | 17 |
| `duplication_candidate` | 共享 process 与 grain 签名的重复候选 | 108 |
| `technical_copy_candidate` | 跨层 + 血缘方向或 Jaccard ≥0.9，疑似技术副本 | 97 |
| `grain_identical_structure_divergent` | 重复组未进连通分量、结构已分歧 | 122 |

> **禁止**：把 `MODEL_OVERLAP` 说成「重复表」，把重合度当删除依据。

### 9.3 Duplication：必须区分语义重复与技术复制

必须逐一核对：

```text
source replication     BU replication     history
backup                 temporary          compatibility
分层加工链路（ODS → DWD）
```

- 同一逻辑事实、多条加工链路、多个下游在用 → **语义重复** → 可 `confirmed`；
- 同一数据在不同层 / 不同源系统的正常落地 → **技术复制** → 应 `rejected`（或至少不是重复建模）。

> **重复 ≠ 可删。** 即使 `confirmed`，删表 / 合表也不在本阶段（见第十三章）。

### 9.4 Aggregate Fact：`Aggregate Fact ≠ Wrong`

```text
Aggregate Fact（聚合事实）是合法形态，不是问题。
```

人工判断标准：

> **这个聚合表是否具有明确业务用途和稳定口径？**

| 机器评估 | 含义 | 是否发问题 |
| --- | --- | --- |
| `valid_aggregate` | 有原子事实上游、自身无粒度 / 重复问题 | **不发问题**（12 条 finding 落在这里） |
| `review_required` | 找不到事实上游 | 发问题，且状态抬为 `review_required`（9 条） |
| `model_problem` | 自身带粒度冲突或落在重复组内 | 发问题（13 条） |

> **禁止**：把「存在聚合表」写成问题，把 `valid_aggregate` 强行纳入清单。

---

## 第十章 UNKNOWN 应该怎么处理

### 10.1 当前事实

```text
UNKNOWN 表合计 2041 张（占 3719 张表的大多数尚无 fact / dimension 锚点覆盖）

NO_ANCHOR  = 463    无锚点且无血缘入边 / 出边   → 问题在「证据覆盖」
NO_EVIDENCE = 1578  有血缘但不足以判定角色     → 问题在「证据强度」
```

对应两条 Problem：`UNKNOWN_MODEL` 各 1 条（`problem_1189` / `problem_1190`），均 `review_required` / weak / P2。

### 10.2 明确禁止的做法

> **不能做**：「为了减少 UNKNOWN，给它们全部找一个角色。」

具体禁止：

```text
❌ 因为 UNKNOWN 而确认模型错误
❌ 把 UNKNOWN 表改写成 FACT 或 DIMENSION 只为了让数字好看
❌ 把 UNKNOWN = 2041 说成「2041 张表有问题」
```

### 10.3 正确做法

```text
能判断   → 补充归属（写进台账：属于哪个过程 / 是否可建模）
不能判断 → 保持 UNKNOWN（这本身就是正确答案）
```

三种处置，逐桶推进：

| 处置 | 适用情形 | 怎么落档 |
| --- | --- | --- |
| **纳入** | 确认属于业务模型范围，只是证据不足 | 记录归属过程 / 对象 + 需要补的证据 |
| **排除** | 技术表、临时表、测试表、已废弃表 | 记录排除理由（写进 note） |
| **补证据** | 表重要但血缘 / 注释缺失 | 记录「要补什么证据」，留待下一轮 |

### 10.4 判断口径

> **UNKNOWN 本身不是错误。** 证据不足时，UNKNOWN 就是当前最诚实的答案。

因此这一类的默认结论通常是 `needs_review`（保持范围待定），只有在你确认「范围不明确已经造成遗漏 / 错纳风险」时才 `confirmed`。

---

## 第十一章 Fact Gate 怎么人工验证

### 11.1 当前事实

```text
Fact Gate 复算：
qualified = 3364
rejected  = 2315
rejected_reason = no_measure_evidence（唯一原因）
matches_m35 = true（与 M3.5 闸门一致）

规则：transaction / event / snapshot 直接通过
      periodic / aggregation / unknown 必须有 measure_columns

被排除的 grain candidate 按形态：
periodic 1044 / aggregation 804 / unknown 467
```

对应 Problem（stage 侧 3 条，均 P0）：

| problem_id | scope_key | 内容 |
| --- | --- | --- |
| `problem_0024` | `aggregation` | Fact Gate 因 aggregation 排除 804 个 grain candidate |
| `problem_0025` | `periodic` | Fact Gate 因 periodic 排除 1044 个 grain candidate |
| `problem_0026` | `unknown` | Fact Gate 因 unknown 排除 467 个 grain candidate |

### 11.2 不要这样问

> **错误**：「这 2315 张是不是错误？ / 这 2315 张不是事实表。」

### 11.3 应该这样问

> **正确**：「其中是否存在**合法事实**，但因为没有传统 measure 字段而被规则排除？」

### 11.4 抽样验证步骤

1. **重点抽样三个形态**：`periodic`（1044）、`aggregation`（804）、`unknown`（467）；
2. 每个形态抽 10–20 张表，回答：
   - 这张表一行代表什么？（事件？状态快照？周期汇总？）
   - 它的「度量」在哪里？（字段值 / 下游差分 / 状态变化 / 本来就没有度量）
   - 它是否被下游当作事实表使用（看血缘出边）？
3. 结论分两类：

| 抽样发现 | 应该怎么记 |
| --- | --- |
| 大量「合法事实但没有传统 measure」 | 记为 **Analysis Rule Limitation（分析规则局限）**——这是闸门规则的盲区，不是模型问题 |
| 确实不是事实（配置表 / 维度表 / 清单） | 闸门判断正确 → 对应 stage problem 可 `rejected`，或记「规则在该形态上有效」 |
| 混合、无法定论 | `needs_review`，把抽样样本与结论留在台账 |

4. 表级 23 条（`fact_without_measure`，全部 weak / `review_required`）逐表按第六章 Q1–Q7 走，**不要批量 confirm**。

### 11.5 记录位置

- 抽样结论写进裁决台账 + 清单 `note` 列；
- 若确认是规则盲区，在台账里显式写 **「Analysis Rule Limitation」**，与 **「Current Model Problem」** 分开统计；
- 规则本身**本阶段不修改**（不改 M3.5 闸门、不改 M3.6 复算）。

---

## 第十二章 如何形成 Refactoring Evidence

人工确认之后，**不是立即设计 DWD**，而是形成一条可追溯的证据链。

### 12.1 七段式

```text
Current State      当前是什么样（描述，不是评价）
       ↓
Confirmed Problem  人工确认的问题类型
       ↓
Evidence           凭什么这么说（可追溯到 finding / 表 / 字段 / 血缘）
       ↓
Impact             会造成什么后果（结构影响）
       ↓
Root Cause         根因是什么（或明确写 UNKNOWN）
       ↓
Why Change         为什么现在要改
       ↓
Human Decision     人工裁决：确认 / 否决 + 理由 + 范围与顺序   ← 只能由人写
```

前六段机器已经给出（见 `current-state-problems.json` 的 `rationale`：`current_state` / `problem` / `evidence` / `impact` / `why_change`，以及 `root_cause`）；**第七段只能由人写**。

### 12.2 完整示例（基于真实 Problem `problem_0050`）

```text
Current State:
表 dme_ads.dwd_crm_member_item 有 3 个 grain candidate、
3 组候选键（order_id / product_code / product_line_code）、
1 个 process（process_candidate_005）；grain assessment = confirmed_conflict。

Confirmed Problem:
GRAIN_PROBLEM（problem_0050，P0，table scope）

Evidence:
FINDING=model_finding_1049；TABLE=dme_ads.dwd_crm_member_item；
COLUMN=order_id / product_code / product_line_code；
PROCESS=process_candidate_005；GRAIN=grain_candidate_1101 / 1102 / 1103

Impact:
GRAIN_INCONSISTENCY（同一语义存在多种粒度口径）
METRIC_AMBIGUITY（指标口径可能不一致）

Root Cause:
MULTIPLE_GRAINS_IN_ONE_MODEL

Why Change:
M4 必须先由人工裁决该表的唯一业务粒度，再决定采信哪一组候选键；
未裁决前不能直接进 Target DWD。

Human Decision:
CONFIRMED —— <Reviewer> <Review Date>
理由：该表同时被订单明细口径与产品线汇总口径写入，行级含义不唯一；
范围：先锁定唯一业务粒度，再评估是否需要按粒度拆分表达。
```

### 12.3 重构证据矩阵（汇总用）

进入重构讨论的 Problem 汇总成四列表；**只写方向，不写具体表设计**：

| Current Problem | Evidence | Root Cause | Potential Refactoring Direction |
| --- | --- | --- | --- |
| `GRAIN_PROBLEM`（表 A） | 3 组互不包含候选键 + 字段证据 + `grain_conflict` finding | `MULTIPLE_GRAINS_IN_ONE_MODEL` | 先裁决唯一业务粒度，再评估是否按粒度拆分表达 |
| `MODEL_DUPLICATION`（表 B、C） | 共享 process + grain 签名 + Jaccard + 跨层血缘 | `MULTIPLE_SOURCE_SYSTEM_REPLICATION` | 先确认权威表与副本关系，再决定收敛范围与顺序 |
| `AGGREGATION_MODEL_PROBLEM`（过程 D） | 聚合表 + 无 fact-anchor 上游血缘 | `UNKNOWN` | 先补齐上游事实来源证据，再决定聚合层是否保留 |
| `MODEL_COVERAGE_GAP`（过程 E） | 过程无 fact candidate + 未产出事实的 grain 候选 | `UNKNOWN` | 先确认该过程是否需要事实建模，再决定覆盖方式 |

**使用规则**：

1. 每行必须能从 `problem_id` 追溯到 `current-state-problem-evidence.json` 的证据行；
2. `Root Cause` 为 `UNKNOWN` 的行，方向只能是「补证据 / 定范围」，**不能**是「拆分 / 合并 / 下线」；
3. 方向停留在**动作类型**（裁决、收敛、补证据、拆分评估），不落到**具体对象**（某张表、某个字段、某套 DWD 设计）；
4. **矩阵是 M4 的输入，不是 M4 的产出。**

---

## 第十三章 现在不要做什么

人工裁决阶段**明确禁止**：

```text
❌ 直接设计 DWD
❌ 直接设计 DWS
❌ 直接删表
❌ 直接合并表
❌ 直接拆表
❌ 直接定义 Semantic Layer
❌ 因为「标准模型理论」而确认问题
❌ 因为表名相似而确认重复
❌ 因为 Jaccard 高而确认重复
❌ 因为 UNKNOWN 而确认模型错误
❌ 因为存在聚合表而确认问题
❌ 把 Fact Gate 排除说成「2315 张非事实表」
❌ 自动把 candidate 改成 confirmed
❌ 修改分析代码 / YAML / JSON 产物 / Problem Taxonomy / 测试
```

当前阶段只回答一个问题：

> **这个问题是不是真的存在？**

一切关于「怎么改」的讨论，留到裁决完成、重构证据矩阵成形之后。

---

## 第十四章 什么时候才能进入 M4

### 14.1 四个门槛（全部满足才开始）

| # | 门槛 | 当前状态 |
| --- | --- | --- |
| 1 | **P0 关键问题已人工裁决**（粒度、职责、角色、覆盖缺口） | 未开始（P0 698 全部 pending） |
| 2 | **P1 中影响最大的结构性问题已裁决**（重复 / 重叠 / 选择歧义） | 未开始（P1 378 全部 pending） |
| 3 | **关键 Fact / Grain 争议已处理**（Fact Gate 抽样、UNKNOWN 范围归属） | 未开始 |
| 4 | **已形成 Refactoring Evidence / Problem Themes** | 未开始 |

### 14.2 配套条件（来自方法论文档，同样是硬约束）

1. `current-state-problem-review-checklist.md` 中 P0 / P1 的行完成回填，`confirmed` / `rejected` 不再为 0；
2. `current-state-review-checklist.md`（Finding 侧）同步回填——**两个清单各自独立**，一个完成不等于另一个完成；
3. 四类判断必须由人给出：**权威表、收敛顺序、粒度唯一键、UNKNOWN 表范围归属**；
4. 重构证据矩阵逐行填完 `Human Decision` 列。

### 14.3 最终状态

```text
Machine Analysis
        ↓
Human Confirmed Problems
        ↓
Problem Themes（问题主题归类）
        ↓
Refactoring Evidence（重构证据）
        ↓
M4 Target DWD Design
```

> **在上述条件满足前，任何「按 problem 清单直接设计 DWD」的做法都越界。**

---

## 第十五章 实际一周怎么做

前提：清单可见 260 行是**第一轮边界**；全量 1190 条按批次推进，超出清单的部分记外部台账。建议每人每天 15–25 条，先小批量跑通流程再提速。

### Day 1 —— P0 Grain（粒度问题）

```text
范围：清单「粒度问题」区 50 行（全量 559）
目标：每人 10~12 行，跑通 Q1~Q7 + 模板
关键动作：
  - 先用 problem_0050 做对齐演练（见第十六章 Case A）
  - 统一「多 grain 是否算错」的判断口径（第 9.1 节）
产出：第一批 confirmed / rejected / needs_review + 台账
```

### Day 2 —— Mixed Responsibility（职责混杂）+ P0 小类

```text
范围：清单「职责混杂」区 50 行（全量 204，P0 130）
     +「角色歧义」4 条 +「过程覆盖缺口」2 条
目标：回答「一张表到底承担几种职责、要不要拆」
关键动作：
  - 先判粒度再判职责（与 Day 1 结论联动）
  - 4 条角色歧义需要业务方定唯一角色
产出：P0 侧基本收口
```

### Day 3 —— Duplication / Overlap（重复 / 重叠）

```text
范围：清单「模型重复」区 50 行（全量 317）
     +「模型重叠」27 条（全量可见）
     +「模型选择歧义」8 条
目标：每组给出权威表 / 副本关系 / 收敛顺序判断
关键动作：
  - 先做 technical_copy_candidate 类（可快速 rejected，见 Case B）
  - 再做 duplication_candidate（需业务确认口径一致）
  - 选择歧义等重复组裁决后再定
产出：P1 结构性问题主体结论
```

### Day 4 —— Fact Identification / UNKNOWN（特殊审计）

```text
范围：Fact Gate stage 3 条 + 表级事实识别 26 条
     + UNKNOWN_MODEL 2 条 + 维度识别 1 条 + 语义歧义 3 条
     + 聚合模型 22 条 + 过程对齐 15 条
目标：不追求 confirm，先区分「模型问题」与「规则局限」
关键动作：
  - 按第十一章抽样 periodic / aggregation / unknown
  - UNKNOWN 坚持「能判断就归属，不能判断保持 UNKNOWN」
产出：抽样报告 + Analysis Rule Limitation 清单
```

### Day 5 —— 汇总与 Themes

```text
范围：全部已裁决条目
目标：
  □ 统计 Confirmed / Rejected / Review Required 分布
  □ 按 root_cause + impact 归并 Problem Themes
  □ 补齐四类判断：权威表、收敛顺序、粒度唯一键、UNKNOWN 范围
  □ 起草重构证据矩阵（第 12.3 节四列）
  □ 列出进入 M4 前仍缺的证据（第十四章门槛对照）
产出：裁决周报 + 重构证据矩阵初稿
```

---

## 第十六章 三个裁决案例

> **声明**：以下三条使用**当前项目真实的 Problem / Finding / 表**；其中的裁决结论是**示范填写**（用于说明格式与推理过程），真实结论必须由业务专家给出。目前所有清单行的 `human_status` 仍为 `pending`。

### Case A：Confirmed Grain Problem —— `problem_0050`

| 字段 | 值 |
| --- | --- |
| Problem ID | `problem_0050` |
| Type / Priority | `GRAIN_PROBLEM` / P0 |
| Scope | `table`：`dme_ads.dwd_crm_member_item` |
| Classification | `confirmed_conflict`（候选键互不包含） |
| Evidence | `FINDING×1、TABLE×1、COLUMN×3、PROCESS×1、GRAIN×3` |
| Finding | `model_finding_1049` |
| Process | `process_candidate_005` |
| Grain Candidates | `grain_candidate_1101 / 1102 / 1103` |
| 候选键字段 | `order_id`、`product_code`、`product_line_code` |
| Impact | `GRAIN_INCONSISTENCY`、`METRIC_AMBIGUITY` |
| Root Cause | `MULTIPLE_GRAINS_IN_ONE_MODEL` |
| 机器问题 | 表 `dme_ads.dwd_crm_member_item` 的业务粒度到底是哪一组键？其余 grain candidate 应作废还是并存？ |

**逐问走一遍**：

- **Q1 Finding 成立？** 是——三组候选键确实互不包含（`order_id` 单键 ⊄ `product_code` ⊄ `product_line_code`）。
- **Q2 同一问题？** 是——同表、同 process、三条证据都指向这张表。
- **Q3 业务上是什么？**（需业务回答）该表是 CRM 会员商品明细表，归属 `process_candidate_005`。
- **Q4 合理解释？** 需要排查：是否一个任务写订单粒度、另一个任务写产品线汇总粒度。**若确认是混写，无合理解释。**
- **Q5 实际影响？** 有：同一张表按不同键汇总会出现重复计数 / 漏计，指标口径不一致。
- **Q6 根因合理？** 合理——确实是同一模型内多粒度（不是「多个过程共享一张表」，因为只有 1 个 process）。
- **Q7 决定**：

```text
Human Decision: CONFIRMED
Human Evidence: 两条加工任务按不同候选键写入同一张表（任务名 / SQL 见台账附件）
Business Explanation: 订单明细粒度 = order_id + product_code；
                      产品线汇总粒度应落在独立汇总表，不应混写明细表
Refactoring Rationale: 先由业务锁定唯一业务粒度，再评估是否按粒度拆分表达
Reviewer: <姓名>      Review Date: <日期>
```

### Case B：Rejected Duplication —— `problem_0860`

| 字段 | 值 |
| --- | --- |
| Problem ID | `problem_0860` |
| Type / Priority | `MODEL_DUPLICATION` / P1 |
| Scope | `table_set`：`dme_cdm.dwd_blue_table_foc_sell_in` \| `dme_ods.s_blue_table_foc_sell_in` |
| Classification | `technical_copy_candidate` |
| Evidence | `FINDING×1、TABLE×2、COLUMN×5、PROCESS×1、GRAIN×2、LINEAGE×1` |
| 共享 | process `process_candidate_004`；共享 grain 签名 `pattern=aggregation, keys=ds+product_code` |
| 层 | DWD、ODS（跨层） |
| 最大 Jaccard | 0.84 |
| 血缘 | 1 条内部血缘边：`dme_ods.s_blue_table_foc_sell_in` → `dme_cdm.dwd_blue_table_foc_sell_in`（来自 SQL 文件 `dwd_blue_table_foc_sell_in`，node 700006513157） |

**逐问走一遍**：

- **Q1 Finding 成立？** 是——两表字段重合 0.84、确有血缘边。
- **Q2 同一问题？** 是——同一张加工链路上的两站。
- **Q3 业务上是什么？** ODS 是源落地层，DWD 是清洗加工层，同一业务数据的两个阶段。
- **Q4 合理解释？** **有，且是决定性的**：这是**分层加工链路**（source replication → 分层加工），不是同一层的重复建模；两表分属不同层、有明确上下游。
- **Q5 实际影响？** 无实质选型困难：下游按层取数，ODS 不作为分析入口。
- **Q6 根因合理？** 机器给的 `DUPLICATED_MODEL_PIPELINES` 不成立——只有一条管线的两站，不是重复管线。
- **Q7 决定**：

```text
Human Decision: REJECTED
Human Evidence: 血缘边 ODS→DWD + SQL 文件 dwd_blue_table_foc_sell_in（台账附件）
Business Explanation: 两表是同一加工链路的上下游（源落地 → 清洗加工），
                      分层职责不同，属正常分层复制，不是重复建模
Refactoring Rationale: 无需收敛；若要优化，属分层治理议题，不进入本轮重构证据
Reviewer: <姓名>      Review Date: <日期>
```

> **这正是「Overlap ≠ Duplication、重复 ≠ 可删」的反向应用：字段像、连通、跨层、Jaccard 高，全部成立，结论依然是 REJECTED。**

### Case C：Review Required Fact Gate —— `problem_0027`

| 字段 | 值 |
| --- | --- |
| Problem ID | `problem_0027` |
| Type / Priority | `FACT_IDENTIFICATION_PROBLEM` / P1 |
| Scope | `table`：`dme_ads.tb_actual_data_bts_v3_temp01` |
| 机器状态 | `review_required`（本来就不是 candidate） |
| Evidence Strength | `weak`（`TABLE×3、GRAIN×1`） |
| Finding | `model_finding_1025`（`fact_without_measure`） |
| 关键证据 | `measure_count=0`；fact candidate `fact_candidate_2156`：`pattern=snapshot`、`candidate_keys=customer_idh_snapshot`、`measures=（空）`；grain `grain_candidate_3571` 备注「形态本身即行级事实（transaction / event / snapshot）所以未过 measure 闸门」 |
| Root Cause | `FACT_GATE_MEASURE_DEPENDENCY` |
| 机器问题 | 该表没有 measure 字段，它仍然是事实表吗？度量在哪里计算？ |

**逐问走一遍**：

- **Q1 Finding 成立？** 是——该表确实没有度量字段。
- **Q2 同一问题？** 是（单表单 finding）。
- **Q3 业务上是什么？** 从形态看是**每日快照**（`pattern=snapshot`，键含 snapshot 标识）。快照表本来可以没有传统 measure：**度量往往由相邻两天的状态差分得出**。
- **Q4 合理解释？** **有**：快照形态直接通过 Fact Gate（规则对 snapshot 直放），但它的度量字段天然缺失——这很可能是**规则盲区 / 设计惯例**，不是模型错误。
- **Q5 实际影响？** 尚不能确认：需确认下游是否真的因缺度量而漏建事实 / 指标算不出。
- **Q6 根因合理？** `FACT_GATE_MEASURE_DEPENDENCY` 方向对，但**证据只有 1–2 类**（weak），不足以定性。
- **Q7 决定**：

```text
Human Decision: REVIEW_REQUIRED（清单填 needs_review）
Human Evidence: 待补——① 该表快照口径与下游用法；② 是否存在差分指标；
               ③ 同族 tb_actual_data_bts* 表的度量计算方式
Business Explanation: （暂缺）形态显示为合法快照事实，但缺度量的解释尚未由业务确认
Refactoring Rationale: （暂缺——按第十二章规则：Root Cause 未确认前不写设计方向）
Reviewer: <姓名>      Review Date: <日期>
```

> **不要为了「把 review_required 消掉」而强行 confirm。** 23 条表级事实识别问题、9 条聚合问题、4 条角色歧义、3 条语义歧义、2 条 UNKNOWN、1 条维度识别——这 42 条就是设计好的「必须人看」缓冲区。

---

## 附录 A 禁用表达对照表

| 禁用表达 | 正确表达 |
| --- | --- |
| 「4439 个问题」 | 「4439 条 Finding（观测）」 |
| 「1190 个已确认问题」 | 「1190 条 Problem Candidate（confirmed = 0）」 |
| 「559 张表粒度错误」 | 「559 条 GRAIN_PROBLEM：候选键不唯一，待人工定粒度」 |
| 「2315 张表不是事实」 | 「Fact Gate 因 `no_measure_evidence` 排除 2315 个 grain candidate」 |
| 「存在 12 条漏报」 | 「12 条 `aggregate_fact` 评估为 `valid_aggregate`，有意不成问题」 |
| 「UNKNOWN 表是坏模型」 | 「UNKNOWN 表证据不足：`NO_ANCHOR` 463 / `NO_EVIDENCE` 1578，需人工定范围」 |
| 「overlap 就是重复表」 | 「重叠与重复是两类问题：`MODEL_OVERLAP` 27 / `MODEL_DUPLICATION` 317」 |
| 「聚合表本身就是问题」 | 「`valid_aggregate` 不发问题；只有无上游或自带粒度 / 重复问题才算」 |
| 「按 problem 清单直接设计 DWD」 | 「先完成人工裁决与重构证据矩阵，再进入 M4」 |
| 「strong = 正确」 | 「strong = 证据类型 ≥4，仍需人工确认」 |
| 「candidate 可以直接改表」 | 「candidate / review_required 都未获人工确认，不产生任何改表动作」 |
| 「Finding 裁决了，Problem 也就裁决了」 | 「两个清单各自独立，回填互不替代」 |
| 「证据不足就先强制分类降 UNKNOWN」 | 「证据不足时 UNKNOWN 就是合法结果，不得为降 UNKNOWN 强制分类」 |
| 「root cause 应该写设计判断」 | 「证据不足时 root cause 必须写 `UNKNOWN`，不写设计偏好」 |

---

## 附录 B 文件与命令索引

| 需要做什么 | 用什么 |
| --- | --- |
| 回填人工结论（唯一入口） | `analysis/review/current-state-problem-review-checklist.md` |
| 查全量 Problem（1190 条） | `analysis/review/current-state-problems.json` |
| 查全量证据（30201 行） | `analysis/review/current-state-problem-evidence.json` |
| 看总体统计 | `analysis/review/current-state-problem-summary.md` |
| 回填 Finding 侧（157 行） | `analysis/review/current-state-review-checklist.md` |
| 查 Finding 全量（4439 条） | `analysis/review/current-state-findings.json` |
| 看方法论（13 类 taxonomy、四条原则） | `docs/M36_PROBLEM_ASSESSMENT.md` |
| 看阶段逻辑与产物地图 | `docs/CODE_LOGIC_ANALYSIS.md` |
| 查看原始平台数据 | `source/` |
| 查 SQL / 血缘 | `analysis/sql/statements.json`、`analysis/lineage/table-lineage.json` |
| 回填后让状态生效 | `uv run data-platform-analysis analyze-current-state-model` |
| 重跑后核对计数 | 看 `current-state-problem-summary.md` §2 的 status 表 |

**最后再强调一次**：

> 本阶段只回答「这个问题是不是真的存在」。
> 确认存在 → 写进重构证据；确认不存在 → 写清合理解释；证据不足 → `needs_review`。
> 三种结论都是合格的产出。

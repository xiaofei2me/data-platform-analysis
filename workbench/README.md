# M3.6 Current-State Model Review Workbench

当前状态模型问题评审工作台 · Human Adjudication。

> Machine-generated candidates. Human decision required. · 机器识别的问题候选，最终结论由人工裁决。

一个**只读消费 M3.6 产物**的静态 Web 工作台，把

```text
打开 JSON → 搜 problem_id → 另开 JSON 找 evidence → 翻 Markdown 拼上下文 → 手改 checklist
```

变成

```text
打开 Workbench → P0 / Grain 过滤 → Problem → Evidence → Affected Tables
→ Confirmed / Rejected / Needs Review → 填 Human Note → Save & Next → 下一个
```

## 启动

必须通过 HTTP 提供（浏览器禁止 `file://` fetch JSON）：

```bash
# 在仓库根目录
python3 -m http.server 8787
open http://localhost:8787/workbench/
```

或

```bash
cd workbench && npm run serve     # 等价于 python3 -m http.server 8787 --directory ..
open http://localhost:8787/workbench/
```

测试：

```bash
cd workbench && npm test          # node --test tests/*.test.mjs，零依赖
```

浏览器端冒烟（真实 localStorage / Export / Reset 二次确认）：打开 <http://localhost:8787/workbench/smoke.html>，期望最后一行 `PASS=true`。

## 边界（第一版硬约束）

| 允许 | 禁止 |
| --- | --- |
| 只读 `analysis/` 下已有 JSON 产物 | 写回 / 重新生成任何产物 |
| `localStorage` 保存人工裁决 | 修改 Python、分析逻辑、Taxonomy、Fact Gate / Grain / Overlap / Duplication 规则 |
| 导出 `m36-human-adjudication.json` | 后端、数据库、API Server、登录、权限 |
| 人工写 Confirmed / Rejected / Needs Review | 自动 Confirmed / Rejected、LLM 自动裁决 |

**机器状态与人工状态永远分离**：机器的 `candidate` / `review_required` 只读展示，UI 没有任何写入机器状态的入口。

## 读取的产物（全部只读）

| 文件 | 用途 | 必需 |
| --- | --- | --- |
| `analysis/business/current-state-problems.json` | Problem 列表 / Detail / 汇总数字 | 是 |
| `analysis/business/current-state-problem-evidence.json` | Evidence Explorer 全量证据行 | 是 |
| `analysis/business/current-state-model-tables.json` | Affected Tables 的 role / shape / process / grain | 否（缺失则降级） |
| `analysis/layer/assessments.json` | Affected Tables 的 Layer | 否（缺失则降级） |

加载失败会显示明确错误（列出必需文件 + `Data load failure ≠ 0 Problems`），绝不显示「0 Problems」。

## 结构

```text
workbench/
├── index.html                 # 骨架：头部 / 概览 / 评审队列 / 问题详情 / 底部导航（界面为中文）
├── styles.css (assets/)       # 轻色、密集、证据优先；语义色 token（P0 danger / Confirmed success …）
├── smoke.html                 # 浏览器冒烟：持久化 / Reload / Export / Reset
├── package.json               # {"type":"module"} + test/serve 脚本，无任何依赖
├── src/
│   ├── main.js                # boot、action 编排、全局事件与快捷键、渲染调度
│   ├── domain/types.js        # Problem / HumanDecision / ReviewFilter / ReviewSort 等领域模型 + 常量
│   ├── logic/
│   │   ├── filtering.js       # 纯函数：filter / search / sort / counts / prev-next
│   │   └── specialAudits.js   # Special Audits 谓词（Fact Gate / UNKNOWN / Dimension / Aggregate Fact）
│   ├── data/
│   │   ├── artifacts.js       # 唯一 fetch 入口 + 错误分类（含 file:// 指引，错误文案为中文）
│   │   ├── problemRepository.js
│   │   ├── evidenceRepository.js
│   │   ├── tableRepository.js # model-tables + layer 只读 join
│   │   └── adjudicationRepository.js  # localStorage（注入 storage/confirm/now，可测）
│   ├── state/store.js         # 小型 pub/sub store
│   └── ui/                    # header / overview / queue / detail / evidence / tables / decision / dom
└── tests/                     # node --test：真实产物数字 + 逻辑 + 渲染 + 安全边界
```

UI 不直接 `fetch`：所有数据访问都经 `ProblemRepository` / `EvidenceRepository` / `TableRepository` / `AdjudicationRepository`，将来换成 Backend API 只需替换 `data/` 层。

## 技术选型

仓库没有任何前端基础设施（无 `package.json` / Vue / React / Vite / Element Plus），按「最简单、依赖最少」原则采用：

- 原生 **ES Modules + 零依赖**，无构建步骤；
- 领域类型用 **JSDoc typedef**（`src/domain/types.js`）表达，避免为第一版引入 TS 工具链；
- 测试用 **Node 22 内置 `node --test`**（无测试框架依赖）。

## 数据流

```text
JSON artifacts ──loadArtifacts──▶ ProblemRepository / EvidenceRepository / TableRepository
                                        │
人工裁决 ──AdjudicationRepository──▶ localStorage["m36-human-adjudication"]
                                        │
                                   Export → m36-human-adjudication.json（再走清单回填流程）
```

- `problems.json` 里机器的 `status`（`candidate` / `review_required`）**只读**。
- 人工状态由 localStorage 决定，缺省 `pending`。
- 「重新加载产物」只重新 fetch JSON，不触碰 localStorage。
- 「重置本机裁决」需要**两次确认**，取消任意一次都会保留数据。

## localStorage 结构

key：`m36-human-adjudication`

```json
{
  "problem_0857": {
    "human_status": "confirmed",
    "human_name": "…",
    "human_note": "…",
    "updated_at": "2026-10-06T04:00:00.000Z"
  }
}
```

`human_status ∈ pending | confirmed | rejected | needs_review`；非 `pending` 必须填 `human_name`（不自动伪造用户名）。保存 `pending` 会移除本机记录（回到缺省 Pending）。

## Export 格式

文件名 `m36-human-adjudication.json`：

```json
{
  "generated_at": "…",
  "source": "M3.6 Current-State Problem Assessment",
  "decisions": [
    {
      "problem_id": "problem_0857",
      "human_status": "confirmed",
      "human_name": "…",
      "human_note": "…",
      "updated_at": "…"
    }
  ]
}
```

导出后再按 `docs/M36_HUMAN_ADJUDICATION_GUIDE.md` 回填正式清单（工作台不自动改 Python 产物）。

## 交互要点

- **评审队列**：优先级 / 人工状态 / 问题类型（13 类）/ 搜索（problem_id、表、过程、Workspace）/ 排序（优先级、类型、问题编号、受影响表数、证据强度、人工状态；默认优先级升序 + 问题编号升序）。
- **问题详情**：机器评估（含机器提出的疑问、机器依据）→ 影响 → 根因 → 受影响的表（搜索 / 排序 / 展开详情）→ 证据（有证据的 Tab 才显示计数，每行显示证据类型 / 来源 / 引用标识）→ 人工裁决。
- **连续处理**：底部固定 `← 上一个 / 保存 / 保存并跳转 / 下一个 →`，顺序即当前筛选后的队列。
- **快捷键**：`←` `→` 切换、`1/2/3` = 已确认 / 已拒绝 / 需进一步核实、`S` = 保存；焦点在输入框 / textarea 时不触发。
- **特殊审查**：事实门 Fact Gate（26）、UNKNOWN 模型（2）、维度识别（1）、聚合事实 Aggregate Fact（186）——只是过滤器，不重新计算。

## 语义边界（界面遵守）

- Finding ≠ Problem ≠ Confirmed Problem
- UNKNOWN = Insufficient Evidence / Needs Business Context，**不是** Bad / Invalid / Wrong
- Overlap ≠ Duplication
- Aggregate Fact ≠ Wrong；Fact Gate failure ≠ Invalid Fact（periodic / aggregation / unknown 需人工判断）

## 未来扩展（架构预留、第一版不实现）

Evidence Graph、Problem Theme、Refactoring Evidence、Business Model / Grain / Process / Table Explorer、Model Comparison、Human Review History、Reviewer Assignment、Backend Persistence、Multi-user Review。

## 手工验收清单

1. 打开页面 → Overview 显示 `Problems 1190 / Findings 4439`，`P0 698 / P1 378 / P2 99 / P3 15`，13 类。
2. 过滤 P0 + GRAIN_PROBLEM、搜索 table/process/workspace、切换排序 → 列表即时变化。
3. 打开 `problem_0050` → 机器评估 / 影响 / 根因 / 受影响的表 / 证据 / 人工裁决 全部有内容。
4. 选「已确认」、填姓名 + 理由 → 「保存并跳转」→ 下一条；刷新页面 → 裁决仍在。
5. 「导出裁决」→ 下载 `m36-human-adjudication.json`。
6. 「重新加载产物」→ 数字刷新但人工裁决不丢；「重置本机裁决」→ 必须两次确认。
7. 断开/改名 JSON 文件 → 显示明确错误，而不是「0 Problems」。

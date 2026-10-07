import { esc } from "./dom.js";
import {
  MACHINE_STATUS_LABELS,
  humanStatusLabel,
} from "../domain/types.js";
import { renderAffectedTables } from "./tables.js";
import { renderEvidencePanel } from "./evidence.js";
import { renderDecisionPanel } from "./decision.js";

/**
 * Problem Detail (spec §11–§19) — the core surface of the workbench.
 * @param {Object} ctx
 * @returns {string} HTML
 */
export function renderDetail(ctx) {
  const state = ctx.store.getState();
  const problem = state.selectedId ? ctx.problemRepo.get(state.selectedId) : null;

  if (!problem) {
    return `
      <div class="detail-empty">
        <div class="big">从左侧评审队列中选择一个问题。</div>
        <div>待人工裁决 · 机器识别的问题候选，最终结论由人工裁决。</div>
      </div>`;
  }

  const draft = state.drafts[problem.problem_id];
  const humanStatus = draft ? draft.human_status : "pending";

  return [
    headerHtml(problem, humanStatus),
    machineAssessmentHtml(ctx, problem),
    impactHtml(problem),
    rootCauseHtml(problem),
    renderAffectedTables(ctx, problem),
    renderEvidencePanel(ctx, problem),
    renderDecisionPanel(ctx, problem),
  ].join("");
}

function headerHtml(problem, humanStatus) {
  const classification = problem.classification || "unclassified";
  return `
    <section class="panel">
      <div class="detail-header">
        <div>
          <div class="dh-id">${esc(problem.problem_id)}</div>
          <div class="dh-badges">
            <span class="badge badge-type">${esc(problem.problem_type)}</span>
            <span class="badge badge-priority-${esc(problem.priority)}">${esc(problem.priority)}</span>
            <span class="badge badge-soft">证据强度: ${esc(problem.evidence_strength)}</span>
            <span class="badge badge-machine ${
              problem.status === "review_required" ? "is-review-required" : ""
            }">机器状态: ${esc(MACHINE_STATUS_LABELS[problem.status] || problem.status)}</span>
            <span class="badge badge-status-${esc(humanStatus)}">人工状态: ${esc(humanStatusLabel(humanStatus))}</span>
            <span class="badge badge-neutral">分类: ${esc(classification)}</span>
          </div>
          <p class="dh-desc">${esc(problem.description)}</p>
        </div>
        <div class="dh-side">
          <div class="kv"><div class="k">范围</div><div class="v mono">${esc(problem.scope)} · ${esc(
            problem.scope_key || "—",
          )}</div></div>
          <div class="kv" style="margin-top:8px">
            <div class="k">受影响表</div>
            <div class="v">${problem.affected_table_count}</div>
          </div>
          <div class="kv" style="margin-top:8px">
            <div class="k">证据行数</div>
            <div class="v">${problem.evidence_total}${problem.evidence_truncated ? " (truncated)" : ""}</div>
          </div>
        </div>
      </div>
    </section>`;
}

function kv(label, value, mono = false) {
  const empty = value === null || value === undefined || value === "" || (Array.isArray(value) && !value.length);
  return `
    <div class="kv">
      <div class="k">${esc(label)}</div>
      <div class="v ${mono ? "mono" : ""}">${empty ? '<span class="muted">—</span>' : esc(
        Array.isArray(value) ? value.join(", ") : value,
      )}</div>
    </div>`;
}

function machineAssessmentHtml(ctx, problem) {
  const modelShape = ctx.tableRepo.modelShapeFor(problem);
  const rationale = problem.rationale || {};
  const rationaleEntries = [
    ["现状", rationale.current_state],
    ["问题", rationale.problem],
    ["证据", rationale.evidence],
    ["影响", rationale.impact],
    ["为何要改", rationale.why_change],
  ].filter(([, value]) => value);

  return `
    <section class="panel">
      <div class="panel-head">
        <h3>机器评估</h3>
        <span class="machine-marker">机器发现 · 机器评估，不是人工结论</span>
      </div>
      <div class="panel-body">
        <div class="kv-grid">
          ${kv("为什么提出这个问题", problem.description)}
          ${kv("过程", problem.process_keys)}
          ${kv("粒度", problem.grain_keys)}
          ${kv("对象", problem.object_keys)}
          ${kv("模型形态", modelShape)}
          ${kv("受影响表", problem.affected_table_count)}
          ${kv("证据条数", problem.evidence_total)}
          ${kv("发现数量", problem.finding_count)}
          ${kv("发现类型", problem.finding_types)}
          ${kv("信号", problem.signals)}
          ${kv("证据强度", problem.evidence_strength)}
        </div>

        ${
          problem.human_question
            ? `<div class="question-box">
                <div class="q-label">机器提出的疑问（人工问题）</div>
                <div class="q-text">${esc(problem.human_question)}</div>
              </div>`
            : ""
        }

        ${
          problem.unresolved_reason
            ? `<div class="evidence-note">${esc(problem.unresolved_reason)}</div>`
            : ""
        }

        ${
          rationaleEntries.length
            ? `<details class="rationale">
                <summary>机器依据（${rationaleEntries.length} 段）</summary>
                <div class="rationale-kv">
                  ${rationaleEntries
                    .map(
                      ([label, value]) => `<div><div class="k">${esc(label)}</div><div class="v">${esc(value)}</div></div>`,
                    )
                    .join("")}
                </div>
              </details>`
            : ""
        }
      </div>
    </section>`;
}

function impactHtml(problem) {
  const hasTypes = (problem.impact_types || []).length > 0;
  const hasText = Boolean(problem.impact);
  if (!hasTypes && !hasText) return "";
  return `
    <section class="panel">
      <div class="panel-head">
        <h3>影响</h3>
        <span class="panel-note">机器评估的影响 · 结构推导，需人工确认</span>
      </div>
      <div class="panel-body">
        ${
          hasTypes
            ? `<div class="tag-row">${problem.impact_types
                .map((type) => `<span class="badge badge-soft">${esc(type)}</span>`)
                .join("")}</div>`
            : ""
        }
        ${hasText ? `<div class="evidence-note">${esc(problem.impact)}</div>` : ""}
      </div>
    </section>`;
}

function rootCauseHtml(problem) {
  if (!problem.root_cause) return "";
  return `
    <section class="panel">
      <div class="panel-head">
        <h3>根因</h3>
        <span class="panel-note">机器评估的根因 — 不是人工最终结论</span>
      </div>
      <div class="panel-body">
        <div class="tag-row">
          <span class="badge badge-type">${esc(problem.root_cause)}</span>
        </div>
        <div class="evidence-note">
          机器评估的根因：由 M3.6 产物推导，人工可保留、覆盖，或在「裁决理由」中补充真正的业务根因。
        </div>
      </div>
    </section>`;
}

/**
 * Bottom navigation (spec §24).
 * @param {Object} ctx
 * @param {{position: number, total: number, disabled: boolean}} meta
 * @returns {string} HTML
 */
export function renderDetailNav(ctx, meta) {
  const { position, total, disabled } = meta;
  const noop = disabled ? "disabled" : "";
  return `
    <button type="button" class="btn" data-action="prev" ${noop}>← 上一个</button>
    <button type="button" class="btn btn-primary" data-action="save" ${noop}>保存</button>
    <button type="button" class="btn btn-primary" data-action="save-next" ${noop}>保存并跳转</button>
    <button type="button" class="btn" data-action="next" ${noop}>下一个 →</button>
    <span class="nav-pos">${disabled ? "—" : `${position} / ${total}`}</span>
    <span class="nav-hint">快捷键：←/→ 切换 · 1 已确认 · 2 已拒绝 · 3 需进一步核实 · S 保存（输入框内不触发）</span>`;
}

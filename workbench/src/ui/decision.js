import { esc } from "./dom.js";
import { HUMAN_STATUSES, MACHINE_STATUS_LABELS, humanStatusLabel } from "../domain/types.js";

const OPTION_HINTS = {
  pending: "未裁决（清空本机裁决，回到默认状态）",
  confirmed: "人工确认：当前确实存在该模型问题",
  rejected: "人工确认：当前模型设计合理，机器判断不成立",
  needs_review: "需要进一步核实：证据或业务上下文不足",
};

/**
 * Human Decision (spec §18–§20). The only writable region of the workbench.
 * Machine status is shown read-only and is never overwritten.
 *
 * @param {Object} ctx
 * @param {import("../domain/types.js").Problem} problem
 * @returns {string} HTML
 */
export function renderDecisionPanel(ctx, problem) {
  const state = ctx.store.getState();
  const draft = state.drafts[problem.problem_id] || {
    human_status: "pending",
    human_name: "",
    human_note: "",
  };
  const saved = state.decisions[problem.problem_id] || null;

  return `
    <section class="panel" data-section="decision">
      <div class="panel-head">
        <h3>人工裁决</h3>
        <span class="panel-note">本区域是唯一可人工写入的位置（localStorage），机器产物只读</span>
      </div>
      <div class="machine-readonly">
        <span class="mr-label">机器状态</span>
        <span class="badge badge-machine ${problem.status === "review_required" ? "is-review-required" : ""}">${esc(
          MACHINE_STATUS_LABELS[problem.status] || problem.status,
        )}</span>
        <span class="mr-label">分类</span>
        <span class="badge badge-neutral">${esc(problem.classification || "unclassified")}</span>
        <span class="mr-label">人工状态</span>
        <span class="badge badge-status-${esc(draft.human_status)}">${esc(humanStatusLabel(draft.human_status))}</span>
        <span class="muted">机器发现 ≠ 已确认 — 机器候选不会被 UI 自动置为已确认。</span>
      </div>
      <div class="panel-body">
        <div class="decision-options" role="radiogroup" aria-label="人工状态">
          ${HUMAN_STATUSES.map(
            (status) => `
            <label class="decision-option ${draft.human_status === status ? "is-active" : ""}">
              <input type="radio" name="human-status" value="${status}"
                     data-action="set-status" ${draft.human_status === status ? "checked" : ""} />
              <span>
                <span class="do-title">${esc(humanStatusLabel(status))}</span>
                <span class="do-hint">${esc(OPTION_HINTS[status])}</span>
              </span>
            </label>`,
          ).join("")}
        </div>

        <div class="form-grid">
          <div class="field">
            <label for="human-name">评审人姓名</label>
            <input type="text" id="human-name" data-role="human-name" data-focus-key="human-name"
                   data-action="draft-field" data-field="human_name"
                   placeholder="评审人姓名" value="${esc(draft.human_name)}" />
            <span class="hint">第一版要求填写（已确认 / 已拒绝 / 需进一步核实 时必填）。不会自动伪造用户名。</span>
          </div>
          <div class="field">
            <label for="human-note">裁决理由</label>
            <textarea id="human-note" data-role="human-note" data-focus-key="human-note"
                      data-action="draft-field" data-field="human_note"
                      placeholder="请说明为什么确认 / 拒绝 / 需要进一步核实。">${esc(draft.human_note)}</textarea>
            <span class="hint">请引用业务规则、模型职责、来源系统、粒度或实际使用场景，便于形成重构证据（Refactoring Evidence）。</span>
          </div>
        </div>

        ${state.decisionError ? `<div class="field-error">${esc(state.decisionError)}</div>` : ""}
        <div class="saved-at">
          ${
            saved
              ? `已保存（本机 localStorage）：${esc(saved.updated_at)} · ${esc(
                  humanStatusLabel(saved.human_status),
                )} · ${esc(saved.human_name || "—")}`
              : "待人工裁决 — 尚未保存本机裁决。"
          }
        </div>
      </div>
    </section>`;
}

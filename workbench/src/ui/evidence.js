import { esc } from "./dom.js";
import { EVIDENCE_SOURCES } from "../domain/types.js";

/**
 * Evidence Explorer (spec §16–§17).
 * Tabs only when a type has evidence; every row carries its provenance.
 *
 * @param {Object} ctx
 * @param {import("../domain/types.js").Problem} problem
 * @returns {string} HTML
 */
export function renderEvidencePanel(ctx, problem) {
  const evidence = ctx.evidenceRepo.forProblem(problem);
  const tabs = ctx.evidenceRepo.tabs(evidence.counts);
  const active = state_activeTab(ctx, tabs);
  const rows = active === "overview" ? [] : ctx.evidenceRepo.rowsOfType(evidence.rows, active);

  return `
    <section class="panel" data-section="evidence">
      <div class="panel-head">
        <h3>证据</h3>
        <span class="panel-note">
          机器证据 · 共 ${evidence.total} 行${evidence.truncated ? `，已加载 ${evidence.rows.length} 行（产物按行数截断）` : ""}
        </span>
      </div>
      <div class="tabs" role="tablist">
        <button type="button" class="tab ${active === "overview" ? "is-active" : ""}"
                data-action="evidence-tab" data-tab="overview">概览 <span class="tab-count">${evidence.total}</span></button>
        ${tabs
          .map(
            (tab) => `
          <button type="button" class="tab ${active === tab.type ? "is-active" : ""}"
                  data-action="evidence-tab" data-tab="${esc(tab.type)}" title="来源：${esc(tab.source)}">
            ${esc(tab.type)} <span class="tab-count">${tab.count}</span>
          </button>`,
          )
          .join("")}
      </div>
      <div class="evidence-body">
        ${
          active === "overview"
            ? overviewHtml(ctx, problem, evidence, tabs)
            : rowsHtml(rows, active, evidence)
        }
      </div>
    </section>`;
}

function state_activeTab(ctx, tabs) {
  const state = ctx.store.getState();
  if (state.evidenceTab === "overview") return "overview";
  if (state.evidenceTab && tabs.some((tab) => tab.type === state.evidenceTab)) return state.evidenceTab;
  return "overview";
}

function overviewHtml(ctx, problem, evidence, tabs) {
  const summary = ctx.evidenceRepo;
  return `
    <div class="evidence-overview">
      ${tabs
        .map(
          (tab) => `
        <div class="evidence-count-card">
          <div class="c-type">${esc(tab.type)}</div>
          <div class="c-num">${tab.count}</div>
          <div class="c-type">${esc(tab.source)}</div>
        </div>`,
        )
        .join("")}
      ${
        tabs.length === 0
          ? `<div class="empty-note"><strong>当前 M3.6 产物没有可用证据。</strong><br/>这并不代表模型有问题。</div>`
          : ""
      }
    </div>
    <div class="evidence-note">
      证据来源说明：${esc(summary.note || "M3.6 分析产物")}${
        evidence.truncated
          ? ` —— 本问题共 ${evidence.total} 行，仅暴露 ${evidence.rows.length} 行（单问题行数上限 ${evidence.rowLimit}）。`
          : "。"
      }
    </div>
    <div class="evidence-note">
      机器发现 ≠ 问题 ≠ 已确认问题。证据由机器收集，结论由人工在「人工裁决」区域填写。
    </div>`;
}

function rowsHtml(rows, type, evidence) {
  const source = EVIDENCE_SOURCES[type] || "M3.6 分析";
  const expected = (evidence.counts && evidence.counts[type]) || 0;

  if (!rows.length) {
    if (expected > 0) {
      return `
        <div class="empty-note">
          <strong>产物中存在 ${expected} 行 ${esc(type)} 证据，但受单问题行数上限影响
          （上限 ${evidence.rowLimit} 行，已加载 ${evidence.rows.length} 行），本类型一行都未被加载。</strong><br/>
          这是产物截断，不是没有证据——也不代表模型有问题。
        </div>
        <div class="evidence-note">来源：${esc(source)} · 全量证据见 analysis/business/current-state-problem-evidence.json。</div>`;
    }
    return `<div class="empty-note"><strong>当前 M3.6 产物没有可用证据。</strong><br/>这并不代表模型有问题。</div>`;
  }

  return `
    <div class="table-scroll" style="max-height:340px">
      <table class="data-table">
        <thead>
          <tr>
            <th style="width:34%">引用标识</th>
            <th style="width:16%">证据类型</th>
            <th style="width:22%">来源</th>
            <th>原因说明</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (row) => `
            <tr>
              <td class="mono">${esc(row.evidence_id)}</td>
              <td><span class="p-type mono">${esc(row.evidence_type)}</span></td>
              <td class="muted">${esc(source)}</td>
              <td>${esc(row.reason || "—")}</td>
            </tr>`,
            )
            .join("")}
        </tbody>
      </table>
    </div>
    <div class="evidence-note">
      来源：${esc(source)} · 显示 ${rows.length}${
        expected > rows.length ? ` / ${expected}` : ""
      } 行${
        evidence.truncated ? `（产物单问题行数上限 ${evidence.rowLimit}，已截断）` : ""
      }。工作台不会重新推导这些证据。
    </div>`;
}

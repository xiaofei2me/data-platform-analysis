import { esc, percent } from "./dom.js";
import { computePriorityCounts, computeStatusCounts, computeTypeCounts } from "../logic/filtering.js";
import { PROBLEM_TYPE_LABELS } from "../domain/types.js";
import { SPECIAL_AUDITS } from "../logic/specialAudits.js";

const PROGRESS_ROWS = [
  ["confirmed", "已确认"],
  ["rejected", "已拒绝"],
  ["needs_review", "需进一步核实"],
  ["pending", "待裁决"],
];

/** 概览：只放关键数字与简单进度，不做图表墙。 */
export function renderOverview(ctx) {
  const state = ctx.store.getState();
  const problems = ctx.problemRepo.list();
  const statusCounts = computeStatusCounts(problems, state.decisions);
  const priorityCounts = computePriorityCounts(problems);
  const typeCounts = computeTypeCounts(problems);
  const topTypes = typeCounts.slice(0, 4);
  const otherCount = typeCounts.slice(4).reduce((sum, [, count]) => sum + count, 0);
  const summary = ctx.problemRepo.summary();

  const metrics = [
    ["问题总数", statusCounts.total, ""],
    ["待裁决", statusCounts.pending, ""],
    ["已确认", statusCounts.confirmed, "metric-success"],
    ["已拒绝", statusCounts.rejected, "metric-danger"],
    ["需进一步核实", statusCounts.needs_review, "metric-warning"],
  ];

  const html = `
    <div class="metric-row">
      ${metrics
        .map(
          ([label, value, cls]) => `
        <div class="metric ${cls}">
          <div class="metric-label">${esc(label)}</div>
          <div class="metric-value">${value}</div>
        </div>`,
        )
        .join("")}
      <div class="metric">
        <div class="metric-label">机器发现（Findings）</div>
        <div class="metric-value">${summary.finding_count}</div>
      </div>
    </div>

    <div class="breakdown-row">
      <span class="breakdown-label">优先级</span>
      ${["P0", "P1", "P2", "P3"]
        .map(
          (p) => `<span class="chip chip-${p.toLowerCase()}">${p} <strong>${priorityCounts[p]}</strong></span>`,
        )
        .join("")}
    </div>

    <div class="breakdown-row">
      <span class="breakdown-label">问题类型</span>
      ${topTypes
        .map(
          ([type, count]) =>
            `<span class="chip" title="${esc(type)}">${esc(PROBLEM_TYPE_LABELS[type] || type)} <strong>${count}</strong></span>`,
        )
        .join("")}
      ${otherCount ? `<span class="chip">其他 <strong>${otherCount}</strong></span>` : ""}
    </div>

    <div class="progress-block">
      <div class="progress-title">裁决进度</div>
      <div class="progress-grid">
        ${PROGRESS_ROWS.map(([key, label]) => {
          const value = statusCounts[key];
          return `
          <div class="progress-item">
            <div class="progress-head"><span>${label}</span><span>${value} / ${statusCounts.total}</span></div>
            <div class="progress-track">
              <div class="progress-fill is-${key}" style="width:${percent(value, statusCounts.total)}%"></div>
            </div>
          </div>`;
        }).join("")}
      </div>
    </div>

    <div class="audit-row">
      <span class="breakdown-label">特殊审查</span>
      ${SPECIAL_AUDITS.map((audit) => {
        const count = problems.filter(audit.predicate).length;
        const active = state.filters.auditId === audit.id;
        return `<button type="button" class="audit-btn ${active ? "is-active" : ""}" data-audit="${esc(
          audit.id,
        )}" title="${esc(audit.hint)}">${esc(audit.label)} <strong>${count}</strong></button>`;
      }).join("")}
      <span class="muted">仅用于聚焦审查，不重新计算。</span>
    </div>

    <div class="breakdown-row" style="margin-top:8px">
      <span class="breakdown-label">机器状态</span>
      ${Object.entries(ctx.problemRepo.summary().status_counts)
        .map(([status, count]) => `<span class="chip">${esc(status)} <strong>${count}</strong></span>`)
        .join("")}
      <span class="muted">机器状态与人工状态（本机裁决 ${Object.keys(state.decisions).length} 条）相互独立。</span>
    </div>
  `;

  document.getElementById("overview").innerHTML = html;
}

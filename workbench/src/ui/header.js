import { esc } from "./dom.js";
import { computeStatusCounts } from "../logic/filtering.js";

/**
 * 头部元信息：数据来源、加载时间与人工裁决计数。
 * 机器产物在此只读展示，没有任何修改入口。
 */
export function renderHeaderMeta(ctx) {
  const state = ctx.store.getState();
  const problems = ctx.problemRepo.list();
  const decisions = state.decisions;
  const counts = computeStatusCounts(problems, decisions);
  const loadedAt = state.loadedAt ? new Date(state.loadedAt).toLocaleString() : "—";

  const items = [
    ["数据来源", "静态 JSON 产物（只读）"],
    ["最近加载", loadedAt],
    ["待裁决", String(counts.pending)],
    ["已确认", String(counts.confirmed)],
    ["已拒绝", String(counts.rejected)],
    ["需进一步核实", String(counts.needs_review)],
  ];

  document.getElementById("header-meta").innerHTML = items
    .map(
      ([label, value]) =>
        `<span class="meta-item"><span class="meta-label">${esc(label)}</span>` +
        `<span class="meta-value">${esc(value)}</span></span>`,
    )
    .join("");
}

import { esc } from "./dom.js";
import { delegate } from "./dom.js";
import { PRIORITIES, PROBLEM_TYPES, PROBLEM_TYPE_LABELS, humanStatusLabel } from "../domain/types.js";
import { findAudit } from "../logic/specialAudits.js";

const STATUS_OPTIONS = [
  ["all", "全部"],
  ["pending", "待裁决"],
  ["confirmed", "已确认"],
  ["rejected", "已拒绝"],
  ["needs_review", "需进一步核实"],
];

const SORT_OPTIONS = [
  ["priority", "优先级"],
  ["problem_type", "问题类型"],
  ["problem_id", "问题编号"],
  ["affected_table_count", "受影响表数"],
  ["strength", "证据强度"],
  ["status", "人工状态"],
];

function segmented(name, options, activeValue) {
  return options
    .map(([value, label]) => {
      const cls = value === activeValue ? "is-active" : "";
      const extra = value === "P0" ? "seg-p0" : value === "P1" ? "seg-p1" : "";
      return `<button type="button" class="seg-btn ${extra} ${cls}" data-${name}="${esc(value)}">${esc(label)}</button>`;
    })
    .join("");
}

/** Build the filter block once so typing in search keeps focus. */
export function initQueueControls(ctx) {
  const root = document.getElementById("queue-filters");
  root.innerHTML = `
    <div class="filter-group">
      <span class="filter-label">优先级</span>
      <div class="segmented" data-group="priority">
        ${segmented("priority", [["all", "全部"], ...PRIORITIES.map((p) => [p, p])], "all")}
      </div>
    </div>
    <div class="filter-group">
      <span class="filter-label">人工状态</span>
      <div class="segmented" data-group="status">
        ${segmented("status", STATUS_OPTIONS, "all")}
      </div>
    </div>
    <div class="filter-group">
      <span class="filter-label">问题类型</span>
      <select data-role="type" aria-label="问题类型">
        <option value="all">全部类型（13）</option>
        ${PROBLEM_TYPES.map(
          (type) => `<option value="${esc(type)}">${esc(PROBLEM_TYPE_LABELS[type] || type)}（${esc(type)}）</option>`,
        ).join("")}
      </select>
    </div>
    <div class="filter-group">
      <span class="filter-label">搜索</span>
      <input type="search" data-role="search" data-focus-key="queue-search"
             placeholder="problem_id / 表 / 过程 / Workspace" />
    </div>
    <div class="filter-group">
      <span class="filter-label">排序</span>
      <div class="filter-row">
        <select data-role="sort" aria-label="排序字段">
          ${SORT_OPTIONS.map(([value, label]) => `<option value="${value}">${label} 升序</option>`).join("")}
        </select>
        <button type="button" class="seg-btn" data-role="sort-dir" title="切换升序 / 降序">升序</button>
      </div>
    </div>
  `;

  delegate(root, "[data-priority]", "click", (event, target) => {
    event.preventDefault();
    ctx.actions.setFilters({ priority: target.dataset.priority });
  });
  delegate(root, "[data-status]", "click", (event, target) => {
    event.preventDefault();
    ctx.actions.setFilters({ status: target.dataset.status });
  });
  delegate(root, '[data-role="type"]', "change", (event, target) => {
    ctx.actions.setFilters({ problem_type: target.value });
  });
  delegate(root, '[data-role="search"]', "input", (event, target) => {
    ctx.actions.setFilters({ search: target.value });
  });
  delegate(root, '[data-role="sort"]', "change", (event, target) => {
    ctx.actions.setSort({ field: target.value });
  });
  delegate(root, '[data-role="sort-dir"]', "click", (event, target) => {
    event.preventDefault();
    const current = ctx.store.getState().sort.direction;
    ctx.actions.setSort({ direction: current === "asc" ? "desc" : "asc" });
    target.textContent = current === "asc" ? "降序" : "升序";
  });
}

/** Keep filter controls in sync with state (active buttons / select values). */
export function updateQueueControls(ctx) {
  const state = ctx.store.getState();
  const { filters, sort } = state;
  const root = document.getElementById("queue-filters");

  root.querySelectorAll("[data-priority]").forEach((el) => {
    el.classList.toggle("is-active", el.dataset.priority === filters.priority);
  });
  root.querySelectorAll("[data-status]").forEach((el) => {
    el.classList.toggle("is-active", el.dataset.status === filters.status);
  });
  const typeSelect = /** @type {HTMLSelectElement} */ (root.querySelector('[data-role="type"]'));
  if (typeSelect.value !== filters.problem_type) typeSelect.value = filters.problem_type;
  const sortSelect = /** @type {HTMLSelectElement} */ (root.querySelector('[data-role="sort"]'));
  if (sortSelect.value !== sort.field) sortSelect.value = sort.field;
  const dirBtn = root.querySelector('[data-role="sort-dir"]');
  if (dirBtn) dirBtn.textContent = sort.direction === "asc" ? "升序" : "降序";
}

function rowHtml(problem, state, ctx) {
  const status = state.decisions[problem.problem_id]
    ? state.decisions[problem.problem_id].human_status
    : "pending";
  const selected = problem.problem_id === state.selectedId;
  const classification = problem.classification || "—";
  return `
    <button type="button" class="queue-item ${selected ? "is-selected" : ""}" role="option"
            aria-selected="${selected}" data-problem-id="${esc(problem.problem_id)}">
      <span class="qi-top">
        <span class="qi-id">${esc(problem.problem_id)}</span>
        <span class="badge badge-status-${esc(status)}">${esc(humanStatusLabel(status))}</span>
      </span>
      <span class="qi-sub">${esc(problem.priority)} · ${esc(problem.problem_type)}</span>
      <span class="qi-meta">
        <span>${esc(classification)}</span>
        <span>${esc(problem.evidence_strength)}</span>
        <span>${problem.affected_table_count} 张表</span>
      </span>
    </button>`;
}

/** Render queue meta, audit banner and the visible problem rows. */
export function renderQueueList(ctx) {
  const state = ctx.store.getState();
  const queue = state.queue;
  document.getElementById("queue-count").textContent = `显示 ${queue.length}`;
  document.getElementById("queue-list").innerHTML = queue.length
    ? queue.map((problem) => rowHtml(problem, state, ctx)).join("")
    : `<div class="queue-empty">没有符合当前筛选条件的问题。</div>`;

  const banner = document.getElementById("audit-banner");
  const audit = findAudit(state.filters.auditId);
  if (audit) {
    banner.classList.remove("hidden");
    banner.innerHTML = `<strong>${esc(audit.label)}</strong><div>${esc(audit.hint)}</div>
      <button type="button" class="audit-clear" data-role="clear-audit">清除特殊审查</button>`;
  } else {
    banner.classList.add("hidden");
    banner.innerHTML = "";
  }

  const list = document.getElementById("queue-list");
  delegateOnce(list, "[data-problem-id]", "click", (event, target) => {
    event.preventDefault();
    ctx.actions.selectProblem(target.dataset.problemId || null);
  });
  delegateOnce(banner, '[data-role="clear-audit"]', "click", (event, target) => {
    event.preventDefault();
    ctx.actions.clearAudit();
  });
}

/** Delegation must be bound once per container even when innerHTML changes. */
const boundDelegates = new WeakMap();

/**
 * @param {Element} root
 * @param {string} selector
 * @param {string} event
 * @param {(event: Event, target: HTMLElement) => void} handler
 */
function delegateOnce(root, selector, event, handler) {
  const token = `${event}:${selector}`;
  let tokens = boundDelegates.get(root);
  if (!tokens) {
    tokens = new Set();
    boundDelegates.set(root, tokens);
  }
  if (tokens.has(token)) return;
  tokens.add(token);
  delegate(root, selector, event, handler);
}

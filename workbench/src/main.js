import { loadArtifacts, describeLoadError, ArtifactsLoadError } from "./data/artifacts.js";
import { createProblemRepository } from "./data/problemRepository.js";
import { createEvidenceRepository } from "./data/evidenceRepository.js";
import { createTableRepository } from "./data/tableRepository.js";
import { createAdjudicationRepository } from "./data/adjudicationRepository.js";
import { createStore } from "./state/store.js";
import { buildQueue, nextId, previousId } from "./logic/filtering.js";
import { auditPredicate, findAudit } from "./logic/specialAudits.js";
import { esc, delegate, downloadJson } from "./ui/dom.js";
import { renderHeaderMeta } from "./ui/header.js";
import { renderOverview } from "./ui/overview.js";
import { initQueueControls, updateQueueControls, renderQueueList } from "./ui/queue.js";
import { renderDetail, renderDetailNav } from "./ui/detail.js";
import { humanStatusLabel } from "./domain/types.js";

const DEFAULT_FILTERS = { priority: "all", status: "all", problem_type: "all", search: "", auditId: null };
const DEFAULT_SORT = { field: "priority", direction: "asc" };

/** @type {any} */
let ctx = null;

function showLoading() {
  const list = document.getElementById("loading-files");
  list.innerHTML = [
    "../analysis/review/current-state-problems.json",
    "../analysis/review/current-state-problem-evidence.json",
    "../analysis/review/current-state-model-tables.json",
    "../analysis/evidence/layer/assessments.json",
  ]
    .map((path) => `<li>${esc(path)}</li>`)
    .join("");
}

function showLoadError(error) {
  const described = describeLoadError(error instanceof ArtifactsLoadError ? error : new ArtifactsLoadError(String(error && error.message)));
  const block = document.getElementById("loading-error");
  block.classList.remove("hidden");
  block.innerHTML = `
    <h3>${esc(described.title)}</h3>
    ${described.details.map((line) => `<div>${esc(line)}</div>`).join("")}
    <ul>${described.files.map((file) => `<li>${esc(file)}</li>`).join("")}</ul>
    <div style="margin-top:8px">数据加载失败 ≠ 0 个问题。</div>`;
  document.getElementById("loading-status").textContent = "加载失败。";
  document.getElementById("loading-status").classList.add("muted");
}

function toast(message, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.toggle("is-error", isError);
  el.classList.remove("hidden");
  clearTimeout(el.__timer);
  el.__timer = setTimeout(() => el.classList.add("hidden"), 2600);
}

/**
 * Rebuild the review queue whenever filters / sort / decisions change.
 * @param {Partial<any>} partial
 * @param {{silent?: boolean}} [options]
 */
function update(partial, options = {}) {
  const state = { ...ctx.store.getState(), ...partial };
  const queue = buildQueue(
    ctx.problemRepo.list(),
    state.decisions,
    state.filters,
    state.sort,
    auditPredicate(state.filters.auditId),
  );
  ctx.store.setState({ ...partial, queue }, options);
}

function selectProblem(problemId) {
  if (!problemId) return;
  const decision = ctx.store.getState().decisions[problemId] || null;
  const draft = decision
    ? {
        human_status: decision.human_status,
        human_name: decision.human_name,
        human_note: decision.human_note,
      }
    : {
        human_status: "pending",
        human_name: lastReviewerName(ctx.store.getState().decisions),
        human_note: "",
      };
  update({
    selectedId: problemId,
    evidenceTab: "overview",
    tableSearch: "",
    tableSort: { field: "table", direction: "asc" },
    expandedTable: null,
    decisionError: "",
    drafts: { ...ctx.store.getState().drafts, [problemId]: draft },
  });
}

function lastReviewerName(decisions) {
  const values = Object.values(decisions).filter((d) => d.human_name);
  return values.length ? values[values.length - 1].human_name : "";
}

function currentDraft() {
  const state = ctx.store.getState();
  if (!state.selectedId) return null;
  return state.drafts[state.selectedId] || null;
}

function saveDecision({ thenNext = false } = {}) {
  const state = ctx.store.getState();
  if (!state.selectedId) return false;
  const draft = currentDraft();
  if (!draft) return false;

  const result = ctx.adjudication.save({
    problem_id: state.selectedId,
    human_status: draft.human_status,
    human_name: draft.human_name,
    human_note: draft.human_note,
  });

  if (!result.ok) {
    update({ decisionError: result.error });
    toast(result.error, true);
    return false;
  }

  const decisions = { ...state.decisions };
  if (draft.human_status === "pending") {
    ctx.adjudication.clear(state.selectedId);
    delete decisions[state.selectedId];
  } else {
    decisions[state.selectedId] = result.decision;
  }

  update({ decisions, decisionError: "" });
  toast(
    draft.human_status === "pending"
      ? `已清除 ${state.selectedId} 的本机裁决（回到未裁决）。`
      : `已保存 ${state.selectedId}：${humanStatusLabel(draft.human_status)}（写入 localStorage）。`,
  );

  if (thenNext) {
    const target = nextId(state.queue.map((p) => p.problem_id), state.selectedId);
    if (target && target !== state.selectedId) selectProblem(target);
  }
  return true;
}

function moveSelection(direction) {
  const state = ctx.store.getState();
  const ids = state.queue.map((p) => p.problem_id);
  const target = direction === "next" ? nextId(ids, state.selectedId) : previousId(ids, state.selectedId);
  if (target && target !== state.selectedId) selectProblem(target);
}

async function reloadArtifacts() {
  const state = ctx.store.getState();
  const decisionCount = Object.keys(state.decisions).length;
  toast("正在重新加载产物…");
  try {
    const artifacts = await loadArtifacts();
    ctx.problemRepo = createProblemRepository(artifacts);
    ctx.evidenceRepo = createEvidenceRepository(artifacts);
    ctx.tableRepo = createTableRepository(artifacts);
    const queueStillHasSelection =
      state.selectedId && ctx.problemRepo.get(state.selectedId);
    const queue = buildQueue(
      ctx.problemRepo.list(),
      state.decisions,
      state.filters,
      state.sort,
      auditPredicate(state.filters.auditId),
    );
    ctx.store.setState({
      artifacts,
      loadedAt: artifacts.loadedAt,
      warnings: artifacts.warnings,
      queue,
      selectedId: queueStillHasSelection ? state.selectedId : queue[0] ? queue[0].problem_id : null,
    });
    render();
    toast(`产物已重新加载：本机裁决 ${decisionCount} 条已保留（localStorage 未改动）。`);
  } catch (error) {
    showLoadError(error);
    document.getElementById("loading-screen").classList.remove("hidden");
    document.getElementById("app").classList.add("hidden");
  }
}

function resetDecisions() {
  const result = ctx.adjudication.reset();
  if (result.ok) {
    const state = ctx.store.getState();
    const drafts = { ...state.drafts };
    if (state.selectedId) {
      drafts[state.selectedId] = {
        human_status: "pending",
        human_name: "",
        human_note: "",
      };
    }
    update({ decisions: {}, drafts, decisionError: "" });
    toast(`重置完成：已删除本机裁决 ${result.removed} 条。`);
  } else if (result.reason === "no-decisions") {
    toast("没有可重置的本机裁决。");
  } else {
    toast("已取消重置，本机裁决保留。", true);
  }
}

function exportDecisions() {
  const payload = ctx.adjudication.exportPayload();
  downloadJson("m36-human-adjudication.json", payload);
  toast(`已导出 ${payload.decisions.length} 条裁决 → m36-human-adjudication.json`);
}

/** Render everything; restore focus/caret for inputs marked data-focus-key. */
function render() {
  const active = document.activeElement;
  const focusKey =
    active && active.getAttribute && active.getAttribute("data-focus-key")
      ? active.getAttribute("data-focus-key")
      : null;
  const selection =
    focusKey && "selectionStart" in active ? { start: active.selectionStart, end: active.selectionEnd } : null;

  renderHeaderMeta(ctx);
  renderOverview(ctx);
  updateQueueControls(ctx);
  renderQueueList(ctx);

  const state = ctx.store.getState();
  document.getElementById("detail-body").innerHTML = renderDetail(ctx);
  const position = state.selectedId
    ? state.queue.findIndex((p) => p.problem_id === state.selectedId) + 1
    : 0;
  document.getElementById("detail-nav").innerHTML = renderDetailNav(ctx, {
    position,
    total: state.queue.length,
    disabled: !state.selectedId,
  });

  if (focusKey) {
    const restored = document.querySelector(`[data-focus-key="${focusKey}"]`);
    if (restored) {
      restored.focus();
      if (selection && "setSelectionRange" in restored) {
        restored.setSelectionRange(selection.start, selection.end);
      }
    }
  }
}

function bindStaticActions() {
  document.getElementById("btn-reload").addEventListener("click", reloadArtifacts);
  document.getElementById("btn-export").addEventListener("click", exportDecisions);
  document.getElementById("btn-reset").addEventListener("click", resetDecisions);

  delegate(document.getElementById("overview"), "[data-audit]", "click", (event, target) => {
    event.preventDefault();
    const id = target.dataset.audit;
    const current = ctx.store.getState().filters.auditId;
    if (current === id) {
      update({ filters: { ...ctx.store.getState().filters, auditId: null } });
    } else {
      const audit = findAudit(id);
      update({
        filters: { ...ctx.store.getState().filters, auditId: audit ? audit.id : null, problem_type: "all" },
      });
    }
  });

  const detailBody = document.getElementById("detail-body");
  delegate(detailBody, '[data-action="evidence-tab"]', "click", (event, target) => {
    event.preventDefault();
    update({ evidenceTab: target.dataset.tab || "overview" });
  });
  delegate(detailBody, '[data-action="toggle-table"]', "click", (event, target) => {
    const key = target.dataset.tableKey;
    const state = ctx.store.getState();
    update({ expandedTable: state.expandedTable === key ? null : key });
  });
  delegate(detailBody, '[data-action="set-status"]', "change", (event, target) => {
    const state = ctx.store.getState();
    if (!state.selectedId) return;
    const draft = currentDraft() || { human_status: "pending", human_name: "", human_note: "" };
    update(
      {
        drafts: {
          ...state.drafts,
          [state.selectedId]: { ...draft, human_status: target.value },
        },
        decisionError: "",
      },
      { silent: true },
    );
    render();
  });
  delegate(detailBody, '[data-action="draft-field"]', "input", (event, target) => {
    const state = ctx.store.getState();
    if (!state.selectedId) return;
    const draft = currentDraft() || { human_status: "pending", human_name: "", human_note: "" };
    const field = target.dataset.field;
    update(
      {
        drafts: {
          ...state.drafts,
          [state.selectedId]: { ...draft, [field]: target.value },
        },
      },
      { silent: true },
    );
  });
  delegate(detailBody, '[data-role="table-search"]', "input", (event, target) => {
    update({ tableSearch: target.value });
  });
  delegate(detailBody, '[data-role="table-sort"]', "change", (event, target) => {
    const state = ctx.store.getState();
    update({ tableSort: { field: target.value, direction: state.tableSort.direction } });
  });
  delegate(detailBody, '[data-action="table-sort-dir"]', "click", (event, target) => {
    event.preventDefault();
    const state = ctx.store.getState();
    update({
      tableSort: { field: state.tableSort.field, direction: state.tableSort.direction === "asc" ? "desc" : "asc" },
    });
  });

  const nav = document.getElementById("detail-nav");
  delegate(nav, '[data-action="save"]', "click", (event, target) => {
    event.preventDefault();
    saveDecision();
  });
  delegate(nav, '[data-action="save-next"]', "click", (event, target) => {
    event.preventDefault();
    saveDecision({ thenNext: true });
  });
  delegate(nav, '[data-action="prev"]', "click", (event, target) => {
    event.preventDefault();
    moveSelection("prev");
  });
  delegate(nav, '[data-action="next"]', "click", (event, target) => {
    event.preventDefault();
    moveSelection("next");
  });
}

function isTypingTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return Boolean(target.isContentEditable);
}

function bindKeyboard() {
  document.addEventListener("keydown", (event) => {
    if (isTypingTarget(event.target)) return;
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    switch (event.key) {
      case "ArrowLeft":
        event.preventDefault();
        moveSelection("prev");
        break;
      case "ArrowRight":
        event.preventDefault();
        moveSelection("next");
        break;
      case "1":
      case "2":
      case "3": {
        const map = { 1: "confirmed", 2: "rejected", 3: "needs_review" };
        const state = ctx.store.getState();
        if (!state.selectedId) break;
        const draft = currentDraft() || { human_name: "", human_note: "" };
        update(
          {
            drafts: {
              ...state.drafts,
              [state.selectedId]: { ...draft, human_status: map[event.key] },
            },
          },
          { silent: true },
        );
        render();
        break;
      }
      case "s":
      case "S":
        event.preventDefault();
        saveDecision();
        break;
      default:
        break;
    }
  });
}

function bindStore() {
  ctx.store.subscribe(() => render());
}

async function boot() {
  showLoading();
  try {
    const artifacts = await loadArtifacts();
    const adjudication = createAdjudicationRepository();
    const decisions = adjudication.loadAll();

    const store = createStore({
      artifacts,
      loadedAt: artifacts.loadedAt,
      warnings: artifacts.warnings,
      decisions,
      filters: { ...DEFAULT_FILTERS },
      sort: { ...DEFAULT_SORT },
      queue: [],
      selectedId: null,
      drafts: {},
      evidenceTab: "overview",
      tableSearch: "",
      tableSort: { field: "table", direction: "asc" },
      expandedTable: null,
      decisionError: "",
    });

    ctx = {
      store,
      adjudication,
      problemRepo: createProblemRepository(artifacts),
      evidenceRepo: createEvidenceRepository(artifacts),
      tableRepo: createTableRepository(artifacts),
      actions: {},
    };

    ctx.actions = {
      setFilters: (patch) => {
        const filters = { ...ctx.store.getState().filters, ...patch };
        if ("problem_type" in patch) filters.auditId = null;
        update({ filters });
      },
      setSort: (patch) => update({ sort: { ...ctx.store.getState().sort, ...patch } }),
      selectProblem,
      clearAudit: () => update({ filters: { ...ctx.store.getState().filters, auditId: null } }),
    };

    const queue = buildQueue(
      ctx.problemRepo.list(),
      decisions,
      ctx.store.getState().filters,
      ctx.store.getState().sort,
      null,
    );
    store.setState({ queue, selectedId: queue[0] ? queue[0].problem_id : null });
    if (queue[0]) selectProblem(queue[0].problem_id);

    document.getElementById("loading-screen").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");

    initQueueControls(ctx);
    bindStaticActions();
    bindKeyboard();
    bindStore();
    render();

    if (artifacts.warnings.length) {
      toast(artifacts.warnings.join(" · "), true);
    }
    const count = Object.keys(decisions).length;
    if (count) toast(`已从 localStorage 恢复 ${count} 条本机裁决。`);
  } catch (error) {
    console.error(error);
    showLoadError(error);
  }
}

boot();

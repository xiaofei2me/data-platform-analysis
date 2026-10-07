import { HUMAN_STATUSES, STORAGE_KEY } from "../domain/types.js";

/**
 * Human decisions live in localStorage only.
 *
 * JSON artifacts = machine source of truth (never written by this module).
 * localStorage  = human working state (exported, not auto-persisted back).
 *
 * Storage is injected so the module stays DOM-free and testable in Node.
 */

/**
 * @param {{storage?: Storage, now?: () => string, confirmFn?: (message: string) => boolean}} [deps]
 */
export function createAdjudicationRepository(deps = {}) {
  const storage = deps.storage || (typeof localStorage !== "undefined" ? localStorage : null);
  const now = deps.now || (() => new Date().toISOString());
  const confirmFn = deps.confirmFn || (typeof confirm === "function" ? confirm : () => false);

  if (!storage) {
    throw new Error("No storage available for human decisions.");
  }

  /**
   * @returns {Record<string, import("../domain/types.js").HumanDecision>}
   */
  function loadAll() {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return {};
    try {
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
      /** @type {Record<string, import("../domain/types.js").HumanDecision>} */
      const decisions = {};
      for (const [problemId, value] of Object.entries(parsed)) {
        if (!value || typeof value !== "object") continue;
        decisions[problemId] = {
          problem_id: problemId,
          human_status: HUMAN_STATUSES.includes(value.human_status) ? value.human_status : "pending",
          human_name: typeof value.human_name === "string" ? value.human_name : "",
          human_note: typeof value.human_note === "string" ? value.human_note : "",
          updated_at: typeof value.updated_at === "string" ? value.updated_at : "",
        };
      }
      return decisions;
    } catch {
      return {};
    }
  }

  /**
   * @param {string} problemId
   * @returns {import("../domain/types.js").HumanDecision|null}
   */
  function get(problemId) {
    return loadAll()[problemId] || null;
  }

  /**
   * @param {{problem_id: string, human_status: import("../domain/types.js").HumanStatus, human_name?: string, human_note?: string}} input
   * @returns {{ok: true, decision: import("../domain/types.js").HumanDecision} | {ok: false, error: string}}
   */
  function save(input) {
    const status = input.human_status;
    if (!HUMAN_STATUSES.includes(status)) {
      return { ok: false, error: `未知的人工状态：${status}` };
    }
    const name = (input.human_name || "").trim();
    const note = (input.human_note || "").trim();
    if (status !== "pending" && !name) {
      return { ok: false, error: "非「未裁决」状态必须填写评审人姓名。" };
    }
    const decisions = loadAll();
    const decision = {
      problem_id: input.problem_id,
      human_status: status,
      human_name: name,
      human_note: note,
      updated_at: now(),
    };
    decisions[input.problem_id] = decision;
    storage.setItem(STORAGE_KEY, JSON.stringify(decisions));
    return { ok: true, decision };
  }

  /**
   * @param {string} problemId
   * @returns {{ok: true} | {ok: false, reason: string}}
   */
  function clear(problemId) {
    const decisions = loadAll();
    if (!decisions[problemId]) return { ok: true };
    delete decisions[problemId];
    storage.setItem(STORAGE_KEY, JSON.stringify(decisions));
    return { ok: true };
  }

  /**
   * Double confirmation before wiping local decisions (spec §7 / §38).
   * @returns {{ok: true, removed: number} | {ok: false, reason: string}}
   */
  function reset() {
    const decisions = loadAll();
    const count = Object.keys(decisions).length;
    if (count === 0) return { ok: false, reason: "no-decisions" };
    const first = confirmFn(`重置本机裁决：将删除 ${count} 条本地裁决，是否继续？`);
    if (!first) return { ok: false, reason: "cancelled" };
    const second = confirmFn("再次确认：此操作不可撤销，确定删除全部本机裁决？");
    if (!second) return { ok: false, reason: "cancelled" };
    storage.removeItem(STORAGE_KEY);
    return { ok: true, removed: count };
  }

  /**
   * @returns {{generated_at: string, source: string, decisions: import("../domain/types.js").HumanDecision[]}}
   */
  function exportPayload() {
    const decisions = loadAll();
    return {
      generated_at: now(),
      source: "M3.6 Current-State Problem Assessment",
      decisions: Object.values(decisions).sort((a, b) => a.problem_id.localeCompare(b.problem_id)),
    };
  }

  /**
   * @returns {{total: number, confirmed: number, rejected: number, needs_review: number, pending_local: number}}
   */
  function localCounts() {
    const decisions = loadAll();
    const values = Object.values(decisions);
    return {
      total: values.length,
      confirmed: values.filter((d) => d.human_status === "confirmed").length,
      rejected: values.filter((d) => d.human_status === "rejected").length,
      needs_review: values.filter((d) => d.human_status === "needs_review").length,
      pending_local: values.filter((d) => d.human_status === "pending").length,
    };
  }

  return { loadAll, get, save, clear, reset, exportPayload, localCounts, storageKey: STORAGE_KEY };
}

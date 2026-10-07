import {
  HUMAN_STATUSES,
  PRIORITY_RANK,
  PROBLEM_TYPES,
  STRENGTH_RANK,
} from "../domain/types.js";

/**
 * Pure review-queue logic: filter, search, sort, counts, navigation.
 * No DOM, no storage — importable from Node for tests.
 */

/**
 * @param {import("../domain/types.js").ReviewFilter} filters
 * @returns {import("../domain/types.js").ReviewFilter}
 */
export function normalizeFilters(filters) {
  return {
    priority: filters.priority || "all",
    status: filters.status || "all",
    problem_type: filters.problem_type || "all",
    search: (filters.search || "").trim(),
    auditId: filters.auditId || null,
  };
}

/**
 * @param {import("../domain/types.js").ReviewSort} sort
 * @returns {import("../domain/types.js").ReviewSort}
 */
export function normalizeSort(sort) {
  const field = sort && sort.field ? sort.field : "priority";
  const direction = sort && sort.direction === "desc" ? "desc" : "asc";
  return { field, direction };
}

/**
 * Effective human status of a problem (defaults to pending).
 * @param {import("../domain/types.js").Problem} problem
 * @param {Record<string, import("../domain/types.js").HumanDecision>} decisions
 * @returns {import("../domain/types.js").HumanStatus}
 */
export function statusOf(problem, decisions) {
  const decision = decisions && decisions[problem.problem_id];
  return decision && HUMAN_STATUSES.includes(decision.human_status)
    ? decision.human_status
    : "pending";
}

/**
 * Case-insensitive substring match across id / process / table / workspace.
 * @param {import("../domain/types.js").Problem} problem
 * @param {string} term
 * @returns {boolean}
 */
export function matchesSearch(problem, term) {
  const q = term.trim().toLowerCase();
  if (!q) return true;
  const haystack = [];
  haystack.push(problem.problem_id);
  if (problem.scope_key) haystack.push(problem.scope_key);
  for (const key of problem.process_keys || []) haystack.push(key);
  for (const key of problem.grain_keys || []) haystack.push(key);
  for (const key of problem.object_keys || []) haystack.push(key);
  for (const key of problem.table_keys || []) {
    haystack.push(key);
    const dot = key.indexOf(".");
    if (dot > 0) {
      haystack.push(key.slice(0, dot)); // workspace / project
      haystack.push(key.slice(dot + 1)); // table name without project
    }
  }
  return haystack.some((value) => String(value).toLowerCase().includes(q));
}

/**
 * @param {import("../domain/types.js").Problem} problem
 * @param {import("../domain/types.js").ReviewFilter} filters
 * @param {Record<string, import("../domain/types.js").HumanDecision>} decisions
 * @param {((p: import("../domain/types.js").Problem) => boolean)|null} auditPredicate
 * @returns {boolean}
 */
export function matchesFilters(problem, filters, decisions, auditPredicate) {
  if (filters.priority !== "all" && problem.priority !== filters.priority) return false;
  if (filters.problem_type !== "all" && problem.problem_type !== filters.problem_type) return false;
  if (filters.status !== "all" && statusOf(problem, decisions) !== filters.status) return false;
  if (auditPredicate && !auditPredicate(problem)) return false;
  if (filters.search && !matchesSearch(problem, filters.search)) return false;
  return true;
}

/**
 * @param {import("../domain/types.js").Problem[]} problems
 * @param {Record<string, import("../domain/types.js").HumanDecision>} decisions
 * @param {import("../domain/types.js").ReviewFilter} filters
 * @param {((p: import("../domain/types.js").Problem) => boolean)|null} [auditPredicate]
 * @returns {import("../domain/types.js").Problem[]}
 */
export function filterProblems(problems, decisions, filters, auditPredicate = null) {
  const f = normalizeFilters(filters);
  return problems.filter((p) => matchesFilters(p, f, decisions, auditPredicate));
}

function compareStrings(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function sortKey(problem, field, decisions) {
  switch (field) {
    case "problem_type":
      return {
        rank: PROBLEM_TYPES.indexOf(problem.problem_type),
        secondary: problem.problem_type,
      };
    case "problem_id":
      return { rank: 0, secondary: problem.problem_id };
    case "affected_table_count":
      return { rank: problem.affected_table_count, secondary: problem.problem_id };
    case "strength":
      return { rank: STRENGTH_RANK[problem.evidence_strength] ?? 9, secondary: problem.problem_id };
    case "status": {
      const order = ["pending", "needs_review", "confirmed", "rejected"];
      return { rank: order.indexOf(statusOf(problem, decisions)), secondary: problem.problem_id };
    }
    case "priority":
    default:
      return { rank: PRIORITY_RANK[problem.priority] ?? 9, secondary: problem.problem_id };
  }
}

/**
 * Default order: Priority ASC, then Problem ID ASC (spec §9).
 * @param {import("../domain/types.js").Problem[]} problems
 * @param {import("../domain/types.js").ReviewSort} sort
 * @param {Record<string, import("../domain/types.js").HumanDecision>} decisions
 * @returns {import("../domain/types.js").Problem[]}
 */
export function sortProblems(problems, sort, decisions = {}) {
  const { field, direction } = normalizeSort(sort);
  const factor = direction === "desc" ? -1 : 1;
  const sorted = [...problems].sort((a, b) => {
    const ka = sortKey(a, field, decisions);
    const kb = sortKey(b, field, decisions);
    const primary = ka.rank - kb.rank;
    if (primary !== 0) return primary * factor;
    return compareStrings(ka.secondary, kb.secondary) * factor;
  });
  return sorted;
}

/**
 * Apply filter + sort in one step.
 * @param {import("../domain/types.js").Problem[]} problems
 * @param {Record<string, import("../domain/types.js").HumanDecision>} decisions
 * @param {import("../domain/types.js").ReviewFilter} filters
 * @param {import("../domain/types.js").ReviewSort} sort
 * @param {((p: import("../domain/types.js").Problem) => boolean)|null} [auditPredicate]
 * @returns {import("../domain/types.js").Problem[]}
 */
export function buildQueue(problems, decisions, filters, sort, auditPredicate = null) {
  return sortProblems(filterProblems(problems, decisions, filters, auditPredicate), sort, decisions);
}

/**
 * @param {string[]} queueIds
 * @param {string|null} selectedId
 * @returns {string|null}
 */
export function nextId(queueIds, selectedId) {
  if (!queueIds.length) return null;
  const index = queueIds.indexOf(selectedId);
  if (index < 0) return queueIds[0];
  return queueIds[Math.min(index + 1, queueIds.length - 1)];
}

/**
 * @param {string[]} queueIds
 * @param {string|null} selectedId
 * @returns {string|null}
 */
export function previousId(queueIds, selectedId) {
  if (!queueIds.length) return null;
  const index = queueIds.indexOf(selectedId);
  if (index < 0) return queueIds[0];
  return queueIds[Math.max(index - 1, 0)];
}

/**
 * @param {import("../domain/types.js").Problem[]} problems
 * @param {Record<string, import("../domain/types.js").HumanDecision>} decisions
 * @returns {{total: number, pending: number, confirmed: number, rejected: number, needs_review: number}}
 */
export function computeStatusCounts(problems, decisions) {
  const counts = { total: problems.length, pending: 0, confirmed: 0, rejected: 0, needs_review: 0 };
  for (const problem of problems) {
    counts[statusOf(problem, decisions)] += 1;
  }
  return counts;
}

/**
 * @param {import("../domain/types.js").Problem[]} problems
 * @returns {Record<string, number>}
 */
export function computePriorityCounts(problems) {
  const counts = { P0: 0, P1: 0, P2: 0, P3: 0 };
  for (const problem of problems) counts[problem.priority] = (counts[problem.priority] || 0) + 1;
  return counts;
}

/**
 * @param {import("../domain/types.js").Problem[]} problems
 * @returns {[string, number][]} type -> count, sorted by count desc
 */
export function computeTypeCounts(problems) {
  const counts = new Map();
  for (const problem of problems) {
    counts.set(problem.problem_type, (counts.get(problem.problem_type) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || compareStrings(a[0], b[0]));
}

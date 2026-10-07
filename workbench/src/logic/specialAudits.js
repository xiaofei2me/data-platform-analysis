/**
 * Special Audits (spec §23): lightweight filters that help reviewers focus on
 * classes of problems that need domain judgement. No recomputation happens —
 * these are predicates over existing artifacts only.
 */

/**
 * @typedef {Object} SpecialAudit
 * @property {string} id
 * @property {string} label
 * @property {string} hint
 * @property {string[]} [types] problem types to include
 * @property {string[]} [signals] machine signals to include (OR within, AND with types)
 * @property {(p: import("../domain/types.js").Problem) => boolean} predicate
 */

/** @type {SpecialAudit[]} */
export const SPECIAL_AUDITS = [
  {
    id: "fact-gate",
    label: "事实门（Fact Gate）",
    hint: "事实识别类问题：判断是否存在合法事实被传统 measure 规则排除。",
    types: ["FACT_IDENTIFICATION_PROBLEM"],
    predicate: (p) => p.problem_type === "FACT_IDENTIFICATION_PROBLEM",
  },
  {
    id: "unknown-model",
    label: "UNKNOWN 模型",
    hint: "缺少可解析锚点或证据的表：UNKNOWN = 证据不足 / 需要业务上下文，不是坏模型。",
    types: ["UNKNOWN_MODEL"],
    predicate: (p) => p.problem_type === "UNKNOWN_MODEL",
  },
  {
    id: "dimension-identification",
    label: "维度识别",
    hint: "业务对象的维度 / 事实角色尚未定论的问题。",
    types: ["DIMENSION_IDENTIFICATION_PROBLEM"],
    predicate: (p) => p.problem_type === "DIMENSION_IDENTIFICATION_PROBLEM",
  },
  {
    id: "aggregate-fact",
    label: "聚合事实（Aggregate Fact）",
    hint: "聚合形态模型与聚合信号：聚合事实完全可能是合理的。",
    types: ["AGGREGATION_MODEL_PROBLEM"],
    signals: ["AGGREGATE"],
    predicate: (p) =>
      p.problem_type === "AGGREGATION_MODEL_PROBLEM" || (p.signals || []).includes("AGGREGATE"),
  },
];

/**
 * @param {string|null|undefined} id
 * @returns {import("../domain/types.js").Problem|null} predicate or null
 */
export function auditPredicate(id) {
  if (!id) return null;
  const audit = SPECIAL_AUDITS.find((item) => item.id === id);
  return audit ? audit.predicate : null;
}

/**
 * @param {string|null|undefined} id
 * @returns {SpecialAudit|null}
 */
export function findAudit(id) {
  if (!id) return null;
  return SPECIAL_AUDITS.find((item) => item.id === id) || null;
}

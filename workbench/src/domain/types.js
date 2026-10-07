/**
 * M3.6 Workbench domain model.
 *
 * Machine status (artifact) and human status (localStorage) are deliberately
 * separate concepts. Nothing in this module may write back to any artifact.
 */

/**
 * @typedef {'pending'|'confirmed'|'rejected'|'needs_review'} HumanStatus
 * @typedef {'P0'|'P1'|'P2'|'P3'} Priority
 * @typedef {'candidate'|'review_required'|'confirmed'|'rejected'} MachineStatus
 *
 * @typedef {Object} HumanDecision
 * @property {string} problem_id
 * @property {HumanStatus} human_status
 * @property {string} human_name
 * @property {string} human_note
 * @property {string} updated_at ISO timestamp
 *
 * @typedef {Object} Problem
 * @property {string} problem_id
 * @property {string} problem_type
 * @property {Priority} priority
 * @property {string} severity
 * @property {MachineStatus} status machine status from the artifact
 * @property {boolean} human_validated
 * @property {boolean} human_review_required
 * @property {string} scope
 * @property {string} scope_key
 * @property {string} [classification]
 * @property {string[]} [table_keys]
 * @property {string[]} [process_keys]
 * @property {string[]} [grain_keys]
 * @property {string[]} [object_keys]
 * @property {string[]} [finding_ids]
 * @property {number} finding_count
 * @property {string[]} [finding_types]
 * @property {number} affected_table_count
 * @property {string[]} [signals]
 * @property {'weak'|'moderate'|'strong'} evidence_strength
 * @property {number} evidence_total
 * @property {boolean} evidence_truncated
 * @property {Record<string, number>} evidence_type_counts
 * @property {string[]} impact_types
 * @property {string} root_cause
 * @property {string} description
 * @property {string} impact
 * @property {string} unresolved_reason
 * @property {string} human_question
 * @property {{current_state?: string, problem?: string, evidence?: string, impact?: string, why_change?: string}} rationale
 * @property {Object[]} evidence sample rows embedded in problems.json
 *
 * @typedef {Object} EvidenceRow
 * @property {string} evidence_type
 * @property {string} evidence_id
 * @property {string} [table_key]
 * @property {string} [table_name]
 * @property {string|null} [column_name]
 * @property {string} [process_key]
 * @property {string} [grain_key]
 * @property {string} [object_key]
 * @property {string} [finding_id]
 * @property {string} reason
 *
 * @typedef {Object} ReviewFilter
 * @property {'all'|Priority} priority
 * @property {'all'|HumanStatus} status
 * @property {'all'|string} problem_type
 * @property {string} search
 * @property {string|null} auditId special audit preset id, null when off
 *
 * @typedef {Object} ReviewSort
 * @property {'priority'|'problem_type'|'problem_id'|'affected_table_count'|'strength'|'status'} field
 * @property {'asc'|'desc'} direction
 */

/** Machine statuses are read-only for this workbench. */
export const MACHINE_STATUSES = Object.freeze(["candidate", "review_required", "confirmed", "rejected"]);

/** Human statuses — the only values a reviewer may write (localStorage only). */
export const HUMAN_STATUSES = Object.freeze(["pending", "confirmed", "rejected", "needs_review"]);

export const PRIORITIES = Object.freeze(["P0", "P1", "P2", "P3"]);

/** Spec order for the Problem Type filter. */
export const PROBLEM_TYPES = Object.freeze([
  "GRAIN_PROBLEM",
  "MODEL_DUPLICATION",
  "MIXED_RESPONSIBILITY",
  "MODEL_OVERLAP",
  "FACT_IDENTIFICATION_PROBLEM",
  "PROCESS_MODEL_ALIGNMENT",
  "AGGREGATION_MODEL_PROBLEM",
  "DIMENSION_IDENTIFICATION_PROBLEM",
  "MODEL_ROLE_AMBIGUITY",
  "MODEL_SELECTION_AMBIGUITY",
  "SEMANTIC_AMBIGUITY",
  "MODEL_COVERAGE_GAP",
  "UNKNOWN_MODEL",
]);

export const STRENGTHS = Object.freeze(["weak", "moderate", "strong"]);

/** Evidence types, tab order from the spec. */
export const EVIDENCE_TYPES = Object.freeze([
  "GRAIN",
  "TABLE",
  "COLUMN",
  "PROCESS",
  "FINDING",
  "LINEAGE",
  "OBJECT",
  "RELATIONSHIP",
  "SQL",
]);

/**
 * Which analysis stage produced each evidence type.
 * Provenance only — the workbench never re-derives evidence.
 */
export const EVIDENCE_SOURCES = Object.freeze({
  FINDING: "M3.6 当前状态模型评审",
  TABLE: "M3.6 模型评审 / 表评估",
  COLUMN: "M3.6 模型评审 / 字段证据",
  GRAIN: "M3.4 粒度候选",
  PROCESS: "M3.3 业务过程候选",
  OBJECT: "M3.2 业务对象与关系",
  RELATIONSHIP: "M3.2 业务对象与关系",
  LINEAGE: "M1 血缘分析",
  SQL: "M3.5 SQL 分析",
});

export const HUMAN_STATUS_LABELS = Object.freeze({
  pending: "未裁决",
  confirmed: "已确认",
  rejected: "已拒绝",
  needs_review: "需进一步核实",
});

/** Machine status values stay verbatim — they are artifact identifiers. */
export const MACHINE_STATUS_LABELS = Object.freeze({
  candidate: "candidate",
  review_required: "review_required",
  confirmed: "confirmed",
  rejected: "rejected",
});

export const PROBLEM_TYPE_LABELS = Object.freeze({
  GRAIN_PROBLEM: "粒度问题",
  MODEL_DUPLICATION: "模型重复",
  MIXED_RESPONSIBILITY: "职责混杂",
  MODEL_OVERLAP: "模型重叠",
  FACT_IDENTIFICATION_PROBLEM: "事实识别",
  PROCESS_MODEL_ALIGNMENT: "过程与模型对齐",
  AGGREGATION_MODEL_PROBLEM: "聚合模型问题",
  DIMENSION_IDENTIFICATION_PROBLEM: "维度识别",
  MODEL_ROLE_AMBIGUITY: "模型角色歧义",
  MODEL_SELECTION_AMBIGUITY: "模型选择歧义",
  SEMANTIC_AMBIGUITY: "语义歧义",
  MODEL_COVERAGE_GAP: "覆盖缺口",
  UNKNOWN_MODEL: "未定模型",
});

/**
 * Words the UI must never use for UNKNOWN / fact-gate cases (spec §32).
 * @type {readonly string[]}
 */
export const FORBIDDEN_LABELS = Object.freeze(["bad", "invalid", "wrong"]);

export const STORAGE_KEY = "m36-human-adjudication";

export const PRIORITY_RANK = Object.freeze({ P0: 0, P1: 1, P2: 2, P3: 3 });
export const STRENGTH_RANK = Object.freeze({ strong: 0, moderate: 1, weak: 2 });

/**
 * @param {string|undefined} type
 * @returns {string}
 */
export function typeLabel(type) {
  return (type && PROBLEM_TYPE_LABELS[type]) || type || "—";
}

/**
 * @param {string|undefined} status
 * @returns {string}
 */
export function humanStatusLabel(status) {
  return (status && HUMAN_STATUS_LABELS[status]) || "Pending";
}

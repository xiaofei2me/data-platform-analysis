import { EVIDENCE_TYPES, EVIDENCE_SOURCES } from "../domain/types.js";

/**
 * Read-only access to current-state-problem-evidence.json.
 * Evidence is loaded per problem on demand — never all at once into the DOM.
 */
export function createEvidenceRepository(artifacts) {
  const artifact = artifacts.evidence;
  const byId = new Map((artifact.problems || []).map((entry) => [entry.problem_id, entry]));

  return {
    note: artifact.note,
    evidence_row_total: artifact.evidence_row_total,
    evidence_type_counts: artifact.evidence_type_counts,

    /** @param {string} problemId */
    get(problemId) {
      return byId.get(problemId) || null;
    },

    /**
     * Full evidence block for a problem, falling back to the sample embedded
     * in problems.json when the evidence artifact has no entry.
     * @param {import("../domain/types.js").Problem} problem
     * @returns {{rows: import("../domain/types.js").EvidenceRow[], counts: Record<string, number>, total: number, truncated: boolean, rowLimit: number, complete: boolean}}
     */
    forProblem(problem) {
      const entry = this.get(problem.problem_id);
      if (entry) {
        return {
          rows: entry.evidence || [],
          counts: entry.evidence_type_counts || {},
          total: entry.evidence_total || 0,
          truncated: Boolean(entry.evidence_truncated),
          rowLimit: entry.evidence_row_limit || 0,
          complete: !entry.evidence_truncated,
        };
      }
      return {
        rows: problem.evidence || [],
        counts: problem.evidence_type_counts || {},
        total: problem.evidence_total || 0,
        truncated: Boolean(problem.evidence_truncated),
        rowLimit: problem.evidence_sample_limit || 0,
        complete: false,
      };
    },

    /**
     * Rows of one evidence type, for a single tab.
     * @param {import("../domain/types.js").EvidenceRow[]} rows
     * @param {string} type
     */
    rowsOfType(rows, type) {
      return rows.filter((row) => row.evidence_type === type);
    },

    /** Tabs with non-zero counts only (spec §16). */
    tabs(counts) {
      return EVIDENCE_TYPES.map((type) => ({
        type,
        count: counts[type] || 0,
        source: EVIDENCE_SOURCES[type] || "M3.6 analysis",
      })).filter((tab) => tab.count > 0);
    },
  };
}

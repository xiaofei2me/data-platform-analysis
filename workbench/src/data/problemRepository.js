/**
 * Read-only access to current-state-problems.json.
 * Builds lookup indexes once; never mutates the artifact.
 */
export function createProblemRepository(artifacts) {
  const artifact = artifacts.problems;
  const problems = artifact.problems;
  const byId = new Map(problems.map((p) => [p.problem_id, p]));

  return {
    /** @returns {import("../domain/types.js").Problem[]} */
    list() {
      return problems;
    },

    /** @param {string} problemId */
    get(problemId) {
      return byId.get(problemId) || null;
    },

    /** Artifact-level summary numbers (machine side only). */
    summary() {
      return {
        count: artifact.count,
        finding_count: artifact.finding_count,
        note: artifact.note,
        priority_counts: artifact.priority_counts,
        problem_type_counts: artifact.problem_type_counts,
        status_counts: artifact.status_counts,
        evidence_strength_counts: artifact.evidence_strength_counts,
        distinct_affected_table_count: artifact.distinct_affected_table_count,
        finding_coverage: artifact.finding_coverage,
      };
    },
  };
}

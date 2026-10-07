import test from "node:test";
import assert from "node:assert/strict";
import {
  buildQueue,
  computePriorityCounts,
  computeStatusCounts,
  computeTypeCounts,
  filterProblems,
  matchesSearch,
  nextId,
  previousId,
  sortProblems,
  statusOf,
} from "../src/logic/filtering.js";
import { fixtureProblems, makeProblem } from "./fixtures.mjs";

const baseFilters = { priority: "all", status: "all", problem_type: "all", search: "", auditId: null };
const baseSort = { field: "priority", direction: "asc" };

test("filter by priority", () => {
  const problems = fixtureProblems();
  const p0 = filterProblems(problems, {}, { ...baseFilters, priority: "P0" });
  assert.deepEqual(
    p0.map((p) => p.problem_id),
    ["problem_0002", "problem_0005"],
  );
  const p3 = filterProblems(problems, {}, { ...baseFilters, priority: "P3" });
  assert.equal(p3.length, 1);
  assert.equal(p3[0].problem_id, "problem_0100");
});

test("filter by problem type", () => {
  const problems = fixtureProblems();
  const rows = filterProblems(problems, {}, { ...baseFilters, problem_type: "MODEL_DUPLICATION" });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].problem_id, "problem_0010");
});

test("filter by human status uses decisions, defaulting to pending", () => {
  const problems = fixtureProblems();
  const decisions = {
    problem_0010: {
      problem_id: "problem_0010",
      human_status: "confirmed",
      human_name: "alice",
      human_note: "ok",
      updated_at: "2026-10-06T00:00:00.000Z",
    },
    problem_0007: {
      problem_id: "problem_0007",
      human_status: "needs_review",
      human_name: "bob",
      human_note: "",
      updated_at: "2026-10-06T00:00:00.000Z",
    },
  };

  const confirmed = filterProblems(problems, decisions, { ...baseFilters, status: "confirmed" });
  assert.deepEqual(
    confirmed.map((p) => p.problem_id),
    ["problem_0010"],
  );

  const pending = filterProblems(problems, decisions, { ...baseFilters, status: "pending" });
  assert.equal(pending.length, 3);

  const needsReview = filterProblems(problems, decisions, { ...baseFilters, status: "needs_review" });
  assert.deepEqual(
    needsReview.map((p) => p.problem_id),
    ["problem_0007"],
  );

  assert.equal(statusOf(makeProblem({ problem_id: "problem_x" }), decisions), "pending");
  assert.equal(statusOf(problems[0], decisions), "confirmed");
});

test("search matches problem_id, table name, process id and workspace", () => {
  const problems = fixtureProblems();
  assert.ok(matchesSearch(problems[0], "problem_0010"));
  assert.ok(matchesSearch(problems[0], "dup_target"));
  assert.ok(matchesSearch(problems[0], "dme_ods"));
  assert.ok(matchesSearch(problems[0], "process_candidate_013"));
  assert.ok(matchesSearch(problems[2], "UNKNOWN_TABLE"));
  assert.ok(!matchesSearch(problems[2], "no_such_term"));

  const byWorkspace = filterProblems(problems, {}, { ...baseFilters, search: "dme_dwd" });
  assert.deepEqual(
    byWorkspace.map((p) => p.problem_id),
    ["problem_0007"],
  );
});

test("default sort is priority ASC then problem_id ASC", () => {
  const problems = fixtureProblems();
  const sorted = sortProblems(problems, baseSort, {});
  assert.deepEqual(
    sorted.map((p) => p.problem_id),
    ["problem_0002", "problem_0005", "problem_0010", "problem_0007", "problem_0100"],
  );
});

test("sort supports every spec field and both directions", () => {
  const problems = fixtureProblems();

  const byType = sortProblems(problems, { field: "problem_type", direction: "asc" }, {});
  assert.equal(byType[0].problem_type, "GRAIN_PROBLEM");

  const byIdDesc = sortProblems(problems, { field: "problem_id", direction: "desc" }, {});
  assert.equal(byIdDesc[0].problem_id, "problem_0100");

  const byTables = sortProblems(problems, { field: "affected_table_count", direction: "asc" }, {});
  assert.equal(byTables[0].affected_table_count, 0);
  assert.equal(byTables[byTables.length - 1].affected_table_count, 24);

  const byStrength = sortProblems(problems, { field: "strength", direction: "asc" }, {});
  assert.equal(byStrength[0].evidence_strength, "strong");
  assert.equal(byStrength[byStrength.length - 1].evidence_strength, "weak");

  // Status = human status: pending → needs_review → confirmed → rejected
  const decisions = {
    problem_0010: {
      problem_id: "problem_0010",
      human_status: "confirmed",
      human_name: "alice",
      human_note: "",
      updated_at: "",
    },
  };
  const byStatus = sortProblems(problems, { field: "status", direction: "asc" }, decisions);
  assert.equal(statusOf(byStatus[0], decisions), "pending");
  assert.equal(byStatus[byStatus.length - 1].problem_id, "problem_0010");
  assert.equal(statusOf(byStatus[byStatus.length - 1], decisions), "confirmed");
});

test("buildQueue combines filters and sort", () => {
  const problems = fixtureProblems();
  const queue = buildQueue(problems, {}, { ...baseFilters, priority: "P0" }, baseSort, null);
  assert.deepEqual(
    queue.map((p) => p.problem_id),
    ["problem_0002", "problem_0005"],
  );
});

test("problem selection: next and previous stay inside the queue", () => {
  const ids = ["problem_0002", "problem_0005", "problem_0010"];
  assert.equal(nextId(ids, "problem_0002"), "problem_0005");
  assert.equal(nextId(ids, "problem_0010"), "problem_0010");
  assert.equal(previousId(ids, "problem_0010"), "problem_0005");
  assert.equal(previousId(ids, "problem_0002"), "problem_0002");
  assert.equal(nextId(ids, "missing"), "problem_0002");
  assert.equal(nextId([], null), null);
  assert.equal(previousId([], null), null);
});

test("counts: status, priority and type", () => {
  const problems = fixtureProblems();
  const decisions = {
    problem_0010: {
      problem_id: "problem_0010",
      human_status: "rejected",
      human_name: "alice",
      human_note: "",
      updated_at: "",
    },
  };
  const statusCounts = computeStatusCounts(problems, decisions);
  assert.deepEqual(statusCounts, {
    total: 5,
    pending: 4,
    confirmed: 0,
    rejected: 1,
    needs_review: 0,
  });

  assert.deepEqual(computePriorityCounts(problems), { P0: 2, P1: 1, P2: 1, P3: 1 });

  const typeCounts = computeTypeCounts(problems);
  assert.equal(typeCounts.length, 5);
  assert.equal(typeCounts[0][1], 1);
});

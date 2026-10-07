import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  ArtifactsLoadError,
  describeLoadError,
  loadArtifacts,
  ARTIFACT_PATHS,
} from "../src/data/artifacts.js";
import { createAdjudicationRepository } from "../src/data/adjudicationRepository.js";
import { buildQueue, computePriorityCounts, computeTypeCounts, filterProblems } from "../src/logic/filtering.js";
import { createEvidenceRepository } from "../src/data/evidenceRepository.js";
import { createProblemRepository } from "../src/data/problemRepository.js";

const root = new URL("../../", import.meta.url);

async function readArtifact(relativePath) {
  return JSON.parse(await readFile(new URL(relativePath, root), "utf8"));
}

let problemsArtifact;
let evidenceArtifact;
let tableArtifact;
let layerArtifact;

test.before(async () => {
  problemsArtifact = await readArtifact("analysis/review/current-state-problems.json");
  evidenceArtifact = await readArtifact("analysis/review/current-state-problem-evidence.json");
  tableArtifact = await readArtifact("analysis/review/current-state-model-tables.json");
  layerArtifact = await readArtifact("analysis/layer/assessments.json");
});

test("machine artifacts: 1190 problems and 4439 findings", () => {
  assert.equal(problemsArtifact.count, 1190);
  assert.equal(problemsArtifact.problems.length, 1190);
  assert.equal(problemsArtifact.finding_count, 4439);
});

test("machine artifacts: priority counts P0/P1/P2/P3 = 698/378/99/15", () => {
  const computed = computePriorityCounts(problemsArtifact.problems);
  assert.deepEqual(computed, { P0: 698, P1: 378, P2: 99, P3: 15 });
  assert.deepEqual(problemsArtifact.priority_counts, computed);
});

test("machine artifacts: 13 problem types with expected counts", () => {
  const typeCounts = Object.fromEntries(computeTypeCounts(problemsArtifact.problems));
  assert.equal(Object.keys(typeCounts).length, 13);
  assert.deepEqual(typeCounts, {
    GRAIN_PROBLEM: 559,
    MODEL_DUPLICATION: 317,
    MIXED_RESPONSIBILITY: 204,
    MODEL_OVERLAP: 27,
    FACT_IDENTIFICATION_PROBLEM: 26,
    PROCESS_MODEL_ALIGNMENT: 15,
    AGGREGATION_MODEL_PROBLEM: 22,
    DIMENSION_IDENTIFICATION_PROBLEM: 1,
    MODEL_ROLE_AMBIGUITY: 4,
    MODEL_SELECTION_AMBIGUITY: 8,
    SEMANTIC_AMBIGUITY: 3,
    MODEL_COVERAGE_GAP: 2,
    UNKNOWN_MODEL: 2,
  });
  assert.deepEqual(problemsArtifact.problem_type_counts, typeCounts);
});

test("machine artifacts: status counts are candidate/review_required only", () => {
  assert.deepEqual(problemsArtifact.status_counts, {
    candidate: 1148,
    review_required: 42,
    confirmed: 0,
    rejected: 0,
  });
  const statuses = new Set(problemsArtifact.problems.map((p) => p.status));
  assert.deepEqual([...statuses].sort(), ["candidate", "review_required"]);
});

test("evidence artifact covers all problems with 30201 rows", () => {
  assert.equal(evidenceArtifact.count, 1190);
  assert.equal(evidenceArtifact.problems.length, 1190);
  assert.equal(evidenceArtifact.evidence_row_total, 30201);
  assert.equal(evidenceArtifact.evidence_type_counts.SQL, 0);
});

test("evidence artifact agrees with problems.json sample metadata", () => {
  const evidenceById = new Map(evidenceArtifact.problems.map((entry) => [entry.problem_id, entry]));
  for (const problem of problemsArtifact.problems.slice(0, 50)) {
    const entry = evidenceById.get(problem.problem_id);
    assert.ok(entry, `missing evidence entry for ${problem.problem_id}`);
    assert.equal(entry.evidence_total, problem.evidence_total);
    assert.deepEqual(entry.evidence_type_counts, problem.evidence_type_counts);
  }
});

test("model tables and layer artifacts cover 3719 tables", () => {
  assert.equal(tableArtifact.count, 3719);
  assert.equal(tableArtifact.tables.length, 3719);
  assert.equal(layerArtifact.count, 3719);
  assert.equal(layerArtifact.assessments.length, 3719);
});

test("workbench queue: default order and P0 filter over real data", () => {
  const repo = createProblemRepository({ problems: problemsArtifact });
  const filters = { priority: "all", status: "all", problem_type: "all", search: "", auditId: null };
  const sort = { field: "priority", direction: "asc" };
  const queue = buildQueue(repo.list(), {}, filters, sort, null);
  assert.equal(queue.length, 1190);
  assert.equal(queue[0].priority, "P0");

  const p0 = filterProblems(repo.list(), {}, { ...filters, priority: "P0" });
  assert.equal(p0.length, 698);

  const grain = filterProblems(repo.list(), {}, { ...filters, problem_type: "GRAIN_PROBLEM" });
  assert.equal(grain.length, 559);

  const byTable = filterProblems(repo.list(), {}, { ...filters, search: "dme_ads.dwd_crm_member_item" });
  assert.ok(byTable.some((p) => p.problem_id === "problem_0050"));
});

test("evidence repository exposes only tabs with counts", () => {
  const repo = createEvidenceRepository({ evidence: evidenceArtifact });
  const problem = problemsArtifact.problems.find((p) => p.problem_id === "problem_0857");
  const block = repo.forProblem(problem);
  assert.equal(block.total, 624);
  assert.equal(block.rows.length, 50);
  assert.equal(block.truncated, true);

  const tabs = repo.tabs(block.counts);
  assert.deepEqual(
    tabs.map((tab) => tab.type),
    ["GRAIN", "TABLE", "COLUMN", "PROCESS", "FINDING"],
  );
  assert.ok(!tabs.some((tab) => tab.type === "SQL"));
  for (const tab of tabs) {
    assert.ok(tab.source, `tab ${tab.type} must carry a provenance source`);
  }

  const grainRows = repo.rowsOfType(block.rows, "GRAIN");
  // Counts are artifact totals; loaded rows are limited by evidence_row_limit,
  // so a truncated problem may expose fewer rows than the tab badge shows.
  for (const row of grainRows) assert.equal(row.evidence_type, "GRAIN");
  assert.ok(grainRows.length <= block.counts.GRAIN);
});

test("loadArtifacts works with an injected fetch and never touches storage", async () => {
  const storage = (() => {
    const map = new Map();
    return {
      getItem: (k) => (map.has(k) ? map.get(k) : null),
      setItem: (k, v) => map.set(k, String(v)),
      removeItem: (k) => map.delete(k),
      snapshot: () => Object.fromEntries(map),
    };
  })();
  const adjudication = createAdjudicationRepository({ storage, confirmFn: () => true });
  adjudication.save({ problem_id: "problem_0001", human_status: "confirmed", human_name: "alice" });
  const before = storage.snapshot();

  const calls = [];
  const fetchImpl = async (url) => {
    calls.push(url);
    if (url.endsWith("current-state-model-tables.json") || url.endsWith("assessments.json")) {
      return { ok: false, status: 404, json: async () => ({}) };
    }
    return { ok: true, status: 200, json: async () => ({ problems: [], count: 0 }) };
  };

  const result = await loadArtifacts({ fetchImpl, protocol: "http:" });
  assert.equal(result.problems.count, 0);
  assert.equal(result.tableMeta, null);
  assert.equal(result.layer, null);
  assert.equal(result.warnings.length, 2);
  assert.equal(calls.length, 4);
  // Reload Artifacts must not overwrite Human Decisions
  assert.deepEqual(storage.snapshot(), before);
});

test("loadArtifacts fails loudly when a required artifact is missing", async () => {
  const fetchImpl = async (url) =>
    url.endsWith("current-state-problem-evidence.json")
      ? { ok: false, status: 404, json: async () => ({}) }
      : { ok: true, status: 200, json: async () => ({ problems: [] }) };

  await assert.rejects(
    () => loadArtifacts({ fetchImpl, protocol: "http:" }),
    (error) => {
      assert.ok(error instanceof ArtifactsLoadError);
      assert.match(error.message, /无法加载 M3\.6 产物/);
      return true;
    },
  );
});

test("loadArtifacts rejects file:// with serving instructions", async () => {
  await assert.rejects(
    () => loadArtifacts({ fetchImpl: async () => ({ ok: true, json: async () => ({}) }), protocol: "file:" }),
    (error) => {
      assert.equal(error.protocol, "file:");
      const described = describeLoadError(error);
      assert.equal(described.title, "无法加载 M3.6 产物。");
      assert.ok(described.details.some((line) => line.includes("http.server")));
      assert.deepEqual(described.files, [
        "current-state-problems.json",
        "current-state-problem-evidence.json",
      ]);
      return true;
    },
  );
});

test("artifact paths point at existing read-only files", async () => {
  const page = new URL("http://localhost/workbench/index.html");
  for (const relativePath of Object.values(ARTIFACT_PATHS)) {
    const httpUrl = new URL(relativePath, page);
    const fileUrl = new URL(httpUrl.pathname.replace(/^\//, ""), root);
    await assert.doesNotReject(() => readFile(fileUrl), `missing artifact: ${relativePath}`);
  }
});

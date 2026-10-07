import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { SPECIAL_AUDITS, auditPredicate, findAudit } from "../src/logic/specialAudits.js";

async function readArtifact(relativePath) {
  return JSON.parse(await readFile(new URL(`../../${relativePath}`, import.meta.url), "utf8"));
}

test("special audits are defined with ids and hints", () => {
  assert.deepEqual(
    SPECIAL_AUDITS.map((a) => a.id),
    ["fact-gate", "unknown-model", "dimension-identification", "aggregate-fact"],
  );
  for (const audit of SPECIAL_AUDITS) {
    assert.ok(audit.label);
    assert.ok(audit.hint);
    assert.equal(typeof audit.predicate, "function");
  }
  assert.equal(auditPredicate(null), null);
  assert.equal(auditPredicate("nope"), null);
  assert.equal(findAudit(null), null);
});

test("special audit counts over real artifacts", async () => {
  const artifact = await readArtifact("analysis/business/current-state-problems.json");
  const counts = Object.fromEntries(
    SPECIAL_AUDITS.map((audit) => [audit.id, artifact.problems.filter(audit.predicate).length]),
  );
  assert.deepEqual(counts, {
    "fact-gate": 26,
    "unknown-model": 2,
    "dimension-identification": 1,
    "aggregate-fact": 186,
  });
});

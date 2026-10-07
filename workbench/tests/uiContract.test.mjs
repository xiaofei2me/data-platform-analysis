import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { EVIDENCE_SOURCES, HUMAN_STATUSES, MACHINE_STATUSES, STORAGE_KEY } from "../src/domain/types.js";

const workbench = new URL("../", import.meta.url);

async function read(path) {
  return readFile(new URL(path, workbench), "utf8");
}

test("domain model keeps machine status and human status separate", () => {
  assert.deepEqual([...HUMAN_STATUSES], ["pending", "confirmed", "rejected", "needs_review"]);
  assert.deepEqual([...MACHINE_STATUSES], ["candidate", "review_required", "confirmed", "rejected"]);
  // human-only values that must not appear as machine statuses
  assert.ok(!MACHINE_STATUSES.includes("needs_review"));
  assert.ok(!MACHINE_STATUSES.includes("pending"));
  assert.equal(STORAGE_KEY, "m36-human-adjudication");
});

test("every evidence type carries a provenance source", () => {
  for (const type of ["FINDING", "TABLE", "COLUMN", "GRAIN", "PROCESS", "OBJECT", "RELATIONSHIP", "LINEAGE", "SQL"]) {
    assert.ok(EVIDENCE_SOURCES[type], `missing source for ${type}`);
  }
});

test("index.html exposes the required workbench structure", async () => {
  const html = await read("index.html");
  for (const marker of [
    'id="loading-screen"',
    'id="loading-error"',
    'id="header-meta"',
    'id="btn-reload"',
    'id="btn-reset"',
    'id="btn-export"',
    'id="overview"',
    'id="queue-filters"',
    'id="queue-list"',
    'id="detail-body"',
    'id="detail-nav"',
    "M3.6",
    "当前状态模型评审工作台",
    "人工裁决",
    "机器识别的问题候选，最终结论由人工裁决。",
  ]) {
    assert.ok(html.includes(marker), `index.html missing: ${marker}`);
  }
  // no machine-status editing affordance in static markup
  assert.ok(!html.includes("data-action=\"set-machine-status\""));
});

test("sources never mutate artifacts or auto-confirm problems", async () => {
  const files = ["src/main.js", "src/data/artifacts.js", "src/data/adjudicationRepository.js"];
  for (const file of files) {
    const source = await read(file);
    assert.ok(!source.includes("auto-confirm"), `${file} must not auto-confirm`);
    assert.ok(!/\bfetch\s*\(\s*[^\)]*method:\s*["']POST/.test(source), `${file} must not POST`);
  }
  // no code path writes confirmed directly into the artifact status
  const main = await read("src/main.js");
  assert.ok(!main.includes('status: "confirmed"'), "main.js must not set machine status");
  const adjudication = await read("src/data/adjudicationRepository.js");
  assert.ok(adjudication.includes("localStorage"), "human decisions must live in localStorage");
  assert.ok(!adjudication.includes("current-state-problems.json"), "adjudication store must not write artifacts");
});

test("UNKNOWN language stays neutral (spec §32)", async () => {
  const files = ["src/ui/detail.js", "src/ui/decision.js", "src/logic/specialAudits.js", "src/ui/overview.js"];
  for (const file of files) {
    const source = await read(file);
    assert.ok(!/>\s*Bad\s*</.test(source), `${file} must not label UNKNOWN as Bad`);
    assert.ok(!/Invalid Fact/.test(source), `${file} must not use "Invalid Fact"`);
    assert.ok(!/Wrong Model/.test(source), `${file} must not use "Wrong Model"`);
  }
  const audits = await read("src/logic/specialAudits.js");
  assert.match(audits, /不是坏模型/);
});

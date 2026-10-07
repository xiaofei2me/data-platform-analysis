import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { renderDetail, renderDetailNav } from "../src/ui/detail.js";
import { createProblemRepository } from "../src/data/problemRepository.js";
import { createEvidenceRepository } from "../src/data/evidenceRepository.js";
import { createTableRepository } from "../src/data/tableRepository.js";

async function readArtifact(relativePath) {
  return JSON.parse(await readFile(new URL(`../../${relativePath}`, import.meta.url), "utf8"));
}

const artifacts = {
  problems: await readArtifact("analysis/business/current-state-problems.json"),
  evidence: await readArtifact("analysis/business/current-state-problem-evidence.json"),
  tableMeta: await readArtifact("analysis/business/current-state-model-tables.json"),
  layer: await readArtifact("analysis/layer/assessments.json"),
};

function makeCtx(overrides = {}) {
  const state = {
    selectedId: null,
    drafts: {},
    decisions: {},
    tableSearch: "",
    tableSort: { field: "table", direction: "asc" },
    expandedTable: null,
    evidenceTab: "overview",
    decisionError: "",
    ...overrides,
  };
  return {
    store: { getState: () => state },
    problemRepo: createProblemRepository(artifacts),
    evidenceRepo: createEvidenceRepository(artifacts),
    tableRepo: createTableRepository(artifacts),
    state,
  };
}

test("detail renders machine assessment, impact, root cause and human decision", () => {
  const ctx = makeCtx({ selectedId: "problem_0050" });
  const html = renderDetail(ctx);

  assert.match(html, /problem_0050/);
  assert.match(html, /GRAIN_PROBLEM/);
  assert.match(html, /badge-priority-P0/);
  assert.match(html, /证据强度: strong/);
  assert.match(html, /机器状态: candidate/);
  assert.match(html, /人工状态: 未裁决/);
  assert.match(html, /机器发现 · 机器评估，不是人工结论/);
  assert.match(html, /机器评估的根因/);
  assert.match(html, /MULTIPLE_GRAINS_IN_ONE_MODEL/);
  assert.match(html, /人工问题/);
  // affected tables + evidence + decision sections
  assert.match(html, /data-section="tables"/);
  assert.match(html, /dme_ads\.dwd_crm_member_item/);
  assert.match(html, /data-section="evidence"/);
  assert.match(html, /data-section="decision"/);
  assert.match(html, /name="human-status"/);
  // no auto-confirmation affordance
  assert.ok(!html.includes("auto-confirm"));
  assert.ok(!html.includes("data-action=\"set-machine-status\""));
});

test("evidence tabs expose provenance and counts", () => {
  const ctx = makeCtx({ selectedId: "problem_0050" });
  const html = renderDetail(ctx);
  assert.match(html, /GRAIN <span class="tab-count">3<\/span>/);
  assert.match(html, /概览 <span class="tab-count">9<\/span>/);
  assert.match(html, /来源：M3\.4 粒度候选/);
  // SQL has zero rows everywhere → must not appear as a tab
  assert.ok(!/data-tab="SQL"/.test(html));
});

test("evidence tab with count but no loaded rows explains artifact truncation", () => {
  // problem_0857: 624 evidence rows, row limit 50 → GRAIN rows exist but are not loaded
  const ctx = makeCtx({ selectedId: "problem_0857", evidenceTab: "GRAIN" });
  const html = renderDetail(ctx);
  assert.match(html, /产物中存在 24 行 GRAIN 证据/);
  assert.match(html, /这是产物截断，不是没有证据/);
});

test("expanded affected table joins layer and model metadata", () => {
  const ctx = makeCtx({ selectedId: "problem_0050", expandedTable: "dme_ads.dwd_crm_member_item" });
  const html = renderDetail(ctx);
  assert.match(html, /模型形态/);
  assert.match(html, /分层判定/);
  assert.match(html, /current-state-model-tables\.json \+ layer\/assessments\.json/);
});

test("human decision panel separates machine status from human status", () => {
  const ctx = makeCtx({
    selectedId: "problem_0050",
    drafts: {
      problem_0050: { human_status: "needs_review", human_name: "alice", human_note: "" },
    },
    decisions: {
      problem_0050: {
        problem_id: "problem_0050",
        human_status: "needs_review",
        human_name: "alice",
        human_note: "need business owner input",
        updated_at: "2026-10-06T00:00:00.000Z",
      },
    },
    decisionError: "非「未裁决」状态必须填写评审人姓名。",
  });
  const html = renderDetail(ctx);
  assert.match(html, /机器状态/);
  assert.match(html, /机器状态: candidate/);
  assert.match(html, /人工状态/);
  assert.match(html, /人工状态: 需进一步核实/);
  assert.match(html, /必须填写评审人姓名/);
  assert.match(html, /已保存（本机 localStorage）：2026-10-06/);
  assert.match(html, /value="needs_review"[\s\S]*checked/);
});

test("detail shows an empty state when nothing is selected", () => {
  const html = renderDetail(makeCtx());
  assert.match(html, /从左侧评审队列中选择一个问题/);
  assert.match(html, /待人工裁决/);
});

test("affected tables without table_keys explain the empty state", () => {
  const problemsArtifact = artifacts.problems;
  const problem = problemsArtifact.problems.find((p) => !(p.table_keys || []).length);
  assert.ok(problem, "expected at least one problem without table_keys");
  const html = renderDetail(makeCtx({ selectedId: problem.problem_id }));
  assert.match(html, /没有可用的受影响表信息/);
});

test("UNKNOWN model detail stays neutral (no Bad / Invalid / Wrong)", () => {
  const unknown = artifacts.problems.problems.find((p) => p.problem_type === "UNKNOWN_MODEL");
  const html = renderDetail(makeCtx({ selectedId: unknown.problem_id }));
  assert.ok(!/>\s*Bad\b/.test(html));
  assert.ok(!/Invalid/.test(html));
  assert.ok(!/Wrong/.test(html));
  assert.match(html, /UNKNOWN_MODEL/);
});

test("detail nav renders the continuous-review controls", () => {
  const html = renderDetailNav(makeCtx(), { position: 3, total: 698, disabled: false });
  assert.match(html, /← 上一个/);
  assert.match(html, />保存</);
  assert.match(html, /保存并跳转/);
  assert.match(html, /下一个 →/);
  assert.match(html, /3 \/ 698/);

  const disabled = renderDetailNav(makeCtx(), { position: 0, total: 0, disabled: true });
  assert.match(disabled, /disabled/);
  assert.match(disabled, /—/);
});

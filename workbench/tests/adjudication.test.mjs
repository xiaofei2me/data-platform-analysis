import test from "node:test";
import assert from "node:assert/strict";
import { createAdjudicationRepository } from "../src/data/adjudicationRepository.js";
import { STORAGE_KEY } from "../src/domain/types.js";

function fakeStorage(initial = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => map.set(key, String(value)),
    removeItem: (key) => map.delete(key),
    snapshot: () => Object.fromEntries(map),
  };
}

function makeRepo(storage, { confirmFn = () => false, now } = {}) {
  return createAdjudicationRepository({ storage, confirmFn, now });
}

test("save confirmed requires a human name", () => {
  const storage = fakeStorage();
  const repo = makeRepo(storage);
  const result = repo.save({ problem_id: "problem_0010", human_status: "confirmed" });
  assert.equal(result.ok, false);
  assert.match(result.error, /必须填写评审人姓名/);
  assert.deepEqual(storage.snapshot(), {});
});

test("save rejects unknown statuses", () => {
  const repo = makeRepo(fakeStorage());
  const result = repo.save({ problem_id: "problem_0010", human_status: "auto-approved" });
  assert.equal(result.ok, false);
  assert.match(result.error, /未知的人工状态/);
});

test("decisions persist across repository instances (page refresh)", () => {
  const storage = fakeStorage();
  const first = makeRepo(storage, { now: () => "2026-10-06T01:00:00.000Z" });
  const saved = first.save({
    problem_id: "problem_0010",
    human_status: "confirmed",
    human_name: "alice",
    human_note: "business rule X",
  });
  assert.equal(saved.ok, true);

  // new repository instance = refreshed page, same localStorage
  const second = makeRepo(storage);
  const all = second.loadAll();
  assert.deepEqual(Object.keys(all), ["problem_0010"]);
  assert.equal(all.problem_0010.human_status, "confirmed");
  assert.equal(all.problem_0010.human_name, "alice");
  assert.equal(all.problem_0010.human_note, "business rule X");
  assert.equal(all.problem_0010.updated_at, "2026-10-06T01:00:00.000Z");
  assert.equal(second.get("problem_0010").human_status, "confirmed");
});

test("pending may be saved without a name and clears to pending", () => {
  const storage = fakeStorage();
  const repo = makeRepo(storage);
  const result = repo.save({ problem_id: "problem_0002", human_status: "pending" });
  assert.equal(result.ok, true);
  assert.equal(repo.get("problem_0002").human_status, "pending");
});

test("clear removes a single decision", () => {
  const storage = fakeStorage();
  const repo = makeRepo(storage);
  repo.save({ problem_id: "problem_0002", human_status: "rejected", human_name: "bob" });
  repo.clear("problem_0002");
  assert.deepEqual(repo.loadAll(), {});
});

test("reset requires two confirmations", () => {
  const storage = fakeStorage();
  const repo = makeRepo(storage);
  repo.save({ problem_id: "problem_0002", human_status: "rejected", human_name: "bob" });

  const calls = [];
  const confirm = makeRepo(storage, {
    confirmFn: (message) => {
      calls.push(message);
      return calls.length < 2; // first yes, second no
    },
  });
  const cancelled = confirm.reset();
  assert.equal(cancelled.ok, false);
  assert.equal(cancelled.reason, "cancelled");
  assert.equal(calls.length, 2);
  // data survives a cancelled reset
  assert.equal(repo.get("problem_0002").human_status, "rejected");

  const wiped = makeRepo(storage, { confirmFn: () => true }).reset();
  assert.equal(wiped.ok, true);
  assert.equal(wiped.removed, 1);
  assert.equal(storage.getItem(STORAGE_KEY), null);
});

test("reset on empty store reports no-decisions without prompting", () => {
  let prompts = 0;
  const repo = makeRepo(fakeStorage(), {
    confirmFn: () => {
      prompts += 1;
      return true;
    },
  });
  const result = repo.reset();
  assert.equal(result.ok, false);
  assert.equal(result.reason, "no-decisions");
  assert.equal(prompts, 0);
});

test("export payload matches the spec format", () => {
  const storage = fakeStorage();
  const repo = makeRepo(storage, { now: () => "2026-10-06T02:00:00.000Z" });
  repo.save({ problem_id: "problem_0010", human_status: "confirmed", human_name: "alice" });
  repo.save({ problem_id: "problem_0002", human_status: "needs_review", human_name: "alice" });

  const payload = repo.exportPayload();
  assert.equal(payload.generated_at, "2026-10-06T02:00:00.000Z");
  assert.equal(payload.source, "M3.6 Current-State Problem Assessment");
  assert.deepEqual(
    payload.decisions.map((d) => d.problem_id),
    ["problem_0002", "problem_0010"],
  );
  for (const decision of payload.decisions) {
    assert.deepEqual(Object.keys(decision).sort(), [
      "human_name",
      "human_note",
      "human_status",
      "problem_id",
      "updated_at",
    ]);
  }
});

test("corrupted storage degrades to an empty decision map", () => {
  const storage = fakeStorage({ [STORAGE_KEY]: "{not-json" });
  const repo = makeRepo(storage);
  assert.deepEqual(repo.loadAll(), {});
});

test("storage holds a plain object keyed by problem_id", () => {
  const storage = fakeStorage();
  const repo = makeRepo(storage);
  repo.save({ problem_id: "problem_0857", human_status: "confirmed", human_name: "alice" });
  const parsed = JSON.parse(storage.getItem(STORAGE_KEY));
  assert.equal(typeof parsed, "object");
  assert.equal(Array.isArray(parsed), false);
  assert.equal(parsed.problem_0857.human_status, "confirmed");
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { executionModeAt, scopesFromRegistry, wipOf } from "../registry.mjs";
import { loadBloodbank } from "../deps.mjs";
import { registryFixture, tempDir, TOLT } from "./helpers.mjs";

const { registry: bbRegistry } = loadBloodbank();
const activation = bbRegistry.bloodbankActivation;
const legacy = () => "legacy";

test("scopes: every owning row; advisory, retired, disabled and plane-less rows are not scopes", () => {
  const { scopes, skipped } = scopesFromRegistry(registryFixture(), { activation, executionMode: legacy });
  assert.deepEqual(scopes.map((s) => s.agentId), ["lost-things-forge-pm", "other-pm", "solo-pm", "tolt-director", "tolt-pm"]);
  const why = Object.fromEntries(skipped.map((s) => [s.agentId, s.why]));
  assert.match(why["tolt-launch-director"], /names no board/);
  assert.match(why["retired-pm"], /bloodbank.enabled is false/);
  assert.equal(why["no-plane"], undefined, "a row without a plane block is not considered at all");

  const toltPm = scopes.find((s) => s.agentId === "tolt-pm");
  assert.deepEqual(
    { board: toltPm.boardId, labels: toltPm.scopeLabels, dflt: toltPm.scopeDefault, wip: toltPm.wip, review: toltPm.review },
    { board: TOLT, labels: ["repo:game"], dflt: true, wip: 2, review: false },
  );
  const solo = scopes.find((s) => s.agentId === "solo-pm");
  assert.equal(solo.wip, 1);
  assert.equal(solo.review, true);
});

test("scopes: retirement by row status, board_scope advisory and gateway mismatch are skipped", () => {
  const reg = registryFixture();
  reg.agents["other-pm"].status = "retired";
  reg.agents["solo-pm"].board_scope = "advisory";
  reg.agents["tolt-director"].bloodbank.target_agent_id = "someone-else";
  const { scopes, skipped } = scopesFromRegistry(reg, { activation, executionMode: legacy });
  assert.deepEqual(scopes.map((s) => s.agentId), ["lost-things-forge-pm", "tolt-pm"]);
  const why = Object.fromEntries(skipped.map((s) => [s.agentId, s.why]));
  assert.match(why["other-pm"], /retired \(status is retired\)/);
  assert.match(why["solo-pm"], /advisory/);
  assert.match(why["tolt-director"], /target_agent_id mismatch/);
});

test("scopes: a repo fenced to a non-legacy execution.mode is skipped", () => {
  const { scopes, skipped } = scopesFromRegistry(registryFixture(), {
    activation,
    executionMode: (path) => (path.endsWith("/solo-pm") ? "managed" : "legacy"),
  });
  assert.ok(!scopes.some((s) => s.agentId === "solo-pm"));
  assert.match(skipped.find((s) => s.agentId === "solo-pm").why, /fenced: .*execution.mode is managed/);
});

test("scopes: --board filters by identifier (any case) or board id", () => {
  const byKey = scopesFromRegistry(registryFixture(), { activation, executionMode: legacy, board: "tolt" });
  assert.deepEqual(byKey.scopes.map((s) => s.agentId), ["lost-things-forge-pm", "tolt-director", "tolt-pm"]);
  assert.equal(byKey.matchedRows, 4, "the advisory launch director row names TOLT too");
  const byId = scopesFromRegistry(registryFixture(), { activation, executionMode: legacy, board: "b-solo" });
  assert.deepEqual(byId.scopes.map((s) => s.agentId), ["solo-pm"]);
  assert.equal(scopesFromRegistry(registryFixture(), { activation, executionMode: legacy, board: "NOPE" }).matchedRows, 0);
});

test("plane.wip: default 2, explicit values honoured, garbage warned and defaulted", () => {
  assert.deepEqual(wipOf({}), { wip: 2 });
  assert.deepEqual(wipOf({ wip: 0 }), { wip: 0 });
  assert.deepEqual(wipOf({ wip: 5 }), { wip: 5 });
  assert.equal(wipOf({ wip: "3" }).wip, 2);
  assert.match(wipOf({ wip: -1 }).warning, /not a non-negative integer/);
});

test("executionModeAt: .project.json execution.mode, legacy when absent or unreadable", () => {
  const dir = tempDir();
  const managed = join(dir, "managed");
  const plain = join(dir, "plain");
  mkdirSync(managed);
  mkdirSync(plain);
  writeFileSync(join(managed, ".project.json"), JSON.stringify({ execution: { mode: "shadow" } }));
  writeFileSync(join(plain, ".project.json"), JSON.stringify({ execution: null }));
  assert.equal(executionModeAt(managed), "shadow");
  assert.equal(executionModeAt(plain), "legacy");
  assert.equal(executionModeAt(join(dir, "missing")), "legacy");
});

test("scopes: client workspaces and plane.krebs false are never scopes", () => {
  const reg = registryFixture();
  reg.agents["other-pm"].plane.workspace = "AutomaticAI";
  reg.agents["solo-pm"].plane.krebs = false;
  const { scopes, skipped } = scopesFromRegistry(reg, { activation, executionMode: legacy });
  assert.deepEqual(scopes.map((s) => s.agentId), ["lost-things-forge-pm", "tolt-director", "tolt-pm"]);
  const why = Object.fromEntries(skipped.map((s) => [s.agentId, s.why]));
  assert.match(why["other-pm"], /client workspace AutomaticAI: owner-reserved/);
  assert.match(why["solo-pm"], /plane.krebs is false/);
});

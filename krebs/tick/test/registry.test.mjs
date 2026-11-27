import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { executionModeAt, launchModeAt, scopesFromRegistry, wipOf } from "../registry.mjs";
import { loadBloodbank } from "../deps.mjs";
import { registryFixture, tempDir, TOLT } from "./helpers.mjs";

const { registry: bbRegistry } = loadBloodbank();
const activation = bbRegistry.bloodbankActivation;
const legacy = () => "legacy";

test("scopes: every owning row; advisory, retired, disabled and plane-less rows are not scopes", () => {
  const { scopes, skipped } = scopesFromRegistry(registryFixture(), { activation, executionMode: legacy });
  assert.deepEqual(scopes.map((s) => s.agentId), ["lost-things-forge-pm", "other-pm", "solo-pm", "tolt-director", "tolt-pm"]);
  const why = Object.fromEntries(skipped.map((s) => [s.agentId, s.why]));
  assert.match(why["tolt-advisor"], /names no board/);
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
  assert.equal(byKey.matchedRows, 4, "the advisory row names TOLT too");
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

test("launchModeAt: mode and polish.wip, tolerantly; steady is develop; broken is develop, never an error", () => {
  const dir = tempDir();
  const repo = join(dir, "repo");
  mkdirSync(repo);
  assert.deepEqual(launchModeAt(join(dir, "missing")), { mode: "develop", polishWip: null });
  writeFileSync(join(repo, ".launch.yaml"), "mode: polish\ndeclared: 2026-11-27\npolish:\n  focus: [ux]\n  wip: 6\n  cadence: \"*/15 * * * *\"\n");
  assert.deepEqual(launchModeAt(repo), { mode: "polish", polishWip: 6 });
  writeFileSync(join(repo, ".launch.yaml"), "mode: polish\n");
  assert.deepEqual(launchModeAt(repo), { mode: "polish", polishWip: null });
  writeFileSync(join(repo, ".launch.yaml"), 'mode: "Launch"  # racing\n');
  assert.deepEqual(launchModeAt(repo), { mode: "launch", polishWip: null });
  writeFileSync(join(repo, ".launch.yaml"), "mode: steady\n");
  assert.equal(launchModeAt(repo).mode, "develop", "steady is the legacy alias of develop");
  writeFileSync(join(repo, ".launch.yaml"), "mode: whatever\n");
  assert.equal(launchModeAt(repo).mode, "develop", "unknown modes read as develop");
  writeFileSync(join(repo, ".launch.yaml"), "\x00 not: [yaml\n  - ][\n");
  assert.deepEqual(launchModeAt(repo), { mode: "develop", polishWip: null }, "a broken file is develop, never an error");
  writeFileSync(join(repo, ".launch.yaml"), "live:\n  mode: polish\n  wip: 9\n");
  assert.deepEqual(launchModeAt(repo), { mode: "develop", polishWip: null }, "only top-level mode: and polish: count");
});

test("scopes: a repo declaring .launch.yaml mode polish gets max(plane.wip or 2, polish.wip or 4)", () => {
  const dir = tempDir();
  const mk = (name, yaml) => {
    const p = join(dir, name);
    mkdirSync(p);
    writeFileSync(join(p, ".launch.yaml"), yaml);
    return p;
  };
  const reg = registryFixture();
  reg.agents["tolt-pm"].project_path = mk("polish-default", "mode: polish\n"); // no plane.wip, no polish.wip
  reg.agents["tolt-director"].project_path = mk("polish-6", "mode: polish\npolish:\n  wip: 6\n");
  reg.agents["lost-things-forge-pm"].project_path = mk("broken", "mode: [broken\n  ][\n");
  reg.agents["other-pm"].project_path = mk("launch", "mode: launch\n");
  reg.agents["solo-pm"].project_path = mk("polish-big-row", "mode: polish\npolish:\n  wip: 3\n");
  reg.agents["solo-pm"].plane.wip = 7; // an explicit larger plane.wip still wins
  const { scopes } = scopesFromRegistry(reg, { activation, executionMode: legacy });
  const by = Object.fromEntries(scopes.map((s) => [s.agentId, s]));
  assert.deepEqual([by["tolt-pm"].wip, by["tolt-pm"].mode], [4, "polish"], "polish defaults to 4 lanes");
  assert.deepEqual([by["tolt-director"].wip, by["tolt-director"].mode], [6, "polish"]);
  assert.deepEqual([by["lost-things-forge-pm"].wip, by["lost-things-forge-pm"].mode], [2, "develop"], "broken yaml: unchanged, never an error");
  assert.deepEqual([by["other-pm"].wip, by["other-pm"].mode], [2, "launch"], "launch lanes unchanged, mode carried");
  assert.deepEqual([by["solo-pm"].wip, by["solo-pm"].mode], [7, "polish"]);
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

test("scopes: TIKT is out of scope", () => {
  const reg = registryFixture();
  reg.agents["solo-pm"].plane.identifier = "TIKT";
  const { scopes, skipped } = scopesFromRegistry(reg, { activation, executionMode: legacy });
  assert.ok(!scopes.some((s) => s.agentId === "solo-pm"));
  assert.match(skipped.find((s) => s.agentId === "solo-pm").why, /TIKT is out of scope/);
});

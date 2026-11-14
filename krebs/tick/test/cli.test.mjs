import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { tempDir } from "./helpers.mjs";

const BIN = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "bin", "krebs.mjs");
const run = (args, env = {}) => spawnSync(process.execPath, [BIN, ...args], { encoding: "utf8", env: { ...process.env, ...env }, timeout: 30_000 });

test("cli: help exits 0, an unknown command or flag exits 2", () => {
  const help = run(["--help"]);
  assert.equal(help.status, 0);
  assert.match(help.stdout, /krebs tick \[--board KEY\] \[--dry-run\] \[--json\]/);
  assert.equal(run(["frobnicate"]).status, 2);
  assert.equal(run(["tick", "--nope"]).status, 2);
});

test("cli: a --board no registry row names is a usage error, before any Plane read", () => {
  const dir = tempDir();
  const registry = join(dir, "agents-registry.yaml");
  writeFileSync(registry, "schema_version: 1\nagents:\n  a-pm:\n    profile_name: a-pm\n    bloodbank: {enabled: true, gateway_scope: fleet, target_agent_id: a-pm}\n    plane: {workspace: w, project_id: b1, identifier: AAA}\n");
  const res = run(["tick", "--dry-run", "--json", "--board", "ZZZ", "--registry", registry], { KREBS_STATE_DIR: dir });
  assert.equal(res.status, 2);
  assert.match(JSON.parse(res.stdout).error, /no agents-registry row .* names board ZZZ/);
});

test("cli: a registry with no scopes ticks cleanly without touching Plane", () => {
  const dir = tempDir();
  const registry = join(dir, "agents-registry.yaml");
  writeFileSync(registry, "schema_version: 1\nagents:\n  off-pm:\n    profile_name: off-pm\n    bloodbank: {enabled: false, gateway_scope: fleet, target_agent_id: off-pm}\n    plane: {workspace: w, project_id: b1, identifier: OFF}\n");
  // A Plane credential that cannot resolve proves Plane was never constructed.
  const res = run(["tick", "--json", "--registry", registry, "--journal", join(dir, "j.jsonl")], { KREBS_STATE_DIR: dir, PLANE_API_KEY: "env:KREBS_TEST_UNSET_VAR" });
  assert.equal(res.status, 0, res.stderr);
  const report = JSON.parse(res.stdout);
  assert.equal(report.ok, true);
  assert.deepEqual(report.scopes, []);
  assert.match(report.skipped[0].why, /bloodbank.enabled is false/);
});

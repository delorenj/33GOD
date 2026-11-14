#!/usr/bin/env node
// krebs: the Krebs lifecycle v2 state manager (spec/lifecycle.v2.yaml).
//
//   krebs tick [--board KEY] [--dry-run] [--json] [--verbose]
//              [--registry PATH] [--journal PATH]
//
// `krebs tick` is the only Todo -> In Progress dispatcher. Candybar runs it
// (krebs/.candybars/krebs-tick.candybar.toml); nothing else schedules it.
// No runtime dependencies: Pilot's Plane client and the bloodbank n8n
// package's built dist are loaded from the sibling 33GOD checkouts.

import { parseArgs } from "node:util";
import { join } from "node:path";

import { loadBloodbank, loadPlane, realPublisher } from "../tick/deps.mjs";
import { scopesFromRegistry } from "../tick/registry.mjs";
import { runTick } from "../tick/run.mjs";
import { Journal, defaultJournalPath, stateDir } from "../tick/journal.mjs";
import { acquireLock } from "../tick/lock.mjs";
import { formatReport } from "../tick/format.mjs";
import { SPEC_VERSION } from "../tick/lifecycle.mjs";

const USAGE = `krebs: Krebs lifecycle v2 state manager (spec ${SPEC_VERSION})

Usage:
  krebs tick [--board KEY] [--dry-run] [--json] [--verbose] [--registry PATH] [--journal PATH]

tick: for every scope in ~/.hermes/agents-registry.yaml (a row with a plane
board, or board + scope_label), repair the lifecycle invariants, then dispatch
triaged Todo tickets into free slots (plane.wip, default 2): one Plane write
(In Progress + agent:working + start_date) and one
bloodbank.agent.invocation.start (reason ticket-delegation) to the scope owner.
A publish that failed on an earlier tick is republished with the same command id.

  --board KEY     only the board with this identifier (e.g. TOLT) or board id
  --dry-run       read only: print the plan; no Plane write, no publish, no journal
  --json          machine output (the full report)
  --verbose       also list registry rows that are not scopes, and why
  --registry PATH agents registry (default: HERMES_AGENTS_REGISTRY or ~/.hermes/agents-registry.yaml)
  --journal PATH  journal file (default: ~/.local/state/krebs/tick-journal.jsonl)

Exit: 0 ok (also when there is nothing to do or another tick holds the lock),
1 a scope or action failed, 2 usage error.
Environment: NATS_URL (default nats://127.0.0.1:4222), KREBS_TZ (start_date zone),
KREBS_STATE_DIR, KREBS_PILOT_DIR, KREBS_BLOODBANK_N8N_DIR, PLANE_API_KEY / PLANE_BASE (as px).`;

function emit(json, value, human) {
  process.stdout.write(`${json ? JSON.stringify(value, null, 2) : human}\n`);
}

async function tick(flags) {
  const dryRun = Boolean(flags["dry-run"]);
  // Belt and braces: Pilot's HTTP layer refuses every non-GET under PILOT_READ_ONLY.
  if (dryRun) process.env.PILOT_READ_ONLY = "1";

  const bb = loadBloodbank();
  const registryPath = flags.registry || bb.registry.hermesRegistryPath();
  const registry = await bb.registry.loadHermesRegistry(registryPath);

  // The Plane binding (and its credential) is resolved only when there is a scope to read.
  let planeBinding = null;
  const plane = async () => (planeBinding ??= await loadPlane());

  const { scopes, skipped, matchedRows } = scopesFromRegistry(registry, {
    activation: bb.registry.bloodbankActivation,
    board: flags.board,
    defaultWorkspace: "33god",
  });
  if (flags.board && matchedRows === 0) {
    return { code: 2, usage: `no agents-registry row with a plane block names board ${flags.board} (${registryPath})` };
  }

  const journalPath = flags.journal || defaultJournalPath();
  const journal = new Journal(journalPath);
  let lock = null;
  if (!dryRun) {
    lock = acquireLock(join(stateDir(), "tick.lock"));
    if (!lock) {
      const report = { ok: true, busy: true, dryRun, at: new Date().toISOString(), spec: SPEC_VERSION, scopes: [], skipped, errors: [] };
      return { code: 0, report };
    }
  }
  try {
    const report = await runTick({
      registry,
      scopes,
      skipped,
      plane: scopes.length ? (await plane()).plane : null,
      fleet: bb.fleet,
      nats: bb.nats,
      publish: dryRun
        ? async () => {
            throw new Error("dry run: publish refused");
          }
        : realPublisher(bb.nats),
      journal,
      dryRun,
      timeZone: process.env.KREBS_TZ || undefined,
    });
    report.registry = registryPath;
    report.journal = journalPath;
    return { code: report.ok ? 0 : 1, report };
  } finally {
    lock?.release();
  }
}

async function main() {
  const argv = process.argv.slice(2);
  const json = argv.includes("--json");
  const [command, ...rest] = argv;
  if (!command || command === "help" || command === "--help" || command === "-h") {
    process.stdout.write(`${USAGE}\n`);
    return 0;
  }
  if (command !== "tick") {
    process.stderr.write(`krebs: unknown command ${JSON.stringify(command)}\n\n${USAGE}\n`);
    return 2;
  }
  let flags;
  try {
    ({ values: flags } = parseArgs({
      args: rest,
      strict: true,
      allowPositionals: false,
      options: {
        board: { type: "string" },
        "dry-run": { type: "boolean" },
        json: { type: "boolean" },
        verbose: { type: "boolean" },
        registry: { type: "string" },
        journal: { type: "string" },
        help: { type: "boolean", short: "h" },
      },
    }));
  } catch (err) {
    process.stderr.write(`krebs tick: ${err.message}\n\n${USAGE}\n`);
    return 2;
  }
  if (flags.help) {
    process.stdout.write(`${USAGE}\n`);
    return 0;
  }
  try {
    const result = await tick(flags);
    if (result.usage) {
      if (json) emit(true, { ok: false, error: result.usage }, "");
      else process.stderr.write(`krebs tick: ${result.usage}\n`);
      return result.code;
    }
    emit(json, result.report, formatReport(result.report, { verbose: flags.verbose }));
    return result.code;
  } catch (err) {
    const msg = String(err?.message ?? err);
    if (json) emit(true, { ok: false, error: msg }, "");
    else process.stderr.write(`krebs tick: ${msg}\n`);
    return 1;
  }
}

process.exitCode = await main();

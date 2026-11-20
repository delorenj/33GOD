#!/usr/bin/env node
// krebs: the Krebs lifecycle v2 state manager (spec/lifecycle.v2.yaml).
//
//   krebs tick   [--board KEY] [--dry-run] [--json] [--verbose] [--trigger KIND]
//                [--registry PATH] [--journal PATH]
//   krebs status [--board KEY] [--ticket KEY] [--json] [--registry PATH] [--journal PATH]
//   krebs watch  [--consumer NAME] [--registry PATH] [--journal PATH] [--verbose]
//
// `krebs tick` is the only Todo -> In Progress dispatcher. Candybar runs it
// (krebs/.candybars/krebs-tick.candybar.toml) as the backstop; `krebs watch`
// (deploy/krebs-watch.service) runs it per board when a Plane edit or a finished
// agent turn says something changed (ADR 0002). Neither is a second clock.
// No runtime dependencies: Pilot's Plane client and the bloodbank n8n
// package's built dist are loaded from the sibling 33GOD checkouts.

import { parseArgs } from "node:util";
import { join } from "node:path";
import { readFileSync } from "node:fs";

import { fileURLToPath } from "node:url";
import { loadBloodbank, loadDurable, loadPlane, natsUrl, realPublisher } from "../tick/deps.mjs";
import { scopesFromRegistry } from "../tick/registry.mjs";
import { runTick } from "../tick/run.mjs";
import { Journal, TURN_WINDOW_MS, boardTurnSends, defaultJournalPath, lastBoardTurns, sentCommands, stateDir } from "../tick/journal.mjs";
import { activityWindows, quietWindows } from "../tick/quiet.mjs";
import { WATCH_SUBJECTS, Watcher, childTickRunner, classifyEvent, journalEcho, routesFromScopes } from "../tick/watch.mjs";
import { readWatchState, writeWatchState } from "../tick/watch-state.mjs";
import { acquireLockWait } from "../tick/lock.mjs";
import { formatReport } from "../tick/format.mjs";
import { candystoreClient, candystoreLiveness, candystoreScopeBusy } from "../tick/liveness.mjs";
import { SPEC_VERSION } from "../tick/lifecycle.mjs";
import { buildStatus, collectBusy, collectTurns, formatStatus, formatTicket, recentActivity, ticketsInPool, ticketsWorthAsking, defaultInclude } from "../tick/status.mjs";

const USAGE = `krebs: Krebs lifecycle v2 state manager (spec ${SPEC_VERSION})

Usage:
  krebs tick [--board KEY] [--dry-run] [--json] [--verbose] [--trigger KIND] [--registry PATH] [--journal PATH]
  krebs status [--board KEY] [--ticket KEY] [--json] [--registry PATH] [--journal PATH]
  krebs watch [--consumer NAME] [--registry PATH] [--journal PATH] [--verbose]

tick: for every scope in ~/.hermes/agents-registry.yaml (a row with a plane
board, or board + scope_label), repair the lifecycle invariants, then dispatch
triaged Todo tickets into free slots (plane.wip, default 2): one Plane write
(In Progress + agent:working + start_date) and one
bloodbank.agent.invocation.start (reason ticket-delegation) to the scope owner.
A publish that failed on an earlier tick is republished with the same command id.
Before the slot math, orphans: an In Progress ticket holding a slot, or any ticket
carrying agent:working, that has been quiet for 30 minutes and has no live agent turn
(Candystore: the ticket's invocation started/completed events, recent agent activity,
or a worker active in a worktree named for it) is released to Todo, or has its stale
agent:working removed. Candystore unreachable means hands off. A ticket released twice
in a week without a handback is held with agent:failed instead.
Then catch-up triage: a Todo ticket with no lifecycle:triaged, hold label, agent:working or
epic label, unchanged for 2 minutes, gets a triage start command (max 1 board turn per scope
per tick, shared with review turns; 6 per tick; oldest first; once per ticket version; no
Plane write), and only while no board turn (triage or review, any ticket) is queued or running
for that scope (Candystore; ADR 0002). Then review turns: In Progress + lifecycle:review, quiet 30 minutes.

watch: the event path. A long-running JetStream consumer (durable "krebs-watch" on BLOODBANK_EVENTS)
for Plane ticket events and the gateway's agent.invocation.completed/failed. Each event maps to a
board; a burst of Plane edits settles 60 s, a finished turn 8 s, then 'krebs tick --board <id> --trigger
<kind> --json' runs (the same code path as Candybar's tick). A ticket still inside its quiet window re-arms
the board for the moment it ends; a held tick.lock retries (bounded). Krebs's own Plane writes are
recognised in the journal and do not start a run. Writes ~/.local/state/krebs/watch.json (status reads it).
  --trigger KIND  recorded on the journal's tick line (default "schedule", Candybar); watch passes
                  plane-edit | turn-ended | quiet-window

status: read-only (no Plane write, no publish, no lock, no journal write). Runs the tick's own
dry-run plan and adds what the plan cannot say: per scope, the turns in flight right now
(Candystore), and for every Todo / In Progress ticket its stage, the reason, and an estimated
time of its next transition (quiet window, triage queue, WIP slot, review). Also the last tick,
the next tick (estimate), recent journal activity, and one line on why nothing moved.
  --board KEY     one board (e.g. PX); without it every scope, idle ones on one line
  --ticket KEY    detail for one ticket (any lane): stage, why, ETA, turn history, journal trail
  --json          the same data as a stable object (shape: tick/README.md, "Watching the pipeline")

  --board KEY     only the board with this identifier (e.g. TOLT) or board id
  --dry-run       read only: print the plan; no Plane write, no publish, no journal
  --json          machine output (the full report)
  --verbose       also list registry rows that are not scopes, and why
  --registry PATH agents registry (default: HERMES_AGENTS_REGISTRY or ~/.hermes/agents-registry.yaml)
  --journal PATH  journal file (default: ~/.local/state/krebs/tick-journal.jsonl)

Exit: 0 ok (also when there is nothing to do or another tick holds the lock),
1 a scope or action failed, 2 usage error.
Environment: NATS_URL (default nats://127.0.0.1:4222), KREBS_CANDYSTORE_URL
(default http://127.0.0.1:8683), KREBS_TZ (start_date zone),
KREBS_STATE_DIR, KREBS_PILOT_DIR, KREBS_BLOODBANK_N8N_DIR, PLANE_API_KEY / PLANE_BASE (as px).`;

/** Candystore's read API: where turn liveness comes from (local; the public hostname sits behind OIDC). */
function candystoreUrl(env = process.env) {
  return env.KREBS_CANDYSTORE_URL || "http://127.0.0.1:8683";
}

function emit(json, value, human) {
  process.stdout.write(`${json ? JSON.stringify(value, null, 2) : human}\n`);
}

/** Registry, scopes and the lazily-built Plane client shared by `tick` and `status`. */
async function openRun(flags) {
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
  const usage = flags.board && matchedRows === 0 ? `no agents-registry row with a plane block names board ${flags.board} (${registryPath})` : null;
  return { bb, registryPath, registry, plane, scopes, skipped, usage };
}

async function tick(flags) {
  const dryRun = Boolean(flags["dry-run"]);
  // Belt and braces: Pilot's HTTP layer refuses every non-GET under PILOT_READ_ONLY.
  if (dryRun) process.env.PILOT_READ_ONLY = "1";

  const trigger = flags.trigger || "schedule";
  if (!/^[a-z][a-z0-9-]{0,31}$/.test(trigger)) return { code: 2, usage: `--trigger wants a short lowercase word (schedule, plane-edit, turn-ended), got ${JSON.stringify(flags.trigger)}` };
  const { bb, registryPath, registry, plane, scopes, skipped, usage } = await openRun(flags);
  if (usage) return { code: 2, usage };

  const journalPath = flags.journal || defaultJournalPath();
  const journal = new Journal(journalPath);
  let lock = null;
  if (!dryRun) {
    // Wait (bounded) for a run already holding it: a board run by `krebs watch` takes about a second, and a
    // Candybar tick that gave up at once would leave every other board to the next 10-minute mark.
    lock = await acquireLockWait(join(stateDir(), "tick.lock"));
    if (!lock) {
      const report = { ok: true, busy: true, dryRun, at: new Date().toISOString(), spec: SPEC_VERSION, trigger, scopes: [], skipped, errors: [] };
      return { code: 0, report };
    }
  }
  let quiet = [];
  try {
    const client = candystoreClient({ base: candystoreUrl() });
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
      liveness: candystoreLiveness({ client, fleet: bb.fleet }),
      scopeBusy: candystoreScopeBusy({ client }),
      trigger,
      triggerDetail: flags["trigger-detail"] || null,
      boardFilter: flags.board || null,
      // Tickets that only wait for their quiet window: `krebs watch` re-arms the board for the earliest.
      inspect: (found) => {
        const nowMs = Date.now();
        quiet = found.flatMap((i) => quietWindows(i.tickets, nowMs).map((q) => ({ board: i.scope.identifier ?? i.scope.boardId, boardId: i.scope.boardId, ...q })));
      },
    });
    report.registry = registryPath;
    report.journal = journalPath;
    // ... and those skipped only for recent agent activity, whose 30-minute window ends with no event either.
    report.quiet = [...quiet, ...activityWindows(report.scopes, Date.now())].sort((a, b) => a.eligibleAt - b.eligibleAt);
    return { code: report.ok ? 0 : 1, report };
  } finally {
    lock?.release();
  }
}

/** `krebs status`: read-only. Never takes the lock, publishes, writes Plane or appends to the journal. */
async function status(flags) {
  process.env.PILOT_READ_ONLY = "1";
  // `--ticket PX-23` narrows the scope to that key's board when no --board was given.
  const focusKey = flags.ticket ? String(flags.ticket).toUpperCase() : null;
  const keyBoard = focusKey && !flags.board ? (focusKey.match(/^(.*)-\d+$/) ?? [])[1] : null;
  if (focusKey && !/^.+-\d+$/.test(focusKey)) return { code: 2, usage: `--ticket wants a key like PX-23, got ${flags.ticket}` };
  const { bb, registryPath, registry, plane, scopes, skipped, usage } = await openRun({ ...flags, board: flags.board || keyBoard || undefined });
  if (usage) return { code: 2, usage };

  const journalPath = flags.journal || defaultJournalPath();
  const journal = new Journal(journalPath);
  const journalEntries = journal.read();
  const client = candystoreClient({ base: candystoreUrl() });
  const nowMs = Date.now();
  let inspected = [];
  await runTick({
    registry,
    scopes,
    skipped,
    plane: scopes.length ? (await plane()).plane : null,
    fleet: bb.fleet,
    nats: bb.nats,
    publish: async () => {
      throw new Error("status is read-only: publish refused");
    },
    journal,
    dryRun: true,
    now: () => new Date(nowMs),
    timeZone: process.env.KREBS_TZ || undefined,
    liveness: candystoreLiveness({ client, fleet: bb.fleet, now: () => new Date(nowMs) }),
    scopeBusy: candystoreScopeBusy({ client, now: () => new Date(nowMs) }),
    inspect: (found) => {
      inspected = found;
    },
  });
  if (focusKey) inspected = inspected.filter((i) => i.tickets.some((t) => t.key === focusKey));
  if (focusKey && !inspected.length) return { code: 2, usage: `no ticket ${focusKey} on any scope's board (${registryPath})` };

  // Live turns, from Candystore: one question per ticket that could have a turn on it.
  const sentByTicket = sentCommands(journalEntries);
  const turnsByScope = new Map();
  let candystore = { ok: true, error: null, url: candystoreUrl() };
  for (const i of inspected) {
    const asking = ticketsWorthAsking(i.tickets, sentByTicket, nowMs, focusKey);
    const res = await collectTurns({ client, fleet: bb.fleet, boardId: i.scope.boardId, tickets: asking, sentByTicket, nowMs });
    turnsByScope.set(`${i.scope.boardId}|${i.scope.agentId}`, res);
    if (!res.ok) {
      candystore = { ok: false, error: res.error, url: candystoreUrl() };
      break; // Candystore is down: asking for the other scopes would only wait out the timeouts
    }
  }
  if (!candystore.ok) for (const i of inspected) if (!turnsByScope.get(`${i.scope.boardId}|${i.scope.agentId}`)?.ok) turnsByScope.set(`${i.scope.boardId}|${i.scope.agentId}`, { ok: false, error: candystore.error, byTicket: new Map() });

  // Tickets the tick would skip as "turn live" (recent agent activity): when does that window end?
  const liveness = candystoreLiveness({ client, fleet: bb.fleet, now: () => new Date(nowMs) });
  const busyByScope = new Map();
  if (candystore.ok) {
    for (const i of inspected) {
      const key = `${i.scope.boardId}|${i.scope.agentId}`;
      const pool = ticketsInPool(i.tickets, i.out, turnsByScope.get(key)?.byTicket, nowMs);
      busyByScope.set(key, await collectBusy({ liveness, boardId: i.scope.boardId, tickets: pool, sentByTicket, nowMs }));
    }
  }

  const reviewsSent = boardTurnSends(journalEntries, nowMs - TURN_WINDOW_MS).review;
  const result = buildStatus({
    busyByScope,
    watch: readWatchState({ nowMs }),
    inspected,
    journalEntries,
    nowMs,
    turnsByScope,
    candystore,
    lastBoardTurn: lastBoardTurns(journalEntries),
    reviewsSent,
    include: focusKey ? (row) => row.key === focusKey : defaultInclude,
    registryPath,
    journalPath,
  });
  if (flags.board || focusKey) result.scopes = result.scopes.filter((s) => (focusKey ? s.tickets.length : true));

  let detail = null;
  if (focusKey) {
    const scopeStatus = result.scopes[0];
    const row = scopeStatus.tickets[0];
    const src = inspected.find((i) => i.scope.agentId === scopeStatus.agentId && i.scope.boardId === scopeStatus.boardId);
    const ticket = src.tickets.find((t) => t.key === focusKey);
    const turns = turnsByScope.get(`${src.scope.boardId}|${src.scope.agentId}`);
    const hist = turns?.ok ? turns.byTicket.get(ticket.id)?.history ?? [] : null;
    const trail = recentActivity(journalEntries, { agentId: src.scope.agentId, nowMs, key: focusKey });
    detail = { row, scope: scopeStatus, trail, turns: hist };
    result.ticket = { ...row, scope: { board: scopeStatus.board, agentId: scopeStatus.agentId }, journal: trail, turns: hist === null ? null : hist.map((x) => ({ invocationId: x.id, reason: x.reason, queuedAt: x.queuedAt && new Date(x.queuedAt).toISOString(), startedAt: x.startedAt && new Date(x.startedAt).toISOString(), endedAt: x.endedAt && new Date(x.endedAt).toISOString(), outcome: x.endType, detachedAt: x.detachedAt && new Date(x.detachedAt).toISOString() })) };
  }
  return { code: 0, status: result, detail, compact: !flags.board && !focusKey };
}

const logLine = (line) => process.stdout.write(`${new Date().toISOString()} ${line}\n`);

/**
 * `krebs watch`: the event path (ADR 0002). Never returns while healthy; a fatal NATS error exits 1 and
 * systemd restarts it. The durable consumer keeps its position on the server, so what arrives while this
 * process is down is replayed on start (events older than ten minutes are skipped: the backstop tick has
 * long since seen them).
 */
async function watch(flags) {
  const bb = loadBloodbank();
  const durable = loadDurable();
  const registryPath = flags.registry || bb.registry.hermesRegistryPath();
  const journalPath = flags.journal || defaultJournalPath();
  const consumerName = flags.consumer || "krebs-watch";
  const verbose = Boolean(flags.verbose);

  let routes = null;
  let routesAt = 0;
  const refreshRoutes = async () => {
    try {
      const registry = await bb.registry.loadHermesRegistry(registryPath);
      const { scopes } = scopesFromRegistry(registry, { activation: bb.registry.bloodbankActivation, defaultWorkspace: "33god" });
      routes = routesFromScopes(scopes);
      routesAt = Date.now();
    } catch (err) {
      if (!routes) throw err;
      logLine(`registry reload failed (${String(err?.message ?? err).split("\n")[0]}); keeping the last routes`);
      routesAt = Date.now();
    }
  };
  await refreshRoutes();

  const startedAt = new Date().toISOString();
  const script = fileURLToPath(import.meta.url);
  const watcher = new Watcher({ run: childTickRunner({ script }), log: logLine });
  const echo = journalEcho(journalPath);
  const state = () => ({ pid: process.pid, startedAt, consumer: consumerName, registry: registryPath, boardsWatched: routes?.byBoard.size ?? 0, ...watcher.snapshot() });
  const heartbeat = () => {
    try {
      writeWatchState(state());
    } catch (err) {
      logLine(`cannot write watch state: ${String(err?.message ?? err)}`);
    }
  };
  heartbeat();
  const beat = setInterval(heartbeat, 30_000);

  const sub = await durable.consumeDurable(
    await durable.jetstreamBackend({
      host: natsUrl(),
      stream: "BLOODBANK_EVENTS",
      name: consumerName,
      subjects: WATCH_SUBJECTS,
      description: "krebs watch: Plane ticket edits and finished agent turns start a board-scoped krebs tick (ADR 0002)",
      connectionName: "krebs-watch",
      maxAckPending: 64,
      onEnsured: (r) => logLine(`consumer ${consumerName}: ${r.action}${r.drift?.length ? ` (${r.drift.join(", ")})` : ""}`),
    }),
    {
      catchUpWindowMs: 10 * 60 * 1000,
      onMessage: async (msg) => {
        let envelope;
        try {
          envelope = JSON.parse(Buffer.from(msg.data).toString("utf8"));
        } catch {
          return "term";
        }
        if (Date.now() - routesAt > 60_000) await refreshRoutes();
        const c = watcher.onClassified(classifyEvent({ subject: msg.subject, envelope }, routes, { echo }));
        if (c.ignored) {
          if (verbose) logLine(`ignored ${msg.subject.split(".").slice(2).join(".")}: ${c.ignored}`);
        } else {
          logLine(`event ${c.kind}: ${c.detail} -> board ${c.boards.map((b) => routes.byBoard.get(b)?.identifier ?? b).join(", ")}`);
        }
        return "ack";
      },
      onStale: (m, ageMs) => logLine(`skipped a stale ${m.subject.split(".").slice(2).join(".")} (${Math.round(ageMs / 1000)}s old)`),
      onWarning: (m, e) => logLine(`warning: ${m}${e ? `: ${String(e.message ?? e).split("\n")[0]}` : ""}`),
      onFatal: (e) => {
        logLine(`fatal: ${String(e?.message ?? e)}`);
        process.exit(1);
      },
    },
  );
  logLine(`watching ${routes.byBoard.size} boards on ${WATCH_SUBJECTS.length} subjects (registry ${registryPath})`);
  const stop = async (signal) => {
    logLine(`${signal}: closing`);
    clearInterval(beat);
    try {
      await sub.close();
    } catch {
      // closing
    }
    process.exit(0);
  };
  process.once("SIGTERM", () => void stop("SIGTERM"));
  process.once("SIGINT", () => void stop("SIGINT"));
  await sub.done;
  return 1;
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.includes("--usage-spec") && !argv.slice(0, argv.indexOf("--usage-spec")).includes("--")) {
    process.stdout.write(readFileSync(new URL("../krebs.usage.kdl", import.meta.url), "utf8"));
    return 0;
  }
  const json = argv.includes("--json");
  const [command, ...rest] = argv;
  if (!command || command === "help" || command === "--help" || command === "-h") {
    process.stdout.write(`${USAGE}\n`);
    return 0;
  }
  if (command !== "tick" && command !== "status" && command !== "watch") {
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
        ticket: { type: "string" },
        trigger: { type: "string" },
        "trigger-detail": { type: "string" },
        consumer: { type: "string" },
        registry: { type: "string" },
        journal: { type: "string" },
        help: { type: "boolean", short: "h" },
      },
    }));
  } catch (err) {
    process.stderr.write(`krebs ${command}: ${err.message}\n\n${USAGE}\n`);
    return 2;
  }
  if (command === "status" && (flags["dry-run"] || flags.verbose)) {
    process.stderr.write(`krebs status: --dry-run and --verbose are tick flags (status is always read-only)\n\n${USAGE}\n`);
    return 2;
  }
  if (command !== "tick" && (flags.trigger || flags["trigger-detail"])) {
    process.stderr.write(`krebs ${command}: --trigger belongs to tick\n\n${USAGE}\n`);
    return 2;
  }
  if (command === "watch" && (flags.board || flags["dry-run"] || flags.ticket || flags.json)) {
    process.stderr.write(`krebs watch: takes --consumer, --registry, --journal and --verbose only\n\n${USAGE}\n`);
    return 2;
  }
  if (command === "tick" && flags.ticket) {
    process.stderr.write(`krebs tick: --ticket belongs to status\n\n${USAGE}\n`);
    return 2;
  }
  if (flags.help) {
    process.stdout.write(`${USAGE}\n`);
    return 0;
  }
  if (command === "watch") {
    try {
      return await watch(flags);
    } catch (err) {
      process.stderr.write(`krebs watch: ${String(err?.message ?? err)}\n`);
      return 1;
    }
  }
  try {
    const result = command === "status" ? await status(flags) : await tick(flags);
    if (result.usage) {
      if (json) emit(true, { ok: false, error: result.usage }, "");
      else process.stderr.write(`krebs ${command}: ${result.usage}\n`);
      return result.code;
    }
    if (command === "status") emit(json, result.status, result.detail ? formatTicket(result.status, result.detail) : formatStatus(result.status, { compact: result.compact }));
    else emit(json, result.report, formatReport(result.report, { verbose: flags.verbose }));
    return result.code;
  } catch (err) {
    const msg = String(err?.message ?? err);
    if (json) emit(true, { ok: false, error: msg }, "");
    else process.stderr.write(`krebs ${command}: ${msg}\n`);
    return 1;
  }
}

process.exitCode = await main();

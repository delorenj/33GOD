// `krebs watch`: the event path (ADR 0002). Plane edits and finished agent turns start a board-scoped
// `krebs tick`, so the lifecycle reacts in minutes instead of waiting for Candybar's 10-minute tick.
//
// This module is the pure half: event -> board mapping, the per-board debounce and the run queue (the
// clock and the runner are injected, so the tests drive it with fakes), and the child-process runner.
// bin/krebs.mjs wires it to the JetStream consumer. It owns no schedule: every run is caused by an event
// or by a time already read off a board (a ticket's quiet window ending); the Candybar tick stays the
// backstop for anything this process misses, and the one thing a restart loses is at most a settle window.
//
// Shape of one run: events touch a board -> after the settle window the board's tick runs (`krebs tick
// --board <id> --json --trigger <kind>`, the same code path Candybar runs) -> the report says whether the
// lock was held (retry, bounded), which tickets only wait for their quiet window (re-arm for the earliest),
// and which turns kept a scope busy (retry once if we already saw them end: Candystore lags the bus).

import { execFile } from "node:child_process";
import { closeSync, existsSync, openSync, readSync, statSync } from "node:fs";

export const PLANE_TASK_SUBJECT = "bloodbank.evt.repo.task.";
/** Comments (`appended`) change nothing the tick reads, and agents write many of them. */
const PLANE_TASK_TYPES = new Set(["created", "updated", "transitioned", "deleted"]);
export const TURN_ENDED_SUBJECTS = ["bloodbank.evt.agent.invocation.completed", "bloodbank.evt.agent.invocation.failed"];
/** The JetStream filter of the durable consumer: exactly what classifyEvent can use. */
export const WATCH_SUBJECTS = [
  "bloodbank.evt.repo.task.created",
  "bloodbank.evt.repo.task.updated",
  "bloodbank.evt.repo.task.transitioned",
  "bloodbank.evt.repo.task.deleted",
  ...TURN_ENDED_SUBJECTS,
];
export const GATEWAY_SERVICE = "bloodbank-hermes-gateway";

export const WATCH_DEFAULTS = Object.freeze({
  /** A Plane edit settles this long (after the last edit of the burst) before the board runs. */
  planeSettleMs: 60_000,
  /** ... but a burst never delays the run past this long after its first edit. */
  planeMaxWaitMs: 180_000,
  /** After an agent turn ends: long enough for the pickup chip's clearing edit and Candystore's ingest. */
  turnSettleMs: 8_000,
  turnMaxWaitMs: 24_000,
  /** Two runs of one board are at least this far apart. */
  minGapMs: 10_000,
  /** At most this many runs per board per window: a runaway guard, never reached by honest traffic. */
  runCap: 20,
  runWindowMs: 10 * 60 * 1000,
  /** A held tick.lock re-arms the board after these delays (then the backstop tick covers it). */
  lockRetryMs: Object.freeze([5_000, 10_000, 20_000, 40_000, 60_000]),
  /** A scope kept busy by a turn we already saw end (Candystore lag): look again this soon, this many times. */
  busyLagRetryMs: 10_000,
  busyLagMaxRetries: 3,
  /** How long an ended turn's id is remembered for that check. */
  endedMemoryMs: 3 * 60 * 1000,
  /** A Krebs write echoes through Plane's webhook within a second or two; this is the match window either side. */
  echoWindowMs: 20_000,
  /** A quiet-window re-arm further out than this is left to the backstop. */
  rearmMaxMs: 60 * 60 * 1000,
  routesTtlMs: 60_000,
  runTimeoutMs: 5 * 60 * 1000,
});

// ---------------------------------------------------------------------------------------------
// Routes: which boards exist, and which boards an agent's turn end concerns
// ---------------------------------------------------------------------------------------------

/**
 * From scopesFromRegistry's scopes: boardId -> {identifier, agents}, agentId -> [boardId]. Only boards some
 * scope owns appear: an event on any other board (a client board, TIKT, an unenrolled project) is not ours.
 */
export function routesFromScopes(scopes) {
  const byBoard = new Map();
  const byAgent = new Map();
  for (const s of scopes) {
    const b = byBoard.get(s.boardId) ?? { boardId: s.boardId, identifier: s.identifier ?? null, agents: new Set() };
    b.agents.add(s.agentId);
    b.identifier ??= s.identifier ?? null;
    byBoard.set(s.boardId, b);
    const boards = byAgent.get(s.agentId) ?? new Set();
    boards.add(s.boardId);
    byAgent.set(s.agentId, boards);
  }
  return { byBoard, byAgent: new Map([...byAgent].map(([a, set]) => [a, [...set]])) };
}

const asObject = (v) => (v && typeof v === "object" && !Array.isArray(v) ? v : {});

/**
 * One bus event -> what it means for the watcher.
 *   {kind: "plane-edit"|"turn-ended", boards: [boardId], detail, ticketKey?, invocationId?}
 *   {ignored: reason}
 * `echo(ticketKey, eventMs)` says whether a Krebs write caused this Plane event (see journalEcho).
 */
export function classifyEvent({ subject, envelope }, routes, { echo = () => false } = {}) {
  const e = asObject(envelope);
  const data = asObject(e.data);
  const subj = String(subject ?? e.subject ?? "");

  if (subj.startsWith(PLANE_TASK_SUBJECT)) {
    const type = subj.slice(PLANE_TASK_SUBJECT.length);
    if (!PLANE_TASK_TYPES.has(type)) return { ignored: `plane ${type} (comments and other facts change nothing the tick reads)` };
    const boardId = String(e.board_id || data.board_id || data.project_id || "");
    if (!boardId) return { ignored: "plane event names no board" };
    if (!routes.byBoard.has(boardId)) return { ignored: `board ${boardId} has no krebs scope` };
    const ticketKey = data.ticket_key ? String(data.ticket_key) : null;
    const eventMs = Date.parse(e.time ?? "");
    if (ticketKey && Number.isFinite(eventMs) && echo(ticketKey, eventMs)) return { ignored: `${ticketKey}: echo of a krebs write` };
    return { kind: "plane-edit", boards: [boardId], ticketKey, detail: `${ticketKey ?? "?"} ${data.provider_event_type ?? subj}` };
  }

  if (TURN_ENDED_SUBJECTS.includes(subj)) {
    // Only the gateway's own lifecycle facts name a command and its target; hook-hub and claude-code
    // session events carry the same type on the same subject and say nothing about a desk's turn.
    const agentId = data.target_agent_id ? String(data.target_agent_id) : null;
    if (!agentId || !data.command_id || (e.service && e.service !== GATEWAY_SERVICE)) return { ignored: "not a gateway turn end" };
    const boards = routes.byAgent.get(agentId);
    if (!boards?.length) return { ignored: `${agentId} owns no krebs scope` };
    const context = asObject(data.context);
    const named = context.board_id ? boards.filter((b) => b === String(context.board_id)) : [];
    const end = subj.endsWith(".failed") ? "failed" : "completed";
    return {
      kind: "turn-ended",
      boards: named.length ? named : boards,
      ticketKey: context.ticket_key ? String(context.ticket_key) : null,
      invocationId: String(data.invocation_id || data.command_id),
      detail: `${agentId} turn ${end}${context.reason ? ` (${context.reason})` : ""}${context.ticket_key ? ` ${context.ticket_key}` : ""}`,
    };
  }
  return { ignored: `subject ${subj} is not watched` };
}

// ---------------------------------------------------------------------------------------------
// Echo: a Plane event that Krebs's own write caused
// ---------------------------------------------------------------------------------------------

/** Journal actions that are one Plane write by krebs (ok true), keyed by the ticket's `key`. */
export const WRITE_ACTIONS = new Set(["dispatch.write", "repair", "orphan.unstick", "orphan.release", "orphan.fail"]);

/**
 * Does the journal hold a successful Krebs write on `ticketKey` within `windowMs` of `eventMs`? That Plane
 * event is the echo of the run that wrote it, which already saw the state it left behind (and re-armed for
 * any quiet window), so it does not start another run. Reads only the journal's tail.
 */
export function journalEcho(journalPath, { windowMs = WATCH_DEFAULTS.echoWindowMs, tailBytes = 256 * 1024 } = {}) {
  return (ticketKey, eventMs) => {
    for (const entry of tailEntries(journalPath, tailBytes)) {
      if (!WRITE_ACTIONS.has(entry.action) || entry.ok !== true || entry.key !== ticketKey) continue;
      const t = Date.parse(entry.ts ?? "");
      if (Number.isFinite(t) && Math.abs(t - eventMs) <= windowMs) return true;
    }
    return false;
  };
}

/** Parseable journal lines from the last `bytes` of the file (a partial first line is dropped). */
export function tailEntries(path, bytes) {
  if (!existsSync(path)) return [];
  const size = statSync(path).size;
  const start = Math.max(0, size - bytes);
  const fd = openSync(path, "r");
  let text;
  try {
    const buf = Buffer.alloc(size - start);
    readSync(fd, buf, 0, buf.length, start);
    text = buf.toString("utf8");
  } finally {
    closeSync(fd);
  }
  const lines = text.split("\n");
  if (start > 0) lines.shift();
  const out = [];
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const entry = JSON.parse(line);
      if (entry && typeof entry === "object") out.push(entry);
    } catch {
      // a torn line
    }
  }
  return out;
}

// ---------------------------------------------------------------------------------------------
// The watcher: per-board debounce, one run at a time
// ---------------------------------------------------------------------------------------------

/** Which trigger a run is recorded under when several are pending: the more urgent signal first. */
const KIND_RANK = { "turn-ended": 0, "plane-edit": 1, "quiet-window": 2 };
const rankOf = (kind) => KIND_RANK[kind] ?? 3;

/**
 * The debounce and run queue. Injected:
 *   now()                       ms clock
 *   setTimer(ms, fn) -> handle  clearTimer(handle)
 *   run(boardId, {trigger, detail}) -> Promise<outcome>   outcome: {busy?, quiet?: [{key, kind, eligibleAt}],
 *                                busyTurns?: [invocationId], error?}
 *   log(line)                   one human line per decision
 *
 * Per board, each trigger kind keeps its own pending entry {due, first, origin, detail}. A run takes every
 * pending entry (it evaluates the whole board, so one run answers all of them); anything arriving while it
 * runs is pending again and runs after it. Runs are serialized (they share tick.lock anyway).
 */
export class Watcher {
  constructor({ now = Date.now, setTimer = (ms, fn) => setTimeout(fn, ms), clearTimer = clearTimeout, run, log = () => {}, config = {} } = {}) {
    if (typeof run !== "function") throw new Error("Watcher needs a run function");
    this.now = now;
    this.setTimer = setTimer;
    this.clearTimer = clearTimer;
    this.runFn = run;
    this.log = log;
    this.cfg = { ...WATCH_DEFAULTS, ...config };
    this.boards = new Map();
    this.ready = [];
    this.active = false;
    this.ended = new Map(); // invocation id -> ms seen
    this.stats = { events: 0, ignored: 0, runs: 0, failures: 0, lastEventAt: null, lastRun: null };
  }

  board(id) {
    let b = this.boards.get(id);
    if (!b) {
      b = { id, pending: new Map(), timer: null, running: false, queued: false, lastEnd: 0, runs: [], lockRetries: 0, busyRetries: 0, capLogged: false };
      this.boards.set(id, b);
    }
    return b;
  }

  /** A debounced signal: the board runs `delayMs` after the last one of this kind, never later than `maxWaitMs` after the first. */
  signal(boardId, kind, { detail = "", delayMs, maxWaitMs = delayMs * 3, origin = kind } = {}) {
    const now = this.now();
    const b = this.board(boardId);
    const cur = b.pending.get(kind);
    const first = cur?.first ?? now;
    const due = Math.min(now + delayMs, first + maxWaitMs);
    b.pending.set(kind, { due, first, origin: cur?.origin ?? origin, details: [...new Set([...(cur?.details ?? []), detail].filter(Boolean))].slice(-3) });
    this.schedule(b);
  }

  /** An exact time: run the board at `atMs` (a quiet window ending, a retry). */
  armAt(boardId, kind, atMs, { detail = "", origin = kind } = {}) {
    const b = this.board(boardId);
    const cur = b.pending.get(kind);
    if (cur && cur.due <= atMs) return;
    b.pending.set(kind, { due: atMs, first: cur?.first ?? this.now(), origin, details: detail ? [detail] : [] });
    this.schedule(b);
  }

  /** One watched Plane or turn event. Returns the classification for logging. */
  onClassified(c) {
    this.stats.events++;
    this.stats.lastEventAt = new Date(this.now()).toISOString();
    if (c.ignored) {
      this.stats.ignored++;
      return c;
    }
    if (c.kind === "turn-ended") this.markEnded(c.invocationId);
    for (const boardId of c.boards) {
      if (c.kind === "plane-edit") this.signal(boardId, "plane-edit", { detail: c.detail, delayMs: this.cfg.planeSettleMs, maxWaitMs: this.cfg.planeMaxWaitMs });
      else this.signal(boardId, "turn-ended", { detail: c.detail, delayMs: this.cfg.turnSettleMs, maxWaitMs: this.cfg.turnMaxWaitMs });
    }
    return c;
  }

  markEnded(id) {
    if (!id) return;
    const now = this.now();
    this.ended.set(id, now);
    for (const [k, t] of this.ended) if (now - t > this.cfg.endedMemoryMs) this.ended.delete(k);
  }

  /** (Re)set the board's timer to its earliest pending due, honouring the gap and the run cap. */
  schedule(b) {
    if (b.running || b.queued || !b.pending.size) return;
    const now = this.now();
    let due = Math.min(...[...b.pending.values()].map((p) => p.due));
    due = Math.max(due, b.lastEnd + this.cfg.minGapMs);
    b.runs = b.runs.filter((t) => now - t < this.cfg.runWindowMs);
    if (b.runs.length >= this.cfg.runCap) {
      due = Math.max(due, b.runs[0] + this.cfg.runWindowMs);
      if (!b.capLogged) {
        b.capLogged = true;
        this.log(`board ${b.id}: ${b.runs.length} runs in ${Math.round(this.cfg.runWindowMs / 60000)} min; holding further runs until the window clears (runaway guard)`);
      }
    } else b.capLogged = false;
    if (b.timer) this.clearTimer(b.timer);
    b.timer = this.setTimer(Math.max(0, due - now), () => {
      b.timer = null;
      b.queued = true;
      this.ready.push(b);
      void this.pump();
    });
  }

  async pump() {
    if (this.active) return;
    this.active = true;
    try {
      while (this.ready.length) {
        const b = this.ready.shift();
        await this.execute(b);
      }
    } finally {
      this.active = false;
    }
  }

  async execute(b) {
    const taken = [...b.pending.entries()].sort((x, y) => x[1].due - y[1].due || rankOf(x[0]) - rankOf(y[0]));
    b.pending = new Map();
    b.queued = false;
    b.running = true;
    if (!taken.length) {
      b.running = false;
      return;
    }
    // the trigger is the most urgent kind among those that were due (all of them, when one run answers the lot)
    const lead = [...taken].sort((x, y) => rankOf(x[1].origin) - rankOf(y[1].origin) || x[1].due - y[1].due)[0][1];
    const trigger = lead.origin;
    const detail = [...new Set(taken.flatMap(([, p]) => p.details))].slice(0, 3).join("; ");
    let outcome;
    try {
      outcome = await this.runFn(b.id, { trigger, detail });
    } catch (err) {
      outcome = { error: String(err?.message ?? err).split("\n")[0] };
    }
    const end = this.now();
    b.runs.push(end);
    b.lastEnd = end;
    b.running = false;
    this.stats.runs++;
    this.stats.lastRun = { board: b.id, trigger, at: new Date(end).toISOString(), ok: !outcome.error && outcome.ok !== false };
    if (outcome.error) this.stats.failures++;
    this.afterRun(b, trigger, outcome);
    this.schedule(b);
  }

  afterRun(b, trigger, outcome) {
    const now = this.now();
    if (outcome.error) {
      this.log(`board ${b.id}: run failed (${outcome.error}); the next event or the backstop tick retries`);
      return;
    }
    // tick.lock held: the board's turn comes again once it frees (bounded; the backstop covers the rest).
    if (outcome.busy) {
      b.lockRetries++;
      const wait = this.cfg.lockRetryMs[b.lockRetries - 1];
      if (wait === undefined) {
        this.log(`board ${b.id}: tick.lock still held after ${this.cfg.lockRetryMs.length} retries; leaving it to the backstop tick`);
        b.lockRetries = 0;
      } else {
        this.log(`board ${b.id}: tick.lock held; trying again in ${Math.round(wait / 1000)}s (${b.lockRetries}/${this.cfg.lockRetryMs.length})`);
        this.armAt(b.id, "lock-retry", now + wait, { origin: trigger, detail: "lock was held" });
      }
      return;
    }
    b.lockRetries = 0;
    // A scope kept busy by a turn this watcher already saw end: Candystore had not ingested the end yet.
    const lagging = (outcome.busyTurns ?? []).filter((id) => this.ended.has(id));
    if (lagging.length && b.busyRetries < this.cfg.busyLagMaxRetries) {
      b.busyRetries++;
      this.log(`board ${b.id}: scope busy on a turn that already ended (Candystore lag); looking again in ${Math.round(this.cfg.busyLagRetryMs / 1000)}s`);
      this.armAt(b.id, "busy-lag", now + this.cfg.busyLagRetryMs, { origin: "turn-ended", detail: "Candystore lag" });
    } else if (!lagging.length) b.busyRetries = 0;
    // Tickets waiting only for time: nothing else will wake the board when their window ends.
    const next = (outcome.quiet ?? []).filter((q) => Number.isFinite(q.eligibleAt) && q.eligibleAt - now <= this.cfg.rearmMaxMs).sort((x, y) => x.eligibleAt - y.eligibleAt)[0];
    if (next) {
      this.log(`board ${b.id}: ${next.key} is eligible for ${next.kind} in ${Math.max(0, Math.round((next.eligibleAt - now) / 1000))}s; armed`);
      this.armAt(b.id, "quiet-window", next.eligibleAt, { origin: "quiet-window", detail: `${next.key} quiet window ends` });
    }
  }

  /** What `krebs status` shows: pending timers per board. */
  snapshot() {
    const out = [];
    for (const b of this.boards.values()) {
      if (b.pending.size || b.running) out.push({ board: b.id, running: b.running, pending: [...b.pending].map(([kind, p]) => ({ kind, due: new Date(p.due).toISOString() })) });
    }
    return { ...this.stats, boards: out };
  }
}

// ---------------------------------------------------------------------------------------------
// The runner: `krebs tick --board ID --json` in a child process, exactly the code path Candybar runs
// ---------------------------------------------------------------------------------------------

/** A tick report -> the outcome the watcher acts on. */
export function outcomeOfReport(code, report) {
  if (!report || typeof report !== "object") return { error: `tick exited ${code} without a JSON report` };
  if (report.ok === false && report.error) return { error: String(report.error) };
  if (report.busy) return { busy: true };
  const scopes = Array.isArray(report.scopes) ? report.scopes : [];
  const sum = (pick) => scopes.reduce((n, s) => n + pick(s), 0);
  return {
    ok: report.ok !== false,
    code,
    quiet: Array.isArray(report.quiet) ? report.quiet : [],
    busyTurns: scopes.flatMap((s) => (s.boardTurnBusy?.turns ?? []).map((t) => t.invocationId)),
    summary: {
      dispatched: sum((s) => (s.dispatches ?? []).filter((d) => d.result === "dispatched").length),
      triaged: sum((s) => (s.triage ?? []).filter((d) => d.result === "published").length),
      reviews: sum((s) => (s.reviews ?? []).filter((d) => d.result === "published").length),
      repaired: sum((s) => (s.repairs ?? []).filter((d) => d.result === "repaired").length),
      busy: scopes.filter((s) => s.boardTurnBusy).length,
      errors: sum((s) => (s.errors ?? []).length),
    },
  };
}

/** Run one board's tick as a child process. Resolves to an outcome; never rejects. */
export function childTickRunner({ node = process.execPath, script, env = process.env, timeoutMs = WATCH_DEFAULTS.runTimeoutMs, exec = execFile } = {}) {
  return (boardId, { trigger, detail }) =>
    new Promise((resolve) => {
      const args = [script, "tick", "--board", boardId, "--json", "--trigger", trigger];
      if (detail) args.push("--trigger-detail", detail);
      exec(node, args, { env, timeout: timeoutMs, maxBuffer: 32 * 1024 * 1024 }, (err, stdout) => {
        let report = null;
        try {
          report = JSON.parse(stdout);
        } catch {
          // no report
        }
        const code = err ? (typeof err.code === "number" ? err.code : 1) : 0;
        if (!report && err) return resolve({ error: String(err.killed ? `tick timed out after ${Math.round(timeoutMs / 1000)}s` : err.message).split("\n")[0] });
        resolve(outcomeOfReport(code, report));
      });
    });
}

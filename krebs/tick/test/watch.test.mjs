import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { appendFileSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { bloodbankN8nDir } from "../deps.mjs";
import { TRIAGE_MIN_AGE_MS, REVIEW_MIN_AGE_MS } from "../select.mjs";
import { quietWindows } from "../quiet.mjs";
import { normalizeTicket } from "../select.mjs";
import { laneModel } from "../lifecycle.mjs";
import { WATCH_DEFAULTS, WATCH_SUBJECTS, Watcher, childTickRunner, classifyEvent, journalEcho, outcomeOfReport, routesFromScopes } from "../watch.mjs";
import { WATCH_STALE_MS, readWatchState, writeWatchState } from "../watch-state.mjs";
import { STATES, LABEL_NAMES, issue, labelId, tempDir } from "./helpers.mjs";

// ---------------------------------------------------------------------------------------------
// event -> board
// ---------------------------------------------------------------------------------------------

const PX = "35730097-d556-4160-ac93-c95c9ead10a0";
const G33 = "15258893-0206-4e8f-aea6-340eb217988c";
const scopes = [
  { agentId: "pilot-pm", boardId: PX, identifier: "PX" },
  { agentId: "33god-pm", boardId: G33, identifier: "33GOD" },
  { agentId: "tolt-pm", boardId: "b-tolt", identifier: "TOLT" },
  { agentId: "forge-pm", boardId: "b-tolt", identifier: "TOLT" },
];
const routes = routesFromScopes(scopes);

const plane = (subject, { board = PX, key = "PX-28", time = "2026-11-20T12:00:00.000Z", type = "plane.ticket.updated" } = {}) => ({
  subject,
  envelope: { subject, time, board_id: board, service: "n8n", data: { board_id: board, ticket_key: key, provider_event_type: type } },
});
const turn = (end, { agent = "pilot-pm", service = "bloodbank-hermes-gateway", board = PX, command = "cmd-1", reason = "ticket-grooming", key = "PX-28" } = {}) => ({
  subject: `bloodbank.evt.agent.invocation.${end}`,
  envelope: { service, data: { invocation_id: command, command_id: command, target_agent_id: agent, context: { reason, board_id: board, ticket_key: key } } },
});

test("routes: boardId -> identifier, agent -> boards; a shared board has one entry", () => {
  assert.equal(routes.byBoard.size, 3);
  assert.deepEqual([...routes.byBoard.get("b-tolt").agents].sort(), ["forge-pm", "tolt-pm"]);
  assert.deepEqual(routes.byAgent.get("pilot-pm"), [PX]);
});

test("a Plane ticket event maps to its board; created, updated, transitioned and deleted all count", () => {
  for (const t of ["created", "updated", "transitioned", "deleted"]) {
    const c = classifyEvent(plane(`bloodbank.evt.repo.task.${t}`), routes);
    assert.equal(c.kind, "plane-edit", t);
    assert.deepEqual(c.boards, [PX]);
    assert.equal(c.ticketKey, "PX-28");
  }
});

test("a comment (appended), an unknown board and a boardless event start nothing", () => {
  assert.match(classifyEvent(plane("bloodbank.evt.repo.task.appended"), routes).ignored, /comments/);
  assert.match(classifyEvent(plane("bloodbank.evt.repo.task.updated", { board: "b-client" }), routes).ignored, /no krebs scope/);
  const boardless = plane("bloodbank.evt.repo.task.updated");
  delete boardless.envelope.board_id;
  delete boardless.envelope.data.board_id;
  assert.match(classifyEvent(boardless, routes).ignored, /no board/);
  assert.match(classifyEvent({ subject: "bloodbank.evt.something.else", envelope: {} }, routes).ignored, /not watched/);
});

test("an event Krebs's own write caused is ignored (echo), and only that ticket's", () => {
  const echo = (key, ms) => key === "PX-28" && ms === Date.parse("2026-11-20T12:00:00.000Z");
  assert.match(classifyEvent(plane("bloodbank.evt.repo.task.updated"), routes, { echo }).ignored, /echo of a krebs write/);
  assert.equal(classifyEvent(plane("bloodbank.evt.repo.task.updated", { key: "PX-29" }), routes, { echo }).kind, "plane-edit");
});

test("a gateway turn end maps to the agent's board; hook-hub and claude-code session ends are not turns", () => {
  const c = classifyEvent(turn("completed"), routes);
  assert.equal(c.kind, "turn-ended");
  assert.deepEqual(c.boards, [PX]);
  assert.equal(c.invocationId, "cmd-1");
  assert.equal(classifyEvent(turn("failed"), routes).kind, "turn-ended");
  const hook = { subject: "bloodbank.evt.agent.invocation.completed", envelope: { service: "hermes-hooks", data: { invocation_id: "s1", payload: {} } } };
  assert.match(classifyEvent(hook, routes).ignored, /not a gateway turn end/);
  assert.match(classifyEvent(turn("completed", { service: "claude-code" }), routes).ignored, /not a gateway turn end/);
  assert.match(classifyEvent(turn("completed", { agent: "navi-pm" }), routes).ignored, /owns no krebs scope/);
});

test("a turn end names the board when the agent owns several, else every board it owns", () => {
  const multi = routesFromScopes([...scopes, { agentId: "pilot-pm", boardId: "b-second", identifier: "SEC" }]);
  assert.deepEqual(classifyEvent(turn("completed", { board: "b-second" }), multi).boards, ["b-second"]);
  assert.deepEqual(classifyEvent(turn("completed", { board: "elsewhere" }), multi).boards.sort(), [PX, "b-second"].sort());
});

test("the consumer filter lists exactly the subjects classifyEvent understands", () => {
  assert.deepEqual(WATCH_SUBJECTS.filter((s) => s.includes("repo.task")).length, 4);
  assert.ok(WATCH_SUBJECTS.includes("bloodbank.evt.agent.invocation.completed"));
  assert.ok(!WATCH_SUBJECTS.some((s) => s.endsWith("appended")), "comments are not subscribed");
});

// ---------------------------------------------------------------------------------------------
// the watcher: debounce, serialization, re-arm
// ---------------------------------------------------------------------------------------------

class Clock {
  constructor(start = 1_000_000) {
    this.t = start;
    this.timers = [];
    this.seq = 0;
  }
  now = () => this.t;
  setTimer = (ms, fn) => {
    const h = { at: this.t + ms, fn, id: ++this.seq, live: true };
    this.timers.push(h);
    return h;
  };
  clearTimer = (h) => {
    if (h) h.live = false;
  };
  /** Advance, firing timers in order; lets async runs finish between timers. */
  async advance(ms) {
    const target = this.t + ms;
    for (;;) {
      await settle();
      const due = this.timers.filter((h) => h.live && h.at <= target).sort((a, b) => a.at - b.at || a.id - b.id)[0];
      if (!due) break;
      due.live = false;
      this.t = Math.max(this.t, due.at);
      due.fn();
    }
    await settle();
    this.t = target;
  }
}
const settle = async () => {
  for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r));
};

function harness({ outcomes = [], config = {} } = {}) {
  const clock = new Clock();
  const runs = [];
  const logs = [];
  const watcher = new Watcher({
    now: clock.now,
    setTimer: clock.setTimer,
    clearTimer: clock.clearTimer,
    log: (l) => logs.push(l),
    config,
    run: async (board, info) => {
      runs.push({ at: clock.t, board, ...info });
      const next = outcomes.shift();
      return typeof next === "function" ? next(board, info) : next ?? { ok: true, quiet: [], busyTurns: [] };
    },
  });
  const plane = (board = PX, key = "PX-28") => watcher.onClassified(classifyEvent({ subject: "bloodbank.evt.repo.task.updated", envelope: { board_id: board, time: new Date(clock.t).toISOString(), data: { board_id: board, ticket_key: key } } }, routes));
  const ended = (cmd = "c1", agent = "pilot-pm") => watcher.onClassified(classifyEvent(turn("completed", { agent, command: cmd }), routes));
  return { clock, runs, logs, watcher, plane, ended };
}

test("a burst of Plane edits is one run, 60 s after the last edit", async () => {
  const { clock, runs, plane } = harness();
  plane();
  await clock.advance(20_000);
  plane();
  await clock.advance(20_000);
  plane();
  await clock.advance(59_000);
  assert.equal(runs.length, 0, "still settling");
  await clock.advance(2_000);
  assert.equal(runs.length, 1);
  assert.equal(runs[0].board, PX);
  assert.equal(runs[0].trigger, "plane-edit");
  assert.match(runs[0].detail, /PX-28/);
  await clock.advance(10 * 60_000);
  assert.equal(runs.length, 1, "no event, no more runs");
});

test("an endless stream of edits cannot postpone the run past the max wait", async () => {
  const { clock, runs, plane } = harness();
  for (let i = 0; i < 40; i++) {
    plane();
    await clock.advance(30_000);
  }
  assert.ok(runs.length >= 1, "ran during the stream");
  assert.ok(runs[0].at - 1_000_000 <= WATCH_DEFAULTS.planeMaxWaitMs + 1000, `first run at +${runs[0].at - 1_000_000}ms`);
});

test("a finished turn runs its board 8 s later, and is not delayed by Plane edits after it", async () => {
  const { clock, runs, plane, ended } = harness();
  ended();
  await clock.advance(3_000);
  plane(); // the pickup chip clears agent:working
  await clock.advance(6_000);
  assert.equal(runs.length, 1, "ran at +8 s");
  assert.equal(runs[0].trigger, "turn-ended");
  assert.equal(runs[0].at - 1_000_000, 8_000);
  await clock.advance(70_000);
  assert.equal(runs.length, 1, "the plane edit was answered by the same run");
});

test("boards run independently; a second signal for the other board does not reset the first", async () => {
  const { clock, runs, plane } = harness();
  plane(PX);
  await clock.advance(30_000);
  plane(G33, "33GOD-9");
  await clock.advance(31_000);
  assert.deepEqual(runs.map((r) => r.board), [PX]);
  await clock.advance(30_000);
  assert.deepEqual(runs.map((r) => r.board), [PX, G33]);
});

test("runs are serialized: two boards due together run one after the other", async () => {
  let inFlight = 0;
  let peak = 0;
  const clock = new Clock();
  const runs = [];
  const watcher = new Watcher({
    now: clock.now, setTimer: clock.setTimer, clearTimer: clock.clearTimer,
    run: async (board) => {
      inFlight++;
      peak = Math.max(peak, inFlight);
      runs.push(board);
      await new Promise((r) => setImmediate(r));
      inFlight--;
      return { ok: true };
    },
  });
  watcher.signal(PX, "plane-edit", { delayMs: 1000 });
  watcher.signal(G33, "plane-edit", { delayMs: 1000 });
  await clock.advance(2000);
  assert.deepEqual(runs.sort(), [G33, PX].sort());
  assert.equal(peak, 1);
});

test("an edit that arrives while the board runs is pending again and runs after it", async () => {
  let release;
  const clock = new Clock();
  const runs = [];
  const watcher = new Watcher({
    now: clock.now, setTimer: clock.setTimer, clearTimer: clock.clearTimer,
    run: async (board, info) => {
      runs.push(info.trigger);
      if (runs.length === 1) await new Promise((r) => (release = r));
      return { ok: true };
    },
  });
  watcher.signal(PX, "plane-edit", { delayMs: 1000 });
  await clock.advance(1500);
  assert.equal(runs.length, 1);
  watcher.signal(PX, "plane-edit", { delayMs: 60_000 }); // mid-run
  release();
  await clock.advance(1000);
  assert.equal(runs.length, 1);
  await clock.advance(70_000);
  assert.equal(runs.length, 2);
});

test("tick.lock held: the board is re-armed with backoff, bounded, then left to the backstop", async () => {
  const busy = { busy: true };
  const { clock, runs, plane, logs } = harness({ outcomes: Array(10).fill(busy) });
  plane();
  await clock.advance(61_000);
  assert.equal(runs.length, 1);
  const gaps = [];
  let last = runs[0].at;
  for (let i = 0; i < 8; i++) {
    await clock.advance(61_000);
    if (runs.length > i + 1) {
      gaps.push(runs[i + 1].at - last);
      last = runs[i + 1].at;
    }
  }
  assert.equal(runs.length, 1 + WATCH_DEFAULTS.lockRetryMs.length, "5 retries, no more");
  // 5 s, 10 s, 20 s, 40 s, 60 s backoff, but two runs of a board are never closer than the 10 s gap
  assert.deepEqual(gaps.map((g) => Math.round(g / 1000)), [10, 10, 20, 40, 60]);
  assert.ok(runs.slice(1).every((r) => r.trigger === "plane-edit"), "a retry keeps the original trigger");
  assert.ok(logs.some((l) => /leaving it to the backstop/.test(l)));
});

test("a lock-held retry that succeeds resets the budget", async () => {
  const { clock, runs, plane } = harness({ outcomes: [{ busy: true }, { ok: true }, { busy: true }, { ok: true }] });
  plane();
  await clock.advance(61_000);
  await clock.advance(30_000);
  assert.equal(runs.length, 2);
  plane();
  await clock.advance(61_000);
  await clock.advance(30_000);
  assert.equal(runs.length, 4);
});

test("a ticket still inside its quiet window re-arms the board for the moment the window ends", async () => {
  const { clock, runs, plane } = harness({
    outcomes: [(board) => ({ ok: true, quiet: [{ key: "PX-28", kind: "triage", eligibleAt: clock.t + 50_000 }], busyTurns: [] }), { ok: true }],
  });
  plane();
  await clock.advance(61_000);
  assert.equal(runs.length, 1);
  await clock.advance(48_000);
  assert.equal(runs.length, 1);
  await clock.advance(3_000);
  assert.equal(runs.length, 2);
  assert.equal(runs[1].trigger, "quiet-window");
  assert.match(runs[1].detail, /PX-28 quiet window ends/);
  await clock.advance(60 * 60_000);
  assert.equal(runs.length, 2, "nothing left waiting: no further run");
});

test("only the earliest quiet window is armed, and a far-off one is left to the backstop", async () => {
  const { clock, runs, plane } = harness({
    outcomes: [(board) => ({ ok: true, quiet: [{ key: "PX-1", kind: "review", eligibleAt: clock.t + 2 * 60 * 60_000 }], busyTurns: [] })],
  });
  plane();
  await clock.advance(61_000);
  await clock.advance(3 * 60 * 60_000);
  assert.equal(runs.length, 1);
});

test("a scope held busy by a turn that already ended (Candystore lag) is looked at again, a bounded number of times", async () => {
  const lag = () => ({ ok: true, quiet: [], busyTurns: ["c1"] });
  const { clock, runs, ended } = harness({ outcomes: [lag, lag, lag, lag, lag, lag] });
  ended("c1");
  await clock.advance(9_000);
  assert.equal(runs.length, 1);
  assert.equal(runs[0].trigger, "turn-ended");
  await clock.advance(5 * 60_000);
  assert.equal(runs.length, 1 + WATCH_DEFAULTS.busyLagMaxRetries);
  assert.ok(runs.slice(1).every((r) => r.trigger === "turn-ended"));
});

test("a scope busy on a turn still running waits for its end event, not a poll", async () => {
  const running = () => ({ ok: true, quiet: [], busyTurns: ["still-running"] });
  const { clock, runs, plane, ended } = harness({ outcomes: [running, { ok: true }] });
  plane();
  await clock.advance(61_000);
  assert.equal(runs.length, 1);
  await clock.advance(30 * 60_000);
  assert.equal(runs.length, 1, "no poll: nothing runs until an event arrives");
  ended("still-running");
  await clock.advance(9_000);
  assert.equal(runs.length, 2, "its end starts the next board turn");
});

test("consecutive turn ends chain back-to-back runs on one board, the min gap apart", async () => {
  const { clock, runs, ended } = harness();
  ended("t1");
  await clock.advance(9_000);
  ended("t2"); // the next triage ended 4.5 min later in real life; here just after, to test the gap
  await clock.advance(30_000);
  assert.equal(runs.length, 2);
  assert.ok(runs[1].at - runs[0].at >= WATCH_DEFAULTS.minGapMs);
});

test("no self-loop: a run that makes Plane edit events every time is held by the runaway cap", async () => {
  // The worst case the echo filter could miss: each run writes, the write echoes as a fresh edit, repeat.
  const clock = new Clock();
  const runs = [];
  const logs = [];
  let watcher;
  watcher = new Watcher({
    now: clock.now, setTimer: clock.setTimer, clearTimer: clock.clearTimer, log: (l) => logs.push(l),
    run: async (board) => {
      runs.push(clock.t);
      watcher.signal(board, "plane-edit", { delayMs: 1000, maxWaitMs: 1000 }); // the echo of its own write
      return { ok: true };
    },
  });
  watcher.signal(PX, "plane-edit", { delayMs: 1000 });
  await clock.advance(10 * 60_000);
  assert.ok(runs.length <= WATCH_DEFAULTS.runCap, `${runs.length} runs in 10 minutes`);
  assert.ok(runs.length >= 2);
  assert.ok(logs.some((l) => /runaway guard/.test(l)));
});

test("no self-loop: Krebs's journalled write is recognised as the echo, so it starts no run", async () => {
  const dir = tempDir();
  const path = join(dir, "j.jsonl");
  const t0 = Date.parse("2026-11-20T12:00:00.000Z");
  writeFileSync(path, [
    JSON.stringify({ ts: "2026-11-20T11:00:00.000Z", action: "dispatch.write", key: "PX-1", ok: true }),
    JSON.stringify({ ts: "2026-11-20T12:00:00.010Z", action: "dispatch.write", key: "PX-28", ok: true }),
    JSON.stringify({ ts: "2026-11-20T12:00:00.020Z", action: "triage.publish", key: "PX-30", ok: true }),
    JSON.stringify({ ts: "2026-11-20T12:00:00.030Z", action: "repair", key: "PX-31", ok: false }),
  ].join("\n") + "\n");
  const echo = journalEcho(path);
  assert.equal(echo("PX-28", t0), true, "a dispatch write 10 ms after the event");
  assert.equal(echo("PX-28", t0 + 60_000), false, "an edit a minute later is a real edit");
  assert.equal(echo("PX-1", t0), false, "an old write");
  assert.equal(echo("PX-30", t0), false, "a publish is not a Plane write");
  assert.equal(echo("PX-31", t0), false, "a failed write changed nothing");
  appendFileSync(path, JSON.stringify({ ts: "2026-11-20T12:00:30.000Z", action: "orphan.release", key: "PX-40", ok: true }) + "\n");
  assert.equal(echo("PX-40", Date.parse("2026-11-20T12:00:30.500Z")), true, "appended later: read fresh each time");
  const c = classifyEvent(plane("bloodbank.evt.repo.task.updated", { time: "2026-11-20T12:00:00.000Z" }), routes, { echo });
  assert.match(c.ignored, /echo/);
});

test("a failing run is logged and does not wedge the board", async () => {
  const { clock, runs, plane, logs } = harness({ outcomes: [() => { throw new Error("boom"); }, { ok: true }] });
  plane();
  await clock.advance(61_000);
  assert.equal(runs.length, 1);
  assert.ok(logs.some((l) => /run failed \(boom\)/.test(l)));
  plane();
  await clock.advance(61_000);
  assert.equal(runs.length, 2);
});

// ---------------------------------------------------------------------------------------------
// the runner and its report
// ---------------------------------------------------------------------------------------------

test("outcomeOfReport reads lock, quiet windows and busy turns off a tick report", () => {
  assert.deepEqual(outcomeOfReport(0, { ok: true, busy: true }), { busy: true });
  assert.match(outcomeOfReport(2, { ok: false, error: "no agents-registry row" }).error, /no agents-registry row/);
  assert.match(outcomeOfReport(1, null).error, /without a JSON report/);
  const out = outcomeOfReport(0, {
    ok: true,
    quiet: [{ key: "PX-28", kind: "triage", eligibleAt: 5 }],
    scopes: [
      { dispatches: [{ result: "dispatched" }, { result: "skipped" }], triage: [{ result: "published" }], reviews: [], repairs: [], errors: [], boardTurnBusy: { why: "x", turns: [{ invocationId: "c9" }] } },
      { dispatches: [], triage: [], reviews: [{ result: "published" }], repairs: [{ result: "repaired" }], errors: ["e"] },
    ],
  });
  assert.deepEqual(out.busyTurns, ["c9"]);
  assert.deepEqual(out.summary, { dispatched: 1, triaged: 1, reviews: 1, repaired: 1, busy: 1, errors: 1 });
  assert.equal(out.quiet[0].key, "PX-28");
});

test("the child runner runs `krebs tick --board <id> --json --trigger <kind>` and parses its report", async () => {
  let seen;
  const run = childTickRunner({
    node: "node", script: "/x/krebs.mjs",
    exec: (cmd, args, opts, cb) => {
      seen = { cmd, args, opts };
      cb(null, JSON.stringify({ ok: true, quiet: [], scopes: [] }), "");
    },
  });
  const out = await run(PX, { trigger: "plane-edit", detail: "PX-28 plane.ticket.updated" });
  assert.deepEqual(seen.args, ["/x/krebs.mjs", "tick", "--board", PX, "--json", "--trigger", "plane-edit", "--trigger-detail", "PX-28 plane.ticket.updated"]);
  assert.equal(out.ok, true);
  const failing = childTickRunner({ script: "/x", exec: (c, a, o, cb) => cb(Object.assign(new Error("spawn failed"), { code: 1 }), "", "") });
  assert.match((await failing(PX, { trigger: "plane-edit" })).error, /spawn failed/);
  const withReport = childTickRunner({ script: "/x", exec: (c, a, o, cb) => cb(Object.assign(new Error("exit 1"), { code: 1 }), JSON.stringify({ ok: false, scopes: [{ errors: ["x"] }] }), "") });
  const o = await withReport(PX, { trigger: "plane-edit" });
  assert.equal(o.ok, false, "exit 1 with a report is a report, not a crash");
});

// ---------------------------------------------------------------------------------------------
// quiet windows, heartbeat, spec pin
// ---------------------------------------------------------------------------------------------

const lanes = laneModel(STATES);
const labelNameOf = new Map(LABEL_NAMES.map((n) => [labelId(n), n]));
const tk = (spec) => normalizeTicket(issue(spec), { lanes, labelNameOf, identifier: "T" });

test("quiet windows: a Todo ticket inside the triage window, a handback inside the review window, nothing else", () => {
  const now = Date.parse("2026-11-20T12:00:00Z");
  const iso = (msAgo) => new Date(now - msAgo).toISOString();
  const tickets = [
    tk({ seq: 1, updated: iso(30_000) }),
    tk({ seq: 2, updated: iso(TRIAGE_MIN_AGE_MS + 5_000) }),
    tk({ seq: 3, updated: iso(30_000), labels: ["lifecycle:triaged"] }),
    tk({ seq: 4, updated: iso(30_000), labels: ["lifecycle:needs-input"] }),
    tk({ seq: 5, state: "ip", labels: ["lifecycle:review"], updated: iso(60_000) }),
    tk({ seq: 6, state: "ip", labels: ["lifecycle:review"], updated: iso(REVIEW_MIN_AGE_MS + 60_000) }),
    tk({ seq: 7, state: "backlog", updated: iso(30_000) }),
  ];
  const q = quietWindows(tickets, now);
  assert.deepEqual(q.map((x) => [x.key, x.kind]), [["T-1", "triage"], ["T-5", "review"]]);
  assert.equal(q[0].eligibleAt, now - 30_000 + TRIAGE_MIN_AGE_MS + 1, "eligible 1 ms after the window, because the tick tests strictly older");
});

test("watch state: a fresh heartbeat from a live pid is alive; a stale or dead one is not", () => {
  const dir = tempDir();
  const path = join(dir, "watch.json");
  assert.equal(readWatchState({ path }).alive, false);
  writeWatchState({ pid: 4242, startedAt: "x" }, { path, now: () => new Date("2026-11-20T12:00:00Z") });
  const at = Date.parse("2026-11-20T12:00:00Z");
  assert.equal(readWatchState({ path, nowMs: at + 30_000, alive: () => true }).alive, true);
  assert.match(readWatchState({ path, nowMs: at + WATCH_STALE_MS + 1, alive: () => true }).why, /last heartbeat/);
  assert.match(readWatchState({ path, nowMs: at + 30_000, alive: () => false }).why, /pid 4242 is gone/);
  assert.equal(JSON.parse(readFileSync(path, "utf8")).pid, 4242);
});

test("spec pin: the triage quiet window in code is the number in spec/lifecycle.v2.yaml", () => {
  const require = createRequire(join(bloodbankN8nDir(), "package.json"));
  const yaml = require("yaml");
  const spec = yaml.parse(readFileSync(new URL("../../spec/lifecycle.v2.yaml", import.meta.url), "utf8"));
  assert.equal(spec.board_turns.triage_quiet_seconds * 1000, TRIAGE_MIN_AGE_MS);
  assert.equal(spec.board_turns.review_quiet_seconds * 1000, REVIEW_MIN_AGE_MS);
  assert.equal(spec.board_turns.settle_seconds.plane_edit * 1000, WATCH_DEFAULTS.planeSettleMs);
  assert.equal(spec.board_turns.settle_seconds.turn_ended * 1000, WATCH_DEFAULTS.turnSettleMs);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { loadBloodbank } from "../deps.mjs";
import { scopesFromRegistry } from "../registry.mjs";
import { runTick } from "../run.mjs";
import { MemoryJournal } from "../journal.mjs";
import {
  TICK_MS,
  buildStatus,
  classifyScope,
  collectTurns,
  formatStatus,
  formatTicket,
  invocationsOf,
  nextTickAfter,
  openTurns,
  projectBoardTurns,
  recentActivity,
  whyNothingMoved,
} from "../status.mjs";
import { FakePlane, SOLO, fakePublisher, issue, registryFixture, tempDir } from "./helpers.mjs";

const { fleet, nats, registry: bbRegistry } = loadBloodbank();

// The PX drop of 2026-11-20, as it stood at 11:37Z: PX-10 and PX-19 already triaged and waiting,
// five untriaged tickets updated within seconds of each other at 11:08Z, both WIP slots free.
const NOW = new Date("2026-11-20T11:37:00Z");
const at = (hhmmss) => `2026-11-20T${hhmmss}Z`;

async function plan({ issues, now = NOW, wip = 2, review = false, relations = {}, journal = new MemoryJournal() }) {
  const registry = registryFixture();
  registry.agents["solo-pm"].plane.wip = wip;
  registry.agents["solo-pm"].plane.review = review;
  const plane = new FakePlane({ [SOLO]: { issues, relations } });
  const { scopes, skipped } = scopesFromRegistry(registry, { activation: bbRegistry.bloodbankActivation, executionMode: () => "legacy", board: "SOLO" });
  let inspected = [];
  const publish = fakePublisher();
  const report = await runTick({ registry, scopes, skipped, plane, fleet, nats, publish, journal, dryRun: true, now: () => now, inspect: (x) => (inspected = x) });
  return { report, inspected, plane, publish, journal };
}

const PX_ISSUES = () => [
  issue({ seq: 10, labels: ["lifecycle:triaged"], updated: at("11:31:00"), sort: 1 }),
  issue({ seq: 19, labels: ["lifecycle:triaged"], updated: at("11:21:00"), sort: 2 }),
  issue({ seq: 12, updated: at("11:08:10") }),
  issue({ seq: 20, updated: at("11:08:20") }),
  issue({ seq: 25, updated: at("11:08:30") }),
  issue({ seq: 18, updated: at("11:08:40") }),
  issue({ seq: 28, updated: at("11:08:50") }),
];

const classify = (p, extra = {}) => {
  const { scope, out, tickets } = p.inspected[0];
  return classifyScope({ scope, out, tickets, nowMs: NOW.getTime(), turns: new Map(), ...extra });
};
const byKey = (result) => Object.fromEntries(result.rows.map((r) => [r.key, r]));
const hhmm = (iso) => iso.slice(11, 16);

test("the PX scenario: triage is serialized one per tick, last untriaged ticket ~70 min after the drop", async () => {
  const p = await plan({ issues: PX_ISSUES() });
  const rows = byKey(classify(p));
  // dispatch: both triaged tickets go at the next tick
  for (const k of ["SOLO-10", "SOLO-19"]) {
    assert.equal(rows[k].stage, "ready", k);
    assert.equal(hhmm(rows[k].eta), "11:40");
  }
  // triage: oldest first, one per tick, 10 minutes apart
  assert.equal(rows["SOLO-12"].stage, "triage-next");
  assert.equal(rows["SOLO-12"].queuePosition, 1);
  assert.equal(hhmm(rows["SOLO-12"].eta), "11:40");
  assert.deepEqual(
    ["SOLO-20", "SOLO-25", "SOLO-18", "SOLO-28"].map((k) => [rows[k].stage, rows[k].queuePosition, hhmm(rows[k].eta)]),
    [
      ["triage-queued", 2, "11:50"],
      ["triage-queued", 3, "12:00"],
      ["triage-queued", 4, "12:10"],
      ["triage-queued", 5, "12:20"],
    ],
  );
  assert.match(rows["SOLO-28"].stageLabel, /queued for triage #5/);
  // the tick's own plan agrees: it will take SOLO-12 now and cap the rest
  assert.deepEqual(p.inspected[0].out.triage.map((t) => t.key), ["SOLO-12"]);
  assert.deepEqual(p.inspected[0].out.triageCapped.map((t) => t.key), ["SOLO-20", "SOLO-25", "SOLO-18", "SOLO-28"]);
});

test("a ticket still inside its 10-minute quiet window waits for it, then for its place in the queue", async () => {
  const issues = [issue({ seq: 1, updated: at("11:30:30") }), issue({ seq: 2, updated: at("11:36:00") }), issue({ seq: 3, updated: at("11:08:00") })];
  const rows = byKey(classify(await plan({ issues })));
  assert.equal(rows["SOLO-3"].stage, "triage-next");
  assert.equal(hhmm(rows["SOLO-3"].eta), "11:40");
  assert.equal(rows["SOLO-1"].stage, "quiet-window");
  assert.match(rows["SOLO-1"].reason, /quiet for 10 min \(eligible ~11:40Z\)/);
  assert.equal(hhmm(rows["SOLO-1"].eta), "11:50", "11:30:30 + 10 min is just after the 11:40 tick");
  assert.equal(hhmm(rows["SOLO-2"].eta), "12:00", "11:36 is eligible 11:46, but the 11:50 turn is taken");
});

test("triage turn exactly 10 minutes old is not eligible, matching the tick (strictly older than 10 min)", () => {
  const items = [{ ticket: { key: "T-1", updatedAt: at("11:30:00"), seq: 1, id: "a" }, kind: "triage", eligibleMs: Date.parse(at("11:40:00")) }];
  const map = projectBoardTurns({ items, nextTickMs: Date.parse(at("11:40:00")) });
  assert.equal(map.get("T-1").tickMs, Date.parse(at("11:40:00")), "a tick starts a moment after the mark, so 11:30:00 is eligible at the 11:40 tick");
  const later = projectBoardTurns({ items: [{ ...items[0], eligibleMs: Date.parse(at("11:40:30")) }], nextTickMs: Date.parse(at("11:40:00")) });
  assert.equal(later.get("T-1").tickMs, Date.parse(at("11:50:00")));
});

test("triage and review alternate within a scope, and the order flips with the last turn sent", () => {
  const mk = (key, seq, kind, eligibleIso) => ({ ticket: { key, seq, id: key, updatedAt: eligibleIso }, kind, eligibleMs: Date.parse(eligibleIso) - 1 });
  const items = [mk("R-1", 1, "review", at("09:00:00")), mk("T-1", 2, "triage", at("10:00:00")), mk("T-2", 3, "triage", at("10:01:00"))];
  const next = Date.parse(at("11:40:00"));
  const fromTriage = projectBoardTurns({ items, nextTickMs: next, prefer: "triage" });
  assert.deepEqual([...fromTriage.entries()].map(([k, v]) => [k, v.order]), [["T-1", 1], ["R-1", 2], ["T-2", 3]]);
  const fromReview = projectBoardTurns({ items, nextTickMs: next, prefer: "review" });
  assert.deepEqual([...fromReview.entries()].map(([k, v]) => [k, v.order]), [["R-1", 1], ["T-1", 2], ["T-2", 3]]);
});

test("nextTickAfter is the next 10-minute mark, strictly after now", () => {
  assert.equal(new Date(nextTickAfter(Date.parse(at("11:37:12")))).toISOString(), "2026-11-20T11:40:00.000Z");
  assert.equal(new Date(nextTickAfter(Date.parse(at("11:40:00")))).toISOString(), "2026-11-20T11:50:00.000Z");
  assert.equal(TICK_MS, 600000);
});

test("held, epic, failed and blocked_by tickets say why nothing will happen to them", async () => {
  const issues = [
    issue({ seq: 1, labels: ["lifecycle:triaged", "lifecycle:blocked"], updated: at("10:00:00") }),
    issue({ seq: 2, labels: ["lifecycle:needs-input"], updated: at("10:00:00") }),
    issue({ seq: 3, labels: ["agent:failed"], updated: at("10:00:00") }),
    issue({ seq: 4, labels: ["lifecycle:human"], updated: at("10:00:00") }),
    issue({ seq: 5, labels: ["epic"], updated: at("10:00:00") }),
    issue({ seq: 6, labels: ["lifecycle:triaged"], updated: at("10:00:00"), sort: 1 }),
    issue({ seq: 7, labels: ["lifecycle:triaged"], updated: at("10:00:00"), sort: 2 }),
    issue({ seq: 8, state: "backlog", updated: at("10:00:00") }),
    issue({ seq: 9, state: "done", updated: at("10:00:00") }),
  ];
  const relations = { "i-6": { blocked_by: [{ issue_id: "i-7" }], blocking: [], relates_to: [] } };
  const result = classify(await plan({ issues, relations }));
  const rows = byKey(result);
  assert.equal(rows["SOLO-1"].stage, "held");
  assert.equal(rows["SOLO-1"].stageLabel, "held: lifecycle:blocked");
  assert.match(rows["SOLO-2"].reason, /waiting on a person/);
  assert.equal(rows["SOLO-3"].stageLabel, "held: agent:failed");
  assert.match(rows["SOLO-4"].reason, /took this one by hand/);
  assert.equal(rows["SOLO-5"].stage, "epic");
  assert.equal(rows["SOLO-5"].stageLabel, "epic: never dispatched");
  assert.equal(rows["SOLO-6"].stage, "blocked-by");
  assert.equal(rows["SOLO-6"].stageLabel, "blocked_by SOLO-7");
  assert.equal(rows["SOLO-7"].stage, "ready");
  assert.equal(rows["SOLO-8"].stage, "backlog");
  assert.equal(rows["SOLO-9"].stage, "done");
});

test("a triaged ticket with no free slot waits behind the slot holders, with no invented ETA", async () => {
  const issues = [
    issue({ seq: 1, state: "ip", labels: ["agent:working"], updated: at("11:20:00") }),
    issue({ seq: 2, state: "ip", labels: ["agent:working"], updated: at("11:25:00") }),
    issue({ seq: 3, labels: ["lifecycle:triaged"], updated: at("11:00:00"), sort: 1 }),
    issue({ seq: 4, labels: ["lifecycle:triaged"], updated: at("11:00:00"), sort: 2 }),
  ];
  const p = await plan({ issues });
  const turns = new Map(
    ["i-1", "i-2"].map((id, n) => [id, { turns: [{ id: `inv-${n}`, reason: "ticket-delegation", kind: "delegation", state: "running", since: NOW.getTime() - (12 + n) * 60000 }], history: [] }]),
  );
  const result = classify(p, { turns });
  const rows = byKey(result);
  assert.equal(rows["SOLO-3"].stage, "wait-slot");
  assert.equal(rows["SOLO-3"].stageLabel, "waiting for a WIP slot behind SOLO-1, SOLO-2");
  assert.equal(rows["SOLO-3"].eta, null);
  assert.match(rows["SOLO-4"].reason, /1 triaged ticket\(s\) are ahead/);
  assert.equal(rows["SOLO-1"].stageLabel, "in progress (delegation running 12m)");
  assert.deepEqual(result.inFlight.map((f) => [f.key, f.kind, f.runningMinutes]), [["SOLO-2", "delegation", 13], ["SOLO-1", "delegation", 12]].sort((a, b) => b[2] - a[2]));
});

test("In Progress with no live turn is an orphan in waiting: release ETA is 30 quiet minutes, rounded up to a tick", async () => {
  const issues = [issue({ seq: 1, state: "ip", updated: at("11:20:00") })];
  const rows = byKey(classify(await plan({ issues })));
  assert.equal(rows["SOLO-1"].stage, "in-progress-idle");
  assert.equal(hhmm(rows["SOLO-1"].eta), "11:50");
});

test("Candystore unreachable: stages do not pretend to know what is running", async () => {
  const issues = [issue({ seq: 1, state: "ip", labels: ["agent:working"], updated: at("11:20:00") }), issue({ seq: 2, state: "ip", updated: at("11:20:00") })];
  const p = await plan({ issues });
  const { scope, out, tickets } = p.inspected[0];
  const rows = byKey(classifyScope({ scope, out, tickets, nowMs: NOW.getTime(), turns: null }));
  assert.equal(rows["SOLO-2"].stage, "in-progress");
  assert.match(rows["SOLO-2"].reason, /Candystore unreachable/);
});

test("review: handed back, waits for 30 quiet minutes then a board turn; a version already asked waits 3 h", async () => {
  const issues = [
    issue({ seq: 1, state: "ip", labels: ["lifecycle:review"], updated: at("11:20:00") }),
    issue({ seq: 2, state: "ip", labels: ["lifecycle:review"], updated: at("09:00:00") }),
  ];
  const p = await plan({ issues, review: true });
  const rows = byKey(classify(p));
  assert.equal(rows["SOLO-1"].stage, "review-wait");
  assert.equal(rows["SOLO-1"].stageLabel, "in review: waiting for quiet");
  assert.equal(rows["SOLO-2"].stage, "review-wait");
  assert.equal(hhmm(rows["SOLO-2"].eta), "11:40", "oldest review is taken first");
  assert.equal(hhmm(rows["SOLO-1"].eta), "11:50", "quiet until 11:50:00; the tick starts just after the mark; and the 11:40 board turn is SOLO-2's");
});

test("review turn already sent for this version: cooling down, with its retry time", async () => {
  const issues = [issue({ seq: 2, state: "ip", labels: ["lifecycle:review"], updated: at("09:00:00") })];
  const journal = new MemoryJournal([
    { ts: at("11:20:06"), action: "review.publish", ok: true, ticket_id: "i-2", ticket_updated_at: at("09:00:00"), attempt: 1, command_id: "c1", agent_id: "solo-pm", board_id: SOLO },
  ]);
  const p = await plan({ issues, review: true, journal });
  const { scope, out, tickets } = p.inspected[0];
  const reviewsSent = new Map([[`i-2|${at("09:00:00")}`, [{ attempt: 1, at: at("11:20:06"), commandId: "c1" }]]]);
  const rows = byKey(classifyScope({ scope, out, tickets, nowMs: NOW.getTime(), turns: new Map(), journal: { reviewsSent } }));
  assert.equal(rows["SOLO-2"].stage, "review-wait");
  assert.equal(hhmm(rows["SOLO-2"].eta), "14:30", "last sent 11:20:06 + 3 h = 14:20:06, so the 14:20 tick is too early and 14:30 is the first that may resend");
});

test("untriaged tickets whose version was already triaged say so instead of promising a turn", async () => {
  const issues = [issue({ seq: 1, updated: at("10:00:00") })];
  const p0 = await plan({ issues });
  const out = { ...p0.inspected[0].out, triageSeen: ["SOLO-1"], triage: [] };
  const rows = byKey(classifyScope({ scope: p0.inspected[0].scope, out, tickets: p0.inspected[0].tickets, nowMs: NOW.getTime(), turns: new Map() }));
  assert.equal(rows["SOLO-1"].stage, "triage-seen");
  assert.equal(rows["SOLO-1"].eta, null);
});

test("a live triage turn is reported in flight with its age, and is not queued again", async () => {
  const issues = [issue({ seq: 1, labels: ["agent:working"], updated: at("11:36:00") }), issue({ seq: 2, updated: at("11:00:00") })];
  const p = await plan({ issues });
  const turns = new Map([["i-1", { turns: [{ id: "x", reason: "ticket-grooming", kind: "triage", state: "running", since: NOW.getTime() - 90_000 }], history: [] }]]);
  const result = classify(p, { turns });
  const rows = byKey(result);
  assert.equal(rows["SOLO-1"].stage, "triage-inflight");
  assert.match(rows["SOLO-1"].reason, /running \(2m\)/);
  assert.equal(rows["SOLO-2"].stage, "triage-next");
  assert.equal(result.inFlight[0].kind, "triage");
});

test("openTurns / invocationsOf: queued, running, detached, sent; ended turns are not live", () => {
  const ev = (type, id, time, ctx = {}, extra = {}) => ({ id: `${type}-${id}-${time}`, type: `bloodbank.agent.invocation.${type}`, time, data: { invocation_id: id, context: ctx, ...extra } });
  const nowMs = Date.parse("2026-11-20T12:00:00Z");
  const events = [
    ev("queued", "a", "2026-11-20T11:40:00Z", { reason: "ticket-grooming" }, { command_service: "krebs-tick" }),
    ev("started", "a", "2026-11-20T11:40:01Z", { reason: "ticket-grooming" }),
    ev("queued", "b", "2026-11-20T11:50:00Z", { reason: "ticket-delegation" }),
    ev("started", "c", "2026-11-20T10:00:00Z", { reason: "ticket-delegation" }),
    ev("detached", "c", "2026-11-20T10:30:00Z"),
    ev("started", "d", "2026-11-20T09:00:00Z", { reason: "ticket-review" }),
    ev("completed", "d", "2026-11-20T09:05:00Z"),
  ];
  const open = openTurns({ invocations: invocationsOf(events), sent: [{ commandId: "zz", at: "2026-11-20T11:58:00Z", kind: "triage" }, { commandId: "a", at: "2026-11-20T11:40:00Z", kind: "triage" }], nowMs });
  const byId = Object.fromEntries(open.map((x) => [x.id, x]));
  assert.deepEqual(Object.keys(byId).sort(), ["a", "b", "c", "zz"]);
  assert.equal(byId.a.state, "running");
  assert.equal(byId.a.kind, "triage");
  assert.equal(byId.b.state, "queued");
  assert.equal(byId.b.kind, "delegation");
  assert.equal(byId.c.state, "detached");
  assert.equal(byId.zz.state, "sent");
});

test("collectTurns: Candystore failing is reported, not thrown", async () => {
  const client = { invocations: async () => { throw new Error("connect ECONNREFUSED 127.0.0.1:8683"); } };
  const res = await collectTurns({ client, fleet, boardId: SOLO, tickets: [{ id: "i-1", key: "SOLO-1" }, { id: "i-2", key: "SOLO-2" }], sentByTicket: new Map(), nowMs: NOW.getTime() });
  assert.equal(res.ok, false);
  assert.match(res.error, /ECONNREFUSED/);
});

test("buildStatus and the human formats: stable JSON shape, idle line, why-nothing-moved", async () => {
  const p = await plan({ issues: PX_ISSUES() });
  const journalEntries = [
    { ts: at("11:10:06"), tick: "tick:2026-11-20T11:10:00.000Z", action: "dispatch.publish", ok: true, agent_id: "solo-pm", key: "SOLO-23", dispatch_id: "d" },
    { ts: at("11:30:06"), tick: "tick:2026-11-20T11:30:00.000Z", action: "triage.publish", ok: true, agent_id: "solo-pm", key: "SOLO-10" },
    { ts: at("11:30:07"), tick: "tick:2026-11-20T11:30:00.000Z", action: "tick", ok: true, scopes: 1, dispatched: 0, triaged: 1, reviews: 0, repaired: 0, errors: 0 },
  ];
  const status = buildStatus({
    inspected: p.inspected,
    journalEntries,
    nowMs: NOW.getTime(),
    turnsByScope: new Map([[`${SOLO}|solo-pm`, { ok: true, error: null, byTicket: new Map() }]]),
    candystore: { ok: true, error: null },
    lastBoardTurn: new Map([[`solo-pm|${SOLO}`, "triage"]]),
    reviewsSent: new Map(),
  });
  assert.deepEqual(Object.keys(status), ["version", "generatedAt", "estimates", "tick", "candystore", "registry", "journal", "scopes"]);
  assert.equal(status.version, 1);
  assert.equal(status.tick.last.triaged, 1);
  assert.equal(status.tick.nextEstimate, "2026-11-20T11:40:00.000Z");
  const s = status.scopes[0];
  assert.deepEqual(Object.keys(s), ["board", "boardId", "agentId", "scopeLabels", "wip", "occupied", "free", "overLimit", "reviewRequired", "idle", "inFlight", "idleReason", "tickets", "counts", "recent", "warnings", "errors"]);
  assert.deepEqual(Object.keys(s.tickets[0]), ["key", "title", "lane", "state", "labels", "updatedAt", "stage", "stageLabel", "reason", "eta", "etaNote", "queuePosition", "blockedBy"]);
  assert.equal(s.tickets.length, 7);
  assert.match(s.idleReason, /5 Todo ticket\(s\) untriaged; triage is serialized at 1 per 10 min per scope; next: SOLO-12 at ~11:40Z, last: SOLO-28 at ~12:20Z/);
  assert.match(s.idleReason, /2 triaged ticket\(s\) ready: dispatch at ~11:40Z/);
  assert.deepEqual(s.recent.map((r) => r.action), ["triage.publish", "dispatch.publish"]);
  assert.equal(s.recent[0].ageMinutes, 7);
  const text = formatStatus(status);
  assert.match(text, /last tick 11:30Z \(7m ago\): ok, dispatched 0, triage 1/);
  assert.match(text, /next tick ~11:40Z \(estimate/);
  assert.match(text, /why nothing moved: 5 Todo ticket/);
  assert.match(text, /SOLO-28\s+Todo\s+queued for triage #5/);
  assert.match(text, /next: ~12:20Z \(in ~43m\)/);
  const idleScope = { ...s, idle: true, tickets: [], inFlight: [], errors: [], board: "ZZ", agentId: "zz-pm", scopeLabels: [], occupied: [] };
  assert.match(formatStatus({ ...status, scopes: [idleScope] }), /idle \(1\): ZZ/);
  assert.equal(formatTicket(status, { row: s.tickets[0], scope: s, trail: s.recent, turns: [] }).includes(s.tickets[0].key), true);
});

test("recentActivity keeps the newest N actions of one agent only", () => {
  const entries = [];
  for (let i = 0; i < 15; i++) entries.push({ ts: at(`10:${String(i).padStart(2, "0")}:00`), action: "triage.publish", ok: true, agent_id: "a-pm", key: `A-${i}` });
  entries.push({ ts: at("11:00:00"), action: "triage.publish", ok: true, agent_id: "b-pm", key: "B-1" });
  entries.push({ ts: at("11:01:00"), action: "dispatch.write", ok: true, agent_id: "a-pm", key: "A-99" });
  const out = recentActivity(entries, { agentId: "a-pm", nowMs: Date.parse(at("11:10:00")) });
  assert.equal(out.length, 10);
  assert.equal(out[0].key, "A-14");
  assert.equal(out[0].ageMinutes, 56);
});

test("whyNothingMoved on an empty board", () => {
  assert.match(whyNothingMoved({ scope: { wip: 2 }, rows: [], occupied: [] }), /nothing to do/);
});

test("status is read-only: the plan makes no Plane write, no publish, and leaves the journal untouched", async () => {
  const p = await plan({ issues: PX_ISSUES() });
  assert.deepEqual(p.plane.writes(), []);
  assert.equal(p.publish.sent.length, 0);
  assert.equal(p.journal.read().length, 0);
});

const BIN = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "bin", "krebs.mjs");
const cli = (args, env = {}) => spawnSync(process.execPath, [BIN, ...args], { encoding: "utf8", env: { ...process.env, ...env }, timeout: 30_000 });

test("cli: status is listed in --help, with the triage window the spec says (10 minutes, not 30)", () => {
  const help = cli(["--help"]);
  assert.equal(help.status, 0);
  assert.match(help.stdout, /krebs status \[--board KEY\] \[--ticket KEY\] \[--json\]/);
  assert.match(help.stdout, /unchanged for 10 minutes/);
  assert.doesNotMatch(help.stdout, /unchanged for 30 minutes/);
});

test("cli: status usage errors exit 2; an unknown board never reaches Plane", () => {
  const dir = tempDir();
  const registry = join(dir, "agents-registry.yaml");
  writeFileSync(registry, "schema_version: 1\nagents:\n  a-pm:\n    profile_name: a-pm\n    bloodbank: {enabled: true, gateway_scope: fleet, target_agent_id: a-pm}\n    plane: {workspace: w, project_id: b1, identifier: AAA}\n");
  assert.equal(cli(["status", "--dry-run"]).status, 2);
  assert.equal(cli(["status", "--nope"]).status, 2);
  assert.equal(cli(["tick", "--ticket", "AAA-1"]).status, 2);
  const unknown = cli(["status", "--json", "--board", "ZZZ", "--registry", registry], { KREBS_STATE_DIR: dir });
  assert.equal(unknown.status, 2);
  assert.match(JSON.parse(unknown.stdout).error, /names board ZZZ/);
  const badKey = cli(["status", "--ticket", "nonsense", "--registry", registry], { KREBS_STATE_DIR: dir, PLANE_API_KEY: "env:KREBS_TEST_UNSET_VAR" });
  assert.equal(badKey.status, 2);
});

test("cli: status with no scopes prints an empty status and never creates the journal or the lock", () => {
  const dir = tempDir();
  const registry = join(dir, "agents-registry.yaml");
  const journal = join(dir, "j.jsonl");
  writeFileSync(registry, "schema_version: 1\nagents:\n  off-pm:\n    profile_name: off-pm\n    bloodbank: {enabled: false, gateway_scope: fleet, target_agent_id: off-pm}\n    plane: {workspace: w, project_id: b1, identifier: OFF}\n");
  const res = cli(["status", "--json", "--registry", registry, "--journal", journal], { KREBS_STATE_DIR: dir, PLANE_API_KEY: "env:KREBS_TEST_UNSET_VAR" });
  assert.equal(res.status, 0, res.stderr);
  const out = JSON.parse(res.stdout);
  assert.equal(out.version, 1);
  assert.deepEqual(out.scopes, []);
  assert.equal(existsSync(journal), false);
  assert.equal(existsSync(join(dir, "tick.lock")), false);
});

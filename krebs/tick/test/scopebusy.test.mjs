// spec board_turns.per_scope (ADR 0002): a scope has at most ONE board turn (triage or review, any ticket)
// queued or running; the tick asks Candystore and sends none while one is in flight.

import { test } from "node:test";
import assert from "node:assert/strict";

import { loadBloodbank } from "../deps.mjs";
import { scopesFromRegistry } from "../registry.mjs";
import { runTick } from "../run.mjs";
import { MemoryJournal } from "../journal.mjs";
import { boardTurnsInFlight, candystoreScopeBusy, MAX_OPEN_TRIAGE_MS } from "../liveness.mjs";
import { FakePlane, NOW, fakePublisher, issue, registryFixture } from "./helpers.mjs";

const { fleet, nats, registry: bbRegistry } = loadBloodbank();
const NOW_MS = NOW.getTime();
const minsAgo = (m) => new Date(NOW_MS - m * 60000).toISOString();
const OLD = minsAgo(120);
const OTHER = "b-other";
const AGENT = "other-pm";

const ev = (type, id, { agent = AGENT, reason = "ticket-grooming", key = "OTH-1", ago = 5 } = {}) => ({
  type: `bloodbank.agent.invocation.${type}`,
  time: minsAgo(ago),
  data: { invocation_id: id, command_id: id, target_agent_id: agent, context: { reason, ticket_key: key } },
});
const inFlight = (events, extra = {}) => boardTurnsInFlight({ events, agentId: AGENT, nowMs: NOW_MS, ...extra });

test("boardTurnsInFlight: a triage or review turn queued or running counts, with the ticket and state", () => {
  const q = inFlight([ev("queued", "a", { ago: 4 })]);
  assert.equal(q.busy, true);
  assert.deepEqual(q.turns.map((x) => [x.id, x.state, x.key]), [["a", "queued", "OTH-1"]]);
  const r = inFlight([ev("queued", "b", { reason: "ticket-review", key: "OTH-9", ago: 6 }), ev("started", "b", { reason: "ticket-review", key: "OTH-9", ago: 5 })]);
  assert.equal(r.busy, true);
  assert.equal(r.turns[0].state, "running");
  assert.match(r.why, /review turn on OTH-9 is running/);
});

test("boardTurnsInFlight: an ended turn, another agent's turn, a delegation and a stale turn do not count", () => {
  assert.equal(inFlight([ev("queued", "a", { ago: 9 }), ev("started", "a", { ago: 8 }), ev("completed", "a", { ago: 2 })]).busy, false);
  assert.equal(inFlight([ev("queued", "a", { ago: 9 }), ev("failed", "a", { ago: 2 })]).busy, false);
  assert.equal(inFlight([ev("started", "x", { agent: "someone-else-pm" })]).busy, false, "per-scope isolation");
  assert.equal(inFlight([ev("started", "d", { reason: "ticket-delegation" })]).busy, false, "an implementation turn is not a board turn");
  const stale = inFlight([ev("queued", "s", { ago: MAX_OPEN_TRIAGE_MS / 60000 + 1 })]);
  assert.equal(stale.busy, false, "no end on record after 3 hours: presumed dead");
  assert.match(stale.why, /no board turn/);
});

test("boardTurnsInFlight: krebs's own journalled send counts before the gateway has said a word, and not once it ended", () => {
  const sent = [{ commandId: "k1", at: minsAgo(1), kind: "triage", key: "OTH-3" }];
  const v = inFlight([], { sent });
  assert.equal(v.busy, true);
  assert.deepEqual(v.turns.map((x) => [x.id, x.state]), [["k1", "sent"]]);
  assert.equal(inFlight([ev("completed", "k1", { ago: 0.5 })], { sent }).busy, false);
  assert.equal(inFlight([ev("queued", "k1", { ago: 0.9 })], { sent }).turns[0].state, "queued", "one turn, not a duplicate");
  assert.equal(inFlight([ev("queued", "k1", { ago: 0.9 })], { sent }).turns.length, 1);
});

test("candystoreScopeBusy: one Candystore question per tick for every scope, and unknown when it cannot answer", async () => {
  let asked = 0;
  const client = { boardTurns: async () => (asked++, [ev("started", "a"), ev("started", "z", { agent: "z-pm" })]) };
  const probe = candystoreScopeBusy({ client, now: () => NOW });
  assert.equal((await probe({ scope: { agentId: AGENT }, sent: [] })).busy, true);
  assert.equal((await probe({ scope: { agentId: "z-pm" }, sent: [] })).busy, true);
  assert.equal((await probe({ scope: { agentId: "idle-pm" }, sent: [] })).busy, false);
  assert.equal(asked, 1);
  const down = candystoreScopeBusy({ client: { boardTurns: async () => { throw new Error("connect ECONNREFUSED"); } }, now: () => NOW });
  const v = await down({ scope: { agentId: AGENT }, sent: [] });
  assert.equal(v.unknown, true);
  assert.match(v.why, /ECONNREFUSED/);
  const capped = candystoreScopeBusy({ client: { boardTurns: async () => Array.from({ length: 1000 }, (_, i) => ev("queued", `n${i}`, { agent: "q" })) }, now: () => NOW });
  assert.equal((await capped({ scope: { agentId: AGENT }, sent: [] })).unknown, true, "a truncated read cannot prove the scope idle");
});

function setup({ issues, scopeBusy, journal = new MemoryJournal() }) {
  const plane = new FakePlane({ [OTHER]: { issues } });
  const registry = registryFixture();
  const { scopes, skipped } = scopesFromRegistry(registry, { activation: bbRegistry.bloodbankActivation, executionMode: () => "legacy", board: "OTH" });
  const publish = fakePublisher();
  const idle = async () => ({ live: false, why: "nothing since", lastEnd: null });
  const run = () => runTick({ registry, scopes, skipped, plane, fleet, nats, publish, journal, now: () => NOW, timeZone: "America/New_York", liveness: idle, scopeBusy });
  return { publish, run };
}
const todo = (seq) => issue({ seq, state: "todo", labels: [], updated: OLD });
const handedBack = (seq) => issue({ seq, state: "ip", labels: ["lifecycle:triaged", "lifecycle:review"], updated: OLD });
const busyNow = async () => boardTurnsInFlight({ events: [ev("started", "run1", { key: "OTH-1" })], agentId: AGENT, nowMs: NOW_MS });

test("runTick: a scope with a board turn in flight sends no triage, and says why", async () => {
  const { publish, run } = setup({ issues: [todo(2), todo(3)], scopeBusy: busyNow });
  const report = await run();
  assert.equal(publish.sent.length, 0);
  const s = report.scopes[0];
  assert.deepEqual(s.triage.map((x) => [x.key, x.result]), [["OTH-2", "skipped"], ["OTH-3", "skipped"]]);
  assert.match(s.triage[0].why, /scope busy: a triage turn on OTH-1 is running/);
  assert.equal(s.boardTurnBusy.turns[0].invocationId, "run1");
});

test("runTick: an in-flight triage also blocks a review (one board turn of either kind)", async () => {
  const { publish, run } = setup({ issues: [handedBack(4)], scopeBusy: busyNow });
  const report = await run();
  assert.equal(publish.sent.length, 0);
  assert.deepEqual(report.scopes[0].reviews.map((x) => [x.key, x.result]), [["OTH-4", "skipped"]]);
  assert.match(report.scopes[0].reviews[0].why, /scope busy/);
});

test("runTick: an idle scope still sends exactly one board turn per tick, and the probe sees the scope and what krebs sent", async () => {
  const seen = [];
  const { publish, run } = setup({ issues: [todo(2), todo(3)], scopeBusy: async (arg) => (seen.push(arg), { busy: false, turns: [], why: "none" }) });
  const report = await run();
  assert.equal(publish.sent.length, 1);
  assert.equal(report.scopes[0].triage.filter((x) => x.result === "published").length, 1);
  assert.equal(seen.length, 1, "asked once per scope");
  assert.equal(seen[0].scope.agentId, AGENT);
  assert.deepEqual(seen[0].sent, []);
});

test("runTick: per-scope isolation, only this scope's own turns hold it", async () => {
  const probe = async ({ scope }) => boardTurnsInFlight({ events: [ev("started", "r", { agent: "another-pm" })], agentId: scope.agentId, nowMs: NOW_MS });
  const { publish, run } = setup({ issues: [todo(2)], scopeBusy: probe });
  await run();
  assert.equal(publish.sent.length, 1);
});

test("runTick: Candystore unknown sends no board turn and warns", async () => {
  const { publish, run } = setup({ issues: [todo(2)], scopeBusy: async () => ({ unknown: true, why: "Candystore unreachable" }) });
  const report = await run();
  assert.equal(publish.sent.length, 0);
  assert.equal(report.scopes[0].triage[0].result, "skipped");
  assert.ok(report.scopes[0].warnings.some((w) => /board turns not sent: Candystore unreachable/.test(w)));
});

test("runTick: the probe is not asked when the scope has no board-turn candidate", async () => {
  let asked = 0;
  const { run } = setup({ issues: [issue({ seq: 7, state: "done", labels: [], updated: OLD }), issue({ seq: 8, state: "backlog", labels: [], updated: OLD })], scopeBusy: async () => (asked++, { busy: false, turns: [], why: "" }) });
  await run();
  assert.equal(asked, 0);
});

test("back-to-back runs (krebs watch): the second run sees the first run's send through the journal while Candystore lags, and the turn's end frees the scope", async () => {
  // Integrated: the real Candystore probe and the real journal, no stubbed verdicts. A second run starting the
  // moment the first ends must not send a second board turn to the desk, whatever Candystore has ingested.
  const journal = new MemoryJournal();
  let events = []; // Candystore: nothing ingested yet
  const client = { boardTurns: async () => events };
  let clock = NOW_MS;
  const now = () => new Date(clock);
  const plane = new FakePlane({ [OTHER]: { issues: [todo(2), todo(3)] } });
  const registry = registryFixture();
  const { scopes, skipped } = scopesFromRegistry(registry, { activation: bbRegistry.bloodbankActivation, executionMode: () => "legacy", board: "OTH" });
  const publish = fakePublisher();
  const idle = async () => ({ live: false, why: "nothing since", lastEnd: null });
  const run = () => runTick({ registry, scopes, skipped, plane, fleet, nats, publish, journal, now, timeZone: "America/New_York", liveness: idle, scopeBusy: candystoreScopeBusy({ client, now }) });

  const first = await run();
  assert.equal(publish.sent.length, 1, "first run: one triage");
  const sentKey = first.scopes[0].triage.find((x) => x.result === "published").key;
  const commandId = first.scopes[0].triage.find((x) => x.result === "published").commandId;

  clock += 10_000;
  const second = await run();
  assert.equal(publish.sent.length, 1, "second run: the desk already has one, nothing sent");
  assert.ok(second.scopes[0].triage.every((x) => x.result !== "published"));
  assert.match(second.scopes[0].boardTurnBusy.why, /triage turn on OTH-\d is sent/);

  events = [ev("queued", commandId, { key: sentKey, ago: -0.1 }), ev("started", commandId, { key: sentKey, ago: -0.1 })];
  clock += 4 * 60_000;
  await run();
  assert.equal(publish.sent.length, 1, "running: still one");

  events = [...events, ev("completed", commandId, { key: sentKey, ago: -4.5 })];
  clock += 60_000;
  const after = await run();
  assert.equal(publish.sent.length, 2, "ended: the next ticket's triage goes");
  assert.notEqual(after.scopes[0].triage.find((x) => x.result === "published").key, sentKey);
});

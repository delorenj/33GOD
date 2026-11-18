// spec orphans (33GOD-93): a ticket whose agent turn is over but that still
// holds a slot or carries agent:working is released or unstuck; a ticket with a
// live turn is never touched.

import { test } from "node:test";
import assert from "node:assert/strict";

import { loadBloodbank } from "../deps.mjs";
import { scopesFromRegistry } from "../registry.mjs";
import { ORPHAN_RELEASE_LIMIT, runTick } from "../run.mjs";
import { MemoryJournal } from "../journal.mjs";
import { laneModel } from "../lifecycle.mjs";
import { normalizeTicket, orphanKind } from "../select.mjs";
import { QUIET_MS, candystoreClient, candystoreLiveness, keyPattern, turnState } from "../liveness.mjs";
import { formatReport } from "../format.mjs";
import { FakePlane, LABEL_NAMES, NOW, SOLO, STATES, fakePublisher, issue, labelId, registryFixture } from "./helpers.mjs";

const { fleet, nats, registry: bbRegistry } = loadBloodbank();
const NOW_MS = NOW.getTime();
const minsAgo = (m) => new Date(NOW_MS - m * 60000).toISOString();
const OLD = minsAgo(120);

// other-pm owns OTHER (wip 2, no review); solo-pm owns SOLO (wip 1, review).
const OTHER = "b-other";

function setup({ issues, board = "OTH", boardId = OTHER, liveness, journal = new MemoryJournal() }) {
  const plane = new FakePlane({ [boardId]: { issues } });
  const registry = registryFixture();
  const { scopes, skipped } = scopesFromRegistry(registry, { activation: bbRegistry.bloodbankActivation, executionMode: () => "legacy", board });
  const publish = fakePublisher();
  const run = (over = {}) =>
    runTick({ registry, scopes, skipped, plane, fleet, nats, publish, journal, now: () => NOW, timeZone: "America/New_York", liveness, ...over });
  return { plane, publish, journal, run };
}

/** A liveness probe answering from a map of ticket key -> verdict (default idle). */
function probe(byKey = {}) {
  const calls = [];
  const fn = async ({ key, ticketId, boardId }) => {
    calls.push({ key, ticketId, boardId });
    return byKey[key] ?? { live: false, why: "last turn completed 2.0 h ago; nothing since", lastEnd: null };
  };
  fn.calls = calls;
  return fn;
}

const lanes = laneModel(STATES);
const labelNameOf = new Map(LABEL_NAMES.map((n) => [labelId(n), n]));
const t = (spec) => normalizeTicket(issue(spec), { lanes, labelNameOf, identifier: "T" });
const labelsOf = (plane, boardId, id) => plane.boards[boardId].issues.get(id).labels;
const stateOf = (plane, boardId, id) => plane.boards[boardId].issues.get(id).state;

test("orphanKind: which tickets are suspects, before asking about liveness", () => {
  const kind = (spec) => orphanKind(t({ updated: OLD, ...spec }), NOW_MS, QUIET_MS);
  assert.equal(kind({ seq: 1, state: "ip", labels: ["agent:working", "lifecycle:triaged"] }), "release", "GRUV-182 shape");
  assert.equal(kind({ seq: 2, state: "ip", labels: [] }), "release", "a pre-v2 In Progress ticket with no labels holds a slot too");
  assert.equal(kind({ seq: 3, state: "ip", labels: ["agent:working", "lifecycle:needs-input"] }), "stale-working", "held: no slot, stale label");
  assert.equal(kind({ seq: 4, state: "ip", labels: ["agent:working", "lifecycle:review"] }), "stale-working");
  assert.equal(kind({ seq: 5, state: "ip", labels: ["lifecycle:review"] }), null, "waiting on a verdict is not an orphan");
  assert.equal(kind({ seq: 6, state: "ip", labels: ["lifecycle:blocked"] }), null);
  assert.equal(kind({ seq: 7, state: "ip", labels: ["epic"] }), null, "an epic someone started keeps its slot");
  assert.equal(kind({ seq: 8, state: "ip", labels: ["epic", "agent:working"] }), "stale-working");
  assert.equal(kind({ seq: 9, state: "todo", labels: ["agent:working"] }), "stale-working", "a dead triage turn's label");
  assert.equal(kind({ seq: 10, state: "todo", labels: ["lifecycle:triaged"] }), null);
  assert.equal(kind({ seq: 11, state: "done", labels: ["agent:working"] }), null, "terminal tickets are the invariant repair's job");
  assert.equal(kind({ seq: 12, state: "ip", labels: ["agent:working"], updated: minsAgo(10) }), null, "updated in the quiet window: never second-guessed");
  assert.equal(kind({ seq: 13, state: "ip", labels: ["agent:working"], updated: minsAgo(30) }), null, "exactly 30 minutes is still quiet-window");
});

test("33GOD-93 reproduction: an In Progress ticket whose turn ended with no handback is released, and its slot refills in the same tick", async () => {
  const live = probe();
  const { plane, publish, journal, run } = setup({
    liveness: live,
    issues: [
      issue({ seq: 182, state: "ip", labels: ["agent:working", "lifecycle:triaged"], updated: OLD }),
      issue({ seq: 200, state: "ip", labels: ["agent:working", "lifecycle:triaged"], updated: OLD }),
      issue({ seq: 175, state: "todo", labels: ["lifecycle:triaged"], sort: 10, updated: OLD }),
    ],
  });
  const report = await run();
  const s = report.scopes[0];
  assert.deepEqual(s.orphans.map((o) => [o.key, o.kind, o.result]), [["OTH-182", "release", "released"], ["OTH-200", "release", "released"]]);
  // The release write: back to Todo, agent:working removed, nothing else.
  const release = plane.writes().find((w) => w.id === "i-182");
  assert.deepEqual([release.fields, release.addLabels, release.removeLabels], [{ state: "s-todo" }, [], [labelId("agent:working")]]);
  assert.ok(labelsOf(plane, OTHER, "i-182").includes(labelId("lifecycle:triaged")), "keeps lifecycle:triaged: it is not re-triaged");
  const comments = plane.calls.filter((c) => c.method === "comment");
  assert.equal(comments.length, 2);
  assert.match(comments[0].html, /moved this back to Todo/);
  // Both slots freed; the PM's Todo order decides what fills them.
  assert.equal(s.free, 2);
  assert.deepEqual(s.dispatches.map((d) => [d.key, d.result]), [["OTH-175", "dispatched"], ["OTH-182", "dispatched"]]);
  assert.equal(publish.sent.length, 2);
  const actions = journal.read().map((e) => [e.action, e.key, e.ok]).filter(([a]) => a.startsWith("orphan."));
  assert.deepEqual(actions, [["orphan.release", "OTH-182", true], ["orphan.release", "OTH-200", true]]);
});

test("a ticket with a live turn is never touched: no write, no comment, and it keeps its slot", async () => {
  const live = probe({ "OTH-1": { live: true, why: "turn abc started 40 min ago and has not ended" } });
  const { plane, run } = setup({
    liveness: live,
    issues: [
      issue({ seq: 1, state: "ip", labels: ["agent:working", "lifecycle:triaged"], updated: OLD }),
      issue({ seq: 2, state: "ip", labels: ["agent:working", "lifecycle:needs-input"], updated: OLD }),
    ],
  });
  const live2 = probe({ "OTH-1": { live: true, why: "x" }, "OTH-2": { live: true, why: "y" } });
  const report = await run({ liveness: live2 });
  const s = report.scopes[0];
  assert.deepEqual(s.orphans.map((o) => o.result), ["live", "live"]);
  assert.equal(plane.writes().length, 0);
  assert.equal(plane.calls.filter((c) => c.method === "comment").length, 0);
  assert.deepEqual(s.occupied, ["OTH-1"]);
  assert.equal(stateOf(plane, OTHER, "i-1"), "s-ip");
});

test("Candystore unreachable: hands off, with a warning, and the tick still succeeds", async () => {
  const { plane, run } = setup({
    liveness: async () => ({ unknown: true, why: "liveness unknown (fetch failed)" }),
    issues: [issue({ seq: 1, state: "ip", labels: ["agent:working"], updated: OLD })],
  });
  const report = await run();
  assert.equal(report.ok, true);
  assert.equal(plane.writes().length, 0);
  assert.equal(report.scopes[0].orphans[0].result, "unknown");
  assert.match(report.scopes[0].warnings.join("\n"), /liveness unknown/);
});

test("no liveness probe configured: nothing is released, and the report says so", async () => {
  const { plane, run } = setup({ liveness: null, issues: [issue({ seq: 1, state: "ip", labels: ["agent:working"], updated: OLD })] });
  const report = await run();
  assert.equal(plane.writes().length, 0);
  assert.match(report.scopes[0].warnings.join("\n"), /no liveness probe/);
});

test("stale agent:working on held, in-review and Todo tickets is removed; lanes and other labels stay", async () => {
  const { plane, run } = setup({
    liveness: probe(),
    issues: [
      issue({ seq: 3, state: "ip", labels: ["agent:working", "lifecycle:needs-input", "lifecycle:triaged"], updated: OLD }),
      issue({ seq: 4, state: "ip", labels: ["agent:working", "lifecycle:review"], updated: OLD }),
      issue({ seq: 9, state: "todo", labels: ["agent:working"], updated: OLD }),
    ],
  });
  const report = await run();
  assert.deepEqual(report.scopes[0].orphans.map((o) => [o.key, o.result]), [["OTH-3", "unstuck"], ["OTH-4", "unstuck"], ["OTH-9", "unstuck"]]);
  for (const id of ["i-3", "i-4", "i-9"]) assert.ok(!labelsOf(plane, OTHER, id).includes(labelId("agent:working")), id);
  assert.equal(stateOf(plane, OTHER, "i-3"), "s-ip");
  assert.equal(stateOf(plane, OTHER, "i-9"), "s-todo");
  assert.ok(labelsOf(plane, OTHER, "i-3").includes(labelId("lifecycle:needs-input")));
  // Both become board-turn candidates: the in-review ticket a review, the Todo one a triage.
  // One board turn per scope per tick, oldest first (same age: lower sequence), so the review goes first.
  assert.deepEqual(report.scopes[0].reviews.map((x) => x.key), ["OTH-4"]);
  assert.deepEqual(report.scopes[0].triageCapped.map((x) => x.key), ["OTH-9"]);
});

test("loop guard: a ticket already released twice this week is held with agent:failed instead", async () => {
  const journal = new MemoryJournal(
    Array.from({ length: ORPHAN_RELEASE_LIMIT }, (_, i) => ({ ts: minsAgo(600 + i * 60), action: "orphan.release", ok: true, ticket_id: "i-7", key: "OTH-7" })),
  );
  const { plane, run } = setup({ journal, liveness: probe(), issues: [issue({ seq: 7, state: "ip", labels: ["agent:working", "lifecycle:triaged"], updated: OLD })] });
  const report = await run();
  const s = report.scopes[0];
  assert.equal(s.orphans[0].result, "held");
  assert.equal(stateOf(plane, OTHER, "i-7"), "s-ip", "stays In Progress");
  assert.ok(labelsOf(plane, OTHER, "i-7").includes(labelId("agent:failed")));
  assert.ok(!labelsOf(plane, OTHER, "i-7").includes(labelId("agent:working")));
  assert.deepEqual(s.occupied, [], "a held ticket holds no slot");
  assert.match(plane.calls.find((c) => c.method === "comment").html, /agent:failed/);
});

test("releases older than the loop window do not count", async () => {
  const journal = new MemoryJournal([
    { ts: minsAgo(8 * 24 * 60), action: "orphan.release", ok: true, ticket_id: "i-7" },
    { ts: minsAgo(9 * 24 * 60), action: "orphan.release", ok: true, ticket_id: "i-7" },
  ]);
  const { run } = setup({ journal, liveness: probe(), issues: [issue({ seq: 7, state: "ip", labels: ["agent:working"], updated: OLD })] });
  const report = await run();
  assert.equal(report.scopes[0].orphans[0].result, "released");
});

test("release re-reads live: a ticket handed back since the listing is left alone", async () => {
  const { plane, run } = setup({ liveness: probe(), issues: [issue({ seq: 5, state: "ip", labels: ["agent:working"], updated: OLD })] });
  const realIssue = plane.issue.bind(plane);
  plane.issue = async (id, ws, board) => {
    const row = await realIssue(id, ws, board);
    return { ...row, labels: [...row.labels, labelId("lifecycle:review")] };
  };
  const report = await run();
  assert.equal(report.scopes[0].orphans[0].result, "skipped");
  assert.equal(plane.writes().length, 0);
});

test("per-scope release cap: the rest wait for the next tick", async () => {
  const { plane, run } = setup({
    liveness: probe(),
    issues: [1, 2, 3].map((seq) => issue({ seq, state: "ip", labels: [], updated: OLD })),
  });
  const report = await run();
  assert.deepEqual(report.scopes[0].orphans.map((o) => o.result), ["released", "released", "capped"]);
  assert.equal(plane.writes().filter((w) => w.fields.state === "s-todo").length, 2);
});

test("dry run plans the orphan work, writes nothing, journals nothing, and shows it in the summary", async () => {
  const journal = new MemoryJournal();
  const { plane, publish, run } = setup({
    journal,
    liveness: probe(),
    issues: [
      issue({ seq: 1, state: "ip", labels: ["agent:working", "lifecycle:triaged"], updated: OLD }),
      issue({ seq: 2, state: "ip", labels: ["agent:working", "lifecycle:blocked"], updated: OLD }),
    ],
  });
  const report = await run({ dryRun: true });
  assert.deepEqual(report.scopes[0].orphans.map((o) => [o.key, o.result, o.action]), [
    ["OTH-1", "planned", "-> Todo -agent:working"],
    ["OTH-2", "planned", "-agent:working"],
  ]);
  assert.equal(plane.writes().length, 0);
  assert.equal(publish.sent.length, 0);
  assert.equal(journal.read().length, 0);
  assert.deepEqual(report.scopes[0].dispatches.map((d) => [d.key, d.result]), [["OTH-1", "planned"]], "the freed slot shows in the plan");
  const text = formatReport(report);
  assert.match(text, /orphan: OTH-1 -> Todo -agent:working planned/);
});

test("the ticket's routing decides who probes it: the probe gets the board and ticket id", async () => {
  const live = probe();
  const { run } = setup({ board: "SOLO", boardId: SOLO, liveness: live, issues: [issue({ seq: 1, state: "ip", labels: ["agent:working"], updated: OLD })] });
  await run({ dryRun: true });
  assert.deepEqual(live.calls, [{ key: "SOLO-1", ticketId: "i-1", boardId: SOLO }]);
});

// ---- turnState: the Candystore verdict ----

const ev = (type, minutes, extra = {}) => ({ type, time: minsAgo(minutes), domain: type.split(".")[1], data: { invocation_id: extra.id ?? "inv-1", ...extra.data }, ...extra.top });

test("turnState: an invocation started and not ended is live", () => {
  const v = turnState({ key: "GRUV-219", nowMs: NOW_MS, correlated: [ev("bloodbank.agent.invocation.started", 90)] });
  assert.equal(v.live, true);
  assert.match(v.why, /has not ended/);
});

test("turnState: started then completed, nothing in the last 30 minutes, is idle", () => {
  const v = turnState({
    key: "GRUV-219",
    nowMs: NOW_MS,
    correlated: [ev("bloodbank.agent.invocation.started", 300), ev("bloodbank.agent.invocation.completed", 180), ev("bloodbank.conversation.turn.completed", 180)],
  });
  assert.equal(v.live, false);
  assert.match(v.why, /last turn completed 3\.0 h ago/);
  assert.equal(v.lastEnd.type, "completed");
});

test("turnState: a failed turn is over too", () => {
  const v = turnState({ key: "X-1", nowMs: NOW_MS, correlated: [ev("bloodbank.agent.invocation.started", 200), ev("bloodbank.agent.invocation.failed", 100)] });
  assert.equal(v.live, false);
  assert.match(v.why, /failed/);
});

test("turnState: an open turn past the 8 hour limit is presumed dead", () => {
  const v = turnState({ key: "X-1", nowMs: NOW_MS, correlated: [ev("bloodbank.agent.invocation.started", 9 * 60)] });
  assert.equal(v.live, false);
});

test("turnState: a detached turn is live for a day (its worker may still run)", () => {
  const correlated = [ev("bloodbank.agent.invocation.started", 600), ev("bloodbank.agent.invocation.detached", 590)];
  assert.equal(turnState({ key: "X-1", nowMs: NOW_MS, correlated }).live, true);
});

test("turnState: an older turn ended but a second turn on the ticket is still open", () => {
  const correlated = [
    ev("bloodbank.agent.invocation.started", 300, { id: "a" }),
    ev("bloodbank.agent.invocation.completed", 250, { id: "a" }),
    ev("bloodbank.agent.invocation.started", 60, { id: "b" }),
  ];
  assert.equal(turnState({ key: "X-1", nowMs: NOW_MS, correlated }).live, true);
});

test("turnState: agent activity on the ticket in the last 30 minutes is live; Plane webhook echoes and skips are not activity", () => {
  const recent = turnState({ key: "X-1", nowMs: NOW_MS, correlated: [ev("bloodbank.agent.invocation.completed", 10)] });
  assert.equal(recent.live, true, "a turn that just ended is inside the quiet window");
  const echoes = turnState({
    key: "X-1",
    nowMs: NOW_MS,
    correlated: [
      ev("bloodbank.agent.invocation.completed", 200),
      { type: "bloodbank.repo.task.appended", domain: "repo", time: minsAgo(5), data: {} },
      { type: "bloodbank.agent.invocation.skipped", domain: "agent", time: minsAgo(5), data: {} },
    ],
  });
  assert.equal(echoes.live, false, "a comment by a person is not an agent turn");
});

test("turnState: a coding worker in a worktree named for the ticket is live; a different ticket's worktree is not", () => {
  const worker = (wd, minutes, cli = "codex") => ({ type: "bloodbank.agent.tool.completed", domain: "agent", time: minsAgo(minutes), actor: { cli }, data: { working_directory: wd } });
  const base = { key: "GRUV-21", nowMs: NOW_MS, correlated: [ev("bloodbank.agent.invocation.completed", 200)] };
  assert.equal(turnState({ ...base, mentions: [worker("/home/x/code/gruvato/.worktrees/gruv-21-fix", 5)] }).live, true);
  assert.equal(turnState({ ...base, mentions: [worker("/home/x/code/gruvato/.worktrees/gruv-219-fix", 5)] }).live, false, "GRUV-21 is not GRUV-219");
  assert.equal(turnState({ ...base, mentions: [worker("/home/x/code/gruvato/.worktrees/gruv-21-fix", 45)] }).live, false, "older than the quiet window");
  assert.equal(
    turnState({ ...base, mentions: [{ type: "bloodbank.repo.task.appended", domain: "repo", time: minsAgo(5), data: { body: "see gruv-21" } }] }).live,
    false,
    "a mention that is not a worker",
  );
});

test("keyPattern matches the key as a whole token", () => {
  const p = keyPattern("TOLT-84");
  assert.ok(p.test("/x/.worktrees/lane-story-tolt-84-landing-entry"));
  assert.ok(p.test("/x/tolt-84"));
  assert.ok(!p.test("/x/tolt-841-other"));
  assert.ok(!p.test("/x/xtolt-84"));
});

test("candystoreLiveness queries by the ticket's correlation id and turns errors into unknown", async () => {
  const urls = [];
  const fetchImpl = async (url) => {
    urls.push(url);
    return { ok: true, json: async () => ({ events: [] }) };
  };
  const live = candystoreLiveness({ client: candystoreClient({ base: "http://cs:1/", fetchImpl }), fleet, now: () => NOW });
  const v = await live({ boardId: "b1", ticketId: "t1", key: "OTH-1" });
  assert.equal(v.live, false);
  assert.match(v.why, /no agent turn/);
  const cid = fleet.ticketCorrelationId("b1", "t1");
  assert.ok(urls.some((u) => u.startsWith("http://cs:1/events?") && u.includes(`correlationid=${cid}`)), urls.join("\n"));
  assert.ok(urls.some((u) => u.includes("q=oth-1")));

  const down = candystoreLiveness({ client: candystoreClient({ base: "http://cs:1", fetchImpl: async () => ({ ok: false, status: 502, json: async () => ({}) }) }), fleet, now: () => NOW });
  const u = await down({ boardId: "b1", ticketId: "t1", key: "OTH-1" });
  assert.equal(u.unknown, true);
  assert.match(u.why, /502/);
});

// ---- the queued blind spot: krebs's own commands ----

test("turnState: a command krebs sent with no start yet (queued for a gateway slot) is live", () => {
  const v = turnState({ key: "X-1", nowMs: NOW_MS, correlated: [], sent: [{ commandId: "c1", at: minsAgo(50), kind: "dispatch" }] });
  assert.equal(v.live, true);
  assert.match(v.why, /queued or running/);
});

test("turnState: a sent command whose end is on record no longer counts; caps differ for dispatch and triage", () => {
  const ended = turnState({
    key: "X-1",
    nowMs: NOW_MS,
    correlated: [ev("bloodbank.agent.invocation.started", 100, { id: "c1" }), ev("bloodbank.agent.invocation.completed", 60, { id: "c1" })],
    sent: [{ commandId: "c1", at: minsAgo(110), kind: "dispatch" }],
  });
  assert.equal(ended.live, false);
  assert.equal(turnState({ key: "X-1", nowMs: NOW_MS, sent: [{ commandId: "c2", at: minsAgo(4 * 60), kind: "triage" }] }).live, false, "triage cap is 3 h");
  assert.equal(turnState({ key: "X-1", nowMs: NOW_MS, sent: [{ commandId: "c3", at: minsAgo(4 * 60), kind: "dispatch" }] }).live, true, "dispatch cap is 8 h");
  assert.equal(turnState({ key: "X-1", nowMs: NOW_MS, sent: [{ commandId: "c4", at: minsAgo(9 * 60), kind: "dispatch" }] }).live, false);
});

test("sentCommands folds the journal: published dispatches (via their intent) and published triages, per ticket", async () => {
  const { sentCommands } = await import("../journal.mjs");
  const m = sentCommands([
    { ts: "t0", action: "dispatch.intent", dispatch_id: "d1", command_id: "c1", ticket_id: "i-1" },
    { ts: "t1", action: "dispatch.write", dispatch_id: "d1", ok: true },
    { ts: "t2", action: "dispatch.publish", dispatch_id: "d1", command_id: "c1", ok: true },
    { ts: "t3", action: "dispatch.intent", dispatch_id: "d2", command_id: "c2", ticket_id: "i-2" },
    { ts: "t4", action: "dispatch.publish", dispatch_id: "d2", command_id: "c2", ok: false },
    { ts: "t5", action: "triage.publish", command_id: "c3", ticket_id: "i-1", ok: true },
  ]);
  assert.deepEqual(m.get("i-1"), [{ commandId: "c1", at: "t2", kind: "dispatch" }, { commandId: "c3", at: "t5", kind: "triage" }]);
  assert.equal(m.get("i-2"), undefined, "a failed publish sent nothing");
});

test("runTick hands the probe the commands krebs sent for that ticket", async () => {
  const journal = new MemoryJournal([
    { ts: minsAgo(45), action: "dispatch.intent", dispatch_id: "d1", command_id: "c1", ticket_id: "i-1" },
    { ts: minsAgo(45), action: "dispatch.publish", dispatch_id: "d1", command_id: "c1", ok: true },
  ]);
  const seen = [];
  const { plane, run } = setup({
    journal,
    liveness: async (q) => {
      seen.push(q);
      return turnState({ key: q.key, nowMs: NOW_MS, sent: q.sent });
    },
    issues: [issue({ seq: 1, state: "ip", labels: ["agent:working", "lifecycle:triaged"], updated: minsAgo(45) })],
  });
  const report = await run();
  assert.equal(seen[0].sent[0].commandId, "c1");
  assert.equal(report.scopes[0].orphans[0].result, "live", "dispatched 45 min ago and still queued: hands off");
  assert.equal(plane.writes().length, 0);
});

test("orphanKind: a stale agent:working in Backlog is a suspect too", () => {
  assert.equal(orphanKind(t({ seq: 30, state: "backlog", labels: ["agent:working"], updated: OLD }), NOW_MS, QUIET_MS), "stale-working");
  assert.equal(orphanKind(t({ seq: 31, state: "backlog", labels: [], updated: OLD }), NOW_MS, QUIET_MS), null);
});

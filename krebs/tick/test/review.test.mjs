// spec catch_up.review: a ticket handed back with lifecycle:review gets a review
// turn from its scope's PM (the verdict giver), and spec hold lifecycle:human:
// the owner's own hold, which no krebs path ever touches.

import { test } from "node:test";
import assert from "node:assert/strict";

import { loadBloodbank } from "../deps.mjs";
import { scopesFromRegistry } from "../registry.mjs";
import { REVIEW_MAX_ATTEMPTS, REVIEW_REASON, REVIEW_RETRY_MS, runTick } from "../run.mjs";
import { MemoryJournal, reviewAttempts, sentCommands } from "../journal.mjs";
import { HOLD_LABELS, laneModel } from "../lifecycle.mjs";
import { dispatchGuard, normalizeTicket, occupies, orphanKind, reviewGuard, triageGuard } from "../select.mjs";
import { QUIET_MS } from "../liveness.mjs";
import { formatReport } from "../format.mjs";
import { FakePlane, LABEL_NAMES, NOW, STATES, fakePublisher, issue, labelId, registryFixture } from "./helpers.mjs";

const { fleet, nats, registry: bbRegistry } = loadBloodbank();
const NOW_MS = NOW.getTime();
const minsAgo = (m) => new Date(NOW_MS - m * 60000).toISOString();
const OLD = minsAgo(120);
const OTHER = "b-other";

function setup({ issues, liveness, journal = new MemoryJournal() }) {
  const plane = new FakePlane({ [OTHER]: { issues } });
  const registry = registryFixture();
  const { scopes, skipped } = scopesFromRegistry(registry, { activation: bbRegistry.bloodbankActivation, executionMode: () => "legacy", board: "OTH" });
  const publish = fakePublisher();
  const run = (over = {}) =>
    runTick({ registry, scopes, skipped, plane, fleet, nats, publish, journal, now: () => NOW, timeZone: "America/New_York", liveness, ...over });
  return { plane, publish, journal, run };
}

const idle = async () => ({ live: false, why: "last turn completed 2.0 h ago; nothing since", lastEnd: null });
const lanes = laneModel(STATES);
const labelNameOf = new Map(LABEL_NAMES.map((n) => [labelId(n), n]));
const t = (spec) => normalizeTicket(issue(spec), { lanes, labelNameOf, identifier: "T" });

test("reviewGuard: only a quiet, unheld In Progress ticket handed back with lifecycle:review", () => {
  const g = (spec) => reviewGuard(t({ updated: OLD, ...spec }), NOW_MS);
  assert.equal(g({ seq: 1, state: "ip", labels: ["lifecycle:review"] }), null);
  assert.match(g({ seq: 2, state: "ip", labels: [] }), /not handed back/);
  assert.match(g({ seq: 3, state: "todo", labels: ["lifecycle:review"] }), /not In Progress/);
  assert.match(g({ seq: 4, state: "ip", labels: ["lifecycle:review", "lifecycle:needs-input"] }), /held/);
  assert.match(g({ seq: 5, state: "ip", labels: ["lifecycle:review", "agent:working"] }), /agent:working/);
  assert.match(g({ seq: 6, state: "ip", labels: ["lifecycle:review", "epic"] }), /epic/);
  assert.match(g({ seq: 7, state: "ip", labels: ["lifecycle:review"], updated: minsAgo(10) }), /30 minutes/);
  assert.match(g({ seq: 8, state: "ip", labels: ["lifecycle:review", "lifecycle:human"] }), /held \(lifecycle:human\)/);
});

test("a handed-back ticket gets one review turn to its scope's PM: reason ticket-review, verdict prompt, journaled", async () => {
  const { publish, journal, run } = setup({ liveness: idle, issues: [issue({ seq: 4, state: "ip", labels: ["lifecycle:triaged", "lifecycle:review"], updated: OLD })] });
  const report = await run();
  assert.equal(report.ok, true, JSON.stringify(report.scopes[0].errors));
  const s = report.scopes[0];
  assert.deepEqual(s.reviews.map((r) => [r.key, r.result, r.attempt]), [["OTH-4", "published", 1]]);
  assert.equal(publish.sent.length, 1);
  const cmd = publish.sent[0];
  assert.equal(cmd.data.context.reason, REVIEW_REASON);
  assert.equal(cmd.data.context.dispatcher, "krebs-tick");
  assert.equal(cmd.data.target_agent_id, s.agentId);
  assert.equal(cmd.correlationId, fleet.ticketCorrelationId(OTHER, "i-4"));
  assert.match(cmd.data.prompt, /verdict giver/);
  assert.match(cmd.data.prompt, /px close/);
  assert.match(cmd.data.prompt, /returned:/);
  assert.match(cmd.data.prompt, /reviewer is never the implementer/);
  nats.validateEnvelope(cmd.type, nats.buildEnvelope(cmd).envelope);
  const rec = journal.read().find((e) => e.action === "review.publish");
  assert.equal(rec.ok, true);
  assert.equal(rec.attempt, 1);
  assert.equal(rec.ticket_id, "i-4");
  // liveness rule 0 counts a sent review as a queued turn, with the short cap
  assert.deepEqual(sentCommands(journal.read()).get("i-4").map((c) => c.kind), ["review"]);
  assert.match(formatReport(report), /review: OTH-4 published/);
});

test("a review is sent again after the cool-down, and at most REVIEW_MAX_ATTEMPTS times per episode, whatever the ticket version", async () => {
  const spec = { seq: 4, state: "ip", labels: ["lifecycle:review"], updated: OLD };
  const at = (m, attempt, version = OLD) => ({ ts: minsAgo(m), action: "review.publish", ok: true, ticket_id: "i-4", ticket_updated_at: version, attempt, command_id: `c${attempt}` });

  const recent = await setup({ liveness: idle, journal: new MemoryJournal([at(30, 1)]), issues: [issue(spec)] }).run();
  assert.deepEqual(recent.scopes[0].reviews, []);
  assert.match(recent.scopes[0].reviewsSeen[0].why, /review turn sent 30 min ago/);

  const cooled = setup({ liveness: idle, journal: new MemoryJournal([at(REVIEW_RETRY_MS / 60000 + 5, 1)]), issues: [issue(spec)] });
  const second = await cooled.run();
  assert.deepEqual(second.scopes[0].reviews.map((r) => [r.result, r.attempt]), [["published", 2]]);
  assert.notEqual(cooled.publish.sent[0].commandId, "c1");

  const spent = Array.from({ length: REVIEW_MAX_ATTEMPTS }, (_, i) => at(1000 + i, i + 1));
  const done = setup({ liveness: idle, journal: new MemoryJournal(spent), issues: [issue(spec)] });
  const doneReport = await done.run();
  assert.deepEqual(doneReport.scopes[0].reviews, []);
  assert.match(doneReport.scopes[0].reviewsSeen[0].why, /ended without a verdict/);
  assert.deepEqual(doneReport.scopes[0].parks.map((p) => [p.key, p.result]), [["OTH-4", "parked"]], "the cap parks the ticket instead of asking again");

  // The pickup chip rewrites updated_at after every turn, so each send is at a different version.
  // That must NOT reset the count (33GOD-33: 50 turns, every one "attempt 1").
  const churned = Array.from({ length: REVIEW_MAX_ATTEMPTS }, (_, i) => at(1000 + i, 1, minsAgo(2000 - i * 100)));
  const same = await setup({ liveness: idle, journal: new MemoryJournal(churned), issues: [issue({ ...spec, updated: minsAgo(60) })] }).run();
  assert.deepEqual(same.scopes[0].reviews, []);
  assert.deepEqual(same.scopes[0].parks.map((p) => p.result), ["parked"]);
  assert.equal(reviewAttempts(spent).get(`i-4|${OLD}`).length, REVIEW_MAX_ATTEMPTS);
});

test("a live turn on the ticket (the implementer still at it) holds the review back; unknown liveness too", async () => {
  const live = async () => ({ live: true, why: "turn x started 5 min ago and has not ended" });
  const r1 = await setup({ liveness: live, issues: [issue({ seq: 4, state: "ip", labels: ["lifecycle:review"], updated: OLD })] }).run();
  assert.deepEqual(r1.scopes[0].reviews.map((r) => [r.result, r.why]), [["skipped", "turn live: turn x started 5 min ago and has not ended"]]);
  const unknown = async () => ({ unknown: true, why: "liveness unknown (candystore 502)" });
  const r2 = await setup({ liveness: unknown, issues: [issue({ seq: 4, state: "ip", labels: ["lifecycle:review"], updated: OLD })] }).run();
  assert.equal(r2.scopes[0].reviews[0].result, "skipped");
  assert.ok(r2.scopes[0].warnings.some((w) => /review not sent/.test(w)));
});

test("one board turn per scope per tick: the scope alternates triage and review, oldest first within a kind", async () => {
  const issues = [
    issue({ seq: 1, state: "todo", labels: [], updated: minsAgo(300) }),
    issue({ seq: 2, state: "ip", labels: ["lifecycle:review"], updated: minsAgo(600) }),
    issue({ seq: 3, state: "ip", labels: ["lifecycle:review"], updated: minsAgo(100) }),
  ];
  // Nothing on record: triage first, even though the review is older (a review backlog never starves triage).
  const first = setup({ liveness: idle, issues });
  const s1 = (await first.run()).scopes[0];
  assert.deepEqual(s1.triage.map((r) => r.key), ["OTH-1"]);
  assert.deepEqual(s1.reviewsCapped.map((r) => r.key), ["OTH-2", "OTH-3"]);
  assert.equal(first.publish.sent.length, 1);
  // The last board turn was a triage: this tick the oldest review goes.
  const journal = new MemoryJournal([{ action: "triage.publish", ok: true, agent_id: first.publish.sent[0].data.target_agent_id, board_id: first.publish.sent[0].data.context.board_id, ticket_id: "x", command_id: "c-x", ts: minsAgo(10) }]);
  const second = setup({ liveness: idle, issues, journal });
  const s2 = (await second.run()).scopes[0];
  assert.deepEqual(s2.reviews.map((r) => r.key), ["OTH-2"]);
  assert.deepEqual(s2.triageCapped.map((r) => r.key), ["OTH-1"]);
});

test("dry run plans a review and sends nothing", async () => {
  const { publish, journal, run } = setup({ liveness: idle, issues: [issue({ seq: 4, state: "ip", labels: ["lifecycle:review"], updated: OLD })] });
  const report = await run({ dryRun: true });
  assert.equal(report.scopes[0].reviews[0].result, "planned");
  assert.equal(publish.sent.length, 0);
  assert.equal(journal.read().length, 0);
});

test("lifecycle:human is a hold: never dispatched, triaged, reviewed or released, and holds no slot", async () => {
  assert.ok(HOLD_LABELS.includes("lifecycle:human"));
  const h = (spec) => t({ updated: OLD, ...spec, labels: [...(spec.labels ?? []), "lifecycle:human"] });
  assert.match(dispatchGuard(h({ seq: 1, state: "todo", labels: ["lifecycle:triaged"] })), /held \(lifecycle:human\)/);
  assert.match(triageGuard(h({ seq: 2, state: "todo" }), NOW_MS), /held/);
  assert.equal(occupies(h({ seq: 3, state: "ip" })), false);
  assert.equal(orphanKind(h({ seq: 4, state: "ip" }), NOW_MS, QUIET_MS), null, "the owner working it by hand is not an orphan");

  let probed = 0;
  const { plane, publish, run } = setup({
    liveness: async () => { probed++; return { live: false, why: "idle" }; },
    issues: [
      issue({ seq: 1, state: "todo", labels: ["lifecycle:triaged", "lifecycle:human"], updated: OLD }),
      issue({ seq: 2, state: "todo", labels: ["lifecycle:human"], updated: OLD }),
      issue({ seq: 3, state: "ip", labels: ["lifecycle:human"], updated: OLD }),
      issue({ seq: 4, state: "ip", labels: ["lifecycle:review", "lifecycle:human"], updated: OLD }),
    ],
  });
  const s = (await run()).scopes[0];
  assert.deepEqual([s.dispatches, s.triage, s.reviews, s.orphans, s.occupied], [[], [], [], [], []]);
  assert.equal(probed, 0);
  assert.equal(publish.sent.length, 0);
  assert.equal(plane.writes().length, 0);
});

test("a board-turn candidate with a turn already queued or running is skipped, and the next oldest takes the turn", async () => {
  const busy = new Set(["OTH-1"]);
  const { publish, run } = setup({
    liveness: async ({ key }) => (busy.has(key) ? { live: true, why: "agent activity on the ticket 3 min ago" } : { live: false, why: "idle" }),
    issues: [
      issue({ seq: 1, state: "todo", labels: [], updated: minsAgo(300) }),
      issue({ seq: 2, state: "todo", labels: [], updated: minsAgo(200) }),
      issue({ seq: 3, state: "ip", labels: ["lifecycle:review"], updated: minsAgo(100) }),
    ],
  });
  const s = (await run()).scopes[0];
  assert.deepEqual(s.triage.map((r) => [r.key, r.result]), [["OTH-1", "skipped"], ["OTH-2", "published"]]);
  assert.match(s.triage[0].why, /^turn live:/);
  assert.deepEqual(s.reviewsCapped.map((r) => r.key), ["OTH-3"]);
  assert.equal(publish.sent.length, 1);
});

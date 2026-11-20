// Board-turn loops: a review or triage turn that ends with no outcome must be asked again a
// bounded number of times PER EPISODE, then parked. The 33GOD-33 replay is the regression:
// the pickup chip rewrites updated_at on every turn, which used to make each send "attempt 1".

import { test } from "node:test";
import assert from "node:assert/strict";

import { loadBloodbank } from "../deps.mjs";
import { scopesFromRegistry } from "../registry.mjs";
import { LOOP_PARK_TICK_CAP, REVIEW_MAX_ATTEMPTS, REVIEW_RETRY_MS, TRIAGE_MAX_ATTEMPTS, TRIAGE_RETRY_MS, runTick } from "../run.mjs";
import { MemoryJournal, boardTurnSends } from "../journal.mjs";
import { activitiesOf, episodeStartMs } from "../episode.mjs";
import { judgeBoardTurn, parkComment } from "../turns.mjs";
import { FakePlane, NOW, fakePublisher, issue, labelId, registryFixture } from "./helpers.mjs";

const { fleet, nats, registry: bbRegistry } = loadBloodbank();
const OTHER = "b-other";
const MIN = 60000;
const at = (ms) => new Date(ms).toISOString();
const idle = async () => ({ live: false, why: "last turn completed 2.0 h ago; nothing since" });

function setup({ issues, journal = new MemoryJournal() }) {
  const plane = new FakePlane({ [OTHER]: { issues } });
  const registry = registryFixture();
  const { scopes, skipped } = scopesFromRegistry(registry, { activation: bbRegistry.bloodbankActivation, executionMode: () => "legacy", board: "OTH" });
  const publish = fakePublisher();
  const run = (nowMs, over = {}) =>
    runTick({ registry, scopes, skipped, plane, fleet, nats, publish, journal, now: () => new Date(nowMs), timeZone: "America/New_York", liveness: idle, ...over });
  return { plane, publish, journal, run };
}

const label = (name, { add = true, ms }) => ({ created_at: at(ms), verb: "updated", field: "labels", old_value: add ? "" : name, new_value: add ? name : "" });
const state = (from, to, ms) => ({ created_at: at(ms), verb: "updated", field: "state", old_value: from, new_value: to });
const chip = (ms) => [label("agent:working", { add: true, ms }), label("agent:working", { add: false, ms: ms + 5 * MIN })];

/**
 * Replay the 33GOD-33 pattern: a handed-back ticket whose every review turn ends with no verdict and
 * leaves only the pickup chip behind (agent:working added, then removed five minutes later), so
 * updated_at is new each time. Ticks run every 10 minutes for `hours`.
 */
async function replayReviewLoop({ hours, journal = new MemoryJournal() }) {
  const handback = NOW.getTime() - 60 * MIN;
  const row = issue({ seq: 33, state: "ip", labels: ["lifecycle:triaged", "lifecycle:review"], updated: at(handback) });
  const env = setup({ issues: [row], journal });
  env.plane.activity["i-33"] = [state("E2E Testing & QA", "In Progress", handback), label("lifecycle:review", { ms: handback })];
  const sent = [];
  for (let m = 0; m <= hours * 60; m += 10) {
    const nowMs = NOW.getTime() + m * MIN;
    const before = env.publish.sent.length;
    const report = await env.run(nowMs);
    assert.equal(report.ok, true, JSON.stringify(report.scopes[0].errors));
    if (env.publish.sent.length > before) {
      sent.push(nowMs);
      // the turn: the chip's two writes, which is all the turn changes on the ticket
      env.plane.activity["i-33"].push(...chip(nowMs));
      env.plane.boards[OTHER].issues.get("i-33").updated_at = at(nowMs + 5 * MIN);
    }
  }
  return { ...env, sent, row: () => env.plane.boards[OTHER].issues.get("i-33") };
}

test("33GOD-33 replay: review turns that only leave the chip behind stop at REVIEW_MAX_ATTEMPTS and the ticket is parked, once, with a comment", async () => {
  const { sent, plane, journal, row } = await replayReviewLoop({ hours: 48 });
  assert.equal(sent.length, REVIEW_MAX_ATTEMPTS, `exactly ${REVIEW_MAX_ATTEMPTS} turns in 48 hours, not one per 40 minutes`);
  for (let i = 1; i < sent.length; i++) assert.ok(sent[i] - sent[i - 1] >= REVIEW_RETRY_MS, "at least REVIEW_RETRY_MS apart");
  const parked = row();
  assert.ok(parked.labels.includes(labelId("agent:failed")), "parked with agent:failed");
  assert.ok(parked.labels.includes(labelId("lifecycle:review")), "the handback label is left as it was");
  const comments = plane.calls.filter((c) => c.method === "comment");
  assert.equal(comments.length, 1, "one comment, ever");
  assert.match(comments[0].html, /3 times/);
  assert.match(comments[0].html, /agent:failed/);
  const parks = journal.read().filter((e) => e.action === "loop.park");
  assert.deepEqual(parks.map((e) => [e.stage, e.attempts, e.ok]), [["review", 3, true]]);
  assert.equal(journal.read().filter((e) => e.action === "review.publish").length, 3);
});

test("a person clearing agent:failed starts a fresh episode: REVIEW_MAX_ATTEMPTS more turns, not an instant re-park", async () => {
  const first = await replayReviewLoop({ hours: 24 });
  assert.equal(first.sent.length, 3);
  const row = first.row();
  const clearedAt = NOW.getTime() + 25 * 60 * MIN;
  row.labels = row.labels.filter((l) => l !== labelId("agent:failed"));
  row.updated_at = at(clearedAt);
  first.plane.activity["i-33"].push(label("agent:failed", { add: false, ms: clearedAt }));
  const publishedBefore = first.publish.sent.length;
  await first.run(clearedAt + 40 * MIN);
  assert.equal(first.publish.sent.length, publishedBefore + 1, "a new episode: the PM is asked again");
  assert.equal(first.plane.calls.filter((c) => c.method === "comment").length, 1, "and the ticket was not re-parked");
});

test("a real new handback (lifecycle:review added again after a release) is a new episode even inside the retry gap", async () => {
  const handback = NOW.getTime() - 60 * MIN;
  const env = setup({ issues: [issue({ seq: 4, state: "ip", labels: ["lifecycle:review"], updated: at(handback) })] });
  env.plane.activity["i-4"] = [label("lifecycle:review", { ms: handback - 600 * MIN }), state("In Progress", "Todo", handback - 500 * MIN), label("lifecycle:review", { ms: handback })];
  const journal = [{ ts: at(handback - 400 * MIN), action: "review.publish", ok: true, ticket_id: "i-4", ticket_updated_at: at(handback - 540 * MIN), attempt: 1, command_id: "old1" }];
  for (const e of journal) env.journal.append(e);
  const report = await env.run(NOW.getTime());
  assert.deepEqual(report.scopes[0].reviews.map((r) => [r.result, r.attempt]), [["published", 1]]);
});

test("unreadable activity log: no send, no park, a warning (a loop is what is being prevented)", async () => {
  const handback = NOW.getTime() - 60 * MIN;
  const journal = new MemoryJournal([{ ts: at(NOW.getTime() - 5 * 60 * MIN), action: "review.publish", ok: true, ticket_id: "i-4", ticket_updated_at: at(handback - 100 * MIN), attempt: 1, command_id: "c1" }]);
  const env = setup({ journal, issues: [issue({ seq: 4, state: "ip", labels: ["lifecycle:review"], updated: at(handback) })] });
  env.plane.failActivities = () => new Error("GET activities -> HTTP 502");
  const report = await env.run(NOW.getTime());
  const s = report.scopes[0];
  assert.deepEqual(s.reviews, []);
  assert.deepEqual(s.parks, []);
  assert.ok(s.warnings.some((w) => /review not sent, activity log unreadable/.test(w)));
  assert.equal(env.publish.sent.length, 0);
  assert.equal(env.plane.writes().length, 0);
});

test("a first-ever review reads no activity log (a healthy handback costs nothing extra)", async () => {
  const env = setup({ issues: [issue({ seq: 4, state: "ip", labels: ["lifecycle:review"], updated: at(NOW.getTime() - 60 * MIN) })] });
  const report = await env.run(NOW.getTime());
  assert.equal(report.scopes[0].reviews[0].result, "published");
  assert.equal(env.plane.calls.filter((c) => c.method === "activities").length, 0);
});

test("HEYMA-39 replay: triage turns that only leave the chip behind stop at TRIAGE_MAX_ATTEMPTS and the ticket is parked", async () => {
  const entered = NOW.getTime() - 60 * MIN;
  const env = setup({ issues: [issue({ seq: 39, state: "todo", labels: [], updated: at(entered) })] });
  env.plane.activity["i-39"] = [{ created_at: at(entered - 5000 * MIN), verb: "created", field: null, old_value: null, new_value: null }, state("Backlog", "Todo", entered)];
  const sent = [];
  for (let m = 0; m <= 12 * 60; m += 10) {
    const nowMs = NOW.getTime() + m * MIN;
    const before = env.publish.sent.length;
    const report = await env.run(nowMs);
    assert.equal(report.ok, true, JSON.stringify(report.scopes[0].errors));
    if (env.publish.sent.length > before) {
      sent.push(nowMs);
      env.plane.activity["i-39"].push(...chip(nowMs));
      env.plane.boards[OTHER].issues.get("i-39").updated_at = at(nowMs + 2 * MIN);
    }
  }
  assert.equal(sent.length, TRIAGE_MAX_ATTEMPTS);
  for (let i = 1; i < sent.length; i++) assert.ok(sent[i] - sent[i - 1] >= TRIAGE_RETRY_MS);
  assert.ok(env.plane.boards[OTHER].issues.get("i-39").labels.includes(labelId("agent:failed")));
  assert.deepEqual(env.journal.read().filter((e) => e.action === "loop.park").map((e) => [e.stage, e.attempts]), [["triage", 3]]);
  assert.match(env.plane.calls.find((c) => c.method === "comment").html, /triage this ticket 3 times/);
});

test("triage: a ticket that re-enters Todo (released, moved back from Backlog) is a new episode", () => {
  const rows = [{ created_at: at(1000), verb: "created", field: null }, state("Backlog", "Todo", 2000), state("Todo", "In Progress", 3000), state("In Progress", "Todo", 4000)];
  assert.equal(episodeStartMs(rows, { stage: "triage", stateName: "Todo" }), 4000);
  assert.equal(episodeStartMs(rows, { stage: "triage", stateName: "Backlog" }), 1000, "an unrelated state name only sees creation");
  // the owner asking for a re-triage (removing lifecycle:triaged) also begins one
  assert.equal(episodeStartMs([...rows, label("lifecycle:triaged", { add: false, ms: 5000 })], { stage: "triage", stateName: "Todo" }), 5000);
});

test("episode: the chip's agent:working pairs, comments and descriptions never begin one", () => {
  const rows = [label("lifecycle:review", { ms: 1000 }), ...chip(2000), ...chip(9000), { created_at: at(9500), verb: "updated", field: "description", old_value: "a", new_value: "b" }, { created_at: at(9600), verb: "updated", field: "priority", old_value: "none", new_value: "high" }];
  assert.equal(episodeStartMs(rows, { stage: "review", stateName: "In Progress" }), 1000);
  // a hold label removed (a person answered the question, or cleared the park) does begin one
  assert.equal(episodeStartMs([...rows, label("lifecycle:needs-input", { add: false, ms: 9800 })], { stage: "review", stateName: "In Progress" }), 9800);
  assert.equal(episodeStartMs([], { stage: "review", stateName: "In Progress" }), Number.NEGATIVE_INFINITY);
});

test("judgeBoardTurn: send, wait inside the gap, park at the cap; sends from an earlier episode do not count", async () => {
  const handback = NOW.getTime() - 600 * MIN;
  const plane = new FakePlane({ [OTHER]: { issues: [] } });
  plane.activity["i-4"] = [label("lifecycle:review", { ms: handback })];
  const ticket = { id: "i-4", stateName: "In Progress" };
  const sendsAt = (...mins) => mins.map((m) => ({ at: at(NOW.getTime() - m * MIN) }));
  const j = (sends) => judgeBoardTurn({ plane, ws: "33god", board: OTHER, ticket, stage: "review", sends, nowMs: NOW.getTime() });
  assert.deepEqual(await j([]), { action: "send", attempt: 1 });
  assert.deepEqual(await j(sendsAt(500)), { action: "send", attempt: 2 }, "the gap has passed");
  assert.deepEqual(await j(sendsAt(30)), { action: "wait", why: "review turn sent 30 min ago", sent: 1 });
  assert.deepEqual(await j(sendsAt(500, 300, 200)), { action: "park", attempts: 3, lastAt: at(NOW.getTime() - 200 * MIN) });
  assert.deepEqual(await j(sendsAt(900, 800, 700)), { action: "send", attempt: 1 }, "three sends before the handback belong to the old episode");
});

test("activitiesOf follows Plane's cursor when the client has no activities() (the real Plane class)", async () => {
  const pages = [
    { results: [{ id: "a" }], next_page_results: true, next_cursor: "500:1:0" },
    { results: [{ id: "b" }], next_page_results: false, next_cursor: "500:2:0" },
  ];
  const urls = [];
  const plane = { boardUrl: (ws, board) => `https://plane/api/v1/workspaces/${ws}/projects/${board}`, get: async (url) => (urls.push(url), pages[urls.length - 1]) };
  assert.deepEqual((await activitiesOf(plane, "i-1", "33god", "b-1")).map((r) => r.id), ["a", "b"]);
  assert.match(urls[0], /issues\/i-1\/activities\/\?per_page=500$/);
  assert.match(urls[1], /cursor=500%3A1%3A0$/);
});

test("boardTurnSends counts per ticket across versions and ignores failed publishes and old entries", () => {
  const e = (action, id, ts, ok = true) => ({ action, ok, ticket_id: id, ts, ticket_updated_at: ts, command_id: `${id}${ts}` });
  const entries = [e("review.publish", "i-1", "2026-11-14T10:00:00Z"), e("review.publish", "i-1", "2026-11-14T10:40:00Z"), e("review.publish", "i-1", "2026-11-14T11:20:00Z", false), e("triage.publish", "i-2", "2026-11-14T10:00:00Z"), e("review.publish", "i-3", "2026-10-01T10:00:00Z")];
  const { review, triage } = boardTurnSends(entries, Date.parse("2026-11-07T00:00:00Z"));
  assert.equal(review.get("i-1").length, 2, "two versions, one ticket, two sends");
  assert.equal(triage.get("i-2").length, 1);
  assert.equal(review.has("i-3"), false);
});

test("the park write is capped per tick, skips a held ticket and a ticket that changed, and a dry run writes nothing", async () => {
  const handback = NOW.getTime() - 60 * MIN;
  const used = (id) => [0, 1, 2].map((i) => ({ ts: at(NOW.getTime() - (400 + i * 190) * MIN), action: "review.publish", ok: true, ticket_id: id, ticket_updated_at: at(handback - (i + 1) * 70 * MIN), attempt: i + 1, command_id: `${id}-${i}` }));
  const count = LOOP_PARK_TICK_CAP + 2;
  const issues = Array.from({ length: count }, (_, i) => issue({ seq: 100 + i, state: "ip", labels: ["lifecycle:review"], updated: at(handback) }));
  const journal = new MemoryJournal(issues.flatMap((r) => used(r.id)));
  const env = setup({ issues, journal });
  for (const r of issues) env.plane.activity[r.id] = [label("lifecycle:review", { ms: handback - 2000 * MIN })];

  const dry = await env.run(NOW.getTime(), { dryRun: true });
  assert.equal(dry.scopes[0].parks.length, count);
  assert.ok(dry.scopes[0].parks.every((p) => p.result === "planned"));
  assert.equal(env.plane.writes().length, 0);

  const real = await env.run(NOW.getTime());
  const results = real.scopes[0].parks.map((p) => p.result);
  assert.equal(results.filter((r) => r === "parked").length, LOOP_PARK_TICK_CAP);
  assert.equal(results.filter((r) => r === "capped").length, 2);
  assert.equal(env.plane.writes().length, LOOP_PARK_TICK_CAP);
  assert.equal(env.publish.sent.length, 0, "a parked ticket is never also sent a turn");
});

test("parkComment says who asked what, how many times, and how to resume", () => {
  const review = parkComment("review", 3, "2026-11-20T11:30:07.262Z");
  assert.match(review, /review this handed-back ticket 3 times \(the last one at 2026-11-20 11:30Z\)/);
  assert.match(review, /a verdict \(close, release or attention\)/);
  assert.match(review, /remove <code>agent:failed<\/code>/);
  assert.match(parkComment("triage", 3, null), /triage this ticket 3 times, and none of those turns ended with lifecycle:triaged or a hold label/);
});

test("the spec's catch_up_attempts block says what the code does", async () => {
  const { readFileSync } = await import("node:fs");
  const spec = readFileSync(new URL("../../spec/lifecycle.v2.yaml", import.meta.url), "utf8");
  assert.match(spec, new RegExp(`review: \\{max_attempts: ${REVIEW_MAX_ATTEMPTS}, min_gap: ${REVIEW_RETRY_MS / 3600000} hours\\}`));
  assert.match(spec, new RegExp(`triage: \\{max_attempts: ${TRIAGE_MAX_ATTEMPTS}, min_gap: ${TRIAGE_RETRY_MS / 60000} minutes\\}`));
  assert.match(spec, new RegExp(`At most ${LOOP_PARK_TICK_CAP} parks per tick`));
});

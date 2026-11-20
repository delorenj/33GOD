import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { join } from "node:path";

import { loadBloodbank } from "../deps.mjs";
import { scopesFromRegistry } from "../registry.mjs";
import { COMMAND_TYPE, TRIAGE_REASON, TRIAGE_RETRY_MS, runTick, triageIds } from "../run.mjs";
import { MemoryJournal, Journal, triagedCommandIds } from "../journal.mjs";
import { laneModel } from "../lifecycle.mjs";
import { normalizeTicket, triageCandidatesOf, triageGuard } from "../select.mjs";
import { formatReport } from "../format.mjs";
import { FakePlane, LABEL_NAMES, NOW, SOLO, STATES, TOLT, fakePublisher, issue, labelId, registryFixture, tempDir } from "./helpers.mjs";

const { fleet, nats, registry: bbRegistry } = loadBloodbank();

function setup({ boards, board, publish = fakePublisher(), journal = new MemoryJournal(), registry = registryFixture() }) {
  const plane = new FakePlane(boards);
  const { scopes, skipped } = scopesFromRegistry(registry, { activation: bbRegistry.bloodbankActivation, executionMode: () => "legacy", board });
  const run = (over = {}) => runTick({ registry, scopes, skipped, plane, fleet, nats, publish, journal, now: () => NOW, timeZone: "America/New_York", ...over });
  return { plane, publish, journal, run };
}

const scopeOf = (report, agentId) => report.scopes.find((s) => s.agentId === agentId);
const triages = (publish) => publish.sent.filter((c) => c.data.context.reason === TRIAGE_REASON);

// NOW is 15:00Z. 14:00Z is an hour old; 14:45Z is 15 minutes old.
const OLD = "2026-11-14T14:00:00Z";
const FRESH = "2026-11-14T14:45:00Z";

const lanes = laneModel(STATES);
const labelNameOf = new Map(LABEL_NAMES.map((n) => [labelId(n), n]));
const t = (spec) => normalizeTicket(issue(spec), { lanes, labelNameOf, identifier: "T" });

test("triage eligibility: triaged, held, working, epic, too fresh, not Todo are all excluded", () => {
  const nowMs = NOW.getTime();
  const why = (spec) => triageGuard(t({ updated: OLD, ...spec }), nowMs);
  assert.equal(why({ seq: 1 }), null, "plain stale Todo ticket is eligible");
  assert.equal(why({ seq: 2, labels: ["repo:game", "feature"] }), null, "other labels do not matter");
  assert.match(why({ seq: 3, labels: ["lifecycle:triaged"] }), /already triaged/);
  for (const hold of ["lifecycle:needs-input", "lifecycle:blocked", "agent:failed"]) assert.match(why({ seq: 4, labels: [hold] }), /held/);
  assert.match(why({ seq: 5, labels: ["agent:working"] }), /agent:working/);
  assert.match(why({ seq: 6, labels: ["epic"] }), /epic container/);
  assert.match(why({ seq: 7, labels: ["epic:big-thing"] }), /epic container/);
  assert.match(why({ seq: 8, updated: "2026-11-14T14:55:00Z" }), /last 10 minutes/);
  assert.match(why({ seq: 9, updated: "2026-11-14T14:50:00Z" }), /last 10 minutes/, "exactly 10 minutes (one tick) is not older than 10 minutes");
  assert.equal(why({ seq: 10, updated: "2026-11-14T14:49:59Z" }), null);
  assert.equal(why({ seq: 12, updated: FRESH }), null, "15 minutes old is past the one-tick window");
  assert.match(why({ seq: 11, updated: null }), /no updated_at/);
  assert.match(why({ seq: 12, state: "backlog" }), /not in Todo/);
  assert.match(why({ seq: 13, state: "ip" }), /not in Todo/);
});

test("triage candidates are oldest first", () => {
  const tickets = [
    t({ seq: 1, updated: "2026-11-14T13:00:00Z" }),
    t({ seq: 2, updated: "2026-11-14T11:00:00Z" }),
    t({ seq: 3, updated: "2026-11-14T12:00:00Z" }),
  ];
  assert.deepEqual(triageCandidatesOf(tickets, NOW.getTime()).map((x) => x.key), ["T-2", "T-3", "T-1"]);
});

test("a stale untriaged Todo ticket gets the Ticket Triage lane's command, and nothing is written to Plane", async () => {
  const boards = { [SOLO]: { issues: [issue({ seq: 1, updated: OLD, name: "do the thing" })] } };
  const { plane, publish, journal, run } = setup({ boards, board: "SOLO" });
  const report = await run();
  assert.equal(report.ok, true, JSON.stringify(report.scopes.map((s) => s.errors)));
  assert.deepEqual(plane.writes(), [], "no Plane write for triage");
  assert.equal(publish.sent.length, 1);
  const cmd = publish.sent[0];
  assert.equal(cmd.type, COMMAND_TYPE);
  assert.equal(cmd.kind, "command");
  assert.equal(cmd.data.target_agent_id, "solo-pm");
  assert.equal(cmd.data.context.reason, "ticket-grooming");
  assert.equal(cmd.data.context.ticket_key, "SOLO-1");
  assert.equal(cmd.data.context.board_id, SOLO);
  assert.equal(cmd.data.context.phase, "Todo");
  assert.deepEqual(Object.keys(cmd.data.context), ["reason", "repo", "ticket_key", "ticket_id", "board_id", "workspace", "title", "phase", "previous_phase", "provider_event_type"]);
  const facts = fleet.ticketFactsFromEnvelope({ data: { repo: "solo", board_id: SOLO, ticket_key: "SOLO-1", ticket_id: "i-1", title: "do the thing", workspace: "33god", phase: "Todo" } });
  assert.equal(cmd.data.prompt, fleet.groomingPrompt(facts, "/nonexistent/solo-pm", "lifecycle:triaged"), "the Fleet node's groomTicket prompt, verbatim");
  assert.match(cmd.data.prompt, /^Triage the ticket that just entered Todo/);
  assert.equal(cmd.observedAt, "2026-11-14T14:00:00.000Z", "stable: the ticket version's own time");
  const planned = scopeOf(report, "solo-pm").triage;
  assert.deepEqual(planned.map((x) => [x.key, x.result]), [["SOLO-1", "published"]]);
  const entry = journal.read().find((e) => e.action === "triage.publish");
  assert.equal(entry.ok, true);
  assert.equal(entry.command_id, cmd.commandId);
  assert.equal(journal.read().find((e) => e.action === "tick").triaged, 1);
});

test("deterministic command id: board + ticket + updated_at + triage; a new version, ticket or agent gets a new one", () => {
  const base = { boardId: SOLO, ticketId: "i-1", updatedAt: OLD, agentId: "solo-pm" };
  const a = triageIds({ fleet, nats }, base);
  assert.deepEqual(triageIds({ fleet, nats }, base), a);
  assert.notEqual(triageIds({ fleet, nats }, { ...base, updatedAt: "2026-11-14T14:01:00Z" }).commandId, a.commandId);
  assert.notEqual(triageIds({ fleet, nats }, { ...base, ticketId: "i-2" }).commandId, a.commandId);
  assert.notEqual(triageIds({ fleet, nats }, { ...base, boardId: "b-x" }).commandId, a.commandId);
  assert.match(a.commandId, /^[0-9a-f-]{36}$/);
});

test("once per ticket version: a second tick sends nothing; a new updated_at triages again", async () => {
  const boards = { [SOLO]: { issues: [issue({ seq: 1, updated: OLD })] } };
  const { plane, publish, journal, run } = setup({ boards, board: "SOLO" });
  await run();
  assert.equal(triages(publish).length, 1);
  const second = await run();
  assert.equal(triages(publish).length, 1, "same version: not triaged again");
  const solo = scopeOf(second, "solo-pm");
  assert.deepEqual(solo.triage, []);
  assert.deepEqual(solo.triageSeen, ["SOLO-1"]);

  // A fresh Runtime with only the journal file knows it too.
  const dir = tempDir();
  const file = new Journal(join(dir, "j.jsonl"));
  for (const e of journal.read()) file.append(e);
  const third = setup({ boards, board: "SOLO", journal: file });
  await third.run();
  assert.equal(triages(third.publish).length, 0);

  // The ticket changed (a person edited it) and the retry gap has passed: a new version, a new command id.
  plane.boards[SOLO].issues.get("i-1").updated_at = "2026-11-14T14:10:00Z";
  await run({ now: () => new Date(NOW.getTime() + TRIAGE_RETRY_MS + 60000) });
  assert.equal(triages(publish).length, 2);
  assert.notEqual(triages(publish)[0].commandId, triages(publish)[1].commandId);
});

test("a failed triage publish is journaled not-ok and retried next tick with the identical command", async () => {
  const boards = { [SOLO]: { issues: [issue({ seq: 1, updated: OLD })] } };
  let fail = true;
  const publish = fakePublisher({ fail: () => fail });
  const { journal, run } = setup({ boards, board: "SOLO", publish });
  const first = await run();
  assert.equal(first.ok, false);
  assert.equal(scopeOf(first, "solo-pm").triage[0].result, "publish failed");
  assert.equal(triagedCommandIds(journal.read()).size, 0);
  fail = false;
  const second = await run();
  assert.equal(second.ok, true);
  assert.equal(publish.sent.length, 2);
  assert.deepEqual(publish.sent[0], publish.sent[1], "byte-identical retry");
  assert.equal(triagedCommandIds(journal.read()).size, 1);
});

test("caps (scope cap 2): 2 per scope, oldest first; 6 per tick overall, oldest first; capped tickets are reported", async () => {
  // forge, director and tolt-pm on TOLT (agent id order: forge, tolt-director, tolt-pm), plus OTHER's solo board.
  const at = (h, m = 0) => `2026-11-14T${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:00Z`;
  const boards = {
    [TOLT]: {
      issues: [
        // tolt-pm (default scope: repo:game and unlabelled): 4 stale, oldest are 1 (01:00) and 2 (02:00)
        issue({ seq: 1, labels: ["repo:game"], updated: at(1) }),
        issue({ seq: 2, labels: [], updated: at(2) }),
        issue({ seq: 3, labels: ["repo:game"], updated: at(3) }),
        issue({ seq: 4, labels: ["repo:game"], updated: at(4) }),
        // forge: 3 stale, oldest are 5 (05:00) and 6 (06:00)
        issue({ seq: 5, labels: ["repo:forge"], updated: at(5) }),
        issue({ seq: 6, labels: ["repo:forge"], updated: at(6) }),
        issue({ seq: 7, labels: ["repo:forge"], updated: at(7) }),
        // director: 3 stale
        issue({ seq: 8, labels: ["repo:tolt"], updated: at(8) }),
        issue({ seq: 9, labels: ["repo:tolt"], updated: at(9) }),
        issue({ seq: 10, labels: ["repo:tolt"], updated: at(10) }),
      ],
    },
  };
  const { plane, publish, run } = setup({ boards, board: "TOLT" });
  const report = await run({ triageScopeCap: 2 });
  assert.deepEqual(plane.writes(), []);
  const sent = triages(publish).map((c) => c.data.context.ticket_key);
  // per scope: pm {1,2}, forge {5,6}, director {8,9} = 6 = exactly the tick cap, oldest first overall
  assert.deepEqual(sent, ["TOLT-1", "TOLT-2", "TOLT-5", "TOLT-6", "TOLT-8", "TOLT-9"]);
  const pm = scopeOf(report, "tolt-pm");
  assert.deepEqual(pm.triageCapped.map((c) => [c.key, /scope cap/.test(c.why)]), [["TOLT-3", true], ["TOLT-4", true]]);
  assert.deepEqual(scopeOf(report, "lost-things-forge-pm").triageCapped.map((c) => c.key), ["TOLT-7"]);

  // Now the tick cap: lower it to 3; the three oldest of the six go, the others report a tick cap.
  const again = setup({ boards, board: "TOLT" });
  const r2 = await again.run({ triageScopeCap: 2, triageTickCap: 3 });
  assert.deepEqual(triages(again.publish).map((c) => c.data.context.ticket_key), ["TOLT-1", "TOLT-2", "TOLT-5"]);
  const tickCapped = r2.scopes.flatMap((s) => s.triageCapped).filter((c) => /tick cap/.test(c.why)).map((c) => c.key).sort();
  assert.deepEqual(tickCapped, ["TOLT-6", "TOLT-8", "TOLT-9"]);
  assert.deepEqual(r2.scopes.flatMap((s) => s.triage).map((x) => x.key).sort(), ["TOLT-1", "TOLT-2", "TOLT-5"], "capped plans leave the scope's triage list");
});

test("a ticket edited between listing and triage is skipped (live re-read)", async () => {
  const boards = { [SOLO]: { issues: [issue({ seq: 1, updated: OLD })] } };
  const { plane, publish, run } = setup({ boards, board: "SOLO" });
  const realIssue = plane.issue.bind(plane);
  plane.issue = async (...a) => {
    const row = await realIssue(...a);
    row.labels.push(labelId("lifecycle:triaged"));
    return row;
  };
  const report = await run();
  assert.equal(publish.sent.length, 0);
  assert.match(scopeOf(report, "solo-pm").triage[0].why, /already triaged/);
});

test("excluded tickets are not triaged in a full tick (triaged, held, working, epic, fresh, epic:*)", async () => {
  const boards = {
    [SOLO]: {
      issues: [
        issue({ seq: 1, labels: ["lifecycle:triaged"], updated: OLD }),
        issue({ seq: 2, labels: ["lifecycle:needs-input"], updated: OLD }),
        issue({ seq: 3, labels: ["agent:working"], updated: OLD }),
        issue({ seq: 4, labels: ["epic"], updated: OLD }),
        issue({ seq: 5, updated: FRESH }),
        issue({ seq: 6, labels: ["epic:big-thing"], updated: OLD }),
        issue({ seq: 7, state: "backlog", updated: OLD }),
        issue({ seq: 8, updated: OLD }),
      ],
    },
  };
  const { publish, run } = setup({ boards, board: "SOLO" });
  await run();
  assert.deepEqual(triages(publish).map((c) => c.data.context.ticket_key), ["SOLO-8"]);
});

test("dry run: plans the triage (report only); no publish, no Plane write, no journal file", async () => {
  const boards = { [SOLO]: { issues: [issue({ seq: 1, updated: OLD }), issue({ seq: 2, updated: OLD }), issue({ seq: 3, updated: OLD })] } };
  const dir = tempDir();
  const journal = new Journal(join(dir, "j.jsonl"));
  const publish = fakePublisher({ fail: true });
  const { plane, run } = setup({ boards, board: "SOLO", publish, journal });
  const calls = () => plane.calls.filter((c) => c.method === "issue").length;
  const report = await run({ dryRun: true });
  assert.equal(report.ok, true);
  assert.equal(publish.sent.length, 0);
  assert.deepEqual(plane.writes(), []);
  assert.equal(existsSync(journal.path), false);
  assert.equal(calls(), 0, "dry run does no live re-reads");
  const solo = scopeOf(report, "solo-pm");
  // default scope cap is 1: one triage turn per desk per tick, so two never race the desk's lease
  assert.deepEqual(solo.triage.map((x) => [x.key, x.result]), [["SOLO-1", "planned"]]);
  assert.ok(solo.triage.every((x) => x.commandId));
  assert.deepEqual(solo.triageCapped.map((c) => c.key), ["SOLO-2", "SOLO-3"]);
});

test("human summary: a triage catch-up line per scope, with planned ids, caps and already-triaged versions", async () => {
  const boards = { [SOLO]: { issues: [issue({ seq: 1, updated: OLD }), issue({ seq: 2, updated: OLD }), issue({ seq: 3, updated: OLD })] } };
  const { run } = setup({ boards, board: "SOLO" });
  const text = formatReport(await run({ dryRun: true }));
  assert.match(text, /triage catch-up: SOLO-1 planned cmd [0-9a-f-]{36}; capped 2: SOLO-2 \(scope cap/);
  const none = formatReport(await setup({ boards: { [SOLO]: { issues: [] } }, board: "SOLO" }).run());
  assert.match(none, /triage catch-up: none/);
});

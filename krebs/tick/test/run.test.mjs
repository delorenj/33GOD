import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { loadBloodbank } from "../deps.mjs";
import { scopesFromRegistry } from "../registry.mjs";
import { COMMAND_TYPE, dispatchIds, runTick } from "../run.mjs";
import { Journal, MemoryJournal, pendingPublishes } from "../journal.mjs";
import { FakePlane, NOW, OTHER, SOLO, TOLT, WS, fakePublisher, issue, labelId, registryFixture, tempDir } from "./helpers.mjs";

const { fleet, nats, registry: bbRegistry } = loadBloodbank();

function setup({ boards, board, publish = fakePublisher(), journal = new MemoryJournal(), registry = registryFixture() }) {
  const plane = new FakePlane(boards);
  const { scopes, skipped } = scopesFromRegistry(registry, {
    activation: bbRegistry.bloodbankActivation,
    executionMode: () => "legacy",
    board,
  });
  const run = (over = {}) =>
    runTick({ registry, scopes, skipped, plane, fleet, nats, publish, journal, now: () => NOW, timeZone: "America/New_York", ...over });
  return { plane, publish, journal, run, scopes };
}

const scopeOf = (report, agentId) => report.scopes.find((s) => s.agentId === agentId);

function toltBoard() {
  return {
    [TOLT]: {
      issues: [
        issue({ seq: 1, labels: ["lifecycle:triaged", "repo:game"], sort: 100 }),
        issue({ seq: 2, labels: ["lifecycle:triaged", "repo:game"], sort: 200 }),
        issue({ seq: 3, labels: ["lifecycle:triaged", "repo:game"], sort: 300 }),
        issue({ seq: 4, labels: ["lifecycle:triaged", "repo:forge"], sort: 100, start: "2026-11-01" }),
        issue({ seq: 5, labels: ["lifecycle:triaged", "repo:tolt"], sort: 100 }),
        issue({ seq: 6, labels: ["lifecycle:triaged"], sort: 50 }), // no repo label: the default scope (tolt-pm)
        issue({ seq: 7, state: "ip", labels: ["lifecycle:triaged", "repo:game"] }),
        issue({ seq: 8, state: "ip", labels: ["lifecycle:triaged", "repo:forge", "lifecycle:review"] }),
      ],
    },
  };
}

test("shared board: each scope sees only the tickets routed to it, and dispatches to its own agent", async () => {
  const { plane, publish, run } = setup({ boards: toltBoard(), board: "TOLT" });
  const report = await run();
  assert.equal(report.ok, true, JSON.stringify(report.scopes.map((s) => s.errors)));

  const pm = scopeOf(report, "tolt-pm");
  assert.equal(pm.tickets, 5, "T-1,2,3,7 carry repo:game, T-6 has no scope label");
  assert.deepEqual(pm.occupied, ["TOLT-7"]);
  assert.equal(pm.free, 1);
  assert.deepEqual(pm.dispatches.map((d) => [d.key, d.result]), [["TOLT-6", "dispatched"]]);
  assert.deepEqual(pm.waiting, ["TOLT-1", "TOLT-2", "TOLT-3"]);

  const forge = scopeOf(report, "lost-things-forge-pm");
  assert.deepEqual(forge.occupied, [], "a ticket in review does not hold a slot");
  assert.equal(forge.free, 2);
  assert.deepEqual(forge.dispatches.map((d) => d.key), ["TOLT-4"]);

  const director = scopeOf(report, "tolt-director");
  assert.deepEqual(director.dispatches.map((d) => d.key), ["TOLT-5"]);

  // One Plane write per dispatch: In Progress + agent:working (+ start_date only when unset).
  // Scopes run in agent id order: forge, director, tolt-pm.
  assert.deepEqual(
    plane.writes().map((w) => [w.id, w.fields, w.addLabels, w.removeLabels]),
    [
      ["i-4", { state: "s-ip" }, [labelId("agent:working")], []],
      ["i-5", { state: "s-ip", start_date: "2026-11-14" }, [labelId("agent:working")], []],
      ["i-6", { state: "s-ip", start_date: "2026-11-14" }, [labelId("agent:working")], []],
    ],
  );

  // One start command per dispatch, to the scope owner, reason ticket-delegation.
  const byTicket = Object.fromEntries(publish.sent.map((c) => [c.data.context.ticket_key, c]));
  assert.equal(byTicket["TOLT-6"].data.target_agent_id, "tolt-pm");
  assert.equal(byTicket["TOLT-4"].data.target_agent_id, "lost-things-forge-pm");
  assert.equal(byTicket["TOLT-5"].data.target_agent_id, "tolt-director");
  for (const c of publish.sent) {
    assert.equal(c.type, COMMAND_TYPE);
    assert.equal(c.kind, "command");
    assert.equal(c.data.context.reason, "ticket-delegation");
    assert.equal(c.data.context.board_id, TOLT);
    assert.equal(c.data.context.phase, "In Progress");
    assert.equal(c.eventId, c.commandId);
    assert.equal(c.correlationId, fleet.ticketCorrelationId(TOLT, c.data.context.ticket_id));
    assert.match(c.data.prompt, /Krebs has just dispatched it to you/);
    assert.match(c.data.prompt, /NO review step/);
  }
});

test("the start command is a valid canonical envelope, stable across rebuilds", async () => {
  const { publish, run } = setup({ boards: toltBoard(), board: "TOLT" });
  await run();
  const cmd = publish.sent[0];
  const { subject, envelope } = nats.buildEnvelope(cmd);
  assert.equal(subject, "bloodbank.cmd.agent.invocation.start");
  nats.validateEnvelope(COMMAND_TYPE, envelope);
  assert.equal(envelope.command_id, cmd.commandId);
  assert.equal(envelope.idempotency_key, `agent.invocation.start:target:${cmd.data.target_agent_id}:command:${cmd.commandId}`);
  assert.equal(envelope.time, NOW.toISOString());
  assert.equal(JSON.stringify(nats.buildEnvelope(structuredClone(cmd)).envelope), JSON.stringify(envelope));
});

test("deterministic command id: same ticket version, same id; a new version or agent, a new one", async () => {
  const first = await setup({ boards: toltBoard(), board: "TOLT" }).run({ dryRun: true });
  const second = await setup({ boards: toltBoard(), board: "TOLT" }).run({ dryRun: true });
  const planned = (r) => scopeOf(r, "tolt-pm").dispatches[0];
  assert.equal(planned(first).commandId, planned(second).commandId);
  assert.equal(planned(first).dispatchId, planned(second).dispatchId);

  const expectedDispatch = nats.deterministicUuid(`krebs:dispatch:${TOLT}:i-6:2026-11-14T10:00:00Z`);
  assert.equal(planned(first).dispatchId, expectedDispatch);
  assert.equal(planned(first).commandId, fleet.fleetCommandId(expectedDispatch, "delegateTicket", "tolt-pm"));

  const live = setup({ boards: toltBoard(), board: "TOLT" });
  await live.run();
  assert.equal(live.publish.sent.find((c) => c.data.context.ticket_key === "TOLT-6").commandId, planned(first).commandId, "the live dispatch uses the id the dry run showed");

  const base = { boardId: TOLT, ticketId: "i-6", updatedAt: "2026-11-14T10:00:00Z", agentId: "tolt-pm" };
  const ids = (over) => dispatchIds({ fleet, nats }, { ...base, ...over }).commandId;
  assert.equal(ids({}), planned(first).commandId);
  assert.notEqual(ids({ updatedAt: "2026-11-15T10:00:00Z" }), ids({}));
  assert.notEqual(ids({ agentId: "lost-things-forge-pm" }), ids({}));
  assert.notEqual(ids({ ticketId: "i-7" }), ids({}));
});

test("dry run: reads only; no Plane write, no publish, no journal file", async () => {
  const dir = tempDir();
  const path = join(dir, "tick-journal.jsonl");
  const boards = toltBoard();
  boards[TOLT].issues.push(issue({ seq: 9, state: "done", labels: ["agent:working", "repo:game"] }));
  const { plane, publish, run } = setup({ boards, board: "TOLT", journal: new Journal(path) });
  const report = await run({ dryRun: true });
  assert.equal(report.dryRun, true);
  assert.deepEqual(plane.writes(), []);
  assert.deepEqual(publish.sent, []);
  assert.equal(existsSync(path), false);
  const pm = scopeOf(report, "tolt-pm");
  assert.deepEqual(pm.dispatches.map((d) => [d.key, d.result]), [["TOLT-6", "planned"]]);
  assert.deepEqual(pm.repairs.map((r) => [r.key, r.remove, r.result]), [["TOLT-9", ["agent:working"], "planned"]]);
  assert.ok(!plane.calls.some((c) => c.method === "issue"), "a dry run does not even re-read candidates");
});

test("over the limit drains: nothing dispatched, nothing evicted", async () => {
  const boards = {
    [SOLO]: {
      issues: [
        issue({ seq: 1, state: "ip", labels: ["lifecycle:triaged"] }),
        issue({ seq: 2, state: "ip", labels: ["lifecycle:triaged", "agent:working"] }),
        issue({ seq: 3, labels: ["lifecycle:triaged"] }),
      ],
    },
  };
  const { plane, publish, run } = setup({ boards, board: "SOLO" });
  const report = await run();
  const solo = scopeOf(report, "solo-pm");
  assert.equal(solo.wip, 1);
  assert.equal(solo.free, 0);
  assert.equal(solo.overLimit, 1);
  assert.deepEqual(solo.dispatches, []);
  assert.deepEqual(solo.waiting, ["SOLO-3"]);
  assert.deepEqual(plane.writes(), []);
  assert.deepEqual(publish.sent, []);
  assert.ok(!plane.calls.some((c) => c.method === "relations"), "a full scope reads no relations");
});

test("held and review tickets free their slot", async () => {
  const boards = {
    [SOLO]: {
      issues: [
        issue({ seq: 1, state: "ip", labels: ["lifecycle:triaged", "lifecycle:review"] }),
        issue({ seq: 2, state: "ip", labels: ["lifecycle:triaged", "lifecycle:needs-input"] }),
        issue({ seq: 3, labels: ["lifecycle:triaged"] }),
      ],
    },
  };
  const { publish, run } = setup({ boards, board: "SOLO" });
  const report = await run();
  assert.deepEqual(scopeOf(report, "solo-pm").dispatches.map((d) => d.key), ["SOLO-3"]);
  assert.match(publish.sent[0].data.prompt, /REQUIRES review/);
  assert.equal(publish.sent[0].data.context.review_required, true);
});

test("guards: untriaged, held, working and epic Todo tickets are never dispatched", async () => {
  const boards = {
    [SOLO]: {
      issues: [
        issue({ seq: 1, labels: [] }),
        issue({ seq: 2, labels: ["lifecycle:triaged", "lifecycle:blocked"] }),
        issue({ seq: 3, labels: ["lifecycle:triaged", "agent:working"] }),
        issue({ seq: 4, labels: ["lifecycle:triaged", "epic"] }),
        issue({ seq: 5, labels: ["lifecycle:triaged", "epic:big-thing"] }),
      ],
    },
  };
  const { plane, run } = setup({ boards, board: "SOLO" });
  const report = await run();
  const solo = scopeOf(report, "solo-pm");
  assert.deepEqual(solo.dispatches, []);
  assert.deepEqual(solo.excluded.map((e) => e.key), ["SOLO-1", "SOLO-2", "SOLO-3", "SOLO-4", "SOLO-5"]);
  assert.deepEqual(plane.writes(), []);
});

test("an open blocking relation skips the ticket; a closed one does not; cross-board blockers are looked up", async () => {
  const boards = {
    [SOLO]: {
      issues: [
        issue({ seq: 1, labels: ["lifecycle:triaged"], sort: 1 }),
        issue({ seq: 2, labels: ["lifecycle:triaged"], sort: 2 }),
        issue({ seq: 3, labels: ["lifecycle:triaged"], sort: 3 }),
        issue({ seq: 8, state: "done" }),
        issue({ seq: 9, state: "todo" }),
      ],
      relations: {
        "i-1": { blocked_by: [{ project_id: SOLO, issue_id: "i-9" }] },
        "i-2": { blocked_by: [{ project_id: OTHER, issue_id: "o-1" }] },
        "i-3": { blocked_by: [{ project_id: SOLO, issue_id: "i-8" }, { project_id: OTHER, issue_id: "o-2" }] },
      },
    },
    [OTHER]: {
      issues: [
        { ...issue({ seq: 101, state: "ip" }), id: "o-1" },
        { ...issue({ seq: 102, state: "cancel" }), id: "o-2" },
      ],
    },
  };
  const { publish, run } = setup({ boards, board: "SOLO" });
  const report = await run();
  const solo = scopeOf(report, "solo-pm");
  assert.deepEqual(solo.blocked.map((b) => b.key), ["SOLO-1", "SOLO-2"]);
  assert.match(solo.blocked[0].why, /blocked by SOLO-9 \(Todo\)/);
  assert.match(solo.blocked[1].why, /blocked by #101 \(In Progress\)/);
  assert.deepEqual(solo.dispatches.map((d) => [d.key, d.result]), [["SOLO-3", "dispatched"]]);
  assert.equal(publish.sent.length, 1);
});

test("invariant repair: one delta write per ticket, journaled", async () => {
  const boards = {
    [SOLO]: {
      issues: [
        issue({ seq: 1, state: "todo", labels: ["lifecycle:review", "lifecycle:triaged", "lifecycle:needs-input"] }),
        issue({ seq: 2, state: "done", labels: ["agent:working", "feature"] }),
        issue({ seq: 3, state: "cancel", labels: ["agent:working", "lifecycle:review"] }),
        issue({ seq: 4, state: "ip", labels: ["lifecycle:review", "agent:working"] }),
      ],
    },
  };
  const journal = new MemoryJournal();
  const { plane, run } = setup({ boards, board: "SOLO", journal });
  const report = await run();
  assert.deepEqual(
    plane.writes().map((w) => [w.id, w.removeLabels, w.addLabels, w.fields]),
    [
      ["i-1", [labelId("lifecycle:review")], [], {}],
      ["i-2", [labelId("agent:working")], [], {}],
      ["i-3", [labelId("lifecycle:review"), labelId("agent:working")], [], {}],
    ],
  );
  assert.deepEqual(scopeOf(report, "solo-pm").repairs.map((r) => r.result), ["repaired", "repaired", "repaired"]);
  assert.deepEqual(plane.boards[SOLO].issues.get("i-2").labels, [labelId("feature")]);
  assert.equal(journal.entries.filter((e) => e.action === "repair" && e.ok).length, 3);
});

test("journal republish: a publish that failed is republished next tick with the same command, once", async () => {
  const dir = tempDir();
  const path = join(dir, "tick-journal.jsonl");
  const boards = { [SOLO]: { issues: [issue({ seq: 1, labels: ["lifecycle:triaged"] })] } };
  const failing = fakePublisher({ fail: true });
  const ctx = setup({ boards, board: "SOLO", publish: failing, journal: new Journal(path) });

  const first = await ctx.run();
  assert.equal(first.ok, false);
  assert.equal(scopeOf(first, "solo-pm").dispatches[0].result, "publish failed");
  const lines = readFileSync(path, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.deepEqual(lines.map((l) => [l.action, l.ok]), [
    ["dispatch.intent", undefined],
    ["dispatch.write", true],
    ["dispatch.publish", false],
    ["tick", false],
  ]);
  assert.equal(pendingPublishes(lines).length, 1);

  // Tick 2: the bus is back. The ticket is In Progress now; the owed publish goes out, no new write.
  const working = fakePublisher();
  const second = await runTick({
    registry: registryFixture(), scopes: ctx.scopes, skipped: [], plane: ctx.plane, fleet, nats,
    publish: working, journal: new Journal(path), now: () => new Date(NOW.getTime() + 600_000), timeZone: "America/New_York",
  });
  assert.equal(second.ok, true);
  const solo = scopeOf(second, "solo-pm");
  assert.deepEqual(solo.republishes.map((r) => r.result), ["republished"]);
  assert.deepEqual(solo.occupied, ["SOLO-1"]);
  assert.deepEqual(solo.dispatches, []);
  assert.equal(ctx.plane.writes().length, 1, "the ticket was written once, on tick 1");
  assert.equal(working.sent.length, 1);
  assert.deepEqual(working.sent[0], failing.sent[0], "byte-identical command: same id, same time, same prompt");
  assert.equal(
    JSON.stringify(nats.buildEnvelope(working.sent[0]).envelope),
    JSON.stringify(nats.buildEnvelope(failing.sent[0]).envelope),
  );

  // Tick 3: nothing owed any more.
  const third = await runTick({
    registry: registryFixture(), scopes: ctx.scopes, skipped: [], plane: ctx.plane, fleet, nats,
    publish: working, journal: new Journal(path), now: () => new Date(NOW.getTime() + 1_200_000),
  });
  assert.deepEqual(scopeOf(third, "solo-pm").republishes, []);
  assert.equal(working.sent.length, 1);
  assert.equal(pendingPublishes(new Journal(path).read()).length, 0);
});

test("journal recovery: an intent with no write on record is checked live before republishing", async () => {
  const boards = {
    [SOLO]: {
      issues: [
        issue({ seq: 50, state: "ip", labels: ["lifecycle:triaged", "agent:working"] }),
        issue({ seq: 51, state: "ip", labels: ["lifecycle:triaged"] }),
        issue({ seq: 52, state: "done", labels: ["lifecycle:triaged"] }),
        issue({ seq: 53, state: "ip", labels: ["lifecycle:triaged", "agent:working", "lifecycle:needs-input"] }),
      ],
    },
  };
  const intent = (seq) => ({
    ts: "2026-11-14T14:50:00.000Z",
    action: "dispatch.intent",
    dispatch_id: `d-${seq}`,
    command_id: `c-${seq}`,
    agent_id: "solo-pm",
    board_id: SOLO,
    workspace: WS,
    ticket_id: `i-${seq}`,
    key: `SOLO-${seq}`,
    command: { type: COMMAND_TYPE, kind: "command", commandId: `c-${seq}`, data: { target_agent_id: "solo-pm", prompt: "p" } },
  });
  const journal = new MemoryJournal([intent(50), intent(51), intent(52), intent(53)]);
  const { publish, run } = setup({ boards, board: "SOLO", journal });
  const report = await run();
  const r = Object.fromEntries(scopeOf(report, "solo-pm").republishes.map((x) => [x.key, x]));
  assert.equal(r["SOLO-50"].result, "republished");
  assert.equal(r["SOLO-51"].result, "dropped");
  assert.match(r["SOLO-51"].why, /no agent:working/);
  assert.equal(r["SOLO-52"].result, "dropped");
  assert.match(r["SOLO-52"].why, /left In Progress \(Done\)/);
  assert.equal(r["SOLO-53"].result, "dropped");
  assert.match(r["SOLO-53"].why, /held \(lifecycle:needs-input\)/);
  assert.deepEqual(publish.sent.map((c) => c.commandId), ["c-50"]);
  assert.equal(pendingPublishes(journal.read()).length, 0);
});

test("a refused write dispatches nothing; an unknown-outcome write is verified on the next tick", async () => {
  const boards = { [SOLO]: { issues: [issue({ seq: 1, labels: ["lifecycle:triaged"] })] } };
  const journal = new MemoryJournal();
  const ctx = setup({ boards, board: "SOLO", journal });
  ctx.plane.failWrite = () => Object.assign(new Error("PATCH -> HTTP 400"), { status: 400 });
  const refused = await ctx.run();
  assert.equal(scopeOf(refused, "solo-pm").dispatches[0].result, "write failed");
  assert.equal(ctx.publish.sent.length, 0);
  assert.equal(pendingPublishes(journal.read()).length, 0);

  ctx.plane.failWrite = () => Object.assign(new Error("PATCH -> no answer within 5000 ms"), { code: "request_timeout" });
  await ctx.run();
  const owed = pendingPublishes(journal.read());
  assert.equal(owed.length, 1);
  assert.equal(owed[0].writeKnown, false);

  // Next tick: the write did not land (still Todo), so the owed publish is dropped and the ticket dispatched afresh.
  ctx.plane.failWrite = null;
  const retry = await ctx.run();
  const solo = scopeOf(retry, "solo-pm");
  assert.equal(solo.republishes[0].result, "dropped");
  assert.deepEqual(solo.dispatches.map((d) => d.result), ["dispatched"]);
  assert.equal(ctx.publish.sent.length, 1);
  assert.equal(pendingPublishes(journal.read()).length, 0);
});

test("a candidate that changed between listing and dispatch is not dispatched", async () => {
  const boards = { [SOLO]: { issues: [issue({ seq: 1, labels: ["lifecycle:triaged"] })] } };
  const { plane, publish, run } = setup({ boards, board: "SOLO" });
  const read = plane.issue.bind(plane);
  plane.issue = async (id, ws, board) => {
    plane.boards[SOLO].issues.get(id).labels.push(labelId("lifecycle:needs-input"));
    return read(id, ws, board);
  };
  const report = await run();
  const d = scopeOf(report, "solo-pm").dispatches[0];
  assert.equal(d.result, "skipped");
  assert.match(d.why, /changed since the listing: held/);
  assert.deepEqual(plane.writes(), []);
  assert.deepEqual(publish.sent, []);
});

test("a board that cannot be read is a scope error, not a crash, and other boards still tick", async () => {
  const boards = { [SOLO]: { issues: [issue({ seq: 1, labels: ["lifecycle:triaged"] })] } };
  const { publish, run } = setup({ boards }); // TOLT and OTHER are not in the fake: 404
  const report = await run();
  assert.equal(report.ok, false);
  assert.match(scopeOf(report, "tolt-pm").errors[0], /cannot read board TOLT/);
  assert.match(scopeOf(report, "other-pm").errors[0], /cannot read board OTH/);
  assert.deepEqual(scopeOf(report, "solo-pm").dispatches.map((d) => d.result), ["dispatched"]);
  assert.equal(publish.sent.length, 1);
});

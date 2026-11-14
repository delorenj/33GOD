import { test } from "node:test";
import assert from "node:assert/strict";

import { laneModel } from "../lifecycle.mjs";
import { candidatesOf, compareCandidates, dispatchGuard, normalizeTicket, pickDispatches, repairsFor, slotsOf } from "../select.mjs";
import { STATES, LABEL_NAMES, issue, labelId } from "./helpers.mjs";

const lanes = laneModel(STATES);
const labelNameOf = new Map(LABEL_NAMES.map((n) => [labelId(n), n]));
const t = (spec) => normalizeTicket(issue(spec), { lanes, labelNameOf, identifier: "T" });

test("slot math: only plain In Progress tickets occupy a slot", () => {
  const tickets = [
    t({ seq: 1, state: "ip" }),
    t({ seq: 2, state: "ip", labels: ["lifecycle:review"] }),
    t({ seq: 3, state: "ip", labels: ["lifecycle:needs-input"] }),
    t({ seq: 4, state: "ip", labels: ["lifecycle:blocked"] }),
    t({ seq: 5, state: "ip", labels: ["agent:failed"] }),
    t({ seq: 6, state: "todo", labels: ["lifecycle:triaged"] }),
    t({ seq: 7, state: "done", labels: ["agent:working"] }),
  ];
  const slots = slotsOf(2, tickets);
  assert.deepEqual(slots.occupied.map((x) => x.key), ["T-1"]);
  assert.equal(slots.free, 1);
  assert.equal(slots.overLimit, 0);
});

test("slot math: over the limit drains (free 0, never negative, nothing evicted)", () => {
  const tickets = [1, 2, 3, 4].map((seq) => t({ seq, state: "ip", labels: ["lifecycle:triaged"] }));
  assert.deepEqual(slotsOf(2, tickets), { wip: 2, occupied: tickets, free: 0, overLimit: 2 });
  assert.equal(slotsOf(0, []).free, 0);
  assert.equal(slotsOf(3, tickets.slice(0, 1)).free, 2);
});

test("ordering: sort_order, then priority (urgent>high>medium>low>none), then sequence id", () => {
  const a = t({ seq: 10, sort: 200, priority: "urgent" });
  const b = t({ seq: 11, sort: 100, priority: "none" });
  const c = t({ seq: 12, sort: 100, priority: "high" });
  const d = t({ seq: 9, sort: 100, priority: "high" });
  const e = t({ seq: 8, sort: 100, priority: "low" });
  const f = t({ seq: 7, sort: 100, priority: "medium" });
  const order = [a, b, c, d, e, f].sort(compareCandidates).map((x) => x.key);
  assert.deepEqual(order, ["T-9", "T-12", "T-7", "T-8", "T-11", "T-10"]);
});

test("guards: untriaged, held, working, epic containers and non-Todo are excluded", () => {
  const cases = [
    [{ seq: 1, labels: ["lifecycle:triaged"] }, null],
    [{ seq: 2, labels: [] }, /not triaged/],
    [{ seq: 3, labels: ["lifecycle:triaged", "lifecycle:needs-input"] }, /held \(lifecycle:needs-input\)/],
    [{ seq: 4, labels: ["lifecycle:triaged", "lifecycle:blocked"] }, /held \(lifecycle:blocked\)/],
    [{ seq: 5, labels: ["lifecycle:triaged", "agent:failed"] }, /held \(agent:failed\)/],
    [{ seq: 6, labels: ["lifecycle:triaged", "agent:working"] }, /agent:working/],
    [{ seq: 7, labels: ["lifecycle:triaged", "epic"] }, /epic container/],
    [{ seq: 8, labels: ["lifecycle:triaged", "epic:big-thing"] }, /epic container/],
    [{ seq: 9, state: "backlog", labels: ["lifecycle:triaged"] }, /not in Todo/],
    [{ seq: 10, state: "ip", labels: ["lifecycle:triaged"] }, /not in Todo/],
  ];
  for (const [spec, want] of cases) {
    const why = dispatchGuard(t(spec));
    if (want === null) assert.equal(why, null, `T-${spec.seq}`);
    else assert.match(why, want, `T-${spec.seq}`);
  }
  const { candidates, excluded } = candidatesOf(cases.map(([spec]) => t(spec)));
  assert.deepEqual(candidates.map((x) => x.key), ["T-1"]);
  // Non-Todo tickets are not candidates and not reported as Todo exclusions.
  assert.equal(excluded.length, 7);
});

test("pickDispatches: fills free slots in order, skips blocked, never reads relations past the last pick", async () => {
  const list = [1, 2, 3, 4].map((seq) => t({ seq, labels: ["lifecycle:triaged"] }));
  const asked = [];
  const blockerOf = async (x) => {
    asked.push(x.key);
    return x.key === "T-1" ? "blocked by T-99 (Todo)" : null;
  };
  const r = await pickDispatches(list, 2, blockerOf);
  assert.deepEqual(r.picked.map((x) => x.key), ["T-2", "T-3"]);
  assert.deepEqual(r.blocked.map((x) => x.ticket.key), ["T-1"]);
  assert.deepEqual(r.waiting.map((x) => x.key), ["T-4"]);
  assert.deepEqual(asked, ["T-1", "T-2", "T-3"]);

  const none = await pickDispatches(list, 0, async () => assert.fail("no relation read on a full scope"));
  assert.equal(none.picked.length, 0);
  assert.equal(none.waiting.length, 4);
});

test("invariant repair: review outside In Progress, working on Done/Cancelled", () => {
  const repairs = repairsFor([
    t({ seq: 1, state: "todo", labels: ["lifecycle:review", "lifecycle:triaged"] }),
    t({ seq: 2, state: "done", labels: ["agent:working"] }),
    t({ seq: 3, state: "cancel", labels: ["agent:working", "lifecycle:review"] }),
    t({ seq: 4, state: "ip", labels: ["lifecycle:review", "agent:working"] }),
    t({ seq: 5, state: "backlog", labels: ["agent:working"] }),
  ]);
  assert.deepEqual(
    repairs.map((r) => [r.ticket.key, r.remove]),
    [
      ["T-1", ["lifecycle:review"]],
      ["T-2", ["agent:working"]],
      ["T-3", ["lifecycle:review", "agent:working"]],
    ],
  );
});

test("laneModel: stock five lanes, and a board without an In Progress lane says so", () => {
  assert.equal(lanes.inProgress.id, "s-ip");
  assert.deepEqual(lanes.todoStateIds, ["s-todo"]);
  assert.deepEqual(lanes.problems, []);
  const legacy = laneModel([
    { id: "a", name: "Todo", group: "unstarted" },
    { id: "b", name: "Doing", group: "started" },
    { id: "c", name: "QA", group: "started" },
  ]);
  assert.equal(legacy.inProgress, null);
  assert.equal(legacy.laneOf.get("c"), "started");
  assert.match(legacy.problems.join(), /no In Progress lane/);
});

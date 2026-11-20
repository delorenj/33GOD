// Two gaps the event path left after ADR 0002 (adversarial review, 2026-11-20):
//   1. tick.lock: the Candybar tick on the :x0 mark gave up at once when a board run held the lock, costing every
//      other board a whole backstop period. It now waits, bounded (acquireLockWait).
//   2. agent activity: a board-turn candidate skipped as "turn live" for recent agent activity (liveness rules 3,
//      4) had no event to wake its board when that 30-minute window ended, while `krebs status` projected the
//      turn at that moment. The tick report now carries the window end, and the watcher re-arms for it.

import { test } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { writeFileSync } from "node:fs";

import { loadBloodbank } from "../deps.mjs";
import { scopesFromRegistry } from "../registry.mjs";
import { runTick } from "../run.mjs";
import { MemoryJournal } from "../journal.mjs";
import { acquireLock, acquireLockWait } from "../lock.mjs";
import { activityWindows } from "../quiet.mjs";
import { Watcher, outcomeOfReport } from "../watch.mjs";
import { FakePlane, NOW, fakePublisher, issue, registryFixture, tempDir } from "./helpers.mjs";

const { fleet, nats, registry: bbRegistry } = loadBloodbank();
const NOW_MS = NOW.getTime();
const minsAgo = (m) => new Date(NOW_MS - m * 60000).toISOString();

test("acquireLockWait: a lock held for a moment is waited for, not reported busy", async () => {
  let t = 0;
  let freeAt = 1200;
  const lock = await acquireLockWait("x", {
    waitMs: 45_000,
    pollMs: 250,
    now: () => t,
    sleep: async (ms) => {
      t += ms;
    },
    acquire: () => (t >= freeAt ? { release() {} } : null),
  });
  assert.ok(lock, "taken once the holder let go");
  assert.equal(t, 1250, "polled every 250 ms");
  freeAt = Infinity;
  t = 0;
  const none = await acquireLockWait("x", { waitMs: 1000, pollMs: 300, now: () => t, sleep: async (ms) => void (t += ms), acquire: () => null });
  assert.equal(none, null, "still held at the deadline: busy");
  assert.equal(t, 1000, "never waits past the deadline");
});

test("acquireLockWait: a real lock file held by a live process, then released", async () => {
  const path = join(tempDir(), "tick.lock");
  const held = acquireLock(path);
  assert.ok(held);
  assert.equal(await acquireLockWait(path, { waitMs: 300, pollMs: 50 }), null, "this process holds it (alive)");
  setTimeout(() => held.release(), 100);
  const got = await acquireLockWait(path, { waitMs: 3000, pollMs: 50 });
  assert.ok(got, "free after the release");
  got.release();
  writeFileSync(path, "999999999");
  const stale = await acquireLockWait(path, { waitMs: 0 });
  assert.ok(stale, "a dead holder's lock is taken over without waiting");
  stale.release();
});

test("runTick: a candidate skipped for recent agent activity carries the moment that window ends", async () => {
  const plane = new FakePlane({ "b-other": { issues: [issue({ seq: 2, state: "todo", labels: [], updated: minsAgo(60) })] } });
  const registry = registryFixture();
  const { scopes, skipped } = scopesFromRegistry(registry, { activation: bbRegistry.bloodbankActivation, executionMode: () => "legacy", board: "OTH" });
  const until = NOW_MS + 12 * 60000;
  const report = await runTick({
    registry, scopes, skipped, plane, fleet, nats, publish: fakePublisher(), journal: new MemoryJournal(), now: () => NOW, timeZone: "America/New_York",
    liveness: async () => ({ live: true, why: "agent activity on the ticket 18m ago", busyUntil: until }),
    scopeBusy: async () => ({ busy: false, turns: [], why: "none" }),
  });
  const t = report.scopes[0].triage[0];
  assert.equal(t.result, "skipped");
  assert.equal(t.busyUntil, new Date(until).toISOString());
  const windows = activityWindows(report.scopes, NOW_MS);
  assert.deepEqual(windows.map((w) => [w.key, w.kind, w.boardId, w.eligibleAt]), [["OTH-2", "triage", "b-other", until + 1000]]);
});

test("activityWindows: only skipped triage/review entries with a future window end, earliest first", () => {
  const iso = (m) => new Date(NOW_MS + m * 60000).toISOString();
  const scopes = [
    {
      identifier: "PX",
      boardId: "b-px",
      triage: [
        { key: "PX-1", result: "skipped", busyUntil: iso(20) },
        { key: "PX-2", result: "skipped", busyUntil: iso(-1) },
        { key: "PX-3", result: "published" },
        { key: "PX-4", result: "skipped", why: "scope busy" },
      ],
      reviews: [{ key: "PX-5", result: "skipped", busyUntil: iso(5) }],
    },
    { identifier: "OTH", boardId: "b-oth" },
  ];
  assert.deepEqual(activityWindows(scopes, NOW_MS).map((w) => [w.key, w.kind]), [["PX-5", "review"], ["PX-1", "triage"]]);
  assert.deepEqual(activityWindows(undefined, NOW_MS), []);
});

test("watcher: a tick report's activity window re-arms the board for the moment it ends", async () => {
  let t = NOW_MS;
  const timers = [];
  const runs = [];
  const at = NOW_MS + 7 * 60000;
  const w = new Watcher({
    now: () => t,
    setTimer: (ms, fn) => {
      const h = { due: t + ms, fn };
      timers.push(h);
      return h;
    },
    clearTimer: (h) => timers.splice(timers.indexOf(h), 1),
    run: async (board, { trigger }) => {
      runs.push([t, trigger]);
      return runs.length === 1 ? outcomeOfReport(0, { ok: true, scopes: [], quiet: [{ key: "PX-1", kind: "triage", eligibleAt: at }] }) : { ok: true };
    },
  });
  w.signal("b-px", "turn-ended", { delayMs: 8000 });
  for (let i = 0; i < 5 && timers.length; i++) {
    timers.sort((a, b) => a.due - b.due);
    const next = timers.shift();
    t = next.due;
    next.fn();
    await new Promise((r) => setImmediate(r));
  }
  assert.deepEqual(runs, [
    [NOW_MS + 8000, "turn-ended"],
    [at, "quiet-window"],
  ]);
});

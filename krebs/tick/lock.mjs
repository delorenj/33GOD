// One tick at a time per host. Candybar does not start a fire while the last
// one runs, but a hand-run `krebs tick` can overlap a scheduled one, and two
// dispatchers reading the same free slot would both fill it.

import { closeSync, mkdirSync, openSync, readFileSync, unlinkSync, writeSync } from "node:fs";
import { dirname } from "node:path";

function alive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err.code === "EPERM";
  }
}

/** Take the lock, or return null when a live process holds it. A dead holder's lock is taken over. */
export function acquireLock(path) {
  mkdirSync(dirname(path), { recursive: true });
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const fd = openSync(path, "wx");
      writeSync(fd, String(process.pid));
      closeSync(fd);
      return {
        path,
        release() {
          try {
            if (readFileSync(path, "utf8").trim() === String(process.pid)) unlinkSync(path);
          } catch {
            // already gone
          }
        },
      };
    } catch (err) {
      if (err.code !== "EEXIST") throw err;
      let holder = NaN;
      try {
        holder = Number(readFileSync(path, "utf8").trim());
      } catch {
        // vanished between open and read: retry
      }
      if (Number.isInteger(holder) && holder > 0 && alive(holder)) return null;
      try {
        unlinkSync(path);
      } catch {
        // someone else took it over first
      }
    }
  }
  return null;
}

/**
 * How long a tick waits for a held tick.lock before it reports busy (ADR 0002). Since `krebs watch` runs
 * board ticks on events, the Candybar tick on the :x0 mark can meet a board run holding the lock (a board
 * run takes about a second). Returning busy at once would cost every other board a whole backstop period,
 * so the tick waits: a bounded retry inside one invocation, not a schedule.
 */
export const LOCK_WAIT_MS = 45_000;
const LOCK_POLL_MS = 250;

/** acquireLock, retried every `pollMs` for up to `waitMs`. Resolves to the lock, or null when it stayed held. */
export async function acquireLockWait(path, { waitMs = LOCK_WAIT_MS, pollMs = LOCK_POLL_MS, now = Date.now, sleep = (ms) => new Promise((r) => setTimeout(r, ms)), acquire = acquireLock } = {}) {
  const deadline = now() + waitMs;
  for (;;) {
    const lock = acquire(path);
    if (lock || now() >= deadline) return lock;
    await sleep(Math.min(pollMs, Math.max(0, deadline - now())));
  }
}

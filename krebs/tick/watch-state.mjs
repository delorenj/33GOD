// The watcher's heartbeat file: ~/.local/state/krebs/watch.json (KREBS_STATE_DIR relocates it).
// `krebs watch` rewrites it every 30 s; `krebs status` reads it to say whether the event path is alive
// (the ETA math differs: events react in minutes, the backstop tick every ten).

import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { stateDir } from "./journal.mjs";

/** A heartbeat older than this means the watcher is not running (it beats every 30 s). */
export const WATCH_STALE_MS = 2 * 60 * 1000;

export function watchStatePath(env = process.env) {
  return join(stateDir(env), "watch.json");
}

export function writeWatchState(state, { path = watchStatePath(), now = () => new Date() } = {}) {
  mkdirSync(join(path, ".."), { recursive: true });
  const tmp = `${path}.${process.pid}.tmp`;
  writeFileSync(tmp, `${JSON.stringify({ ...state, heartbeatAt: now().toISOString() }, null, 2)}\n`, "utf8");
  renameSync(tmp, path);
}

function pidAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err.code === "EPERM";
  }
}

/** The watcher as `krebs status` sees it: {alive, why, state}. Never throws. */
export function readWatchState({ path = watchStatePath(), nowMs = Date.now(), alive = pidAlive } = {}) {
  let state;
  try {
    state = JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return { alive: false, why: "no heartbeat file (krebs-watch.service is not running or never started)", state: null };
  }
  const beat = Date.parse(state?.heartbeatAt ?? "");
  if (!Number.isFinite(beat) || nowMs - beat > WATCH_STALE_MS) return { alive: false, why: `last heartbeat ${state?.heartbeatAt ?? "never"}`, state };
  if (!Number.isInteger(state.pid) || !alive(state.pid)) return { alive: false, why: `pid ${state?.pid} is gone`, state };
  return { alive: true, why: "heartbeat fresh", state };
}

// The tick journal: one JSON line per action, append-only.
//
// Default path: $XDG_STATE_HOME/krebs/tick-journal.jsonl (~/.local/state/...),
// KREBS_STATE_DIR relocates the directory, --journal names the file.
//
// A dispatch is journaled in up to three lines sharing one dispatch_id:
//   dispatch.intent   before the Plane write; carries the full command (the
//                     publish options minus the NATS host), so a republish is
//                     byte-identical (the gateway journals command_id plus a
//                     digest of the whole envelope and rejects a same-id
//                     command whose digest differs);
//   dispatch.write    the one Plane write: ok true/false;
//   dispatch.publish  the bus publish: ok true/false. Repeated on republish.
// and closed early by dispatch.dropped when a pending publish is abandoned.
//
// A dispatch is pending (republished on the next tick, same command id) when
// its write succeeded and no publish has, or when only its intent is on record
// (the process died between the write and journaling it); the tick then checks
// the ticket live before republishing.

import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";

export const PENDING_MAX_AGE_MS = 24 * 60 * 60 * 1000;

export function stateDir(env = process.env) {
  if (env.KREBS_STATE_DIR) return env.KREBS_STATE_DIR;
  return join(env.XDG_STATE_HOME || join(homedir(), ".local", "state"), "krebs");
}

export function defaultJournalPath(env = process.env) {
  return join(stateDir(env), "tick-journal.jsonl");
}

export class Journal {
  constructor(path) {
    this.path = path;
  }

  /** Every parseable line; a torn or foreign line is skipped, never fatal. */
  read() {
    if (!existsSync(this.path)) return [];
    const out = [];
    for (const line of readFileSync(this.path, "utf8").split("\n")) {
      if (!line.trim()) continue;
      try {
        const entry = JSON.parse(line);
        if (entry && typeof entry === "object") out.push(entry);
      } catch {
        // a torn last line from a crash: ignore
      }
    }
    return out;
  }

  append(entry) {
    mkdirSync(dirname(this.path), { recursive: true });
    appendFileSync(this.path, `${JSON.stringify(entry)}\n`, "utf8");
  }
}

/** A journal that records in memory only (dry runs never touch the file). */
export class MemoryJournal {
  constructor(entries = []) {
    this.entries = [...entries];
  }

  read() {
    return [...this.entries];
  }

  append(entry) {
    this.entries.push(entry);
  }
}

/**
 * Dispatches whose publish is still owed, oldest first.
 * Each: {dispatchId, commandId, agentId, boardId, workspace, ticketId, key,
 *        command, since, writeKnown, attempts}
 */
export function pendingPublishes(entries) {
  const byId = new Map();
  for (const e of entries) {
    if (!e?.dispatch_id || typeof e.action !== "string" || !e.action.startsWith("dispatch.")) continue;
    let d = byId.get(e.dispatch_id);
    if (!d) {
      d = { dispatchId: e.dispatch_id, intent: null, write: null, published: false, dropped: false, attempts: 0 };
      byId.set(e.dispatch_id, d);
    }
    // A new intent under the same dispatch id (the ticket is dispatched again at
    // the same version, e.g. after its owed publish was dropped) starts over.
    if (e.action === "dispatch.intent") Object.assign(d, { intent: e, write: null, published: false, dropped: false, attempts: 0 });
    else if (e.action === "dispatch.write") d.write = e;
    else if (e.action === "dispatch.publish") {
      d.attempts++;
      if (e.ok) d.published = true;
    } else if (e.action === "dispatch.dropped") d.dropped = true;
  }
  const out = [];
  for (const d of byId.values()) {
    if (!d.intent || d.published || d.dropped) continue;
    // A refused write dispatched nothing. A write that failed without a verdict
    // (timeout, 5xx, a delta Plane did not echo) may have applied: keep it
    // pending, unverified, so the next tick checks the ticket live.
    if (d.write && !d.write.ok && d.write.definitive !== false) continue;
    out.push({
      dispatchId: d.dispatchId,
      commandId: d.intent.command_id,
      agentId: d.intent.agent_id,
      boardId: d.intent.board_id,
      workspace: d.intent.workspace,
      ticketId: d.intent.ticket_id,
      key: d.intent.key,
      command: d.intent.command,
      since: d.intent.ts,
      writeKnown: Boolean(d.write?.ok),
      attempts: d.attempts,
    });
  }
  out.sort((a, b) => String(a.since).localeCompare(String(b.since)));
  return out;
}

/**
 * The start commands krebs itself sent, per ticket id: [{commandId, at, kind}],
 * kind "dispatch", "triage" or "review". The gateway publishes invocation.started only
 * when a turn gets a slot (measured waits up to 55 min), so a command krebs
 * sent with no end on record yet is queued or running: liveness counts it.
 */
export function sentCommands(entries) {
  const intents = new Map(); // dispatch_id -> intent
  const out = new Map();
  const add = (ticketId, cmd) => {
    if (!ticketId || !cmd.commandId) return;
    const list = out.get(ticketId) ?? [];
    list.push(cmd);
    out.set(ticketId, list);
  };
  for (const e of entries) {
    if (e?.action === "dispatch.intent" && e.dispatch_id) intents.set(e.dispatch_id, e);
    else if (e?.action === "dispatch.publish" && e.ok === true) {
      const intent = intents.get(e.dispatch_id);
      add(intent?.ticket_id, { commandId: e.command_id, at: e.ts, kind: "dispatch" });
    } else if (e?.action === "triage.publish" && e.ok === true) {
      add(e.ticket_id, { commandId: e.command_id, at: e.ts, kind: "triage" });
    } else if (e?.action === "review.publish" && e.ok === true) {
      add(e.ticket_id, { commandId: e.command_id, at: e.ts, kind: "review" });
    }
  }
  return out;
}

/** Successful orphan releases per ticket id since `sinceMs` (the loop guard's count). */
export function releaseCounts(entries, sinceMs) {
  const counts = new Map();
  for (const e of entries) {
    if (e?.action !== "orphan.release" || e.ok !== true || !e.ticket_id) continue;
    const t = Date.parse(e.ts ?? "");
    if (!Number.isFinite(t) || t < sinceMs) continue;
    counts.set(e.ticket_id, (counts.get(e.ticket_id) ?? 0) + 1);
  }
  return counts;
}

/**
 * Command ids of catch-up triages already published (action triage.publish,
 * ok true). A triage command id is derived from board + ticket + updated_at, so
 * one id is one ticket version: a version in this set is never triaged again.
 */
export function triagedCommandIds(entries) {
  const ids = new Set();
  for (const e of entries) {
    if (e?.action === "triage.publish" && e.ok === true && e.command_id) ids.add(e.command_id);
  }
  return ids;
}

/**
 * Review turns already published per ticket version ("<ticket id>|<updated_at>"):
 * [{attempt, at, commandId}], oldest first. A review that ended without a
 * verdict leaves the version unchanged, so the tick sends it again after a
 * cool-down, up to a few attempts (each attempt is its own command id).
 */
export function reviewAttempts(entries) {
  const out = new Map();
  for (const e of entries) {
    if (e?.action !== "review.publish" || e.ok !== true || !e.ticket_id) continue;
    const key = `${e.ticket_id}|${e.ticket_updated_at ?? ""}`;
    const list = out.get(key) ?? [];
    list.push({ attempt: Number(e.attempt) || 1, at: e.ts, commandId: e.command_id });
    out.set(key, list);
  }
  for (const list of out.values()) list.sort((a, b) => a.attempt - b.attempt);
  return out;
}

/**
 * The kind of the last board turn each scope was sent ("<agent>|<board>" -> "triage" | "review"):
 * when a scope has both kinds waiting, the tick alternates, so a review backlog never starves
 * triage and a triage stream never starves reviews.
 */
export function lastBoardTurns(entries) {
  const out = new Map();
  for (const e of entries) {
    if (e?.ok !== true || (e.action !== "triage.publish" && e.action !== "review.publish")) continue;
    out.set(`${e.agent_id}|${e.board_id}`, e.action === "review.publish" ? "review" : "triage");
  }
  return out;
}

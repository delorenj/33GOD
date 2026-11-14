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

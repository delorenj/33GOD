// Board-turn episodes: when did THIS stretch of a ticket's life in a stage begin?
//
// A review or triage turn that ends with no verdict must be asked again a bounded
// number of times, then parked. "Bounded" needs a counter, and the counter needs a
// key that the turn itself cannot change. The ticket's updated_at is not one: the
// pickup chip adds agent:working when a turn starts and removes it when the turn
// ends, so every turn, even one whose model call was refused, leaves a new
// updated_at behind. Keyed on it, every send was "attempt 1" for ever
// (33GOD-33: 50 review turns in 42 hours; HEYMA-39: 12 triage turns in 8 hours).
//
// An episode is keyed on the ticket's own activity log instead, which says what
// actually happened to it. It begins at the latest of:
//   review  lifecycle:review added (the implementer's handback);
//   triage  the ticket entered its current Todo state, or was created in it, or
//           lifecycle:triaged was removed (the owner asked for a re-triage);
//   both    a hold label removed (agent:failed, needs-input, blocked, human): the
//           person who cleared Krebs's park, or answered the question, restarts the count.
// Attempts are the board turns Krebs sent for the ticket since that moment. The
// agent:working add/remove pairs the chip writes are in no list above, so they
// cannot reset anything.

import { HOLD_LABELS, LABEL } from "./lifecycle.mjs";

const MAX_PAGES = 20;

const ms = (iso) => {
  const n = Date.parse(iso ?? "");
  return Number.isFinite(n) ? n : null;
};

/**
 * The latest episode start in a ticket's activity rows, in epoch ms, or -Infinity when
 * the log holds no entry event (then every send in the look-back window counts).
 * Pure. `stage` is "review" or "triage"; `stateName` is the ticket's current state name.
 */
export function episodeStartMs(activities, { stage, stateName }) {
  let start = Number.NEGATIVE_INFINITY;
  for (const a of activities ?? []) {
    const at = ms(a?.created_at);
    if (at === null) continue;
    const field = a.field ?? null;
    const added = String(a.new_value ?? "");
    const removed = String(a.old_value ?? "");
    let begins = false;
    if (field === "labels") {
      if (stage === "review" && added === LABEL.review) begins = true;
      if (stage === "triage" && removed === LABEL.triaged && !added) begins = true;
      if (HOLD_LABELS.includes(removed) && !added) begins = true;
    } else if (field === "state") {
      if (stage === "triage" && stateName && added === stateName) begins = true;
    } else if (field === null && a.verb === "created") {
      if (stage === "triage") begins = true;
    }
    if (begins && at > start) start = at;
  }
  return start;
}

/** Every activity row of one ticket, oldest first (Plane pages them; the cursor is followed). */
export async function activitiesOf(plane, ticketId, ws, board) {
  if (typeof plane.activities === "function") return plane.activities(ticketId, ws, board);
  const base = `${plane.boardUrl(ws, board)}/issues/${ticketId}/activities/?per_page=500`;
  const rows = [];
  let cursor = null;
  for (let page = 0; page < MAX_PAGES; page++) {
    const res = await plane.get(cursor ? `${base}&cursor=${encodeURIComponent(cursor)}` : base);
    if (Array.isArray(res)) return res;
    rows.push(...(res?.results ?? []));
    if (!res?.next_page_results || !res?.next_cursor) return rows;
    cursor = res.next_cursor;
  }
  throw new Error(`activity log of ${ticketId} longer than ${MAX_PAGES} pages`);
}

/**
 * The episode of one ticket for one stage: {ok: true, startMs} or {ok: false, why}.
 * Unreadable means the caller leaves the ticket alone this tick: it neither sends
 * (a loop is the thing being prevented) nor parks (a park is a Plane write made on
 * a count that could not be checked).
 */
export async function readEpisode(plane, { ticket, stage, ws, board }) {
  try {
    const rows = await activitiesOf(plane, ticket.id, ws, board);
    return { ok: true, startMs: episodeStartMs(rows, { stage, stateName: ticket.stateName ?? null }) };
  } catch (err) {
    return { ok: false, why: `activity log unreadable (${err instanceof Error ? err.message : String(err)})` };
  }
}

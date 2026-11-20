// The pure half of a tick: given one scope's tickets, what to repair, how many
// slots are free, and which Todo tickets may be dispatched in what order.
// No I/O except the injected blocker lookup in pickDispatches.

import { LABEL, heldBy, isContainer, normalizeNames, priorityRank } from "./lifecycle.mjs";

/** Ids from a Plane list that may hold bare ids or expanded objects. */
export function idsOf(values) {
  return (values ?? []).map((v) => (typeof v === "string" ? v : v?.id)).filter(Boolean);
}

/**
 * One Plane issue as the tick sees it.
 * lanes: laneModel(states); labelNameOf: Map(label id -> name).
 */
export function normalizeTicket(issue, { lanes, labelNameOf, identifier }) {
  const stateId = typeof issue.state === "object" && issue.state !== null ? issue.state.id : issue.state;
  const labelIds = idsOf(issue.labels);
  const labels = normalizeNames(labelIds.map((id) => labelNameOf.get(id)).filter(Boolean));
  const seq = issue.sequence_id;
  const sortOrder = Number(issue.sort_order);
  return {
    id: issue.id,
    seq: Number.isFinite(Number(seq)) ? Number(seq) : null,
    key: identifier && seq !== undefined && seq !== null ? `${identifier}-${seq}` : String(seq ?? issue.id),
    title: issue.name ?? "",
    stateId,
    stateName: lanes.nameOf.get(stateId) ?? null,
    lane: lanes.laneOf.get(stateId) ?? "other",
    labels,
    labelIds,
    sortOrder: Number.isFinite(sortOrder) ? sortOrder : Number.POSITIVE_INFINITY,
    priority: issue.priority ?? "none",
    startDate: issue.start_date ?? null,
    updatedAt: issue.updated_at ?? null,
    archived: Boolean(issue.archived_at),
    draft: Boolean(issue.is_draft),
  };
}

/** spec invariants: lifecycle:review only in In Progress; agent:working never on Done/Cancelled. */
export function repairsFor(tickets) {
  const out = [];
  for (const ticket of tickets) {
    const remove = [];
    const why = [];
    if (ticket.labels.includes(LABEL.review) && ticket.lane !== "started") {
      remove.push(LABEL.review);
      why.push(`lifecycle:review outside In Progress (${ticket.stateName ?? ticket.lane})`);
    }
    if (ticket.labels.includes(LABEL.working) && ticket.lane === "terminal") {
      remove.push(LABEL.working);
      why.push(`agent:working on a ${ticket.stateName ?? "terminal"} ticket`);
    }
    if (remove.length) out.push({ ticket, remove, why: why.join("; ") });
  }
  return out;
}

/** spec slots.occupied_by: In Progress AND NOT lifecycle:review AND NOT any hold label. */
export function occupies(ticket) {
  return ticket.lane === "started" && !ticket.labels.includes(LABEL.review) && heldBy(ticket.labels).length === 0;
}

/** Slot math for one scope. Over the limit drains: free is 0 and nothing is evicted. */
export function slotsOf(wip, tickets) {
  const occupied = tickets.filter(occupies);
  return {
    wip,
    occupied,
    free: Math.max(0, wip - occupied.length),
    overLimit: Math.max(0, occupied.length - wip),
  };
}

/** Why a ticket may not be dispatched on its labels and lane alone, or null. Relations are checked later. */
export function dispatchGuard(ticket) {
  if (ticket.archived) return "archived";
  if (ticket.draft) return "draft";
  if (ticket.lane !== "todo") return `not in Todo (${ticket.stateName ?? ticket.lane})`;
  const holds = heldBy(ticket.labels);
  if (holds.length) return `held (${holds.join(", ")})`;
  if (!ticket.labels.includes(LABEL.triaged)) return "not triaged (no lifecycle:triaged)";
  if (ticket.labels.includes(LABEL.working)) return "agent:working (a turn is running on it)";
  if (isContainer(ticket.labels)) return "epic container";
  return null;
}

/** spec dispatch order: Plane sort_order (the PM's Todo order), then priority, then sequence id. */
export function compareCandidates(a, b) {
  if (a.sortOrder !== b.sortOrder) return a.sortOrder < b.sortOrder ? -1 : 1;
  const pa = priorityRank(a.priority);
  const pb = priorityRank(b.priority);
  if (pa !== pb) return pa - pb;
  const sa = a.seq ?? Number.POSITIVE_INFINITY;
  const sb = b.seq ?? Number.POSITIVE_INFINITY;
  if (sa !== sb) return sa < sb ? -1 : 1;
  return String(a.id) < String(b.id) ? -1 : String(a.id) > String(b.id) ? 1 : 0;
}

/** The scope's Todo tickets split into ordered candidates and label-level exclusions. */
export function candidatesOf(tickets) {
  const candidates = [];
  const excluded = [];
  for (const ticket of tickets) {
    if (ticket.lane !== "todo") continue;
    const why = dispatchGuard(ticket);
    if (why) excluded.push({ ticket, why });
    else candidates.push(ticket);
  }
  candidates.sort(compareCandidates);
  excluded.sort((a, b) => compareCandidates(a.ticket, b.ticket));
  return { candidates, excluded };
}

/**
 * Walk the ordered candidates and pick up to `free`, skipping any with an open
 * blocking relation. `blockerOf(ticket)` resolves to null (free to go) or a
 * reason string. Relations are only read for tickets the walk reaches, so a
 * full scope costs no relation reads at all.
 */
export async function pickDispatches(candidates, free, blockerOf) {
  const picked = [];
  const blocked = [];
  let i = 0;
  for (; i < candidates.length && picked.length < free; i++) {
    const ticket = candidates[i];
    const why = await blockerOf(ticket);
    if (why) blocked.push({ ticket, why });
    else picked.push(ticket);
  }
  return { picked, blocked, waiting: candidates.slice(i) };
}

/**
 * spec orphans: a ticket that may have nobody on it, judged on labels, lane and
 * quiet time alone (the caller then asks Candystore whether a turn is live).
 *
 *   "release"        In Progress, holds a slot (no review, no hold), not an epic:
 *                    if no turn is live it goes back to Todo.
 *   "stale-working"  carries agent:working in Todo or Backlog, or in In Progress
 *                    without holding a slot (review or hold), or on an epic: if
 *                    no turn is live the label is removed.
 *
 * Returns null for everything else, and for any ticket updated within quietMs
 * (a dispatch write or a fresh turn's first edit is never second-guessed).
 */
export function orphanKind(ticket, nowMs, quietMs) {
  if (ticket.archived || ticket.draft) return null;
  const updated = Date.parse(ticket.updatedAt ?? "");
  if (!Number.isFinite(updated) || nowMs - updated <= quietMs) return null;
  const working = ticket.labels.includes(LABEL.working);
  if (ticket.lane === "started") {
    if (occupies(ticket) && !isContainer(ticket.labels)) return "release";
    return working ? "stale-working" : null;
  }
  if (working && ticket.lane !== "terminal") return "stale-working"; // Todo, Backlog, any other open lane
  return null;
}

/**
 * spec board_turns.triage_quiet_seconds: a Todo ticket unchanged this long gets a triage turn.
 * krebs is the only triage sender since the n8n Ticket Triage lane was retired (2026-11-18, ADR 0001),
 * and the quiet window only keeps it from triaging a ticket someone is still writing. Since the event
 * path (`krebs watch`, ADR 0002) debounces Plane edits itself, two minutes is enough; it was ten when
 * the only clock was a 10-minute tick. A spec test pins this number to spec/lifecycle.v2.yaml.
 */
export const TRIAGE_MIN_AGE_MS = 2 * 60 * 1000;
/** At most this many catch-up triages per scope per tick, and per tick overall. */
// One per scope per tick: a desk serializes its board turns on the board-driver lease, so two triage
// turns sent to one desk in the same instant collide and the second backs off unstamped
// (seen on navi-pm and pjangler-pm, 2026-11-14). Event-driven runs no longer serialize board turns in
// time, so the tick also refuses a board turn while one is queued or running for the scope (ADR 0002).
export const TRIAGE_SCOPE_CAP = 1;
export const TRIAGE_TICK_CAP = 6;

/**
 * Why a ticket is not a catch-up triage candidate, or null when it is. Labels
 * and lane only (the live re-read applies it again): Todo, not archived or a
 * draft, no lifecycle:triaged, no hold label, no agent:working, not an epic
 * container, and updated_at older than `minAgeMs` (a ticket with no usable
 * updated_at has no version to key a command on, so it is not eligible).
 */
export function triageGuard(ticket, nowMs, minAgeMs = TRIAGE_MIN_AGE_MS) {
  if (ticket.archived) return "archived";
  if (ticket.draft) return "draft";
  if (ticket.lane !== "todo") return `not in Todo (${ticket.stateName ?? ticket.lane})`;
  if (ticket.labels.includes(LABEL.triaged)) return "already triaged (lifecycle:triaged)";
  const holds = heldBy(ticket.labels);
  if (holds.length) return `held (${holds.join(", ")})`;
  if (ticket.labels.includes(LABEL.working)) return "agent:working (a turn is running on it)";
  if (isContainer(ticket.labels)) return "epic container";
  const updated = Date.parse(ticket.updatedAt ?? "");
  if (!Number.isFinite(updated)) return "no updated_at";
  if (nowMs - updated <= minAgeMs) return `updated within the last ${Math.round(minAgeMs / 60000)} minutes`;
  return null;
}

/** Oldest updated_at first, then sequence id, then id. */
export function compareTriage(a, b) {
  const ua = Date.parse(a.updatedAt ?? "");
  const ub = Date.parse(b.updatedAt ?? "");
  if (ua !== ub) return ua < ub ? -1 : 1;
  const sa = a.seq ?? Number.POSITIVE_INFINITY;
  const sb = b.seq ?? Number.POSITIVE_INFINITY;
  if (sa !== sb) return sa < sb ? -1 : 1;
  return String(a.id) < String(b.id) ? -1 : String(a.id) > String(b.id) ? 1 : 0;
}

/** The scope's tickets that pass triageGuard, oldest first. */
export function triageCandidatesOf(tickets, nowMs, minAgeMs = TRIAGE_MIN_AGE_MS) {
  return tickets.filter((t) => triageGuard(t, nowMs, minAgeMs) === null).sort(compareTriage);
}

/**
 * spec catch_up.review: an In Progress ticket handed back with lifecycle:review
 * and unchanged this long gets a review turn from its scope's PM (the verdict
 * giver; Launch Directors are retired). Same quiet window as the orphan sweep.
 */
export const REVIEW_MIN_AGE_MS = 30 * 60 * 1000;

/**
 * Why a ticket is not a review candidate, or null when it is. Labels and lane
 * only (the live re-read applies it again, and liveness is asked before the
 * publish): In Progress, lifecycle:review, not archived or a draft, no hold
 * label, no agent:working, not an epic, updated_at older than `minAgeMs`.
 */
export function reviewGuard(ticket, nowMs, minAgeMs = REVIEW_MIN_AGE_MS) {
  if (ticket.archived) return "archived";
  if (ticket.draft) return "draft";
  if (ticket.lane !== "started") return `not In Progress (${ticket.stateName ?? ticket.lane})`;
  if (!ticket.labels.includes(LABEL.review)) return "not handed back (no lifecycle:review)";
  const holds = heldBy(ticket.labels);
  if (holds.length) return `held (${holds.join(", ")})`;
  if (ticket.labels.includes(LABEL.working)) return "agent:working (a turn is running on it)";
  if (isContainer(ticket.labels)) return "epic container";
  const updated = Date.parse(ticket.updatedAt ?? "");
  if (!Number.isFinite(updated)) return "no updated_at";
  if (nowMs - updated <= minAgeMs) return "updated within the last 30 minutes";
  return null;
}

/** The scope's tickets that pass reviewGuard, oldest first. */
export function reviewCandidatesOf(tickets, nowMs, minAgeMs = REVIEW_MIN_AGE_MS) {
  return tickets.filter((t) => reviewGuard(t, nowMs, minAgeMs) === null).sort(compareTriage);
}

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

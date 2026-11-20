// Turn liveness: is an agent turn running on this ticket right now?
//
// Candystore archives every Bloodbank event. Each agent turn on a ticket emits
// bloodbank.agent.invocation.queued when the gateway durably accepts the
// command (ADR 0001; before it waits for a slot), .started once it has a slot,
// and then .completed / .failed (or .detached when the turn hands its work to
// a background worker), all stamped
// with the ticket's correlation id: fleet.ticketCorrelationId(board, ticket),
// the same id krebs puts on a dispatch. Measured 2026-11-18: all 632 ticket
// turns of the previous 14 days have both ends on record (the longest
// delegation ran 4.6 h). Detached coding workers (codex, claude, opencode in a
// `.worktrees/<ticket-key>-*` checkout) do not carry that id; they are
// recognised by recent agent-CLI activity whose working directory names the
// ticket key.
//
// A ticket's turn is LIVE when any of these hold, else it is IDLE:
//   0. krebs itself sent a dispatch (triage, review) command for it less than
//      MAX_OPEN_TURN (MAX_OPEN_TRIAGE) ago and no end for that command is on
//      record: this bridges the gap between krebs' publish and the gateway's
//      claim (seconds, or minutes while a lane is paused), and covers gateways
//      that predate the queued event;
//   1. an invocation queued or started, whoever sent it, with no end on record,
//      less than MAX_OPEN_TURN ago (MAX_OPEN_TRIAGE for a triage or review
//      command that never started);
//   2. an invocation detached less than MAX_DETACHED ago;
//   3. any agent or conversation event on the ticket's correlation id in the
//      last QUIET window (30 min);
//   4. any agent-CLI event in the last QUIET window whose working directory
//      names the ticket key (a worker in its worktree).
// Candystore unreachable or erroring means UNKNOWN, and krebs touches nothing.

export const QUIET_MS = 30 * 60 * 1000;
/** An invocation with a start and no end older than this is presumed dead (gateway crash). */
export const MAX_OPEN_TURN_MS = 8 * 60 * 60 * 1000;
/** The same cap for a triage or review command krebs sent (grooming turns ran at most 86 min, queueing included). */
export const MAX_OPEN_TRIAGE_MS = 3 * 60 * 60 * 1000;
/** A detached turn's worker may outlive the turn; give it this long. */
export const MAX_DETACHED_MS = 24 * 60 * 60 * 1000;
/** How far back a ticket's turn history is read (for the open-turn rules and the "why"). */
export const HISTORY_MS = 7 * 24 * 60 * 60 * 1000;

const QUEUED = "bloodbank.agent.invocation.queued";
const STARTED = "bloodbank.agent.invocation.started";
/** Board-turn reasons: a queued one that never started is presumed dead after MAX_OPEN_TRIAGE. */
const SHORT_REASONS = new Set(["ticket-grooming", "ticket-review"]);
const ENDED = new Set(["bloodbank.agent.invocation.completed", "bloodbank.agent.invocation.failed"]);
const DETACHED = "bloodbank.agent.invocation.detached";
const ACTIVITY_DOMAINS = new Set(["agent", "conversation"]);

const asObject = (v) => {
  if (v && typeof v === "object") return v;
  if (typeof v === "string") {
    try {
      const parsed = JSON.parse(v);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }
  return {};
};

const ms = (iso) => {
  const n = Date.parse(iso ?? "");
  return Number.isFinite(n) ? n : null;
};

const ago = (nowMs, t) => {
  const m = Math.round((nowMs - t) / 60000);
  return m < 120 ? `${m} min ago` : `${(m / 60).toFixed(1)} h ago`;
};

/** A matcher for the ticket key inside a path: "GRUV-21" must not match "gruv-219". */
export function keyPattern(key) {
  const escaped = String(key).toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^a-z0-9])${escaped}([^0-9]|$)`);
}

function workdirOf(event) {
  const data = asObject(event.data);
  return String(data.working_directory || asObject(data.payload).cwd || "").toLowerCase();
}

function cliOf(event) {
  return asObject(event.actor).cli || event.cli || null;
}

/**
 * The verdict for one ticket, from its correlation-id events and the recent
 * events that mention its key. Pure: no I/O.
 * Returns {live: boolean, why: string, lastEnd: {type, at} | null}; a verdict that is live only because of
 * recent activity (rules 3 and 4) also carries busyUntil (ms): when that quiet window ends (for `krebs status`).
 */
export function turnState({ correlated = [], mentions = [], sent = [], key, nowMs }) {
  const invocations = new Map(); // invocation id -> {queued, started, ended, detached, reason, sender}
  let lastActivity = null;
  let lastEnd = null;
  // A turn the gateway refused before handing it to an agent (error_code
  // *_before_dispatch) did no work: its started/failed/turn events are
  // bookkeeping, not activity, so they must not hold the ticket for the quiet
  // window (BB-43: 23 refused commands kept their tickets idle 30 more minutes).
  const refused = new Set();
  for (const e of correlated) {
    const data = asObject(e.data);
    if (e.type === "bloodbank.agent.invocation.failed" && /_before_dispatch$/.test(String(data.error_code ?? ""))) {
      for (const id of [data.invocation_id, data.command_id, data.turn_id]) if (id) refused.add(id);
    }
  }
  const refusedEvent = (data) =>
    refused.size > 0 && [data.invocation_id, data.command_id, data.turn_id].some((id) => id && refused.has(id));
  for (const e of correlated) {
    const t = ms(e.time);
    if (t === null) continue;
    const data = asObject(e.data);
    const id = data.invocation_id || data.command_id || e.id;
    if (e.type === QUEUED || e.type === STARTED || ENDED.has(e.type) || e.type === DETACHED) {
      const inv = invocations.get(id) ?? { queued: null, started: null, ended: null, detached: null, reason: null, sender: null };
      inv.reason ??= asObject(data.context).reason ?? null;
      inv.sender ??= data.command_service ?? asObject(data.context).dispatcher ?? null;
      if (e.type === QUEUED) inv.queued = Math.max(inv.queued ?? 0, t);
      else if (e.type === STARTED) inv.started = Math.max(inv.started ?? 0, t);
      else if (e.type === DETACHED) inv.detached = Math.max(inv.detached ?? 0, t);
      else {
        inv.ended = Math.max(inv.ended ?? 0, t);
        if (!lastEnd || t > lastEnd.at) lastEnd = { type: e.type.split(".").pop(), at: t };
      }
      invocations.set(id, inv);
    }
    // queued is a claim, not activity: rule 1 judges it with its own cap.
    if (ACTIVITY_DOMAINS.has(e.domain ?? String(e.type).split(".")[1]) && e.type !== "bloodbank.agent.invocation.skipped" && e.type !== QUEUED && !refusedEvent(data)) {
      if (lastActivity === null || t > lastActivity) lastActivity = t;
    }
  }
  const end = lastEnd ? { type: lastEnd.type, at: new Date(lastEnd.at).toISOString() } : null;

  for (const cmd of sent) {
    const at = ms(cmd.at);
    if (at === null) continue;
    const cap = cmd.kind === "dispatch" ? MAX_OPEN_TURN_MS : MAX_OPEN_TRIAGE_MS;
    if (nowMs - at >= cap) continue;
    const inv = invocations.get(cmd.commandId);
    if (!inv || inv.ended === null) {
      const state = inv?.started != null ? "running" : inv?.queued != null ? "queued" : "queued or running";
      return { live: true, why: `krebs sent its ${cmd.kind} command ${ago(nowMs, at)}, no end on record yet (${state})`, lastEnd: end };
    }
  }

  for (const [id, inv] of invocations) {
    if (inv.started !== null && inv.ended === null && inv.detached === null && nowMs - inv.started < MAX_OPEN_TURN_MS) {
      return { live: true, why: `turn ${id} started ${ago(nowMs, inv.started)} and has not ended`, lastEnd: end };
    }
    if (inv.queued !== null && inv.started === null && inv.ended === null && inv.detached === null) {
      const cap = SHORT_REASONS.has(inv.reason) ? MAX_OPEN_TRIAGE_MS : MAX_OPEN_TURN_MS;
      if (nowMs - inv.queued < cap) {
        const who = inv.sender ? ` by ${inv.sender}` : "";
        return { live: true, why: `turn ${id} queued${who} ${ago(nowMs, inv.queued)}, waiting for a gateway slot`, lastEnd: end };
      }
    }
    if (inv.detached !== null && inv.ended === null && nowMs - inv.detached < MAX_DETACHED_MS) {
      return { live: true, why: `turn ${id} detached to a worker ${ago(nowMs, inv.detached)}`, lastEnd: end };
    }
  }
  if (lastActivity !== null && nowMs - lastActivity < QUIET_MS) {
    return { live: true, why: `agent activity on the ticket ${ago(nowMs, lastActivity)}`, lastEnd: end, busyUntil: lastActivity + QUIET_MS };
  }
  const pattern = keyPattern(key);
  for (const e of mentions) {
    const t = ms(e.time);
    if (t === null || nowMs - t >= QUIET_MS) continue;
    if (!cliOf(e)) continue;
    if (pattern.test(workdirOf(e))) {
      return { live: true, why: `a ${cliOf(e)} worker in ${workdirOf(e)} was active ${ago(nowMs, t)}`, lastEnd: end, busyUntil: t + QUIET_MS };
    }
  }
  const why = end
    ? `last turn ${end.type} ${ago(nowMs, Date.parse(end.at))}; nothing since`
    : invocations.size
      ? "its only turn on record never ended and is past the open-turn limit"
      : "no agent turn on it in the last 7 days";
  return { live: false, why, lastEnd: end };
}

/** Candystore's read API (GET /events), with a per-request timeout. */
export function candystoreClient({ base, fetchImpl = globalThis.fetch, timeoutMs = 8000 } = {}) {
  const root = String(base).replace(/\/+$/, "");
  const get = async (params) => {
    const url = `${root}/events?${new URLSearchParams(params)}`;
    const res = await fetchImpl(url, { signal: AbortSignal.timeout(timeoutMs) });
    if (!res.ok) throw new Error(`candystore ${res.status} for ${url}`);
    const body = await res.json();
    if (!Array.isArray(body?.events)) throw new Error(`candystore answered ${url} without an events list`);
    return body.events;
  };
  return {
    /** Every event on one correlation id since `fromIso`, newest first. */
    correlated: (correlationId, fromIso) => get({ correlationid: correlationId, from: fromIso, limit: "1000", tools: "1" }),
    /** One ticket's invocation lifecycle events (queued/started/ended/detached) since `fromIso`, newest first. For `krebs status`. */
    invocations: (correlationId, fromIso) =>
      get({
        correlationid: correlationId,
        from: fromIso,
        type: "bloodbank.agent.invocation.queued,bloodbank.agent.invocation.started,bloodbank.agent.invocation.completed,bloodbank.agent.invocation.failed,bloodbank.agent.invocation.detached",
        limit: "300",
      }),
    /** Recent events whose text mentions `key` (worker activity is filtered by the caller). */
    mentions: (key, fromIso) => get({ q: String(key).toLowerCase(), from: fromIso, limit: "200", tools: "1" }),
  };
}

/**
 * A liveness probe for runTick: probe({boardId, ticketId, key}) resolves to
 * {live, why, lastEnd} or {unknown: true, why} when Candystore cannot answer.
 */
export function candystoreLiveness({ client, fleet, now = () => new Date() }) {
  return async ({ boardId, ticketId, key, sent = [] }) => {
    const nowMs = now().getTime();
    try {
      const correlationId = fleet.ticketCorrelationId(boardId, ticketId);
      const since = new Date(nowMs - HISTORY_MS).toISOString();
      const recent = new Date(nowMs - QUIET_MS).toISOString();
      const [correlated, mentions] = await Promise.all([client.correlated(correlationId, since), client.mentions(key, recent)]);
      return turnState({ correlated, mentions, sent, key, nowMs });
    } catch (err) {
      return { unknown: true, why: `liveness unknown (${String(err?.message ?? err).split("\n")[0]})` };
    }
  };
}

/** Run `fn` over `items` with at most `limit` in flight; results keep input order. */
export async function mapLimit(items, limit, fn) {
  const out = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const i = next++;
      out[i] = await fn(items[i], i);
    }
  });
  await Promise.all(workers);
  return out;
}

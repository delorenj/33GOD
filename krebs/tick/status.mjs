// `krebs status`: what is happening on the board, and when will each ticket move?
//
// Read-only. It never writes Plane, publishes, takes tick.lock or appends to the journal. The
// plan comes from the tick itself (`runTick({dryRun: true, inspect})`), so triage eligibility,
// dispatch order, slot math, blockers and orphans are the tick's own decisions, not a copy.
// What this module adds is a projection in time: given the tick's rules (a tick every 10 minutes,
// one board turn per scope per tick, shared and alternating between triage and review, a quiet
// window before a ticket is eligible), when does each ticket's next transition happen?
//
// The projection is an estimate: it assumes every tick fires on the 10-minute mark, no ticket is
// edited meanwhile, no turn takes long to finish, and the 6-per-tick cross-scope cap does not bite.

import { LABEL, heldBy, isContainer } from "./lifecycle.mjs";
import {
  REVIEW_MIN_AGE_MS,
  TRIAGE_MIN_AGE_MS,
  compareTriage,
  reviewGuard,
  triageGuard,
} from "./select.mjs";
import { MAX_DETACHED_MS, MAX_OPEN_TRIAGE_MS, MAX_OPEN_TURN_MS, HISTORY_MS, mapLimit } from "./liveness.mjs";
import { REVIEW_MAX_ATTEMPTS, REVIEW_RETRY_MS } from "./run.mjs";

export const STATUS_VERSION = 1;
/** Candybar fires `krebs tick` on this period (krebs/.candybars/krebs-tick.candybar.toml, every 10 minutes). */
export const TICK_MS = 10 * 60 * 1000;
/** A tick starts a moment after its boundary; ticket ages are judged at that moment. */
const TICK_JITTER_MS = 2000;
/** The orphan sweep's quiet window (liveness.QUIET_MS). */
const ORPHAN_QUIET_MS = 30 * 60 * 1000;
/** The projection gives up after this many ticks (24 h); a ticket beyond it has no ETA. */
const PROJECTION_TICKS = 144;
const RECENT_LIMIT = 10;
const JOURNAL_ACTIONS = new Set([
  "triage.publish",
  "review.publish",
  "dispatch.publish",
  "dispatch.dropped",
  "orphan.release",
  "orphan.unstick",
  "orphan.fail",
  "repair",
]);

const REASON_NAME = {
  "ticket-delegation": "delegation",
  "ticket-grooming": "triage",
  "ticket-review": "review",
};
const reasonName = (reason) => REASON_NAME[reason] ?? (reason ? String(reason) : "turn");

const HOLD_WHY = {
  [LABEL.needsInput]: "waiting on a person: the question is in a comment on the ticket",
  [LABEL.blocked]: "waiting on another ticket or something outside; krebs will not touch it",
  [LABEL.failed]: "a turn failed and nobody has looked; remove agent:failed once you have",
  [LABEL.human]: "you took this one by hand: krebs and the agents write nothing to it",
};

/** The first tick boundary strictly after `ms`. */
export function nextTickAfter(ms) {
  return (Math.floor(ms / TICK_MS) + 1) * TICK_MS;
}

const ms = (iso) => {
  const n = Date.parse(iso ?? "");
  return Number.isFinite(n) ? n : null;
};

// ---------------------------------------------------------------------------------------------
// Candystore: live turns
// ---------------------------------------------------------------------------------------------

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

/**
 * Fold one ticket's invocation events into invocations:
 * [{id, reason, sender, queuedAt, startedAt, endedAt, endType, detachedAt}] (ms), oldest first.
 */
export function invocationsOf(events) {
  const byId = new Map();
  for (const e of events ?? []) {
    const t = ms(e.time);
    if (t === null) continue;
    const data = asObject(e.data);
    const id = data.invocation_id || data.command_id || e.id;
    const inv = byId.get(id) ?? { id, reason: null, sender: null, queuedAt: null, startedAt: null, endedAt: null, endType: null, detachedAt: null };
    inv.reason ??= asObject(data.context).reason ?? null;
    inv.sender ??= data.command_service ?? asObject(data.context).dispatcher ?? null;
    const kind = String(e.type).split(".").pop();
    if (kind === "queued") inv.queuedAt = Math.max(inv.queuedAt ?? 0, t);
    else if (kind === "started") inv.startedAt = Math.max(inv.startedAt ?? 0, t);
    else if (kind === "detached") inv.detachedAt = Math.max(inv.detachedAt ?? 0, t);
    else if (kind === "completed" || kind === "failed") {
      if (inv.endedAt === null || t >= inv.endedAt) {
        inv.endedAt = t;
        inv.endType = kind;
      }
    }
    byId.set(id, inv);
  }
  return [...byId.values()].sort((a, b) => (a.queuedAt ?? a.startedAt ?? 0) - (b.queuedAt ?? b.startedAt ?? 0));
}

/**
 * The turns live right now, by the same open-turn rules as liveness.turnState:
 * running (started, no end), queued (waiting for a gateway slot), detached (a worker has it),
 * and "sent" (krebs published a command and the gateway has not said a word yet).
 * Returns [{id, reason, kind, state, since, sender}] with `since` in ms.
 */
export function openTurns({ invocations, sent = [], nowMs }) {
  const out = [];
  const seen = new Set();
  for (const inv of invocations) {
    seen.add(inv.id);
    const reason = inv.reason;
    if (inv.startedAt !== null && inv.endedAt === null && inv.detachedAt === null && nowMs - inv.startedAt < MAX_OPEN_TURN_MS) {
      out.push({ id: inv.id, reason, kind: reasonName(reason), state: "running", since: inv.startedAt, sender: inv.sender });
    } else if (inv.queuedAt !== null && inv.startedAt === null && inv.endedAt === null && inv.detachedAt === null) {
      const cap = reason === "ticket-grooming" || reason === "ticket-review" ? MAX_OPEN_TRIAGE_MS : MAX_OPEN_TURN_MS;
      if (nowMs - inv.queuedAt < cap) out.push({ id: inv.id, reason, kind: reasonName(reason), state: "queued", since: inv.queuedAt, sender: inv.sender });
    } else if (inv.detachedAt !== null && inv.endedAt === null && nowMs - inv.detachedAt < MAX_DETACHED_MS) {
      out.push({ id: inv.id, reason, kind: reasonName(reason), state: "detached", since: inv.detachedAt, sender: inv.sender });
    }
  }
  const SENT_REASON = { dispatch: "ticket-delegation", triage: "ticket-grooming", review: "ticket-review" };
  for (const cmd of sent) {
    const at = ms(cmd.at);
    if (at === null || seen.has(cmd.commandId)) continue;
    const cap = cmd.kind === "dispatch" ? MAX_OPEN_TURN_MS : MAX_OPEN_TRIAGE_MS;
    if (nowMs - at >= cap) continue;
    out.push({ id: cmd.commandId, reason: SENT_REASON[cmd.kind] ?? null, kind: cmd.kind === "dispatch" ? "delegation" : cmd.kind, state: "sent", since: at, sender: "krebs-tick" });
  }
  return out;
}

/**
 * Ask Candystore about the turns on `tickets`. Resolves to {ok, error, byTicket: Map(ticketId -> {turns, history})}.
 * One failure stops the rest (no point waiting 8 s per ticket on a dead service).
 */
export async function collectTurns({ client, fleet, boardId, tickets, sentByTicket, nowMs }) {
  const byTicket = new Map();
  let error = null;
  const since = new Date(nowMs - HISTORY_MS).toISOString();
  await mapLimit(tickets, 8, async (t) => {
    if (error) return;
    try {
      const events = await client.invocations(fleet.ticketCorrelationId(boardId, t.id), since);
      const invocations = invocationsOf(events);
      byTicket.set(t.id, { history: invocations, turns: openTurns({ invocations, sent: sentByTicket.get(t.id) ?? [], nowMs }) });
    } catch (err) {
      error ??= String(err?.message ?? err).split("\n")[0];
    }
  });
  if (error) return { ok: false, error, byTicket: new Map() };
  return { ok: true, error: null, byTicket };
}

/** Which tickets are worth a Candystore question: anything that could have a turn on it. */
export function ticketsWorthAsking(tickets, sentByTicket, nowMs, focusKey = null) {
  const recent = (list) => (list ?? []).some((c) => nowMs - (ms(c.at) ?? 0) < MAX_OPEN_TURN_MS);
  return tickets.filter(
    (t) =>
      (focusKey && t.key === focusKey) ||
      (t.lane !== "terminal" && t.lane !== "backlog" && (t.lane === "started" || t.labels.includes(LABEL.working) || recent(sentByTicket.get(t.id)))),
  );
}

/**
 * The board-turn pool's tickets that Candystore may be holding back: untriaged Todo and handed-back In Progress
 * tickets with no live turn, past the label checks. The tick skips one of these ("turn live") while any agent
 * activity on it is less than 30 minutes old, and takes the next ticket instead.
 */
export function ticketsInPool(tickets, out, turns, nowMs) {
  const triageSeen = new Set(out.triageSeen ?? []);
  return tickets.filter(
    (t) =>
      !(turns?.get(t.id)?.turns ?? []).length &&
      ((triageGuard(t, nowMs, Number.NEGATIVE_INFINITY) === null && !triageSeen.has(t.key)) || reviewGuard(t, nowMs, Number.NEGATIVE_INFINITY) === null),
  );
}

/**
 * Ask the liveness probe about each pool ticket (at most `limit` per scope, oldest first) and return
 * Map(ticket key -> ms when its activity quiet window ends). Unknown or failing probes just leave the ticket out.
 */
export async function collectBusy({ liveness, boardId, tickets, sentByTicket, nowMs, limit = 12 }) {
  const busy = new Map();
  const pool = [...tickets].sort(compareTriage).slice(0, limit);
  await mapLimit(pool, 4, async (t) => {
    const v = await liveness({ boardId, ticketId: t.id, key: t.key, sent: sentByTicket.get(t.id) ?? [] });
    if (v && !v.unknown && v.live && Number.isFinite(v.busyUntil) && v.busyUntil > nowMs) busy.set(t.key, v.busyUntil);
  });
  return busy;
}

// ---------------------------------------------------------------------------------------------
// Projection: when does each board turn happen?
// ---------------------------------------------------------------------------------------------

/**
 * Replay the tick's board-turn rule forward. Each tick, per scope: among the waiting tickets
 * that are past their quiet window, take ONE; the kind whose turn it is goes first (alternating
 * after each turn sent), oldest ticket first within a kind.
 *
 * items: [{ticket, kind: "triage"|"review", eligibleMs}]. A ticket is taken at tick time T when
 * T > eligibleMs (the tick tests `now - updated_at > window`).
 * Returns Map(ticket.key -> {kind, tickMs, order}) where `order` counts turns of any kind in the order sent.
 */
export function projectBoardTurns({ items, nextTickMs, prefer = "triage", maxTicks = PROJECTION_TICKS }) {
  const pending = [...items];
  const out = new Map();
  const horizon = nextTickMs + maxTicks * TICK_MS;
  let turn = prefer;
  let T = nextTickMs;
  let order = 0;
  while (pending.length && T < horizon) {
    const at = T + TICK_JITTER_MS;
    const ready = pending.filter((i) => at > i.eligibleMs);
    if (!ready.length) {
      // nothing is past its window: jump to the first tick at which something is
      const soonest = Math.min(...pending.map((i) => i.eligibleMs));
      T = Math.max(T + TICK_MS, Math.floor((soonest - TICK_JITTER_MS) / TICK_MS) * TICK_MS + TICK_MS);
      continue;
    }
    ready.sort((a, b) => (a.kind === turn ? 0 : 1) - (b.kind === turn ? 0 : 1) || compareTriage(a.ticket, b.ticket));
    const pick = ready[0];
    order++;
    out.set(pick.ticket.key, { kind: pick.kind, tickMs: T, order });
    pending.splice(pending.indexOf(pick), 1);
    turn = pick.kind === "triage" ? "review" : "triage";
    T += TICK_MS;
  }
  return out;
}

// ---------------------------------------------------------------------------------------------
// Classifier: stage, reason and ETA for every ticket in a scope
// ---------------------------------------------------------------------------------------------

function fmtMin(n) {
  const m = Math.max(0, Math.round(n / 60000));
  if (m < 1) return "<1m";
  if (m < 120) return `${m}m`;
  const h = Math.floor(m / 60);
  return `${h}h${String(m % 60).padStart(2, "0")}m`;
}

/**
 * Classify one scope.
 *
 *   scope    {agentId, identifier, boardId, wip, review, ...}
 *   out      the tick's plan for this scope (a dry-run report scope)
 *   tickets  normalized tickets owned by the scope (select.normalizeTicket)
 *   nowMs    the clock
 *   turns    Map(ticketId -> {turns, history}) from Candystore, or null when Candystore is unreachable
 *   journal  {lastBoardTurn: "triage"|"review"|undefined, reviewsSent: Map("<ticket id>|<updated_at>" -> [{attempt, at}])}
 *   busyUntil Map(ticket key -> ms): tickets with recent agent activity on them (Candystore's 30-minute quiet rule:
 *            the tick skips them as "turn live" without spending the scope's board turn); null/absent when unknown
 *
 * Returns {rows: [...], inFlight: [...], projection} where rows cover every ticket (the caller filters).
 */
export function classifyScope({ scope, out, tickets, nowMs, turns, journal = {}, busyUntil = null }) {
  const nextTickMs = nextTickAfter(nowMs);
  const plannedTriage = new Set(out.triage.filter((x) => x.result === "planned" || x.result === "published").map((x) => x.key));
  const triageSeen = new Set(out.triageSeen);
  const reviewsSeen = new Map((out.reviewsSeen ?? []).map((x) => [x.key, x.why]));
  const dispatchPlanned = new Set(out.dispatches.filter((d) => d.result === "planned" || d.result === "dispatched").map((d) => d.key));
  const blockedBy = new Map(out.blocked.map((b) => [b.key, b.why]));
  const waiting = out.waiting;
  const orphanOf = new Map((out.orphans ?? []).map((o) => [o.key, o]));
  const liveTurns = (t) => turns?.get(t.id)?.turns ?? [];
  const turnOfKind = (t, kind) => liveTurns(t).find((x) => x.kind === kind) ?? null;

  // The projection pool: tickets the tick would take for a board turn, once their window passes.
  const items = [];
  for (const t of tickets) {
    if (liveTurns(t).length) continue;
    if (triageGuard(t, nowMs, Number.NEGATIVE_INFINITY) === null && !triageSeen.has(t.key)) {
      items.push({ ticket: t, kind: "triage", eligibleMs: ms(t.updatedAt) + TRIAGE_MIN_AGE_MS });
    } else if (reviewGuard(t, nowMs, Number.NEGATIVE_INFINITY) === null && !reviewsSeen.has(t.key)) {
      items.push({ ticket: t, kind: "review", eligibleMs: ms(t.updatedAt) + REVIEW_MIN_AGE_MS });
    } else if (reviewGuard(t, nowMs, Number.NEGATIVE_INFINITY) === null) {
      // a version whose last review turn is cooling down: eligible again REVIEW_RETRY_MS after the last send
      const sent = journal.reviewsSent?.get(`${t.id}|${t.updatedAt ?? ""}`) ?? [];
      const last = sent[sent.length - 1];
      if (sent.length < REVIEW_MAX_ATTEMPTS && last && ms(last.at) !== null) {
        items.push({ ticket: t, kind: "review", eligibleMs: Math.max(ms(t.updatedAt) + REVIEW_MIN_AGE_MS, ms(last.at) + REVIEW_RETRY_MS) });
      }
    }
  }
  // A ticket with recent agent activity on it is skipped by the tick ("turn live") until 30 quiet minutes
  // have passed since that activity, so its window ends at the later of the two.
  const busyOf = new Map();
  for (const i of items) {
    const b = busyUntil?.get(i.ticket.key);
    if (b !== undefined && b > i.eligibleMs) {
      i.eligibleMs = b;
      busyOf.set(i.ticket.key, b);
    }
  }
  const projection = projectBoardTurns({ items, nextTickMs, prefer: journal.lastBoardTurn === "triage" ? "review" : "triage" });
  const triageOrder = [...projection.entries()].filter(([, v]) => v.kind === "triage").sort((a, b) => a[1].order - b[1].order).map(([k]) => k);
  const eligibleOf = new Map(items.map((i) => [i.ticket.key, i.eligibleMs]));

  const slotHolders = out.occupied;
  const waitingOrder = new Map(waiting.map((k, i) => [k, i + 1]));
  const rows = [];

  for (const t of tickets) {
    const row = {
      key: t.key,
      title: t.title,
      lane: t.lane,
      state: t.stateName,
      labels: t.labels,
      updatedAt: t.updatedAt,
      stage: "unknown",
      stageLabel: "",
      reason: "",
      eta: null,
      etaNote: null,
      queuePosition: null,
      blockedBy: null,
    };
    const set = (stage, stageLabel, reason, extra = {}) => Object.assign(row, { stage, stageLabel, reason }, extra);
    const eta = (tickMs, note = null) => {
      row.eta = new Date(tickMs).toISOString();
      row.etaNote = note;
    };
    const holds = heldBy(t.labels);
    const updatedMs = ms(t.updatedAt);
    const quietFor = updatedMs === null ? null : nowMs - updatedMs;
    const live = liveTurns(t);
    const working = t.labels.includes(LABEL.working);

    if (t.lane === "terminal") {
      set(/cancel/i.test(t.stateName ?? "") ? "cancelled" : "done", t.stateName ?? "done", "finished; krebs ignores it");
    } else if (t.lane === "backlog") {
      set("backlog", "backlog", "the owner's queue: nothing runs from Backlog; move it to Todo to start the pipeline");
    } else if (t.lane === "other") {
      set("other-lane", `in lane ${t.stateName ?? "?"}`, "not one of the five stock lanes; krebs does not manage it");
    } else if (holds.length) {
      set("held", `held: ${holds.join(", ")}`, holds.map((h) => HOLD_WHY[h]).join("; "));
      if (live.length) row.reason += ` (a ${live[0].kind} turn is still running on it)`;
    } else if (isContainer(t.labels)) {
      set("epic", "epic: never dispatched", "an epic label marks a container; krebs never triages, dispatches or reviews it (its children carry the work)");
    } else if (t.lane === "todo") {
      const turn = turnOfKind(t, "triage");
      if (turn) {
        set("triage-inflight", "triage in flight", `a triage turn is ${turn.state === "running" ? "running" : turn.state === "queued" ? "queued at the gateway" : "sent, gateway has not acknowledged"} (${fmtMin(nowMs - turn.since)}); it ends by adding lifecycle:triaged or lifecycle:needs-input`);
        row.etaNote = "when the turn finishes";
      } else if (live.length) {
        const x = live[0];
        set("turn-inflight", `${x.kind} turn in flight`, `a ${x.kind} turn is ${x.state} on it (${fmtMin(nowMs - x.since)})`);
      } else if (working) {
        set(
          "working",
          "agent:working",
          turns ? "agent:working is set but Candystore shows no live turn; the orphan sweep clears it after 30 quiet minutes" : "agent:working: a turn is presumably running (Candystore unreachable, cannot confirm)",
        );
        if (turns && quietFor !== null) eta(nextTickAfterMs(updatedMs + ORPHAN_QUIET_MS, nowMs), "orphan sweep clears the label");
      } else if (t.labels.includes(LABEL.triaged)) {
        if (dispatchPlanned.has(t.key)) {
          set("ready", "ready to dispatch", `triaged, and ${scope.wip - slotHolders.length > 0 ? "a WIP slot is free" : "next in line"}: the next tick moves it to In Progress`);
          eta(nextTickMs);
        } else if (blockedBy.has(t.key)) {
          const why = blockedBy.get(t.key);
          set("blocked-by", `blocked_by ${(why.match(/blocked by (\S+)/) ?? [])[1] ?? "another ticket"}`, `${why}; dispatched once the blocker is Done or Cancelled`, { blockedBy: why });
        } else if (waitingOrder.has(t.key)) {
          const n = waitingOrder.get(t.key);
          set(
            "wait-slot",
            `waiting for a WIP slot${slotHolders.length ? ` behind ${slotHolders.join(", ")}` : ""}`,
            `triaged; all ${scope.wip} slot(s) are taken${n > 1 ? `, and ${n - 1} triaged ticket(s) are ahead of it in Todo order` : ""}; it goes in when a slot frees (a handback, a hold label, Done)`,
            { queuePosition: n },
          );
          row.etaNote = "when a slot frees up";
        } else {
          set("ready", "triaged", "triaged and waiting for the next tick's dispatch pass");
          eta(nextTickMs);
        }
      } else if (triageSeen.has(t.key)) {
        set("triage-seen", "triage already sent", "a triage turn already ran on this exact version and did not triage it or hold it; krebs will not send it again until the ticket is edited (look at the last turn's comment)");
      } else {
        const proj = projection.get(t.key);
        const eligibleMs = eligibleOf.get(t.key);
        const inQuiet = eligibleMs !== undefined && nowMs <= eligibleMs;
        const position = triageOrder.indexOf(t.key) + 1 || null;
        if (proj) {
          if (inQuiet && busyOf.has(t.key)) {
            set("quiet-window", "waiting: agent activity", `an agent was active on it recently; krebs sends no board turn until the ticket has had 30 quiet minutes (eligible ~${hhmm(eligibleMs)}Z)${position > 1 ? `, then it is #${position} in the triage queue (1 turn per scope per tick)` : ""}`, { queuePosition: position });
          } else if (inQuiet) {
            set("quiet-window", "waiting: quiet window", `edited ${fmtMin(quietFor)} ago; triage waits until a ticket has been quiet for 10 min (eligible ~${hhmm(eligibleMs)}Z)${position > 1 ? `, then it is #${position} in the triage queue (1 turn per scope per tick)` : ""}`, { queuePosition: position });
          } else if (position === 1) {
            set("triage-next", "next for triage", "past the quiet window and first in line: the next tick sends its triage turn", { queuePosition: 1 });
          } else {
            set("triage-queued", `queued for triage #${position}`, `${position - 1} untriaged ticket(s) go first; a scope gets 1 board turn per tick (shared with reviews)`, { queuePosition: position });
          }
          eta(proj.tickMs, `triage turn starts, then ${out.free > 0 ? "dispatch on a following tick (a WIP slot is free now)" : `it needs a WIP slot (${slotHolders.length}/${scope.wip} taken now)`}`);
        } else {
          set("triage-queued", "queued for triage", "waiting for a board turn (beyond the 24 h projection)");
        }
      }
    } else if (t.lane === "started") {
      if (t.labels.includes(LABEL.review)) {
        const turn = turnOfKind(t, "review");
        const proj = projection.get(t.key);
        if (turn) set("review-inflight", "review in flight", `the PM's review turn is ${turn.state} (${fmtMin(nowMs - turn.since)})`);
        else if (!scope.review) set("review-noverdict", "in review (no verdict giver)", "lifecycle:review on a scope with plane.review off: nobody is asked to review it; look at it by hand");
        else if (working) set("review-working", "in review: agent:working", "a turn holds it (agent:working); review turns wait until that clears");
        else if (reviewsSeen.has(t.key) && !proj) set("review-sent", "in review: turn already sent", `${reviewsSeen.get(t.key)}; it is asked again after 3 h, up to ${REVIEW_MAX_ATTEMPTS} times, then it needs you`);
        else if (proj) {
          const eligibleMs = eligibleOf.get(t.key);
          set("review-wait", eligibleMs !== undefined && nowMs <= eligibleMs ? "in review: waiting for quiet" : "in review: review turn queued", `handed back; the PM is asked for a verdict once it has been quiet 30 min (~${hhmm(eligibleMs)}Z), 1 board turn per scope per tick shared with triage`, { queuePosition: proj.order });
          eta(proj.tickMs, "review turn starts");
        } else set("review-wait", "in review", "handed back, waiting for a verdict");
      } else if (live.length) {
        const x = live.find((y) => y.kind === "delegation") ?? live[0];
        set("in-progress", `in progress (${x.kind} ${x.state === "running" ? "running" : x.state} ${fmtMin(nowMs - x.since)})`, `an agent turn is ${x.state === "detached" ? "handed to a background worker" : x.state}; it ends with a handback (lifecycle:review, or Done) or a hold label`);
        row.etaNote = "when the agent hands back";
      } else if (turns) {
        const o = orphanOf.get(t.key);
        const releaseAt = updatedMs === null ? null : updatedMs + ORPHAN_QUIET_MS;
        set("in-progress-idle", "in progress: no live turn", `holds a WIP slot but Candystore shows no live turn; if it stays quiet 30 min krebs releases it back to Todo${o?.result === "planned" ? " (the next tick will)" : ""}`);
        if (releaseAt !== null) eta(nextTickAfterMs(releaseAt, nowMs), "orphan release if nothing changes");
      } else {
        set("in-progress", "in progress", "Candystore unreachable: cannot tell whether a turn is running");
      }
    }
    rows.push(row);
  }

  const inFlight = [];
  for (const t of tickets) {
    for (const x of liveTurns(t)) {
      inFlight.push({ key: t.key, title: t.title, kind: x.kind, reason: x.reason, state: x.state, since: new Date(x.since).toISOString(), runningMinutes: Math.round((nowMs - x.since) / 60000), invocationId: x.id });
    }
  }
  inFlight.sort((a, b) => a.since.localeCompare(b.since));
  return { rows, inFlight, projection };
}

/** The first tick boundary at or after `ms` and strictly after `nowMs` (an overdue event happens at the next tick). */
function nextTickAfterMs(targetMs, nowMs) {
  const base = Math.max(targetMs, nowMs);
  const T = Math.ceil((base - TICK_JITTER_MS) / TICK_MS) * TICK_MS;
  return T > nowMs ? T : nextTickAfter(nowMs);
}

function hhmm(msValue) {
  if (msValue === undefined || msValue === null) return "?";
  const d = new Date(msValue);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------------------------
// Headline: why nothing moved
// ---------------------------------------------------------------------------------------------

const STAGE_ORDER = ["triage-inflight", "turn-inflight", "in-progress", "review-inflight", "in-progress-idle", "ready", "triage-next", "triage-queued", "quiet-window", "wait-slot", "blocked-by", "review-wait", "review-sent", "review-noverdict", "review-working", "triage-seen", "working", "held", "epic", "other-lane"];
const stageRank = (stage) => {
  const i = STAGE_ORDER.indexOf(stage);
  return i < 0 ? 99 : i;
};

/** One sentence: what the board is waiting on, and what happens next. Only for a board with no live turn. */
export function whyNothingMoved({ scope, rows, occupied }) {
  const by = (...stages) => rows.filter((r) => stages.includes(r.stage));
  const untriaged = by("triage-next", "triage-queued", "quiet-window");
  const ready = by("ready");
  const waitSlot = by("wait-slot");
  const held = by("held");
  const parts = [];
  if (untriaged.length) {
    const sorted = [...untriaged].sort((a, b) => (a.eta ?? "").localeCompare(b.eta ?? ""));
    const first = sorted[0];
    const last = sorted[sorted.length - 1];
    parts.push(
      `${untriaged.length} Todo ticket(s) untriaged; triage is serialized at 1 per ${TICK_MS / 60000} min per scope` +
        `${first.eta ? `; next: ${first.key} at ~${hhmm(Date.parse(first.eta))}Z` : ""}` +
        `${untriaged.length > 1 && last.eta ? `, last: ${last.key} at ~${hhmm(Date.parse(last.eta))}Z` : ""}`,
    );
  }
  if (ready.length) parts.push(`${ready.length} triaged ticket(s) ready: dispatch at ~${hhmm(Date.parse(ready[0].eta))}Z (${ready.map((r) => r.key).join(", ")})`);
  if (waitSlot.length) parts.push(`WIP full (${occupied.length}/${scope.wip}: ${occupied.join(", ") || "none"}); ${waitSlot.length} triaged ticket(s) wait for a slot (${waitSlot.map((r) => r.key).join(", ")})`);
  const reviewing = by("review-wait", "review-sent");
  if (reviewing.length) parts.push(`${reviewing.length} ticket(s) in review awaiting the PM's verdict (${reviewing.map((r) => r.key).join(", ")})`);
  if (held.length) parts.push(`${held.length} held for you or another ticket (${held.map((r) => `${r.key} ${r.labels.filter((l) => heldBy([l]).length).join("+")}`).join(", ")})`);
  const stuck = by("in-progress-idle", "working", "triage-seen");
  if (stuck.length) parts.push(`${stuck.length} looks stuck (${stuck.map((r) => `${r.key}: ${r.stageLabel}`).join("; ")})`);
  if (!parts.length) return "nothing to do: no Todo, In Progress or review work on this board";
  return parts.join(" | ");
}

// ---------------------------------------------------------------------------------------------
// Recent journal activity
// ---------------------------------------------------------------------------------------------

export function recentActivity(entries, { agentId, nowMs, limit = RECENT_LIMIT, key = null }) {
  const out = [];
  for (let i = entries.length - 1; i >= 0 && (key || out.length < limit); i--) {
    const e = entries[i];
    if (!e || !JOURNAL_ACTIONS.has(e.action) || e.agent_id !== agentId) continue;
    if (key && e.key !== key) continue;
    const t = ms(e.ts);
    const base = { ts: e.ts, ageMinutes: t === null ? null : Math.round((nowMs - t) / 60000), action: e.action, key: e.key ?? null, ok: e.ok !== false };
    let detail = "";
    switch (e.action) {
      case "triage.publish":
        detail = e.ok === false ? `triage command failed to publish: ${e.error}` : "triage turn sent";
        break;
      case "review.publish":
        detail = e.ok === false ? `review command failed to publish: ${e.error}` : `review turn sent${e.attempt > 1 ? ` (attempt ${e.attempt})` : ""}`;
        break;
      case "dispatch.publish":
        detail = e.ok === false ? `dispatch publish failed: ${e.error}` : e.republish ? "dispatch republished" : "dispatched to In Progress, delegation turn sent";
        break;
      case "dispatch.dropped":
        detail = `owed dispatch dropped: ${e.why}`;
        break;
      case "orphan.release":
        detail = `orphan released back to ${e.to ?? "Todo"}: ${e.why}`;
        break;
      case "orphan.unstick":
        detail = `stale agent:working removed: ${e.why}`;
        break;
      case "orphan.fail":
        detail = `held with agent:failed after repeated releases: ${e.why}`;
        break;
      case "repair":
        detail = `repaired -${(e.removed ?? []).join(" -")}: ${e.why}`;
        break;
      default:
        detail = e.action;
    }
    out.push({ ...base, detail });
  }
  return out;
}

// ---------------------------------------------------------------------------------------------
// Assemble the whole status object
// ---------------------------------------------------------------------------------------------

export function lastTickOf(entries) {
  for (let i = entries.length - 1; i >= 0; i--) {
    const e = entries[i];
    if (e?.action === "tick") {
      const started = typeof e.tick === "string" && e.tick.startsWith("tick:") ? e.tick.slice(5) : e.ts;
      return { at: started, finishedAt: e.ts, ok: e.ok !== false, scopes: e.scopes ?? null, dispatched: e.dispatched ?? 0, triaged: e.triaged ?? 0, reviews: e.reviews ?? 0, repaired: e.repaired ?? 0, errors: e.errors ?? 0 };
    }
  }
  return null;
}

/**
 * Build the status object.
 *   inspected     runTick's `inspect` payload: [{scope, out, snap, tickets}]
 *   turnsByScope  Map(boardId|agentId -> {ok, error, byTicket}) from collectTurns
 *   include       (row) => boolean, which rows to list (default: live work: not done/cancelled/backlog)
 */
export function buildStatus({ inspected, journalEntries, nowMs, turnsByScope, candystore, lastBoardTurn, reviewsSent, busyByScope = new Map(), include = defaultInclude, registryPath = null, journalPath = null }) {
  const lastTick = lastTickOf(journalEntries);
  const nextTickMs = nextTickAfter(nowMs);
  const overdue = lastTick ? nowMs - Date.parse(lastTick.at) > 2.5 * TICK_MS : true;
  const scopes = [];
  for (const { scope, out, tickets } of inspected) {
    const scopeKey = `${scope.boardId}|${scope.agentId}`;
    const turns = turnsByScope.get(scopeKey);
    const { rows, inFlight } = classifyScope({
      scope,
      out,
      tickets,
      nowMs,
      turns: turns?.ok ? turns.byTicket : null,
      journal: { lastBoardTurn: lastBoardTurn.get(`${scope.agentId}|${scope.boardId}`), reviewsSent },
      busyUntil: busyByScope.get(scopeKey) ?? null,
    });
    const listed = rows.filter(include).sort((a, b) => stageRank(a.stage) - stageRank(b.stage) || (a.eta ?? "~").localeCompare(b.eta ?? "~") || a.key.localeCompare(b.key, undefined, { numeric: true }));
    const active = rows.filter(defaultInclude);
    const recent = recentActivity(journalEntries, { agentId: scope.agentId, nowMs });
    scopes.push({
      board: scope.identifier ?? scope.boardId,
      boardId: scope.boardId,
      agentId: scope.agentId,
      scopeLabels: scope.scopeLabels ?? [],
      wip: scope.wip,
      occupied: out.occupied,
      free: out.free,
      overLimit: out.overLimit,
      reviewRequired: Boolean(scope.review),
      idle: active.length === 0,
      inFlight,
      idleReason: inFlight.length === 0 && turns?.ok ? whyNothingMoved({ scope, rows: active, occupied: out.occupied }) : null,
      tickets: listed,
      counts: Object.fromEntries([...new Set(active.map((r) => r.stage))].sort().map((s) => [s, active.filter((r) => r.stage === s).length])),
      recent,
      warnings: [...out.warnings],
      errors: [...out.errors],
    });
  }
  return {
    version: STATUS_VERSION,
    generatedAt: new Date(nowMs).toISOString(),
    estimates: "every eta is an estimate: ticks assumed on the 10-minute mark, no edits meanwhile, turns assumed short, no cross-scope cap",
    tick: {
      everyMinutes: TICK_MS / 60000,
      last: lastTick,
      overdue,
      nextEstimate: new Date(nextTickMs).toISOString(),
    },
    candystore,
    registry: registryPath,
    journal: journalPath,
    scopes,
  };
}

export function defaultInclude(row) {
  return row.lane !== "terminal" && row.lane !== "backlog";
}

// ---------------------------------------------------------------------------------------------
// Human output
// ---------------------------------------------------------------------------------------------

export function relAge(minutes) {
  if (minutes === null || minutes === undefined) return "?";
  if (minutes < 1) return "just now";
  if (minutes < 120) return `${minutes}m ago`;
  if (minutes < 48 * 60) return `${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, "0")}m ago`;
  return `${Math.floor(minutes / 1440)}d ago`;
}

function clock(iso, nowMs) {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return "?";
  const d = new Date(t);
  const day = d.toISOString().slice(0, 10) === new Date(nowMs).toISOString().slice(0, 10) ? "" : `${d.toISOString().slice(5, 10)} `;
  return `${day}${hhmm(t)}Z`;
}

function etaText(row, nowMs) {
  if (!row.eta) return row.etaNote ? row.etaNote : "";
  const mins = Math.round((Date.parse(row.eta) - nowMs) / 60000);
  const inText = mins <= 0 ? "next tick" : mins < 120 ? `in ~${mins}m` : `in ~${(mins / 60).toFixed(1)}h`;
  return `~${clock(row.eta, nowMs)} (${inText})${row.etaNote ? `: ${row.etaNote}` : ""}`;
}

const trunc = (s, n) => (String(s).length > n ? `${String(s).slice(0, n - 1)}…` : String(s));

function parkedSummary(rows) {
  const counts = new Map();
  for (const r of rows) {
    const label = r.stage === "held" ? r.labels.filter((l) => heldBy([l]).length).join("+") : r.stage === "blocked-by" ? "blocked_by" : r.stage;
    counts.set(label, [...(counts.get(label) ?? []), r.key]);
  }
  return [...counts.entries()].map(([label, keys]) => `${keys.length} ${label} (${keys.slice(0, 4).join(", ")}${keys.length > 4 ? ", ..." : ""})`).join("; ");
}

function scopeHeader(s) {
  const labels = s.scopeLabels.length ? ` ${s.scopeLabels.join("+")}` : "";
  return `${s.board}${labels} -> ${s.agentId}`;
}

export function formatStatus(status, { compact = false, ticket = null } = {}) {
  const nowMs = Date.parse(status.generatedAt);
  const lines = [];
  const t = status.tick;
  const last = t.last
    ? `last tick ${clock(t.last.at, nowMs)} (${relAge(Math.round((nowMs - Date.parse(t.last.at)) / 60000))}): ${t.last.ok ? "ok" : "ERRORS"}, dispatched ${t.last.dispatched}, triage ${t.last.triaged}, review ${t.last.reviews}, repaired ${t.last.repaired}${t.last.errors ? `, errors ${t.last.errors}` : ""}`
    : "no tick on record in the journal";
  lines.push(`krebs status ${clock(status.generatedAt, nowMs)}   ${last}`);
  lines.push(`next tick ~${clock(t.nextEstimate, nowMs)} (estimate: Candybar fires every ${t.everyMinutes} min on the :00 mark)${t.overdue ? "   WARNING: no recent tick; is the krebs-tick candybar running?" : ""}`);
  if (!status.candystore.ok) lines.push(`WARNING: Candystore unreachable (${status.candystore.error}): live turns unknown; stages assume nothing is running`);

  const PARKED = new Set(["held", "epic", "blocked-by", "other-lane"]);
  const moving = (s) => s.inFlight.length > 0 || s.tickets.some((r) => !PARKED.has(r.stage)) || s.errors.length > 0;
  const active = status.scopes.filter((s) => !s.idle || s.errors.length);
  // compact (every scope): a scope with nothing in flight and nothing but parked tickets is one line.
  const quiet = compact && !ticket ? active.filter((s) => !moving(s)) : [];
  const idle = status.scopes.filter((s) => s.idle && !s.errors.length);

  for (const s of active.filter((x) => !quiet.includes(x))) {
    lines.push("");
    lines.push(`== ${scopeHeader(s)}   wip ${s.occupied.length}/${s.wip}${s.occupied.length ? ` (${s.occupied.join(", ")})` : ""}${s.overLimit ? `  OVER LIMIT by ${s.overLimit}, draining` : ""}${s.reviewRequired ? "   review:on" : ""}`);
    lines.push("in flight now:");
    if (s.inFlight.length) {
      for (const f of s.inFlight) lines.push(`  ${f.key}  ${f.kind} ${f.state}${f.state === "running" ? " for" : " since"} ${f.runningMinutes}m   ${trunc(f.title, 60)}`);
    } else if (!status.candystore.ok) lines.push("  unknown: Candystore is unreachable, so running turns cannot be seen");
    else lines.push("  nothing: no agent turn is running on this board");
    if (s.idleReason) lines.push(`why nothing moved: ${compact ? trunc(s.idleReason, 220) : s.idleReason}`);
    lines.push("tickets:");
    const shown = compact && !ticket ? s.tickets.filter((r) => !PARKED.has(r.stage)) : s.tickets;
    const cap = compact && !ticket ? 12 : Infinity;
    for (const r of shown.slice(0, cap)) {
      lines.push(`  ${r.key.padEnd(8)} ${r.lane === "todo" ? "Todo" : r.lane === "started" ? "IP  " : (r.state ?? r.lane).slice(0, 4).padEnd(4)}  ${r.stageLabel}`);
      lines.push(`           ${trunc(r.title, 70)}`);
      lines.push(`           why: ${r.reason}`);
      const e = etaText(r, nowMs);
      if (e) lines.push(`           next: ${e}`);
    }
    if (shown.length > cap) lines.push(`  ... +${shown.length - cap} more (krebs status --board ${s.board})`);
    if (shown.length < s.tickets.length) lines.push(`  parked (not moving without you): ${parkedSummary(s.tickets.filter((r) => PARKED.has(r.stage)))}   (krebs status --board ${s.board})`);
    const recent = compact && !ticket ? s.recent.slice(0, 3) : s.recent;
    if (recent.length) {
      lines.push("recent activity:");
      for (const a of recent) lines.push(`  ${relAge(a.ageMinutes).padEnd(10)} ${(a.key ?? "").padEnd(8)} ${a.action.padEnd(16)} ${a.detail}${a.ok ? "" : "  [FAILED]"}`);
    }
    for (const w of s.warnings) lines.push(`warning: ${w}`);
    for (const e of s.errors) lines.push(`ERROR: ${e}`);
  }
  if (quiet.length) {
    lines.push("");
    lines.push("parked, nothing moving without you:");
    for (const s of quiet) lines.push(`  ${scopeHeader(s).padEnd(36)} wip ${s.occupied.length}/${s.wip}   ${trunc(parkedSummary(s.tickets), 150)}`);
  }
  if (idle.length) {
    lines.push("");
    lines.push(`idle (${idle.length}): ${idle.map((s) => `${s.board}${s.scopeLabels.length ? `/${s.scopeLabels[0]}` : ""}`).join(", ")}   (no Todo or In Progress tickets)`);
  }
  return lines.join("\n");
}

/** `--ticket KEY`: the detail view for one ticket (stage, ETA, journal trail, Candystore turn history). */
export function formatTicket(status, detail) {
  const nowMs = Date.parse(status.generatedAt);
  const lines = [];
  const { row, scope, trail, turns } = detail;
  lines.push(`${row.key}  ${row.title}`);
  lines.push(`  board ${scope.board} -> ${scope.agentId}   lane ${row.state ?? row.lane}   labels: ${row.labels.join(", ") || "(none)"}`);
  lines.push(`  updated ${row.updatedAt ?? "?"}`);
  lines.push(`  stage: ${row.stageLabel}`);
  lines.push(`  why:   ${row.reason}`);
  const e = etaText(row, nowMs);
  if (e) lines.push(`  next:  ${e}`);
  lines.push("  turns (Candystore, last 7 days):");
  if (turns === null) lines.push("    unreachable");
  else if (!turns.length) lines.push("    none");
  for (const x of turns ?? []) {
    const start = x.startedAt ?? x.queuedAt;
    const end = x.endedAt ? `${x.endType} ${clock(new Date(x.endedAt).toISOString(), nowMs)} (${fmtMin(x.endedAt - (start ?? x.endedAt))})` : x.detachedAt ? "detached" : "no end on record";
    lines.push(`    ${clock(new Date(start ?? x.endedAt).toISOString(), nowMs)}  ${reasonName(x.reason).padEnd(10)} ${end}`);
  }
  lines.push("  krebs journal:");
  if (!trail.length) lines.push("    nothing on record");
  for (const a of trail.slice(0, 15)) lines.push(`    ${relAge(a.ageMinutes).padEnd(9)} ${a.action.padEnd(16)} ${a.detail}`);
  return lines.join("\n");
}

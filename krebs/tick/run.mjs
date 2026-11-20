// One Krebs tick: for every scope, republish owed dispatches, repair the two
// invariants, release orphans, do the slot math and dispatch into free slots;
// then publish the board turns: catch-up triages (spec catch_up.triage) for
// Todo tickets the n8n triage lane never got to, and review turns (spec
// catch_up.review) that ask the scope's PM for a verdict on a ticket handed
// back with lifecycle:review. One board turn per scope per tick, oldest first.
//
// Everything with a side effect is injected (plane, publish, journal, now), so
// the tests drive it with fakes and --dry-run drives it with no writer at all.

import { LABEL, SPEC_VERSION, heldBy, laneModel } from "./lifecycle.mjs";
import {
  REVIEW_MIN_AGE_MS,
  TRIAGE_MIN_AGE_MS,
  TRIAGE_SCOPE_CAP,
  TRIAGE_TICK_CAP,
  candidatesOf,
  compareTriage,
  dispatchGuard,
  normalizeTicket,
  orphanKind,
  pickDispatches,
  repairsFor,
  reviewCandidatesOf,
  reviewGuard,
  slotsOf,
  triageCandidatesOf,
  triageGuard,
} from "./select.mjs";
import { PENDING_MAX_AGE_MS, TURN_WINDOW_MS, boardTurnSends, lastBoardTurns, pendingPublishes, releaseCounts, sentBoardTurnsByAgent, sentCommands, triagedCommandIds } from "./journal.mjs";
import { QUIET_MS, mapLimit } from "./liveness.mjs";
import { judgeBoardTurn, parkComment } from "./turns.mjs";
import { dispatchPrompt, reviewPrompt } from "./prompt.mjs";

/** spec orphans: caps on what one tick does, so a backlog of orphans drains over a few ticks. */
export const ORPHAN_RELEASE_SCOPE_CAP = 2;
export const ORPHAN_RELEASE_TICK_CAP = 12;
export const ORPHAN_UNSTICK_TICK_CAP = 30;
/** A ticket released this many times in ORPHAN_LOOP_WINDOW_MS is held with agent:failed instead. */
export const ORPHAN_RELEASE_LIMIT = 2;
export const ORPHAN_LOOP_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;
const LIVENESS_CONCURRENCY = 8;

function releaseComment(why) {
  return (
    `<p>Krebs moved this back to Todo. Nobody was working on it: ${why}, and the turn left no handback ` +
    `(no <code>lifecycle:review</code>, no hold label, not closed). It was holding one of the project's work ` +
    `slots. Its other labels stay as they were, and it gets the next free slot in Todo order.</p>`
  );
}

function failComment(why, count) {
  return (
    `<p>Krebs has already moved this back to Todo ${count} times this week, and each time the agent turn ended ` +
    `without a handback (latest: ${why}). It now carries <code>agent:failed</code> so it stops looping. ` +
    `Look at the last turn, fix what stops it, then remove <code>agent:failed</code>.</p>`
  );
}

export const COMMAND_TYPE = "bloodbank.agent.invocation.start";
export const INVOCATION_REASON = "ticket-delegation";
/** The operation fleetCommandId hashes in; the n8n Fleet node's delegation operation. */
export const DISPATCH_OPERATION = "delegateTicket";
export const KREBS_SOURCE = "urn:33god:service:krebs-tick";
export const KREBS_ACTOR = Object.freeze({ type: "service", agent_id: "krebs.tick" });
export const PROVIDER_EVENT_TYPE = "krebs.dispatch";
/** The n8n Fleet node's groomTicket operation (reason ticket-grooming), which the "Ticket Triage" lane sends. */
export const TRIAGE_OPERATION = "groomTicket";
export const TRIAGE_REASON = "ticket-grooming";
export const TRIAGE_PROVIDER_EVENT_TYPE = "krebs.catch_up.triage";
/** The completion marker the triage prompt asks for; the Fleet node's GROOMED_LABEL. */
export const TRIAGED_LABEL = LABEL.triaged;
/** Review turns (spec catch_up.review): the PM's verdict on a lifecycle:review ticket. */
export const REVIEW_OPERATION = "reviewTicket";
export const REVIEW_REASON = "ticket-review";
export const REVIEW_PROVIDER_EVENT_TYPE = "krebs.catch_up.review";
/** Attempt caps per episode (tick/turns.mjs): a review or triage turn with no outcome is asked again, then the ticket is parked. */
export { REVIEW_MAX_ATTEMPTS, REVIEW_RETRY_MS, TRIAGE_MAX_ATTEMPTS, TRIAGE_RETRY_MS } from "./turns.mjs";
/** A tick parks at most this many looping tickets (a Plane write each); the rest wait for the next tick. */
export const LOOP_PARK_TICK_CAP = 12;
/** Liveness checks per scope per tick when picking its board turn (triage or review). */
export const BOARD_TURN_PROBES = 3;

/** YYYY-MM-DD in `timeZone` (default: the host's zone): Plane's start_date. */
export function localDate(date, timeZone) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: timeZone || undefined,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

/**
 * The deterministic ids of one dispatch. A dispatch is a ticket at one version
 * (its updated_at just before the write), so a retry of the same dispatch gets
 * the same ids and a later re-dispatch of the same ticket (SENT BACK, then a
 * slot again) gets new ones.
 */
export function dispatchIds({ fleet, nats }, { boardId, ticketId, updatedAt, agentId }) {
  const dispatchId = nats.deterministicUuid(`krebs:dispatch:${boardId}:${ticketId}:${updatedAt ?? ""}`);
  const commandId = fleet.fleetCommandId(dispatchId, DISPATCH_OPERATION, agentId);
  return { dispatchId, commandId };
}

/** The publish options of a dispatch command, minus the NATS host. Same shape as the n8n Fleet node's. */
export function dispatchCommand({ fleet }, { scope, ticket, route, inProgressName, dispatchId, commandId, observedAt }) {
  const facts = fleet.ticketFactsFromEnvelope({
    data: {
      repo: scope.repo ?? "",
      board_id: scope.boardId,
      ticket_key: ticket.key,
      ticket_id: ticket.id,
      title: ticket.title,
      workspace: scope.workspace,
      phase: inProgressName,
      previous_phase: ticket.stateName ?? "Todo",
      provider_event_type: PROVIDER_EVENT_TYPE,
      labels: ticket.labels,
    },
  });
  return {
    type: COMMAND_TYPE,
    kind: "command",
    data: {
      target_agent_id: route.agentId,
      prompt: dispatchPrompt(fleet, facts, route.projectPath, scope.review),
      context: {
        reason: INVOCATION_REASON,
        repo: facts.repo,
        ticket_key: facts.ticketKey,
        ticket_id: facts.ticketId,
        board_id: facts.boardId,
        workspace: facts.workspace,
        title: facts.title,
        phase: facts.phase,
        previous_phase: facts.previousPhase,
        provider_event_type: facts.providerEventType,
        dispatcher: "krebs-tick",
        dispatch_id: dispatchId,
        review_required: scope.review,
        lifecycle_spec: SPEC_VERSION,
      },
    },
    commandId,
    eventId: commandId,
    correlationId: fleet.ticketCorrelationId(scope.boardId, ticket.id),
    causationId: null,
    observedAt,
    source: KREBS_SOURCE,
    producer: "krebs",
    service: "krebs-tick",
    actor: { ...KREBS_ACTOR },
  };
}

/**
 * The deterministic ids of one catch-up triage: board + ticket id + updated_at +
 * "triage". One id is one ticket version, so it is triaged at most once ever.
 */
export function triageIds({ fleet, nats }, { boardId, ticketId, updatedAt, agentId }) {
  const triageId = nats.deterministicUuid(`krebs:triage:${boardId}:${ticketId}:${updatedAt ?? ""}:triage`);
  const commandId = fleet.fleetCommandId(triageId, TRIAGE_OPERATION, agentId);
  return { triageId, commandId };
}

/**
 * The publish options of a catch-up triage: the command the n8n "Ticket Triage"
 * lane (Fleet node, groomTicket) sends for a ticket that just entered Todo.
 * Same keys, same prompt (groomingPrompt), reason ticket-grooming. observedAt is
 * the ticket's updated_at, so a retry rebuilds a byte-identical command.
 */
export function triageCommand({ fleet }, { scope, ticket, route, todoName, commandId, observedAt }) {
  const facts = fleet.ticketFactsFromEnvelope({
    data: {
      repo: scope.repo ?? "",
      board_id: scope.boardId,
      ticket_key: ticket.key,
      ticket_id: ticket.id,
      title: ticket.title,
      workspace: scope.workspace,
      phase: todoName,
      provider_event_type: TRIAGE_PROVIDER_EVENT_TYPE,
      labels: ticket.labels,
    },
  });
  return {
    type: COMMAND_TYPE,
    kind: "command",
    data: {
      target_agent_id: route.agentId,
      prompt: fleet.groomingPrompt(facts, route.projectPath, TRIAGED_LABEL),
      context: {
        reason: TRIAGE_REASON,
        repo: facts.repo,
        ticket_key: facts.ticketKey,
        ticket_id: facts.ticketId,
        board_id: facts.boardId,
        workspace: facts.workspace,
        title: facts.title,
        phase: facts.phase,
        previous_phase: facts.previousPhase,
        provider_event_type: facts.providerEventType,
      },
    },
    commandId,
    eventId: commandId,
    correlationId: fleet.ticketCorrelationId(scope.boardId, ticket.id),
    causationId: null,
    observedAt,
    source: KREBS_SOURCE,
    producer: "krebs",
    service: "krebs-tick",
    actor: { ...KREBS_ACTOR },
  };
}

/**
 * The deterministic ids of one review turn: board + ticket + updated_at +
 * attempt. A verdict changes the ticket, so a new version is a new review; an
 * attempt that ended without one is retried under the next attempt number.
 */
export function reviewIds({ fleet, nats }, { boardId, ticketId, updatedAt, agentId, attempt = 1 }) {
  const reviewId = nats.deterministicUuid(`krebs:review:${boardId}:${ticketId}:${updatedAt ?? ""}:${attempt}`);
  const commandId = fleet.fleetCommandId(reviewId, REVIEW_OPERATION, agentId);
  return { reviewId, commandId };
}

/** The publish options of a review turn (reason ticket-review, krebs's reviewPrompt). */
export function reviewCommand({ fleet }, { scope, ticket, route, commandId, observedAt, attempt = 1 }) {
  const facts = fleet.ticketFactsFromEnvelope({
    data: {
      repo: scope.repo ?? "",
      board_id: scope.boardId,
      ticket_key: ticket.key,
      ticket_id: ticket.id,
      title: ticket.title,
      workspace: scope.workspace,
      phase: ticket.stateName ?? "In Progress",
      provider_event_type: REVIEW_PROVIDER_EVENT_TYPE,
      labels: ticket.labels,
    },
  });
  return {
    type: COMMAND_TYPE,
    kind: "command",
    data: {
      target_agent_id: route.agentId,
      prompt: reviewPrompt(facts, route.projectPath),
      context: {
        reason: REVIEW_REASON,
        repo: facts.repo,
        ticket_key: facts.ticketKey,
        ticket_id: facts.ticketId,
        board_id: facts.boardId,
        workspace: facts.workspace,
        title: facts.title,
        phase: facts.phase,
        provider_event_type: facts.providerEventType,
        dispatcher: "krebs-tick",
        review_attempt: attempt,
        lifecycle_spec: SPEC_VERSION,
      },
    },
    commandId,
    eventId: commandId,
    correlationId: fleet.ticketCorrelationId(scope.boardId, ticket.id),
    causationId: null,
    observedAt,
    source: KREBS_SOURCE,
    producer: "krebs",
    service: "krebs-tick",
    actor: { ...KREBS_ACTOR },
  };
}

function message(err) {
  return String(err?.message ?? err).split("\n")[0];
}

/** A Plane write error whose outcome is known: the server refused it (4xx other than 429). */
function definitiveFailure(err) {
  return Number.isInteger(err?.status) && err.status >= 400 && err.status < 500 && err.status !== 429;
}

function ticketRef(t) {
  return { key: t.key, ticketId: t.id, title: t.title };
}

export async function runTick({
  registry,
  scopes,
  skipped = [],
  plane,
  fleet,
  nats,
  publish,
  journal,
  dryRun = false,
  now = () => new Date(),
  timeZone,
  pendingMaxAgeMs = PENDING_MAX_AGE_MS,
  triageMinAgeMs = TRIAGE_MIN_AGE_MS,
  triageScopeCap = TRIAGE_SCOPE_CAP,
  triageTickCap = TRIAGE_TICK_CAP,
  reviewMinAgeMs = REVIEW_MIN_AGE_MS,
  liveness: probeLiveness = null,
  orphanQuietMs = QUIET_MS,
  orphanReleaseScopeCap = ORPHAN_RELEASE_SCOPE_CAP,
  orphanReleaseTickCap = ORPHAN_RELEASE_TICK_CAP,
  orphanUnstickTickCap = ORPHAN_UNSTICK_TICK_CAP,
  inspect = null,
  // ADR 0002: probe({scope, sent}) -> {busy, turns, why} | {unknown, why}. A scope with a board turn queued or
  // running (triage or review, any ticket) is sent no new one. Null = no guard (tests, no Candystore).
  scopeBusy = null,
  // What started this run, for the journal's tick line: "schedule" (Candybar), "plane-edit", "turn-ended", ...
  trigger = "schedule",
  triggerDetail = null,
  boardFilter = null,
}) {
  const started = now();
  const tickId = `tick:${started.toISOString()}`;
  const ts = () => now().toISOString();
  const record = (entry) => {
    if (!dryRun) journal.append({ ts: ts(), tick: tickId, ...entry });
  };
  const journalEntries = journal.read();
  const pending = pendingPublishes(journalEntries);
  const triaged = triagedCommandIds(journalEntries);
  const sentByTicket = sentCommands(journalEntries);
  // One Candystore verdict per ticket per tick: the orphan sweep and the board-turn pick may
  // both ask about the same ticket (a ticket released this tick becomes a triage candidate).
  const livenessSeen = new Map();
  const liveness = probeLiveness
    ? (req) => {
        if (!livenessSeen.has(req.ticketId)) livenessSeen.set(req.ticketId, probeLiveness(req));
        return livenessSeen.get(req.ticketId);
      }
    : null;
  const releasedBefore = releaseCounts(journalEntries, started.getTime() - ORPHAN_LOOP_WINDOW_MS);
  // Board turns Krebs sent per TICKET in the look-back window (not per version: the pickup chip rewrites the version every turn).
  const turnSends = boardTurnSends(journalEntries, started.getTime() - TURN_WINDOW_MS);
  // The kind of the last board turn each scope was sent: when a scope has both kinds waiting,
  // it alternates, so a review backlog never starves triage (the flow's gate) and a triage
  // stream never starves reviews.
  const lastBoardTurn = lastBoardTurns(journalEntries);
  const boardTurnsSent = sentBoardTurnsByAgent(journalEntries);
  let releasesThisTick = 0;
  let unsticksThisTick = 0;
  let parksThisTick = 0;
  const triagePlans = []; // board turns {kind, scope, snap, out, entry, ticket}: picked per scope, capped tick-wide after the loop
  const inspected = []; // per scope {scope, out, snap, tickets()}, handed to `inspect` (krebs status) when the plan is complete
  const boards = new Map(); // `${ws}:${board}` -> snapshot | {error}
  const statesCache = new Map();

  const statesOf = async (ws, board) => {
    const key = `${ws}:${board}`;
    if (!statesCache.has(key)) statesCache.set(key, plane.states(ws, board));
    return statesCache.get(key);
  };

  const loadBoard = async (ws, board, identifier) => {
    const key = `${ws}:${board}`;
    if (boards.has(key)) return boards.get(key);
    let snapshot;
    try {
      const [states, labels, issues] = await Promise.all([
        statesOf(ws, board),
        plane.collection("labels", ws, board),
        plane.issues({ ws, board }),
      ]);
      const lanes = laneModel(states);
      const labelNameOf = new Map();
      const labelIdOf = new Map();
      for (const l of labels ?? []) {
        const name = String(l.name ?? "").trim().toLowerCase();
        if (!name) continue;
        labelNameOf.set(l.id, name);
        if (!labelIdOf.has(name)) labelIdOf.set(name, l.id);
      }
      const ctx = { lanes, labelNameOf, identifier };
      const tickets = (issues ?? []).map((i) => normalizeTicket(i, ctx));
      snapshot = { ws, board, identifier, lanes, labelNameOf, labelIdOf, ctx, tickets, byId: new Map(tickets.map((t) => [t.id, t])) };
    } catch (err) {
      snapshot = { error: `cannot read board ${identifier ?? board}: ${message(err)}` };
    }
    boards.set(key, snapshot);
    return snapshot;
  };

  /** The state group of any issue, on this board or another; null when unreadable. */
  const groupOfIssue = async (ws, homeBoard, issueId, projectId) => {
    const board = projectId || homeBoard;
    const cached = boards.get(`${ws}:${board}`);
    const known = cached?.byId?.get(issueId);
    if (known) return { group: cached.lanes.groupOf.get(known.stateId) ?? null, ref: known.key, state: known.stateName };
    try {
      const issue = await plane.issue(issueId, ws, board);
      const stateId = typeof issue?.state === "object" && issue.state !== null ? issue.state.id : issue?.state;
      const states = await statesOf(ws, board);
      const state = (states ?? []).find((s) => s.id === stateId);
      return { group: state?.group ?? null, ref: issue?.sequence_id !== undefined ? `#${issue.sequence_id}` : issueId, state: state?.name ?? null };
    } catch {
      return { group: null, ref: issueId, state: null };
    }
  };

  const report = {
    ok: true,
    dryRun,
    tickId,
    at: started.toISOString(),
    spec: SPEC_VERSION,
    trigger,
    scopes: [],
    skipped,
    errors: [],
  };

  for (const scope of scopes) {
    const out = {
      agentId: scope.agentId,
      identifier: scope.identifier,
      boardId: scope.boardId,
      workspace: scope.workspace,
      scopeLabels: scope.scopeLabels,
      scopeDefault: scope.scopeDefault,
      wip: scope.wip,
      review: scope.review,
      tickets: 0,
      occupied: [],
      free: 0,
      overLimit: 0,
      republishes: [],
      repairs: [],
      orphans: [],
      dispatches: [],
      blocked: [],
      triage: [],
      triageCapped: [],
      triageSeen: [],
      triageHeld: [],
      parks: [],
      boardTurnBusy: null,
      reviews: [],
      reviewsCapped: [],
      reviewsSeen: [],
      waiting: [],
      excluded: [],
      warnings: [...(scope.warnings ?? [])],
      errors: [],
    };
    report.scopes.push(out);
    const ws = scope.workspace;
    const board = scope.boardId;

    const snap = await loadBoard(ws, board, scope.identifier);
    if (snap.error) {
      out.errors.push(snap.error);
      continue;
    }
    const ownerOf = (t) => {
      const route = fleet.resolveFleetAgentForBoard(registry, board, "", t.labels);
      return route.matchedBy === "board" ? route.agentId : null;
    };
    let mine = snap.tickets.filter((t) => !t.archived && ownerOf(t) === scope.agentId);
    out.tickets = mine.length;
    inspected.push({ scope, out, snap, tickets: () => mine });

    // 1. Owed publishes from earlier ticks (same command id, byte-identical command).
    for (const p of pending.filter((x) => x.agentId === scope.agentId && x.boardId === board)) {
      const entry = { key: p.key, ticketId: p.ticketId, dispatchId: p.dispatchId, commandId: p.commandId, since: p.since, attempts: p.attempts };
      const drop = (why) => {
        entry.result = dryRun ? "would drop" : "dropped";
        entry.why = why;
        record({ action: "dispatch.dropped", dispatch_id: p.dispatchId, command_id: p.commandId, agent_id: scope.agentId, key: p.key, why });
      };
      const ticket = snap.byId.get(p.ticketId);
      const age = started.getTime() - Date.parse(p.since);
      if (Number.isFinite(age) && age > pendingMaxAgeMs) drop(`publish still owed after ${Math.round(age / 3600000)}h; giving up (ticket stays In Progress: look at it)`);
      else if (!ticket) drop("ticket is no longer on the board");
      else if (ticket.lane !== "started") drop(`ticket left In Progress (${ticket.stateName ?? ticket.lane})`);
      else if (ticket.labels.includes(LABEL.review)) drop("ticket already handed back (lifecycle:review)");
      else if (heldBy(ticket.labels).length) drop(`ticket is held (${heldBy(ticket.labels).join(", ")}): a turn already ran on it`);
      else if (!p.writeKnown && !ticket.labels.includes(LABEL.working)) drop("the dispatch write is not on the ticket (no agent:working)");
      else if (!p.command) drop("journal intent carries no command");
      else if (dryRun) entry.result = "would republish";
      else {
        try {
          const res = await publish(p.command);
          entry.result = "republished";
          entry.subject = res?.subject ?? null;
          record({ action: "dispatch.publish", dispatch_id: p.dispatchId, command_id: p.commandId, agent_id: scope.agentId, key: p.key, ok: true, republish: true, subject: res?.subject ?? null });
        } catch (err) {
          entry.result = "republish failed";
          entry.error = message(err);
          out.errors.push(`${p.key}: republish failed: ${entry.error}`);
          record({ action: "dispatch.publish", dispatch_id: p.dispatchId, command_id: p.commandId, agent_id: scope.agentId, key: p.key, ok: false, republish: true, error: entry.error });
        }
      }
      out.republishes.push(entry);
    }

    // 2. Invariant repairs.
    for (const r of repairsFor(mine)) {
      const ids = r.remove.map((name) => snap.labelIdOf.get(name)).filter(Boolean);
      const entry = { ...ticketRef(r.ticket), remove: r.remove, why: r.why };
      if (dryRun) entry.result = "planned";
      else {
        try {
          await plane.editIssue(r.ticket.id, { removeLabels: ids }, ws, board);
          entry.result = "repaired";
          record({ action: "repair", agent_id: scope.agentId, board_id: board, key: r.ticket.key, ticket_id: r.ticket.id, removed: r.remove, why: r.why, ok: true });
        } catch (err) {
          entry.result = "failed";
          entry.error = message(err);
          out.errors.push(`${r.ticket.key}: repair failed: ${entry.error}`);
          record({ action: "repair", agent_id: scope.agentId, board_id: board, key: r.ticket.key, ticket_id: r.ticket.id, removed: r.remove, why: r.why, ok: false, error: entry.error });
        }
      }
      out.repairs.push(entry);
    }

    // 2b. Orphans (spec orphans): a ticket whose agent turn is over but still
    // looks worked on. Candystore says whether a turn is live; unknown means
    // hands off. Released tickets go back to Todo, which frees their slot below.
    {
      const nowMs = started.getTime();
      const found = mine.map((t) => ({ t, kind: orphanKind(t, nowMs, orphanQuietMs) })).filter((x) => x.kind);
      if (found.length && !liveness) {
        out.warnings.push(`${found.length} possible orphan(s) not checked: no liveness probe (Candystore) configured`);
      } else if (found.length) {
        const todoId = snap.lanes.todoStateIds[0] ?? null;
        const todoName = todoId ? snap.lanes.nameOf.get(todoId) : null;
        const workingId = snap.labelIdOf.get(LABEL.working);
        const failedId = snap.labelIdOf.get(LABEL.failed);
        const verdicts = await mapLimit(found, LIVENESS_CONCURRENCY, ({ t }) =>
          liveness({ boardId: board, ticketId: t.id, key: t.key, sent: sentByTicket.get(t.id) ?? [] }),
        );
        let releasedInScope = 0;
        const replace = (ticket, patch) => {
          const next = { ...ticket, ...patch };
          mine = mine.map((x) => (x.id === ticket.id ? next : x));
          return next;
        };
        for (const [i, { t, kind }] of found.entries()) {
          const v = verdicts[i];
          const entry = { ...ticketRef(t), kind, why: v.why };
          out.orphans.push(entry);
          if (v.unknown) {
            entry.result = "unknown";
            out.warnings.push(`${t.key}: ${v.why}; left alone`);
            continue;
          }
          if (v.live) {
            entry.result = "live";
            continue;
          }
          const hasWorking = t.labels.includes(LABEL.working);
          const record2 = (action, ok, extra = {}) =>
            record({ action, agent_id: scope.agentId, board_id: board, key: t.key, ticket_id: t.id, why: v.why, ok, ...extra });

          if (kind === "stale-working") {
            if (unsticksThisTick >= orphanUnstickTickCap) {
              entry.result = "capped";
              continue;
            }
            unsticksThisTick++;
            entry.action = `-${LABEL.working}`;
            if (dryRun) entry.result = "planned";
            else {
              try {
                await plane.editIssue(t.id, { removeLabels: [workingId].filter(Boolean) }, ws, board);
                entry.result = "unstuck";
                record2("orphan.unstick", true);
              } catch (err) {
                entry.result = "failed";
                entry.error = message(err);
                out.errors.push(`${t.key}: removing stale ${LABEL.working} failed: ${entry.error}`);
                record2("orphan.unstick", false, { error: entry.error });
                continue;
              }
            }
            replace(t, { labels: t.labels.filter((l) => l !== LABEL.working) });
            continue;
          }

          // kind === "release"
          const priorReleases = releasedBefore.get(t.id) ?? 0;
          if (priorReleases >= ORPHAN_RELEASE_LIMIT) {
            entry.action = `+${LABEL.failed}${hasWorking ? ` -${LABEL.working}` : ""}`;
            if (!failedId) {
              entry.result = "skipped";
              out.warnings.push(`${t.key}: would hold with ${LABEL.failed} but the board has no such label`);
              continue;
            }
            if (dryRun) entry.result = "planned";
            else {
              try {
                await plane.editIssue(t.id, { addLabels: [failedId], removeLabels: hasWorking && workingId ? [workingId] : [] }, ws, board);
                record2("orphan.fail", true, { releases: priorReleases });
                entry.result = "held";
              } catch (err) {
                entry.result = "failed";
                entry.error = message(err);
                out.errors.push(`${t.key}: holding a looping orphan failed: ${entry.error}`);
                record2("orphan.fail", false, { error: entry.error });
                continue;
              }
              try {
                await plane.comment(t.id, failComment(v.why, priorReleases), ws, board);
              } catch (err) {
                out.warnings.push(`${t.key}: held, but the comment failed: ${message(err)}`);
              }
            }
            replace(t, { labels: [...t.labels.filter((l) => l !== LABEL.working), LABEL.failed].sort() });
            continue;
          }
          if (!todoId) {
            entry.result = "skipped";
            out.warnings.push(`${t.key}: cannot release, the board has no Todo lane`);
            continue;
          }
          if (releasedInScope >= orphanReleaseScopeCap || releasesThisTick >= orphanReleaseTickCap) {
            entry.result = "capped";
            continue;
          }
          releasedInScope++;
          releasesThisTick++;
          entry.action = `-> ${todoName}${hasWorking ? ` -${LABEL.working}` : ""}`;
          if (dryRun) entry.result = "planned";
          else {
            // Re-read live: a turn may have handed back or held it since the listing.
            let fresh;
            try {
              fresh = normalizeTicket(await plane.issue(t.id, ws, board), snap.ctx);
            } catch (err) {
              entry.result = "skipped";
              entry.why = `live re-read failed: ${message(err)}`;
              out.errors.push(`${t.key}: orphan ${entry.why}`);
              continue;
            }
            if (orphanKind(fresh, nowMs, orphanQuietMs) !== "release") {
              entry.result = "skipped";
              entry.why = "changed since the listing";
              continue;
            }
            try {
              await plane.editIssue(t.id, { removeLabels: hasWorking && workingId ? [workingId] : [], fields: { state: todoId } }, ws, board);
              entry.result = "released";
              record2("orphan.release", true, { to: todoName });
            } catch (err) {
              entry.result = "failed";
              entry.error = message(err);
              out.errors.push(`${t.key}: releasing an orphan failed: ${entry.error}`);
              record2("orphan.release", false, { error: entry.error });
              continue;
            }
            try {
              await plane.comment(t.id, releaseComment(v.why), ws, board);
            } catch (err) {
              out.warnings.push(`${t.key}: released, but the comment failed: ${message(err)}`);
            }
          }
          replace(t, { lane: "todo", stateId: todoId, stateName: todoName, labels: t.labels.filter((l) => l !== LABEL.working) });
        }
      }
    }

    // 3. Slots.
    const slots = slotsOf(scope.wip, mine);
    out.occupied = slots.occupied.map((t) => t.key);
    out.free = slots.free;
    out.overLimit = slots.overLimit;

    // 3b. Catch-up triage candidates (published after every scope has ticked).
    {
      const nowMs = started.getTime();
      const candidates = triageCandidatesOf(mine, nowMs, triageMinAgeMs);
      const fresh = [];
      const toPark = []; // {kind, t, attempts, lastAt}: the episode has used every attempt
      for (const t of candidates) {
        const ids = triageIds({ fleet, nats }, { boardId: board, ticketId: t.id, updatedAt: t.updatedAt, agentId: scope.agentId });
        if (triaged.has(ids.commandId)) {
          out.triageSeen.push(t.key);
          continue;
        }
        const v = await judgeBoardTurn({ plane, ws, board, ticket: t, stage: "triage", sends: turnSends.triage.get(t.id) ?? [], nowMs });
        if (v.action === "send") fresh.push({ t, ...ids });
        else if (v.action === "park") {
          toPark.push({ kind: "triage", t, attempts: v.attempts, lastAt: v.lastAt });
          out.triageSeen.push(t.key);
          out.triageHeld.push({ key: t.key, why: `${v.attempts} triage turns ended without lifecycle:triaged` });
        } else {
          out.triageSeen.push(t.key);
          out.triageHeld.push({ key: t.key, why: v.why });
          if (v.action === "unreadable") out.warnings.push(`${t.key}: triage not sent, ${v.why}; left alone`);
        }
      }
      // Review turns: an episode (since the handback) gets REVIEW_MAX_ATTEMPTS sends, REVIEW_RETRY_MS apart, then it is parked.
      for (const t of reviewCandidatesOf(mine, nowMs, reviewMinAgeMs)) {
        const v = await judgeBoardTurn({ plane, ws, board, ticket: t, stage: "review", sends: turnSends.review.get(t.id) ?? [], nowMs });
        if (v.action === "send") {
          fresh.push({ t, kind: "review", attempt: v.attempt, ...reviewIds({ fleet, nats }, { boardId: board, ticketId: t.id, updatedAt: t.updatedAt, agentId: scope.agentId, attempt: v.attempt }) });
        } else if (v.action === "park") {
          toPark.push({ kind: "review", t, attempts: v.attempts, lastAt: v.lastAt });
          out.reviewsSeen.push({ key: t.key, why: `${v.attempts} review turns ended without a verdict` });
        } else if (v.action === "wait") {
          out.reviewsSeen.push({ key: t.key, why: v.why });
        } else {
          out.reviewsSeen.push({ key: t.key, why: v.why });
          out.warnings.push(`${t.key}: review not sent, ${v.why}; left alone`);
        }
      }
      for (const p of toPark) await parkLoop({ scope, snap, out, ...p });
      // One board turn per scope per tick (a desk serializes its board turns), oldest ticket first.
      // Liveness is asked HERE, before a candidate takes the scope's turn (ADR 0001): a ticket
      // with a turn already queued or running (an n8n triage, the implementer still at it) is
      // skipped and the next oldest gets the turn. At most BOARD_TURN_PROBES probes per scope;
      // Candystore unknown stops the scope's board turns for this tick.
      const prefer = lastBoardTurn.get(`${scope.agentId}|${board}`) === "triage" ? "review" : "triage";
      const rank = (x) => ((x.kind ?? "triage") === prefer ? 0 : 1);
      fresh.sort((a, b) => rank(a) - rank(b) || compareTriage(a.t, b.t));
      let chosen = 0;
      let probes = 0;
      let blind = null;
      // Scope-busy guard (ADR 0002): the desk serializes board turns on its lease, so while ANY board
      // turn (any ticket) is queued or running for this scope, none is sent. Asked only when there is a
      // candidate. Candystore unknown stops the scope's board turns, like the per-ticket probe below.
      let busyWhy = null;
      if (scopeBusy && fresh.length) {
        const v = await scopeBusy({ scope, sent: boardTurnsSent.get(scope.agentId) ?? [] });
        if (v.unknown) {
          blind = v.why;
          out.warnings.push(`board turns not sent: ${v.why}`);
        } else if (v.busy) {
          busyWhy = `scope busy: ${v.why}`;
          out.boardTurnBusy = { why: v.why, turns: v.turns.map((x) => ({ invocationId: x.id, reason: x.reason, key: x.key, state: x.state, since: new Date(x.since).toISOString() })) };
        }
      }
      for (const { t, commandId, kind = "triage", attempt } of fresh) {
        const entry = { ...ticketRef(t), updatedAt: t.updatedAt, agentId: scope.agentId, commandId, ...(kind === "review" ? { attempt } : {}) };
        const list = kind === "review" ? out.reviews : out.triage;
        const capped = kind === "review" ? out.reviewsCapped : out.triageCapped;
        if (busyWhy) {
          list.push({ ...entry, result: "skipped", why: busyWhy });
          continue;
        }
        if (chosen >= triageScopeCap) {
          capped.push({ ...ticketRef(t), updatedAt: t.updatedAt, why: `scope cap (${triageScopeCap} board turn per scope per tick)` });
          continue;
        }
        if (!liveness && blind) {
          list.push({ ...entry, result: "skipped", why: blind });
          continue;
        }
        if (liveness) {
          if (blind) {
            list.push({ ...entry, result: "skipped", why: blind });
            continue;
          }
          if (probes >= BOARD_TURN_PROBES) {
            capped.push({ ...ticketRef(t), updatedAt: t.updatedAt, why: `probe cap (${BOARD_TURN_PROBES} liveness checks per scope per tick)` });
            continue;
          }
          probes++;
          const v = await liveness({ boardId: board, ticketId: t.id, key: t.key, sent: sentByTicket.get(t.id) ?? [] });
          if (v.unknown) {
            blind = v.why;
            out.warnings.push(`${t.key}: ${kind} not sent, ${v.why}`);
            list.push({ ...entry, result: "skipped", why: v.why });
            continue;
          }
          if (v.live) {
            // busyUntil: the ticket's 30-minute agent-activity window ends then (rules 3, 4); `krebs watch`
            // re-arms the board for it, since no event marks that moment.
            list.push({ ...entry, result: "skipped", why: `turn live: ${v.why}`, ...(Number.isFinite(v.busyUntil) ? { busyUntil: new Date(v.busyUntil).toISOString() } : {}) });
            continue;
          }
        }
        chosen++;
        list.push(entry);
        triagePlans.push({ kind, attempt, scope, snap, out, entry, ticket: t });
      }
    }

    // 4. Candidates.
    const { candidates, excluded } = candidatesOf(mine);
    out.excluded = excluded.map((e) => ({ key: e.ticket.key, why: e.why }));
    const workingId = snap.labelIdOf.get(LABEL.working);
    const blockers = [
      ...snap.lanes.problems,
      ...(workingId ? [] : [`board has no ${LABEL.working} label`]),
    ];
    if (blockers.length && slots.free > 0 && candidates.length) {
      out.errors.push(`cannot dispatch on ${scope.identifier ?? board}: ${blockers.join("; ")}`);
      out.waiting = candidates.map((t) => t.key);
      continue;
    }
    if (blockers.length) out.warnings.push(...blockers);

    const blockerOf = async (t) => {
      let rel;
      try {
        rel = await plane.relations(t.id, ws, board);
      } catch (err) {
        return `relations unreadable (${message(err)}); not dispatching blind`;
      }
      for (const raw of rel?.blocked_by ?? []) {
        const issueId = typeof raw === "string" ? raw : raw?.issue_id ?? raw?.id;
        const projectId = typeof raw === "string" ? null : raw?.project_id ?? null;
        if (!issueId) continue;
        const b = await groupOfIssue(ws, board, issueId, projectId);
        if (b.group === null) return `blocked by ${b.ref} (its state is unreadable)`;
        if (b.group !== "completed" && b.group !== "cancelled") return `blocked by ${b.ref} (${b.state ?? b.group})`;
      }
      return null;
    };
    const { picked, blocked, waiting } = await pickDispatches(candidates, slots.free, blockerOf);
    out.blocked = blocked.map((b) => ({ key: b.ticket.key, why: b.why }));
    out.waiting = waiting.map((t) => t.key);

    // 5. Dispatch.
    for (const candidate of picked) {
      const entry = { ...ticketRef(candidate) };
      out.dispatches.push(entry);
      let ticket = candidate;
      if (!dryRun) {
        try {
          ticket = normalizeTicket(await plane.issue(candidate.id, ws, board), snap.ctx);
        } catch (err) {
          entry.result = "skipped";
          entry.why = `live re-read failed: ${message(err)}`;
          out.errors.push(`${candidate.key}: ${entry.why}`);
          continue;
        }
        const why = dispatchGuard(ticket) ?? (ownerOf(ticket) === scope.agentId ? null : "moved to another scope");
        if (why) {
          entry.result = "skipped";
          entry.why = `changed since the listing: ${why}`;
          continue;
        }
      }
      const route = fleet.resolveFleetAgentForBoard(registry, board, scope.repo ?? "", ticket.labels);
      if (!route.eligible || route.agentId !== scope.agentId) {
        entry.result = "skipped";
        entry.why = `route refused: ${route.agentId || "(none)"} ${route.why}`;
        out.errors.push(`${ticket.key}: ${entry.why}`);
        continue;
      }
      const { dispatchId, commandId } = dispatchIds({ fleet, nats }, { boardId: board, ticketId: ticket.id, updatedAt: ticket.updatedAt, agentId: route.agentId });
      const observedAt = ts();
      const command = dispatchCommand({ fleet }, { scope, ticket, route, inProgressName: snap.lanes.inProgress.name, dispatchId, commandId, observedAt });
      const fields = { state: snap.lanes.inProgress.id };
      if (!ticket.startDate) fields.start_date = localDate(now(), timeZone);
      Object.assign(entry, { dispatchId, commandId, agentId: route.agentId, write: { state: snap.lanes.inProgress.name, addLabels: [LABEL.working], ...(fields.start_date ? { start_date: fields.start_date } : {}) } });
      if (dryRun) {
        entry.result = "planned";
        continue;
      }

      record({ action: "dispatch.intent", dispatch_id: dispatchId, command_id: commandId, agent_id: route.agentId, board_id: board, workspace: ws, ticket_id: ticket.id, key: ticket.key, command });
      try {
        await plane.editIssue(ticket.id, { addLabels: [workingId], fields }, ws, board);
        record({ action: "dispatch.write", dispatch_id: dispatchId, command_id: commandId, key: ticket.key, ok: true });
      } catch (err) {
        entry.result = "write failed";
        entry.error = message(err);
        out.errors.push(`${ticket.key}: dispatch write failed: ${entry.error}`);
        // A refusal is final; any other failure may have applied, so the next
        // tick checks the ticket live and publishes if the write is there.
        record({ action: "dispatch.write", dispatch_id: dispatchId, command_id: commandId, key: ticket.key, ok: false, definitive: definitiveFailure(err), error: entry.error });
        continue;
      }
      try {
        const res = await publish(command);
        entry.result = "dispatched";
        entry.subject = res?.subject ?? null;
        record({ action: "dispatch.publish", dispatch_id: dispatchId, command_id: commandId, agent_id: route.agentId, key: ticket.key, ok: true, subject: res?.subject ?? null });
      } catch (err) {
        entry.result = "publish failed";
        entry.error = message(err);
        out.errors.push(`${ticket.key}: written but publish failed (republished next tick): ${entry.error}`);
        record({ action: "dispatch.publish", dispatch_id: dispatchId, command_id: commandId, agent_id: route.agentId, key: ticket.key, ok: false, error: entry.error });
      }
    }
  }

  /**
   * A ticket whose episode has used every board-turn attempt: agent:failed plus one comment, so the
   * loop stops and a person can see why. Re-reads the ticket live and applies the same guard the send
   * would, and asks Candystore that no turn is live; anything uncertain leaves the ticket for the next tick.
   */
  async function parkLoop({ scope, snap, out, kind, t, attempts, lastAt }) {
    const ws = scope.workspace;
    const board = scope.boardId;
    const entry = { ...ticketRef(t), kind, attempts };
    out.parks.push(entry);
    const failedId = snap.labelIdOf.get(LABEL.failed);
    if (!failedId) {
      entry.result = "skipped";
      out.warnings.push(`${t.key}: would park with ${LABEL.failed} but the board has no such label`);
      return;
    }
    if (parksThisTick >= LOOP_PARK_TICK_CAP) {
      entry.result = "capped";
      return;
    }
    const record2 = (ok, extra = {}) =>
      record({ action: "loop.park", stage: kind, agent_id: scope.agentId, board_id: board, workspace: ws, key: t.key, ticket_id: t.id, attempts, ok, ...extra });
    if (dryRun) {
      entry.action = `+${LABEL.failed}`;
      entry.result = "planned";
      return;
    }
    let live;
    try {
      live = normalizeTicket(await plane.issue(t.id, ws, board), snap.ctx);
    } catch (err) {
      entry.result = "skipped";
      entry.why = `live re-read failed: ${message(err)}`;
      out.errors.push(`${t.key}: parking ${entry.why}`);
      return;
    }
    const nowMs = started.getTime();
    const why = (kind === "review" ? reviewGuard(live, nowMs, reviewMinAgeMs) : triageGuard(live, nowMs, triageMinAgeMs)) ?? (live.updatedAt !== t.updatedAt ? "changed since the listing (new version; next tick)" : null);
    if (why) {
      entry.result = "skipped";
      entry.why = `changed since the listing: ${why}`;
      return;
    }
    if (liveness) {
      const v = await liveness({ boardId: board, ticketId: t.id, key: t.key, sent: sentByTicket.get(t.id) ?? [] });
      if (v.unknown || v.live) {
        entry.result = "skipped";
        entry.why = v.unknown ? v.why : `turn live: ${v.why}`;
        return;
      }
    }
    parksThisTick++;
    entry.action = `+${LABEL.failed}`;
    try {
      await plane.editIssue(t.id, { addLabels: [failedId] }, ws, board);
      record2(true);
      entry.result = "parked";
    } catch (err) {
      entry.result = "failed";
      entry.error = message(err);
      out.errors.push(`${t.key}: parking a looping ${kind} failed: ${entry.error}`);
      record2(false, { error: entry.error });
      return;
    }
    try {
      await plane.comment(t.id, parkComment(kind, attempts, lastAt), ws, board);
    } catch (err) {
      out.warnings.push(`${t.key}: parked, but the comment failed: ${message(err)}`);
    }
  }

  /** One review turn: live re-read, guard, liveness, then the publish. */
  async function publishReview({ scope, snap, out, entry, ticket: listed, attempt }) {
    const ws = scope.workspace;
    const board = scope.boardId;
    let ticket = listed;
    if (!dryRun) {
      try {
        ticket = normalizeTicket(await plane.issue(listed.id, ws, board), snap.ctx);
      } catch (err) {
        entry.result = "skipped";
        entry.why = `live re-read failed: ${message(err)}`;
        out.errors.push(`${entry.key}: review ${entry.why}`);
        return;
      }
      const owner = fleet.resolveFleetAgentForBoard(registry, board, "", ticket.labels);
      const why = reviewGuard(ticket, started.getTime(), reviewMinAgeMs) ?? (owner.matchedBy === "board" && owner.agentId === scope.agentId ? null : "moved to another scope");
      if (why) {
        entry.result = "skipped";
        entry.why = `changed since the listing: ${why}`;
        return;
      }
      if (ticket.updatedAt !== listed.updatedAt) {
        entry.result = "skipped";
        entry.why = "changed since the listing (new version; next tick)";
        return;
      }
    }
    // Liveness was asked when the scope picked this ticket for its board turn (step 3b).
    const route = fleet.resolveFleetAgentForBoard(registry, board, scope.repo ?? "", ticket.labels);
    if (!route.eligible || route.agentId !== scope.agentId) {
      entry.result = "skipped";
      entry.why = `route refused: ${route.agentId || "(none)"} ${route.why}`;
      out.errors.push(`${ticket.key}: review ${entry.why}`);
      return;
    }
    if (dryRun) {
      entry.result = "planned";
      return;
    }
    const { reviewId, commandId } = reviewIds({ fleet, nats }, { boardId: board, ticketId: ticket.id, updatedAt: ticket.updatedAt, agentId: route.agentId, attempt });
    Object.assign(entry, { reviewId, commandId });
    const command = reviewCommand({ fleet }, { scope, ticket, route, commandId, attempt, observedAt: new Date(ticket.updatedAt).toISOString() });
    const base = { command_id: commandId, review_id: reviewId, agent_id: route.agentId, board_id: board, workspace: ws, ticket_id: ticket.id, key: ticket.key, ticket_updated_at: ticket.updatedAt, attempt };
    try {
      const res = await publish(command);
      entry.result = "published";
      entry.subject = res?.subject ?? null;
      record({ action: "review.publish", ...base, ok: true, subject: res?.subject ?? null });
    } catch (err) {
      entry.result = "publish failed";
      entry.error = message(err);
      out.errors.push(`${ticket.key}: review publish failed (retried next tick, same command id): ${entry.error}`);
      record({ action: "review.publish", ...base, ok: false, error: entry.error });
    }
  }

  // Board turns (catch-up triage, review): tick-wide cap (oldest first across scopes), then one publish each.
  // Triage first (it gates dispatch; a review backlog from the 11-14 migration is weeks old and
  // would otherwise win every oldest-first sort), then reviews; oldest first within each.
  const kindRank = (plan) => (plan.kind === "review" ? 1 : 0);
  triagePlans.sort((a, b) => kindRank(a) - kindRank(b) || compareTriage(a.ticket, b.ticket) || (a.scope.agentId < b.scope.agentId ? -1 : 1));
  for (const [i, plan] of triagePlans.entries()) {
    const { scope, snap, out, entry } = plan;
    if (plan.kind === "review") {
      if (i >= triageTickCap) {
        out.reviews.splice(out.reviews.indexOf(entry), 1);
        out.reviewsCapped.push({ key: entry.key, ticketId: entry.ticketId, title: entry.title, updatedAt: entry.updatedAt, why: `tick cap (${triageTickCap} per tick)` });
        continue;
      }
      await publishReview(plan);
      continue;
    }
    if (i >= triageTickCap) {
      out.triage.splice(out.triage.indexOf(entry), 1);
      out.triageCapped.push({ key: entry.key, ticketId: entry.ticketId, title: entry.title, updatedAt: entry.updatedAt, why: `tick cap (${triageTickCap} per tick)` });
      continue;
    }
    const ws = scope.workspace;
    const board = scope.boardId;
    let ticket = plan.ticket;
    if (!dryRun) {
      try {
        ticket = normalizeTicket(await plane.issue(ticket.id, ws, board), snap.ctx);
      } catch (err) {
        entry.result = "skipped";
        entry.why = `live re-read failed: ${message(err)}`;
        out.errors.push(`${entry.key}: triage ${entry.why}`);
        continue;
      }
      const owner = fleet.resolveFleetAgentForBoard(registry, board, "", ticket.labels);
      const why = triageGuard(ticket, started.getTime(), triageMinAgeMs) ?? (owner.matchedBy === "board" && owner.agentId === scope.agentId ? null : "moved to another scope");
      if (why) {
        entry.result = "skipped";
        entry.why = `changed since the listing: ${why}`;
        continue;
      }
    }
    const route = fleet.resolveFleetAgentForBoard(registry, board, scope.repo ?? "", ticket.labels);
    if (!route.eligible || route.agentId !== scope.agentId) {
      entry.result = "skipped";
      entry.why = `route refused: ${route.agentId || "(none)"} ${route.why}`;
      out.errors.push(`${ticket.key}: triage ${entry.why}`);
      continue;
    }
    const { triageId, commandId } = triageIds({ fleet, nats }, { boardId: board, ticketId: ticket.id, updatedAt: ticket.updatedAt, agentId: route.agentId });
    Object.assign(entry, { updatedAt: ticket.updatedAt, triageId, commandId });
    if (triaged.has(commandId)) {
      entry.result = "skipped";
      entry.why = "this ticket version was already triaged";
      continue;
    }
    if (dryRun) {
      entry.result = "planned";
      continue;
    }
    const command = triageCommand({ fleet }, { scope, ticket, route, todoName: ticket.stateName ?? "Todo", commandId, observedAt: new Date(ticket.updatedAt).toISOString() });
    try {
      const res = await publish(command);
      entry.result = "published";
      entry.subject = res?.subject ?? null;
      triaged.add(commandId);
      record({ action: "triage.publish", command_id: commandId, triage_id: triageId, agent_id: route.agentId, board_id: board, workspace: ws, ticket_id: ticket.id, key: ticket.key, ticket_updated_at: ticket.updatedAt, ok: true, subject: res?.subject ?? null });
    } catch (err) {
      entry.result = "publish failed";
      entry.error = message(err);
      out.errors.push(`${ticket.key}: triage publish failed (retried next tick, same command id): ${entry.error}`);
      record({ action: "triage.publish", command_id: commandId, triage_id: triageId, agent_id: route.agentId, board_id: board, workspace: ws, ticket_id: ticket.id, key: ticket.key, ticket_updated_at: ticket.updatedAt, ok: false, error: entry.error });
    }
  }

  report.ok = report.errors.length === 0 && report.scopes.every((s) => s.errors.length === 0);
  // The finished plan, for read-only callers (`krebs status`). It changes nothing in the report.
  if (inspect) inspect(inspected.map((i) => ({ scope: i.scope, out: i.out, snap: i.snap, tickets: i.tickets() })));
  record({
    action: "tick",
    ok: report.ok,
    trigger,
    ...(triggerDetail ? { trigger_detail: triggerDetail } : {}),
    ...(boardFilter ? { board: boardFilter } : {}),
    scopes: report.scopes.length,
    dispatched: report.scopes.reduce((n, s) => n + s.dispatches.filter((d) => d.result === "dispatched").length, 0),
    repaired: report.scopes.reduce((n, s) => n + s.repairs.filter((r) => r.result === "repaired").length, 0),
    republished: report.scopes.reduce((n, s) => n + s.republishes.filter((r) => r.result === "republished").length, 0),
    triaged: report.scopes.reduce((n, s) => n + s.triage.filter((t) => t.result === "published").length, 0),
    reviews: report.scopes.reduce((n, s) => n + s.reviews.filter((t) => t.result === "published").length, 0),
    busy: report.scopes.filter((s) => s.boardTurnBusy).length,
    errors: report.scopes.reduce((n, s) => n + s.errors.length, 0),
  });
  return report;
}

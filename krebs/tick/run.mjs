// One Krebs tick: for every scope, republish owed dispatches, repair the two
// invariants, do the slot math and dispatch into free slots.
//
// Everything with a side effect is injected (plane, publish, journal, now), so
// the tests drive it with fakes and --dry-run drives it with no writer at all.

import { LABEL, SPEC_VERSION, heldBy, laneModel } from "./lifecycle.mjs";
import { candidatesOf, dispatchGuard, normalizeTicket, pickDispatches, repairsFor, slotsOf } from "./select.mjs";
import { PENDING_MAX_AGE_MS, pendingPublishes } from "./journal.mjs";
import { dispatchPrompt } from "./prompt.mjs";

export const COMMAND_TYPE = "bloodbank.agent.invocation.start";
export const INVOCATION_REASON = "ticket-delegation";
/** The operation fleetCommandId hashes in; the n8n Fleet node's delegation operation. */
export const DISPATCH_OPERATION = "delegateTicket";
export const KREBS_SOURCE = "urn:33god:service:krebs-tick";
export const KREBS_ACTOR = Object.freeze({ type: "service", agent_id: "krebs.tick" });
export const PROVIDER_EVENT_TYPE = "krebs.dispatch";

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
}) {
  const started = now();
  const tickId = `tick:${started.toISOString()}`;
  const ts = () => now().toISOString();
  const record = (entry) => {
    if (!dryRun) journal.append({ ts: ts(), tick: tickId, ...entry });
  };
  const pending = pendingPublishes(journal.read());
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
      dispatches: [],
      blocked: [],
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
    const mine = snap.tickets.filter((t) => !t.archived && ownerOf(t) === scope.agentId);
    out.tickets = mine.length;

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

    // 3. Slots.
    const slots = slotsOf(scope.wip, mine);
    out.occupied = slots.occupied.map((t) => t.key);
    out.free = slots.free;
    out.overLimit = slots.overLimit;

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

  report.ok = report.errors.length === 0 && report.scopes.every((s) => s.errors.length === 0);
  record({
    action: "tick",
    ok: report.ok,
    scopes: report.scopes.length,
    dispatched: report.scopes.reduce((n, s) => n + s.dispatches.filter((d) => d.result === "dispatched").length, 0),
    repaired: report.scopes.reduce((n, s) => n + s.repairs.filter((r) => r.result === "repaired").length, 0),
    republished: report.scopes.reduce((n, s) => n + s.republishes.filter((r) => r.result === "republished").length, 0),
    errors: report.scopes.reduce((n, s) => n + s.errors.length, 0),
  });
  return report;
}

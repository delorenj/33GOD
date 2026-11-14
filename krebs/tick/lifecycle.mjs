// Krebs lifecycle v2 vocabulary (spec/lifecycle.v2.yaml), as the tick reads it.
//
// Only what `krebs tick` needs: the six lifecycle labels, which of them hold a
// ticket out of the flow, what makes a ticket a container, the dispatch order,
// and how a board's states map onto the five stock lanes.

export const SPEC_VERSION = "2.0.0";

export const LABEL = Object.freeze({
  working: "agent:working",
  triaged: "lifecycle:triaged",
  review: "lifecycle:review",
  needsInput: "lifecycle:needs-input",
  blocked: "lifecycle:blocked",
  failed: "agent:failed",
});

/** spec hold_labels: never dispatched, never hold a slot. */
export const HOLD_LABELS = Object.freeze([LABEL.needsInput, LABEL.blocked, LABEL.failed]);

/** spec slots.default; a registry row overrides it with plane.wip. */
export const DEFAULT_WIP = 2;

/** Dispatch order, second key (spec transitions.dispatch.order). */
export const PRIORITY_RANK = Object.freeze({ urgent: 0, high: 1, medium: 2, low: 3, none: 4 });

/** The hold labels a ticket carries, in spec order. `names` are lowercased label names. */
export function heldBy(names) {
  return HOLD_LABELS.filter((label) => names.includes(label));
}

/** spec container_labels: [epic, "epic:*"]. */
export function isContainer(names) {
  return names.some((name) => name === "epic" || name.startsWith("epic:"));
}

export function priorityRank(priority) {
  const rank = PRIORITY_RANK[String(priority ?? "none").toLowerCase()];
  return rank === undefined ? PRIORITY_RANK.none : rank;
}

/**
 * How a board's Plane states map onto the lanes the tick reasons about.
 *
 *   todo        the Todo lane: the state named "Todo", else the board's only
 *               unstarted-group state. Only Todo tickets are dispatch candidates.
 *   started     every started-group state. On a v2 board that is exactly
 *               In Progress; on a board still carrying extra started lanes,
 *               counting all of them as occupied is the conservative reading.
 *   terminal    completed and cancelled groups (Done, Cancelled).
 *   inProgress  the dispatch target: the state named "In Progress", else the
 *               only started-group state. Null when the board has neither, and
 *               then nothing on that board can be dispatched.
 */
export function laneModel(states) {
  const rows = Array.isArray(states) ? states : [];
  const named = (name) => rows.filter((s) => String(s.name ?? "").trim().toLowerCase() === name);
  const grouped = (group) => rows.filter((s) => s.group === group);

  const todoNamed = named("todo");
  const unstarted = grouped("unstarted");
  const todo = todoNamed.length ? todoNamed : unstarted.length === 1 ? unstarted : [];
  const started = grouped("started");
  const inProgressNamed = named("in progress").filter((s) => s.group === "started");
  const inProgress = inProgressNamed[0] ?? (started.length === 1 ? started[0] : null);

  const laneOf = new Map();
  for (const s of rows) {
    if (todo.includes(s)) laneOf.set(s.id, "todo");
    else if (s.group === "started") laneOf.set(s.id, "started");
    else if (s.group === "completed" || s.group === "cancelled") laneOf.set(s.id, "terminal");
    else if (s.group === "backlog") laneOf.set(s.id, "backlog");
    else laneOf.set(s.id, "other");
  }
  return {
    laneOf,
    groupOf: new Map(rows.map((s) => [s.id, s.group])),
    nameOf: new Map(rows.map((s) => [s.id, s.name])),
    todoStateIds: todo.map((s) => s.id),
    inProgress: inProgress ? { id: inProgress.id, name: inProgress.name } : null,
    problems: [
      ...(todo.length ? [] : ["board has no Todo lane (no state named Todo and not exactly one unstarted state)"]),
      ...(inProgress ? [] : ["board has no In Progress lane (no started state named In Progress and not exactly one started state)"]),
    ],
  };
}

/** Lowercased, trimmed, unique label names. */
export function normalizeNames(names) {
  return [...new Set((names ?? []).map((n) => String(n ?? "").trim().toLowerCase()).filter(Boolean))].sort();
}

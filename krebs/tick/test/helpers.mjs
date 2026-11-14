// Test fixtures: an in-memory Plane that records every call, a fake publisher,
// and a registry shaped like ~/.hermes/agents-registry.yaml.

import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export const WS = "33god";
export const TOLT = "b-tolt";
export const SOLO = "b-solo";
export const OTHER = "b-other";

export const STATES = [
  { id: "s-backlog", name: "Backlog", group: "backlog", default: true },
  { id: "s-todo", name: "Todo", group: "unstarted" },
  { id: "s-ip", name: "In Progress", group: "started" },
  { id: "s-done", name: "Done", group: "completed" },
  { id: "s-cancel", name: "Cancelled", group: "cancelled" },
];

export const LABEL_NAMES = [
  "agent:working", "lifecycle:triaged", "lifecycle:review", "lifecycle:needs-input",
  "lifecycle:blocked", "agent:failed", "epic", "epic:big-thing", "repo:game", "repo:forge", "repo:tolt", "feature",
];

export const labelId = (name) => `l-${name}`;

const STATE_OF = { backlog: "s-backlog", todo: "s-todo", ip: "s-ip", done: "s-done", cancel: "s-cancel" };

let counter = 0;
export function issue({ seq, state = "todo", labels = [], sort = 1000, priority = "none", start = null, updated = "2026-11-14T10:00:00Z", name } = {}) {
  counter++;
  return {
    id: `i-${seq ?? counter}`,
    sequence_id: seq ?? counter,
    name: name ?? `ticket ${seq ?? counter}`,
    state: STATE_OF[state] ?? state,
    labels: labels.map(labelId),
    sort_order: sort,
    priority,
    start_date: start,
    updated_at: updated,
    archived_at: null,
    is_draft: false,
  };
}

export class FakePlane {
  constructor(boards) {
    // boards: { [boardId]: { issues: [...], relations: { [issueId]: {...} }, states?, labels? } }
    this.boards = {};
    for (const [id, b] of Object.entries(boards)) {
      this.boards[id] = {
        states: b.states ?? STATES,
        labels: b.labels ?? LABEL_NAMES.map((name) => ({ id: labelId(name), name })),
        issues: new Map((b.issues ?? []).map((i) => [i.id, structuredClone(i)])),
        relations: b.relations ?? {},
      };
    }
    this.calls = [];
    this.failWrite = null; // (issueId) => Error | null
    this.writeSeq = 0;
  }

  board(id) {
    const b = this.boards[id];
    if (!b) throw Object.assign(new Error(`GET board ${id} -> HTTP 404`), { status: 404 });
    return b;
  }

  async states(ws, board) {
    this.calls.push({ method: "states", board });
    return structuredClone(this.board(board).states);
  }

  async collection(kind, ws, board) {
    this.calls.push({ method: "collection", kind, board });
    if (kind !== "labels") throw new Error(`fake has no ${kind}`);
    return structuredClone(this.board(board).labels);
  }

  async issues({ ws, board }) {
    this.calls.push({ method: "issues", board });
    return [...this.board(board).issues.values()].map((i) => structuredClone(i));
  }

  async issue(id, ws, board) {
    this.calls.push({ method: "issue", id, board });
    const found = this.board(board).issues.get(id);
    if (!found) throw Object.assign(new Error(`GET issue ${id} -> HTTP 404`), { status: 404 });
    return structuredClone(found);
  }

  async relations(id, ws, board) {
    this.calls.push({ method: "relations", id, board });
    return structuredClone(this.board(board).relations[id] ?? { blocked_by: [], blocking: [], relates_to: [] });
  }

  async editIssue(id, { addLabels = [], removeLabels = [], fields = {} } = {}, ws, board) {
    this.calls.push({ method: "editIssue", id, board, addLabels: [...addLabels], removeLabels: [...removeLabels], fields: { ...fields } });
    const err = this.failWrite?.(id);
    if (err) throw err;
    const row = this.board(board).issues.get(id);
    if (!row) throw Object.assign(new Error(`PATCH ${id} -> HTTP 404`), { status: 404 });
    row.labels = row.labels.filter((l) => !removeLabels.includes(l));
    for (const l of addLabels) if (!row.labels.includes(l)) row.labels.push(l);
    Object.assign(row, fields);
    row.updated_at = `2026-11-14T12:00:${String(++this.writeSeq).padStart(2, "0")}Z`;
    return structuredClone(row);
  }

  writes() {
    return this.calls.filter((c) => c.method === "editIssue");
  }
}

export function fakePublisher({ fail = false } = {}) {
  const sent = [];
  const publish = async (command) => {
    sent.push(structuredClone(command));
    if (typeof fail === "function" ? fail(command) : fail) throw new Error("nats: connection refused");
    return { subject: "bloodbank.cmd.agent.invocation.start", commandId: command.commandId, eventId: command.eventId };
  };
  publish.sent = sent;
  return publish;
}

function agent(id, plane, extra = {}) {
  return {
    repo: extra.repo ?? id.replace(/-pm$/, ""),
    role: "pm",
    type: "hermes",
    profile_name: id,
    project_path: extra.project_path ?? `/nonexistent/${id}`,
    bloodbank: { enabled: true, gateway_scope: "fleet", target_agent_id: id, ...(extra.bloodbank ?? {}) },
    ...(plane ? { plane } : {}),
    ...Object.fromEntries(Object.entries(extra).filter(([k]) => !["repo", "project_path", "bloodbank"].includes(k))),
  };
}

/** A registry like the real one: TOLT shared by three scopes, an advisory launch director, a solo board. */
export function registryFixture() {
  return {
    schema_version: 1,
    agents: {
      "tolt-pm": agent("tolt-pm", { workspace: WS, project_id: TOLT, identifier: "TOLT", scope_label: "repo:game", scope_default: true }, { repo: "tolt" }),
      "lost-things-forge-pm": agent("lost-things-forge-pm", { workspace: WS, project_id: TOLT, identifier: "TOLT", scope_label: "repo:forge" }),
      "tolt-director": agent("tolt-director", { workspace: WS, project_id: TOLT, identifier: "TOLT", scope_label: "repo:tolt" }, { repo: "tolt", role: "director" }),
      "tolt-launch-director": agent("tolt-launch-director", { workspace: WS, identifier: "TOLT" }, { board_scope: "advisory" }),
      "solo-pm": agent("solo-pm", { workspace: WS, project_id: SOLO, identifier: "SOLO", wip: 1, review: true }),
      "other-pm": agent("other-pm", { workspace: WS, project_id: OTHER, identifier: "OTH" }),
      "retired-pm": agent("retired-pm", { workspace: WS, project_id: "b-retired", identifier: "RET" }, { bloodbank: { enabled: false } }),
      "no-plane": agent("no-plane", null),
    },
  };
}

export function tempDir() {
  return mkdtempSync(join(tmpdir(), "krebs-tick-test-"));
}

export const NOW = new Date("2026-11-14T15:00:00Z");

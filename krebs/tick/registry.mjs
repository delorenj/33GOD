// Scopes from the Hermes agents registry (~/.hermes/agents-registry.yaml).
//
// A scope is one registry row that owns a board, or a board plus a scope label
// (spec slots.unit). Every agent row with a `plane:` block is considered; a row
// is a scope only if it can actually own work:
//
//   - its plane block names a board (`project_id`, or `board_id`). Launch
//     director rows carry `plane: {workspace, identifier}` with no board id and
//     `board_scope: advisory`: they are verdict givers, not owners;
//   - it is not advisory (`board_scope: advisory`);
//   - it is not retired. Retirement in this registry is `flume retire`: it sets
//     `bloodbank.enabled: false` and removes the plane claim, so a retired row
//     normally never reaches here. A row-level `status`/`employment` of
//     `retired` or `suspended`, `retired: true` or a `retired_at` is honoured too;
//   - it is fleet-addressable, by the same four checks the n8n Fleet node and
//     the hermes gateway apply (profile_name, a bloodbank block whose `enabled`
//     resolves to enabled, gateway_scope fleet, target_agent_id equal to the id);
//   - its repo is not fenced: when the row has a `project_path`, that repo's
//     `.project.json` `execution.mode`, when present, must be `legacy`. Missing
//     or unreadable manifests count as legacy, exactly as the Fleet node reads
//     them (best effort: a row whose project_path is a parent repo, e.g. tolt-pm
//     at ~/code/tolt, is judged by that parent's manifest).
//
// Ownership of a ticket on a shared board is NOT decided here: run.mjs routes
// each ticket with the same resolver n8n uses (scope_label / scope_default), so
// Krebs and the triage lane agree on who owns what.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { DEFAULT_WIP } from "./lifecycle.mjs";

const RETIRED = new Set(["retired", "suspended", "offboarded"]);

function mapping(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value : undefined;
}

function text(value) {
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return "";
}

/** A scope_label declaration (string or list), lowercased, as n8n's scope.ts reads it. */
export function scopeLabelsOf(plane) {
  const raw = plane.scope_label ?? plane.scope_labels;
  const list = Array.isArray(raw) ? raw : [raw];
  return [...new Set(list.map((v) => text(v).toLowerCase()).filter(Boolean))].sort();
}

/** plane.wip: a non-negative integer, else the default (with a warning when it was set but unusable). */
export function wipOf(plane) {
  if (!Object.prototype.hasOwnProperty.call(plane, "wip") || plane.wip === null) return { wip: DEFAULT_WIP };
  const value = plane.wip;
  if (Number.isInteger(value) && value >= 0) return { wip: value };
  return { wip: DEFAULT_WIP, warning: `plane.wip ${JSON.stringify(value)} is not a non-negative integer; using ${DEFAULT_WIP}` };
}

/** Why a row is retired, or null. */
export function retiredWhy(row) {
  for (const key of ["status", "employment"]) {
    const value = text(row[key]).toLowerCase();
    if (RETIRED.has(value)) return `${key} is ${value}`;
  }
  if (row.retired === true) return "retired: true";
  if (text(row.retired_at)) return `retired_at ${text(row.retired_at)}`;
  return null;
}

/**
 * Fleet eligibility of one row, mirroring n8n fleet.ts resolveFleetAgentForBoard
 * (which mirrors hermes-gateway contract.py). `activation` is the n8n package's
 * bloodbankActivation. Returns null when eligible, else the reason.
 */
export function ineligibleWhy(agentId, row, activation) {
  if (!text(row.profile_name)) return "no profile_name";
  const bloodbank = mapping(row.bloodbank);
  if (!bloodbank) return "no bloodbank block";
  const state = activation(bloodbank);
  if (state === "disabled") return "bloodbank.enabled is false";
  if (state !== "enabled") return `bloodbank.enabled is invalid (${JSON.stringify(bloodbank.enabled)})`;
  if (bloodbank.gateway_scope !== "fleet") return "bloodbank.gateway_scope is not fleet";
  if (text(bloodbank.target_agent_id) !== agentId) return `bloodbank.target_agent_id mismatch (${text(bloodbank.target_agent_id) || "unset"})`;
  return null;
}

/** `.project.json` execution.mode at a repo path, or "legacy" (same rule as the n8n Fleet node's executionMode). */
export function executionModeAt(projectPath) {
  try {
    const manifest = JSON.parse(readFileSync(join(projectPath, ".project.json"), "utf8"));
    const execution = manifest && typeof manifest === "object" ? manifest.execution : undefined;
    const mode = execution && typeof execution === "object" ? execution.mode : undefined;
    return typeof mode === "string" && mode.trim() ? mode.trim() : "legacy";
  } catch {
    return "legacy";
  }
}

/** Does `--board KEY` select this board? KEY is the identifier (case-insensitive) or the board id. */
export function boardMatches(key, { identifier, boardId }) {
  if (!key) return true;
  const want = String(key).trim().toLowerCase();
  return want === String(identifier ?? "").toLowerCase() || want === String(boardId ?? "").toLowerCase();
}

/**
 * Every scope the registry defines, and every plane-bearing row that is not one (with why).
 *
 * opts.activation      bloodbankActivation from the n8n package (required)
 * opts.executionMode   (projectPath) => mode; default reads .project.json
 * opts.board           --board KEY filter (rows on other boards are left out entirely)
 * opts.defaultWorkspace  used when a plane block names no workspace
 */
export function scopesFromRegistry(registry, { activation, executionMode = executionModeAt, board, defaultWorkspace } = {}) {
  if (typeof activation !== "function") throw new Error("scopesFromRegistry needs the bloodbankActivation function");
  const agents = mapping(mapping(registry)?.agents);
  if (!agents) throw new Error("agents registry has no agents mapping");

  const scopes = [];
  const skipped = [];
  let matchedRows = 0;
  for (const agentId of Object.keys(agents).sort()) {
    const row = mapping(agents[agentId]);
    const plane = row && mapping(row.plane);
    if (!plane) continue;
    const boardId = text(plane.project_id) || text(plane.board_id);
    const identifier = text(plane.identifier) || null;
    if (!boardMatches(board, { identifier, boardId })) continue;
    matchedRows++;
    const where = { agentId, identifier, boardId: boardId || null };
    const skip = (why) => skipped.push({ ...where, why });

    if (!boardId) { skip("plane block names no board (project_id); advisory row, not an owner"); continue; }
    if (text(row.board_scope).toLowerCase() === "advisory") { skip("board_scope is advisory"); continue; }
    const retired = retiredWhy(row);
    if (retired) { skip(`retired (${retired})`); continue; }
    const ineligible = ineligibleWhy(agentId, row, activation);
    if (ineligible) { skip(`not fleet-addressable: ${ineligible}`); continue; }
    const projectPath = text(row.project_path) || text(row.repo_path) || null;
    if (projectPath) {
      const mode = executionMode(projectPath);
      if (mode !== "legacy") { skip(`fenced: ${projectPath}/.project.json execution.mode is ${mode} (v2 engine retired)`); continue; }
    }
    const workspace = text(plane.workspace) || defaultWorkspace || null;
    if (!workspace) { skip("plane block names no workspace"); continue; }

    const { wip, warning } = wipOf(plane);
    scopes.push({
      agentId,
      repo: text(row.repo) || null,
      profileName: text(row.profile_name),
      projectPath,
      workspace,
      boardId,
      identifier,
      scopeLabels: scopeLabelsOf(plane),
      scopeDefault: plane.scope_default === true,
      wip,
      review: plane.review === true,
      warnings: warning ? [warning] : [],
    });
  }
  return { scopes, skipped, matchedRows };
}

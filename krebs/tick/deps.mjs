// The real collaborators a tick runs against, loaded from sibling 33GOD
// checkouts so Krebs carries no copy of them and no install step:
//
//   Pilot      <33GOD>/pilot/src/plane.js (class Plane) and src/config.js
//              (homeBinding: the base URL and credential reference px itself
//              uses outside a repo binding, from ~/.config/pilot/config.json /
//              PLANE_API_KEY / the built-in op:// reference). Krebs writes as
//              that shared Pilot identity, never as an agent's own key.
//   Bloodbank  <33GOD>/bloodbank/integrations/n8n-nodes-bloodbank/dist: the
//              built n8n package (CommonJS). fleet.js for routing, ids and the
//              delegation prompt; nats.js for the envelope and the publish;
//              registry.js for the registry path, YAML load and the
//              bloodbank.enabled rule.
//
// KREBS_PILOT_DIR and KREBS_BLOODBANK_N8N_DIR override the two locations.

import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const KREBS_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const GOD_ROOT = resolve(KREBS_ROOT, "..");

export function pilotDir(env = process.env) {
  return resolve(env.KREBS_PILOT_DIR || join(GOD_ROOT, "pilot"));
}

export function bloodbankN8nDir(env = process.env) {
  return resolve(env.KREBS_BLOODBANK_N8N_DIR || join(GOD_ROOT, "bloodbank", "integrations", "n8n-nodes-bloodbank"));
}

const require = createRequire(import.meta.url);

/** The n8n package's pure helpers (no connection is opened by loading them). */
export function loadBloodbank(env = process.env) {
  const dist = join(bloodbankN8nDir(env), "dist");
  let fleet, nats, registry;
  try {
    fleet = require(join(dist, "fleet.js"));
    nats = require(join(dist, "nats.js"));
    registry = require(join(dist, "registry.js"));
  } catch (err) {
    throw new Error(`cannot load the bloodbank n8n package dist at ${dist} (build it: npm run build there): ${err.message}`);
  }
  for (const [mod, names] of [
    [fleet, ["resolveFleetAgentForBoard", "ticketCorrelationId", "fleetCommandId", "ticketFactsFromEnvelope", "delegationPrompt"]],
    [nats, ["buildEnvelope", "deterministicUuid", "publish", "validateEnvelope"]],
    [registry, ["hermesRegistryPath", "loadHermesRegistry", "bloodbankActivation"]],
  ]) {
    for (const name of names) {
      if (typeof mod[name] !== "function") throw new Error(`bloodbank n8n dist at ${dist} has no ${name}(); rebuild it`);
    }
  }
  return { fleet, nats, registry, dist };
}

/** Pilot's Plane client bound to the shared Pilot credential. */
export async function loadPlane(env = process.env) {
  const dir = pilotDir(env);
  const { Plane } = await import(pathToFileURL(join(dir, "src", "plane.js")).href);
  const { homeBinding } = await import(pathToFileURL(join(dir, "src", "config.js")).href);
  const binding = homeBinding();
  const plane = new Plane({ ...binding, workspace: binding.workspace || "33god" });
  return { plane, defaultWorkspace: binding.workspace || "33god", base: binding.base };
}

/** The NATS server a real publish goes to: NATS_URL, else the local default. */
export function natsUrl(env = process.env) {
  return env.KREBS_NATS_URL || env.NATS_URL || "nats://127.0.0.1:4222";
}

/** The real publisher: the n8n package's publish(), one connection per call. */
export function realPublisher(nats, env = process.env) {
  const host = natsUrl(env);
  return async (command) => nats.publish({ ...command, host, timeoutMs: Number(env.KREBS_NATS_TIMEOUT_MS) || 5000 });
}

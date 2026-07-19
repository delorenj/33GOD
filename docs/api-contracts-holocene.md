# Holocene HTTP API Contracts

## Boundary

The live Fastify API listens on port 4000 and exposes host-control capabilities. It has wildcard CORS and no application authentication/authorization. Treat every route as privileged and restrict the listener to a trusted boundary.

## Health and Clock

- `GET /health`
- `GET /api/clock/state`
- `POST /api/clock/in`
- `POST /api/clock/out`

Clock code currently sends `Authentication`; the specification requires `Authorization`.

## Fleet and Organization

- Fleet snapshot and five-second SSE stream under `/api/modules/hermes-fleet/`
- Agent log and per-service action routes
- Fleet-wide restart and template synchronization actions
- `GET /api/modules/org/tree`

Fleet history reads Candystore, trying `/api/v1/events` then `/events`. Errors become an empty history array.

## Systems, Containers, and Tooling

- Systems inventory, history, preview, terminal, and action routes
- `GET /api/modules/containers/snapshot`
- Tooling definitions, stats, refresh, and SSE routes

Action inputs generally use allowlists and `execFile`; preview/log paths apply containment checks. The preview roots are still broad enough to expose sensitive configuration to an authorized caller.

## Web Route Handlers

Next.js provides browser proxies and HQ Telegram Mini App routes. `/api/modules/:path*` is rewritten to the API; HQ has separate init-data verification. An empty HQ allowlist accepts any valid user for the bot, and future-dated auth timestamps are not rejected.

## Availability Contract

SSE is snapshot polling per connection, not Bloodbank consumption. Each fleet client can trigger serial systemd work. Candystore failure is currently silent; callers must not equate an empty history with a healthy zero-event state.

## Lifecycle Client Contract

The implemented Holocene API reads a versioned Lifecycle projection from
Candystore and returns explicit unknown/degraded output when it is missing or
stale. The web surface preserves identity, spec/state versions, provenance,
freshness, status/health/phase/fingerprint, frontier, obligations,
blockers/gates, and stable verdicts.

High-level actions accept the selected authority frontier, expected state
version, actor, capability ID, and intent parameters. Capability version and
all semantic IDs are derived from the authoritative projection and full
immutable request; caller-supplied substitutes are rejected. Missing, wrong, or
`allowed=false` frontier items publish nothing. Gate resolution also publishes
nothing unless `parameters.resolution` is present.

The publisher requires its subject argument to equal `envelope.subject`. Its
core NATS TCP write plus PING/PONG receipt is reported as broker processing,
with `durable_jetstream_acknowledged: false` and `authority_accepted: false`;
it is not described as queueing or durable acceptance. Holocene does not
optimistically update local state, and renders only the later authoritative
projection/verdict as truth.

## Lifecycle Browser Proof Contract

`scripts/prove-lifecycle-browser.mjs` opens `/lifecycle/<id>` in Chromium and
derives its request exclusively from the rendered current projection. Its JSON
receipt records the exact DOM frontier/actor/grant/version, confirmation text
and acceptance, actual clicked control, browser-originated request body, raw and
parsed HTTP 202 body, non-authoritative command identities, initial/final
rendered state and source causality, matching command verdict, and desktop/
mobile screenshot paths plus hashes. It neither intercepts network routes nor
predicts a transition. The context blocks service workers and requires the 202
response to belong to the exact captured browser request. Completion requires
the later Lifecycle-owned outcome to appear through the Candystore-backed
projection.

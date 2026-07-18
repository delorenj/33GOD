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

## Planned Lifecycle Client Contract

There is no deployed lifecycle API or Holocene adapter today. The target
Holocene surface may read versioned authoritative snapshots and submit
idempotent high-level intent commands through Bloodbank. It must expose pending,
accepted, rejected, stale, and unavailable outcomes without optimistically
writing local state. Lifecycle performs capability validation and reconciliation;
Holocene only renders the result.

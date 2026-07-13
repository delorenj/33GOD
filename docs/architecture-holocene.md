# Holocene Architecture

## Executive Summary

Holocene is a production-first, single-operator mission-control dashboard. Its live architecture combines a Next.js web container with an external Fastify host API that reads Hermes/systemd/runtime files, Redis hook health, Prometheus, Traefik state, and Candystore history. It is an operational prototype with broad host authority, not an enterprise multi-user control plane.

## Technology Stack

| Category | Technology | Version/evidence |
|---|---|---|
| Workspace | pnpm/Turbo | pnpm 10.0.0, Turbo 2.x |
| Web | Next.js / React | 15.0.0 / 18.3.1 |
| API | Fastify / TypeScript | Fastify 5.1, TS 5.6 |
| Runtime | Node | Compose 22, CI 20, live API 26.5 |
| Projections | Redis, host files, systemd, Prometheus, Traefik, Candystore HTTP | External dependencies |

## Architecture Pattern

Split-deployment control plane with stateless snapshot projections and client polling/SSE. The web is containerized; the API runs with host-user authority through systemd. Generic module packages model a future event-reducer architecture but are mostly dormant in the live path.

## Runtime Components

- Fleet projection: Hermes registry/runtime/systemd state plus Candystore history.
- Tooling projection: local hook configuration and Redis health snapshots.
- Systems projection: bgls inventory/actions and Prometheus history.
- Containers projection: Traefik Deathwatch targets.
- Clock: n8n webhook proxy plus local UI state.
- HQ: Telegram Mini App org tree derived from org config, registry, and fleet state.

## State Management

Holocene owns no durable database. The API recomputes snapshots and SSE clients trigger repeated reads. Browser state is local React state/polling, with clock state also using `localStorage`. See [Holocene Data Models](./data-models-holocene.md).

## API Design

The Fastify API exposes health, clock mutation, fleet snapshot/stream/control, org, system inventory/history/preview/actions, container state, and tooling endpoints. It binds `0.0.0.0:4000`, uses wildcard CORS, and has no application auth/authz. See [Holocene API Contracts](./api-contracts-holocene.md).

## Integration Architecture

The live Bloodbank client is a stub. Fleet history comes from Candystore HTTP, but the default URL is wrong and failures become empty arrays. Hook health comes through Redis. PJangler integration is through shared `.project.json`/Hermes projections and older generated agent scaffolding.

## Deployment Architecture

Next.js runs in `holocene-web`; the Fastify API is an external, untracked user service with hard-coded host paths. Browser routes may be protected by Traefik/OIDC, but the direct API listener is separate. `/hq` uses Telegram validation and has its own auth behavior.

## Testing Strategy

There are no application tests. Package tests and lint commands are no-op stubs; CI calls nonexistent scripts. Typecheck/build commands are the only substantive local quality gates until tests exist.

## Principal Risks

Unauthenticated host-control API, tracked n8n credential, silent history outage, expensive per-client SSE snapshots, inconsistent Node versions, missing test coverage, misleading “ticket velocity” labeling, and legacy generated PJangler/BMAD contracts.

## Development Workflow

Use [Holocene Development Guide](./development-guide-holocene.md) and [UI Component Inventory](./component-inventory-holocene.md). Changes to controls or network exposure require explicit security review.

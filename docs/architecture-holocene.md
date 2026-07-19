# Holocene Architecture

## Executive Summary

Holocene is a production-first, single-operator mission-control dashboard. Its live architecture combines a Next.js web container with an external Fastify host API that reads Hermes/systemd/runtime files, Redis hook health, Prometheus, Traefik state, and Candystore history. It is an operational prototype with broad host authority, not an enterprise multi-user control plane. For project lifecycle it is only a renderer and high-level command surface; it never calculates or writes lifecycle truth.

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

Fleet history, hook health, and PJangler integration retain their existing
boundaries. The implemented Lifecycle surface is separate: it reads
Candystore's authoritative projection, preserves identity, spec/state versions,
provenance, observation freshness, frontier, obligations, blockers, gates, and
stable verdicts, and publishes high-level commands through Bloodbank. Missing
or stale projections render unknown/degraded. It never writes provider,
Candystore, or Lifecycle state directly.

The Lifecycle page exposes stable semantic identity for the current state,
source causality, selected actor, capability grant, legal frontier, action
control, success/error receipt, and command verdict. Holocene's reusable
Playwright proof drives that real page: it validates and accepts the
identity-bearing confirmation, clicks the enabled control, records the actual
browser POST and HTTP 202 response, and waits for the later authoritative
state/version/causality/verdict to render. The 202 receipt is explicitly broker
processing only, never Lifecycle acceptance.

## Deployment Architecture

Next.js runs in `holocene-web`; the Fastify API is an external, untracked user service with hard-coded host paths. Browser routes may be protected by Traefik/OIDC, but the direct API listener is separate. `/hq` uses Telegram validation and has its own auth behavior.

## Testing Strategy

The Lifecycle client, command builder, API routes, proof-contract helpers, and
actionable/disabled/success/error UI states have focused tests. The reusable
browser script is additionally constrained by root anti-synthetic gates.
Typecheck and production build remain the broad workspace gates. Legacy
host-control modules still have uneven test coverage.

## Principal Risks

Unauthenticated host-control API, tracked n8n credential, silent legacy fleet
history outage, expensive per-client SSE snapshots, inconsistent Node versions,
misleading “ticket velocity” labeling, and legacy generated PJangler/BMAD
contracts. The Lifecycle surface avoids silent-empty state and optimistic
mutation but does not repair unrelated host-control risks.

## Development Workflow

Use [Holocene Development Guide](./development-guide-holocene.md) and [UI Component Inventory](./component-inventory-holocene.md). Changes to controls or network exposure require explicit security review.

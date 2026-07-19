# 33GOD Project Overview

**Date:** 2026-07-19

**Type:** Four-part monorepo knowledge boundary

**Deployment maturity:** Integrated local stack live under root Compose

## Executive summary

33GOD is a private, local-first agentic development environment whose current
Lifecycle slice integrates Bloodbank, Lifecycle, Candystore, Momo, Holocene,
and PJangler's identity boundary.
They exchange CloudEvents over NATS/Dapr, persist an audit read model, expose a
local mission-control UI/API, and provision projects and agents.

Root owns the normalized Compose projection and semantic/live gates. Component
sources remain authoritative and are pinned by root gitlinks. Lifecycle owns
project-lifecycle spec/state/reconcile/frontier/obligations/grants and all
writes; root owns only the service topology.

## Component and runtime model

| Part | Purpose | Candidate boundary |
|---|---|---|
| Bloodbank | Event names, schemas, NATS streams, Dapr transport | Default NATS JetStream, one-shot stream init, Dapr placement |
| Lifecycle | Deterministic project lifecycle authority | Dedicated PostgreSQL, one-shot migrate/bootstrap, exact-digest serve |
| Candystore | Durable event history, query/session APIs, audit UI | Exactly one default PostgreSQL/app/daprd deployment |
| Holocene | Fleet observation and privileged host control | Default web plus preflight; API remains `holocene-api.service` on host port 4000 |
| PJangler | Registry, parity, recipes, templates, CLI/MCP | Zero-replica CLI and stdio MCP definitions for explicit `run` in `tools`/`full` |

The target uses loopback, caller-overridable published ports, four external
Docker networks, and six volume identities. It excludes Bloodbank's legacy
Candystore profile, so the canonical `candystore-events` durable consumer cannot
be duplicated by the projection.

## Profile truth

- No profile: the local Bloodbank/Lifecycle/Candystore/Holocene-web target.
- `tools`: default plus run-only PJangler CLI and MCP definitions.
- `full`: currently the same governed model as `tools`.
- `cloud`: a render-only unsupported local-bind model with an explicit rejection
  service. It is not a hosted deployment profile and must never be started.

## Architecture highlights

- Bloodbank-local schemas and naming rules own event identity.
- Candystore is the durable read model; Holocene reads it over the host API's
  loopback boundary.
- Lifecycle is the only project-lifecycle writer. Bloodbank transports its
  contracts, Candystore is append-only audit/projection only, Momo chooses and
  executes legal work while publishing retry-stable evidence, and Holocene only
  renders and invokes high-level actions.
- Holocene web and API remain separate trust zones. Compose preflights the host
  API but does not claim or containerize its system authority.
- PJangler is operational tooling, not an HTTP service. MCP uses stdio.
- Direct Redis/host integrations remain documented exceptions to the event
  backbone.
- Root docs and validator govern relationships; component docs govern internals.

## Demonstrated guarantees

- Default, `tools`, `full`, and `cloud` render as Compose JSON.
- The semantic validator enforces exact service sets, one Candystore triplet,
  Lifecycle's immutable image/no-build/storage/ordering boundary, start
  dependencies, caller-selected ports, host boundaries, source mounts, four
  external networks, and six external volumes.
- Focused tests prove a known-invalid legacy model is rejected and a missing
  source root fails clearly.
- The documentation drift gate executes that validator against the caller's
  explicit source root while retaining the previous parity checks.

The isolated live gate additionally proves Lifecycle persistence and
offline/restart/outage behavior plus the Candystore, Momo, and Holocene seams.

Runtime acceptance additionally verifies health, volume attachment,
durable-consumer cardinality, and route behavior against the live root stack.

## Open product risks

Cloud use remains blocked by local bind mounts, external local networks,
host-systemd authority, unauthenticated/broad listeners, local-development
credentials, single-host storage, and missing backup/restore acceptance.
Candystore poison-message durability, Holocene API authorization, and PJangler
reproducibility/safe-default risks remain tracked in
[Drift Governance](./drift-governance.md).

## Documentation map

- [Documentation Index](./index.md)
- [Integration Architecture](./integration-architecture.md)
- [Deployment Guide](./deployment-guide.md)
- [Drift Governance](./drift-governance.md)
- [Validation Report](./validation-report.md)

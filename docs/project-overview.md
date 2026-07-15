# 33GOD Project Overview

**Date:** 2026-07-15

**Type:** Four-part monorepo knowledge boundary

**Deployment maturity:** Validated integrated local target; live cutover pending

## Executive summary

33GOD is a private, local-first agentic development environment made from four
independently owned components: Bloodbank, Candystore, Holocene, and PJangler.
They exchange CloudEvents over NATS/Dapr, persist an audit read model, expose a
local mission-control UI/API, and provision projects and agents.

Implementation HEAD `c4f78bb` turns the former root readiness scaffold into a
normalized Compose target. The root owns this projection and its semantic
validator; component sources remain authoritative and were not modified. The
candidate has been rendered and validated, but existing component Compose
projects and the host Holocene API have not been replaced.

## Component and runtime model

| Part | Purpose | Candidate boundary |
|---|---|---|
| Bloodbank | Event names, schemas, NATS streams, Dapr transport | Default NATS JetStream, one-shot stream init, Dapr placement |
| Candystore | Durable event history, query/session APIs, audit UI | Exactly one default PostgreSQL/app/daprd deployment |
| Holocene | Fleet observation and privileged host control | Default web plus preflight; API remains `holocene-api.service` on host port 4000 |
| PJangler | Registry, parity, recipes, templates, CLI/MCP | Zero-replica CLI and stdio MCP definitions for explicit `run` in `tools`/`full` |

The target preserves the existing port contract, three external Docker
networks, and five adopted volume identities. It excludes Bloodbank's legacy
Candystore profile, so the canonical `candystore-events` durable consumer cannot
be duplicated by the projection.

## Profile truth

- No profile: the local Bloodbank/Candystore/Holocene-web target.
- `tools`: default plus run-only PJangler CLI and MCP definitions.
- `full`: currently the same governed model as `tools`.
- `cloud`: a render-only unsupported local-bind model with an explicit rejection
  service. It is not a hosted deployment profile and must never be started.

## Architecture highlights

- Bloodbank-local schemas and naming rules own event identity.
- Candystore is the durable read model; Holocene reads it over the host API's
  loopback boundary.
- Holocene web and API remain separate trust zones. Compose preflights the host
  API but does not claim or containerize its system authority.
- PJangler is operational tooling, not an HTTP service. MCP uses stdio.
- Direct Redis/host integrations remain documented exceptions to the event
  backbone.
- Root docs and validator govern relationships; component docs govern internals.

## Demonstrated guarantees

- Default, `tools`, `full`, and `cloud` render as Compose JSON.
- The semantic validator enforces exact service sets, one Candystore triplet,
  start dependencies, fixed ports, host boundaries, source mounts, three
  external networks, and five external volumes.
- Focused tests prove a known-invalid legacy model is rejected and a missing
  source root fails clearly.
- The documentation drift gate executes that validator against the caller's
  explicit source root while retaining the previous parity checks.

These are static guarantees. Runtime health, volume contents, durable-consumer
cardinality, route behavior, and rollback readiness still require the cutover
acceptance procedure.

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

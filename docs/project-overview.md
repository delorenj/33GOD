# 33GOD Project Overview

**Date:** 2026-08-26

**Type:** Multi-component platform knowledge boundary

**Deployment maturity:** Integrated local stack live under root Compose

## Executive summary

33GOD is a private, local-first agentic development environment. Bloodbank,
Candystore, and Holocene form the live event/audit/operator core; PJangler,
Hermes Fleet, Momo, Krebs, Skillex, and Hindsight add provisioning, execution,
lifecycle, capability, and memory boundaries. Plane and n8n provide the current
external ticket-fact ingress.

Implementation base `c4f78bb` turns the former root readiness scaffold into a
normalized Compose target. The root owns this projection, its semantic
validator, and the live Bloodbank/Candystore/Holocene-web lifecycle. Component
sources remain authoritative and are pinned by root gitlinks. The Holocene API
remains an active host service by design.

## Core component and runtime model

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

## Orchestration and integration roles

| Boundary | Role in the pipeline |
|---|---|
| Plane + n8n | Ticket authority plus one raw-body HMAC provenance adapter into Bloodbank |
| Hermes Fleet + gateway | Registry-gated durable command consumption and agent dispatch |
| Momo | PM/EM decisions and command production without duplicating provider facts |
| Krebs | Canonical ticket-lifecycle machine and provider-normalized transitions |
| Skillex | Single-source skill registry and distribution topology |
| Hindsight | Project/session recall and retention, never event or ticket authority |

## Profile truth

- No profile: the local Bloodbank/Candystore/Holocene-web target.
- `tools`: default plus run-only PJangler CLI and MCP definitions.
- `full`: currently the same governed model as `tools`.
- `cloud`: a render-only unsupported local-bind model with an explicit rejection
  service. It is not a hosted deployment profile and must never be started.

## Architecture highlights

- Bloodbank-local schemas and naming rules own event identity.
- Events carry facts; commands carry intent. Hermes lifecycle events provide
  the correlated durable completion/rejection evidence.
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
- [Event and Command Journey](./event-journey.md)
- [Skill Event-Journey Audit](./skill-event-journey-audit.md)
- [Deployment Guide](./deployment-guide.md)
- [Drift Governance](./drift-governance.md)
- [Validation Report](./validation-report.md)

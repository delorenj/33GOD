# 33GOD Documentation Index

**Type:** Multi-component platform knowledge boundary

**Architecture:** Event-driven local-first platform with a live integrated core

**Last updated:** 2026-08-26

## Current state

33GOD combines a root-managed Bloodbank/Candystore/Holocene core with PJangler,
Hermes Fleet, Momo, Krebs, Skillex, Hindsight, and provider/integration
boundaries including Plane and n8n. Component implementation remains in the
owning repository; root documentation governs the journey between them.

The normalized core is live under Compose project `33god-platform`; privileged
Holocene and Hermes gateway processes remain host services by design. The
hosted/cloud model is still render-only and unsupported.

Default services are Bloodbank NATS/init/placement, exactly one standalone
Candystore PostgreSQL/app/Dapr sidecar, a Holocene host-API preflight, and
Holocene web. PJangler appears only as zero-replica, run-only CLI and stdio MCP
definitions under `tools`/`full`. `cloud` is render-only and unsupported.

## Authority and scope

Live manifests, code, and tests outrank prose. Root documentation governs
cross-component relationships, the normalized projection, and deployment
gates; component repositories govern their internals. Contradictions are
recorded in [Drift Governance](./drift-governance.md).

| Core part | Role | Root | Runtime boundary in the target |
|---|---|---|---|
| Bloodbank | Event contracts and transport | `bloodbank/` | Default NATS, initializer, placement |
| Candystore | Durable history and read API | `candystore/` | Exactly one default PostgreSQL/app/daprd |
| Holocene | Mission control and host control | `holocene/` | Default web; API stays host systemd |
| PJangler | Provisioning control plane | `pjangler/` | Explicit run-only CLI and stdio MCP |

## Core documentation

- [Project Overview](./project-overview.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Integration Architecture](./integration-architecture.md)
- [Event and Command Journey](./event-journey.md)
- [Skill Event-Journey Audit](./skill-event-journey-audit.md)
- [Editable Excalidraw Architecture and Message Traces](./diagrams/33god-event-pipeline.excalidraw)
- [Deployment Guide](./deployment-guide.md)
- [Drift Governance](./drift-governance.md)
- [Validation Report](./validation-report.md)
- [Project Parts Metadata](./project-parts.json)
- [Project Scan Report](./project-scan-report.json)
- [Integrated Compose Topology Audit](../33god-platform/docs/integrated-compose-topology-audit.md)

## Part documentation

| Part | Architecture | Development | Contracts | Data/inventory |
|---|---|---|---|---|
| Bloodbank | [Architecture](./architecture-bloodbank.md) | [Development](./development-guide-bloodbank.md) | [Protocols](./api-contracts-bloodbank.md) | [Data](./data-models-bloodbank.md), [inventory](./component-inventory-bloodbank.md) |
| Candystore | [Architecture](./architecture-candystore.md) | [Development](./development-guide-candystore.md) | [HTTP](./api-contracts-candystore.md) | [Data](./data-models-candystore.md), [inventory](./component-inventory-candystore.md) |
| Holocene | [Architecture](./architecture-holocene.md) | [Development](./development-guide-holocene.md) | [HTTP](./api-contracts-holocene.md) | [Data](./data-models-holocene.md), [inventory](./component-inventory-holocene.md) |
| PJangler | [Architecture](./architecture-pjangler.md) | [Development](./development-guide-pjangler.md) | [CLI/MCP](./api-contracts-pjangler.md) | [Data](./data-models-pjangler.md), [inventory](./component-inventory-pjangler.md) |

## Verification entrypoint

From this checkout, validate against a populated source root without starting
services:

```bash
GOD_SOURCE_ROOT=/home/delorenj/code/33GOD mise run docs:drift
```

The gate retains all component/document checks and also renders and
semantically validates default, `tools`, `full`, and `cloud`. A green result
proves projection consistency, not current runtime health; live proof is
recorded separately in [Event and Command Journey](./event-journey.md).

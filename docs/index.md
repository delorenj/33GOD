# 33GOD Documentation Index

**Type:** Four-part current integration boundary plus one approved planned component

**Architecture:** Event-driven local-first platform with a validated integrated Compose target

**Last updated:** 2026-07-15

## Current state

33GOD combines Bloodbank, Candystore, Holocene, and PJangler. The root-owned
`33god-platform/compose.yaml` is now a statically validated normalized
projection of their local topology. It is a target, not proof of a live
cutover: existing component projects and the host `holocene-api.service` remain
untouched.

Default services are Bloodbank NATS/init/placement, exactly one standalone
Candystore PostgreSQL/app/Dapr sidecar, a Holocene host-API preflight, and
Holocene web. PJangler appears only as zero-replica, run-only CLI and stdio MCP
definitions under `tools`/`full`. `cloud` is render-only and unsupported.

The approved target adds a separate headless `lifecycle` component. It is the
sole owner of lifecycle spec/state/reconciliation, legal frontier, obligations,
and capability validation. It has no standalone repository, gitlink, service,
or Compose entry in this snapshot. The tested
`bloodbank/services/lifecycle-controller/` directory is the extraction embryo,
not proof that the target component is deployed.

## Authority and scope

Live manifests, code, and tests outrank prose. Root documentation governs
cross-component relationships, the normalized projection, and deployment
gates; component repositories govern their internals. Contradictions are
recorded in [Drift Governance](./drift-governance.md).

| Part | Role | Root | Runtime boundary in the target |
|---|---|---|---|
| Bloodbank | Event contracts and transport | `bloodbank/` | Default NATS, initializer, placement |
| Candystore | Durable history and read API | `candystore/` | Exactly one default PostgreSQL/app/daprd |
| Holocene | Mission control and host control | `holocene/` | Default web; API stays host systemd |
| PJangler | Provisioning control plane | `pjangler/` | Explicit run-only CLI and stdio MCP |
| Lifecycle (planned) | Deterministic project lifecycle authority | No root/gitlink yet | Extract controller embryo; deploy exactly one service only after migration gates |

## Core documentation

- [Project Overview](./project-overview.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Integration Architecture](./integration-architecture.md)
- [Deployment Guide](./deployment-guide.md)
- [Drift Governance](./drift-governance.md)
- [Validation Report](./validation-report.md)
- [Project Parts Metadata](./project-parts.json)
- [Project Scan Report](./project-scan-report.json)
- [Integrated Compose Topology Audit](../33god-platform/docs/integrated-compose-topology-audit.md)
- [Planned Lifecycle Architecture](./architecture-lifecycle.md)

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
proves candidate consistency, not runtime health or cutover completion.
It still validates the current four checked-out component roots; it does not
prove the planned lifecycle repository, migration, service, or client wiring.

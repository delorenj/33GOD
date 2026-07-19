# 33GOD Documentation Index

**Architecture:** Event-driven, local-first platform with an implemented
Lifecycle authority vertical slice

**Last updated:** 2026-07-19

## Current state

The root-owned `33god-platform/compose.yaml` normalizes Bloodbank,
Lifecycle, Candystore, Holocene, and run-only PJangler tooling. The Lifecycle
path is implemented and locally verified with:

- immutable image
  `ghcr.io/delorenj/lifecycle@sha256:b216be4e1b796236309ee0b39120b0f353b62ee9f3c677901b2441a2c7aef210`;
- dedicated PostgreSQL, secret, volume, and private network;
- fail-closed migration, deterministic bootstrap, then serve ordering;
- canonical Bloodbank contracts and JetStream;
- durable Candystore Lifecycle projections;
- bounded Momo legal-work execution with retry-stable, artifact-backed
  completion publication and PubAck-before-ACK; and
- a Candystore-backed Holocene read/command surface.

The isolated acceptance gate proves the seven offline, restart, stale-version,
capability, broker-recovery, ordering, and persistence invariants plus
pending-obligation evidence, versioned grants, pre-start durable replay, and
canonical conflicting-duplicate integrity. The cloud profile remains
render-only and unsupported.

## Ownership

| Component | Sole concern in this slice |
|---|---|
| PJangler | Project/bootstrap identity and binding inputs |
| Lifecycle | Specification, operational state, reconcile, legal work, grants, and writes |
| Bloodbank | Canonical schemas and NATS/Dapr transport |
| Candystore | Append-only history and read projections |
| Momo | Business ranking/delegation, legal-work execution, and evidence; never lifecycle truth |
| Holocene | Rendering and high-level action invocation only |
| Root platform | Process topology, pins, profiles, validation, and release gates |

Live manifests, code, and tests outrank prose. Root documentation governs
cross-component relationships; component repositories govern their internals.

## Core documentation

- [Project Overview](./project-overview.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Integration Architecture](./integration-architecture.md)
- [Lifecycle Architecture](./architecture-lifecycle.md)
- [Deployment Guide](./deployment-guide.md)
- [Drift Governance](./drift-governance.md)
- [Validation Report](./validation-report.md)
- [Project Parts Metadata](./project-parts.json)
- [Project Scan Report](./project-scan-report.json)
- [Integrated Compose Topology Audit](../33god-platform/docs/integrated-compose-topology-audit.md)

## Component documentation

| Part | Architecture | Development | Contracts | Data/inventory |
|---|---|---|---|---|
| Bloodbank | [Architecture](./architecture-bloodbank.md) | [Development](./development-guide-bloodbank.md) | [Protocols](./api-contracts-bloodbank.md) | [Data](./data-models-bloodbank.md), [inventory](./component-inventory-bloodbank.md) |
| Candystore | [Architecture](./architecture-candystore.md) | [Development](./development-guide-candystore.md) | [HTTP](./api-contracts-candystore.md) | [Data](./data-models-candystore.md), [inventory](./component-inventory-candystore.md) |
| Holocene | [Architecture](./architecture-holocene.md) | [Development](./development-guide-holocene.md) | [HTTP](./api-contracts-holocene.md) | [Data](./data-models-holocene.md), [inventory](./component-inventory-holocene.md) |
| PJangler | [Architecture](./architecture-pjangler.md) | [Development](./development-guide-pjangler.md) | [CLI/MCP](./api-contracts-pjangler.md) | [Data](./data-models-pjangler.md), [inventory](./component-inventory-pjangler.md) |

## Verification entrypoints

```bash
GOD_SOURCE_ROOT="$PWD" mise run docs:drift
proof_dir="$(mktemp -d /tmp/33god-lifecycle-proof-XXXXXXXX)"
python3 33god-platform/scripts/verify-lifecycle-live.py \
  --proof-dir "$proof_dir" \
  --screenshots-dir "$proof_dir/screenshots"
```

The first command is static/read-only. The second creates an isolated,
uniquely named Docker project and cleans only its own resources.

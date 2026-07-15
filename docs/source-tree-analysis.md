# 33GOD Source Tree Analysis

**Date:** 2026-07-15

## Overview

The root is a coordination workspace for four independently versioned component
repositories. Root files own cross-component governance and a normalized
deployment projection. The component repositories remain the implementation
sources and are not generated from the root projection.

```text
33GOD/
├── _bmad/                              # Root BMAD configuration
├── docs/                               # Cross-component knowledge and validation record
├── scripts/
│   └── check-doc-drift.py              # Parity gate plus candidate validator invocation
├── 33god-platform/
│   ├── components.yaml                 # Product/profile/projection policy
│   ├── components/{bloodbank,candystore,holocene,pjangler}.yaml
│   │                                   # Component ownership and projection declarations
│   ├── compose.yaml                    # Root-owned normalized candidate
│   ├── scripts/validate-compose.py     # Four-model semantic validator
│   ├── scripts/pjangler-tool-entrypoint.sh
│   │                                   # Run-only CLI/MCP selector
│   ├── tests/                          # Positive and adversarial validator tests
│   ├── changes/*.jsonl                 # Machine-readable platform changes
│   └── docs/integrated-compose-topology-audit.md
│                                       # Evidence, decision, implemented outcome
├── bloodbank/                          # Event contracts, NATS/Dapr source
├── candystore/                         # PostgreSQL event history, app/UI, Dapr component
├── holocene/                           # Next.js web and host Fastify API source
└── pjangler/                           # Node CLI, stdio MCP, registry/templates
```

## Projection boundaries

| Root artifact | Reads from component source | Does not own |
|---|---|---|
| `compose.yaml` | Bloodbank stream init, Candystore build/Dapr components, Holocene source/env, PJangler dist/source | Component implementation or runtime state |
| `validate-compose.py` | Required paths beneath explicit `--source-root` | Component correctness beyond the projected contract |
| `check-doc-drift.py` | Component BMAD/config/contracts and root candidate validator | Lifecycle state or destructive remediation |
| Component manifests | Native Compose/source paths and root projection metadata | Component-local release decisions |

`GOD_SOURCE_ROOT` separates the candidate checkout from the populated source
checkout. It defaults to `.` in root mise tasks and to `..` inside Compose, but
must be set explicitly when this worktree validates against
`/home/delorenj/code/33GOD`.

## Runtime entrypoints

| Part | Entrypoint | Candidate behavior |
|---|---|---|
| Bloodbank | NATS image plus tracked `compose/nats/init.sh` | Default service/one-shot/placement trio |
| Candystore | `python -m candystore.main` plus daprd | Default standalone triplet; app migrates on startup |
| Holocene | Next.js `start`; API `apps/api/dist/server.js` | Web in candidate, API in existing user systemd |
| PJangler | `dist/index.js`, `dist/mcp-server.js` | Explicit `run` only; read-only source mount, ephemeral dependencies |

## Configuration boundaries

- Root `_bmad` files use root-relative tokens.
- Component env files, 1Password references, host systemd configuration,
  registries, and provider credentials remain outside root ownership.
- Three networks and five adopted volumes are declared external so Compose
  cannot silently create replacement identities.
- Detached Bloodbank legacy PostgreSQL volumes are intentionally absent from
  the candidate and must not be removed during migration.

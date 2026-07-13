# 33GOD Source Tree Analysis

**Date:** 2026-07-13

## Overview

The root checkout is a coordination workspace containing independently versioned component repositories. This analysis intentionally documents exactly four product parts and the root coordination layer. Other sibling projects may appear in platform manifests, but are outside this scan boundary.

## Annotated Structure

```text
33GOD/
├── _bmad/                         # Root BMAD configuration for this knowledge base
├── _bmad-output/                  # Root planning/implementation artifact target
├── docs/                          # Root cross-component knowledge and scan state
├── scripts/
│   └── check-doc-drift.py         # Read-only contract/document parity check
├── 33god-platform/                # Component registry, change policy, backfills, compose scaffold
│   ├── components.yaml            # Platform inventory; broader than this four-part scan
│   ├── components/*.yaml          # Per-component repo/health/source declarations
│   ├── changes/*.jsonl            # Machine-readable cross-component changes
│   ├── backfills/*.yaml           # Read-only drift definitions
│   ├── scripts/platform.py        # Registry validation/list/backfill CLI
│   └── compose.yaml               # Tools-only validation scaffold
├── bloodbank/                     # Part: Bloodbank
│   ├── schemas/                   # Canonical JSON Schema contracts
│   ├── docs/event-naming.md        # Locked type/subject naming contract
│   ├── compose/                   # NATS, Dapr, registry, catalog, reference services
│   ├── services/agent-hooks/      # Canonical hook envelope builder and publisher
│   ├── services/lifecycle-controller/ # Tested but undeployed lifecycle worker
│   ├── cli/bb.py                  # Operator CLI
│   └── ops/                       # Smoke, trace, replay, health workflows
├── candystore/                    # Part: Candystore
│   ├── candystore/                # HTTP, ingestion, persistence, queries, summaries
│   ├── migrations/               # PostgreSQL event/dead-letter schema
│   ├── dapr-components/           # JetStream subscription definition
│   ├── web/                       # React/Vite source
│   ├── static/                    # Prebuilt UI copied into image
│   ├── tests/                     # Python and migration checks
│   └── compose.yml                # Canonical standalone audit deployment
├── holocene/                      # Part: Holocene
│   ├── apps/api/                  # Fastify host-control and projection API
│   ├── apps/web/                  # Next.js mission-control UI and HQ routes
│   ├── packages/                  # Org model and mostly dormant module abstractions
│   ├── docs/                      # Current design/spec and historical plan material
│   └── compose.yml                # Web-only production container
└── pjangler/                      # Part: PJangler
    ├── src/index.ts               # Commander CLI
    ├── src/mcp-server.ts          # stdio MCP server
    ├── src/project/               # Registry/projection/bootstrap planning
    ├── src/parity/                # Audit and migration rules
    ├── src/recipes/               # Mise, Docker, Node, Hermes, hook recipes
    ├── templates/commonproject/   # CommonProject Copier template gitlink
    ├── templates/hermes-agent/    # Hermes agent template gitlink
    └── tests/                     # Filesystem-mutating Node regression scripts
```

## Entry Points

| Part | Runtime or operator entrypoint | Bootstrap behavior |
|---|---|---|
| Bloodbank | `services/agent-hooks/publish.py`, `cli/bb.py`, component Compose | NATS stream initialization plus optional profile services |
| Candystore | `python -m candystore.main` | Applies all SQL migrations, then binds HTTP; Dapr discovers subscriptions |
| Holocene | `apps/api/dist/server.js`, Next.js `next start` | API runs through external user systemd; web runs in Compose |
| PJangler | `dist/index.js`, `dist/mcp-server.js` | Host-user CLI/MCP; recipes and templates may mutate repos and user profile |

## File Organization Patterns

- Bloodbank is contract-first: schemas and naming rules sit beside multiple reference/runtime implementations.
- Candystore is a compact vertical slice: HTTP routing, ingestion, database, queries, summaries, and a separately built UI.
- Holocene is a pnpm workspace; live behavior resides mainly in `apps/*`, while several packages model a future modular event architecture.
- PJangler is host automation: typed plans, parity rules, recipes, and executable Copier templates.

## Configuration Boundaries

- Root `_bmad` files use `{project-root}` tokens and must not inherit malformed component substitutions.
- `33god-platform/components.yaml` is the broader product registry; `docs/project-parts.json` is the exact scan declaration.
- Component `.env`, systemd, user registries, runtime directories, and external Docker networks are operational dependencies, not source-controlled root configuration.

## Exclusions

The exhaustive evidence packets excluded Git metadata, dependency/vendor trees, build output, caches, runtime databases, generated framework packages, and large generated frontend artifacts unless needed to establish deployment behavior. Those exclusions prevent generated state from being mistaken for maintained architecture.

---

_Generated using the BMAD Method `document-project` workflow._

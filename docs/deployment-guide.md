# 33GOD Deployment Guide

## Current Deployment Truth

There is no integrated four-component Docker Compose stack. `33god-platform/compose.yaml` is a read-only tools scaffold that prints validation guidance. Do not present `docker compose up` at the root as a product deployment.

## Runtime Topology

| Part | Current runtime | External dependencies | Material caveat |
|---|---|---|---|
| Bloodbank | Component Compose with default and optional profiles | Docker, external ports, local volumes | Heartbeat profile references a missing build context; NATS is unauthenticated |
| Candystore | Standalone Compose | Existing `bloodbank-network` and `proxy`; Bloodbank NATS/placement | Never run with Bloodbank’s legacy Candystore profile |
| Holocene | Web in Compose; API in external user systemd | Host systemd, Hermes registry, Redis, bgls, Traefik, Candystore | API is not application-authenticated and binds `0.0.0.0:4000` |
| PJangler | Host CLI and stdio MCP | Node/npm, Copier, optional external providers/systemd | No container boundary; templates execute trusted host code |

## Safe Preflight

From the repository root:

```bash
python3 33god-platform/scripts/platform.py validate
python3 33god-platform/scripts/platform.py components list
python3 33god-platform/scripts/platform.py backfills check
docker compose -f 33god-platform/compose.yaml --profile tools config
python3 scripts/check-doc-drift.py --source-root . --docs-root .
```

The drift check may report known live contradictions. A nonzero result means a missing required artifact or evidence-backed contract conflict, not that the checker itself failed.

## Bloodbank

Use Bloodbank’s component Compose and documented profiles. Default services establish NATS, stream initialization, Dapr placement, Apicurio, and EventCatalog. `mise run up` is narrower than the Compose default and starts only NATS plus stream initialization; read the component guide before selecting a command. Avoid the broken heartbeat profile until its missing recorder context is restored or removed.

Before relying on event durability, distinguish a successful core NATS `PUB`/PING from a JetStream publish acknowledgement. The current hook publisher proves connectivity, not persisted stream acknowledgement.

## Candystore

Bring up Bloodbank’s NATS/placement dependencies and required external Docker networks first. Then use `candystore/compose.yml`. The app exposes loopback `8683`, PostgreSQL loopback `5434`, and Dapr loopback `3504` by default. The app migrates the database at startup.

Never enable Bloodbank’s `candystore` profile at the same time. Both deployments share durable `candystore-events` and queue `candystore`, which distributes messages across two databases.

Backups, point-in-time recovery, retention, and operator replay are not implemented. Treat the single PostgreSQL volume as a development durability boundary, not an enterprise audit archive.

## Holocene

The web container and API service deploy separately. Build/typecheck the API, restart the external user service, and verify `127.0.0.1:4000/health`. Rebuild/recreate the web container separately. Configure `CANDYSTORE_API_URL=http://127.0.0.1:8683` for the host API unless the topology is deliberately changed.

Do not expose port 4000 beyond a trusted host boundary until application authentication/authorization exists. Traefik protection of browser routes does not protect direct listeners. Rotate and purge the tracked clock credential before treating the clock integration as safe.

## PJangler

PJangler runs as the host user. CLI, MCP, Copier `--trust`, recipes, user systemd operations, and external provider wiring are privileged actions. Use dry-run modes where available and inspect template sources. Current vendored template gitlinks are dirty and Hermes uses `HEAD`, so provisioning is not reproducible from the parent PJangler commit alone.

## Release Gate

Before a compose-affecting or cross-component release:

1. Run component contract/config tests.
2. Run root platform validation and backfill checks.
3. Run the root drift checker with live sources and candidate docs.
4. Render Compose configuration without starting services.
5. Confirm mutual-exclusion rules and external networks.
6. Record known failures in `docs/drift-governance.md` and the platform change logs.
7. Obtain component-owner review for every changed contract.

Starting services is intentionally outside this documentation workflow.

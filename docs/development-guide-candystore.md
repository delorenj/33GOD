# Candystore Development Guide

## Prerequisites

- Python 3.11+
- PostgreSQL for DB-backed tests
- Node/npm for the React UI
- Docker Compose for the standalone topology
- Existing `bloodbank-network` and `proxy` networks for Compose

## Canonical Commands

```bash
cd candystore
mise run install
mise run start
mise run test
mise run test:schema
mise run lint
mise run build:ui
mise run up
mise run logs
mise run down
```

Equivalent backend commands are `pip install -e '.[dev]'`, `python -m candystore.main`, `pytest tests/ -v`, and `ruff check candystore/ tests/`.

## Environment

Runtime variables include `APP_HOST`, `APP_PORT`, `DATABASE_URL`, `SUBSCRIBE_PUBSUB`, `SUBSCRIBE_TOPIC`, `SUBSCRIBE_ROUTE`, `SUBSCRIBE_MODE`, and `LOG_LEVEL`. Compose host ports use `CANDYSTORE_PORT`, `CANDYSTORE_POSTGRES_PORT`, and `CANDYSTORE_DAPR_HTTP_PORT`. UI builds use `VITE_API_URL`.

Entering through mise can link agent files and run `op inject`, which changes local state and requires 1Password. Prefer explicit commands for read-only work.

## Backend Workflow

The server applies every lexically sorted migration on startup in one transaction. Migrations must remain idempotent until a ledger/checksum system exists. Validate both a fresh schema and an upgrade path when adding migrations.

## Frontend Workflow

Run `mise run build:ui` before building the container. The Dockerfile copies `static/`; it does not build `web/src`, so stale static output is otherwise deployable.

## Test Interpretation

DB-backed pytest cases skip without a configured/reachable database. Confirm the summary rather than treating process exit alone as full coverage. The current gaps include dead-letter write failure, full Bloodbank schema enforcement, replay, stable pagination/concurrency, migration upgrades, backup/restore, Dapr/NATS integration, and frontend tests.

## Deployment Cautions

Run only standalone Candystore or Bloodbank’s legacy profile, never both. Use `/readyz` for database readiness even though the current Docker healthcheck uses `/healthz`. The API is unauthenticated and should remain loopback or behind a verified authenticating proxy.

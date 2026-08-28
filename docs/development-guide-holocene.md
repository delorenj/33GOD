# Holocene Development Guide

## Prerequisites

- pnpm 10.0.0 through Corepack
- Node compatible with the workspace; reconcile Node 20/22/26 before release claims
- Docker Compose for the web
- User systemd for the live API
- External Hermes, Redis, Prometheus, Traefik, srvls, n8n, Telegram, and Candystore dependencies as features require

## Workspace Commands

```bash
cd holocene
pnpm install --frozen-lockfile
pnpm dev
pnpm build
pnpm typecheck
```

`pnpm lint` and `pnpm test` currently exercise no-op package scripts, not substantive lint/tests. CI also calls nonexistent scripts and is not a reliable gate.

## API Workflow

```bash
pnpm --filter @holocene/api typecheck
pnpm --filter @holocene/api build
systemctl --user restart holocene-api.service
curl -fsS http://127.0.0.1:4000/health
```

The restart mutates live state and requires explicit authorization. The tracked repository does not contain the active systemd unit.

## Web Workflow

```bash
pnpm --filter @holocene/web typecheck
docker compose up -d --force-recreate holocene-web
docker compose ps holocene-web
docker logs --tail 100 holocene-web
```

The production container bind-mounts source and rebuilds on start, which updates generated state in the checkout.

## Required Local Configuration

For the current host API plus standalone Candystore topology, set `CANDYSTORE_API_URL=http://127.0.0.1:8683`. Do not rely on the default `http://candystore:8080`. Confirm Redis, Hermes registry, systemd bus, Prometheus, and Traefik paths for the host.

## Security Gate

Do not expose the API listener to untrusted networks. Any change to fleet/service actions, terminal launch, preview roots, clock mutation, or wildcard CORS requires auth/authz and threat review. Rotate the tracked n8n credential and remove it from reachable history.

## Testing Priorities

Add API authorization tests, action allowlist tests, path-containment tests, Candystore outage visibility, hook parser fixtures, Telegram replay/future-date cases, UI mutation-error behavior, and SSE load behavior before calling the system production-grade.

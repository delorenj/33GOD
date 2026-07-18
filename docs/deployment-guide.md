# 33GOD Deployment Guide

## Current deployment truth

`33god-platform/compose.yaml` is the normalized local process topology for
Bloodbank, Lifecycle, Candystore, and Holocene web. Process ownership does not
grant Lifecycle semantic ownership to root. Lifecycle remains the only
project-lifecycle writer.

The exact Lifecycle runtime is:

`ghcr.io/delorenj/lifecycle@sha256:20a6d4e7c37ceee9867e05e922d46f3fa682ccf597dff4bb733e3f5649850a76`

Compose has no Lifecycle build key. The cloud profile is render-only and
unsupported; never run `docker compose --profile cloud up`.

## Static gates

From the root checkout:

```bash
export GOD_SOURCE_ROOT="$PWD"
mise run platform:validate
mise run platform:components
mise run platform:backfills:check
mise run platform:compose:validate
mise run platform:compose:test
mise run docs:drift
```

These commands render with `--no-env-resolution` and do not start services or
print secret values.

## Default dependency order

1. Dedicated Lifecycle PostgreSQL becomes healthy.
2. `lifecycle-migrate` completes successfully.
3. Deterministic `lifecycle-bootstrap` completes successfully.
4. Bloodbank NATS becomes healthy and `nats-init` initializes canonical
   JetStream streams.
5. Lifecycle serve starts and its `/readyz` gate verifies PostgreSQL and
   Bloodbank connectivity.
6. Candystore PostgreSQL/app become healthy and the durable Dapr sidecar joins
   Bloodbank.
7. The host Holocene API preflight completes, then Holocene web starts.

A failed migration/bootstrap or unhealthy database/broker prevents Lifecycle
readiness.

## Ports

All Compose-published development ports bind to loopback and can be overridden:

| Environment key | Default | Owner |
|---|---:|---|
| `BLOODBANK_NATS_CLIENT_PORT` | 4222 | Bloodbank |
| `BLOODBANK_NATS_MONITOR_PORT` | 8222 | Bloodbank |
| `BLOODBANK_DAPR_PLACEMENT_PORT` | 50005 | Bloodbank/Dapr |
| `LIFECYCLE_PORT` | 8088 | Lifecycle |
| `CANDYSTORE_POSTGRES_PORT` | 5434 | Candystore |
| `CANDYSTORE_PORT` | 8683 | Candystore |
| `CANDYSTORE_DAPR_HTTP_PORT` | 3504 | Candystore/Dapr |

Holocene web is exposed to the `proxy` network on container port 3001. The
host `holocene-api.service` owns port 4000; Compose does not publish it.

## Networks, volumes, and secret

The default external names are:

- networks: `bloodbank-network`, `lifecycle-internal`,
  `candystore-internal`, and `proxy`;
- volumes: `bloodbank_bloodbank-nats-data`, `lifecycle_pgdata`,
  `candystore_pgdata`, and the three `holocene_*_node_modules/.next`
  volumes; and
- secret input: `LIFECYCLE_POSTGRES_PASSWORD_FILE`, pointing to a read-only file
  inside a caller-owned private directory; it must be readable by the non-root
  Lifecycle and PostgreSQL container users.

Lifecycle PostgreSQL joins only `lifecycle-internal`. Lifecycle serve joins
`lifecycle-internal` and `bloodbank-network`. It never mounts Candystore
storage or credentials.

All network and volume names are caller-overridable. This is required for
isolated acceptance and safe coexistence with unrelated projects.

## Isolated live acceptance

```bash
python3 33god-platform/scripts/verify-lifecycle-live.py \
  --screenshots-dir /tmp/33god-lifecycle-proof
```

Before `up`, the gate renders the model and rejects any Lifecycle digest
mismatch or build key. It allocates a unique Compose project, free ports,
networks, volumes, and local Candystore image. It then proves:

1. Holocene-offline independence.
2. Momo-offline safety.
3. deterministic restart catch-up without duplicate effects.
4. stale-version rejection without mutation.
5. capability rejection without mutation.
6. NATS outage/recovery with committed-state preservation, ordered outbox, and
   eventual publication.
7. dedicated PostgreSQL persistence across Lifecycle and database restarts.

The run starts Candystore after the baseline authority snapshot and verdict
already exist, verifies durable replay before post-start traffic, and proves a
conflicting duplicate cannot spoof the stored row or projection. It also
exercises pending-obligation rejection, Momo's exact completion-evidence path,
authoritative capability-version flow, and Holocene's read/command surface.
Cleanup uses the unique resource names and never prunes Docker.

## Promotion boundary

This implemented slice is locally verified. Production/cloud rollout, root
integration publication, and a release tag require a separate owner decision.
No cloud lifecycle command is supported by this guide.

# 33GOD Deployment Guide

## Current deployment truth

`33god-platform/compose.yaml` is the normalized local process topology for
Bloodbank, Lifecycle, Candystore, and Holocene web. Process ownership does not
grant Lifecycle semantic ownership to root. Lifecycle remains the only
project-lifecycle writer.

The exact Lifecycle runtime is:

`ghcr.io/delorenj/lifecycle@sha256:fc1775ac67f79e8e3289d8e424069519430d68e8473f4b936c6e5dcbbdd0cef5`

Compose has no Lifecycle build key. The cloud profile is render-only and
unsupported; never run `docker compose --profile cloud up`.

### Anonymous registry consumption

On 2026-07-18, the exact digest above passed an empty-credential Docker pull.
The gate created a unique `DOCKER_CONFIG` directory containing zero credential
files, ran `docker pull` by digest, confirmed the returned repository digest,
and removed only that temporary directory. The observed result was:

```bash
ghcr_anon_dir="$(mktemp -d /tmp/33god-ghcr-anon.XXXXXX)"
case "$ghcr_anon_dir" in /tmp/33god-ghcr-anon.*) ;; *) exit 1 ;; esac
trap 'find "$ghcr_anon_dir" -depth -delete' EXIT
test "$(find "$ghcr_anon_dir" -mindepth 1 -type f | wc -l)" -eq 0
DOCKER_CONFIG="$ghcr_anon_dir" docker pull \
  ghcr.io/delorenj/lifecycle@sha256:fc1775ac67f79e8e3289d8e424069519430d68e8473f4b936c6e5dcbbdd0cef5
test "$(find "$ghcr_anon_dir" -mindepth 1 -type f | wc -l)" -eq 0
```

```text
Digest: sha256:fc1775ac67f79e8e3289d8e424069519430d68e8473f4b936c6e5dcbbdd0cef5
Status: Downloaded newer image for ghcr.io/delorenj/lifecycle@sha256:fc1775ac67f79e8e3289d8e424069519430d68e8473f4b936c6e5dcbbdd0cef5
credential_files_before=0
credential_files_after=0
temporary_docker_config_removed=yes
```

A bare manifest request returning HTTP 401 is the registry's normal Bearer
authentication challenge; by itself, it is not evidence that anonymous image
consumption is unavailable. The authoritative consumption gate is the
successful digest-pinned `docker pull` with an empty credential directory.

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
6. a canonical authority transaction during NATS outage, committed state and
   exact ordered pending outbox rows, followed by exact-ID publication and
   drain after recovery without a duplicate transition effect.
7. dedicated PostgreSQL persistence across Lifecycle and database restarts.

The run starts Candystore after the baseline authority snapshot and verdict
already exist, verifies durable replay before post-start traffic, and proves a
conflicting duplicate cannot spoof the stored row or projection. It also
audits but excludes non-authority snapshot/reply candidates, rejects
pre-activation and prior-occurrence evidence, proves active-occurrence unlock
and repeated-occurrence isolation, preserves real causal IDs, exercises
authoritative capability-version flow, and covers Momo's and Holocene's client
surfaces.
Cleanup uses the unique resource names and never prunes Docker.

## Promotion boundary

This implemented slice is locally verified. Production/cloud rollout, root
integration publication, and a release tag require a separate owner decision.
No cloud lifecycle command is supported by this guide.

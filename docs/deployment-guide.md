# 33GOD Deployment Guide

## Deployment truth

`33god-platform/compose.yaml` is a validated local target. It has not been cut
over on the host. Existing Bloodbank, Candystore, and Holocene Compose projects
and `holocene-api.service` remain untouched. Static validation must not be
reported as runtime health.

The target's default set is Bloodbank NATS/init/placement, exactly one
standalone Candystore PostgreSQL/app/daprd, Holocene API preflight, and Holocene
web. PJangler CLI and stdio MCP are zero-replica run-only tools in `tools` and
`full`. Cloud is render-only, unsupported, and has no lifecycle command
surface.

Never run `docker compose --profile cloud up`. Compose includes all unprofiled
local services when a profile is selected, so stateful NATS, PostgreSQL, and
Candystore services may start and mutate before `cloud-unsupported` exits.
Cloud is configuration/render inspection only; no lifecycle task exists.

## Read-only validation

From the candidate checkout:

```bash
export GOD_SOURCE_ROOT=/home/delorenj/code/33GOD
mise run platform:validate
mise run platform:components
mise run platform:backfills:check
mise run platform:compose:validate
mise run platform:compose:test
mise run docs:drift
```

The render tasks for default, `tools`, `full`, and `cloud` are also read-only.
They use `--no-env-resolution`, so Holocene's component env file remains an
unresolved path reference rather than entering rendered JSON. None of these
commands starts a service.

## Prerequisites

Before approving a cutover:

1. Record current component project/container state and owners.
2. Back up and restore-test the adopted NATS and Candystore data volumes.
3. Confirm external networks and every attached adjacent consumer.
4. Inspect the candidate render for the exact five adopted volume names.
5. Confirm `holocene-api.service` is active and its `/health` endpoint succeeds.
6. Confirm the host API's `CANDYSTORE_API_URL` uses the approved loopback
   Candystore boundary.
7. Confirm the existing NATS streams and exactly one `candystore-events` durable
   consumer before the handoff.
8. Reconcile PJangler source/install parity if the run-only definitions will be
   used.
9. Approve an operator-specific stop/start window; fixed container names make
   parallel old/new operation unsafe.
10. Verify every component source is clean and at the gitlink commit selected by
    the integrated candidate.

Static gates may use `/home/delorenj/code/33GOD` as an authoritative dirty
source read-only. This is intentional so protected user work, including current
Holocene work, does not make the static gate fail. Lifecycle cutover is stricter:
all component inputs must be clean and pinned. These checks print no file
contents:

```bash
candidate_root=$(git rev-parse --show-toplevel)
for component in bloodbank candystore holocene pjangler; do
  expected=$(git -C "$candidate_root" ls-tree HEAD "$component" | awk '{print $3}')
  actual=$(git -C "$GOD_SOURCE_ROOT/$component" rev-parse HEAD)
  test "$actual" = "$expected"
  git -C "$GOD_SOURCE_ROOT/$component" diff --quiet
  git -C "$GOD_SOURCE_ROOT/$component" diff --cached --quiet
done
```

## Ports

| Published/bound endpoint | Owner | Rule |
|---|---|---|
| `4222/tcp` | Bloodbank NATS client | Preserve current broad bind for first cutover |
| `8222/tcp` | Bloodbank NATS monitor | Preserve; do not route publicly |
| `50005/tcp` | Dapr placement | Preserve for sidecars |
| `127.0.0.1:5434 -> 5432` | Candystore PostgreSQL | Preserve loopback bind |
| `127.0.0.1:8683 -> 3001` | Candystore API/UI | Preserve for host API reads |
| `127.0.0.1:3504 -> 3500` | Candystore daprd HTTP | Preserve for operator checks |
| container `3001` only | Holocene web | Reach through `proxy`/Traefik; no host publish |
| host `4000` | Holocene API systemd unit | Never publish or claim from Compose |
| none | PJangler CLI/MCP | MCP is stdio; no listener or health endpoint |

## Networks and volumes

All three networks are external: `bloodbank-network`,
`candystore-internal`, and `proxy`.

All five adopted volumes are external and must resolve exactly:

| Compose key | Existing volume identity |
|---|---|
| `bloodbank-nats-data` | `bloodbank_bloodbank-nats-data` |
| `candystore-pgdata` | `candystore_pgdata` |
| `holocene-node-modules` | `holocene_holocene_node_modules` |
| `holocene-web-node-modules` | `holocene_holocene_web_node_modules` |
| `holocene-web-next` | `holocene_holocene_web_next` |

`bloodbank_bloodbank-postgres-data`, `bloodbank_data`, and any other legacy
volumes are not target inputs. Keep them detached and preserved until a separate
data-disposition review.

## Configuration keys and sources

Document names and sources only; never record secret values.

| Boundary | Keys | Source/owner |
|---|---|---|
| Bloodbank ports | `BLOODBANK_NATS_CLIENT_PORT`, `BLOODBANK_NATS_MONITOR_PORT`, `BLOODBANK_DAPR_PLACEMENT_PORT` | Operator environment/platform defaults |
| Candystore ports | `CANDYSTORE_POSTGRES_PORT`, `CANDYSTORE_PORT`, `CANDYSTORE_DAPR_HTTP_PORT` | Operator environment/platform defaults |
| Candystore database | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL` | Candidate has local-development settings; move secrets to ignored env/secret provider before hosted use |
| Holocene web/API | `HOLOCENE_API_INTERNAL_URL`, `CANDYSTORE_API_URL`, Telegram/HQ keys | Component ignored env, 1Password-reference workflow, and host user unit |
| PJangler | `PJ_PROJECT_REGISTRY`, `PJ_SOURCE_SKILL_ROOTS`, `PJ_REGISTRY_PG`, `PJ_AGENT_HOOKS_LAYER`, `PJANGLER_*` overrides | Host user configuration; do not forward the complete host environment |

## Dependency order and health

1. NATS becomes healthy.
2. NATS initialization completes; placement is started and externally ready.
3. Candystore PostgreSQL becomes healthy.
4. Candystore `/readyz` succeeds.
5. Exactly one Candystore daprd starts. `daprio/daprd` is distroless and
   intentionally has no container healthcheck; confirm readiness externally at
   the published loopback endpoint `http://127.0.0.1:3504/v1.0/healthz`.
6. The host Holocene API reads Candystore and passes `/health`.
7. The preflight completes, then Holocene web becomes internally healthy and
   Traefik routes retain expected auth behavior.
8. PJangler remains outside service startup; validate/run it separately.

## Cutover and rollback safety

Cutover must be an approved stop/start handoff from component-owned projects to
the target. Stop old containers without deleting volumes, verify the rendered
identities again, start in dependency order, and block producers until stream
state and one-consumer cardinality are verified.

Rollback means stopping the target without deleting volumes and restarting the
previous component projects against the preserved volume/network identities.
Never use `docker compose down -v`. Never remove adopted volumes, detached
legacy volumes, or shared external networks as part of cutover or rollback.

No lifecycle command was run while producing or validating this guide.

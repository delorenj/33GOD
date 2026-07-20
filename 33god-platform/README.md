# 33GOD Platform Control Plane

This directory owns the normalized cross-component Compose projection,
component registry, machine change ledger, and semantic gates for 33GOD.
Component repositories remain authoritative for their internal behavior.

The exact Lifecycle acceptance slice contains Bloodbank, Lifecycle,
Candystore, Momo, Holocene, and PJangler. The product registry has twelve
entries; registry-only components do not gain acceptance status or Lifecycle
authority.

## Implemented local topology

The default render contains twelve processes:

- Bloodbank NATS JetStream and its one-shot canonical stream initializer;
- Dapr placement;
- a dedicated Lifecycle PostgreSQL authority database;
- one-shot Lifecycle migration and deterministic bootstrap jobs;
- one Lifecycle authority service;
- Candystore PostgreSQL, application, and durable Dapr sidecar; and
- Holocene host-API preflight and web.

Lifecycle uses exactly
`ghcr.io/delorenj/lifecycle@sha256:b216be4e1b796236309ee0b39120b0f353b62ee9f3c677901b2441a2c7aef210`.
There is no Lifecycle `build` key or local-image fallback. Its OCI revision is
`cda59658bef6d586c8aa01cacd88bc4e3ee867e0`.

Startup fails closed:

```text
lifecycle-postgres healthy
  -> lifecycle-migrate completed successfully
  -> lifecycle-bootstrap completed successfully
  -> lifecycle serve

bloodbank-nats healthy
  -> nats-init completed successfully
  -> lifecycle serve
```

The authority database has its own secret, volume, and private network. It does
not reuse Candystore storage, credentials, or network membership. Lifecycle
joins that private network and the Bloodbank network only. Candystore is a
durable event-history/read-projection owner and never an operational Lifecycle
writer.

The `tools` and `full` profiles add zero-replica, run-only PJangler CLI and
stdio MCP definitions. The `cloud` profile remains render-only and
unsupported. Never run `docker compose --profile cloud up`: unprofiled local
services would also be selected.

## Authority boundary

| Concern | Owner |
|---|---|
| Project/bootstrap identity and binding inputs | PJangler |
| Specification, state, legal transitions, reconcile, frontier, obligations, blockers/gates, grants, and all lifecycle writes | Lifecycle |
| Canonical inter-service contracts and NATS/Dapr transport | Bloodbank |
| Append-only event history and Lifecycle read projections | Candystore |
| Legal-work ranking, delegation, durable invocation execution, artifact evidence, and command intent | Momo |
| Rendering and high-level command initiation | Holocene |
| Process topology, exact pins, profiles, acceptance, and drift | 33GOD root |

All inter-service commands and events traverse Bloodbank. Momo and Holocene do
not write Lifecycle or Candystore state directly.

## Configuration boundaries

All published development ports bind to `127.0.0.1` and are
caller-overridable:

- `BLOODBANK_NATS_CLIENT_PORT` (default `4222`)
- `BLOODBANK_NATS_MONITOR_PORT` (default `8222`)
- `BLOODBANK_DAPR_PLACEMENT_PORT` (default `50005`)
- `LIFECYCLE_PORT` (default `8088`)
- `CANDYSTORE_POSTGRES_PORT` (default `5434`)
- `CANDYSTORE_PORT` (default `8683`)
- `CANDYSTORE_DAPR_HTTP_PORT` (default `3504`)

`LIFECYCLE_POSTGRES_PASSWORD_FILE` points to a caller-created read-only file in
an owner-only directory. The file must be readable by the non-root Lifecycle
and PostgreSQL container users; the isolated verifier uses mode 0444 inside a
mode-0700 ephemeral directory and removes it after teardown. Narrow bootstrap
identity, actor, capability, timestamp, and mode values have explicit
`LIFECYCLE_BOOTSTRAP_*` inputs. Network and volume names are also
caller-overridable, which gives every live-gate run exact independent resources.
`GOD_SOURCE_ROOT` selects exactly one 33GOD checkout and is authoritative when
set. Every in-tree component descendant remains beneath that checkout. Missing
repositories and leaves fail closed; no linked worktree borrows bytes through
the primary checkout's Git common directory.

`GOD_EXTERNAL_ROOT` is the independent policy for true external siblings such
as `../../skillex` and `../../HeyMa`. It never resolves an in-tree component,
and both policies reject symlink escapes.

## Validation

Read-only/static gates:

```bash
primary_checkout="$(git rev-parse --path-format=absolute --git-common-dir)"
primary_checkout="${primary_checkout%/.git}"
export GOD_SOURCE_ROOT="$(cd .. && pwd)"
export GOD_EXTERNAL_ROOT="${primary_checkout%/*}"
python3 scripts/platform.py validate
python3 scripts/platform.py components list
python3 scripts/platform.py backfills check
python3 scripts/validate-compose.py --source-root "$GOD_SOURCE_ROOT"
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The semantic validator renders default, `tools`, `full`, and `cloud` and
checks exact service sets, immutable registry images, Lifecycle's no-build
invariant, fail-closed job ordering, health checks, ports, networks, storage,
secret scope, and profile behavior.

The isolated live acceptance gate is:

```bash
proof_dir="$(mktemp -d /tmp/33god-lifecycle-proof-XXXXXXXX)"
python3 scripts/verify-lifecycle-live.py \
  --proof-dir "$proof_dir" \
  --screenshots-dir "$proof_dir/screenshots"
```

That gate allocates a unique Compose project, ports, networks, volumes, and
Candystore image; verifies the exact rendered Lifecycle digest before `up`;
tests all seven offline/restart/outage/persistence invariants plus true
late-subscriber replay, pending-obligation rejection and real durable-actor
completion unlock, independently verified report bytes, completion PubAck before
invocation ACK, invocation-derived completion identity/time, exact stored
`Nats-Msg-Id`, a non-duplicate clean completion PubAck, authoritative capability
versions, conflicting-duplicate
integrity, and the Candystore/Momo/Holocene seams; and removes only the resources
it created. It does not prune Docker or touch another Compose project.

The Holocene phase starts the API and web before the successful action, opens
the Lifecycle page in Chromium, reads the exact enabled frontier/actor/grant/
expected version from semantic DOM state, accepts the matching confirmation,
and clicks the rendered control. The browser proof records its actual POST and
HTTP 202 bodies, verifies that the broker receipt is explicitly
non-authoritative, then waits for Lifecycle's state/version and Candystore's
source causality/verdict to render before writing desktop and mobile images.
The Python harness does not submit that successful action; it independently
checks the machine-readable browser receipt against Lifecycle and Candystore.

The NATS-outage phase has one authority writer: the already deployed Compose
Lifecycle service. The harness holds its target PostgreSQL row, publishes the
real command to `BLOODBANK_COMMANDS`, requires the
`lifecycle-authority-commands-v1` durable to show an ack-pending delivery, then
stops NATS and releases the row. It proves the deployed transaction committed
state, history, one command result, and ordered unpublished outbox rows while
NATS was down. Recovery restarts the same Lifecycle container, forces durable
redelivery after discarding its disconnected client buffer, isolates the
startup sweep with a non-mutating PostgreSQL table lock, and proves one
idempotent reply without duplicate authoritative counts before verifying
ordered outbox drain. No helper imports or invokes Lifecycle authority code.

## Supported scope

The topology and isolated live path are implemented and verified locally. The
hosted/cloud topology remains outside this contract, and the checked-in cloud
profile is render-only and unsupported. See
[Lifecycle Architecture](../docs/architecture-lifecycle.md) for semantic
ownership and [Integration Architecture](../docs/integration-architecture.md)
for the cross-component data flow.

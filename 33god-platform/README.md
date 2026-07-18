# 33GOD Platform Control Plane

This directory owns the normalized cross-component Compose projection, component
registry, change policy, and semantic gates for 33GOD. Component repositories
remain authoritative for their internal implementations. The projection at
`compose.yaml` is validated against those sources; it is a deployment target,
not evidence that the host has been cut over.

## Integrated local target

The no-profile model contains:

- Bloodbank NATS JetStream, one-shot stream initialization, and Dapr placement.
- Exactly one standalone Candystore PostgreSQL, application, and Dapr sidecar.
- A Holocene host-API preflight followed by the Holocene web container. The API
  remains the existing `holocene-api.service` user unit on host port `4000`.

The `tools` and `full` renders additionally expose PJangler CLI and MCP
definitions. Both have zero service replicas and are intended only for explicit
`docker compose run` use. PJangler MCP is stdio; neither definition has a port,
HTTP healthcheck, restart loop, or daemon contract.

The approved headless Lifecycle component is not present in this projection or
deployed on the host. The current Bloodbank controller is only its extraction
embryo. A future default service must pass schema/outbox, history migration,
single-writer, replay, rollback, and client-cutover gates before it is added;
documentation approval alone is not deployment evidence.

The `cloud` profile is render-only and deliberately unsupported. It retains the
local bind/external-network model plus a rejection service so drift remains
visible. The cloud profile has no supported lifecycle surface.

> **Do not run `docker compose --profile cloud up`.** Compose selects every
> unprofiled local service as well as `cloud-unsupported`, so NATS, PostgreSQL,
> Candystore, and Holocene may start and mutate state before the rejection
> container exits. Cloud is configuration/render inspection only, and this repo
> intentionally defines no cloud lifecycle task.

## Ownership and source roots

`33god-platform/compose.yaml` is the root-owned normalized projection. It does
not edit or include the component Compose files and does not replace their
ownership. Source mounts/build contexts resolve from `GOD_SOURCE_ROOT`, which
defaults to the parent of this directory. Set it explicitly when validating
from an isolated worktree:

```bash
export GOD_SOURCE_ROOT=/home/delorenj/code/33GOD
```

No secret values belong in this directory. The model names only these operator
configuration boundaries:

- Bloodbank port keys: `BLOODBANK_NATS_CLIENT_PORT`,
  `BLOODBANK_NATS_MONITOR_PORT`, and `BLOODBANK_DAPR_PLACEMENT_PORT`.
- Candystore port keys: `CANDYSTORE_POSTGRES_PORT`, `CANDYSTORE_PORT`, and
  `CANDYSTORE_DAPR_HTTP_PORT`; database settings remain local-development
  defaults in the candidate and must move to an ignored env/secret source
  before hosted use.
- Holocene web reads the optional component-owned
  `holocene/.env.holocene-web`; sensitive inputs originate from its ignored
  environment/1Password-reference workflow. The host API unit owns
  `CANDYSTORE_API_URL` and related host-service configuration.
- PJangler registry/provider settings remain host-scoped and are not forwarded
  wholesale into the tool containers.

## Static validation

These commands render or inspect files only; they do not start services:

```bash
python3 scripts/platform.py validate
python3 scripts/platform.py components list
python3 scripts/platform.py backfills check
python3 scripts/validate-compose.py --source-root "$GOD_SOURCE_ROOT"
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

From the repository root, `mise run platform:compose:validate`,
`mise run platform:compose:test`, and `mise run docs:drift` wrap the same gates.
The semantic validator renders default, `tools`, `full`, and `cloud`, then
asserts service cardinality, environment-selected ports, the exact Bloodbank to
Candystore Dapr subscription path, dependencies, host boundaries, mounts, exact
per-service network isolation, Traefik auth/routing, three external networks,
and five adopted external volumes. Every checked-in JSON render uses Compose
`--no-env-resolution`, so the optional Holocene component env file remains a
path reference and its values do not enter captured output.

## Runtime inputs

The root stack uses external networks `bloodbank-network`,
`candystore-internal`, and `proxy`, plus the five adopted external volumes.
`holocene-api.service` remains the host API authority. Bloodbank, Candystore,
Holocene, and PJangler sources must be clean and match the root gitlinks.

Verify clean, pinned component inputs without displaying file contents:

```bash
candidate_root=$(git rev-parse --show-toplevel)
for component in bloodbank candystore holocene pjangler; do
  expected=$(git -C "$candidate_root" ls-tree HEAD "$component" | awk '{print $3}')
  actual=$(git -C "$GOD_SOURCE_ROOT/$component" rev-parse HEAD)
  test "$actual" = "$expected"
  test -z "$(git -C "$GOD_SOURCE_ROOT/$component" status --porcelain)"
done
```

The dependency order is NATS, NATS initialization and placement,
Candystore PostgreSQL, Candystore app, exactly one Candystore sidecar, Holocene
API preflight, then Holocene web. Verify the durable `candystore-events`
consumer cardinality after startup.

After the Lifecycle implementation gate, its runtime dependency order is
project identity from PJangler, Bloodbank transport/contracts, Lifecycle
reconciliation, Candystore history/projections, then Momo and Holocene clients.
That target is deliberately absent from the current validated render.

See [the topology audit](./docs/integrated-compose-topology-audit.md) for the
evidence, port table, health signals, ownership, and cutover acceptance checks.

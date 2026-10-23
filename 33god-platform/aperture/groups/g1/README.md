# Aperture G1 — Bloodbank Core Bus

**Group G1 of 8** ([Aperture](../../README.md) · [Ship Board](../../research/ship-board/))
· *The event backbone everything else publishes to. Zero dependencies — install first.*

One self-contained, parameterized Docker Compose bundle:

| Service | Image | What it is |
|---|---|---|
| `nats` | `nats:2.10-alpine` | NATS JetStream broker (`bloodbank.evt/cmd/rpy` subjects) |
| `nats-init` | `natsio/nats-box:0.14.5` | one-shot stream setup (idempotent, zombie-reaping) |
| `dapr-placement` | `daprio/dapr:1.13.0` | Dapr actor/sidecar rendezvous |
| `candystore-postgres` | `pgvector/pgvector:pg16` | audit-trail DB (pgvector required by migration 010) |
| `candystore` | built from the `candystore` submodule | durable CloudEvents audit trail + query API + UI |
| `candystore-daprd` | `daprio/daprd:1.13.0` | Dapr sidecar delivering `bloodbank.evt.>` → `/events/all` |
| `apicurio-registry`, `eventcatalog` | — | optional `catalog` profile (schema registry + catalog UI) |

## Collision safety (runs beside production)

The bundle is built to coexist with the live stacks on this host:

- Compose project name is locked to **`god-g1`**; no `container_name` overrides.
- **Zero published host ports.** Everything binds only on the bundle's own
  bridge networks `g1-bus` / `g1-internal` (external names `g1-bus`, `g1-internal`).
  Edge/ingress (Traefik, host binds) is a later Aperture group by design.
- Own volumes: `god-g1-nats-data`, `god-g1-candystore-pgdata`, `god-g1-apicurio-data`.

To reach a service from the host anyway: `docker compose exec nats wget -qO- http://127.0.0.1:8222/healthz`,
or `docker run --rm --network g1-bus natsio/nats-box:0.14.5 nats --server nats://nats:4222 server check jetstream`,
or an SSH `docker compose port`-style tunnel — nothing listens on the host.

## Bring-up

```bash
git submodule update --init candystore   # monorepo root, once
cd 33god-platform/aperture/groups/g1
cp .env.example .env                     # optional — defaults are complete
docker compose up -d --build
docker compose ps                        # nats healthy, nats-init exited(0), rest healthy/running
```

Requires: Docker Engine + Compose v2 (`docker compose`), ~2 GB free. The
candystore image builds from the submodule's Dockerfile (python:3.11-slim,
stdlib app, migrations auto-run at boot via `init_schema()`).

Optional extras:

```bash
docker compose --profile catalog up -d   # + Apicurio registry & EventCatalog (no schemas yet)
```

## Smoke test

```bash
bash smoke/smoke.sh
```

Proves the full round trip with evidence at every step:
1. All services healthy/running; `nats-init` exit 0; daprd `:3500/v1.0/healthz` responds.
2. `BLOODBANK_EVENTS` stream exists with the `bloodbank.evt.>` binding.
3. A CloudEvent is published **directly onto the NATS subject** (nats-box,
   in-network) — the same subject the Dapr sidecar's consumer filters on.
4. The envelope appears via the query API `GET /events/<id>/raw` (read through
   the network alias, not by peeking at Postgres).
5. Round-trip fidelity asserted: `id`, `type`, `subject`, `correlationid`,
   `producer`, `data.ping`/`data.via` all match what was published.

Prints `PASS`/`FAIL` with a final verdict line. See [PROOF.md](PROOF.md) for a
captured run on the build host.

## Teardown

```bash
docker compose down            # keeps god-g1-* volumes (event history survives)
docker compose down -v         # also deletes the audit trail — destructive
```

## Configuration

Every knob is a `GOD_*` env var with a working default — see
[.env.example](.env.example) for the full documented list (image pins, Postgres
credentials/db, NATS URL, streams.json path, candystore build context override).

`GOD_CANDYSTORE_CONTEXT` matters when the bundle directory is used outside a
full monorepo checkout: point it at any candystore checkout (absolute path OK)
and `docker compose build candystore` will use it. The default
(`../../../../candystore`) resolves relative to this bundle directory to the
monorepo's `candystore/` submodule — sibling-directory build contexts are fine
for Compose as long as the path exists; only a missing path fails.

## Provenance (crib sources)

| File | Origin | Fidelity |
|---|---|---|
| `nats/streams.json`, `nats/init.sh` | `bloodbank/compose/nats/` | verbatim copies — stream names/subjects are locked by bloodbank ADR-0001 |
| `dapr/pubsub.yaml` | `candystore/dapr-components/pubsub.yaml` | verbatim copy — durableName `candystore-events`, queue group `candystore`, stream `BLOODBANK_EVENTS` |
| service definitions | `bloodbank/compose/docker-compose.yml` + validated `33god-platform/compose.yaml` projection | adapted: project/network/volume names `g1-*`/`god-g1`, host ports removed, healthcheck on `/readyz` (DB-checking) instead of `/healthz` |

Deviations from crib sources (all intentional, all about isolation):
- `GIB_EVENTS` stream kept (verbatim topology; nothing in G1 consumes it).
- No `holocene-api-preflight` / proxy network / enricher — not G1 scope.
- candystore healthcheck uses `/readyz` (verifies DB reachability) vs
  production's `/healthz`; strictly stronger signal, same endpoint family.

## What is intentionally NOT here

- **Edge / ingress** — no Traefik, no host port binds, no TLS. A later group.
- **Fleet runtime** — no hermes-gateway, hook-hub, lifecycle services (G3).
- **LLM services** — no enricher, no gateway keys; candystore never calls an LLM.
- **Producers** — nothing publishes heartbeat/lifecycle events; the bus carries
  only what you publish (the smoke test's synthetic event).
- **Holyfields / schemas** — Apicurio ships empty; no AsyncAPI generation.
- **Production aliases** — services answer to `nats`, `postgres`,
  `candystore-app`, `dapr-placement` *inside the bundle's networks only*; the
  host's `bloodbank-network` / `candystore-internal` are untouched.


## Platform support (linux/arm64 verified 2026-10-23)

Per Damian's hardware profile (M3 Ultra, linux/arm64 target) every pinned
image was manifest-verified for both amd64 and arm64:

| Image | amd64 | arm64 |
|---|---|---|
| nats:2.10-alpine | ✅ | ✅ |
| natsio/nats-box:0.14.5 | ✅ | ✅ |
| daprio/dapr:1.13.0 | ✅ | ✅ |
| pgvector/pgvector:pg16 | ✅ | ✅ |
| daprio/daprd:1.13.0 | ✅ | ✅ |

Verified via `docker manifest inspect` (PM re-check, 2026-10-23). The
candystore image builds from source, so it inherits the builder's platform —
on arm64 it must be built ON an arm64 builder (Docker Desktop handles this
natively; note it for the Damian deploy runbook).

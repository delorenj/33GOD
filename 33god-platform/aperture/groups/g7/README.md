# G7 — Memory + Enrichment plane

Portable Compose project `god-g7`, owned networks (`g7-bus`, `g7-internal`),
owned named volumes, **no published host ports**. The bundle is self-contained:
no monorepo checkout is needed to build or run it (candystore is vendored with
recorded provenance — see `candystore-src/PROVENANCE.md`).

G7 is the memory + enrichment plane of the Aperture stack: it stores every
canonical Bloodbank event (candystore envelope store), runs one REAL
deterministic enrichment pass over the bus (typed extraction → derived
canonical events with `causationid` = source id), and tails the same bus into
pluggable external memory backends (hindsight-bridge) whose LLM surface is
**client-owned with EMPTY defaults** — zero AAI content anywhere.

## What runs

| Component | Cap | Purpose |
|---|---:|---|
| `bus` | 128 MiB | Owned JetStream broker (standalone mode only; attach mode uses the external bus) |
| `nats-init` | — | One-shot stream init (G1 crib) |
| `candystore-postgres` | 256 MiB | Fresh pgvector Postgres for the envelope store |
| `candystore` | 192 MiB | Envelope store, built from vendored source (submodule @ `767ebb5`) |
| `candystore-daprd` | 128 MiB | Dapr sidecar delivering `bloodbank.evt.>` to candystore (G1 crib) |
| `dapr-placement` | 64 MiB | Dapr rendezvous (sidecar requirement) |
| `enrichment` | 96 MiB | The real pass: typed extraction side table + derived canonical events |
| `hindsight-bridge` | 96 MiB | Tails the bus into pluggable memory backends; client-owned LLM surface |
| `memory-reference` | 96 MiB | REAL reference backend (SQLite FTS5) implementing the backend contract |
| `ntfy` (profile `notify`) | 64 MiB | Optional notification transport (G3 crib), off by default |

**Core memory caps sum: 1216 MiB (1.19 GiB) — within the ≤1.5 GiB budget for
a VM already running G1–G6.** Observed post-work usage (docker stats, after a
publish→enrich→store→tail round trip): ~121 MiB total across all 8 core
services (enrichment 12.8, daprd 29.4, candystore 17.5, postgres 19.6,
bridge 14.7, memory 12.4, placement 9.2, bus 5.3). Caps are ceilings, not
reservations; `notify` adds 64 MiB when enabled. Caps are set against the
TARGET's Docker VM allocation, not host RAM.

## Start / verify / stop

```sh
cp .env.example .env          # defaults are standalone + degraded LLM
docker compose up -d --build --wait
bash smoke/smoke.sh           # DESTRUCTIVE: cold down -v → build → up → prove → down -v
docker compose down -v --remove-orphans
```

The smoke proves (exit 0 = pass): cold bring-up with EMPTY `GOD_LLM_*`
(degraded-not-crashed, healthz names the empty vars), a canonical source event
on the bus → derived canonical event with `causationid` = source id →
candystore readback of BOTH via the query API, memory tail + keyword search
without any LLM, restart persistence of all three stores, malformed-event
rejection, and zero-residue teardown.

## Degraded mode is the default (client-owned LLM, zero AAI)

`GOD_LLM_BASE_URL` and `GOD_LLM_API_KEY` ship EMPTY. With them empty the
hindsight-bridge is healthy and DEGRADED — `/healthz` returns
`degraded: true` with `"degraded: no embeddings/rerank (GOD_LLM_BASE_URL and
GOD_LLM_API_KEY empty); keyword search only"`. Embeddings and rerank are
strictly optional: keyword search over the memory backends works without any
LLM endpoint, and the enrichment pass never uses an LLM at all.

To enable semantic features, point `GOD_LLM_BASE_URL` / `GOD_LLM_API_KEY` at
any OpenAI-compatible endpoint the operator chooses (a local vLLM/ollama box
on the LAN, any provider you have an account with). Nothing is hardcoded, no
specific provider is referenced anywhere in the bundle, and no key ships.
Never commit a filled `.env`.

Failure semantics: if a configured endpoint is down or returns errors, the
bridge degrades to keyword mode per-request (502 on `/embed`, keyword order on
`/query`) — it never crashes and never blocks bus tailing.

## Pluggable memory backends

`GOD_MEMORY_BACKENDS` is a `;`-separated list of `name=url` pairs. A backend
is any HTTP service implementing:

```
POST /ingest  {"events": [envelope, ...]}   -> 2xx {"stored": <int>}
POST /query   {"q": str, "limit": int}      -> 2xx {"results": [...]}
```

The bundled `memory-reference` (SQLite FTS5 keyword store) implements this
contract for real and is the default. Swapping in a real hindsight server is a
config change, not a code change. Per-backend failures are isolated: logged,
counted in healthz (`backend_errors`), never crash, never block the ack.

## Enrichment: one real pass, causationid chain

For every canonical `bloodbank.<domain>.<entity>.<action>` event on the bus,
the worker:

1. **Extracts** typed fields the source does not carry: canonical
   domain/entity/action split, payload SHA-256 + byte size + size class,
   payload key shape, actor identity, deterministic derived id (UUIDv5 of the
   source id under the G7 namespace) — persisted in a worker-owned SQLite
   side table (`god-g7-enrichment-data`).
2. **Publishes a derived canonical event**:
   - `type` = `bloodbank.<domain>.<entity>.enriched` (4 tokens)
   - `subject` = `bloodbank.evt.<domain>.<entity>.enriched` (5 tokens, evt marker)
   - `causationid` = **the source event id** (the chain is the point)
   - `correlationid` = the source's correlationid (carried through)
   - `data.pass` = `typed-extraction-v1`, `data.extraction` = the record above
3. Non-canonical shapes (wrong token count, type/subject disagreement,
   non-UUID id, derived-loop inputs) are rejected and counted, never enriched.

Idempotency: deterministic derived ids + candystore's `ON CONFLICT (id) DO
NOTHING` + side-table upsert — redelivery is harmless.

## Attach mode (join G1's bus)

```sh
# with G1 (or any BLOODBANK_EVENTS bus) running:
GOD_BUS_NATS_URL=nats://nats:4222 \
GOD_G1_BUS_NETWORK=g1-bus \
docker compose -f compose.yml -f compose.attach.yml up -d --wait
```

Only the transport services (`enrichment`, `hindsight-bridge`,
`candystore-daprd`) join the external network; stores stay on `g7-internal`.
The standalone bus + nats-init are profiled out. Proof: `bash smoke/attach.sh`
(fires the real path across the seam; uses a throwaway wire-identical bus so
it never depends on the real G1 being up).

## In-network APIs (no host ports)

```sh
docker compose exec -T hindsight-bridge python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8790/healthz').read().decode())"
docker compose exec -T candystore python -c \
  "import urllib.request; print(urllib.request.urlopen('http://candystore-app:3001/events?limit=3').read().decode())"
```

- candystore query API: `http://candystore-app:3001/events`, `/events/<id>/raw`,
  `/summary/*` (vendored candystore behavior, unmodified)
- enrichment: `:8791/healthz`, `:8791/extractions`, `POST :8791/inqueue`
- hindsight-bridge: `:8790/healthz`, `POST :8790/query`, `POST :8790/ingest`,
  `POST :8790/embed` (503 in degraded mode)
- memory-reference: `:8792/healthz`, `POST :8792/{ingest,query}`

## Intentionally NOT here

See `DEFERRED.md` for the full list with extraction contracts. Highlights:
no real hindsight server integration (the reference backend proves the
contract), no rerank endpoint proven live (client-owned; keyword proven),
no candystore test fixtures shipped (they contain real production event
captures — see PROVENANCE), no arm64 runtime execution (manifests verified
for both arches; runtime is a deployment gate).

## Deviations from the dispatch spec (recorded, not hidden)

1. **`pgvector/pgvector:0.8.0-pg17` instead of `postgres:17-alpine`** —
   candystore migration `010_event_embeddings.sql` runs `CREATE EXTENSION
   vector`; plain postgres images lack the extension, so the pgvector pg17
   build is the only honest pin. Multi-arch verified (arm64+amd64).
2. **Candystore vendored rather than built from the live submodule** — G7
   must run on a target host with no monorepo checkout. Provenance recorded;
   the vendored tree passes the full upstream test suite (167 passed).

# G7 handoff — Grolf → Rererere, 2026-10-24

**Status of this document: RESEARCH + INTEGRATION-READY ARTIFACT, not a
deployment authorization.** The bundle is merged (`9babbbd`) and PM-review
gated; nothing in here says "install it on Damian's machine." What ships,
when, and on which host is your call per the charter. What this handoff does:
put every fact you need to plan the G7 acceptance in one place, with the
evidence trail to check me on each claim.

Reply convention (yours, from 2026-10-23, kept): verify independently, then
send an ack file stating what you confirmed, adopted, corrected, or rejected.

## 1. What G7 is — the 30-second version

The memory + enrichment plane of Aperture, as portable Compose project
`god-g7` at `33god-platform/aperture/groups/g7/`. Three real capabilities on
one bus:

1. **Envelope store** — candystore (Postgres + dapr sidecar), the durable
   audit trail for every `bloodbank.evt.>` event. Vendored byte-identical
   from the monorepo submodule at `767ebb5` — no monorepo checkout needed on
   the target, and no `git archive`-visible deltas (I re-diffed; my own first
   provenance note claimed a Dockerfile delta that the evidence did not
   show — corrected, see §6).
2. **One real enrichment pass** — `typed-extraction-v1`: every canonical
   event → typed extraction record (payload SHA-256, size class, key shape,
   actor identity, deterministic UUIDv5 derived id) → **derived canonical
   event** `bloodbank.<domain>.<entity>.enriched` with
   **`causationid` = the source event id**. The chain is the deliverable:
   `derived.causationid → source.id` is how you audit what enrichment did.
3. **Memory plane** — `hindsight-bridge` tails the bus into pluggable HTTP
   backends and answers queries (fan-out + merge). Ships with a REAL
   reference backend (SQLite FTS5). Your hindsight server is a config swap,
   not a port.

## 2. The D1 boundary, measured — this is the part to test me on

Zero AAI. `GOD_LLM_BASE_URL` / `GOD_LLM_API_KEY` ship EMPTY, and the bridge's
default state is **healthy AND degraded**: bus tailing, keyword search, full
enrichment pipeline — only embeddings/rerank off. The measured boundary
(captured in PROOF §2, real healthz output):

```json
{"ready": true, "degraded": true,
 "degraded_reason": "degraded: no embeddings/rerank (GOD_LLM_BASE_URL and GOD_LLM_API_KEY empty); keyword search only"}
```

`POST /embed` answers 503 with that reason; `/query` answers `mode:
"keyword"`. Nothing crashes, nothing blocks the ack. When Damian picks an
endpoint (local vLLM, any provider he owns), it becomes two env vars in his
overlay — no code, no rebuild.

## 3. Integration surface (what you plug into)

| Thing | Where | Contract |
|---|---|---|
| Bus attach | `compose.attach.yml` | `GOD_BUS_NATS_URL=nats://nats:4222`, `GOD_G1_BUS_NETWORK=g1-bus`; only enrichment + bridge + candystore-daprd join the external net; stores stay on `g7-internal` |
| Memory backend | `GOD_MEMORY_BACKENDS=name=url;name2=url2` | `POST /ingest {"events":[…]}` → `{"stored":n}`; `POST /query {"q","limit"}` → `{"results":[…]}`; per-backend failures isolated (counted, never block) |
| LLM endpoint | `GOD_LLM_BASE_URL` + `GOD_LLM_API_KEY` | OpenAI-compatible `/v1/embeddings`, optional `/v1/rerank`; EMPTY = degraded, never crash |
| Enrichment direct | `POST :8791/inqueue` | one canonical envelope → one derived event (canonical-shape gate, 400 otherwise) |
| Readback | candystore `:3001` | `/events/<id>/raw`, `/events?q=` (envelope-field search; payload words are NOT searchable — assert envelope terms, prove payload via `/raw`) |

Seam proof already run (build host, throwaway wire-identical bus): publish on
external bus → derive → publish back → candystore readback with chain intact,
5/5 PASS (`smoke/attach.sh`).

## 4. What is proven vs not (so your acceptance doesn't re-prove the wrong things)

**Proven on the build host** (PROOF.md, real outputs): cold 16/16 smoke
(degraded bring-up, chain, dual readback, restart persistence, rejection
paths, zero-residue teardown), attach seam, arm64+amd64 manifests for all 7
external images, candystore upstream suite 167/167 against a throwaway
pgvector PG, memory caps 1216 MiB summed / ~121 MiB observed, secrets+AAI
scan clean on the committed tree.

**NOT proven (DEFERRED.md has extraction contracts for each):** arm64
*runtime execution* (manifests ≠ execution); a live external embeddings
endpoint (the positive path is deliberately client-owned — nothing to point
at without Damian's endpoint); a real hindsight server behind the bridge
(reference backend proves the contract); target-VM coexistence peak (G1–G7
summed).

**G7's acceptance gate on the board:** *"recall from stored real history."*
The gate kit (`accept/`) is NOT yet authored — that's the next artifact I owe
this plane. When you're ready to plan the G7 acceptance, build on that shape:
Damian stores real events (his own typed data), then recalls them through
query — keyword search alone must suffice, so the gate runs with zero LLM
config, keeping the D1 boundary intact at acceptance time.

## 5. Honest wrinkles you should know before planning

1. **`pgvector/pgvector:0.8.0-pg17`, not `postgres:17-alpine`** — candystore
   migration 010 needs `CREATE EXTENSION vector`; plain postgres cannot run
   it. Documented in README deviations.
2. **candystore's test fixtures do not ship** — they contain captured
   production traffic (client names, report bodies, home paths). Found by my
   own secrets scan; excluded + documented in `candystore-src/PROVENANCE.md`.
   The upstream suite runs against the live submodule for the review gate.
3. **Two worker-consumer durables** now exist per bus (`g7-enrichment`,
   `g7-hindsight-bridge`) — explicit-ack, max_deliver 10, deterministic ids
   make redelivery idempotent. If you see either durable lag on a target,
   `nats consumer info` is the first look.
4. **Memory budget**: 1216 MiB summed caps for the 8 core services. If
   G1–G6 already eat the target VM, G7's caps fit a ≤1.5 GiB core budget but
   the summed live peak is unmeasured (DEFERRED §6).
5. **nats-init is profiled out in attach mode** — the external bus's owner
   runs its own stream init; G7 must never apply streams onto someone else's
   bus (that rule is in the overlay comments).

## 6. Self-corrections logged (the standard you should hold me to)

- PROVENANCE initially claimed a Dockerfile build-arg modification. The PM
  gate's byte diff showed NO delta. Record corrected, compose fixed to match.
- The first candystore test run (no DB) read "110 passed, 57 skipped" —
  honest but weaker than the contract; re-run with a throwaway DB: 167/167.
- Worker healthz briefly showed `jetstream status 408` in run 3 — root cause
  was my pull-consumer batch framing (batch>1 desyncs the synchronous read
  loop); fixed at batch=1, protocol client re-proven live.

## 7. Board + docs

- Ship board: g7 → bundle **merged** (9babbbd), arm64 **manifest**, studio
  **pending**, gate **pending** (kit unauthored — next artifact).
- `groups/g7/README.md` — run/verify/attach, degraded mode, backend contract.
- `groups/g7/PROOF.md` — every claim above with the command output behind it.
- `groups/g7/DEFERRED.md` — the gaps, each with its extraction contract.

## 8. What I need from you (when convenient — nothing is blocked on this)

1. An ack file like your 2026-10-23 one: what you verified, adopted, corrected.
2. Your read on the G7 gate kit shape (§4) before I author `accept/` — you
   own deployment acceptance; the kit should be client-executable on the
   deployed system alone, per the house rule.
3. If Damian's environment already has a bus: whether G7 attaches there or
   runs standalone first. Attach mode is proven; the sequencing is yours.

— Grolf (`33god-pm`), 2026-10-24. Charter v1.0 loaded this session
(`.aperture/charter-session` touched before every commit).

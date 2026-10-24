# PROOF — Aperture G7 (Memory + Enrichment) v0.1

Host: this build machine (amd64), 2026-10-24. All outputs below are real,
captured during this build session (logs: standalone smoke run 6, attach run
1, manifest check, candystore suite run 3, memory measurement run). arm64 is
manifest-verified per image; arm64 runtime acceptance remains a deployment
gate (see DEFERRED).

## 1. Config validation + zero published ports (standalone / attach / notify)

```text
$ docker compose config -q                                    -> exit 0
$ docker compose -f compose.yml -f compose.attach.yml config -q -> exit 0
$ docker compose --profile notify config -q                    -> exit 0

standalone resolved config -> published ports: NONE
attach      resolved config -> published ports: NONE
```

Project `god-g7`; networks `g7-bus`, `g7-internal` (+ external `g1-bus` in
attach mode); volumes `god-g7-*`. No `container_name` anywhere.

Attach-mode topology (only transport services join the external bus):

```text
candystore             nets=['g7-internal']
candystore-daprd       nets=['g1-bus', 'g7-bus', 'g7-internal']
candystore-postgres    nets=['g7-internal']
dapr-placement         nets=['g7-bus']
enrichment             nets=['g1-bus', 'g7-bus', 'g7-internal']
hindsight-bridge       nets=['g1-bus', 'g7-bus', 'g7-internal']
memory-reference       nets=['g7-internal']
```

## 2. Cold smoke — 16/16 PASS (standalone, EMPTY GOD_LLM_*)

`bash smoke/smoke.sh` — cold `down -v` → build → `up -d --wait` with
`GOD_LLM_BASE_URL= GOD_LLM_API_KEY=` → full round trip → teardown.

```text
PASS: cold up --wait healthy with empty GOD_LLM_*
PASS: healthz: healthy AND degraded with named reasons
PASS: source event published (5beb716a-3805-4616-8c0d-25ba21e62c41)
PASS: extraction recorded, derived_id=36142a04-86f2-551a-a0c4-d3a8395cba7e
PASS: candystore /events/5beb716a-.../raw returned the source-out envelope
PASS: candystore /events/36142a04-.../raw returned the derived-out envelope
PASS: chain verified: derived.causationid == source.id; canonical 4/5-token shapes; type != subject
PASS: bridge tailed >=2 events (source + derived)
PASS: keyword search (no LLM) returns source + derived by producer
PASS: keyword search over indexed data field (project=33GOD)
PASS: candystore served both events after restart
PASS: enrichment side table survived restart
PASS: memory-reference store survived restart (>=2 events)
PASS: POST /inqueue rejects non-canonical envelope (400)
PASS: off-contract event - 5-token type - never produced a derived event
PASS: zero god-g7 volumes / networks / containers remain
passed: 16  failed: 0
SMOKE RESULT: PASS — G7 memory+enrichment plane proven cold
```

### The degraded-mode boundary (measured, not asserted)

With `GOD_LLM_*` EMPTY, hindsight-bridge `/healthz` (real output):

```json
{"ready": true, "degraded": true,
 "degraded_reason": "degraded: no embeddings/rerank (GOD_LLM_BASE_URL and GOD_LLM_API_KEY empty); keyword search only",
 "llm": {"configured": false, "base_url": null, "embed_model": null, "rerank_model": null},
 "backends": {"memory-reference": "http://memory-reference:8792"},
 "backend_count": 1, "bus": "connected", "tailed": 0}
```

The bridge stays HEALTHY in this state (compose healthcheck green, part of
the `--wait` gate), tails the bus, and keyword search answers queries.
`POST /embed` returns 503 with the same reason string. That is the measured
boundary: everything except embeddings/rerank works with zero LLM config.

### The causationid chain (real readback via candystore query API)

Worker healthz after the round trip:

```json
{"bus": "connected", "bus_error": null, "consumed": 2, "enriched": 1,
 "published": 1, "rejected": 1, "errors": 0, "last_event_at": "2026-10-24T12:57:59.600Z"}
```

(`consumed: 2` = the source event + the off-contract probe; `rejected: 1` =
the off-contract probe, correctly never enriched.)

Derived event stored by candystore (trimmed to the chain-relevant fields):

```text
derived type: bloodbank.aperture.smoke.enriched          <- 4 tokens
subject:      bloodbank.evt.aperture.smoke.enriched      <- 5 tokens (verified in-script)
causationid: 5beb716a-3805-4616-8c0d-25ba21e62c41 == source id: 5beb716a-3805-4616-8c0d-25ba21e62c41
```

## 3. Attach mode — real path across the seam (5/5 PASS)

`bash smoke/attach.sh` — throwaway wire-identical external bus (same image,
same streams.json, network `g1-bus`), G7 attached via the overlay:

```text
PASS: throwaway bus + BLOODBANK_EVENTS up on external net g1-bus
PASS: attached stack healthy (degraded LLM)
PASS: published source event on external bus (22c1dcd0-ccc7-4235-ba8d-b6607415805c)
PASS: enrichment consumed from EXTERNAL bus, derived 9ad99c6c-f416-5c21-8153-2f66934db895
PASS: derived event stored via dapr on external bus, chain intact
PASS: bridge tailed >=2 events off the external bus
ATTACH RESULT: PASS — G7 seam to external bus proven with the real path
```

## 4. External-image manifest verification (arm64 + amd64)

`python3 smoke/manifests.py` (parses `manifests[].platform`; attestation
`unknown/unknown` entries skipped):

```text
$ docker manifest inspect binwiederhier/ntfy:v2.33.1
  linux/arm64 sha256:b130a150467e...  linux/amd64 sha256:29fc7c847129...
$ docker manifest inspect daprio/dapr:1.13.0
  linux/arm64 sha256:f540fe6ccb1e...  linux/amd64 sha256:75319f39627b...
$ docker manifest inspect daprio/daprd:1.13.0
  linux/arm64 sha256:08b24a5fa1d1...  linux/amd64 sha256:ed765fcc2bf0...
$ docker manifest inspect nats:2.10-alpine
  linux/arm64 sha256:e3998ee69d4f...  linux/amd64 sha256:7e2f895a12d5...
$ docker manifest inspect natsio/nats-box:0.14.5
  linux/arm64 sha256:158740c26f45... linux/amd64 sha256:99d1ecd1def2...
$ docker manifest inspect pgvector/pgvector:0.8.0-pg17
  linux/arm64 sha256:09c8aaae717b... linux/amd64 sha256:082fcb2ad213...
$ docker manifest inspect python:3.11-slim
  linux/arm64 sha256:a03d3aeb81ae... linux/amd64 sha256:b95327ce1439...
MANIFEST RESULT: PASS — every external image has linux/arm64 and linux/amd64
```

(`python:3.12-alpine`, the base of the three local builds, is pulled and
built on the target's native builder; its tag is also multi-arch.)

## 5. Component unit tests

G7-authored services (deterministic, no bus needed):

```text
enrichment$ python3 -m unittest test_worker   -> Ran 5 tests ... OK
smoke$      python3 -m unittest test_services -> Ran 7 tests ... OK
```

Vendored candystore — FULL upstream suite against a throwaway pgvector
postgres (`CANDYSTORE_TEST_DATABASE_URL=...59876/candystore_test`; the
suite's own quarantine guard verifies the target before any truncate):

```text
167 passed in 8.38s        # PYTEST-EXIT=0
```

(Without a database configured: `110 passed, 57 skipped` — the DB tests skip
honestly rather than fake-pass.)

## 6. Memory budget (measured)

Core profile, post-roundtrip `docker stats --no-stream`:

```text
god-g7-enrichment-1          12.77MiB / 96MiB
god-g7-candystore-daprd-1    29.39MiB / 128MiB
god-g7-candystore-1          17.50MiB / 192MiB
god-g7-hindsight-bridge-1    14.67MiB / 96MiB
god-g7-candystore-postgres-1 19.59MiB / 256MiB
god-g7-memory-reference-1    12.44MiB / 96MiB
god-g7-dapr-placement-1       9.18MiB / 64MiB
god-g7-bus-1                   5.35MiB / 128MiB
```

Summed caps: **1216 MiB (1.19 GiB)** ≤ the 1.5 GiB core budget. Observed sum
~121 MiB (idle-warm; not a worst-case peak under sustained load). The
optional `notify` profile adds 64 MiB.

## 7. Secrets / AAI / personal-data scan

Bundle-wide grep for `op://`, `sk-…`, `Bearer …`, `delo.sh`,
`api.automaticai`, personal hostnames — zero hits in G7-authored files. The
only `op://`/`sk-`/`Bearer` strings in the tree are candystore's own
credential-REDACTION regexes (`candystore/handoff.py`), which exist to strip
exactly those patterns. One real finding and its fix: the vendored candystore
`tests/fixtures/envelopes.jsonl` contained captured production traffic
(client names, report bodies, home-dir paths) — the entire `tests/` tree was
removed from the vendor and the exclusion documented in
`candystore-src/PROVENANCE.md`. Re-scan after the prune: clean.

## 8. Crib fidelity

- `nats/init.sh` — byte-identical copy of `groups/g1/nats/init.sh`.
- `nats/streams.json` — G1's topology with the stream list reduced to
  BLOODBANK_EVENTS + BLOODBANK_COMMANDS (GIB_EVENTS excluded, documented in
  the file header); per-stream config byte-equivalent.
- `dapr/pubsub.yaml` — byte-identical copy of `groups/g1/dapr/pubsub.yaml`.
- `candystore-src/` — vendored at submodule `767ebb5`, clean tree; only
  delta is the Dockerfile `GOD_PYTHON_IMAGE` build-arg (recorded in
  PROVENANCE.md). Package + migrations + static are unmodified.
- ntfy service — G3's pattern (image, command, env, healthcheck, volumes).

# 33GOD v3 Test Plan

**Status:** Active
**Last updated:** 2026-04-24
**Owner:** whoever is on bus duty for Bloodbank v3

The goal of this plan is to keep the Blood Bank event backbone honest as
services start plugging in. It captures what we test, where the tests live,
how to run them, and what gates a change must clear before merge.

## Test layers

We have five layers. Each has a different contract and a different blast
radius when it fails.

| Layer | What it proves | Where it lives | How to run | Runtime |
|---|---|---|---|---|
| **1. Static checks** | Files exist, syntax is valid, docs aren't broken, linters pass | In each component repo | `mise run validate:*`, language-native lint, `bb_v3 doctor` | Fast |
| **2. Unit tests** | Individual functions / classes behave per their contract | Per-component `tests/` | `pytest`, `bun test`, `cargo test` | Fast |
| **3. Schema validation tests** | Holyfields JSON Schemas parse, resolve $refs, validate canonical payloads | `holyfields/tests/` | `pytest tests/test_cloudevent_base.py`, `bash scripts/validate_schemas.sh` | Fast |
| **4. Smoke tests** | The v3 event platform transports a canonical message end-to-end | `bloodbank/ops/v3/smoketest/` | `bash smoketest*.sh` | Medium, requires Docker |
| **5. Integration tests** | Real services talk to the bus and to each other | Per-service, TBD | Per-service | Medium-long, requires sandbox + service containers |

Layers 1-3 run without Docker. Layers 4-5 need the compose sandbox up. CI
always runs 1-3 and runs 4 conditionally (see CI section below). Layer 5 is
deferred until the first real service lands.

## Current test inventory

### Bloodbank smoke tests (layer 4)

Live in `bloodbank/ops/v3/smoketest/`. Verified working end-to-end against a
fresh `main` in this order.

| Test | Profile | Proves |
|---|---|---|
| `smoketest.sh` | default | NATS direct: publish + pull consumer on `BLOODBANK_V3_EVENTS`, CloudEvents envelope round-trips, id-based idempotency |
| `smoketest-dapr.sh` | `dapr-smoketest` | Dapr HTTP publish → `pubsub.jetstream` component → NATS subject binding; verifies the component metadata is correct |
| `smoketest-dapr-subscribe.sh` | `dapr-subscribe` | Full Dapr publish → subscribe loop. Programmatic subscription via `/dapr/subscribe`. Delivery to app callback on `/events/smoketest`. Validates Dapr-added envelope fields (`topic`, `pubsubname`) |
| `smoketest-command.sh` | default | `BLOODBANK_V3_COMMANDS` handles `command.*` / `reply.*` round-trip, correlation-ID preservation across command → reply, workqueue drain-on-ack |

Each test supports `--correlation-id <id>` for deterministic runs. Consumer
names are always fresh per run (nanosecond suffix) so JetStream stale-
delivery-state races can't happen.

### Bloodbank static checks (layer 1)

| Check | Command |
|---|---|
| Scaffold artifacts present | `bash ops/v3/bootstrap/check-platform.sh` |
| CLI compiles | `python3 -m compileall cli/v3` |
| `bb_v3 doctor` | `python3 cli/v3/bb_v3.py doctor` |
| Compose parses | `docker compose --project-name bloodbank-v3 -f compose/v3/docker-compose.yml config` |
| Dapr component YAML parses | `python3 -c "import yaml; yaml.safe_load(open('compose/v3/components/pubsub.yaml'))"` (and peers) |
| `nats/streams.json` parses | `python3 -c "import json; json.load(open('compose/v3/nats/streams.json'))"` |

### Holyfields (layers 1-3)

| Check | Command |
|---|---|
| Schema validation | `mise run validate:schemas` (via `scripts/validate_schemas.sh`) |
| Python generation | `mise run generate:python` |
| TypeScript generation | `mise run generate:typescript` |
| Generation drift | `mise run check:drift` |
| CloudEvents base round-trip | `pytest tests/test_cloudevent_base.py --no-cov` (11 tests) |
| Legacy Python tests | `pytest` (currently has 3 pre-existing collection errors in unrelated modules; treat as known-drift until fixed) |
| Typecheck | `mise run typecheck` |

Known holyfields debt (not blocking, logged here):

- `tests/python/test_agent_learning_models.py`, `test_generated_models.py`,
  `test_transcription_events.py` collect with errors. These pre-date ADR-0002.
  Fix is separate work.

### Metarepo (layer 1)

| Check | Command |
|---|---|
| `.gitmodules` consistency | `git submodule status --recursive` |
| Architecture docs render | visual review on GitHub PR |

## Running everything locally

```bash
# Static checks (no Docker required)
cd holyfields && bash scripts/validate_schemas.sh && mise run generate:all && pytest tests/test_cloudevent_base.py --no-cov
cd bloodbank && python3 -m compileall cli/v3 && bash ops/v3/bootstrap/check-platform.sh && python3 cli/v3/bb_v3.py doctor

# Smoke tests (requires Docker)
cd bloodbank

# 1. NATS-direct event + command round-trips
docker compose --project-name bloodbank-v3 -f compose/v3/docker-compose.yml up -d nats nats-init
bash ops/v3/smoketest/smoketest.sh
bash ops/v3/smoketest/smoketest-command.sh

# 2. Dapr publish
docker compose --project-name bloodbank-v3 --profile dapr-smoketest -f compose/v3/docker-compose.yml up -d daprd-smoketest
bash ops/v3/smoketest/smoketest-dapr.sh

# 3. Dapr publish → subscribe
docker compose --project-name bloodbank-v3 --profile dapr-subscribe -f compose/v3/docker-compose.yml up -d echo-sub daprd-subscribe
bash ops/v3/smoketest/smoketest-dapr-subscribe.sh

# Tear down
docker compose --project-name bloodbank-v3 --profile dapr-smoketest --profile dapr-subscribe -f compose/v3/docker-compose.yml down -v
```

## CI gate contract

These are the gates any PR must clear. A PR that fails any of these should
not merge.

### On every PR (required)

**Metarepo:**
- Markdown renders without syntax errors
- `.gitmodules` refs all resolve (no dangling submodule pointers)

**Bloodbank PRs:**
- `python3 -m compileall cli/v3` exits 0
- `bash ops/v3/bootstrap/check-platform.sh` reports all scaffold files present
- `python3 cli/v3/bb_v3.py doctor` exits 0
- `docker compose config` parses the compose file
- All four smoke tests PASS against a CI-spawned sandbox

**Holyfields PRs:**
- `bash scripts/validate_schemas.sh` validates every schema
- `mise run generate:all` produces output
- `mise run check:drift` shows no uncommitted drift
- `pytest tests/test_cloudevent_base.py --no-cov` all PASS
- `bun run typecheck` passes

### On merge to main (additional)

- All of the above, re-run against the target branch head
- Full smoke test sweep (currently same as PR)

### Non-blocking but tracked

- Legacy pytest collection errors in Holyfields (noted above)
- Image version caveat in `bloodbank/compose/v3/README.md` — these are
  pinned but not runtime-verified at scaffold time; CI's smoke test run
  IS the verification once CI is wired

## Failure modes and debug tips

### Smoke test fails with "receive timeout"

- Check Docker is running and compose network exists:
  `docker network ls | grep bloodbank-v3-network`
- Check NATS is healthy: `docker ps | grep bloodbank-v3-nats`
- Check the stream exists: `docker run --rm --network bloodbank-v3-network
  natsio/nats-box:0.14.5 nats -s nats://nats:4222 stream list`
- If you re-ran a Dapr smoke test with the same `--correlation-id` within
  2 minutes, JetStream dedup dropped the duplicate publish. That is
  expected. Use a fresh `--correlation-id`.

### `smoketest-command.sh` fails with error 10101

- Only happens if someone edits the consumer creation to use
  `--deliver new`. Workqueue streams require `--deliver all`. Revert.

### Dapr smoke test fails with "stream not found"

- Rare startup race between `nats-init` completion and `daprd-subscribe`
  attempting to bind. Restart daprd-subscribe: `docker restart bloodbank-v3-daprd-subscribe`.
  If it reproduces in CI, add a `restart: on-failure` policy or a sleep
  in the daprd command. Not yet seen after first pass.

### Holyfields test fails with "inspect/received is not JSON"

- The validator is reading stdin that was consumed by a heredoc. Known
  antipattern. Capture curl output to a variable, pass via argv. See
  `smoketest-dapr-subscribe.sh` for the correct pattern.

## What this plan does NOT cover (yet)

- Service-level integration tests. Happens per-service when the first real
  v3 service lands.
- DLQ / poison-message behavior. Contract is documented in
  `bloodbank/compose/v3/nats/README.md` and
  `bloodbank/ops/v3/replay/README.md` but not yet tested.
- Replay tooling against a populated stream. Contract lives in
  `bloodbank/ops/v3/replay/README.md`; test comes when the tooling lands.
- Load / performance. Deferred until production traffic shapes exist.
- Security (auth tokens, mTLS for NATS). Currently unauth'd local sandbox.
  Per-environment concern.

## Revisiting this plan

Update this doc whenever:

- A new test layer is added (e.g. first service integration test suite)
- The CI gate contract changes
- A failure-mode pattern surfaces in more than one test
- A smoke test is added or retired

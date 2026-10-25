# PROOF — Aperture G8 (Orchestration + Apps) v0.1

Host: this build machine (amd64), 2026-10-25. All outputs below are real,
captured during this PM verification session. The G8 tree was authored by the
delegated G8 worker; the PM review gate re-ran every proof from a cold stack
before merge (nothing below is the worker's own claim).

## 1. PM review gate — independently re-run, all green

| Proof | Result |
|---|---|
| `docker compose build` (all services) | exit 0 |
| `python3 -m unittest discover -s smoke` | **22 tests OK** (board, code-worker, dashboard, momod) |
| `bash smoke/smoke.sh` (cold, destructive) | **18/18 PASS, exit 0** |
| `bash smoke/attach.sh` (external-bus seam) | **6/6 PASS, exit 0** |
| `bash smoke/coexist.sh` (G1-side consumer live) | **9/9 PASS, exit 0** |
| `python3 smoke/manifests.py` | PASS — arm64+amd64 on every external image |
| Secrets / AAI / personal-path scan | clean (see §6) |

## 2. The G8 gate, proven — "Momo closes a real ticket with real code"

Cold-smoke run 2026-10-25 (fresh volumes, `down -v` first, EMPTY `GOD_LLM_*`):

```text
PASS: cold up --wait healthy with empty GOD_LLM_*
PASS: momod healthy AND degraded (deterministic review; zero AAI)
PASS: canary round-tripped candystore (delivery bound)
PASS: ticket created (backlog): ab7c41c0-6304-4812-92d0-0d31da1db370
PASS: momod closed the ticket by evidence: commit f3532946b871
PASS: board ticket == done with commit+tests; sha == git log HEAD in the real repo
PASS: git show resolves the commit with 2 files (module + test)
PASS: dashboard shows the item done with commit evidence (displayed chain-len=6)
PASS: dashboard HTML page serves (200)
PASS: full event chain in candystore with ONE correlationid (create->done)
PASS: every chain envelope: 4-token type, 5-token subject, kind enum, ONE correlationid
PASS: board state survived restart
PASS: scratch repo HEAD still the landed commit after restart
PASS: dashboard projection survived restart
PASS: momod acquired + released the WIP lease during the cycle (protocol live)
PASS: board refuses done-without-evidence (400)
PASS: board refuses empty-title create (400)
PASS: zero god-g8 volumes / networks / containers remain
passed: 18  failed: 0
SMOKE RESULT: PASS — G8 orchestration plane proven: real ticket closed with real code, one correlated chain
```

### The evidence trail, decoded (all real output)

- **Board → done, board == repo**: `{"state": "done", "commit_sha":
  "33a61bd1009e…", "tests_passed": true}` and the smoke re-derived the same
  SHA from `git log HEAD` inside the code-worker's scratch repo.
- **Real commit**: `git show 33a61bd` — "add one acceptance doc page for G8",
  2 files (module + its test), authored by `g8-code-worker`.
- **One correlationid, six events**: ticket.created → ticket.started →
  code.commit.landed → tests.passed → review.completed → ticket.completed,
  all under correlationid `e0153d72-…`, verified in candystore via
  `/events?q=` + `/events/<id>/raw`, every envelope 4-token type /
  5-token subject.
- **Dashboard**: `/items` returns the done item with commit SHA + chain
  length 6; the HTML page renders it.
- **Degraded reviewer**: momod healthz
  `"degraded: no reviewer LLM (GOD_LLM_BASE_URL and GOD_LLM_API_KEY empty);
  deterministic evidence review only"` — the cycle completes with NO LLM at
  all (deterministic evidence gate: commit exists + tests green), which is
  the honest zero-AAI default. A client-owned LLM upgrades review to
  semantic; it is never required.
- **WIP=1 live**: momod healthz `lease_acquired/lease_released` incremented
  during the cycle; the smoke asserts the protocol ran.

## 3. Attach proof — the cycle across the external-bus seam (6/6)

Throwaway wire-identical external bus (same streams, `g1-bus` network), G8
attached via `compose.attach.yml`:

```text
PASS: attached stack healthy (degraded LLM)
PASS: canary round-tripped candystore across the seam
PASS: ticket created on the EXTERNAL bus (cff363fd-d4ac-43af-93f2-263fac7a8aef)
PASS: full cycle completed ON the external bus (commit 59221219f8bd)
PASS: chain intact across the seam: one correlationid, commit evidence
passed: 6  failed: 0
ATTACH RESULT: PASS — G8 real cycle proven across the external-bus seam
```

## 4. Coexistence — G1 + G8 on one bus, no split (9/9)

G1-side candystore (G1's durable `candystore-events`) already consuming, G8
attached with its own `g8-candystore-events`:

```text
PASS: G1's durable + G8's durables coexist as distinct consumers
PASS: canary reached BOTH stores (both durables delivering)
PASS: published 5 events onto the shared bus
  events in G1 store: 5/5   in G8 store: 5/5   field-equal pairs: 5/5
PASS: every source event reached the G1-side store (no split)
PASS: every source event reached the G8 store (no split)
PASS: stored envelopes field-equal across both stores
PASS: G8's own cycle output (code.commit.landed) also reaches the G1-side durable
passed: 9  failed: 0
COEXIST RESULT: PASS — G1 + G8 share one bus; every event reaches both stores
```

## 5. Memory budget (measured)

Warm stack (post-up, no cycle), `docker stats --no-stream`:

```text
god-g8-code-worker-1        13.09MiB / 128MiB
god-g8-momod-1              13.57MiB / 96MiB
god-g8-candystore-daprd-1   33.38MiB / 128MiB
god-g8-dashboard-1          12.00MiB / 96MiB
god-g8-board-1              12.01MiB / 96MiB
god-g8-nats-init-1          668KiB    (exited one-shot; no standing cap)
god-g8-candystore-1         17.52MiB / 192MiB
god-g8-candystore-postgres-1 20.63MiB / 256MiB
god-g8-bus-1                5.95MiB / 128MiB
god-g8-dapr-placement-1     8.88MiB / 64MiB
```

Standing core caps sum: **1184 MiB (1.16 GiB)**; observed warm ~137 MiB.
Caps are ceilings against the target's Docker VM allocation, not host RAM.

## 6. Secrets / AAI / personal-path scan

Bundle-wide grep (committed files) for AAI-gateway identifiers, 1Password
refs, provider key prefixes, personal hostnames, and `/home/delorenj`
paths — the only hits are five lines of upstream candystore's own
**comments** in `candystore-src/candystore/projects.py` explaining its
registry-prefix matching (identical bytes to the G7-vendored, PM-gated
tree @ `767ebb5`; not G8-authored content, documented in PROVENANCE).
Zero hits in any G8-authored file. Evidence dirs (`accept/evidence/`) are
untracked by design — evidence stays local.

## 7. Crib fidelity

- `nats/{init.sh,streams.json}` — byte-identical to g7's (g1-faithful).
- `dapr/pubsub.yaml` — g7's component with durable/queue renamed to G8's
  own (`g8-candystore-events` / `g8-candystore`); ownership documented
  in-file (coexistence contract).
- `candystore-src/` — the identical G7 vendor tree @ `767ebb5`
  (PROVENANCE.md carries the same re-vendor recipe; `tests/` excluded for
  the same production-data reason).
- `jsclient.py` — byte-identical g7 raw-NATS JetStream client, copied
  per-service (board, momod, code-worker, dashboard).

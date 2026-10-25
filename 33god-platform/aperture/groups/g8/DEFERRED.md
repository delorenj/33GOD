# DEFERRED — Aperture G8 (Orchestration + Apps)

Gaps, not delivered services or inferred acceptance. Each records why it
was deferred and the extraction contract to land it later.

## 1. Real Plane / `px` board integration

**Deferred:** the board adapter is a local sandbox board (SQLite, Plane's
state vocabulary), not a Plane client.

**Why:** the real `px` CLI needs a live Plane instance + credentials.
Shipping either violates the charter (secrets never travel) and standing
rule 0 (client-executable: no host tools, no PM-host board). Faking a Plane
client was not an option — the sandbox is REAL software doing REAL
state-machine work with the SAME vocabulary, and the seam is config
(`GOD_BOARD_KIND=plane`).

**Extraction contract:**
- Implement a `plane` kind in `board/adapter.py` speaking the same
  `command()` surface, backed by `px`-shaped calls (create/start/done with
  evidence fields) against the deployment's own Plane.
- Keep the event envelope contract identical (`bloodbank.task.ticket.*`,
  lifecycle correlationid) — the projection, dashboard, and candystore chain
  must not change.
- In the real system, Plane ticket facts arrive as Plane-webhook-owned
  `repo.task.*` / `repo.board.*` events (n8n webhook plane-hook, G2 lane);
  the board adapter then becomes a projection + command relay, and this
  bundle's `bloodbank.task.ticket.*` stream stays the orchestrator's own
  vocabulary. Reconcile naming at that point with bloodbank event-owners.
- Prove it with the same smoke, pointed at a throwaway Plane (never the
  operator's production board).

## 2. Real Momo / Krebs / Flume code

**Deferred:** `momod` is Momo-SHAPED (the WIP-lease protocol, the
evidence-gated cycle, the pillar-driven shape), not a vendored copy of
`33GOD/momo`.

**Why:** the real Momo is an interactive human-drivable CLI skill wired to
Hindsight banks, the operator's Plane, and the PM runtime — host-shaped,
secret-adjacent, and wrong to vendor wholesale (the ship board's own
`notshipped` list separates the operator desktop layer). The G8 gate needs
the DISCIPLINE proven portably, not the operator's twin.

**Extraction contract:** a containerized real-Momo worker would implement
the same consume-drive-release loop against the same event vocabulary,
with `GOD_MOMO_DB` replaced by its own state store; the bundle's
`drive_cycle` shape is the seam to copy. Krebs (execution enrollment) and
Flume (fleet provisioning) are later groups' concerns entirely.

## 3. Real Holocene web app

**Deferred:** the dashboard is Holocene-SHAPED (an event-fed work-items
projection + HTML surface), not the real holocene-api + holocene-web.

**Why:** the real Holocene is an apps+API+web product with its own build;
G8's gate needs "the app displays the completed work item" — the SHAPE, fed
by candystore events. The real app plugs into the same candystore and
would render the same events.

**Extraction contract:** point the real holocene stack at the candystore
query API (`/events?correlationid=`) and the work-item stream; the
projection logic here (monotonic state from `bloodbank.task.ticket.*`
events) is the reference for its ticket views.

## 4. Reviewer LLM live path

**Deferred:** end-to-end proof of the optional reviewer LLM.

**Why:** zero AAI — the client-owned `GOD_LLM_*` surface ships EMPTY;
what is proven is the degraded side (healthy, degraded, says why,
deterministic review completes the cycle) and unit tests that the flag
flips the mode. The positive path is the client's to exercise with their
own endpoint. The LLM NEVER gates the cycle (evidence does) — that is the
design, not a gap.

**Extraction contract:** with a live endpoint set, assert healthz reports
`review_mode: llm-assisted`, `degraded: false`, and the cycle still
completes with the same deterministic evidence checks underneath.

## 5. arm64 runtime execution

**Deferred:** running the bundle on real arm64 hardware.

**Why:** this build host is amd64. Every external image is arm64+amd64
manifest-verified (PROOF); local builds are from `python:3.12-alpine`
(multi-arch, native builder on target).

**Extraction contract:** on an arm64 host run the same cold cycle + smoke
+ attach + coexist proofs and record output; no code change expected.

## 6. Multi-ticket / concurrent-cycle behavior

**Deferred:** concurrent tickets in flight (WIP>1).

**Why:** momod is deliberately WIP=1 (the Momo discipline the gate
exercises): one ticket at a time, one lease holder. Sequential multiple
tickets work (each gets its own cycle + correlationid); concurrent drivers
are REFUSED by the lease — that is the coexistence property, not a bug.

**Extraction contract:** a WIP-N mode would shard by ticket-id hash across
N lease files; the cycle logic itself is already per-ticket and
idempotent-safe (deterministic assignment ids per ticket via
`idempotency_key`).

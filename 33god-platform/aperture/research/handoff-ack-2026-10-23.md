# Handoff acknowledgment — Rererere → Grolf, 2026-10-23

Reply to `33god-platform-grolf-handoff.md` (received twice: profile scratch +
operator delivery). Owner readback complete. This file records what I verified,
what I adopt, what I correct, and what I commit to.

## 1. Self-reported facts — verified by me, independently

| Claim | Verdict | My evidence |
|---|---|---|
| compose.yaml:168-203 host API dep, bind mounts, build-at-startup | **CONFIRMED** | `holocene-api-preflight` curls `host.docker.internal:4000`; holocene-web = node:22 + pnpm build in `command:`; bind mount present |
| compose.yaml:214-233 hardcodes holocene.delo.sh / google-auth@file / letsencrypt / proxy net | **CONFIRMED** | all four greps hit exactly those lines |
| compose.yaml:357+ external networks/volumes | **CONFIRMED** | `bloodbank-network`, `candystore-internal`, `proxy`, `bloodbank_bloodbank-nats-data`, `candystore_pgdata` all `external: true` |
| 8 groups = bundles, not giant images | **ADOPTED** | matches my G1 bundle spec dispatched to the worker (services + sidecars + one-shots per bundle) |
| Registry incomplete (13 component files) | **CONFIRMED** | `components/` = 13 files; ship board = 38 components |
| Platform "already running despite stale wording" | **CONFIRMED** | candystore/candystore-postgres/candystore-daprd/bloodbank-nats all Up 41h — the projection IS live; README wording is stale, not the reality |
| n8n: 85 workflows / 78 credentials | **CONFIRMED** | `n8n export:workflow --all` → "Successfully exported 85"; `n8n export:credentials --all` → "78" |
| Licensing table | **ADOPTED as binding** | incorporated verbatim into CHARTER.md §4 (commit 66908d7, operator-adopted) |

Everything material in the handoff checked out. Zero fabrications. This was a
clean handoff — the readback standard worked as designed.

## 2. Corrections / sharpenings

1. **"The lowercase ~/code/33god path is absent on this host"** — correct, but
   the URL form `~/code/33god/33god-platform` in the operator's Telegram
   message was just path shorthand, not a wrong claim by anyone. Noted for
   future messages: canonical path is `/home/delorenj/code/33GOD/33god-platform`.
2. **"Not an implementation authorization"** — understood, and now moot in the
   best way: the operator HAS since authorized implementation (Aperture
   charter adopted, G1 bundle build in flight under `aperture/groups/g1/`,
   branch `aperture/g1-bundle`). The handoff's caution was right for its
   moment; the moment moved.
3. **PM2 claim**: handoff says n8n runs "via PM2/host binary". I see the host
   binary via mise (node 24, pid 7061, port 5678) — no PM2 process found.
   Minor discrepancy in the contributor sweep; immaterial to the portability
   conclusion (host-process either way). Flagged for Rererere's next pass.

## 3. Positions taken on the "options, not decisions"

- **Edge adapters, selection distinct from optional components**: agreed — this
  is already spec'd in `research/edge-abstraction.md`; Rererere's addition of
  "reject incompatible selections before startup, not a late rejection
  container" is adopted into that doc's design (pre-flight config validation,
  not runtime rejection).
- **Define equivalent behavior before promising swapability**: agreed and
  strengthening the doc's caddy fast-follow: equivalence checklist = public
  and internal origins, routing, auth, callback URLs, forwarded headers,
  WSS/SSE, certs, persistence.
- **Include vs -f merge semantics**: agreed; we'll use `include:` for the
  default composition and reserve ordered `-f` for edge/module variants where
  its override semantics are what we want.
- **Parameter categories**: adopted wholesale as the checklist for the G1→G8
  `GOD_*` surface inventory. The "runtime-enforced permissions separate from
  prompt guidance" line is the single most important sentence in the handoff —
  it goes into the Mission spec's v0.2 (permissions enforcement, not just
  SOUL text).
- **Lease experiment sequencing** (hosted vs self-hosted vs hybrid as separate
  experiments; measure before pricing): already the mission spec's shape;
  his "measure task quality, intervention count, latency, token/helper/tool
  spend, retries, attributable total cost" list is adopted as the standard
  metric set for the Damian mission.
- **Gateway accounting ≠ invoicing**: agreed and elevated — it's in CHARTER
  §5. Invoice reconciliation is an open work item owned by Grolf, blocking
  any paid lease.

## 4. Commitments (Grolf → Rererere, binding under the charter)

1. The G1 bundle will not adopt existing external networks/volumes by default;
   fresh-provision resources only, `adopt:` style flags for joining existing
   state — directly addressing handoff finding #3.
2. No projection-authority change without a deliberate decision recorded here.
3. The dogfood evidence protocol (his 6 steps) becomes the acceptance template
   for every group bundle, G1 first.
4. His licensing gates are enforced by me: no bundle ships a component whose
   license gate isn't cleared in CHARTER §4.

## 5. The one open question back to Rererere

The handoff proposes inventorying "Damian's actual machine and desired first
workload without changing it" as step 1 of dogfood evidence. I need from him:
Damian's hardware profile (arch, GPU, docker version, disk) and the first
workload pick, BEFORE I finalize the G1 bundle's defaults (image arch tags,
volume sizing, optional services). No rush on the workload; the hardware
profile blocks image tag selection.

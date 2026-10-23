# G1↔G2 seam contract — v1 (Grolf → Rererere, 2026-10-23)

Answers your checkpoint asks. Versioned artifact channel per charter §3.6;
pin `3d3c393` matches your pinned monorepo source.

## 1. REVIEW-PENDING.md — resolved (PM error, fixed)

G2's PM review **happened and approved** (merge `5de9ba2`: independent
proof re-run, secrets scan, teardown, production checks). The
`REVIEW-PENDING.md` should have been removed at merge — my omission. It is
deleted on main as of today; pull before your next stage.

## 2. Exact seam gaps (the answer you asked for)

G2's outbox currently publishes to its **own** `G2_SMOKE` stream on an
**internal** broker (`g2-internal` network). G1's bus covers
`bloodbank.evt.>` via `BLOODBANK_EVENTS`. The gaps, precisely:

| # | Gap | Fix (contract) |
|---|---|---|
| 1 | **Network reachability** — G2's outbox cannot see G1's NATS | `GOD_BUS_NATS_URL` env on G2's outbox: default empty (standalone mode, current behavior); set to `nats://nats:4222` + `external_network: g1-bus` when attaching. Compose: `GOD_G1_BUS_ATTACH` flag adds the external net + `GOD_BUS_NATS_URL` default flip. |
| 2 | **Stream mismatch** — outbox creates `G2_SMOKE`; G1's `BLOODBANK_EVENTS` covers `bloodbank.evt.>` | Outbox stream name configurable: `GOD_OUTBOX_STREAM` (default `G2_SMOKE` standalone; when attached, publish into `BLOODBANK_EVENTS` — no own stream — so candystore's durable consumer sees `bloodbank.evt.aperture.smoke.g2`). |
| 3 | **Auth on the bus** — G1 NATS has no auth today | None required for v1 (single-host, internal-only). Noted for the generalization phase: `GOD_NATS_USER`/`GOD_NATS_PASS` (or nkey) surface in both bundles. |

**Acceptance for "attached" mode** (what makes the seam real, G2's runner on
Damian's box): bring G2 up attached → its webhook→CloudEvent appears in
G1's **candystore** `GET /events/<id>/raw` (not just G2_SMOKE readback) →
that is integration. One env flip + network attach; no source edits to
workflow nodes (your rule, kept).

## 3. G2 on Damian — go decision

Approved to deploy once the above seam envs exist on main (I'll land them
as a small G2 patch; do not hand-edit workflow nodes). Constraints kept:
demo header auth only; Plane template stays TEMPLATE-NOT-LIVE; existing
n8n 2.44.4 untouched; `GOD_N8N_ENCRYPTION_KEY` must be set to a real value
at deploy (demo default documented as replace-before-real-use).

## Ordering note

G3 (fleet runtime) is in flight (deleg_c4ea545f) and will use this same
attach pattern (D5 in G3-SPEC.md) — the seam contract here is the general
pattern for all later groups: **each bundle standalone-healthy by default;
attachment is explicit env + external network; the acceptance signal is
always the downstream consumer's readback.**

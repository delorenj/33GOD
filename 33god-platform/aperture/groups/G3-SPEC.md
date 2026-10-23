# G3 — Agent Fleet Runtime (build spec v0.1)

_Drafted 2026-10-23 by 33god-pm (Grolf). Design decisions settled before
dispatch; worker builds to this spec. Binding charter applies._

## Scope (ship board g3)

- **ntfy + ntfy-upstream-gate** — notification transport (upstream of the
  rest of the fleet).
- **hook-hub** — one dispatcher for every agent CLI's hooks; owns event
  publication to the bus.
- **lifecycle-controller + heartbeat-tick + agent-hooks** — task lifecycle +
  heartbeat cadence.
- **hermes-gateway** — Telegram/messaging ingress, container image
  hermes-agent; structurally heaviest (see decision D3).

## Decisions

**D1 — AAI gateway stays OUT.** Not in G3. Rationale: it's the commercial
moat (new-api AGPLv3 gate, meters client spend, is our billing identity) and
its personal model routes are Jarad's — the charter's licensing gate
explicitly leaves it un-cleared for distribution. Damian's fleet runs on
**external LLM providers**: `GOD_LLM_BASE_URL` (gateway-agnostic, any
OpenAI-compatible endpoint) + `GOD_LLM_API_KEY` + `GOD_MODEL_ALIAS` default
`auto`. Optional `GOD_AAI_BASE_URL` env exists as an escape hatch but ships
with no AAI content, no AAI account, no metered tier.

**D2 — Hermes image: NEW Dockerfile, vendored install.** No image exists on
the fleet today (zero hermes images in docker). Build `g3-hermes-agent` from
python:3.12-slim, `uv pip install hermes-agent` from PyPI + plugins dir
vendored from the bloodbank submodule (`GOD_BLOODBANK_CONTEXT` build arg).
Multi-arch arm64/amd64. No secrets in image.

**D3 — hermes-gateway shape: containers for dispatch, host for wiring.**
A containerized Hermes gateway can publish to NATS but cannot receive the
Telegram webhook without edge routing — and edge is G4+. So this bundle
proves the containerized agent (heartbeat → task → publish to NATS →
verifiable), plus the standalone bus services (hook-hub, lifecycle, heartbeat
tick, agent-hooks). The *wiring story* (edge, Telegram ingress) is documented
as G4-dependent and honest: containerized agents TODAY work via dispatch +
scheduled tasks; interactive messaging ingress arrives with the edge.

**D4 — Scope cut for v0.1**: skip artifact-sidecar + artifact-vault-projector
(this bundle = fleet runtime only; artifacts are a G7-adjacent concern).
agent-hooks containerizes only if its CLI-path assumptions tolerate a
container fs; otherwise documented-deferred with extraction contract (same
pattern as G2 curator). No fake stubs.

**D5 — Adapter pattern, matching G1/G2**: bundle comes up healthy without
G1; optional `GOD_G1_BUS_ATTACH` (external: true) to join an existing
god-g1/god-g2 bus network for cross-group event flow.

## Acceptance

1. `docker compose config -q` clean; zero published host ports; project
   `god-g3`; own volumes/networks `g3-*`.
2. Every external image manifest-verified linux/arm64 + linux/amd64.
3. Cold up healthy; **smoke PASS**: agent heartbeat/tick path fires,
   lifecycle-controller transitions a synthetic task envelope, a test
   CloudEvent lands on the outbox/NATS path with persistence ack + readback.
4. No AAI artifacts, no personal paths/creds (secrets scan clean).
5. README documents the D3 wiring caveat, D1 external-LLM pattern,
   bring-up/teardown, what is intentionally NOT here (edge, AAI gateway,
   artifacts).
6. PROOF.md with real outputs; branch `aperture/g3-bundle`; PM review before
   merge.

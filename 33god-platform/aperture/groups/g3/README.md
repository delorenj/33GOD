# Aperture G3 — Agent Fleet Runtime (v0.1)

Self-contained `god-g3`: a **containerized Hermes agent** (D2 image) plus the
standalone bus services — **heartbeat tick**, **lifecycle controller**, a
synthetic **NATS outbox/smoke adapter**, and self-contained **ntfy**. No G1/G2
dependency, no published host ports, **no AutomaticAI gateway content**.
**hook-hub and agent-hooks are explicitly deferred**, not faked:
[hook-hub/DEFERRED.md](hook-hub/DEFERRED.md) and
[agent-hooks/DEFERRED.md](agent-hooks/DEFERRED.md) record the crib and rationale.

This is an internal-use deployment artifact. [The charter](../../CHARTER.md)
remains binding. Nothing here is activated on Damian's machine; Rererere owns
that acceptance.

## Quick start (arm64 first; amd64 also supported)

Requires Docker Engine/Desktop with Compose v2+ and BuildKit; host Python 3 for
the smoke. Every external image's arm64 and amd64 manifest is verified in
[PROOF.md](PROOF.md). Only amd64 runtime execution was performed on this build
host; arm64 runtime acceptance remains with Rererere.

```bash
cd 33god-platform/aperture/groups/g3
cp .env.example .env                 # optional demo defaults, no real secrets
docker compose config -q
docker compose up -d --build         # builds 5 local images + pulls 3 external
docker compose ps -a
bash smoke/smoke.sh
```

Six long-running services become healthy (nats, outbox, heartbeat-tick,
lifecycle-controller, hermes-agent, ntfy). The optional `upstream` profile adds
`ntfy-upstream-gate`; the `tools` profile adds the in-network curl client the
smoke uses. `GOD_*` configuration is listed in [.env.example](.env.example).

## What the proof demonstrates (D3 scope, honestly bounded)

The containerized agent proves this closed loop, and the smoke verifies each
leg from the NATS stream (never an HTTP cache):

1. **heartbeat fires** — `heartbeat-tick` emits
   `bloodbank.system.heartbeat.received` every `GOD_G3_HEARTBEAT_INTERVAL`.
2. **a synthetic task envelope transitions** — `lifecycle-controller` runs the
   verbatim-cribbed reconciler over one synthetic envelope and publishes
   `bloodbank.lifecycle.status.updated` (`planned → active`, `PROGRESSING`).
3. **the agent publishes to NATS** — the `hermes-agent` container builds a
   valid `bloodbank.agent.invocation.start` command, validates it through the
   vendored plugin's own `decode_command`, constructs the real
   `bloodbank.agent.invocation.started` event with the plugin's
   `started_events`, and publishes it with a JetStream persistence ack.
4. **verifiable readback** — the outbox adapter's `GET /latest` and the direct
   `POST /publish` path both return the NATS sequence, and the smoke correlates
   `id`/`subject`/`sequence` on readback.

### D3 caveat — no Telegram/webhook ingress (this is G4)

The containerized agent **publishes** to NATS but does **not receive** the
Telegram webhook. Inbound messaging needs the edge router, which is a G4
concern. Nothing in this bundle claims interactive messaging ingress; a live
gateway deployment must add the edge and route webhook → command before a
human can talk to the agent through this stack.

## D1 — LLM providers are external and gateway-agnostic

There is **no AutomaticAI gateway content, account, or metered tier** in G3.
The agent's LLM wiring is deployment-owned and OpenAI-compatible:

| Variable | Meaning |
|---|---|
| `GOD_LLM_BASE_URL` | Any OpenAI-compatible base URL (empty default — no live calls) |
| `GOD_LLM_API_KEY` | The key for that endpoint (empty default) |
| `GOD_MODEL_ALIAS` | Model alias, `auto` by default |
| `GOD_AAI_BASE_URL` | Exists for parity but **empty default**; unused here |

The G3 proof performs **zero live LLM calls**; `GOD_LLM_API_KEY` stays empty.
The vendored `bloodbank-hermes-gateway` plugin carries no provider keys or
gateway URLs in the image.

## The D2 image — `Dockerfile.hermes`

`python:3.12-slim`, `uv pip install hermes-agent` from PyPI, then the vendored
Bloodbank plugin (`hermes/vendor/hermes-gateway`, cribbed verbatim from
`bloodbank/services/hermes-gateway/`) installed via pip so its
`hermes_agent.plugins → bloodbank-platform` entry point registers. The
`GOD_BLOODBANK_CONTEXT` build arg (default `hermes/vendor`) is the re-vendoring
override. Multi-arch: the base and every dependency publish `linux/arm64` and
`linux/amd64`. No secrets are baked in; runtime config is env-only.

The vendored plugin is copied into the bundle rather than referenced live from
the Bloodbank submodule so the build context stays narrow (the g3 directory),
keeping the image build fast and independent of a populated submodule checkout.

## The bus and proof boundary

`nats` is an owned, isolated JetStream broker (stream `G3_EVENTS`,
subjects `bloodbank.evt.>`), **not** G1's bus and **not** the host Bloodbank.
Every service publishes through the shared stdlib `nats_publish.py` (socket
primitives cribbed from `agent-hooks/core/nats_publish.py`, HPUB + PubAck
cribbed from `hook-hub/observations.py`, JetStream request/reply cribbed from
G2's outbox). `outbox` accepts only the fixed synthetic
`bloodbank.evt.aperture.smoke.g3` subject for direct HTTP publish; its
`GET /latest?subject=<s>` reads back any retained G3 event.

Connecting to G1 (D5) is **not** wired by default: `GOD_G1_BUS_ATTACH` names an
existing bus network, and joining it is a separately reviewed coupling — the
G3 stream and subjects are self-contained and attach is a documented override,
not a shipped link.

## Resource envelope

| Service | Hard memory cap |
|---|---:|
| hermes-agent (full Hermes + plugin) | 512 MiB |
| JetStream broker | 128 MiB |
| outbox / heartbeat / lifecycle / ntfy | 96 MiB each |
| ntfy-upstream-gate (optional) | 64 MiB |
| curl smoke client (on demand) | 64 MiB |

Steady-state caps total **1024 MiB** for the six core services. This is a
bounded small-demo budget, not a throughput promise.

## Isolation / teardown

Project `god-g3`, bridge `g3-internal`, and volumes `god-g3-nats-data`,
`god-g3-ntfy-cache`, `god-g3-ntfy-data` are all fresh and bundle-owned. No
external/adopted volumes, host home mounts, Docker socket, or published ports.

```bash
docker compose down                # preserves G3 stream + ntfy state
docker compose down -v             # ONLY for this disposable demo; deletes god-g3 data
```

## Provenance / intentionally NOT here

- **hook-hub** and **agent-hooks** deferred with crib + extraction contract
  (see their DEFERRED.md) — host agent-CLI / Hindsight / AAI-routing bound.
- **artifact-sidecar** and **artifact-vault-projector** are out of scope (D4).
- **No Telegram/Slack webhook ingress** (G4 edge), no interactive agent, no
  profile dispatch, no live LLM call, no provider key.
- **No AAI gateway** — no gateway endpoint, account, metered tier, or model
  routing anywhere in the bundle.
- The lifecycle controller ships the **pure reconciler** cribbed verbatim from
  `krebs/src/krebs/project_health/`; its asyncpg/Postgres persistence, structlog
  and krebs-execution worker are **not** shipped (see hook-hub/DEFERRED.md and
  the reconciler header for the extraction rationale).
- Image tags are explicit version/channel pins, not immutable digests. Recheck
  manifests after overriding them.

Independent PM review and arm64 real-deployment acceptance remain open.

# Aperture — productization and monetization of the 33GOD stack

> Project ID: `aperture` · Home: `33god-platform/aperture/` · Status: **active**
> Parent initiative: `I-6` (33GOD director level) · Dogfood target: Damien's machine
> Created: 2026-10-23 by operator order (voice, 2026-10-23)

## What this is

The 33GOD stack is a multi-year, deeply custom agentic development environment:
event bus (Bloodbank), audit trail (Candystore), agent fleet runtime, observability,
project tooling, voice pipeline (HeyMa/Wax/Vinyl), enrichment/memory, and the
orchestration layer (Momo/Krebs/Flume/Holocene). It is uniquely ours — the moat is
the integration, the custom patterns, and the measurable gains (auto-routing,
lifecycle, enrichment signals).

Aperture turns that moat into deployable product and revenue.

## Phase 1 — Eight domains, eight images, one stack

Ground truth: the [Ship Board](https://s3.delo.sh/projects/33god/a88a63b1-830a-5600-9475-23877bff0e0c/g33-ship-board/index.html)
(38 components, 8 non-overlapping groups, dependency-ordered, live dependency gating).
Source snapshot: `research/ship-board/` in this directory (self-contained HTML + data).

Each group becomes one Docker image + a compose bundle that brings the stack up:

| # | Group | Contents |
|---|-------|----------|
| G1 | Bloodbank core bus | NATS + Dapr + Apicurio + Candystore (+pg) |
| G2 | Integration plane | n8n (containerized) + workflows + curator + webhook adapters |
| G3 | Agent fleet runtime | hermes-gateway + hook-hub + lifecycle + ntfy |
| G4 | Observability | prometheus + grafana + loki + otel + exporters |
| G5 | Project tooling | PJangler + Skillex + CommonProject + mcp-hub |
| G6 | Voice pipeline | Wax + passes + Vinyl + transcription-service + Voxxy |
| G7 | Enrichment & memory | enricher + turn-enricher + cost-bridge + Hindsight |
| G8 | Orchestration & apps | Momo + Krebs + Flume + Pilot + Holocene |

Install order = dependency order: G1 → G2 → G3 → G4 → G5 → G6 → G7 → G8.
Ship board tracks wrapping/deployment progress per component with live gating.

**Dogfood rule:** deploy on Damien's machine, one group at a time, checked off on
the board. A group is "done" only when it runs on his hardware from its image.

## Phase 2 — Monetization avenues (to be explored, not yet chosen)

Operator seed list (from the founding voice memo, lightly edited):

1. **Lease agents** — keep the stack local, expose agents publicly (Cloudflare
   agents / Telegram bots) and charge per use or subscription.
2. **Sell the whole stack** — license + ship for self-deployment. Needs
   generalization: config surface, multi-tenant secrets, docs.
3. **Productize subsystems** — e.g. HeyMa (Wax + Vinyl) as a standalone voice
   pipeline product; other domains can follow the same pattern.
4. **Advertise & license parts** — publish the 33GOD ecosystem story, license
   individual domains (auto-router patterns, lifecycle contracts, enrichment).

Nothing is decided. Each avenue gets an evaluation note in `research/monetization/`
before any build work starts. The moat claims get backed by measurements we
already collect (LLM observability, crank logs, enrichment signals).

## Phase 3 — Generalization work (required by avenue 2/3)

- Config surface: every Jarad-specific path/endpoint/secret becomes an env var
  with a sane default (`GOD_*` namespace).
- Secrets: `.env.op` placeholder pattern stays; deployments carry their own keys.
- Namespacing: drop hard dependencies on `delo.sh`, Jarad's 1Password vault,
  Telegram identity, Plane instance (adapter or bundle).
- Docs: install guide per group; one "bring up the whole stack" runbook.

## Repository layout

```
33god-platform/aperture/
  README.md               ← this file — project charter
  research/
    ship-board/           ← live dashboard source (index.html + data.json)
    inventory-2026-10-23.md  ← the full sweep notes behind the board
    monetization/         ← one note per avenue (phase 2)
  (phase 1 build artifacts land here as work proceeds)
```

## Governance

- Owned by 33god-platform (control plane) — this directory is the project home.
- Parent tracks it as initiative **I-6**; no implementation epics in the parent.
- Ship board URL is the operator's live checkoff surface; keep `research/ship-board/`
  in sync with the published artifact.
- Secrets never land in this repo. `.env.op` refs only.

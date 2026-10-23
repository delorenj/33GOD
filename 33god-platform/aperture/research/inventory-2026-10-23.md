# Inventory sweep — 2026-10-23

Ground-truth sweep behind the Aperture ship board. Sources examined:

- `/home/delorenj/code/33GOD` top level + 10 git submodules (bloodbank,
  candystore, flume, hermes-agent-template, holocene, mcp-hub, momo, monitoring,
  pilot, pjangler)
- `docker ps` — 150 running containers on the host (+5 on aai-gateway)
- `systemctl --user` — 104 loaded service units, ~60 33GOD-relevant
- `bloodbank/compose/*.yml`, `bloodbank/services/*` (10 services),
  `bloodbank/integrations/*` (n8n nodes + workflows), `docs/event-naming.md`
  (45+ event types in the contract)
- `33god-platform/compose.yaml` + `components.yaml` (11 component manifests)
- `~/code/HeyMa` (wax: 11 passes + 2 pipelines; vinyl; n8n components;
  audio intake transports), `~/code/vinyl`, `~/code/skillex`, `~/code/CommonProject`
- n8n 2.18.4 local (port 5678) + task-runner; systemd units feeding it
  (curator-serve, curator-drain, pdf2md-serve)
- Hermes fleet: 41 profiles under `~/.hermes/profiles/`
- Monitoring compose: 13 services (prom, grafana, loki, alloy, otel, exporters,
  alertmanager, uptime-kuma, dockge, health-monitor)

## Key structural findings

1. **Bloodbank + Candystore are the true base layer** (G1) — everything else
   publishes to the bus. NATS + Dapr + Apicurio + Postgres.
2. **n8n is a host process today** (mise node 24, port 5678) and is a prereq for
   dev-journal, HeyMa workflows, and the Plane webhook — it must be containerized
   for G2 to ship.
3. **The 33god-platform compose projection already exists** as the validated
   local target (G1 + parts) — Aperture phase 1 grows this into per-group
   bundles rather than inventing a new shape.
4. **LLM-touching services are endpoint-agnostic already** (enricher,
   turn-enricher use OPENAI_COMPAT/JEV env vars) — generalization for other
   deployments is config, not code.
5. **Interlock cluster confirmed**: PJangler → Skillex (`@delorenj/skillex`
   0.1.2 npm) + CommonProject (copier template) → must ship together in G5.
6. **HeyMa = Wax + Vinyl + passes + n8n + transport + transcription** — the
   clearest standalone-product candidate (operator's own example).
7. **Plane is only needed for ticket facts** (webhook → board) — on other
   deployments it's an adapter decision, not a hard dep.
8. **Jarad-only layers, deliberately not shipped**: desktop orchestration
   (zellij Workspace, asm painters, deckard, orca, crank/zcrank), DeLoNET edge
   (traefik, tunnels, 1Password Connect), media/household stacks, personal
   memory banks.

## The 8 groups

G1 Bloodbank core bus → G2 Integration plane → G3 Agent fleet runtime →
G4 Observability → G5 Project tooling → G6 Voice pipeline → G7 Enrichment &
memory → G8 Orchestration & apps. Full component detail: `data.json` beside
this file; live view: the published ship board.

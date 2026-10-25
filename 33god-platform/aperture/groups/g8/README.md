# G8 — Orchestration + Apps plane

Portable Compose project `god-g8`, owned networks (`g8-bus`, `g8-internal`),
owned named volumes, **no published host ports**. The bundle is self-contained:
no monorepo checkout is needed to build or run it (candystore vendored with
recorded provenance — the identical G7 vendor; see
`candystore-src/PROVENANCE.md`).

G8 is the top of the Aperture stack: the orchestration + apps plane that
closes the loop **"Momo closes a real ticket with real code"** (the ACCEPTANCE
G8 gate). A ticket goes backlog → in_progress → done **closed BY EVIDENCE**
— a real git commit exists, real tests passed — with the human only
initiating, the entire event chain in candystore under ONE correlationid,
and a Holocene-shaped dashboard displaying the completed item.

## What runs

| Component | Cap | Purpose |
|---|---:|---|
| `bus` | 128 MiB | Owned JetStream broker (standalone mode; attach mode uses the external bus) |
| `nats-init` | — | One-shot stream init (G1 crib) |
| `candystore-postgres` | 256 MiB | Fresh pgvector Postgres for the envelope store |
| `candystore` | 192 MiB | Envelope store, built from vendored source (G7 vendor @ `767ebb5`) |
| `candystore-daprd` | 128 MiB | Dapr sidecar delivering `bloodbank.evt.>` to candystore — G8's OWN durable `g8-candystore-events` |
| `dapr-placement` | 64 MiB | Dapr rendezvous (sidecar requirement) |
| `board` | 96 MiB | REAL sandbox board, Plane state vocabulary, canonical ticket events |
| `code-worker` | 128 MiB | The real lane: real git commits + real test runs on a scratch repo |
| `momod` | 96 MiB | Momo-shaped orchestrator: WIP-lease discipline, evidence-gated cycle |
| `dashboard` | 96 MiB | Holocene-shaped surface: event-fed work-items projection + HTML view |

**Core memory caps sum: 1184 MiB (1.16 GiB).** Caps are ceilings against the
TARGET's Docker VM allocation, not host RAM; measured usage in PROOF.

## Start / verify / stop

```sh
cp .env.example .env          # defaults are standalone + degraded LLM
docker compose up -d --build --wait
bash smoke/smoke.sh           # DESTRUCTIVE: cold down -v → build → up → prove → down -v
docker compose down -v --remove-orphans
```

The smoke proves (exit 0 = pass): cold bring-up with EMPTY `GOD_LLM_*`
(degraded-not-crashed), a readiness canary FIRST (fresh dapr sidecars bind
durables 10-60s late), ONE full real cycle — ticket created through the
board, momod drives start → assign → code-worker lands a REAL commit with
REAL passing tests → deterministic review verifies the sha against the real
repo → board done with evidence — board state == repo evidence, dashboard
displays the completed item, the whole chain in candystore under ONE
correlationid, restart persistence, WIP-lease counters, rejection paths
(400s), and zero-residue teardown.

## The cycle (what actually happens)

```
you (or the gate): POST board /command {action: create, title: "..."}
  └─ board persists ticket (backlog) + publishes bloodbank.task.ticket.created
momod (holds WIP lease):
  ├─ board start ──────────── bloodbank.task.ticket.started
  ├─ assign (cmd stream) ──── bloodbank.cmd.task.ticket.assigned
  ├─ code-worker: writes module+test, RUNS unittest, git commit (REAL sha)
  │    ├─ publishes ───────── bloodbank.code.commit.landed (+ /landed evidence)
  │    └─ reply ───────────── bloodbank.rpy.task.ticket.completed
  ├─ review: sha resolves in the real repo (deterministic, no LLM)
  ├─ bloodbank.task.cycle.reviewed (commit + tests evidence)
  └─ board done(commit_sha, tests_passed) ─ bloodbank.task.ticket.completed
```

Every event carries the ticket's **lifecycle correlationid** — one UUID from
ticket-create to ticket-done. `momod` WIP-leases before driving (refuses if a
fresh lease is held by another driver; steals stale ones after TTL) — the
momo-wip-lock protocol containerized stdlib-only.

## Degraded mode is the default (client-owned LLM, zero AAI)

`GOD_LLM_BASE_URL` / `GOD_LLM_API_KEY` ship EMPTY. With them empty momod is
healthy and DEGRADED — `/healthz` returns `degraded: true` with
`"degraded: no reviewer LLM (GOD_LLM_BASE_URL and GOD_LLM_API_KEY empty);
deterministic evidence review only"`. The cycle NEVER depends on the LLM:
evidence gates it (commit exists, tests pass, sha resolves). With a
client-owned endpoint configured, `review_mode` flips to `llm-assisted` —
commentary only, never gating. Zero AAI content anywhere.

## Board honesty (sandbox vs Plane)

The board adapter is a REAL local SQLite board with **Plane's state
vocabulary** (backlog / in_progress / done, evidence-gated transitions).
It is NOT a Plane client: the real `px` CLI needs a real Plane instance and
credentials that never travel with a bundle (charter: secrets never travel;
standing rule 0: no host tools). The seam is config — `GOD_BOARD_KIND` —
and the real-Plane adapter is a documented deferral with an extraction
contract (DEFERRED.md §1). In the real system Plane ticket facts arrive as
Plane-webhook-owned `repo.task.*` events; the sandbox emits this bundle's
own `bloodbank.task.ticket.*` vocabulary — an explicit, honest boundary.

## Attach mode (join an existing bus)

```sh
# with G1 (or any BLOODBANK_* bus) running:
GOD_BUS_NATS_URL=nats://nats:4222 \
GOD_G1_BUS_NETWORK=g1-bus \
docker compose -f compose.yml -f compose.attach.yml up -d --wait
```

Only the transport services (`board`, `code-worker`, `momod`, `dashboard`,
`candystore-daprd`) join the external network; stores stay on `g8-internal`.
Proofs: `bash smoke/attach.sh` (the full real cycle across a throwaway
wire-identical external bus) and `bash smoke/coexist.sh` (a G1-shaped
incumbent consumer ALREADY consuming; every event reaches BOTH stores —
G8's own durables never split the incumbent's).

## In-network APIs (no host ports)

```sh
docker compose exec -T board python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8793/tickets').read().decode())"
```

- board: `:8793/healthz`, `:8793/tickets`, `:8793/ticket/<id>`,
  `POST :8793/command` (create|start|done)
- code-worker: `:8794/healthz`, `:8794/landed`, `:8794/git-log`,
  `:8794/workbench`
- momod: `:8795/healthz`, `:8795/cycles`
- dashboard: `:8796/` (HTML), `:8796/api/items`, `:8796/healthz`
- candystore query API: `http://candystore-app:3001/events`, `/events/<id>/raw`

Browser access to the dashboard on a headless host: SSH tunnel to the
bridge IP (documented pattern in g2/README) — this bundle publishes nothing.

## Intentionally NOT here

See `DEFERRED.md` for the full list with extraction contracts. Highlights:
no real Plane/`px` integration (sandbox board with same state vocabulary;
real-Plane adapter deferred), no real Momo/Krebs/Flume code vendored (momod
is Momo-SHAPED — the WIP-lease protocol and evidence-gating discipline, not
a copy of the interactive CLI), no real Holocene web app (dashboard is
Holocene-SHAPED — event-fed work-items surface), no client-owned LLM
endpoint proven live (degraded boundary proven + unit-pinned), no arm64
runtime execution (manifests verified; deployment gate).

## Acceptance gate (client-executable)

`accept/accept-g8.sh "your real small task title"` — you initiate ONE real
task, hands off, then verify board state, the commit, the dashboard item,
and the correlated chain yourself. Evidence lands in `accept/evidence/`
(local-only by the kit's own .gitignore). Proven on the build host: cold
stack, full pass (PROOF.md).

# G8 — Orchestration + Apps (build spec v0.1)

_Drafted 2026-10-24 by the delegated G8 worker (re-dispatch), following the
G3-SPEC pattern: decisions settled here BEFORE the build, from CHARTER.md,
ACCEPTANCE.md, ship-board g8, PILLARS.md, and the g1-g7 bundle conventions.
Worker builds to this spec; the PM review gate (independent spec review)
follows handback. Binding charter applies — no paid route, no secrets, no
production mutation, no Damian's-machine access from this bundle._

## Scope (ship board g8, honest subset)

The ship board names Momo + Krebs + Flume + Pilot + Holocene for G8. A
faithful v0.1 portable bundle cannot containerize five entire agent stacks
and stay honest — several of them are operator-desktop or host-CLI shaped
(ship board's own `notshipped` list separates the desktop layer). This
bundle delivers the **G8 gate contract** (ACCEPTANCE.md G8: "Momo closes a
real ticket with real code") as a self-contained portable Compose project
with REAL work in every lane:

- **momod** — Momo-shaped orchestration worker: WIP=1 lease discipline
  (momo-wip-lock protocol), ticket lifecycle driver emitting the full
  canonical event chain with ONE correlationid.
- **board** — board adapter: a REAL local sandbox board (SQLite) speaking
  Plane's state vocabulary (Backlog/In Progress/Done), with an honest
  documented boundary vs the real `px`/Plane (see "Board honesty").
- **code-worker** — the lane that produces a REAL commit: initializes a
  scratch git repo, writes a real file, runs real tests, commits with a
  verifiable SHA, reports evidence back through the bus.
- **dashboard** — Holocene-shaped apps surface: an in-network web app fed
  by candystore events that displays the completed work item with its
  commit and test evidence.
- **candystore + bus + dapr** — the plane's own envelope store and bus
  (g7 vendoring pattern: byte-copied candystore-src with PROVENANCE,
  g1-crib streams/init, g8-OWN durable names).

## Decisions (settled; charter/G8-gate constraints)

- **D1 — Adapter for the board (PILLARS #4).** The real `px` CLI needs a
  real Plane instance + credentials; shipping those would violate
  secrets-never-travel and client-executable rule 0. The bundle ships a
  local sandbox board adapter implementing the SAME state vocabulary and
  command shape (create → start → done with evidence). The seam to a real
  Plane/px is `GOD_BOARD_KIND=plane|sandbox` (config, not code); `plane`
  is documented-deferred with an extraction contract.
- **D2 — code-worker is REAL, not simulated.** The G8 gate demands "closed
  BY EVIDENCE (commit exists, tests pass)". The code-worker lane does
  actual `git init/commit` in a scratch repo inside its own container
  volume, actually runs a real test file with python's unittest, and the
  smoke verifies the commit SHA exists, tests passed, and board state ==
  git log. No mock, no fake stdout.
- **D3 — WIP-lease discipline is in-bundle.** momod uses the
  momo-wip-lock.py protocol (acquire/refresh/release with TTL + heartbeat,
  steal-after-expiry) adapted to stdlib-only container use. Only
  lease-holder drives ticket transitions — the coexistence property G8's
  own gate ("the human only initiates") exercises.
- **D4 — Zero AAI, degraded-not-crashed LLM surface.** The orchestrator's
  optional "reviewer LLM" is client-owned: `GOD_LLM_BASE_URL` /
  `GOD_LLM_API_KEY` ship EMPTY; with them empty momod runs
  deterministic-evidence review (diff exists, tests green, sha matches)
  and is healthy + degraded in healthz, exactly the G7 boundary pattern.
- **D5 — Own durables, attach overlay, g1-crib bus.** JetStream durables
  are `g8-*` (g8-momod, g8-board-adapter, g8-dashboard); NEVER
  candystore-events/g7-candystore-events (shared durables split events
  between stores). Attach overlay `compose.attach.yml` joins god-g8's
  transport services to the external `g1-bus` network, with a
  coexistence proof against a G1-shaped incumbent consumer.
- **D6 — stdlib-only Python.** Every authored service is
  python:3.12-alpine + stdlib; bus via the g7 jsclient.py copied
  BYTE-IDENTICAL (CONNECT headers:true, batch=1 pulls, publish-ack). No
  pip installs inside authored images.
- **D7 — Event types.** G8's own domain vocabulary, canonical 4-token
  type / 5-token subject per bloodbank-envelope.md:
  `bloodbank.task.ticket.<created|started|completed|...>` etc. — see
  `events.md` in the bundle. `repo.task.*`/`repo.board.*` Plane-webhook
  facts are NOT emitted by this bundle (they are Plane-owned in the real
  system; the sandbox board emits `bloodbank.task.ticket.*` under its own
  producer identity, documented as the sandbox boundary).

## Acceptance (client-executable, non-destructive)

Standing rules 0-4 from ACCEPTANCE.md apply. `accept/accept-g8.sh` drives
ONE full real cycle with the human only initiating: creates a real small
task, momod drives it, code-worker lands a real commit + passing tests,
board reaches done with evidence, dashboard displays it, candystore shows
the whole chain under one correlationid. Evidence dir local-only
(.gitignored). Gate kit proven on the build host (cold stack, full pass).

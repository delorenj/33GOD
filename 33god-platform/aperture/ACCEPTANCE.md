# Aperture acceptance criteria — real-task dogfood gates (v1.1)

_Operator directive 2026-10-23: each group G1–G8 gates on a REAL task that
dogfoods the stack, not synthetic pings. Criteria are binary, evidence-
backed, and run wherever the group is deployed. Standing rule 0 makes every
gate CLIENT-EXECUTABLE: completable by Damian on the deployed system ALONE —
no upstream monorepo, no host tools (`px`/`pj`), no PM-host board or
candystore. Real data is generated locally (typed by the client or measured
from his own machine). PILLARS: evidence > status; a claim without
repo/bus evidence is not acceptance._

## Standing rules (apply to every group)

0. **Client-executable** — every gate must be completable BY THE CLIENT on
   the deployed system ALONE: no upstream monorepo, no host tools (`px`,
   `pj`), no PM-host Plane board, no PM-host candystore/Hindsight. Real data
   is generated locally (typed by the client or measured from their own
   machine). If a gate needs credentials (LLM, external SaaS), they are
   deployment-owned and optional-stage unless the gate says otherwise.
1. **Canonical envelope or it didn't happen** — every event must satisfy the
   4-token `type` / 5-token `subject` / `kind` / `actor` / `ordering_key`
   contract (bloodbank/docs/event-naming.md). Cross-group acceptance signal
   is the **downstream candystore readback**, never the publisher's ack.
2. **Persistence through restart** — the accepted evidence must survive a
   full `down/up` cycle of the producing group.
3. **No production harm** — host services, Damian's 24 containers, and
   existing n8n/Plane untouched (verified before/after).
4. **Evidence bundle** — each gate produces: trimmed command output, event
   ids, and (where UI) a screenshot, filed under `aperture/acceptance/`.

---

## G1 — Bloodbank Core Bus: "the founder's decision is on the record"

**Real task (client-executable)**: Damian records a REAL decision he made
that day — his own words, typed by him (e.g. "we'll price the starter tier
at $49") — plus one real machine-measured fact from his own Studio (e.g.
current `docker ps` container count or disk free), published as a canonical
`bloodbank.studio.decision.recorded` event via the provided publish script.

- **PASS** when all of:
  - [ ] candystore `GET /events/<id>/raw` returns his envelope (his exact
        words in `data.decision`, machine fact in `data.context`)
  - [ ] candystore free-text search for a word FROM HIS OWN SENTENCE finds
        it (`?q=<word>`)
  - [ ] a deliberately malformed envelope he also sends lands in dead-letter
        with a reason string (not silently dropped)
  - [ ] after full stack restart (`down`/`up -d`), the search STILL finds it
- *Why real*: the data exists only on his deployment, authored by him; the
  search-and-survive path is the feature real agents consume daily.
- Build-host variant (PM): same gate with a real monorepo commit as the
  payload.

## G2 — Integration Plane: "the client ships his first workflow"

**Real task (client-executable)**: Damian builds a REAL workflow HIMSELF in
the deployed n8n UI — Form trigger ("note" + "mood" fields he designs) →
publish to the bus with canonical envelope (template code node provided) →
candystore readback. No upstream, no Plane, nothing of ours.

- **PASS** when:
  - [ ] he submits his own form once; the event appears in candystore
        `/events/<id>/raw` ≤60s later with his exact form values
  - [ ] the webhook-rejection path still holds on HIS build (missing auth
        header → 401) — he tests it himself with curl
  - [ ] free-text search finds the event by a word from his form input
  - [ ] n8n shows the execution as succeeded; killing the workflow
        (deactivate) stops events — no ghost deliveries
- *Why real*: proves the client can BUILD on the platform unaided — the
  actual product question for G2. Building it is the test.
- Build-host variant (PM): real Plane ticket via `px` → event.

## G3 — Agent Fleet Runtime: "the phone buzzes from the Studio"

**Real task (client-executable)**: the Studio's own fleet does a real
scheduled job and tells Damian about it.

- Stage 1 (no external creds needed): heartbeat-tick fires →
  lifecycle-controller transitions a real item DAMIAN creates (small client
  script: "watch this project") → ntfy push with the transition lands on
  HIS phone (he subscribes to the topic in the ntfy app).
- Stage 2 (optional, his LLM key if he wants it): agent turn summarizes the
  last 24h of heartbeats → push.
- **PASS when stage 1 holds**:
  - [ ] real ntfy push on-device (screenshot filed)
  - [ ] the transition chain (command → started → result) is a complete
        linked correlationid chain in candystore
  - [ ] the heartbeat stream shows ≥1 tick/interval for the past hour
        (spot-check count)
  - [ ] stopping the heartbeat container pauses ticks; restart resumes with
        sequence continuity
- *Why real*: his schedule, his item, his phone — no upstream involvement.

## G4 — Observability: "the dead container pages you"

**Real task**: kill a real service and get paged; then watch it heal.

- **PASS** when:
  - [ ] `docker stop` on a real G1/G3 container → Prometheus alert fires →
        Alertmanager → ntfy push received on-device
  - [ ] Grafana dashboard shows the gap + restart in the real timeline
        (Loki logs present for the incident window)
  - [ ] alert RESOLVES when the container returns (no stuck firing state)
  - [ ] the whole stack monitors ITSELF (self-scrape), no external dependency
- *Why real*: chaos on real services; the page-to-phone path is the product.

## G5 — Project Tooling: "a real project born on the stack"

**Real task**: scaffold a REAL new project end-to-end on the deployed tooling
— the Aperture acceptance-evidence project itself.

- **PASS** when:
  - [ ] `pj` creates a real project from CommonProject template + registers
        it (manifest committed to a real repo)
  - [ ] a Skillex skill installs and EXECUTES in that project (real run,
        real output)
  - [ ] the project notebook takes a note and serves it back
  - [ ] the whole flow emits its events to the bus (attached mode)
- *Why real*: this exact acceptance-evidence repo becomes the dogfood.

## G6 — Voice Pipeline: "the real recording becomes a real task"

**Real task**: feed a REAL audio recording (actual voice memo / meeting
excerpt, ≥60s, operator-provided) through intake → transcription → Wax
enrichment → event.

- **PASS** when:
  - [ ] transcript contains ≥3 verbatim phrases from the recording
        (spot-check list recorded beforehand in the evidence bundle)
  - [ ] enrichment produces a real summary/todo extraction a human agrees
        matches the content
  - [ ] `bloodbank.voice.transcript.completed` in candystore with the
        transcript id linked
  - [ ] round-trip latency recorded (dogfood-grade, not benchmarked)
- *Why real*: real audio, real words, human-verified content match.

## G7 — Enrichment + Memory: "the stack remembers what happened"

**Real task**: after G1–G6 have produced REAL events, enrich them and recall
them.

- **PASS** when:
  - [ ] a real raw event batch gets titles/summaries via real LLM calls
        through the external-LLM pattern (spot-check 5 by hand)
  - [ ] cost-bridge records real token/cost rows for those calls
  - [ ] hindsight recall answers a question answerable ONLY from this
        deployment's stored history (e.g. "which ticket did we create in
        the G2 gate, and what was its title?")
  - [ ] zero enrichment calls bypass the declared LLM endpoint (traffic log)
- *Why real*: memory of real work, not fixtures; recall is checked against
  ground truth the operator knows.

## G8 — Orchestration + Apps: "Momo closes a real ticket with real code"

**Real task**: one full real cycle on the deployed stack — a real ticket
goes backlog → done, closed BY EVIDENCE (commit exists, tests pass), with
the human only initiating.

- **PASS** when:
  - [ ] a real small task (e.g. "add one acceptance doc page") is created,
        delegated, implemented (real commit), and reviewed by the deployed
        orchestrator pair
  - [ ] board state matches repo evidence (`px` ticket state == git log)
  - [ ] the Holocene app (or dashboard) displays the completed work item
  - [ ] the entire cycle's event chain is in candystore with one linked
        correlationid from ticket-create to ticket-done
- *Why real*: this is the whole company doing its actual job, once, unaided.

---

## Gate order & current state (2026-10-23)

- G1: synthetic proof done (10/10 smoke + Studio arm64); **decision-record
  gate pending** (replaces ping-shaped evidence for final acceptance).
- G2: canonical + seam proven; **client-builds-workflow gate pending**.
- G3: merged, build-host proven; **phone-buzz stage-1 gate pending** (needs
  ntfy topic subscribe on Damian's device; LLM stage optional/his key).
- G4–G8: unbuilt; gates above are the contract for their specs.

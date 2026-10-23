# Aperture acceptance criteria — real-task dogfood gates (v1)

_Operator directive 2026-10-23: each group G1–G8 gates on a REAL task that
dogfoods the stack, not synthetic pings. Criteria below are binary, evidence-
backed, and run wherever the group is deployed (build host first, Damian's
Studio for integration acceptance). PILLARS: evidence > status; a claim
without repo/bus evidence is not acceptance._

## Standing rules (apply to every group)

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

## G1 — Bloodbank Core Bus: "the real commit in the audit trail"

**Real task**: take a REAL commit from this monorepo (actual `git log` data)
and make it queryable in the deployed candystore.

- Publish the real commit (sha, author, message, files-changed count) as a
  canonical `bloodbank.repo.commit.observed` event via NATS.
- **PASS** when all of:
  - [ ] candystore `GET /events/<id>/raw` returns the envelope (real sha in `data`)
  - [ ] candystore free-text search (`?q=<first-8-of-sha>`) finds it
  - [ ] a deliberately malformed envelope lands in dead-letter with a reason
        string (not silently dropped, not retried forever)
  - [ ] after full stack restart, the search still finds it
- *Why real*: uses actual repo history; the search path is the feature real
  agents consume daily (`candystore context latest` depends on it).

## G2 — Integration Plane: "the real Plane ticket becomes an event"

**Real task**: a REAL ticket created on the 33GOD Plane board (via `px`)
shows up in candystore as a canonical event — no synthetic webhook input.

- Deployment-owned Plane credentials (token env, never shipped in bundle);
  n8n workflow: schedule trigger → Plane API list-tickets → publish
  `bloodbank.repo.task.observed` per new ticket → bus (attached mode).
- **PASS** when:
  - [ ] a ticket created by `px task create` (title chosen at test time,
        recorded in the evidence) appears in candystore ≤60s later
  - [ ] `data` matches Plane truth (title, id) — cross-checked via `px`
  - [ ] the event is visible in the SHARED candystore when attached (not
        just G2's local stream)
  - [ ] removing/rotating the Plane token produces a 401 error event or
        workflow failure visible in n8n — no silent no-op
- *Why real*: Plane→Bloodbank is the flagship integration this group exists
  to ship; this is it, live, with real credentials.

## G3 — Agent Fleet Runtime: "the phone buzzes from the Studio"

**Real task**: the containerized fleet runs a REAL agent turn on a schedule
and a human receives the result as a push notification.

- heartbeat-tick fires → lifecycle-controller transitions a real tracked
  item → hermes-agent executes one real turn (external LLM creds, real
  prompt: "summarize today's heartbeat stream and name anything stalled")
  → result posted to ntfy → **notification received on Damian's phone**
  (ntfy app subscribed to the topic).
- **PASS** when:
  - [ ] a real ntfy push arrives on-device (screenshot in evidence bundle)
  - [ ] the agent's summary references ACTUAL heartbeat data from the last
        24h (spot-check numbers against the stream)
  - [ ] the invocation (command → started → result) is a complete causal
        chain in candystore (correlationid linked)
  - [ ] LLM call went through the external-LLM pattern (zero AAI traffic)
- *Why real*: it's the fleet doing fleet work end-to-end — schedule, LLM,
  bus, notification, human.

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

- G1: synthetic proof done (10/10 smoke + Studio arm64); **real-commit gate
  pending** — replaces ping-shaped evidence for final acceptance.
- G2: canonical + seam proven; **real-Plane-ticket gate pending** (needs
  deployment-owned Plane token + schedule workflow on Studio).
- G3: merged, build-host proven; **phone-buzz gate pending** (needs ntfy
  topic subscribe on Damian's device + external LLM creds).
- G4–G8: unbuilt; gates above are the contract for their specs.

Integration acceptance for the Damian deployment = each group's real-task
gate passing ON THE STUDIO with evidence filed under `aperture/acceptance/`.

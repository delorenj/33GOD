---
title: '33GOD initiatives (integration work that spans children)'
governed_by: 'director-rule-plan.md'
created: '2026-09-29'
---

<!-- The parent holds outcomes that span children, never work inside one.
     NOT epics.md: keys here are I-n / I-n.m on purpose. bmad-loop only parses
     `epic-<digits>` and `<digits>-<digits>-<slug>`, so nothing in this file can be
     dispatched as code. Do not paste these into a sprint-status.yaml.
     Refer to child work only as `<project>:<key>` or a ticket ref (FLUME-12).
     Status is derived from the boards and events, never typed here. -->

# Initiatives

## I-1 Flume agent rollout throughout the system

**Outcome.** Every pjangler-registered project has a declared post held by a named
agent, the workforce is visible on the bus and in `/hq`, and a named specialist can be
invoked with no repo present.
**Owner:** `33god` (Grolf). Implementation is owned by the children named in each
story's delegations. The full story list (I-1.1 to I-1.8) is in
`director-rule-plan.md`; only the two below are authored so far.

### I-1.1 Flume and PJangler seam

```yaml
owner_project: 33god
delegations:
  - owner_project: pjangler
    request: pj audit and flume review agree on the same repo
  - owner_project: flume
    request: roster derives every PM post from the pjangler registry
depends_on: []
```

**Seam acceptance criteria**

- For any project registered in pjangler, `flume roster` shows its PM post with zero
  hand-maintained fields.
- `pj audit` and `flume review` agree on the same repo.
- The two binaries share only the handbook contract; neither imports the other.

**Seam evidence (executable).** Run `pj list` and `flume roster --json`; diff the
project ids and post states. Run `pj audit <repo>` and `flume review <repo>` for one
repo and compare findings on the fields both report.

### I-1.6 Company projection sourced from Flume

```yaml
owner_project: 33god
delegations:
  - owner_project: flume
    request: expose one company snapshot with a freshness envelope
  - owner_project: holocene
    request: build the /hq company view from that snapshot
depends_on: [I-1.1]
```

Resolves the transport decision deferred in the architecture spine (AD-5): how Flume
publishes the company projection, and retiring `org.yaml` as the hierarchy source. It
is the seam half of the former Story 1.3.

**Seam acceptance criteria**

- The `/hq` company view is built from one Flume snapshot carrying a freshness
  envelope.
- Hierarchy is no longer read from `org.yaml`.
- A change in Flume appears in `/hq` within the declared maximum age.

**Seam evidence (executable).** Change a post in Flume; measure the time until the
`/hq` API reflects it; assert it is under the declared maximum age and that
`org.yaml` is not opened during the request.

## I-2 Holocene Auto walking skeleton

**Outcome.** On Jarad's factory Honda Civic Si 2026 AAOS Google built-in system,
activity from multiple harnesses is available through one normalized view; the
driving voice interface routes a confirmed instruction to one supported
conversation, its real reply is heard through Voxxy, and an explicit broadcast
fact reaches multiple subscribers.
The complete conversational loop requires no screen reads or taps while driving;
detailed event browsing remains parked-only.

**Owner:** `33god` for integrated acceptance; `holocene` for the operator-facing
product. The cross-project seam contract is
[Holocene Auto](../specs/spec-holocene-auto/SPEC.md); its companions define current
capabilities, car modes, gaps, and bounded demonstration evidence. Child PMs own
all implementation stories. HOLOC-9 supplies the accepted emulator diagnostic
baseline; the next approved seams are final-answer publication (I-2.2) and isolated
real-speech evidence (I-2.3), not the full integrated driving product.

### I-2.1 Observability, voice, and conversation seams

```yaml
owner_project: 33god
delegations:
  - owner_project: holocene
    request: prove Honda-AAOS emulator feasibility and a legitimate category, installation, and driving-voice path before the integrated surface
    ticket_ref: HOLOC-9
  - owner_project: bb
    owner_component: bloodbank
    request: support schema-valid exact-conversation intent and correlated execution evidence without route substitution
    ticket_ref: pending
  - owner_project: candystore
    request: supply durable correlated event history and reconnect evidence for the car surface
    ticket_ref: pending
  - owner_project: transcription-queue
    owner_component: heyma
    binding_state: requires-reconciliation
    request: reconcile the moved checkout binding and provide schema-aligned final-transcript voice ingress usable from the head unit
    ticket_ref: pending
  - owner_project: infra
    request: verify the existing ASR bridge as a bounded head-unit recognition dependency
    ticket_ref: pending
  - owner_project: pending
    owner_component: hermes-fleet
    request: resolve the runtime-owning project and prove declared conversation continuity with resolved-session evidence
    ticket_ref: pending
  - owner_project: voxxy
    request: provide correlated short speech output with explicit synthesis and playback distinctions
    ticket_ref: pending
depends_on: []
```

**Seam acceptance criteria**

- Two harnesses are observable independently of Deckard panes with identity and
  freshness preserved.
- One confirmed utterance reaches the selected supported conversation and yields
  correlated lifecycle evidence plus an audible response; unsupported routes are
  read-only, never silently redirected.
- A confirmed typed broadcast fact reaches two passive subscribers and durable
  history; publication does not claim subscriber execution.
- Disconnect/reconnect preserves the demonstration history and does not duplicate
  the instruction; Driving/Unknown hides detailed activity but supports the
  validated hands-free selection, instruction, broadcast, reply, and cancel loop.
- First-release driving acceptance requires no display reads or taps; stationary
  staging alone is not final proof of movement-dependent hardware behavior.
- Honda-emulator feasibility, category/testing-route evidence, actual-car
  installation, and driving proof are distinct; host UX restrictions are obeyed
  and actual-vehicle ADB is never an installation dependency.

**Seam evidence.** Execute the staged acceptance sequence and collect canonical
event IDs, declared conversation and resolved-session identifiers, correlation
IDs, receipt and answer readback, device/activation proof, audio playback,
reconnect/broadcast observations, and non-screen interaction evidence as specified
in the contract's `acceptance.md` companion. APK installability alone is not
integration completion.

### I-2.2 Durable final assistant answers

```yaml
owner_project: 33god
delegations:
  - owner_project: bb
    owner_component: bloodbank
    request: publish a final assistant answer with exact invocation and conversation lineage, durable replay, and no repeated execution
    ticket_ref: BB-30
depends_on: []
related_to: [33GOD-16]
```

**Seam acceptance criteria**

- A valid targeted invocation producing a nonempty final assistant answer yields
  one schema-valid message fact, explicitly distinguishable from processing
  completion, commentary, tool output, history, and reasoning.
- Command, target/profile, correlation/causation, logical thread/turn, and native
  session/turn identities remain distinct and traceable. Concurrent or delegated
  turns cannot cross-wire the parent answer.
- Captured results and immutable event identity/body are persisted before publish;
  command acknowledgement follows acknowledged answer and terminal publication.
  Publication/restart/redelivery replays stored facts without rerunning execution.
  Pre-capture ambiguity is disclosed, not called global exactly-once delivery.
- Schema compatibility and deterministic failure/replay tests prove the contract;
  later authorized live verification proves durable Candystore arrival.

**Seam evidence.** Canonical schema validation, exact command/turn/answer identifiers,
restart/publication-failure replay tests, consumer deduplication, and an authorized
live answer row. No ASR, TTS, mobile authentication, or arbitrary terminal resume is
part of this first authority-owner request.

### I-2.3 Isolated real speech and diagnostic playback

```yaml
owner_project: 33god
delegations:
  - owner_project: holocene
    request: prove a known isolated speech waveform through the emulator microphone, real final recognition, local audible acknowledgement, and bounded cancellation
    ticket_ref: HOLOC-10
depends_on: []
prerequisites: [holocene:HOLOC-9]
```

**Seam acceptance criteria**

- A known short synthetic/prerecorded phrase enters the Android microphone path,
  with waveform provenance, sample statistics, duration, and a silence control.
  Canned text written into transcript state cannot satisfy recognition.
- The current recognizer produces a nonempty final transcript and timing/callback
  evidence; unsupported, no-match, or network failure is a reproduced blocker,
  never replaced by a fixture transcript.
- Output derived from that final transcript is audibly rendered with recorded
  guest-output evidence and engine/asset identity. Platform-local diagnostic
  playback is labeled as such, not Vox synthesis or a real agent reply.
- Capture/playback cancellation, focus/resource release, and late-callback handling
  work under permitted host UX. Screen and simulated-key tests do not claim Honda
  steering-wheel, spoken stop, or non-screen driving support.
- No room microphone recording, assistant-default change, Play upload, actual-car
  modification, agent/broadcast dispatch, or direct engine/broker bypass occurs.
  CAP-8 and the eventual live Vox/agent loop remain required and unfulfilled.

**Seam evidence.** Input and output waveform identifiers/statistics, actual ASR
provider/support/final callbacks, transcript and latency, cancellation/focus/host
behavior, and explicit diagnostic-versus-live boundaries. This independent audio
slice may progress alongside I-2.2; shared runtime activation is serialized later.

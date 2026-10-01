---
id: SPEC-holocene-auto
companions:
  - brownfield.md
  - car-modes.md
  - acceptance.md
sources: []
---

# Holocene Auto

## Why

Jarad needs a car-based Holocene surface for following agentic development and conversing with the right agents while driving, without holding an iPad or reading terminals. His head unit installs Android apps directly. A tangible walking skeleton must prove active-agent awareness, normalized activity, spoken intent, correctly targeted commands, broadcasts, and audible responses. Driving usability is a first-release requirement; a parked-only demo is not the finished product. Deckard supplies terminal context but does not define the universe of agents.

## Capabilities

- **CAP-1**
  - **intent:** Jarad can identify active agents across harnesses and distinguish recent work, requests for attention, and unknown state.
  - **success:** All evidenced active runtimes/conversations in the declared coverage appear independently of Deckard panes; a minimum two-harness demonstration preserves stable references, project context, last observation, and explicit coverage/stale/unavailable/unknown state. Driving mode exposes the same information through concise requested speech.

- **CAP-2**
  - **intent:** Jarad can select an agent conversation and understand its activity through consistent presentation.
  - **success:** One normalized renderer handles lifecycle, tool, and message facts, preserves event identity/provenance across replay, and has an unknown-type fallback. Parked mode offers bounded detail; driving mode offers short spoken summaries without requiring screen reading. Deckard context appears only through explicit associations.

- **CAP-3**
  - **intent:** Jarad can use one spoken ingress to select a destination, request status, or compose an instruction without touching the screen while driving.
  - **success:** A proven hands-free activation path yields a final transcript, bounded clarification, and spoken confirmation of interpreted intent and frozen destination. Cancellation publishes no instruction. Screen PTT may supplement parked use but cannot satisfy driving acceptance.

- **CAP-4**
  - **intent:** Jarad can send a confirmed instruction to the selected agent conversation and continue that conversation.
  - **success:** One supported conversation receives a schema-valid targeted command and emits correlated lifecycle and answer evidence; a follow-up proves continuity. Unsupported targets remain read-only. Routing never silently substitutes another agent, native session, logical thread, or newly created conversation.

- **CAP-5**
  - **intent:** Jarad can explicitly publish a broadcast fact for multiple interested consumers through the same voice interface.
  - **success:** A spoken, confirmed named/typed broadcast reaches two demonstration subscribers and durable history without screen interaction. Publication is distinguished from consumer execution; ambiguous intent never becomes a broadcast.

- **CAP-6**
  - **intent:** Jarad can hear concise status, clarification, and agent responses and maintain a spoken conversation.
  - **success:** A real correlated reply is spoken through Voxxy on the head unit, with immediate spoken stop/mute and no microphone feedback loop. Engine identity is recorded; audio failure preserves the text response and never repeats the agent command.

- **CAP-7**
  - **intent:** Jarad can understand instruction progress and recover from lost connectivity without duplicate work.
  - **success:** Submission, gateway dispatch, processing outcome, and answer availability are distinct evidence-backed states, including rejected/unknown. Reconnection preserves identities and readback; drafts never auto-send; retransmission requires proven consumer deduplication.

- **CAP-8**
  - **intent:** Jarad can use the complete first-release conversational loop while driving without reading a terminal or operating a touch workflow.
  - **success:** Driving/Unknown modes support validated hands-free selection, summary, clarification, confirmation, instruction, broadcast, response, and cancel. They suppress detailed timelines, editing, and complex touch controls. Acceptance demonstrates zero required screen reads/taps; parked-only functionality does not satisfy this capability.

## Constraints

- The confirmed first target is a standalone Android head-unit APK, not projected Android Auto or Android Automotive distribution. Device and interaction gates are in `car-modes.md`.
- This is a cross-project seam contract, not a root implementation spec. Holocene owns the surface/composition; Bloodbank owns schemas and command dispatch; Candystore owns durable history; HeyMa owns voice ingress with infra's existing ASR bridge as a candidate; Voxxy owns synthesis; the runtime owner owns conversation continuity; Deckard is optional enrichment. Child PMs own code and implementation planning.
- Bloodbank is the normalized behavioral spine: facts use `bloodbank.evt.*`, targeted intent uses `bloodbank.cmd.*`, and execution emits lifecycle facts. Existing read APIs are read-side seams, not another command lane. ASR/TTS HTTP implementations stay behind owned bus adapters.
- The APK uses an authenticated Holocene boundary, not broker credentials, raw registries, terminal-keystroke injection, or unrestricted service credentials. Server-side secrets remain vault references or process environment values.
- Employee identity, harness/runtime scope, native session, logical conversation thread, event correlation, and optional pane location are distinct. Source identifiers survive projection; labels and repository names are not routing keys.
- Observation does not imply write support. A destination must declare its exact supported conversation route, continuity guarantees, and reply capability. Missing support disables intervention with an explanation; a native session ID cannot masquerade as a Bloodbank `thread_id`.
- Voice is half-duplex: activate, capture, transcribe, clarify, confirm, dispatch, await, speak. A bounded activation listener may be necessary; always-listening general conversation and full-duplex audio are not required. ASR is separate from Vox TTS.
- Driving/Unknown modes never depend on visual browsing or touch confirmations. Unknown motion state stays visually restrictive but does not remove a validated voice path. Loss of microphone/activation/audio support explicitly blocks driving readiness.
- Hardware and stationary interaction tests precede motion-dependent verification; they are not a substitute for first-release driving usability or a claim of certification. Missing vehicle data or zero GPS speed never automatically unlocks Parked detail.
- New mobile ingress, reply publication, session joins, schema alignment, bus voice adapters, receipt semantics, and retry guarantees require owning-project acceptance. `brownfield.md` identifies the current gaps rather than presenting them as deployed features.

## Non-goals

- A full mobile Holocene clone, terminal mirror, source editor, or visual code-review workflow in the car.
- Arbitrary spoken shell execution, implicit broadcast, or universal first-release write adapters for every observed harness.
- Android Auto category workarounds, public-store publication, or Android Automotive certification.
- Always-listening general conversation, full-duplex audio, offline execution, or automatic replay of pending instructions.
- A new workforce registry, ticket state machine, event store, broker, or general-purpose orchestrator.

## Success signal

On the actual head unit in its driving interaction profile, Jarad can activate by voice or an equivalent proven non-screen entrypoint, hear activity from two harnesses, select one supported conversation, dictate and verbally confirm an instruction, hear the real correlated reply through Voxxy, and continue the conversation without reading or tapping the screen. An explicit spoken broadcast reaches two passive subscribers; disconnect/reconnect preserves evidence and does not repeat the instruction. Detailed event browsing remains parked-only. `acceptance.md` separates stationary proof, motion-dependent hardware verification, and first-release driving readiness.

## Assumptions

- Native Android is the recommended first client; Holocene chooses packaging and internal stack.
- The first writable target will be a dedicated, explicitly established Bloodbank conversation with one fleet agent; interactive CLI sessions remain observable until their owning adapters prove exact routing.
- The first broadcast is a non-operational note with two passive subscribers; broader control expands through a bounded intent catalog.
- Half-duplex voice, default `rick`, and prototype latency budgets are proposed defaults. The user confirmed direct Android installation, the Holocene Auto name/scope, driving usability, and planning publication—not these individual implementation choices.

## Open Questions

- What head-unit make/model, Android/API version, install path, mic/audio-focus behavior, connectivity, and parked/moving signals are available?
- Which supported non-screen activation mechanism works reliably: bounded wake word, hardware voice/PTT integration, or an existing voice-assistant entrypoint?
- Which agent and declared conversation should prove CAP-4, and which broadcast fact and two subscribers should prove CAP-5?
- Which ASR path meets the measured short-utterance budget, and is VoxCPM specifically required or is Voxxy's current selected engine acceptable?

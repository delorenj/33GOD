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

Jarad needs a native car-based Holocene surface for following agentic development and conversing with the right agents while driving, without holding an iPad or reading terminals. His target is the factory Google built-in system in a 2026 Honda Civic Si, running Android Automotive OS (AAOS), not an unrestricted aftermarket Android tablet. A tangible walking skeleton must prove active-agent awareness, normalized activity, spoken intent, correctly targeted commands, broadcasts, and audible responses. Driving usability is a first-release requirement; a parked-only demo is not the finished product. Deckard supplies terminal context but does not define the universe of agents.

## Capabilities

- **CAP-1**
  - **intent:** Jarad can identify active agents across harnesses and distinguish recent work, requests for attention, and unknown state.
  - **success:** All evidenced active runtimes/conversations in declared coverage appear independently of Deckard panes; a minimum two-harness demonstration preserves stable references, project context, observation time, and explicit coverage/stale/unavailable/unknown state. Driving use exposes the same information through concise requested speech.

- **CAP-2**
  - **intent:** Jarad can select an agent conversation and understand its activity through consistent presentation.
  - **success:** One normalized renderer handles lifecycle, tool, and message facts with canonical identity/provenance, replay deduplication, and unknown-type fallback. Parked use offers bounded detail where permitted; driving use offers short spoken summaries without screen reading. Deckard context requires explicit associations.

- **CAP-3**
  - **intent:** Jarad can use one spoken ingress to select a destination, request status, or compose an instruction without touching the screen while driving.
  - **success:** A proven non-screen activation path yields a final transcript, bounded clarification, and spoken confirmation of interpreted intent and frozen destination. Cancellation publishes no instruction. Screen PTT may supplement parked use but cannot satisfy driving acceptance.

- **CAP-4**
  - **intent:** Jarad can send a confirmed instruction to the selected agent conversation and continue that conversation.
  - **success:** One supported conversation receives a schema-valid targeted command and emits correlated lifecycle and answer evidence; a follow-up proves continuity. Unsupported targets remain read-only. Routing never silently substitutes another agent, native session, logical thread, or new conversation.

- **CAP-5**
  - **intent:** Jarad can explicitly publish a broadcast fact for multiple interested consumers through the same voice interface.
  - **success:** A spoken, confirmed named/typed broadcast reaches two demonstration subscribers and durable history without screen interaction. Publication is distinguished from consumer execution; ambiguous intent never becomes a broadcast.

- **CAP-6**
  - **intent:** Jarad can hear concise status, clarification, and agent responses and maintain a spoken conversation.
  - **success:** A real correlated reply is spoken through Voxxy on the head unit, with immediate non-screen stop/mute and no microphone feedback loop. Engine identity is recorded; audio failure preserves the response and never repeats the agent command.

- **CAP-7**
  - **intent:** Jarad can understand instruction progress and recover from lost connectivity without duplicate work.
  - **success:** Submission, gateway dispatch, processing outcome, and answer availability are distinct evidence-backed states, including rejected/unknown. Reconnection preserves identities and readback; drafts never auto-send; retransmission requires proven consumer deduplication.

- **CAP-8**
  - **intent:** Jarad can use the complete first-release conversational loop while driving without reading a terminal or operating a touch workflow.
  - **success:** On a supported AAOS route, driving use provides hands-free selection, summary, clarification, confirmation, instruction, broadcast, reply, and cancel with zero required screen reads/taps. Detailed timelines, editing, and complex touch controls are suppressed. Emulator or parked-only proof does not establish actual-car driving readiness.

## Constraints

- First target is native Honda AAOS with Google built-in on the 2026 Civic Si's 9-inch factory display, independent of a connected phone. Phone-projected Android Auto is not the first delivery. Actual firmware/API/ABI remain unverified; Honda's 9-inch API 33 emulator is a candidate, not the exact vehicle image.
- Honda states ADB cannot be used in an actual vehicle. Development installs target the emulator; actual-car delivery requires a verified Automotive Play testing/distribution or explicitly approved OEM route. No sideload, debugging-menu, or unrestricted APK assumption is permitted.
- AAOS host UX restrictions govern every mode. A local Driving/Unknown voice profile cannot override host restrictions. Validated hands-free driving remains the product requirement; a host-blocked path is a feasibility blocker, not permission to remove the requirement or bypass restrictions.
- Category eligibility and installation are separate gates. Do not relabel agent dialogue as media, software agents as IoT devices, or dashboards as navigation/messaging. Templated driving categories use the supported Car App Library host; media has a separate session/service architecture. Holocene chooses architecture only after verifying a legitimate route.
- This is a cross-project seam contract. Holocene owns surface/composition; Bloodbank owns schemas/dispatch; Candystore owns history; HeyMa/infra own voice ingress/ASR seams; Voxxy owns synthesis; the runtime owner owns continuity; Deckard is enrichment. Child PMs own implementation planning and code.
- Bloodbank is the behavioral spine: facts use `bloodbank.evt.*`, targeted intent uses `bloodbank.cmd.*`, and execution emits lifecycle facts. Read APIs are not another command lane. ASR/TTS HTTP engines stay behind owned bus adapters.
- The client uses an authenticated Holocene boundary, not broker credentials, raw registries, terminal-keystroke injection, or unrestricted service credentials. Server secrets remain vault references or process environment values.
- Employee, harness/runtime, native session, logical thread, correlation, and pane identity stay distinct. Labels are not routing keys. Observation does not imply write support; destinations declare exact routes, continuity, and reply capability. A native session ID cannot masquerade as `thread_id`.
- Voice is half-duplex: activate, capture, transcribe, clarify, confirm, dispatch, await, speak. Factory “Hey Google” and the steering-wheel talk button activate the system assistant; custom launch/intents, mic capture, cancellation, and background behavior require proof. ASR is separate from Vox TTS; no custom hotword privileges are assumed.
- Driving interaction never relies on visual browsing or touch confirmation. Host-restricted/unknown state never unlocks detail through GPS or privileged raw vehicle properties. Loss of activation/mic/audio support explicitly blocks readiness.
- The immediate child slice is a bounded Honda-emulator feasibility spike, not completion of these capabilities. `car-modes.md` defines platform gates; `acceptance.md` separates emulator evidence, distribution readiness, actual installation, and integrated driving proof. `brownfield.md` records existing backend gaps as dated evidence.

## Non-goals

- A full mobile Holocene clone, terminal mirror, source editor, or visual code-review workflow in the car.
- Arbitrary spoken shell execution, implicit broadcast, or universal first-release write adapters.
- Android Auto projection, rooting, sideload/host-policy workarounds, or automatic Play/OEM approval.
- A public product launch in the feasibility spike; Automotive testing eligibility remains in scope because actual-car delivery depends on it.
- Always-listening general conversation, full-duplex audio, offline execution, or automatic replay of pending instructions.
- A new workforce registry, ticket state machine, event store, broker, or general-purpose orchestrator.

## Success signal

On the actual Civic Si through a verified native AAOS route, Jarad can activate without the screen, hear activity from two harnesses, select one supported conversation, dictate and verbally confirm an instruction, hear its real correlated Voxxy reply, and continue the conversation without reading or tapping the display. An explicit spoken broadcast reaches two passive subscribers; reconnect preserves evidence without repeating work. Detailed browsing remains parked-only where supported. Emulator feasibility is an intermediate milestone, not this success signal.

## Assumptions

- U.S.-market factory Google built-in equipment matches the official model documentation; actual unit information must confirm software and capability details.
- Honda's API 33 9-inch LHD image is the initial development candidate; Holocene owns packaging and version choices after inspecting the real unit.
- First writable target is a dedicated declared Bloodbank conversation with one fleet agent; interactive CLI sessions remain observable until exact routing is proven.
- First broadcast is a non-operational note with two passive subscribers. Half-duplex voice, default `rick`, and latency budgets remain proposed defaults.

## Open Questions

- What firmware/API/ABI, template host, mic/focus/network behavior, and app-accessible UX restrictions does the actual Civic Si expose?
- Which legitimate AAOS category or approved voice-assistant/integration route supports agent conversation/control while driving, and what device eligibility remains beyond internal-track testing?
- Can system-assistant launch lead to supported non-screen capture and cancel, or is an OEM-supported voice interaction route required?
- Which agent/conversation and broadcast subscribers prove the loop, and which ASR path meets measured latency? Is VoxCPM mandatory or is Voxxy's selected engine acceptable?

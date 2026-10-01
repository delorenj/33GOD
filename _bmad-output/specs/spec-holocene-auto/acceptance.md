# Integrated acceptance

This is cross-project planning, not child stories or evidence of completed implementation. Parent keys are `33GOD:I-2` and `33GOD:I-2.1`; accepting child PMs own tickets, builds, and code. No root sprint file or `stories.yaml` is created.

## Bound the walking skeleton

Observe at least two harnesses, enable writes for one declared conversation, and prove real voice input, answer publication, Voxxy playback, follow-up continuity, and an explicit broadcast to two passive subscribers. **Driving usability belongs to this first delivery.** A parked-only or screen-PTT-only app cannot close CAP-8.

Fixture mode may support early UI iteration but must be labeled; emulator/fixture success is not live integration proof. A newly established dedicated Bloodbank thread may prove conversation continuity if it is visibly declared as that thread, not passed off as an existing terminal session.

| Seam checkpoint | Owning request | Integration exit evidence |
|---|---|---|
| Hardware and activation feasibility | Holocene; HeyMa/infra for ASR | Native install, mic/audio/connectivity, reliable non-screen activation and cancellation, API/background/focus behavior measured on the actual unit. |
| Truthful observation | Holocene + Bloodbank/Candystore; Deckard optional | Two real harnesses; canonical runtime/native-session/correlation associations; explicit unknown/stale/coverage and supported-route descriptors. |
| Real responder and continuity | Bloodbank + runtime owner + Holocene | Confirmed targeted command, lifecycle facts, published answer, and a second turn retaining context through the same declared route; unsupported terminal intervention remains disabled. |
| Complete hands-free loop | Holocene + HeyMa/infra + Bloodbank + Voxxy | Activate, select, dictate, clarify/confirm, dispatch, hear response, follow up, broadcast, stop/cancel with zero required display reads/taps. |
| Recovery and vehicle behavior | Same owners | No duplicate execution after reconnect, two broadcast observations and durable row, audio focus/interruption, and Driving/Unknown visual restrictions without losing the valid voice path. |

These checkpoints are not a requirement to finish wider DeloHQ or workforce rollout first. Reuse existing facts and solve only the missing seam. Initial stationary tests precede any motion-dependent checks; final reporting must still identify whether driving usability has actually been verified.

## Demonstration sequence

1. Record actual unit/API/ABI, APK build, backend versions, connectivity, mic/audio/activation behavior, mode source, and the selected route descriptor. Keep credentials out of evidence.
2. Launch Unknown. Show restrictive visuals and the working voice path. While stationary, open Parked detail and demonstrate that missing signals/zero GPS speed do not automatically unlock it.
3. Produce real activity from two harnesses. Match roster rows to canonical event/runtime/conversation evidence independently of Deckard. An observed-only harness must reject intervention visibly and audibly.
4. Inspect a bounded parked stream with lifecycle, tool, message, and unknown-type examples. Match canonical event IDs, source timestamps, cursor/replay behavior, and coverage. Do not infer Needs input or session termination from silence.
5. Enter the Driving interaction profile while stationary for initial testing. Hide detail and run the rest without looking at/tapping the display. Activate through the chosen non-screen mechanism, ask which agents are active, and select the supported conversation by voice.
6. Dictate a short bounded instruction containing a unique marker. Use only the final transcript, hear target/action confirmation, then confirm verbally. Ambiguity, cancellation, or route changes publish nothing.
7. Collect stable command/request ID, correlation, target/profile, logical thread, turn, and resolved session evidence. Distinguish transport submission, gateway dispatch, processing outcome, and actual answer. Query durable facts; invocation completion alone cannot prove reply delivery.
8. Hear the real published response through Voxxy on the head unit. Record response ID, returned synthesis engine, audio duration, playback/interrupt result, and latency. A placeholder or discarded response cannot satisfy this step.
9. Follow up by asking about the earlier marker without repeating it. Prove context continuity and declared route behavior. If an exact-native-session route was promised, prove it or reject reset; logical-thread continuity cannot be misrepresented as native-session targeting.
10. Explicitly request a broadcast note, hear fact type/audience, and confirm by voice. Collect one schema-valid fact, two passive subscriber observations, and one durable Candystore row. Publication is not proof of consumer work execution.
11. Drop connectivity before and after controlled submission in separate tests. Unsent drafts must never auto-send. After publication, outcome stays Unknown until readback; do not retransmit without proven consumer deduplication. Replay must not duplicate visible events or agent execution.
12. Interrupt with phone/navigation/focus loss and stop/mute/cancel. Demonstrate prompt nonvisual cancellation, no TTS-to-ASR echo command, and explicit resumption without republishing intent.
13. Exercise actual hardware behavior affected by movement, using a controlled test/operator arrangement that does not require the driver to inspect diagnostics. Document activation, focus, networking, mode changes, and zero required display interaction. Stationary simulation alone is not evidence that firmware remains usable in motion.

## Negative cases

| Test | Expected result |
|---|---|
| Shared display names or multiple sessions | Spoken clarification using canonical route choices; no guessed destination. |
| Route reset/eligibility change after capture | Cancel or reconfirm; no hidden replacement conversation. |
| Missing hook coverage/end fact or stale source | Unknown/stale with evidence, not invented Idle/Completed/Needs input. |
| Mic/provider/activation denied or unavailable | No command; explicit driving-readiness blocker. |
| Partial or ambiguous ASR/intent | Clarify before confirmation/publication. |
| Unsupported interactive target | Read-only/rejected; no keystroke or `/resume` prompt workaround. |
| Unknown/malformed/out-of-order/replayed event | Bounded fallback, stable ID deduplication, no false lifecycle regression. |
| Gateway completed but no answer | Processing complete/answer unavailable, not “agent replied.” |
| Same idempotency key with different command ID | Do not assume deduplication; current gateway keys claim by command ID plus envelope digest. |
| Vox/focus failure or expired URL | Preserve answer and retry speech only; no repeated agent command. |
| App output heard by activation/ASR | No command publication; local cancel remains usable. |
| Driving/Unknown entered | Hide logs/editing, retain validated voice path, cancel unsent touch composition. |
| Broadcast ambiguity | Clarify; no implicit all-agent command. |

## Proposed measurement budgets

These are defaults pending actual hardware/owner measurements, not existing guarantees.

- Live presentation within 5 seconds of observed ingress; also record source-to-display latency and upstream coverage.
- Recent-history recovery within 10 seconds after restored connectivity; explicit gap if catch-up is incomplete.
- Final transcription within 5 seconds after short utterance completion.
- Warm short Vox acknowledgement within 10 seconds; immediate local capture feedback must not wait for synthesis. Measure cold starts separately.
- Nonvisual stop/cancel local response target under 1 second; verify during backend delays and playback.
- No fixed agent-execution promise; distinguish delay/Unknown from actual failure.
- Owners declare per-source max-age. Silence is not an idle-state reducer.

## Closeout evidence

Keep device/build and activation proof, canonical event/command/correlation IDs, declared logical-thread versus native-session guarantees, second-turn continuity, real answer publication, speech/playback evidence, subscriber observations, reconnect/deduplication, audio interruptions, and non-screen interaction measurements. Link child tickets and landed revisions when implementation happens; derive progress rather than entering duplicate status here.

Report separately: **implemented**, **installed**, **live integrated proof**, and **verified driving usability**. Planning establishes none of those runtime outcomes. The next recommended step is Holocene-led hardware/activation and conversation-route feasibility, followed by accepted child requests for the smallest complete voice slice.

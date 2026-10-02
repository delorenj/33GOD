# Integrated acceptance

Parent keys are `33GOD:I-2`, `I-2.1`, `I-2.2`, and `I-2.3`; child PMs own implementation tickets, builds, and code. This is cross-project acceptance, not child stories. No root sprint file or `stories.yaml` is created.

## Accepted Honda AAOS feasibility baseline

HOLOC-9 is accepted and published in Holocene main `41d9ba22bf97b55be2b7a50dccbec2e787abeee4`; its child evidence owns the executed results. The following describes that bounded baseline, not a requirement to repeat the spike or proof of the complete walking skeleton:

1. Identify installed/needed toolchain and an available Honda 9-inch emulator candidate. Jarad authorized installing missing Android tooling, accepting Android SDK/Honda emulator licenses, and downloading the required image; record installed versions and acceptance/setup results. Actual Civic firmware/API remains a separate measurement.
2. Produce a minimal native AAOS build/launch experiment and labeled agent-observation/voice shell where tooling permits. Fixtures may prove rendering and interaction plumbing but cannot claim live agent commands or replies.
3. Exercise host restriction transitions, permitted mic capture/endpointing, audio focus, and a non-screen activation/cancel candidate; distinguish Assistant launch from app capture. Report each unavailable feature and whether the issue is emulator capability, permission, architecture, or OEM integration.
4. Return a source-backed category/distribution decision and evaluate category-eligible in-app voice versus genuine VIA/assistant-role availability as separate branches. No TTS-as-media, agents-as-IoT, or navigation/messaging disguise. Google lists AAOS internal testing with no car form-factor review and closed review as non-blocking; that opportunity does not prove device eligibility or privileges. Honda does not expose actual-vehicle ADB.
5. Identify the smallest next owner requests for runtime/session joins, response publication, ASR schema alignment, and Vox bus adapters, using current code rather than assuming the September 30 gaps are unchanged.

Spike exit can be **demonstrated**, **blocked with reproduced evidence**, or **requires OEM/Play confirmation** per question. It cannot close CAP-8 or substitute parked-only scope. Internal/closed test or public-store upload is not authorized by the spike alone.

## Next independently deliverable seams

The full loop needs two narrow advances after the HOLOC-9 baseline:

- **I-2.2 / Bloodbank final answers (`bb:BB-30`):** capture a full final assistant answer and
  exact command/logical/native lineage, journal immutable message identity, then
  publish a canonical durable fact before command acknowledgement. Commentary,
  tool output, reasoning, empty/failure/interrupted outcomes, and processing-only
  receipts cannot satisfy answered state. Publication/restart replay must not
  rerun completed execution; pre-capture ambiguity stays explicit. Existing
  generic conversation messages remain compatible.
- **I-2.3 / Holocene real speech (`holocene:HOLOC-10`):** inject one known short synthetic/prerecorded
  phrase into the isolated emulator microphone, measure actual waveform and
  silence control, obtain a real final recognizer transcript, and render a local
  diagnostic acknowledgement with guest-output evidence. No canned transcript
  substitution. Local playback is not Vox or an agent reply. Screen/simulated-key
  cancel tests do not prove spoken stop or factory steering-wheel support.

These slices can develop in separate child repos; shared runtime activation and
integrated verification are serialized. Known synthetic input is authorized; room
microphone recording, assistant-default changes, account/model/provider updates,
Play uploads and vehicle modifications are not. Recognition failure is a
reproduced blocker, not permission to send the APK directly to a backend engine
or bypass Bloodbank. This advances CAP-3/4/6/7 evidence without claiming CAP-8.

## Authorized serialized runtime verification

After BB-30 passes independent specification and quality review and its exact
revision is on component/root main, Jarad authorized restarting only the affected
fleet gateway once no commands are in flight. Two benign no-tool prompts in a
dedicated eligible test conversation may then verify final-answer arrival and
follow-up continuity. Verify the intended subscription route, no paid fallback,
full correlation/lineage, stable message identity and Candystore readback; no
unrelated agent turns or provider/fleet reconfiguration are included. This is
permission for later proof, not evidence that activation or live publication has
succeeded.

HOLOC-10 runtime verification remains isolated synthetic audio. A failed or
protectively stopped emulator boot establishes a resource/setup blocker, not ASR
failure. Any next emulator-only experiment must retain the existing bounded
memory policy, measure actual scope/process usage, and prove private audio,
authenticated loopback gRPC and disabled host microphone before input/output
claims. Do not raise shared limits or convert unit/fake-server success into
on-device acceptance.

## Bound the integrated walking skeleton

Observe at least two harnesses, write to one declared conversation, and prove real voice input, answer publication, Voxxy playback, follow-up continuity, and an explicit broadcast to two passive subscribers. **Driving usability remains first-release scope.** Screen-PTT-only or parked-only functionality fails CAP-8.

Emulator/fixture proof, distribution eligibility, actual installation, live backend proof, and actual-car driving behavior are separate stages. A dedicated Bloodbank thread may demonstrate continuity if declared honestly, not represented as an existing terminal session.

| Seam checkpoint | Owning request | Exit evidence |
|---|---|---|
| AAOS feasibility | Holocene | Reproducible Honda-emulator experiment, host UX/voice findings, honest category/installation-path decision, remaining production blockers. |
| Actual delivery and activation | Holocene; HeyMa/infra for ASR | Verified Automotive testing/OEM route, installed build, measured real unit/API/mic/focus/network and non-screen capture/cancel. No vehicle-ADB dependency. |
| Truthful observation | Holocene + Bloodbank/Candystore; Deckard optional | Two harnesses; canonical runtime/native-session/correlation associations, freshness/coverage, explicit supported-route descriptors. |
| Real responder/continuity | Bloodbank + runtime owner + Holocene | Targeted confirmed command, lifecycle facts, published answer, and context retained on a second turn. |
| Complete driving voice loop | Holocene + HeyMa/infra + Bloodbank + Voxxy | Permitted activation, selection, capture, clarify/confirm, dispatch, reply, follow-up, broadcast, stop/cancel without screen reads/taps. |
| Recovery/vehicle behavior | Same owners | No duplicate execution, two broadcast observations and durable row, focus/interruption, host restriction behavior, supported nonvisual operation on actual hardware. |

No wider DeloHQ/workforce completion is imposed as a prerequisite. Host UX restrictions always govern permitted behavior; a blocked driving path is a concrete feasibility result, not a local override.

## Integrated demonstration sequence

1. Record build/toolchain/emulator revision, then actual unit/API/ABI, verified distribution route, backend revisions, connectivity/mic/focus/activation, and selected conversation guarantees. Keep credentials out of evidence.
2. Exercise AAOS host restrictions in the emulator before actual-car verification. Unknown/missing evidence must not unlock detail; supported host callbacks dominate local UI modes. Host-blocked capture/audio must stop, not bypass the restriction.
3. Produce activity from two harnesses; match roster rows to canonical identities/events independently of Deckard. Observed-only targets must reject intervention visibly/audibly.
4. Where the chosen architecture permits parked detail, inspect a bounded stream with lifecycle, tool, message, and unknown-type examples. Verify timestamps/cursors/replay/coverage; silence does not prove Needs input or termination.
5. In the host-permitted driving interaction path, activate without the display, ask for agent status, and select a supported conversation by voice. Initial stationary simulation stages this test but does not prove real in-motion firmware behavior.
6. Dictate a short bounded instruction with a unique marker. Use final transcript, speak target/action confirmation, then confirm verbally. Ambiguity/cancel/route change publishes nothing.
7. Collect command/request ID, correlation, recipient/profile, logical thread/turn, and resolved-session evidence. Distinguish submission, gateway dispatch, processing completion, and actual answer; query durable facts.
8. Hear the real published reply through Voxxy on the head unit; capture response/engine/audio/playback/interrupt/latency evidence. A fixture, discarded response, or processing-only receipt fails this step.
9. Ask about the earlier marker without repeating it; prove declared continuity. Logical-thread continuation cannot be called strict native-session targeting; if strict routing was promised, resets must reject/reconfirm.
10. Dictate an explicit broadcast, hear fact type/audience, confirm by voice, and verify one canonical fact, two passive observations, and one Candystore row. Publication is not subscriber execution.
11. Lose connectivity before and after controlled submission in separate tests. Drafts never auto-send; published outcome stays Unknown until readback. No retransmission without consumer deduplication; replay never duplicates rows or work.
12. Exercise calls/navigation/focus loss, host restriction change, and non-screen stop/mute/cancel. No TTS echo commands or automatic intent replay; resume explicitly through the supported path.
13. Verify movement-dependent production behavior through a controlled test/operator arrangement without driver diagnostic interaction. Record host restrictions, activation/capture/audio/network and zero required screen reads/taps. Emulator/stationary proof alone cannot close driving readiness.

## Negative cases

| Test | Expected result |
|---|---|
| Unsupported category/install/mic/assistant path | Reproduced/source-backed blocker; no relabeling or ADB/host-policy workaround. |
| Host disallows UI/audio/capture | Obey; report incomplete driving readiness without removing CAP-8. |
| Shared names/multiple sessions | Spoken canonical-route clarification, no guessed destination. |
| Route reset/eligibility change | Cancel/reconfirm, no hidden replacement conversation. |
| Missing hook/end facts or stale coverage | Unknown/stale evidence, not invented Idle/Completed/Needs input. |
| Partial/ambiguous ASR | Clarify before publication; unavailable voice means no command. |
| Unsupported interactive terminal | Read-only/rejected; no keystroke or `/resume` workaround. |
| Unknown/malformed/out-of-order/duplicate event | Bounded fallback, canonical deduplication, no receipt regression. |
| Processing completed, no answer | Processing-complete/answer-unavailable, not “agent replied.” |
| Same idempotency key, new command ID | No assumed deduplication; preserve supported command identity/body on any allowed retry. |
| Vox/focus/URL failure | Preserve answer; retry speech only. |
| Own output heard by ASR/activation | No command; local supported cancel remains responsive. |
| Broadcast ambiguous | Clarify, not implicit all-agent execution. |

## Proposed budgets and closeout

Measure rather than assume: live presentation under 5 seconds from ingress plus source delay/coverage; history recovery under 10 seconds after connectivity; final short transcript under 5 seconds; warm short Vox acknowledgement under 10 seconds; local non-screen cancel under 1 second. Cold starts are separate; agent execution has no fixed completion promise. Owners declare source max-age; silence is not an idle reducer.

Keep emulator/build/category evidence, actual install and activation proof, event/command/correlation IDs, logical/native route guarantees, follow-up context, published answer and playback, broadcast observations, reconnect, host restrictions, audio interruption, and zero-display interaction measurements. Link child tickets/revisions; derive progress rather than duplicate state.

Report separately: **emulator feasibility**, **distribution path**, **installed on Civic**, **live integrated proof**, and **verified driving usability**. The immediate request advances the first stage, not all five.

# Car platform and interaction contract

Derived from the Holocene Auto memlog. Jarad explicitly requires first-release usability while driving; this supersedes the earlier parked-first scope. Stationary tests are validation staging, not the product boundary.

## Target and hardware gate

**Confirmed:** an Android head unit that installs apps directly. Deliver a native APK, not an Android Auto projection. Holocene chooses the child implementation; Kotlin/Compose is a candidate, not an existing dependency or parent mandate.

Record make/model, Android/API level, ABI, landscape size/density, install/debug path, Google-services presence, microphone/speaker path, hardware voice controls, audio focus, sleep/resume, background microphone restrictions, DeLoNET connectivity, and motion/park signal availability. Test with the phone disconnected to distinguish native apps from projection. Use private connectivity and service hostnames, not a public broker.

Start on a matching landscape emulator, then the stationary real head unit. Verify mic, speech activation, audio interruption, and focus on that hardware; emulator success does not establish them.

| Platform | Relationship to this spec |
|---|---|
| Standalone Android/AOSP head unit | First target; firmware may lack Play Services, recognition provider, car APIs, vehicle signals, or hardware-button mapping. |
| Phone-projected Android Auto | Deferred. No documented developer-agent dashboard category; a regular Activity is not a projected app. Do not relabel as messaging/media/navigation/IoT. |
| Embedded Android Automotive OS | Deferred. Host UX restrictions and OEM capabilities apply; it is not synonymous with standalone Android or Google built-in. |

“Parked-only” is not an unrestricted publication exemption. Native installation does not establish platform eligibility or tested in-motion behavior.

## Modes

| Mode | Visual behavior | Conversational behavior |
|---|---|---|
| Unknown | Default until motion evidence is available; same restrictive visuals as Driving. No detail/editor/touch decision flow. | Validated voice selection, summary, confirmation, instruction, broadcast, reply, and cancel remain available. Missing motion data does not remove the voice product. |
| Parked | Large agent tiles, bounded normalized event detail, optional Deckard context, PTT supplement, device/setup diagnostics. Enter deliberately while stationary or through a trusted signal. | Same conversational loop; setup may use touch. |
| Driving | Minimal glanceable identity/status; no scrolling logs, source editing, transcript review, or complex touch confirmation. | Complete supported hands-free loop. No step requires reading or tapping the display; complex work is summarized/deferred, not exposed as a terminal. |

Missing/stale motion data, zero GPS speed, disconnected phone, or silence cannot unlock Parked detail. Manual Parked selection is not automatic enforcement. A mode transition cancels any unsent touch-oriented composition but need not cancel an already confirmed voice command. Published work continues; its result remains available by conversation/correlation.

On a later AAOS target, host restrictions take precedence; do not assume this ordinary Android mode policy grants AAOS driving permission.

## Hands-free activation gate

A screen-only PTT button fails driving acceptance. Choose and demonstrate an actual non-screen entrypoint supported on the unit:

- a bounded wake-word/activation recognizer;
- a reliable hardware/steering-wheel voice control if exposed by firmware;
- an existing voice-assistant integration that opens the app's supported capture flow.

Do not assume Google Assistant, key events, a privileged mic service, or continuous `SpeechRecognizer` works on this hardware. The activation choice remains an explicit open question. If a bounded listener is required, it is in scope; unrestricted always-listening general conversation is not. Explain mic permissions and foreground-service behavior within Android's actual API constraints.

Wake-word activation should not continuously upload cabin audio. Forward only intentionally captured utterances through the owned voice ingress. A local activation/cancel path must remain responsive during network/LLM/TTS delays.

## Conversational experience

Supported first catalog: enumerate/summarize agents, select an unambiguous conversation, request a short activity summary, compose an instruction, explicitly broadcast a note, clarify/confirm, repeat last reply, and stop/mute/cancel. One ingress routes these bounded intents; interpretation never invents recipients or unrestricted shell actions.

1. Activate without the screen. Stop this app's playback and announce/listen with brief local feedback; freeze current destination/context.
2. Capture one short utterance after explicit microphone permission. End by proven voice-activity detection, spoken completion, or hardware release. Screen release is only a parked option.
3. Use a final transcript, not partial recognizer guesses. Clarify uncertain speech, aliases, target, or intent using short spoken choices. Limit unsolicited verbosity.
4. For an instruction or broadcast, speak back the exact destination or audience and a concise interpreted action. Require verbal confirmation in driving mode. A target/session change invalidates confirmation.
5. Publish once with stable command/request identity and correlation. Say “sent” only after known transport evidence, not “done.” Capture/ASR/TTS retries never repeat publication.
6. Distinguish queued/submitted, gateway dispatch, processing outcome, and answer availability. “Started” from the current gateway is not proof a model turn began; a missing answer remains missing even if processing completed.
7. Speak the real correlated response through Voxxy, explicitly requesting `voice: "rick"` by default. Preserve the exact declared conversation for follow-ups. Stop/mute/cancel must interrupt promptly by voice or the chosen reliable hardware path.

Half-duplex capture and playback do not overlap. A tested local interrupt detector or hardware path may remain available during output, but it must reject the app's own audio; do not solve cancellation by continuously recording TTS into command ingress. Broad full-duplex/barge-in conversation is not required.

Agent attention notifications are opt-in, bounded, and evidence-backed. A tool event or finished turn is not automatically “needs input.” Do not read every event, code block, or full transcript aloud.

## Voice services and interruptions

Android `SpeechRecognizer` needs an installed working provider; API 31+ on-device support still requires a model. It is not intended as continuous listening. Backend ASR is a candidate when the unit lacks a provider; HeyMa/infra must define mobile upload and canonical transcription publication. Vox is TTS, not recognition.

The APK reaches authenticated Holocene ingress. Behavioral ASR, agent, and TTS requests/results use owner-defined Bloodbank adapters; existing HTTP engines sit behind those adapters. No raw mobile broker or engine credentials.

Request suitable transient audio focus; release promptly. Stop/defer own speech on phone/navigation/focus loss without masquerading as navigation guidance. Foreground/background mic and audio focus must work under the measured Android version; if not, driving readiness is blocked rather than falsely declared.

Vox URL synthesis is synchronous full audio, not incremental streaming. Keep replies to one or two short sentences when possible. Record engine identity; distinguish synthesis success, URL availability, client playback, and actual user acknowledgement. Retry an expired URL or speech failure for the same answer only.

## Failure behavior

| Condition | Required behavior |
|---|---|
| Activation/mic/ASR unavailable | Announce through any working path and disable voice dispatch; explicit driving-readiness blocker, not invisible failure. Observation remains available later. |
| Ambiguous transcript/alias/target/intent | Short spoken clarification; no publication until explicit confirmation. |
| Route/session resets or eligibility disappears | Cancel/reconfirm; never silently target a replacement thread. |
| Connectivity lost before publication | Retain an explicitly unsent draft if supported; never auto-send on reconnect. |
| Connectivity lost after publication | Spoken Unknown/delayed outcome; correlation-based readback, no retry without proven deduplication. |
| Vox unavailable/audio expired | Preserve answer; speech-only retry or brief local unavailable prompt. Never repeat agent work. |
| Call/navigation/focus interruption | Stop own capture/playback; pause interaction and preserve context. Resume only explicitly, not by replaying confirmed intent. |
| Tool flood or long response | Bound/group details and speak a short summary. Canonical history stays queryable. |
| Driving/Unknown entered during visual composition | Hide detail and cancel unsent touch draft; a voice instruction must be freshly clarified/confirmed. |

## Platform references

Checked 2026-09-30; revisit before platform expansion.

- [Android Auto versus AAOS](https://source.android.com/docs/automotive/start/what_automotive)
- [Supported categories](https://developer.android.com/training/cars), [Car App Library setup](https://developer.android.com/training/cars/apps/library/set-up-project), and [car app quality](https://developer.android.com/docs/quality-guidelines/car-app-quality)
- [SpeechRecognizer](https://developer.android.com/reference/android/speech/SpeechRecognizer)
- [Audio focus](https://developer.android.com/reference/android/media/AudioFocusRequest) and [microphone service restrictions](https://developer.android.com/develop/background-work/services/fgs/service-types)
- [AAOS UX restrictions](https://source.android.com/docs/automotive/driver_distraction/consume)
- [ADB](https://developer.android.com/tools/adb), [AAOS emulator](https://developer.android.com/training/cars/testing/emulator), and [Android Auto Desktop Head Unit](https://developer.android.com/training/cars/testing/dhu)

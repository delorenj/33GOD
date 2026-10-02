# Honda AAOS platform and interaction contract

Jarad requires first-release usability while driving. Vehicle identification supersedes the earlier aftermarket-Android inference: the target is native factory AAOS with Google built-in in a 2026 Honda Civic Si. Stationary/emulator tests stage validation; they do not replace driving acceptance.

## Hardware and development target

Official U.S. model documentation confirms a 9-inch Google built-in display, native Play apps, system-assistant voice activation through “Hey Google” and the steering-wheel talk button, plus separate wireless Android Auto/CarPlay support. Native app execution does not need a phone; backend connectivity still needs proof.

Honda's SDK feed includes:

| Candidate | SDK package | Evidence boundary |
|---|---|---|
| Android 13/API 33, 9-inch LHD | `system-images;android-33;Honda-ivi-9inch-LHD` | x86_64, revision `25.03.120114`, archive approximately 2.72 GB. Initial U.S.-market development candidate, not proof of actual Civic firmware or ABI. |
| Android 12L/API 32, 9-inch LHD | `system-images;android-32;Honda-ivi-9inch-LHD` | Compatibility candidate if actual unit information warrants it. |

Use Android Studio's SDK Update Sites to add the official feed, then a Honda Automotive AVD. Accepting SDK/vendor licenses and downloading the images are separate owner decisions; this planning correction does neither. Default image/example settings for another Honda model are not Civic display measurements.

Record actual head-unit software/API/ABI, resolution/density, template host, installed assistant/recognition services, audio focus, sleep/resume, microphone permissions, UX restriction behavior, and connectivity. Prefer private service-hostname routing to authenticated Holocene; no public broker or embedded engine credentials.

**Honda explicitly says ADB cannot be used in an actual vehicle.** ADB install/logging belongs to emulator development. Actual-car tests require an independently verified Automotive Play testing/distribution or approved OEM route; do not assume sideload or a hidden developer menu.

## Architecture and distribution gate

| Question | Required evidence |
|---|---|
| Does a permitted AAOS category cover this product? | Source-backed assessment of agent status/conversation/control, not a category label selected merely to make an emulator launch. No established fit is claimed yet. |
| Can it use the templated host? | Category eligibility, actual host/version/features, and a supported `CarAppService`/AAOS entrypoint. Freeform driving UI is not the default. |
| Is a media architecture appropriate? | Only for genuine audio-media functionality. `MediaSession` with `MediaBrowserService`/`MediaLibraryService` can work without template UI; TTS replies alone do not establish media eligibility. |
| Can the app reach the actual car? | Automotive test-track/device eligibility or explicit OEM delivery permission. Track review behavior is described below; testing is not a blanket capability approval. No upload is authorized by this spike. |
| Is a voice-assistant route available? | Documented OEM/user role-selection and permitted permissions. App launch by Assistant is not replacement of Assistant or automatic access to the voice-button audio. |

`app-automotive` applies to a templated AAOS implementation, not every possible AAOS architecture. Adding a library or `distractionOptimized` metadata is not a general unlock, app-category approval, or host-policy override. Android Auto messaging support does not imply native AAOS messaging eligibility.

The feasibility result must distinguish a runnable emulator experiment, a legitimate distribution candidate, and actual-car readiness. If the current feature set has no supported route, retain the driving requirement and return a concrete architecture/OEM decision—not a parked-only product silently substituted for it.

Google's [distribution table](https://developer.android.com/training/cars/distribute) lists AAOS internal testing without car form-factor review, closed testing with non-blocking review, and open/production with blocking review. Internal App Sharing is Android Auto-only. Internal testing is a real capability-probe opportunity, not proof of device filtering, category fit, or privileged access; production approval is not assumed necessary before every vehicle test.

Two legitimate voice branches need separate evidence:

- **In-app voice:** a category-eligible templated host can expose `CarAudioRecord` with Car App API 5+, `RECORD_AUDIO`, audio focus, and recording indicator. This supports an in-app assistant, not background hotword or steering-wheel ownership. Car App Actions currently cover POI parking/charging, not arbitrary agent commands or microphone handoff.
- **Voice Interaction Application (VIA):** AOSP documents `VoiceInteractionService`, session/recognition, and a custom voice plate. Only the selected default receives system PTT/TTT; documented OEM deployment uses preinstallation and required grants, with later store updates. Check `ROLE_ASSISTANT` availability/selection rather than assuming Honda supports third-party replacement. `BIND_VOICE_INTERACTION` protects binding; it alone does not prove the APK must be system-signed. Hotword/system-control permissions are distinct.

No default-assistant change or internal-track upload is authorized now. A missing assistant role blocks the VIA branch, not necessarily in-app voice; a working emulator role does not establish the factory vehicle's role.

## Modes under host authority

| Mode | Visual behavior | Required conversational outcome |
|---|---|---|
| Unknown/restricted | No detailed logs, editor, or touch decision flow. Missing app vehicle evidence cannot unlock detail. | Hands-free path remains the product goal but runs only where host permissions/restrictions allow; unsupported state is a readiness blocker. |
| Parked/unrestricted | Supported setup and bounded event detail. Custom Views/Compose are allowed only where the selected AAOS architecture/category permits them, not merely because the vehicle is stationary. | Same conversation loop; parked screen PTT may supplement setup/testing. |
| Driving | Supported host-rendered/minimal presentation, no scrolling logs, transcript review, or complex touch confirmation. | Selection, summaries, clarification, confirmation, instruction, broadcast, reply, and cancel without screen reads/taps through a proven permitted path. |

Use app-accessible AAOS UX restrictions and supported host callbacks. Do not substitute raw privileged speed/gear properties, zero GPS speed, or manual Parked selection for host authority. Host restriction changes cancel unsent visual composition and may suspend capture/playback; published work continues and remains queryable later. Do not keep audio active when the host forbids it.

## Hands-free activation

A screen-only PTT fails driving acceptance. Honda's factory activation proves access to the **system assistant**, not a Holocene capture API. Test system-assistant app launch/intents and the selected architecture's microphone entrypoint first. Hardware-key interception, custom wake words, default-assistant replacement, and privileged hotword capture remain unproven; do not require them without an available route.

Record each separately: assistant invocation, app launch, microphone permission/capture, utterance completion, verbal confirmation, and non-screen cancellation. A launched app with no supported way to capture or cancel is not hands-free proof. User-initiated recording, a local cancel path, and short audible state feedback must remain responsive during backend delays.

If an approved bounded activation listener is used, it must not continuously upload cabin audio. Android `SpeechRecognizer` is not continuous hotword recognition. Any assistant role/privileged permission dependency is reported explicitly; an emulator granting it does not prove production Honda access.

## Conversational loop

Initial catalog: enumerate/summarize agents, select an unambiguous conversation, summarize activity, compose an instruction, explicitly broadcast a note, clarify/confirm, repeat last reply, and stop/mute/cancel. One ingress routes bounded intent, not guessed recipients or arbitrary shell execution.

1. Activate through the proven non-screen route; stop own playback, provide short local feedback, and freeze destination/context.
2. Capture one short intentional utterance after permission; complete by proven endpointing or hardware release. Screen release is parked-only.
3. Process final transcript, not partial guesses. Clarify uncertain speech/aliases/intent using short spoken choices.
4. Speak exact recipient or audience plus concise action; require verbal confirmation for driving instruction/broadcast. A route/session change invalidates confirmation.
5. Publish once with stable command/request identity and correlation. Transport evidence permits “sent,” not “done”; ASR/TTS retries never republish intent.
6. Distinguish submission, gateway dispatch, processing outcome, and actual answer. Current gateway `started` is not proof of model execution; processing completion without answer remains answer-unavailable.
7. Speak the real correlated response through Voxxy with `voice: "rick"` by default. Follow-ups preserve the declared route. Non-screen stop/mute/cancel must interrupt promptly.

Half-duplex capture and playback do not overlap. A permitted local interrupt detector/hardware path may remain active, but must reject the app's own speech. Broad full-duplex/barge-in conversation is not required. Attention announcements are opt-in/bounded; a tool event or finished turn is not automatically “needs input.”

## Voice services, focus, and failures

`SpeechRecognizer` needs an installed working provider; API 31+ on-device support still requires a model. HeyMa/infra's backend ASR is a candidate through owned upload/transcription adapters; Vox supplies TTS, not recognition. Actual mic/focus/network behavior needs production evidence.

The AAOS client reaches authenticated Holocene ingress. ASR, agent, and synthesis behavior crosses owner-defined Bloodbank adapters; existing HTTP engines stay behind them. Appropriate audio focus is requested/released without impersonating navigation. Calls/navigation/host restriction changes interrupt/defer speech and capture.

Vox URL synthesis is complete-audio, not streaming. Keep spoken replies short and record engine identity; synthesis, URL availability, playback, and user acknowledgement are distinct. Speech-only retries never repeat agent work.

| Failure | Required behavior |
|---|---|
| Unsupported category/install/voice/permission route | Explicit feasibility blocker and next decision; no disguised app or policy bypass. |
| Mic/activation/provider unavailable | No voice dispatch; audible/local available explanation and readiness blocker. |
| Ambiguous transcript/recipient/action | Spoken clarification before confirmation/publication. |
| Route resets or eligibility changes | Cancel/reconfirm; never silently replace thread. |
| Offline before publication | Explicit unsent draft if supported, never automatic send. |
| Offline after publication | Unknown/delayed until correlation readback; no retry without proven deduplication. |
| Vox/focus/URL failure | Preserve answer; speech-only retry, no duplicated instruction. |
| Host restricts activity/audio | Obey restriction, preserve context, resume explicitly through supported flow. |
| Tool flood/long reply | Bounded summary and canonical history, not an unbounded audio log. |

## Official references

Honda sources and feed verified in this conversation; SDK availability is not an installed emulator or exact-vehicle claim.

- [2026 Civic Si Google built-in and factory voice controls](https://www.hondainfocenter.com/2026/Civic-Si/Feature-Guide/Interior-Features/Google-Built-In/)
- [Honda emulator setup and no-vehicle-ADB FAQ](https://global.honda/en/cars-apps/)
- [Honda SDK feed](https://global.honda/cars-apps/emulator/honda-ivi-sys.xml)
- [Android for Cars categories](https://developer.android.com/training/cars), [AAOS templated implementation](https://developer.android.com/training/cars/apps/automotive-os), [car quality requirements](https://developer.android.com/docs/quality-guidelines/car-app-quality)
- [Media architecture](https://developer.android.com/training/cars/media), [AAOS UX restrictions](https://source.android.com/docs/automotive/driver_distraction/consume)
- [Automotive distribution tracks](https://developer.android.com/training/cars/distribute), [car microphone recording](https://developer.android.com/training/cars/apps/library/car-microphone), [Car App Actions](https://developer.android.com/develop/devices/assistant/cars)
- [VIA integration/distribution](https://source.android.com/docs/automotive/voice/voice_interaction_guide/integration_flows), [VIA implementation](https://source.android.com/docs/automotive/voice/voice_interaction_guide/app_development)
- [SpeechRecognizer](https://developer.android.com/reference/android/speech/SpeechRecognizer), [audio focus](https://developer.android.com/reference/android/media/AudioFocusRequest), [microphone service constraints](https://developer.android.com/develop/background-work/services/fgs/service-types)

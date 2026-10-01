# Current integration evidence and missing seams

Source inspected 2026-09-30. Paths below are relative to `/home/delorenj/code/33GOD` unless absolute. This is current-source evidence, not deployment acceptance. Read-only observation did not execute agent commands or test ASR/TTS. Revalidate sources before child implementation; older documents and installed skills disagree with several current behaviors.

## Ownership and existing shape

| Owner | Existing seam | Required Auto contribution |
|---|---|---|
| Holocene | Next.js 15/React 18 web, Fastify 5 API, SQLite event projection; host API plus platform-composed web | New native client and authenticated mobile/voice ingress; truthful roster/conversation projection and spoken receipt presentation. No Android/Gradle/Kotlin module found. |
| Bloodbank | CloudEvents schemas, NATS/Dapr, harness hooks, ASM live state, shared fleet invocation gateway | Runtime/session join, declared supported routes, answer publication, canonical mobile behavioral/voice contracts, observable rejection. |
| Candystore | PostgreSQL/Dapr event history and HTTP query API | Bounded correlation-based history/reconnect evidence; not a command executor or native-session registry. |
| HeyMa | Canonical checkout `/home/delorenj/HeyMa`; Wax durable file/audio workflow | Mobile voice ingress and schema-aligned transcript facts. `/home/delorenj/code/HeyMa` is retired, despite the older platform component path. |
| infra | Existing local faster-whisper multipart ASR bridge | Candidate recognition implementation behind an owned bus adapter; latency and live recognition not proven here. |
| Voxxy | `/home/delorenj/code/voxxy`; synchronous URL synthesis | Owned Bloodbank synthesis adapter/result contract; actual car playback remains a client observation. |
| Hermes/runtime owner + Flume | Logical conversation resolution and eligible named profiles | Declare route guarantees and resolve session continuity; no arbitrary CLI/native-session control assumed. |
| Deckard | Sibling `/home/delorenj/code/deckard`; Rust global-agent/mux/pane state | Optional explicit pane/session association. No daemon HTTP registry API found. |
| 33GOD | Cross-project composition and integrated acceptance | Seam outcome and delegation references, not child code or a duplicate event/workforce store. |

Holocene's `packages/delohq-contracts` provides useful evidence/freshness envelopes, but legacy APIs remain allowlisted and reference kinds omit runtime/session/pane. It is not an already migrated mobile command API: `holocene/packages/delohq-contracts/src/envelope.ts:36`, `dialect-guard.test.ts:50`, `refs.ts:8`. Auto is not constrained to Telegram Mini App authentication.

Project identities are not component labels: Bloodbank declares `project_id: bb` (`bloodbank/.project.json:31`); HeyMa declares `project_id: transcription-queue` while its `repo_path` still points to the retired checkout (`/home/delorenj/HeyMa/.project.json:4`, `:18`). Resolve that moved binding before live delegation. Holocene, Candystore, infra, and Voxxy declare matching project IDs. The runtime-owning project remains unresolved; `hermes-fleet` is a component, not an invented `hermes-runtime` project. All I-2 ticket references stay pending.

## Observability already available

### Holocene live and replay

Current routes in `holocene/apps/api/src/event-routes.ts:7`:

- `GET /api/events?after=<cursor>&type=<exact>&subject=<exact>&source=<exact>&limit=100`
- `GET /api/events/stream?after=<cursor>` or `Last-Event-ID`; SSE emits `ready`, `bloodbank-event`, and `reset`.
- `GET /api/events/status` exposes collection state, pending/catch-up and history gaps.

Rows carry `cursor`, `stream`, `sequence`, `subject`, `collected_at`, and the canonical `envelope`. SSE without a cursor tails current events; it does not flood the archive. REST defaults to oldest matching rows; paginate with `next_cursor`, not the global collection cursor. Invalid/expired cursors require reset/backfill handling. Transactional store/checkpoint behavior: `holocene/apps/api/src/event-store.ts:19`, `:85`, `:203`; collection status: `event-collector.ts:43`.

These filters do not select agent, project, native session, or correlation. A supported projection/filter join is new scope. Existing hook-handler timelines are not agent-work timelines.

During bounded inspection, collection reported `live`, `pending: 0`, **`history_gap: true`**; Candystore readiness returned 204. Healthy services do not prove complete historical coverage.

### Bloodbank agent state machine

Holocene serves `/api/modules/tooling/stats/agent-state-machine`, an envelope containing an ASM card with state rows and `detail` fields such as `cli`, `cwd`, `pid`, `profile`, `basis`, and optional Zellij context. Current state derivation includes working/tool-running/delegating/awaiting-human/failed/stale/idle/unknown.

Identity is CLI plus process/starttime or Hermes profile, not pane identity: `bloodbank/services/agent-hooks/core/asm.py:168`. The current proposer writes empty `session_id` and `correlationid`: `asm.py:422`; card export omits them and block/timing detail: `core/sweep.py:261`. This prevents treating the card as a supported conversation selector today.

Card TTL is 90 seconds. Missing Redis data yields Unknown/null, and fallback `observedAt: now` is not fresh agent evidence: `core/sweep.py:231`, `holocene/apps/api/src/tooling.ts:319`. Profile-gateway unit health is not proof that an employee has no active task/session. Some discovered-but-unobserved agents collapse to a count; declared adapters do not prove complete deployment coverage.

Needs input is explicit gate/bell evidence, not “turn finished.” `deckard.evt.attention` is outside persisted `bloodbank.evt.>`; ordinary replay cannot reconstruct historical attention: `bloodbank/services/agent-hooks/core/publisher.py:136`, `asm.lua:366`. Resolve authoritative live attention and disclose historical coverage rather than invent a durable state machine.

### Candystore history

Current read APIs:

- `GET /events?cli=&producer=&project=&correlationid=&lens=&class=&from=&to=&q=&tools=0`
- `GET /sessions/<correlation-UUID>` and `/sessions/<correlation-UUID>/summary`
- `GET /events/<event-UUID>/raw`

Routing/filter evidence: `candystore/candystore/main.py:104`; feed result shape: `query.py:454`; session query: `query.py:615`.

`/sessions/<id>` uses the **correlation UUID**, not native harness session ID, and returns an unbounded ascending timeline. Feed pagination is offset/time based, unlike Holocene's ingestion cursor. Tool folding in `/events` does not apply to session responses. Summary `ended_at` is the last event time, not proof of a session-ended event: `query.py:664`. No Candystore live-tail/SSE implementation was found; use the current Holocene live seam and a bounded history projection, with explicit gaps and event-ID deduplication.

### Required identity model

Keep separate: employee/profile, host runtime scope, native harness session, logical thread, correlation UUID, and optional Zellij pane/tab. Generic hook `actor.agent_id = bloodbank.agent.<cli>` identifies a harness, not an employee. New publisher correlation behavior is native-session scoped: `bloodbank/services/agent-hooks/clients/base.py:122`.

Deckard internal `GlobalAgent` has native session and optional pane/tab references: `/home/delorenj/code/deckard/crates/deckard-daemon/src/agents.rs:367`. Pane reuse is lifetime/epoch scoped: `deckard-core/src/state/store.rs:352`. `deckard status` is a fresh mux text probe, not a daemon registry HTTP API: `deckard-cli/src/main.rs:89`, `:353`. Never join by a recycled pane number or require a pane for an agent to appear.

## Commands, continuation, and replies

### Canonical invocation

`bloodbank/schemas/bloodbank/agent/invocation.start.json:12` defines type `bloodbank.agent.invocation.start`, subject `bloodbank.cmd.agent.invocation.start`, and schema revision `bloodbank.agent.invocation.start.v1`. No version token belongs in the bus subject/type.

Required command identity includes actor, causation/correlation, command UUID, nonblank idempotency key, `delivery: single_consumer`, `data.target_agent_id`, and `data.prompt`. Optional `thread_id`, `turn_id`, and `context` carry conversation context. `actor.agent_id` is the issuer; `target_agent_id` is the recipient. Validate the full schema and canonical naming contract, not merely the gateway's permissive manual decoder: `services/hermes-gateway/bloodbank_hermes_gateway/contract.py:103`.

Fleet routing requires an eligible registry entry with a valid profile, `bloodbank` mapping, activation absent/true, `gateway_scope: fleet`, and matching target identity; invalid non-boolean activation disables routing. Eligibility is rechecked before dispatch: `contract.py:190`, `adapter.py:454`. `holocene-pm` was a candidate eligible target, not invoked or approved as the demo recipient here.

### What `thread_id` actually means

The gateway defaults thread to `bloodbank:<correlationid>` and turn to command ID, then creates a Bloodbank DM source in the resolved profile: `contract.py:306`, `adapter.py:477`. Under fleet multiplexing the route key is `agent:<profile>:bloodbank:dm:<thread_id>`; Hermes looks up or creates the session behind that key: `/home/delorenj/.hermes/hermes-agent/gateway/session.py:664`, `:870`.

Same profile/thread supports **logical route continuation**, not arbitrary native-session selection. The command has no typed native-session precondition; reset/compression/recovery may change the native session. Passing a terminal's session ID as `thread_id` does not resume that terminal. Select an explicitly established Bloodbank conversation for the first walk, or add a strict owner-defined native-session contract before promising existing-session intervention.

Interactive Claude/Codex/OpenCode hooks are event producers, not inbound control consumers. No typed cross-harness resume/cancel adapter was found. Prompting `/resume` is not a replacement API and cannot prove exact routing.

### Lifecycle is not answer delivery

- Publication is transport evidence, not responder acceptance; no distinct invocation-accepted event was found.
- Gateway `started` is emitted before invoking Hermes; not proof that the model started.
- `completed` means processing completion, not business/task success or answer delivery.
- Invalid/ineligible routes can be dropped without a failure event; authenticated ingress needs explicit rejection/readback semantics.
- Gateway `send()` discards response content: `adapter.py:684`. Completed schema contains no answer. **Publish a schema-backed final response before claiming a real voice round trip.** Existing `bloodbank/schemas/bloodbank/conversation/message.appended.json:25` is a candidate, not a decision that its current shape suffices.

Lifecycle/dispatch details: `adapter.py:460`, `:515`, `:654`; envelope builder: `contract.py:334`. Current claim/replay deduplication is keyed by **command ID plus full-envelope digest**, not idempotency key alone: `adapter.py:381`. Identical retry must preserve command ID/body; a new command ID with the same key can execute again. Replays may repeat lifecycle facts, so client event-ID deduplication remains necessary.

Events are facts broadcast to subscribers; commands target one consumer. A future multi-agent instruction expands a confirmed target list into separate commands/receipts. Never use `target_agent_id: "*"` or assume every observer executes a broadcast fact.

## Voice seams and mismatches

### Recognition

Canonical `audio.transcription.completed` requires `transcription_id`, `file_path`, and `transcript_text`: `bloodbank/schemas/bloodbank/audio/transcription.completed.json:22`. Related start/started/failed schemas are file-path based, not mobile upload contracts.

HeyMa/Wax pipeline is an existing durable file workflow, but its state-change transcription events currently use `{item_id, from_state, to_state, cause_code, evidence}`, missing canonical fields: `/home/delorenj/HeyMa/components/wax/src/wax/ledger.py:262`, `:347`; outbox: `wax/events.py:88`. No mobile upload API, canonical transcription-start consumer, or started emitter was found. Do not treat these topic names as schema-aligned recognition readiness.

infra's existing loopback ASR implements `POST /v1/audio/transcriptions`, multipart file with optional language/model, returning text, language, durations and model: `/home/delorenj/code/infra/scripts/vocalinux-faster-whisper-server.py:130`, `:167`, `:319`. It serializes CPU/int8 inference and has a 50 MiB upload cap. Tests with a fake model do not prove live short-utterance latency. Keep this behind an owned bus/mobile adapter; do not embed a loopback address or infer remote availability in the APK.

HeyMa's older `/asr` WebSocket and obsolete publication command have a disabled server unit/stale checkout reference. They are not a proven current route.

### Synthesis

Voxxy currently exposes `POST https://vox.delo.sh/synthesize-url` with text, voice and synthesis settings; result contains `audio_url`, `engine`, `duration_s`, `bytes`, and `format: ogg_opus`: `/home/delorenj/code/voxxy/app/main.py:89`, `:238`, `:414`. Request **`voice: "rick"` explicitly**; HTTP omission differs from the MCP default: `main.py:193`, `:660`.

Synthesis completes before audio is returned; it is not streaming. Default cache TTL is 3600 seconds, without an explicit expiry/job/playback receipt; sweeper timing controls actual retention: `app/cache.py:25`. Returned engine can be a fallback despite HTTP 200; engine identity matters. Current source defaults to VibeVoice-only selection, contradicting older skill guidance requiring both engines: `compose.yml:23`, `cli/voxxy/commands/engine.py:295`. Jarad's “VoxCPM/Vox/Voxxy” identifies the requested service family; strict engine choice remains an open question.

No Bloodbank TTS command/result adapter was found. Queued sink delivery is not playback/heard proof: `app/sink.py:123`. Auto needs correlated voice result publication and actual client playback evidence, with cancellation/focus behavior measured on the head unit.

## Bounded proposed composition

The APK observes and speaks through one authenticated Holocene boundary. Holocene combines current read-side snapshots/history with canonical live events. A voice adapter turns intentional captured audio into canonical final transcript evidence; the bounded intent router produces either a targeted single-consumer command or a confirmed typed broadcast fact. The agent publishes a correlated final answer; a Vox adapter synthesizes and publishes its audio result; the client plays it and records playback separately.

Required before integrated acceptance: identity/session join; mobile ingress and non-screen activation; schema-aligned ASR; one declared route with response publication; explicit rejection/readback and retry policy; Vox bus adapter; bounded replay and attention-coverage disclosure. This plan proposes contracts and ownership, not deployed endpoint names or new schema names.

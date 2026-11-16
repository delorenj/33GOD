# Waybill: a flight recorder for one prompt

Status: v1 spec, 2026-11-15. Owner: `33god` (platform-wide, spans child projects).

A **waybill** is the paper that travels with freight and gets stamped at every
hand-off. Here it is one JSON document that records everything one prompt turn
caused across 33GOD, in order, with cause and effect. It works like the
Chrome DevTools Network panel, but its unit is a prompt rather than a request.
The Factory (`manual/sandbox`, live at https://manual.delo.sh/sandbox/) replays
it as a camera tour of the real components, seen from the prompt's point of view.

```
waybill record            # arm, then type a prompt in Claude / Codex / Codex Desktop
waybill capture --session <sid> [--turn N | --latest]   # rebuild a past turn
waybill show <file>       # DevTools-style waterfall in the terminal
waybill publish <file>    # MinIO + the Factory deep link
```

## 1. Ground truth (verified 2026-11-15, see `research/understand.json`)

The path of one prompt, in order. Each item names where the recorder can read it afterwards.

| # | What happens | Component id | Where it is recorded |
|---|---|---|---|
| 1 | Operator presses Enter. Claude writes the user entry to its transcript first. Codex writes it after the hooks return. | `ext:claude-code`, `ext:codex-cli`, `ext:codex-desktop` | Claude `~/.claude/projects/*/<sid>.jsonl` (glob by sid). Codex rollout via `~/.codex/state_5.sqlite threads.rollout_path` plus `thread_history_1.sqlite thread_turns` byte offsets. Desktop is identified by `session_meta.originator` (`codex_work_desktop` / `Codex Desktop`). `codex_exec` is headless. |
| 2 | The native hook runs `bb-hook` (and the Orca shim). | `bb-hook` | Not recorded on the client side. Fail-open exits leave no trace. |
| 3 | hook-hub claims an invocation, selects handlers, spawns async ones first, then runs sync handlers serially by `order`. | `hook-hub` | `~/.local/state/33god/hook-hub/receipts.sqlite3` (`invocations`, `executions`, `receipt_events`). The `session_id` query param on the HTTP API is ignored, so use SQL. Order by `receipt_events.sequence`, never by `at`. About 4 days of retention. |
| 4 | Sync handlers inject context: skill-reminder, crank-tag, hindsight-recall (one `hindsight memory recall` subprocess per bank), codegraph-prompt, automaticai-routing-start (codex), hub-selftest. | `hook-hub` + `hindsight` + `skillex`... | The merged text lands in the Claude transcript as a `hook_additional_context` attachment, and in Codex as `response_item` role=developer. The Hindsight server audit (`hindsight audit list <bank> --action recall --start-date --end-date -o json`) holds the exact query and the ranked memories. Join it by bank and time, because it carries no id. Journal: `~/.agents/journal/sessions/<cli>-<sid>.jsonl`. |
| 5 | The async `bloodbank-publisher` runs agent-hooks `publish.py`. It folds into ASM (Redis), then core-NATS PUBs the CloudEvent. `sent` only means a PONG came back. | `agent-hooks`, `asm`, `bb-nats` | The receipt `executions.event_id`. Redis `asm:t:<cli>:s:<sid>` (stream) and `asm:a:<cli>:s:<sid>` (hash), with a TTL of 900 s. `~/.local/state/33god/asm/transitions.log` (local time). Each ASM edge creates an extra hub invocation `native=transition` with `session_id` NULL. |
| 6 | JetStream stores it in `BLOODBANK_EVENTS` (7 d). | `bb-nats` | Holocene `~/.local/state/holocene/events.sqlite3 events(event_id UNIQUE, stream, sequence, subject, type, collected_at, envelope)` gives the event id to seq lookup. Consumer inventory: `GET :8222/jsz?streams=true&consumers=true&config=true`. Core subscribers: `/connz?subs=detail`. |
| 7 | Fan-out. Durable: `candystore-events` (Dapr, via the queue group), `enricher-events` (Dapr, ignores turn.started). Ephemeral: Holocene ordered consumer. Core: ntfy-router (`bloodbank.evt.>`), deckard (`conversation.turn.>`), turn-enricher (`turn.completed`). | `candystore`, `bb-dapr`, `enricher`, `holocene`, `ntfy-router`, `deckard`, `turn-enricher` | Candystore Postgres `events.received_at` is the archived-at time. The HTTP API hides it, so use `docker exec candystore-postgres psql`. Holocene `collected_at`. Docker log lines from `bloodbank-ntfy-router` (`routed:` / `rate-limited:` / `digested:`) carry the type only, so match by time. `dead_letter` holds the enricher's dropped `report.session.completed`. |
| 8 | hook-hub mirrors each receipt as `bloodbank.agent.hook.updated` (correlationid = invocation_id, real PubAck, coalesced). | `hook-hub` | Candystore and Holocene, by correlationid = invocation_id. |
| 9 | The model call goes through the AutomaticAI gateway. | `aai-gateway`, `aai-llm-observability` | The transcript (`api-request`, assistant `requestRef`, `usage`, `requestedModel`, `message.model`). `bloodbank.llm.usage.recorded` in Candystore: correlationid is its own id, so filter `data->>'session_id'` in a time window. Usage lands about 1.5 to 7 s after the call, and `occurred_at` is the completion time. Fallback hops need `/api/automaticai/traces/{request_id}` (admin PAT, opt-in `--deep`). |
| 10 | Tools: PreToolUse, then the tool runs, then PostToolUse. Each step is its own hook invocation and handler set, plus `agent.tool.requested` / `completed` events. | same as 3-8 | `tool_use_id` = `toolu_…` = `hook_success.toolUseID` = Candystore `data.tool_call_id`. Tool events do NOT carry a turn_id (`turn_number` is a tool counter), so attribute them by time window between turn.started and turn.completed. |
| 11 | Stop: `conversation.turn.completed`, then turn-enricher (Jev gate) `turn.annotated` (causationid = turn.completed id, about 330 ms later). hindsight-turn buffers the turn in `~/.local/state/33god/hook-hub/capture/<cli>-<sid>.json`. The Hindsight document `session-<cli>-<sid>` is POSTed only at 9000 or more chars, SessionEnd, or after 2 h idle. | `turn-enricher`, `hindsight` | Candystore, the capture file, the journal (`session_flush*`). |
| 12 | Silent failures seen live, which a waybill must surface rather than hide: `codegraph-prompt` and `code-review-graph-*` report `handler_binary_missing` (the hub PATH has no mise shims). `claude-notify` is a broken symlink. `candystore-context` fails on every SessionStart. The enricher's session reports are dead-lettered. ASM never reaches `gone`. `traceparent` is all zeros on every event. | various | Receipts, `dead_letter`, the ASM hash. |

Causation on the bus is a **linear per-session chain**: `causationid` = the previous event the publisher
emitted for that session. `session.started.id == session_id`. Service-produced events (turn.annotated,
project.artifact.created) carry true causation. The waybill reconstructs the real DAG from the
sources above and keeps the bus's chain as `attrs.causationid` only.

## 2. File format: `33god.waybill` v1

One UTF-8 JSON object. Filename `<id>.waybill.json`. All times in spans and events are **milliseconds
relative to `clock.t0`** (floats allowed). Absolute ISO-8601 UTC timestamps live in `attrs.at` when useful.
Unknown fields must be ignored by readers. A reader rejects an unknown **major** `version`.

```ts
interface Waybill {
  format: '33god.waybill'
  version: 1
  id: string                     // 'wb_' + 26-char sortable id (time-based)
  title: string                  // human, e.g. 'claude · "Read the candystore README…" · 41 s'
  recorded_at: string            // ISO
  recorder: { name: 'waybill', version: string, host: string, mode: 'record' | 'capture', profile: 'full' | 'public', argv?: string[] }
  origin: {
    cli: 'claude' | 'codex' | string
    surface: 'claude-code' | 'claude-code-headless' | 'codex-cli' | 'codex-exec' | 'codex-desktop' | string
    session_id: string
    turn_id: string | null       // Claude '<sid>:turn:N', Codex native UUIDv7
    turn_index: number | null
    cwd: string | null
    project: string | null       // repo / bank name
    model: { requested: string | null, served: string | null } | null
  }
  prompt: { text: string | null, chars: number, sha256: string, truncated: boolean }
  clock: { t0: string, t_end: string, duration_ms: number, settle_ms: number }   // t0 = the submit instant
  components: Record<string, Component>
  spans: Span[]
  events: BusEvent[]
  links: Link[]
  artifacts: Record<string, Artifact>
  gaps: Gap[]
  findings: Finding[]
  sources: Source[]
  stats: Record<string, number>  // free-form counters: spans, events, tools, llm_calls, tokens_in, tokens_out, handlers_skipped ...
}

interface Component {
  id: string                     // registry id (33god-platform/components/<id>.yaml) or 'ext:<name>'
  name: string                   // display name
  kind: 'cli' | 'service' | 'handler-host' | 'bus' | 'store' | 'memory' | 'model' | 'device' | 'external' | string
  registry: boolean              // true when a registry record exists
}

type SpanKind =
  | 'prompt'      // root: the typed prompt (component = the CLI)
  | 'hook'        // one native hook invocation as a whole (a parcel); parent = prompt/llm/tool
  | 'handler'     // one hook-hub execution (a job card); parent = hook
  | 'context'     // the injected context that went back to the model (the briefing card)
  | 'memory'      // Hindsight recall / buffer / retain / consolidation
  | 'publish'     // a producer putting an event on the bus
  | 'consume'     // a consumer receiving/acting on an event (archive, collect, route, enrich, ignore)
  | 'state'       // ASM transition, painter, Redis write
  | 'notify'      // ntfy push, nanoleaf, Orca, sound, Stream Deck
  | 'llm'         // one model request through the gateway
  | 'tool'        // tool_use -> tool_result
  | 'file'        // a local state file written
  | 'turn'        // the turn as a whole (prompt submit -> Stop), optional umbrella
  | string

interface Span {
  id: string                     // deterministic, see section 3
  kind: SpanKind
  component: string              // key of components
  name: string                   // short label, e.g. 'hindsight-recall', 'turn.started', 'Bash'
  summary: string                // one human sentence, used verbatim by `show` and the Factory caption
  phase: 'prompt_submit' | 'model_call' | 'pre_tool' | 'tool' | 'post_tool' | 'turn_end' | 'async_after' | 'session_start' | 'session_end'
  t0: number                     // ms from clock.t0
  t1: number | null              // null = instant or never finished
  status: 'ok' | 'skipped' | 'failed' | 'timeout' | 'pending' | 'dropped' | 'unknown'
  reason?: string | null         // e.g. 'handler_binary_missing', 'not_a_crank_prompt', 'ask_buffered'
  sync?: boolean                 // true when the prompt WAITED on it (sync handler, llm, tool)
  parent?: string | null         // display tree parent (hook -> handler); causation lives in links
  refs?: { invocation_id?: string, event_id?: string, tool_use_id?: string, request_id?: string, seq?: number, handler_id?: string, [k: string]: unknown }
  attrs?: Record<string, unknown>
  payload?: string               // artifact id
  evidence: string[]             // source ids that observed it; [] = inferred
}

interface BusEvent {
  id: string                     // CloudEvent id (the Note ID)
  type: string                   // bloodbank.conversation.turn.started
  subject: string | null         // bloodbank.evt.conversation.turn.started
  stream: string | null          // BLOODBANK_EVENTS | null (core only)
  seq: number | null             // JetStream stream sequence (the belt number)
  t: number                      // envelope time, ms from t0
  stored?: number | null         // JetStream/Holocene collected_at
  archived?: number | null       // Candystore received_at
  correlationid: string | null   // the barcode
  causationid: string | null     // the bus's "came after"
  producer: string | null
  publisher_span: string | null  // span id that published it
  consumers: Consumer[]
  payload?: string               // artifact id of the full envelope
  schema?: { file: string | null, valid: boolean | null, errors?: string[] }
}

interface Consumer {
  name: string                   // 'candystore-events', 'holocene', 'ntfy-router', ...
  component: string
  kind: 'durable' | 'ephemeral' | 'core'
  filter: string | null
  outcome: 'archived' | 'collected' | 'routed' | 'rate-limited' | 'digested' | 'ignored' | 'enriched' | 'delivered' | 'dropped' | 'unknown'
  t?: number | null
  evidence: 'observed' | 'inferred'
  span?: string | null           // consume span id, when one exists
}

interface Link {
  from: string                   // span id or 'evt:<event id>'
  to: string
  kind: 'calls' | 'runs' | 'publishes' | 'delivers' | 'injects' | 'feeds' | 'triggers' | 'writes' | 'records' | 'mirrors' | 'causes'
  label?: string
}

interface Artifact { mime: string, bytes: number, sha256: string, truncated: boolean, text?: string, json?: unknown, note?: string }

interface Gap {                  // expected but not observed, or not observable at all
  component: string
  what: string
  why: string
  severity: 'info' | 'warn' | 'broken'
  span?: string | null
}

interface Finding {              // something is wrong, with proof
  severity: 'info' | 'warn' | 'broken'
  title: string                  // 'codegraph-prompt never runs: binary not on hook-hub PATH'
  detail: string
  component: string
  evidence: string[]             // span ids / event ids / source ids
}

interface Source {
  id: string                     // 'hookhub', 'candystore', 'holocene', 'nats', 'transcript', 'gateway', 'hindsight', 'asm', 'logs', 'files', 'live-nats', 'live-redis'
  kind: string
  locator: string                // path / URL / command (never a credential)
  status: 'ok' | 'empty' | 'error' | 'skipped'
  items: number
  ms: number
  error?: string | null
}
```

### Profiles

- `full` (default for local files): prompt text, injected context, recall memories, tool inputs
  and outputs, each artifact truncated at 64 KiB.
- `public` (default for `waybill publish` and for samples committed under `manual/sandbox/public/waybills/`):
  - prompt text is kept;
  - injected context, memory texts and tool outputs are cut to 280 chars;
  - environment values are dropped;
  - home-directory paths become `~`.

Both profiles always pass every string through a credential scrubber (op tokens, `sk-…`, bearer tokens,
`ghp_…`, AWS keys, JWTs, and URL user:pass) that replaces each match with `«redacted»`.

## 3. Deterministic ids

Collectors run independently and link to each other's spans by computing the same ids. Use exactly these:

| Thing | Span / node id |
|---|---|
| the typed prompt | `prompt` |
| the turn umbrella | `turn` |
| hook invocation | `hook:<invocation_id>` |
| hook-hub execution | `handler:<invocation_id>:<handler_id>` |
| injected context for an invocation | `context:<invocation_id>` (merged), `context:<invocation_id>:<handler_id>` (split) |
| bus event | `evt:<event id>` (used in links; the event itself lives in `events[]`) |
| publish of an event | `publish:<event id>` |
| a consumer acting on an event | `consume:<consumer name>:<event id>` |
| model request | `llm:<n>` with n = 1-based order within the turn; refs.request_id = gateway request_id, refs.client_request = transcript api-request id / Codex response_id |
| tool call | `tool:<tool_use_id>` |
| Hindsight recall per bank | `memory:recall:<invocation_id>:<bank>` |
| Hindsight buffer / flush | `memory:buffer:<invocation_id>`, `memory:flush:<operation_id>` |
| ASM transition | `state:asm:<stream entry id or at_ms>` |
| notify | `notify:<channel>:<event id or at_ms>` |
| file written | `file:<sha1(path)[:12]>:<at_ms>` |

Component of a `handler` span is always `hook-hub`; attrs.handler_id and attrs.mode carry the rest.
The effect a handler causes (recall, publish, ASM) is its own span at the effect's component, linked
`handler -> effect` with `calls`/`writes`/`publishes`.

## 4. Package layout (`33god-platform/waybill/`)

```
waybill/
  SPEC.md                 this file
  README.md
  mise.toml               tasks: test, install (symlink ~/.local/bin/waybill), record, capture, show
  bin/waybill             launcher -> python3 -m waybill
  waybill/__init__.py     VERSION
  waybill/model.py        Fragment + helpers (ids, time, scrub, artifacts) — shared contract
  waybill/collectors/     one module per source; each exposes collect(ctx) -> Fragment
    hookhub.py candystore.py holocene.py nats.py transcript_claude.py transcript_codex.py
    gateway.py hindsight.py asm.py logs.py files.py
  waybill/window.py       resolve (session, turn) -> TurnWindow (t0, t_end, cli, surface, turn_id, transcript path)
  waybill/assemble.py     merge fragments -> Waybill; dedupe spans by id; drop dangling links into gaps; derive findings; stats; title
  waybill/live.py         `record`: arm taps (core NATS sub bloodbank.evt.> + deckard.evt.attention, Redis SUBSCRIBE nlp:events / asm:*), wait for the next prompt_submit receipt, follow until Stop + settle, snapshot short-lived state (ASM, capture buffer) before it expires, then run capture with live fragments merged in
  waybill/show.py         terminal waterfall
  waybill/publish.py      profile=public, then ~/.agents/skills/artifacts/scripts/publish.py, print the Factory URL
  waybill/cli.py          argparse entry point
  schema/waybill.v1.schema.json
  tests/                  unittest, fixtures from real captured data (scrubbed)
  research/understand.json  the 2026-11-15 discovery dump that grounds this spec
```

Stdlib only, plus `nats` (nats-py, already importable by `/usr/bin/python3` 3.14) for live mode and
seq lookups, imported lazily. Postgres reads use `docker exec candystore-postgres psql` with the
container's own env, so no credential lives in this repo. Every collector is **read-only**.
It must never create a JetStream consumer, write to Redis, or POST anywhere, and it must fail soft: an
error becomes `Source.status = 'error'` plus a `Gap`, never a crash.

## 5. The Factory player (`manual/sandbox/src/waybill/`)

- New store mode `'waybill'` next to `'sandbox' | 'tour'`. Entering it pauses the ambient sim.
- Loaders:
  - `?waybill=<url>`: absolute, or relative to `BASE_URL` (`waybills/<file>`); MinIO allows any origin.
  - drag-and-drop or a file picker;
  - a sample list from `public/waybills/index.json`.
- Director (a pure function, `waybill -> Stop[]`):
  - groups spans into **stops** by component, in causal and time order;
  - collapses tool loops into one stop with a per-tool count;
  - marks sync spans as "the prompt waited here".
- Each stop flies the camera with the existing `setFor()` machinery.
- Stations are resolved through a registry-id table; unmapped components get auto-placed kiosks.
- Hero form by kind:
  - hook: parcel;
  - context: briefing card;
  - publish/event: post-it;
  - command: envelope;
  - llm: phone call to the staffing desk;
  - memory: library slip;
  - tool: toolbox.
- HUD:
  - the DevTools waterfall: rows by component, bars on the real ms axis, sync and async lanes, a playhead, click to inspect;
  - a stop caption card carrying the span `summary`, real ids and timings;
  - play, pause and step;
  - the inspector shows attrs, refs and artifacts;
  - fan-out shows each consumer with observed/inferred evidence;
  - gaps and findings are listed on the end card ("what didn't happen").
- The scripted tour stays reachable at `?tour` until Jarad retires it.

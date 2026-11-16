# Waybill

A flight recorder for one prompt across 33GOD.

A **waybill** is one JSON document (`33god.waybill` v1) that records everything a single prompt turn
caused: the hooks that ran, the context they injected, the model calls and tools, every bus event and
who consumed it, ASM state edges, notifications and memory writes. Each piece has a time, a status,
the evidence it came from, and a cause. It reads like the Chrome DevTools Network panel, except the
unit is a prompt, not a request.

Full contract: [SPEC.md](SPEC.md). JSON Schema: [schema/waybill.v1.schema.json](schema/waybill.v1.schema.json).

Stdlib only. The launcher runs `/usr/bin/python3`; `record` picks a Python that can import `nats-py`.

## Install

```bash
mise run install        # ln -sf .../waybill/bin/waybill ~/.local/bin/waybill
waybill --help
```

Or run `bin/waybill` in place. `mise run test` runs the unit tests (no live systems touched).

## The four commands

```bash
waybill capture --session <sid> [--turn N | --latest | --at <ISO>] [--cli claude|codex] [--profile full|public]
waybill record  [--cli claude|codex] [--profile full|public]
waybill show    <file.waybill.json> [--width N] [--all] [--no-color]
waybill publish <file.waybill.json> [--full] [--name N] [--dry-run]
waybill list    [--cli claude|codex] [--limit N] [--json]     # pick a turn to capture
```

**capture** rebuilds a past turn from what every source still holds. It resolves the turn window
(from the transcript, falling back to the hook-hub receipts), runs all collectors in parallel, each with
its own deadline, and assembles the file. Without `--session` it takes the most recent prompt on the
machine. `--at` picks the turn whose prompt was submitted at or just before that time. Takes 3 to 6 s.
Hook-hub receipts keep about 4 days, so older turns come back thinner (the gaps say so).

**record** arms live taps before you type: a core-NATS subscription on `bloodbank.evt.>` and
`deckard.evt.attention`, and a `redis-cli PSUBSCRIBE` on `nlp:events` and `asm:*`. Both are
subscribe-only; nothing is published and no JetStream consumer is created. It waits for the next
prompt (any CLI, or the one you name), follows the session to Stop while snapshotting the ASM stream
(its 900 s TTL is short), waits `--settle` seconds (default 15) for late consumers, then assembles with
the live taps as extra evidence. Ctrl-C writes whatever it has. Live mode sees things capture cannot:
exact ASM edge times and reasons, nanoleaf pane colours, the bus as it happened.

**show** prints the waterfall: one row per span with start, duration, status glyph, component and a
bar on a shared time axis. Events hang off the span that published them with a fan-out line
(stored and archived deltas, then each consumer's outcome). Tool loops and repeated events collapse
unless you pass `--all`. Findings, gaps and per-source status follow.

```
start    dur       component      name                       │0       1s       2s       3s│
     0ms   2.41s ✓ ext:claude-co… turn                       │▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒│
    21ms   831ms ✓ hook-hub       ⧉ UserPromptSubmit         │███████                    │
   277ms   188ms ✓ hook-hub         hindsight-turn           │  ▒▒▒                       │
   331ms   371ms ✓ agent-hooks      conversation.turn.started│   ▒▒▒▒▒▒                  │
                                      ↳ conversation.turn.started · seq 10430870 · archived +6ms
                                         →  ●candystore-events archived  ●holocene collected
   952ms   1.38s ✓ aai-gateway    model call 1               │          ████████████      │
```

Glyphs: `✓` ok, `·` skipped, `✗` failed, `⏱` timeout, `…` pending, `⊘` dropped. Bars: `█` synchronous,
`▒` async, `┄` still open, `◆` instant, `░` a collapsed group.
`●` is an observed consumer outcome, `○` an inferred one.

**publish** converts to the `public` profile, publishes through the artifacts skill to MinIO
(`https://s3.delo.sh/projects/<project>/<date>/<name>/`), reads it back anonymously, then prints the JSON
URL and the Factory link. `--dry-run` runs the publish script without uploading. `--full` publishes the
full profile as is (only the credential scrubber still runs).

## How the Factory plays it

The Factory (`manual/sandbox`, https://manual.delo.sh/sandbox/) replays a waybill as a camera tour of the
real components, from the prompt's point of view. Open a published file with a deep link:

```
https://manual.delo.sh/sandbox/?waybill=<urlencoded https url of the .waybill.json>
```

`waybill publish` prints that link on its last line. The player reads `components`, `spans`, `events`,
`links` and the clock; unknown fields are ignored, and an unknown major `version` is rejected.

## Profiles

| | `full` | `public` |
|---|---|---|
| default for | local files from `capture` / `record` | `waybill publish`, committed samples |
| prompt text | kept | kept |
| injected context, memory texts, tool I/O | up to 64 KiB each | cut to 280 chars |
| environment values | kept | dropped |
| home paths | as is | `~` |
| credential scrubber | always | always |

The scrubber replaces op tokens, `sk-…`, bearer tokens, `ghp_…`, AWS keys, JWTs and URL `user:pass`
with `«redacted»` in both profiles.

## Data sources

All reads are read-only: sqlite via `mode=ro`, redis `GET/HGETALL/XRANGE/SCAN/TTL/TYPE/SUBSCRIBE`,
Postgres via `docker exec candystore-postgres psql` with `default_transaction_read_only=on`, HTTP GET,
`docker logs`. No credentials live in this repo.

| Collector | Source | Gives |
|---|---|---|
| `hookhub` | `~/.local/state/33god/hook-hub/receipts.sqlite3` | hook invocations, per-handler status and reason, timings, the publisher's event id |
| `transcript_claude` | `~/.claude/projects/*/<sid>.jsonl` | prompt, injected context, model calls with usage, tools, turn end |
| `transcript_codex` | `~/.codex/state_5.sqlite` + rollout file | the same for Codex (CLI, exec, Desktop) |
| `candystore` | `:8683` HTTP + `candystore-postgres` | archived-at time, dead letters, the stored envelope |
| `holocene` | `~/.local/state/holocene/events.sqlite3` | JetStream sequence and collected-at per event |
| `nats` | `:8222/jsz` and `/connz` | consumer inventory (durable, ephemeral, core) for fan-out |
| `gateway` | Candystore `llm.usage.recorded` rows | which gateway call served which model call |
| `hindsight` | journal, audit list, capture buffer | memory recall and retain, buffered turns |
| `asm` | Redis `asm:*` + `transitions.log` | agent state edges |
| `logs` | `docker logs` of ntfy-router, enricher, turn-enricher, daprd; `publish-errors.log` | notifications, publish failures |
| `files` | agent-hooks state, session-proof, journals | session files the pipeline wrote |
| live taps | NATS core, redis pub/sub | record mode only |

A collector that fails or times out becomes a source with `status: error` and a gap. Capture never aborts on one.

## Blind spots

A waybill states what it could not see. Each blind spot below is a `gaps[]` entry in the file.

**Silent failures it surfaces** (SPEC section 1, row 12): `codegraph-prompt` and `code-review-graph-*`
report `handler_binary_missing` because the hook-hub PATH has no mise shims; `claude-notify` is a broken
symlink; `candystore-context` fails on every SessionStart; the enricher's session reports are dead-lettered;
ASM never reaches `gone` for session-keyed scopes; `traceparent` is all zeros on every event, so the
waybill reconstructs causation itself (the bus's own `causationid` is a per-session linear chain and is
kept only as `attrs.causationid`).

**Gaps it cannot close:**

- `bb-hook` timing and fail-open exits leave no trace on the client side.
- hook-hub stores no handler stdout or stderr. Injected text survives only in the CLI transcript or rollout.
- A publisher `sent` is a core-NATS PONG, not a JetStream ack. Events that were never stored are flagged.
- The consumer inventory is a snapshot taken at capture time. Consumers created or removed since are not reflected.
  Observed consumer outcomes are marked `observed`; the rest are `inferred` from the inventory.
- ASM Redis streams expire after 900 s. After that, edge times fall back to `transitions.log` (1 s resolution, no reason).
- nanoleaf pane colours and the zellij tab painter keep no history.
- ntfy-router log lines carry the event type only; notify spans are matched by type and time.
- The Hindsight capture buffer is deleted at session end.
- Gateway fallback hops need `--deep` and an admin token.
- Headless (`-p`) Claude sessions and in-progress turns have no `turn_duration`; the turn end is estimated.
- Receipts keep about 4 days.

## Layout

```
bin/waybill                launcher
waybill/model.py           shared contract (Fragment, Span, BusEvent, ids, scrubber)
waybill/collectors/        one module per source; REGISTRY in __init__.py
waybill/window.py          turn window resolver
waybill/assemble.py        merge, joins, rebase, gaps, findings, stats, profiles
waybill/cli.py live.py show.py publish.py
schema/waybill.v1.schema.json
tests/                     python3 -m unittest discover -s tests
```

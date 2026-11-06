# ASM (Agent State Machine) as it runs on 2026-11-06

## Summary

ASM is a Redis-backed fold of every agent CLI's hook events into one state per agent. It is written by a Lua script that runs atomically in Redis. It lives inside `delorenj/bloodbank` at `services/agent-hooks/` and is plain Python stdlib plus Lua, with no package.

The design is sound, but how it is wired today breaks it. On 2026-09-13 every CLI's hooks were routed through hook-hub (commit `00f36a8`). Since then the identity ladder no longer finds the agent process. Each Claude agent now has two rows in Redis, rows from different agents collapse onto the hook-hub daemon's pid, `session_id` is empty on every row, and Hermes liveness checks look for systemd units that no longer exist. Every item marked "verified" below was checked read-only against live Redis on 6379, `/proc` and systemd.

**Rule breach to report:** I created two scratch files, `/tmp/asm-keys-survey.txt` (a SCAN dump) and `/tmp/asm-survey-panes.json` (`list-panes` output). I left them in place rather than delete anything. No other file, key or service was touched, and I did not run `test_asm.py` because it writes to production Redis.

---

## 1. What ASM is

### Flow
- The publisher run for each hook calls `asm.record()`. The single call site is `core/publisher.py:134-170` (`_asm_observe`), placed before the alert early-return.
- `record()` maps the event type to a signal, resolves a scope and EVALs `core/asm.lua`. When the derived state changes, it sends a `native:"transition"` frame to the hook-hub socket (`asm.py:298-338, 413-476`).
- `asm.lua` is the only arbiter. It reads the hash, folds counters, derives a state, writes the keys, and on a real edge appends to the stream and publishes. It uses the server clock (`asm.lua:49-50`).
- The sweeper and the surfaces propose through `asm.fire()` (`asm.py:371-410`), which goes through the same Lua.

### Signals (`asm.py:60-74`, `asm.lua:116-186`)

| Signal | Source |
|---|---|
| `start` | `session.started` |
| `prompt` | `turn.started` |
| `tool_req` / `tool_done` | `tool.requested` / `tool.completed` |
| `sub_start` / `sub_done` | `invocation.started` / `invocation.completed` |
| `fail` | `invocation.failed`, or a `tool_done` whose payload carries an error (`asm.py:257-278`) |
| `quiesce` | `session.ended` or `turn.completed` (Stop means the turn went quiet, not that the process exited) |
| `attention` | alert hooks, split into bell or gate by `attention_kind` from `hooks.master.json` |
| `ack` | a surface; may only lower the bell, enforced at `asm.lua:196-204` |
| `discover`, `stale`, `gone` | the sweeper |

### States
`asm.lua:221-258` derives one state from the counters by priority, highest first:

1. `gone` (sweeper verdict)
2. `stale` (sweeper verdict)
3. `awaiting_human` (bell or gate window still open)
4. `failed` (an error within the last 30 s)
5. `delegating` (a subagent lane is live)
6. `tool_running`
7. `working`
8. `starting`
9. `idle`

`unknown` is only produced by `discover` on a row that has no state yet. `gone` deletes the row after publishing (`asm.lua:345-356, 395`).

### Fields in the `asm:a:{scope}` hash
Verified live with HGETALL (27 fields): `state prev since prev_held_ms seq turn tools subs blocked_until gated_until block_kind err_ms last_ms scope sv cli pid starttime cwd basis zellij_session zellij_pane correlationid session_id last_role profile main_lane`.

### Agent identity: the five-rung ladder (`asm.py:168-229`)

| Rung | Method | Scope format |
|---|---|---|
| 1 | `CLAUDE_PID` / `CODEX_PID` env | `cli:p:pid.starttime` |
| 2 | `HERMES_HOME` profile | `hermes:a:<profile>` |
| 3 | walk up `/proc` ancestry matching comm | `cli:p:pid.starttime` |
| 4 | session id from the payload (`session_id`, `sessionId`, `conversationId`) | `cli:s:<sid>` |
| 5 | parent pid | `cli:x:ppid.starttime` |

The pane and the correlationid are deliberately never used as identity. The pane is carried as a field plus a secondary index (`asm.py:451-453`).

### Key schema
Verified by SCAN: 94 `asm:*` keys.

| Key | Type | Live count | Notes |
|---|---|---|---|
| `asm:a:{scope}` | hash | 37 | TTL 900 s |
| `asm:t:{scope}` | stream | 36 | MAXLEN about 500, TTL 900 s; field `j` holds the transition JSON |
| `asm:lane:{scope}` | zset | 0 | |
| `asm:live` | zset | 1 key, 37 members | TTL 900 s, trimmed both ways |
| `asm:idx:pane:{sess}:{pane}` | string | 18 | |
| `asm:seen` | hash | 1 key, 70 fields | `cli|type` and `profile|<name>`, TTL 30 days |
| `asm:sweeper` | string | 1 | `pid:bootid`, EX 60 |
| `holocene:tooling:stat:agent-state-machine` | string | 1 | EX 90 |
| `asm:transitions` | pub/sub channel | 2 subscribers | |

The README key table (`README.md:416-424`) omits `asm:seen`, `asm:sweeper` and the Holocene key.

Redis is 8.0.2 with `maxmemory 0` and `noeviction`. It is shared with the nanoleaf wall and Holocene, which is why every ASM key carries a TTL.

### Writers
- **Hook path:** all nine CLIs go through `bb-hook`, which hands each hook to hook-hub (pid 22822). The hub starts `publish.py` as an async handler (`hub.py:604-616`). Attention alerts reach ASM because `hub.py:188-189` gives them the event type `deckard.v1.agent.attention`.
- **Sweeper:** `asmctl sweep` (`sweep.py`).
- **Surface `ack`:** `asm-tabpaint` (`asm-tabpaint:184-200`).
- **Holocene stat:** written by the sweeper (`sweep.py:252-340`).

### Readers
- `asmctl` (`ls`, `watch`, `log`, `tail`, `agents`, `who`).
- `asm-tabpaint` and `asm-orcapaint`. These are the two `asm:transitions` subscribers, though I did not check which clients they are.
- Hub handlers `asm-log` and `asm-stale-alert` (`hook-hub/handlers.toml:308-322`). Their scripts live in the `delorenj/agents` repo at `~/.agents/hooks/asm/*.sh`. `asm-blocked-amber` is disabled.
- Holocene `apps/api/src/hub.ts:208-241` (`hermes:a:*` rows only, plus `asm:sweeper`) and `tooling.ts:151` (the stat key).
- Flume `flume-hr/src/org/live.ts:117-123` (`asm:a:hermes:a:<profile>` via `redis-cli`).
- Wingman `src/wingman/sources/fleet.py:92` and `events.py:30`.
- `health/hook_telemetry.py:49` (`asm:seen`).
- **Not read by:** Deckard (no `asm:` reference in `~/code/deckard`), pjangler, or the asm pane index (no reader anywhere).

### Bloodbank events
- **Consumed:** none from the bus. ASM folds, inside the publisher process, the event type that the publisher is about to send.
- **Published:** none to the bus. The hub skips publishing for `transition` frames (`hub.py:604`). Transitions only go to Redis pub/sub and the hub socket, so ASM history is never durable: each stream is capped at about 500 entries and expires after 900 s.

---

## 2. What ASM knows about terminal location and native sessions

### Zellij location
- It stores only `zellij_session` and `zellij_pane`.
  - On the hook path these come from the hook env, forwarded by the `bb-hook` allowlist (`hook-hub/client/bb-hook:63-64`).
  - On the sweeper path they come from `/proc/<pid>/environ` (`core/agents.py:76,95`).
- Stored in the hash and in the transition JSON (`asm.lua:282-283, 375-376`).
- **Not stored:** tab id, tab name, tty (`SSH_TTY` is forwarded but unused), terminal pid, focus.
- `asm:idx:pane` points from a pane to a scope, is last-writer-wins, and nothing reads it.
- Tab topology exists only in `asm-tabpaint`'s memory:
  - It parses the text output of `list-panes --tab` every 5 s and `list-tabs --state` (`asm-tabpaint:117-156`).
  - The session name is hard-coded to `Workspace` (`asm-tabpaint:96`, and in the unit file).
- `asmctl who` gets the focused pane from `zellij action list-clients` (`asmctl:176-185`).

### Native sessions

**Claude**
- The session id survives only as the scope suffix `claude:s:<sid>`, from rung 4, and as `main_lane` (from the forwarded `CLAUDE_CODE_SESSION_ID`, `asm.py:241`).
- The `session_id` field is never written; see section 5.
- ASM never reads `~/.claude/sessions/<pid>.json`. Verified: `665090.json` has `sessionId=c2658124…`, which is this session's `claude:s:` scope.

**Codex**
- `CODEX_THREAD_ID` is forwarded by `bb-hook:117` but ASM never uses it. `CODEX_PID` is not forwarded.
- No live `codex:s:` rows exist. I did not verify whether the Codex payload carries a session id.

**Hermes**
- Identity is the profile from `HERMES_HOME`, which is forwarded (`bb-hook:118`).
- ASM knows no Hermes session id.

**The hub already resolves more than ASM uses.** `receipts.py:58-65` (`native_session_id`) reads `session_id`, `sessionId`, `sessionID`, `thread_id` and `threadId`, plus env fallbacks. The hub passes `BB_HOOK_SESSION_ID` and `BB_HOOK_PARENT_PID` to every handler (`hub.py:252-253`). ASM reads neither.

---

## 3. What ASM does not do, and which callers do it themselves

| Responsibility | ASM today | Who does it instead (evidence) |
|---|---|---|
| Pane and tab topology | Has no topology model. `asm-tabpaint` keeps a private in-memory copy | Deckard `crates/deckard-mux/src/panes.rs` and `proc.rs`; pjangler `src/crank/panes.ts` and `index.ts`, which is on main since `dd9eb4e` (the digest saying "not on main" is out of date); Wingman `sources/zellij.py`; zcrank |
| Agent process detection | Partial. `core/agents.py:28-99` matches exact comm against 7 names (no gemini, kimi, openclaw or agy, and it misses CLIs launched through node or python) | Deckard `proc.rs` (argv-based; the module doc says it uses `/proc` plus `ZELLIJ_PANE_ID`); pjangler `panes.ts:41` (a port of `proc.rs` with a starttime guard) |
| Session-file lookup (pid to session) | None | pjangler `panes.ts:365` (`readClaudeSession`) |
| Tab painting | Yes: `asm-tabpaint` (glyph renames) and `asm-orcapaint` (Orca cards) | Deckard paints its own Stream Deck from its own state |
| Pane input (keys, text) | None | zcrank engine uses raw `write-chars`. Whether Deckard sends input is unverified |
| Focus and navigation | None; it only reads the focused pane in `asmctl who` | Deckard `deckard-mux/src/cli.rs` / `source.rs` (`go-to-tab-by-id`), per the survey; not re-verified |
| A second state machine | ASM says it is the only one (`README.md:380`) | Deckard runs its own fold of bus events, `/proc` and the pane map (`deckard-daemon/src/agents.rs:1-40`). The README claim is out of date and the code proves it |

---

## 4. Packaging

### Repo and layout
- Repo: `git@github.com:delorenj/bloodbank.git`, the `33GOD/bloodbank` submodule at `613d485`.
- Files: `services/agent-hooks/{core/asm.py, asm.lua, sweep.py, agents.py, board.py, resp.py; bin/asmctl, asm-tabpaint, asm-orcapaint; ops/systemd/asm-*; tests/test_asm.py}`.
- The handler scripts live in a different repo, `delorenj/agents` (`~/.agents/hooks/asm/`).
- 16 commits touch ASM files, from `9abd694` (2026-09-05) to `b6dd519` (2026-10-30). The last one changed only the hub socket path in `asm.py`.

### Runtime and install
- Python 3, stdlib only, with its own RESP client (`core/resp.py`), plus Redis Lua.
- No `pyproject` and no install step. Units run `/usr/bin/python3` directly from the git checkout.
- The four units in `~/.config/systemd/user` are symlinks into `ops/systemd/` and match the repo copies.
- `mise run asm:install` (`bloodbank/mise.toml:229-242`) links only the sweep units. The `tabpaint` and `orcapaint` symlinks were made by hand; there is no mise task for them.

### Processes running now (verified)
- **Hook path:** one async `publish.py` child of hook-hub per hook, with publish slots set to 2 (`hub.py:57`).
- **`asm-sweep.timer`:** enabled, oneshot every 15 s (`OnUnitActiveSec=15s`). It writes about two journal lines per tick.
- **`asm-tabpaint.service`:** running, pid 5109.
- **`asm-orcapaint.service`:** running, pid 5351.
- **Per-transition bash spawns:** `asm-log` (pattern `^.+->.+$` matches every edge, so it spawns a bash on every transition; `transitions.log` rotates at 1 MB, about daily) and `asm-stale-alert`.

### The Candybar clock rule
- `asm-sweep.timer` is a native systemd timer running outside Candybar.
- There is an exception record at `candybar/deploy/scheduling-policy.json:43-46` ("Canonical exclusion (c): sub-minute 15s agent liveness guard") and `cron-inventory.md:149`.
- `~/.agents/AGENTS.md:70-72` says only `candybar-watchdog.timer` is exempt, and that any other exception needs an owner-approved record "in its component". This record sits in Candybar, not in bloodbank, and bloodbank's unit file and README don't mention it. Whether it counts as owner-approved is unverified.
- `bloodbank-agent-hooks-health.timer` is retired and not active.

### Tests
- `tests/test_asm.py` has 76 tests in 9 classes and runs the real Lua against Redis.
- By default it targets production `127.0.0.1:6379` (`test_asm.py:23`).
- CI runs only `test_attention*.py` (`.github/workflows/ci.yml:64`), so ASM has no CI coverage. There is no test for whether `session_id` gets filled in.

### Coupling to the rest of bloodbank
- Imports `core.resp`, `core.board` and `core.agents`.
- Hard-wired into `publisher.py`.
- The hub special-cases `transition` (`hub.py:604, 656-658`) and holds the handler rows (`handlers.toml:297-335`).
- `hook-hub/hindsight.py:277-283` copies the identity constants (`IDENTITY_ENV_FOR_CLI`, `NOT_AN_AGENT_PROFILE`).
- Shares `BLOODBANK_*` env switches and the hook-hub socket.
- Its key schema is read directly by Holocene, Flume and Wingman, with no API in between.

---

## 5. Defects and gaps (verified unless marked)

**D1. `session_id` and `correlationid` are always empty.**
- `record()` hard-codes both to `""` (`asm.py:438`).
- `fire()` copies the already-empty values from the hash (`asm.py:384-399`).
- The sweeper's `discover` call passes neither (`sweep.py:149-156`).
- `asm.lua:284-285` overwrites them on every write.
- Live: 37 of 37 rows have both empty, and the transition JSON leaves them out entirely (`asm.lua:366-384`).
- The line numbers in the brief have shifted. `sweep.py:261-307` is now `write_holocene_stat`, which emits no session id; the `discover` proposal is at `sweep.py:149-156`.

**D2. Routing through the hub broke the identity ladder (`00f36a8`, 2026-09-13).**
- Rung 1: `CLAUDE_PID` and `CODEX_PID` are not in the `bb-hook` allowlist.
- Rung 3: the ancestry walk goes `publish.py` → `hub.py` (pid 22822) → systemd and never finds the CLI.
- Result: Claude lands on rung 4 (`claude:s:<sid>`, pid 0, so `gone` can never be proven), and CLIs without a session id land on rung 5, keyed to the hub pid.
- `BB_HOOK_PARENT_PID` and `BB_HOOK_SESSION_ID` are available but unused. I did not verify that the parent pid's ancestry leads to the CLI.
- `README.md:426` still says the scope is the process. The code and live data disagree, and the code wins.

**D3. Every Claude agent with hooks has two rows.**
- One is an observed `claude:s:<sid>` row; the other is a `claude:p:<pid>` row from `discover`, stuck at `unknown`. Verified on 8 panes.
- Consequences, verified by replaying `asm-tabpaint`'s pane mapping against live Redis (not by watching the bar itself):
  - The tab bar hides bells: panes 93 and 160 are `awaiting_human` but resolve to `unknown`, because the sweeper refreshes the twin row later.
  - The discovered rows read 23 `unknown`, 2 `idle` and 1 `tool_running`, so `asmctl agents` and `asmctl who` see almost nothing as claimable and ticket claiming falls back to the fleet PM.
  - The pane index flips between the two rows every 15 s.
- Wingman documents this split and works around it (`fleet.py:5-10`).

**D4. Ghost rows pinned to the hub pid.**
- `copilot`, `gemini`, `hermes` and `opencode:x:22822.11015` are "stale for 197.9h".
- `claude:x:22822.11015` is "awaiting_human for 163.4h" on pane 41, which does not exist.
- Different agents of one CLI collapse into one row. Because the hub process is alive, the sweeper keeps these rows warm forever (`sweep.py:199-212`).
- The Holocene stat is therefore permanently `critical`, and the pane 89 tab shows red.

**D5. Hermes liveness checks units that no longer exist.**
- `gateway_pids()` queries `hermes-*-gateway.service` (`sweep.py:69-72`), but there is now a single `hermes-gateway.service`. The call returns `{}` (verified).
- So `hermes:a:*` rows can never be marked `gone` or refreshed and just expire on their TTL.
- Only 3 Hermes rows are live, against 29 profiles in `asm:seen`.

**D6. The CLI lists have drifted.**
- `AGENT_COMMS` (`agents.py:28`) and `COMM_FOR_CLI` (`asm.py:85`) differ from each other and from the 9 CLIs in `hooks.master.json`.

**D7. Tests leak into production.**
- The suite targets production Redis by default.
- `asm.lua:391` publishes to the literal channel `asm:transitions`, so test edges reach the live painters.
- `test_sweeper_publishes_its_own_liveness` writes the production `asm:sweeper` key.
- The production `asm:seen` hash has a `test|attention` field, last written 2026-11-04 12:54 EST. I did not find its source.

**D8. Event ordering is no longer guaranteed (unverified inference).**
- Publishing is now async with 2 slots (`hub.py:57, 611`), so two hooks from one agent can be folded out of order.
- For example, a `tool_req` folded after `quiesce` would leave the agent in `tool_running` until the next turn boundary.

**D9. There is no machine interface.**
- `asmctl` has no `--json` output and no scope or state query. The `asmctl scope`/`state --json` interfaces in `/tmp/feature-design.md` §7 do not exist yet.
- Consumers read the raw keys.

**D10. `asm.py`'s own docstrings are out of date.**
- `asm.py:8-20` (a fold "inside the hook", latency against the hook deadline) and `asm.py:96-110` (per-profile gateways) describe the design before the hub.

---

## Responsibilities ASM owns today
1. Folding hook events into one per-agent state (10 states, priority ladder, atomic Lua).
2. Resolving agent identity (the five-rung ladder) — currently broken (D2).
3. Telling a bell from a gate in `awaiting_human`, using `attention_kind` from `hooks.master.json`.
4. Tracking subagent lanes (`delegating`).
5. Detecting `stale` and `gone` through the 15 s sweeper.
6. Agent process discovery from `/proc`, including pane, cwd, Hermes profile and board (`agents.py`, `board.py`).
7. Hermes per-profile liveness — currently broken (D5).
8. A per-agent transition log (stream) and a live edge feed (`asm:transitions`).
9. Dispatching transitions to hook-hub handlers (`asm-log`, `asm-stale-alert`).
10. Hook-fire telemetry (`asm:seen`, per CLI and type and per Hermes profile).
11. The `asm:live` index and the `asm:idx:pane` index (which has no reader).
12. Sweeper liveness (`asm:sweeper`).
13. The Holocene dashboard stat.
14. Surfaces: the `asmctl` CLI (`ls`, `watch`, `log`, `tail`, `sweep`, `agents`, `who`), the zellij tab painter with `ack`, and the Orca card painter (which also reads Plane lanes via Candystore and `px`).
15. Choosing a ticket-claim candidate (`asmctl who`).

## Adjacent responsibilities ASM lacks
1. Native session id as a field (Claude, Codex thread, Hermes session), and joining pid to session via `~/.claude/sessions/<pid>.json`.
2. Using the hub's `BB_HOOK_PARENT_PID` and `BB_HOOK_SESSION_ID` for identity.
3. Merging the observed row and the discovered row into one agent.
4. Correlationid tracking.
5. Pane and tab topology as a shared model: tab id and name, readiness, pane reuse or lifetime. Today it exists only in `tabpaint`'s memory.
6. tty and terminal pid.
7. A single agent-CLI classifier that matches `hooks.master.json`, including CLIs launched through an interpreter.
8. Hermes liveness under the single-gateway layout.
9. Pane input (send keys or text) and focus or navigation.
10. A machine-readable API (`--json`, socket or HTTP) instead of raw Redis keys.
11. Durable history and bus publication of transitions (no `bloodbank.evt.agent.*` event, nothing in Candystore).
12. Reconciling with Deckard's separate state machine.
13. A test Redis kept apart from production, and CI coverage.
14. Scheduling under Candybar, or an exception recorded in bloodbank itself.
15. Being a standalone repo or package: today it sits inside bloodbank, its handler scripts live in `delorenj/agents`, and its identity constants are duplicated in `hook-hub/hindsight.py`.

The key files are all under `/home/delorenj/code/33GOD/bloodbank/services/agent-hooks/` (`core/asm.py`, `core/asm.lua`, `core/sweep.py`, `core/agents.py`, `bin/asmctl`, `bin/asm-tabpaint`, `bin/asm-orcapaint`, `ops/systemd/`, `tests/test_asm.py`), plus `/home/delorenj/code/33GOD/bloodbank/services/hook-hub/client/bb-hook`, `/home/delorenj/code/33GOD/bloodbank/services/hook-hub/hub.py`, `/home/delorenj/code/33GOD/bloodbank/services/hook-hub/handlers.toml` and `/home/delorenj/code/33GOD/candybar/deploy/scheduling-policy.json`.
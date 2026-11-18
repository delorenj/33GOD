# Crank state: crank.lua, Redis and the prompt segment

Crank state lives in Redis (127.0.0.1:6379, AOF on since 2026-11-18). **One writer** holds
it: `crank.lua`, a Redis Functions library named `crank`. Every proposer (pj, zcrankctl,
zcrank.py, the prompt) sends signals or asks questions; none writes a key or carries a copy
of a rule.

## The arbiter

- Source: `~/.agents/tools/jev-clairic/bin/crank.lua`. It is loaded through
  `statekit.Library` (`bloodbank/services/agent-hooks/core/statekit.py`) by
  `crank_arbiter.py`, or by hand with `zcrankctl arbiter-load`. The library carries a
  `crank_version` function, and callers reload it when the sha differs or on
  `ERR Function not found`.
- statekit is the shared kit for 33GOD Redis state machines: a single Lua writer, a resolved
  hash per subject, a capped transition stream, one pubsub channel, a TTL and a heartbeat.
  ASM is consumer 1 and crank is consumer 2. Reuse it for the next state machine instead of
  copying either.
- pjangler's tests vendor `crank.lua` and `statekit_prelude.lua`. A drift test fails when the
  copies diverge, so refresh the vendored copies whenever you change the originals.

| Function | Kind | Does |
|---|---|---|
| `crank_attach`, `crank_fire`, `crank_end` | write | v2 binding hash `crank:b:<binding>` + pane pointer `crank:idx:pane:<session>:terminal_<N>` |
| `crank_get` | read-only | follow a pane pointer to its binding. An expired hash under a live pointer returns `{binding, pane, expired:"1"}` |
| `crank_apply` | write | legacy registry ops: `tab`, `pane`, `clear_panes`, `config`, `log`, `replace_log`, `del`. Validated before any write |
| `crank_resolve` | read-only | the one copy of the legacy on/off + interval rule |
| `crank_scan` | write | the legacy engine's per-tick observation of panes, plus the `crank:engine` heartbeat |

v2 and legacy cannot clobber each other. `crank_scan` and `crank_apply` leave `crank:b:*`
and its pointers alone.

## Keys and channels

| Key | Holds |
|---|---|
| `crank:b:<binding>` | v2: cli, session_id, pid, pid_start, project, root, zellij_session, pane, interval, schedule, candybar_id, next_due, on, since, last_fire, fires, last_class, last_officer(_ms), reclocked_ms |
| `crank:idx:pane:<session>:terminal_<N>` | v2 pane → binding pointer |
| `crank:p:<session>:terminal_<N>` | legacy resolved pane state (on, since, decided_by, interval, keys, owners, last_run, next_due, scan_ms, held, seq). 1d TTL. **Frozen since the legacy beat stopped** |
| `crank:idx:panes` | legacy pane index |
| `crank:t:<session>:<pane>`, `crank:t` | transition streams (capped) |
| `crank:transitions` | pubsub channel, one JSON per edge |
| `crank:engine` | legacy engine heartbeat (ts, scan_ms, session, by, panes) |
| `zcrank:tab:*`, `zcrank:pane:*`, `zcrank:log:*`, `zcrank:config` | legacy registry. See [legacy.md](legacy.md) |

Only edges escape: a signal that changes nothing writes no transition.

## The prompt and status-line segment

`pjangler-prompt` (`pjangler/src/prompt-pipeline.ts`, `readPaneCrank`) pipelines
`HGETALL crank:p:…`, `HGETALL crank:engine` and `FCALL_RO crank_get` over one RESP
connection with a 150ms budget. It is shared by the starship prompt and the Claude Code
status line.

1. **A v2 binding wins:** `⚡ crank ↑<uptime> ↻<interval> ⏳<countdown>`, with the countdown
   read from the binding's own cron. `⚠ crank stalled <age>` appears when no fire has come
   for max(15m, 2×interval + 5m), or when the hash expired under a live pointer.
2. **Legacy fallback:** the `crank:p` hash is believed only while `crank:engine` is from
   **this** zellij session and at most 15 minutes old. Otherwise there is no segment.
   Legacy never yields `stalled` (pjangler `791c615`).
3. Redis down or slow → no segment. It is never shown as OFF.

Outside a zellij pane the segment shows the project's switch through the cached refresher.
After editing the prompt: `npm run build`, then copy `dist/prompt*.js*` into
`~/.local/lib/node_modules/@delorenj/pjangler/dist/`, or reinstall.

## Tests

- pjangler: `TMPDIR=/tmp node scripts/run-tests.mjs --no-build crank prompt`
- jev-clairic: `tests/test_crank_arbiter.py`, `tests/test_crank_review_fixes.py`
- agent-hooks: `tests/test_statekit.py`

All of them start a throwaway redis-server on a port the kernel picks. Never the live 6379.

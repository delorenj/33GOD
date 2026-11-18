# The legacy tab-keyed crank (retired)

**Retired by crank v2 (PJAN-216, 2026-11-18).** Candybar `crank-beat` is disabled, Hermes job
`777c511a009c` (profile `33god-pm`) is paused, and the legacy switches are off. Read this to
interpret old data or the parts still running. Do not use it to turn crank on: use
`pj crank enable` ([sessions.md](sessions.md)).

## What it was

A `*/5` beat over every crank-enabled **zellij tab**. `zcrank-gate` scanned panes and
printed `tab|pane|class` (`poke`, `interrogate<N>`, `long<N>`, `burn<N>`).
`crank-beat-brief.sh` injected `crank-beat-prompt.txt` and `gate-tails.md`, and one
Hermes beat acted on every listed pane. v2 replaced it with one clock and one officer per
session, because a tab is not an agent and the beat cost 600k–1.1M tokens per non-skipped
run.

## Still running or still read

| Piece | Status |
|---|---|
| `crank-watchdog` (Candybar `*/15`) | runs; its report is read by `crank-attention` ([health.md](health.md)) |
| `zcrank-gate.py` attention readers | imported by `crank-attention`, so there is one parser |
| `zcrank_screen.py`, `zcrank.py` classify | shared screen and ASM readers used by `crank-pane` |
| `zcrank-send` | the only way to type into a pane, for every Crank |
| `crank:p:*`, `crank:engine` | frozen; the prompt ignores them once the heartbeat is 15m+ old |

## Registry (zcrankctl)

Every write goes through `crank_apply` and the rule through `crank_resolve`
([state.md](state.md)).

- `zcrank:tab:<tab>` is a hash: `{enabled, interval, root}`. `root` is the main-worktree
  path of the project that owns the switch.
- `zcrank:pane:<owner>:terminal_<N>` is an override, `"0"` or `"1"`, that beats the tab.
- `zcrank:config` holds the global interval. `zcrank:log:<tab>` holds JSON rows.
- Unlisted means OFF.
- Commands: `zcrankctl list | on|off <tab> [--pane N] | pane | history | tail | log | checked | arbiter-load`.
  `list` prints UNKNOWN when the arbiter is unavailable.
- Rule: a pane override under any owner spelling wins, and every override found must be 1.
  Otherwise every tab key must have `enabled=1`. Interval is the longest one set on any key,
  else `zcrank:config`, else 5m.

## Pitfalls that still bite

- Tab names contain spaces. Quote `"$k"`, or drive redis-cli from an argv list.
- Never interpolate JSON into a shell string for `RPUSH`. Use an argv list and read the row
  back.
- `zcrank-scan.sh` changes the stale counters. Never run it as a read-only probe.
- A Hermes `cron/output/777c511a009c/*.md` file proves that an execution produced a file,
  not that anything was attended.

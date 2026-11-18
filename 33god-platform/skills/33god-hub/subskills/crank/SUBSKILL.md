---
name: crank
description: Crank, the 33GOD momentum layer that prods idle agent sessions forward while the operator is away. Crank v2 (PJAN-214/215/216/218) gives one Candybar-clocked crank to every live interactive agent session in a project whose .project.json crank block is on. Covers pj crank (enable, disable, interval, config, sessions, attach, detach, reap, fire, log, tui, panes), the crank-pane gate and crank officer, crank-attention and crank-watchdog, zcrank-send and the [crank] tag, the crank.lua Redis arbiter on statekit, the prompt and status-line crank segment, and the retired tab-keyed legacy beat (zcrankctl, zcrank:tab:*, crank-beat). Use when turning crank on or off, asking "is the crank alive?", seeing "⚠ crank stalled", "crank off" or no crank segment, a pane being poked wrongly or never poked, a binding that will not attach or end, or changing crank code.
---

# Crank

Crank is the operator's stand-in attention. **Crank v2** is the live system: every live
interactive agent session that starts in a crank-enabled project gets its own **binding**.
A binding is one exec Candybar row, `crank-<cli>-<sid8>-<pid>`, clocked on a staggered cron.
Each fire runs `pj crank fire <binding>`, which proves the agent process is still the same
incarnation and then runs the `crank-pane` gate. The gate wakes the LLM **crank officer**
only when the pane needs it. An unchanged pane costs 0 tokens.

The tab-keyed **legacy** crank (zcrankctl switches, `crank-beat`) is retired (PJAN-216). Its
code still runs for reading and as the watchdog's plumbing.

## Rules on every route

- Candybar is the only clock. A binding *is* its Candybar row; never add a timer, cron or
  Hermes schedule for crank. Load the `candybar` skill before touching a schedule.
- Every keystroke into a pane goes through `~/.local/bin/zcrank-send`, which adds the
  `[crank]` tag and checks the screen. Raw `write-chars`, `write` or `paste` is denied for
  Hermes by hook-hub `crank-keys-guard`.
- Crank is not the operator. It never asserts an operator-only fact and never approves
  client-visible sends, spending, deletes, or credential and permission changes. Releases,
  deploys and merges are **not** reserved (standing approval, 2026-11-15).
  → [references/officer-contract.md](references/officer-contract.md)
- Policy is declared, never inferred from a tab or pane name. Use the `.project.json` `crank`
  block, then `~/.config/33god/crank.toml`, then the built-in default.
- `crank.lua` is the only writer of `crank:*` and `zcrank:*` keys. Change state through its
  functions (`pj crank …`, `zcrankctl …`), never with raw `redis-cli HSET`.
- Absent is not OFF. Redis unreachable, an unknown heartbeat or a missing hash means
  *unknown* and shows no segment. Do not read any of them as "crank off".

## Ask the system first

| Question | Ask |
|---|---|
| Is crank on for this project, and why? | `pj crank status` (each value with its source) |
| Which sessions are being cranked right now? | `pj crank sessions --all` |
| What did each fire see and do? | `pj crank log`; `~/.local/state/crank/log/<binding>.jsonl` |
| Did a binding attach or end, and why? | `~/.local/state/crank/hooks.jsonl`, `events.jsonl` |
| Is a binding's clock firing? | `cd ~/code/33GOD/candybar && uv run candybar show <binding>` |
| Which agent CLI and session is in each pane? | `pj crank panes` (from /proc, read-only) |
| Did anyone read a watchdog alarm? | `~/.agents/tools/jev-clairic/bin/crank-attention --status [KEY]` |
| What does Redis hold for a binding? | `redis-cli FCALL_RO crank_get 0 <session> terminal_<N>` |

## Routes — read exactly one, then come back

| When you are… | Read |
|---|---|
| Turning crank on or off, setting an interval, attaching or ending a session, or reading what a binding is | [references/sessions.md](references/sessions.md) |
| Debugging why a pane was or was not poked, or changing the gate, officer brief or exit codes | [references/fire-and-officer.md](references/fire-and-officer.md) |
| Writing or judging what Crank says into a pane (the safety contract) | [references/officer-contract.md](references/officer-contract.md) |
| Answering "is the crank alive?", or seeing a watchdog alarm or a stalled crank | [references/health.md](references/health.md) |
| Touching `crank.lua`, Redis keys, the transition stream or statekit, or a prompt/status-line segment that looks wrong | [references/state.md](references/state.md) |
| Reading old tab-keyed data, `zcrankctl`, `zcrank:tab:*`, `crank:p:*` or `crank-beat` | [references/legacy.md](references/legacy.md) |

## Common combinations

| Task | Read, in order |
|---|---|
| A pane shows `⚠ crank stalled` | `references/health.md`, then `references/fire-and-officer.md` |
| Changing crank code | `references/state.md`, then the reference for the half you change |
| Crank typed something wrong into a pane | `references/officer-contract.md`, then `references/fire-and-officer.md` |

## Not here

| Topic | Go to |
|---|---|
| Making any scheduled LLM pass cost 0 tokens when nothing changed (the pattern crank uses) | the `interval-driver` skill |
| Candybar manifests, invocations and the single-clock rule | the `candybar` skill |
| Zellij panes, tabs and the zellij CLI | the `zellij-workspace-ops` skill |
| The ASM agent state machine crank reads | the `bloodbank-integration` skill; `bloodbank/services/agent-hooks/README.md` |
| Feature packaging (feature homes, claims, `features.toml`) | the `33god-features` skill |

## Gotchas

- A binding is keyed by the agent **session and process incarnation**, never by the pane.
  Pane ids are reused after a restart, and a new agent in an old pane inherits nothing.
  → `references/sessions.md`
- SessionEnd does not fire on pane close or reboot. Every fire checks its own agent and ends
  itself, `reason=orphan_reaped`. → `references/sessions.md`
- `⚠ crank stalled` comes only from v2: no fire for max(15m, 2×interval + 5m). The legacy
  `crank:p` hashes are frozen and are believed only under a fresh `crank:engine` heartbeat.
  → `references/state.md`
- A paused `crank-beat` and an old `cron/output/777c511a009c/` are expected. They do not mean
  the crank is dead. → `references/health.md`
- Never rerun `zcrank-scan.sh` as a probe: it changes the stale counters. → `references/legacy.md`

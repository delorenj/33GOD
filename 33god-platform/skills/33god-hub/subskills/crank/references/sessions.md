# Crank v2 sessions: policy and bindings

**One crank per live interactive agent session**, enabled by the project and clocked by its
own Candybar row. Code: `pjangler/src/crank/` (`policy.ts`, `binding.ts`, `sessions.ts`,
`cli.ts`). Shipped as PJAN-214, PJAN-215 (Redis projection) and PJAN-216 (a session belongs to
its agent's project).

## Policy: whether, and how often

Each value resolves in two layers, and `pj crank status` prints where it came from:

| Layer | File | Keys |
|---|---|---|
| Project (wins) | `.project.json` → `crank` | `enabled`, `interval`, `prompt`, `target`, `rules` |
| Install default | `$XDG_CONFIG_HOME/33god/crank.toml` (absent = built-in defaults) | `enabled_by_default`, `default_interval`, `zellij_session`, `officer_profile`, `officer_max_turns`, `prompt` |

- Interval grammar: `1-59m`, `1-23h` or `1d`. A bad interval is refused, never stored.
- Unknown keys in either layer are kept, so new fields land without a migration.
- The project block is the standing opt-in for every interactive session started in that
  project (I-8 AD-3, 2026-11-18). A tab name or a pane never opts a session in.
- A session belongs to its **agent's project**: the cwd of the agent process
  (`/proc/<pid>/cwd`), not the pane's or the shell's (PJAN-216).

```bash
pj crank status                       # policy + live sessions for this project
pj crank enable | disable             # writes .project.json crank.enabled; attaches or ends live sessions
pj crank interval 15m | default       # --global sets the install default
pj crank config set prompt '<guidance for the officer>'
pj crank config --global get default_interval
```

`pj crank enable` also turns the project's **legacy** tab switch off, so the retired beat
never drives the same session twice.

## Bindings: the session-keyed registry

- **Identity:** cli + native session id + process incarnation (pid + `/proc/<pid>/stat`
  starttime). The pane is only where the session lives now. A binding whose incarnation is
  gone is dead, whatever sits in its old pane.
- **Name:** `crank-<cli>-<sid8>-<pid>`, for example `crank-claude-8f7ffa7d-1381555`.
- **The registry is Candybar.** Each binding is one exec candybar tagged `crank-session`.
  Its runner env carries the identity, and its schedule is a staggered 5-field cron
  (`4-59/5 * * * *`) so bindings do not fire together. The manifest goes in the project's
  `.candybars/crank-*.candybar.toml`, which the machine-wide gitignore excludes so a repo
  never churns. It stays visible in that project's `candybar ls`.
- **Redis projection:** `crank.lua` `crank_attach`, `crank_fire` and `crank_end` keep
  `crank:b:<binding>` plus a pane pointer `crank:idx:pane:<session>:terminal_<N>`. The
  prompt reads it through `crank_get`. See [state.md](state.md).
- **Events:** `bloodbank.crank.binding.created` and `bloodbank.crank.binding.ended`, with
  `reason` set to `explicit`, `orphan_reaped`, `pane_closed` and so on.
- **Removal:** archive the candybar (Candybar has no delete, CAND-54), delete the manifest
  file, emit the ended event. An ended binding never comes back: a late fire is refused and
  cannot take its successor's pane.

## Lifecycle

| Moment | What runs | Where it logs |
|---|---|---|
| Agent session starts | hook-hub `crank-attach` (session_start, async) → `pj crank attach --hook`. Proves pid + start time from bb-hook, the pane from that process's environ, and for Claude that kind=interactive. Refuses everything else. | `~/.local/state/crank/hooks.jsonl` |
| Each fire | Candybar → `pj crank fire <binding>` → `crank-pane` | `~/.local/state/crank/log/<binding>.jsonl` |
| Agent session ends | hook-hub `crank-detach` (session_end) → `pj crank detach --hook` | `hooks.jsonl`, `events.jsonl` |
| Pane closed or reboot (no SessionEnd) | the next fire finds its agent gone and ends itself; `pj crank reap` ends every orphan | `reason=orphan_reaped` |

By hand: `pj crank attach` binds the agent session the command was started from.
`pj crank detach <binding>` (or `--session-id`) ends one.

## Views

`pj crank sessions [--all]` (alias `list`) · `pj crank log` · `pj crank tui` (project
toggle, interval, sessions with last and next fire, log) · `pj crank panes` (read-only
pane → pid → CLI → session inventory from /proc).

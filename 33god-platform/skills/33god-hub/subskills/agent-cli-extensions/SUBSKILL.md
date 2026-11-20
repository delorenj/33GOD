---
name: agent-cli-extensions
description: Extending the agent CLIs (Claude Code, Codex, OpenCode) so 33GOD shows up inside them — slash commands like /identity, menus and panes, display-only printouts, and the one-plugin-per-CLI layout under 33god-platform/agent-cli/. Covers where adapter sources live, how each CLI installs and reloads them, which CLI can answer without a model turn, and the recipe for adding the next 33GOD command to all three at once. Use when adding or changing a 33GOD slash command, menu, pane or plugin in any agent CLI, when /identity (or another 33GOD command) is missing or stale in one CLI, or when asked "can Claude/Codex/OpenCode do X?" for a 33GOD integration.
---

# Agent CLI extensions

33GOD reaches the operator through three agent CLIs: **Claude Code**, **Codex** and
**OpenCode**. Each one gets the same 33GOD commands (first: `/identity`, the shell
prompt's PM identity segment expanded). The commands are built so that adding the next
one is a recipe, not a design.

## Rules on every route

- **The view lives in a component CLI, never in an adapter.** A command's output is
  rendered by the owning 33GOD CLI (`flume identity manifest [employee] --markdown`).
  Each CLI adapter only passes the arguments and prints what comes back. To change what
  `/identity` shows, change flume; all three CLIs follow.
- **One plugin per CLI, named `33god`, sourced from `33god-platform/agent-cli/<cli>/`.**
  Every 33GOD command for that CLI goes into that one plugin. Never write an adapter into
  a CLI's home directory by hand (`~/.claude/...`, `~/.codex/...`, `~/.config/opencode/...`);
  install it from the platform checkout so the source is versioned.
- **Ship to all three CLIs together.** A 33GOD command that exists in one CLI and not the
  others is drift. Same name, same arguments, same output.
- **Prefer no model turn.** Where the CLI can print a command's output itself, do that and
  keep it out of the model's context. Claude Code and OpenCode can; Codex cannot (a
  skill, one model turn).
- **Adapter skills never go in `~/.agents/skills/`.** That root is shared by every CLI. A
  skill named after a command collides with the Claude command of the same name, and it
  breaks the one-hub-per-repo rule. Codex's adapter skill lives inside its `33god` plugin.
- Land each change: commit `33god-platform`, then reinstall or reload wherever that CLI
  needs it (see its reference), then prove it with the non-interactive check below.

## Ask the system first

| Question | Ask |
|---|---|
| What does the command print? (identical in every CLI) | `flume identity manifest [employee] --markdown` from the repo |
| Is the Claude plugin installed, and from where? | `~/.local/bin/claude plugin list` (`33god@33god`, `Read from:` the checkout) |
| Is the Codex plugin installed? | `codex plugin list` (`33god@33god installed, enabled`) |
| Is the OpenCode plugin installed, or did it fail? | `opencode plugin list` (`plugins/33god` local); the footer's `plugin failed` → `~/.local/share/opencode/log/opencode.log` |

## Route table

Read exactly one row, then come back.

| When you are… | Read |
|---|---|
| Adding a new 33GOD command to every CLI (the recipe) | [references/adding-a-command.md](references/adding-a-command.md) |
| Working on the Claude Code `33god` plugin: hooks module, display-only output, panes and menus, tests | [references/claude-code.md](references/claude-code.md) |
| Working on the Codex `33god` plugin: plugin-shipped skill, `/33god:<cmd>` naming, reinstall after edits | [references/codex.md](references/codex.md) |
| Working on the OpenCode `33god` TUI plugin: local slash commands, select menus, dialogs, the tmux proof | [references/opencode.md](references/opencode.md) |

## What each CLI can do (2026-11-20)

| | Claude Code 2.1.x | Codex 0.167 | OpenCode 2.3 |
|---|---|---|---|
| Invocation | `/identity [employee]` | `/33god:identity [employee]` (or `$33god:identity`) | `/identity [employee]` (also ctrl+p) |
| Output without a model turn | yes (`isTextDisplayOnly`, drawn in the transcript) | no: a skill, so the model runs the command and echoes it | yes (a TUI-local slash command opening a dialog) |
| Menus, panes, pickers from an extension | yes: panes with Buttons/Select, the band above the prompt, desktop right-click rows | no: only built-in pickers | yes: `dialog.select` menus (chained = submenus), dialogs, routes, panels |
| `/identity` with no argument shows | the PM in full plus the other agents (markdown) | same as Claude | a menu of the project's agents labelled `id v1 5/6`; a pick opens that agent |
| Edits reach a session by | `/reload-plugins` (folder marketplace, read in place) | `codex plugin add 33god@33god` again (copied to cache), then a new session | a new TUI session (symlinked folder, read in place) |

# Adding a 33GOD command to every agent CLI

The recipe, using `/identity` as the worked example. Do every step for all three CLIs in one
change.

## 1. Put the view in the owning component CLI

The command's whole output comes from one component CLI invocation with a `--markdown`
flag, run from the operator's cwd:

```bash
flume identity manifest [employee] --markdown
```

- With no argument it reads the cwd's project (`.project.json`, searching upward), the same
  way the shell prompt does. With an argument it answers for that one thing.
- A failure is still markdown on stdout (`✗ <reason>`), with a non-zero exit. Adapters print
  it as it is.
- `--json` returns the same data, for the prompt refresher, scripts and menus. Put any label a
  menu shows into the JSON (flume adds `prompt: "id v1 5/6"` to each project agent), so no
  adapter re-derives it. Test both in the
  component's own suite (flume: `tests/identity-manifest-regressions.mjs`).

If the logic needs a fact some other component owns, call that component's CLI from the
owning CLI. Never call it from an adapter.

## 2. Add a thin adapter per CLI

| CLI | Where | What |
|---|---|---|
| Claude Code | `agent-cli/claude/33god/hooks/register.tsx` | `$.command.register` + a `command.run` hook that runs the CLI and returns `{ text, isTextDisplayOnly: true }`; a no-argument form may open a pane with a `Select` menu built from the CLI's `--json`, falling back to the printout where no pane is placed; a test in `hooks/*.test.tsx` ([claude-code.md](claude-code.md)) |
| Codex | `agent-cli/codex/33god/skills/<cmd>/SKILL.md` + `agents/openai.yaml` | a skill that runs the CLI and echoes stdout verbatim; explicit-only ([codex.md](codex.md)) |
| OpenCode | `agent-cli/opencode/33god/tui.js` | another entry in the `ctx.keymap.layer` commands list whose `run` calls the CLI and shows a dialog; a no-argument form may offer a `dialog.select` menu built from the CLI's `--json` ([opencode.md](opencode.md)) |

Use the same command name in each CLI (Codex adds its `33god:` namespace) and the same
optional argument.

## 3. Install, then prove each one

Run each CLI's verify step: `claude -p "/<cmd>" < /dev/null`, `codex exec '$33god:<cmd>'`
and the OpenCode tmux proof in [opencode.md](opencode.md). Each must print what the component CLI
printed. Then commit `33god-platform`, plus the component repo, and push both.

## 4. Route it

Add the command to the component's docs (flume: `docs/identity-provisioning.md`) and, if
operators will look for it, to the "What each CLI can do" table in
[../SUBSKILL.md](../SUBSKILL.md).

# Codex: the `33god` plugin

Source: `33god-platform/agent-cli/codex/`, a local Codex marketplace named `33god` that holds
one plugin, `33god/`. In Codex 0.167 a plugin can ship skills, MCP servers, apps and hooks,
but **not slash commands**. An enabled skill does appear in the slash list, though, so each
33GOD command is a skill inside the plugin.

```text
agent-cli/codex/
  .agents/plugins/marketplace.json           { name: "33god", plugins: [{ name: "33god", source: { source: "local", path: "./33god" } }] }
  33god/.codex-plugin/plugin.json            name 33god, "skills": "./skills/"
  33god/skills/<cmd>/SKILL.md                one skill per 33GOD command
  33god/skills/<cmd>/agents/openai.yaml      policy: { allow_implicit_invocation: false }
```

## Naming and invocation

A plugin skill is namespaced by its plugin, so the command is **`/33god:identity [employee]`**.
`$33god:identity` also works. Typing `/identity` in the composer filters the popup to it.
`allow_implicit_invocation: false` keeps the skill out of the model's implicit skill list. It
runs only when the operator names it, and it costs no context in any other turn.

## What it can't do

- **No output without a model turn.** Codex substitutes no `$ARGUMENTS` and injects no
  shell output into a skill. The skill tells the model to run the component CLI and echo
  its stdout verbatim. That costs one model turn, and the session's context makes it large.
  (`codex exec '$33god:identity'` used ~58k tokens on 2026-11-20.)
- **No extension menus or pickers.** Only the built-in ones exist (`/model`, `/skills`, …).
- A typed `/<name>` that is not a built-in, a skill or a deprecated prompt is rejected in
  the composer, so a `UserPromptSubmit` hook cannot answer it. Custom prompts
  (`~/.codex/prompts/`) are deprecated in favour of skills.

## The skill body

Keep it short and literal: one command, its stdout verbatim, nothing else.

```markdown
---
name: identity
description: Print the 33GOD identity view (…). Use only when the user types /identity or $identity, optionally followed by an employee name.
---
Run exactly one shell command from the current working directory and reply with its stdout verbatim …
- No argument: `flume identity manifest --markdown`
- An argument: `flume identity manifest <employee> --markdown`
```

## Install, update, verify

```bash
codex plugin marketplace add ~/code/33GOD/33god-platform/agent-cli/codex   # once per machine
codex plugin add 33god@33god                                               # install; REPEAT after every edit
codex plugin list | grep 33god                                              # installed, enabled
cd ~/code/33GOD && codex exec --skip-git-repo-check '$33god:identity'       # live (one model turn)
```

Codex **copies** the plugin into `~/.codex/plugins/cache/33god/33god/<version>/`. An edit in
the checkout reaches Codex only after `codex plugin add 33god@33god` runs again. Bump
`version` in `plugin.json` when the change matters to other machines. The operator's
`codex` is a shell function that adds `--dangerously-bypass-approvals-and-sandbox`. From
scripts, call the binary (`command codex …`).

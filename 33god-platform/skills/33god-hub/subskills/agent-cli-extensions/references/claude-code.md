# Claude Code: the `33god` plugin

Source: `33god-platform/agent-cli/claude/`, a **folder marketplace** named `33god` that holds
one plugin, `33god/`. It is a "mod": a plugin with a hooks module (`hooks/register.ts`)
running on the Claude Code engine (`$`, `on(event, matcher, hook)`). The built-in
`plugin-authoring` skill is the full API reference. Load it before writing anything beyond
a new command.

```text
agent-cli/claude/
  .claude-plugin/marketplace.json     { name: "33god", plugins: [{ name: "33god", source: "./33god" }] }
  33god/.claude-plugin/plugin.json    name 33god
  33god/hooks/hooks.json              { "modules": ["./register.ts"] }  (one module)
  33god/hooks/register.ts             every 33GOD command
  33god/hooks/*.test.ts               claude plugin test
```

## A command

Register it at `session.start` and answer it in `command.run`. The answer is **display-only**:
it is drawn in the transcript, never sent to the model, so it costs no turn.

```ts
on('session.start', async ($, e, next) => {
  await $.command.register({ name: 'identity', description: '…', argumentHint: '[employee]' })
  return next(e)
})
on('command.run', { command: 'identity' }, async ($, e) => {
  const employee = (e.args ?? '').trim()          // args can be undefined (tests, $.command.run)
  const run = await $.process.run(['flume', 'identity', 'manifest', ...(employee ? [employee] : []), '--markdown'],
    { cwd: await $.session.cwd(), timeoutMs: 30000 })
  return { text: (run.stdout || run.stderr).trimEnd(), isTextDisplayOnly: true }
})
```

`text` is markdown, and the terminal draws its tables. Add the next command as another pair
of hooks in the same `register.ts`.

## Menus, panes, submenus

These are hooks modules too. They are not needed for a printout, but they are available:

- **Pane** (sidebar or dialog): `$.ui.open({ id, title, focus, closeOnEscape })` plus a
  `ui.render` hook on `{ component: 'Pane', requestId: id }`. It returns `Box`/`Text`/`Button`/`Select`
  from `$.ui.resolve(e)`. Buttons take `hotkey`s, and Tab and the arrows walk them. A menu
  with submenus is a pane whose Select or Buttons change an atom (`update($, atom, fn)`)
  that the render reads.
- **Band above the prompt**: a `ui.render` hook on `{ component: 'AbovePrompt' }`.
- **Desktop right-click rows**: a `ui.render` hook on `{ component: 'ContextMenu' }`.
- **Status line entry**: `$.ui.status(text)`. The operator's status line is
  `~/.claude/statusline.sh`, which mirrors the starship prompt, so prefer that.

## Install, reload, test

```bash
C=~/.local/bin/claude       # the shell `claude` function adds flags that `plugin test` refuses
$C plugin marketplace add ~/code/33GOD/33god-platform/agent-cli/claude   # once per machine
$C plugin install 33god@33god --scope user                              # once per machine
$C plugin validate ~/code/33GOD/33god-platform/agent-cli/claude/33god    # hooks, calls, refusals
$C plugin test     ~/code/33GOD/33god-platform/agent-cli/claude/33god    # *.test.ts against the engine
cd ~/code/33GOD && $C -p "/identity" < /dev/null                          # live, no model turn
```

The marketplace is a folder, so sessions **read the plugin from the checkout in place**.
After an edit, run `/reload-plugins` in a running session. There is no reinstall and no
version bump. The engine lays editor types into `33god/.claude-plugin/types/`, which git
ignores.

In tests, calls on `$` are answered by the test's own hooks with `{ value }`, for example
`on('process.run', () => ({ value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }))`.

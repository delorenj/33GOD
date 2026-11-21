# Claude Code: the `33god` plugin

Source: `33god-platform/agent-cli/claude/`, a **folder marketplace** named `33god` that holds
one plugin, `33god/`. It is a "mod": a plugin with a hooks module (`hooks/register.tsx`)
running on the Claude Code engine (`$`, `on(event, matcher, hook)`). The built-in
`plugin-authoring` skill is the full API reference. Load it before writing anything beyond
a new command.

```text
agent-cli/claude/
  .claude-plugin/marketplace.json     { name: "33god", plugins: [{ name: "33god", source: "./33god" }] }
  33god/.claude-plugin/plugin.json    name 33god, "types": "./types/index.d.ts"
  33god/types/index.d.ts              the $.state contract (every atom's value type)
  33god/hooks/hooks.json              { "modules": ["./register.tsx"] }  (one module)
  33god/hooks/register.tsx            every 33GOD command (JSX: panes)
  33god/hooks/*.test.tsx              claude plugin test
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
of hooks in the same `register.tsx`.

## Menus, panes, submenus

Bare `/identity` is the worked example: a pane holding a menu of the project's agents.

1. `command.run` runs `flume identity manifest --json`, writes the agents (each with flume's
   own `prompt` label) and the first agent's plain-text detail into an atom, then
   `$.ui.open({ id: 'identity', title, focus: true, closeOnEscape: true })`.
2. A `ui.render` hook on `{ component: 'Pane', requestId: 'identity' }` reads the atom and
   draws `<Select key="agent" options=… value=… autoFocus onSelect=…>` from
   `$.ui.resolve(e)`, then the picked agent's detail as `Text` rows (flume's plain text, so
   the view stays in flume; cut to `e.viewport?.rows`).
3. `onSelect` updates the atom's `selected`, runs `flume identity manifest <employee>` once
   per agent, and stores the text. Each `update($, atom, fn)` redraws the pane.
4. `$.ui.open` resolves `{ isPlaced }`. Under `claude -p` nothing is placed, so return the
   `--markdown` printout instead. Never leave a non-interactive caller with nothing.

Rules for panes:

- Every atom is declared in `types/index.d.ts` under `interface PluginState { '33god': { key: Shaped<T> } }`,
  and given a `shape` tag. Bump the tag (`identity-menu-1` → `-2`) when its fields change:
  `$.state` outlives `/reload-plugins`, and the tag makes a reload decline old values.
- A submenu is another atom field the render branches on, changed by a `Select` or `Button`
  (`hotkey`s; Tab and the arrows walk them).
- Draw detail with `Text` rows, not `Markdown`: a terminal surface may refuse `Markdown`.

Elsewhere:

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
$C plugin test     ~/code/33GOD/33god-platform/agent-cli/claude/33god    # *.test.tsx against the engine
cd ~/code/33GOD && $C -p "/identity" < /dev/null                          # live, no model turn (the markdown fallback)
```

The marketplace is a folder, so sessions **read the plugin from the checkout in place**.
After an edit, run `/reload-plugins` in a running session. There is no reinstall and no
version bump. The engine lays editor types into `33god/.claude-plugin/types/`, which git
ignores.

In tests, calls on `$` are answered by the test's own hooks with `{ value }`, for example
`on('process.run', () => ({ value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }))`.

Pane tests mount the pane after the command has run: stub `ui.open` with
`{ value: { isPlaced: true } }`, run `$.command.run({ command: 'identity' })`, then
`$.ui.mount({ plugin: '33god', surface: 'terminal', component: 'Pane', requestId: 'identity', props: {…} })`,
`ui.find({ type: 'Select' })`, `ui.select({ key: 'agent', value })` and `ui.find({ type: 'Text', text: /re/ })`.

To see the pane itself, start `~/.local/bin/claude` in a throwaway tmux session (it opens the
sessions dashboard; typing `/identity` and Enter creates a session for it, and Enter on that row
attaches), then `tmux capture-pane -p`. The pane draws on the right. Remove the test session
from the dashboard with ctrl+x twice.

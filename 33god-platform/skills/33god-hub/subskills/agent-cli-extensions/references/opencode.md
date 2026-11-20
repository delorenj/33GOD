# OpenCode: the `33god` TUI plugin

Source: `33god-platform/agent-cli/opencode/33god/tui.js`, an OpenCode **v2 TUI plugin**.
It is installed as a directory symlink, `~/.config/opencode/plugins/33god` → that folder.
OpenCode v2 scans only directories (or links to them) under `~/.config/opencode/plugins/`;
loose files are ignored. A directory's `tui.js` is its TUI entry and `index.js` its server
entry. `tui.json` no longer registers plugins.

v1 plugin code does not run in v2. The `@opencode-ai/plugin` types under
`~/.config/opencode/node_modules` are v1 and stale. The v2 API is the JS bundled in the
binary. The built-in `/cd` and the Orca status plugin
(`~/.config/opencode/plugins/orca-opencode-status-tui/tui.js`) are the working references.

## Shape

```js
export default { id: "33god", setup }            // setup(ctx) may return a cleanup function
async function setup(ctx) {
  ctx.keymap.layer(() => ({                       // an ACCESSOR: a plain object fails setup ("e is not a function")
    mode: "global",
    commands: [{
      id: "33god.identity", title: "33GOD identity", group: "33GOD", palette: true, bind: false,
      slash: { name: "identity", arguments: true },
      run: (argString) => identity(ctx, argString),   // runs in the TUI: no model turn, no server round trip
    }],
  }))
}
```

A local slash command runs before any server command lookup, so it never reaches the model.
It also shows in the `/` popup and the ctrl+p palette.

## UI the plugin can open

- `ctx.ui.dialog.select({ title, options: [{ title, value, description, category }] })` resolves
  the picked `value`, or `undefined` on Esc. This is the menu. Chain calls for submenus
  (`/identity` lists the project's agents grouped `PM` / `Agents`, and a pick opens that agent).
- `ctx.ui.dialog.alert({ title, message })` shows **plain text**, so use the component
  CLI's text format, not `--markdown`. Also available: `.confirm`, `.prompt`, `.show(jsx)`,
  `.set({ size })` and `.clear()`.
- `ctx.ui.toast.show({ variant, title, message })`. Also `ctx.ui.router`, `ctx.ui.panel` and
  `ctx.ui.slot` for whole routes and side panels.
- The session's directory: `ctx.data.session.get(ctx.ui.router.current().sessionID)?.location?.directory`,
  then `ctx.location?.directory`, then `process.cwd()`. Run component CLIs there.

Plugins run on Bun, so `node:child_process` `execFile` works. Call component CLIs by name;
`~/.local/bin` is on the TUI's PATH.

## Markdown commands (fallback, model turn)

`~/.config/opencode/commands/` (→ `~/.agents/commands/`) holds `*.md` commands with
`description`, `agent`, `model` and `subagent` frontmatter, `$ARGUMENTS`, and `` !`cmd` ``
shell injection. They always go through the model, so a 33GOD command uses the TUI plugin
instead. Do not add a markdown twin.

## Install, reload, verify

```bash
ln -sfn ~/code/33GOD/33god-platform/agent-cli/opencode/33god ~/.config/opencode/plugins/33god   # once per machine
command opencode plugin list            # lists .../plugins/33god as local
```

The link reads the checkout in place, and a new TUI session picks up edits. A plugin that
throws in `setup` shows as `⊙ 1 plugin failed /plugins` in the footer. The reason is in
`~/.local/share/opencode/log/opencode.log` (`message="plugin operation failed" … plugin=33god`).

TUI commands can't be driven headlessly (`opencode run` has no `--command`). Prove one in a
throwaway tmux session and read the screen:

```bash
tmux new-session -d -s octest -x 200 -y 50 -c ~/code/33GOD "$(bash -c 'command -v opencode')"
sleep 9; tmux send-keys -t octest "/identity"; sleep 1
tmux send-keys -t octest Enter; sleep 1; tmux send-keys -t octest Enter   # first Enter completes, second submits
sleep 4; tmux capture-pane -p -t octest | tail -25; tmux kill-session -t octest
```

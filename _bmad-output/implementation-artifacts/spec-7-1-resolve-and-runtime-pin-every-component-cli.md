---
title: 'Story 7.1: Resolve and Runtime-Pin Every 33GOD Component CLI'
type: 'feature'
created: '2026-11-19'
status: 'in-progress'
route: 'interactive'
owner: 'Grolf (33god-pm)'
epic: 'Epic 7: 33GOD CLI Surface — one contract, native binaries'
plane_ref: '33GOD-102'
plane_epic: '33GOD-101'
review_loop_iteration: 0
context:
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-19.md
  - _bmad-output/planning-artifacts/architecture/architecture-33GOD-2026-11-19-cli-surface/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/research/cli-surface-research-2026-11-19.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Story:** As an agent (or Candybar, or a systemd unit), I can run any 33GOD
component CLI by its native name from any cwd and any PATH, on the runtime it
needs, so the CLI surface stops depending on luck of the shell.

**Problem:** krebs has no installed command (Candybar runs `node` plus a repo
path); Node component launchers use `#!/usr/bin/env node`, so systemd or `env -i`
picks `/usr/bin/node` v20.19.4 and a cwd mise pin can pick node 20 or 22; two
`hermes` binaries resolve differently by cwd; and three skillex versions answer to
"skillex" (PATH, `pj skills` bundled, flume's sha pin).

**Approach:** fix the root causes directly with no umbrella (architecture spine
AD-1, AD-2, AD-6): pinned-interpreter wrappers written by one tracked installer,
krebs on PATH, Candybar calling the launcher, the hermes shadow removed with its
scoping kept under an explicit name, and one skillex.

**Belsky level (`belsky-doctrine`):** every 33GOD component CLI, not just the ones
that broke today.

## Acceptance Criteria (verbatim, approved 2026-11-19)

- **AC1** krebs is on PATH: `env -i HOME=$HOME PATH=$HOME/.local/bin:/usr/bin:/bin krebs --help` (or its equivalent no-side-effect invocation, e.g. tick --dry-run if --help is unsupported) succeeds from /tmp. It must NOT perform a live tick.
- **AC2** Every 33GOD Node CLI launcher in ~/.local/bin (at least pj, pjangler, px, pilot, flume, fl, krebs, skillex) runs on a pinned Node >=24 regardless of cwd mise pins or a minimal PATH: for each, `env -i HOME=$HOME PATH=$HOME/.local/bin:/usr/bin:/bin <cli> --version` (or --help where no version flag) succeeds and reports the expected version, and the same from a directory whose mise config pins node 20. Mechanism: ONE tracked, idempotent installer in the 33GOD repo (e.g. 33god-platform/scripts/cli-launchers.py or .sh) that writes the ~/.local/bin wrappers from a declared list, resolving the interpreter via mise (e.g. `mise where node@24` or the ~/.local/share/mise/installs/node/24 alias) so it is portable to the Mac peer, with a --check mode that exits nonzero on drift. Wrappers exec the pinned node with the CLI's real entry file. Python CLIs (candybar, candystore, bb, wax, waybill) are listed as already-pinned (uv tool venvs / launchers) or fixed if --check finds them broken under the minimal PATH.
- **AC3** Candybar: the krebs-tick manifest (~/code/33GOD/krebs/.candybars/krebs-tick.candybar.toml) runs krebs through the pinned launcher (absolute path to ~/.local/bin/krebs, tick, --json) instead of bare `node` + repo path. Follow the candybar skill (~/.agents/skills/candybar/SKILL.md): commit the manifest, apply/register it the documented way, READ BACK the registration through the Candybar API, and prove the next scheduled terminal invocation succeeded and had its intended effect. NEVER `candybar run` krebs-tick manually (its manifest says not to). Also scan all other .candybars manifests across ~/code for bare node/npx interpreters and report them (fix only trivially safe ones).
- **AC4** hermes resolves to the same binary from ~/code/33GOD, ~/code/skillex and /tmp. The per-PM launcher at agents/hermes/pm/hermes (put on PATH by `_.path` in ~/code/33GOD/mise.toml:4 and ~/code/skillex/mise.toml:14) stops shadowing the global hermes; whatever it provides (HERMES_HOME/profile scoping for PM desks) stays reachable under an explicit, documented name or mechanism, and every caller that relied on the shadow is updated. Investigate callers BEFORE changing anything (rg across ~/code, ~/.hermes, ~/.agents, hermes-agent-template generators — generated files are rendered, never hand-edited: fix the generator). Never restart hermes-gateway except via `hermes-gateway-restart --reason` and only if truly required.
- **AC5** One skillex: the skillex on PATH equals the latest npm release (0.4.10 at time of writing; check `npm view @delorenj/skillex version`), stale co-installed mise versions are pruned, and `pj skills` execs the PATH skillex instead of its bundled @delorenj/skillex 0.4.4 (remove the dependency). Release pjangler the standard way: bump package.json (`npm version X --no-git-tag-version`), commit, push main; its .github/workflows/publish.yml publishes via npm trusted publishing (never `npm publish` locally, never --otp). After CI publishes, update the global install so `pj --version` shows the new version, then verify `pj skills --version` == `skillex --version`. Report flume's github:delorenj/skillex#<sha> pin (do not change it; note it needs a reason+exit ticket under features.toml F3).
- **AC6** Every touched repo committed and pushed (`git unpushed` shows nothing new for them). No secrets in files.

## Boundaries & Constraints

**Always:**
- Native binary names stay canonical (AD-1). Nothing here introduces `33god`.
- Resolve node through mise in the installer so it runs on the Mac peer too.
- Commit only your own paths with explicit pathspecs; `git pull --rebase --autostash`
  before push; commit and push inside each submodule repo you change.
- Fix generators, never hand-edit rendered files (hermes-agent-template).

**Never:**
- Never `candybar run krebs-tick` (it writes Plane and publishes to the bus).
- Never hard-pin skillex in `~/.config/mise/config.toml` (features.toml F3; AD-6).
- Never `npm publish` locally or pass `--otp`; pjangler ships through trusted publishing.
- Never restart hermes-gateway except through `hermes-gateway-restart --reason`.
- Never bump submodule pointers in the 33GOD superproject from this story (the lead does).
- Never write a secret into a file.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Minimal PATH | `env -i HOME=$HOME PATH=$HOME/.local/bin:/usr/bin:/bin <cli> --version` from /tmp | Runs on node >= 24, prints the expected version | Wrapper prints which interpreter it could not resolve and exits nonzero |
| cwd pins node 20 | Same command from a dir whose `mise.toml` pins node 20 | Same result as minimal PATH | Same |
| krebs safe probe | `krebs --help` (or `tick --dry-run`) | Usage or dry-run output; no Plane write, no bus publish | If `--help` is unsupported, use the dry-run form and record which |
| Installer re-run | Wrappers already correct | No changes; `--check` exits 0 | n/a |
| Installer drift | A wrapper edited, missing, or pointing at a stale interpreter | `--check` exits nonzero and names the wrapper | Plain run rewrites it |
| Mac peer | No `/home/delorenj`, node from mise | Installer resolves node via `mise where node@24` | Fails loudly if mise has no node 24 |
| Hermes from any cwd | `command -v hermes` in 33GOD, skillex, /tmp | Same path | PM-desk scoping reachable under its new explicit name |
| pj skills | `pj skills --version` | Equals `skillex --version` | n/a |

</frozen-after-approval>

## Tasks / Subtasks

- [ ] **T1 Launcher installer (AC2)**
  - [ ] Write the declared list (CLI name, real entry file, runtime) for pj, pjangler, px, pilot, flume, fl, krebs, skillex; list candybar, candystore, bb, wax, waybill as Python with their current launchers.
  - [ ] Add the tracked installer in `33god-platform/scripts/` (name per AC2), resolving node via `mise where node@24` or the `node/24` alias directory.
  - [ ] Wrappers exec the pinned node with the entry file; idempotent writes.
  - [ ] `--check` mode: exit nonzero on any missing, edited or stale wrapper; also probe the Python CLIs under the minimal PATH.
  - [ ] Run it; record the `env -i` and node-20-cwd results per CLI in the Dev Agent Record.
- [ ] **T2 krebs on PATH (AC1)**
  - [ ] Include krebs in the installer list (`krebs/bin/krebs.mjs`).
  - [ ] Prove `krebs --help` (or `tick --dry-run`) from /tmp under the minimal PATH, with no live tick.
- [ ] **T3 Candybar krebs-tick (AC3)**
  - [ ] Load `~/.agents/skills/candybar/SKILL.md`; change `krebs-tick.candybar.toml:41` argv to the absolute launcher, `tick`, `--json`.
  - [ ] Commit and push the manifest in the krebs repo; apply/register it the documented way.
  - [ ] Read back the registration through the Candybar API.
  - [ ] Wait for the next scheduled fire; prove a terminal success and its intended effect. No manual `candybar run`.
  - [ ] Scan every `.candybars/*.candybar.toml` under `~/code` for bare `node`/`npx`; report them; fix only trivially safe ones.
- [ ] **T4 Hermes shadow (AC4)**
  - [ ] Inventory callers first: `rg` across `~/code`, `~/.hermes`, `~/.agents` and the hermes-agent-template generators for reliance on the per-PM `hermes`.
  - [ ] Remove `agents/hermes/pm` from `_.path` in `33GOD/mise.toml:4` and `skillex/mise.toml:14` (fix the generator that renders them, if any).
  - [ ] Expose PM-desk HERMES_HOME/profile scoping under an explicit, documented name or mechanism; update every caller.
  - [ ] Prove `command -v hermes` is identical from 33GOD, skillex and /tmp.
- [ ] **T5 One skillex (AC5)**
  - [ ] Make PATH skillex the latest npm release; prune stale mise installs.
  - [ ] In pjangler: make `pj skills` exec PATH skillex; remove the `@delorenj/skillex` dependency; `npm version <X> --no-git-tag-version`; commit; push main; let `publish.yml` publish.
  - [ ] After CI publishes: update the global pj install; verify `pj --version` and `pj skills --version` == `skillex --version`.
  - [ ] Report flume's `github:delorenj/skillex#<sha>` pin (unchanged) and that it needs a reason and exit ticket under F3.
- [ ] **T6 Land everything (AC6)**
  - [ ] `git unpushed` clean for every touched repo; no secrets in files.
  - [ ] Post the evidence on the Story 7.1 Plane ticket; Grolf gives the verdict.

## Dev Notes

Facts from `research/cli-surface-research-2026-11-19.md` (re-check before relying
on them; other agents are changing this state now):

- **Install methods today (six ways).** npm global dir symlink (pj ->
  `../lib/node_modules/@delorenj/pjangler/dist/index.js`); symlink straight into a
  repo checkout (px and pilot -> `33GOD/pilot/bin/pilot.js`; flume and fl ->
  `33GOD/flume/packages/flume-hr/dist/index.js`, which runs whatever build is in the
  working tree; bb, waybill, wax); uv tool venvs (candybar, candystore); the mise npm
  backend (skillex, `"npm:@delorenj/skillex" = {version='latest'}` in
  `~/.config/mise/config.toml`, not in `~/.local/bin`); a prebuilt binary copy
  (hindsight); a sh shim (hermes); and krebs with no installed command at all.
- **The systemd Node 20 gotcha.** Under `env -i PATH=/usr/bin:/bin` or a systemd
  PATH, `node` is `/usr/bin/node` v20.19.4. PATH skillex then prints
  `E_NODE_VERSION: Node 24 or newer is required; running 20.19.4` and exits 2
  (skillex `src/cli.ts:364-377`). process.execve is also undefined there. Repos
  pinning node 20: capitalism, overworld, tiller-mcp-server; others pin 22.
  pjangler pins node 26.4 (why its `link-bins.sh` exists). Global mise pins node
  24.6.0. Candybar's executor PATH puts mise shims first (candybar-executor.service).
- **krebs-tick manifest line.** `krebs/.candybars/krebs-tick.candybar.toml:41`:
  `argv = ["node", "/home/delorenj/code/33GOD/krebs/bin/krebs.mjs", "tick", "--json"]`.
  Lines 12-13: live since 2026-11-14; it writes Plane and publishes to the bus, so
  never `candybar run` it; the first scheduled fire after `resume` is the proof.
  krebs is Node >= 24.6 ESM, zero dependencies, `node:util` parseArgs; its only
  subcommand is `tick`. krebs answers `unknown command "--version"`.
- **Hermes `_.path` lines.** `~/code/33GOD/mise.toml:4`:
  `_.path = [".mise/scripts", "agents/hermes/pm", "agents/hermes/pm/hermes"]`.
  `~/code/skillex/mise.toml:14`:
  `_.path = ["agents/hermes/pm", "agents/hermes/pm/hermes", ".mise/scripts"]`.
  The per-PM launcher sources `~/.hermes/fleet.env` and scopes HERMES_HOME to a
  profile. In interactive zsh `hermes` is also a function wrapping
  `_lastagent_wrap`, which fails in non-interactive shells.
- **skillex skew.** PATH skillex 0.4.8 at research time; 0.4.10 released
  (`npm view @delorenj/skillex version` = 0.4.10 on 2026-11-19); pjangler
  `package.json:64` bundles `"@delorenj/skillex": "0.4.4"` for `pj skills`; flume
  `packages/flume-hr/package.json:18` pins
  `github:delorenj/skillex#f51ff3eb4f971f025f1ed29e14b0cca9a1550a16`; eleven versions
  were co-installed under mise. A re-check on 2026-11-19 at 13:40 showed the mise
  install dir already reduced to `0 0.1 0.1.3 0.4 0.4.10 latest`, so pruning may
  be in progress.
- **usage-cli** is 3.3.0 locally; the mise global config line now reads
  `usage = "latest"` (the research saw a 3.3.0 pin). Not in scope for 7.1 (Story 7.2).
- **Versions seen at research time:** pj 1.5.47, px 0.5.0, skillex 0.4.8, candybar
  0.1.0, flume 1.0.0 (hardcoded in index.ts), waybill 1.0.0. bb, wax and candystore
  have no version flag.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Evidence per Acceptance Criterion

| AC | Command / check | Result | Link (commit, ticket comment) |
|----|-----------------|--------|-------------------------------|
| AC1 | | | |
| AC2 | | | |
| AC3 | | | |
| AC4 | | | |
| AC5 | | | |
| AC6 | | | |

### Completion Notes List

### File List

## Spec Change Log

## Review Triage Log

| Verdict | Location | Evidence / Disposition | Route |
|---------|----------|------------------------|-------|

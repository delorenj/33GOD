# Plain mode on Damian's Mac (2026-11-21)

Jarad asked to cut Damian's AI apps loose from 33GOD so Damian has a clean baseline: Claude Code and Codex (CLI and Desktop) back on their own accounts, no gateway, no 33GOD hooks, skills or instructions. 33GOD infra (pjangler registry, Postgres, Colima, hook-hub, Candybar, Hindsight, Hermes) stays up as long as the apps no longer touch it, so flipping back is easy.

Lane (charter §3.8): Jarad handed this session to Claude Code directly on 2026-11-21 with "do that now". Rererere still owns real-deployment acceptance (§2): this record is evidence for that acceptance, not the acceptance itself. Damian's first real use of the apps is the acceptance test.

Built one level up (belsky-doctrine): the switch is `33god-mode` for **any 33GOD Mac peer** (`scripts/peer-mode.py`, host specifics as `PEER_*` env vars), with `scripts/plain-check.py` as its acceptance. Damian's Mac is the first user.

## What was done (Mac `hellosubconscious@100.117.109.60`)

| When (UTC) | Step |
|---|---|
| 16:45-16:57 | Read-only sweep, 3 independent agents (Claude surface, Codex surface, env and rewriters). Nothing changed. |
| 17:02:30 | `33god-mode off`. Backup of every touched file: `~/.config/33god/config-backups/20261121T170230Z-33god-mode-before-off/`. Parked state: `~/.config/33god/mode/parked.json`. |
| 17:02:40 | Damian's own Claude login restored. 33GOD had removed his `export CLAUDE_CODE_OAUTH_TOKEN` from `~/.zshrc` on 11-15 and moved the value into the 0600 store. `~/.zshrc` now exports it in interactive shells through `env-op-resolve` and `~/.config/33god/clients/claude-login.env.op` (ref only, no value in any file). The login keychain can't be written over ssh. The line works in both modes: under `on`, the gateway apiKeyHelper outranks it. |
| 17:02:40 | `~/.local/bin/codex-mode` (11-20, Codex-only half switch) now hands off to `33god-mode`: `regular` runs off, `gateway` runs on. The old script is in the backup dir. |
| 17:02:47 | `codex app-server daemon restart` so the managed daemon reloads the plain config. |
| 17:04 | `plain-check.py --live`: 12 static PASS, 3 live turns PASS. |

`33god-mode off` changed:

- `~/.claude/settings.json`: removed `apiKeyHelper` (aai-gateway-token), the 10-key gateway `env` block and the 13 bb-hook hooks. Kept his git-checkpoint SessionEnd hook, permissions, model and voice settings.
- `~/.codex/config.toml`: removed `model_provider = automaticai`, `model_catalog_json`, the gateway `model`, `[model_providers.automaticai]` with `.auth`, `[agents].default_subagent_model`, `[profiles.openai-direct]`, and `[shell_environment_policy]` with `.set`. The last one is the gateway env that Codex Desktop's Claude import copied over on 11-16; it also set `inherit = core`. Set `model = "gpt-6.1-terra"`, his pre-33GOD value. Plugins, MCP (lamp, node_repl), projects and `hooks.state` are untouched.
- `~/.codex/hooks.json`: removed the 10 bb-hook groups. His git-checkpoint group stays at index 0, so its trust hash still matches.
- Instructions: removed the 33GOD `<!-- name:start/end -->` blocks (`agents:candybar-policy`, `delegate-to-rere`; the first run also took Damian's own `damian:breadth-first`, now restored) from `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`, and `delegate-to-rere` from `~/AGENTS.md`. His gittyup and THE YARD sections stay.
- `~/.claude/skills` and `~/.codex/skills` were links into the shared `~/.agents/skills`. They are now plain empty folders.
- Skills: parked 202 entries.
  - In `~/.agents/skills`: the 60 skillex catalog links (including coaching-practice-catalog and org-chart, see below), ego-browser, and the 10 stripe, metronome and connect folders that arrived with the `~/.agents` copy of `delorenj/agents`.
  - The skillex links in `~/code/space` and `~/code/hello-subconscious-team-inbox`.
  - Links were recorded and removed; folders were moved to `~/.config/33god/mode/parked-skills/`. Nothing was deleted.
  - Left: `source-command-lamp-session`, `source-command-mission` (his commands), `synced/`, `.system`, `.trash`.
- `~/.gitconfig`: unset `core.hooksPath`, which pointed at Jarad's git guards in `~/.agents/git`. The first run also unset `core.excludesFile`. That was the verify blocker, and it has been restored (see below).

## Proof (plain-check.py --live, 17:04Z)

| Client | Turn | Auth / provider | Candystore events | Gateway ledger (token 113) |
|---|---|---|---|---|
| Claude CLI 2.1.325 | `affd3e88-d308-4877-ac48-a13e46b8ce0b`, reply PLAIN-OK-CLAUDE | OAuth token, `apiKeySource=none`, model `claude-opus-5-5` (Anthropic direct) | 0 | 0 rows since 17:02:30Z |
| Codex CLI 0.171.0 (brew) | `01a1ff0f-e265-7da1-98a6-0db72833154c`, reply PLAIN-OK-CODEX-CLI | ChatGPT login, `model_provider=openai` | 0 | 0 |
| Codex Desktop bundled binary 0.169 | `01a1ff10-429d-7131-886b-db32548b2957`, reply PLAIN-OK-CODEX-DESKTOP | ChatGPT login, `model_provider=openai` | 0 | 0 |

- The only bus traffic in that window is infra heartbeats: `system.hook.updated` from hook-hub every 30 s, and Candybar ticks.
- Gateway rows for token 113 today: 02:56Z (Codex in gateway mode, last night) and 11:00Z. 11:00Z is 06:00 ET, which matches the `mac-dev-journal-nightly` Candybar job, not Damian.

## Adversarial verify and fixes (17:05-17:40Z)

Two read-only agents checked the work: one tried to show the Mac is not plain, the other tested whether `on` would undo it. Their findings and what was done:

| Finding | Fix |
|---|---|
| **Blocker.** Unsetting `core.excludesFile` removed the Mac's only global ignore list. Damian's git-checkpoint hook runs `git add -A`, commits and pushes, so the next session end would have committed about 2,900 junk files: 1,659 `node_modules` files in `space`, 1,104 in team-inbox `.worktrees`, and `.env` files. | `GIT_KEYS` is now `core.hooksPath` only. The ignore list is passive and stays. Restored on the Mac. New plain-check row `git/global-ignore-present`. |
| Damian's own instruction block `damian:breadth-first` was stripped along with the 33GOD ones. | Only blocks whose names match `PEER_BLOCK_RE` are parked: `agents:`, `delegate-to-`, `33god`, `hindsight`, `candybar`, `candystore`, `bloodbank`, `hermes`. Restored on the Mac. |
| Claude could no longer see Damian's own skills in `~/.agents/skills` after `~/.claude/skills` became an empty folder. | In plain mode, `~/.claude/skills` gets links to the non-33GOD entries of the shared folder. `on` treats those links as its own, not as extras. New row `skills/own-skills-visible-to-claude`. |
| A manual `skillex sync` would re-link all 60 catalog skills (`[cli.codex] enabled = true`). | `off` flips it to false and `on` flips it back. New row `skills/skillex-global-sync-off`. |
| plain-check did not watch the Ego browser's link. | The catalog check now also matches `~/.local/share/ego/`. |
| The `on` mode with both the gateway apiKeyHelper and the restored OAuth export had never been tested. | Tested live, see below. |
| A `__pycache__` left in `~/.local/bin`. It came from the verifier importing the script. | Deleted. |

The fixed switch was deployed and run on the Mac as a live round trip:

- 17:27:51 `on`: everything came back, including 202 skills, 3 docs, git guards and hooks.
- One interactive Claude turn reported `apiKeySource=apiKeyHelper` with model `automaticai/auto/orchestrator`, so the gateway outranks the OAuth export. The gateway ledger shows exactly that one row, 17:28:00Z.
- 17:28:08 `off` with the new rules, then `codex app-server daemon restart`.
- 17:40Z `plain-check.py --live`: **22/22 PASS**, with 0 Candystore events for any of the 3 turns:
  - Claude `8e072f0a-72ac-4923-b254-8d0336e4423d` on `claude-opus-5-5`, apiKeySource none
  - Codex CLI `01a1ff30-f03d-7a13-8303-51d14b13a57d`, provider openai
  - Desktop binary `01a1ff31-5a3a-7033-97da-b2c19d30943e`, provider openai
- Gateway ledger for token 113 has no rows after 17:28:00Z.

plain-check now runs the Claude turn through `zsh -i`, the way Damian runs it, and gives every command `/dev/null` as stdin, because `codex exec` waits on an open stdin. The non-interactive Claude path fails: `~/.claude/.credentials.json` (Nov 12) has `expiresAt 0` and a refresh that no longer works, and there is no keychain item.

## Known gaps

1. **ChatGPT.app GUI has not been relaunched.** It started 2026-11-20 21:51 with the gateway config, so Damian must Cmd+Q and reopen it. Until then, Desktop GUI turns still use the old config. Its Claude-import sync runs on launch and now imports a clean `~/.claude`.
2. **Claude login works in interactive terminals only.** That matches pre-33GOD. A `claude` started from a non-interactive shell has an expired stored login (see above); `/login` once in a terminal fixes that permanently through the keychain. Not tested over ssh: the Claude desktop app, which uses its own sign-in.
3. **coaching-practice-catalog and org-chart are parked.** Damian's name is on the commits, but they were written in the 33GOD era inside Jarad's catalog. `33god-mode on` brings them back.
4. **Still 33GOD, by design:**
   - The Hermes desks (gateway inference).
   - The `mac-dev-journal-nightly` email, which uses the gateway token.
   - The starship prompt's pjangler segment.
   - The infra services.
   - GitMark's narrate step reads local Candystore at :8683 for commit-message context. It is read-only, uses local ollama, and is Damian's own tool.

   None of these are Claude or Codex user config.
5. **Project-level, not switched:**
   - `~/code/CoachingAgentFramework` `AGENTS.md`/`CLAUDE.md` carry a mandatory session bootstrap. It loads `~/.agents/skills` and runs a Hindsight recall over ssh to big-chungus. Its `lamp-skills/.agents/skills` holds 91 vendored skills, including hindsight and vox-tts.
   - `~/code/33GOD` itself is 33GOD by definition.

   These are files in Damian's repos, so `33god-mode` does not edit them.
6. **Ego browser** may re-create `~/.agents/skills/ego-browser` on its next start or update. plain-check now flags it, and `33god-mode off` re-parks it.
7. **Old threads:** 17 Codex threads were created on `automaticai/auto/orchestrator`. Resuming one may ask for that model, so start new threads.

## Toggle

```
33god-mode            # status
33god-mode on         # 33GOD back, exactly as parked (then Cmd+Q / reopen the apps)
33god-mode off        # plain again
```

On a fake-home copy of these exact files, an `off` then `on` round trip gave back `settings.json`, `config.toml`, `hooks.json` and all three instruction files byte-identical, and the skills tree identical. `.gitconfig` came back with the same keys in a different order.

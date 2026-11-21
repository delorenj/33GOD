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
- Instructions: removed the 33GOD `<!-- name:start/end -->` blocks (`agents:candybar-policy`, `delegate-to-rere`, `damian:breadth-first`) from `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`, and `delegate-to-rere` from `~/AGENTS.md`. His gittyup and THE YARD sections stay.
- `~/.claude/skills` and `~/.codex/skills` were links into the shared `~/.agents/skills`. They are now plain empty folders.
- Skills: parked 202 entries.
  - In `~/.agents/skills`: the 60 skillex catalog links (including coaching-practice-catalog and org-chart, see below), ego-browser, and the 10 stripe, metronome and connect folders that arrived with the `~/.agents` copy of `delorenj/agents`.
  - The skillex links in `~/code/space` and `~/code/hello-subconscious-team-inbox`.
  - Links were recorded and removed; folders were moved to `~/.config/33god/mode/parked-skills/`. Nothing was deleted.
  - Left: `source-command-lamp-session`, `source-command-mission` (his commands), `synced/`, `.system`, `.trash`.
- `~/.gitconfig`: unset `core.hooksPath` and `core.excludesFile`, which pointed at Jarad's git guards in `~/.agents/git`.

## Proof (plain-check.py --live, 17:04Z)

| Client | Turn | Auth / provider | Candystore events | Gateway ledger (token 113) |
|---|---|---|---|---|
| Claude CLI 2.1.325 | `affd3e88-d308-4877-ac48-a13e46b8ce0b`, reply PLAIN-OK-CLAUDE | OAuth token, `apiKeySource=none`, model `claude-opus-5-5` (Anthropic direct) | 0 | 0 rows since 17:02:30Z |
| Codex CLI 0.171.0 (brew) | `01a1ff0f-e265-7da1-98a6-0db72833154c`, reply PLAIN-OK-CODEX-CLI | ChatGPT login, `model_provider=openai` | 0 | 0 |
| Codex Desktop bundled binary 0.169 | `01a1ff10-429d-7131-886b-db32548b2957`, reply PLAIN-OK-CODEX-DESKTOP | ChatGPT login, `model_provider=openai` | 0 | 0 |

- The only bus traffic in that window is infra heartbeats: `system.hook.updated` from hook-hub every 30 s, and Candybar ticks.
- Gateway rows for token 113 today: 02:56Z (Codex in gateway mode, last night) and 11:00Z. 11:00Z is 06:00 ET, which matches the `mac-dev-journal-nightly` Candybar job, not Damian.

## Known gaps

1. **ChatGPT.app GUI has not been relaunched.** It started 2026-11-20 21:51 with the gateway config, so Damian must Cmd+Q and reopen it. Until then, Desktop GUI turns still use the old config. Its Claude-import sync runs on launch and now imports a clean `~/.claude`.
2. **Claude login works in interactive terminals only.** That matches pre-33GOD. A `claude` started from a non-interactive shell has no token; `/login` once fixes that permanently through the keychain.
3. **coaching-practice-catalog and org-chart are parked.** Damian's name is on the commits, but they were written in the 33GOD era inside Jarad's catalog. `33god-mode on` brings them back.
4. **Still 33GOD, by design:** the Hermes desks (gateway inference), the `mac-dev-journal-nightly` email (uses the gateway token), the starship prompt's pjangler segment, and the infra services. None of these are Claude or Codex.
5. **Old threads:** 17 Codex threads were created on `automaticai/auto/orchestrator`. Resuming one may ask for that model, so start new threads.

## Toggle

```
33god-mode            # status
33god-mode on         # 33GOD back, exactly as parked (then Cmd+Q / reopen the apps)
33god-mode off        # plain again
```

On a fake-home copy of these exact files, an `off` then `on` round trip gave back `settings.json`, `config.toml`, `hooks.json` and all three instruction files byte-identical, and the skills tree identical. `.gitconfig` came back with the same keys in a different order.

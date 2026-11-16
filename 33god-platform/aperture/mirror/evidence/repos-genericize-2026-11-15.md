# Repos and genericization lane (2026-11-15)

Executor: Claude Code subagent on big-chungus, SSH to Damian's Mac Studio (`hellosubconscious@100.117.109.60`) under the Aperture charter handover (Jarad, untagged, 2026-11-15). Scope: PLAN.md rows W1-3 follow-up, W9-1 (delonet-conventions), the bloodbank pin, Codex Desktop, and the final `clients-check.py` sweep. No secret was printed, written or committed.

Backup of everything touched on the Mac: `~/.config/33god/config-backups/20261116T020637Z-repos/` (pointer `~/.config/33god/config-backups/LATEST-repos`). It holds the pre-reset 33GOD HEAD, both local commits as `git format-patch`, `submodule-status.txt`, the three catalog skill dirs as they were, and the Codex config/hooks before the relaunch. A branch `mac-local-pre-sync-20261116T020637Z` in the Mac's `~/code/33GOD` keeps the old HEAD (`fd68b88`).

## 1. 33GOD parent and submodule pins on the Mac

Found: Mac `~/code/33GOD` on `main`, 2 local commits ahead and 128 behind origin; `bloodbank` checkout at `6cdefcd` (restored by the clients audit) while the parent pinned `db9fd9f`; the nine other checked-out submodules all clean and behind their pins (pure fast-forwards); `candybar` was a stand-alone clone, not initialised as a submodule, and its gitlink in the Mac parent pointed at a SHA absent from `.gitmodules`.

The two local commits (both authored under Damian's git identity):

| Commit | What | Disposition |
|---|---|---|
| `c4ff8e8` docs(aperture/mirror): W8 supersedes (c) with native macOS Vinyl/Wax port | an 11-line PLAN.md note | **Not on origin.** Preserved as a branch plus the patch `evidence/mac-local-W8-supersede-2026-11-14.patch` in this directory. See owner ask 1 |
| `fd68b88` checkpoint auto-commit | adds a `candybar` gitlink at `52ea6e1` | Dropped from `main` (superseded by origin's proper `candybar` pin `28cdcc3`); kept on the backup branch. It comes from the `~/.agents/hooks/git-checkpoint` auto-commit link |

Actions on the Mac:

| Step | Result |
|---|---|
| Parent | `git reset --hard origin/main` after the backup branch and patches existed: HEAD `853f37e` = origin/main at the time, `git status` clean |
| `bloodbank` | `git submodule update bloodbank`: `6cdefcd` -> `28db044` (fast-forward, `6cdefcd` is an ancestor). `sync.py --check`: `hooks-sync: OK`. The diff added two hook-hub handlers (`crank-tag`, `crank-keys-guard`); both only fire on `[crank]` prompts or `hermes` tool calls, so they are inert for Damian |
| other 8 submodules | `candystore e13b70a`, `flume be2fa7e` (plus its nested `templates/hermes-agent` `9445c56`), `hermes-agent-template f41c81c`, `holocene 4758683`, `momo 73d71d3`, `monitoring 933a157`, `pilot 690f3f5`, `pjangler 8d00d67`: all `git submodule update`, all fast-forward, all clean afterwards. `mcp-hub` already matched |
| `candybar` | `git merge --ff-only 28cdcc3` inside its own clone (stays on `main`; one commit behind origin, `b771b27`, the W9-4 manifest, which is newer than the pin). `git submodule status` still prints `-` for it because the Mac never registered it as a submodule; HEAD equals the pin |
| `io.33god.hook-hub` | `launchctl kickstart -k` (runs `bloodbank/services/hook-hub/hub.py` from the checkout, so a restart was required). Health: `running`, no registry/journal/transport error |
| `io.33god.candybar-executor` | `launchctl kickstart -k` at 21:09:57 EST (between fires). Log: `schema guard open: registry head 0010 matches this checkout`; the 21:10 and 21:20 `mac-hindsight-capture-sweep` fires both `scheduled success`; API on `127.0.0.1:8700` still lists `mac-canary`, `mac-hindsight-capture-sweep`, `mac-dev-journal-nightly`, all enabled; no `pyproject`/lock change in the 16-commit delta so no venv sync was needed |
| `pjangler` | source moved to the pin; the running registry service (`node dist/project-registry-service.js`, `dist/` is tracked build output in that repo) was **not** restarted and keeps running its loaded code. None of the other seven checkouts is used by a running service |

End-to-end hook proof (Mac, run before the change, after the bloodbank bump + hub restart, and again after the candybar restart and the final sweep): a synthetic Claude `SessionStart` piped to `~/.local/bin/bb-hook claude SessionStart` exits 0 and Candystore (`docker --context colima exec candystore-postgres ... psql`) returns `bloodbank.agent.session.started | bloodbank.agent.claude | claude` and `bloodbank.agent.hook.updated | hook-hub | claude` for the unique session id. Last run id `aperture-repos-test-022427-18622`. The `clients-check.py` `hook-client` row now reports bloodbank `28db044`.

Finding: the Mac's 33GOD checkout can never push (Damian has pull-only on `delorenj/33GOD`), so any local commit there is stranded; the dropped `checkpoint` commit is the example. The auto-checkpoint link is the source.

## 2. W9-1 genericize delonet-conventions (and the two quick checks)

Canonical source: `delorenj/skills` `all-skills/` (the skillex catalog, live copy `~/code/skillex/all-skills`). Built in a worktree off `origin/main`, pushed to `main`.

| Repo | Commit | What |
|---|---|---|
| `delorenj/skills` | `27d7dc4` | `delonet-conventions` restructure + `delonet-dotenv` scoping |
| `delorenj/skills` | `0a891e8` | fix: quote both `description:` values (my first draft had a colon-space, which made the frontmatter invalid YAML; skillex's pre-push `pytest` (`test_personal_learned_inventory`) caught it before it could reach anyone's links) |
| `delorenj/skillex` | `9260f8f`, `ff5682c` | `all-skills` pointer bumps (convention from W9-1: `835d61f`). Now on `origin/main` |

`delonet-conventions`:

- `SKILL.md` now holds only host-agnostic rules (home layout, shell/BSD portability, secrets as `op://` refs or the interim store, git-ignore policy, project creation, mise, Candybar as the only clock, CI budget, naming, non-negotiables) and a **Step 0** that picks one network file by tailnet (`tailscale status --self --json` MagicDNS suffix), falling back to hostname/OS. Unknown network: no file, do not borrow another's facts, ask the owner.
- `references/networks/delonet.md` (Jarad): LAN `192.168.1.0/24`, `burro-salmon.ts.net`, `delo.sh`, Traefik/Cloudflare Tunnel, `zshyzsh`/`$ZC`, op-cache, CI runners, parental controls, editors, operator style. Its deep references moved under `references/networks/delonet/` (`docker_patterns`, `docker-service-provisioning`, `selfhosted-agent-infrastructure`, `tailscale_audio_forwarding`, `zshyzsh_patterns`, `project_patterns`), each with a "DeLoNET only" banner.
- `references/networks/tuxedo-morpho.md` (Damian): tailnet `tuxedo-morpho.ts.net`, Mac Studio / macOS 26 / arm64, launchd user agents, Colima (`docker --context colima`, Docker Desktop is the default context and must not be used), BSD userland, Homebrew python 3.14 first, loopback ports (Candybar 8700, hook-hub 8685, Hindsight 8888, Candystore 8683, NATS 4222), the interim secret store (`secrets.env`, `refmap.tsv`, `host.env`, `env-op-resolve`), gateway route policy, Candybar-only scheduling, no CI runner, pull-only repo access. Operator style: "no recorded preferences" (nothing invented).
- `references/ci-runners.md` **stays at its old path** (pjangler templates, three workflows and the global agent instructions link to it) with a DeLoNET-only banner. `shell-context-independence.md` stays generic; two `/home/delorenj` paths became `~/`.

`delonet-dotenv`: it is wholly big-chungus conventions (constants, `delo.sh`, Traefik, MinIO, Jarad's email) except the interim-store half, which is the part the Mac uses. Fix: a "Two halves" banner at the top of `SKILL.md`, the description and the Out-of-scope line now say only the interim-store half applies on peer hosts, and a DeLoNET-only banner on `constants.md`, `decisions.md`, `traefik-routing.md`, `gotchas.md`. No code changed.

`delonet-daily-report`: swept for Jarad hardcodes (LAN, tailnet, `delo.sh`, `/home/delorenj`, personal email, Slack/Telegram ids, vault names). **None found** (W9-1 of 2026-11-12 already genericized it; the only `op://DeLoSecrets` mention is an example in the safety rules). No change.

Mac side ("pull the skills so his links serve the new content"): `~/.agents/skills/delonet-{conventions,dotenv,daily-report}` link into `~/code/skillex/all-skills/<name>`, which on the Mac is an untracked copy imported at `ec902ce` (not a git checkout of the upstream). I rsynced the three upstream directories over those copies (`--delete`, keeping each dir's `.source.yaml` provenance, no git operation in that repo) after copying the originals into the backup dir, and moved the installed clone `~/.local/share/33god/skills` (the one `nightly.sh` runs from) to `0a891e8` (no `delonet-daily-report` or `activity-report` delta in the 5 commits, hashes equal before and after). Proof: `~/.agents/skills/delonet-conventions/references/networks/{delonet.md,tuxedo-morpho.md}` exist and serve the new `SKILL.md`; `skillex status --scope global` exit 0 (60 owned, receipt valid); `skillex skill show delonet-conventions` still reads `modified_locally: false`. Resync run `20261116T022228Z-0ebc8a2f`: `attention`, the same single expected desk (`team-inbox`, the unapproved cutover). Not verified: that the stored import digest in `.source.yaml` is not recomputed later; it did not complain.

## 3. Codex Desktop

The "Codex Desktop" app on this Mac is `/Applications/ChatGPT.app` (it hosts the Codex framework; there is no separate `Codex.app`). It was running (up 1 day, started before the provider fix) and Damian was away: HID idle 24,568 s (6.8 h), no Codex thread activity since 2026-11-14 20:30 (the only log rows in the last day are the app's own `getAuthStatus` heartbeat every 2 minutes), no rollout file newer than my 13:33 headless runs. Checked `~/.codex/config.toml` parses and carries `model_provider = "automaticai"`, `model = "automaticai/auto/orchestrator"`. Quit with `osascript -e 'tell application "ChatGPT" to quit'` (clean exit, 0 processes), reopened with `open -a ChatGPT` at 21:23 EST; new process 18310 and a fresh `codex app-server` came up.

Not verified: GUI-originated hook events. I cannot drive the GUI (osascript has no assistive access over SSH). After the relaunch the app-server log shows only the known dead-MCP noise (`http://localhost/mcp`, the lamp MCP the app re-imports from `~/.claude.json`). Next real Damian prompt closes it; check:
`docker --context colima exec candystore-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "select type, actor->>$$cli$$, created_at from events where actor->>$$cli$$='"'"'codex'"'"' order by 3 desc limit 5"'` (or just re-run `clients-check.py --live` after he uses it).

## 4. `clients-check.py` sweep (2026-11-16 02:24 UTC, non-live)

| Client | Requirement | Status | Note |
|---|---|---|---|
| claude-cli | skills | PASS | `~/.claude/skills` -> `~/.agents/skills` |
| codex-cli | skills | PASS | `~/.codex/skills` -> `~/.agents/skills` |
| claude-cli | hooks | PASS | 13 events via `bb-hook --cli claude` |
| codex-cli | hooks | PASS | 10 events via `bb-hook --cli codex` |
| hook-client | hooks | PASS | bloodbank `28db044`, `hooks-sync: OK` |
| hook-hub | hooks | PASS | `running` |
| claude-cli | provider | PASS | `apiKeyHelper` + env block, no mismatches |
| codex-cli | provider | PASS | `automaticai`, `automaticai/auto/orchestrator`, `/v1`, `responses` |
| helper-claude-code | provider | PASS | token resolves, len 51, sha256[:8] `8cd8d112` |
| helper-codex | provider | PASS | same token |
| gateway-claude-code | provider | PASS | `/v1/models` 200, 26 routes, auto family present, `aai/damian/auto` literal absent (as decided) |
| gateway-codex | provider | PASS | same |
| all | no-secrets-in-config | PASS | 3 config files clean |
| claude-desktop | all | N/A | Claude.app not installed |
| codex-desktop | installed | PASS | ChatGPT.app present, relaunched on the new config |

Totals: 14 PASS, 0 FAIL, 1 N/A (15 rows).

## Owner asks

1. **Fold Damian's W8 note into PLAN.md.** His commit `c4ff8e8` (native macOS Vinyl/Wax port supersedes pairing option (c); Parakeet v3 Studio benchmark; blocker: his GitHub account cannot see `delorenj/vinyl`) is not in origin. The patch is `evidence/mac-local-W8-supersede-2026-11-14.patch`; apply it by hand to the W8 block (I did not edit PLAN.md).
2. **skillex pushes are gated by a red node test suite on this host** (several `✖` in `npm test`: Hermes/Kimi client-root cases, unrelated to skills content), on top of the YAML failure above that was mine and is fixed. My `git push` printed only `failed to push some refs` on two retries; `origin/main` is now `ff5682c`, so the bump did land, but I did not establish who pushed it or why my own attempts reported failure. Not investigated further.
3. Close the Codex Desktop GUI-hook gap with one real Damian prompt (or a `clients-check.py --live` after it).
4. Optional hygiene (Damian's call): the Mac's `~/.agents/hooks/git-checkpoint` auto-commit keeps writing commits into `~/code/33GOD` that can never push.

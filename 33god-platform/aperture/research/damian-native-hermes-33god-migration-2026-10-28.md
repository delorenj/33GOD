# Damian's native Hermes -> 33GOD Hermes: in-place migration record (2026-10-28)

> **Executed under Jarad's explicit hand-over.** On 2026-10-28 Jarad handed this session the
> authority to act on Damian's Mac Studio for this migration, overriding CHARTER §1/§3.8
> ("only Rererere acts on Damian's machine") for this task only. This is a record of what was
> done, not a standing authorization.

Target: `hellosubconscious@damians-mac-studio` (100.117.109.60), macOS 26.3 arm64.
Preceded by five read-only scouting reports on 2026-10-28 (Damian's native Hermes, the 33GOD
contract, macOS tooling, Aperture governance, the gateway's Damien Personal channel).

## Operator decisions applied (Jarad, 2026-10-28)

1. **Routing:** all of Damian's Hermes inference goes through the AutomaticAI gateway "Damien
   Personal" channel (consumer token `damien-personal`, scoped to the 13 `automaticai/damien/*`
   Claude routes plus the `automaticai/auto*` family, no free routes). Main `auto/orchestrator`,
   delegation `auto/subagent`, auxiliary `auto/fast`. Codex (`openai-damien`) not connected.
2. **private-desk privacy rule nixed:** its SOUL no longer says "local models only / never send
   source material to cloud models"; intake-and-sorting purpose and folder workflow kept; its
   Ollama model pin dropped.
3. **Secrets:** target-local mode-0600 `.env` files (accepted exception to `op://` refs). No
   DeLoSecrets references and no 1Password service token on Damian's Mac.
4. **Cutover in place** to the delorenj/hermes-agent fork (`main` @ `20a9721964`, same config
   version 50 / state schema 31 as his v0.22.0 app, so no downgrade). One multiplexed launchd
   gateway. Nous "Hermes Agent.app" parked (quit, not uninstalled); `~/Code/hermes-agent`
   (upstream v0.15.1) retired as a consumer (not deleted).
5. **Memory:** Damian's local Hindsight (`127.0.0.1:8888`, `io.damian.hindsight-studio`) with
   fresh banks per desk; widened from synthetic-only for those desks (recorded in
   `~/Code/damian-33god-deploy/docs/hermes-33god-hindsight-desk-banks-20261028.md`, commit
   `b4f4fcd` there). Jarad's banks never shipped. bb-hook installed but off (`BB_HOOK_HUB=off`):
   the G1 NATS bus has no host port.
6. **Untouched:** Jarad's `aai-personal` auto pool, OpenClaw jobs, Docker/Aperture `god-g*`
   stacks, Plane, n8n, the pjangler registry.

## What changed on Damian's Mac

| Area | Before | After |
|---|---|---|
| Runtime | Hermes Agent.app v0.22.0 bundled payload (`serve` for private-desk + cron for all homes); `~/.local/bin/hermes` -> `~/Code/hermes-agent` v0.15.1 | One install: `~/.hermes/hermes-agent` = delorenj fork `20a9721964` (full clone, tracks `delorenj/main`, no Nous remote), managed toolchain in `~/.hermes/tools`, extras all + voice + stt-whisper + messaging |
| Entry points | wrappers/symlinks into the app payload and the old checkout | `~/.local/bin/{hermes,aai-team,private-desk,hermes-agent,hermes-acp}` are 2-line shims to the fork launcher; nothing on PATH resolves to the app or the old checkout |
| App | running since 2026-10-20 | quit gracefully; orphan `browser_harness.daemon` (since 2026-10-18) killed; no login item; still installed |
| Fleet base `~/.hermes/config.yaml` | openai-codex / gpt-6.1-sol, ElevenLabs TTS, built-in memory | Damian's own preferences kept; model/delegation/auxiliary/MoA on the gateway (auto names), `free_only`, `discovery: false`, fallback `[]`, 9 bb-hook hooks (hub off), `memory.provider: hindsight`, `tts.provider: vox` (`https://vox.delo.sh`, his voxxy default), `gateway.multiplex_profiles`, bloodbank toolsets + 1800 s tool timeouts |
| Desks | hand-made `aai-team` (no config version) and `private-desk` (Ollama Qwen pin) | generated desks: override-only `config.delta.yaml`, rendered `config.yaml` (check clean), identity-only `profile.yaml`; aai-team lockdown kept minus its codex pin; private-desk Ollama pin and the cloud ban dropped, toolsets/reasoning kept; both chat platforms disabled |
| Secrets | `~/.hermes/.env` 0644 (blank keys) | every `.env` 0600; `AUTOMATICAI_GATEWAY_KEY` (damien-personal) in base + desks, `HINDSIGHT_API_KEY` in desks, `BB_HOOK_HUB=off`; no `op://` anywhere |
| Memory | built-in only | `hindsight` plugin pinned `d56c4ac` in base + both desks; banks `agent-aai-team`, `agent-private-desk` created, pinned, retain+recall proven |
| Skills | desks held a copy of the bundled `hermes-agent` skill | strict Skillex-only (`.skillex-only`, `.no-bundled-skills`), selection = Damian's global selection (currently empty); foreign entries quarantined under `~/.hermes/.skill-quarantine/`; resync LaunchAgent `io.33god.skillex-hermes-resync` healthy |
| Org chart | none | `~/.hermes/agents-registry.yaml` (his own): two portable-specialist rows, bloodbank quarantined (no bus port), fork pin; definitions in `~/.agents/workforce/<id>/agent.yaml` |
| Gateway | none | LaunchAgent `ai.hermes.gateway` (loaded in `user/501`, installed over SSH), serving default + aai-team + private-desk with zero chat platforms; it is now the cron ticker for every home |
| Transcriber | `com.damian.private-desk-transcriber` ran the app payload's python | runs the same script on the fork runtime through a wrapper; local STT re-proven |
| Tooling | old clones | `~/Code/{flume,hermes-agent-template,skillex}` updated (his local edits kept), flume built on Node 24 (`~/.local/bin/flume`), npm skillex 0.3.1 side by side (`~/.local/bin/skillex-npm`; his Python `skillex` untouched), Homebrew bash 5.3, PyYAML venv, host `config.toml` + `fleet.env` retargeted |

## Adopted vs fresh, and what this did NOT do (charter §3.5)

- **Adopted existing state:** both desks (`aai-team`, `private-desk`) with their `state.db`
  history, hand-written SOULs (aai-team unchanged; private-desk rewritten only per decision 2),
  the base home's MotherHen/LAMP memories, the transcriber script and its LaunchAgent, Damian's
  config preferences, his Hindsight Studio service (widened, not replaced).
- **Fresh-provisioned:** the fork install and toolchain, the fleet base invariants, the two
  Hindsight banks (empty at creation), the org chart, the gateway and resync LaunchAgents, the
  npm skillex install, the bb-hook client.
- **Not done:** no Docker restart, no change to the `god-g*` stacks, OpenClaw, Plane, n8n or the
  pjangler registry; no chat bot wired; no Bloodbank activation; no `op`/vault on his Mac; no
  copy of any operator bank, SOUL or personality; the parked app was not uninstalled and
  `~/Code/hermes-agent` was not deleted; no commercial or client-facing surface was created (the
  routing is Jarad's own decision 1, on Damian's own Claude account channel).
- **Status:** execution record under the hand-over above. It authorizes nothing further.

## Proof

- Oneshot per desk -> "OK" on `automaticai/auto/orchestrator` (sessions `20261028_150857_4878e1`,
  `20261028_150904_7d21c3`).
- Gateway ledger rows 535370-535374, token `aai:damien-personal`, account `claude-damien`,
  channel 10, quota 0: two `damien/claude-opus-5.5` turns (19:09:01Z, 19:09:07Z) and two
  `damien/claude-haiku-4.5` auxiliary calls; every personal/intelliforia alternative
  "excluded: scope".
- `hermes-single-install-check.py`: OK (15 consumers on one install).
- flume: roster in good standing; host rules fleet-config, bloodbank-toolsets,
  dotenv-no-op-refs, wake-word-session, delta-list-override and systemd.sentinel pass;
  gateway-routing fails only on the two operator-accepted points (curated route list,
  no `op://` mapping); skillex-resync warns (rule is systemd-only); `review` is "unhealthy"
  on portable-specialist singleton links (the operator's own rererere fails the same way);
  `audit --employee` is "unable to assess" (adopted desks carry no hire marker; Damian's catalog
  checkout cannot resolve the `global` set).

## Tooling changes landed on big-chungus (all pushed to main)

- skillex `43025ec` (resync LaunchAgent pins `SKILLEX_BIN`), `aa59c85` (cutover honours
  `SKILLEX_BIN`).
- flume `c92e969` (launchd gateway found in `gui/<uid>` or `user/<uid>`), `f15ed49` (template pin).
- hermes-agent-template `17eade8`: `docs/adopt-existing-hermes-host.md`, the generic runbook.

## Rollback

Backup on the Mac: `~/hermes-backups/pre-33god-20261028T181710Z/` (owner-only) with `ROLLBACK.md`:
full `~/.hermes` tarball, consistent `state.db` copies, app support dir, original
`~/.local/bin` entries, transcriber plist, rc files, pre-edit copies of the host config,
fleet.env and configs, and the original Hindsight boundary files. Full rollback = bootout the
new LaunchAgents, move `~/.hermes` aside and extract the tarball, restore the wrappers and the
plist, relaunch the app.

## Open items

- **Codex device sign-in** for `openai-damien`: Damian must do it himself
  (`oauth-connections.py begin openai-damien ...`); then routes, scope and tiers.
- **Damian's other subscriptions:** none found in the vault; nothing wired.
- **private-desk privacy:** the local-only rule was removed by operator decision; private
  Inbox material now goes to cloud Claude via the gateway when the desk works on it.
- **Global skill selection is empty** on his host (`~/.agents/skills.json` =
  `{"inherit_global": true}`), and his catalog checkout (`~/Code/skillex/all-skills` @ 9ab19b2,
  staged deletions, a failed update dir from today) cannot resolve the shared sets. The desks
  run with no catalog skills until that is sorted by whoever owns it.
- **Base (default) profile memory:** `bank_id_template: agent-{profile}` resolves to
  `agent-default`, which the Hindsight boundary still refuses (not authorized). Bare `hermes`
  is sticky on `private-desk` anyway (`~/.hermes/active_profile`), left as Damian had it.
- **Bus:** rows quarantined (`bloodbank.enabled: false`) and `BB_HOOK_HUB=off` until God-G1 NATS
  (or an edge) is reachable from the host and a hook-hub runs there.
- **aai-team channels:** Telegram/Slack deferred; no bot credential exists on his side.
- **flume gaps** (no adopt path; curated route list and `op://` requirement in gateway-routing;
  skillex-resync rule systemd-only; fleet.env `$'...'` quoting) - see the runbook's "Known gaps".
- **OpenClaw** jobs and the plaintext keys in the dead `ai.openclaw.gateway` plist were not touched.
- The installer appended a guarded `~/.local/bin` PATH line to `~/.zprofile`.

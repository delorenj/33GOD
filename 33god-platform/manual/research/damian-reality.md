# Damian's reality (input to The Manual, I-10)

Snapshot: 2026-11-11, about 10:00 to 10:15 EST. Live readback over read-only ssh to `hellosubconscious@100.117.109.60` (Mac Studio, M3 Ultra, 96 GiB, macOS 26.3, up since the 2026-11-10 19:27:59 hard reset), checked against the I-6.1 evidence in `/home/delorenj/code/33GOD/33god-platform/aperture/mirror/`. Where a doc and the live box disagree, the live box wins and the doc is named. No secret value was read or printed. Client names that appear in Damian's own tools are deliberately left out.

## 1. One-paragraph truth

Waves W0 to W4 of the I-6.1 mirror are done, so Damian's Mac runs a working, partial 33GOD peer. It has its own event bus, its own Candystore, its own hook pipeline, its own Plane, its own pjangler registry and px against that Plane. Waves W5 to W10 have not started. Candybar, the Flume workforce, the Hindsight stack swap, HeyMa dictation, the enricher, the daily report and notifications are all absent. `PLAN.md`'s header ("nothing in this plan has been executed") is stale. The last mirror commit is `d3f3f27` (W3+W4 closeout, 2026-11-10 21:39). Damian has accepted the two GitHub invites (pilot, monitoring) but has not yet done the setup-script items or anything on the HeyMa path.

## 2. What is installed, and its state

State is as of the live probe. "Evidence" is the file that proves how it got there. The paths are under `/home/delorenj/code/33GOD/33god-platform/aperture/mirror/evidence/` unless stated.

| Component | Where and how | State now | Evidence |
|---|---|---|---|
| Colima 0.10.3 | brew service `sh.brew.colima` in `gui/501`; VM vz + virtiofs + rosetta, 12 CPU / 32 GiB / 200 GiB | running, 15 h. Starts only at GUI login, so after a reboot someone must log in at the console | W0-2.md, post-crash-2026-11-10.md |
| Plane v1.4.2 (12 containers) | Colima; `0.0.0.0:80` and `127.0.0.1:8443`; `plane.local` published by LaunchAgent `local.plane.bonjour` | running, `plane.local` returns 200. Workspaces `damians-desk` (19 projects) and `hello-subconscious-team` (1). 185 issues including one cancelled px probe (HSCOMP-4) | W0-3.md, W4-3.md |
| n8n-foundation 2.44.4 | Colima, `127.0.0.1:5678` | healthy. 1 workflow and 1 credential, both synthetic prototypes | W0-3.md |
| pjangler registry | native LaunchAgent `io.33god.pjangler-registry` (source build, bound `0.0.0.0:8764` by decision) plus PG16 on Colima `127.0.0.1:18765` | running (PID 29525, last exit 0). `pj list` shows 7 projects, all now pointing at restored repos under `~/code`. Password rotated in W4-1 | W4-1.md, W4-2.md |
| 1Password cache redis | Colima, `127.0.0.1:6379` | healthy, cache only | W0-3.md |
| NATS JetStream bus (project `33god-bus`) | Colima, `127.0.0.1:4222`; `bloodbank-nats` plus `dapr-placement` | healthy. Streams `BLOODBANK_EVENTS` (7 d), `BLOODBANK_COMMANDS` (1 d, workqueue), `GIB_EVENTS` (30 d), identical to big-chungus. 4,226 messages in EVENTS right now | W2-2.md; live `nats stream info` |
| Candystore (project `33god-store`) | Colima: candystore app, pgvector PG16, candystore-daprd 1.13.0; `127.0.0.1:8683` | healthy, `/healthz` 204. Fresh empty DB, nothing of Jarad's migrated. Reads the bus through the Dapr `pubsub.jetstream` component (durable `candystore-events`) | W3-1.md |
| hook-hub | native LaunchAgent `io.33god.hook-hub`, `127.0.0.1:8685`, launcher wrapper at the durable `~/.local/share/33god/hook-hub/` | running, publishing, 0 pending. Handlers like `claude-notify`, `nanoleaf`, `zellij-notify` are still enabled and may no-op on a Mac | W2-3.md |
| bb-hook client and `~/.agents/hooks` | repaired wrapper, `BB_HOOK_HUB` on | works. A real Codex turn landed in the stream. Fail-open is fast for a missing socket but not bounded for a hung hub (15 s). `sync.py --install` must not be re-run on the Mac | W2-4.md |
| Interim secrets store | `~/.config/33god/secrets.env` (0600), `refmap.tsv`, `~/.local/bin/env-op-resolve` | working. Four key names: the Jev `damian-studio` key, the pjangler PG password, the Candystore PG password, the Plane px token. There is no `RESEND_API_KEY` | W0-5.md, W4-1.md, W4-3.md |
| Toolchain | coreutils, gnu-sed, nats 0.5.1, minio-mc via brew; `gh` via the mise shim, authed as `DamiMiller` | working in login shells and under launchd PATH | W1-1.md |
| 33GOD checkout | `~/code/33GOD`, all 10 submodules initialized (pilot and monitoring after Damian accepted two GitHub invites); `candybar/` cloned but not installed | main is 3 commits behind origin; the bloodbank submodule is checked out at a commit that differs from its gitlink (W2-3 moved it to the genericized `8cfa82e` line). Both are known drift | W1-2.md |
| px 0.5.0 | launcher `~/.local/bin/px` (pins node 24.15.0), bound by `~/code/hello-subconscious-company/.project.json` to `plane.local`, workspace `damians-desk`, board `HSCOMP` | `px whoami` returns ok. The token comes from the store. Writes act as `damian@hellosubconscious.com`. The older px 0.4.2 links were repointed to this launcher | W4-3.md |
| Hermes gateway | one multiplexed LaunchAgent `ai.hermes.gateway`, 6 profiles, install `~/.hermes/hermes-agent` at `20a9721` (the 2026-10-28 install) | running. Telegram connected for `music-lab-pm`. Not yet moved to the reviewed pinned SHA (W6-1 pending). The `music-lab-pm` cron tick throws `FileExistsError` on its cron dir every minute | post-crash note, W4-2.verify.md, live `gateway.error.log` |
| Skillex resync | `io.33god.skillex-hermes-resync`, `StartInterval=900` (a policy violation, to move to Candybar in W5-4) | not running, exit 1 every run. 6 strict desks refuse or error because the Mac's catalog lacks the `bmad-*` and `delonet-*` skills. 50 broken links under `~/.agents`, 267 under `~/.hermes` (BSD `find -L -type l`) | W1-3.md, live `hermes-resync.last.json` |
| Cruise Control gateway | Damian's own separate gateway (the team-inbox profile), `:8642` | healthy (200). Restored from `~/code.backup` after the reset. Not ours, not touched | post-crash note |
| Hindsight Studio | Damian's native service `io.damian.hindsight-studio`, `127.0.0.1:8888`, bearer-gated (401 without a token) | running. Made restart-safe in W1-4 (scripts restored to `~/infra/hindsight-studio/scripts`, plist repaired, bridge symlink `~/code/damian-33god-deploy` still in place). Did not return unaided after the hard reset; a stale `postmaster.pid` and socket had to be removed by hand. No fresh PG18 backup or isolated restore yet (W7-1 open) | W1-4.md, post-crash note |
| OpenSign trial | 5 containers on Docker Desktop (not Colima), `127.0.0.1:8791` | running, 200, empty (0 users, 0 documents). Its proxy stalls on Colima for an unknown reason, so Docker Desktop must keep running. No restart policy, so it does not return after a reboot without a manual `docker start` | W0-3.md, post-crash note |
| lamp-skills stack | Docker Desktop, stopped | stopped on purpose. The volume is kept as a backup. Damian decides its fate | W0-1.md |
| Aperture god-g1..g4 | retired with `down` and no `-v`; 11 volumes kept as cold backups | gone as services, as decided | W0-4.md |
| Power policy | `pmset`: sleep 0, womp 1, autorestart 1 | already set before the script (assertions from caffeinate, ChatGPT and powerd also hold it awake) | post-crash note, live `pmset -g` |
| `~/damian-setup.sh` | present (8,515 B, same as the repo copy) | never run (no `~/Library/Logs/damian-setup-*.log`) | `scripts/damian-setup.sh` |

Not installed and not started (W5 to W10): Candybar control plane and executor (so `candybar` is not on PATH), Flume workforce build, the Hermes SHA update, the Hindsight compose stack and bank migration, HeyMa and Vinyl (only `~/.config/vinyl/token` exists, and neither `vinyl` nor `HeyMa.app` is installed), turn-enricher, daily report and rollups, MinIO consumer scoping, ntfy, the artifact projector.

## 3. Damian's own world

This is what he does all day. It is not a software shop. It is a coaching and creative business that happens to run on agents.

- **Business.** Hello Subconscious, run with a partner (Lilian). His Plane (`plane.local`) holds 19 projects in `damians-desk`. The biggest are LAMP (workbook and participant delivery, 30 issues), CONTROL (control room and agent infrastructure, 18), LILIAN (private staging, 17), FRONT (website and client journey, 14), ADMIN (11) and MUSIC (11). A second workspace, `hello-subconscious-team`, has one TEAM board with about 30 issues. HSCOMP ("Hello Subconscious Company") is the board his px is bound to and has 4 issues.
- **His repos** (`~/code`): `hello-subconscious-company`, `hello-subconscious-team-inbox`, `space` (people workspace, calendly commissioning, Hermes templates), `Music Lab`, `CoachingAgentFramework`, `pjangler-learning-lab`, `hellosubconscious-site` (a Next.js site), `HSub` (his Obsidian vault, also `~/HSub`), `damian-33god-deploy`, `skillex`, `33GOD`. Also `~/HeyMa` (the HeyMa monorepo), `~/openclaw-mission-control` and `~/plane-selfhost`.
- **His agent desks (Hermes profiles, one gateway).**
  - `aai-team`: company coordination for Damian and Jarad. Telegram not provisioned.
  - `private-desk`: his private intake and sorting partner. It reads `~/Private Desk Intake` (folders Inbox and Processed).
  - Cruise Control (profile `hello-subconscious-team-inbox-team-inbox`): the team-inbox agent. It has its own Telegram bot `@cruise_control_hs_bot` and its own gateway. It serves the HELLO SC OPS group for Damian and Lilian.
  - `music-lab-pm` (bot `@music_lab_pm_bot`, role `pm`): the only desk with the PM role.
  - `lamp-ops-task-agent-team-inbox` and `space-owner`: Flume-composed placeholders.
  - There is no PM desk for the HSCOMP board. That arrives with the Flume work in W6.
- **Music lab.** `~/code/Music Lab` with Relay (a Mac controller app for his EP-133 sampler, with pad maps), a `Sound` repo and the `music-lab-pm` desk.
- **His own services (his, not 33GOD's).** The OpenClaw set (webhook-server, lili-run, caffeinate running; the gateway exits 78, broken since before the reset), `damian-space`, `eclipse-iphone`, `space-tunnel` (cloudflared), `team-cockpit-staging`, `mission-control-sentinel` (not loaded), `private-desk-transcriber`, `task-backup`, Sunshine and Moonlight for remote desktop, Ollama. Apps: Ghostty, Codex, ChatGPT, Obsidian, 1Password, Tailscale, Docker Desktop, Telegram, Slack, Brave. A second Mac, `lamp-base`, sits on his tailnet.
- **Tools he already owns for "what's open".** `yard` (THE YARD, a Vercel-hosted ops surface). The threads I saw were dated May 2026, so treat the Yard as stale as a work list. The mirror lanes also file `33god-mirror-*` threads there.
- **How he talks to 33GOD.** Not through a terminal first. His tools are Codex and ChatGPT, Plane in a browser, Telegram bots, and Obsidian. His `~/AGENTS.md` tells agents to delegate 33GOD and environment work to Rererere with a `delegate-to-rere` skill. W1-3 pruned that skill's link from the Mac, so that instruction now points at nothing. The Aperture CHARTER says Damian is a peer, never a client.
- **Reading style.** The Oct 27 "33GOD Field Guide" (`/home/delorenj/code/33GOD/33god-platform/aperture/guide/`) is the existing attempt to explain things to him. It is a static HTML dossier with about 1,200 visible-text tokens on one page, authored by a fallback Hermes writer (its `PROVENANCE.md` says no Claude was involved). It is the opposite of a LEGO page and is useful as a baseline to beat, not as a style to copy.
- **Technical level.** He has a real toolchain (mise: node, python, go, rust, bun, deno; brew: neovim, tmux, zellij, ripgrep, ffmpeg), so the CLI is not off limits. The limit is attention, not capability.

## 4. What the pictures can stand on today (live proof available)

1. **The nesting meter fits his Mac exactly.** Mac Studio (96 GiB) holds the Colima VM, which holds Plane (12 containers), the bus (2), Candystore (3), n8n, the registry PG and the cache. Beside the VM, native LaunchAgents hold hook-hub, the pjangler registry, the Hermes gateways and Hindsight. Docker Desktop holds OpenSign only. Every bar is checkable with `docker --context colima ps` and `launchctl list`.
2. **The event path is live and provable.** Press Enter in Codex, then `bb-hook`, then hook-hub on `:8685`, then `BLOODBANK_EVENTS` on NATS, then daprd, then Candystore on `:8683`. The stream has 4,226 messages and started yesterday afternoon (first sequence 2026-11-10 14:33), so it will hold seven days once it fills. This is the cleanest "why an event bus on NATS JetStream with Dapr" demo in the whole system, and it runs on his machine.
3. **Plane and px are live.** `px task list` in `~/code/hello-subconscious-company` works against `plane.local`.
4. **Two peers, no federation.** His bus, Candystore, Plane and registry are his. Jarad's are separate. The only shared thing is a remote LLM gateway (Jev). This is a mental-model point the manual should state once.

## 5. Candidate Book 1 topics (ranked)

1. **"Where everything lives" (the nesting-level meter).** It is the grammar's anchor atom, and his Mac is a perfect instance with no stretching. Damian reads it, then can say which things are in the VM, which are native and which are on Jarad's side. His action: none, just a tell-back. It also stops a real source of confusion: why Plane, OpenSign and n8n are in different boxes, and why a login is needed after reboot.
2. **"What happens when you press Enter" (the event path).** This is the page THE_MANUAL.md names as its hardest test. It is live and provable on his box, and he generates events all day. His action: ask any agent a question, then open the stream view and watch one more message land. Mark the page "replay is 7 days" and "announcements, many listeners" as the two ideas to retain.
3. **"Your board and your first ticket" (Plane and px).** The most concrete thing he will actually do. Pictures: folder to `.project.json` to board, token held in the store and not in a file, and `create`, `claim`, `close` or `cancel` as the lanes. On this box px 0.5.0 ran `task create`, `task get` and `cancel -m` cleanly in the W4-3 probe, so an older note that `px task get` is unimplemented is stale here. HSCOMP-4 is an existing cancelled test issue to use as the example. His action: create a ticket, cancel it.
4. **"Your desks" (who you can talk to).** Cruise Control in the HELLO SC OPS Telegram group, `@music_lab_pm_bot` for Music Lab, and the private desk's intake folders. Pictures: a desk is a SOUL (who) plus memory (Hindsight bank `agent-<profile>`) plus skills (what it can do) plus a gateway (the door). Be honest on the page: the skill resync flags all 6 desks (missing catalog skills, resync exits 1) and `music-lab-pm` errors every minute on cron. His action: send one message to a desk and read the reply.
5. **"Three things only you can do" (LEGO numbered steps, with a "+ from another bag" atom).** The set is: accept Jarad's Tailscale share of big-chungus, run `~/damian-setup.sh`, then brew-install HeyMa and the vinyl client. This is the best fit for LEGO's step-and-callout form. It is ranked last because it is not accurate yet. See finding F3. Draft it now but gate publication on W8-2.

Keep in reserve for a Book 2 or a "when it breaks" page: what to check after a reboot (log in at the console so Colima starts, `docker start` the OpenSign set, Hindsight stale-pid recovery) and "which secrets live where" (the interim store and the future 1Password move).

## 6. Pending on Damian (things only he can do)

1. Run `~/damian-setup.sh` (use `--dry-run` first). Today it does little (F3).
2. Accept Jarad's Tailscale share of big-chungus. Until then `big-chungus.burro-salmon.ts.net` does not resolve from the Mac (checked again today: `getaddrinfo` failure). This blocks HeyMa dictation, because the Vinyl server lives on big-chungus. Jarad must share first.
3. Install HeyMa when the share lands: `brew install delorenj/tap/vinyl-client`, `vinyl setup --server <big-chungus MagicDNS>:7733`, `brew services start vinyl-client`, `brew install --cask delorenj/tap/heyma`. Grant Microphone and Accessibility in the GUI at first dictation. The `damian-studio` token is already at `~/.config/vinyl/token`.
4. Resend: sign in to Resend with the shared login (Jarad has it) and confirm `delo.sh` is a verified domain. Someone must also put `RESEND_API_KEY` in the store, since it is not there.
5. Sign in to 1Password (app and CLI) when ready. Create his own vault for the `.env.op` refs. No DeLoSecrets token goes on the Mac.
6. An owner window for the deferred proofs: a logout/login and a reboot persistence check. Colima starts only at GUI login and OpenSign needs a manual start.
7. Owner decisions still open:
   - Which n8n stays (recommended: keep `n8n-foundation`).
   - Keep, restore or delete lamp-skills.
   - The skillex catalog fix, which needs a decision on his dirty checkout (4 ahead, 75 behind). This clears the exit-1 resync and the refused desks.
   - Whether to move the Plane token out of 4 plaintext files he owns (`~/.config/plane/credentials.env`, a cruise-control `.before-restricted-identity` copy, `~/.hermes/fleet.env`, an Ego Lite browser log) and give each desk its own token.
   - The pjangler `0.0.0.0:8764` exposure (decided to keep, recorded).
   - Whether he wants ntfy, the artifact projector, or monitoring.
   - Optionally delete the HSCOMP-4 probe issue in the Plane UI.
8. His own broken services, reported and not touched: `ai.openclaw.gateway` (exit 78), `mission-control-sentinel` (not loaded), `com.openclaw.cron-state-sync` and `zoom-poll` (exit 1), and `team-dashboard` (see F1).
9. His repo `~/code/hello-subconscious-team-inbox` has one unpushed commit (`35345fd` on `codex/booking-agent-repair`). Its origin is the read-only `~/code.backup`, so it cannot push anywhere useful.

## 7. Findings the orchestrator should know

- **F1. team-dashboard is crash-looping, probably because of the mirror's own NF-1 commit.** `com.hellosubconscious.team-dashboard` shows `spawn scheduled`, `runs = 4417`, `last exit code = 1`. Its error log has 4,580 lines of "Dashboard service refused to start at stage=repository; review the production gate evidence." Its `gates.json` and `recovery-receipt.json` (both dated Nov 7) pin repo commit `6f51431`, and `35345fd` appears in neither. The repo's reflog shows the NF-1 fix commit `35345fd` at 21:38:37 on Nov 10 and a branch checkout at 21:38:49, moving HEAD off `6f51431`. The launcher itself exists, and the post-crash note found the dashboard running after the reset, so the commit is the likely trigger. This is a strong inference, not a proof. I changed nothing. Someone with authority should either put the repo back at `6f51431` (keeping the fix on a side branch) or re-record the gate evidence. The NF-1 fix still has to reach `task-backup`, so this needs a choice that keeps both working.
- **F2. `task-backup` has not run yet.** `runs = 0`. The first scheduled run is due about 19:31 EST on Nov 11. Success looks like `runs = 1`, `last exit code = 0`, and one new snapshot. The Nov 9 and Nov 10 snapshots are already missing.
- **F3. `~/damian-setup.sh` is nearly a no-op today and its step A looks for the wrong things.**
  - Step A checks `~/.local/bin/waxd`, `~/.local/bin/transcribe`, `/usr/local/bin/vinyl` and `~/.local/bin/vinyl`. The PLAN's own HeyMa input says Wax and the Vinyl server are Linux-only, and `brew` puts `vinyl` in `/opt/homebrew/bin`. So even after HeyMa is installed, step A will still print "No Wax/Vinyl binaries installed yet".
  - The thing that holds the TCC grants for dictation is `HeyMa.app` (bundle `sh.delo.heyma`), and the grant happens at first dictation.
  - Step B needs `RESEND_API_KEY` in the store, which is absent.
  - Step C is already satisfied.
  - So the script, and any manual page that describes it as written, would teach him something false. Fix the script (or write the page from the HeyMa packaging input), not the other way round.
- **F4. Doc against live disagreements worth knowing.**
  - `PLAN.md` header says nothing was executed (stale).
  - `agents-registry.yaml` still says "Damian's bus (god-g1 NATS) publishes no host port" and keeps every desk's `bloodbank.enabled` false (stale: G1 is retired and a new bus is live on `127.0.0.1:4222`; the bloodbank gateway plugin is still not installed on the Mac).
  - Hermes is still the 2026-10-28 install, not the reviewed pin.
  - Docker's default context is still `desktop-linux`, so always pass `--context colima`.
  - The W1-3 evidence says 329 broken links remain, and today's count is 317 (50 + 267), with the team-inbox runtime links mostly healed by the post-crash restore.
- **F5. The Hindsight Studio hazard is unchanged.** Its supervisor refuses to start over a stale `postmaster.pid`, by design, so another hard reset needs manual cleanup. The `~/code/damian-33god-deploy` bridge symlink is still in place.
- **F6. Two Damian-facing instructions point at removed things.** His `~/AGENTS.md` says to delegate to Rererere using `delegate-to-rere`, whose skill link W1-3 pruned. The Field Guide says "no assumption that the reader has command-line access," while his Mac has a full dev toolchain. Neither blocks the manual, but the first reader's own documents are already out of step with his machine.

## 8. Method and limits

- Live reads: boot time, `pmset`, `launchctl list` and `print` for a handful of labels, `docker --context colima|desktop-linux ps`, `nats stream info`, health GETs on `:8685 :8683 :8642 :5678 :8791 :8888` and `plane.local`, `px whoami`, `pj list`, a read-only `SELECT` on Plane's project and issue tables, directory listings, and the head of the registry, SOULs and READMEs. Nothing was written to the Mac.
- Not checked: macOS TCC state (not readable), whether Telegram messages actually get answered by a desk, the contents of Damian's n8n, any OpenClaw internals.
- The Plane counts come from the database, not the API: 19 plus 1 projects, 4 in HSCOMP.

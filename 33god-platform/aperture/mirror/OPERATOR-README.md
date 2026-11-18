# Operator README: a 33GOD Mac peer (Damian's Mac Studio)

Written 2026-11-17 for whoever operates this Mac next: Jarad, an agent, or Damian. The asker is Damian's Mac. The level is any 33GOD Mac peer, so the procedures below use `PEER_*` overrides and plain labels. Swap the host and they hold for the next peer.

Host: `hellosubconscious@100.117.109.60` (tailnet `tuxedo-morpho.ts.net`), macOS 26.3, Apple silicon, 96 GB. Plan: [PLAN.md](PLAN.md). Acceptance record: [evidence/W10-3-acceptance-2026-11-17.md](evidence/W10-3-acceptance-2026-11-17.md).

## 1. Check health in one command

```
scripts/peer-check.sh hellosubconscious@100.117.109.60          # add --json for machines
```

It runs from big-chungus over ssh and is read-only, apart from one tagged synthetic hook event it sends through the bus and reads back from Candystore. Exit 0 means no FAIL, 1 means a FAIL, 2 means a usage or ssh error. On 2026-11-17 it gave 33 PASS, 4 WARN, 1 FAIL. A green container is not "working". Trust the probe row (hub to NATS to Candystore) over `docker ps`.

## 2. What is installed

Everything under Colima runs on the one Docker daemon. Plain `docker` uses context `colima` (the default since 2026-11-17). Docker Desktop is installed but never started; its volumes are kept cold.

| Component | How it runs | Port | Owner | Data and config |
|---|---|---|---|---|
| Colima (vz, 12 CPU, 32 GiB, 200 GiB) | brew LaunchAgent `homebrew.mxcl.colima` (`gui/501`); becomes system daemon `io.33god.colima` once Damian applies the boot installer | docker socket `~/.colima/default/docker.sock` | 33GOD | `~/.colima/` |
| NATS JetStream and Dapr placement | compose `33god-bus` (`~/33god-migration/2026-11-10/w2-2/compose.bus.yaml`, repo `mac/compose.bus.yaml`) | 127.0.0.1:4222, 8222 | 33GOD | volume in the project |
| Candystore (Postgres, app, daprd) | compose `33god-store` (`~/.local/share/33god/candystore/`, env `store.env.op`) | 127.0.0.1:8683 | 33GOD | project volumes; fresh DB, no Jarad data |
| Turn-enricher | compose `33god-enricher` (`~/.local/share/33god/turn-enricher/`) | none | 33GOD | image `turn-enricher:mac-bfe2a1e` |
| Hindsight (server 1.1.0 plus pgvector PG18) | compose `33god-memory` (`~/.local/share/33god/hindsight/`, env `memory.env.op`) | 127.0.0.1:8888, bearer required | 33GOD | volume `33god-memory_hindsight-pgdata`; 5 banks |
| Candybar control plane (plus Postgres) | compose `candybar` (`~/code/33GOD/candybar/deploy/compose.yml` plus `compose.mac.yml`) | 127.0.0.1:8700, PG 5435 | 33GOD | project volumes; checkout is a plain clone, not a submodule |
| hook-hub | LaunchAgent `io.33god.hook-hub` (`gui/501`) | 127.0.0.1:8685, socket `~/.local/state/33god/hook-hub.sock` | 33GOD | `~/.local/share/33god/hook-hub/`, receipts `~/.local/state/33god/hook-hub/w2-3-receipts.sqlite3`, overlay `~/.config/33god/hook-hub-overlay.toml` |
| Candybar executor | LaunchAgent `io.33god.candybar-executor` (`gui/501`) | 127.0.0.1:8701 | 33GOD | logs `~/Library/Logs/33god/` |
| pjangler registry | LaunchAgent `io.33god.pjangler-registry` (`gui/501`) plus compose `pjangler-registry` (PG) | `*:8764` (kept on purpose), PG 127.0.0.1:18765 | 33GOD, DB is Damian's | `~/infra/pjangler-registry/` |
| Hermes gateway (5 profiles) | LaunchAgent `ai.hermes.gateway` (`gui/501`), install `~/.hermes/hermes-agent` pinned at `2335d9ef` | none | 33GOD runtime, Damian's profiles | `~/.hermes/` |
| Vinyl server and client (voice typing engine) | brew services `vinyl-server`, `vinyl-client` (LaunchAgents `sh.delo.vinyl.*`) | 127.0.0.1:7733 | 33GOD (HeyMa lane) | brew keg; HeyMa cask in `/Applications` |
| flume CLI | `~/.local/bin/flume`, built from the submodule | none | 33GOD | no org, no workforce yet |
| Plane (12 containers) | compose `plane-app` (`~/plane-selfhost/plane-app`) | `*:80`, 127.0.0.1:8443 | **Damian** | his data; his canonical board |
| n8n-foundation 2.44.4 | compose `n8n-foundation` (`~/infra/n8n-foundation`) | 127.0.0.1:5678 | **Damian** | the ONE n8n, kept by default |
| 1Password cache redis | compose `studio-onepassword` (`~/infra/onepassword`) | 127.0.0.1:6379 | **Damian** | his Machines vault tooling |

Native scheduled work is not a LaunchAgent. See section 5.

## 3. Restart procedures

Restart one thing at a time, then run `scripts/peer-check.sh`. Never restart, rebuild or repoint anything marked hands-off.

**Hands-off, always.** Damian's own services: Plane, n8n, the 1Password cache, the OpenClaw agents, team-dashboard, mission-control, task-backup, Sunshine, Ollama, and the Hermes team-inbox gateway (`ai.hermes.gateway-hello-subconscious-team-inbox-team-inbox`, :8642). Never restart the team-inbox gateway. Findings about them are reported to Damian, never fixed in place.

**Compose projects.** Stacks with an `.env.op` render through the resolver, which refuses to render without it:

```
cd ~/.local/share/33god/candystore
env-op-resolve exec --env-file store.env.op -- docker compose -p 33god-store -f compose.store.yaml up -d
```

The same shape works for `33god-memory` (`memory.env.op`, `compose.memory.yaml`) and `33god-enricher` (`enricher.env.op`, `compose.enricher.yaml`). `33god-bus` needs no env. Candybar uses `env-op-resolve exec --env-file deploy/mac/compose.env.op -- docker compose -p candybar -f deploy/compose.yml -f deploy/compose.mac.yml up -d`. Never `down -v`. For a plain bounce, `docker restart <container>` is enough and keeps the existing environment.

**Colima.** Restarting it restarts all 25 containers, so batch it. Before the boot daemon is applied: `brew services restart colima`. After: `sudo launchctl kickstart -k system/io.33god.colima`. Never run `brew services start colima` once the daemon exists: it recreates the user agent and two supervisors fight over one profile. If the daemon gave up (6 starts in 10 minutes), read `/Library/Logs/33god/colima-default.log`, fix the cause, `rm /Library/Logs/33god/colima-default.starts`, then kickstart.

**hook-hub and the Candybar executor.** The domain is `gui/501`, not `user/501`:

```
launchctl kickstart -k gui/501/io.33god.hook-hub
launchctl kickstart -k gui/501/io.33god.candybar-executor
```

Check `curl -s 127.0.0.1:8685/health` (state running, the three error fields null) and `curl -s 127.0.0.1:8701/healthz`. The hub hot-reloads its overlay on file change; a kickstart also loads a new bloodbank checkout. The control plane is a container: `docker restart candybar`.

**Hindsight.** `docker restart hindsight-mac`. A request without the bearer must return 401 on `:8888/health`; that is the boundary, not a fault. Use the `hindsight` CLI on the Mac for anything authenticated; it reads its own `~/.hindsight/config` (0600). Re-render config with `env-op-resolve render`, never `hindsight configure`.

**pjangler registry.** `launchctl kickstart -k gui/501/io.33god.pjangler-registry`. Known: it crashes when its Postgres goes away (PJAN-213) and launchd KeepAlive brings it back, which leaves `last exit code 1`.

**Hermes gateway.** One gateway serves five profiles, so a kickstart (`launchctl kickstart -k gui/501/ai.hermes.gateway`) cuts every in-flight turn. Do it only when idle, once, after batching changes. Never `hermes update` and never `git pull` in the install. Move the pin only with `git checkout --detach <reviewed sha>`.

**Vinyl.** `brew services restart vinyl-server` and `vinyl-client`. Always use the full `delorenj/tap/...` formula names when installing.

## 4. The boot story

After a reboot today, Colima and its containers come back only once someone logs in, because Colima is a user LaunchAgent. The fix is built and waiting: a system LaunchDaemon `io.33god.colima`. Damian runs `sudo ~/33god-boot-daemon.sh --apply` once, types his Mac password, and the installer checks itself and rolls back on failure. The README is [mac/boot-daemon/README.md](mac/boot-daemon/README.md). `scripts/peer-check.sh` turns its `boot-daemon` row from WARN to PASS when it worked. The daemon is not installed yet and has never been tested at a real boot.

Three limits to know:

1. **FileVault is ON.** After a cold start or a power cut the Mac stops at the pre-boot password screen and no daemon runs, ours included. The daemon helps authenticated and logged-in restarts only. For a planned reboot, run `sudo fdesetup authrestart` instead of a menu restart or `shutdown -r`. Turning FileVault off would make power-loss recovery unattended; that is Damian's call and nothing here changes it. `pmset autorestart` is already 1 and sleep is 0.
2. **The native 33GOD agents still start at login.** `io.33god.hook-hub`, `io.33god.candybar-executor` and `io.33god.pjangler-registry` are `gui/501` agents. After an unattended reboot the containers and the bus come back, but hook capture, Candybar jobs and the registry wait for the next login. Moving them to the system domain is a separate change.
3. The 2026-11-14 recovery worked because someone unlocked the Mac five minutes after boot and auto-login did the rest.

## 5. Clocks: Candybar only

Candybar owns when anything recurring runs. No cron entry, no launchd `StartInterval` or `StartCalendarInterval`, no Hermes recurring job, no n8n Schedule Trigger, no private sleep loop. Registered jobs on the Mac (`candybar ls`, API `127.0.0.1:8700/candybars`):

| Job | Schedule | What it does |
|---|---|---|
| `mac-canary` | `5 * * * *` America/New_York | hourly side-effect-free proof the clock fires |
| `mac-hindsight-capture-sweep` | `*/10 * * * *` UTC | Hindsight session capture sweep only |
| `mac-dev-journal-nightly` | `0 6 * * *` America/New_York | the Dev Journal email, once a day |
| `mac-jev-rollup` | `*/10 * * * *` America/New_York | Jev rollup from the bus |
| `mac-skillex-hermes-resync` | `*/15 * * * *` UTC | skills resync, replaced the old launchd interval |

To add one: commit a manifest upstream, read the registration back from the API, prove a terminal run and its effect, then retire any competing clock. Candybar needs the Mac awake and logged in, and a 06:00 fire is only as reliable as that.

`candybar doctor --repo . --live --json` exits 1 on the Mac in the steady state. It lists Damian's own 13 native clocks (10 launchd interval jobs and 3 user-crontab ids). They are his services. No exception is written and nothing is disabled, so the findings stay visible on purpose. Only a finding owned by `io.33god.*` or `ai.hermes.*` is ours, and `peer-check` fails on those.

## 6. Secrets

- The interim store is `~/.config/33god/secrets.env`, mode 0600, outside any repo, never committed. Repos keep `.env.op` files holding `op://` refs only.
- `env-op-resolve` (in `~/.local/bin`) turns a ref into a store key (`op://Vault/Item/Field` becomes `OP_VAULT_ITEM_FIELD`), checks `~/.config/33god/refmap.tsv` against that rule, fails closed on a missing or duplicate ref, and never logs a value. Always run it from the launchd environment, not just a login shell.
- No DeLoSecrets service token lives on this Mac, now or later. Damian's own `cruise-control` 1Password token is scoped to his Machines vault and is his.
- **Never leave a `secrets.env` copy lying around.** Seven pre-change snapshots under `~/33god-migration/2026-11-10/backups/` are the one open FAIL in `peer-check` (section 8).
- **Interim to 1Password.** When Damian is ready: he creates his vault, imports the store values as items, and the resolver switches to `op run`. Caveat from W0-5: the `op://DeLoSecrets/...` refs in the repos cannot be presumed to resolve in his account. The cutover needs either items under identical refs in a vault he can read, or a permanent mapping in `refmap.tsv`. That table is the mapping of record. Do the cutover as one change, test in the launchd environment, then retire the store.

**Gateway token expiry.** Damian's AutomaticAI gateway tokens expire: `damien-personal` on 2027-01-26 and `damien-hindsight` on 2027-02-10 (id 113 and 129, `evidence/W6-4.md` F4). Rotating one on big-chungus does not reach the Mac. A rotation without a push is a silent outage: Hindsight retain and consolidation, and Damian's gateway lane, stop. After `gateway-tokens.py rotate`, run the re-push in `evidence/W6-4.md` Appendix B, then `docker restart hindsight-mac`. The token watch on big-chungus alerts 14 days ahead. The old token 68 `aai:damien` was revoked 2026-11-17.

## 7. Skills rule

Jarad's skills are private. Damian gets only the curated `skills.tar.gz` Jarad ships and scps to the Studio (60 skills, same set for every desk, Claude Code and Codex). Never clone or pull `delorenj/skills` or any private agents or skills repo onto the Mac, and never vendor private files into a public repo. A full re-clone was made once on 2026-11-15 and reverted the same night (`evidence/catalog-reclone-2026-11-15.md`). Skillex keys receipt ownership on volume UUID plus inode.

## 8. Deferred and open

**Deferred, not failed** (Jarad, 2026-11-17): W8-4 Plane to n8n to Bloodbank, W9-3 MinIO consumer, W10-1 ntfy, W10-2 artifact projector, W6-3 org and workforce (the CLI runs; no org exists, so `~/.hermes/org.yaml` is absent). Music Lab is out of scope.

**Owed by Damian:** voice typing allow (Microphone and Accessibility; W8-2), check the 6 am Dev Journal landed in Inbox not Spam, tell us his ChatGPT plan and approve one sign-in code, and run the boot installer once.

**Open findings:**

1. `peer-check` FAIL `secrets-strays`: seven install-introduced `secrets.env` copies under `~/33god-migration/2026-11-10/backups/` (all 0600 in a 0700 tree). Jarad's side: hash each key against the vault, then `rm -P` what the vault covers. Damian's own 0644 `~/.config/zshyzsh/mcp/secrets.env` is his.
2. PJAN-213: the registry crashes on an unhandled Postgres pool error. Filed, not implemented.
3. `mise trust` is missing for `~/code/33GOD/bloodbank`: hook handlers exit 1 for agent sessions whose cwd is that repo.
4. The `candystore` CLI is not installed (`~/.local/bin/candystore` absent), so the `candystore-context` briefing skips on every session start. `mise run cli:install` in candystore fixes it.
5. `dev-journal-reconcile` on big-chungus is red on 28 old-schema archive dates. Unrelated to the Mac.
6. The MacBook Pro voice-typing target is unmet: the Studio's `vinyl-server` binds loopback only.
7. W8-2 TCC is owed by Damian; it cannot be granted over ssh.
8. Smaller: the turn-enricher has no Docker healthcheck; Candystore cannot tell Codex Desktop from `codex-tui` (the originator is dropped; read the local rollout `session_meta` header); the root `~/.hermes/SOUL.md` is Hermes' stock text; a zero-byte `~/.hermes/.hermes-update-in-progress.lock` is left over; `~/.local/share/hindsight-studio-auth-tests-20261023` is old test residue.
9. Not verified: the boot daemon, a native-agent unattended reboot, a FileVault cold boot, Plane LAN discovery and upload, n8n workflows and credentials, and the pre-install baseline diff (no `target-baseline.out.md` exists).

## 9. Where to look

Per-task evidence is in [evidence/](evidence/). Compose overlays and env refs are in [mac/](mac/). The Damian-facing page is [dashboard/index.html](dashboard/index.html), served at https://damian.delo.sh. Aperture working rules are in `../CHARTER.md`: Rererere owns acceptance on this machine and no one else acts on it unless handed the session.

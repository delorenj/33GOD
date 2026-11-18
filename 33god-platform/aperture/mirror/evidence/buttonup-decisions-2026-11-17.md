# Buttonup lane D: Jarad's decisions executed on Damian's Mac (2026-11-17)

Executor: aai (lane D). Mac: `hellosubconscious@100.117.109.60`. Authority: Jarad's untagged decisions of 2026-11-17 (OpenSign = retire; delete old Hindsight Studio after one last pg_dump, the two proof banks, the hook-hub pending archives). No secret values printed; the Hindsight bearer was read from the rendered `~/.hindsight/config` by the CLI only. Other lanes' objects (turn-enricher, hook-hub overlay/kickstart, candybar gc, pjangler registry json, config-backups, flume) were not touched. Nothing here is git-committed (orchestrator commits).

## 1. OpenSign retired

| | Before | After |
|---|---|---|
| Colima containers named `damian-opensign-trial-*` | 5 Exited (proxy-1 Exited 128, server-1 Exited 1, client-1 Exited 1, mongo-1 Exited 0, mail-1 Exited 0), all 7 days old | 0 (`docker ps -a --filter name=opensign -q` is empty) |
| Colima volumes (`docker volume ls`) | 24 | 24, `diff` of before/after name lists is empty (kept: `damian-opensign-trial_database`, `damian-opensign-trial_files`, the two `w03-preserved-damian-opensign-trial_*`, and the two anonymous mongo volumes) |
| Colima total containers (all states) | 32 | 27 |

- `docker rm` without `-v` on each container by name. The first batched attempt by id errored on the shell side and removed nothing; the by-name retry removed all five (proxy-1 first, then server/client/mongo/mail).
- Docker Desktop volumes left as cold backup. Docker Desktop was NOT started: `pgrep` finds no Docker Desktop / com.docker.backend process; `~/Library/Group Containers/group.com.docker/settings-store.json` has `"AutoStart": false`; no Docker LaunchAgent in `~/Library/LaunchAgents` (only `sh.brew.colima.plist`).
- Context switch. Before (no `DOCKER_HOST`): `desktop-linux *` current, `docker ps` failed with `dial unix /Users/hellosubconscious/.docker/run/docker.sock: no such file or directory`; `~/.docker/config.json` `currentContext: desktop-linux`.
  `docker context use colima` -> `Current context is now "colima"`.
  After: `colima *` current, `currentContext: colima`, plain `docker ps` over ssh (no `DOCKER_HOST` set) lists 25 running containers; `docker volume ls` = 24. Interactive and non-interactive ssh now both work without the env var.
- Residue worth knowing: the `default` context entry still points at `/var/run/docker.sock` and `desktop-linux` still exists (harmless, left).

## 2. Old Hindsight Studio deleted (W7-4 follow-through)

Final logical backup. The existing W7-4 final dump (`hindsight_auth-20261112T172058Z.dump`, 12:20) did NOT strictly post-date the Studio's last write (data files stamped 12:21:29 by the clean shutdown, `pg_control`, `pg_wal`, `base/16384/17297`), so a fresh one was taken:
- Copied `~/.local/share/hindsight-studio/lifecycle-v3/data` (65 MB, `postmaster.pid` absent = clean stop, `lsof` 0 handles) to a temp dir; never ran PG on the original.
- Throwaway container `laneD-pg` on Colima, image `pgvector/pgvector:0.8.5-pg18@sha256:12a379b4...` (the digest `hindsight-mac-postgres` runs), `--network none`, data copied in with `docker cp`, `listen_addresses=''`, a `trust` line added only inside the copy. Superuser role in the Studio cluster is `hellosubconscious`, db `hindsight_auth` (the other db is `postgres`).
- `pg_dump -Fc -d hindsight_auth` plus `pg_dumpall --globals-only`. Archive header: created 2026-11-18 00:25:07 UTC, dumped from PG 18.4.
- Files (Mac, mode 0600, off the deleted trees): `~/33god-migration/2026-11-10/backups/w7/`
  - `hindsight-studio-final-2026-11-17.dump`, 120,861 B, sha256 `419bc57c898da07e995f89bf522858d8ba0dfdf65fc5471eefd6b16f9f902feb`
  - `hindsight-studio-final-2026-11-17.globals.sql`, 544 B, sha256 `14be9d62edb4dafddb8bce850910b88b1ba9dc8acf047d8420f3675842ff24dd`
  - `SHA256SUMS-hindsight-studio-final-2026-11-17`
- Sanity: `pg_restore --list` = 208 lines, 25 `TABLE DATA` entries; its non-comment TOC is identical to the 12:20 W7-4 dump's (so no schema or object drift after the cutover dump).
- Cleanup: container removed (`docker ps -a --filter name=laneD` = 0), temp copy dir `~/33god-migration/2026-11-10/laneD-tmp` removed, no volume created (volume list unchanged).

Deletion (before: `launchctl print gui/501/io.damian.hindsight-studio` = "Could not find service" i.e. not loaded; `print-disabled` = `=> disabled`; no process matching hindsight-studio; `lsof +D` on both trees = 0; only reference anywhere in LaunchAgents/`~/.config/33god`/`~/.hindsight` was the plist itself):
- Removed `~/Library/LaunchAgents/io.damian.hindsight-studio.plist`, `~/infra/hindsight-studio` (32 KB, scripts), `~/.local/share/hindsight-studio` (2.4 GB). All three `ls` -> No such file.
- Disable override: cleared with `launchctl enable gui/501/io.damian.hindsight-studio`; `print-disabled` now reads `=> enabled`. The label keeps a launchd database row (only root can rewrite the file in /var/db), but nothing exists to load, so it is inert.
- `~/code.backup` untouched (still present).
- Not in scope, left: `~/.local/share/hindsight-studio-auth-tests-20261023` (separate dir, Oct 23 test residue), a candidate for the next sweep.
- :8888 after: `GET /health` with bearer = 200 `{"status":"healthy","database":"connected",...}`, without bearer = 401 (same boundary as before), `hindsight-mac` and `hindsight-mac-postgres` both `Up 2 days (healthy)`, `general` bank stats readable (238 memory units, 11 documents).

## 3. Proof banks deleted on the live :8888 stack

`hindsight bank list` before: 7 (agent-aai-team, general, space, hello-subconscious-team-inbox, W74-TurnProof, agent-private-desk, studio-synthetic-proof).
Stats before delete: W74-TurnProof 6 memory units / 1 document (3 observation, 3 world); studio-synthetic-proof 1 unit / 1 document.
`hindsight bank delete -y` on each: W74-TurnProof "deleted successfully, items deleted 10"; studio-synthetic-proof "deleted successfully, items deleted 4".
After: 5 banks (agent-aai-team, general, space, hello-subconscious-team-inbox, agent-private-desk). No other bank touched. (studio-synthetic-proof also survives in the three W7 dumps, including the new final dump; W74-TurnProof existed only post-cutover and is gone by decision.)

## 4. hook-hub pending archives discarded (W2-3, decision: discard the ~14.6k pre-reset observations)

- Verified against `W2-3.verify.md` / `W2-3.md` before deleting:
  - `receipts-final.sqlite3` sha256 `1c39edd0d6894cf712e2effbd8ad1e639f2562e58134bde9c2db536e864d17e3` = the value in W2-3.verify.md. Match.
  - `receipts.sqlite3` (initial snapshot) sha256 `70a8321bb7136e06c29f833b1abab56f47e9cdc6935f698ed5b299fb5243cde5` = the value in W2-3.md line 153. Match.
- Deleted both, then `rmdir` of `~/33god-migration/2026-11-10/backups/w2/hook-hub-pending` (271 MB freed; directory gone).
- Stale `~/.local/state/33god/hook-hub/receipts.sqlite3`, `-shm`, `-wal`: deleted, because all conditions held:
  - `lsof` on all three (and on the live `w2-3-receipts.sqlite3`) returned nothing; hub PID 12001 holds no sqlite file open.
  - Live plist `io.33god.hook-hub` sets `HOOK_HUB_RECEIPTS=.../hook-hub/w2-3-receipts.sqlite3`, and `ps eww` on PID 12001 shows that same value in the process environment. The code default (`hub.py` line 73, `STATE_DIR/receipts.sqlite3`) only applies when the env var is missing, and the plist always sets it.
  - Overlay `hook-hub-overlay.toml` and the launcher script `start-hook-hub.sh` contain no receipts path. Only docs mention the old path (`bloodbank/services/hook-hub/README.md`, `skills/disk-space-maintenance/references/machines/big-chungus.md`).
  - The old DB held 14,600 invocations / 14,600 outbox rows, identical counts to the archive (immutable open); content was intentionally discarded.
- State dir 160 MB -> 16 MB. Left in place: `w2-3-receipts.sqlite3` (live), `hub.log`, `capture/`, `bank-exists.json`, launchd logs.
- Hub after: `GET 127.0.0.1:8685/health` -> `state running`, pid 12001, `registry_error/journal_error/transport_error` all null (the other lane's concurrent overlay/kickstart is theirs; I did not touch the service).

## Disk and state summary

Mac data volume 470 Gi free before and after (about 2.7 GB freed in files, below the df rounding). Colima: 25 running containers, 24 volumes, `docker` default context = colima.

## Follow-ups for the orchestrator

1. `PLAN.md` / dashboard rows for W7-4 ("decide when to delete the Studio"), W2-3 ("discard vs replay still open") and the OpenSign line can be closed from this file.
2. W7-4 section 9 rollback recipe (re-enable Studio) is now impossible by design; the only restore path is the new final dump above.
3. Docs still reference the retired hook-hub old receipts path (README, big-chungus.md); cosmetic.

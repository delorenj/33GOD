# Damian's Mac: freeze, hard reset, health check (2026-11-10)

## What happened
- About 17:30 EST the Mac stopped answering on the tailnet. Tailscale ping got no reply, the relay showed `rx 0`, and ssh :22 timed out. The control plane still listed it as online, which fits a machine that is powered on but frozen.
- It was hard-reset at **19:27:59 EST**. The reset report (`ResetCounter-2026-11-10-193049.diag`) records boot faults `rst btn_rst,btn_seq_reset btn_shdn target_off_restart`, which is a power-button reset.
- There is no panic report. Memory after boot: 93% free, no swap. Disk: 480 GiB free. The cause of the freeze is unknown.
- The last 33GOD activity before the freeze was the W4-2 fix pass's read-only snapshot (`/tmp/w42fix/snap.sh`: hashes, git status, docker ps, ps, two local GETs).
- Other diagnostic reports from that day: a Virtualization.VirtualMachine `disk writes` resource report at 13:59 (the Colima VM), a Python diag at 16:22, and a Codex (Service) diag at 19:32 after boot.

## Survived the reboot unaided (the first data point for the deferred reboot proof)
| Component | Result |
|---|---|
| Colima (gui/501 brew service) and every stack on it | came back: Plane (all containers), n8n-foundation (healthy), pjangler-registry-postgres (healthy), studio-onepassword-redis (healthy), 33god-bus (nats healthy with BLOODBANK_EVENTS, BLOODBANK_COMMANDS and GIB_EVENTS intact; dapr-placement up), 33god-store (candystore, its Postgres and daprd healthy; `/healthz` 204). There are 22 colima volumes. |
| io.33god.hook-hub (gui/501) | running, publishing; health 200 with 0 pending; events flowing to candystore |
| io.33god.pjangler-registry | running, health 200; it exited 1 once at boot, probably before its Postgres was up, and KeepAlive restarted it |
| local.plane.bonjour, ai.hermes.gateway (user/501), team-dashboard, Sunshine | running |
| Docker Desktop (autostart off) and OpenSign (no restart policy) | did **not** return, as expected. The orchestrator ran `open -a Docker` and then `docker start` on the 5 `damian-opensign-trial-*` containers. All 5 are up, :8791 returns 200, and desktop-linux still has 30 volumes. |
| io.damian.hindsight-studio | did **not** return. It crash-looped (runs 16, exit 1) with `RuntimeError('occupied_pg')`, because the reset left a stale `data/postmaster.pid` (PID 33543, dead) and a stale socket `s/.s.PGSQL.63145`. By design the supervisor never unlinks stale state. The orchestrator confirmed no postgres was running, backed up both files to `~/33god-migration/2026-11-10/backups/post-crash/` and removed them. Postgres crash recovery was clean (redo done, end-of-recovery checkpoint). The supervisor emitted `ready`, and :8888 returns 401 (the bearer gate, as before). |
| team-inbox Hermes gateway (gui/501) | came back **without its state**, as predicted in W1-3. 11 profile links dangled and it had created a new empty `state.db` (0 sessions). The orchestrator booted it out, moved the new `state.db*` aside to `runtime/.pre-restore-20261110T193823/` and copied the real runtime from `~/code.backup/.../runtime` (read-only source; `.gitattributes`, `.gitignore` and README skipped; existing dirs merged without overwriting). It then made the copy writable and bootstrapped the gateway. All links now resolve except `kanban.db`, which is also absent in the backup. `state.db` passes integrity_check and has 9 sessions. :8642 returns 200 and Telegram reconnected. |
| io.33god.skillex-hermes-resync | not running, exit 1: the known W1-3 catalog blocker |
| ai.openclaw.gateway (Damian's) | exit 78 (EX_CONFIG). This is Damian's service and was not touched; W1-4 had already filed missing paths for it. |

## Still to note
- The machine's power settings are already `sleep 0` (caffeinate, ChatGPT and powerd hold assertions), `womp 1` and `autorestart 1`. The freeze was not sleep.
- Colima starts only at GUI login. The Mac came back because someone logged in at the console (19:30).

Rollbacks:
- team-inbox: bootout the label, restore `.pre-restore-*/state.db*`, remove the copied dirs, bootstrap.
- Hindsight: the stale pid and socket files are in the backup dir. Do not restore them while postgres runs.

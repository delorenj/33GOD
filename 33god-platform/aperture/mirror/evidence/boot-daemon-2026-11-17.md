# Boot-time Colima for a 33GOD Mac peer (Lane E), 2026-11-17

Level: fix boot-time Colima for Damian's Mac Studio; build it for any 33GOD Mac peer
(`belsky-doctrine`). Damian is the first user; the next peer runs the same `install.sh` with no edits.

Nothing was applied: no sudo on the Mac. All work below is probes, a dry run, and one throwaway test profile.

## What exists

- `mac/boot-daemon/install.sh` (bash 3.2 safe, shellcheck-clean, `--dry-run` default, `--apply`, `--uninstall`)
- `mac/boot-daemon/README.md` (what/why, affected native agents, research with sources, verify steps)
- On the Mac: `~/33god-boot-daemon.sh` (755, sha256 `0f2cd7c3e574d83966907da01afa0666fef3d76f3cf7691dd524366e92f250d9`,
  identical to the repo copy) and `~/33god-migration/boot-daemon/install.sh`, plus `dryrun-final.txt` there.

Damian runs: `sudo ~/33god-boot-daemon.sh --apply`

## Mac facts (read over ssh)

| Item | Value |
|---|---|
| macOS / arch | 26.3 (25D125), arm64 |
| colima / lima | 0.10.3 / 2.3.0 (`colima start --foreground` supported; `colima autostart` does not exist) |
| profile | `default`: vz, virtiofs, rosetta, 12 CPU / 32 GiB / 200 GiB, `autoActivate: false`, `sshConfig: false`, network shared, `address: false` |
| limactl entitlements | `com.apple.security.virtualization`, `network.client`, `network.server` all true |
| current supervisor | `gui/501/homebrew.mxcl.colima`, `~/Library/LaunchAgents/sh.brew.colima.plist`, args `start --foreground --activate=false --ssh-config=false`, KeepAlive `SuccessfulExit=true`, pid 1371, runs=1 |
| docker socket | `~/.colima/default/docker.sock`, `srw-------` owned by hellosubconscious |
| pmset | autorestart 1, sleep 0 (prevented) |
| FileVault | **On**, no `autoLoginUser` set |
| /Library/LaunchDaemons | only `com.docker.socket.plist`, `com.docker.vmnetd.plist` (Docker Desktop) |
| running containers | 25 (list in the dry run below) |
| restart policies | all `always` or `unless-stopped` except one-shots `bloodbank-nats-init` (`no`) and `plane-app-migrator-1` (`on-failure`) |
| TCC-protected bind mounts | none (`docker inspect` of every running container: no source under Documents/Desktop/Downloads/etc.) |
| native io.33god agents | `hook-hub`, `candybar-executor`, `pjangler-registry`: all `gui/501`, RunAtLoad+KeepAlive |

## Surprise worth knowing

FileVault is on. After a cold boot or power loss the Mac stops at the pre-boot password screen and no
LaunchDaemon runs, so this change fixes authenticated restarts and logged-in restarts, not an unattended
power-loss boot. The 2026-11-14 recovery happened because someone unlocked it 5 minutes after boot.
`sudo fdesetup authrestart` is the planned-reboot path. Turning FileVault off is Damian's decision; the
installer leaves it alone and warns. Details in the README (Caveat 1).

## Research (sources)

- Lima docs, Automatic Startup: https://lima-vm.io/docs/usage/autostart/ (Lima >= 2.2 `limactl autostart enable --condition=boot`, `--user`, system LaunchDaemon `io.lima-vm.daemon.<instance>.plist`, KeepAlive default true)
- https://github.com/lima-vm/lima/issues/4983 (why: LaunchAgent needs a GUI session)
- https://github.com/lima-vm/lima/issues/5087 and PR https://github.com/lima-vm/lima/pull/5088 (orphaned vz driver after unclean shutdown, fixed 2026-09-30 for 2.3.0; also the open `posix_spawn ... error 0xd` report on an Intel mini whose cause was never found)
- https://github.com/lima-vm/lima/pull/5489 (Colima's `~/.colima/_lima` LIMA_HOME; reports a no-GUI reboot where containers came back)
- https://github.com/abiosoft/colima/pull/1636 (`colima autostart --boot`; runs `limactl start`, skips colima provisioning)
- https://github.com/abiosoft/colima/issues/1490 (bare `KeepAlive=true` around `start --foreground` leaks limactl processes)
- https://github.com/jordanthomas761/bootstrap-device/issues/52 (FileVault: nothing starts until unlocked; `fdesetup authrestart`)
- https://github.com/ExaDev/github-runner/pull/175 (another `colima start` daemon with UserName; says only a real boot proves it)

Conclusion: vz does not need a GUI session; a system LaunchDaemon with `UserName` is the supported shape
(Lima ships it). Design choice here: keep `colima start --foreground` (matches the brief and keeps colima's own
setup) behind a small root-owned runner, rather than `limactl autostart`.

## Tests run without root

| Test | Result |
|---|---|
| `shellcheck -s bash -S style install.sh` (local, v0.11.0) and the embedded runner | clean |
| `bash -n`, and `/bin/bash` 3.2.57 on the Mac | runs |
| `--dry-run` on the Mac as hellosubconscious (under 3.2) | rc 0, full output below |
| `plutil -lint` on the rendered plist (default and non-default profile `g33boot-test`) | OK |
| `--apply` as non-root | refuses, rc 1 |
| `--uninstall --dry-run`, `--help`, bad arg | as designed (rc 0/0/64) |
| Runner guard logic with a fake colima (local) | 6 starts then "giving up", exit 0; already-running branch stops then starts |
| **Live runner test on the Mac**: throwaway profile `g33boot-test` (1 CPU/1 GiB) started by the runner under a temporary LaunchAgent with the rendered environment | foreground start worked in ~15 s, docker socket forwarded, `docker info` answered (1 CPU, 1 GiB); `launchctl bootout` (SIGTERM) stopped it cleanly in ~2 s with no leftover `g33boot-test` processes; profile, disks, agent and test dir then deleted. The default profile stayed at 25 running containers throughout. |

Not testable without sudo: the system-domain bootstrap with `UserName`, and an actual boot. The installer's
verification step covers the first at apply time (and rolls back on failure); the second needs one
authenticated restart (README, "Verify after a reboot").

## Final dry-run output (Mac, as hellosubconscious, `/bin/bash ~/33god-boot-daemon.sh --dry-run`)

```

== Preflight (target: hellosubconscious uid=501 home=/Users/hellosubconscious profile=default label=io.33god.colima)
   mode: install, DRY RUN, nothing is changed
   colima version 0.10.3; limactl version 2.3.0
   colima supports 'start --foreground'
   profile config: /Users/hellosubconscious/.colima/default/colima.yaml (vmType=vz)
   limactl carries the com.apple.security.virtualization entitlement (/opt/homebrew/Cellar/lima/2.3.0/bin/limactl)
   FileVault: FileVault is On.
   WARN: FileVault is ON: the daemon starts only after the disk is unlocked (authenticated restart or software-update restart: yes; cold power-loss boot: no, it stops at the pre-boot password screen). See README.
   pmset autorestart: 1

== Rendered /Library/LaunchDaemons/io.33god.colima.plist
   plutil -lint: OK
     <?xml version="1.0" encoding="UTF-8"?>
     <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
     <plist version="1.0">
     <dict>
     	<key>Label</key>
     	<string>io.33god.colima</string>
     	<key>UserName</key>
     	<string>hellosubconscious</string>
     	<key>GroupName</key>
     	<string>staff</string>
     	<key>ProgramArguments</key>
     	<array>
     		<string>/bin/bash</string>
     		<string>/Library/Application Support/33god/boot-daemon/colima-run.sh</string>
     	</array>
     	<key>RunAtLoad</key>
     	<true/>
     	<key>KeepAlive</key>
     	<dict>
     		<key>SuccessfulExit</key>
     		<false/>
     	</dict>
     	<key>ThrottleInterval</key>
     	<integer>30</integer>
     	<key>ExitTimeOut</key>
     	<integer>120</integer>
     	<key>WorkingDirectory</key>
     	<string>/Users/hellosubconscious</string>
     	<key>EnvironmentVariables</key>
     	<dict>
     		<key>HOME</key>
     		<string>/Users/hellosubconscious</string>
     		<key>USER</key>
     		<string>hellosubconscious</string>
     		<key>LOGNAME</key>
     		<string>hellosubconscious</string>
     		<key>PATH</key>
     		<string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
     		<key>COLIMA_HOME</key>
     		<string>/Users/hellosubconscious/.colima</string>
     		<key>G33_COLIMA_PROFILE</key>
     		<string>default</string>
     		<key>G33_COLIMA_FLAGS</key>
     		<string>--activate=false --ssh-config=false</string>
     		<key>G33_COLIMA_LABEL</key>
     		<string>io.33god.colima</string>
     		<key>G33_COLIMA_LOGDIR</key>
     		<string>/Library/Logs/33god</string>
     	</dict>
     	<key>StandardOutPath</key>
     	<string>/Library/Logs/33god/colima-default.log</string>
     	<key>StandardErrorPath</key>
     	<string>/Library/Logs/33god/colima-default.log</string>
     </dict>
     </plist>

== Runner script /Library/Application Support/33god/boot-daemon/colima-run.sh
     #!/bin/bash
     # colima-run.sh - supervised foreground start of a colima profile, run by
     # launchd (system domain, UserName=<peer user>). Installed by 33god boot-daemon.
     # - clears an orphaned VM left by an unclean shutdown (lima#5087)
     # - caps restart storms: 6 starts in 10 minutes -> exit 0 and stay down
     #   (colima#1490: a bare KeepAlive loop leaked thousands of limactl processes)
     # - exec's colima so launchd's SIGTERM reaches it directly
     set -u
     profile="${G33_COLIMA_PROFILE:-default}"
     flags="${G33_COLIMA_FLAGS---activate=false --ssh-config=false}"
     label="${G33_COLIMA_LABEL:-io.33god.colima}"
     logdir="${G33_COLIMA_LOGDIR:-$HOME/Library/Logs}"
     log() { printf '%s colima-run[%s]: %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$$" "$*"; }
     
     colima="$(command -v colima)" || { log "colima not found on PATH=$PATH"; exit 78; }
     
     guard="$logdir/colima-$profile.starts"
     now="$(date +%s)"
     recent=0
     if [ -f "$guard" ]; then
       while read -r t; do
         case "$t" in ''|*[!0-9]*) continue ;; esac
         [ $((now - t)) -lt 600 ] && recent=$((recent + 1))
       done < "$guard"
     fi
     if [ "$recent" -ge 6 ]; then
       log "$recent starts in the last 10 minutes; giving up (exit 0 keeps launchd from relaunching)."
       log "fix the cause, then: rm '$guard' && sudo launchctl kickstart -k system/$label"
       exit 0
     fi
     echo "$now" >> "$guard"
     tail -n 20 "$guard" > "$guard.tmp" 2>/dev/null && mv "$guard.tmp" "$guard"
     
     if "$colima" status --profile "$profile" >/dev/null 2>&1; then
       log "profile '$profile' already running at launch (not ours); stopping it so launchd can supervise"
       "$colima" stop --profile "$profile" || "$colima" stop --force --profile "$profile" || true
     fi
     # A half-dead instance reports as not running but leaves a driver behind.
     "$colima" stop --force --profile "$profile" >/dev/null 2>&1 || true
     
     log "starting: colima start --profile $profile --foreground $flags (as $(id -un), HOME=$HOME)"
     # shellcheck disable=SC2086
     exec "$colima" start --profile "$profile" --foreground $flags

== 1/6 Capture the running container set (the post-switch acceptance list)
   25 running containers: bloodbank-turn-enricher hindsight-mac hindsight-mac-postgres candybar candybar-postgres candystore-daprd candystore candystore-postgres bloodbank-dapr-placement bloodbank-nats plane-app-proxy-1 plane-app-live-1 plane-app-space-1 plane-app-admin-1 plane-app-web-1 plane-app-beat-worker-1 plane-app-worker-1 plane-app-api-1 plane-app-plane-db-1 plane-app-plane-mq-1 plane-app-plane-minio-1 plane-app-plane-redis-1 n8n-foundation-n8n-1 pjangler-registry-postgres-1 studio-onepassword-redis-1
   + install -d -m 755 -o root -g wheel /Library/Application Support/33god/boot-daemon
   + write list to /Library/Application Support/33god/boot-daemon/io.33god.colima.expected

== 2/6 Retire the user-level brew colima agent (gui/501/homebrew.mxcl.colima)
   loaded in gui/501: booting it out (brief outage; containers restart with the new daemon)
   + launchctl bootout gui/501/homebrew.mxcl.colima
   moving /Users/hellosubconscious/Library/LaunchAgents/sh.brew.colima.plist out of LaunchAgents so a login cannot start a second instance
   + install -d -m 700 -o root -g wheel /Library/Application Support/33god/boot-daemon/saved-agents
   + mv /Users/hellosubconscious/Library/LaunchAgents/sh.brew.colima.plist /Library/Application Support/33god/boot-daemon/saved-agents/sh.brew.colima.plist

== 3/6 Install runner, log dir, plist
   + install -d -m 755 -o hellosubconscious -g staff /Library/Logs/33god
   + install -m 755 -o root -g wheel <runner> /Library/Application Support/33god/boot-daemon/colima-run.sh
   + install -m 644 -o root -g wheel <plist> /Library/LaunchDaemons/io.33god.colima.plist

== 4/6 Load the daemon (system domain)
   + launchctl bootstrap system /Library/LaunchDaemons/io.33god.colima.plist
   + launchctl enable system/io.33god.colima

== 5/6 Verify docker socket and containers
   would wait for /Users/hellosubconscious/.colima/default/docker.sock, then require: the container set captured in step 1

== 6/6 (dry run) Done: nothing changed. Re-run with --apply.
```

# boot-daemon: Colima at boot for a 33GOD Mac peer

One installer, any 33GOD Mac peer. Damian's Mac Studio is the first user.

```
sudo ./install.sh              # dry run (default): probes, renders, prints every command
sudo ./install.sh --apply      # do it
sudo ./install.sh --uninstall  # revert to the brew service
```

On Damian's Mac the copy lives at `~/33god-boot-daemon.sh`:

```
sudo ~/33god-boot-daemon.sh --apply
```

## Why

On a peer Mac, Colima runs as a per-user brew service: `~/Library/LaunchAgents/sh.brew.colima.plist`,
label `homebrew.mxcl.colima`, in the `gui/<uid>` launchd domain. A LaunchAgent exists only
while that user has a GUI session. After a reboot nobody has one until someone logs in, so
Colima never starts, and every container with a restart policy stays down with it:
Plane, Candystore, the Candybar control plane, Hindsight, NATS, n8n, the pjangler Postgres,
the turn-enricher. `pmset autorestart` is already 1 on the Mac, so a power-loss reboot
happens, then nothing recovers until login.

The installer replaces that agent with a system LaunchDaemon, `/Library/LaunchDaemons/io.33god.colima.plist`
(`io.33god.colima.<profile>` for a non-default profile), that runs the same Colima profile as the
same user from boot. Colima is the only thing it moves. The Colima profile, its disk, its
containers and the docker socket path (`~/.colima/<profile>/docker.sock`) stay exactly where they are.

## What `--apply` does

1. Preflight, as the target user: colima supports `start --foreground` (capability check, not a
   version compare), every flag it will pass exists, `limactl` carries the
   `com.apple.security.virtualization` entitlement when the profile is `vz`, the profile config exists,
   plus FileVault and `pmset autorestart` status.
2. Records the running container names (the acceptance list for step 5).
3. Retires the user agent: `launchctl bootout gui/<uid>/homebrew.mxcl.colima`, forces a stop if a
   VM is left over, and moves the plist out of `~/Library/LaunchAgents` into
   `/Library/Application Support/33god/boot-daemon/saved-agents/` so a login cannot start a second instance.
4. Installs a root-owned runner and the plist, `plutil -lint`s it, then
   `launchctl bootstrap system` and `enable`.
5. Waits (default 300 s) for the docker socket, then for every container from step 2 to be running.
   Prints `docker ps` as the user and the daemon's launchd state.
6. If verification fails, it rolls back to the brew service on its own (`--keep-on-fail` disables
   that) and tells you where the log is.

The default is a dry run: it runs the read-only probes and prints every command it would run.
`--uninstall` boots the daemon out, deletes its plist and runner, puts the saved agent plist back
and re-bootstraps it (or runs `brew services start colima` if no plist was saved).

Expect a short outage on `--apply`: the VM stops and starts again under the new owner, and the
containers restart with it (not yet timed on the Mac Studio; `--apply` prints how long the socket and containers took).

### The rendered plist

`UserName=<user>`, `GroupName=<primary group>`, `RunAtLoad`, `KeepAlive {SuccessfulExit=false}`,
`ThrottleInterval 30`, `ExitTimeOut 120`, `WorkingDirectory=$HOME`, explicit `HOME USER LOGNAME PATH
COLIMA_HOME` (`PATH` starts with `/opt/homebrew/bin`), stdout and stderr to
`/Library/Logs/33god/colima-<profile>.log` (owned by the user). The program is
`/bin/bash "/Library/Application Support/33god/boot-daemon/colima-run.sh"`, which `exec`s
`colima start --profile <p> --foreground --activate=false --ssh-config=false`.
Those two flags are what the brew agent already passes on the Mac.

Why a wrapper and not `colima start` directly:

- It clears an orphaned VM before starting, so a crash or a SIGKILL cannot wedge the next start
  ([lima#5087](https://github.com/lima-vm/lima/issues/5087)).
- It caps restart storms: 6 starts in 10 minutes and it logs why and exits 0, which
  `SuccessfulExit=false` treats as "leave it down". A bare `KeepAlive=true` around
  `colima start --foreground` once leaked thousands of `limactl usernet` processes
  ([colima#1490](https://github.com/abiosoft/colima/issues/1490)).
- `exec` means launchd's SIGTERM goes straight to colima, which shuts the VM down gracefully (measured on
  the Mac: 2 s for an idle test VM).
- A deliberate `colima stop` exits 0 and stays stopped. A crash restarts.

### Options

`--user`, `--profile`, `--flags`, `--brew-label`, `--log-dir`, `--expect a,b,c`, `--timeout`,
`--keep-on-fail`, `--emit DIR` (write the plist and runner to DIR for review). Nothing is hardcoded to
Damian: the user defaults to `$SUDO_USER`, home comes from `dscl`, the group from `id -gn`.
Written for macOS `/bin/bash` 3.2 and shellchecked clean.

## Caveat 1: FileVault. A cold boot still stops at the unlock screen

The Mac Studio has FileVault on and no `autoLoginUser`. With FileVault on, the Data volume is locked
until someone types the password at the pre-boot screen. No LaunchDaemon runs before that, ours
included. The 2026-11-14 reboot recovered because someone unlocked it at 20:28, five minutes after boot
(`evidence/W0-3-reboot-2026-11-14.md`).

What the daemon does buy:

| Reboot kind | After this change |
|---|---|
| Authenticated restart: `sudo fdesetup authrestart`, or a macOS software-update restart | Disk is unlocked for the boot. Colima and every container come up with nobody logged in. |
| Restart from a logged-in session | Same as today, but Colima is up before the login window. |
| Power loss or cold boot | Stops at the pre-boot password screen. Nothing runs until someone unlocks. The daemon cannot change that. |

For planned reboots, use `sudo fdesetup authrestart` instead of `shutdown -r` or a menu restart.
Turning FileVault off is what makes a power-loss recovery fully unattended. That is Damian's call, and
the installer does not touch it. Whether daemons really run after an authenticated restart with nobody
logged in is not yet measured on this Mac (see Verify).

## Caveat 2: native 33GOD LaunchAgents still start only at login

Read from `launchctl list` and `~/Library/LaunchAgents` over ssh on 2026-11-17. These are `gui/501`
agents (`RunAtLoad`, `KeepAlive`). They need a GUI session, so after an unattended reboot they stay down
even though their containers are back:

| Agent | Talks to |
|---|---|
| `io.33god.hook-hub` | NATS (`bloodbank-nats`) |
| `io.33god.candybar-executor` | the Candybar control plane |
| `io.33god.pjangler-registry` | `pjangler-registry-postgres-1` |

So the containers and the bus are back at boot, but hook capture, scheduled Candybar jobs and the
pjangler registry resume only at the next login. Moving them to the system domain is a separate change
(each reads files, mise shims and 1Password-resolved env under the user's home, so each needs its own
check). This installer does not touch them. Damian's other agents are in the same position:
`sh.delo.vinyl.server`, `sh.delo.vinyl.client`, `sh.delo.heyma`, `ai.hermes.gateway*`, and the other
`ai.openclaw.*` / `com.openclaw.*` / `com.hellosubconscious.*` agents.

## Research: does Lima/Colima `vz` run from a system LaunchDaemon with `UserName`?

Short answer: yes, and Lima now supports it natively. Findings, with sources:

- **Virtualization.framework does not need a GUI session.** Colima already runs headless over ssh on
  this Mac. The blocker for boot start was the LaunchAgent, not `vz`: an agent needs an active user session, so
  with no login the VM never started ([lima#4983](https://github.com/lima-vm/lima/issues/4983)).
- **Lima >= 2.2 ships boot autostart.** `limactl autostart enable --condition=boot <instance>` installs
  `/Library/LaunchDaemons/io.lima-vm.daemon.<instance>.plist` with `UserName` so the host agent runs
  as the user, not root; `--keep-alive` defaults to true
  ([Lima docs: Automatic Startup](https://lima-vm.io/docs/usage/autostart/)). The Mac has Lima 2.3.0, so
  it could be used. We run `colima start --foreground` instead, because `limactl start` skips colima's
  own provisioning and socket setup (colima PR
  [#1636](https://github.com/abiosoft/colima/pull/1636) notes this), and colima 0.10.3 has no
  `colima autostart` command (checked: `unknown command "autostart"`).
- **Colima's lima home is not `~/.lima`.** It is `~/.colima/_lima`. Lima's generated units used to miss that
  ([lima PR #5489](https://github.com/lima-vm/lima/pull/5489), which reports a no-GUI, no-docker-client
  test where the VM booted and the containers came back). We set `COLIMA_HOME` explicitly and
  colima derives the rest. The Mac uses `~/.colima`, not the XDG path.
- **Unclean shutdown can orphan the vz driver.** After SIGKILL, a launchd timeout or power loss, a daemon
  can find "vz driver is running but host agent is not" and crash-loop; the manual fix is
  `limactl stop --force` ([lima#5087](https://github.com/lima-vm/lima/issues/5087), fixed by
  [PR #5088](https://github.com/lima-vm/lima/pull/5088), merged 2026-09-30 on the v2.3.0 milestone; the Mac
  runs 2.3.0). Our runner also does `colima stop --force` first, as belt and braces. The plist's
  `ExitTimeOut 120` gives the VM time to stop gracefully before launchd's SIGKILL (the brew plist has the
  20 s default).
- **Restart loops leak processes.** Bare `KeepAlive=true` around `colima start --foreground` leaked
  thousands of `limactl` processes when start kept failing
  ([colima#1490](https://github.com/abiosoft/colima/issues/1490)); Homebrew's plist avoids it with a
  `SuccessfulExit` dict. We use the dict plus the 6-in-10-minutes cap in the runner.
- **`vz` needs the entitlement on `limactl`.** Checked on the Mac:
  `codesign -d --entitlements - $(readlink -f $(which limactl))` shows
  `com.apple.security.virtualization = true` (and network client/server). The installer re-checks it.
- **An open spawn failure exists, root cause never found.** In lima PR #5088 a hand-written daemon
  plist with `UserName` failed after a real reboot on an Intel Mac mini with
  `posix_spawn(.../limactl), error 0xd - Permission denied` (exit 78). The same binary ran fine by hand as
  that user. Lima's own generated plist was not what failed. Our installer starts the daemon in the system domain
  with that `UserName` before it declares success, so a spawn denial shows up at install time, with
  an automatic rollback. A pre-login reboot is the only test of the early-boot case.
- **FileVault** (see Caveat 1): [bootstrap-device#52](https://github.com/jordanthomas761/bootstrap-device/issues/52)
  reached the same conclusion: "if FileVault is on, nothing starts after reboot until unlocked", with
  `fdesetup authrestart` for planned restarts. Whether daemons then run with nobody logged in was untested there too.
- **Other pitfalls we checked.**
  - Socket ownership: the docker socket stays `~/.colima/<profile>/docker.sock`, mode 0600, owned by the
    user, so only that user's docker clients reach it.
  - ssh-agent: not needed (no ssh to external hosts); `--ssh-config=false` keeps `~/.ssh/config` untouched.
  - Docker credential helper: pulls that need the login keychain fail in a daemon. Running containers do not.
  - TCC: a daemon-owned vz process may be refused `~/Documents`, `~/Desktop`, `~/Downloads`. The Mac
    shares all of `$HOME` into the VM; no running container bind-mounts from those (checked with
    `docker inspect`).
  - Bridged or reachable-address networking uses `socket_vmnet`, which needs a sudoers entry a daemon
    cannot prompt for. The Mac profile is `network.address: false`, mode `shared`. The installer warns if a profile is not.
  - Docker Desktop's `/usr/local/bin/docker` is on the PATH; the daemon PATH includes `/usr/local/bin`.
  - macOS 13+ shows a "Background items added" notice for a new LaunchDaemon, and it can be toggled off in
    System Settings > General > Login Items & Extensions. If someone toggles it off, boot start stops.

## Verify after a reboot, without logging in

Use `sudo fdesetup authrestart` from an ssh session for the test (it unlocks the disk for exactly one
boot), then from another machine, never touching the GUI:

```
ssh hellosubconscious@<mac> 'sudo launchctl print system/io.33god.colima | egrep "state|pid|username|last exit"'
ssh hellosubconscious@<mac> 'DOCKER_HOST=unix://$HOME/.colima/default/docker.sock /usr/local/bin/docker ps --format "{{.Names}}\t{{.Status}}"'
ssh hellosubconscious@<mac> 'tail -20 /Library/Logs/33god/colima-default.log'
ssh hellosubconscious@<mac> 'who; launchctl list | grep io.33god'   # nobody on console; the 3 native agents are NOT listed yet
```

Pass: `state = running`, a pid, the docker socket answers, all the containers in step 2's list
(also in `/Library/Application Support/33god/boot-daemon/io.33god.colima.expected`) are `Up`, and
`who` shows no console user. Plane should answer on `http://<mac>/` (container-only), while
`http://<mac>:8764/health` (the pjangler registry, a native agent) will not until login (Caveat 2).

If Colima gave up (6 starts in 10 minutes): read the log, fix the cause, then
`rm /Library/Logs/33god/colima-default.starts` and
`sudo launchctl kickstart -k system/io.33god.colima`.

## Gotchas for later

- Never run `brew services start colima` while the daemon is installed: it recreates the user agent and
  you get two supervisors fighting over one profile. `brew upgrade colima` is fine, the runner finds the
  new binary through `PATH`.
- After editing the plist by hand: `sudo launchctl bootout system/io.33god.colima` and `bootstrap` again.
  `kickstart -k` does not re-read it.
- Logs are not rotated. Colima's foreground output is small; trim `/Library/Logs/33god` when you remember.

## Files

| File | Purpose |
|---|---|
| `install.sh` | the installer (`--dry-run` default, `--apply`, `--uninstall`) |
| `README.md` | this file |

Evidence for the first run: `../../evidence/boot-daemon-2026-11-17.md`.

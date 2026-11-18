#!/bin/bash
# install.sh - boot-time Colima for a 33GOD Mac peer (system LaunchDaemon).
#
# Problem: Colima on a peer Mac is a per-user brew service (a LaunchAgent in
# gui/<uid>), so after a reboot nothing that runs in containers (Plane,
# Candystore, Candybar control plane, Hindsight, NATS) comes back until someone
# logs in at the GUI. This installs /Library/LaunchDaemons/io.33god.colima.plist
# so the same Colima profile starts at boot as the peer's user.
#
# Run it with sudo, as the Mac's owner, from the peer's own account:
#   sudo ./install.sh              dry run (default): probes + prints everything
#   sudo ./install.sh --apply      do it
#   sudo ./install.sh --uninstall  revert to the brew service
# The dry run needs no root when run as the target user (it just probes).
#
# macOS /bin/bash is 3.2: no associative arrays, no mapfile, no ${x,,}.

set -u
set -o pipefail

# ------------------------------------------------------------------ defaults
OPT_USER=""
PROFILE="default"
START_FLAGS="--activate=false --ssh-config=false"
LOG_DIR="/Library/Logs/33god"
TIMEOUT=300
EXPECT=""
BREW_LABEL="homebrew.mxcl.colima"
KEEP_ON_FAIL=0
EMIT_DIR=""
ACTION="install"
APPLY=0
FORCE_DRY=0
DAEMON_PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
SUPPORT_DIR="/Library/Application Support/33god/boot-daemon"
LAUNCHD_DIR="/Library/LaunchDaemons"

usage() {
  cat <<'EOF'
Usage: install.sh [--dry-run | --apply | --uninstall] [options]

Modes (dry run is the default and changes nothing):
  --dry-run          probe, render the plist, print every command
  --apply            stop the user-level brew colima agent, install and load
                     the boot-time LaunchDaemon, verify docker + containers
  --uninstall        remove the daemon, restore the brew colima agent
                     (--uninstall --dry-run only prints)

Options:
  --user NAME        macOS account the daemon runs as (default: $SUDO_USER)
  --profile NAME     colima profile (default: default); label becomes
                     io.33god.colima, or io.33god.colima.NAME for non-default
  --flags "..."      flags for 'colima start' (default: --activate=false --ssh-config=false)
  --brew-label L     user-level launchd label to retire (default: homebrew.mxcl.colima)
  --log-dir DIR      log directory (default: /Library/Logs/33god)
  --expect a,b,c     container names that must be running afterwards
                     (default: the running set captured before the switch)
  --timeout SECS     wait budget for socket + containers (default: 300)
  --keep-on-fail     do not auto-roll-back to the brew service if verification fails
  --emit DIR         also write the rendered plist and runner into DIR (for review/tests;
                     touches nothing else)
  -h, --help         this text
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) FORCE_DRY=1 ;;
    --apply) ACTION="install"; APPLY=1 ;;
    --uninstall) ACTION="uninstall"; APPLY=1 ;;
    --user) OPT_USER="${2:-}"; shift ;;
    --profile) PROFILE="${2:-}"; shift ;;
    --flags) START_FLAGS="${2-}"; shift ;;
    --brew-label) BREW_LABEL="${2:-}"; shift ;;
    --log-dir) LOG_DIR="${2:-}"; shift ;;
    --expect) EXPECT="${2:-}"; shift ;;
    --timeout) TIMEOUT="${2:-}"; shift ;;
    --keep-on-fail) KEEP_ON_FAIL=1 ;;
    --emit) EMIT_DIR="${2:-}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 64 ;;
  esac
  shift
done
[ "$FORCE_DRY" = 1 ] && APPLY=0

# ------------------------------------------------------------------ helpers
say()  { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
info() { printf '   %s\n' "$*"; }
warn() { printf '   WARN: %s\n' "$*"; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# run: print the command; execute it only with --apply / --uninstall.
run() {
  printf '   + %s\n' "$*"
  if [ "$APPLY" = 1 ]; then "$@"; else return 0; fi
}
# tryrun: like run, but a failure is reported, not fatal.
tryrun() {
  printf '   + %s\n' "$*"
  if [ "$APPLY" = 1 ]; then "$@" || info "(exit $? ignored)"; else return 0; fi
}

xml() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

[ "$(uname -s)" = "Darwin" ] || die "macOS only (this is $(uname -s))."
case "$PROFILE" in ''|*[!A-Za-z0-9._-]*) die "bad --profile '$PROFILE' (use letters, digits . _ -)";; esac
case "$TIMEOUT" in ''|*[!0-9]*) die "--timeout must be a number of seconds";; esac

# ------------------------------------------------------------------ target user
T_USER="${OPT_USER:-${SUDO_USER:-}}"
[ -n "$T_USER" ] || T_USER="$(id -un)"
if [ "$T_USER" = "root" ]; then
  die "target user resolved to root; run via sudo from the peer's own account or pass --user NAME."
fi
id "$T_USER" >/dev/null 2>&1 || die "no such user: $T_USER"
T_UID="$(id -u "$T_USER")"
T_GROUP="$(id -gn "$T_USER")"
T_HOME="$(dscl . -read "/Users/$T_USER" NFSHomeDirectory 2>/dev/null | awk '{print $2}')"
[ -n "$T_HOME" ] && [ -d "$T_HOME" ] || die "cannot resolve home directory for $T_USER"
COLIMA_HOME="$T_HOME/.colima"

if [ "$PROFILE" = "default" ]; then LABEL="io.33god.colima"; else LABEL="io.33god.colima.$PROFILE"; fi
DAEMON_PLIST="$LAUNCHD_DIR/$LABEL.plist"
RUNNER="$SUPPORT_DIR/colima-run.sh"
SAVED_DIR="$SUPPORT_DIR/saved-agents"
EXPECTED_FILE="$SUPPORT_DIR/$LABEL.expected"
DOCKER_SOCK="$COLIMA_HOME/$PROFILE/docker.sock"
LOG_FILE="$LOG_DIR/colima-$PROFILE.log"
AGENT_DIR="$T_HOME/Library/LaunchAgents"

# can we run things as the target user (for probes, and for real in --apply)?
CAN_AS_USER=0
if [ "$(id -un)" = "$T_USER" ] || [ "$(id -u)" = 0 ]; then CAN_AS_USER=1; fi

as_user() {
  if [ "$(id -un)" = "$T_USER" ]; then
    env HOME="$T_HOME" USER="$T_USER" LOGNAME="$T_USER" PATH="$DAEMON_PATH" COLIMA_HOME="$COLIMA_HOME" "$@"
  elif [ "$(id -u)" = 0 ]; then
    sudo -u "$T_USER" -H env HOME="$T_HOME" USER="$T_USER" LOGNAME="$T_USER" PATH="$DAEMON_PATH" COLIMA_HOME="$COLIMA_HOME" "$@"
  else
    return 99
  fi
}

# ------------------------------------------------------------------ runner script
# Identical on every peer; per-peer values arrive through the plist environment.
emit_runner() {
  cat <<'RUNNER_EOF'
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
RUNNER_EOF
}

# ------------------------------------------------------------------ plist
render_plist() {
  local u g h p
  u="$(xml "$T_USER")"; g="$(xml "$T_GROUP")"; h="$(xml "$T_HOME")"
  p="$(xml "$DAEMON_PATH")"
  cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$(xml "$LABEL")</string>
	<key>UserName</key>
	<string>$u</string>
	<key>GroupName</key>
	<string>$g</string>
	<key>ProgramArguments</key>
	<array>
		<string>/bin/bash</string>
		<string>$(xml "$RUNNER")</string>
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
	<string>$h</string>
	<key>EnvironmentVariables</key>
	<dict>
		<key>HOME</key>
		<string>$h</string>
		<key>USER</key>
		<string>$u</string>
		<key>LOGNAME</key>
		<string>$u</string>
		<key>PATH</key>
		<string>$p</string>
		<key>COLIMA_HOME</key>
		<string>$(xml "$COLIMA_HOME")</string>
		<key>G33_COLIMA_PROFILE</key>
		<string>$(xml "$PROFILE")</string>
		<key>G33_COLIMA_FLAGS</key>
		<string>$(xml "$START_FLAGS")</string>
		<key>G33_COLIMA_LABEL</key>
		<string>$(xml "$LABEL")</string>
		<key>G33_COLIMA_LOGDIR</key>
		<string>$(xml "$LOG_DIR")</string>
	</dict>
	<key>StandardOutPath</key>
	<string>$(xml "$LOG_FILE")</string>
	<key>StandardErrorPath</key>
	<string>$(xml "$LOG_FILE")</string>
</dict>
</plist>
EOF
}

# ------------------------------------------------------------------ probes
find_agent_plist() {
  # prints the path of the user's LaunchAgent whose Label is $BREW_LABEL
  local f lab
  for f in "$AGENT_DIR/sh.brew.colima.plist" "$AGENT_DIR/$BREW_LABEL.plist"; do
    [ -f "$f" ] || continue
    lab="$(plutil -extract Label raw -o - "$f" 2>/dev/null)"
    if [ "$lab" = "$BREW_LABEL" ]; then printf '%s' "$f"; return 0; fi
  done
  return 1
}

agent_loaded() { launchctl print "gui/$T_UID/$BREW_LABEL" >/dev/null 2>&1; }
daemon_loaded() { launchctl print "system/$LABEL" >/dev/null 2>&1; }
gui_domain_up() { launchctl print "gui/$T_UID" >/dev/null 2>&1; }

colima_running() { as_user colima status --profile "$PROFILE" >/dev/null 2>&1; }

docker_names() {
  as_user env DOCKER_HOST="unix://$DOCKER_SOCK" docker ps --format '{{.Names}}' 2>/dev/null
}

PREFLIGHT_FAIL=0
preflight() {
  step "Preflight (target: $T_USER uid=$T_UID home=$T_HOME profile=$PROFILE label=$LABEL)"
  info "mode: $ACTION, $( [ "$APPLY" = 1 ] && echo APPLY || echo 'DRY RUN, nothing is changed' )"
  if [ "$APPLY" = 1 ] && [ "$(id -u)" != 0 ]; then die "--apply/--uninstall need root: sudo $0 ..."; fi
  if [ "$CAN_AS_USER" != 1 ]; then
    warn "not root and not $T_USER: tool probes skipped (re-run as $T_USER or with sudo for the full report)"
    return 0
  fi

  local cver lver ent vmtype yaml
  if ! as_user colima version >/dev/null 2>&1; then
    warn "colima not found on PATH ($DAEMON_PATH) for $T_USER"; PREFLIGHT_FAIL=1; return 0
  fi
  cver="$(as_user colima version 2>/dev/null | head -1)"
  lver="$(as_user limactl --version 2>/dev/null | head -1)"
  info "$cver; $lver"

  # version gate by capability: 'colima start --foreground' must exist, and so must every flag we pass.
  local help flag
  help="$(as_user colima start --help 2>&1)"
  if ! printf '%s' "$help" | grep -q -- '--foreground'; then
    warn "this colima has no 'start --foreground' (needs >= 0.5.6): upgrade with 'brew upgrade colima'"; PREFLIGHT_FAIL=1
  else
    info "colima supports 'start --foreground'"
  fi
  for flag in $START_FLAGS; do
    case "$flag" in
      --*) flag="${flag%%=*}"
           if ! printf '%s' "$help" | grep -q -- "$flag"; then warn "colima start has no flag $flag"; PREFLIGHT_FAIL=1; fi ;;
    esac
  done

  yaml="$COLIMA_HOME/$PROFILE/colima.yaml"
  if [ -f "$yaml" ]; then
    vmtype="$(awk '/^vmType:/{print $2; exit}' "$yaml")"
    info "profile config: $yaml (vmType=${vmtype:-unset})"
    if [ "${vmtype:-vz}" = "vz" ]; then
      ent="$(as_user sh -c 'command -v limactl' 2>/dev/null)"
      ent="$(readlink -f "$ent" 2>/dev/null || printf '%s' "$ent")"
      if [ -n "$ent" ] && codesign -d --entitlements - "$ent" 2>&1 | grep -q 'com.apple.security.virtualization'; then
        info "limactl carries the com.apple.security.virtualization entitlement ($ent)"
      else
        warn "limactl lacks the virtualization entitlement; vz will not start: brew reinstall lima"; PREFLIGHT_FAIL=1
      fi
    fi
    if grep -Eq '^\s*address:\s*true|^\s*mode:\s*bridged' "$yaml"; then
      warn "profile uses a reachable address / bridged network (socket_vmnet needs a sudoers entry that a daemon cannot prompt for)"
    fi
  else
    warn "no $yaml: profile '$PROFILE' was never created; run 'colima start --profile $PROFILE' once as $T_USER first"
    PREFLIGHT_FAIL=1
  fi

  local fv pm
  fv="$(fdesetup status 2>/dev/null | head -1)"
  info "FileVault: ${fv:-unknown}"
  case "$fv" in
    *"is On"*) warn "FileVault is ON: the daemon starts only after the disk is unlocked (authenticated restart or software-update restart: yes; cold power-loss boot: no, it stops at the pre-boot password screen). See README." ;;
  esac
  pm="$(pmset -g 2>/dev/null | awk '/autorestart/{print $2}')"
  info "pmset autorestart: ${pm:-unknown}"
  [ "${pm:-1}" = "1" ] || warn "autorestart is 0; power loss will not reboot the Mac: sudo pmset -a autorestart 1"
  return 0
}

# ------------------------------------------------------------------ waits
wait_agent_gone() {
  local i=0
  while [ "$i" -lt 180 ]; do
    agent_loaded || break
    sleep 1; i=$((i + 1))
  done
  i=0
  while [ "$i" -lt 180 ]; do
    colima_running || return 0
    sleep 2; i=$((i + 2))
  done
  return 1
}

verify_daemon() {
  # waits for socket, then expected containers; prints evidence
  local i=0 names missing n
  say "   waiting up to ${TIMEOUT}s for $DOCKER_SOCK ..."
  while [ "$i" -lt "$TIMEOUT" ]; do
    [ -S "$DOCKER_SOCK" ] && docker_names >/dev/null 2>&1 && break
    sleep 3; i=$((i + 3))
  done
  [ -S "$DOCKER_SOCK" ] || { say "   FAIL: docker socket never appeared"; return 1; }
  say "   socket up after ~${i}s; waiting for containers ..."
  local want="$EXPECT"
  if [ -z "$want" ] && [ -f "$EXPECTED_FILE" ]; then want="$(tr '\n' ',' < "$EXPECTED_FILE")"; fi
  while [ "$i" -lt "$TIMEOUT" ]; do
    names="$(docker_names)"
    missing=""
    for n in $(printf '%s' "$want" | tr ',' ' '); do
      printf '%s\n' "$names" | grep -Fxq "$n" || missing="$missing $n"
    done
    if [ -z "$missing" ]; then break; fi
    sleep 3; i=$((i + 3))
  done
  names="$(docker_names)"
  say "   docker ps (as $T_USER):"
  printf '%s\n' "$names" | sed 's/^/     /'
  if [ -n "${missing:-}" ]; then say "   FAIL: not running after ${i}s:${missing}"; return 1; fi
  if [ -z "$want" ]; then say "   (no expected-container list: only checked that docker ps answers)"; fi
  say "   OK: $(printf '%s\n' "$names" | grep -c .) containers running${want:+, all expected ones present}"
  return 0
}

print_daemon_state() {
  launchctl print "system/$LABEL" 2>/dev/null | grep -E '^\s*(state|pid|runs|last exit code|username|program|path) =' | sed 's/^/     /'
}

# ------------------------------------------------------------------ install
do_install() {
  local agent_plist rendered
  preflight
  [ "$PREFLIGHT_FAIL" = 0 ] || { [ "$APPLY" = 1 ] && die "preflight failed (see WARN lines above); nothing was changed."; }

  step "Rendered $DAEMON_PLIST"
  rendered="$(mktemp -t 33god-colima-plist)" || die "mktemp failed"
  render_plist > "$rendered"
  if plutil -lint "$rendered" >/dev/null 2>&1; then info "plutil -lint: OK"; else plutil -lint "$rendered"; die "rendered plist is invalid"; fi
  sed 's/^/     /' "$rendered"
  if [ -n "$EMIT_DIR" ]; then
    mkdir -p "$EMIT_DIR" && cp "$rendered" "$EMIT_DIR/$LABEL.plist" && emit_runner > "$EMIT_DIR/colima-run.sh" \
      && info "emitted $EMIT_DIR/$LABEL.plist and $EMIT_DIR/colima-run.sh"
  fi

  step "Runner script $RUNNER"
  emit_runner | sed 's/^/     /'

  step "1/6 Capture the running container set (the post-switch acceptance list)"
  local snap=""
  if [ "$CAN_AS_USER" = 1 ] && [ -S "$DOCKER_SOCK" ]; then
    snap="$(docker_names)"
    info "$(printf '%s\n' "$snap" | grep -c .) running containers: $(printf '%s' "$snap" | tr '\n' ' ')"
  else
    info "docker socket not live (or not probeable); acceptance will be 'docker ps answers' unless --expect is given"
  fi
  run install -d -m 755 -o root -g wheel "$SUPPORT_DIR"
  if [ "$APPLY" = 1 ]; then printf '%s\n' "$snap" | grep . > "$EXPECTED_FILE" || : > "$EXPECTED_FILE"; else info "+ write list to $EXPECTED_FILE"; fi

  step "2/6 Retire the user-level brew colima agent (gui/$T_UID/$BREW_LABEL)"
  agent_plist="$(find_agent_plist || true)"
  if agent_loaded; then
    info "loaded in gui/$T_UID: booting it out (brief outage; containers restart with the new daemon)"
    tryrun launchctl bootout "gui/$T_UID/$BREW_LABEL"
    if [ "$APPLY" = 1 ]; then
      if ! wait_agent_gone; then
        warn "colima still running after bootout; forcing a stop"
        as_user colima stop --force --profile "$PROFILE" || true
      fi
    fi
  else
    info "not loaded in gui/$T_UID (already retired, or nobody is logged in)"
  fi
  if [ -n "$agent_plist" ]; then
    info "moving $agent_plist out of LaunchAgents so a login cannot start a second instance"
    run install -d -m 700 -o root -g wheel "$SAVED_DIR"
    run mv "$agent_plist" "$SAVED_DIR/$(basename "$agent_plist")"
  else
    info "no LaunchAgent plist for $BREW_LABEL in $AGENT_DIR (nothing to move)"
  fi
  if [ "$APPLY" = 1 ] && colima_running; then
    warn "colima is running outside launchd; stopping it so the daemon owns the VM"
    as_user colima stop --profile "$PROFILE" || as_user colima stop --force --profile "$PROFILE" || true
  fi

  step "3/6 Install runner, log dir, plist"
  run install -d -m 755 -o "$T_USER" -g "$T_GROUP" "$LOG_DIR"
  if [ "$APPLY" = 1 ]; then
    local tmp_runner; tmp_runner="$(mktemp -t 33god-colima-run)"; emit_runner > "$tmp_runner"
    install -m 755 -o root -g wheel "$tmp_runner" "$RUNNER"; rm -f "$tmp_runner"
    if daemon_loaded; then info "daemon already loaded: booting out before replacing the plist"; launchctl bootout "system/$LABEL" || true; sleep 2; fi
    install -m 644 -o root -g wheel "$rendered" "$DAEMON_PLIST"
    plutil -lint "$DAEMON_PLIST" || die "installed plist failed lint"
    info "installed $RUNNER and $DAEMON_PLIST"
  else
    info "+ install -m 755 -o root -g wheel <runner> $RUNNER"
    info "+ install -m 644 -o root -g wheel <plist> $DAEMON_PLIST"
  fi
  rm -f "$rendered"

  step "4/6 Load the daemon (system domain)"
  run launchctl bootstrap system "$DAEMON_PLIST"
  tryrun launchctl enable "system/$LABEL"

  step "5/6 Verify docker socket and containers"
  if [ "$APPLY" = 1 ]; then
    if verify_daemon; then
      step "6/6 Daemon state"
      print_daemon_state
      say ""
      say "DONE. $LABEL runs colima as $T_USER at boot; no login needed."
      say "Next: README 'Verify after a reboot'. Revert any time: sudo $0 --uninstall"
    else
      step "Verification FAILED"
      tail -n 25 "$LOG_FILE" 2>/dev/null | sed 's/^/     log: /'
      print_daemon_state
      if [ "$KEEP_ON_FAIL" = 1 ]; then
        die "left in place (--keep-on-fail). Log: $LOG_FILE. Revert: sudo $0 --uninstall"
      fi
      say "   rolling back to the brew service so the stack comes back ..."
      do_uninstall quiet
      die "rolled back; the peer is on the brew service again. Log: $LOG_FILE"
    fi
  else
    info "would wait for $DOCKER_SOCK, then require: ${EXPECT:-the container set captured in step 1}"
    step "6/6 (dry run) Done: nothing changed. Re-run with --apply."
  fi
}

# ------------------------------------------------------------------ uninstall
do_uninstall() {
  local quiet="${1:-}" saved f
  [ "$quiet" = quiet ] || preflight
  step "Uninstall: $LABEL -> brew colima agent"
  if daemon_loaded; then
    info "booting out system/$LABEL (ExitTimeOut 120s allows a graceful VM stop)"
    tryrun launchctl bootout "system/$LABEL"
    if [ "$APPLY" = 1 ]; then
      local i=0
      while [ "$i" -lt 150 ] && colima_running; do sleep 2; i=$((i + 2)); done
      colima_running && as_user colima stop --force --profile "$PROFILE" || true
    fi
  else
    info "system/$LABEL is not loaded"
  fi
  run rm -f "$DAEMON_PLIST"
  run rm -f "$RUNNER"
  run rm -f "$EXPECTED_FILE"

  saved=""
  for f in "$SAVED_DIR"/*.plist; do [ -f "$f" ] && saved="$f" && break; done
  if [ -n "$saved" ]; then
    info "restoring the saved LaunchAgent plist"
    run install -m 644 -o "$T_USER" -g "$T_GROUP" "$saved" "$AGENT_DIR/$(basename "$saved")"
    run rm -f "$saved"
    if gui_domain_up; then
      tryrun launchctl bootstrap "gui/$T_UID" "$AGENT_DIR/$(basename "$saved")"
    else
      info "no GUI session for $T_USER: the brew agent will start at the next login"
    fi
  elif [ -x /opt/homebrew/bin/brew ] || [ -x /usr/local/bin/brew ]; then
    info "no saved plist: asking brew to recreate the service"
    tryrun sudo -u "$T_USER" -H env HOME="$T_HOME" PATH="$DAEMON_PATH" brew services start colima
  else
    warn "no saved plist and no brew; start colima yourself: colima start --profile $PROFILE"
  fi
  if [ "$APPLY" = 1 ] && gui_domain_up; then
    local i=0
    while [ "$i" -lt "$TIMEOUT" ] && ! { [ -S "$DOCKER_SOCK" ] && docker_names >/dev/null 2>&1; }; do sleep 3; i=$((i + 3)); done
    say "   docker ps after revert:"; docker_names | sed 's/^/     /'
  fi
  if [ "$quiet" != quiet ]; then
    if [ "$APPLY" = 1 ]; then
      say ""; say "Uninstalled. Colima is a user-level brew service again (login-gated)."
    else
      say ""; say "(dry run) nothing changed. Re-run without --dry-run to uninstall."
    fi
  fi
}

case "$ACTION" in
  install) do_install ;;
  uninstall) do_uninstall ;;
esac

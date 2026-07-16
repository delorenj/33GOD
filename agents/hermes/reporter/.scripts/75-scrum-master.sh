#!/usr/bin/env bash
# Install the Scrum Master continuous-ticket sentinel: systemd timer + runner,
# and stage the engine docs + enforcement tools into the role dir.
# Only meaningful for role: scrum-master (copier guards the _tasks call).
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"
load_role_env

if [[ "$ROLE" != "scrum-master" ]]; then
  log "[75] role is '$ROLE', not scrum-master — skipping sentinel install"; exit 0
fi
if already_done 75-scrum-master && [[ "${FORCE_SENTINEL:-0}" != "1" ]]; then
  log "[75] scrum master sentinel already installed — skipping"; exit 0
fi

RUNTIME="$ROLE_DIR/runtime"
REPO_ROOT="$(project_repo_path)"
RUNNER="$ROLE_DIR/.scripts/scrum-master/continuous-ticket-sentinel.sh"
SYS_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYS_DIR" "$RUNTIME/logs"

[[ -f "$RUNNER" ]] || die "[75] runner missing: $RUNNER (template render incomplete)"
chmod +x "$RUNNER" "$ROLE_DIR/.scripts/scrum-master/"*.sh 2>/dev/null || true
chmod +x "$ROLE_DIR/.scripts/scrum-master/bin/"*.sh 2>/dev/null || true

LOG="$RUNTIME/logs/continuous-ticket-sentinel.log"
ENV_FILE="$HOME/.hermes/${AGENT_ID}.env"

if [[ "$(uname -s)" == "Darwin" ]]; then
  # macOS: a launchd LaunchAgent that runs the sentinel every 60 seconds. It
  # sources the per-agent env file (ticket-provider keys) and exports them.
  LA_DIR="$HOME/Library/LaunchAgents"
  mkdir -p "$LA_DIR"
  LABEL="com.hermes.${AGENT_ID}.sentinel"
  PLIST="$LA_DIR/$LABEL.plist"
  cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>-lc</string>
    <string>set -a; [ -f "$ENV_FILE" ] &amp;&amp; . "$ENV_FILE"; set +a; exec "$RUNNER"</string>
  </array>
  <key>StartInterval</key><integer>60</integer>
  <key>RunAtLoad</key><true/>
  <key>WorkingDirectory</key><string>$REPO_ROOT</string>
  <key>EnvironmentVariables</key>
  <dict><key>HERMES_HOME</key><string>$RUNTIME</string></dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
PLIST
  launchctl unload "$PLIST" >/dev/null 2>&1 || true
  if launchctl load -w "$PLIST" >/dev/null 2>&1; then
    log "    loaded launchd agent: $LABEL"
  else
    warn "    launchd load failed; plist written at $PLIST"
  fi
else
  # Linux: systemd --user oneshot service plus a 1-minute timer.
  ENV_FILES="$(cat <<'ENVFILES'
EnvironmentFile=-%h/.config/hermes-agent/env
EnvironmentFile=-%h/.hermes/env
EnvironmentFile=-%h/.hermes/hermes-agent.env
ENVFILES
)"
  ENV_FILES="$ENV_FILES
EnvironmentFile=-%h/.hermes/${AGENT_ID}.env"
  SVC_UNIT="hermes-${AGENT_ID}-continuous-ticket-sentinel.service"
  TIMER_UNIT="hermes-${AGENT_ID}-continuous-ticket-sentinel.timer"
  cat > "$SYS_DIR/$SVC_UNIT" <<UNIT
[Unit]
Description=Hermes Continuous Ticket Sentinel — $DISPLAY_NAME
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$REPO_ROOT
Environment=HERMES_HOME=$RUNTIME
$ENV_FILES
ExecStart=$RUNNER
TimeoutStartSec=45min
StandardOutput=append:$LOG
StandardError=append:$LOG
UNIT
  cat > "$SYS_DIR/$TIMER_UNIT" <<UNIT
[Unit]
Description=Continuous ticket sentinel for $AGENT_ID

[Timer]
OnBootSec=1min
OnUnitInactiveSec=1min
Unit=$SVC_UNIT
Persistent=true

[Install]
WantedBy=timers.target
UNIT
  if systemd_user_available; then
    systemctl --user daemon-reload
    systemctl --user enable --now "$TIMER_UNIT" >/dev/null 2>&1 \
      && log "    enabled: $TIMER_UNIT" \
      || warn "    failed to enable: $TIMER_UNIT"
  else
    warn "    systemd --user not available; units installed at $SYS_DIR but not enabled"
  fi
fi

log "[75] scrum master sentinel installed (provider: $(yaml_get ticket_provider.name))"
mark_done 75-scrum-master

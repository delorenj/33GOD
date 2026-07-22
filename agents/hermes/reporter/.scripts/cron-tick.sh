#!/usr/bin/env bash
set -euo pipefail

PROFILE_NAME="delonet-company-reporter"
PROFILE_HOME="$HOME/.hermes/profiles/$PROFILE_NAME"
FLEET_ENV="${HERMES_FLEET_ENV:-$HOME/.hermes/fleet.env}"

if [[ -f "$FLEET_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$FLEET_ENV"
fi

HERMES_BIN="${HERMES_FLEET_BIN:-$HOME/.local/bin/hermes}"
exec env \
  HERMES_HOME="$PROFILE_HOME" \
  HERMES_TIMEZONE="America/New_York" \
  HERMES_OAUTH_FILE="${HERMES_FLEET_OAUTH_FILE:-$HOME/.hermes/auth.json}" \
  CODEX_HOME="${HERMES_FLEET_CODEX_HOME:-$HOME/.codex}" \
  "$HERMES_BIN" cron --accept-hooks tick

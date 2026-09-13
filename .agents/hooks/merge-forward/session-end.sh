#!/usr/bin/env bash
# Legacy compatibility launcher. Native ownership belongs to hook-hub after
# cutover; direct registrations left by old installers become passive.
set -uo pipefail
CLIENT="${BB_HOOK_CLI:-unknown}"
if [[ "${1:-}" == "--client" ]]; then CLIENT="${2:-unknown}"; fi
OWNERSHIP="${HOME}/.agents/hooks/hub/ownership.py"
if [[ -f "$OWNERSHIP" ]] && python3 "$OWNERSHIP" merge-forward --cli "$CLIENT"; then
  cat >/dev/null 2>&1 || true
  exit 0
fi
if [[ "${GOD_MERGE_FORWARD_REBALANCE:-0}" == "1" || "${GOD_MERGE_FORWARD_REBALANCE_ENABLE:-1}" != "1" ]]; then
  cat >/dev/null 2>&1 || true
  exit 0
fi
REPOSITORY="$(git rev-parse --show-toplevel 2>/dev/null || true)"
WORKER="${REPOSITORY}/.agents/skills/33god-merge-forward/scripts/rebalance.py"
if [[ -z "$REPOSITORY" || ! -f "$WORKER" ]]; then
  cat >/dev/null 2>&1 || true
  exit 0
fi
INPUT_TMP="$(mktemp -t 33god-merge-forward-session.XXXXXX 2>/dev/null)" || exit 0
cat >"$INPUT_TMP" 2>/dev/null || printf '{}\n' >"$INPUT_TMP"
STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/33god-merge-forward"
mkdir -p "$STATE_DIR" 2>/dev/null || true
GOD_MERGE_FORWARD_REBALANCE=1 setsid nohup timeout "${GOD_MERGE_FORWARD_REBALANCE_TIMEOUT:-900}" \
  python3 "$WORKER" --client "$CLIENT" --input "$INPUT_TMP" \
  </dev/null >>"${STATE_DIR}/launcher.log" 2>&1 &
disown 2>/dev/null || true
exit 0

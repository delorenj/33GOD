#!/usr/bin/env bash
# Fast session-end entrypoint. Capture stdin and detach the real skill tuner.
# Always exit successfully and never hold up agent shutdown.
set -uo pipefail

CLIENT="unknown"
if [[ "${1:-}" == "--client" ]]; then
  CLIENT="${2:-unknown}"
fi

# The tuner invokes Codex itself. Its child session must not recursively tune.
if [[ "${GOD_MERGE_FORWARD_REBALANCE:-0}" == "1" || "${GOD_MERGE_FORWARD_REBALANCE_ENABLE:-1}" != "1" ]]; then
  cat >/dev/null 2>&1 || true
  exit 0
fi

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HOOK_DIR}/../../.." && pwd)"
WORKER="${REPO_ROOT}/skills/33god-merge-forward/scripts/rebalance.py"
[[ -f "$WORKER" ]] || { cat >/dev/null 2>&1 || true; exit 0; }

INPUT_TMP="$(mktemp -t 33god-merge-forward-session.XXXXXX 2>/dev/null)" || exit 0
cat >"$INPUT_TMP" 2>/dev/null || printf '{}\n' >"$INPUT_TMP"

STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/33god-merge-forward"
mkdir -p "$STATE_DIR" 2>/dev/null || true

GOD_MERGE_FORWARD_REBALANCE=1 \
  setsid nohup timeout "${GOD_MERGE_FORWARD_REBALANCE_TIMEOUT:-900}" \
  python3 "$WORKER" --client "$CLIENT" --input "$INPUT_TMP" \
  </dev/null >>"${STATE_DIR}/launcher.log" 2>&1 &
disown 2>/dev/null || true

exit 0

#!/usr/bin/env bash
# hook-guard.sh <hook-id> <command> [args...]
set -uo pipefail

HOOK_ID="${1:-}"
shift || true

# shellcheck source=local-config.sh
source "$(dirname "${BASH_SOURCE[0]}")/local-config.sh"

if [[ -n "$HOOK_ID" ]] && hook_disabled "$HOOK_ID"; then
  cat >/dev/null 2>&1 || true
  exit 0
fi

[[ $# -eq 0 ]] && exit 0
exec "$@"

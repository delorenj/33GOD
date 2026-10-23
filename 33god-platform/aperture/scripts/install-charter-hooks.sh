#!/usr/bin/env bash
# Installs the Aperture charter commit-msg hook into the 33god-platform repo.
# Idempotent. Run from anywhere: bash aperture/scripts/install-charter-hooks.sh
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # 33god-platform root
HOOK_SRC="$REPO/aperture/scripts/commit-msg-hook.sh"
HOOK_DST="$REPO/.git/hooks/commit-msg"
mkdir -p "$REPO/.git/hooks"
install -m 0755 "$HOOK_SRC" "$HOOK_DST"
echo "charter gate installed: $HOOK_DST"
echo "every commit touching aperture/ now requires a charter-ack marker in the message"

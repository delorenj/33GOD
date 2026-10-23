#!/usr/bin/env bash
# Installs the Aperture charter pre-commit hook into the 33god-platform repo.
# Works with the fleet-wide core.hooksPath: the fleet pre-commit chains to
# the repo's own .git/hooks/pre-commit via guard_chain_local.
# Idempotent. Run: bash aperture/scripts/install-charter-hooks.sh
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # 33god-platform root
HOOK_SRC="$REPO/aperture/scripts/charter-pre-commit.sh"
HOOK_DST="$REPO/.git/hooks/pre-commit"
mkdir -p "$REPO/.git/hooks"

# compose with any existing repo pre-commit (chain, don't clobber)
if [ -f "$HOOK_DST" ] && ! grep -q 'APERTURE CHARTER GATE' "$HOOK_DST"; then
  mv "$HOOK_DST" "$HOOK_DST.pre-charter"
  printf '%s\n' '#!/usr/bin/env bash' 'bash "$(dirname "$0")/../aperture/scripts/charter-pre-commit.sh" "$@" || exit 1' 'exec bash "$(dirname "$0")/pre-commit.pre-charter" "$@"' > "$HOOK_DST"
  chmod +x "$HOOK_DST"
  echo "chained charter gate after existing repo pre-commit"
else
  install -m 0755 "$HOOK_SRC" "$HOOK_DST"
  echo "charter gate installed: $HOOK_DST"
fi
echo "every commit touching aperture/ now requires a fresh (<4h) .aperture/charter-session marker"
echo "create it after READING the charter:  mkdir -p .aperture && touch .aperture/charter-session"

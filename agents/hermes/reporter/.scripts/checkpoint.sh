#!/usr/bin/env bash
# Auto-checkpoint commit for the agent's runtime submodule.
# Idempotent — exits 0 with no commit if there are no changes.
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "$0")/../runtime" && pwd)"
cd "$RUNTIME_DIR"

# Skip if not a git repo (e.g. submodule not initialized)
[[ -d .git || -f .git ]] || exit 0

git add -A
if git diff --cached --quiet; then
  exit 0
fi
git -c commit.gpgsign=false commit -m "checkpoint $(date -Iseconds)" >/dev/null
git push origin HEAD 2>&1 | tail -1 || true

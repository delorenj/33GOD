#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run agent-voice-soprano
fi

if command -v mise >/dev/null 2>&1; then
  exec mise x -- uv run agent-voice-soprano
fi

echo "Error: neither 'uv' nor 'mise' found in PATH" >&2
exit 1

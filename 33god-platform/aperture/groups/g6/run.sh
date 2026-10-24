#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
case "${GOD_GPU:-0}" in
  0) exec docker compose "$@" ;;
  1) exec docker compose --profile gpu "$@" ;;
  *) printf 'GOD_GPU must be 0 or 1\n' >&2; exit 2 ;;
esac

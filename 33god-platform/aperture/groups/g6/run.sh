#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# The flag owns profile selection; never inherit a stale GPU profile.
unset COMPOSE_PROFILES
case "${GOD_GPU:-0}" in
  0) exec docker compose "$@" ;;
  1) exec docker compose --profile gpu "$@" ;;
  *) printf 'GOD_GPU must be 0 or 1\n' >&2; exit 2 ;;
esac

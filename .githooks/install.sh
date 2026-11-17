#!/usr/bin/env bash
# Point this checkout's .git/hooks/pre-commit at the versioned dispatcher.
# Idempotent and quiet; mise runs it on every directory enter, so a fresh
# clone or a clobbered hook heals itself. The fleet-wide guard chains to it.
set -eu
ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null)" || exit 0
HOOKS="$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir)/hooks"
DST="$HOOKS/pre-commit"
SRC="$ROOT/.githooks/pre-commit"
[ "$(readlink "$DST" 2>/dev/null)" = "$SRC" ] && exit 0
mkdir -p "$HOOKS"
if [ -e "$DST" ] && [ ! -L "$DST" ] && ! grep -q 'APERTURE CHARTER GATE' "$DST"; then
  echo "githooks: keeping unknown pre-commit as $DST.local-before-dispatcher" >&2
  mv "$DST" "$DST.local-before-dispatcher"
fi
ln -sfn "$SRC" "$DST"
[ "${1:-}" = "--quiet" ] || echo "githooks: $DST -> $SRC"

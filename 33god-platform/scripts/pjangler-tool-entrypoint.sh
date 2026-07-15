#!/bin/sh
set -eu

case "${PJANGLER_TOOL_MODE:-}" in
  cli)
    program="dist/index.js"
    ;;
  mcp)
    program="dist/mcp-server.js"
    ;;
  *)
    echo "PJANGLER_TOOL_MODE must be 'cli' or 'mcp'" >&2
    exit 64
    ;;
esac

if [ ! -f "${program}" ] || [ ! -f package.json ]; then
  echo "pjangler source mount is incomplete: expected package.json and ${program}" >&2
  exit 66
fi

# node_modules is an anonymous volume; the read-only source bind is untouched.
npm install --omit=dev --no-package-lock --ignore-scripts --no-audit --no-fund >&2
exec node "${program}" "$@"

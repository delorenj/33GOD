#!/usr/bin/env bash
# The Aperture charter gate now runs from the 33GOD repo's versioned pre-commit
# dispatcher (.githooks/pre-commit), next to the Atlas gate. This shim keeps the
# old entry point working: it installs the dispatcher. Idempotent.
set -euo pipefail
ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
bash "$ROOT/.githooks/install.sh"
echo "every commit touching aperture/ now requires a fresh (<4h) .aperture/charter-session marker"
echo "create it after READING the charter:  mkdir -p .aperture && touch .aperture/charter-session"

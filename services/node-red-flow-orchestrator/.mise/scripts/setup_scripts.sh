#!/usr/bin/env bash
set -euo pipefail

cd "${SCRIPTS_DIR}"

if [[ ! -d .venv ]]; then
  echo "Creating Python venv..."
  uv venv
fi

echo "Installing dependencies..."
uv pip install aio-pika boto3

echo "Script environment ready."

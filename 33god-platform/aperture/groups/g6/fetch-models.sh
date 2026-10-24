#!/usr/bin/env bash
# WARNING: downloads ~149 MB from public model registries into the G6 models volume.
set -euo pipefail
cd "$(dirname "$0")"
docker compose build whisper
docker compose run --rm --no-deps whisper python -m runtime.fetch_models

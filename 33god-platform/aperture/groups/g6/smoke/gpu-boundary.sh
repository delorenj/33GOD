#!/usr/bin/env bash
# Build the REAL packaged GPU engine, then hide all GPU devices.
# No model, network, inference mock or production volume is used.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --profile gpu build voxxy-engine-voxcpm
for mode in 0 1; do
  docker run --rm -i --runtime=runc --network none --memory 1856m --memory-swap 1856m     -e GOD_GPU="$mode" -e NVIDIA_VISIBLE_DEVICES=void -e CUDA_VISIBLE_DEVICES=     -e HF_HUB_OFFLINE=1 --entrypoint python "${GOD_G6_GPU_IMAGE:-god-g6-voxcpm:0.1}" - <<'PY'
import os
import torch
from fastapi.testclient import TestClient
from engine.main import app
assert not torch.cuda.is_available()
with TestClient(app) as client:
    health = client.get('/healthz')
    print('GOD_GPU=' + os.environ['GOD_GPU'], 'cuda_available=False health', health.status_code, health.json(), flush=True)
    assert health.status_code == 200
    assert health.json()['status'] == 'degraded' and not health.json()['ready']
    response = client.post('/v1/synthesize', json={'text': 'The voice pipeline is working.'})
    print('synthesis', response.status_code, response.json(), flush=True)
    assert response.status_code == 503 and response.json()['error']['code'] == 'UNAVAILABLE'
print('PASS packaged VoxCPM startup alive, degraded, unavailable synthesis', flush=True)
PY
 done

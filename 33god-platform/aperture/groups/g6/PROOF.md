# G6 proof — implementer evidence, PM review pending

Executed 2026-10-24 on Linux amd64; Docker server 29.2.1, Compose v5.0.2
(Compose v2-compatible CLI). CPU services explicitly use runc with no device
requests. GPU image was built separately; production voice containers were
not stopped or adopted. This is not ARM64 runtime or GPU inference acceptance.

## Cold CPU acceptance

Command: `bash smoke/smoke.sh`, exit **0**. It first deletes all owned G6
volumes, builds, runs `up -d --wait`, executes real data-path tests, then
`down -v` and asserts zero project residue. All six core services were healthy.
Trimmed verbatim output (build progress/deprecation warnings omitted):

```text
PASS manifest python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70 linux/amd64 + linux/arm64
PASS manifest postgres:17.6-alpine@sha256:ef257d85f76e48da1c64832459b59fcaba1a4dac97bf5d7450c77753542eee94 linux/amd64 + linux/arm64
PASS manifest ghcr.io/astral-sh/uv:0.9.7@sha256:ba4857bf2a068e9bc0e64eed8563b065908a4cd6bfb66b531a9c424c8e25e142 linux/amd64 + linux/arm64
PASS manifest nvidia/cuda:12.4.1-runtime-ubuntu22.04@sha256:517da2300c184c9999ec203c2665244bdebd3578d12fcc7065e83667932643d9 linux/amd64 + linux/arm64
PASS config zero published ports; GPU reservations isolated to gpu profile
god-g6-audio-intake-1   god-g6-cpu:0.1                                                                                 "uvicorn runtime.int…"   audio-intake   11 seconds ago   Up 11 seconds (healthy)   
god-g6-espeak-1         god-g6-cpu:0.1                                                                                 "uvicorn runtime.esp…"   espeak         11 seconds ago   Up 11 seconds (healthy)   
god-g6-vinyld-serve-1   god-g6-cpu:0.1                                                                                 "python -m runtime.v…"   vinyld-serve   11 seconds ago   Up 5 seconds (healthy)    
god-g6-vox-1            god-g6-cpu:0.1                                                                                 "uvicorn app.main:ap…"   vox            11 seconds ago   Up 5 seconds (healthy)    
god-g6-vox-db-1         postgres:17.6-alpine@sha256:ef257d85f76e48da1c64832459b59fcaba1a4dac97bf5d7450c77753542eee94   "docker-entrypoint.s…"   vox-db         11 seconds ago   Up 11 seconds (healthy)   5432/tcp
god-g6-whisper-1        god-g6-cpu:0.1                                                                                 "uvicorn runtime.whi…"   whisper        11 seconds ago   Up 11 seconds (healthy)   
Ran 6 tests in 0.051s
OK
PASS Vox missing authentication rejected 401
PASS GPU boundary {'engine': 'espeak', 'ready': True, 'model_loaded': True, 'status': 'degraded', 'device': 'cpu', 'reason': 'neural_gpu_engine_disabled', 'capabilities': {'accepts_reference_audio': False, 'needs_transcript': False, 'output_sample_rate': 22050, 'multi_speaker': False}} {'ready': True, 'status': 'degraded', 'device': 'cpu', 'reason': 'gpu_disabled', 'model': 'Systran/faster-whisper-base', 'revision': 'ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66'}
PASS TTS /synthesize 94012 WAV bytes 2.13 seconds espeak
PASS STT roundtrip returns a transcript without error: 'The moist pipeline is working.'
PASS STT bundled returns a transcript without error: 'The moist pipeline is working.'
PASS rejection 422
PASS rejection 400
PASS intake pickup SHA256 c50fea3c3e3239e69e5c0565ad425220d8216d8b3d77ba2ac07e5a3d2ff8bfc9 receipt {'version': 1, 'id': '45dfc0f6-63fc-41c0-bb9a-15f2c771e6ed', 'sha256': 'c50fea3c3e3239e69e5c0565ad425220d8216d8b3d77ba2ac07e5a3d2ff8bfc9', 'file': 'c50fea3c3e3239e69e5c0565ad425220d8216d8b3d77ba2ac07e5a3d2ff8bfc9.wav', 'bytes': 94012, 'state': 'landed', 'notified': False}
PASS invalid intake quarantined; poller remains ready
PASS Vinyl unauthorized rejected
PASS Vinyl TCP -> Whisper final: ['The voice pipeline is working.']
/god-g6-audio-intake-1 health=healthy restarts=0 requests=null
/god-g6-espeak-1 health=healthy restarts=0 requests=null
/god-g6-vinyld-serve-1 health=healthy restarts=0 requests=null
/god-g6-vox-1 health=healthy restarts=0 requests=null
/god-g6-vox-db-1 health=healthy restarts=0 requests=null
/god-g6-whisper-1 health=healthy restarts=0 requests=null
god-g6-audio-intake-1 40.88MiB / 128MiB
god-g6-espeak-1 41.29MiB / 96MiB
god-g6-vinyld-serve-1 51.6MiB / 160MiB
god-g6-vox-1 76.19MiB / 320MiB
god-g6-vox-db-1 24.36MiB / 128MiB
god-g6-whisper-1 250.9MiB / 1GiB
PASS down -v: zero project containers, volumes, networks
SMOKE RESULT: PASS — CPU TTS/STT, Vinyl, intake, no-GPU, teardown
```

The receipt hash correlates newly synthesized WAV bytes, the local input
file and durable receipt. The bundled fixture is 2.13 s real eSpeak speech,
not silence/tones or a mocked transcript. Both fresh and bundled decode gates
assert nonempty text without error, not exact words. Vox missing-auth,
empty-text, malformed-audio, invalid intake, and Vinyl token rejection were
executed. Caps sum to 1856 MiB; the stats snapshot above is **not a peak test**.
No reserved NVIDIA devices and zero restarts were observed for every core.

## Packaged neural engine: real no-GPU boundary

Command: `bash smoke/gpu-boundary.sh`, exit **0**. Builds the actual bundled
VoxCPM image, then starts its actual lifespan under 1856 MiB with `runtime=runc`,
no network, no model mount, and GPU hidden, for BOTH flag settings. Trimmed
verbatim output:

```text
voxcpm degraded-not-failed: GPU disabled or unavailable; synthesis UNAVAILABLE
GOD_GPU=0 cuda_available=False health 200 {'engine': 'voxcpm', 'status': 'degraded', 'reason': 'gpu_disabled_or_unavailable', 'ready': False, 'model_loaded': False, 'vram_used_gb': None, 'capabilities': {'accepts_reference_audio': True, 'needs_transcript': False, 'max_ref_seconds': 30.0, 'output_sample_rate': 16000, 'multi_speaker': False}}
synthesis 503 {'error': {'code': 'UNAVAILABLE', 'message': 'GPU disabled or unavailable'}}
PASS packaged VoxCPM startup alive, degraded, unavailable synthesis
voxcpm degraded-not-failed: GPU disabled or unavailable; synthesis UNAVAILABLE
GOD_GPU=1 cuda_available=False health 200 {'engine': 'voxcpm', 'status': 'degraded', 'reason': 'gpu_disabled_or_unavailable', 'ready': False, 'model_loaded': False, 'vram_used_gb': None, 'capabilities': {'accepts_reference_audio': True, 'needs_transcript': False, 'max_ref_seconds': 30.0, 'output_sample_rate': 16000, 'multi_speaker': False}}
synthesis 503 {'error': {'code': 'UNAVAILABLE', 'message': 'GPU disabled or unavailable'}}
PASS packaged VoxCPM startup alive, degraded, unavailable synthesis
```

`ready=false` is capability truth; HTTP 200 + `status=degraded` is service
liveness. Synthesis is honestly unavailable (503), not a fabricated audio
success. Compose health accepts `ready` or `degraded` status. The CPU core
uses real eSpeak and int8 Whisper instead.

For comparison, the **unmodified** upstream loader was run read-only with
GPU hidden and the existing cached public model weights under the entire
1856 MiB CPU-core budget. Exit **137**, trimmed output:

```text
cuda_available False
```

Exit 137 establishes failure to fit this cap, not impossibility on a larger
CPU host. No claim of CUDA-positive inference follows from these tests.

## Architecture manifests

`python3 smoke/manifests.py` is part of the cold smoke. All four external
index digests returned and matched linux/amd64 **and** linux/arm64 entries.
Exact per-architecture digests are in `images.lock.json`. Local source-built
tags are not represented as published multi-architecture images. ARM64 native
build/wheels/runtime are deferred rather than inferred from base manifests.

## Upstream tests and source fidelity

Read-only upstream suites (isolated interpreters, no cache/bytecode writes,
scratch TMPDIR; each repository's existing venv):

```text
voxxy: 51 passed, 2 warnings in 4.78s
vinyl: Ran 182 tests in 5.500s
OK
```

The packaged CPU unit suite additionally ran inside the built image: six
passing tests (real speech, empty text, inert configuration, pickup/hash/
idempotence, invalid WAV and symlink rejection). Original source Git statuses
for Voxxy, Vinyl and HeyMa exactly matched their pre-task states. All 25
vendored source/packaged hash pairs were checked against read-only sources.
`vendor/SOURCES.json` marks actual adaptations: local URL/host text, auth
string representation, cache docstring, HTTP recognizer, no-GPU guard and
extended engine health. No upstream implementation was edited.

## Configuration, portable payload and cleanup

CPU/gpu/attach/dev-journal configurations rendered successfully with zero
published ports. Reservations occur only on `voxxy-engine-voxcpm` in the gpu
profile. `run.sh` was checked with inherited `COMPOSE_PROFILES=gpu`: flag zero
excludes that service, flag one includes it. `dev-journal` adds no service.
Shell scripts passed `bash -n`; `git diff --check` passed.

`python3 smoke/audit.py` verifies zero forbidden secret/personal-host tokens,
all packaged provenance hashes, four configuration modes and the 1856 MiB
budget. Every bundle payload file was checked against Git's tracked index;
bundle-local ignore exceptions preserve `runtime/` and `.env.example`.
`down -v` left **zero project containers, volumes and networks**, as asserted
by label lookups. Build images/cache are intentionally retained, not counted
as runtime residue. Existing production voice/transcription containers stayed
running.


## Clean committed-context replay

Exported revision `5b3944e` using `git archive HEAD` (G6 subtree only) into a
scratch directory, then ran its shipped `bash smoke/smoke.sh`: exit **0**.
This excludes ignored source files, external source checkouts and working-tree
payload. Trimmed verbatim output:

```text
PASS secrets/personal-host scan: zero hits
PASS packaged provenance hashes: 25 files
PASS CPU memory caps: 1856 MiB
PASS config cpu zero published ports, no adopted container names
PASS config gpu zero published ports, no adopted container names
PASS config attach zero published ports, no adopted container names
PASS config dev-journal zero published ports, no adopted container names
PASS config zero published ports; GPU reservations isolated to gpu profile
PASS Vox missing authentication rejected 401
PASS TTS /synthesize 94012 WAV bytes 2.13 seconds espeak
PASS STT roundtrip returns a transcript without error: 'The moist pipeline is working.'
PASS STT bundled returns a transcript without error: 'The moist pipeline is working.'
PASS intake pickup SHA256 c50fea3c3e3239e69e5c0565ad425220d8216d8b3d77ba2ac07e5a3d2ff8bfc9 receipt {'version': 1, 'id': '64170bb0-7d77-4230-a387-a62c2d8d1fad', 'sha256': 'c50fea3c3e3239e69e5c0565ad425220d8216d8b3d77ba2ac07e5a3d2ff8bfc9', 'file': 'c50fea3c3e3239e69e5c0565ad425220d8216d8b3d77ba2ac07e5a3d2ff8bfc9.wav', 'bytes': 94012, 'state': 'landed', 'notified': False}
PASS invalid intake quarantined; poller remains ready
PASS Vinyl unauthorized rejected
PASS Vinyl TCP -> Whisper final: ['The voice pipeline is working.']
PASS down -v: zero project containers, volumes, networks
SMOKE RESULT: PASS — CPU TTS/STT, Vinyl, intake, no-GPU, teardown
```

## Unproved acceptance / intentional scope limits

* Attach overlay is **config-verified only**. Real G2 audio receiver is absent;
  remote receipt delivery and G3 ntfy readback are not proved.
* Remote intake defaults INERT; local pickup is proved, actual remote-provider
  credentials and polling are not.
* ARM64 runtime, GPU-positive inference/model snapshot pinning, full 7.7 GiB
  multi-group VM coexistence peak, desktop capture and host package install
  are not proved.
* PM independently re-runs review before merge. See `DEFERRED.md`.


## GPU-positive inference (PM addendum, 2026-10-24)

Proven on the build host RTX 3090 after the merge (previously deferred):

- `GOD_GPU=1 docker compose --profile gpu up -d` -> voxcpm engine loads
  VoxCPM2 on `cuda, dtype: bfloat16`, healthz:
  `{'engine': 'voxcpm', 'status': 'ready', 'model_loaded': True, 'ready': True,
  'capabilities': {'accepts_reference_audio': True, 'max_ref_seconds': 30.0}}`
- Real neural synthesis through the stack: `POST vox:8000/synthesize`
  -> `200 audio/wav 337964 bytes` (eSpeak CPU fallback produced 94,012).
- Build-host caveat, NOT a bundle defect: the 3090 here is shared with 19
  production processes (19.2/24.5 GiB used); the first GPU load attempt OOM'd
  with only 220 MiB free. Freeing ~6 GiB (temporarily stopping the host's own
  voxxy-engine-voxcpm) let the bundle's engine load and synthesize. A client
  host with a dedicated modern GPU (e.g. 96 GiB) has no such contention —
  the `gpu` profile with `deploy.resources.reservations.devices` (driver
  nvidia, capabilities [gpu]) is the intended tap.
- Verified the env contract: `GOD_GPU` must be exported at compose-invocation
  time (recreating without it re-interpolates to 0 -> engine stays degraded
  by design). Document `GOD_GPU=1` in the bring-up command, not just .env.

Teardown: `down -v` clean; production voxxy-engine-voxcpm restarted and
healthy (17.5 GiB back on the GPU).

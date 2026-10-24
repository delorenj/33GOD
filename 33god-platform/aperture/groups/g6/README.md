# G6 — Voice pipeline

Portable Compose project `god-g6`, owned network `g6-internal`, owned named
volumes, **no published host ports**. No external source checkout is needed to
build. Vendor provenance and original/packaged hashes: `vendor/SOURCES.json`.
PM independent review is required before merge; this bundle is not a deployment
instruction for any existing production stack.

## What runs

| Component | CPU default | Memory cap | Purpose |
|---|---|---:|---|
| `vox-db` | yes | 128 MiB | Fresh Vox voice catalog; no personal voices |
| `espeak` | yes | 96 MiB | Real eSpeak-NG synthesis via Vox's engine contract |
| `vox` | yes | 320 MiB | Vendored Vox API, catalog, audio/cache and routing |
| `whisper` | yes | 1024 MiB | Warm faster-whisper **base**, int8 CPU |
| `vinyld-serve` | yes | 160 MiB | Actual Vinyl TCP protocol, token, VAD, queues and server |
| `audio-intake` | yes | 128 MiB | Local WAV pickup + opt-in S3-compatible remote transport |
| `voxxy-engine-voxcpm` | **gpu profile only** | 8 GiB | Real upstream VoxCPM2 engine; not part of CPU budget |

CPU hard caps sum to **1856 MiB (1.8125 GiB)**. Observed post-roundtrip usage
was about 486 MiB; this is not a worst-case peak measurement. A 7.7 GiB VM
already using about 5.7 GiB for G1–G4 has little remaining headroom: serialize
requests and do not enable the 8 GiB neural engine on that VM. Build cache,
image storage, model disk space and Docker overhead are additional resources.
CPU allocation caps sum above one CPU; they are ceilings, not reservations.

VoxCPM2 startup on CPU under the **entire 1856 MiB budget** exited 137 while
loading weights. That does not prove CPU inference impossible on larger hosts;
it proves it is not a demonstrated fit here. CPU synthesis is therefore
**eSpeak speech, not VoxCPM cloning**, and CPU STT remains real Whisper.
Vinyl's recognizer adapter delegates to the shared warm Whisper HTTP endpoint
instead of allocating a second recognizer; its server protocol is preserved.

## Start / verify / stop

Prerequisites: Docker Engine + Compose v2, buildx, network access to public
image/package/model registries, and Python 3 for host-side smoke audits.
Run all commands from this directory. Never reuse the `god-g6` project name
for another deployment on the same daemon.

```sh
cp .env.example .env
GOD_GPU=0 ./run.sh up -d --build --wait --wait-timeout 420
docker compose ps
bash smoke/smoke.sh
# smoke is destructive to G6: cold down -v, build, up, real work, down -v.
GOD_GPU=0 ./run.sh down -v --remove-orphans
```

First boot downloads about 149 MB of Whisper base + Silero VAD model files.
`models.lock.json` pins the Hugging Face snapshot
`ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66` and SHA-256 of **every** file.
Silero's release URL is mutable but its bytes must match the recorded hash.
If first-boot network access is slow/restricted, pre-seed explicitly:

```sh
# WARNING: downloads public models; writes only G6's models volume.
./fetch-models.sh
GOD_MODEL_OFFLINE=1 GOD_GPU=0 ./run.sh up -d --wait --wait-timeout 420
```

Offline mode fails rather than substituting a model if a file is absent or
has the wrong digest. `down -v` deletes the pre-seed. First boot and the cold
smoke require registry/model access again after volume deletion.

### In-network APIs

No host port mapping is required. For example:

```sh
docker compose exec -T audio-intake python -c '
import httpx
r=httpx.post("http://vox:8000/synthesize",json={"text":"Hello from the voice pipeline."})
r.raise_for_status()
assert r.headers["content-type"].startswith("audio/wav")
print(len(r.content), "real WAV bytes")'
```

* Vox: `POST http://vox:8000/synthesize`, JSON `{"text":"..."}` → WAV bytes.
  This is the upstream endpoint, **not** `/api/tts`. The default empty voice
  selects an available engine (eSpeak on CPU); catalog voices are fresh.
  Optional `GOD_VOX_API_KEY` enables upstream API-key protection; provide it
  through an operator-managed environment, then pass `X-API-Key` to callers.
* STT: `POST http://whisper:8766/v1/audio/transcriptions`, multipart `file`
  → `{"text":"..."}`. Base model, English decode, 30 s / 16 MiB request caps.
  Smoke tests the real speech fixture and freshly synthesized speech, asserting
  a nonempty transcript **without claiming a particular phrase or accuracy**.
* Vinyl: TCP `vinyld-serve:7733`, real length-prefixed protocol and persistent
  pairing token in its owned `vinyl-state` volume. Smoke exercises unauthorized
  rejection, authenticated audio frames, VAD and a final Whisper transcript.
* Intake health: `http://audio-intake:8000/healthz`. Internal-only APIs without
  host ingress are intentional; an operator adds any ingress policy separately.

## `GOD_GPU` and profiles

Use **`GOD_GPU=0 ./run.sh ...`** (default) or **`GOD_GPU=1 ./run.sh ...`**.
The wrapper translates the exported flag to Compose's `gpu` profile because
Compose cannot conditionally interpolate device reservations. A `.env` flag
alone does not select a profile in the shell wrapper; use the command prefix.
Direct `docker compose --profile gpu ...` is an explicit override and requests
NVIDIA devices even if `GOD_GPU=0`; prefer the wrapper.

* CPU services always use `runtime: runc`, hide NVIDIA/CUDA devices, and never
  request GPUs. eSpeak and Whisper report `ready=true`, `status=degraded`,
  `device=cpu`: reduced neural/GPU capability is **not failed service health**.
* `gpu` adds the real VoxCPM2 image and an NVIDIA reservation. With a GPU and
  `GOD_GPU=1`, upstream weights are loaded. With no visible GPU (or flag zero),
  the engine stays alive, `/healthz` is HTTP 200 with `status=degraded`,
  `ready=false`, and synthesis returns HTTP 503 `UNAVAILABLE`. Its Compose
  healthcheck accepts the explicit degraded status, not imaginary readiness.
* `bash smoke/gpu-boundary.sh` builds the actual GPU image, runs it with GPU
  hidden and no network/model volume under 1856 MiB, tests startup and 503 for
  **both** flag values. This does not test driver pass-through or GPU inference.
* No automatic GPU-to-CPU VoxCPM weight load occurs. Production GPU services
  are not adopted, stopped, or reconfigured. GPU-positive inference and the
  ARM64 GPU dependency/runtime are deferred; see `DEFERRED.md`.
* `dev-journal` is a reserved extension contract, deliberately **no service**.
  `docker compose --profile dev-journal up` runs only the CPU core. No n8n
  keepalive container, broken workflows or imported personal state is shipped.

## Intake and host sync

Remote intake is an **INERT skeleton until the operator supplies real remote
credentials/configuration**. `GOD_INTAKE_ENDPOINT`, `GOD_INTAKE_BUCKET`,
`GOD_INTAKE_ACCESS_KEY`, `GOD_INTAKE_SECRET_KEY` all default empty; ambient
cloud credentials are not adopted. Region, prefix and polling interval are
also wired using the `GOD_INTAKE_*` variables in `.env.example`.

Local pickup is real even when remote intake is inert: atomically place a WAV
in `/pipeline/inbox` in the `god-g6-pipeline` volume. The poller validates WAV
frames, hashes the content, atomically publishes identical bytes to
`/pipeline/input/<sha256>.wav`, writes a durable receipt to
`/pipeline/receipts/<sha256>.json`, logs it, then removes the inbox copy.
Invalid WAVs are quarantined as `.rejected`. Remote objects are never deleted.
Local receipts are versioned transport records, **not Bloodbank envelopes**.
No inference/ledger consumer of `/pipeline/input` is implied by successful pickup.

Example local transfer (the smoke performs this and validates receipt/hash):

```sh
docker compose cp smoke/speech.wav audio-intake:/pipeline/inbox/manual.partial
docker compose exec -T audio-intake mv /pipeline/inbox/manual.partial /pipeline/inbox/manual.wav
```

Syncthing-audio is a **host-policy mounted source, not a container service**.
Have the host poller stage finished files into the owned pipeline inbox (using
an atomic rename). Alternatively mount an operator-owned sync directory onto
`/pipeline/inbox` in a private Compose overlay; preserve writable ownership for
UID 10001 and prevent partially written files. No host path or sync policy is
shipped here. `HOST-SIDE.md` explains the waxd/sync boundary.

## Attach to G2 / G3 (same ntfy path as G4)

Standalone mode is unchanged. The overlay attaches only `audio-intake` to
existing `g2-internal` and `g3-internal` networks. Set their names through
`GOD_G2_NETWORK` / `GOD_G3_NETWORK` if customized. It defaults ntfy to
`http://ntfy:80`, topic `aperture-g6-alerts`; G4 uses the same G3 ntfy path.

```sh
GOD_N8N_INTAKE_URL=http://n8n:5678/webhook/YOUR-INSTALLED-PATH   docker compose -f compose.yml -f compose.attach.yml up -d --wait
```

There is **no receiving audio workflow in G2 yet**. The URL remains empty by
default; do not point at G2's bus smoke ingress and assume it understands these
receipts. Once an actual receiver implements the contract in `DEFERRED.md`,
HTTP 2xx marks the receipt `notified=true`; failures retry on subsequent scans.
`GOD_N8N_INTAKE_KEY` optionally sends `X-API-Key`. That is at-least-once
notification, so the receiver deduplicates by receipt id or SHA-256. A filename
is **not** shared audio bytes across projects: choose an explicit transport
before enabling the downstream consumer. Remote/notification errors post a
JSON message to G3 ntfy; standalone URL blank means no external notifications.
Overlay config was rendered/checked; end-to-end external delivery is deferred,
not claimed from internal smoke results.

## Architecture support and reproducibility

| Image / layer | amd64 | arm64 | Runtime proof |
|---|---|---|---|
| Python 3.12 slim base | pinned manifest | pinned manifest | amd64 build + CPU smoke |
| PostgreSQL 17.6 Alpine | pinned manifest | pinned manifest | amd64 cold healthy |
| uv 0.9.7 build stage | pinned manifest | pinned manifest | amd64 build |
| CUDA 12.4.1 Ubuntu base | pinned manifest | pinned manifest | amd64 GPU-image build + no-GPU boundary |
| `god-g6-cpu:0.1` source build | local build | native build required | **arm64 runtime not yet proved** |
| `god-g6-voxcpm:0.1` source build | local build | dependencies unproved | **GPU runtime not yet proved** |

All external base images use immutable multi-arch index digests;
`images.lock.json` additionally records both architecture-specific digests.
`python3 smoke/manifests.py` re-queries the registries and compares them.
Source-built local tags are not published multi-arch registry images and do
not have an invented distribution digest. Build natively on the target ARM64
host, then execute the smoke there; base manifests alone do not prove Python
wheels/CUDA drivers support that host. CPU packages are version-locked in
`requirements.lock.txt` in addition to the upstream frozen uv lock; PyAV 15.1.0
is deliberate (PyAV 19 broke faster-whisper's `metadata_errors` decode call).
APT repositories remain distribution-managed, so exact bit-reproducible image
bytes are not claimed.

## Intentionally not here

waxd/desktop capture, PipeWire/audio devices, microphone/GUI access, systemd
user units, personal voices, production transcription workers, private
credentials, Wax's ledger, a syncthing daemon, personal n8n workflows, an audio
pipeline consumer, paid provider routes, ingress, and a fake neural engine.
See `HOST-SIDE.md`, `DEFERRED.md`, `PROOF.md` and `smoke/`.

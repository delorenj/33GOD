# G6 deferred work and extraction contracts

These are gaps, not delivered services or inferred acceptance.

## Dev-journal n8n workflows (reserved `dev-journal` profile)

No personal/live n8n exports, broken workflow JSON or dummy n8n service ships.
The `x-dev-journal` Compose extension reserves the name; enabling the profile
adds zero services. Implement a fresh, sanitized workflow in G2 only after:

* Input schema is agreed: version 1 transport receipt with `id`, `sha256`,
  `file`, `bytes`, `state=landed`; `notified` is sender bookkeeping.
* An actual receiving URL and optional `X-API-Key` authentication are installed.
  G6 sends its JSON receipt and considers only HTTP 2xx successful.
* File transport is explicit. A basename in G6's private volume is not readable
  in G2. Choose an authorized object reference/download or explicit shared
  read-only mount; do not expose arbitrary host paths or imply bytes travel in
  the notification.
* Duplicate deliveries are idempotent by receipt id/hash. Retry and retention
  policy, STT invocation, journal ownership and failure paging are specified.
* Real speech traverses receipt → real workflow → actual persisted journal
  entry, with a correlated readback and rejected malformed/auth cases.
* Workflow-upgrade/re-import procedure is documented by the owning G2 artifact;
  updating a JSON file alone must never imply an already imported workflow
  changed. No importer or marked workflow volume exists in G6 today.

## Attach-mode external runtime

The G2/G3 overlay renders with zero published ports and only the intake service
joins external networks. No G2 audio receiver exists, so full receipt delivery
and G3 ntfy alert readback remain unproved. Do not count standalone receipt
logging or a rendered network list as downstream ingestion. Use an isolated
copy of the real receiver/ntfy to prove the seam before activating it; do not
mutate a production stack for a smoke.

## Remote S3 intake

Configuration variables are wired and local pickup/hash/atomic publish/error
handling are exercised. Real provider credentials, paginated remote polling,
ETag change handling and remote retry behavior have not been proved against an
actual provider. Remote mode is intentionally INERT with empty defaults.
No remote object is ever deleted. No Wax ledger or automatic transcription
consumer is shipped.

## GPU and ARM64

* The GPU image builds on amd64. Hidden-GPU startup with flag zero **and one**
  stays alive/degraded and returns 503 for synthesis. This is a real packaged
  engine boundary test, not neural inference success.
* GPU-positive model download, synthesis, driver pass-through, GPU OOM behavior
  and ARM64 GPU runtime remain deferred. A CUDA base ARM64 manifest does not
  establish compatible PyTorch/VoxCPM wheels or a Jetson-compatible driver stack.
* The upstream VoxCPM loader references its upstream model name without an
  immutable model snapshot pin. Pin/fetch/verify its full dependency-model set
  before treating GPU mode as a reproducible offline distribution.
* CPU ARM64 native build and real TTS/STT smoke are pending a target host. Both
  architecture manifests of every base image are recorded and verified, but
  that does not prove a source image or wheel set on ARM64.
* The 7.7 GiB target VM's complete G1–G4 + G6 coexistence peak is not measured.
  CPU G6 caps sum to 1856 MiB; the measured post-work snapshot is not peak RSS.

## Desktop / host package

waxd remains an existing host Debian package, graphical/PipeWire-coupled.
Host package installation, desktop capture, syncthing policy and ingress are
not part of the container proof. See `HOST-SIDE.md`.

## Review gate

Branch proof is the implementer's evidence. PM independently re-runs cold
smoke, upstream unit suites, config/manifest/secret checks and crib fidelity
before merge. No merge or deployment acceptance is claimed by this branch.

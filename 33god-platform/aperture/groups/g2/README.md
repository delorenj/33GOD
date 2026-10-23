# Aperture G2 — Integration Plane (v0.1)

Self-contained `god-g2`: **n8n + fresh Postgres + three fresh workflows + a
synthetic NATS outbox**. No G1 dependency and no published host ports.
**Folder-curator is explicitly deferred**, not implemented:
[curator/DEFERRED.md](curator/DEFERRED.md) records the host unit crib and rationale.

This is an internal-use deployment artifact, not approval for a paid n8n hosted
service. [The charter](../../CHARTER.md) remains binding. Nothing here is activated
on Damian's machine; Rererere owns that acceptance.

## Quick start (arm64 first; amd64 also supported)

Requires Docker Engine/Desktop with Compose v2+; host Python 3 for smoke. Native
linux/arm64 builds need no platform override on an Apple Silicon Docker VM.
Every external image's arm64 and amd64 manifest is verified in [PROOF.md](PROOF.md).
Only amd64 runtime execution was performed on this build host; arm64 runtime
acceptance remains with Rererere.

```bash
cd 33god-platform/aperture/groups/g2
cp .env.example .env                 # optional demo defaults, no real secrets
# Before real use set fresh DB password, encryption key, and demo header value.
docker compose config -q
docker compose up -d --build
docker compose ps -a
bash smoke/smoke.sh
```

Four long-running services become healthy; `n8n-import` exits 0. First boot runs:

```sh
n8n import:workflow --separate --input=/bundle/workflows
n8n update:workflow --id=apertureG2Smoke01 --active=true
```

The one-shot importer runs **before** n8n starts. A marker on the owned n8n
volume prevents subsequent `up` calls from overwriting operator-edited workflows.
Only the smoke workflow is activated. This is fresh-provisioned state; no host
DB, n8n home directory, credential database, workflow export or personal vault
is mounted. `GOD_*` configuration is listed in [.env.example](.env.example).
The demo password/token/key literals are deliberately non-production defaults.
Keep deployment values in ignored `.env` (or inject via your deployment manager),
not in workflow JSON. Keep the encryption key stable while retaining the DB.

### First owner login / access without port publication

Editor setup is deployment-owned; **no owner account is seeded**. Inspect readiness
without touching the host's n8n port:

```bash
docker compose exec n8n node -e "fetch('http://127.0.0.1:5678/healthz/readiness').then(r=>console.log(r.status))"
# Any HTTP request from inside the bundle network:
docker compose run --rm --no-deps smoke-client -fsS http://n8n:5678/healthz/readiness
```

On a Linux Docker host, obtain the private bridge IP and use an SSH tunnel from
your workstation (on the Docker HOST; these commands do not publish a port):

```bash
docker inspect -f '{{(index .NetworkSettings.Networks "g2-internal").IPAddress}}' "$(docker compose ps -q n8n)"
# workstation: replace <private-ip> and <docker-host>; choose an unused local port
ssh -N -L 15679:<private-ip>:5678 <docker-host>
# open http://localhost:15679 and create your own n8n owner
```

Docker Desktop bridge addresses are VM-private, not normally host-routable.
For Desktop use in-network `compose exec/run` for the proof; browser access needs
an explicit deployment-owned ingress/tunnel into that VM. This bundle does not
silently install one. Do not connect to or modify an existing host n8n instance.

## What the workflows do

All three JSON files are **authored from scratch**, inactive on disk, and contain
no credential bindings. No custom/community nodes are installed.

| Workflow | Activation | Behavior |
|---|---|---|
| `01-smoke.json` | importer activates | POST `/webhook/aperture-g2-smoke`, demo header check, UUIDv4 + `ping=true` validation, fresh CloudEvent, HTTP → local JetStream outbox, persistence ack response |
| `02-schedule-skeleton.json` | inactive | Daily Schedule Trigger → NoOp; no requests, dispatch or hidden scheduler |
| `03-plane-TEMPLATE-NOT-LIVE.json` | inactive, fail-closed | Shape only: webhook → validate → publish. Validation unconditionally errors until deployment-specific raw-body HMAC, webhook-id mapping and routing exist |

The Plane template is **not a working Plane adapter**. It includes no live URL,
secret lookup, project IDs, production topics or copied node implementation.
Its publication stub targets only the synthetic outbox, which refuses anything
but the G2 smoke CloudEvent. Do not activate it as an ingress boundary.

## KNOWN GAP — credential binding

n8n's first-boot workflow importer does **not** provision headerAuth credentials
from an environment variable. No credentials are imported here. The demo uses
`X-Aperture-Demo` via `GOD_DEMO_HEADER_TOKEN`: built-in Code checks the incoming
header, and HTTP Request adds that same environment value for the local outbox.
This requires `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`; it is a **demo env-pattern**,
not a portable credential-manager integration or Plane signature verification.
Only trusted local workflow authors should have access to this instance.

Proposed real binding: recipient creates a native Header Auth credential in
n8n, binds its deployment-local ID to the Webhook/HTTP Request nodes, removes
the demo Code/env auth path, and disables node env access. A future owned
bootstrap may create it through an authenticated deployment API using env input,
but must return only a binding ID and never export credentials. That automation
and real Plane HMAC are not implemented or proved in v0.1.

## Outbox and proof boundary

`nats-outbox-broker` is an owned, isolated JetStream server, not G1 or the host
Bloodbank. `nats-outbox` is a  stdlib HTTP→NATS adapter (not an n8n custom node).
It accepts only `bloodbank.evt.aperture.smoke.g2`, validates the CloudEvent and
waits for JetStream's persistence acknowledgment. `GET /latest` **queries the
NATS stream**; no HTTP cache stands in for bus evidence. Bounded retention:
100 events / 1 MiB / 24 hours. Requests are capped at 64 KiB.

The smoke runs curl inside `g2-internal`, rejects missing auth (401) and invalid
input (400), triggers the active webhook, then compares ID, correlation, subject,
data and persisted sequence from stream readback. It also asserts all service
health, exact activation states and zero host ports. No assertion is skipped.
There is no G1→Candystore delivery claim. Connecting to G1 requires a separately
reviewed network, authentication and transport contract; this demo adapter is
not a second production Bloodbank ingress.

## Resource envelope

| Service | Hard memory cap |
|---|---:|
| n8n (768 MiB JS old-space) | 1408 MiB |
| Postgres (96 MiB shared buffers; 30 connections) | 384 MiB |
| JetStream broker | 128 MiB |
| HTTP outbox | 96 MiB |
| Importer (exits before n8n starts) | 384 MiB |
| Curl proof client (on demand) | 64 MiB |

Steady-state caps total **2016 MiB**. Even summing every cap including the
non-overlapping importer and smoke yields **2464 MiB (<2.5 GiB)**; Docker VM
and filesystem-cache overhead still need headroom. This is a bounded small-demo
budget, not a throughput promise or permission to run arbitrary workflows under
it. Real curation/enrichment will require budget reallocation and measurements.

## Isolation / teardown

Project `god-g2`, bridge `g2-internal`, and volumes `god-g2-n8n-data`,
`god-g2-n8n-pgdata`, `god-g2-outbox-data` are all fresh and bundle-owned. No
external/adopted volumes, host home mounts, Docker socket or published ports.
Service `5678/tcp` in `compose ps` is image metadata, **not** a host port bind.

```bash
docker compose down                # preserves workflow DB + n8n key/state
# ONLY for the disposable proof / deliberate reset of THIS demo:
docker compose down -v             # deletes god-g2 data; never run on live stacks
```

Resetting only one DB/data volume can leave the importer marker out of sync;
for a **disposable** fresh demo, reset all `god-g2` volumes together. For retained
instances restore matching DB/n8n volume backups rather than removing the marker.
Do not rerun the raw import command on a running user-edited instance.

## Provenance / intentionally NOT here

- G1 Compose naming/isolation conventions adapted, not source-copy deployment.
- Host n8n's mise launch is read-only context; official image replaces it here.
- Plane webhook→validate→publish **shape only**, no production export touched.
- Curator unit ExecStart lines are the only verbatim crib; see the defer note.
- **No Jarad workflows (85), credentials (78), custom nodes, live Plane routes,
  production n8n DB, owner identity, real gateway URLs/keys, curation engine,
  curator-drain, pdf2md, LLM, G1 attachment, fleet, ingress or paid-service go.**
- Image tags are explicit version/channel pins, not immutable digests. Recheck
  manifests after overriding/updating them. n8n 1.120.4 emits a task-runner
  deprecation warning; updating it is a separate compatibility review, not a
  claim that this historical release is the latest or paid-hosting approved.

Independent PM review and arm64 real-deployment acceptance remain open.

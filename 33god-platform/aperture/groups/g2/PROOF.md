# G2 — executed proof (2026-10-23, build host)

Scope: branch `aperture/g2-bundle`, bundle directory
`33god-platform/aperture/groups/g2/`, Compose project **god-g2**. Docker
29.2.1, Compose v5.0.2, host runtime **linux/x86_64 (amd64)**. This is not
arm64 runtime acceptance; arm64 manifest availability is proved below.

No production n8n HTTP request, DB access, workflow/credential export, service
restart or host configuration change was performed. All DB queries below target
only `god-g2-n8n-postgres`. The production listener/process identity was observed
read-only before and after the proof.

## 1. Architecture checks — every external image

Command: `python3 smoke/manifests.py` (exit 0). It resolves Compose including
the tools profile and outbox Dockerfile base, runs `docker manifest inspect`
for each image, parses JSON `manifests[].platform`, requires BOTH targets,
and prints the exact per-platform manifest digest. Attestation entries with
`unknown/unknown` are not treated as architecture support. Local
`god-g2-outbox:0.1` builds from the verified Python base, pure stdlib source,
with no downloaded dependencies or architecture-specific binaries.

```text
$ docker manifest inspect curlimages/curl:8.12.1
exit=0 schemaVersion=2
linux/arm64 sha256:62dc7f48483d54c86914bf0aed8031bb07ac70eb4ef423b97e6af6592df163b5
linux/amd64 sha256:88a9abad9d958340e48564f9bdcdaa29916a2984be59314da709f8bbc0eef6f7
$ docker manifest inspect n8nio/n8n:1.120.4
exit=0 schemaVersion=2
linux/arm64 sha256:bc5e2503488c56027e4da815d98dc67b44227a1f6bfd6ea30d149dead0abd65e
linux/amd64 sha256:898053295b6fa2eee96dd4ed82ed7ea1fc7ba0beada336be14c3ca797c859a6e
$ docker manifest inspect nats:2.10-alpine
exit=0 schemaVersion=2
linux/arm64 sha256:e3998ee69d4f40928019753acacce3275c038d209748de6587f6a21de0667fa1
linux/amd64 sha256:7e2f895a12d5bc4586191452f5dd20968e8c800d53622073a2730c38d6b0eccb
$ docker manifest inspect postgres:16-alpine
exit=0 schemaVersion=2
linux/arm64 sha256:7a8050e52090c5f77effbe7e0cbed4a0587306776c3f26dc99933a63c619eaf1
linux/amd64 sha256:cbf42f0edc946c0bc1b8eeed62403734e1f25dc67a3491455d07a92fdb558b28
$ docker manifest inspect python:3.12-alpine
exit=0 schemaVersion=2
linux/arm64 sha256:57f679a3910bed1eb16ad722b904a118bca8586ec8ad39d98dd13350e7062cb2
linux/amd64 sha256:9b98a8d37794ca093ba8d5afe1ffac52f5a15168b9b4e67594d86c20e14fa681
MANIFEST RESULT: PASS — every external image has linux/arm64 and linux/amd64
```

## 2. Config and cold bring-up

`docker compose config -q` → exit 0, no output. Resolved project `god-g2`;
all six services (including importer and tools) have `ports: []` and only
`g2-internal`. No external/adopted volume or network; DB, n8n state and outbox
store are fresh `god-g2-*` volumes.

Final run started from **no G2 containers/volumes** (a previous disposable test
was fully removed). `docker compose up -d --build` → exit 0. Trimmed actual output:

```text
 Container god-g2-nats-outbox-broker-1 Created
 Container god-g2-nats-outbox-1 Creating
 Container god-g2-n8n-postgres-1 Created
 Container god-g2-n8n-import-1 Creating
 Container god-g2-nats-outbox-1 Created
 Container god-g2-n8n-import-1 Created
 Container god-g2-n8n-1 Creating
 Container god-g2-n8n-1 Created
 Container god-g2-nats-outbox-broker-1 Starting
 Container god-g2-n8n-postgres-1 Starting
 Container god-g2-nats-outbox-broker-1 Started
 Container god-g2-nats-outbox-broker-1 Waiting
 Container god-g2-n8n-postgres-1 Started
 Container god-g2-n8n-postgres-1 Waiting
 Container god-g2-nats-outbox-broker-1 Healthy
 Container god-g2-nats-outbox-1 Starting
 Container god-g2-n8n-postgres-1 Healthy
 Container god-g2-n8n-import-1 Starting
 Container god-g2-n8n-import-1 Started
 Container god-g2-nats-outbox-1 Started
 Container god-g2-nats-outbox-1 Waiting
 Container god-g2-n8n-import-1 Waiting
 Container god-g2-n8n-import-1 Exited
 Container god-g2-nats-outbox-1 Healthy
 Container god-g2-n8n-1 Starting
 Container god-g2-n8n-1 Started
```

`docker compose ps -a` → exit 0:

```text
NAME                          IMAGE                COMMAND                  SERVICE              CREATED          STATUS                      PORTS
god-g2-n8n-1                  n8nio/n8n:1.120.4    "tini -- /docker-ent…"   n8n                  20 seconds ago   Up 8 seconds (healthy)      5678/tcp
god-g2-n8n-import-1           n8nio/n8n:1.120.4    "/bin/sh /bundle/boo…"   n8n-import           20 seconds ago   Exited (0) 10 seconds ago
god-g2-n8n-postgres-1         postgres:16-alpine   "docker-entrypoint.s…"   n8n-postgres         20 seconds ago   Up 20 seconds (healthy)     5432/tcp
god-g2-nats-outbox-1          god-g2-outbox:0.1    "python -u /app/serv…"   nats-outbox          20 seconds ago   Up 14 seconds (healthy)
god-g2-nats-outbox-broker-1   nats:2.10-alpine     "docker-entrypoint.s…"   nats-outbox-broker   20 seconds ago   Up 20 seconds (healthy)     4222/tcp, 6222/tcp, 8222/tcp
```

The `5678/tcp`/`5432/tcp` entries are exposed image ports, not host bindings.
One-shot import uses `n8n import:workflow --separate --input=/bundle/workflows`.
The importer is complete before n8n starts. It imports three fresh workflows,
activates only the smoke one, then sets a persistent marker. A repeat `up -d
--build` was also exercised (exit 0) and logged:

```text
n8n-import-1  | G2 fresh workflows imported; smoke only active, templates inactive
n8n-import-1  | G2 workflows already imported; skipping (no workflow overwrites)
n8n-import-1  | G2 workflows already imported; skipping (no workflow overwrites)
```

First boot emitted n8n's “Could not find workflow / Could not remove webhooks”
messages for the fresh fixed IDs; the same command then reported
`Successfully imported 3 workflows`, exited 0, and activation states were
checked directly in the owned DB by smoke. These are not hidden import failures.
n8n 1.120.4 also warns that disabled task runners are deprecated and the release
is older than six weeks. This bundle makes no latest-version/support claim.

## 3. Smoke — real webhook to retained NATS message

`bash smoke/smoke.sh` → exit 0 (final cold run):

```text
PASS: god-g2 only, zero published ports, 4 services healthy, import exit 0
PASS: only smoke active; Plane TEMPLATE-NOT-LIVE and schedule inactive
PASS: fresh n8n database has zero credential records
PASS: missing demo header rejected (401)
PASS: malformed synthetic input rejected (400)
PASS: in-network curl → n8n → JetStream persistence ack: {"published": true, "id": "ce3a7c66-76e9-49a7-a033-eabef36251fa", "subject": "bloodbank.evt.aperture.smoke.g2", "stream": "G2_SMOKE", "sequence": 1}
PASS: NATS stream GET (not HTTP cache) CloudEvent fidelity: {"specversion": "1.0", "id": "ce3a7c66-76e9-49a7-a033-eabef36251fa", "source": "urn:33god:aperture:g2", "type": "bloodbank.evt.aperture.smoke.g2", "subject": "bloodbank.evt.aperture.smoke.g2", "time": "2026-10-23T18:57:53.041Z", "datacontenttype": "application/json", "correlationid": "ce3a7c66-76e9-49a7-a033-eabef36251fa", "producer": "aperture-g2-n8n", "data": {"ping": true, "via": "n8n-webhook"}}
SMOKE RESULT: PASS — webhook → validate → CloudEvent → NATS JetStream → readback
```

The HTTP response follows a **JetStream persistence acknowledgment**; `/latest`
issues `$JS.API.STREAM.MSG.GET.G2_SMOKE`, decodes the stored message and returns
the NATS sequence. No HTTP-memory cache is used as the event proof.

Additional run: `docker compose restart nats-outbox` (exit 0) followed by smoke
(exit 0) retained the stream and advanced its sequence to 2:

```text
PASS: god-g2 only, zero published ports, 4 services healthy, import exit 0
PASS: only smoke active; Plane TEMPLATE-NOT-LIVE and schedule inactive
PASS: missing demo header rejected (401)
PASS: malformed synthetic input rejected (400)
PASS: in-network curl → n8n → JetStream persistence ack: {"published": true, "id": "078c496d-811f-4bec-ab34-20439f2ea2eb", "subject": "bloodbank.evt.aperture.smoke.g2", "stream": "G2_SMOKE", "sequence": 2}
PASS: NATS stream GET (not HTTP cache) CloudEvent fidelity: {"specversion": "1.0", "id": "078c496d-811f-4bec-ab34-20439f2ea2eb", "source": "urn:33god:aperture:g2", "type": "bloodbank.evt.aperture.smoke.g2", "subject": "bloodbank.evt.aperture.smoke.g2", "time": "2026-10-23T18:56:11.265Z", "datacontenttype": "application/json", "correlationid": "078c496d-811f-4bec-ab34-20439f2ea2eb", "producer": "aperture-g2-n8n", "data": {"ping": true, "via": "n8n-webhook"}}
SMOKE RESULT: PASS — webhook → validate → CloudEvent → NATS JetStream → readback
```

G1 was not required or attached. No NATS assertion was skipped. This does **not**
prove G1/Candystore integration, real Plane HMAC, production credential binding,
curator execution or a Damian deployment.

## 4. Unit / resource / static evidence

`python3 -m unittest discover -s outbox -v` → exit 0:

```text
test_bad_uuid_time_data (test_server.Tests.test_bad_uuid_time_data) ... ok
test_disconnect_does_not_ack (test_server.Tests.test_disconnect_does_not_ack) ... ok
test_jetstream_error_propagates (test_server.Tests.test_jetstream_error_propagates) ... ok
test_nats_ping_and_ack (test_server.Tests.test_nats_ping_and_ack) ... ok
test_no_other_subjects (test_server.Tests.test_no_other_subjects) ... ok
test_required_fields (test_server.Tests.test_required_fields) ... ok
test_truncated_message_does_not_ack (test_server.Tests.test_truncated_message_does_not_ack) ... ok
test_valid_cloud_event (test_server.Tests.test_valid_cloud_event) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.001s

OK
```

Tests cover allowed envelope, wrong fixed subject/source/version/content type,
missing fields, malformed UUID/time/data, NATS PING, persistence ack decoding,
JetStream errors, disconnect and truncated message rejection.

`docker stats --no-stream ...` immediately after final smoke:

```text
god-g2-n8n-1 331MiB / 1.375GiB
god-g2-n8n-postgres-1 29.6MiB / 384MiB
god-g2-nats-outbox-1 11.99MiB / 96MiB
god-g2-nats-outbox-broker-1 4.379MiB / 128MiB
```

Configured caps: n8n 1408 MiB + Postgres 384 + NATS 128 + outbox 96 =
**2016 MiB steady state**. All caps including the 384 MiB importer and
64 MiB smoke client sum to **2464 MiB (<2560 MiB)**; importer finishes before
n8n starts. VM/Docker overhead is separate; no load/throughput claim.

`git diff --check` → exit 0. JSON and Python syntax checks passed on file writes.
`python3 scripts/platform.py validate` in canonical `33god-platform` → exit 0,
`33GOD platform manifest OK`. The same gate from the isolated worktree exits 1
because component submodules/sibling repos are not populated there (missing
Bloodbank/Candystore/Holocene Compose and Skillex/HeyMa paths); no deployment or
component modification was performed to make it pass. The G2 bundle itself
has no submodule dependency and its config/build/smoke passed in the worktree.

## 5. Teardown and production isolation

`docker compose down -v` → exit 0 (ONLY disposable god-g2 data):

```text
 Container god-g2-nats-outbox-broker-1 Stopping
 Container god-g2-nats-outbox-broker-1 Stopped
 Container god-g2-nats-outbox-broker-1 Removing
 Container god-g2-nats-outbox-broker-1 Removed
 Volume god-g2-n8n-data Removing
 Volume god-g2-n8n-pgdata Removing
 Volume god-g2-outbox-data Removing
 Network g2-internal Removing
 Volume god-g2-n8n-pgdata Removed
 Volume god-g2-n8n-data Removed
 Volume god-g2-outbox-data Removed
 Network g2-internal Removed
```

```text
$ docker compose ps -a
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
$ docker ps -a --filter label=com.docker.compose.project=god-g2 --format '{{.Names}}'
(no output, exit 0)
$ docker volume ls --format '{{.Name}}' --filter name=god-g2-
(no output, exit 0)
$ docker network ls --format '{{.Name}}' --filter name=^g2-internal$
(no output, exit 0)
```

Before and after: production n8n listener PID 7061, same start time and binary.
After teardown:

```text
State  Recv-Q Send-Q Local Address:Port Peer Address:PortProcess
LISTEN 0      511          0.0.0.0:5678      0.0.0.0:*    users:(("node /home/delo",pid=7061,fd=25))
    PID                  STARTED COMMAND
   7061 Wed Oct 21 21:14:47 2026 node /home/delorenj/.local/share/mise/installs/node/24.6.0/bin/n8n
```

The production DB/credentials were deliberately not inspected or hashed; the
claim is isolated commands/mounts and unchanged observed listener/process,
not a fabricated byte-for-byte production database comparison.

## Deviations / remaining gates

- **Curator deferred** with actual host unit crib and extraction rationale in
  `curator/DEFERRED.md`. No fake curator container or curation proof.
- Built-in n8n HTTP Request + demo-only stdlib NATS outbox replaces credentialed
  NATS custom-node publication; only the fixed synthetic subject is supported.
- Native credential provisioning and Plane verification are explicitly **KNOWN
  GAP** / **TEMPLATE-NOT-LIVE**, not working production integrations.
- All five external tags support arm64 and amd64; arm64 runtime proof remains
  Rererere's deployment acceptance. This worker touched no Damian environment.
- Parent PM independent review is pending (`REVIEW-PENDING.md`). No merge or
  paid-service/licensing authorization is implied by these executed checks.

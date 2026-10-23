# PROOF — Aperture G3 (Agent Fleet Runtime) v0.1

Host: this build machine (amd64), 2026-10-23. All outputs below are real,
captured during this build session. arm64 is manifest-verified per image;
arm64 runtime acceptance remains a separate deployment gate (see Deviations).

## 1. Config validation

```text
$ cd 33god-platform/aperture/groups/g3 && docker compose config -q
(exit 0, no output)

$ docker compose --profile tools config --format json   # service/image/ports check
heartbeat-tick   image god-g3-heartbeat-tick:0.1        ports null
hermes-agent     image god-g3-hermes-agent:0.1          ports null
lifecycle-controller image god-g3-lifecycle-controller:0.1 ports null
nats             image nats:2.10-alpine                 ports null
ntfy             image binwiederhier/ntfy:v2.33.1       ports null
outbox           image god-g3-outbox:0.1                ports null
smoke-client     image curlimages/curl:8.12.1           ports null
```

Project `god-g3`; zero published host ports across all services and profiles.

## 2. External-image manifest verification (arm64 + amd64)

`python3 smoke/manifests.py` enumerates every external image from the resolved
Compose config (pull images AND every build's `GOD_PYTHON_IMAGE` base) and
parses `manifests[].platform` from each index:

```text
$ python3 smoke/manifests.py
$ docker manifest inspect binwiederhier/ntfy:v2.33.1
exit=0 schemaVersion=2
linux/arm64 sha256:b130a150467e21b77e9126968070940f073026384c27be43207069d133d273fd
linux/amd64 sha256:29fc7c847129a36717e46d322cb7897ffaed9a72ff3f40820795df10aa921671
$ docker manifest inspect curlimages/curl:8.12.1
exit=0 schemaVersion=2
linux/arm64 sha256:62dc7f48483d54c86914bf0aed8031bb07ac70eb4ef423b97e6af6592df163b5
linux/amd64 sha256:88a9abad9d958340e48564f9bdcdaa29916a2984be59314da709f8bbc0eef6f7
$ docker manifest inspect nats:2.10-alpine
exit=0 schemaVersion=2
linux/arm64 sha256:e3998ee69d4f40928019753acacce3275c038d209748de6587f6a21de0667fa1
linux/amd64 sha256:7e2f895a12d5bc4586191452f5dd20968e8c800d53622073a2730c38d6b0eccb
$ docker manifest inspect python:3.12-alpine
exit=0 schemaVersion=2
linux/arm64 sha256:57f679a3910bed1eb16ad722b904a118bca8586ec8ad39d98dd13350e7062cb2
linux/amd64 sha256:9b98a8d37794ca093ba8d5afe1ffac52f5a15168b9b4e67594d86c20e14fa681
$ docker manifest inspect python:3.12-slim
exit=0 schemaVersion=2
linux/arm64 sha256:6c6ae3622772575c3ac02ecb2b02a06d05f19e1713a0cbff476ef37bca79e90f
linux/amd64 sha256:e8a38829209aea82774882e5157e1f7c3e8c8393ff53a697b3580896e57f345c
MANIFEST RESULT: PASS — every external image has linux/arm64 and linux/amd64
```

## 3. Cold start + health

After `docker compose down -v --remove-orphans` (fresh volumes, fresh network):

```text
$ docker compose --profile upstream --profile tools build   # all 5 local images
Image god-g3-heartbeat-tick:0.1 Built
Image god-g3-hermes-agent:0.1 Built
Image god-g3-lifecycle-controller:0.1 Built
Image god-g3-ntfy-upstream-gate:0.1 Built
Image god-g3-outbox:0.1 Built

$ docker compose up -d
Container god-g3-nats-1 Healthy
Container god-g3-hermes-agent-1 Started
Container god-g3-heartbeat-tick-1 Started
Container god-g3-outbox-1 Started
Container god-g3-lifecycle-controller-1 Started

$ docker compose ps -a
NAME                            IMAGE                             COMMAND                  SERVICE                CREATED          STATUS                    PORTS
god-g3-heartbeat-tick-1         god-g3-heartbeat-tick:0.1         "python -u /app/main…"   heartbeat-tick         23 seconds ago   Up 17 seconds (healthy)
god-g3-hermes-agent-1           god-g3-hermes-agent:0.1           "python -u /opt/herm…"   hermes-agent           23 seconds ago   Up 17 seconds (healthy)
god-g3-lifecycle-controller-1   god-g3-lifecycle-controller:0.1   "python -u -m lifecy…"   lifecycle-controller   23 seconds ago   Up 17 seconds (healthy)
god-g3-nats-1                   nats:2.10-alpine                  "docker-entrypoint.s…"   nats                   23 seconds ago   Up 23 seconds (healthy)   4222/tcp, 6222/tcp, 8222/tcp
god-g3-ntfy-1                   binwiederhier/ntfy:v2.33.1        "ntfy serve"             ntfy                   23 seconds ago   Up 23 seconds (healthy)   80/tcp
god-g3-outbox-1                 god-g3-outbox:0.1                 "python -u /app/serv…"   outbox                 23 seconds ago   Up 17 seconds (healthy)
```

All six core services healthy on a cold start; PORTS column shows only
in-network exposure, no host bindings.

### D2 evidence — the container really is hermes-agent + vendored plugin

From `docker compose logs hermes-agent` (the container's own stdout):

```text
INFO g3-hermes-agent stack: hermes-agent = 0.19.0
INFO g3-hermes-agent stack: bloodbank_hermes_gateway = imports (adapter + contract)
INFO g3-hermes-agent stack: hermes_agent.plugins entry points = ['bloodbank-platform']
INFO g3-hermes-agent heartbeat task published: type=bloodbank.agent.invocation.started subject=bloodbank.evt.agent.invocation.started seq=3 id=f37226f5-84ae-52d5-ad61-6e0218380ee3 tick=0
INFO g3-hermes-agent heartbeat task published: type=bloodbank.agent.invocation.started subject=bloodbank.evt.agent.invocation.started seq=5 id=01ac32eb-d630-57a0-962a-f5e13e508bd3 tick=1
INFO g3-hermes-agent heartbeat task published: type=bloodbank.agent.invocation.started subject=bloodbank.evt.agent.invocation.started seq=8 id=4c5910fb-59af-52c3-a752-eb62ce2cc78d tick=2
...
```

`hermes-agent` 0.19.0 installed from PyPI inside the image; the vendored
Bloodbank plugin imports against Hermes' own `gateway`/`hermes_cli` modules and
its `hermes_agent.plugins` entry point resolves to `bloodbank-platform`;
synthetic invocation events publish with real JetStream sequence numbers.

## 4. Smoke

`bash smoke/smoke.sh` (runs `smoke/check.py` from inside the bundle; assertions
in the script, human-readable output here):

```text
$ bash smoke/smoke.sh
PASS: god-g3 only, zero published ports, 6 services healthy
PASS: hermes-agent stack verified (hermes-agent + vendored bloodbank-platform plugin)
PASS: heartbeat path fires (seq=10, tick_seq=5)
PASS: synthetic task envelope transitioned (none -> active, reason=PROGRESSING)
PASS: agent heartbeat task published invocation.started (seq=11, producer=hermes-agent:g3-demo)
PASS: missing demo header rejected (401)
PASS: malformed synthetic input rejected (400)
PASS: in-network curl -> outbox -> JetStream persistence ack: {"published": true, "id": "39ad9089-1237-4f4e-bb02-fadab73d5892", "subject": "bloodbank.evt.aperture.smoke.g3", "stream": "G3_EVENTS", "sequence": 13}
PASS: NATS stream GET (not HTTP cache) CloudEvent fidelity: {"specversion": "1.0", "id": "39ad9089-1237-4f4e-bb02-fadab73d5892", "source": "urn:33god:aperture:g3", "type": "bloodbank.evt.aperture.smoke.g3", "subject": "bloodbank.evt.aperture.smoke.g3", "time": "2026-10-23T20:31:24Z", "datacontenttype": "application/json", "correlationid": "39ad9089-1237-4f4e-bb02-fadab73d5892", "producer": "aperture-g3-smoke", "data": {"ping": true, "via": "g3-outbox"}}
SMOKE RESULT: PASS — heartbeat fires + lifecycle transition + agent publish + CloudEvent persistence ack + retained readback
```

Every readback is correlated: same `id` on publish and read, same `subject`,
same stream `sequence` — proven from the NATS stream via the outbox's
`GET /latest`, not an HTTP cache.

### JetStream stream state (broker's own monitoring endpoint)

```text
$ docker compose run --rm --no-deps -T smoke-client -s "http://nats:8222/jsz?streams=true"
"streams": 1, "messages": 36
stream_detail: name "G3_EVENTS"  state: first_seq 1, last_seq 36, num_subjects 4
```

Four subjects retained: heartbeat, lifecycle, agent invocation, smoke.

### Optional upstream profile

```text
$ docker compose --profile upstream up -d ntfy-upstream-gate
ntfy-upstream-gate:running:healthy
WARNING ntfy-upstream-gate no upstream configured (GOD_NTFY_UPSTREAM_URL/TOPIC); gate is inert
```

Healthy by design and inert without deployment-owned upstream credentials —
an honest default, not a fake forwarder.

## 5. Teardown and isolation

```text
$ docker compose --profile upstream --profile tools down -v --remove-orphans
Network g3-internal Removed
Volume god-g3-nats-data Removed
Volume god-g3-ntfy-cache Removed
Volume god-g3-ntfy-data Removed

$ docker compose ps -a
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
(no rows)

containers-left: 0
volumes-left: 0
networks-left: 0
```

Production untouched: the G3 bus is a fresh `god-g3`-owned NATS (not the host
Bloodbank, not G1), ntfy is fresh, and no host mounts, Docker socket, adopted
volumes, or host ports were used anywhere. Nothing activated on any other
environment.

## 6. Secrets / AAI scan

```text
$ grep -rE 'op://|sk-[A-Za-z0-9]|Bearer [A-Za-z0-9._-]{8,}|/home/delorenj|delo\.sh|api\.automaticai|xoxb-|ghp_' \
    --exclude-dir=.git .
(no matches)
```

Zero credential strings, personal paths, personal hostnames, or gateway
endpoints. `GOD_AAI_BASE_URL` exists in `.env.example` with an empty default
(spec D1 parity); it is unused by any G3 service. The only "automaticai"
occurrences left in-tree are inside the vendored plugin's docstring example
(`hermes/vendor/.../contract.py`, verbatim bloodbank crib) and DEFERRED.md /
README prose *explaining the exclusion* — no endpoint, account, or routing
content ships.

## Deviations / remaining gates

- **hook-hub + agent-hooks deferred** with full extraction contracts
  (`hook-hub/DEFERRED.md`, `agent-hooks/DEFERRED.md`) — host agent-CLI,
  Hindsight, and AAI-routing bound; G3 ships their event-publication layer
  (the shared stdlib NATS publisher), not a fake daemon.
- **D3 bounded honestly:** no Telegram/webhook ingress; the container proves
  heartbeat → task → CloudEvent publish → correlated readback. Interactive
  ingress is G4.
- **D5 attach not wired:** `GOD_G1_BUS_ATTACH` is documented (README) but not
  exercised; joining G1's bus is a separately reviewed coupling.
- **arm64 runtime:** all external images are arm64-manifest-verified, but only
  amd64 runtime execution was performed on this build host. Real arm64
  acceptance (Rererere's hardware) remains open.
- **Lifecycle persistence:** the reconciler crib is the pure in-memory state
  machine over a synthetic envelope; Postgres persistence (asyncpg), structlog,
  and the krebs-execution worker are out of scope here.
- Parent PM review pending; no merge performed.

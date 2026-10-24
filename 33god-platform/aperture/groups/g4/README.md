# Aperture G4 — Observability (v0.1)

Self-contained `god-g4`: a portable observability bundle — **Prometheus**,
**Grafana**, **Alertmanager**, **node-exporter**, **cadvisor**, and a
stdlib-Python **alert-bridge** (Alertmanager webhook → ntfy). Opt-in `logs`
profile (**loki + alloy**) and `otel` profile (**otel-collector**). No external
dependency, **zero published host ports**, **no operator-gateway content**, no
secrets. Runs beside (never against) the live production monitoring stack.

This is an internal-use deployment artifact. [The charter](../../CHARTER.md)
remains binding.

## Quick start (arm64 first; amd64 also supported)

Requires Docker Engine/Desktop with Compose v2+ and BuildKit; host Python 3 for
the smoke. Every external image's arm64 and amd64 manifest is verified in
[PROOF.md](PROOF.md). Only amd64 runtime execution was performed on this build
host; arm64 runtime acceptance remains a separate deployment gate.

```bash
cd 33god-platform/aperture/groups/g4
cp .env.example .env                 # optional demo defaults, no real secrets
docker compose config -q
docker compose up -d --build         # builds 2 local images + pulls 5 external
docker compose ps -a
bash smoke/smoke.sh                  # full data-path proof (exits non-zero on failure)
```

Seven long-running core services become healthy (prometheus, grafana,
alertmanager, node-exporter, cadvisor, alert-bridge, canary). The canary is a
smoke fixture (a real scrape target the smoke pauses to prove the alert path),
not an observability component. `GOD_*` configuration is listed in
[.env.example](.env.example).

## Profiles (opt-in; default `up` = core only)

| Profile | Services | Purpose |
|---|---|---|
| (default) | prometheus, grafana, alertmanager, node-exporter, cadvisor, alert-bridge, canary | metrics + alerting |
| `logs` | + loki, alloy | container-log aggregation, scoped to `compose_project == "god-g4"` |
| `otel` | + otel-collector | OTLP ingress (grpc 4317 / http 4318) + prometheus self-expose (8889) |
| `tools` | + smoke-client | in-network curl the smoke uses |

```bash
docker compose --profile logs up -d
docker compose --profile otel up -d
```

## arm64 / amd64 manifest table

Every external image is pinned and its `linux/arm64` **and** `linux/amd64`
manifest verified (full digests + command in [PROOF.md §2](PROOF.md)). Local
images (`god-g4-alert-bridge`, `god-g4-canary`) build from `python:3.12-alpine`.

| Image | arm64 digest | amd64 digest |
|---|---|---|
| prom/prometheus:v2.53.1 | `sha256:eb9653beb0…df3cf0` | `sha256:e815f1c12a…d941ec` |
| grafana/grafana:11.1.4 | `sha256:5ae306d63a…c099c8` | `sha256:b71d75d22f…73364b62` |
| prom/alertmanager:v0.27.0 | `sha256:2fbdd4c66d…237a84fb` | `sha256:45c3a586d4…c40ca5f` |
| prom/node-exporter:v1.8.2 | `sha256:1eabab826c…edea74004` | `sha256:065914c033…8f5a9396` |
| gcr.io/cadvisor/cadvisor:v0.49.1 | `sha256:735714451f…dfc1fcdf` | `sha256:524779a266…1fd229461` |
| grafana/loki:3.1.1 (`logs`) | `sha256:e5a11aa539…a459437849` | `sha256:609c03d2e9…caaf60b135` |
| grafana/alloy:v1.3.1 (`logs`) | `sha256:83e18d00ae…098dacdf8` | `sha256:2381097248…09acd2dbaf` |
| otel/opentelemetry-collector-contrib:0.105.0 (`otel`) | `sha256:aa7d5ef71d…e33fb599f` | `sha256:1888ac50a4…4d08f9f0817` |
| python:3.12-alpine (build base) | `sha256:57f679a391…7062cb2` | `sha256:9b98a8d377…c20e14fa681` |
| curlimages/curl:8.12.1 (`tools`) | `sha256:62dc7f4848…df163b5` | `sha256:88a9abad9d…0eef6f7` |

## Resource envelope (measured on this host, steady-state)

| Service | Hard cap (`mem_limit`) | Measured steady-state |
|---|---:|---:|
| prometheus | 300 MiB | ~71 MiB |
| grafana | 220 MiB | ~53 MiB |
| cadvisor | 256 MiB | ~35 MiB |
| node-exporter | 64 MiB | ~11 MiB |
| alertmanager | 48 MiB | ~18 MiB |
| alert-bridge | 48 MiB | ~13 MiB |
| canary | 32 MiB | ~11 MiB |
| **core total** | **968 MiB** | **~212 MiB** |
| loki (`logs`) | 256 MiB | — |
| alloy (`logs`) | 128 MiB | — |
| otel-collector (`otel`) | 256 MiB | — |
| smoke-client (`tools`) | 64 MiB | — |

Core steady-state is well under the 1.2 GiB budget (measured ~212 MiB; hard
caps total 968 MiB). These are bounded small-demo budgets, not throughput
promises.

## Attaching to G3's ntfy (phone paging)

Standalone mode keeps `GOD_NTFY_URL` empty: the alert-bridge formats every
alert and logs it visibly but delivers nowhere (it must never be a single
point of failure). To page a phone, run the attach overlay, which joins the
bundle's alert-bridge to G3's existing `g3-internal` network (where G3's ntfy
listens as `ntfy`) and points `GOD_NTFY_URL` at `http://ntfy:80`:

```bash
docker compose -f compose.yml -f compose.attach.yml up -d
# requires G3 running and, in .env:
#   GOD_G3_NETWORK=g3-internal   (G3's bridge name)
#   GOD_NTFY_URL=http://ntfy:80
#   GOD_NTFY_TOPIC=aperture-g4-alerts
```

Attachment is an explicit, separately reviewed choice; standalone mode is what
the proof exercises. Both Compose variants pass `config -q`.

## The alert path

Prometheus loads `prometheus/rules/alerts.yml` (InstanceDown = `up == 0` for
30s; ContainerGone = the canary's liveness beacon absent for 30s) and sends to
Alertmanager, which routes every alert to the alert-bridge webhook with
`send_resolved: true`. The bridge formats one human line per alert
(`<emoji> <alertname> [<status>] <summary> (<instance>)`) and POSTs to ntfy.
See [PROOF.md §4](PROOF.md) for why ContainerGone uses the canary beacon rather
than a cadvisor signal.

## Isolation / teardown

Project `god-g4`, bridge `g4-internal`, volumes `god-g4-{prometheus,grafana,
alertmanager,loki,alloy}-data` — all fresh and bundle-owned. cadvisor mounts
`/var/run/docker.sock:ro` and `/:/ro` (standard cadvisor pattern, read-only);
node-exporter mounts host `/proc`, `/sys`, `/` read-only (reporting on the host
by definition). No external/adopted volumes, home mounts, or published ports.

```bash
docker compose down                # preserves metric/log state
docker compose down -v             # deletes god-g4 data (cold cycle, disposable)
```

## Provenance / intentionally NOT here

- **cadvisor stop-detection** and **otel→loki log export** are deferred with
  crib + extraction contracts ([DEFERRED.md](DEFERRED.md)).
- **No published host ports** — every service is reachable only on the internal
  `g4-internal` bridge; Grafana/Prometheus/Alertmanager are in-network only.
- **No operator gateway** — no gateway endpoint, account, metered tier, or
  model routing anywhere in the bundle (secrets/gateway scan in PROOF.md §6).
- **No Telegram/Discord receivers or tokens** — the only delivery target is the
  in-bundle alert-bridge → ntfy (empty URL in standalone mode).
- Image tags are explicit version/channel pins, not immutable digests. Recheck
  manifests after overriding them.

Independent PM review and arm64 real-deployment acceptance remain open.

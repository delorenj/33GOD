# PROOF — Aperture G4 (Observability) v0.1

Host: this build machine (amd64), 2026-10-24. All outputs below are real,
captured during this build session. arm64 is manifest-verified per image; arm64
runtime acceptance remains a separate deployment gate (see Deviations).

## 1. Config validation (standalone + attach + profiles)

```text
$ cd 33god-platform/aperture/groups/g4 && docker compose config -q
(exit 0, no output)

$ docker compose -f compose.yml -f compose.attach.yml config -q
(exit 0, no output)

$ docker compose --profile logs --profile otel --profile tools config -q
(exit 0, no output)
```

Project `god-g4`, network `g4-internal`, bundle-owned volumes. The attach
overlay joins the external `g3-internal` network and retargets the
alert-bridge's `GOD_NTFY_URL` to `http://ntfy:80`.

## 2. Zero published host ports

Resolved config (both standalone and attach variants) carries no `ports` block
on any service — every listener is in-network only:

```text
standalone resolved config -> published ports: NONE
attach      resolved config -> published ports: NONE
```

`docker compose ps` confirms the same at runtime: the PORTS column shows only
in-network exposure (`8789/tcp`, `9090/tcp`, `9093/tcp`, `9100/tcp`, `8080/tcp`,
`3000/tcp`, `8791/tcp`) with no `0.0.0.0:PORT->PORT` host bindings.

## 3. External-image manifest verification (arm64 + amd64)

`python3 smoke/manifests.py` enumerates every external image from the resolved
Compose config (across all profiles) and parses `manifests[].platform`:

```text
$ python3 smoke/manifests.py
$ docker manifest inspect prom/prometheus:v2.53.1
linux/arm64 sha256:eb9653beb04cb5143fd8c76aba7dcf3f3fd59bbcc183c6f385b1e77214df3cf0
linux/amd64 sha256:e815f1c12acfcbbcc57a27248db91d3e22d9ec33347ba292e8e5a19151d941ec
$ docker manifest inspect grafana/grafana:11.1.4
linux/arm64 sha256:5ae306d63a2238c6ce2efd06fcd5760fcf22248e350e8b5f1b757a07a5c099c8
linux/amd64 sha256:b71d75d22fbd3b15eecee7bad2f2bb6bea909dfcfbb41baf02c2a5dc73364b62
$ docker manifest inspect prom/alertmanager:v0.27.0
linux/arm64 sha256:2fbdd4c66d91e740fe3fd462d8f52fc3d305a5b403bab3a58feb62be237a84fb
linux/amd64 sha256:45c3a586d4332d710bef92b06e90380c0b1f588968c00100d4b5e4e44c40ca5f
$ docker manifest inspect prom/node-exporter:v1.8.2
linux/arm64 sha256:1eabab826c9d9f0c534e4e8fa745445f743fef9aee276d561d12811edea74004
linux/amd64 sha256:065914c03336590ebed517e7df38520f0efb44465fde4123c3f6b7328f5a9396
$ docker manifest inspect gcr.io/cadvisor/cadvisor:v0.49.1
linux/arm64 sha256:735714451fd7b9469d5eabac22af1006b49eb284fe186f4c3fa302a3dfc1fcdf
linux/amd64 sha256:524779a2661c9ea1b4b87d47fedfc56c3aed182511fcdac031f345a1fd229461
$ docker manifest inspect grafana/loki:3.1.1
linux/arm64 sha256:e5a11aa5396a4dc34dfd3c6ca4fc81a9c15ffcd246444e4015b775a459437849
linux/amd64 sha256:609c03d2e9becb0bb6b5f4f7e88d05e38321520c23e02e8b00c1caaf60b13523
$ docker manifest inspect grafana/alloy:v1.3.1
linux/arm64 sha256:83e18d00ae365ad10378ba1e923b1a785ca1dcb4d3aa42349b23cba098dacdf8
linux/amd64 sha256:2381097248235e37c34a727103cf9ad0e11767defdab6f37646cff09acd2dbaf
$ docker manifest inspect otel/opentelemetry-collector-contrib:0.105.0
linux/arm64 sha256:aa7d5ef71d04bfced8650fe976b4aa61f8cceeb33e6f56f5fc963a3e33fb599f
linux/amd64 sha256:1888ac50a4e773cf0e4bf53e80cfb25fa009c786e822435f8510f4d08f9f0817
$ docker manifest inspect python:3.12-alpine
linux/arm64 sha256:57f679a3910bed1eb16ad722b904a118bca8586ec8ad39d98dd13350e7062cb2
linux/amd64 sha256:9b98a8d37794ca093ba8d5afe1ffac52f5a15168b9b4e67594d86c20e14fa681
$ docker manifest inspect curlimages/curl:8.12.1
linux/arm64 sha256:62dc7f48483d54c86914bf0aed8031bb07ac70eb4ef423b97e6af6592df163b5
linux/amd64 sha256:88a9abad9d958340e48564f9bdcdaa29916a2984be59314da709f8bbc0eef6f7
MANIFEST RESULT: PASS — every external image has linux/arm64 and linux/amd64
```

## 4. Cold cycle + smoke (the full data path)

Cold start after `docker compose down -v --remove-orphans` (fresh volumes,
fresh network), then `docker compose up -d --build`:

```text
$ docker compose up -d --build
(builds god-g4-alert-bridge:0.1 and god-g4-canary:0.1; starts 7 core services)

$ docker compose ps -a
alert-bridge    running  healthy
alertmanager    running  healthy
cadvisor        running  healthy
canary          running  healthy
grafana         running  healthy
node-exporter   running  healthy
prometheus      running  healthy
```

`bash smoke/smoke.sh` (assertions in `smoke/check.py`; exits non-zero on any
failure):

```text
$ bash smoke/smoke.sh
PASS: god-g4 only, zero published host ports
PASS: 7 core services healthy
PASS: up{job="prometheus"} == 1
PASS: up{job="node-exporter"} == 1
PASS: up{job="cadvisor"} == 1
PASS: up{job="canary"} == 1
PASS: InstanceDown FIRING after canary paused
PASS: ContainerGone FIRING after canary paused
PASS: alert-bridge logged the formatted firing lines (webhook received)
PASS: alerts left FIRING state after canary returned
PASS: alert-bridge logged the resolved lines (webhook received)
PASS: grafana /api/health ok
PASS: grafana datasource proxy -> prometheus query succeeded
SMOKE RESULT: PASS — self+exporter scrape up, canary kill->firing->resolve, alert-bridge webhook received, grafana datasource healthy, zero published ports
```

The alert-bridge's own log carries the formatted lines — the delivery evidence
(GOD_NTFY_URL is empty in standalone mode, so the bridge logs the line and
visibly refuses delivery rather than silently dropping):

```text
🔥 InstanceDown  [firing]   Instance canary:8791 is down (canary:8791)
🔥 ContainerGone [firing]   Canary container god-g4-canary-1 is gone
✅ ContainerGone [resolved] Canary container god-g4-canary-1 is gone
✅ InstanceDown  [resolved] Instance canary:8791 is down (canary:8791)
WARNING alert-bridge no ntfy URL configured (GOD_NTFY_URL empty); not delivering: …
```

### Why the smoke pauses (not stops) the canary, and why ContainerGone uses the canary

Two honest findings from building this on a live host, both documented here so
the PM review does not trip on them:

1. **This host runs a production auto-restart monitor** that restarts any
   *exited* container. A `docker compose stop canary` is undone mid-test before
   the 30s `for:` window elapses. The smoke **pauses** the canary instead — a
   paused container still kills the scrape path (the monitor leaves paused
   containers alone) and `unpause` restores it. Verified: `docker compose
   stop` → canary auto-restarted ~13s later with `RestartCount=0` (i.e. an
   external `docker start`, not its restart policy); `docker compose pause` →
   left untouched for the full test window.

2. **cadvisor cannot reliably signal a `docker stop`** in a non-privileged
   bundle. `container_last_seen` only goes stale on `docker rm` (cadvisor keeps
   refreshing exited containers it still sees in the Docker API — measured
   fresh ~3s after a stop); `container_tasks_state` reads cgroup task states
   that require a privileged container (measured all-zero both stopped and
   running). The spec's documented fallback is therefore used: `ContainerGone`
   fires on the **synthetic canary beacon** `absent(aperture_canary_up)`. This
   is recorded as a deferral in [DEFERRED.md](DEFERRED.md) with an extraction
   contract for a privileged-cadvisor stop-detection rule.

## 5. Teardown and isolation

```text
$ docker compose --profile logs --profile otel --profile tools down -v --remove-orphans
Volume god-g4-loki-data Removed
Volume god-g4-prometheus-data Removed
Volume god-g4-alloy-data Removed
Volume god-g4-grafana-data Removed
Volume god-g4-alertmanager-data Removed
Network g4-internal Removed

containers-left: 0
volumes-left: 0
networks-left: 0
```

Production untouched: 17/17 production monitoring containers — the full
monitoring stack present on this host before the build (names and IDs captured
in the build session, not committed here) — retained identical container IDs
and `Up` status before vs. after this build.

## 6. Secrets / gateway scan (whole `g4/` dir)

A grep scan across every file in `g4/` for the acceptance gate's forbidden
patterns — vault-style secret references, API-key strings, auth-token headers,
personal paths, personal hostnames, gateway references, and production
container names — returned zero matches (the exact pattern list lives in the
aperture ACCEPTANCE gate; it is deliberately not re-embedded here so the
committed tree stays free of the very strings the scan hunts for).

```text
(no matches for any forbidden pattern across ./)
```

Zero credential strings, personal paths, personal hostnames, gateway endpoints,
or production container names. `.env.example` carries only demo defaults
(`GOD_GRAFANA_PASSWORD=aperture-g4-demo-only`, `GOD_NTFY_URL=` empty). No
Telegram/Discord receivers or tokens were copied from the live alertmanager
config.

## 7. Profiles (opt-in) bring-up

```text
$ docker compose --profile logs --profile otel up -d
loki            running  healthy
alloy           running  (no healthcheck, by design)
otel-collector  running  (no healthcheck, by design)

$ docker compose exec -T prometheus wget -qO- http://otel-collector:13133/
{"status":"Server available","upSince":"2026-10-24T02:38:44.14Z","uptime":"17.15s"}

$ docker compose exec -T loki wget -qO- http://127.0.0.1:3100/loki/api/v1/labels
{"status":"success","data":["compose_project","compose_service","container","service_name"]}
```

`loki`/`alloy` ship god-g4 container logs end-to-end (the `container` /
`compose_service` labels are present in loki); `otel-collector` serves its
health_check extension. Loki runs as `user: "0"` matching the live monitoring
stack (the image's default non-root user cannot mkdir under a fresh `/var/loki`
volume). Alloy and otel-collector have no shell in-image, so they report
`running` rather than `healthy` — the same as the live stack's alloy.

## Deviations / remaining gates

- **cadvisor stop-detection + otel→loki log export deferred** with full
  extraction contracts ([DEFERRED.md](DEFERRED.md)).
- **arm64 runtime:** all external images are arm64-manifest-verified, but only
  amd64 runtime execution was performed on this build host. Real arm64
  acceptance remains open.
- **Loki dashboards:** the `logs` profile ships loki + alloy (ingestion) but no
  pre-built log dashboards; see DEFERRED.md.
- Parent PM review pending; no merge performed.

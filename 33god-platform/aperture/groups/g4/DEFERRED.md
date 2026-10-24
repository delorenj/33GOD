# DEFERRED — Aperture G4 (Observability)

G4 v1 ships the core metrics + alerting path fully proven. The items below are
deliberately not faked; each records the crib, why it was deferred, and the
exact extraction contract to land it later.

## 1. cadvisor-based container-stop detection (`ContainerGone`)

**Deferred:** a `ContainerGone` alert rule driven by a cadvisor signal.

**Why:** on this host, in a non-privileged cadvisor bundle (the standard
cadvisor pattern — docker.sock + rootfs, no `privileged`):

- `container_last_seen` only goes stale on `docker rm`, not `docker stop` —
  cadvisor keeps refreshing exited containers it still sees in the Docker API
  (measured fresh ~3s after a `docker compose stop`).
- `container_tasks_state` reads cgroup task states that require privileged
  access; measured all-zero both while the container is stopped and while it is
  running.

The spec's documented fallback ("if unreliable, use a synthetic canary scrape
target that the smoke stops/starts") is therefore what shipped: `ContainerGone`
is `absent(aperture_canary_up)` for 30s, driven by the canary's own liveness
beacon. It is proven end-to-end in [PROOF.md §4](PROOF.md).

**Extraction contract:** add a third rule group `g4_container_lifecycle`
backed by cadvisor, gated behind a cadvisor config that opts into privileged
cgroup reads:

- add `privileged: true` (or the narrower `--devices` / cgroup mounts) to the
  cadvisor service behind a new `GOD_CADVISOR_PRIVILEGED` toggle, default off;
- rule: `time() - container_last_seen{name=~"god-g4-.*"} > 60` for 30s (fires
  on `docker rm` of any god-g4 container);
- optionally `sum by (name) (container_tasks_state{name=~"god-g4-.*"}) == 0`
  for `docker stop`, only once privileged cgroup reads are verified non-zero
  for running containers;
- smoke: prove the rule fires on `docker rm <container>` and does not
  false-positive on a healthy restart.

## 2. otel-collector → loki log export

**Deferred:** the `otel` profile's log pipeline shipping OTLP logs to loki.

**Why:** the `logs` profile (loki + alloy) and the `otel` profile are
independent opt-ins, so wiring otel→loki would make `otel` silently depend on
`logs`. The collector currently exports logs to the `debug` exporter only
(metrics self-expose on :8889 for prometheus).

**Extraction contract:** add an `otlphttp` exporter and a log pipeline, gated
on the loki endpoint being reachable:

```yaml
exporters:
  otlphttp/loki:
    endpoint: http://loki:3100/otlp
service:
  pipelines:
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/loki, debug]
```

and document that the `otel` profile then requires `--profile logs` (or make
`otel-collector` `depends_on` loki with `condition: service_started` and
document the soft-fail if loki is absent).

## 3. Loki / log dashboards

**Deferred:** pre-built Grafana dashboards for the `logs` profile.

**Why:** v1 scope is one provisioned dashboard proving the prometheus
datasource and node/container up state. Log-query dashboards are a
presentation concern on top of the (already-proven) loki ingestion path.

**Extraction contract:** add a loki datasource (uid `g4-loki`, url
`http://loki:3100`) to `grafana/provisioning/datasources/`, plus a dashboard
under `grafana/provisioning/dashboards/` querying `{compose_project="god-g4"}`
via LogQL.

## 4. arm64 runtime execution

**Deferred:** running the bundle on real arm64 hardware.

**Why:** this build host is amd64. Every external image is arm64 +
amd64 manifest-verified ([PROOF.md §3](PROOF.md)); the two local images build
from `python:3.12-alpine` (multi-arch).

**Extraction contract:** on an arm64 host, run the same cold cycle + smoke
from [README.md](README.md) and record the output; no code change expected.

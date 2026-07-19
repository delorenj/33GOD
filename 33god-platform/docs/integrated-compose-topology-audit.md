# Integrated Compose topology audit

**Status:** Historical 2026-07-15 topology snapshot; superseded for Lifecycle
topology by the 2026-07-18 addendum

**Snapshot:** 2026-07-15 01:22-01:25 EDT

**Scope:** Bloodbank, Candystore, Holocene, and PJangler

**Constraint:** The evidence capture was read-only. The implemented outcome
changes only the root-owned platform projection and governance artifacts; it
does not change component repositories or runtime state.

## 2026-07-18 lifecycle-boundary addendum

The body below remains evidence for the four-component snapshot it captured.
Current root Compose additionally includes the digest-pinned standalone
Lifecycle authority, dedicated PostgreSQL/private network/secret, fail-closed
migrate/bootstrap/serve chain, durable Candystore projection, Momo
obligation-to-skill seam, and Holocene read/command surface. The isolated live
gate proves all seven offline/restart/outage/persistence invariants. See
`../README.md` and `../../docs/architecture-lifecycle.md` for current truth.

## Decision

Replace the platform readiness scaffold with an integrated local stack, but do
not include the current component Compose files verbatim.

The implemented first slice uses a root-owned normalized projection in
`33god-platform/compose.yaml` because component repositories were read-only for
this task. Component-owned fragments remain a possible later ownership refactor,
but only if they preserve the executable semantic contract. The no-profile local
stack manages:

1. Bloodbank NATS JetStream, stream initialization, and Dapr placement.
2. Exactly one Candystore deployment: PostgreSQL, application, and one Dapr
   sidecar using durable consumer `candystore-events`.
3. Holocene's Docker web application on the external `proxy` network.

Holocene's privileged API should remain an explicit host-systemd dependency in
the first slice. PJangler should remain host CLI and stdio MCP tooling. Neither
should be represented as a fake HTTP container.

Optional Bloodbank catalog and smoke services should remain opt-in profiles.
The legacy Bloodbank-owned Candystore profile must not be carried into the
integrated target.

## Implemented outcome

Implementation base `c4f78bb` replaced `platform-ready` with a root-owned,
normalized projection in `33god-platform/compose.yaml`. Component Compose files
were not edited or included verbatim. The candidate is validated against an
explicit populated `GOD_SOURCE_ROOT`, which lets an isolated worktree test the
projection against the read-only component sources.

The candidate implements:

- default Bloodbank services `bloodbank-nats`, `nats-init`, and
  `dapr-placement`;
- exactly one default Candystore deployment named `candystore-postgres`,
  `candystore`, and `candystore-daprd`;
- `holocene-api-preflight` against the existing host API followed by
  `holocene-web`; there is no Compose-owned Holocene API service;
- zero-replica `pjangler-cli` and `pjangler-mcp` definitions in `tools` and
  `full`, intended only for explicit `docker compose run`; MCP remains stdio
  and neither tool has ports, healthchecks, or a restart loop; and
- a render-only `cloud` profile whose rejection service makes the unsupported
  local-bind model explicit. It is not a deployment command surface.

The root projection preserves all audited ports, exact external networks
`bloodbank-network`, `candystore-internal`, and `proxy`, and the five adopted
external volume identities. Bloodbank's legacy Candystore services are absent;
its detached legacy PostgreSQL volumes remain outside the projection and must
remain preserved.

Executable evidence for `ROOT-COMPOSE-01` is the candidate semantic gate:

```bash
GOD_SOURCE_ROOT=/home/delorenj/code/33GOD \
  python3 33god-platform/scripts/validate-compose.py \
  --source-root /home/delorenj/code/33GOD
GOD_SOURCE_ROOT=/home/delorenj/code/33GOD \
  python3 -m unittest discover -s 33god-platform/tests -p 'test_*.py' -v
```

The validator renders default, `tools`, `full`, and `cloud` and rejects service
cardinality, dependency, port, network, volume, mount, host-boundary, run-only,
or cloud-blocker drift. This resolves the missing integrated model. It does not
prove a cutover: no lifecycle command was run, existing component projects and
the host `holocene-api.service` remain untouched, and the live acceptance list
below is still required before migration.

## Non-negotiable topology invariants

- Bloodbank owns the NATS/Dapr v3 transport plane, stream definitions, Dapr
  component names, and `bloodbank-network` contract.
- Candystore has exactly one durable deployment and exactly one
  `candystore-events` durable consumer. Two sidecars using that durable and
  queue group would split the audit trail across databases.
- Holocene web and Holocene API are different runtime units. The web is a
  Docker service; the API is currently a privileged user systemd service.
- PJangler is an npm-installed CLI plus MCP stdio server. It has no HTTP
  listener, health endpoint, or long-running Compose service.
- The current projection has no Lifecycle service. Adding one requires the
  approved extraction/migration gates and must preserve exactly one operational
  lifecycle writer; database co-location does not transfer ownership to
  Bloodbank or Candystore.
- Existing host ports, Docker volume identities, Docker network identities,
  and Traefik/OIDC behavior must survive the cutover unless a separately
  approved migration explicitly changes them.
- A move from component Compose project names to `33god-platform` must not
  silently create empty replacement data volumes.

## Authority and evidence policy

Evidence was weighted in this order:

1. Live Docker, systemd, listener, health, and NATS monitoring state.
2. Executable Compose, Dockerfile, package, Dapr, and stream manifests.
3. Current code and generated BMAD documentation.
4. Platform and component prose.

The component source checkouts under `/home/delorenj/code/33GOD` were treated
as authoritative and read-only for static validation. Static inspection may use
dirty source without failing merely because protected user work exists. A
lifecycle cutover has a stronger boundary: every component source must be clean
and pinned to the candidate's intended gitlink. Recent timestamps were used as a
staleness signal, not as proof of correctness.

### Source snapshot

| Component | HEAD | Source state relevant to this audit |
| --- | --- | --- |
| Bloodbank | `d4327b5` | Compose modified 2026-07-15 00:49 EDT; live NATS, placement, and legacy PostgreSQL hashes matched the current render. |
| Candystore | `c206f43` | Compose modified 2026-07-10 15:33 EDT; live PostgreSQL and Dapr hashes matched, but the app hash differed from the current render. |
| Holocene | `edaf31b` | Clean and published; the `/hq` and `/_next/static` router expansion is pinned by the root candidate. |
| PJangler | `0034df3` | Source package is `1.2.18`; globally installed CLI/MCP is `1.2.17`. |

Relevant evidence timestamps included:

- Bloodbank Compose: 2026-07-15 00:49 EDT.
- Bloodbank stream definition: 2026-06-02 15:00 EDT.
- Candystore Compose: 2026-07-10 15:33 EDT.
- Candystore BMAD deep-dive plan: 2026-07-09 14:09 EDT.
- Holocene Compose: 2026-07-13 12:02 EDT.
- Holocene API source: 2026-07-13 06:10 EDT.
- Holocene user unit: 2026-06-07 17:20 EDT.
- PJangler package metadata: 2026-07-13 14:41 EDT.
- PJangler generated deployment guide: 2026-07-13 08:55 EDT.

## Evidence commands and captured results

All commands in this section are read-only. Secret values were not recorded;
only environment key names and secret-source boundaries were retained.

### Compose rendering

```bash
docker compose -f 33god-platform/compose.yaml --profile tools config --no-env-resolution --quiet
docker compose --project-name bloodbank \
  -f /home/delorenj/code/33GOD/bloodbank/compose/docker-compose.yml \
  config --no-env-resolution --quiet
docker compose --project-name bloodbank \
  -f /home/delorenj/code/33GOD/bloodbank/compose/docker-compose.yml \
  --profile '*' config --no-env-resolution --quiet
docker compose --project-name candystore \
  -f /home/delorenj/code/33GOD/candystore/compose.yml \
  config --no-env-resolution --quiet
docker compose --project-name holocene \
  -f /home/delorenj/code/33GOD/holocene/compose.yml \
  config --no-env-resolution --quiet
```

All five renders passed with Docker Compose `v5.0.2`.

| Model | Rendered services |
| --- | --- |
| Platform `tools` | `platform-ready` only |
| Bloodbank default | `apicurio-registry`, `dapr-placement`, `eventcatalog`, `nats`, `nats-init` |
| Bloodbank all profiles | Fourteen services, including heartbeat/smoke services and the prohibited legacy Candystore triplet |
| Candystore | `postgres`, `candystore`, `daprd` |
| Holocene | `holocene-web` only |

Bloodbank reports profiles `candystore`, `dapr-smoketest`, `dapr-subscribe`,
and `heartbeat`. Candystore and Holocene define no profiles today.

### Live container, network, volume, and listener evidence

```bash
docker compose ls --all
docker ps -a
docker inspect bloodbank-nats bloodbank-dapr-placement bloodbank-postgres \
  candystore-postgres candystore candystore-daprd holocene-web
docker network inspect bloodbank-network
docker network inspect proxy
docker volume ls
docker volume inspect \
  bloodbank_bloodbank-nats-data \
  bloodbank_bloodbank-postgres-data \
  candystore_pgdata \
  holocene_holocene_node_modules \
  holocene_holocene_web_node_modules \
  holocene_holocene_web_next
ss -ltnp
```

The live Compose projects were `bloodbank` with three running containers,
`candystore` with three, and `holocene` with one. Bloodbank's separate
`bloodbank-toaster` project was also running and attached to
`bloodbank-network`.

| Live unit | State | Health | Networks | Published ports |
| --- | --- | --- | --- | --- |
| `bloodbank-nats` | Running | Healthy | `bloodbank-network` | `0.0.0.0/[::]:4222`, `0.0.0.0/[::]:8222` |
| `bloodbank-dapr-placement` | Running | No container healthcheck | `bloodbank-network` | `0.0.0.0/[::]:50005` |
| `bloodbank-postgres` | Running | Healthy | `bloodbank-network` | Internal `5432` only |
| `candystore-postgres` | Running | Healthy | `candystore-internal` | `127.0.0.1:5434` |
| `candystore` | Running | Healthy | `candystore-internal`, `proxy` | `127.0.0.1:8683` |
| `candystore-daprd` | Running | No container healthcheck | `candystore-internal`, `bloodbank-network` | `127.0.0.1:3504` |
| `holocene-web` | Running | No container healthcheck | `proxy` | None; Traefik reaches internal `3001` |

The live Bloodbank project did not contain `nats-init`, Apicurio,
EventCatalog, or a Bloodbank Candystore app/sidecar at the snapshot. Its
running `bloodbank-postgres` is therefore a legacy persistence artifact, not
an active second event consumer.

### Live health and durability evidence

```bash
curl -fsS http://127.0.0.1:8222/healthz
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8683/healthz
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8683/readyz
curl -sS -o /dev/null -w '%{http_code}\n' \
  http://127.0.0.1:3504/v1.0/healthz
curl -fsS http://127.0.0.1:4000/health
curl -sS -o /dev/null -w '%{http_code}\n' https://holocene.delo.sh/
curl -sS -o /dev/null -w '%{http_code}\n' https://candystore.delo.sh/
curl -fsS \
  'http://127.0.0.1:8222/jsz?accounts=true&streams=true&consumers=true&config=true'
```

Captured results:

- NATS health: HTTP 200, `{"status":"ok"}`.
- Candystore liveness: HTTP 204.
- Candystore readiness: HTTP 204.
- Candystore Dapr sidecar: HTTP 204.
- Holocene host API: HTTP 200,
  `{"ok":true,"service":"holocene-api"}`.
- Both public sites returned HTTP 307 into the Google OIDC flow.
- `BLOODBANK_EVENTS` was file-backed with seven-day retention, 23,846
  messages, and one consumer.
- `BLOODBANK_COMMANDS` was file-backed work-queue retention with a one-day
  maximum age and no consumer.
- The one `BLOODBANK_EVENTS` consumer was durable
  `candystore-events`, filtered on `bloodbank.evt.v1.>`, with explicit
  acknowledgement, zero pending messages, and zero acknowledgement-pending
  messages.

This is direct evidence that the live audit path currently has exactly one
durable Candystore consumer. The target must preserve that cardinality.

### Holocene host API evidence

```bash
systemctl --user show holocene-api.service \
  -p FragmentPath -p ActiveState -p SubState -p MainPID \
  -p ExecStart -p WorkingDirectory -p EnvironmentFiles \
  -p RestartUSec -p NRestarts
systemctl --user status holocene-api.service --no-pager
```

The enabled unit was active with zero restarts. It ran:

```text
/home/delorenj/.local/share/mise/installs/node/latest/bin/node
/home/delorenj/code/33GOD/holocene/apps/api/dist/server.js
```

Its working directory was
`/home/delorenj/code/33GOD/holocene/apps/api`. Unit environment keys were
`HOST`, `PORT`, `HERMES_REGISTRY_PATH`, and `PATH`; values were intentionally
redacted from this audit. Source defaults are port `4000` and host `0.0.0.0`.
The live listener was `0.0.0.0:4000`.

### PJangler runtime evidence

```bash
command -v pjangler
command -v pj
command -v pjangler-mcp
pjangler --version
npm list -g --depth=0 @delorenj/pjangler
stat /home/delorenj/.config/pjangler/projects.yaml
```

All three binaries resolved under the mise Node installation. The installed
package was `@delorenj/pjangler@1.2.17`; source package metadata was `1.2.18`.
The central registry existed at `~/.config/pjangler/projects.yaml`. Package
metadata maps `pjangler` and `pj` to `dist/index.js`, and `pjangler-mcp` to
`dist/mcp-server.js`. The MCP implementation uses stdio.

## Current versus target service matrix

| Owner | Current unit | Current deployment truth | Recommended target |
| --- | --- | --- | --- |
| Platform | `platform-ready` | Alpine tools-profile scaffold only; starts no component | Remove after the integrated model and preflight command exist. Do not retain as a false readiness signal. |
| Bloodbank | NATS | Live `nats:2.10-alpine`, healthy, JetStream file storage | Default core service; preserve container DNS `nats`, ports 4222/8222, stream volume identity, command, and healthcheck. |
| Bloodbank | `nats-init` | Declared default one-shot, absent from live container inventory | Default one-shot; depend on healthy NATS and gate all durable subscribers on `service_completed_successfully`. |
| Bloodbank | Dapr placement | Live `daprio/dapr:1.13.0`; no container healthcheck | Default core service; preserve `dapr-placement:50005`. Add a platform-level external readiness probe rather than a shell healthcheck inside the distroless image. |
| Bloodbank | Apicurio | Declared default at host 8080; not live | Optional `catalog`/`full` profile only until its host-port collision and schema-sync value are resolved. |
| Bloodbank | EventCatalog | Declared default at host 3000; not live | Optional `catalog`/`full`; depend on healthy Apicurio. Preserve the read-only site mount if enabled. |
| Bloodbank | Heartbeat/subscription/smoke services | Opt-in component profiles; render successfully | Keep in `smoke`/`test`, outside the product default. Retain component ownership and current test ports. |
| Bloodbank | Legacy `postgres`, `candystore`, `daprd-candystore` | Profile can create a second database and competing durable consumer. Only its PostgreSQL container is live now. | Exclude all three. Preserve the legacy volume offline until its contents are reviewed; never start its app/sidecar alongside canonical Candystore. |
| Candystore | PostgreSQL | Live `postgres:16-alpine`, healthy, volume `candystore_pgdata` | Default audit service; preserve loopback 5434, volume identity, database name, and healthcheck. |
| Candystore | App/API/UI | Live image `candystore:local`, healthy, loopback 8683, Traefik network | Default audit service built from `../candystore`; preserve image name for the first cutover. Change dependency readiness to `/readyz`. |
| Candystore | Dapr sidecar | Live `daprio/daprd:1.13.0`, durable `candystore-events`, loopback 3504 | Exactly one default sidecar. Depend on NATS initialization, placement start, and Candystore readiness. The distroless daprd image intentionally has no Compose healthcheck; probe its published loopback health endpoint externally. |
| Holocene | Web | Live `node:22` Compose service on `proxy`; source bind mount and three named volumes; no host port or healthcheck | Default control UI; preserve internal port 3001, bind/volume layout, `host.docker.internal`, Traefik labels, and OIDC/HQ router behavior for the first cutover. Add internal web health. |
| Holocene | API | Host user service, active on `0.0.0.0:4000`; broad host-system authority | Keep external to Compose in the local profile. Make its unit health a preflight requirement. Do not containerize by mounting the systemd socket or broad host paths. |
| PJangler | CLI | Globally installed npm binary with host-user authority | Host prerequisite and operator command, not an `up` service. Pin source/install parity before the platform cutover. |
| PJangler | MCP | `pjangler-mcp` stdio binary | Host stdio tool, launched by an MCP client. No ports, Docker healthcheck, or HTTP route. An optional one-shot tools image can be added only after a dedicated image contract exists. |
| Bloodbank adjacent | Event toaster | Separate live Compose project on `bloodbank-network` | Leave separate in the first cutover or add an explicit `observability` profile later. Do not break its access to `bloodbank-network`. |

## Images and build contexts

| Service group | Current image/build | Target handling |
| --- | --- | --- |
| NATS | `nats:2.10-alpine` | Pin unchanged for the initial cutover. |
| NATS initializer | `natsio/nats-box:0.14.5` plus read-only `streams.json` and `init.sh` | Keep Bloodbank-owned mounts and one-shot entrypoint. Paths must resolve relative to the Bloodbank fragment, not the platform directory. |
| Dapr placement | `daprio/dapr:1.13.0` | Pin unchanged. |
| Dapr sidecars | `daprio/daprd:1.13.0` | Pin unchanged and mount service-specific components read-only. |
| Candystore database | `postgres:16-alpine` | Pin unchanged. |
| Candystore app | `build: /home/delorenj/code/33GOD/candystore`, `image: candystore:local`; Dockerfile uses `python:3.11-slim` | Platform fragment should use the component repo as build context and retain `candystore:local` for the first migration. The frontend remains prebuilt into `static/`. |
| Holocene web | `node:22`; no Dockerfile; repository bind-mounted and installed/built at container start | Preserve for the first cutover to avoid combining topology migration with image redesign. A later component-owned Dockerfile should replace runtime `pnpm install` and the writable source mount. |
| Apicurio | `apicurio/apicurio-registry:3.0.6` | Optional profile only. |
| EventCatalog | `quay.io/eventcatalog/eventcatalog:2.11.1` | Optional profile only. |
| Bloodbank smoke subscriber | `python:3.11-alpine` | Test profile only. |
| Heartbeat publisher | Build context `bloodbank/services/heartbeat-tick` | Test profile only. |
| PJangler | No Docker image or Dockerfile; npm package with Node `>=20` | Do not invent an image during the Compose migration. Keep host CLI/MCP. |

The platform Compose directory changes relative-path semantics. Normalized
component fragments should keep build and bind paths component-relative. A
single duplicated platform file with `../..` path arithmetic is more likely to
drift and should not be the durable design.

## Ports

### Ports to preserve in the first cutover

| Port | Bind | Owner/purpose | Target rule |
| --- | --- | --- | --- |
| 4222 | `0.0.0.0` and `[::]` | Bloodbank NATS client | Preserve initially because host publishers use it. Authentication and loopback reduction are separate security work. |
| 8222 | `0.0.0.0` and `[::]` | NATS monitor | Preserve initially; do not route publicly. |
| 50005 | `0.0.0.0` and `[::]` | Dapr placement | Preserve initially for existing sidecars. |
| 5434 | `127.0.0.1` | Canonical Candystore PostgreSQL | Preserve. |
| 8683 | `127.0.0.1` | Candystore API/UI | Preserve. Holocene host API depends on this address. |
| 3504 | `127.0.0.1` | Candystore Dapr HTTP | Preserve for operator health/debugging. |
| 3001 | Container only | Holocene web | Do not publish to host. Traefik reaches it over `proxy`. |
| 4000 | Host `0.0.0.0` | Holocene host API | Compose must not claim it. Its exposure is an existing security risk and a separate hardening decision. |

### Optional and collision-sensitive ports

| Port | Source declaration | Finding |
| --- | --- | --- |
| 8080 | Bloodbank Apicurio | Not live. Host 8080 is already occupied by Traefik, so the source default cannot join the integrated stack unchanged. Keep the service disabled until a new bind is approved. |
| 3000 | Bloodbank EventCatalog | Not live. Enable only with the catalog profile after Apicurio is resolved. |
| 3301/3501 | Dapr subscribe smoke pair | Test-only. |
| 3601/3502 | Heartbeat recorder/sidecar | Test-only. |
| 3500/50001 | Dapr smoke HTTP/gRPC | Test-only and collision-prone. |
| 3603/3505 | Legacy Bloodbank Candystore app/sidecar | Remove from the integrated topology. Canonical values are 8683/3504. |

## Health and readiness

| Unit | Current signal | Target gate |
| --- | --- | --- |
| NATS | Container healthcheck calls monitor `/healthz`; live HTTP 200 | `service_healthy`. |
| NATS streams | Monitor showed both configured streams and file storage | `nats-init` must complete successfully before subscribers. Add a post-init assertion for `BLOODBANK_EVENTS` and `BLOODBANK_COMMANDS`. |
| Dapr placement | Running, no healthcheck | External TCP/gRPC-aware readiness probe; do not add `CMD-SHELL` to a distroless image. |
| Candystore PostgreSQL | `pg_isready`; live healthy | `service_healthy`. |
| Candystore app | Container checks `/healthz`; live `/healthz` and `/readyz` both 204 | Use `/readyz` for dependent startup so database readiness is included. Keep `/healthz` for liveness. |
| Candystore Dapr | Distroless `daprio/daprd`; intentionally no container healthcheck; live published loopback `/v1.0/healthz` returned 204 | External readiness at `http://127.0.0.1:3504/v1.0/healthz`. Do not claim or depend on Compose `service_healthy` for daprd. |
| Holocene host API | systemd active; `/health` HTTP 200 | Required host preflight before Holocene web is declared ready. |
| Holocene web | Running; no container healthcheck; public route returns OIDC 307 | Add an internal HTTP healthcheck against port 3001. Public 307 proves routing/auth, not application readiness. |
| PJangler | `pjangler --version`; npm install metadata | Validation command, not service health. Require installed/source version parity. |

## Dependencies and start order

The integrated dependency graph should be explicit where Compose can express
it and documented where it crosses the host boundary.

```text
external proxy network
external/owned bloodbank-network
        |
        v
Bloodbank NATS --healthy--> nats-init --completed-------------------+
        |                                                            |
        +--> Dapr placement --externally ready-----------------------+
                                                                     v
Candystore PostgreSQL --healthy--> Candystore app --ready--> Candystore daprd
                                                        (one durable consumer)

Candystore ready --> Holocene host API reads 127.0.0.1:8683
Holocene host API healthy --> Holocene web starts/declares ready

PJangler CLI/MCP: independent host tooling; no Compose start dependency
```

Recommended cutover order:

1. Back up the NATS and canonical Candystore volumes and record restore
   commands.
2. Confirm `proxy` and `bloodbank-network` exist and retain adjacent consumers
   such as the event toaster.
3. Stop old component-managed containers without deleting volumes.
4. Start NATS and placement under the integrated model using the existing NATS
   volume identity.
5. Complete stream initialization and verify both stream contracts.
6. Start canonical Candystore PostgreSQL and app using `candystore_pgdata`.
7. Start exactly one Candystore Dapr sidecar and verify NATS shows exactly one
   `candystore-events` consumer with no backlog.
8. Verify the host Holocene API reads Candystore successfully and returns 200.
9. Start Holocene web, then verify its internal health and both Traefik routes.
10. Verify PJangler CLI/MCP version parity separately. Do not start it with
    `docker compose up`.

## Profiles

| Target profile | Contents | Notes |
| --- | --- | --- |
| No profile | NATS, NATS init, Dapr placement, canonical Candystore PostgreSQL/app/sidecar, Holocene API preflight, Holocene web | Validated local target. Host API, three external networks, and five external volumes are prerequisites. |
| `tools` | No-profile target plus zero-replica PJangler CLI and stdio MCP definitions | Run-only. No ports, healthcheck, daemon, or `up` contract. |
| `full` | Current no-profile target plus the same run-only PJangler definitions | Deliberately identical to `tools` until optional services receive explicit governance. |
| `cloud` | Local target plus an explicit unsupported-model rejection service | Render-only evidence with no supported lifecycle surface; hosted use remains blocked by local binds, external networks, host systemd authority, auth, secrets, storage, and backup gaps. |

Catalog, observability, and smoke services remain component-owned and outside
the implemented projection. Their absence prevents accidental port collisions
and keeps test/reference services out of the product default.

`docker compose --profile cloud up` is not a safe rejection test. Compose also
selects every unprofiled local service, so NATS, PostgreSQL, Candystore, and
Holocene may start and mutate before `cloud-unsupported` exits. Cloud is
configuration/render inspection only; no lifecycle task is provided.

## Secrets and environment

No secret values belong in the integrated Compose file or this audit.

| Owner | Current keys/source | Target handling |
| --- | --- | --- |
| Bloodbank | `BLOODBANK_*_PORT`, heartbeat interval, NATS URL; Dapr secret store expects `BLOODBANK_NATS_TOKEN` and `BLOODBANK_NATS_SEED_KEY` semantics | Keep local port defaults in a documented platform env example. Keep actual credentials external. Resolve the current mismatch between secret references and unauthenticated NATS before any cloud profile. |
| Candystore | `CANDYSTORE_PORT`, `CANDYSTORE_POSTGRES_PORT`, `CANDYSTORE_DAPR_HTTP_PORT`; inline local database user/password and `DATABASE_URL` | Preserve local values for first cutover, then move the password and URL to an ignored env file or secret provider. Do not print them in rendered evidence. |
| Holocene web | `.env.holocene-web` keys: `HOLOCENE_WEB_PORT`, `HOLOCENE_API_INTERNAL_URL`, `TELEGRAM_HQ_BOT_TOKEN`, `HQ_OPERATOR_TELEGRAM_IDS` | Continue using the component-owned ignored env file. Preserve `HOLOCENE_API_INTERNAL_URL=http://host.docker.internal:4000` behavior and `extra_hosts: host-gateway`. Never bake Telegram secrets into an image. |
| Holocene source secrets | `.env.op` carries 1Password-backed inputs for OpenRouter, n8n, and Telegram/HQ values | Keep `.env.op` as secret-reference source and render locally outside Compose. |
| Holocene API | Unit keys `HOST`, `PORT`, `HERMES_REGISTRY_PATH`, `PATH`; source also supports `CANDYSTORE_API_URL`, Redis/tooling URL, Prometheus URL, bgls path, and Hermes paths | Keep in the user unit or an ignored unit EnvironmentFile. Explicitly set `CANDYSTORE_API_URL=http://127.0.0.1:8683` instead of relying on fallback. |
| PJangler | `PJ_PROJECT_REGISTRY`, `PJ_SOURCE_SKILL_ROOTS`, `PJ_REGISTRY_PG`, `PJ_AGENT_HOOKS_LAYER`, and `PJANGLER_*` template/config overrides; provider credentials come from host tooling | Keep host-scoped. Do not pass the user's full environment into a container. Any future one-shot tools image needs a narrow, documented mount/env allowlist. |

## Volumes and persistence

| Current identity | Contents/role | Target requirement |
| --- | --- | --- |
| `bloodbank_bloodbank-nats-data` | Live JetStream file store; created 2026-05-11 | Reuse by explicit `name:` during project-name migration. Back up before cutover. Never allow an automatic `33god-platform_*` replacement. |
| `candystore_pgdata` | Canonical Candystore PostgreSQL; created 2026-06-10 | Reuse by explicit `name:`. This is the only active audit database volume. Back up and test restore first. |
| `bloodbank_bloodbank-postgres-data` | Legacy Bloodbank-profile PostgreSQL; created 2026-05-26 | Do not mount in the target. Preserve offline until data ownership is reviewed; do not delete during Compose migration. |
| `bloodbank_data` | Older Bloodbank volume from 2025 | Out of the target. Inventory separately before deletion. |
| `holocene_holocene_node_modules` | Web dependency cache | Preserve explicit identity for first cutover; disposable after a dedicated image migration. |
| `holocene_holocene_web_node_modules` | App dependency cache | Same. |
| `holocene_holocene_web_next` | Next build output | Same. |
| Holocene repository bind | Whole repo mounted read-write at `/app` | Preserve only for first cutover. Replace with an immutable component image in separate work. |
| Bloodbank NATS config mounts | `streams.json`, `init.sh` read-only | Preserve component-relative, read-only mounts. |
| Candystore Dapr components | `candystore/dapr-components` to `/components:ro` | Preserve. This service-specific durable configuration must not be replaced with the generic Bloodbank component. |

Named volume migration is a data-safety boundary. A successful Compose render
does not prove the target points at the existing data. The implementation must
inspect rendered volume `name` values before any `up`.

## Networks and Traefik

| Network | Current use | Target contract |
| --- | --- | --- |
| `bloodbank-network` | NATS, Dapr placement, legacy Bloodbank PostgreSQL, Candystore Dapr, event toaster, and another adjacent app | Preserve the exact name. Bloodbank owns the contract. The integrated stack must not remove/recreate it while external consumers are attached. |
| `candystore-internal` | Canonical PostgreSQL, app, and Dapr sidecar | Preserve the exact name and isolation. Only the Dapr sidecar also joins `bloodbank-network`; only the app joins `proxy`. |
| `proxy` | External shared Traefik/Cloudflare network | Keep `external: true`. Holocene web and Candystore app remain attached. PostgreSQL and Dapr remain off it. |

Traefik behavior to preserve:

- Holocene uses Docker labels, `traefik.docker.network=proxy`, internal port
  3001, TLS with `letsencrypt`, and the shared `google-auth@file` middleware
  for the main router.
- The higher-priority Holocene HQ router bypasses Google auth for `/hq` and its
  `/_next/static` assets, matching committed Holocene HEAD. HQ data remains
  guarded by Telegram init-data validation.
- Candystore has no container labels. A file-provider definition routes
  `candystore.delo.sh` to `http://candystore:3001`, applies `google-auth`, and
  checks `/healthz`.
- The live Cloudflare tunnel routes `holocene.delo.sh`, `*.delo.sh`, and the
  apex through `https://traefik:443` with internal TLS verification disabled.
- Public probes returned the expected 307 OIDC redirect for both Holocene and
  Candystore.

The integrated stack must preserve container/DNS names `holocene-web` and
`candystore` or update the external Traefik file in the same coordinated
change. Namespaced Compose service keys can coexist with preserved
`container_name`/network aliases during the first cutover, but fixed container
names require the old projects to be stopped before the new project starts.

## Collision and migration risks

| Risk | Severity | Evidence and required mitigation |
| --- | --- | --- |
| Two Candystore durable consumers | Critical | Both current Compose models can use durable `candystore-events` and queue `candystore`. Exclude the Bloodbank profile and assert one consumer in NATS after cutover. |
| Empty replacement data volumes | Critical | Compose project-name changes alter generated volume names. Use explicit current names, back up first, and inspect the rendered model. |
| Current app/render drift | High | Candystore app and Holocene web live config hashes differed from current renders. Reconcile/freeze the desired source before cutover; do not assume recreate is no-op. |
| Apicurio port 8080 | High | Source declares host 8080 while live Traefik owns host 8080. Keep catalog disabled until a non-conflicting route is approved. |
| Verbatim Compose include collisions | High | Bloodbank and Candystore both define generic `postgres`/`candystore` service names and independent top-level project names. Normalize and namespace fragments before `include`. |
| Fixed container names | High | Old and new Compose projects cannot own the same fixed names simultaneously. Use a planned stop/start cutover with no `-v`. |
| Bloodbank network ownership | High | External projects are attached. Removing or renaming it breaks Candystore Dapr and event toaster connectivity. |
| Holocene API exposure | Critical for untrusted/cloud use | API binds `0.0.0.0:4000`, has host-system authority, and is outside Traefik auth. Preserve the boundary locally but block cloud/untrusted claims. |
| Holocene source bind | High | Web container can write the source repo and installs/builds at startup. Preserve only to isolate the topology change, then replace with immutable image work. |
| NATS/placement broad binds | High | 4222, 8222, and 50005 listen on all interfaces. Preserve for compatibility in the first slice, then add auth and binding review. |
| Inline development credentials | High for hosted use | Candystore database defaults and Bloodbank local secret-store behavior are local-only. Keep cloud profile blocked. |
| PJangler version skew | Medium | Installed 1.2.17 differs from source 1.2.18. Pin one version before claiming a reproducible tool profile. |
| External Traefik DNS coupling | High | Candystore file-provider config depends on `candystore:3001`; Holocene labels depend on `proxy` and router names. Verify both before and after cutover. |
| Legacy data ambiguity | Medium | `bloodbank_bloodbank-postgres-data` and older `bloodbank_data` remain. Preserve but do not attach; disposition needs owner review. |

## Unresolved questions

1. Should Apicurio and EventCatalog be part of `full`, or remain component
   sandboxes until Holyfields synchronization is operationally useful?
2. Which non-conflicting endpoint should Apicurio use, given Traefik already
   owns host 8080?
3. Should `bloodbank-network` become a permanently external, bootstrap-managed
   network, or should all adjacent Bloodbank consumers move under the platform
   project before ownership changes?
4. Is the legacy `bloodbank_bloodbank-postgres-data` volume disposable,
   archival, or a migration source? No deletion should occur without an
   evidence-backed answer.
5. Should the Holocene API continue binding all interfaces after the Compose
   cutover, or can it move to loopback without breaking web/container access?
   A loopback-only API would require a deliberate bridge/proxy mechanism.
6. What backup tool and restore acceptance test gate the NATS and Candystore
   volume handoff?
7. Should the first platform implementation pin PJangler 1.2.17 to match the
   installed tool or deploy 1.2.18 to match source?
8. Which services, if any, are allowed to retain broad host binds after the
   local migration? This must be answered before a cloud profile exists.

Resolved candidate decisions are no longer recommendations: committed Holocene
HEAD, including `/_next/static`, is the baseline, and PJangler remains narrow,
read-only-source, zero-replica CLI/stdio MCP tooling
invoked only with explicit `docker compose run`.

## Historical implementation recommendation

The following recommendation was the basis for `c4f78bb`. The implementation
kept the same topology but placed the normalized projection at the root because
component repositories were read-only for this slice. A future component-owned
fragment refactor must preserve the semantic validator's contract.

### 1. Normalize component-owned fragments

Create component-owned platform fragments in follow-up component changes:

- Bloodbank core fragment with namespaced service keys for NATS, NATS init,
  Dapr placement, and optional catalog/smoke services. Remove the embedded
  Candystore triplet from the platform fragment.
- Candystore fragment with namespaced PostgreSQL, app, and Dapr keys while
  retaining the canonical app/network aliases and exactly one durable
  component mount.
- Holocene web fragment only. Keep the API as a documented external host
  prerequisite.

Fragments should omit top-level project `name` and use component-relative
paths. They should expose stable extension points for the platform without
duplicating service definitions in `33god-platform`.

### 2. Make the platform Compose an include-based aggregator

After normalization, replace the scaffold with an aggregator that:

- Uses project name `33god-platform`.
- Includes the three component-owned fragments.
- Declares/reuses exact data volume names.
- Preserves `bloodbank-network`, `candystore-internal`, and external `proxy`.
- Implements actual `full`, `catalog`, `observability`, `smoke`, and `tools`
  profiles.
- Contains no PJangler HTTP service and no pretend Holocene API container.
- Adds narrow probe services only where distroless/external readiness cannot be
  expressed directly.

Do not include the current full files directly. Their service-name collisions,
top-level project names, legacy Candystore profile, relative paths, and port
assumptions make that unsafe.

### 3. Preserve data identities during cutover

Render and review the candidate before starting anything. The candidate must
resolve to the existing volume identities, especially:

```text
bloodbank_bloodbank-nats-data
candystore_pgdata
holocene_holocene_node_modules
holocene_holocene_web_node_modules
holocene_holocene_web_next
```

Back up and restore-test the first two. Stop old projects without `-v`. Start
the candidate in dependency order and verify the one-consumer invariant before
allowing producers to continue.

### 4. Preserve the host-control boundary honestly

Add a platform preflight that verifies:

```bash
systemctl --user is-active holocene-api.service
curl -fsS http://127.0.0.1:4000/health
pjangler --version
command -v pjangler-mcp
```

These are external prerequisites, not Compose services. The Holocene API needs
a separate security redesign before container or cloud migration. PJangler
needs a dedicated tool-image contract before an optional one-shot `tools`
container is justified.

### 5. Gate the implementation with static and live acceptance

Static candidate gates:

```bash
python3 33god-platform/scripts/platform.py validate
python3 33god-platform/scripts/platform.py components list
python3 33god-platform/scripts/platform.py backfills check
docker compose -f 33god-platform/compose.yaml config --no-env-resolution --quiet
docker compose -f 33god-platform/compose.yaml --profile tools config --no-env-resolution --quiet
docker compose -f 33god-platform/compose.yaml --profile full config --no-env-resolution --quiet
docker compose -f 33god-platform/compose.yaml --profile cloud config --no-env-resolution --quiet
python3 33god-platform/scripts/validate-compose.py --source-root "$GOD_SOURCE_ROOT"
python3 -m unittest discover -s 33god-platform/tests -p 'test_*.py' -v
GOD_SOURCE_ROOT=/home/delorenj/code/33GOD mise run docs:drift
```

Cutover acceptance must then prove:

- Existing NATS and Candystore volumes are mounted.
- Both Bloodbank streams retain their expected configuration and data.
- Exactly one `candystore-events` durable consumer exists.
- Candystore `/healthz` and `/readyz` return success.
- Candystore Dapr health returns success with no backlog.
- Holocene host API health returns success and reads Candystore at
  `127.0.0.1:8683`.
- Holocene web is internally healthy.
- Holocene and Candystore public routes retain their OIDC behavior; HQ retains
  its deliberate route exception and application-level Telegram validation.
- PJangler CLI and MCP binaries match the chosen source/package version.
- Legacy Bloodbank PostgreSQL volumes remain detached and preserved.

Static gates may use the authoritative primary component sources read-only even
when they contain protected work. Before any lifecycle command, verify clean,
pinned sources without printing file contents:

```bash
candidate_root=$(git rev-parse --show-toplevel)
for component in bloodbank candystore holocene pjangler; do
  expected=$(git -C "$candidate_root" ls-tree HEAD "$component" | awk '{print $3}')
  actual=$(git -C "$GOD_SOURCE_ROOT/$component" rev-parse HEAD)
  test "$actual" = "$expected"
  test -z "$(git -C "$GOD_SOURCE_ROOT/$component" status --porcelain)"
done
```

## Runtime summary

The implemented projection is the live local four-part runtime integration:
Bloodbank core plus one canonical Candystore plus Holocene web, with the
Holocene API as a host prerequisite and PJangler as explicit run-only CLI/stdio
MCP tooling. It is not a project-lifecycle authority. The approved standalone
Lifecycle service, single-writer cutover, and Momo/Holocene clients remain
unimplemented.

The two strongest prohibitions are simple:

1. Never run both Candystore deployment shapes.
2. Never model PJangler or the Holocene host API as an ordinary web container
   merely to make the service list look unified.

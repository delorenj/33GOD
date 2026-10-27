# PJangler registry-only unblock — Grolf → Rererere

2026-10-27. **Research and build-host evidence, not Studio deployment authorization.** Rererere owns target installation and acceptance. This does not accept the broader PJangler create → repeat → repeat gate.

## Finding

The **published npm package already runs the registry**. Independently tested on a disposable Linux x86_64 installation: clean production-only install, registry health 200, fresh empty index, malformed request rejected 400, synthetic `.project.json` indexed and read back, `pj list` read back, registry process restarted and identical record returned. The synthetic manifest remained unchanged. No source rebuild, BMAD, Copier, Plane, Flume or LLM was needed.

Exact artifact:
- URL: https://registry.npmjs.org/@delorenj/pjangler/-/pjangler-1.5.18.tgz
- SHA256: `5dd18ab8df773f7f6ccf85ac81672f413f5c676af35ccc87bebfac352cc33f1c`
- npm gitHead: `84a342280046d7708f54c57e8692aab7fd9d01f8`
- Entrypoint: `dist/project-registry-service.js` (40,544 bytes).
- Tested runtime: Node 26.5.0, npm 11.17.0, PostgreSQL 17.9. Package requires Node >=24; that declared minimum was not the tested runtime.

The source checkout also says 1.5.18 but differs from the npm artifact. Use the tarball hash, not the local version string, as identity.

## Fastest registry-only target trial

**Proposal for Rererere:** native Node on Studio + recipient-owned PostgreSQL. A new npm release is not needed for this narrow topology. Choose a private deployment prefix and download/verify the exact tarball above; install that verified local file:

```sh
npm install --prefix "$PREFIX" --omit=dev --ignore-scripts "$VERIFIED_TARBALL"
# Supply recipient-owned PGHOST, PGPORT, PGDATABASE, PGUSER and PGPASSWORD locally.
# Do not print credentials. This version ignores DATABASE_URL.
export PJ_REGISTRY_PORT=8764
node "$PREFIX/node_modules/@delorenj/pjangler/dist/project-registry-service.js"
```

- PostgreSQL must be reachable and the deployment-owned database role must be allowed to create `citext`, schema and tables. Startup performs this DDL; no separate migration command was needed in the disposable proof.
- Every CLI consumer needs `PJ_REGISTRY_URL=http://127.0.0.1:8764` (or the chosen local port). Package installation does not start or supervise the singleton.
- **Do not run `registry:install` on macOS:** it assumes Linux/systemd and hardcodes a Unix PostgreSQL socket, database, OS role and port.
- Do not run `npm run build` inside the installed package; compiled output is already present and development tools are intentionally absent.
- For lasting native operation, Rererere selects recipient-owned supervision (e.g. launchd); reboot/supervisor behavior is not yet proven.

## Registry-only target acceptance

1. `GET /health`: HTTP 200, `ok:true`, service `pjangler-project-registry`.
2. Index a **disposable recipient-owned** regular file named `.project.json`, containing a synthetic `project_id`, via `POST /v1/index` with `{"manifest_path":"/absolute/disposable-project/.project.json"}`.
3. `GET /v1/registry` and packaged `pj list`: the same synthetic ID and path; index status `ok`.
4. Restart only the registry process through the chosen supervisor; repeat readback.
5. Separately verify database-volume persistence and supervisor/host-reboot recovery before durable operational acceptance.

The service indexes filesystem paths visible to **the service**, not uploaded manifest JSON. Native execution sees native paths. Containerization needs deliberate project mounts and consistent paths; mutation routes require writable manifests.

## Packaging repairs still required

- G5 image bundles only the CLI and omits this real daemon. The no-daemons inventory statement was incorrect for the registry.
- Executable binds to `127.0.0.1` and ignores `HOST`/`PJ_REGISTRY_HOST`; ordinary Docker bridge publishing cannot reach that listener. A Compose/container-client topology requires a versioned bind-host/interface and packaging correction—not an ad-hoc public exposure.
- DATABASE_URL support is absent; explicit PG* configuration works.
- Native macOS installer/supervisor and packaged consumer documentation remain incomplete.

PJangler's PM has received the component delivery request. Full BMAD create → repeat → repeat convergence remains a separate, unaccepted gate under the existing PJAN-168 work; registry-only success must not close it or G5 wholesale.

Evidence retained locally by Grolf: independent registry acceptance report, tarball identity, raw health/index/CLI/restart and negative configuration checks. All disposable processes/database resources were removed. No Studio, production database or live configuration was changed.

# Integrated Compose Documentation Validation Report

**Validated:** 2026-07-15

**Implementation base:** `c4f78bbe383a9c1d5ee12e2e81472f6a179b97ad`

**Documentation commit:** `bdbd441a203891bacba55bd3d72cc279264079ac`

**Remediation evidence commit:** the commit containing this report with subject
`fix(platform): harden integrated compose gates`. After integration, resolve its
hash without embedding an impossible self-reference:

```bash
git log -1 --format=%H --fixed-strings \
  --grep='fix(platform): harden integrated compose gates'
```

**Final team checkout:** `/home/delorenj/code/33GOD/worktrees/team-daedalus`

**Read-only source root:** `/home/delorenj/code/33GOD`

## Outcome

The normalized integrated Compose stack and its documentation/governance
projection pass the complete verification matrix. `ROOT-COMPOSE-01` is resolved
by executable render, semantic evidence, and live runtime evidence. Root Compose
owns Bloodbank core, Candystore, and Holocene web. The healthy
`holocene-api.service` remains external by design.

Cloud remains blocked. Its successful render proves the unsupported local-bind
model and rejection gate remain visible; no cloud lifecycle command is
supported.

## Exact drift result

Command:

```bash
GOD_SOURCE_ROOT=/home/delorenj/code/33GOD mise run docs:drift
```

Final summary:

```text
SUMMARY PASS=21 WARN=0 FAIL=0
```

The 21 passes include all prior root/component parity checks plus:

```text
PASS root-compose: compose semantic validation passed: default, tools, full, cloud
PASS doc-markers: no forbidden incomplete markers in 27 Markdown files
PASS doc-links: all Markdown file links resolve
```

## Compose validator and tests

- `python3 33god-platform/scripts/validate-compose.py --source-root
  /home/delorenj/code/33GOD` — passed: default, `tools`, `full`, `cloud`.
- `python3 -m unittest discover -s 33god-platform/tests -p 'test_*.py'
  -v` — 11 tests passed. Coverage includes the populated source render,
  actionable rejection of legacy/false-readiness services, subscription and
  daprd path mutations, Traefik auth/Host attacks, PostgreSQL proxy attachment,
  caller-selected port drift, secret-safe env-file rendering/error handling,
  and rejection of an unpopulated source root.
- `mise run platform:compose:validate` — passed.
- `mise run platform:compose:test` — 11 tests passed.

Rendered service sets:

| Model | Services | Result |
|---|---:|---|
| default | 8 | Bloodbank NATS/init/placement; one Candystore triplet; Holocene preflight/web |
| `tools` | 10 | Default plus run-only PJangler CLI/MCP |
| `full` | 10 | Same currently governed model as `tools` |
| `cloud` | 9 | Default plus `cloud-unsupported`; render-only |

Every JSON render uses `--no-env-resolution`. The semantic validator confirmed
the exact environment-selected ports, Bloodbank/Candystore subscription and
daprd path, start dependencies, host API boundary, no PJangler listeners, exact
service network memberships, Traefik Host/auth/proxy labels, five adopted
external volumes, source-root mounts, and absence of Bloodbank legacy
Candystore. The safe test asserts that sensitive Holocene env-file keys and
values are absent without printing either.

## Platform governance

- `python3 33god-platform/scripts/platform.py validate` — `33GOD platform
  manifest OK` with explicit `GOD_SOURCE_ROOT`.
- `python3 33god-platform/scripts/platform.py components list` — all ten active
  component paths present; the four core manifests report profiles
  `default`, `default`, `default`, and `tools,full`.
- `python3 33god-platform/scripts/platform.py backfills check` — four checks
  returned `OK`.
- Changed structured artifacts parsed successfully: 5 YAML files, 2 root JSON
  state/metadata files, and 5 platform JSONL logs.

## Repository hygiene

- `git diff --check` — passed.
- Secret scan of added lines found the intentionally inherited Candystore
  username/password and `DATABASE_URL` used by the local-development topology.
  Those fixed development-only values were already part of the adopted
  component model; no real operator, hosted, Telegram, provider, or production
  secret value was added. Holocene's ignored env-file values are not rendered.
- Candystore built successfully from the pinned source during root startup.
- Markdown incomplete-marker and internal-link checks — passed in the drift
  gate.
- Component-owned projects were stopped and the root project was started. No
  volume was deleted and the host systemd service was not mutated.

## Runtime result

- Bloodbank NATS, Dapr placement, Candystore PostgreSQL/app/daprd, and Holocene
  web are running under Compose project `33god-platform`.
- NATS reports `BLOODBANK_COMMANDS` and `BLOODBANK_EVENTS` with exactly one
  `candystore-events` consumer and no pending or unacknowledged messages.
- NATS, Candystore health/readiness, Candystore daprd, Holocene host API, and
  Holocene web health checks pass.
- The excluded legacy Bloodbank PostgreSQL container was removed; the separate
  event-toaster consumer remains attached.

Hosted deployment remains unsupported until local binds, external local
networks, host systemd authority, listener/auth risks, local credentials,
single-host storage, tenancy, and backup/restore are replaced by a cloud-owned
design.

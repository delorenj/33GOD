---
epic: GOD-43
parent_epic: GOD-40
title: 'Bloodbank v3 — first real-world events + CI (wave 2)'
status: 'in-flight'
created: '2026-04-28'
related:
  - _bmad-output/planning-artifacts/epic-god-42-v3-stories.md
  - _bmad-output/planning-artifacts/epic-god-42-sanity-check-2026-04-26.md
  - docs/architecture/v3-implementation-plan.md
  - docs/architecture/ADR-0001-v3-platform-pivot.md
  - docs/architecture/ADR-0002-holyfields-scope-refactor.md
  - docs/testing/test-plan.md
---

# Epic GOD-43 — Bloodbank v3 wave 2: First real-world events + CI

GOD-42 closed out the v3 scaffold. This epic captures the wave-2 work
that has shipped or is in flight since 2026-04-19, plus the next
follow-ups. Several stories below are **already DONE** but were merged
without a story shell; documenting them here brings the planning
artifact back in sync with reality.

All stories inherit ADR-0001 (v3 platform pivot) and ADR-0002
(Holyfields scope narrowed to JSON Schema + Pydantic/Zod). The Plane
ticket gate is suspended (`CLAUDE.md`); descriptive branch names and
commit messages serve as the ticket during this epic.

## Scope summary

```
GOD-43 wave 2
  ├── Schemas:    V3-101 (CloudEvents base + agent migration)
  ├── CI:         V3-102 (bloodbank), V3-103 (holyfields)
  ├── Testing:    V3-104 (test plan + 5-layer gate)
  ├── Producers:  V3-105 (heartbeat), V3-106 (claude-code), V3-109 (next variable-payload)
  ├── Trunk:      V3-107 (long-lived branch retired)
  ├── Sandbox:    V3-108 (claude-events compose profile + recorder)
  └── Migration:  V3-110 (legacy agent.* schemas to v3 base)
```

## Story V3-101 — Holyfields v3 CloudEvents base schema

**Status:** DONE (holyfields PR #21, merged 2026-04-23). Documented
retroactively.

**Goal:** Publish the canonical CloudEvents 1.0 envelope with 33GOD
extension fields as the source of truth for all v3 events.

**Files (in holyfields):**
- `holyfields/schemas/_common/cloudevent_base.v1.json`
- `holyfields/tests/test_cloudevent_base.py`

**Given/When/Then:**
- Given the schema, when validated against CloudEvents 1.0 spec, then
  all required CE fields (`specversion`, `id`, `source`, `type`,
  `time`) are present.
- Given the 33GOD extensions, when checked, then `correlationid`,
  `causationid`, `producer`, `service`, `domain`, `schemaref`,
  `traceparent` are documented and required where appropriate.
- Given a producer, when it builds an envelope using this base, then
  `additionalProperties: false` on the data block prevents drift.

## Story V3-102 — Bloodbank CI pipeline

**Status:** DONE (bloodbank PR #29 + metarepo PR #24, merged
2026-04-25). Documented retroactively.

**Goal:** Two-job CI pipeline (static + smoke) gating every PR.

**Files (in bloodbank):**
- `.github/workflows/ci.yml`

**Given/When/Then:**
- Given a PR, when CI runs, then `static-checks` (~18s) executes
  before `smoke-tests` (~5min).
- Given the smoke job, when run, then all five smoke tests
  (`smoketest.sh`, `smoketest-dapr.sh`, `smoketest-dapr-subscribe.sh`,
  `smoketest-command.sh`, `smoketest-heartbeat.sh`) execute and pass.
- Given a smoke-test failure, when CI runs, then container logs and
  NATS stream state are dumped as diagnostics.

## Story V3-103 — Holyfields CI pipeline

**Status:** DONE (holyfields PR #25, merged 2026-04-25). Documented
retroactively.

**Goal:** CI gates schema validity, code generation, drift, and tests.

**Files (in holyfields):**
- `.github/workflows/ci.yml`

**Given/When/Then:**
- Given a schema PR, when CI runs, then it executes: schema lint,
  Python codegen, TypeScript codegen, generated-artifact drift check,
  pytest, mypy/typecheck.
- Given any drift between committed and freshly-regenerated artifacts,
  when CI runs, then the drift step fails the build.
- Given the test job, when run, then 23 tests pass (11 base envelope +
  12 heartbeat).

## Story V3-104 — V3 test plan + CI gate contract

**Status:** DONE (metarepo PR #23, merged 2026-04-25). Documented
retroactively.

**Goal:** Document the five-layer test strategy and the contract
between CI gates so future repos can adopt the same shape.

**Files:**
- `docs/testing/test-plan.md`

**Given/When/Then:**
- Given the doc, when read, then it defines five layers (static,
  unit, schema, smoke, integration) and assigns ownership of each.
- Given a new repo, when bootstrapped, then the doc explains which
  layers are mandatory and which are optional.
- Given a PR gate, when designed against this doc, then it implements
  the static + smoke pair as a minimum.

## Story V3-105 — First real-world event: heartbeat

**Status:** DONE (bloodbank PR #28 + holyfields PR #27, merged
2026-04-26). Documented retroactively.

**Goal:** Production-shape producer + consumer pair emitting and
recording `system.heartbeat.tick` events.

**Files (in bloodbank):**
- `services/heartbeat-tick/{main.py,Dockerfile,README.md}`
- `services/heartbeat-recorder/{main.py,Dockerfile}`
- `compose/v3/docker-compose.yml` (heartbeat profile)
- `ops/v3/smoketest/smoketest-heartbeat.sh`

**Files (in holyfields):**
- `holyfields/schemas/system/heartbeat.tick.v1.json`
- `holyfields/tests/test_heartbeat_tick.py`

**Given/When/Then:**
- Given the heartbeat profile is up, when heartbeat-tick runs for
  ≥10s with a 2s interval, then heartbeat-recorder records ≥5 ticks
  with monotonic `tick_seq` per producer instance.
- Given a producer restart, when consumers inspect
  `/inspect/recorded`, then `tick_seq` resets and `started_at`
  changes — restart detection works.
- Given the smoke test, when run in CI, then it asserts the
  monotonic invariant within a 60s budget.

## Story V3-106 — Claude Code → Bloodbank publisher

**Status:** DONE (metarepo PR #29, merged 2026-04-26). Documented
retroactively.

**Goal:** Claude Code session and tool-use events flow into the v3
bus as CloudEvents envelopes.

**Files (in metarepo):**
- `.claude/hooks/bloodbank-publisher.sh`
- `.claude/hooks/README.md`
- `.claude/settings.json`

**Given/When/Then:**
- Given a `SessionStart` / `PostToolUse` / `Stop` hook, when fired,
  then a CloudEvents 1.0 envelope is POSTed to the local Dapr
  sidecar with `type` in `{agent.session.started, agent.tool.invoked,
  agent.session.ended}`.
- Given the Dapr sidecar is unreachable, when the hook fires, then
  the hook exits 0 silently and writes a rotated error-log line to
  `.claude/sessions/publish-errors.log`.
- Given the heartbeat profile is up, when a hook fires, then the
  envelope appears on `event.agent.*` subjects in
  `BLOODBANK_V3_EVENTS`.

## Story V3-107 — Trunk cutover

**Status:** DONE (bloodbank PR #26, merged 2026-04-25). Documented
retroactively.

**Goal:** Retire the long-lived `v3-refactor` branch and adopt
trunk-based main with PR gating.

**Files (in bloodbank):**
- `.github/workflows/ci.yml` (trigger cleanup)
- `README.md` (branch policy)

**Given/When/Then:**
- Given the cutover, when inspected, then `main` contains the v3
  scaffold + wave-2 work as the default branch.
- Given CI triggers, when checked, then they fire on PRs to `main`
  and pushes to `main` only — no longer on `v3-refactor`.
- Given a feature branch policy, when enforced, then it follows the
  pattern documented in `git-workflow-and-versioning` (short-lived,
  ~1-3 days, descriptive name).

## Story V3-108 — Dedicated `claude-events` compose profile + recorder

**Status:** Pending. Today the Claude Code publisher piggybacks on
`daprd-heartbeat` (works because Dapr publish is generic). When
query/inspection of the `agent.*` stream becomes a recurring need, a
dedicated profile improves separation of concerns.

**Files (in bloodbank, planned):**
- `compose/v3/docker-compose.yml` (new `claude-events` profile)
- `services/claude-events-recorder/{main.py,Dockerfile,README.md}`
- `ops/v3/smoketest/smoketest-claude-events.sh`

**Given/When/Then:**
- Given the profile is up, when an `agent.*` event lands, then the
  recorder captures it with `/inspect/recorded` matching the heartbeat
  pattern.
- Given the publisher hook config, when updated, then
  `BLOODBANK_DAPR_URL` defaults to the new sidecar's host port.
- Given a smoke test, when run in CI, then a synthetic
  `agent.session.started` round-trips and the recorder asserts shape.

## Story V3-109 — Next real-world event with payload variability

**Status:** Pending. The heartbeat (V3-105) and claude-code (V3-106)
events partially satisfy this — the latter has true payload
variability. A third, non-agent event (e.g.
`code.commit.created`, `artifact.build.completed`) would prove the
generality of the platform across domains.

**Files (in holyfields, planned):**
- `holyfields/schemas/<domain>/<entity>.<action>.v1.json`
- `holyfields/tests/test_<entity>_<action>.py`

**Files (in bloodbank, planned):**
- producer service or smoke test exercising the new contract

**Given/When/Then:**
- Given a new domain (not `system`, not `agent`), when an event ships,
  then it extends `_common/cloudevent_base.v1.json` and follows the
  pattern reference in `claude-code-event-publishing.md`.
- Given the producer, when run, then the envelope passes schema
  validation and lands on the corresponding NATS subject.

## Story V3-110 — Migrate legacy agent.* schemas to v3 base

**Status:** Pending. Today's `agent.session.{started,ended}` and
`agent.tool.invoked` schemas in Holyfields extend the legacy
`base_event.v1.json`. The publisher emits v3-shaped envelopes
inline. Authoring v3 versions and wiring strict validation in CI
closes the loop.

**Files (in holyfields, planned):**
- `holyfields/schemas/agent/session.started.v2.json` (or rev v1 in
  place if no consumers depend on v1)
- `holyfields/schemas/agent/session.ended.v2.json`
- `holyfields/schemas/agent/tool.invoked.v2.json`
- `holyfields/tests/test_agent_*.py`

**Files (in metarepo, planned):**
- `.claude/hooks/bloodbank-publisher.sh` (consume generated Pydantic)

**Given/When/Then:**
- Given the v3 schemas, when validated, then they extend
  `_common/cloudevent_base.v1.json` and lock `type`/`domain` via
  `const`.
- Given the publisher, when refactored, then it builds envelopes via
  the generated Pydantic models (or remains inline-built but with a
  CI gate that round-trips a sample envelope through schema
  validation).
- Given CI, when run on holyfields, then `agent.*.v2` schemas have
  the same test coverage as `system.heartbeat.tick.v1`.

## Dependency order

```
V3-101 (CE base)  ── done
  ├── V3-102 (BB CI)            ── done
  ├── V3-103 (HF CI)            ── done
  └── V3-104 (test plan)        ── done

V3-105 (heartbeat)              ── done    (depends on V3-101)
V3-106 (claude publisher)       ── done    (depends on V3-101)
V3-107 (trunk cutover)          ── done

V3-108 (claude-events profile)  ── pending (depends on V3-106)
V3-109 (third domain event)     ── pending (depends on V3-101)
V3-110 (agent v3 migration)     ── pending (depends on V3-106 + V3-101)
```

Group A (done): V3-101, V3-102, V3-103, V3-104, V3-105, V3-106, V3-107.
Group B (next): V3-108, V3-109, V3-110 — independent of each other.

## Definition of done for the epic

- [ ] V3-108: dedicated profile + recorder shipping with smoke gate
- [ ] V3-109: at least one event outside `system` and `agent` domains
- [ ] V3-110: agent.* schemas extend `cloudevent_base.v1.json` and
      have CI test coverage
- [ ] All seven retroactive stories (V3-101…V3-107) have a one-line
      verification entry in `bloodbank/docs/architecture/verification-log.md`

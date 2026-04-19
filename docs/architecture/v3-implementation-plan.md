# 33GOD Event Platform v3 — Implementation Plan

**Status:** Source of truth (promoted from `bloodbank/v3-implementation-plan.md` on 2026-04-19 under GOD-42).
**Scope:** Cross-component pivot covering Bloodbank (runtime/ops), Holyfields (contracts/generation), and metarepo-level platform wiring (Dapr runtime, NATS JetStream, EventCatalog, Apicurio Registry).
**Companion:** [ADR-0001](./ADR-0001-v3-platform-pivot.md) — codified non-negotiable decisions.
**Epic:** GOD-40 Blood Bank Event Backbone Rebuild → Story GOD-42.

This document is the execution plan for the 33GOD v3 event platform pivot. It
is meant to be followed by a mixed-seniority team without reinterpreting the
architecture on every ticket.

Use this plan as the source of truth for Plane ticket decomposition and
component coordination. Component-local specialization (e.g. Holyfields
contract generation specifics) lives in those component repos; cross-component
contracts and runtime decisions live here.

## Current baseline

The starting point is the Bloodbank submodule on branch `v3-refactor`, created
from commit `14d9122`, with preservation tag `pre-preservation-2026-04-19` on
its remote. The parent 33GOD repository references the `v3-refactor` submodule
commit after the 2026-04-19 slimdown (GOD-41).

Cleanup deletions from the pruning pass were intentionally committed. Do not
revert them without explicit user direction. New v3 work lands in clearly
named `v3` paths so it does not depend on removed legacy files.

## Source documents

Read these before editing code or tickets:

- `docs/architecture/ADR-0001-v3-platform-pivot.md` (decision ratification)
- `bloodbank/docs/architecture/bloodbank-vnext.md`
- `bloodbank/docs/architecture/dapr-vs-faststream.md`
- `bloodbank/docs/architecture/overhaul-backlog.md`
- `bloodbank/GOD.md` (legacy v2 context)
- `bloodbank/README.md`
- `AGENTS.md` (metarepo)
- `services/registry.yaml` (surviving service topology)

The vNext docs inside bloodbank define the target bloodbank-internal
architecture. Metarepo-level architecture decisions are in ADR-0001 and this
document.

## Non-negotiable architecture decisions

Ratified in ADR-0001. Do not reopen inside implementation tickets.

- **Runtime platform:** Dapr.
- **Broker:** NATS JetStream.
- **Immutable event envelope:** CloudEvents 1.0.
- **Command envelope:** separate from events (mutable, correlated).
- **Contract description:** AsyncAPI.
- **Human/agent discovery:** EventCatalog.
- **Runtime schema governance:** Apicurio Registry.
- **Local + self-hosted deployment:** Docker Compose.
- **Bloodbank CLI role:** operator tool, not the primary production publish path.
- **Holyfields role:** central contract and service registry.
- **Business event schemas:** owned by their producing services and registered
  via Holyfields. Bloodbank does not own business schemas.

## Repository boundaries

This plan separates Bloodbank and Holyfields by intent.

**Bloodbank owns runtime and operations** (inside the `bloodbank/` submodule):

- Dapr component manifests (pubsub, statestore, secretstore).
- NATS JetStream bootstrap (streams, subjects, retention).
- Compose files for the platform sandbox.
- Operator CLI scaffolding (`bb_v3` doctor / trace / replay / emit).
- Adapter migration points (hookd, openclaw, infra_dispatcher).
- Replay, trace, and dead-letter tools.
- Documentation that explains how to operate v3.

**Holyfields owns contracts and generation** (inside the `holyfields/` submodule):

- CloudEvents base schema.
- Command envelope schema.
- Service-level AsyncAPI documents.
- Service-owned event and command schemas.
- Generated Python and TypeScript SDKs.
- EventCatalog source and generated catalog output.
- Apicurio schema synchronization.

**Metarepo owns cross-component coordination** (here):

- This implementation plan.
- ADR-0001 decision record.
- Plane epic + story tracking (GOD-40, GOD-42).
- Cross-repo integration checkpoints.
- Smoke test definitions spanning multiple components.

If a ticket requires editing `holyfields/` from a Bloodbank ticket, do that
work in the Holyfields repo or a dedicated Holyfields ticket. Do not hide
Holyfields changes inside Bloodbank.

## Target Bloodbank v3 layout

Paths are relative to `bloodbank/` inside the metarepo.

```text
bloodbank/
  compose/
    v3/
      docker-compose.yml
      README.md
      components/
        pubsub.yaml
        statestore.yaml
        secretstore.yaml
      nats/
        README.md
        streams.json
      apicurio/
        README.md
      eventcatalog/
        README.md
  ops/
    v3/
      bootstrap/
        README.md
        check-platform.sh
      trace/
        README.md
      replay/
        README.md
  cli/
    v3/
      README.md
      bb_v3.py
  adapters/
    v3/
      README.md
      hookd/
        README.md
      openclaw/
        README.md
      infra_dispatcher/
        README.md
  docs/
    architecture/
      bloodbank-vnext.md
      dapr-vs-faststream.md
      overhaul-backlog.md
      v3-holyfields-contract-work.md
```

The first scaffold must be documentation-heavy and safe. Do not wire
production traffic to Dapr or NATS in the first pass.

## Naming rules

- Plane parent story: `GOD-42` (in `33GOD Infrastructure` project).
- Implementation ticket series: `BB-*` (in `Bloodbank` Plane project), tagged
  `v3-refactor` label.
- Holyfields tracker: one `HOLYF-*` ticket referenced by BB implementation tickets.
- Branch name (in bloodbank): `v3-refactor`.
- Compose project name: `bloodbank-v3`.
- Dapr pub/sub component name: `bloodbank-v3-pubsub`.
- Dapr app ID prefix: `bloodbank-v3-`.
- NATS stream for immutable events: `BLOODBANK_V3_EVENTS`.
- NATS stream for commands: `BLOODBANK_V3_COMMANDS`.
- NATS subject prefix for events: `event.`
- NATS subject prefix for commands: `command.`
- NATS subject prefix for replies: `reply.`

## Message contracts

Bloodbank must not invent business schemas. The temporary local examples below
exist only to prove platform plumbing until Holyfields-generated packages are
available.

**Immutable event envelope (CloudEvents 1.0 + 33GOD extensions):**

```json
{
  "specversion": "1.0",
  "id": "uuid",
  "source": "urn:33god:service:example",
  "type": "artifact.created",
  "subject": "artifact/example-id",
  "time": "2026-04-12T00:00:00Z",
  "datacontenttype": "application/json",
  "dataschema": "urn:33god:holyfields:schema:artifact.created.v1",
  "correlationid": "uuid",
  "causationid": "uuid-or-null",
  "producer": "example-service",
  "service": "artifact-service",
  "domain": "artifact",
  "schemaref": "artifact.created.v1",
  "traceparent": "w3c-trace-context",
  "data": {}
}
```

**Command envelope:**

```json
{
  "command_id": "uuid",
  "command_type": "artifact.rebuild",
  "target_service": "artifact-service",
  "issued_by": "operator-or-service",
  "issued_at": "2026-04-12T00:00:00Z",
  "timeout_ms": 300000,
  "correlation_id": "uuid",
  "causation_id": "uuid-or-null",
  "reply_to": "reply.artifact-service.rebuild",
  "payload_schema": "artifact.rebuild.v1",
  "payload": {}
}
```

## Developer workflow

For every implementation ticket:

1. Read this plan and the ticket acceptance criteria.
2. Confirm the current branch is `v3-refactor` (inside bloodbank) or the
   appropriate component branch.
3. Confirm the ticket path scope before editing.
4. Make only the files required by the ticket.
5. Run the ticket-specific verification command.
6. Run a local self-review.
7. Ask for spec review.
8. Ask for code quality review.
9. Mark the ticket complete only after both reviews pass.

Do not mark a ticket complete if verification was skipped.

## Verification commands

First scaffold wave:

```bash
# Inside bloodbank submodule
git status --short
python -m compileall cli/v3
bash ops/v3/bootstrap/check-platform.sh
```

`check-platform.sh` must not require Docker to be running. It validates file
presence and static configuration only.

Once the Compose stack exists, this optional manual check:

```bash
docker compose -f bloodbank/compose/v3/docker-compose.yml config
```

Baseline verification must not require network access or pulling images.

## Plane ticket set

### Parent (metarepo)

Story `GOD-42` — **Rebuild Blood Bank as NATS-based event backbone**
(child of epic `GOD-40 Blood Bank Event Backbone Rebuild`).

Description pointer: this file + ADR-0001.

### Child implementation tickets (Bloodbank project)

Each is a `BB-*` ticket linked to `GOD-42` via the description. Create these
under the Bloodbank Plane project; apply label `v3-refactor`.

| ID | Title | Scope |
|---|---|---|
| V3-001 | Sync Bloodbank submodule baseline | Confirm branch, record starting commit, preserve cleanup deletions |
| V3-002 | Create v3 Compose scaffold | `compose/v3/` docker-compose.yml + component dirs |
| V3-003 | Add Dapr component manifests | pubsub.yaml, statestore.yaml, secretstore.yaml |
| V3-004 | Define NATS JetStream topology | streams.json + README defining subjects, retention, DLQ |
| V3-005 | Add operator CLI v3 skeleton | `bb_v3` with doctor/trace/replay/emit stubs |
| V3-006 | Add platform bootstrap check | `check-platform.sh` static validator |
| V3-007 | Add replay and trace docs | operator workflow documentation |
| V3-008 | Add adapter migration scaffolds | hookd, openclaw, infra_dispatcher README stubs |
| V3-009 | Link implementation plan from architecture docs | cross-reference sweep |
| V3-010 | Create Holyfields contract work tracker | tracker in Holyfields project + link from here |
| V3-011 | Verify first scaffold wave | run all static checks + document results |

Full acceptance criteria per ticket live in the Plane issues and in the
per-story BMAD files at `_bmad-output/planning-artifacts/story-v3-*.md`.

### Child tracker (Holyfields project)

Create one `HOLYF-*` ticket linked from V3-010:

- CloudEvents base schema registration
- Command envelope schema registration
- AsyncAPI document template
- SDK generation pipeline (Python + TypeScript)
- EventCatalog source
- Apicurio synchronization script

Mark as external to Bloodbank; block V3 production rollout until this work
closes.

## Subagent orchestration protocol

Use subagent-driven development for the scaffold wave.

**Controller rules:**

- Dispatch a fresh implementer subagent per ticket.
- Do not dispatch multiple implementer subagents in parallel.
- Give each subagent the full ticket text from this plan + its Plane issue.
- Give each subagent the exact allowed write paths.
- Require each implementer to self-review before returning.
- Dispatch a spec reviewer after implementation.
- Dispatch a code quality reviewer only after spec review passes.
- If a reviewer finds issues, send the issue list back to the implementer and
  re-review.
- Mark a Plane ticket complete only after both review stages pass.

For the first session, scaffold tickets may be grouped only when their write
sets are disjoint and the controller can still review them thoroughly:

- **Group A:** V3-002, V3-003, V3-004 — platform files under `compose/v3/`
- **Group B:** V3-005, V3-006 — operator CLI and bootstrap checks under
  `cli/v3/` and `ops/v3/bootstrap/`
- **Group C:** V3-007, V3-008, V3-009, V3-010 — docs and adapter scaffolds

V3-011 is not grouped; it is a verification gate after the scaffold groups.

## Stop conditions

Stop and ask for direction if any of these happen:

- A ticket requires editing `holyfields/` from the Bloodbank submodule.
- A migration would route live production traffic to Dapr or NATS.
- The cleanup delete set needs to be reverted.
- Plane API creation fails after authentication and endpoint checks.
- Docker Compose requires pulling images during a static verification step.
- ADR-0001's non-negotiable decisions appear to require revisiting (escalate
  before proceeding).

## Sprint one definition of done

- `GOD-42` story is linked to ADR-0001 and this plan.
- All `BB-*` child tickets exist under the V3 set in the Bloodbank project.
- `HOLYF-*` tracker ticket exists and is linked from V3-010.
- The Bloodbank v3 scaffold exists under the target paths.
- The operator CLI and bootstrap check compile or run locally.
- The implementation plan is linked from the bloodbank architecture docs.
- Spec review and code quality review have passed for the scaffold wave.

## Extraction provenance

This document was extracted from `bloodbank/v3-implementation-plan.md` to the
metarepo on 2026-04-19 under Plane GOD-42 because the plan spans multiple
components (Bloodbank, Holyfields, services/, metarepo-level platform
wiring). The bloodbank copy remains in place for backward compatibility of
deep links; this metarepo copy is the source of truth going forward. When
the first V3 implementation ticket lands, a short stub in bloodbank will
redirect deep links to this file.

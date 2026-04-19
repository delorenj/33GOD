---
epic: GOD-42
parent_epic: GOD-40
title: 'Rebuild Blood Bank as NATS-based event backbone (v3 pivot)'
status: 'ready-for-dev'
created: '2026-04-19'
related:
  - docs/architecture/v3-implementation-plan.md
  - docs/architecture/ADR-0001-v3-platform-pivot.md
---

# Epic GOD-42 — Blood Bank v3 Pivot: Story Breakdown

Per the v3 implementation plan and ADR-0001. Stories map 1:1 to Plane
implementation tickets (V3-001 through V3-011) to be created in the Bloodbank
(BB) Plane project, plus one cross-component tracker in the Holyfields
(HOLYF) project.

All stories inherit the non-negotiable architecture decisions in ADR-0001.
Each story's acceptance criteria must be checked as Given/When/Then before
marking the ticket complete; reviewers cross-check against ADR-0001 and the
implementation plan.

## Story V3-001 — Sync Bloodbank submodule baseline

**Goal:** Establish a clean, documented starting point on the `v3-refactor`
branch of the bloodbank submodule.

**Files touched:** None. This ticket records state only.

**Given/When/Then:**
- Given the bloodbank submodule on remote `v3-refactor`, when the ticket
  owner inspects branch state, then branch is `v3-refactor` with preservation
  tag `pre-preservation-2026-04-19` already present on the remote.
- Given the cleanup delete set from the 2026-04-19 pruning pass, when the
  ticket owner reviews the working tree, then no cleanup deletions have been
  reverted.
- Given the ticket, when linked documents are checked, then the description
  links to `docs/architecture/v3-implementation-plan.md` and ADR-0001.

## Story V3-002 — Create v3 Compose scaffold

**Goal:** Stand up the `bloodbank/compose/v3/` Docker Compose skeleton for
the v3 platform.

**Files touched (inside bloodbank/):**
- `compose/v3/docker-compose.yml`
- `compose/v3/README.md`
- `compose/v3/components/` (dir, for V3-003)
- `compose/v3/nats/` (dir, for V3-004)
- `compose/v3/apicurio/README.md`
- `compose/v3/eventcatalog/README.md`

**Given/When/Then:**
- Given the scaffold in place, when `docker compose -f bloodbank/compose/v3/docker-compose.yml config` runs, then it parses without error and lists services `nats`, `dapr-placement`, `apicurio-registry`, `eventcatalog`.
- Given the Compose file, when inspected, then no services reference v2
  RabbitMQ containers or the `33god-rabbitmq` network.
- Given the service naming, when checked against ADR-0001, then names and
  labels use the `bloodbank-v3` compose project prefix.

## Story V3-003 — Add Dapr component manifests

**Goal:** Provide static Dapr component definitions for pubsub, statestore,
and secretstore.

**Files touched (inside bloodbank/):**
- `compose/v3/components/pubsub.yaml`
- `compose/v3/components/statestore.yaml`
- `compose/v3/components/secretstore.yaml`

**Given/When/Then:**
- Given the pubsub manifest, when parsed, then it targets NATS JetStream and
  is named `bloodbank-v3-pubsub`.
- Given any manifest, when inspected, then no secret values are literal;
  values either reference Dapr secret store or use placeholder env vars
  prefixed `BLOODBANK_V3_`.
- Given `compose/v3/README.md`, when read, then all three manifests are
  documented with a one-paragraph purpose statement each.

## Story V3-004 — Define NATS JetStream topology

**Goal:** Lock the stream names, subject conventions, retention posture, and
replay semantics before any publishing code lands.

**Files touched (inside bloodbank/):**
- `compose/v3/nats/streams.json`
- `compose/v3/nats/README.md`

**Given/When/Then:**
- Given `streams.json`, when parsed, then it defines exactly
  `BLOODBANK_V3_EVENTS` and `BLOODBANK_V3_COMMANDS` with subject patterns
  `event.>`, `command.>`, and `reply.>`.
- Given the README, when read, then it explains retention window,
  dead-letter strategy, and replay preservation of original IDs.
- Given the topology, when checked against ADR-0001, then it introduces no
  coupling to RabbitMQ.

## Story V3-005 — Add operator CLI v3 skeleton

**Goal:** Produce a safe, side-effect-free CLI scaffold for v3 operator
workflows.

**Files touched (inside bloodbank/):**
- `cli/v3/README.md`
- `cli/v3/bb_v3.py`

**Given/When/Then:**
- Given the scaffold, when `python -m compileall cli/v3` runs, then it
  exits 0.
- Given `python cli/v3/bb_v3.py doctor`, when run against a complete
  scaffold, then it reports success without performing any network I/O.
- Given the CLI, when any subcommand is invoked (`doctor`, `trace`,
  `replay`, `emit`), then no production traffic is published.

## Story V3-006 — Add platform bootstrap check

**Goal:** Provide a junior-friendly verification script that catches missing
scaffold pieces without requiring Docker, Dapr, or network access.

**Files touched (inside bloodbank/):**
- `ops/v3/bootstrap/README.md`
- `ops/v3/bootstrap/check-platform.sh`

**Given/When/Then:**
- Given a complete scaffold, when `bash ops/v3/bootstrap/check-platform.sh`
  runs, then it exits 0 and prints a `PASS` line per checked artifact.
- Given a missing file, when the script runs, then output names the missing
  file and the exit code is non-zero.
- Given the script, when inspected, then it performs no Docker, Dapr, NATS,
  or network calls.

## Story V3-007 — Add replay and trace docs

**Goal:** Document operator expectations for replay and trace workflows
before implementing real tooling.

**Files touched (inside bloodbank/):**
- `ops/v3/replay/README.md`
- `ops/v3/trace/README.md`

**Given/When/Then:**
- Given the replay doc, when read, then it defines what data is safe to
  replay and states that replays preserve original IDs while adding replay
  metadata.
- Given the trace doc, when read, then it defines the expected use of
  `correlation_id`, `causation_id`, and `traceparent`.
- Given either doc, when read, then it does not claim production replay or
  trace tooling is implemented yet.

## Story V3-008 — Add adapter migration scaffolds

**Goal:** Prepare migration directories that bridge v2 consumers to v3
without writing migration code yet.

**Files touched (inside bloodbank/):**
- `adapters/v3/README.md`
- `adapters/v3/hookd/README.md`
- `adapters/v3/openclaw/README.md`
- `adapters/v3/infra_dispatcher/README.md`

**Given/When/Then:**
- Given each adapter README, when read, then it names the v2 component it
  replaces and the v3 publish path via Holyfields-generated contracts +
  Dapr + NATS.
- Given any adapter directory, when inspected, then it contains no
  executable migration code (docs and stubs only in this wave).
- Given the top-level `adapters/v3/README.md`, when read, then it states
  that adapters must not invent local envelopes.

## Story V3-009 — Link implementation plan from architecture docs

**Goal:** Make the plan discoverable from where readers already look.

**Files touched (inside bloodbank/):**
- `README.md`
- `docs/architecture/README.md`
- `docs/architecture/overhaul-backlog.md`

**Given/When/Then:**
- Given each linking file, when a reader follows the link, then it resolves
  to `docs/architecture/v3-implementation-plan.md` in the metarepo (not the
  legacy bloodbank copy).
- Given `bloodbank/GOD.md`, when read, then it remains clearly marked as
  legacy v2 / current-state context.
- Given the architecture index, when read, then it also links to the
  Holyfields contract work tracker (V3-010 output).

## Story V3-010 — Create Holyfields contract work tracker

**Goal:** Document the Holyfields-side work that must happen in a sibling
repo, without editing Holyfields from Bloodbank.

**Files touched (inside bloodbank/):**
- `docs/architecture/v3-holyfields-contract-work.md`

**Plane side effect:** one `HOLYF-*` ticket is created in the Holyfields
Plane project, linked from this file.

**Given/When/Then:**
- Given the tracker doc, when read, then it lists: CloudEvents base schema,
  command envelope schema, AsyncAPI template, SDK generation pipeline
  (Python + TypeScript), EventCatalog source, Apicurio sync.
- Given the tracker, when checked against the bloodbank repo, then no
  Holyfields code is edited from this ticket.
- Given the Plane tracker ticket, when checked, then it is linked from
  this doc and from `GOD-42`.

## Story V3-011 — Verify first scaffold wave

**Goal:** Run the full static verification suite and record results before
declaring sprint one done.

**Files touched:** None (verification only; may append to a
`docs/architecture/verification-log.md` inside bloodbank).

**Verification commands:**
```bash
# inside bloodbank/
git status --short
python -m compileall cli/v3
bash ops/v3/bootstrap/check-platform.sh
docker compose -f compose/v3/docker-compose.yml config   # optional
```

**Given/When/Then:**
- Given the scaffold wave is complete, when static checks run, then all
  three required commands exit 0.
- Given Docker Compose is not available or requires image pulls, when the
  optional check is skipped, then the skip is documented with the reason.
- Given both reviews (spec review + code quality review) are complete, when
  statuses are checked in Plane, then both show passing before this ticket
  closes.

## Dependency order

```
V3-001 (baseline)
  ├── V3-002 (compose scaffold)
  │     ├── V3-003 (dapr manifests)
  │     └── V3-004 (nats topology)
  ├── V3-005 (cli skeleton)
  ├── V3-006 (bootstrap check)
  ├── V3-007 (replay + trace docs)
  ├── V3-008 (adapter scaffolds)
  ├── V3-009 (cross-references)
  └── V3-010 (holyfields tracker)
V3-011 (verify)   ← blocked by all of the above
```

Grouping permitted per the plan's subagent orchestration protocol:
Group A = V3-002 + V3-003 + V3-004; Group B = V3-005 + V3-006;
Group C = V3-007 + V3-008 + V3-009 + V3-010. V3-011 is ungrouped.

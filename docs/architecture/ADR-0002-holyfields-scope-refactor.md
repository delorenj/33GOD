# ADR-0002: Holyfields Scope Refactor — schemas + generators, not a platform

**Status:** Accepted
**Date:** 2026-04-24
**Amends:** [ADR-0001](./ADR-0001-v3-platform-pivot.md) (Role reassignments, Contracts and discovery)
**Supersedes:** the implicit scope creep in ADR-0001 that assigned AsyncAPI authorship, EventCatalog ownership, and runtime service responsibilities to Holyfields.

## Context

ADR-0001 assigned Holyfields the role of "central contract and service registry" and
made it responsible for:

- CloudEvents base schema
- Command envelope schema
- Per-service AsyncAPI documents
- Per-event and per-command schemas
- Generated Python and TypeScript SDKs
- EventCatalog source
- Apicurio schema synchronization

That framing turned Holyfields into a platform the team would need to build and
operate. An audit of the actual `holyfields/` submodule on 2026-04-24 shows a much
narrower and more useful shape already shipping:

- A git repo of ~30+ JSON Schema files under `schemas/` (artifact, session, agent,
  command, llm, asset domains)
- Build-time generators that produce Pydantic models (`src/holyfields/generated/python/`)
  and Zod schemas (`src/holyfields/generated/typescript/`) from those JSON Schemas
- A Python package (`holyfields` on pyproject) and an npm package (`holyfields` in
  package.json) that services depend on at build/import time

Holyfields has no running service, no AsyncAPI artifacts, no EventCatalog
integration, and no Apicurio sync. The v3 stack landed after the ADR-0001
framing was written (Dapr, NATS JetStream, Apicurio Registry, EventCatalog), and
those runtime pieces cover concerns that Holyfields was implicitly going to
re-implement.

The trigger for this ADR: before we invest build effort in AsyncAPI generation,
EventCatalog pipelines, and Apicurio sync code inside Holyfields, we reevaluated
whether Holyfields should own those at all.

## Decision

Holyfields' scope is narrowed to two responsibilities:

1. **Source of truth for event and command payload JSON Schemas.** Humans edit
   schemas here; nowhere else.
2. **Build-time generator for Pydantic (Python) and Zod (TypeScript) artifacts**
   published as versioned packages (`holyfields` on PyPI, `holyfields` on npm).

Everything else the ADR-0001 framing assigned to Holyfields moves out:

| Concern | Previous plan (ADR-0001) | New home |
|---|---|---|
| Per-service AsyncAPI authorship | Holyfields | The service itself (lives in its own repo) |
| EventCatalog source | Holyfields | CI aggregator that collects every service's AsyncAPI + reads Apicurio |
| Apicurio sync | Holyfields-as-platform | Holyfields CI step (one-way: git → Apicurio), not a runtime role |
| Runtime schema registry | Holyfields | **Apicurio Registry** (already in the v3 stack) |
| Service contract discovery surface | Holyfields | **EventCatalog** (already in the v3 stack) |
| Service contract description format | Holyfields-invented | **AsyncAPI 3.0**, one per service |

Holyfields becomes boring library infrastructure. That is the point.

## The mental model (toy example)

A `weather-service` wants to publish `weather.reading.recorded` events.

| Artifact | Lives where | Who edits | Who reads |
|---|---|---|---|
| `reading.recorded.v1.json` payload schema | `holyfields/schemas/weather/reading.recorded.v1.json` | Human, in Holyfields repo | All generators below |
| `WeatherReadingRecordedV1` Pydantic class | Generated, published as `holyfields` Python package | Never edited directly | `weather-service` imports it |
| Zod schema | Generated, published as `holyfields` npm package | Never edited directly | Frontends / TS consumers |
| Apicurio registry entry | `apicurio://holyfields/weather.reading.recorded/versions/1` | CI, from Holyfields repo on merge | Runtime validators, future Dapr middleware |
| `weather-service/asyncapi.yaml` | Inside `weather-service` repo | The service team | EventCatalog build step |
| EventCatalog static site | CI output, aggregated from all service AsyncAPI + Apicurio | CI | Humans, agents browsing events |

**One-line mental model:** Holyfields is the source (git). Apicurio is the
distribution (runtime registry). AsyncAPI is each service's declaration of
intent. EventCatalog is the human-readable lobby. CI is the glue.

You never edit the same thing in two places. Payload schemas only in Holyfields.
Service intent only in the service's own AsyncAPI. Apicurio and EventCatalog are
machine-populated.

## What Holyfields explicitly does NOT do

- **Does not run as a service.** No FastAPI, no Dapr sidecar, no HTTP endpoints.
  It is a git repo plus two published packages.
- **Does not own AsyncAPI documents.** Each service authors its own AsyncAPI
  describing which events it publishes and consumes. AsyncAPI references
  Holyfields JSON Schemas by URI.
- **Does not generate EventCatalog.** A separate CI aggregator pulls every
  service's AsyncAPI + Apicurio metadata and feeds EventCatalog.
- **Does not act as the runtime schema registry.** That is Apicurio's job.
  Services consuming schemas at runtime call Apicurio, not Holyfields.
- **Does not validate events at publish time.** Publish-time validation, if
  ever added, lives in a Dapr pub/sub middleware that consults Apicurio.
  Holyfields is a build-time concern only.

## Responsibility boundaries

### Holyfields (this component) owns

- `holyfields/schemas/**/*.json` — JSON Schema source of truth
- `holyfields/src/holyfields/generated/python/**` — generated Pydantic (do not edit)
- `holyfields/src/holyfields/generated/typescript/**` — generated Zod (do not edit)
- `holyfields/scripts/**` — generation and validation scripts
- `holyfields/.github/workflows/sync-to-apicurio.yml` — CI that pushes schemas
  to Apicurio on merge (one-way, additive, versioned)
- `holyfields` package publication (PyPI + npm)

### Services (consumers) own

- Their own `asyncapi.yaml` (or equivalent) describing what they publish and
  consume
- A pinned dependency on a specific `holyfields` package version
- Their own CI to validate that AsyncAPI references resolve against the pinned
  Holyfields version

### Apicurio (v3 stack) owns

- Runtime schema storage, versioning, compatibility checks
- REST API for runtime consumers that need to fetch schemas by URI
- One artifact group per schema authority. Holyfields publishes under
  `groupId=holyfields`. Services that generate their own schemas outside
  Holyfields (rare; treated as an exception) use their own group.

### EventCatalog (v3 stack) owns

- The human-readable discovery site
- Consumes: aggregated AsyncAPI (per service) + Apicurio metadata
- Rebuilds on merge to any service's main branch

### CI (the glue) owns

- **Holyfields CI:** validate JSON Schemas → generate Pydantic + Zod → publish
  packages → push schemas to Apicurio (new version when content hash changes)
- **Service CI:** validate `asyncapi.yaml` resolves against pinned Holyfields
  version → deploy service with that version pinned
- **EventCatalog CI:** aggregate all services' AsyncAPI → enrich from Apicurio
  → rebuild static site

## Consequences

### Positive

- **Holyfields becomes boring.** It does one thing: schemas in, typed bindings
  out. Low bus-factor, low ongoing maintenance, easy to reason about.
- **Service teams own their contracts.** AsyncAPI lives next to the code that
  publishes. When a service changes what it emits, the change is atomic with
  the service PR. No "update two repos" footgun.
- **Apicurio is used as designed.** It is a runtime registry. We do not
  reimplement it. Versioning, compatibility checks, and discovery come for free.
- **EventCatalog is populated by a standard source.** Aggregating AsyncAPI
  documents is an off-the-shelf pattern; we do not write catalog generation
  ourselves.
- **No new runtime service to operate.** Holyfields stays a library + CI
  pipeline. Less ops surface.

### Negative / costs

- **CI aggregation for EventCatalog is new ground.** We have no aggregator
  today. First service that ships an AsyncAPI forces us to build it. Mitigation:
  small, well-scoped script; can live in a dedicated repo or under 33GOD.
- **Cross-service refactors require touching multiple AsyncAPI files.** If we
  rename `event.artifact.created` to `event.artifact.registered`, every service
  that publishes or subscribes to it edits its own AsyncAPI. This is honestly a
  *feature* (change surface is explicit) but it is more work than a single-repo
  rename in a hypothetical Holyfields-owns-everything model.
- **The Holyfields-to-Apicurio CI sync is a small new piece we must build.**
  It is a few dozen lines of Python or shell hitting Apicurio's REST API. Not
  a real cost, but call it out so it does not get missed.

### Neutral / deferred

- **Publish-time schema validation in Dapr pub/sub.** Deferred. Would require
  a custom Dapr middleware that calls Apicurio before forwarding to NATS.
  Useful for strict contract enforcement, not required for v3 scaffold.
- **Replay / projection rebuild support.** Not a Holyfields concern.
  Documented under Bloodbank `ops/v3/replay/README.md`.
- **Cross-language SDK targets beyond Python + TypeScript.** Not a problem
  until we have a service in another language. Rust, Go, etc. can be added as
  generation targets later without changing the scope decision here.

## Alternatives considered

- **Keep Holyfields as-planned (full platform).** Rejected. Reinvents Apicurio
  and EventCatalog. Ongoing maintenance cost with no unique value over the v3
  off-the-shelf components.
- **Delete Holyfields; put schemas directly in Apicurio as source of truth.**
  Rejected. Throws away working generation tooling and the ~30+ schemas already
  under git review history. Apicurio's UI is not a comfortable schema editing
  surface. Git with review is the right human-facing surface.
- **Let each service define its own payload schemas inline in its AsyncAPI.**
  Rejected. Duplication would be immediate (every service redefines
  `correlationid`, `causationid`, etc.). Cross-service schema reuse needs a
  shared source, which is Holyfields.
- **Centralize AsyncAPI authorship in Holyfields.** Rejected. AsyncAPI
  describes *what a service does*, and should live with that service so the
  declaration is atomic with the code change.

## Implementation

This ADR is a scope decision, not a rewrite. Holyfields does not lose any
current capability. The change is what we *do not* build on top of it.

Immediate implications on existing work:

1. **Update ADR-0001 cross-references.** The ADR-0001 role-reassignments
   section says Holyfields "owns CloudEvents base schema, command envelope
   schema, per-service AsyncAPI documents, per-event and per-command schemas,
   generated SDKs, EventCatalog source, Apicurio synchronization." Amend to
   reflect the narrowed scope. Mark the amendment inline in ADR-0001 with a
   pointer to this ADR.
2. **Audit existing Holyfields schemas for CloudEvents extension coverage.**
   Confirm the base envelope schema includes `correlationid`, `causationid`,
   `producer`, `service`, `domain`, `schemaref`, `traceparent`. If any are
   missing, that is a closeable gap, not an architectural problem.
3. **Add the Holyfields-to-Apicurio CI sync.** One-way, idempotent. Runs on
   merge to Holyfields main. Skip this step until the first service needs
   runtime schema lookup; do not over-build ahead of demand.
4. **Document the per-service AsyncAPI convention.** A short "authoring guide"
   in `docs/architecture/` when the first real service plugs in. Do not write
   the guide before we have a concrete example to anchor it.
5. **Leave the `holyfields/theboard/` subdirectory alone.** It predates this
   ADR and is out of scope; if it turns out to be AsyncAPI-shaped work that
   should move, that is a separate cleanup.

## Review triggers

Revisit this ADR if:

- A service team needs to publish events whose payload cannot be expressed
  in JSON Schema (e.g. binary or streaming formats). Holyfields' generator
  pipeline may need extension or we may add a parallel artifact class.
- Apicurio becomes unstable or its compatibility-check semantics break
  Holyfields' versioning model. We would need to reconsider who owns runtime
  lookup.
- Cross-service schema refactor frequency becomes painful enough that
  service-local AsyncAPI feels worse than a central registry. If we see more
  than ~3 cross-cutting schema renames per quarter, revisit.
- A non-Python, non-TypeScript service ships and the generator matrix does
  not yet support its target language.

## Notes on renaming

Holyfields keeps its name. The name is a joke, which is fine, and renaming a
scoped library is more cost than benefit. If anyone later files a bikeshed PR
to rename it to `33god-schemas` or similar, this ADR is the reason we push
back: boring library infrastructure does not need a rebrand.

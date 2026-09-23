---
id: SPEC-delohq
companions:
  - ../../planning-artifacts/prds/prd-33GOD-2026-09-23/prd.md
  - ../../planning-artifacts/prds/prd-33GOD-2026-09-23/addendum.md
  - ../../planning-artifacts/architecture/architecture-33GOD-2026-09-23/ARCHITECTURE-SPINE.md
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. The PRD and architecture spine remain required reading; this kernel states the implementation contract they jointly establish.

# DeloHQ Executive Experience

## Why

DeloHQ gives the solo executive one truthful, mobile surface for understanding company posture, meaningful movement, attention, and bounded decisions. The existing `/hq` experience already lives inside Holocene, but its projections and actions need one explicit contract so DeloHQ does not become a second owner of workforce, project, ticket, event, runtime, or history facts. The work matters now because the finalized architecture spine has established the boundary and the next implementation slices need stable capabilities, states, identities, and receipts.

## Capabilities

- **CAP-1**
  - **intent:** The executive can inspect a Flume-backed Company projection showing workforce hierarchy, identity, and posture.
  - **success:** Company and Agent Office use one workforce snapshot, preserve canonical identity, and show freshness or Unknown when evidence cannot support a stronger claim.

- **CAP-2**
  - **intent:** The executive can see meaningful company movement as grouped Now stories and open their exact owning context.
  - **success:** Now items are grouped from canonical event and outcome evidence with stable item identity and context links; raw volume, polling order, absence, and empty results never imply progress.

- **CAP-3**
  - **intent:** The executive can review Executive Inbox items classified by human consequence and understand the evidence before deciding.
  - **success:** Inbox classification, attention precedence, evidence, priority, and entry context come from the shared policy and remain consistent across surfaces.

- **CAP-4**
  - **intent:** The executive can inspect one Employee's Agent Office context, including role, current work, owned project context, runtime state, and intervention paths.
  - **success:** The view joins canonical Employee, Project, ticket, runtime, and receipt references without making DeloHQ or a display label an owner of any fact.

- **CAP-5**
  - **intent:** The executive can explicitly confirm a bounded action from its originating Inbox item or Agent Office context.
  - **success:** A named, typed, allowlisted command reaches only its owning canonical system and carries verified actor context, target, idempotency key, and correlation ID.

- **CAP-6**
  - **intent:** The executive can track a consequential action through a durable Action Receipt and see its terminal outcome.
  - **success:** The receipt preserves source state and evidence while rendering `accepted`, `in_progress`, `completed`, `failed`, `expired`, `rejected`, or `unknown`; HTTP acceptance alone never renders completion.

- **CAP-7**
  - **intent:** The executive can enter DeloHQ from Telegram and hand off to the owning conversation or canonical system without losing context.
  - **success:** Every public `/hq` request verifies Telegram Mini App `initData`, derives actor context, and preserves the originating item, Employee, Project, Action, or Receipt reference through the handoff.

- **CAP-8**
  - **intent:** The executive can distinguish current, stale, unavailable, contradictory, and Unknown company state on every DeloHQ surface.
  - **success:** Company, Now, Inbox, Office, action, and receipt responses carry schema version, source, generation time, observation time, freshness, and evidence or error detail.

- **CAP-9**
  - **intent:** DeloHQ implementers can evolve projections, commands, receipts, and errors through one shared versioned contract.
  - **success:** Holocene adapters, `/hq` routes, views, and contract tests consume `holocene/packages/delohq-contracts/`; incompatible changes require an explicit versioned migration.

## Constraints

- Holocene is the v1 host and composition boundary: `/hq` remains in the Holocene web app, host-side integrations remain in `holocene-api.service`, and v1 creates no separate DeloHQ service, repository, API, database, event stream, or runtime.
- Flume owns workforce identity, hierarchy, delegation, escalation, and workforce policy; PJangler owns project identity; Krebs and Pilot own ticket lifecycle; Bloodbank and Candystore own event transport and durable history; Hermes owns runtime execution and receipts.
- The browser consumes only authenticated `/hq/api/*` DeloHQ envelopes. It never reads `org.yaml`, registries, systemd, Candystore, Bloodbank, Flume stores, or internal Fastify routes directly.
- Opaque canonical identifiers survive every projection. Display names, repository labels, and Telegram usernames are labels or destinations, never join keys.
- Every projection preserves source, timestamps, freshness, evidence, and explicit error or Unknown state. The existing `org.yaml` data may be used only through a bounded transitional adapter and is never workforce authority or writable by DeloHQ.
- Consequential operations use named allowlisted commands, verified actor context, originating context, idempotency, correlation, canonical-system transitions, and durable receipts. DeloHQ never owns a parallel state machine.
- Traefik, `holocene-web`, and `holocene-api.service` remain observable split deployment components. Dependency or proxy failure degrades to explicit error, stale, or Unknown state and never fabricated success.
- The declared pnpm 10 and Node 22 Compose toolchain must be executable before implementation evidence relies on package-manager commands; the current Node 26.5 host shim failure is a platform handoff.

## Non-goals

- DeloHQ is not a workforce system of record, project registry, ticket tracker, event store, runtime executor, or history database.
- DeloHQ v1 is not a general operator shell, arbitrary path proxy, unrestricted command console, or replacement for the owning Telegram conversations and canonical systems.
- DeloHQ v1 does not define every possible Action, every notification class, numeric freshness budget, Flume transport, or Hindsight memory policy; those remain explicit upstream decisions.
- DeloHQ v1 does not create a general event-reducer platform or require a separate deployable product boundary.

## Success signal

From Telegram, the executive can open `/hq` and, within 30 seconds, identify company posture, meaningful movement, items needing attention, the relevant Employee or project context, and the next decision. A bounded action can be confirmed and followed to a durable receipt whose state is truthful, while a stale, unavailable, contradictory, or unknown dependency is visibly represented rather than presented as healthy or complete.

## Assumptions

- The approved DeloHQ name remains the executive-surface name; it does not imply a separate deployable product.
- The existing Holocene split deployment remains the v1 operational shape while the shared DeloHQ contract is implemented.

## Open Questions

- What max age makes each Company, Now, Inbox, and Agent Office projection stale or Unknown?
- Which bounded Actions and receipt providers are in the first release beyond approve, reject, and acknowledge?
- Which supported Flume read surface supplies the workforce projection, and how is the current `org.yaml` presentation overlay retired?
- Which current `/hq` controls and capabilities remain, change, or retire under the DeloHQ navigation model?
- Which Hindsight summaries can be shown in Agent Office without exposing raw private runtime memory?

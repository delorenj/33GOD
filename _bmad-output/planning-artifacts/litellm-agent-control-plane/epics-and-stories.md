# Epics and Stories — LiteLLM Agent Control Plane (ACP)

**Project:** 33GOD — Agent Control Plane Integration
**Date:** 2026-08-13
**Status:** Reviewed planning baseline — Stage 0 complete; implementation gated
**Stable planning keys:** ACP-E0 through ACP-E6 remain the canonical BMAD keys.
The active Plane hierarchy maps them to `ACP-E1` through `ACP-E7` and real work
items `33GOD-5` through `33GOD-32`, beneath initiative container `33GOD-4`.
The complete mapping is in the [dispatch receipt](../../../33god-platform/knowledge/33god-pm-litellm-acp-dispatch.yaml).

**Parent requirements:**
- FR16 (Normalized agent sessions and research custody)
- [Integration decision document](../../../33god-platform/docs/litellm-agent-control-plane-integration.md)
- ARCHITECTURE-SPINE.md (AD-ACP-1 through AD-ACP-10)

---

## Requirements Inventory

### Functional Requirements (ACP scope)

| FR | Description | Covered by |
|----|-------------|------------|
| FR16-AC1 | Pinned, protected, removable lab service | ACP-E1 |
| FR16-AC2 | No permanent identity duplication | ACP-E1, ACP-E4 |
| FR16-AC3 | Canonical Bloodbank command per turn | ACP-E2 |
| FR16-AC4 | Assistant result through governed contract | ACP-E2 |
| FR16-AC5 | Scoped virtual key, no credential duplication | ACP-E1 |
| FR16-AC6 | Hindsight/Candystore/Holocene/DeLoHQ boundaries | ACP-E3, ACP-E5 |
| FR16-AC7 | OpenNotebook read-model custody | ACP-E0 |

### Non-Functional Requirements (applicable)

- Local-first: ACP lab deploys on laptop before cloud.
- Idempotent: Commands carry idempotency keys; backfills safe to rerun.
- Fail-open: Adapter failure must not block existing Hermes sessions.
- Source-of-truth clarity: ACP is never treated as project/fleet/identity truth.
- Secret hygiene: Scoped LiteLLM key never tracked in config.
- Observable gates: Each stage has explicit acceptance criteria.

---

## Epic List

| Key | Epic | Stages | Dependencies | Owner |
|-----|------|--------|--------------|-------|
| ACP-E0 | BMAD Alignment & Planning Governance | Stage 0 | None (this work) | 33god-pm |
| ACP-E1 | Isolated Lab Deployment | Stage 1 | ACP-E0 | 33god-platform |
| ACP-E2 | Canonical Bloodbank Bridge (33god-hermes Adapter) | Stage 2 | ACP-E1, Bloodbank invocation schema, Fleet gateway | 33god-platform |
| ACP-E3 | Operator Projections (Holocene & DeLoHQ) | Stage 3 | ACP-E2, Candystore correlation | Holocene |
| ACP-E4 | Identity & Credential Boundary Enforcement — verification-only | Cross-stage verification | ACP-E1, PJangler, LiteLLM | 33god-platform |
| ACP-E5 | Hindsight, Memory & Audit Boundaries — verification-only | Cross-stage verification | ACP-E2 | Hindsight |
| ACP-E6 | Flume Execution Port Design | Stage 4 | ACP-E3, Flume repository/contract | Flume (planned) |

---

## Epic ACP-E0: BMAD Alignment & Planning Governance

**Goal:** Produce and commit a complete, verified BMAD planning artifact set that
reconciles the ACP integration decision into the 33GOD product brief, PRD,
architecture, epics, stories, and readiness assessment. This epic gates all
implementation work; it does not authorize production deployment.

**This epic is complete.** The reviewed artifact set is committed alongside a
machine-readable receipt for the active `33GOD Platform` board. Plane work items
`33GOD-4` through `33GOD-32` represent one initiative container, seven epics, and
21 stories; authoritative readback verified all 28 non-root parent links. This
completion closes planning traceability only and does not authorize deployment.

### Story ACP-E0.1: Produce planning artifact set

As the 33GOD product director, I want a complete BMAD artifact set for the ACP
integration so that all planning, ownership, dependency, and risk information is
recorded in Git/BMAD before any implementation work begins.

**Acceptance Criteria:**

- **Given** the integration decision document and root PRD/architecture
- **When** the BMAD artifact set is produced
- **Then** the following files exist in `_bmad-output/planning-artifacts/litellm-agent-control-plane/`:
  - `product-brief-delta.md`
  - `prd-reconciliation.md`
  - `ARCHITECTURE-SPINE.md`
  - `epics-and-stories.md`
  - `implementation-readiness-assessment.md`
  - `dependency-and-ownership-ledger.md`
  - `evidence-and-decision-ledger.md`
  - `.memlog.md`
- **And** every file cross-references the integration decision document, PRD.md, and parent architecture
- **And** stable planning keys ACP-E0 through ACP-E6 map deterministically to
  `33GOD-5` through `33GOD-32`, beneath `33GOD-4`, without fabricated IDs
- **And** the active board binding is workspace `33god`, project `33GOD Platform`
  (`15258893-0206-4e8f-aea6-340eb217988c`)
- **And** the machine-readable dispatch receipt records all IDs, sequence keys,
  parent links, Bloodbank lineage, and created-versus-reused disposition
- **And** current canonical-source revisions are compared with the OpenNotebook
  custody receipt; changed sources are re-ingested to a completed receipt, or an
  explicit blocking exception is recorded before Stage 1
- **And** HeyMa RED status is recorded as pre-existing, not ACP-caused

**Dependencies:** Plane traceability satisfied; OpenNotebook freshness check remains a Stage 1 go/no-go input
**Owner:** 33god-pm
**Security gate:** N/A (planning only)
**Rollback:** Revert committed files
**Kill switch:** N/A

---

## Epic ACP-E1: Isolated Lab Deployment

**Goal:** Deploy ACP as a pinned, isolated lab service with its own database,
internal hostname, scoped LiteLLM virtual key, and one disposable runtime/profile.
Prove it can create sessions, stream turns, cancel, and clean up. Prove ACP
shutdown has no effect on existing Hermes services.

### Story ACP-E1.1: Pin upstream ACP revision and security review

As a platform operator, I want the ACP upstream revision pinned to an immutable
SHA or image digest so that the lab deployment is reproducible and auditable.

**Acceptance Criteria:**

- **Given** the ACP upstream repository at `53bfd20e2fec51fc8f665fb614512c6b138367da`
- **When** the security review is completed
- **Then** a specific SHA or image digest is pinned in the deployment configuration
- **And** `latest` is never used
- **And** a security review document exists covering all 10 required gates from the integration decision

**Dependencies:** ACP-E0
**Owner:** 33god-platform
**Security gate:** 1 — Pin upstream commit or digest
**Rollback:** Revert pin to previous known-good revision
**Kill switch:** Remove pinned ref from config

### Story ACP-E1.2: Deploy ACP with dedicated database

As a platform operator, I want ACP deployed with a separate PostgreSQL database
and internal-only service hostname so that it is isolated from existing 33GOD
component state.

**Acceptance Criteria:**

- **Given** the ACP docker-compose or deployment manifest
- **When** `docker compose up` is run with the ACP profile
- **Then** ACP starts with its own database (not Candystore's or any other DB)
- **And** ACP API is reachable only on an internal hostname (not published to host)
- **And** the deployment does not modify any existing Compose service or volume
- **And** existing `platform:validate` still passes its non-ACP gates

**Dependencies:** ACP-E1.1
**Owner:** 33god-platform
**Security gates:** 2 (dedicated DB), 3 (internal hostname), 4 (no untrusted network exposure)
**Rollback:** `docker compose down` for ACP services
**Kill switch:** Remove ACP profile from deployment config

### Story ACP-E1.3: Create scoped DeLoNET LiteLLM virtual key

As a platform operator, I want a scoped virtual key for ACP that has bounded
budget, distinct LiteLLM identity, and only the `hermes` alias/models, so that
ACP cannot access unapproved providers or unbounded spend.

**Acceptance Criteria:**

- **Given** the DeLoNET LiteLLM gateway is operational
- **When** a virtual key is created for the `acp-lab` consumer
- **Then** the key has only the `hermes` alias/models needed by the pilot
- **And** the key has a bounded spend or request budget
- **And** the key has a distinct identity in LiteLLM logs
- **And** the key has no dashboard, key-management, or provider authority
- **And** the key is injected at runtime, never tracked in configuration

**Dependencies:** ACP-E1.1, DeLoNET LiteLLM gateway
**Owner:** 33god-platform
**Security gates:** 5 (keep secrets in LiteLLM), 6 (no env dumps in session metadata)
**Rollback:** Revoke virtual key in LiteLLM
**Kill switch:** Revoke key; ACP loses model access

### Story ACP-E1.4: Create disposable acp-lab runtime/profile

As a platform operator, I want one disposable ACP runtime/profile registered so
that I can exercise session creation, turn streaming, cancellation, and cleanup
without affecting any Hermes PM profile.

**Acceptance Criteria:**

- **Given** ACP is deployed and has a scoped LiteLLM key
- **When** a new `acp-lab` runtime/profile is created in ACP
- **Then** the profile uses the `hermes` model alias via the scoped key
- **And** the profile is NOT registered in the Hermes fleet or PJangler registry
- **And** session creation works with a user turn
- **And** turn streaming returns intermediate output
- **And** cancellation terminates the session cleanly
- **And** cleanup removes all disposable resources

**Dependencies:** ACP-E1.2, ACP-E1.3
**Owner:** 33god-platform
**Security gate:** 8 (BR-1 blocks Stage 2); 10 (kill switch)
**Rollback:** Delete `acp-lab` profile and ACP DB
**Kill switch:** Disable `acp-lab` profile in ACP

### Story ACP-E1.5: Prove ACP shutdown independence

As a platform operator, I want to prove that stopping ACP leaves every existing
Hermes PM, heartbeat, gateway, and Bloodbank route fully operational, so that
the removable claim is evidenced.

**Acceptance Criteria:**

- **Given** ACP is running with the `acp-lab` profile and existing Hermes PMs are operational
- **When** ACP is stopped (`docker compose down` for ACP services)
- **Then** every existing Hermes PM continues heartbeating normally
- **And** the fleet-shared gateway continues processing Bloodbank commands
- **And** existing Telegram/Slack gateways remain operational
- **And** Bloodbank NATS continues routing messages
- **And** no Hermes PM log shows ACP-related errors
- **And** restarting ACP does not affect running PMs

**Dependencies:** ACP-E1.4
**Owner:** 33god-platform
**Security gate:** 10 (kill switch boundary)
**Rollback:** Restart ACP services
**Kill switch:** N/A (this IS the kill switch test)

---

## Epic ACP-E2: Canonical Bloodbank Bridge (33god-hermes Adapter)

**Goal:** Implement the `33god-hermes` ACP runtime adapter that publishes one
schema-valid Bloodbank command per turn, consumes correlated events, and returns
assistant results through a governed response contract.

### Story ACP-E2.1: Implement `33god-hermes` adapter — command publication

As an ACP runtime implementer, I want the `33god-hermes` adapter to publish
schema-valid `bloodbank.v1.agent.invocation.start` commands so that ACP turns
enter the canonical Bloodbank event backbone.

**Acceptance Criteria:**

- **Given** ACP has received a user turn for a managed-Hermes session
- **When** the `33god-hermes` adapter processes the turn
- **Then** it publishes exactly one command on subject `bloodbank.cmd.v1.agent.invocation.start`
- **And** the command payload conforms to `bloodbank.v1.agent.invocation.start.v1` schema
- **And** `data.thread_id` = ACP session ID
- **And** `data.turn_id` = ACP turn ID
- **And** `data.target_agent_id` identifies the Hermes target profile
- **And** `data.prompt` contains the user turn text
- **And** `data.context` contains bounded, non-secret ACP/session metadata
- **And** every command carries stable `correlationid`, `causationid`, `command_id`, and `idempotency_key`
- **And** the actor identifies the ACP adapter, never a provider name

**Dependencies:** ACP-E1 (lab deployment), Bloodbank invocation schema, Fleet gateway readiness
**Owner:** 33god-platform (Bloodbank)
**Security gates:** 7 (command/session correlation in Bloodbank)
**Rollback:** Disable adapter; ACP turns stop publishing commands
**Kill switch:** Disable adapter without touching fleet-shared gateway

### Story ACP-E2.2: Consume correlated Hermes lifecycle events

As an ACP runtime implementer, I want the `33god-hermes` adapter to consume
correlated Bloodbank events so that ACP knows the invocation lifecycle state.

**Acceptance Criteria:**

- **Given** a Bloodbank command was published by the adapter
- **When** Hermes processes the invocation
- **Then** the adapter consumes `bloodbank.v1.agent.invocation.started`
- **And** the adapter consumes `bloodbank.v1.agent.invocation.completed` or `...failed`
- **And** each consumed event shares the same `correlationid` as the published command
- **And** the adapter can correlate ACP turn status to the terminal event
- **And** duplicate delivery, timeout, and poison-command cases are handled without crashing

**Dependencies:** ACP-E2.1
**Owner:** 33god-platform (Bloodbank)
**Security gate:** 7 (correlation)
**Rollback:** Disable event consumption in adapter
**Kill switch:** Remove adapter subscription

### Story ACP-E2.3: Add assistant response contract (close the gap)

As an ACP implementer, I want the assistant's response text and artifact
references returned through a governed Bloodbank event
(`bloodbank.v1.conversation.message.appended`) so that ACP chat completion is
evidenced by a canonical event stream.

**Acceptance Criteria:**

- **Given** a Hermes invocation completes with a reply message
- **When** the fleet-shared gateway or Bloodbank publishes the result
- **Then** a `bloodbank.v1.conversation.message.appended` event is published
- **And** the event carries the assistant's text or artifact reference
- **And** the event shares the `correlationid` of the original command
- **And** Candystore persists the event
- **And** ACP can mark its turn complete when this event is received
- **And** without this event, ACP chat is NOT considered complete (gap resolution)

**Dependencies:** ACP-E2.2, Bloodbank schema work, Candystore review, Holocene consumer review
**Owner:** 33god-platform (Bloodbank)
**Security gate:** 7 (correlation)
**Rollback:** Revert schema extension; ACP remains in gap state
**Kill switch:** Disable adapter event subscription

### Story ACP-E2.4: Duplicate delivery, timeout, cancellation, and poison-command testing

As a platform operator, I want the adapter tested against edge cases so that it
handles failures gracefully without degrading existing services.

**Acceptance Criteria:**

- **Given** the adapter is connected to the lab ACP and Bloodbank
- **When** duplicate commands are sent (same `idempotency_key`)
- **Then** the gateway rejects or deduplicates them
- **When** a command times out waiting for completion
- **Then** the adapter reports failure and cleans up
- **When** a cancellation is issued during an active turn
- **Then** the adapter publishes a cancellation event and Hermes terminates
- **When** a poison/invalid command is published
- **Then** the adapter's error does NOT crash the gateway or other services

**Dependencies:** ACP-E2.2, ACP-E2.3
**Owner:** 33god-platform
**Security gate:** N/A (testing)
**Rollback:** N/A (testing)
**Kill switch:** N/A

### Story ACP-E2.5: Persist complete ACP trace in Candystore

As a platform operator, I want the end-to-end ACP session trace persisted in
Candystore so that the audit trail is queryable alongside all other 33GOD events.

**Acceptance Criteria:**

- **Given** an ACP session produced start, turn, and completion events
- **When** Candystore is queried for the `correlationid`
- **Then** all events from command through completion are present
- **And** the trace includes the assistant message event (when gap is closed)
- **And** the trace is queryable through Candystore's existing API (no ACP-specific endpoint required)

**Dependencies:** ACP-E2.3, Candystore
**Owner:** Candystore
**Security gate:** 7 (correlation)
**Rollback:** No Candystore changes beyond standard ingestion
**Kill switch:** N/A (Candystore continues as before)

---

## Epic ACP-E3: Operator Projections (Holocene & DeLoHQ)

**Goal:** Surface ACP health, session state, and correlated history in Holocene.
Join ACP session data with Candystore correlation history. Expose only bounded
executive controls in DeLoHQ.

### Story ACP-E3.1: Add ACP health and session state to Holocene

As a 33GOD operator, I want ACP health and live session state visible in
Holocene so that I can monitor the ACP lab from the existing control surface.

**Acceptance Criteria:**

- **Given** Holocene is the operator-facing control plane
- **When** ACP is running
- **Then** Holocene shows ACP component health (up/down/degraded)
- **And** Holocene shows active ACP sessions with status (active/completed/failed)
- **And** ACP session state is obtained through the ACP API (not runtime file scraping)
- **And** Holocene distinguishes ACP from other component health

**Dependencies:** ACP-E2, Holocene
**Owner:** Holocene
**Security gate:** N/A (read-only monitor)
**Rollback:** Remove ACP health panel from Holocene
**Kill switch:** Disconnect Holocene ACP data source

### Story ACP-E3.2: Join ACP sessions with Candystore history

As a 33GOD operator, I want ACP session data joined with Candystore correlation
history in Holocene so that I can see the complete lifecycle of an ACP session.

**Acceptance Criteria:**

- **Given** Holocene displays ACP sessions
- **When** an operator views a specific ACP session
- **Then** Holocene shows correlated Candystore events (invocation started/completed, assistant message)
- **And** the correlation is by `correlationid`
- **And** the Candystore-originated events are clearly tagged as historical audit data

**Dependencies:** ACP-E3.1, ACP-E2.5
**Owner:** Holocene
**Security gate:** N/A (read-only)
**Rollback:** Remove correlation join panel
**Kill switch:** Disconnect Candystore query for ACP

### Story ACP-E3.3: Add approval and exception events to DeLoHQ

As a 33GOD executive, I want to see ACP approval requests and exception events
in DeLoHQ so that I can approve or deny bounded operations from the mobile
surface.

**Acceptance Criteria:**

- **Given** DeLoHQ is the mobile executive surface (currently Holocene's `/hq`)
- **When** an ACP session requires approval (e.g., elevated budget, extended lifetime)
- **Then** DeLoHQ surfaces the approval request with session context
- **And** the operator can approve or deny from DeLoHQ
- **And** DeLoHQ does NOT expose ACP session builder, runtime config, or model selection
- **And** DeLoHQ remains strictly bounded to status, approvals, exceptions, budgets, and coarse controls

**Dependencies:** ACP-E3.2
**Owner:** DeLoHQ / Holocene
**Security gate:** N/A (limited to bounded controls)
**Rollback:** Remove ACP approval surfaces from DeLoHQ
**Kill switch:** Disable ACP approval routing

---

## Epic ACP-E4: Identity & Credential Boundary Enforcement

**Goal:** Prove that ACP never creates duplicate permanent identities, never
receives provider credentials, and never bypasses PJangler or the fleet registry.
Cross-cutting verification work.

**Classification:** ACP-E4.1 and ACP-E4.2 are cross-cutting verification-only
stories, not independent implementation slices. They verify ACP-E1 behavior and
are included in the accurate total of 21 stories.

### Story ACP-E4.1: Verify no ACP-created permanent identities

As a platform operator, I want to verify that ACP has not created any permanent
project, fleet, or agent identity that duplicates PJangler or the Hermes fleet
registry, so that identity integrity is maintained.

**Acceptance Criteria:**

- **Given** ACP is running with at least one session
- **When** the PJangler project registry is queried
- **Then** all permanent project identities remain PJangler-managed
- **And** ACP has no `.project.json` files in its runtime storage
- **And** the Hermes fleet registry has no entries created by ACP
- **And** a comparison of ACP session IDs vs permanent identity registries shows zero overlap

**Dependencies:** ACP-E1, PJangler, Hermes fleet
**Owner:** 33god-platform
**Security gate:** N/A (verification)
**Rollback:** N/A
**Kill switch:** N/A

### Story ACP-E4.2: Verify no provider credential leakage

As a platform operator, I want to verify that ACP has no direct provider
credentials and that all model requests go through the DeLoNET LiteLLM gateway
with the scoped virtual key, so that credential boundaries are enforced.

**Acceptance Criteria:**

- **Given** ACP is running with the `acp-lab` profile
- **When** the ACP runtime environment is inspected
- **Then** there are no OpenAI, Anthropic, Google, or OpenRouter API keys
- **And** the only model credential is the scoped LiteLLM virtual key
- **And** all outbound model requests go to the LiteLLM gateway URL
- **And** LiteLLM logs show the ACP consumer identity on every request

**Dependencies:** ACP-E1.3
**Owner:** 33god-platform
**Security gate:** 5 (credential boundary)
**Rollback:** Revoke scoped key if compromised
**Kill switch:** Revoke scoped key

---

## Epic ACP-E5: Hindsight, Memory & Audit Boundaries

**Goal:** Prove that ACP memory is session-local scratch only, Hindsight remains
the durable memory owner, and Candystore remains the durable audit owner.

**Classification:** ACP-E5.1 and ACP-E5.2 are cross-cutting verification-only
stories, not independent implementation slices. They verify ACP-E2 behavior and
are included in the accurate total of 21 stories.

### Story ACP-E5.1: Verify Hindsight remains durable memory owner

As a platform operator, I want to verify that ACP has not duplicated, replaced,
or interfered with Hindsight's durable memory role, so that agent memory
continues working through canonical hooks.

**Acceptance Criteria:**

- **Given** ACP is running with active sessions
- **When** a Hermes PM uses Hindsight for recall or retain
- **Then** the Hindsight hook continues to work identically to pre-ACP state
- **And** ACP session data does not appear in Hindsight responses (unless explicitly promoted)
- **And** no ACP component modifies Hindsight's hook scripts or configuration

**Dependencies:** ACP-E2, Hindsight
**Owner:** Hindsight
**Security gate:** N/A (verification)
**Rollback:** N/A
**Kill switch:** N/A

### Story ACP-E5.2: Verify Candystore remains durable audit owner

As a platform operator, I want to verify that Candystore is the only durable
audit store and that ACP retains only its session projection/cache, so that the
audit trail integrity is maintained.

**Acceptance Criteria:**

- **Given** ACP is running and generating session events
- **When** Candystore is queried for complete event history
- **Then** all Bloodbank events (including ACP-generated) are present in Candystore
- **And** ACP's own storage contains only session projection data, not the canonical audit record
- **And** deleting ACP's database does not remove any events from Candystore

**Dependencies:** ACP-E2.5, Candystore
**Owner:** Candystore
**Security gate:** N/A (verification)
**Rollback:** N/A
**Kill switch:** N/A

---

## Epic ACP-E6: Flume Execution Port Design

**Goal:** Map Flume work requests and delegation metadata onto normalized ACP
sessions. Keep org hierarchy, authority, budget, and escalation decisions in
Flume. Route permanent employees through registered Hermes targets. Allow
disposable workers only within explicit bounds.

### Story ACP-E6.1: Define Flume-to-ACP mapping contract

As a platform architect, I want the mapping between Flume work requests and ACP
sessions defined as a contract so that engineers building Flume know how to
call ACP sessions.

**Acceptance Criteria:**

- **Given** Flume is a planned protocol/product boundary
- **When** the Flume→ACP mapping is designed
- **Then** the mapping specification exists in `33god-platform/docs/`
- **And** it maps: work request → user message/turn, employee identity → `target_agent_id`, delegated task ID → correlation ID + ACP session ID, task attempt → ACP turn ID + Bloodbank command ID, work result → terminal lifecycle event + correlated assistant message
- **And** escalation/approval continues through Bloodbank events to Holocene/DeLoHQ
- **And** Flume retains org hierarchy, authority, budget, and escalation decisions

**Dependencies:** ACP-E3 (operator projections deployed), Flume contract exists
**Owner:** Flume (planned)
**Security gate:** N/A (design document)
**Rollback:** Revise design doc
**Kill switch:** N/A (design only without implementation authorization)

### Story ACP-E6.2: Route permanent employees through registered Hermes targets

As a platform architect, I want permanent Hermes fleet employees routed through
registered profiles and the fleet-shared gateway, never through ad-hoc ACP
runtimes, so that PJangler identity and fleet lifecycle remain canonical.

**Acceptance Criteria:**

- **Given** a Flume work request targets a permanent employee (registered Hermes PM)
- **When** Flume creates an ACP session for the request
- **Then** the ACP session targets a registered Hermes fleet profile via `data.target_agent_id`
- **And** the command goes through the fleet-shared gateway
- **And** the permanent employee's profile is managed by PJangler, not ACP

**Dependencies:** ACP-E6.1, Flume contract
**Owner:** Flume (planned)
**Security gate:** AD-ACP-2 (no permanent identity in ACP)
**Rollback:** N/A (design)
**Kill switch:** N/A

### Story ACP-E6.3: Specify disposable worker capability bounds

As a platform architect, I want a reviewable specification for disposable ACP
worker bounds so that a future Flume/ACP implementation has unambiguous policy
and test obligations without claiming enforcement exists today.

**Acceptance Criteria:**

- **Given** Flume has no repository or versioned contract
- **When** disposable-worker behavior is designed
- **Then** a design specification defines an explicit approved capability set
- **And** the specification defines workspace/repository scope, spend ceiling,
  maximum delegation depth, and maximum lifetime
- **And** the specification defines required termination and Bloodbank escalation
  semantics for every exceeded bound
- **And** the specification defines future conformance tests without claiming those
  tests or runtime controls currently exist
- **And** design acceptance does not authorize runtime enforcement work

**Dependencies:** ACP-E6.1 (design); implementation explicitly blocked on a Flume repository, versioned contract, and assigned implementation owner
**Owner:** 33god-platform architecture (specification); Flume/ACP owner TBD (future implementation)
**Security gate:** AD-ACP-7 (Flume owns delegation policy)
**Rollback:** Revise or withdraw design specification
**Kill switch:** N/A (design only)

**Blocked future enforcement slice:** Implement and test capability, workspace,
spend, depth, lifetime, termination, and escalation controls only after Flume has
a repository and versioned contract and an implementation owner is assigned.

---

## Staged Lab-to-Flume Execution-Port Sequence

```
Stage 0 (ACP-E0): BMAD Alignment
  → Planning artifacts reviewed and codified
  → 29 Plane work items created on active 33GOD Platform board (33GOD-4–33GOD-32)
  → 28/28 requested parent links verified by authoritative readback
  → OpenNotebook receipt freshness checked; stale sources re-ingested or blocking exception recorded
  → No implementation authorization

Stage 1 (ACP-E1): Isolated Lab
  → Pinned ACP deployed, separate DB, internal hostname
  → Scoped LiteLLM key created
  → One disposable runtime/profile
  → Session create/turn/stream/cancel/cleanup proven
  → Shutdown independence proven

Stage 2 (ACP-E2): Bloodbank Bridge
  → BR-1 backup/restore gate passed before work begins
  → 33god-hermes adapter implemented
  → Canonical command publication
  → Event consumption with correlation
  → Assistant response contract (close gap)
  → Edge-case testing (duplicate, timeout, cancel, poison)
  → Candystore trace persistence

Stage 3 (ACP-E3): Operator Projections
  → ACP health + session state in Holocene
  → Candystore correlation join
  → DeLoHQ approval/exception surfaces

Stage 4 (ACP-E6): Flume Execution Port
  → Design/specification acceptance only while Flume has no repository/contract
  → Flume→ACP mapping and permanent-employee routing specified
  → Disposable worker bounds and future conformance tests specified
  → Runtime enforcement remains a blocked future slice
```

**Cross-cutting verification (ACP-E4, ACP-E5):** Run continuously from Stage 1
through Stage 4 to prove identity, credential, memory, and audit boundaries are
never violated.

---

## Blocking Gate BR-1: Backup, Restore, and Failure Recovery Before Stage 2

Stage 2 MUST NOT begin until ACP data is classified and recovery obligations are
proved. This is a blocking gate, not a vague deferral and not an additional story
(the document therefore remains 7 epics / 21 stories).

1. **Classify:** Identify authoritative, reproducible, ephemeral, and durable ACP data.
2. **Decide and implement:** If any data requires durability, configure `forever-ago`
   tiered retention (FR5) or document an approved equivalent. If no data requires
   durability, document and approve reproducibility evidence rather than silently
   skipping backup.
3. **Restore test:** Restore the backup into a fresh ACP instance and verify database
   integrity and required session continuity/recovery behavior.
4. **Failure tests:** Explicitly test interrupted backup, corrupt/missing backup,
   failed restore, process restart during recovery, and safe terminal failure reporting.
5. **Evidence:** Record commands, timestamps, source backup identifier, destination,
   integrity checks, and pass/fail result. Any failure keeps Stage 2 blocked.

## Rollback and Kill Switch Summary

| Story | Rollback | Kill switch |
|-------|----------|-------------|
| ACP-E1.1 | Revert pin | Remove pinned ref |
| ACP-E1.2 | `docker compose down` | Remove ACP profile |
| ACP-E1.3 | Revoke LiteLLM key | Revoke key |
| ACP-E1.4 | Delete profile + DB | Disable profile |
| ACP-E1.5 | Restart ACP | N/A (this IS the test) |
| ACP-E2.1 | Disable adapter | Disable adapter (gateway untouched) |
| ACP-E2.2 | Disable event consumption | Remove subscription |
| ACP-E2.3 | Revert schema | Disable event subscription |
| ACP-E2.4 | N/A (testing) | N/A |
| ACP-E2.5 | No Candystore changes needed | N/A |
| ACP-E3.1 | Remove ACP panel | Disconnect data source |
| ACP-E3.2 | Remove correlation join | Disconnect Candystore query |
| ACP-E3.3 | Remove approval surfaces | Disable approval routing |
| ACP-E4.1 | N/A (verification) | N/A |
| ACP-E4.2 | Revoke key | Revoke key |
| ACP-E5.1 | N/A (verification) | N/A |
| ACP-E5.2 | N/A (verification) | N/A |
| ACP-E6.1 | Revise design doc | N/A |
| ACP-E6.2 | N/A (design) | N/A |
| ACP-E6.3 | Revise/withdraw specification | N/A (design only) |

## Cancellation, Restart, Shutdown Independence

- **Cancellation:** Any story can be cancelled independently by reverting its
  changes. No story creates an irreversible infrastructure change.
- **Restart:** ACP can be restarted (`docker compose restart`) without affecting
  other services. ACP-E1.5 must test restart while PMs continue operating; BR-1
  must test restart during recovery. Adapter state is ephemeral.
- **Shutdown independence:** Proved in ACP-E1.5. Stopping ACP must not stop or
  degrade any existing Hermes PM, heartbeat, gateway, or Bloodbank route.
- **Duplicate delivery:** ACP-E2.4 tests idempotency via `idempotency_key`.
- **Cancellation (in-flight):** ACP-E1.4 and ACP-E2.4 test turn/session
  cancellation paths.
- **Timeout/failure:** ACP-E2.2 and ACP-E2.4 explicitly test timeout, poison/invalid
  commands, failed terminal events, cleanup, and isolation from other services.
- **Backup/restore failure:** BR-1 explicitly tests interrupted/corrupt/missing
  backups, failed restore, restart during recovery, and terminal failure reporting.

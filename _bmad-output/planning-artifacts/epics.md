---
stepsCompleted: [1, 2]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-33GOD-2026-09-23/prd.md
  - _bmad-output/planning-artifacts/prds/prd-33GOD-2026-09-23/addendum.md
  - _bmad-output/planning-artifacts/architecture/architecture-33GOD-2026-09-23/ARCHITECTURE-SPINE.md
  - _bmad-output/specs/spec-delohq/SPEC.md
  - _bmad-output/planning-artifacts/ux-designs/ux-33GOD-2026-08-25/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-33GOD-2026-08-25/EXPERIENCE.md
---

# 33GOD - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for 33GOD,
decomposing the DeloHQ requirements from the final PRD, adopted implementation
spec, finalized architecture spine, and the draft UX handoff. DeloHQ remains
the executive experience hosted by Holocene; the canonical systems retain
authority for their domain facts and mutations.

## Requirements Inventory

### Functional Requirements

- **FR-1:** Show a Flume-backed Company projection of Departments, Employees, roles, and ownership with source and freshness.
- **FR-2:** Explain Employee posture in company language, distinguishing Working, Waiting on you, Blocked, Quiet, Unavailable, and Unknown.
- **FR-3:** Navigate from a Department or Employee to the relevant Agent Office, Project, Evidence, or conversation and return without losing context.
- **FR-4:** Group related canonical Evidence into readable Now items that identify what changed, when, and why it matters.
- **FR-5:** Open the exact Agent Office, Project, Decision, Exception, or Evidence behind a Now item; label missing or expired Evidence.
- **FR-6:** Classify Inbox items as Approval, Exception, Question, or Briefing and show current attention state without equating awareness with resolution.
- **FR-7:** Explain a decision with requesting owner, affected Project, recommendation, consequence of waiting, available choice, and supporting Evidence.
- **FR-8:** Preserve Inbox state and context when entered from Company, Now, Telegram, or Agent Office, including terminal states that prevent duplicate action.
- **FR-9:** Show an Employee's role, Department, mission, current work, latest outcome, blockers, open Inbox items, and current Evidence.
- **FR-10:** Link Agent Office to the relevant Project, board, repository, Evidence, Company Memory, or Telegram conversation while preserving context.
- **FR-11:** Distinguish Message Agent, inspect Evidence, acknowledge Exception, and request bounded Action intervention paths.
- **FR-12:** Require explicit confirmation for approve, reject, acknowledge, and other bounded consequential Actions after showing target, reason, expected outcome, and Evidence.
- **FR-13:** Show Action Receipt progress through accepted, in progress, completed, failed, expired, rejected, or Unknown without treating acceptance as completion.
- **FR-14:** Preserve durable correlation between each Action, its originating Inbox item or Agent Office, actor, request, and Canonical System outcome Evidence.
- **FR-15:** Support context-preserving Telegram bot-menu, notification, and Agent-conversation entry into Company, Now, Inbox, Exception, or Agent Office.
- **FR-16:** Hand off to the relevant Telegram conversation without replacing native Agent chat or treating chat as a Decision, Evidence, or Receipt by itself.

### NonFunctional Requirements

- **NFR-1 Truthfulness:** Do not display current, healthy, completed, or successful state without supporting Canonical System Evidence; use explicit Unknown, stale, unavailable, or contradictory states.
- **NFR-2 Freshness visibility:** Expose source, timestamps, freshness context, and the missing or contradictory Evidence needed to interpret a projection.
- **NFR-3 Action integrity:** Correlate every consequential Action to one originating context and one Canonical System outcome; refresh, revisit, or reopen must not duplicate it.
- **NFR-4 Mobile clarity and accessibility:** Company, Now, Inbox, Office, and Receipt remain usable in the mobile-first Telegram Mini App; urgency, state, failure, and completion are understandable from text and structure, not color alone.
- **NFR-5 Audience and data boundary:** Design for one Executive Operator in v1, reveal only context needed for the selected decision or intervention, and do not create a shadow permission model or expose raw private Agent memory by default.
- **NFR-6 Contract consistency:** Browser-facing payloads, view models, item identity, freshness vocabulary, attention precedence, command inputs, receipt states, and errors come from one versioned `delohq-contracts` registry with contract tests.
- **NFR-7 Auth and failure behavior:** Verify Telegram `initData` at every public `/hq` route, derive actor context, and represent proxy, source, auth, and command failures as distinct explicit states rather than fabricated success.
- **NFR-8 Operational observability:** Preserve source, correlation, outcome, timestamps, and concise failure reasons across the Traefik, `holocene-web`, and `holocene-api.service` split deployment without exposing credentials, prompts, raw private memory, or arbitrary command text.
- **NFR-9 Success latency:** The executive should be able to answer what is happening, what needs attention, who owns it, and whether an Action completed within 30 seconds of opening DeloHQ.

### Additional Requirements

- **AD-1 Authority boundary:** Flume owns workforce identity, hierarchy, delegation, escalation, and policy; PJangler owns project identity; Krebs and Pilot own ticket lifecycle; Bloodbank and Candystore own event transport and durable history; Hermes owns runtime execution and receipts; DeloHQ projects, explains, links, acknowledges, and requests bounded commands.
- **AD-2 Host boundary:** Extend Holocene `/hq`, `holocene/apps/api`, and shared Holocene packages; keep `holocene-api.service` as the host-side integration authority and create no separate DeloHQ service, database, event stream, or runtime in v1.
- **AD-3 API seam:** Browser data crosses authenticated `/hq/api/*` routes only; each route returns a typed, versioned envelope with explicit degraded or error state.
- **AD-4 Identity:** Preserve opaque canonical identifiers for Employees or Agents, Projects, tickets, events, executions, Actions, and Receipts; display names, labels, and usernames are never join keys.
- **AD-5 Workforce projection:** Company and Office consume one Flume-backed workforce snapshot; until transport is selected, registry and `org.yaml` may pass through one transitional read adapter, with `org.yaml` remaining presentation metadata and never writable authority.
- **AD-6 Evidence composition:** Compose Now, Inbox, and history from canonical Bloodbank/Candystore evidence and outcomes; the shared contract owns item identity, grouping, attention class, and precedence, and empty or timed-out sources remain Unknown or unavailable.
- **AD-7 Command gateway:** Every consequential operation is a named, typed, allowlisted command with target, originating context, actor, idempotency, correlation, canonical transition, normalized receipt, and preserved upstream state; the current Hermes path proxy is transitional.
- **AD-8 Telegram boundary:** Verify Telegram Mini App `initData`, freshness, and operator allowlist on every public `/hq` request; reject commands without verified actor context and carry `actor_ref`, `auth_observed_at`, and route metadata.
- **AD-9 Projection envelope:** Every projection carries `schema_version`, source, `generated_at`, `observed_at`, freshness, and evidence or error details; each surface declares a max-age policy before implementation.
- **AD-10 Deployment behavior:** Traefik routes `/hq` to `holocene-web`, the web proxies to `holocene-api.service`, and dependency or proxy failure degrades to explicit error, stale, or Unknown state.
- **AD-11 Shared seam:** Commit `holocene/packages/delohq-contracts/` as the sole browser and command contract registry; adapters, routes, views, and tests import it and evolve through explicit versioned migrations.
- **Stack and toolchain:** Use the existing Next.js 15 / React 18.3 web, Fastify 5.1 / TypeScript 5.6 API, Node 22 Compose target, pnpm 10 / Turbo 2 workspace, Flume handbook schema 5 / contract 1.4.0, and existing Telegram WebApp SDK URL. Resolve the current Node 26.5 host shim failure before package-manager evidence is trusted.
- **Deferred decisions:** Before dependent stories are accepted, decide numeric freshness budgets, the first bounded Action catalog and receipt providers, Flume read transport and `org.yaml` retirement, retained or retired `/hq` capabilities and grouping policy, Telegram notification classes, and safe Company Memory fields.
- **Scope boundary:** MVP excludes a DeloHQ workforce registry, full workforce reorganization, TDLib, arbitrary history replay, untrustworthy budget views, voice/Boardroom/intervention-room features, desktop-first or native-mobile redesign, and independent DeloHQ infrastructure.

### UX Design Requirements

- **UX-DR1:** No actionable UX requirements were extracted because the matching `DESIGN.md` and `EXPERIENCE.md` files are draft shells containing metadata only.
- **UX-DR2:** Preserve the draft UX pair in the input set as advisory context; mobile information architecture, visual identity, interaction patterns, accessibility details, and mockups remain open work and must not be invented as finalized requirements in stories.

### FR Coverage Map

FR-1: Epic 1 - Flume-backed Company projection.
FR-2: Epic 1 - Company-language Employee posture and Unknown handling.
FR-3: Epic 1 - Navigation from Company to owned context.
FR-4: Epic 2 - Grouped meaningful movement in Now.
FR-5: Epic 2 - Exact context from Now items.
FR-6: Epic 3 - Human-consequence Inbox classification.
FR-7: Epic 3 - Decision explanation and supporting Evidence.
FR-8: Epic 3 - Preserved Inbox state across entry points.
FR-9: Epic 4 - Employee role, work, outcomes, blockers, and Evidence.
FR-10: Epic 4 - Agent working-context links.
FR-11: Epic 4 - Distinct conversational, observational, and consequential intervention paths.
FR-12: Epic 5 - Explicit confirmation for bounded Actions.
FR-13: Epic 5 - Action Receipt progress and terminal outcome.
FR-14: Epic 5 - Durable Action correlation and non-duplication.
FR-15: Epic 1 - Initial Telegram entry into exact DeloHQ context; deep-link continuity recurs in Epics 2–4.
FR-16: Epic 4 - Context-preserving handoff to the responsible Agent conversation.

Cross-cutting NFRs and AD-1 through AD-11 apply to every epic. The first
vertical slice owns the shared contract, Telegram verification, freshness/error
envelopes, and Company projection without creating a technical-only epic.

## Epic List

### Epic 1: Open HQ and Understand the Company

The executive can open `/hq`, understand workforce posture, and navigate from
Departments or Employees to owned context. This vertical slice includes the
shared contract, verified route boundary, freshness/error envelope, and Flume
projection needed to make the first read experience truthful.
**FRs covered:** FR-1, FR-2, FR-3, FR-15

### Epic 2: Know What Changed

The executive can see grouped meaningful movement and open the exact supporting
context without reconstructing a raw event stream.
**FRs covered:** FR-4, FR-5

### Epic 3: Decide from the Executive Inbox

The executive can review Approvals, Exceptions, Questions, and Briefings with
ownership, consequence, Evidence, preserved context, and terminal-state clarity.
**FRs covered:** FR-6, FR-7, FR-8

### Epic 4: Understand and Reach an Agent

The executive can understand an Employee's role and current work, inspect
Evidence, choose the correct intervention path, and continue in Telegram when
needed.
**FRs covered:** FR-9, FR-10, FR-11, FR-16

### Epic 5: Act and Verify the Outcome

The executive can confirm bounded Actions and follow durable receipts through
truthful terminal outcomes. The first Action catalog and receipt providers are
an explicit prerequisite for this epic's dependent stories.
**FRs covered:** FR-12, FR-13, FR-14

### Dependency Flow

Epic 1 is the first independently useful read-only slice. Epics 2–4 build on
its shared `/hq` contract and context model but each delivers a complete user
outcome within its own surface. Epic 5 builds on Inbox and Agent Office context
but is gated by the bounded Action catalog and canonical receipt contracts.
Telegram exact-context entry, freshness, Unknown, auth, and failure behavior
remain acceptance concerns across all applicable epics.

<!-- Epic and story sections will be added in later workflow steps. -->

## Epic 1: Open HQ and Understand the Company

The executive can open `/hq`, understand workforce posture, and navigate from
Departments or Employees to owned context. This vertical slice includes the
shared contract, verified route boundary, freshness/error envelope, and Flume
projection needed to make the first read experience truthful.

### Story 1.1: Establish the Shared DeloHQ Projection Contract

As the executive operator,
I want every DeloHQ surface to use one versioned projection contract,
So that company facts remain consistent as additional surfaces and actions are added.

**Acceptance Criteria:**

**Given** Holocene has multiple DeloHQ projections and route consumers
**When** the shared contract package is created at `holocene/packages/delohq-contracts/`
**Then** it exports versioned envelopes, canonical reference types, freshness vocabulary, explicit Unknown/error states, and evidence metadata.

**Given** a browser-facing DeloHQ projection is returned
**When** the response is validated against the contract
**Then** it requires `schema_version`, `source`, `generated_at`, `observed_at`, freshness state, and evidence or error detail.

**Given** a DeloHQ projection contains an Employee, Project, Action, Receipt, ticket, event, or execution
**When** its identity is serialized
**Then** it preserves the opaque canonical reference and never uses a display name or username as a join key.

**Given** adapters, routes, or views define a DeloHQ payload
**When** contract tests run
**Then** incompatible local dialects are rejected and the shared registry remains the only browser-facing contract source.

### Story 1.2: Open HQ Through the Verified Telegram Boundary

As the executive operator,
I want to open DeloHQ from Telegram without a second login,
So that only my verified executive context can access company information.

**Acceptance Criteria:**

**Given** a valid, fresh, allowlisted Telegram Mini App `initData`
**When** the executive requests a public `/hq/api/*` route
**Then** the route verifies the data, derives actor context, and forwards the request as a typed DeloHQ operation.

**Given** a request has verified actor context
**When** the route creates the command or projection context
**Then** it includes `actor_ref`, `auth_observed_at`, and originating route metadata.

**Given** `initData` is missing, invalid, expired, or not allowlisted
**When** the executive requests `/hq` data
**Then** the route rejects the request with an explicit typed auth error and exposes no source data or command capability.

**Given** the browser attempts to bypass `/hq/api/*` and call an internal host API directly
**When** the request is received
**Then** the browser-facing flow does not depend on or expose that internal route as its trust boundary.

**Given** the host API or an upstream source is unavailable
**When** an authenticated `/hq/api/*` request is made
**Then** the response reports an explicit unavailable, stale, or Unknown state and never fabricated success.

### Story 1.3: Show the Flume-Backed Company Projection

As the executive operator,
I want to see Departments, Employees, roles, and ownership from the workforce authority,
So that Company reflects the real organization without a DeloHQ-owned roster.

**Acceptance Criteria:**

**Given** the authenticated Company request succeeds
**When** Holocene builds the Company projection
**Then** it returns Departments, Employees, roles, ownership, and canonical opaque identifiers from one workforce projection snapshot.

**Given** the workforce projection is rendered
**When** the response reaches the browser
**Then** it includes source, projection generation time, observation time, and freshness state through the shared DeloHQ envelope.

**Given** the Flume transport is not yet available
**When** the transitional workforce adapter is used
**Then** registry data is treated as an operational reference, `org.yaml` data is treated as presentation metadata, and neither source is writable through DeloHQ.

**Given** the workforce source is unavailable, partial, stale, or contradictory
**When** Company renders
**Then** the affected projection is labeled unavailable, stale, contradictory, or Unknown instead of appearing empty, healthy, or current.

**Given** a newly provisioned Employee exists in the workforce projection
**When** Company loads
**Then** the Employee can appear without hand-editing a DeloHQ-specific roster.

### Story 1.4: Explain Employee Posture in Company Language

As the executive operator,
I want to see each Employee's current posture explained in company language,
So that I understand whether an Agent is working, waiting on me, blocked, quiet, unavailable, or in an unknown state without guessing.

**Acceptance Criteria:**

**Given** a Company projection containing Employees
**When** the Employee posture is derived
**Then** it maps canonical agent runtime status and event evidence into one of six distinct company postures: Working, Waiting on you, Blocked, Quiet, Unavailable, or Unknown.

**Given** an Employee is waiting on human input or decision approval
**When** posture is evaluated
**Then** it reflects "Waiting on you" and references the specific awaiting context or pending action.

**Given** an Employee is waiting on dependencies or has an active error state
**When** posture is evaluated
**Then** it reflects "Blocked" if execution is halted on blockers, or "Unavailable" if runtime communication or heartbeat is lost.

**Given** supporting runtime evidence or heartbeat is stale, missing, or contradictory
**When** posture is evaluated
**Then** it defaults to "Unknown" with explanatory evidence metadata, rather than guessing or defaulting to a healthy state.

**Given** posture is displayed in the UI
**When** rendered in the mobile-first Telegram Mini App
**Then** posture meaning is clear from text and structure rather than color alone, satisfying accessibility requirements.


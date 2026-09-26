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
- **FR-17:** Define and instantiate repo-independent named agents bound by Role and/or Job Description rather than a repository checkout.
- **FR-18:** Provide curated, portable Skillex skill packs bound to named agents that travel with them regardless of invocation context or working directory.
- **FR-19:** Persist and mount traveling Hindsight memory banks (`agent-<name>`) that accumulate role-specific learnings across all invocations.
- **FR-20:** Normalize named agent definitions so they are framework-agnostic and projectable into both persistent daemon profiles (Hermes) and dynamic CLI/headless harnesses.
- **FR-21:** Route event-driven Bloodbank commands directly to named agents by canonical `target_agent_id` with full lifecycle event reporting without requiring a repo binding.

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
FR-15: Epic 1 - Initial Telegram entry into exact DeloHQ context; deep-link continuity recurs in later epics.
FR-17: Epic 2 - Repo-independent named agent contract and role/JD binding.
FR-18: Epic 2 - Curated, portable Skillex skill packs.
FR-19: Epic 2 - Traveling Hindsight memory bank integration.
FR-20: Epic 2 - Framework-agnostic harness projections.
FR-21: Epic 2 - Event-driven Bloodbank dispatch without repo bindings.
FR-4: Epic 3 - Grouped meaningful movement in Now.
FR-5: Epic 3 - Exact context from Now items.
FR-6: Epic 4 - Human-consequence Inbox classification.
FR-7: Epic 4 - Decision explanation and supporting Evidence.
FR-8: Epic 4 - Preserved Inbox state across entry points.
FR-9: Epic 5 - Employee role, work, outcomes, blockers, and Evidence.
FR-10: Epic 5 - Agent working-context links.
FR-11: Epic 5 - Distinct conversational, observational, and consequential intervention paths.
FR-16: Epic 5 - Context-preserving handoff to the responsible Agent conversation.
FR-12: Epic 6 - Explicit confirmation for bounded Actions.
FR-13: Epic 6 - Action Receipt progress and terminal outcome.
FR-14: Epic 6 - Durable Action correlation and non-duplication.

Cross-cutting NFRs and AD-1 through AD-11 apply to every epic. The first
vertical slice owns the shared contract, Telegram verification, freshness/error
envelopes, and Company projection. Epic 2 delivers the walking skeleton for
portable named specialist agents.

## Epic List

### Epic 1: Open HQ and Understand the Company

The executive can open `/hq`, understand workforce posture, and navigate from
Departments or Employees to owned context. This vertical slice includes the
shared contract, verified route boundary, freshness/error envelope, and Flume
projection needed to make the first read experience truthful.
**FRs covered:** FR-1, FR-2, FR-3, FR-15

### Epic 2: Repo-Independent Named Specialist Workforce

The platform can define, house, and invoke portable named agents bound by Role/Job Description with traveling Hindsight memory, curated Skillex skills, framework-agnostic harness projections, and Bloodbank event dispatch — establishing our walking skeleton with the inaugural n8n workflow specialist and big-chungus infra specialist.
**FRs covered:** FR-17, FR-18, FR-19, FR-20, FR-21

### Epic 3: Know What Changed

The executive can see grouped meaningful movement and open the exact supporting
context without reconstructing a raw event stream.
**FRs covered:** FR-4, FR-5

### Epic 4: Decide from the Executive Inbox

The executive can review Approvals, Exceptions, Questions, and Briefings with
ownership, consequence, Evidence, preserved context, and terminal-state clarity.
**FRs covered:** FR-6, FR-7, FR-8

### Epic 5: Understand and Reach an Agent

The executive can understand an Employee's role and current work, inspect
Evidence, choose the correct intervention path, and continue in Telegram when
needed.
**FRs covered:** FR-9, FR-10, FR-11, FR-16

### Epic 6: Act and Verify the Outcome

The executive can confirm bounded Actions and follow durable receipts through
truthful terminal outcomes. The first Action catalog and receipt providers are
an explicit prerequisite for this epic's dependent stories.
**FRs covered:** FR-12, FR-13, FR-14

### Dependency Flow

Epic 1 provides the read-only workforce and company context. Epic 2 delivers the essential walking skeleton: repo-independent named specialists with curated skills, traveling memory, and event-driven invocation—decoupling agents from repositories and fulfilling the breadth-before-depth platform imperative. Epics 3–6 build upon this foundation to provide unified visibility (Now feed, Inbox, Agent Office) and consequential action execution across both repo-bound and cross-cutting specialist agents.

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

### Story 1.5: Navigate from Company to Owned Context

As the executive operator,
I want to navigate from a Department or Employee in Company directly into their Agent Office, Project, Evidence, or conversation and return without losing context,
So that I can quickly drill down into active work without having to reorient or re-filter.

**Acceptance Criteria:**

**Given** the executive is viewing a Department or Employee in the Company projection
**When** selecting the Department or Employee
**Then** the UI provides direct navigational links to their associated Agent Office, active Project, canonical Evidence, or Telegram conversation.

**Given** navigation occurs from Company to a drill-down context (Office, Project, Evidence, or conversation)
**When** the destination view loads
**Then** it preserves originating filters, scroll position, and context so the executive can return to Company seamlessly.

**Given** an Employee or Department link is resolved
**When** routing to the target resource
**Then** navigation uses opaque canonical identifiers (`agent_ref`, `project_ref`, `evidence_ref`) rather than display names or usernames.

**Given** an associated target (such as an Agent Office, active Project, or Telegram conversation) is unprovisioned, unavailable, or lacks supporting evidence
**When** the link is rendered or clicked
**Then** the destination shows an explicit unprovisioned or unavailable state instead of a broken route or silent failure.

## Epic 2: Repo-Independent Named Specialist Workforce

The platform can define, house, and invoke portable named agents bound by Role/Job Description with traveling Hindsight memory, curated Skillex skills, framework-agnostic harness projections, and Bloodbank event dispatch — establishing our walking skeleton with the inaugural n8n workflow specialist and big-chungus infra specialist.

### Story 2.1: Portable Named Agent Contract & Skillex Pack Binding

As a platform developer,
I want to define named agents by Role and Job Description decoupled from repository checkouts and bind them to curated Skillex packs,
So that specialists can be maintained as first-class workforce members whose capabilities travel with them anywhere.

**Acceptance Criteria:**

**Given** a named agent definition
**When** the agent contract is authored
**Then** it defines identity (`name`, `display_name`, `role`), role charter/directives, a traveling Hindsight memory bank reference (`agent-<name>`), and curated Skillex pack references without requiring a `repo` or `project_path` attribute.

**Given** an agent's curated skills are declared
**When** resolving the skills via Skillex
**Then** the agent binds to a reference-only Skillex pack composed of canonical skills from `~/code/skillex/all-skills/`, adhering to ADR-0001 reference-only topology.

**Given** an agent requires bespoke or agent-specific skills
**When** those skills are defined
**Then** they are housed in the canonical Skillex catalog or the agent's desk directory and exposed via managed symlinks, never creating unmanaged duplicate skill copies.

**Given** an agent's desk directory (`~/.agents/workforce/<name>/` or equivalent canonical location) is provisioned
**When** the environment is initialized
**Then** its `.agents/skills` directory contains verified symlinks to all declared skills in its Skillex pack.

### Story 2.2: Framework-Agnostic Projection Engine

As a platform developer,
I want tooling to project normalized named agent definitions into runtime execution harnesses,
So that specialists can run in Hermes, dynamic CLI panes, or headless workers without rewriting their configuration.

**Acceptance Criteria:**

**Given** a normalized named agent specification
**When** the projection engine runs for Hermes
**Then** it generates or updates the Hermes profile (`~/.hermes/profiles/<name>`), registers the agent in `agents-registry.yaml`, and configures gateway/systemd units without requiring a repo post directory.

**Given** a normalized named agent specification
**When** invoked in an interactive terminal or dynamic working directory
**Then** the harness runner configures the active environment with the agent's persona prompt, curated Skillex skills, and active Hindsight bank.

**Given** changes to an agent's core charter, directives, or skills in the source specification
**When** the projection is refreshed
**Then** target harness configurations (Hermes, CLI) update deterministically to reflect the changes without manual config drift.

### Story 2.3: Provision the n8n Workflow Specialist

As the lead developer,
I want an n8n workflow specialist agent with curated n8n skills and a personal Hindsight bank,
So that I have an AI specialist who understands how my workflows are organized, my node design patterns, field exposure preferences, and script thresholds.

**Acceptance Criteria:**

**Given** the n8n specialist role charter
**When** the agent is provisioned
**Then** its persona and directives codify standards for n8n workflow design, node structure, field exposure levels, and criteria for when embedded scripts (JS/Python) are preferred over stock nodes.

**Given** the n8n specialist's skill manifest
**When** resolving skills
**Then** it binds to the curated `n8n` Skillex set (`~/code/skillex/sets/n8n`), providing node configuration, expression syntax, error handling, subworkflows, and MCP tools expertise.

**Given** the n8n specialist is invoked
**When** performing workflow operations or reviews
**Then** it mounts and records to Hindsight bank `agent-n8n-specialist`, recalling historical preferences and decisions across sessions.

### Story 2.4: Provision the Big Chungus Infrastructure Specialist

As the lead developer,
I want an infrastructure specialist agent with curated homelab/Docker skills and a personal Hindsight bank,
So that I have an AI specialist who knows the big-chungus topology, Docker stack layouts, Traefik routing, and environment secrets.

**Acceptance Criteria:**

**Given** the infra specialist role charter
**When** the agent is provisioned
**Then** its persona and directives codify operational guidelines for `big chungus` Docker stacks in `~/docker`, Traefik reverse proxy routing, systemd user services, and `.env.op` 1Password references.

**Given** the infra specialist's skill manifest
**When** resolving skills
**Then** it binds to curated homelab skills including `delonet-conventions`, `delonet-dotenv`, and related infrastructure toolsets from the Skillex catalog.

**Given** the infra specialist is invoked
**When** inspecting, deploying, or troubleshooting host services
**Then** it mounts and records to Hindsight bank `agent-infra-specialist`, preserving operational learnings, service quirks, and network boundaries.

### Story 2.5: Event-Driven Dispatch & Lifecycle via Bloodbank

As a platform developer,
I want to invoke named specialists via Bloodbank commands and receive durable lifecycle events,
So that specialists can be triggered asynchronously from n8n, webhooks, or other agents without a repo binding.

**Acceptance Criteria:**

**Given** a command published to `bloodbank.cmd.agent.invocation.start` with `data.target_agent_id` matching a named specialist (e.g. `n8n-specialist` or `infra-specialist`)
**When** the fleet Bloodbank gateway processes the command
**Then** it authorizes the agent against the registry, resolves the specialist's profile and desk, and dispatches the execution payload.

**Given** an invocation is dispatched to a named specialist
**When** execution begins and concludes
**Then** the gateway emits canonical CloudEvents (`bloodbank.agent.invocation.started`, and `completed` or `failed`) echoing correlation context and outcome metadata to `BLOODBANK_EVENTS`.

**Given** a specialist invocation is triggered without an active repository context
**When** the agent executes
**Then** it runs in its designated desk environment with full access to its curated skills and Hindsight bank, completing without repo-dependency errors.




---
title: "DeloHQ: The Company in Your Pocket"
status: final
created: 2026-09-23
updated: 2026-09-23
product: DeloHQ
project: 33GOD
---

# PRD: DeloHQ: The Company in Your Pocket

## 0. Document Purpose

This PRD turns the approved DeloHQ product brief into a decision-ready
capability contract for UX, architecture, and story planning. It is written for
Jarad as the sole executive operator and for the downstream workflows that will
shape the existing Holocene `/hq` experience. It preserves the product brief's
four surfaces—Company, Now, Executive Inbox, and Agent Office—while making the
authority boundary explicit: DeloHQ is an executive experience, not a system of
record. The existing [product brief](../../briefs/brief-33GOD-2026-08-25/brief.md),
[idea bank](../../briefs/brief-33GOD-2026-08-25/addendum.md), and UX workspace are
inputs, not duplicated implementation plans.

## 1. Vision

DeloHQ gives Jarad a trustworthy view of his agent company. Within thirty
seconds of opening it, he can understand what the company is doing, what needs
his attention, who owns a piece of work, and whether an action actually
completed. The experience uses company language—departments, people, offices,
decisions, and exceptions—before exposing infrastructure language.

DeloHQ brings together the truths already held by the 33GOD systems. Flume
provides workforce identity and authority. Krebs and Pilot provide ticket
lifecycle. Bloodbank and Candystore provide event transport and history. Hermes
provides runtime execution and receipts. Holocene hosts the projections and
serves the initial experience. DeloHQ makes those truths legible and actionable
without becoming a competing source of truth.

The product is deliberately quiet when work is healthy and specific when Jarad
needs to decide or intervene. A completed action is not represented by a toast
alone: DeloHQ shows the action's progress from accepted through completed or
failed, with evidence a human can inspect.

## 2. Target User

### 2.1 Jobs To Be Done

- As Jarad, I want to understand the company's current posture quickly so I can
  decide where my attention belongs.
- As Jarad, I want to distinguish productive quiet, active work, blocked work,
  and unavailable agents so that I do not treat missing evidence as success.
- As Jarad, I want every decision or intervention request to explain its owner,
  urgency, consequence, and evidence so I can make a bounded decision without
  reconstructing context across chats and boards.
- As Jarad, I want to follow an action from acceptance to outcome so I know
  whether the company actually did what I asked.
- As Jarad, I want to move from company context to the responsible agent's
  office, board, repository, evidence, or Telegram conversation without
  remembering which front door owns each detail.

### 2.2 Non-Users (v1)

- DeloHQ v1 is not a multi-tenant customer portal.
- DeloHQ v1 is not a replacement for native agent conversations, Plane, or
  operational dashboards.
- Agents and services are subjects of the experience, not independent human
  audiences who need their own DeloHQ accounts.

### 2.3 Key User Journeys

#### UJ-1. Jarad opens the company and finds what matters

- **Persona + context:** Jarad opens Telegram after receiving a morning brief.
- **Entry state:** Jarad is authenticated in Telegram and opens DeloHQ through
  the Open HQ menu or a morning-brief deep link.
- **Path:** DeloHQ opens on Now or Company; Jarad sees meaningful movement and
  the current Department and Agent posture; he selects an item or Agent that
  needs attention; DeloHQ opens the relevant context.
- **Climax:** Jarad can state what is working, what is blocked, and what needs
  him without visiting every Agent chat or board.
- **Resolution:** Jarad remains in Company, Now, or the selected Agent Office
  with the next useful action visible.
- **Edge case:** If source evidence is stale or unavailable, DeloHQ labels the
  state as unknown or stale and explains what evidence is missing.

#### UJ-2. Jarad makes a decision and verifies the outcome

- **Persona + context:** Jarad has an Approval in the Executive Inbox and wants
  to approve a bounded recommendation.
- **Entry state:** Jarad opens a deep link to an Inbox item or selects it from
  the Executive Inbox.
- **Path:** DeloHQ identifies the requesting Agent, affected Project, reason for
  the request, consequence of waiting, and supporting evidence; Jarad chooses
  Approve or Reject; DeloHQ confirms the consequential action; the item moves
  through its visible progress states.
- **Climax:** DeloHQ displays a durable Action Receipt that says whether the
  request completed or failed, rather than implying completion from acceptance.
- **Resolution:** Jarad can inspect the evidence, return to the Inbox, or open
  the responsible Agent Office.
- **Edge case:** If the request expires, fails, or has already been handled,
  DeloHQ prevents a duplicate action and explains the current outcome.

#### UJ-3. Jarad responds to an exception without becoming an operator

- **Persona + context:** Jarad receives an Exception notification for work that
  cannot continue normally.
- **Entry state:** A Telegram notification deep-links to the affected Agent
  Office or Exception detail.
- **Path:** DeloHQ explains the human consequence, distinguishes blocked work
  from an unavailable Agent, shows the latest evidence, and identifies the
  owning Agent or Department; Jarad acknowledges the exception, opens a bounded
  intervention if one is available, or selects Message Agent.
- **Climax:** Jarad reaches the right conversation or bounded action with the
  project context already attached.
- **Resolution:** The Exception remains visible until a canonical update closes
  it; DeloHQ does not hide it because Jarad acknowledged the notification.
- **Edge case:** If no trustworthy owner or evidence exists, DeloHQ presents an
  explicit unknown state and does not invent an owner.

#### UJ-4. Jarad understands one Agent's place in the company

- **Persona + context:** Jarad wants to know what an Agent is responsible for
  before contacting or redirecting it.
- **Entry state:** Jarad selects an Agent from Company, Now, an Inbox item, or a
  notification.
- **Path:** The Agent Office shows role, Department, current work, latest
  outcome, blockers, open requests, Project links, evidence, and Telegram
  conversation; Jarad follows the link that answers his question.
- **Climax:** Jarad understands the Agent's mission and current state without
  treating a raw runtime label as the whole story.
- **Resolution:** Jarad returns to the originating surface or continues in the
  Agent's Telegram conversation.

## 3. Glossary

- **DeloHQ** — The executive experience that presents company context and
  bounded actions. It is not a system of record.
- **Action** — A bounded consequential operation requested through DeloHQ and
  executed by a Canonical System.
- **Agent** — The runtime-facing identity and behavior of an Employee. An
  Employee is the workforce entity; an Agent is how that Employee does work.
- **Decision** — A recorded human choice or recommendation outcome associated
  with an Approval, Question, or bounded Action.
- **Executive Operator** — Jarad, the sole human decision-maker for v1.
- **Flume** — The workforce authority for Employees, roles, hierarchy,
  delegation, escalation, and workforce policy.
- **Holocene** — The initial host and projection layer for DeloHQ and the wider
  33GOD mission-control experience.
- **Employee** — A deployed agent represented by Flume with a role, Department,
  work context, and current standing.
- **Department** — A company grouping used to organize Employees and explain
  ownership.
- **Project** — A repository and its associated project identity, board, and
  work context.
- **Agent Office** — The DeloHQ view that gathers one Employee's role, work,
  outcomes, requests, evidence, and useful links.
- **Company** — The DeloHQ entry surface showing Departments, Employees, and
  current posture.
- **Now** — The DeloHQ surface showing grouped meaningful movement since the
  Executive Operator's last visit or selected time window.
- **Executive Inbox** — The DeloHQ queue of Approvals, Exceptions, Questions,
  and Briefings that may require human attention.
- **Approval** — An Inbox item asking the Executive Operator to accept or reject
  a proposed bounded action.
- **Exception** — An Inbox item describing work that cannot continue normally or
  whose evidence requires intervention.
- **Question** — An Inbox item asking the Executive Operator for missing context
  or judgment.
- **Briefing** — An Inbox item intended to inform without requiring a decision.
- **Evidence** — The source facts and links that support a displayed state,
  recommendation, or outcome.
- **Company Memory** — An approved, bounded summary of durable Hindsight
  context relevant to an Employee's current work; it is not a raw memory dump.
- **Action Receipt** — The durable, user-visible record of a bounded action's
  accepted, in-progress, completed, failed, or otherwise terminal state.
- **Canonical System** — The system that owns a domain fact and is authoritative
  for that fact's mutation and completion.
- **Unknown** — A deliberately visible state used when DeloHQ lacks trustworthy
  evidence; it is not a synonym for idle or healthy.

## 4. Features

### 4.1 Company: the living organization

**Description:** Company is the primary DeloHQ entry surface. It presents the
organization as Departments and Employees, with meaningful posture attached to
the responsible owner. The surface prioritizes where work belongs and what
needs attention over infrastructure inventory. It realizes UJ-1 and UJ-4.

**Functional Requirements:**

#### FR-1: Show a Flume-backed company projection

DeloHQ can show the current Departments, Employees, roles, and ownership from a
Flume-backed projection.

**Consequences (testable):**

- The Company surface identifies the source and freshness of workforce data.
- DeloHQ does not require a DeloHQ-specific roster for an Employee to appear.
- Changes to workforce identity or hierarchy are reflected from Flume's
  projection rather than silently authored by the UI.

#### FR-2: Explain Employee posture in company language

DeloHQ can show an Employee's meaningful state—such as Working, Waiting on you,
Blocked, Quiet, Unavailable, or Unknown—with a short explanation.

**Consequences (testable):**

- The state distinguishes missing evidence from healthy inactivity.
- A raw runtime signal is not displayed as the complete human explanation.
- A stale or contradictory source is visible as a limitation or Exception.

#### FR-3: Navigate from Company to owned context

The Executive Operator can select a Department or Employee and reach the
relevant Agent Office, Project, evidence, or conversation.

**Consequences (testable):**

- Every displayed owner link resolves to the owning context or an explicit
  unavailable state.
- The Executive Operator can return to Company without losing the originating
  context.

### 4.2 Now: meaningful movement

**Description:** Now is a compact account of what changed: work started or
completed, work became blocked, an Agent requested a decision, a delivery gate
changed, a recommendation was made, or a runtime problem began preventing work.
It groups related facts into readable stories instead of exposing a raw event
firehose. It realizes UJ-1.

#### FR-4: Group meaningful movement into stories

DeloHQ can present related Evidence as a readable Now item linked to its
Employee, Department, Project, Decision, Exception, and source Evidence.

**Consequences (testable):**

- Each Now item identifies what changed, when it changed, and why it matters.
- Related events do not require the Executive Operator to reconstruct the story
  from separate raw records.
- Quiet successful activity does not crowd out Decisions and Exceptions.

#### FR-5: Open exact context from a Now item

The Executive Operator can open the Agent Office, Project, Decision, Exception,
or Evidence that explains a Now item.

**Consequences (testable):**

- A link never lands on a generic home screen when a specific context exists.
- Missing or expired Evidence is labeled rather than replaced with an invented
  summary.

### 4.3 Executive Inbox: attention and decisions

**Description:** The Executive Inbox contains only items that deserve human
attention or useful awareness. It separates Approvals, Exceptions, Questions,
and Briefings. Each item explains who is asking, why it matters now, what
happens if the Executive Operator waits, and what Evidence supports it. It
realizes UJ-1, UJ-2, and UJ-3.

#### FR-6: Classify Inbox items by human consequence

DeloHQ can classify an Inbox item as an Approval, Exception, Question, or
Briefing and show its current attention state.

**Consequences (testable):**

- The category and reason are visible before the item is opened.
- Acknowledging a notification does not silently remove an unresolved item.
- Briefings do not appear equivalent to decisions or Exceptions.

#### FR-7: Explain a decision before asking for it

DeloHQ can show the requesting Employee or Department, affected Project,
recommendation, consequence of waiting, available choice, and supporting
Evidence for an Approval or Question.

**Consequences (testable):**

- The Executive Operator can identify the decision owner and intended outcome.
- A missing owner, consequence, or Evidence is presented as an explicit gap.
- DeloHQ does not imply that a chat message alone is a durable Decision.

#### FR-8: Preserve Inbox state across entry points

The Executive Operator can enter an Inbox item from Company, Now, Telegram, or
an Agent Office and return without losing its current state or context.

**Consequences (testable):**

- Deep links open the exact item when it still exists.
- A completed, failed, expired, or already-handled item explains its terminal
  state rather than offering a duplicate action.

### 4.4 Agent Office: coherent context for one Employee

**Description:** Agent Office gathers the context needed to understand one
Employee without turning DeloHQ into a replacement chat client or operations
console. It realizes UJ-3 and UJ-4.

#### FR-9: Show the Employee's role and current work

DeloHQ can show an Employee's role, Department, mission, current work, latest
outcome, blockers, open Inbox items, and current Evidence.

**Consequences (testable):**

- The view distinguishes workforce identity, Project ownership, runtime state,
  and recent activity instead of flattening them into one label.
- The latest outcome includes a source and timestamp or is marked Unknown.

#### FR-10: Link the Employee's working context

The Executive Operator can open the relevant Project, board, repository,
Evidence, Company Memory, or Telegram conversation from Agent Office.

**Consequences (testable):**

- Links preserve the Employee and Project context that caused the navigation.
- DeloHQ never claims ownership of the linked system's data or conversation.

#### FR-11: Distinguish intervention paths

DeloHQ can distinguish Message Agent, inspect Evidence, acknowledge an
Exception, and request a bounded Action when those paths are available.

**Consequences (testable):**

- The Executive Operator can tell whether an interaction is conversational,
  observational, or consequential before selecting it.
- An unavailable path explains why it cannot be used.

### 4.5 Bounded actions and Action Receipts

**Description:** DeloHQ may request a small set of approved consequential
actions, but it never exposes arbitrary shell, systemd, or infrastructure
control. Every action is explicit, correlated to its originating item, and
visible through a durable Action Receipt. It realizes UJ-2 and UJ-3.

#### FR-12: Require explicit confirmation for consequential actions

The Executive Operator can approve, reject, acknowledge, or request a bounded
Action only after DeloHQ presents the action's target, reason, expected outcome,
and Evidence.

**Consequences (testable):**

- The confirmation view names the target and selected operation.
- An accidental tap cannot be represented as an intentional approval.
- Arbitrary command text and unconstrained infrastructure operations are not
  available through DeloHQ.

#### FR-13: Show Action progress and terminal outcome

DeloHQ can show an Action Receipt progressing through accepted, in progress,
completed, failed, expired, rejected, or otherwise terminal states as supported
by the Canonical System.

**Consequences (testable):**

- Accepted is never presented as completed without completion Evidence.
- A failed or timed-out Action exposes the failure state and next available
  path.
- Refreshing or revisiting the receipt does not create a second Action.

#### FR-14: Preserve durable correlation

Every consequential DeloHQ Action is linked to its originating Inbox item or
Agent Office and to outcome Evidence from the Canonical System.

**Consequences (testable):**

- The Executive Operator can reconstruct what was requested, by whom, when, and
  what happened afterward.
- If the Canonical System cannot provide a receipt, DeloHQ shows that the
  outcome is unknown rather than claiming success.

### 4.6 Telegram front door and mobile experience

**Description:** Telegram is the first front door for DeloHQ. Notifications,
the bot menu, and Agent conversations lead into the Mini App; DeloHQ handles
company context, navigation, decisions, and receipts. The experience is mobile
first, with desktop inspection remaining useful. It realizes UJ-1 through UJ-4.

#### FR-15: Support context-preserving Telegram entry

The Executive Operator can open Company, Now, an Inbox item, an Exception, or an
Agent Office from the Telegram bot menu, notification, or Agent conversation.

**Consequences (testable):**

- The entry point opens the intended DeloHQ context when the target is valid.
- Invalid, expired, or unauthorized deep links fail clearly without exposing
  unrelated company information.

#### FR-16: Keep conversation in Telegram

DeloHQ can open the relevant Telegram conversation without attempting to replace
  native Agent chat.

**Consequences (testable):**

- The destination identifies the Agent and Project context that motivated the
  handoff.
- A conversation is not treated as a Decision, Evidence, or Action Receipt
  until a Canonical System records it as such.

## 5. Information Architecture and Experience Rules

- Company, Now, and Executive Inbox are the persistent primary destinations.
- Agent Office, Decision detail, Exception detail, and Action Receipt are
  focused contextual views reached from those destinations.
- Company language precedes infrastructure language; implementation Evidence is
  available on demand.
- Attention is prioritized by Decisions and Exceptions, not by event volume or
  apparent productivity.
- `Unknown` is reserved for genuinely missing, stale, or contradictory
  Evidence.
- The visual design must make ownership, current posture, and next action clear
  on a phone before adding decorative company simulation.

## 6. Authority and Integration Boundaries

DeloHQ consumes and links domain truths; it does not replace their authorities.

| Domain | Canonical System | DeloHQ responsibility |
| --- | --- | --- |
| Workforce identity, hierarchy, delegation, escalation, workforce policy | Flume | Present projection, explain ownership, request approved bounded actions |
| Project identity and board binding | PJangler / project registry | Link Project context and show ownership |
| Ticket lifecycle and provider state | Krebs and Pilot | Present relevant ticket facts and deep links |
| Event transport and durable history | Bloodbank and Candystore | Group Evidence into Now, Inbox, and receipts |
| Runtime execution and execution receipts | Hermes | Present runtime consequences and terminal Evidence |
| Executive presentation and navigation | DeloHQ | Own the user experience and attention model |
| Initial web/Mini App hosting and read projections | Holocene | Serve the experience and provide projections |

The exact transport, schemas, read-model shape, authorization mechanics, and
deployment topology belong to the architecture spine and addendum, not to this
capability PRD.

## 7. Cross-Cutting Requirements

### Truthfulness and freshness

- DeloHQ must not display a current, healthy, completed, or successful state
  without supporting Evidence from the relevant Canonical System.
- DeloHQ must expose enough source and freshness context for the Executive
  Operator to recognize stale, missing, or contradictory Evidence.
- When a projection cannot support a stronger claim, DeloHQ must use Unknown or
  an explicit stale/unavailable state rather than silently preserving a healthy
  interpretation.

### Action integrity

- Every consequential Action must be correlated to one originating Inbox item or
  Agent Office and one Canonical System outcome.
- Reopening, refreshing, or revisiting an Action Receipt must not create a
  duplicate Action.
- DeloHQ must preserve pending or Unknown state when the Canonical System has not
  yet provided completion Evidence.

### Mobile clarity and accessibility

- Company, Now, Executive Inbox, Agent Office, and Action Receipt must remain
  usable in the mobile-first Telegram Mini App experience.
- State, urgency, failure, and completion must be understandable from text and
  structure, not color alone.
- Deep-link errors, expired targets, and unavailable source data must explain the
  next available path in plain language.

### Audience and data boundary

- v1 is designed for one Executive Operator; DeloHQ must not imply a broader
  audience or tenant model.
- DeloHQ should reveal only the Evidence and context needed for the selected
  decision or intervention, not expose raw private Agent memory by default.
- Domain systems remain responsible for their own authorization and mutation;
  DeloHQ must not create a shadow permission model.

## 8. Non-Goals (Explicit)

- DeloHQ will not become a general Telegram client.
- DeloHQ will not replace Holocene's operational mission-control views.
- DeloHQ will not become a raw Bloodbank event viewer or event-store query tool.
- DeloHQ will not own workforce identity, hierarchy, Projects, ticket lifecycle,
  runtime execution, or durable history.
- DeloHQ will not expose arbitrary shell, systemd, or infrastructure commands.
- DeloHQ will not treat event volume, chat volume, or Agent activity as
  productivity.
- DeloHQ will not let Telegram folders define company authority.
- DeloHQ will not require a separate repository or standalone deployment in v1.
- DeloHQ will not become a multi-user or customer-facing product in v1.

## 9. MVP Scope

### 9.1 In Scope

- A Flume-backed Company projection with Departments, Employees, ownership, and
  meaningful posture.
- Company, Now, Executive Inbox, and Agent Office on the mobile-first DeloHQ
  experience.
- Grouped meaningful movement with links to source Evidence.
- Inbox categories for Approvals, Exceptions, Questions, and Briefings.
- Decision and Exception detail with owner, consequence, Evidence, and next
  action.
- Telegram bot-menu and notification deep links into exact DeloHQ context.
- Explicit bounded actions with visible Action Receipts through a terminal
  outcome.
- Links to the relevant Project, board, repository, memory, and Telegram
  conversation.
- Clear Unknown and stale states when evidence cannot support a stronger claim.

### 9.2 Out of Scope for MVP

- A DeloHQ-owned workforce registry or org-authority store.
- Full write-through workforce reorganization; a future governed event may
  propose a change, but dragging a card cannot silently change authority.
- TDLib as a native Telegram client; Telegram remains the host and conversation
  surface for v1.
- Company replay with arbitrary historical scrubbing beyond the Now and receipt
  views needed for current decisions.
- Executive budget views before model usage and cost attribution are trustworthy.
- Voice navigation, Boardroom sessions, intervention rooms, and shareable
  context cards from the idea bank.
- Desktop-first redesign or a separate native mobile application.
- Independent DeloHQ repository, deployment, or product infrastructure.

## 10. Success Metrics

### Primary

- **SM-1:** Jarad can answer what the company is doing, what needs attention,
  who owns it, and whether an action completed within thirty seconds of opening
  DeloHQ. Validates FR-1, FR-2, FR-6, FR-9, and FR-13.
- **SM-2:** Every consequential action visible in DeloHQ has a traceable Action
  Receipt from request through terminal outcome, or an explicit Unknown state
  when the Canonical System cannot provide completion Evidence. Validates FR-12
  through FR-14.
- **SM-3:** Urgent Telegram notifications open the exact relevant Inbox item,
  Exception, or Agent Office rather than a generic landing screen. Validates
  FR-5, FR-8, and FR-15.

### Secondary

- **SM-4:** Jarad can identify the owner and next useful path for a sampled
  Company, Now, Inbox, or Agent Office item without switching among multiple
  unrelated front doors. Validates FR-3, FR-5, FR-7, and FR-10.
- **SM-5:** A newly provisioned Employee appears without hand-editing a
  DeloHQ-specific roster. Validates FR-1 and the authority boundary.
- **SM-6:** Unknown is used for missing, stale, or contradictory Evidence and
  does not silently render as healthy or completed. Validates FR-2, FR-4, and
  FR-13.

### Counter-metrics

- **SM-C1:** Do not optimize for the number of visible events, notifications,
  Inbox items, or daily opens; increased volume is a product failure when it
  obscures Decisions and Exceptions.
- **SM-C2:** Do not optimize for the number of actions taken; fewer, better-
  evidenced interventions are preferable to turning DeloHQ into a control panel.

## 11. Open Questions

1. Which bounded Actions belong in the first release beyond approve, reject, and
   acknowledge, and which Canonical Systems provide their receipts? **Owner:**
   Architecture + PM. **Revisit:** before story acceptance criteria are
   written.
2. What freshness budget should each Company, Now, Inbox, and Agent Office
   projection expose before it becomes stale or Unknown? **Owner:** Architecture
   + UX. **Revisit:** before projection implementation begins.
3. Which current `/hq` capabilities are retained, redesigned, or retired in
   the first DeloHQ slice? **Owner:** UX + Holocene. **Revisit:** during the
   first `/hq` experience audit.
4. What exact Telegram notification classes are enabled for v1, and which are
   deliberately silent? **Owner:** PM + Hermes/Momo. **Revisit:** before
   notification wiring is implemented.
5. When does the DeloHQ experience warrant its own repository or deployment
   rather than remaining hosted by Holocene? **Owner:** PM + Architecture.
   **Revisit:** when the surface requires an independent release cadence or
   deployment boundary.
6. Which Hindsight memories are safe and useful to summarize in Agent Office,
   and which remain private to the Agent runtime? **Owner:** Architecture + UX.
   **Revisit:** before Company Memory is exposed in the first Agent Office.

## 12. Assumptions Index

- **[ASSUMPTION: A-1]** Jarad remains the sole Executive Operator for v1.
- **[ASSUMPTION: A-2]** Telegram remains the first front door and identity shell
  for v1; DeloHQ does not need an independent login flow.
- **[ASSUMPTION: A-3]** Holocene remains the initial host for DeloHQ while Flume
  matures as the workforce authority.
- **[ASSUMPTION: A-4]** Existing 33GOD systems can expose enough Evidence to
  distinguish current, stale, failed, and Unknown states without DeloHQ becoming
  a second event or ticket authority.
- **[ASSUMPTION: A-5]** The first release is mobile first and desktop useful,
  not a native mobile application.
- **[ASSUMPTION: A-6]** Approved bounded Actions can be correlated to durable
  outcomes; Actions without that contract remain out of scope.
- **[ASSUMPTION: A-7]** The existing `/hq` experience is an in-place product
  starting point, not a greenfield replacement.

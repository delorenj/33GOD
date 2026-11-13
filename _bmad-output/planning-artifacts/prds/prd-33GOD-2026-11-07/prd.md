---
title: "I-9: Change crank from one feature hub"
status: final
created: 2026-11-07
updated: 2026-11-08
project: 33GOD
initiative: I-9
working_mode: coaching
entry_point: vision-and-features
stage: finalized-for-architecture
---

# PRD: I-9 — Change crank from one feature hub

## 0. Purpose and authority

Define the first useful increment of I-9: a reliable starting point and a
coordinated change workflow for a cross-repository feature, proven through the
existing I-8 pane/session-bound crank outcome. This document is for the operator,
the delegated PM and downstream architecture and component PM workflows. It is
**a finalized requirements baseline for architecture, not delivery authorization
or a claim of working software**.

Provenance matters:

- **Direct operator input:** “I want to change crank without hunting through eight
  repos.” The operator also approved the agent/terminal ownership split, Deckard's
  required ASM dependency, a central catalog, main-first delivery and crank's own
  feature repo/domain, and clarified component versus feature.
- **Delegated product input:** subsequent answers supplied as pjangler-pm driving
  the coaching session define the coordinated workflow, first proof, failure
  handling and minimum reusable handoff. These are not relabeled as direct
  operator statements. Their decision trail is `.memlog.md`.
- **Engineering choice under delegation:** create a new terminal-driver component
  rather than repurpose Perth/zellij-driver. Rationale and other technical input
  are preserved in `addendum.md`, not presented as new product requirements.

The 33GOD parent owns shared outcomes and integration acceptance. Component PMs
own their implementation backlogs. A feature hub coordinates through links; it
does not copy those backlogs or take over the existing execution authority.

## 1. Vision

The operator describes a crank behavior change once, starting at the crank
feature hub. An agent can discover the relevant owners and contracts, reuse the
existing work, coordinate the component contributions and return evidence of the
complete changed path. The operator sees the outcome, affected components,
consequential tradeoffs and genuine decision blockers—not a request to locate
repositories, relay context to their agents or reconcile their test claims.

The bet is **one place to start and resume, not one repository that implements
everything**. A current map without a usable handoff is insufficient; orchestration
without trustworthy integrated evidence is also insufficient. The first increment
may use documented manual procedures rather than new automation, provided an agent
can execute them through existing owner workflows and return the evidence to the
hub.

## 2. Users and stakes

This is brownfield internal tooling for one operator and their coding agents and
component PMs. The operator requests the outcome and settles exceptional product
or authority decisions. A coordinating agent performs discovery and handoffs;
component owners retain implementation authority. A fresh agent must be able to
continue without privileged conversation history or the operator reconstructing
context.

Primary jobs:

- Start a crank change without first rediscovering its cross-repository structure.
- Understand what is affected and what actually works across the participating
  components, including unresolved failures.
- Hand the next request to a fresh agent with a reliable, reusable starting point.

No market study, fictional personas or new dashboard product is needed for this
increment. It is not a general-purpose installer or orchestration platform launch.

## 3. Glossary

- **Component:** functionality owned within one repository, with its own domain
  and implementation workflow. Shared use does not by itself make it a feature.
- **Feature:** a cross-repository capability promoted because its scattered parts
  have become hard to maintain or extend. Crank is the first promoted feature;
  catalog candidates are not automatically promoted.
- **Feature hub:** the feature's dedicated formal repository, binding its outcome,
  boundaries, participating components, linked work and integrated acceptance.
  Feature-owned implementation may live there; participant implementation stays
  with the component owner.
- **Owner:** the component responsible for a domain fact or behavior and the
  corresponding implementation work.
- **Contract:** the owner-provided interface or behavior that participating
  components agree to use; a target contract is not an installed capability.
- **Integrated acceptance:** a gate based on observed behavior across the complete
  changed path. A green local test or Done ticket does not establish a pass.
- **Evidence record:** the actual proof result with tested revisions, conditions,
  observations, failures, limitations and source links. It is not another ticket
  state store.
- **Live agent session:** the particular running agent session selected for crank
  opt-in. Its current pane is a location, not permission transferable to whoever
  later occupies that pane.
- **Nudge:** the intended crank input delivered to an opted-in live agent session.
  Computing eligibility or logging a decision is not proof of delivery.

## 4. Capabilities and functional requirements

FR identifiers are stable across subsequent edits. These are platform seam
requirements; they do not create component implementation stories.

### 4.1 A reliable feature starting point

#### FR-1 — Discover the feature and its boundaries

An agent can find the crank feature hub from the tracked 33GOD catalog and begin
with the feature outcome and domain boundaries.

Testable consequences:

- The hub identifies crank's purpose, first-proof scope and participating
  components without the operator supplying a list of repositories.
- It distinguishes feature-owned implementation from participating integration
  work and distinguishes existing capabilities from target contracts.
- Single-repo components and other feature candidates are not silently promoted
  as part of this increment.

#### FR-2 — Find the relevant owners and contracts

From the hub, an agent can determine which owners and contracts a crank request
may affect, and verify those references against their authoritative sources.

Testable consequences:

- For the I-8 proof, the linked map covers crank's domain/registry/engine, ASM
  agent facts, terminal-driver topology/actions and the pj integration, plus any
  additional owner actually required by the changed path.
- The map follows the first proof from selection through dispatch, eligibility,
  pane-bound local-Linux Claude native messaging and evidence, linking every
  participating owner/contract. Hermes Fleet owns the narrow `agent.message`
  Adapter contract in planning; no terminal fallback. Include the existing Hermes
  job and Candybar clock where they participate; reuse their catalog/I-8 links
  rather than another separately maintained table.
- Links resolve to the real owners and interface definitions. An unimplemented,
  missing or stale reference is visible as a gap, not presented as readiness.
- Previously recorded investigations and the provisional PJAN-202 inventory are
  reused where applicable; a missing target API does not license a new duplicate.

**Narrow route amendment, delegated pjangler-pm disposition, 2026-11-08:** replaces
only this requirement's terminal-input route. Claude is a capability-gated
candidate, not certified support; owner assignment is not work acceptance or an
existing API. FR-6/NFRs, scope and execution authority remain unchanged. See
[change impact and provenance](../../architecture/architecture-33GOD-2026-11-08/route-disposition.md).

### 4.2 Coordinate without duplicating authority

#### FR-3 — Reuse and link existing work

An agent can find and reuse the affected component work and dependencies through
existing catalog, Plane relations, BMAD artifacts and owner workflows.

Testable consequences:

- I-9 links the existing I-8 outcome and relevant PJAN-202 work instead of creating
  a competing implementation backlog for the same behavior.
- Work status remains authoritative in the existing owner systems. The hub links
  or derives it and labels unavailable/stale observations; it does not maintain
  a separately editable copy of component ticket states.
- Any genuinely missing work is routed to its owner and linked back to the
  feature outcome, rather than implemented in an unrelated repo.

#### FR-4 — Hand off work with sufficient context

The coordinating agent can route required contributions through existing owning
PM/worker workflows without the operator repeating the request to each one.

Testable consequences:

- Each handoff identifies the requested outcome, applicable contracts, integration
  acceptance, dependencies and existing work links; the receiver need not recover
  context from the operator's conversation.
- Manual-but-documented handoffs are acceptable if an agent can perform them,
  observe whether they were accepted or blocked, and return results to the hub.
- Unrelated ready work may continue in parallel; work depending on a failed or
  unavailable prerequisite is not represented as ready.

#### FR-5 — Surface only consequential decisions

The operator can see the intended outcome, affected components, consequential
tradeoffs and blockers that genuinely require a decision.

Testable consequences:

- Ordinary defects within agreed requirements and existing authority return to
  the true owner for repair without a generic request for operator takeover.
- Escalation identifies one exact decision, a recommendation and supporting
  evidence. Valid causes include missing access/credentials, conflicting product
  requirements, an unapproved destructive action, extra spend/cap changes,
  ownership/scope changes or consequential tradeoffs not settled by the pillars.
- The workflow does not add new production sign-off rituals or assume new
  authority. Planning, implementation, merge, deployment and live proof remain
  distinguishable states governed by existing authority.

### 4.3 Prove the I-8 behavior through the complete path

#### FR-6 — Define and observe the first integrated acceptance

An agent can run or delegate a repeatable acceptance procedure for the scoped
I-8 outcome defined here, once the relevant execution and live-target permissions
exist. This scoped proof is distinct from full I-8 initiative acceptance (§7).

Testable consequences:

- The operator selects one specific live agent session. Renaming or reordering
  its tab preserves that choice; a different agent in the same pane does not
  silently inherit opt-in.
- Unknown or stale bindings cause no input and expose an actionable reason.
  A pane with no live agent process receives no input. Independent process/session
  corroboration checks the inventory rather than relying only on agreement among
  consumers of the same potentially wrong owner result.
- One project's dashboard exposes the actual target and why it was nudged or
  skipped. The specific existing surface is a downstream architecture choice.
- In an explicitly opted-in live proof, the chosen live agent session receives
  exactly one intended nudge and neighboring, disabled and replacement sessions
  receive none. Evidence exercises tab rename and process replacement and
  distinguishes actual input delivery from an eligibility decision alone.
- The eventual procedure specifies prerequisites and authorization, scenario
  setup/reset, positive and negative observation points, expected versus observed
  results, stop/fail conditions, evidence locations and revision/configuration
  capture. Architecture selects concrete mechanisms; the PRD does not run them.
- Each observation names the scenario and target. If a required scenario cannot
  be run or observed, integrated acceptance is not reported as passed.

This imports I-8's seam outcome for verification, not its internal task breakdown.
Cross-pane session migration and headless delivery are not implied. The procedure
must not send input to arbitrary operator panes merely to satisfy a planning gate.

#### FR-7 — Return an honest evidence record

An agent can explain the complete-path result from the hub using the actual proof
and authoritative linked evidence.

Testable consequences:

- The evidence record names exact tested revisions of participating components,
  relevant runtime/configuration conditions, procedure, observations and result.
  Tests on one revision do not certify a different deployed revision.
- It separates implemented, locally tested, integrated-tested and deployed claims.
  Outstanding failures, unrun checks, manual steps and limitations remain visible.
- The latest attempt cannot be masked by an older pass. If revisions or relevant
  conditions change, previous evidence remains historical rather than an
  unqualified certification of the new state.
- Authoritative evidence can be linked rather than copied, but an agent starting
  at the hub can resolve it without the operator gathering the pieces.

#### FR-8 — Repair failure without manufacturing success

When integrated acceptance fails, the coordinating agent retains the failed gate,
records observed versus expected behavior and routes defects to their owners.

Testable consequences:

- Defect work is owner-linked, fixes receive independent review, and the failed
  seam plus relevant regressions are rerun after those fixes.
- Retries require evidence-backed progress. Repeated failures without progress
  trigger diagnosis/course correction rather than an unbounded blind loop.
- Local green results or board states cannot override a failed integrated gate.
  Scope expansion, suppressed negative checks or safety bypass cannot turn it green.

### 4.4 Make the next request independently resumable

#### FR-9 — Leave a reusable handoff for a fresh agent

A fresh agent can start the next crank request at the hub without the operator
reconstructing the owner map or forwarding prior conversations.

Testable consequences:

- The hub supplies the outcome/boundaries, accurate linked owner/contract map,
  existing work/dependencies, repeatable acceptance procedure and last real
  evidence record with exact revisions, failures and limitations.
- A fresh agent, without this coaching transcript, can identify the relevant
  owners, reuse the existing work, run or delegate the authorized proof, and
  explain its complete-path result without asking the operator to navigate
  participating repos. Component workers may still access their owning repos.
- The first exercise records where manual steps or missing context remain.
  Documentation counts as sufficient only if the fresh agent can actually follow it.

## 5. First-increment scope and explicit deferrals

**Included:** crank as one discoverable formal feature hub; linked owner/contracts
and work/dependencies; agent-performable documented coordination; the repeatable
I-8 proof and honest evidence; owner-routed failure handling; a fresh-agent reuse
exercise. Reuse the current platform rather than build replacement infrastructure.

**Deferred:** generic feature installers/updaters/uninstallers, universal
orchestration engines, more feature promotions, new terminal backends, automatic
rollbacks, headless delivery and cross-pane migration. If the first proof reveals
that one is truly necessary, surface an explicit scope decision with evidence;
do not silently include it.

The approved ASM/terminal split and Deckard's required ASM dependency remain target
constraints. This increment does not claim that every foundation extraction or
consumer migration is already done, nor make completion of all of I-9 a prerequisite
for a useful crank proof. Architecture must identify the minimum owner work needed
without introducing new duplicate authorities. Existing authority—not a new ritual—
governs delivery. Planning completion alone authorizes no merge, deployment, live
input or economics-cap change; Candybar remains the only recurring clock.

## 6. Non-functional requirements

- **NFR-1 — One owner per fact:** use existing owner interfaces and authoritative
  work/evidence systems. No second state machine, editable duplicate backlog or
  universal scheduler is introduced for feature coordination.
- **NFR-2 — Fail closed at the nudge boundary:** ambiguous, unknown or stale
  live-agent-session binding must produce zero input, even when component-local
  checks pass. A visible, actionable reason is required.
- **NFR-3 — Reproducible evidence:** every integrated result is bound to its exact
  tested revisions and relevant conditions. An independent agent must be able to
  follow the procedure or identify a concrete access/authorization blocker.
- **NFR-4 — Migration continuity:** preserve existing authority and current cap
  while planning and migrating. No competing clock, unapproved destructive action
  or uncontrolled live-pane test is introduced to obtain a pass.

## 7. Success measures and counter-measures

No time savings or percentage improvement is invented. Establish a baseline by
performing and recording the first proof and the fresh-agent reuse exercise.

| ID | Observable success | Counter-measure |
|---|---|---|
| SM-1 | Fresh agent discovers the affected owners/contracts and existing work from the hub without operator repo navigation or context forwarding. | Record unresolved links, omitted owners, required operator reconstruction and remaining manual steps; do not hide them behind a successful kickoff. |
| SM-2 | The opted-in I-8 proof observes one intended nudge and zero input to neighboring, disabled or replacement sessions, with rename/replacement scenarios covered. | A false target, unobservable exclusion or unrun required scenario keeps the gate unproven/failed; a local test count is not a substitute. |
| SM-3 | Fresh agent runs or delegates the permitted proof and explains the actual integrated result with exact revisions and limitations. | Record reliance on private transcript knowledge, stale evidence, duplicate work tracking and manual evidence assembly. |

### Three independently evidenced results

**Accepted delegated decision, pjangler-pm, 2026-11-08:** track these separately,
with explicit evidence, remaining failures and limitations:

1. **Reusable hub/workflow demonstrated:** a fresh agent performs discovery,
   reuses the work, runs or delegates a permitted proof and explains the actual
   result from the hub. An honest failed behavior result can demonstrate this
   handoff capability; merely documenting an unexercised procedure cannot.
2. **Scoped crank behavioral proof passed:** all FR-6 scenarios and their positive
   and negative observations pass at the stated revisions/conditions. A successful
   handoff cannot turn this result green or support a claim that crank works when
   behavior remains failed or unproven.
3. **Full I-8 acceptance:** remains governed by I-8's full linked acceptance scope.
   Cross-pane migration, pane movement between tabs and restart recovery remain
   outstanding I-8 work, neither waived nor prerequisites for demonstrating the
   narrower reusable workflow or scoped proof. A scoped pass is not I-8 completion.

Evidence records identify which result they establish, rather than a single
ambiguous "done" flag. Unknown, failed and unrun conditions remain explicit.
Independent process/session corroboration and no-agent/no-input remain part of
the scoped FR-6 coverage. None of these planning decisions changes the existing
cap-lift condition or grants merge, deployment or live-input authority.

## 8. Downstream questions and gate status

No further product choice is inferred from sample manifest fields, commands or
installation transcripts in the initial studies. Downstream architecture must
resolve:

- The minimum contract surfaces and foundation work for this thin proof, including
  supported agent/session identities and how stale/replaced bindings are detected.
- The concrete existing project dashboard surface and evidence/handoff layout,
  without introducing a second truth store.
- The authorized scenario arrangement and observation method that establish both
  actual delivery and zero unintended input; no live execution occurs in this PRD run.

These are architecture/delivery questions under the recorded constraints, not
implicit expansions of PRD scope. Broader state-display semantics, repo visibility
or sweeping policies do not become required decisions unless the thin proof
actually depends on them; then escalate with the concrete dependency.

Downstream questions are owned by the I-9 architecture workflow and revisited
before its final review. If reality-checking reveals a scope/authority conflict,
return the exact decision to the delegated PM/operator rather than infer approval.

**PRD gate:** source reconciliation, decision-log audit, independent quality
recheck and delegated completion-scope disposition are satisfied. See
[final gate evidence](final-gates.md); the original review remains historical.
No substantive PRD blocker remains. The delegated PM requested continuation into
I-9-scoped architecture, not component implementation. Briefly explain each BMAD
step's purpose and artifact while using it; learning the method is a secondary
goal, not a separate training deliverable.

## 9. Source inputs

- [Initiatives I-8 and I-9](../../initiatives.md)
- [Tracked feature catalog](../../../../features.toml)
- [ASM ownership study](../../33god-features/asm-ownership-study.md)
- [Initial packaging research](../../33god-features/feature-packaging-design.md)
- [Accepted Director Rule](../../director-rule-plan.md)
- [Architecture inputs](addendum.md) and [canonical coaching log](.memlog.md)

The initial studies contain superseded proposals. The direct operator decisions
and separately attributed delegated coaching decisions take precedence.

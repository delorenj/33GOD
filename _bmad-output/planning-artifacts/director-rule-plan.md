---
title: 'The Director Rule: BMAD for a parent repo with pjangler-registered submodules'
status: 'accepted'
created: '2026-09-29'
accepted: '2026-09-29'
owner: 'grolf (33god-pm)'
---

<!-- Deliberately NOT named epics.md and deliberately uses no `## Epic N:` / `### Story N.M`
     headings: bmad sprint planning turns that grammar into a loop-dispatchable board. -->

# The Director Rule

> **The parent holds outcomes that span children. It never holds work inside one.**
> Applies to any repo with at least one submodule registered as a pjangler project (`pj list`).

## Why

Today the parent is doing its children's backlogs. Verified 2026-09-29:

- Of the 10 stories drafted in `epics.md`, 7 are pure child implementation (Holocene or Flume), 3 are mixed (1.3, 2.2, 2.5), **0 are pure integration**.
- Flume has `_bmad/` installed and an empty `_bmad-output/`, so Flume's whole Epic 2 is planned in the parent.
- Story 1.1 (Holocene code) was dispatched by `bmad-loop` from the parent's board. It paused a finished story because the spec stamped a Holocene SHA that does not exist in the parent repo. Story 2.1 stamped a parent SHA and passed, so success depended on which SHA the dev session wrote.
- Story 2.2 was ordered without knowing the 2026-09-23 named-agent work existed (`epic-2-context.md` never mentions it).

BMAD itself gives no help: its planning skills have no story type, owning repo or delegated story, and `bmad-loop` treats every `sprint-status.yaml` row as code to implement.
`bmad-architecture` is the one BMAD skill whose purpose ("keep separately built parts consistent") is director-level.

## The invariants (borrowed from how companies do it)

1. **Level is decided by who must be involved, not by size.** Parent artifact if and only if at least two children, or a timing dependency a child cannot see, are involved.
2. **One owner per fact.** Implementation facts belong to the child. Integration, timing and dependency facts belong to the parent.
3. **Link, don't copy.** The parent refers to `flume:2-1-<slug>` or `FLUME-12`, never restates scope.
4. **Pull, not push.** Delegation is a request the child accepts through its own intake and its own BMAD flow.
5. **Status is derived, never re-entered.**
6. **Acceptance-criteria split.** Parent ACs are checkable at the seam. A parent AC that needs a child's internals is a child AC in disguise.
7. **Default interaction is X-as-a-service at a contract seam.** Joint work is a time-boxed exception with an end date.

## Where each artifact lives

| Artifact | Parent (33GOD) | Child (submodule) |
|---|---|---|
| PRD | Platform PRD: requirements that only make sense across children | Product PRD (DeloHQ is a Holocene product) |
| Architecture | Cross-cutting ADs: authority boundary, inter-project contracts, deployment topology | Internal architecture and package layout |
| Epics | **Initiatives** in `initiatives.md` (integration outcomes) | Implementation epics in the child's `epics.md` |
| Stories | **Integration stories** (seam outcome plus delegations) | Implementation stories, specs, loops |
| `sprint-status.yaml` | **None** (see Guards) | The child's own; the loop runs here |
| Status | Plane board (Grolf) plus a derived rollup (Phase 3) | Child's board |

**The parent MAY hold:** Initiative, Integration Story, Milestone (a dated, checkable seam state), Dependency (`A blocked_by B`, cross-project), Decision (ADR plus `bloodbank.repo.decision.recorded`), traceability map (FR to child epics, derived).
**The parent MAY NOT hold:** a story owned by a child; any AC naming a path or symbol inside a child; a copy of a child's epic or story text; a child story key as its own key; a `spec-*.md` for child code.

### Keys

Parent keys are non-numeric: `I-1` for an initiative, `I-1.3` for an integration story.
The loop parser accepts only `epic-<digits>` and `<digits>-<digits>-<slug>` rows and ignores everything else, so a parent story can never be picked up even if someone pastes it into a sprint-status file. This is a deliberate departure from fork 3's reserved-numeric-range idea (`epic-101`), which would parse and therefore be dispatchable.
Cross-references are always project-qualified (`flume:2-1-portable-named-agent-contract-…`). A bare `2-1` is not a valid cross-project reference; `2-1` already exists on at least 10 boards under `~/code`.

## Delegation protocol

1. **Author.** Grolf writes an Integration Story: outcome, seam ACs, `delegations[]`, `depends_on`. No task breakdown.
2. **Request.** For each delegation Grolf sends the child a Work Request: outcome, seam AC, priority signal, back-link (`33GOD:I-1.3`), labels `from:33god` and `int:I-1.3`. It says what must be true at the seam, never how.
   - Preferred (pull): Bloodbank command `bloodbank.cmd.agent.invocation.start` to the child PM, whose own intake creates the ticket and, through the child's BMAD flow, whatever epic or story it wants.
   - Practical form today: file the Work Request as a ticket on the child's board. The Plane-to-Bloodbank lane (ticket created, then grooming, then `bloodbank.cmd.agent.invocation.start`) delivers it to that board's PM. Filing goes through `px`.
   - A child with no PM has no receiver; hire one first (Flume was in this state until 2026-09-29, now `flume-pm`).
3. **Link.** A Plane relation (`blocked_by` or `relates_to`) from the parent ticket to the child ticket, through `px` (the only Plane writer).
4. **Implement.** The child owns triage, refinement, spec, loop, review and merge, run inside the child.
5. **Signal.** Child ticket Done emits `bloodbank.repo.task.completed` (schema exists). Grolf's reconcile pass matches it to the delegation.
6. **Verify at the seam.** "Child Done" is not "integration done". The parent story closes only on parent-owned evidence: a smoke command, event query or contract test that exercises the seam.

## Guards, strongest first

1. **No `sprint-status.yaml` in the parent.** Tested in a scratch project: with no board, `bmad-loop validate` fails and `run --dry-run` errors. This is the hard guard against `bmad-loop`. (Interactive `/bmad-build` can still be invoked, so also add the AGENTS.md pitfall.)
2. **Non-numeric keys**, so nothing in the parent parses as a loop row.
3. **`director.scope` lint in `pj audit`** (deterministic, no LLM):
   - R1 parent epic or story text must not reference paths inside a registered submodule.
   - R2 a story owned by a child must not be in a parent board.
   - R3 warn on title or AC overlap with a child epic or story (duplicate suspicion).
   - R4 every delegation resolves to a ticket ref or `pending`; orphan tickets labeled `from:<parent>` warn.
   - R5 fail if a parent story's spec or diff touches a child path. This would have flagged Story 1.1 on day one.
4. **Grolf's charter.** Its "never mutate code" rule is prose only today; only the interactive Momo agent has a structural no-Edit/Write guard. Whether Hermes can enforce a tool allowlist for Grolf is unverified, so do not rely on the charter alone.

## Grolf's role

- Flume composes Grolf's SOUL from `roles/pm.md`, shared by every per-repo PM. Do not hand-edit `SOUL.md`. Add a `director` role file and re-compose with `flume remediate hermes.pm-scaffold 33god`.
- New directives: never author a story owned by a child; delegate by request, never by task list; link, don't copy; derive status; close only on seam evidence; parent presence is opt-in. The list of children comes from the pjangler registry, never hand-maintained.
- Lifecycle: delegation is an axis, not a new phase.
  - triage: the first question becomes "who owns the code?"; child-owned means convert to a delegation, do not decompose.
  - refining: repair seam ACs, strip implementation ACs.
  - in progress: WIP=1 applies to parent-owned work only; waiting on a delegation is a relation, not a worker.
  - review: inspects seam evidence, not child code.
  - done: derived, never set by hand.
- BMAD at the parent level: `bmad-prd`, `bmad-architecture`, `bmad-correct-course` (to deliver a delegation into a child). Not `bmad-build` or `bmad-loop` for child work.

## Child side

Each child needs `_bmad/` installed (all but two already have it), its own `epics.md`, and its own board.
A delegation enters through `bmad-correct-course`, then a `bmad-sprint-planning` refresh, then `bmad-loop` run **inside the child**. Running in the child also removes the submodule baseline mismatch.
The child's resulting story key is recorded back on the parent story as a qualified ref.

## Prerequisites found (all verified 2026-09-29)

- **Flume's PM is `flume-pm` ("Flumey")**, created 2026-09-29: `flume/.project.json` lists it as provisioned, the Hermes registry row has `bloodbank.enabled: true` and `target_agent_id: flume-pm`, its `FLUME` board is `bf5663f0-8d37-41c6-97a3-437d45d64523`, and `hermes-flume-pm-gateway.service` is active. Registered and running; not yet exercised by a delegation.
- **`px` cannot go cross-board:** `~/.config/krebs/manifests.json` does not exist, and `px` has no relation or link command.
- **Plane cross-board relations exist:** `GET .../work-items/{id}/relations/` returns 200. POST is untested.
- **Holocene is not in the pjangler registry.** It has a PM and a `HOLOC` board in the Hermes registry. Only `pjangler`, `bb`, `flume`, `candystore` and `momo` are registered among the 8 submodules; `hermes-agent-template` and `mcp-hub` are not, and a rule keyed on registration excludes them.
- **pjangler is already in the loop for this:** `pj audit` has a rule framework (`AuditFinding`, existing `bmad.*` rules), so `director.scope` fits its shape.

## Where today's parent epics land

| Parent today | Verdict | Landing |
|---|---|---|
| Epic 1 (1.1, 1.2, 1.4, 1.5) | Holocene implementation | Move to Holocene BMAD; 1.1 already done, leave a tombstone `moved_to: holocene:1-1` |
| Story 1.3 | Split | Flume read-transport decision (AD-5) becomes a parent integration story; consumer work goes to Holocene |
| Epics 3-6 | Holocene implementation | Move to Holocene. The parent keeps one initiative, "DeloHQ executive surface", with only the seam stories (evidence contract, action catalog and receipt providers, Telegram and gateway boundary) |
| Stories 2.1-2.4 | Flume implementation | Move to Flume BMAD. This creates Flume's epic. 2.1 is done (tombstone). 2.2 is rescoped first (below) |
| Story 2.5 | Genuine integration (Flume, Bloodbank, gateway) | Stays in the parent as an integration story |
| FRs, NFRs, AD-1 | Platform PRD and architecture | Stay. AD-2 and AD-11 (package layout) move to Holocene architecture. FR-to-epic map becomes a derived table |

**Story 2.2 rescope (from the 2026-09-23 overlap check).** The Hermes profile, systemd and registry mechanics already exist as template steps 10, 70 and 80, but step 10 dies without an owning repo and `<project>/.agents/skills.json`. Story 2.1's validator also re-invented identity rules more loosely than the Sep 23 `readRoleIdentity()`. So 2.2 becomes: (1) make the 2.1 validator reuse the Sep 23 identity rules, (2) let step 10 accept a desk as its owning root, (3) build the new harness runner. It becomes Flume's first story.

## First dogfood initiative: I-1 "Flume agent rollout throughout the system"

Every story is `owner_project: 33god`; ACs are observable at the seam and name no child internals.

| Key | Story | Delegations | Depends on | Seam AC |
|---|---|---|---|---|
| I-1.1 | Flume and PJangler seam | pjangler, flume | none | For any pjangler-registered project, `flume roster` shows its PM post with zero hand-maintained fields; `pj audit` and `flume review` agree on the same repo; the two binaries share only the handbook contract |
| I-1.2 | Workforce events on the bus | bloodbank, candystore | I-1.1 | Hire, onboard, offboard and review each emit a schema-valid event, queryable in Candystore by correlation id; durable consumers survive restart |
| I-1.3 | Registry and handbook seam | flume, hermes-agent-template | I-1.1 | `flume remediate hermes.registry-parity` is clean across all registry agents; an induced drift is detected within one reconcile cycle |
| I-1.4 | Named-agent invocation through the gateway (was 2.5) | flume, bloodbank, hermes-agent-template | I-1.3 | `bloodbank.cmd.agent.invocation.start` with a named `target_agent_id` yields `started` then `completed` or `failed` with echoed correlation id, with no repo context present |
| I-1.5 | Every project has a declared post | flume, each child PM | I-1.1 | `flume roster` lists every pjangler project with post state in {deployed, planned, none-by-decision}; zero unknown |
| I-1.6 | Company projection sourced from Flume (was 1.3 seam) | flume, holocene | I-1.1 | `/hq` company view is built from one Flume snapshot with a freshness envelope; hierarchy no longer read from `org.yaml`; a Flume change appears in `/hq` within the declared max age |
| I-1.7 | Skill packs survive the round trip | skillex, flume | none | Each named agent's desk `.agents/skills` symlinks resolve to canonical Skillex entries and stay valid after a Skillex sync |
| I-1.8 | Named identity end to end on the board | flume, pilot, krebs | I-1.5 | Plane ticket activity is attributed to the named agent, not only the post, across px and Krebs writes |

## Phases

**Phase 0 (about a day): write the rule and stop the bleeding.**
Land this document; add a one-line pointer in the parent `CLAUDE.md` ("bmad-loop runs in each child, never in the parent"); create `initiatives.md` with I-1.1 and I-1.6 only; freeze new parent implementation stories (Epics 3-6 stay backlog, nothing lost).

**Phase 1: one real delegation, end to end.**
First delegation: hand Epic 2's Flume-owned stories (2.1-2.4) to Flumey so Flume's own BMAD creates Flume's epic (Story 2.1 done, Story 2.2 rescoped). It is real work, it is Flume-only, and it exercises the whole path. Create `~/.config/krebs/manifests.json` to unblock `px --board`; file the ticket on `FLUME` with back-link labels (`from:33god`); add the relation through a minimal `px link`; observe the `agent.invocation.started` and later `task.completed` events; verify the seam by hand. Then repeat with I-1.6 across `HOLOC` and `FLUME`. Success is closing the loop once.

**Phase 2: lint.**
Deliver `director.scope` (R1-R5) to pjangler as a Work Request (the first delegation of the rule itself). Run against the parent. Expect red on Epics 1 and 3-6 on day one; that is the dogfood proof.

**Phase 3: migrate, charter, rollup.**
Move Epic 1 and 3-6 to Holocene and 2.1-2.4 to Flume with tombstones, in small commits verified per repo (the parent auto-checkpoint sweeps cross-repo moves into submodule working directories). Register Holocene with pjangler. Add the `director` role and re-compose Grolf. Add the derived `portfolio-status.yaml` rollup only if the Plane board proves not to be enough; do not build it up front.

## Risks

- **Ceremony creep** for a solo developer: keep parent artifacts to frontmatter plus seam ACs, and let the machine derive status.
- **Vague seam ACs rot:** require an executable check (smoke command, event query, contract test) per integration story.
- **Reprovision traps:** Grolf's SOUL is generated; edit the Flume role file and re-compose, never the generated file. Four registries record each repo path.
- **`px` is the only Plane writer:** a direct REST relation POST would bypass it; a stopgap must be flagged as a bypass.
- **Lint false positives:** R3 is warn-only; R1, R2 and R5 are path- and registry-based and precise.

## Defaults assumed unless changed

- `bmad-loop` runs inside each child.
- Parent presence threshold: at least two children, or a timing dependency on another child.
- The dependency record is a native Plane cross-board `blocked_by` relation, delivered through `px link`.

## Decisions (2026-09-29)

1. DeloHQ (PRD, epics, AD-2, AD-11) moves wholly to Holocene.
2. Flume gets its own PM rather than Grolf driving the `FLUME` board: `flume-pm` ("Flumey"), created and onboarded 2026-09-29.
3. Parent keys are non-numeric: `I-n` and `I-n.m`.
4. Grolf gets a new `director` role file, composed by Flume, rather than a `portfolio:` block on `pm`.
5. Epics 3-6 are tombstoned in place until Holocene starts them; Flume's 2.1-2.4 move first.

## Status of the phases

- **Phase 0 (2026-09-29):** this plan accepted; pointer added to the parent `CLAUDE.md`; `initiatives.md` created with I-1.1 and I-1.6; `epics.md` frozen with owner notes and tombstones on every epic.
- **Transitional gap:** Epic 1's rows are still in the parent's `sprint-status.yaml` until they migrate to Holocene (Phase 3), so a bare `bmad-loop run` in the parent could still pick up Story 1.2. The rule is to not run it there; the structural guard (no parent board) arrives with the Epic 1 migration.

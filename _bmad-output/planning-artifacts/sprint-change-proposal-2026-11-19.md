---
title: 'Sprint Change Proposal: 33GOD CLI surface (one contract, native binaries)'
type: sprint-change-proposal
workflow: bmad-correct-course
mode: batch
created: 2026-11-19
status: approved
approved_by: Jarad (operator), 2026-11-19, untagged message in an interactive Claude Code session
owner: Grolf (Hermes PM desk 33god-pm)
scope_classification: moderate
binds: [Epic 7, Story 7.1, Story 7.2, Story 7.3, Story 7.4, Story 7.5, Story 7.6, Story 7.7]
sources:
  - research/cli-surface-research-2026-11-19.md
  - architecture/architecture-33GOD-2026-11-19-cli-surface/ARCHITECTURE-SPINE.md
  - epics.md
  - ../../features.toml
---

# Sprint Change Proposal: 33GOD CLI surface

**Operator approval (2026-11-19, verbatim):** "yes! Make sure this is locked in via
appropriate bmad steps, then start on step 1 implementation. Note: this should be
owned by Grolf (33god_pm)". The change below is the approved decision. This
workflow ran in **batch mode**, non-interactively, with the decision text taken as
the operator's answers to every checklist prompt. It records the analysis and the
handoff; it does not authorize anything beyond the decision.

**Owner:** Grolf, the Hermes PM desk `33god-pm` (`display_name: Grolf` in
`~/.hermes/agents-registry.yaml`), PM of the 33GOD Plane board (workspace `33god`,
identifier `33GOD`, bound in `~/code/33GOD/.project.json` `agents.33god-pm`).

## 1. Issue summary

### Problem statement

33GOD's command surface depends on the shell it happens to run in, and it has no
shared contract an agent can read. Jarad asked whether 33GOD should copy the AWS
CLI (one `aws`-style umbrella) and move work out of mise tasks. A four-agent
investigation on 2026-11-19 (inventory, AWS internals, architect design,
adversarial critique) answered: **follow AWS's contract, not its monolith**. The
evidence and the corrected verdict are in
[`research/cli-surface-research-2026-11-19.md`](research/cli-surface-research-2026-11-19.md);
its "corrected verdict" section supersedes its design section.

### Category

Strategic direction (new requirement from the operator) combined with technical
limitations discovered during the investigation. No in-flight story triggered it.

### Evidence (from the research file, re-checked where noted)

- **krebs has no installed command.** Candybar runs it by interpreter plus repo
  path: `krebs/.candybars/krebs-tick.candybar.toml:41` is
  `argv = ["node", "/home/delorenj/code/33GOD/krebs/bin/krebs.mjs", "tick", "--json"]`
  (re-checked 2026-11-19).
- **Node is chosen per cwd and per PATH.** Under a minimal or systemd PATH, `node`
  is `/usr/bin/node` v20.19.4, and PATH skillex exits 2 with
  `E_NODE_VERSION: Node 24 or newer is required; running 20.19.4`
  (skillex `src/cli.ts:364-377`). Several repos pin node 20 or 22.
- **Two `hermes` binaries.** `_.path` in `~/code/33GOD/mise.toml:4` and
  `~/code/skillex/mise.toml:14` put `agents/hermes/pm` on PATH, so the per-PM
  launcher shadows `~/.local/bin/hermes` depending on cwd (re-checked:
  `which -a hermes` lists `~/code/skillex/agents/hermes/pm/hermes` before
  `~/.local/bin/hermes` from the skillex checkout).
- **Two skillex behaviours.** PATH skillex 0.4.8 at research time, 0.4.10
  released (`npm view @delorenj/skillex version` = 0.4.10, re-checked), `pj skills`
  runs a bundled 0.4.4 (`pjangler/package.json:64`, re-checked), flume pins
  `github:delorenj/skillex#f51ff3e` (re-checked), and eleven versions were
  co-installed under mise.
- **Five JSON envelope shapes and two unknown-command exit codes** across the
  component CLIs (skillex `{schema:2,...}`, flume `{schema_version:1,...}`, px
  flat `{ok,...}`, raw payloads elsewhere; 1 vs 2 for an unknown command).
- **Only px has a machine-readable command tree** (`px help --json`,
  `pilot/src/surface.js:936`).
- **skills:sync still sits in 34 mise.toml files** despite the 2026-10-10 skillex
  rule, because the template generators still emit it.
- **An argv guard would be bypassed by passthrough.** `native_clock_guard.py`
  (bloodbank hook-hub) branches on `name == "hermes"`; `33god hermes cron create`
  would slip past the Candybar-only-clock rule.

## 2. Change analysis checklist (batch results)

Status key: `[x]` done, `[N/A]` not applicable, `[!]` action needed (recorded
for Grolf).

### Section 1: Understand the trigger and context

- `[x]` **1.1 Triggering story.** None. The trigger is an operator question and
  the research run of 2026-11-19, not a story. Recorded as "no triggering story".
- `[x]` **1.2 Core problem.** Strategic direction plus discovered technical
  limitations (statement above).
- `[x]` **1.3 Evidence.** Listed in §1, with file and line anchors from the
  research file. Facts marked "re-checked" were re-read for this proposal.

### Section 2: Epic impact assessment

- `[N/A]` **2.1 Current epic.** No current epic contains this work. Epics 1-6
  are DeloHQ and named-agent work, frozen or migrated to children under the
  Director Rule; none is affected.
- `[x]` **2.2 Epic-level change.** Add **Epic 7: 33GOD CLI Surface — one
  contract, native binaries** with stories 7.1-7.7.
- `[x]` **2.3 Remaining epics.** Epics 1-6 are unaffected. Epic 2's named-agent
  work consumes skillex and hermes; Story 7.1 (one skillex, the hermes shadow)
  removes skew for it rather than changing its scope.
- `[x]` **2.4 Obsolete or new epics.** None obsolete. One new epic (Epic 7).
- `[x]` **2.5 Order and priority.** Story 7.1 runs now at the operator's
  direction. 7.2 precedes 7.7 (blocking relation). 7.5 precedes any passthrough
  in 7.4 or later. 7.3 converts components by agent call frequency.
- `[!]` **Director Rule tension.** `epics.md` is frozen for new implementation
  stories (2026-09-29): the parent holds outcomes spanning children, and the rule
  places those in `initiatives.md` under non-numeric keys so `bmad-loop` cannot
  dispatch them. Epic 7 spans at least nine child repos (pjangler, pilot, krebs,
  skillex, candybar, flume, bloodbank, hermes-agent-template, 33god-platform), so
  it is parent-level by invariant 1. It is appended to `epics.md` with numeric
  keys and `sprint-status.yaml` rows because the operator's lock-in request
  asked for epic, story spec and sprint status. This is a recorded exception.
  **Guard:** do not run `bmad-loop` in this repo (the Director Rule still
  applies); per-repo code lands in each child, and each child's commits are the
  evidence. **Grolf decides** at the first verdict whether to keep Epic 7 here or
  mirror it as an `I-14` initiative with child delegations.

### Section 3: Artifact conflict and impact analysis

- `[x]` **3.1 PRD.** No conflict. Neither PRD covers a CLI surface:
  `prds/prd-33GOD-2026-09-23` is DeloHQ; `prds/prd-33GOD-2026-11-07` is I-9
  (change crank from one feature hub). This is a gap, not a contradiction. The
  requirements for this change are stated as CS-1 to CS-6 in the new architecture
  spine and as the Epic 7 acceptance criteria. No PRD is rewritten.
  `[!]` If Grolf wants a scoped platform PRD for the CLI surface, it follows the
  I-9 pattern (scoped PRD, not a regenerated platform PRD). Not required to start.
- `[x]` **3.2 Architecture.** No conflict with existing spines:
  - `architecture-33GOD-2026-09-23` (DeloHQ) is unaffected.
  - `architecture-33GOD-2026-11-08` (I-9 crank hub) is consistent: its AD-12
    ("Source tracks main; exceptional pins carry a reason/exit ticket") is the
    rule that rejects hard-pinning skillex in mise (the deviation recorded in
    the new spine's AD-6).
  - New spine: `architecture/architecture-33GOD-2026-11-19-cli-surface/ARCHITECTURE-SPINE.md`
    (AD-1 to AD-10).
  - **Stale:** the research file's design section (a `33god.cli/1` schema, a
    passthrough `33god` umbrella, Candybar argv through `33god`, Bloodbank and
    MCP projections). It is superseded by the corrected verdict and the new
    spine. It stays in the file as provenance and is not rewritten.
- `[N/A]` **3.3 UI/UX.** No user interface. The UX drafts
  (`ux-designs/ux-33GOD-2026-08-25`) are DeloHQ shells.
- `[x]` **3.4 Other artifacts.**
  - **Candybar manifests:** krebs-tick moves to the pinned launcher (7.1 AC3);
    other `.candybars` with bare `node`/`npx` are reported (7.1 AC3).
  - **Launchers in `~/.local/bin`:** one tracked, idempotent installer in
    33god-platform with `--check` (7.1 AC2), portable to the Mac peer.
  - **Agent hooks / guards:** `native_clock_guard.py` and other argv guards
    learn to unwrap `33god` before any passthrough (7.5).
  - **Generators:** hermes-agent-template and `flume/templates/hermes-agent` emit
    `skills:sync`; fix in 7.6. Generated files are rendered, never hand-edited.
  - **Skills and docs:** the 33god-hub skill's Commands section, hub command
    blocks (7.7), and every doc citing a deleted alias task (7.6, same commit).
  - **CI:** pjangler's `.github/workflows/publish.yml` trusted publishing carries
    the 7.1 AC5 release. No paid runners are added.
  - **features.toml:** `[candidate.cli-surface]` added (F1: inventory, not
    authorization for a new repo).
  - **Mac peer (Damian's Mac):** mise stays the deployment mechanism there; the
    launcher installer resolves node through mise, not a Linux path.

### Section 4: Path forward evaluation

- `[x]` **4.1 Option 1, Direct Adjustment: viable (selected, hybrid).** Add Epic 7
  inside the current structure. Root-cause fixes first (7.1), then the shared
  contract (7.2, 7.3), then discovery and health (7.4), the guard prerequisite
  (7.5), mise cleanup (7.6) and generated skill blocks (7.7). Effort: medium
  overall, low for 7.1. Risk: low; every step is reversible and each component
  converts on its own schedule.
- `[N/A]` **4.2 Option 2, Rollback.** Nothing completed needs reverting.
- `[N/A]` **4.3 Option 3, PRD MVP review.** Neither PRD's MVP is affected.
- `[x]` **4.4 Selected path.** Direct Adjustment with root-cause-first ordering.
  Rejected alternatives (from the research, with corrected scores): status quo
  plus mise tasks (3/10; leaves krebs off PATH and the hermes shadow); an
  AWS-style model-driven monolith (2/10; two Belsky levels up, rewrites
  polyglot tools); a passthrough umbrella as canonical spelling (the design's
  option 4 as written, corrected to 6/10; adds a second name for every command
  and bypasses argv guards); extending pj into the umbrella (3.5/10; `pj skills`
  already proves the skew failure); mcp-hub as the only umbrella (5/10; agents
  and Candybar need a binary). Selected: usage-spec contract plus root-cause
  fixes plus a discovery-only front door (8/10).

### Section 5: Proposal components

- `[x]` 5.1 Issue summary (§1). `[x]` 5.2 Epic and artifact impact (§2).
  `[x]` 5.3 Recommended path (§3). `[x]` 5.4 MVP impact and action plan (§3,
  §4). `[x]` 5.5 Handoff plan (§5).

### Section 6: Final review and handoff

- `[x]` **6.1 Checklist complete.** Action-needed items: the Director Rule
  exception (§2.5), an optional scoped PRD (§3.1).
- `[x]` **6.2 Proposal accuracy.** Cross-checked against the research file's
  corrected verdict and the operator's decision text.
- `[x]` **6.3 Approval.** Given by the operator on 2026-11-19 (quoted above),
  before this document was written.
- `[x]` **6.4 sprint-status.yaml.** `epic-7: in-progress`, `7-1-...: in-progress`,
  7.2-7.7 `backlog`, `epic-7-retrospective: optional`.
- `[x]` **6.5 Handoff.** Grolf owns Epic 7 on the 33GOD board; tickets land in
  Backlog (Grolf's queue; nothing runs from Backlog).

## 3. Recommended approach

**Direct Adjustment: add Epic 7.** The decision, as approved:

1. **Native component binaries stay canonical** in skills, guards and Candybar:
   px, pj, skillex, candybar, flume, bb, candystore, krebs, waybill, wax.
2. **Adopt jdx's `usage` spec as the self-describe contract**
   (`<cli> --usage-spec`). Exporters exist: `@usage-spec/commander` (npm),
   `usage-spec-typer` and `argparse-usage` (PyPI), the `clap_usage` crate.
   Upgrade usage-cli 3.3.0 first. **Do not invent a `33god.cli/1` schema.**
3. **Standardise only what usage lacks:** one JSON envelope, a superset of
   skillex's `{schema, command, ok, exit, data, findings}` v2 (which skillex already
   satisfies), and one exit-code table (skillex's: 0 ok, 1 failure, 2 usage/config,
   3 refused, 4 partial, 5 lock-busy/retry, 6 drift, 130 interrupted). Convert one
   component at a time by agent call frequency. pj goes consumers-first (raw
   `pj list --json` is parsed by pilot `registry.js:61` and candystore
   `projects.py:75`). flume adds a `schema` alias before dropping `schema_version`.
4. **A small `33god` for discovery and health only:** `ls`, `where`, `versions`,
   `doctor --all`, `describe`, reading the component registry
   (`33god-platform/components/*.yaml`) and the usage specs. It may start as
   `platform.py` subcommands. **No passthrough** until every argv guard unwraps
   it (7.5).
5. **Mise keeps** `[tools]` and runtime pins, `[env]`, enter/leave hooks, per-repo
   build/test with `depends`/`watch_files`, every deploy task (including
   mobile-deploy-hub `mise run deploy`), and its role as the deployment mechanism
   on the Mac peer. Delete only pure alias tasks (body exactly `<cli> <args>`, no
   depends, env or dir) and rewrite citing docs in the same commit. Retire
   `skills:sync` (34 files) with `skillex integrations retire-mise` only after
   narrowing its over-broad matchers, which would otherwise delete Milkshake
   `skill:link`/`skill:reference`, pilot `skill:surface` and IntelliForia
   `skills:bootstrap`/`local`/`library:pull`. Fix the generators.
6. **Not now** (only when a real caller asks): a Bloodbank CLI-runner (the bus has
   a closed command vocabulary and signed actor envelopes) and an mcp-hub `cli`
   domain.
7. **Boundary rule:** if a task operates on the running platform, crosses repos,
   or must be callable from any cwd by an agent, Candybar, the bus or MCP, it is a
   CLI command. If it builds, tests, pins or bootstraps this repo, it is a mise
   task.

**Deviation from the earlier draft:** do **not** hard-pin skillex in the mise
config. features.toml F3 says track main, no pins without a reason and an exit
ticket. Instead make the installed skillex current, prune stale installs and
remove the bundled copy behind `pj skills`. Skew detection arrives with
`33god versions` (Story 7.4).

**Belsky level (pillar `belsky-doctrine`):** Jarad's agents get a CLI surface that
works from any shell; the level one up is every 33GOD component CLI: on PATH with
a pinned runtime, self-described in a standard spec, speaking one envelope and one
exit table. Not a CLI platform with its own schema or framework. Other pillars:
`agent-is-an-employee`, `it-behaves-like-it-looks`, `stay-on-the-edge`,
`reversible-beats-cautious`, `homelab-is-not-a-nasa-lab`.

**Effort:** 7.1 about a day (in progress now). 7.2-7.7 are each small to medium
and independent except for the recorded blocks. **Risk:** low. **Timeline:** no
existing epic moves.

## 4. Detailed change proposals

### Epics (`epics.md`)

```
Section: Epic List (append after Epic 6)
OLD: (no Epic 7)
NEW: ### Epic 7: 33GOD CLI Surface — one contract, native binaries
     Owner: 33god (Grolf, 33god-pm). Cross-children exception to the Director
     Rule freeze, approved 2026-11-19.
Rationale: operator-approved change; spans nine child repos.
```

```
Section: Dependency Flow (append one line)
NEW: Epic 7 is independent of Epics 1-6. Inside it: 7.1 first; 7.2 blocks 7.7;
     7.5 precedes any passthrough; 7.3 and 7.6 run per component by call frequency.
```

```
Section: new "## Epic 7" with Stories 7.1-7.7 in Given/When/Then form.
Story 7.1 carries the approved ACs verbatim (AC1-AC6).
Deferred items (Bloodbank cli-runner, mcp-hub cli domain) are recorded as not-now.
```

### Architecture

New spine `architecture/architecture-33GOD-2026-11-19-cli-surface/ARCHITECTURE-SPINE.md`:
AD-1 native names canonical, AD-2 interpreter pinning in launchers, AD-3 usage spec
as describe contract, AD-4 envelope superset, AD-5 exit table, AD-6 one skillex
without a hard pin, AD-7 discovery-only `33god`, AD-8 guards before passthrough,
AD-9 mise boundary, AD-10 projections deferred. No change to the 2026-09-23 or
2026-11-08 spines.

### PRD

None. Gap recorded (§2, 3.1).

### UI/UX

None.

### features.toml

```
Section: candidates
NEW: [candidate.cli-surface] status = "scattered", repo = "delorenj/33god-platform"
     (hypothetical home), requires = ["clock", "project.identity", "agent.hooks"],
     initiatives = ["I-9", "I-12"].
Rationale: F1 says a cross-repo capability starts as a candidate entry before any
new location or atom. No new atom: `33god` is an L4 consumer and owns none.
```

### sprint-status.yaml

```
NEW: epic-7: in-progress
     7-1-resolve-and-runtime-pin-every-component-cli: in-progress
     7-2 ... 7-7: backlog
     epic-7-retrospective: optional
```

### Story spec

`implementation-artifacts/spec-7-1-resolve-and-runtime-pin-every-component-cli.md`,
status in-progress, with an empty Dev Agent Record for the implementers' evidence.

## 5. Implementation handoff

**Scope: Moderate.** Backlog reorganisation on the 33GOD board plus developer
implementation across child repos. No fundamental replan.

| Role | Who | Responsibility |
|---|---|---|
| Owner and verdict giver | Grolf (`33god-pm`) | Owns Epic 7 on the 33GOD board. Accepts stories from Backlog to Todo, orders Todo, gives verdicts against the ACs. Decides the Director Rule exception (keep here or mirror as `I-14`). |
| Story 7.1 implementers | Interactive Claude Code session at Jarad's direction (2026-11-19) | Implement 7.1 now; post evidence on the 7.1 ticket and in the spec's Dev Agent Record. Grolf gives the verdict. |
| Child owners | pjangler, pilot, krebs, skillex, candybar, flume, bloodbank, hermes-agent-template PMs | Implement per-repo pieces of 7.2-7.7 through their own intake when Grolf delegates. |
| Operator | Jarad | Reserved actions only (client-visible sends, spending, deleting data, credential or permission changes). |

**Plane:** one epic plus seven tickets on the 33GOD board, all in Backlog, keyed
with idempotency namespace `cli-surface-2026-11-19`. 7.2 blocks 7.7. Nobody claims,
dispatches or moves them; nobody touches `agent:*` labels.

| Item | Ref |
|---|---|
| Epic 7 | 33GOD-101 |
| Story 7.1 (comment: being implemented now, Grolf gives the verdict) | 33GOD-102 |
| Story 7.2 (blocks 33GOD-108) | 33GOD-103 |
| Story 7.3 | 33GOD-104 |
| Story 7.4 | 33GOD-105 |
| Story 7.5 | 33GOD-106 |
| Story 7.6 | 33GOD-107 |
| Story 7.7 (blocked by 33GOD-103) | 33GOD-108 |

**Success criteria (epic level):**

- Every 33GOD component CLI runs by its native name from any cwd and a minimal
  PATH on the runtime it needs (7.1).
- Each component answers `--usage-spec` or ships a static `.usage.kdl` (7.2).
- Converted components emit the platform envelope and exit table (7.3).
- `33god ls|where|versions|doctor --all|describe` exist and read the registry
  plus usage specs, with no passthrough (7.4).
- Argv guards unwrap `33god` with a test per alias before any passthrough (7.5).
- `skills:sync` is gone fleet-wide, generators no longer emit it, only pure alias
  tasks were deleted, and deploy tasks remain (7.6).
- Hub command blocks are generated from usage specs and drift fails
  `skillex skill lint` (7.7).

**Decision event:** recorded with `record-decision.py` against the Epic 7 ticket
(`--basis belsky-doctrine --basis agent-is-an-employee --basis it-behaves-like-it-looks --basis stay-on-the-edge`).

## Workflow completion

- Issue addressed: 33GOD CLI surface direction (AWS contract, not monolith).
- Change scope: Moderate.
- Artifacts modified: this proposal, the new architecture spine, `epics.md`,
  `sprint-status.yaml`, the 7.1 story spec, `features.toml`.
- Routed to: Grolf (`33god-pm`); Story 7.1 implementers in the interactive session.

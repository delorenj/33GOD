# T4b — The ONE versioned Lifecycle spec (design)

> **Promoted to Krebs.** This document was written when the lifecycle machine
> lived at `momo/lifecycle/`. The machine is now owned by Krebs at
> `krebs/spec/lifecycle.v1.yaml`; historical `momo/lifecycle/...` paths below
> read as `krebs/spec/...`. Momo consumes the machine by pointer.

Status: DESIGN DRAFT (scratch). Do not apply to live repos. Grounded 2026-07-21.

## 0. Problem (grounded)

Today the ticket-lifecycle state machine is **duplicated per repo**. Every
pjangler CommonProject repo carries its own copy at
`<repo>/_bmad/custom/workflows/ticket-lifecycle/workflow.yaml` (verified live in
~30 repos: `33GOD/momo`, `33GOD/holocene`, `33GOD/candystore`, `33GOD/pjangler`,
`voxxy`, `srvls`, `LifeLaunch`, `~/docker`, `~/.config/zshyzsh`, `KeepyMoney`,
`castagram`, `drumjangler`, `sidepiece`, `CommonProject`, … plus the pjangler
template `templates/commonproject/_bmad/.../workflow.yaml` that seeds new ones).

The momo skill only **mirrors** it (`skill/references/board-clearing-loop.md`
line 14: *"State machine (mirror — canonical labels from the repo's
ticket-lifecycle workflow.yaml)"*, and SKILL.md line 66:
*"mirror of the BMAD ticket-lifecycle … Do not invent a different state
machine."*). There is no single owned artifact — the "canonical" thing is
whatever copy the current repo happens to hold, and copies drift.

This violates Pillar #3 (LEGO not statues) and #4 (the state machine is a
Strategy that should have one definition + per-repo strategy objects). T4b
promotes it to **one versioned spec inside the Momo component**, with per-repo
*label* differences pushed down into the `tp` adapter's normalized-state map
(the Strategy seam) — not copied into N machines.

## 1. What the per-repo workflow.yaml actually contains (as-built)

`33GOD/momo/_bmad/custom/workflows/ticket-lifecycle/workflow.yaml` (representative):

- `ac_rubric`: 4 booleans — `require_non_empty`, `require_testable_assertions`,
  `require_enumerated_items`, `require_fr_coverage` (all four, no short-circuit).
- `qa.max_retries`: 3.
- `staleness` (minutes): triage 10, refining 30, in_progress 120, review 15, qa 60.
- `events`: `topic_prefix: ticket`, `include_project_id`, `include_ticket_id`.
- `states`: a **label map** — the 9 semantic states → Plane column names:
  `backlog:Backlog, triage:Triage, refining:Refining, ready:Ready,
   in_progress:In Progress, review:Review, qa:QA, done:Done, blocked:Blocked`.

The **transitions + guards** are NOT in workflow.yaml — they live in prose in
`board-clearing-loop.md` (lines 25-29) and the `steps-c/`, `steps-e/`, `steps-v/`
step files. So the machine is split across three surfaces today:
config (workflow.yaml) + narrative (board-clearing-loop.md) + step scripts.

The `tp` adapter (`<role_dir>/.scripts/lib/ticket-provider.sh`, live copy at
`~/docker/agents/hermes/pm/.scripts/lib/ticket-provider.sh`, 102 lines) reasons
in a **coarser 5-state band**:
`TP_STATES="backlog unstarted started in_review completed"` (line 95:
*"Normalized states the engine reasons in. Adapters map these to provider terms."*).
`transition <id> <backlog|unstarted|started|in_review|completed>` is the only
state vocabulary the adapter accepts.

So there are already TWO altitudes, and the design keeps both — it just gives
each one ONE home:

| Altitude | What it is | Owner (after T4b) |
|---|---|---|
| 9 semantic phases + transitions + guards (the machine) | triage→ready→in_progress→review→qa→done, +backlog/blocked | the **Lifecycle spec** (new, in `momo/`) |
| 5 normalized bands (provider-portable vocabulary) | backlog / unstarted / started / in_review / completed | the **`tp` adapter** (Strategy, per repo) |

## 2. The spec: format, location, versioning

### 2.1 Location in `momo/`

```
momo/
  lifecycle/                      # NEW component-level dir (peer of skill/)
    lifecycle.v1.yaml             # THE canonical machine (SSOT)
    lifecycle.schema.json         # JSON-Schema the yaml validates against
    CHANGELOG.md                  # semver history of the spec
    README.md                     # human-facing rendering + rationale
```

Rationale for `krebs/spec/` (not `momo/skill/references/`): the spec is a
**shared contract** consumed by three carriers, so it must sit above any one of
them —
1. the **skill** (`board-clearing-loop.md` mirrors it),
2. the future **MCP proxy server** (Epic 6 — `issue_transition` verb validates
   against it),
3. the **Hermes adapter** (Epic 5 — the sentinel single-pass drives it).
Putting it under `skill/` would re-couple it to one carrier (statue risk).

### 2.2 Format — YAML machine + JSON-Schema

YAML (same family as the existing workflow.yaml, so the promotion is legible),
but promoted from a *label map* to a full **state-machine declaration**:
`spec_version`, `states[]` (each with `phase`, `tp_band`, `terminal`,
`staleness_minutes`), `transitions[]` (each with `from`, `to`, `guard`,
`on_fail`), and the tunable `guards{}` block (ac_rubric, qa, events). The
JSON-Schema (`lifecycle.schema.json`) makes "is this a valid lifecycle spec"
machine-checkable and lets the MCP server / adapters validate at load.

### 2.3 Versioning

- **Semver in the filename** (`lifecycle.v1.yaml`) AND a `spec_version: 1.0.0`
  key inside — filename tracks the major (breaking-shape) line so N versions can
  coexist during migration; the key tracks minor/patch.
- **`CHANGELOG.md`** records every change with the pillar/decision that drove it.
- Bump rules: **major** = state added/removed or a transition/guard semantics
  change (breaks consumers) → new `lifecycle.vN.yaml` file; **minor** = new
  optional guard knob or a default change; **patch** = doc/typo. A consumer
  pins the major it speaks (`spec: lifecycle.v1`).
- Wire it into the existing repo versioning workflow (`mise-versioning`) so
  `version:check` includes `krebs/spec/lifecycle.v*.yaml` `spec_version`.

### 2.4 Canonical states (the 9 phases) + their tp band

| Phase | tp_band | terminal | notes |
|---|---|---|---|
| `backlog` | backlog | no | operator's queue; a stop signal, not a work lane |
| `triage` | unstarted | no | evaluate AC against the 4-criterion rubric |
| `refining` | unstarted | no | AC repair; re-evaluate |
| `ready` | unstarted | no | AC 4/4; eligible to pull under WIP=1 |
| `in_progress` | started | no | exactly one implementer worker (WIP=1) |
| `review` | in_review | no | spec-compliance + quality gates (fresh reviewer) |
| `qa` | in_review | no | adversarial review + close gate; retryable |
| `done` | completed | **yes** | all AC pass |
| `blocked` | (retains prior band; flagged) | **yes*** | *terminal for the loop, re-openable by operator |

Three semantic phases collapse into the single `unstarted` band
(`triage`/`refining`/`ready`) and two into `in_review` (`review`/`qa`). That
collapse is deliberate: the board only needs the coarse band; Momo/Hermes track
the fine phase internally (ticket comments + evidence file + decision events),
which is why a repo can run on Plane's **default** "To Do" column (one unstarted
lane) OR on an explicit Triage/Refining/Ready three-column board and the spec is
identical. This is exactly the ambiguity `board-clearing-loop.md` lines 18-22
already call out.

### 2.5 Guards (promoted verbatim from workflow.yaml + made explicit)

- **AC sufficiency rubric** (triage→ready): `non_empty ∧ testable ∧ enumerated ∧
  fr_coverage` — all four, **no short-circuit**. Any fail → `refining`.
- **QA retries** (qa→done): `qa.max_retries` (default 3); on retry re-verify
  **only** previously-failed AC; retries exhausted → `blocked`.
- **Reviewer independence** (review/qa): reviewer ≠ implementer, always
  (non-negotiable; asserted in SKILL prime directive #4).
- **WIP=1** (ready→in_progress): at most one active implementer, shared with
  Hermes via the flock.
- **Staleness watchdog** (per state, minutes): triage 10, refining 30,
  in_progress 120, review 15, qa 60 — nothing rots silently. (No step file
  enforces this today — the spec makes it a first-class `staleness_minutes` field
  and the loop runs the sweep, per board-clearing-loop.md line 39.)
- **Explicit-Review gotcha fix**: transition to `review` MUST set the board state
  before the review gate runs (board-clearing-loop.md line 37 gotcha, promoted
  into the transition as a precondition).
- **Single blocked funnel**: ALL `→ blocked` edges route through one
  completion/summary step (gotcha fix, promoted into `on_fail: blocked`).

### 2.6 Proposed `lifecycle.v1.yaml` shape (illustrative)

```yaml
spec_version: 1.0.0
schema: ./lifecycle.schema.json
# Canonical ticket-lifecycle state machine for all pjangler CommonProject repos.
# Provider LABELS are NOT here — they live in the tp adapter's normalized-state
# map (Strategy). This file speaks only phases + the 5 tp bands.

states:
  - phase: backlog
    tp_band: backlog
    terminal: false
  - phase: triage
    tp_band: unstarted
    staleness_minutes: 10
  - phase: refining
    tp_band: unstarted
    staleness_minutes: 30
  - phase: ready
    tp_band: unstarted
  - phase: in_progress
    tp_band: started
    staleness_minutes: 120
  - phase: review
    tp_band: in_review
    staleness_minutes: 15
  - phase: qa
    tp_band: in_review
    staleness_minutes: 60
  - phase: done
    tp_band: completed
    terminal: true
  - phase: blocked
    terminal: true          # loop-terminal; operator-reopenable

transitions:
  - {from: acquired,     to: triage}
  - {from: triage,       to: ready,       guard: ac_rubric_pass}
  - {from: triage,       to: refining,    guard: ac_rubric_fail}
  - {from: refining,     to: ready,       guard: ac_rubric_pass}
  - {from: refining,     to: blocked,     guard: ac_still_insufficient}
  - {from: ready,        to: in_progress, guard: wip_slot_free}     # worker spawned
  - {from: in_progress,  to: review,      guard: worker_done, precondition: set_board_review}
  - {from: review,       to: qa,          guard: gates_pass}
  - {from: review,       to: in_progress, guard: gate_fail}         # retry
  - {from: in_progress,  to: blocked,     guard: ac_ambiguity}
  - {from: qa,           to: done,        guard: all_ac_pass}
  - {from: qa,           to: in_progress, guard: qa_fail_retries_left}
  - {from: qa,           to: blocked,     guard: qa_retries_exhausted}

guards:
  ac_rubric:
    require_non_empty: true
    require_testable_assertions: true
    require_enumerated_items: true
    require_fr_coverage: true
    short_circuit: false
  qa:
    max_retries: 3
    reverify_failed_only: true
  reviewer_independence: true       # reviewer != implementer
  wip: 1

events:                              # promoted from workflow.yaml unchanged
  topic_prefix: ticket
  include_project_id: true
  include_ticket_id: true
```

### 2.7 The per-repo `workflow.yaml` after promotion (knobs-only overlay)

The per-repo file does **not** die — it becomes a thin, spec-pinned **override**
of tunable knobs only (Decorator over the base spec), never a redefinition of
the machine:

```yaml
# <repo>/_bmad/custom/workflows/ticket-lifecycle/workflow.yaml  (post-T4b)
spec: krebs/spec/lifecycle.v1     # <- pins the canonical machine
overrides:                            # optional; empty = inherit all defaults
  staleness: { in_progress: 240 }     # e.g. a slow repo widens the WIP timeout
  qa: { max_retries: 5 }
# NO `states:` label map here anymore — labels are the tp adapter's job (§3).
```

The pjangler template
(`pjangler/templates/commonproject/_bmad/.../workflow.yaml`) is updated to emit
this thin overlay for every NEW repo, so drift can't reappear at the source.

## 3. Per-repo label diffs → the tp normalized-state map (the Strategy seam)

The spec speaks the 5 tp bands (`backlog|unstarted|started|in_review|completed`)
— never provider labels. Mapping a band to a repo's actual column name is the
**`tp` adapter's** single responsibility (`ticket-provider.sh`, `TP_STATES`, the
`transition <id> <normalized>` verb). That adapter IS the Gang-of-Four
**Strategy** object: one interface (`transition`, `list_issues` returning
`state`+`state_type`), many provider implementations (Plane/Linear via `tp`,
Trello via the bundled adapter + `.momo/config.json` lane map).

Concretely, per-repo differences resolve like this — **without touching the
spec**:

- **Plane, defaults board** (one unstarted lane called "To Do"): the three
  `unstarted`-band phases (triage/refining/ready) all live in the single
  Plane-default state whose `state_type=unstarted`. The adapter maps band
  `unstarted` → that column by `state_type`, not by name. Momo distinguishes the
  fine phase via ticket comments/evidence, per board-clearing-loop.md §state-machine.
- **Plane, ticket-lifecycle board** (Triage/Refining/Ready as three real
  columns): same band `unstarted`; the adapter still selects by `state_type`,
  and (optionally) a name hint picks the finest-grained matching column.
- **`in_review` band**: maps to whichever of Review / QA the board exposes;
  boards with only one review column collapse both phases there.
- **Trello**: the `.momo/config.json` lane map is the per-repo Strategy data —
  `scripts/momo-config.py detect|set` captures the odd lane names once, then the
  bundled adapter maps band→lane from that file (SKILL.md preflight step 2).

So "this repo calls it X, that repo calls it Y" is **data in the adapter**, never
a fork of the machine. The old `states:` label map in each workflow.yaml (the
thing that varied per repo) is **deleted** — its job moves entirely to the tp
adapter, which already reasons in the 5 bands. That deletion is the whole point
of the promotion: N label maps → 1 spec + 1 Strategy.

### 3.1 One divergence to reconcile (not blocking, but record it)

The spec's `events.topic_prefix: ticket` and the momo skill's
`record-decision.py` Bloodbank identity are different surfaces, but note the
recon finding: `record-decision.py` emits
`source=urn:33god:agent:<actor>:<slug>` while the live Bloodbank scheme on disk
is `source=hermes://agent/<agent_id>` / `producer=hermes-agent:<agent_id>`. The
Lifecycle spec does not own that reconciliation (it's a Bloodbank-identity task),
but the spec's `events` block should be documented as *"envelope identity per
Bloodbank scheme; see bloodbank-integration"* rather than re-specifying a third
form.

## 4. Consumer rewiring (what references the spec after promotion)

1. `skill/references/board-clearing-loop.md` — change lines 14-16 & 31 from
   *"the repo's ticket-lifecycle workflow.yaml … is the source of truth"* to
   *"`krebs/spec/lifecycle.v1.yaml` is the SSOT; the repo workflow.yaml only
   overrides knobs; provider labels come from the `tp` adapter."*
2. `skill/SKILL.md` line 66-69 — same repoint; keep *"Do not invent a different
   state machine"* but point it at the spec, not the per-repo file.
3. pjangler commonproject template — emit the thin knobs-only overlay (§2.7).
4. (Deferred, Epic 6) MCP `issue_transition` — validate against
   `lifecycle.schema.json`.

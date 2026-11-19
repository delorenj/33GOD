---
title: 'Self-evolving skills and the skill tree (I-13)'
created: '2026-11-19'
owner: 'skillex (SKRILL board, skillex-pm)'
dogfood: 'the-factory (33god-hub sub-skill hub) and factory-maintenance'
---

# Self-evolving skills and the skill tree

Jarad declared a new skill archetype on 2026-11-19, the **Self-Evolving Skill**, and asked whether the whole
skill ecosystem can become one balanced tree that agents enter through a single root. This brief states the
archetype, the tree, its operations and invariants, the feasibility evidence from today's 134 global skills,
and what is delegated to Skillex. The first adopter is already live: `the-factory` (a hub under `33god-hub`)
and its child `factory-maintenance`, which the nightly factory-forge agent follows and feeds.

## 1. The archetype: Self-Evolving Skill

A skill is self-evolving when **every task routed through it leaves the skill better for the next run of the
same task**, and the skill keeps its own size in balance.

| Rule | What it means in practice |
|---|---|
| Feed back | Before a task linked to the skill finishes, the agent folds what it learned into the skill: it fixes the step that misled it, adds an "ask the system" row, or adds one dated lesson line. Rewrite what is now wrong; never append a diary. |
| Optimise for the next run | A lesson is written where it bites (the step, the gotcha, the command), short, dated and sourced (`(2026-11-19, hook-hub run)`), so the next agent spends fewer turns. |
| Budget | Each node declares `metadata.budget_lines`. A node over budget must split; a child under a third of its budget merges back. |
| Validity | The tree stays routable after every edit: every relative link resolves, no nested `SKILL.md` (sub-skills are `SUBSKILL.md`, ADR-0002), every child has a route row in its parent, frontmatter has `name` and `description`. |
| Lands with the work | The lesson commits with (or right after) the change that taught it, through the owner's normal gates. |

Frontmatter (additive; unknown keys are ignored by today's harnesses and lint clean in `skillex skill lint`):

```yaml
metadata:
  archetype: self-evolving
  parent: 33god-hub        # the one route in
  budget_lines: 150
```

**Live adopter (33GOD `c73260a`).** `33god-platform/skills/33god-hub/subskills/the-factory/` (hub) with
`subskills/factory-maintenance/` (leaf: the forge procedure, the operator runbook and dated lessons from the
first two real runs). The forge agent may now write that subtree as well as its asset directory;
`factory_forge.py skill` lints it (the validity rules above plus `budget_lines`), and `factory-forge.sh` lands
the lessons in their own commit on a pass *or* a fail, or rejects them (kept in the run dir) when they break
the tree. Tests: `SkillTest` in `33god-platform/tests/test_factory_forge.py`.

## 2. The tree

- **Skill === Node.** `type = numChildren > 0 ? HubSkill : Skill`.
- **One parent, one route.** Every node has exactly one parent; the root has none. A skill reachable two ways is
  a bug (it means two siblings overlap).
- **Non-overlapping siblings.** Sibling descriptions must be disjoint enough that an agent reading only the
  parent's route table picks one child without hesitation.
- **A hub is a router** (ADR-0002 hub standard): what it is, rules on every route, ask-the-system table, one route
  row per child, out-of-scope, gotchas. Target under 200 lines.
- **Ownership still holds** (ADR-0002): a repo-owned hub's subtree moves as a unit and stays in its repo. New
  internal nodes that no repo owns are wild hubs in `all-skills/`, owned by Skillex.

### Red-black, or B-tree?

The instinct is right, and the precise name is a **B-tree**. A red-black tree is the binary encoding of a 2-3-4
tree (a B-tree of order 4): its rotations and recolourings *are* the B-tree's split, merge and borrow-from-sibling
seen through a binary lens. Skills are n-ary and have no total order, so the tree should be implemented in its
B-tree form directly. That is also why split and merge felt like an "extra function not common in a red-black
tree": they are the B-tree's native operations.

| B-tree | Skill tree |
|---|---|
| Key order | Semantic fit: the child whose description best matches the skill or task (embedding similarity over descriptions, LLM adjudication only when the top two are close) |
| Node capacity (order m) | Fan-out bounds per hub, `min..max` children (proposal below), plus the node's `budget_lines` |
| Search | Route: from the root, pick the best-fitting child until a leaf |
| Insert | `addSkill`: route the new skill's description down; attach where no child fits better than the hub itself |
| Split (overflow) | A hub over `max` children, or a node over `budget_lines`: cluster into two or more children under new hubs |
| Merge / borrow (underflow) | A hub under `min` children: borrow from a sibling or merge into it; a lone child is hoisted ("rotation") |
| Height bound | Depth bound (root to leaf at most 4 hops) |

### Operations (proposed `skillex tree` verbs)

| Verb | Does | Notes |
|---|---|---|
| `tree show [--json\|--html]` | The tree with per-node size, fan-out, depth, health | Extends `skillex graph` (which already maps hubs, sub-skills and lint) |
| `tree route "<task>"` | The path an agent would take for a task | The test harness for routing accuracy, and the runtime for single-root traversal |
| `tree add <skill> [--dry-run]` | Places a new skill: route its description from the root, attach, then rebalance locally | **Dogfood:** `the-factory` must place under `33god-hub`, `factory-maintenance` under `the-factory` |
| `tree balance [--dry-run]` | Walks the tree; for each hub out of bounds proposes split / merge / borrow / hoist; for overlapping siblings proposes a merge; for oversize nodes proposes a split | Mechanical moves apply directly; content splits are proposals an agent authors |
| `tree split <node>` / `tree merge <a> <b>` | Moves files, rewrites route rows and relative links, keeps lint clean | |
| `skill lint` (extended) | Adds `budget_lines`, parent route, `archetype` checks for SUBSKILL nodes at any depth | Today's lint already passes nested sub-skills |

### Activation

The end state lists **one** root skill (`skills`) in every harness; everything else is reached by traversal
(sub-skills are already never auto-listed). Transitional mode lists the root's children (about a dozen hubs),
which keeps auto-triggering strong while the router descriptions are tuned. Skillex already controls what is
linked into `~/.agents/skills`, `~/.claude/skills` and the Hermes profiles, so activation is a selection
change, not a harness change. Harness built-ins and plugin skills are outside the tree.

## 3. Feasibility from today's global skills

**Yes, as a B-tree.** Three candidate trees were built from the 134 skills in today's global selection
(ownership-first, task-first, and a refined final tree). Each was traced on 20 real prompts and judged. The full
candidate, with every node, its description and the traces, is in
[`skill-tree-candidate.json`](skill-tree-candidate.json).

| Measure | Result |
|---|---|
| Coverage | All 134 skills appear exactly once, plus `the-factory` and `factory-maintenance` under `33god-hub` (no missing skills, no duplicates) |
| Shape | 165 nodes: the root, 3 existing hubs (`33god-hub`, `the-factory`, `heyma`), 23 new hubs and 138 leaves. Fan-out is 3–12 and depth is at most 4 |
| Routing, 20 test prompts | Final tree: 20/20 with no wrong turns. Ownership-first: 15/20 (it won the composite score, 74.5/100). Task-first: 17/20 (71/100, but it splits repo-owned subtrees and needs 32 new hubs) |
| Routing, 12 held-out prompts | 11/12 |
| Cost per lookup | 2.7 router reads on average (1–3 hops). A binary tree (red-black) would need about 8 |
| Context saved | One root description of about 1,000 characters replaces the flat listing of about 55,500 characters in every session |

**Top level (root `skills`, 10 branches):** `33god-hub` (12), `delonet` (6), `bmad` (7),
`engineering-practice` (9), `repo-toolchain` (5), `agent-tools` (8), `writing` (4), `design` (7),
`vendor-apis` (11) and `personal-and-business` (5).

**The 23 new hubs:**

| Parent | New hubs |
|---|---|
| Under the root | delonet, bmad, engineering-practice, repo-toolchain, agent-tools, writing, design, vendor-apis, personal-and-business |
| Under `33god-hub` | bloodbank, pjangler, skillex, orchestration, observability, memory-and-routing, voice |
| Under `bmad` | bmad-core, bmad-personas, bmad-planning, bmad-delivery, bmad-creative-suite, bmad-builder |
| Under `engineering-practice` | code-review |

**Lessons from the wrong turns.** Every miss in the first two trees was lexical, so description changes fixed
them all; no structural change was needed. The root description must name the high-value intents outright:
"did my hook fire" (Waybill), "client updates", "ring me when someone texts", "mobile releases", "pitch decks" and
"paying a provider". Each sibling also needs a "Not here" pointer to its nearest neighbour.

**Blockers, in the order they bite:**

1. **Activation.** Only the root can be listed. Generated routers must be `SUBSKILL.md` files, or Hermes' rglob
   lists them. A pinned set stays listed during the transition because CLAUDE.md and other skills load these by
   name: `belsky-doctrine`, `artifacts`, `kapture`, `candybar`, `web-search` and `pillars`.
2. ~~**`mobile-devex` is missing from the global selection.**~~ Resolved 2026-11-19 (`~/.agents` `4a97532`; all
   46 strict Hermes desks resynced). Without it, the mobile-release route ended at `mise-versioning`, a hand
   version bump that CLAUDE.md forbids.
3. **`33god-hub` is full.** It reached the maximum of 12 children with the Factory insert, so the next `addSkill`
   overflows it. The planned rotation is an `operator-desktop` hub (Atlas G10) holding `crank`,
   `zellij-workspace-ops` and `33god-features`, which brings `33god-hub` back to 10.
4. **BMAD and Stripe merges are blocked upstream.** Their overlaps are handled by hub routers, not by merging
   the skills.

**Split candidates the balancer would raise first:**

- `agent-fleet-operations`, split inside flume's own repo hub;
- `pilot`, split per adapter;
- `humanizer`, by moving its pattern catalog into `references/`;
- `project-lifecycle`, split, or merged into `krebs`;
- `delonet-daily-report`.

Ownership fixes a skill's parent first. Balancing never moves a repo-owned subtree out of its repo.

## 4. Delegation

Owner: **Skillex** (`skillex-pm`, SKRILL board). The parent (33GOD) holds this brief and the dogfood; Skillex owns
the archetype's canonical doc (`docs/skills/`), the `tree` verbs, lint and activation. See I-13 in
`initiatives.md` and SKRILL-49.

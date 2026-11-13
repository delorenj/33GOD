# Owner dependency graph and exact catalog proposal

Derived planning companion; no owner backlog/ticket is created. `P-n` below are
local contract-map row identifiers, not stories, Plane refs or copied statuses.
Every row has one accountable owner; contributors do not become second writers.

## Nodes and typed edges

| Node | One accountable owner | Bounded result / existing reference |
| --- | --- | --- |
| P1 | 33GOD parent planning owner | Intake-authority disposition and catalog delta proposal, not a new board/actor; I-9 |
| P2 | Hermes Fleet | One native `agent.message` contract and G1/G2/G3 runnable-validation manifest, or precise unsupported outcome; no matching owner ticket established |
| P3 | ASM | Canonical identity/session/incarnation/freshness contract; use BB-33's Bloodbank current provider and PJAN-202 knowledge, not duplicate detection |
| P4 | Terminal-driver | Topology/location contract with provisional PJAN-202, no agent classification/new send stack; existing I-9 split delegation |
| P5 | Crank | Opt-in/final admission/attempt/uncertainty contract adopting P2/P3/P4; existing I-8 registry/engine delegation |
| P6 | PJangler | Existing `pj crank tui`/CLI selection and result projection through P5, not direct registry mutation; I-8/PJAN-202 |
| P7 | Crank | Integrated FR-6 scenario/evidence procedure linking owner results, not rewriting native gate verdicts |
| B32 | Bloodbank | Existing BB-32 isolated real Redis/key/channel test outcome |
| B33 | Bloodbank | Existing BB-33 current ASM identity/session repair, separate from ASM target contract/extraction |

**Planning/adoption edges** (dependency → dependent):

- P1 → P2, **adoption-authority edge**: the coordination designation prerequisite
  is now satisfied by delegated disposition; the single supported planning request
  is published. P2 owner adoption/refinement remains pending its actual response.
  Satisfying authority and publishing do not themselves accept the local proposal.
- P2, P3, P4 → P5 contract convergence; P5 → P6 and P7. Drafting can proceed
  independently with explicit missing prerequisites; nobody claims implementation
  ready merely because its proposal exists.
- B32 → B33 is an actual read-back blocking relation. B33 → P3's verified
  provisional-provider readiness. No blanket full ASM extraction prerequisite is
  added merely to refine P2.

**Enablement/proof edges:** verified B32 isolation and B33/ASM identity where used,
P4 pane association, P5 uninterrupted submit authority and incarnation-scoped
unknown fencing, plus P2 G1+G2+G3 PASS → authorization-qualified execution of P7.
P6 proves the UI part independently; it cannot certify a native gate. Full I-8
migration/restart/cap lift remains separate. No edge allows automatic execution.

This edge list is the explicit acyclic graph; it intentionally avoids generating
parent component epics/stories or a redundant visual/status tracker.

## Precise unapplied catalog delta

Inspected `33GOD/features.toml` on 2026-11-08:

- `agent.job` already uses owner key `hermes-agent`; the Fleet domain's existing
  catalog spelling is therefore reused, not a second `hermes-fleet` identity.
- `agent.session` remains ASM; `pane.input` remains terminal-driver.
- Crank currently requires `pane.input` and lacks `agent.message`.

Proposed delta only (raw catalog remains unchanged):

```diff
 [atoms]
+"agent.message"   = { owner = "hermes-agent", state = "approved", note = "Hermes Fleet narrow native-message Adapter planning owner; pane-bound local-Linux Claude candidate only; no API/certified support; no terminal fallback" }

 [feature.crank]
-requires = ["agent.state", "agent.session", "pane.topology", "pane.input", "project.identity", "agent.job", "clock"]
+requires = ["agent.state", "agent.session", "pane.topology", "agent.message", "project.identity", "agent.job", "clock"]
```

`approved` records accepted planning ownership, not `owned`/deployed. No `interface`
or provisional API is invented. Preserve the existing `pane.input` atom and
terminal-driver owner for terminal actions elsewhere. Do not change crank's
`status = "scattered"`, current homes or `today` references as if migration had
happened. This targets the selected first-proof dependency, not a waiver of full
I-8 work or a rewrite of historical current homes.

Before future application, parent planning owner reviews this exact diff and
verifies the actual enrolled Fleet owner route. The mapping `hermes-agent` = Fleet
is supported by existing `agent.job` spelling and platform ownership context, not
proof that a PM named `hermes-agent` exists. The catalog key must not be used as a
dispatch address. Applying catalog changes is not authorized by this proposal.

## Reuse and no duplication

I-8/I-9 remain authoritative parent outcomes; BB-32/BB-33 retain their Bloodbank
work and ordering; PJAN-202 remains completed provisional read-only discovery.
CAND-52 historical runner restoration is not reopened. Owning PM searches its
board before introducing missing work; absence in the inspected FLUME list does
not establish absence on every board. Owner work/status returns are links, not
editable copies in this package. No feature promotion/repository/clock is added.

# Momo improvement triage — feedback from tech team

## Source
Direct operator feedback summarizing a black-box read of Momo's recent lifecycle run (Trello card, Aug 7–9). The feedback validates the verification posture but identifies six waste/control issues.

## Classification
- **Domain:** PM-orchestrator tooling / 33GOD platform
- **Type:** Meta-improvement (hardens Momo itself)
- **Cross-component:** Yes — touches agent runtime, board adapters, evidence scripts, and possibly Bloodbank event contracts
- **Second occurrence:** Yes — these patterns recurred during the session, so Rule of Three applies (#3)
- **LoE:** Medium–Large (2–3 person-days, can be split into independent subtasks)

## Plane tickets created
- Epic: **33GPM-2** Harden Momo lifecycle against worker/reporter waste
- 33GPM-3 Structured worker hand-back with heartbeat and retry policy
- 33GPM-4 Automate evidence capture (baselines + mutation checks)
- 33GPM-5 Reporting discipline and deduplication
- 33GPM-6 Stable findings ledger
- 33GPM-7 Gated lane transitions
- 33GPM-8 Lock working tree against background auto-commits during active sessions

## Decomposed subtasks (from 33GPM-3 to 33GPM-8)

### 33GPM-3 — Structured worker hand-back with heartbeat and retry policy
Make delegation reliable. Before a worker counts as done it must write a hand-back bundle to disk (diff, test log, evidence file). Add a heartbeat/timeout policy and retries so silent worker death is an incident, not per-occasion improvisation.

### 33GPM-4 — Automate evidence capture (baselines + mutation checks)
Turn mutation checks and baseline-vs-branch test counts into script/CI artifacts that Momo links, instead of suites Momo re-runs and narrates.

### 33GPM-5 — Reporting discipline and deduplication
One comment per event; each comment contains delta + current state + asks only; post-mortems go to the decision trail with a link; add a dedupe guard on the reporter.

### 33GPM-6 — Stable findings ledger
Replace findings-as-prose with a stable checklist or single edited table with IDs, persisted per issue.

### 33GPM-7 — Gated lane transitions
Encode lane transitions as precondition checks, not later audit repairs. Moving to "Awaiting approval" / "Done" requires passing the close gate.

### 33GPM-8 — Lock working tree against background auto-commits during active sessions
Prevent unowned background writes to the working tree while a Momo session is active.

## Dependencies
- 33GPM-4 depends on 33GPM-3 for the hand-back bundle shape.
- 33GPM-5 and 33GPM-6 depend on 33GPM-3/33GPM-4 for artifact shapes.
- 33GPM-7 can be worked in parallel with 33GPM-5/33GPM-6 once 33GPM-3/4 are stable.
- 33GPM-8 is independent of the others.

## Implementation delegation
Delegated to **33god-dev** (delegation id `deleg_622c1281`). The dev agent is instructed to read the Momo skill references, implement the six tickets in dependency order, fix the PROJ/33GPM identifier drift in `.project.json` and `role.yaml`, and return evidence.

## Config drift noted
`.project.json` and `role.yaml` list the Plane project identifier as `PROJ`, but the live Plane identifier is `33GPM`. The dev agent will correct this as part of the work so the `tp` adapter resolves the right board.

# Architecture Spine Review — Rubric Walker

## Verdict

Good brownfield feature spine with accurate ownership and deployment boundaries,
but not yet ready for parallel implementation. The spine names the major
divergence points and honestly carries the unresolved Flume, freshness, and
command-catalog decisions. It needs one shared DeloHQ contract registry and
shared state mappings before independently built Company, Inbox, and command
units can be expected to converge.

## Findings

### High

- **Shared browser contract is implied, not fixed.** AD-3 and AD-11 require
  versioned typed envelopes and contract tests, but they do not name the one
  committed package or registry that defines the Company, Now, Inbox, Office,
  Action, Receipt, error, and freshness shapes. Two adapters could each claim
  schema version 1 while using different fields or state vocabularies. **Fix:**
  add a shared `@holocene/delohq-contracts` seam with one versioned model and
  state vocabulary; every API adapter and route imports it.

### Medium

- **Receipt normalization is still underspecified.** AD-7 lists DeloHQ terminal
  states but does not define the mapping from Hermes, Krebs/Pilot, or future
  Flume outcomes into that vocabulary. **Fix:** make the shared contract own a
  canonical receipt-state mapping and require every command adapter to publish
  the source state alongside the normalized DeloHQ state.
- **Toolchain reality has one pre-handoff mismatch.** `holocene/package.json`
  declares pnpm 10.0.0, but the current host's `pnpm` invocation resolves a
  cached 11.5.0 shim and fails under Node 26.5 before reporting a version.
  **Fix:** resolve the host/deployment toolchain before implementation claims
  the documented pnpm stack is executable; record the chosen runtime path in
  the platform handoff.

## Dimension judgments

- **Divergence coverage — adequate:** AD-1 through AD-10 cover authority,
  hosting, reads, identity, commands, auth, freshness, and operations; shared
  model ownership needs tightening.
- **Rule enforceability — adequate:** Rules are concrete and mostly testable;
  the browser contract and receipt normalization remain too distributed.
- **Brownfield fit — strong:** The spine correctly treats `/hq`, the host API,
  `org.yaml`, current path-pinned actions, and split deployment as transitional
  reality rather than completed design.
- **Technology reality — adequate:** Versions and paths are confirmed against
  current source and service state, with the pnpm/Node mismatch recorded.
- **Capability coverage — strong:** The PRD FRs and UJs map to architecture
  areas without adding a second product surface.
- **Operational envelope — adequate:** Deployment, auth, source failure, and
  receipt degradation are covered; toolchain convergence remains an external
  gate.
- **Deferred discipline — strong:** Numeric budgets, Flume transport, action
  catalog, UI migration, memory policy, and independent deployment are named
  rather than silently invented.

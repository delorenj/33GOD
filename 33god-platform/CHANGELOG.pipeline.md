# 33GOD Pipeline Changelog

This changelog records changes that affect more than one 33GOD component. It is
fed by `changes/*.jsonl`; update both when a contract shifts.

## 2026-08-10

### Trunk Checkpoint

- Folded every piece of in-flight work to `main` across the family and advanced
  all nine submodule pins to their `origin/main` tips — the first checkpoint
  where that has been true simultaneously.
- Pruned six worktrees. Four held branches already contained in `origin/main`;
  two more (`feature/PJAN-19-hermes-bloodbank-gateway`,
  `codex/reporting-contracts`) looked like thousands of lines of unmerged work
  but were stale pre-rebase duplicates. Content comparison, not commit count,
  is the test: the gateway branch was byte-poorer than `main` and missing
  `execution_state.py`, and merging the contracts branch would have deleted the
  `curator` domain, the `skill` entity, and five schemas `main` already had.
- Recorded FR14 (trunk discipline) so this state is a gate, not an accident.

### Skill Ownership Relocation

- Moved skill sources of truth out of root `skills/` and into the components
  whose contracts they describe: Bloodbank owns event-integration skills,
  PJangler owns provisioning and mise skills, Krebs owns lifecycle and triage
  skills, and `33god-platform/` owns cross-cutting skills.
- Root `skills/` is now a link farm with no divergent copies.
- Split Skillex pack provisioning from skill fan-out in `mise.toml` so packs
  declared in `.agents/skills.json` resolve before sync runs.

### Registry Expansion

- Registered Momo (PM/EM orchestration agent) and Toad (project custodian
  agent), bringing the active component list to thirteen.
- Required every component to declare a runtime mode, so non-service components
  state an execution model rather than carrying an empty compose block.

### Lifecycle Authority

- Declared Krebs the single ticket-lifecycle authority (PRD FR12). One machine,
  five normalized `tp` bands, per-repo variation limited to label maps.
- Opened `momo-lifecycle-duplicate-v1`: `momo/lifecycle/` still carries the
  pre-promotion copy and both its spec and schema have drifted from
  `krebs/spec/`, while Momo's own agent spec already points at Krebs.

## 2026-07-15

### Root Compose Cutover

- Published Holocene `edaf31b`, pinned all four component gitlinks, and added
  formal Holocene and PJangler submodule mappings at the monorepo root.
- Replaced the three component-owned Compose lifecycles with the root project.
  Bloodbank core, one Candystore triplet, and Holocene web are live under
  `33god-platform`; PJangler remains clean, pinned, and run-only.
- Adopted the Holocene `/hq` plus `/_next/static` routing contract and removed
  the excluded legacy Bloodbank PostgreSQL container.

### Integrated Compose Target

- Replaced the readiness scaffold with a root-owned normalized projection for
  Bloodbank NATS/init/placement, one standalone Candystore triplet, Holocene
  host-API preflight and web, and opt-in run-only PJangler CLI/MCP tools.
- Preserved ports, three external network identities, and five adopted external
  volume identities; excluded Bloodbank's legacy Candystore services and kept
  detached legacy volumes outside the target.
- Added a semantic validator and focused tests for default, `tools`, `full`,
  and render-only unsupported `cloud` models.
- Extended the documentation drift gate to validate the candidate against an
  explicit source root. Cloud deployment remains blocked.
- Hardened every checked-in render task with `--no-env-resolution`, preserved
  caller-selected port overrides for validation, and suppressed captured
  Compose errors that could otherwise disclose component env-file values.
- Expanded semantic/adversarial gates for the canonical Candystore subscription
  and daprd placement path, exact Traefik Host/auth/proxy behavior, and exact
  per-service network isolation. The committed Holocene `/hq` router and its
  `/_next/static` asset path are the pinned baseline.

### Registry Truth Reconciliation

- Corrected PJangler, Hermes Fleet, and HeyMa paths to their live checkouts and
  restored PJangler's canonical npm health command.
- Removed Holyfields and Hookd from the active component list because neither
  repository is present in the current platform checkout. Their manifest files
  remain as historical definitions until those components are deliberately
  restored.
- Re-established the platform manifest validator as a live-truth gate.

## 2026-07-10

### Component Registry Repair

- Restored the Candybar, Holyfields, and Hookd component manifests referenced by
  `components.yaml`.
- Removed the incomplete Flume manifest from the active registry until the repo
  path and platform contract are real.
- Re-established `platform:validate` and `platform:components` as usable
  control-plane gates for the next director handoff.

## 2026-07-08

### Platform Control Plane Bootstrap

- Added the `33god-platform` control-plane scaffold.
- Indexed the current component constellation: Bloodbank, Candystore, Holocene,
  PJangler, Hermes Fleet, Skillex, Hindsight, Pipeline MCP Hub, Candybar, HeyMa,
  Holyfields, and Hookd.
- Established the first machine-readable change entry and read-only backfill
  checks for canonical Hindsight/Bloodbank hook migrations.
- Added a unified `33god-hub` skill entrypoint so agents start from one product
  map before drilling into component-specific skills.

Backfill checks introduced:

- `hindsight-canonical-hooks-v1`
- `bloodbank-canonical-agent-publisher-v1`
- `hermes-inherited-profile-config-v1`
- `skillex-33god-hub-v1`

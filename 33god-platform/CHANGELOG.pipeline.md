# 33GOD Pipeline Changelog

This changelog records changes that affect more than one 33GOD component. It is
fed by `changes/*.jsonl`; update both when a contract shifts.

## 2026-07-15

### Integrated Compose Target

- Replaced the readiness scaffold with a root-owned normalized projection for
  Bloodbank NATS/init/placement, one standalone Candystore triplet, Holocene
  host-API preflight and web, and opt-in run-only PJangler CLI/MCP tools.
- Preserved ports, three external network identities, and five adopted external
  volume identities; excluded Bloodbank's legacy Candystore services and kept
  detached legacy volumes outside the target.
- Added a semantic validator and focused tests for default, `tools`, `full`,
  and render-only unsupported `cloud` models. This validates a target only; no
  services or existing component projects were changed.
- Extended the documentation drift gate to validate the candidate against an
  explicit source root. Cloud deployment remains blocked.

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

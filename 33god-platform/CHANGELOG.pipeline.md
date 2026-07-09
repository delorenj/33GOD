# 33GOD Pipeline Changelog

This changelog records changes that affect more than one 33GOD component. It is
fed by `changes/*.jsonl`; update both when a contract shifts.

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

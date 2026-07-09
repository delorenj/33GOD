# 33GOD Platform Control Plane

This directory is the product control plane for the 33GOD development
environment. It does not replace the existing component repos. It indexes them,
describes their contracts, validates their local presence, records pipeline-wide
changes, and gives agents one hub to start from.

## First slice

```bash
python3 scripts/platform.py validate
python3 scripts/platform.py components list
python3 scripts/platform.py backfills check
```

The first slice is intentionally local-first and read-only:

- `components.yaml` and `components/*.yaml` describe the platform.
- `changes/*.jsonl` records cross-component changes in machine-readable form.
- `CHANGELOG.pipeline.md` is the human-readable ecosystem changelog.
- `backfills/*.yaml` describes legacy migration checks.
- `skills/33god-hub/` is the unified skill entrypoint.
- `compose.yaml` captures the product compose target and profile names while
  component compose files are normalized.

## Ownership rule

Each component keeps owning its implementation. This control plane owns the
relationships between components: what changes affect whom, what must be
backfilled, and what a local or hosted 33GOD environment should bring up.

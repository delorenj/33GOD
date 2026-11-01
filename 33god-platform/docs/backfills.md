# Backfill Program

Backfills are idempotent migrations that bring old repos, host configs, or agent
runtime projections up to current 33GOD contracts.

The first implementation is read-only:

```bash
python3 scripts/platform.py backfills check
```

Backfill manifests live under `backfills/`. Each one declares search paths,
forbidden patterns, and remediation notes. An opt-in bounded contract check can
also declare `external_root`, `required_contents` (exact named files and literal
substrings), and `required_symlinks` (exact membership link targets). If the
external root is unavailable, the runner reports `NOT VERIFIED` and exits nonzero,
not `OK`. Neither mode writes files, runs generators, or certifies runtime
activation. A later slice can add `backfills apply <id>` once each remediation
has been made reversible and safe.

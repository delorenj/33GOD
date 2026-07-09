# Backfill Program

Backfills are idempotent migrations that bring old repos, host configs, or agent
runtime projections up to current 33GOD contracts.

The first implementation is read-only:

```bash
python3 scripts/platform.py backfills check
```

Backfill manifests live under `backfills/`. Each one declares search paths,
forbidden patterns, and remediation notes. A later slice can add
`backfills apply <id>` once each remediation has been made reversible and safe.

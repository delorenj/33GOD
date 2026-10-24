# candystore-src provenance

Vendored copy of the `candystore` git submodule of the 33GOD monorepo.

- Submodule commit: `767ebb5eb8351b43b43bb6406aa1882ef3912713`
- Submodule status at vendor time: clean working tree (`git status --porcelain` empty)
- What was copied: `candystore/` (package), `migrations/`, `static/`,
  `pyproject.toml`, `Dockerfile` — with `__pycache__/` and `*.pyc` excluded.
- **`tests/` is deliberately NOT vendored.** Its fixture corpus
  (`tests/fixtures/envelopes.jsonl`, ~650 envelopes) is a capture of real
  production traffic: client project names and report bodies (including
  client-facing activity reports with addresses/invoice amounts), personal
  home-dir paths, and internal workspace names. Shipping it would violate
  the charter's secrets-never-travel and no-personal-data rules (found by
  the bundle's own secrets scan on first run — scan, don't assume). The
  upstream suite still runs against the live submodule for the PM review
  gate; this bundle proves candystore via its live behavior (ingest,
  dedupe, readback) in smoke/smoke.sh.
- Nothing else from the submodule is included (no compose files, no
  dapr-components, no agent notebooks, no docs trees, no `runtime/`, no
  `web/`, no images).
- Local modification: **NONE.** The PM crib-fidelity diff (`git archive
  767ebb5` vs this tree) shows all five copied artifacts byte-identical,
  Dockerfile included (upstream base `python:3.11-slim`, which is multi-arch —
  manifest-verified). Do not invent deltas that the evidence does not show.

G1 builds candystore from the live submodule; G7 vendors it so the bundle is
self-contained on a target host with no monorepo checkout. To re-vendor:

```sh
rsync -a --exclude='__pycache__' --exclude='*.pyc' \
  /path/to/monorepo/candystore/{candystore,migrations,static,tests,pyproject.toml,Dockerfile} ./
git -C /path/to/monorepo/candystore rev-parse HEAD   # update this file
```

Crib-fidelity check (PM review gate): `diff -r` the vendored tree against the
submodule at the pinned commit, expecting only the Dockerfile build-arg change
and no `__pycache__` differences.

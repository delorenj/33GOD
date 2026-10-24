---
title: Aperture G5 honest project-tooling artifacts
type: chore
created: 2026-10-24
status: in-review
route: oneshot
---

<frozen-after-approval>

## Intent

Package the existing project tooling as run-only tool images; no daemons.
PJangler and Skillex are executable CLIs, CommonProject is a read-only Copier
template mount, and Skillex's one present MCP server is a stdio tool image.
No service graph or Compose wrapper is appropriate. Preserve all source repos
and prove builds, CLI execution, base manifests, no ports, and clean packaging
on this host. Push the worker branch for independent PM review, not merge.

</frozen-after-approval>

## Implementation Notes

- Additive, group-local packaging only; no production activation or source edits.
- Investigation: the supplied Python PJangler assumption is stale. The available
  PJangler repo is the monorepo child, not a sibling checkout; it has no Python
  packaging metadata. Its package is `@delorenj/pjangler` 1.5.18, Node >=24.
  Skillex is `@delorenj/skillex` 0.3.1, also Node >=24. Use Node 24 rather than
  knowingly ship broken Python/Node-20 images. Python 3.12 + uv belongs to MCP.
- Exactly one directory exists under Skillex `mcp-servers/`:
  `codegraph-voyage-mcp`, whose script is
  `codegraph_voyage_mcp.server:main`. It supports `--help` and stdio.
- CommonProject is not vendored here. Document and exercise its read-only mount;
  the smoke must not execute template tasks or change any source checkout.
- BuildKit Bake declares amd64 and arm64; native smoke explicitly overrides to
  the host platform for `--load`. Manifest presence is not arm64 runtime proof.
- Existing G1/G4 establish GOD_* overrides, explicit scope and trimmed proof.
  Root charter, source component contracts and the supplied architecture rule
  govern this artifact group. No fake network listener will be introduced.
- Verification: render Bake, build all three images, execute both CLI helps,
  MCP help and protocol initialization; inspect users and exposed ports; mount
  CommonProject read-only; inspect both external immutable base manifests; scan
  group files and compare source git status before/after. Arm64 native execution,
  publication, and the broader G5 real-project/bus gate remain explicit deferrals.
- All three images passed a no-cache native build; complete smoke passed exit 0.
  Actual MCP SDK uses newline-delimited JSON-RPC; initialize/list/EOF all passed.
  Existing MCP tests passed 9/9 against the image-installed package with source
  tests mounted read-only. Source Git statuses stayed byte-identical.
- MCP copies Python module source only, excluding pre-existing host bytecode and
  egg-info. Source template tasks and full Node test suites were not executed.
- Independent review cannot be launched from this worker runtime; REVIEW.md
  hands the designated PM the full bounded review. No self-approval or merge.


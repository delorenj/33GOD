# PJangler Development Guide

## Prerequisites

- Node.js 24+
- npm
- Copier 9+ for templates
- mise for local tool/runtime coordination
- Optional provider CLIs and user systemd for live provisioning

## Canonical Commands

```bash
cd pjangler
npm install
npm run build
npm run typecheck
npm test
npm start
npm run mcp
```

The build bundles CLI and MCP entrypoints with esbuild. `npm test` runs `scripts/run-tests.mjs`, which typechecks as a hard gate, rebuilds, then attempts all sixty-one suites — esbuild never typechecks, so suites run against un-typechecked source report fiction.

## Safe Operation

Prefer project-init dry runs, migration dry runs, and local modes. Inspect each MCP tool’s defaults: `run_recipe` executes by default. Do not assume all MCP calls are non-mutating.

## Registry and Projection Changes

Treat `~/.config/pjangler/projects.yaml` as catalog/bootstrap authority and `.project.json` as the repository-local runtime projection. Add regression coverage for central/local disagreement and concurrent registry updates when changing either model.

## Template Changes

`templates/commonproject` is the only submodule. Copier uses `--trust`; template tasks are executable host code. Pin template provenance, eliminate dirty gitlink dependence, and review remote installers, provider wiring, and secret handling. The agent template and its host-service provisioning are Flume's. Update platform change logs and define a regeneration/backfill plan for every material template contract change.

For `.gitignore`, preserve existing repo rules and add only the portable
project contract. Never copy or hard-code `core.excludesFile`, and never add
negations that make `.claude/`, `.codex/`, or another generated client root
canonical. A structural migration may delete exact lines PJangler previously
generated; it must not call `git rm --cached`. Route index reconciliation to
`gitignore-maintenance` and cover both an isolated global-ignore fixture and a
tracked-path-preservation regression.

## Tests

The Node regression scripts create/remove temporary filesystem state. Run them only in a writable test environment. Existing coverage includes parity migration, MCP catalog/server flows, project initialization, registry conflicts, agent preservation, and ticket projections.

Add focused tests for prompt cancellation, ingredient failure propagation, MCP concurrent output capture, template shell scripts, and security boundaries.

## Known Self-Parity Drift

PJangler’s root mise hook syntax is older than its generated template, and `.mise/scripts/setup-plane.py` can recreate `.plane.json`. Repair sources before regenerating downstream projects.

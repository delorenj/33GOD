# PJangler Development Guide

## Prerequisites

- Node.js 20+
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

The build bundles CLI and MCP entrypoints with esbuild. The package reports 1.2.18, while the root lock metadata reports 1.2.10; resolve that before publishing or relying on lock parity.

## Safe Operation

Prefer project-init dry runs, migration dry runs, and local modes. Inspect each MCP tool’s defaults: `run_recipe` executes by default and `deploy_hermes_agent` is local but not dry-run by default. Do not assume all MCP calls are non-mutating.

## Registry and Projection Changes

Treat `~/.config/pjangler/projects.yaml` as catalog/bootstrap authority and `.project.json` as the repository-local runtime projection. Add regression coverage for central/local disagreement and concurrent registry updates when changing either model.

## Template Changes

Copier uses `--trust`; template tasks are executable host code. Pin template provenance, eliminate dirty gitlink dependence, and review remote installers, provider wiring, secret handling, systemd changes, and checkpoint pushes. Update platform change logs and define a regeneration/backfill plan for every material template contract change.

## Tests

The Node regression scripts create/remove temporary filesystem state. Run them only in a writable test environment. Existing coverage includes parity migration, MCP catalog/server flows, project initialization, registry conflicts, agent preservation, and ticket projections.

Add focused tests for prompt cancellation, ingredient failure propagation, MCP concurrent output capture, non-local Hermes provisioning, template shell scripts, Bloodbank contract/durability, and security boundaries.

## Known Self-Parity Drift

PJangler’s root mise hook syntax is older than its generated template, and `.mise/scripts/setup-plane.py` can recreate `.plane.json`. Repair sources before regenerating downstream projects. The root platform manifest currently points to another checkout and invokes Bun; use the live `33GOD/pjangler` repository and npm commands for evidence.

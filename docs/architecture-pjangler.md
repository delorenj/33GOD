# PJangler Architecture

## Executive Summary

PJangler is a host-local provisioning control plane with a Commander CLI and stdio MCP server. Its reliable core is registry/project projection, parity detection/migration, CommonProject rendering, and recipe orchestration. Several “live” and safe-default claims exceed implementation behavior, and generated Bloodbank integration is transitional.

## Technology Stack

| Category | Technology | Version/evidence |
|---|---|---|
| Runtime | Node.js ESM | >=20; local mise 26.4 |
| Language/build | TypeScript / esbuild | TS 5.9 lock, esbuild 0.25 |
| Interfaces | Commander / MCP SDK | 14.x / 1.29.0 |
| Validation | Zod / YAML | 4.4.3 / 2.9.0 |
| Templates | Copier | 9+ |
| Package | `@delorenj/pjangler` | code 1.2.18; lock root 1.2.10 |

## Architecture Pattern

Host automation and provisioning pipeline. Typed plans separate some preview from execution; parity rules detect/migrate repository state; recipes compose sequential ingredients; Copier templates create project and Hermes runtime projections.

## Core Components

- Central registry at `~/.config/pjangler/projects.yaml` with atomic replacement but no concurrency control.
- `.project.json` repository-local runtime projection.
- Eleven parity rules covering mise, versioning, symlinks, project identity, secrets, provenance, BMAD, Hermes, and systemd.
- CommonProject and Hermes Copier templates.
- CLI groups for project/recipe/command/audit/migrate/config/Hermes operations.
- Eleven MCP tools exposing overlapping catalog, audit, migration, bootstrap, project, recipe, and deployment behavior.

## Data Architecture

TypeScript interfaces and runtime validation, rather than JSON Schema, define the registry and `.project.json`. The central registry is catalog/bootstrap authority; `.project.json` is the repository-local runtime projection. See [PJangler Data Models](./data-models-pjangler.md).

## API Design

PJangler has no HTTP server. CLI and stdio MCP are its public control surfaces. Several MCP tools mutate by default, result success is sometimes inferred from console output, and recipe cancellation is not reliably terminal. See [PJangler Contracts](./api-contracts-pjangler.md).

## Template and Integration Architecture

Templates may mutate repositories, user profiles, systemd, external providers,
and remote services. Copier is invoked with trust. Template gitlinks must pin
published component revisions so parent commits remain reproducible; local
dirty submodule state is never release evidence.

### Repository ignore boundary (PJAN-126)

CommonProject treats `.gitignore` as a small, portable project contract. It
preserves existing content, appends only secret and `.agents` local-projection
rules, and never copies the operator's `core.excludesFile`. `.agents/` is the
only canonical agent-config tree; the six supported client roots remain local
generated projections governed by the global ignore.

The `bmad.cli-roots` migration removes only exact client-root override lines
from PJangler's retired managed block. It does not mutate Git's index. Existing
repositories use the globally distributed `gitignore-maintenance` skill to
resolve rule provenance, review tracked ignored paths, prove local copies
survive, and then commit/push explicit index changes.

> **Superseded 2026-08-04 (PJAN-19 landed):** Bloodbank command ingress is now the
> single fleet-shared `hermes-fleet-bloodbank-gateway.service` routing
> `data.target_agent_id` through the fleet registry. Provisioning writes the
> registry `bloodbank: {gateway_scope: fleet, target_agent_id}` block and installs
> NO per-agent consumer, checkpoint timer, or inbox files; `pj audit` /
> `pj migrate hermes.registry-parity` enforce this. Canon:
> `hermes-agent-template/docs/architecture.md` § "Bloodbank wiring". The
> paragraph below records the pre-PJAN-19 state this scan observed.

Generated Bloodbank integration (as of the July 2026 scan) used core NATS and inbox files, violated canonical subject routing, and spooled sentinel events locally. Candystore and Holocene are indirect downstream consumers, not direct API dependencies.

## Deployment Architecture

PJangler runs directly with host-user permissions. It has no container or Compose service. The platform `provisioning` profile is metadata, not a started service.

## Testing Strategy

Four Node regression scripts cover parity migrations, MCP catalog/server behavior, and project registry flows. Gaps include non-local provisioning, template shell behavior, cancellation/result propagation, MCP concurrency, security, and end-to-end Bloodbank delivery. Typechecking and built CLI smoke checks passed in the audit.

## Principal Risks

Wrong root repository identity, dirty/unpinned templates, package-lock version drift, misleading `--live` behavior, unsafe MCP defaults, failure/cancellation propagation defects, stale `.plane.json` setup, supply-chain `curl | sh`, secrets in process arguments, and host-level privilege.

## Development Workflow

Use [PJangler Development Guide](./development-guide-pjangler.md). Template changes require platform change evidence and downstream regeneration/backfill planning; repository-ignore drift is inventoried by `gitignore-global-policy-v1`.

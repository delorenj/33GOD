# PJangler CLI and MCP Contracts

## CLI

Implemented groups are `init`, `add`, `subsystems`, `board`, `notebook`, `list`, `info`, `remove`, `link`, `identity`, `doctor`, `reindex`, `recipe list|describe|run`, `command list|describe|create`, `audit`, `migrate`, and `describe`. `project init|list|show|remove|link|identity|doctor` survives as a legacy alias group over the same implementations. `command create` is the one unimplemented stub. Agent deploy and the org chart moved to Flume; see `flume/README.md`.

`audit` takes `--rules <comma,separated,ids>` to report only those rules; an unknown id is an error, never an empty pass. The eight employee rule ids are unknown to PJangler and answer to `flume audit`.

Project initialization supports preview, `--apply`, `--yes`, and interactive confirmation. Its typed plan can contain a ticket-provider action that execution logs but does not always perform, so `--live` is not a guarantee that every planned action ran.

## MCP Tools

The stdio server exposes:

1. `pjangler_list_capabilities`
2. `pjangler_list_parity_rules`
3. `pjangler_audit_project`
4. `pjangler_migrate_project`
5. `pjangler_bootstrap_33god_project`
6. `pjangler_project_init`
7. `pjangler_info`
8. `pjangler_project_list`
9. `pjangler_project_show`
10. `pjangler_describe_project`
11. `pjangler_describe_recipe`
12. `pjangler_run_recipe`

Inputs are Zod-validated. Results are JSON serialized inside MCP text content, not `structuredContent`.

## Mutation Semantics

Migration, bootstrap, and project init default toward preview/dry-run. `run_recipe` executes by default. Callers must inspect tool-specific semantics and cannot assume MCP-wide safe defaults.

## Failure Semantics

Recipe ingredients do not consistently stop on unsuccessful results. MCP recipe success may be inferred from captured console glyphs rather than structured results. Global console replacement makes concurrent calls potentially interfere.

## Security Boundary

MCP uses local stdio, but runs with host-user authority and can mutate repositories, GitHub, ticket providers, and templates. It no longer installs systemd units or writes agent profiles — Flume does that, and `enableSystemd` was removed rather than accepted and ignored. Target paths are not sandboxed. Treat MCP client configuration as privileged code execution.

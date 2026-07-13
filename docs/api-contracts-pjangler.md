# PJangler CLI and MCP Contracts

## CLI

Implemented groups include `init`, `add`, `list`, `project init|list|show|doctor`, `recipe list|describe|run`, `command list|describe|create`, `audit`, `migrate`, `hermes-agent`/`hermes`, `config bootstrap`, and `describe`. `command create` and top-level `describe` are unimplemented stubs.

Project initialization supports preview, `--apply`, `--yes`, and interactive confirmation. Its typed plan can contain ticket-provider and Hermes actions that execution currently logs but does not perform, so `--live` is not a guarantee that every planned action ran.

## MCP Tools

The stdio server exposes:

1. `pjangler_list_capabilities`
2. `list_parity_rules`
3. `audit_project`
4. `migrate_project`
5. `bootstrap_33god_project`
6. `project_init`
7. `project_list`
8. `project_show`
9. `describe_recipe`
10. `run_recipe`
11. `deploy_hermes_agent`

Inputs are Zod-validated. Results are JSON serialized inside MCP text content, not `structuredContent`.

## Mutation Semantics

Migration, bootstrap, and project init default toward preview/dry-run. `run_recipe` executes by default. `deploy_hermes_agent` defaults local but not dry-run. Callers must inspect tool-specific semantics and cannot assume MCP-wide safe defaults.

## Failure Semantics

Recipe ingredients do not consistently stop on unsuccessful results. Prompt cancellation can return `{success:false}` without halting Hermes provisioning. MCP recipe success may be inferred from captured console glyphs rather than structured results. Global console replacement makes concurrent calls potentially interfere.

## Security Boundary

MCP uses local stdio, but runs with host-user authority and can mutate repositories, profiles, systemd, GitHub, ticket providers, Telegram, Cloudflare, and templates. Target paths are not sandboxed. Treat MCP client configuration as privileged code execution.

# Ticket Provider (`tp`) adapters

The `tp` adapter is the Strategy layer that maps Krebs's five normalized bands to
each provider's native labels, columns, and APIs.

## Normalized bands

Krebs reasons in five coarse bands. A provider adapter must implement them:

| Band | Meaning |
|---|---|
| `backlog` | Not yet ready to pull |
| `unstarted` | Ready / triage / refining lanes |
| `started` | Actively in progress |
| `in_review` | Review / QA lanes |
| `completed` | Done |

## Adapter interface

Each provider implements these operations:

- `resolve()` → `{provider, board_id, board_url, me, list_map, board_lists}`
- `active_milestone()` → `{id, name, state}`
- `list_issues()` → list of normalized ticket objects
- `get_issue(id)` → normalized ticket object with comments
- `comment(id, body)` → create comment, return comment id
- `transition(id, band_or_lane)` → move ticket to the target band or literal lane

## Provider implementations

- `plane/` — Plane REST API adapter
- `linear/` — Linear GraphQL adapter
- `trello/` — Trello REST adapter

## Per-repo configuration

Provider credentials and board identifiers come from:

1. `.project.json` `ticket_provider` block
2. Environment variables (provider-specific)
3. Optional per-repo lane maps (e.g., `.momo/config.json` for Trello non-standard boards)

## Agent & Orchestrator Usage Notes

The `tp` adapter is purely an internal engine mechanism used by orchestrators like **Momo** and **Hermes PM** to talk to the configured ticket provider.

**Crucial Rules for AI Agents:**
1. **Never run `tp` as a bare CLI command.** `tp` is not a standalone executable in the system `$PATH`. It is a bash shell function maintained in `hermes-agent-template/template/.scripts/lib/ticket-provider.sh`. When a project is scaffolded, this script is placed in the project's agent role directory (e.g., `<role_dir>/.scripts/lib/ticket-provider.sh`).
2. **Execution context:** Orchestrator scripts (like Momo's `momo-board.sh`) locate the repo's `.project.json`, find the `role_dir`, source the `ticket-provider.sh` script, and only then call the `tp` function.
3. **Command syntax:** Even when properly sourced, the `tp` function requires an *operation* as the first argument, not a ticket number. For example, `tp get_issue PLANE-123` is correct; `tp PLANE-123` is a syntax error.

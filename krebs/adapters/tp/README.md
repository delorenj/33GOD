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

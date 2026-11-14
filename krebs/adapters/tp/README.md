# Ticket Provider (`tp`) adapters

The `tp` adapter is the Strategy layer that maps Krebs's five normalized bands to
each provider's native labels, columns, and APIs.

## Normalized bands

A provider adapter must implement these targets:

| Target | Meaning | Plane (lifecycle v2) |
|---|---|---|
| `backlog` | Not yet ready to pull | Backlog |
| `unstarted` | Accepted; triage, then waiting for a slot | Todo |
| `started` | Actively in progress | In Progress |
| `in_review` | Handed back, waiting for a verdict | In Progress + `lifecycle:review` |
| `completed` | Done | Done |
| `cancelled` | Abandoned | Cancelled |
| `awaiting_decision` | Held on a person (aliases `needs_attention`, `waiting_reply`) | + `lifecycle:needs-input`, lane unchanged (Todo or In Progress only) |

Plane boards follow [lifecycle v2](../../docs/lifecycle.md): the five stock lanes, with
review and holds carried by labels. The adapter never creates a lifecycle label and
writes labels as a delta on a fresh read, since Plane's PATCH replaces the whole list.
Linear and Trello have no lifecycle labels here, so their `in_review` and
`awaiting_decision` are lanes the role names. The nine-lane extended targets
(`e2e_testing`, `ready_for_documentation`, `needs_re_evaluation`) are retired.

## Adapter interface

Each provider implements these operations:

- `resolve()` → `{provider, board_id, board_url, me, list_map, board_lists}`
- `active_milestone()` → `{id, name, state}`
- `list_issues()` → list of normalized ticket objects
- `get_issue(id)` → normalized ticket object with comments
- `comment(id, body)` → create comment, return comment id
- `transition(id, band_or_lane)` → move ticket to the target band or literal lane

## Provider implementations

- `plane.sh` — Plane REST API adapter
- `linear.sh` — Linear GraphQL adapter
- `trello.sh` — Trello REST adapter

These three files are the CANONICAL copies. They used to live only inside
`hermes-agent-template/template/.scripts/providers/`, which made them agent
assets that a project could not use without one: pjangler created a project's
ticket board by staging a fake Hermes role tree in a temp dir and running the
agent template's adapter inside it. Board creation is a ticket concern, so the
adapters belong to Krebs, and both consumers now read them from here:

- Flume renders them into each employee's role directory, from a vendored mirror
  in the template. `tests/test_tp_adapter_vendoring.py` asserts the mirror is
  byte-identical to these files.
- pjangler resolves them directly for `pj init --provision-ticket-board`.

Change them HERE, then re-sync the template mirror.

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

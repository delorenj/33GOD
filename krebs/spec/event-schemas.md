# Krebs event schemas

Krebs normalizes ticket-provider events into CloudEvents and publishes them to
Bloodbank. This file documents the normalized event types and their payloads.

Krebs emits **repo-scoped task events**. The repo slug lives in `data.repo`.

The authority for event identity is
[`bloodbank/docs/event-naming.md`](../../bloodbank/docs/event-naming.md); the
runtime enforcement point is
`bloodbank/services/agent-hooks/core/validate.py`. Anything below that
conflicts with those two is a defect here.

## Envelope shape

- `type` is exactly four tokens: `bloodbank.<domain>.<entity>.<action>`.
  For Krebs that is `bloodbank.repo.task.<action>`. **There is no version
  token in `type`** — the schema-revision axis lives in `dataschema` and
  `schemaref`, never in the wire name.
- `subject` is the NATS subject: `bloodbank.evt.repo.task.<action>` — the
  same tokens as `type` with the kind marker `evt` inserted in position 2.
  It is five tokens. Ticket identity does **not** go here; it goes in
  `ordering_key` and `data`.
- `kind` is `event`, and `domain` must equal segment 2 of `type` (`repo`).
- `correlationid`, `producer`, `service`, `actor`, and `ordering_key` are
  required. Candystore **drops** an envelope missing any required field, so a
  publish that omits them reports success and persists nothing.
- `actor` carries provider identity (`plane`, `linear`, `trello`). Provider
  names are banned in `type` and belong in `actor`, `source`, and
  `data.provider` instead.
- `ordering_key` is `task:<repo>:<ticket_id>` for ticket events and
  `board:<board_id>` for board events.

Common fields on every Krebs envelope:

- `specversion`: `"1.0"`
- `source`: `urn:33god:agent:krebs`, or the originating provider adapter
- `datacontenttype`: `"application/json"`

## repo.task.created

Emitted when a new ticket is created in the provider.

```json
{
  "specversion": "1.0",
  "id": "<uuid>",
  "source": "urn:33god:agent:krebs",
  "type": "bloodbank.repo.task.created",
  "subject": "bloodbank.evt.repo.task.created",
  "time": "2026-08-02T00:00:00Z",
  "datacontenttype": "application/json",
  "schemaref": "bloodbank.repo.task.created.v1",
  "correlationid": "<uuid>",
  "causationid": null,
  "producer": "krebs",
  "service": "krebs",
  "domain": "repo",
  "kind": "event",
  "actor": {
    "type": "service",
    "agent_id": "bloodbank.agent.krebs",
    "provider": "plane"
  },
  "ordering_key": "task:<repo slug>:<provider ticket id>",
  "data": {
    "repo": "<repo slug>",
    "slug": "<repo slug>",
    "workspace": "33god",
    "board_id": "<provider board id>",
    "project_id": "<provider project id>",
    "ticket_id": "<provider ticket id>",
    "ticket_key": "<human-readable key>",
    "provider": "plane",
    "provider_event_type": "plane.ticket.created",
    "title": "...",
    "phase": "backlog",
    "tp_band": "backlog",
    "timestamp": "2026-08-02T00:00:00Z",
    "ticket": {}
  }
}
```

## repo.task.updated

Emitted on every ticket update that changes state, assignment, labels, title, or
other tracked fields.

```json
{
  "specversion": "1.0",
  "id": "<uuid>",
  "source": "urn:33god:agent:krebs",
  "type": "bloodbank.repo.task.updated",
  "subject": "bloodbank.evt.repo.task.updated",
  "time": "2026-08-02T00:00:00Z",
  "datacontenttype": "application/json",
  "schemaref": "bloodbank.repo.task.updated.v1",
  "correlationid": "<uuid>",
  "causationid": null,
  "producer": "krebs",
  "service": "krebs",
  "domain": "repo",
  "kind": "event",
  "actor": {
    "type": "service",
    "agent_id": "bloodbank.agent.krebs",
    "provider": "plane"
  },
  "ordering_key": "task:<repo slug>:<provider ticket id>",
  "data": {
    "repo": "<repo slug>",
    "project_id": "<provider project id>",
    "ticket_id": "<provider ticket id>",
    "ticket_key": "<human-readable key>",
    "slug": "<repo slug>",
    "workspace": "33god",
    "board_id": "<provider board id>",
    "provider": "plane",
    "provider_event_type": "plane.ticket.transitioned",
    "previous_phase": "triage",
    "phase": "ready",
    "previous_tp_band": "unstarted",
    "tp_band": "unstarted",
    "changed_fields": ["phase"],
    "trigger_source": "momo",
    "timestamp": "2026-08-02T00:00:00Z",
    "ticket": {}
  }
}
```

## repo.task.appended

Emitted when a new comment is added to a ticket.

```json
{
  "specversion": "1.0",
  "id": "<uuid>",
  "source": "urn:33god:agent:krebs",
  "type": "bloodbank.repo.task.appended",
  "subject": "bloodbank.evt.repo.task.appended",
  "time": "2026-08-02T00:00:00Z",
  "datacontenttype": "application/json",
  "schemaref": "bloodbank.repo.task.appended.v1",
  "correlationid": "<uuid>",
  "causationid": null,
  "producer": "krebs",
  "service": "krebs",
  "domain": "repo",
  "kind": "event",
  "actor": {
    "type": "service",
    "agent_id": "bloodbank.agent.krebs",
    "provider": "plane"
  },
  "ordering_key": "task:<repo slug>:<provider ticket id>",
  "data": {
    "repo": "<repo slug>",
    "project_id": "<provider project id>",
    "ticket_id": "<provider ticket id>",
    "ticket_key": "<human-readable key>",
    "slug": "<repo slug>",
    "workspace": "33god",
    "board_id": "<provider board id>",
    "provider": "plane",
    "provider_event_type": "plane.ticket.commented",
    "comment_id": "<provider comment id>",
    "author_id": "<provider user id>",
    "body": "<markdown body>",
    "appended_at": "2026-08-02T00:00:00Z",
    "comment": {}
  }
}
```

## repo.task.flagged

Emitted when a ticket exceeds its configured staleness threshold in a phase.

> **Not yet schema-backed.** `bloodbank/schemas/bloodbank/repo/` has no
> `task.flagged.json`. The envelope below satisfies the naming contract, but
> `validate_envelope()` cannot check its `data` until that schema is authored.
> Treat the `data` block as provisional.

```json
{
  "specversion": "1.0",
  "id": "<uuid>",
  "source": "urn:33god:agent:krebs",
  "type": "bloodbank.repo.task.flagged",
  "subject": "bloodbank.evt.repo.task.flagged",
  "time": "2026-08-02T00:00:00Z",
  "datacontenttype": "application/json",
  "schemaref": "bloodbank.repo.task.flagged.v1",
  "correlationid": "<uuid>",
  "causationid": null,
  "producer": "krebs",
  "service": "krebs",
  "domain": "repo",
  "kind": "event",
  "actor": {
    "type": "service",
    "agent_id": "bloodbank.agent.krebs",
    "provider": "plane"
  },
  "ordering_key": "task:<repo slug>:<provider ticket id>",
  "data": {
    "repo": "<repo slug>",
    "project_id": "<provider project id>",
    "ticket_id": "<provider ticket id>",
    "ticket_key": "<human-readable key>",
    "provider": "plane",
    "flag_reason": "stale",
    "stuck_phase": "in_progress",
    "duration_minutes": 150,
    "max_duration_minutes": 120,
    "timestamp": "2026-08-02T00:00:00Z"
  }
}
```

## Provider-specific webhook mapping

Incoming provider webhooks are normalized to the events above.

| Provider event | Normalized Krebs event |
|---|---|
| Plane: issue.created | repo.task.created |
| Plane: issue.updated | repo.task.updated |
| Plane: comment.created | repo.task.appended |
| Linear: Issue created | repo.task.created |
| Linear: Issue updated | repo.task.updated |
| Linear: Comment created | repo.task.appended |
| Trello: createCard | repo.task.created |
| Trello: updateCard | repo.task.updated |
| Trello: commentCard | repo.task.appended |

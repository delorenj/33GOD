# Krebs event schemas

Krebs normalizes ticket-provider events into CloudEvents and publishes them to
Bloodbank. This file documents the normalized event types and their payloads.

Krebs emits **repo-scoped task events**. The repo slug lives in `data.repo`.

All events use the CloudEvents 1.0 envelope with these fields:

- `specversion`: "1.0"
- `type`: `bloodbank.v1.repo.task.<action>`
- `source`: `hermes://agent/krebs` or the originating provider adapter
- `subject`: `task:<ticket_id>`
- `datacontenttype`: "application/json"

## repo.task.created

Emitted when a new ticket is created in the provider.

```json
{
  "specversion": "1.0",
  "type": "bloodbank.v1.repo.task.created",
  "source": "hermes://agent/krebs",
  "subject": "task:<ticket_id>",
  "id": "<uuid>",
  "time": "2026-08-02T00:00:00Z",
  "datacontenttype": "application/json",
  "data": {
    "repo": "<repo slug>",
    "project_id": "<provider project id>",
    "ticket_id": "<provider ticket id>",
    "ticket_key": "<human-readable key>",
    "provider": "plane",
    "title": "...",
    "phase": "backlog",
    "tp_band": "backlog",
    "timestamp": "2026-08-02T00:00:00Z"
  }
}
```

## repo.task.updated

Emitted on every ticket update that changes state, assignment, labels, title, or
other tracked fields.

```json
{
  "specversion": "1.0",
  "type": "bloodbank.v1.repo.task.updated",
  "source": "hermes://agent/krebs",
  "subject": "task:<ticket_id>",
  "id": "<uuid>",
  "time": "2026-08-02T00:00:00Z",
  "datacontenttype": "application/json",
  "data": {
    "repo": "<repo slug>",
    "project_id": "<provider project id>",
    "ticket_id": "<provider ticket id>",
    "ticket_key": "<human-readable key>",
    "provider": "plane",
    "previous_phase": "triage",
    "phase": "ready",
    "previous_tp_band": "unstarted",
    "tp_band": "unstarted",
    "changed_fields": ["phase"],
    "trigger_source": "momo",
    "timestamp": "2026-08-02T00:00:00Z"
  }
}
```

## repo.task.appended

Emitted when a new comment is added to a ticket.

```json
{
  "specversion": "1.0",
  "type": "bloodbank.v1.repo.task.appended",
  "source": "hermes://agent/krebs",
  "subject": "task:<ticket_id>",
  "id": "<uuid>",
  "time": "2026-08-02T00:00:00Z",
  "datacontenttype": "application/json",
  "data": {
    "repo": "<repo slug>",
    "project_id": "<provider project id>",
    "ticket_id": "<provider ticket id>",
    "ticket_key": "<human-readable key>",
    "provider": "plane",
    "comment_id": "<provider comment id>",
    "author_id": "<provider user id>",
    "body": "<markdown body>",
    "appended_at": "2026-08-02T00:00:00Z"
  }
}
```

## repo.task.flagged

Emitted when a ticket exceeds its configured staleness threshold in a phase.

```json
{
  "specversion": "1.0",
  "type": "bloodbank.v1.repo.task.flagged",
  "source": "hermes://agent/krebs",
  "subject": "task:<ticket_id>",
  "id": "<uuid>",
  "time": "2026-08-02T00:00:00Z",
  "datacontenttype": "application/json",
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

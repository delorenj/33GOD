# Bloodbank Event Schemas

Reference for events broadcast during ticket lifecycle execution.
Source schemas: ~/code/33GOD/holyfields/schemas/agent/

## ticket.state_changed

Broadcast at every state transition. Primary event for this workflow.

```json
{
  "event_type": "ticket.state_changed",
  "version": "v1",
  "payload": {
    "project_id": "{from ticket_provider.board_id in .project.json}",
    "ticket_id": "{plane ticket ID}",
    "previous_state": "{state before transition}",
    "new_state": "{state after transition}",
    "trigger_source": "ticket-lifecycle-workflow",
    "timestamp": "{ISO 8601}"
  }
}
```

## ticket.stale

Broadcast when a ticket exceeds max duration in any state.

```json
{
  "event_type": "ticket.stale",
  "version": "v1",
  "payload": {
    "project_id": "{from ticket_provider.board_id in .project.json}",
    "ticket_id": "{plane ticket ID}",
    "stuck_state": "{state ticket is stuck in}",
    "duration_minutes": "{how long it has been in this state}",
    "max_duration_minutes": "{configured max from workflow.yaml}",
    "timestamp": "{ISO 8601}"
  }
}
```

## Existing Holyfields Schemas Used

These are published via Bloodbank CLI at ~/code/33GOD/bloodbank/

- `agent.task.assigned` - When sub-agent receives work
- `agent.task.completed` - When sub-agent finishes work
- `agent.message.sent` - For audit trail notifications

## Publishing

```bash
# Example: publish state change event
cd ~/code/33GOD/bloodbank
./publish.sh ticket.state_changed '{payload_json}'
```

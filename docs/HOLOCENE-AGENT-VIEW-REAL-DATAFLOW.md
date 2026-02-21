# Holocene Agent View — Real Dataflow Design

## Goal
Replace placeholder agent cards with real roster, avatars, and ticket-backed activity.

## Source of Truth
1. **Agent roster**: static config `services/registry.yaml` + agent session metadata.
2. **Avatars**: filesystem mount of `~/.openclaw/Avatars/` into Holocene container (read-only).
3. **Activity stream**: Bloodbank events (`agent.*`, `session.*`, `task.*`).
4. **Ticket linkage**: Plane GOD project issues filtered by assignee/agent label.

## Required Rule
An agent can only display `working` if there is an active matching Plane ticket (`started`/`in-progress`).
No active ticket -> show `idle` or `blocked`.

## Proposed Pipeline
1. Holocene ingest live events via WS relay (`ws://bloodbank-ws-relay:8683`).
2. Normalize events into per-agent activity cache keyed by `agent_name`.
3. Poll Plane API every 60s for active GOD issues.
4. Join activity cache + Plane ticket map.
5. Resolve avatar path by agent name (`~/.openclaw/Avatars/{agent}.png`).
6. Render cards with: avatar, status, current ticket id/title, last event timestamp.

## Data Contracts
- `AgentCardViewModel`
  - `agent_name`
  - `avatar_uri`
  - `status` (idle|working|blocked|offline)
  - `current_ticket_id`
  - `current_ticket_title`
  - `last_event_type`
  - `last_event_at`

## Guardrails
- If ticket lookup fails -> force status to `idle`.
- If avatar missing -> deterministic fallback icon (no dragons).
- Emit telemetry event `holocene.agent_view.mismatch` when event says working but no ticket exists.

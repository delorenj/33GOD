# Bloodbank Event Bus Live Audit — 2026-02-21

## Runtime Checks
- RabbitMQ running: YES (`theboard-rabbitmq`)
- Bloodbank API running: YES (`http://127.0.0.1:8682/healthz`)
- WS relay path alive: YES (`ws://127.0.0.1:11819/ws` welcome message)
- Active consumers: YES (`bloodbank-ws-broadcaster`, `infra-dispatcher`, relay queue)

## End-to-End Flow Proven
Flow: `Agent action -> Bloodbank publish -> RabbitMQ -> WS relay -> Holocene stream`

### Proof command output
- API publish:
  - `POST http://127.0.0.1:8682/events/custom`
  - Response: `200 {"status":"published", ...}`
- WS receive from Holocene endpoint:
  - `{"routing_key":"agent.grolf.action", ...}`

Result: live events reach dashboard stream path.

## Follow-up
- Increase producer coverage (more real agent actions) so dashboard is continuously populated.
- Add health dashboard widget for queue consumer counts + event rate.

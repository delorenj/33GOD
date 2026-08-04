# Observability

Krebs exposes queryable event history and health metrics for ticket activity.

## Event log

All normalized Krebs events are durably stored in Candystore (via Bloodbank).
Queries support:

- Ticket-level history
- Project-level aggregate transitions
- Staleness reports
- Provider sync lag

## Health metrics

- Webhook delivery success/failure rate per provider
- Normalization error rate
- Fan-out latency
- Lifecycle phase distribution

## Consumers

- Candybar topology / dashboards
- Holocene mission control
- Operator ad-hoc queries via MCP

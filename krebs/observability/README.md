# Observability

> **Not implemented.** Krebs serves none of the queries or metrics below; this
> is a design note. Ticket history today is the `bloodbank.repo.task.*` facts
> the n8n `Plane → Bloodbank` workflow publishes (see `../webhooks/README.md`),
> stored by Candystore. Krebs's own record is `bloodbank.evt.lifecycle.receipt.recorded`.

Krebs would expose queryable event history and health metrics for ticket activity.

## Event log

Ticket facts are durably stored in Candystore (via Bloodbank).
Queries support:

- Ticket-level history
- Project-level aggregate transitions
- Staleness reports
- Provider sync lag

## Health metrics

- Webhook delivery and normalization errors (owned by the n8n workflow, not Krebs)
- Lifecycle phase distribution

## Consumers

- Candybar topology / dashboards
- Holocene mission control
- Operator ad-hoc queries via MCP

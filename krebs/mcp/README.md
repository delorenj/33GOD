# MCP domains

Krebs exposes its capabilities to agents through the Pipeline MCP Hub.

## Domains

- `krebs.lifecycle` — read lifecycle spec, validate phase transitions
- `krebs.ticket_provider` — list adapters, resolve provider label ↔ band mappings
- `krebs.webhooks` — inspect ingress health and recent normalized events
- `krebs.observability` — query staleness, transition counts, provider lag

All domain tools emit repo-scoped `bloodbank.v1.repo.task.*` events on mutations.
See `spec/event-schemas.md` for event payloads.

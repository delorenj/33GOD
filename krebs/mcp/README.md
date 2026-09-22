# MCP domains

> **Not implemented.** No MCP server or hub registers any `krebs.*` domain
> below; this is a design note. Krebs managed v2 is driven over Bloodbank
> (`bloodbank.cmd.lifecycle.task.invoke`), not MCP.

Krebs would expose its capabilities to agents through the Pipeline MCP Hub.

## Domains

- `krebs.lifecycle` — read lifecycle spec, validate phase transitions
- `krebs.ticket_provider` — list adapters, resolve provider label ↔ band mappings
- `krebs.observability` — query staleness, transition counts, provider lag

Mutations would go through Pilot to the provider; the provider's webhook echo
(normalized by n8n, see `webhooks/README.md`) is the `bloodbank.repo.task.*`
fact. See `spec/event-schemas.md`.

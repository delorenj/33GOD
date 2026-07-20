# Bloodbank Component Inventory

| Component | Location | Current responsibility |
|---|---|---|
| Contract schemas | `schemas/` | Canonical event and command envelopes |
| Event naming | `docs/event-naming.md` | Canonical subjects, types, and token rules |
| NATS topology | `compose/nats/` | JetStream declarations and initialization |
| Dapr components | `compose/components/` | Pub/sub and transport configuration |
| Agent hooks | `services/agent-hooks/` | Canonical mapping, envelope validation, and publication |
| Heartbeat services | `services/heartbeat-*` | Reference transport producers/consumers |
| Operator CLI | `cli/bb.py` | Contract and transport diagnostics |
| Operations | `ops/` | Bootstrap, smoke, trace, replay, and repository health |
| Registry/catalog | Compose Apicurio/EventCatalog services | Optional contract discovery infrastructure |
| Adapters | `adapters/` | Transport integration scaffolds |

Bloodbank has no executable lifecycle authority. Its current ownership ends at
schemas, validation, transport, and non-authoritative observations. Lifecycle
owns deterministic state, reconciliation, legal work, capabilities, commands,
and every authoritative write.

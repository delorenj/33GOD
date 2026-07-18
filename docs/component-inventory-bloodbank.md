# Bloodbank Component Inventory

| Component | Location | Status and responsibility |
|---|---|---|
| Contract schemas | `schemas/` | Canonical 61-document event/command model |
| NATS topology | `compose/nats/` | Two JetStream declarations and partial reconciliation |
| Dapr components | `compose/components/` | Event pub/sub, in-memory state, environment secrets |
| Agent hooks | `services/agent-hooks/` | Canonical mapping, envelope construction, validation, raw NATS publication |
| Heartbeat tick | `services/heartbeat-tick/` | Dapr reference producer |
| Heartbeat recorder | Referenced but absent | Broken Compose/CI build dependency |
| Lifecycle controller embryo | `services/lifecycle-controller/` | Tested deterministic reconcile/state/history/outbox worker; undeployed, publisher-unconfigured, and approved for history-preserving extraction into Lifecycle |
| Operator CLI | `cli/bb.py` | Doctor/envelope verification plus unimplemented emit/trace/replay surfaces |
| Operations | `ops/` | Bootstrap, smoke, trace, replay, repo-health, and BMAD workflows |
| Registry/catalog | Compose Apicurio/EventCatalog services | Infrastructure present without proven schema/catalog synchronization |
| Adapters | `adapters/` | Migration scaffolds, not production integrations |

The agent-hook contract layer is the most mature runtime producer. The
controller embryo is extraction evidence, not Bloodbank's target domain
ownership. Its outbox and schema drift, plus the heartbeat deployment path,
require repair before they are operational guarantees.

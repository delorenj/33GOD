# 33GOD Product Map

33GOD is a private, local-first development environment. Component
implementations remain split across repos; this control plane provides one
root-owned, normalized Compose target and one product-governance surface. The
local Lifecycle path has semantic and isolated live validation; hosted/cloud
topology is outside the supported scope.

| Product card | Component | What subscribers get |
|---|---|---|
| Event Backbone | Bloodbank | CloudEvents over NATS/Dapr with canonical schemas and transport contracts. |
| Event History | Candystore | Durable event/session history with query and summary APIs. |
| Lifecycle Authority | Lifecycle | Versioned spec/state, deterministic reconciliation, legal frontier, obligations, capability validation, and all lifecycle writes. |
| Process Manager | Momo | Intelligent PM/EM policy and durable actor that selects legal work, executes exact skill invocations, and publishes retry-stable artifact evidence with PubAck-before-ACK without writing lifecycle truth. |
| Operator Dashboard | Holocene | Dashboard/renderer and high-level action invoker for pipeline health, hooks, agents, and operations. |
| Project Factory | PJangler | Project identity, bootstrap, and provider-neutral bindings from one registry and template set. |
| Managed AI Worker Fleet | Hermes Fleet | Long-running agents with shared provider config and profile-local state. |
| Unified Agent Skills | Skillex | One skill/capability catalog distributed across coding-agent CLIs. |
| Persistent Memory | Hindsight | Recall, retain, and journal hooks across sessions. |
| Tool Gateway | Pipeline MCP Hub | Compact MCP access to Plane, Bloodbank, lifecycle, and future domains. |
| Visual Topology | Candybar | Event and service topology inspection. |
| Voice Interface | HeyMa | Voice, meeting, transcription, and TTS integration path. |

## Product layers

1. **Runtime core:** Bloodbank, Dapr, NATS, Lifecycle, and Candystore.
2. **Process policy:** Momo PM/EM orchestration over Lifecycle's legal frontier.
3. **Operator access:** Holocene dashboard/renderer and Pipeline MCP Hub.
4. **Bootstrap and bindings:** PJangler, CommonProject, Hermes agent templates.
5. **Agent capability:** Skillex, Hindsight, canonical hooks.
6. **Root governance:** platform manifests, exact pins, topology, acceptance, and drift.

## Local-first rule

The laptop product must work before the hosted product exists. The current
default target covers Bloodbank core; dedicated Lifecycle
PostgreSQL/migrate/bootstrap/serve; one standalone Candystore; Holocene API
preflight; and Holocene web. PJangler remains run-only CLI/stdio MCP tooling in
`tools` and `full`; Momo is a client seam, not a second reconcile service.

`cloud` renders only to expose remaining local binds, external networks, host
systemd authority, local credentials, and storage assumptions. It is
unsupported and must never be started with `docker compose up`. Hosted
deployment requires separate auth, tenancy, managed storage, backup/restore,
network, and secret-provider design.

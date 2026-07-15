# 33GOD Product Map

33GOD is a private, local-first development environment. Component
implementations remain split across repos; this control plane provides one
root-owned, normalized Compose target and one product-governance surface. The
target is statically validated but has not replaced the existing component
projects on the host.

| Product card | Component | What subscribers get |
|---|---|---|
| Event Backbone | Bloodbank | CloudEvents over NATS/Dapr with canonical schemas and agent lifecycle events. |
| Event History | Candystore | Durable event/session history with query and summary APIs. |
| Mission Control | Holocene | Live dashboard for pipeline health, hooks, agents, and operations. |
| Project Factory | PJangler | Project and agent provisioning from one registry and template set. |
| Managed AI Worker Fleet | Hermes Fleet | Long-running agents with shared provider config and profile-local state. |
| Unified Agent Skills | Skillex | One skill/capability catalog distributed across coding-agent CLIs. |
| Persistent Memory | Hindsight | Recall, retain, and journal hooks across sessions. |
| Tool Gateway | Pipeline MCP Hub | Compact MCP access to Plane, Bloodbank, lifecycle, and future domains. |
| Visual Topology | Candybar | Event and service topology inspection. |
| Voice Interface | HeyMa | Voice, meeting, transcription, and TTS integration path. |

## Product layers

1. **Runtime core:** Bloodbank, Dapr, NATS, Candystore.
2. **Control plane:** Holocene, Pipeline MCP Hub, platform manifests.
3. **Provisioning:** PJangler, CommonProject, Hermes agent templates.
4. **Agent capability:** Skillex, Hindsight, canonical hooks.
5. **Operator experience:** Candybar, HeyMa, product docs.

## Local-first rule

The laptop product must work before the hosted product exists. The current
default target covers Bloodbank core, one standalone Candystore, Holocene API
preflight, and Holocene web. PJangler remains run-only CLI/stdio MCP tooling in
`tools` and `full`; it has no service port or daemon contract.

`cloud` renders only to expose remaining local binds, external networks, host
systemd authority, local credentials, and storage assumptions. It is
unsupported and must never be started with `docker compose up`. Hosted
deployment requires separate auth, tenancy, managed storage, backup/restore,
network, and secret-provider design.

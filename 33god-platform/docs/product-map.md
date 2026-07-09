# 33GOD Product Map

33GOD is a private, local-first, cloud-ready development environment. The
current implementation remains split across repos; this control plane turns
those repos into one product surface.

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

The laptop product must work before the hosted product exists. Hosted deployment
uses the same component graph with stricter auth, tenant/workspace IDs, managed
storage, and cloud secret stores.

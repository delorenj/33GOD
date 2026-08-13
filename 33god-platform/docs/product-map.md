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

## Planned integration layer

These boundaries are part of the target product but are not active component
registry members. They enter `components.yaml` only after a real repository or
immutable deployment contract, lifecycle owner, health check, source-of-truth
paths, and validation gates exist.

| Product capability | Boundary | Intended role |
|---|---|---|
| Workforce and Delegation | Flume | Corporate hierarchy, authority, task delegation, escalation, and budget policy above agent runtimes. |
| Agent Session Broker | LiteLLM Agent Control Plane | Experimental normalized session/runtime API and developer lab beneath Flume and above canonical Bloodbank dispatch. |
| Model Gateway | DeLoNET LiteLLM | Provider credentials, model catalog, budgets, aliases, and fallback policy for every approved runtime. |
| Executive Surface | DeLoHQ | Mobile status, approvals, exceptions, budgets, and coarse controls; currently projected through Holocene's `/hq` surface. |
| Research Read Model | OpenNotebook | Searchable project corpus and synthesis over canonical Git/BMAD evidence; never an architectural source of truth. |

The approved ownership and pilot design lives in
[`litellm-agent-control-plane-integration.md`](litellm-agent-control-plane-integration.md).

## Product layers

1. **Runtime core:** Bloodbank, Dapr, NATS, Candystore.
2. **Control plane:** Holocene, Pipeline MCP Hub, platform manifests.
3. **Provisioning:** PJangler, CommonProject, Hermes agent templates.
4. **Agent capability:** Skillex, Hindsight, canonical hooks.
5. **Operator experience:** Candybar, HeyMa, product docs.
6. **Planned execution integration:** Flume policy -> ACP sessions -> Bloodbank
   commands -> Hermes fleet, with DeLoNET LiteLLM owning model routing.

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

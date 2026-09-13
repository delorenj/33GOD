# 33GOD Product Map

33GOD is a private, local-first development environment. Component
implementations remain split across repos; this control plane provides one
root-owned, normalized Compose target and one product-governance surface. The
root-managed Bloodbank, Candystore, and Holocene core is live on the host; the
hosted/cloud projection remains validation-only.

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

## Integration spines

| Journey | Path | Meaning |
|---|---|---|
| External fact | Plane → signed n8n ingress → Bloodbank EVENTS → Candystore → Holocene | A ticket-provider fact is authenticated, normalized, transported, durably stored, and then displayed. |
| Agent intent | Momo/UI/CLI → Bloodbank COMMANDS → Hermes gateway → fleet-registry gate → Hermes profile | Work is requested; the command itself is not evidence that work completed. |
| Lifecycle proof | Hermes gateway/profile → Bloodbank EVENTS → Candystore → Holocene | Started, completed, failed, or rejected facts close the command correlation loop. |
| Memory context | Agent runtime ↔ Hindsight | Recall/retain augments decisions but never replaces ticket, event, or command authority. |
| Repository hygiene | Skillex → `gitignore-maintenance` → Git effective-ignore/index review; PJangler → CommonProject repo contract | Global personal exclusions stay global, project rules stay portable, and tracked ignored files are removed only after provenance review. |

The complete authority map, security boundary, current proof, and editable
architecture/message-trace diagrams are in [Event and Command
Journey](../../docs/event-journey.md).

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

Repository hygiene deliberately spans provisioning and capability layers.
CommonProject preserves an existing `.gitignore` and adds only project-owned
secret/local-projection rules; it never copies a developer's
`core.excludesFile`. PJangler can retire only its exact historical managed
lines and never mutates the index. Skillex distributes
`gitignore-maintenance`, which resolves the effective global file dynamically,
audits tracked matches with provenance, and performs the reviewed commit/push
parity workflow. `.agents/` is canonical; `.claude/`, `.codex/`, and the other
client roots are local generated projections.

## Local-first rule

The laptop product must work before the hosted product exists. The current live
default stack covers Bloodbank core, one standalone Candystore, Holocene API
preflight, and Holocene web. PJangler remains run-only CLI/stdio MCP tooling in
`tools` and `full`; it has no service port or daemon contract.

`cloud` renders only to expose remaining local binds, external networks, host
systemd authority, local credentials, and storage assumptions. It is
unsupported and must never be started with `docker compose up`. Hosted
deployment requires separate auth, tenancy, managed storage, backup/restore,
network, and secret-provider design.

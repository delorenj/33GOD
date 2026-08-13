# LiteLLM Agent Control Plane integration

- Status: **architecture intent approved; implementation gated**
- Decision date: 2026-08-13
- Planning owner: `33god-pm`
- Platform owner: `33god-platform`
- Candidate upstream revision: `53bfd20e2fec51fc8f665fb614512c6b138367da`

## Decision

33GOD will evaluate the LiteLLM Agent Control Plane (ACP) as a subordinate
agent execution and session broker. ACP is not the 33GOD control plane and does
not replace any existing source of truth.

The target relationship is:

```text
DeLoHQ / Holocene
  executive status, approvals, operations, fleet and session views
                         |
                         v
Flume
  workforce hierarchy, delegation, task policy, budgets
                         |
                  normalized work request
                         v
LiteLLM ACP
  session API, runtime normalization, SSE, developer lab
                         |
                 33GOD managed-agent adapter
                         v
Bloodbank command -> fleet-shared Hermes gateway -> target profile
        |                                          |
        |                                          v
        |                                DeLoNET LiteLLM gateway
        |                                model policy and fallbacks
        v
Candystore -> Holocene / DeLoHQ / ACP correlated session projection

Git + BMAD artifacts ---------------------- canonical product intent
OpenNotebook ------------------------------ searchable research/read model
Hindsight --------------------------------- durable agent memory
```

ACP earns a place in the stack by normalizing sessions across runtimes and by
providing an immediate agent laboratory. It must remain removable: stopping ACP
must not stop or degrade existing Hermes PMs, their heartbeats, Telegram/Slack
gateways, or canonical Bloodbank command routing.

## Ownership boundaries

| Concern | Canonical owner | ACP relationship |
| --- | --- | --- |
| Product intent, architecture, epics, stories | Git and BMAD artifacts | Reads approved definitions; never becomes the product record |
| Project, board, and permanent agent identity | `.project.json` and PJangler | Read-only projection; no duplicate permanent identities |
| Ticket lifecycle | Krebs | Consumes normalized work state; no private state machine |
| Workforce hierarchy and delegation policy | Flume | Execution port beneath Flume; no competing org model |
| Fleet profiles and host lifecycle | Hermes fleet registry and systemd | Calls registered profiles; no per-agent ACP consumer or scheduler |
| Command ingress and event contracts | Bloodbank | Translates ACP turns into canonical commands and consumes correlated events |
| Durable event history | Candystore | ACP holds only its session projection/cache |
| Durable agent memory | Hindsight | ACP memory is optional session-local scratch only |
| Models, provider credentials, budgets, and fallbacks | DeLoNET LiteLLM | Uses a scoped virtual key and stable gateway aliases |
| Tool and skill distribution | Pipeline MCP Hub, Skillex, project manifests | References approved tools; no duplicate source of truth |
| Operator mission control | Holocene | Supplies runtime/session data to the existing control surface |
| Mobile executive surface | DeLoHQ, currently the Holocene `/hq` surface | Status, approvals, exceptions, budgets, and coarse controls only |
| Research corpus and synthesis | OpenNotebook | Searchable read model over canonical sources; never authoritative |

Flume, DeLoHQ, OpenNotebook, DeLoNET LiteLLM, and ACP are integration
boundaries, not automatically active `components.yaml` members. A service joins
the active registry only when its repository or immutable deployment contract,
health check, lifecycle owner, source-of-truth paths, and validation gates are
real. This is the same rule currently keeping Flume out of the active registry.

## Why ACP is useful

### A real Flume execution port

Flume keeps the human-legible company model: employees, teams, managers,
directors, delegation, budgets, and escalation. ACP supplies the lower-level
session operations that should not be embedded in that domain model:

- create or resume a runtime session;
- send a user turn;
- stream runtime events;
- normalize runtime-specific state;
- attach approved tools and workspace context;
- terminate disposable sessions.

The first mapping is deliberately small:

| Flume/33GOD concept | ACP/runtime concept |
| --- | --- |
| work request | user message/turn |
| employee identity | `target_agent_id` for managed agents, runtime definition for ephemeral workers |
| delegated task ID | correlation ID plus ACP session ID |
| task attempt | ACP turn ID plus Bloodbank command ID |
| work result | terminal lifecycle event plus correlated assistant message/artifact |
| escalation/approval | Bloodbank event projected to Holocene/DeLoHQ |

### A normalized session projection

Holocene should not implement every coding-agent protocol. ACP can expose a
common session/read surface while Bloodbank and Candystore remain the audit
spine. Holocene combines both views: ACP supplies live runtime/session detail;
Candystore supplies canonical event history and attribution.

DeLoHQ remains intentionally narrower than either ACP or Holocene. It is the
executive surface for status, approvals, exceptions, spend/budget posture, and
safe coarse controls. It is not a mobile IDE or a second agent builder.

### An immediate agent laboratory

ACP's dashboard can be used to test disposable agent definitions, runtimes,
tools, models, and session behavior before those capabilities are productized
in Holocene. Ephemeral workers may be ACP-native. Long-running PMs and other
permanent identities must remain PJangler-managed Hermes profiles.

## Managed Hermes adapter contract

The pilot runtime adapter is named `33god-hermes`. It must publish one canonical
command per ACP turn:

- subject: `bloodbank.cmd.v1.agent.invocation.start`;
- type: `bloodbank.v1.agent.invocation.start`;
- schema reference: `bloodbank.v1.agent.invocation.start.v1`;
- routing key: `data.target_agent_id`;
- delivery: `single_consumer`;
- ACP session ID -> `data.thread_id`;
- ACP turn ID -> `data.turn_id`;
- prompt -> `data.prompt`;
- ACP/session metadata -> bounded, non-secret `data.context`;
- stable `correlationid`, `causationid`, `command_id`, and
  `idempotency_key` on every command;
- an actor that identifies the ACP adapter, never a provider name in the event
  type.

The adapter consumes correlated canonical events rather than scraping Hermes
runtime files:

- `bloodbank.v1.conversation.turn.started`;
- `bloodbank.v1.agent.invocation.started`;
- `bloodbank.v1.agent.invocation.completed`;
- `bloodbank.v1.agent.invocation.failed`;
- `bloodbank.v1.conversation.turn.completed`;
- `bloodbank.v1.conversation.message.appended` for assistant text and artifact
  references.

The final event is the known contract gap. The current fleet-shared gateway
publishes lifecycle completion but not the assistant reply text. An ACP chat
session is not considered complete until the reply can be returned through a
schema-conformant correlated event or equivalent governed response stream.
This work belongs in Bloodbank and requires Candystore and Holocene consumer
review.

## Model and credential policy

ACP receives no direct OpenAI, Anthropic, Kimi, Google, or OpenRouter
credentials for the managed-Hermes path. Model requests use the DeLoNET
LiteLLM gateway through a least-privilege virtual key. The gateway remains the
only owner of account selection and fallback policy.

The initial managed-Hermes alias is `hermes`, whose current text/coding chain
is:

```text
Kimi Code plan
  -> personal ChatGPT plan / gpt-5.6-sol
  -> OpenRouter / deepseek/deepseek-v4-flash
```

Direct-provider routes and unsupported modalities do not inherit this fallback
chain. ACP runtime templates that require Anthropic or Gemini API keys do not
unlock Claude Code or Antigravity subscription OAuth and are outside this
pilot.

The scoped ACP key must have:

- only the aliases/models needed by the pilot;
- a bounded spend or request budget;
- a distinct identity for LiteLLM logs and revocation;
- no dashboard, key-management, or unrelated provider authority;
- runtime-only secret injection, never tracked configuration.

## Security and trust boundary

The initial deployment is a single-operator internal lab, not a hosted or
multi-tenant control plane.

Required gates:

1. Pin an upstream commit or immutable image digest; never deploy `latest`.
2. Use a dedicated ACP database and internal service hostname.
3. Put browser and API routes behind the existing DeLoNET access boundary.
4. Do not expose ACP's runtime-harness administration to untrusted networks.
5. Keep provider secrets in DeLoNET LiteLLM; inject only the scoped virtual key.
6. Keep ACP session metadata free of repository secrets and full environment
   dumps.
7. Record command/session correlation in Bloodbank and Candystore.
8. Back up ACP only after its data classification and restore test are defined.
9. Complete a security review before ACP can trigger a permanent fleet profile.
10. Preserve a kill switch that disables the adapter without touching the
    fleet-shared gateway.

OpenNotebook also has a deployment gate: its encryption key and database
credentials must be runtime-injected rather than committed before provider
credentials are stored there. As of this decision, OpenNotebook contains no
configured provider credentials or models, so source custody can begin without
embedding or LLM transformations while that secret debt is resolved.

## Knowledge custody and OpenNotebook

The deterministic project notebook is:

`33GOD - Platform Architecture and Control Plane`

It indexes canonical and upstream evidence, including this decision, the root
PRD, the platform product map, the Bloodbank command contract, the fleet
operations contract, the DeLoNET LiteLLM gateway policy, and the pinned ACP
upstream sources.

Custody rules:

- Git and BMAD artifacts are authoritative.
- OpenNotebook sources carry their original path/URL, revision, and ingestion
  date in the source text or title.
- Re-ingestion is deterministic by notebook name plus source title; operators
  update or supersede sources instead of creating ambiguous duplicates.
- OpenNotebook notes, generated summaries, chats, and insights are research
  outputs. They become decisions only after promotion to Git/BMAD and review.
- Secrets, `.env` files, runtime databases, private logs, and provider tokens
  are never ingested.
- Source processing without embeddings is acceptable while no embedding model
  is configured; this limits semantic search but preserves safe custody.

## Pilot plan

### Stage 0 - BMAD alignment

The `33god-pm` agent owns the BMAD flow. It must:

1. reconcile this decision into the root product brief/PRD/architecture;
2. decide whether ACP is an external integration, a new repository, or a
   component only after the registry gates can be satisfied;
3. define epics and ticket-sized stories across Bloodbank, Holocene, Flume,
   DeLoHQ, LiteLLM, and the ACP adapter;
4. create or update traceable Plane work on the `33GPM` board;
5. record dependencies, owners, acceptance tests, security gates, and rollback;
6. keep Flume described as a planned protocol/product boundary until a real
   repository and contract exist;
7. distinguish the existing HeyMa validation drift from ACP-caused work;
8. commit and push all resulting planning artifacts.

Stage 0 approves work; it does not authorize production deployment or provider
credential duplication.

### Stage 1 - isolated lab

- Deploy the pinned ACP revision with a separate database.
- Use an internal hostname and protected UI/API.
- Create one disposable `acp-lab` runtime/profile.
- Use a scoped DeLoNET LiteLLM virtual key and the `hermes` alias.
- Prove session creation, turn streaming, cancellation, and cleanup.
- Prove ACP shutdown has no effect on existing Hermes services.

### Stage 2 - canonical Bloodbank bridge

- Implement `33god-hermes` as an ACP runtime adapter.
- Validate and publish the canonical invocation command.
- Preserve correlation and idempotency through terminal events.
- Add assistant-message/result transport using a governed Bloodbank contract.
- Persist and query the complete trace in Candystore.
- Exercise duplicate delivery, timeout, cancellation, poison command, and
  gateway restart cases.

### Stage 3 - operator projections

- Add ACP health and session state to Holocene.
- Join ACP session/run data with Candystore correlation history.
- Add approval and exception events.
- Expose only approved status, budget, approval, cancellation, and escalation
  controls in DeLoHQ.

### Stage 4 - Flume execution port

- Map Flume work requests and delegation metadata onto normalized sessions.
- Keep org hierarchy, authority, budget, and escalation decisions in Flume.
- Route permanent employees through registered Hermes targets.
- Allow disposable workers only within explicit capability, workspace, spend,
  depth, and lifetime bounds.

## Acceptance criteria

The pilot is successful only when all of the following are evidenced:

- ACP is pinned, isolated, protected, and removable.
- No provider credential or fallback policy is duplicated outside LiteLLM.
- No permanent project/agent identity is duplicated outside PJangler and the
  fleet registry.
- No canonical PM heartbeat or schedule moves into ACP.
- Each turn produces one schema-valid, idempotent Bloodbank command.
- Target routing occurs only through the fleet-shared gateway.
- Started, completed/failed, assistant message, and turn-terminal events share
  usable correlation identifiers.
- Candystore contains the end-to-end audit trace.
- Holocene shows health and session/run status without scraping runtime files.
- DeLoHQ exposes only its bounded executive controls.
- Hindsight remains the durable memory owner.
- Killing ACP leaves the current fleet fully operational.
- The existing 33GOD platform validation baseline is recorded honestly; ACP
  does not claim to repair unrelated HeyMa drift.
- BMAD artifacts and Plane tickets link back to this decision and to captured
  verification evidence.

## Explicit non-goals

- Replacing Holocene or DeLoHQ with ACP's dashboard.
- Replacing Flume's org/delegation model.
- Replacing PJangler or `.project.json` identity.
- Replacing Bloodbank/Candystore event and audit authority.
- Replacing Hindsight memory.
- Replacing the Pipeline MCP Hub or Skillex.
- Moving model credentials, OAuth sessions, or fallback policy into ACP.
- Registering ACP, Flume, or DeLoHQ as active components before their contracts
  satisfy the registry gate.
- Treating the first lab deployment as hosted-product readiness.

## Evidence

- [LiteLLM Agent Control Plane upstream](https://github.com/LiteLLM-Labs/litellm-agent-control-plane)
- [ACP architecture](https://github.com/LiteLLM-Labs/litellm-agent-control-plane/blob/main/docs/learn/architecture.mdx)
- [ACP runtime SDK contract](https://github.com/LiteLLM-Labs/litellm-agent-control-plane/blob/main/docs/engineering/sdk-api-contract.mdx)
- [ACP Hermes runtime template](https://github.com/LiteLLM-Labs/litellm-agent-control-plane/blob/main/templates/hermes/README.md)
- [DeLoNET LiteLLM gateway policy](https://github.com/delorenj/DeLoContainers/blob/main/stacks/ai/litellm/README.md)
- [Bloodbank Hermes gateway](../../bloodbank/services/hermes-gateway/README.md)
- [Canonical invocation schema](../../bloodbank/schemas/bloodbank/v1/agent/invocation.start.v1.json)
- [Fleet operations contract](../../pjangler/skills/agent-fleet-operations/SKILL.md)
- [33GOD root PRD](../../PRD.md)

The upstream revision named above is the revision inspected for this decision.
BMAD must refresh the pin and re-run the security/contract review before any
implementation or deployment story is marked ready.

# Execution contract v2

Approved direction: Krebs owns deterministic ticket execution; Momo teaches PM behavior; Pilot (`px`) is the agent-facing tool and Plane adapter; PJangler owns canonical `.project.json` bindings and derived indexes; Hermes and interactive hosts own runtime supervision. Bloodbank owns interservice commands/events and Candystore durable event history. Plane is the v1 provider. This document is implementation intent, not a claim of deployed capability.

## Authority and identity

A canonical project_id is distinct from workspace_slug, board_id and provider issue UUID. Manifest bindings declare PM actor, expected native Plane user ID, op:// key reference, runtime adapter, lifecycle mode (legacy/shadow/managed), policy/schema and skill version. No secrets are tracked or persisted in temporary files. Distinct native identities are required for each long-lived PM, interactive Codex/Claude and controller-origin repairs. Verify users/me and board membership; never replace an enrolled actor with a shared key. Temporary workers/reviewers have distinct run IDs with accountable parent actor. Bind requested actor to authenticated command ingress; trusting a payload actor string is insufficient.

One controller authority per managed board. Root PM delegates children to owning component PM; it cannot silently claim their board. Takeover is explicit and audited. Parent completion requires verified child receipts plus its own integration checks. Manifests are canonical, indexes and runtime registry derived. Do not invent a missing board binding.

## State and execution

Exact lanes: Backlog; Needs Re-evaluation; Todo; In Progress; E2E Testing & QA; Ready for Documentation; Done; Needs Attention; Cancelled. Rename Awaiting Decision preserving its UUID where possible. State groups cannot substitute for exact lanes: several lanes share `started`.

Public operations: `px task claim|handoff|complete|attention|resume|release|cancel|takeover|status`, `px run heartbeat|finish`, CRUD including get/comment/update. Existing claim/close aliases must use the same authority on managed boards. Provider-only commands are internal, pinned and cannot recurse through the public lifecycle client. Managed automated CRUD/state/label writes cannot bypass Krebs. Controller unavailability is a hard stop for managed execution.

Default capacity one active execution per board; heartbeat 60s, lease 300s, sweep 60s. Expiry invalidates authority but does not alone free capacity: prove old runtime stopped/parked before replacement. Every command carries command_id, idempotency_key, project_id, ticket_id, actor_id, runtime_id/run_id, attempt generation, expected revision and causation/correlation identifiers as applicable. Store requested/applied identity separately. Persist full commands and durable receipts; repeated key/body returns original receipt, different body conflicts. Old generation outcomes are audit-only.

Use Krebs-owned Postgres schema, transactional capacity acquisition/uniqueness and version/fence predicates on all writes. Durable intent precedes provider mutation. GET readback verifies exact expected state/assignees/labels/comment marker. On ambiguous response reconcile before retry; uncertain create/comment POSTs must not blindly repeat. Persist command result, transitions, provider intents and outbox consistently. Durable command consumer redelivery must be safe. New `bb call` waits for accepted/result receipts and supports operation status; NATS flush/PONG is not acceptance.

Question flow records stable question_id, context and resume state; moves ticket to Needs Attention before presenting when provider is available; revokes mutation authority and parks/stops the worker before freeing capacity. Chat or board answer references question_id, closes it once and reacquires capacity with a new generation. Scope changes invalidate readiness/frozen acceptance. Recoverable failures permit at most three classified retries; dependency waits consume none. Success exit only produces a run outcome, never automatic Done without evidence. Release/cancel/takeover require safe runtime termination semantics.

Evidence is frozen to accepted ticket revision, acceptance profile and current delivered artifact/revision. Require independent spec and quality reviewers distinct from implementer, applicable test/docs/notebook/skill/main/push/deployment receipts. Artifact change invalidates prior reviews. QA then documentation then Done require their respective gates; irrelevant gates must be explicitly inapplicable with reason. Manual Done without adequate evidence becomes Needs Attention; explicit operator override is recorded distinctly. Distinguish own webhook echoes, genuine human changes and obsolete deliveries.

## Transport, migration and rollout

All interservice communication uses Bloodbank canonical command/event types, NATS durable consumption and authenticated publisher/consumer bindings; no ad hoc HTTP control API. Schemas live with Bloodbank and extend its canonical envelope. Provider facts remain existing repo.task events. Krebs state is authoritative for attempts; Plane for ticket content; Candystore for durable event history. Persist enough outbox metadata to retry without losing provenance. No falsely published marker when transport fails.

Keep the existing Bloodbank project-health prototype distinct from ticket execution. Move source to a separate Krebs module with compatibility entrypoints and old database semantics retained; no destructive health-data migrations. Krebs ships one supervised Python/Postgres service with migrations, health/readiness, pinned artifacts and root validation. Pilot may be a pinned Node subprocess provider helper. No lifecycle/ duplicate authority.

Cutover fences old sentinel/tp hooks, n8n dispatch, direct agent:working writers and callback handlers per board, while preserving signed webhook ingress and non-Plane legacy operation. Rollback pauses managed authority; never reactivate dual writers. Shadow must perform no mutations. Canary 33GOD and James Brennan before remaining active Plane PMs. Inventory every eligible PM with source, native identity, memberships (including PX feedback board), key reference, runtime and enrollment/readiness status. Manual key enrollment is accepted; incomplete boards remain explicitly blocked and must not be called rolled out.

Material friction creates an attributed `px idea` with source project/ticket, real actor, Pilot version, attempted command, workaround and desired behavior. Deduplicate repeats and spool failed delivery outside source; feedback failure cannot block ticket completion.

## Proof

Test simultaneous claims, duplicate/body-conflicting commands, wrong identity zero writes, exact lane progression, independent current-artifact gates, question/resume once, crash/restart, expiry with live worker, late callbacks, provider partial writes, own echoes/manual edits, child receipt gating, healthy versus stranded reconciliation, no-op repeat, outbox retry and durable Candystore receipt. Report implementation, fixture tests, shadow and actual fleet proof separately.

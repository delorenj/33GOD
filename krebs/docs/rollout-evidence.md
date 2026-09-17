# Lifecycle rollout evidence — 33GOD-63

This ledger separates implementation from verified runtime activation. Tracking: 33GOD-63 and PJAN-129. The approved behavior is in [execution-contract.md](execution-contract.md); the initial per-PM inventory is in [rollout-inventory-2026-09-16.json](rollout-inventory-2026-09-16.json).

## Initial live observations

Observed during implementation on 2026-09-16/17:

| Check | Observed result | Implication |
|---|---|---|
| Fleet PM roles | 20 total; 17 Bloodbank-enabled | Disabled roles remain visible and excluded from automatic activation |
| Enabled PM manifest board bindings | 14 of 17 | Three need canonical manifest repair before enrollment |
| Missing canonical project IDs | 12 of 20 PM roles | Runtime registry names cannot substitute for project_id |
| James Brennan actor key | `op://DeLoSecrets/Plane/API Keys - Agent Roster/George Carlin` resolves to native user `2d34d5ca-2433-478f-8132-ccb99cec714a`, `george.carlin` | Native identity verified by `/api/v1/users/me/` |
| James Brennan membership | Native user appears in JIMB board members | JIMB access verified without mutations |
| James Brennan feedback access | PX board members returns HTTP 403 under George's key | Feedback access needs enrollment; failed idea delivery must queue |
| Existing Pilot credential resolution in JIMB | `Plane/Main/apiKey`, native user Jarad (`a95d7646-e557-437e-b453-ae82d7f78df7`) | Current legacy wiring does not use the existing PM key |
| Root native PM identity | Not yet enrolled/verified | 33GOD canary activation blocked |
| Interactive Codex, Claude and controller identities | Not yet enrolled/verified | No shared human-key fallback for managed mode |
| NATS JetStream | Existing `BLOODBANK_EVENTS` and `BLOODBANK_COMMANDS` streams | Infrastructure present; new consumer behavior still requires proof |
| Candystore | `/healthz` and `/readyz` return 204; `/events?limit=1` returns structured events | Storage API reachable; lifecycle receipt persistence still requires proof |
| Momo manifest | Empty board ID and no PM binding | Do not invent a Momo board or separate Momo actor |
| TonnyBox | Disabled route; manifest and runtime registry board IDs disagree | Resolve drift before any future activation |

`px whoami` in the baseline only reported credential/board resolution; native identity above was checked against Plane directly. No secret value was printed or written to disk. The bootstrap tracking tickets use the existing configured native account and explicitly record that fact.

## Activation gates

For each board, record independently: canonical manifest valid; native actor and membership verified; source and installed skill versions agree; legacy dispatch, direct label writers and callbacks fenced; controller healthy; exact lane mapping and readback pass; claim/recovery/evidence tests pass; durable event observed in Candystore. A board remains legacy or shadow until all its managed-mode gates pass.

The first managed canaries are 33GOD and James Brennan. Plane key enrollment is manual for this rollout. A missing actor blocks that board, while implementation, fixture verification and read-only shadow checks continue. Rollback pauses authority and drains/parks runs before changing the writer; it must not enable simultaneous legacy and managed writers.

## Verification ledger

- Preserved project-health baseline: 21 tests passed (`test_reconciler.py`, `test_runtime_blockers.py`) before source migration.
- Independent provider boundary checks: 3 passed; wrong native identity and missing membership produced no mutations.
- Real isolated transport: `tests/test_transport_integration.py` passed against disposable Postgres/NATS, exercising the actual Pilot CLI and `bb call`, real Krebs command handling, authenticated Unicode/newline/numeric payloads, duplicate replay with one provider write, and JetStream outbox persistence. Plane and runtime adapters were fixtures; this is not production worker proof.
- Bloodbank `bb verify-envelope` accepted the generated receipt event's canonical naming/envelope.
- Live event transport/storage fixture: event `402d9659-dc1c-4794-b902-82e6c4f14e47`, explicitly marked `fixture=true`, was acknowledged by `BLOODBANK_EVENTS` at stream sequence `2299057` and fetched from Candystore at `/events/402d9659-dc1c-4794-b902-82e6c4f14e47` (HTTP 200). No Plane ticket was created or modified for this probe.

These checks do not establish that the new controller is running in production, any PM is enrolled for managed mode, or any stranded ticket has been repaired. Further implementation and integration checks remain pending.

## Workspace preservation

Initial `git unpushed` found extensive pre-existing workspace state (502 reported repositories/worktrees). This task stages its own paths and preserves unrelated changes, including existing root settings, component changes and journal output. A global dirty report is not evidence that those unrelated edits belong to this implementation.

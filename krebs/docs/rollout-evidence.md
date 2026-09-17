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

## Initial verification ledger (superseded by final results below)

- Preserved project-health baseline: 21 tests passed (`test_reconciler.py`, `test_runtime_blockers.py`) before source migration.
- Independent provider boundary checks: 3 passed; wrong native identity and missing membership produced no mutations.
- Real isolated transport: `tests/test_transport_integration.py` passed against disposable Postgres/NATS, exercising the actual Pilot CLI and `bb call`, real Krebs command handling, authenticated Unicode/newline/numeric payloads, duplicate replay with one provider write, and JetStream outbox persistence. Plane and runtime adapters were fixtures; this is not production worker proof.
- Bloodbank `bb verify-envelope` accepted the generated receipt event's canonical naming/envelope.
- Live event transport/storage fixture: event `402d9659-dc1c-4794-b902-82e6c4f14e47`, explicitly marked `fixture=true`, was acknowledged by `BLOODBANK_EVENTS` at stream sequence `2299057` and fetched from Candystore at `/events/402d9659-dc1c-4794-b902-82e6c4f14e47` (HTTP 200). No Plane ticket was created or modified for this probe.

- Real Pilot HTTP adapter: four integration checks pass against an isolated HTTP server, using the production Node subprocess and Plane client. Verified paginated membership, exact states, native assignment, preserved unrelated labels/assignees, one escaped question comment and zero writes for rejected identity/membership/state bindings. Controller capability changes are under review; final tests will use durable intents.
- Installed Momo: Skillex vendored canonical Momo `9c69b5d` into catalog commit `3a3fc73` (Skillex pin `e2afe8c`). Fresh native Hermes `skill_view` calls for `33god-pm` and `james-brennan-pm` returned the exact canonical entrypoint SHA256 `af9e0d9a5141a207e935bac61aa8a019807d71947da2875f5b1cabb4152e3568` and referenced playbook SHA256 `15b51e3cb0832bfddf6f4d075d972a22044189bfbdeb14ce24c2781e6c39d9da`. These prove native loading, not managed activation; final review fixes will be re-vendored.
- Formal review: blind, edge-case and verification layers completed. Individual verified findings and correction groups are recorded in the implementation spec; corrections are in progress.

These initial checks did not establish production activation or repair of stranded tickets. Final implementation and installation results follow below.

## Canary lane preparation

Both canaries now have exactly the nine required lane names. `Awaiting Decision` was renamed to `Needs Attention` in place: root UUID `ef47899c-a3cd-4cf8-8f70-d5d23bbe7871`, JIMB UUID `9211f33e-3030-4436-98c7-e185fab747ae`. GET readback confirmed unchanged state IDs, groups, defaults and order. The native bootstrap operator `a95d7646-e557-437e-b453-ae82d7f78df7` performed this schema preparation; it is not a managed PM identity. Both roles retain `reconcile.enabled=false`. Their role mappings now use the new name.

## Independent failure-path verification

The root integration suite now runs the actual Controller/Postgres capability path through the Node provider and an isolated HTTP server. It verifies lost PATCH responses, lost question POST responses, a failure between those mutations, controller restart and duplicate replay, then question/resume/delivery/review/QA/documentation/Done progression. A concurrent human scope change during transition revokes authority and cannot produce Done. Direct helper mutation without a durable intent is rejected.

The real Pilot/Bloodbank/NATS test injects null/list/string commands and an authenticated incomplete command before a valid CLI claim; the consumer survives and the receipt/event schemas validate. Three direct configuration checks prove managed ownership outside the project CWD and rejection of malformed or missing ownership configuration.

JIMB role mapping and previously queued PM evidence landed through PR142, merged as `5c5d70bc` after the required `gate` passed. No application source changed in that PR.

## Root integration checks

- Root platform validation reaches an existing unrelated failure: `33god-platform/components/heyma.yaml` refers to missing `/home/delorenj/code/HeyMa/compose.yml`. This task did not alter that component.
- Root documentation drift: 20 checks passed, including Compose semantic validation and Markdown links; one existing failure is incomplete markers in `docs/cli-hook-audit-2026-09-13.md`. This task did not alter that audit.
- Read-only backfill scan: seven guards passed, including the new Momo distribution ownership guard. Existing gitignore-policy drift remains in Holocene and PJangler; those unrelated ignore files were not changed.
- A fresh inventory read still finds 20 PM roles, 17 enabled, 12 missing canonical IDs and zero managed activations.

## Workspace preservation

Initial `git unpushed` found extensive pre-existing workspace state (502 reported repositories/worktrees). This task stages its own paths and preserves unrelated changes, including existing root settings, component changes and journal output. A global dirty report is not evidence that those unrelated edits belong to this implementation.

## Final acceptance and installation — 2026-09-17

All individually triaged adversarial findings were corrected under the approved
contract. The final required gate passed **58/58 with zero skips**, using fresh
disposable PostgreSQL/NATS and real user systemd supervision. Additional suites:
77 n8n behavioral checks, 8 Pilot checks, 52 focused Hermes checks, PJangler
readiness/typecheck, and 21 standalone project-health checks installed outside
this checkout from immutable Git-pinned Krebs. The health compatibility pin is
`4227e0e`; the project-health source is unchanged in final core `2fdd5b8`.

| Artifact | Verified source / result |
|---|---|
| Installed Krebs core | `2fdd5b8369773327c6b3c815efda50a92d4d5eb9` |
| Wheel SHA256 | `3bb1481575f4e4ade92f6da16ecf51926eedd126f14906d4137dac62f34eaab2` |
| Dependency lock SHA256 | `535104e09b5e1d728eeac1f556f20ce123eb8b804c4ed215a7dc2275a64538d0` |
| Pilot | `6fa3757d67a81c6b3fad5669f2ede5f4342bcaee` |
| Pilot bundle SHA256 | `7c421077f6ec26ee3242b12a22dae68a16379b3f372f4d1d285b86ebc208a0d3` |
| Momo | `5d64d25c727618575867e61436012fd110307ab5` |
| Complete Momo bundle SHA256 | `31a1911a135225d0c0a9401a66333ac6b9adf36d86cc4867c45934850d5a1b2e` |
| Bloodbank / Hermes / PJ implementation | `a170335` / `5f972b5` / `cfd1647` |
| Skill catalog / Skillex pin | `a9cb53d` / `5ed208a` |
| JIMB helper projection | PR146, required gate passed; merge `6e63e8a1` |

The immutable release lives at
`~/.local/share/krebs/releases/2fdd5b8369773327c6b3c815efda50a92d4d5eb9`.
Every one of its 25 wheel source files was compared byte-for-byte with Git;
installed-wheel verification and full Pilot/Momo bundle verification passed.
The database reference is `op://DeLoSecrets/Krebs Execution/database_url`.
The additive Krebs schema migration and installed `health` operation passed.
`krebs-execution.service` is loaded, disabled and inactive. Pinned readiness exits
1 with these exact results:

```json
[
  {"project_id":"33god","ready":false,"error":"execution is not enrolled"},
  {"project_id":"james-brennan","ready":false,"error":"execution is not enrolled"}
]
```

Fresh native Hermes `skill_view` calls in both PM profiles successfully loaded
the final entrypoint and managed playbook. Their SHA256 values are respectively
`ddf376f420e0acd1d17ed8ad3157765dd0e997cc54c327963c8882c1d68b9903` and
`81ffadcb7039b81ba5a4198edfd2d12dc7260e1417146199c4553c995e0e672e`.
The complete installed catalog bundle matches the immutable release. Native
Hermes emitted its external-skill symlink trust warning while successfully
loading; this proof does not imply native actor enrollment. Existing uncommitted
Momo delegation edits remain outside the immutable release and are preserved.

PJAN-129 passed QA/documentation and is Done with exact provider readback.
33GOD-63 is Needs Attention, with the remaining native PM/Codex/Claude/controller
key enrollment and JIMB feedback membership request recorded. These tracking
updates used the explicitly identified bootstrap operator, not a managed actor.
No fleet-wide stranded-ticket repair or managed production execution is claimed.
[Activation steps](activation.md) describe the remaining enrollment, shadow,
writer-fence and controlled canary checks.

The final workspace sweep reports 501 dirty/unpushed repositories/worktrees
across the workspace (502 at baseline; concurrent work continued). Task-owned component commits and skill distribution are
pushed; unrelated changes are preserved. Root integration adds the reviewed
component pins and this evidence separately from the installed core revision.

## Enrollment follow-up — supplied PM references

The user supplied George Carlin and Grolf's `op://` references and selected
NewAPI at `api.automaticai.io` for interactive model-provider OAuth. Both Plane
keys were resolved only in process memory and `/api/v1/users/me/` verified:

| Actor | Native ID | Actual board access |
|---|---|---|
| George Carlin | `2d34d5ca-2433-478f-8132-ccb99cec714a` | JIMB membership verified |
| Grolf | `62b4fef6-b0fe-4cd2-bcd7-53737a61feb4` | No root/PX membership in bootstrap-operator readback; root ticket/state/label/member reads return 403 |

A successful project-detail GET under Grolf does not prove usable membership.
The exact references and remaining enrollment steps are in [activation.md](activation.md).

The local NewAPI source (`middleware/auth.go`, `router/relay-router.go`) uses
NewAPI token validation on relay requests. The deployed image reports
`newapi-automaticai:v1.0.0-rc.25`; the local checkout describes the same tag.
Its `ops/sync-claude-token.py` follows the access token owned by Claude Code,
without taking over refresh-token rotation. No Plane/Krebs actor bridge was
found in the inspected routes/operations. No model relay, OAuth refresh, provider
channel change, Plane membership write or managed activation was performed.
Interactive model authentication and native ticket attribution remain separate;
the requested meaning of passthrough is awaiting clarification.

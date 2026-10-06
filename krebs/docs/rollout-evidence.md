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
The architecture decision is explicit: NewAPI OAuth authenticates
model-provider traffic only; native Plane identities and separate `op://`
references provide ticket attribution for interactive Codex, Claude and Kimi
actors. A gateway identity-to-Plane mapping is out of scope.

## Re-verification 2026-10-06

Read-only checks on 2026-10-06. Plane keys were resolved in process with
`op read` and sent only as request headers; no secret value was printed or
written. Nothing was written to Plane, Postgres, NATS, systemd or any manifest.
The sections above stay as recorded; this section lists what they no longer
describe and what has been observed since.

### Superseded

| Recorded (2026-09-17) | Observed 2026-10-06 | Source |
|---|---|---|
| Grolf is `62b4fef6-b0fe-4cd2-bcd7-53737a61feb4`; root member, state, label and issue reads return 403 | The Grolf roster reference resolves to `db1ac9dc-6180-47d0-aa87-e1bf46d10707` (jaradd+grolf, created 2026-09-17 11:30 UTC). It is an active project member of 33GOD, PX, BB, DECK, GENESIS, HERPM, HEYMA, HOLOC, HOLYF, MOMO, PJAN, SIDE and the archived CNDY, and gets 403 on JIMB members. `62b4fef6` (grolf@delo.sh) has an inactive 33god workspace membership, no project membership, and an API token last used 2026-09-17 11:10 UTC | `GET /api/v1/users/me/` per key; 33GOD and PX `members/`; Grolf `GET /workspaces/33god/projects/` (`is_member`); read-only Plane ORM query of WorkspaceMember, ProjectMember and APIToken `last_used` |
| Root native PM identity not yet enrolled | Two candidates exist. Besides Grolf `db1ac9dc`, the agent-registry row `33god-pm` uses `op://DeLoSecrets/Plane Agent 33god-pm/apiKey`, which resolves to `b29eaffc-cc8d-4de1-a10b-7425c67177ab` (33god-pm@delo.sh, created 2026-09-20). It is an active 33god workspace member with no project membership and gets 403 on 33GOD and PX issue reads. 33GOD and PX members are exactly Grolf `db1ac9dc` and Jarad `a95d7646` | `~/.hermes/agents-registry.yaml` (`33god-pm.plane`); `users/me`; issue GETs as `b29eaffc`; ORM query |
| Both PM roles retain `reconcile.enabled=false` | 33GOD `agents/hermes/pm/role.yaml` has `reconcile.enabled: true` and `explicit_opt_out: false` since `8a4e7fd` (2026-09-23, migrated to the template default). JIMB still has `false` | Both `role.yaml` files; `git show 8a4e7fd` |
| The PM heartbeat drives `managed-execution.py` (lease renewal and planner) | Per-agent heartbeat timers were retired on 2026-09-17 (hermes-agent-template `63466a8`); 28 unit files for 14 agents are archived in `~/.hermes/retired-units-20260917T091432Z`. FLUME-15 (flume `827ac7b`, merged `c48ee02` on 2026-10-05) retired the handbook requirement. No heartbeat timer or unit is installed, and `heartbeat.sh:86` is the only caller of `managed-execution.py`, so nothing renews 300 s leases or runs the planner | `git show`; archive listing; `systemctl --user list-timers --all` and `list-unit-files`; `rg managed-execution.py flume/templates` |
| Candystore fixture event `402d9659-dc1c-4794-b902-82e6c4f14e47` returns HTTP 200 | HTTP 404 (retention). `/healthz` and `/readyz` return 204. The receipt gate must be proved again at canary time | `curl 127.0.0.1:8683` |
| Release Pilot `6fa3757` and Momo `5d64d25` are the current sources | Pilot checkout HEAD `8e02b20` is 20 commits ahead; `7a49409`, `1bc8a13` and `ddf55e2` are not in the pin. Bundle digests: release Pilot `7c421077…`, checkout `e4b45cf4…`; release Momo `31a1911a…`, Skillex catalog `cb02f43c…` (Skillex `a855e57`, re-vendored at momo `8d110b0` on 2026-10-01), momo HEAD `4029c34` `f1d4a8bb…`. Both canaries' `.agents/skills/momo` resolve to the catalog | `release.json`; artifacts `release-input.json`; `git merge-base --is-ancestor`; `krebs.bundles.bundle_digest` in the release venv |
| Root validation fails on missing `/home/delorenj/code/HeyMa/compose.yml`; docs drift fails on markers in `docs/cli-hook-audit-2026-09-13.md` | HeyMa deleted `compose.yml` in `1d21e8b` (2026-07-25) and now runs as systemd user units, so `heyma.yaml` lists no compose file. The audit markers were fixed in `3a8a447` (2026-09-23) | HeyMa `git log`; `platform.py validate`; `scripts/check-doc-drift.py` |
| `spec/execution-command.v2.schema.json` lists the command operations | It listed 17. `contract.py` OPERATIONS and Bloodbank `lifecycle/task.invoke.json` list 22 (adding plan, reevaluate, override, reconcile and planner). The spec now matches `contract.py`; nothing validates against the spec file | `contract.py:9-11`; `task.invoke.json` enum; `rg execution-command` |

### Unchanged

- George Carlin's reference resolves to `2d34d5ca-2433-478f-8132-ccb99cec714a`.
  JIMB members are George, damian `36dce2c2` and Jarad `a95d7646`; George gets
  403 on PX members.
- `verify_release` passes. Pinned readiness, run with
  `PYTHONDONTWRITEBYTECODE=1` (no `.pyc` written), exits 1 with
  `[{"error":"execution is not enrolled","project_id":"33god","ready":false},{"error":"execution is not enrolled","project_id":"james-brennan","ready":false}]`.
- `git diff 2fdd5b8..HEAD -- krebs/src krebs/ops krebs/pyproject.toml krebs/uv.lock`
  is empty. `krebs-execution.service` is disabled and inactive.

### New observations

- All 37 Hermes profiles set
  `secrets.onepassword.env.PLANE_API_KEY=op://DeLoSecrets/Plane/Main/AutomaticAI API Token`,
  which resolves to Jarad `a95d7646`. Even the enrolled PMs run on the shared
  key. Source: `~/.hermes/profiles/*/config.yaml`; `users/me`.
- Krebs DB: Postgres 17.10. The `krebs` schema has 7 tables (boards, commands,
  history, intents, outbox, provider_steps, reviews), all with 0 rows, and
  `outbox.sequence` exists (migration 003). Source: read-only transaction
  through the release venv.
- NATS: `BLOODBANK_COMMANDS` (`bloodbank.cmd.>` and `bloodbank.rpy.>`,
  workqueue) has one consumer, `bloodbank-hermes-gateway`, filtering
  `bloodbank.cmd.agent.invocation.start`. `BLOODBANK_EVENTS` (`bloodbank.evt.>`)
  has `candystore-events`. `krebs-execution-v2` does not exist yet; `serve`
  creates it. Source: JetStream `stream_info` and `consumers_info`.
- The fences are open:
  - `KREBS_FENCED_BOARDS` is absent from every n8n process environment, and the
    Ticket Pickup Chip treats an unset value as `[]`. Source: `/proc/<pid>/environ`
    key check; `bloodbank/integrations/n8n-workflows/ticket-pickup-chip.v1.json`.
  - The Fleet node checks the fence only `if (route.projectPath)`, and
    `executionMode()` returns `legacy` on any read error. Source:
    `Fleet.node.ts:95-102,512`.
  - Dev Journal `process-report.js:129,192,212` POSTs comments and issues and
    PATCHes Done, with no mode check.
  - jimb-api `apps/project-room/server/plane.mjs` POSTs `/work-items/` with
    `labels` and `module`.
  - `legacy_writers_fenced` is only compared to `true` (`readiness.py:22`,
    `controller.py:40`).
- Shadow semantics: `boardMode()` treats any non-legacy mode as managed (pilot
  `src/surface.js:27-28`); `Plane.request()` refuses non-GET requests
  (`src/plane.js:52`); `loadConfig` requires an enrolled actor
  (`src/config.js:158-162`); the controller refuses everything except
  `status`/`get` unless the mode is managed (`controller.py:21`).
- Cohort: `launch.py:35` sets `KREBS_MANIFESTS` from the release. Readiness runs
  the full `validate_binding` and a live verify for every listed manifest
  regardless of mode (`service.py:106-120`), while PJangler accepts incomplete
  shadow bindings (`executionBinding.ts:28-35`).
- Capacity: one `state['active']` per board, with lease `now+300`
  (`contract.py:93`) and `review_until` `now+1800` after finish
  (`contract.py:142`).

The rollout plan, including the open decisions, is Flume Epic 6 in
[`flume/_bmad-output/planning-artifacts/epics.md`](../../flume/_bmad-output/planning-artifacts/epics.md).
The current runbook is [activation.md](activation.md).

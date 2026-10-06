# Managed execution activation

State on 2026-10-06: no board is in shadow or managed mode. The installed release
is `~/.local/share/krebs/releases/2fdd5b8369773327c6b3c815efda50a92d4d5eb9`;
`krebs-execution.service` is loaded, disabled and inactive. `verify_release`
passes and pinned readiness exits 1 with `execution is not enrolled` for both
cohort manifests (33GOD, james-brennan). The database
(`op://DeLoSecrets/Krebs Execution/database_url`, Postgres 17.10) has the `krebs`
schema with migrations 001-003 applied and every table empty. NATS
`BLOODBANK_COMMANDS` and `BLOODBANK_EVENTS` exist; the durable consumer
`krebs-execution-v2` is created on first serve.

The rollout plan is Flume Epic 6, "Migrate legacy boards to Krebs-managed
execution", in
[`flume/_bmad-output/planning-artifacts/epics.md`](../../flume/_bmad-output/planning-artifacts/epics.md),
tracked as tickets on the FLUME board. Evidence for everything below is in
[rollout-evidence.md](rollout-evidence.md#re-verification-2026-10-06).

## Identities

| Actor | Key reference | Native user | Board access |
|---|---|---|---|
| Grolf (33GOD PM candidate) | `op://DeLoSecrets/Plane/API Keys - Agent Roster/Grolf` | `db1ac9dc-6180-47d0-aa87-e1bf46d10707` (jaradd+grolf, created 2026-09-17) | Member of 33GOD and PX, also BB, DECK, GENESIS, HERPM, HEYMA, HOLOC, HOLYF, MOMO, PJAN, SIDE; 403 on JIMB |
| Registry row `33god-pm` (33GOD PM candidate) | `op://DeLoSecrets/Plane Agent 33god-pm/apiKey` | `b29eaffc-cc8d-4de1-a10b-7425c67177ab` (33god-pm@delo.sh, created 2026-09-20) | 33god workspace member; member of neither 33GOD nor PX (403 on issue reads) |
| George Carlin (James Brennan PM) | `op://DeLoSecrets/Plane/API Keys - Agent Roster/George Carlin` | `2d34d5ca-2433-478f-8132-ccb99cec714a` | JIMB member; 403 on PX |
| Controller (operator) | none | none | none |
| Interactive Codex, Claude, Kimi | none | none | none |

- `62b4fef6-b0fe-4cd2-bcd7-53737a61feb4` (grolf@delo.sh), recorded here on
  2026-09-17, is stale: its workspace membership is inactive, it has no project
  membership, and its token was last used on 2026-09-17. Do not bind it.
- Which identity is the 33GOD `pm_actor` is an open decision recorded in the epic.
- All 37 Hermes profiles set
  `PLANE_API_KEY=op://DeLoSecrets/Plane/Main/AutomaticAI API Token`, which
  resolves to Jarad (`a95d7646-e557-437e-b453-ae82d7f78df7`). Every PM, enrolled
  or not, writes to Plane as Jarad today.
- NewAPI OAuth at `api.automaticai.io` authenticates model-provider traffic only.
  It is not a Plane/Krebs actor; interactive CLIs need their own native Plane users.

## Open blockers

1. **No lease or planner driver.** Leases last 300 s, and `sweep()` then expires
   the attempt, stops the worker and moves the ticket to Needs Attention. Only
   Flume's `managed-execution.py` renews leases (`px run heartbeat`) and runs the
   PM planner (`px run planner`), and only `heartbeat.sh` calls it. Per-agent
   heartbeat timers were retired on 2026-09-17 (hermes-agent-template `63466a8`;
   28 unit files for 14 agents archived to
   `~/.hermes/retired-units-20260917T091432Z`), and FLUME-15 (flume `827ac7b`,
   merged `c48ee02`, 2026-10-05) retired the handbook requirement. Nothing
   schedules either today, and no production `planner_argv` exists.
2. **Missing identities.** No controller (operator) or interactive actor exists,
   and readiness requires an `operator` controller on every board. Nothing sets
   `PILOT_ACTOR_ID` for PM gateways or interactive shells.
3. **Planner flag.** The 33GOD PM `role.yaml` has had `reconcile.enabled: true`
   since `8a4e7fd` (2026-09-23, the template default); JIMB has `false`. This
   contradicts the earlier guidance to keep planning off until its writer exists.
   `heartbeat.sh` passes the flag as `KREBS_PLANNER_ENABLED`; with no heartbeat it
   has no effect today.
4. **Stale release pins.** The release pins Pilot `6fa3757` (bundle `7c421077…`).
   The Pilot checkout is 20 commits ahead, and the pin lacks `ddf55e2`
   (digit-leading refs such as `33GOD-NN` in the managed regexes) and `1bc8a13`
   (label and assignee deltas on a fresh read in `provider-helper.js`). Momo is
   pinned at `31a1911a…` (`5d64d25`). The canaries' `.agents/skills/momo` symlinks
   to the Skillex catalog, now `cb02f43c…` (vendored at `8d110b0`); Momo HEAD is
   `f1d4a8bb…` (`4029c34`). Readiness compares each manifest's
   `momo_bundle_sha256` with the installed `<repo>/.agents/skills/momo` digest and
   its `pilot_bundle_sha256` with the release's Pilot, so a new release is needed,
   and every Pilot bump or catalog re-vendor needs a re-pin.
5. **Open fences.** `legacy_writers_fenced` is self-attested: readiness and the
   controller only check that it is `true`, and no code verifies a fence.
   - The Ticket Pickup Chip and its stale-chip sweep fence only through
     `$env.KREBS_FENCED_BOARDS`, which is unset in the pm2 n8n environment, so
     they fail open.
   - The n8n Fleet node skips the fence when a registry row has no
     `project_path`, and treats an unreadable manifest as legacy.
   - Dev Journal POSTs issues and comments and PATCHes Done on 33god-workspace
     boards, 33GOD included, with no mode check.
   - jimb-api (`james-brennan/apps/project-room/server/plane.mjs`) POSTs JIMB
     work items with a label and a module directly.
   - Raw Plane API use with the shared key is unfenced.
6. **Shadow is a write freeze, not observation.** px treats shadow as managed:
   every command, reads included, needs an enrolled actor, and px refuses
   non-GET Plane requests. The controller refuses everything except
   `status`/`get` unless the mode is `managed`, and those answer only while the
   service runs.
7. **The cohort is fixed in the release.** `release.json` `manifests` is the
   activation cohort. Readiness runs as ExecStartPre (with `Restart=on-failure`)
   and is all-or-nothing: it validates every listed manifest fully, in either
   mode. A new board needs a new release, a unit rewrite by `install.py` and a
   restart, which is a hard stop for every managed board. Mode and binding edits
   on an already-listed board take effect live, except `pilot_bundle_sha256`,
   which must equal the release's Pilot.
8. **Capacity.** Each board has one active execution. After `finish`,
   `review_until` is finish + 1800 s, so a ticket must clear review, QA and
   documentation within 30 minutes or its lease expires to Needs Attention.

## Activation sequence

Per board, once the blockers above are cleared:

1. Cut a new release with current Pilot and the chosen Momo pin
   ([ops/README.md](../ops/README.md)). Its cohort is exactly the boards being
   enrolled.
2. Populate the canonical `.project.json` execution binding per
   [the contract](execution-contract.md): policy version 2, exact state UUIDs for
   all nine lanes, the `agent:working` label, PM and operator actors with unique
   native identities, `op://` key references, runtime IDs, systemd prefixes, the
   PM `planner_argv`, and the new release's Pilot and Momo digests. Readiness
   rejects an incomplete binding in shadow as well as managed.
3. Prove every legacy writer fenced for that board before recording
   `legacy_writers_fenced: true`.
4. Run `RELEASE_DIR/venv/bin/python -m krebs.launch RELEASE_DIR/release.json
   --readiness` until every cohort board passes.
5. Enter shadow only with the service running, and keep the window short; select
   managed once enrollment, lanes, runtime and fences pass.
6. Exercise one controlled canary ticket through claim, start,
   question/Attention, answer/new generation, delivery, independent reviews, QA,
   documentation and Done. Verify Plane readback, actual actor provenance and a
   Candystore receipt. The 2026-09-17 fixture event now returns 404, so the
   receipt gate must be proved again. Repeat crash/lease recovery before
   enrolling more boards.

Rollback pauses managed execution and proves workers stopped before another
writer is allowed. Do not remove enrollment or enable legacy dispatch while a
managed worker can still mutate. Uncertain provider writes are reconciled by
readback; they are never blindly retried.

The 2026-09-16 inventory (20 PM roles) is historical; the agent registry now
lists 25 PM rows. Repair each binding in its owning repository; do not infer
board ownership from a runtime registry alias.

# Execution v2 operations

The supported supervisor is the host's user systemd manager. Build the release
wheel with `uv build` and export locked runtime dependencies with
`uv export --frozen --no-dev --no-emit-project --format requirements-txt`.
Stage the wheel, requirements file, committed Pilot bundle and committed Momo
skill bundle in immutable release paths. Do not bind a mutable working tree.

`python3 ops/install.py release.json --destination RELEASE_DIRECTORY` validates
all inputs before writing, installs the hash-locked dependencies and wheel into
a fresh venv, and generates the user systemd unit with those exact paths.
Installation does not activate the service. The descriptor contains:

- `wheel`, `wheel_sha256`, `requirements`, `requirements_sha256`;
- `source_revision` (40 lowercase hex), `pilot_root`, `pilot_bundle_sha256`;
- `momo_root`, `momo_bundle_sha256`, and `manifests` (canonical manifest paths);
- `environment`: `KREBS_DATABASE_URL`, `NATS_URL`, optional `NATS_TOKEN`, and any
  required runtime variables. Secret values must be `op://` references.

The generated ExecStartPre validates installed wheel bytes, full Pilot/Momo
bundle digests, enrolled native identities, exact lanes, runtime systemd access
and writer fences. `krebs.launch` resolves vault references only into the child
process environment, repeats readiness at launch, then executes the service.
Use the readiness argv printed by the installer before activation. Source
includes no mutable-checkout example unit and no plaintext environment file.

Run `krebs migrate` explicitly against the selected database. Migrations touch
only the `krebs` schema; the existing project-health tables are unchanged. Run
`krebs readiness`, `krebs health`, then start `krebs serve`. Bloodbank streams must
cover `bloodbank.cmd.>` and `bloodbank.evt.>`; durable consumer is
`krebs-execution-v2`. Request/reply is `lifecycle.task.invoke`, events are
`lifecycle.receipt.recorded`, schema revision2. Receipts and full commands persist
in Postgres; retry uses the exact original command body and ID.

A pending provider intent holds capacity. `krebs reconcile` reads back exact
provider state before any mutation, and never repeats a previously sent uncertain
POST. Manual investigation must resolve a mismatched uncertain intent; do not
clear pending or delete the board row to unblock a worker. Outbox publication
uses persisted monotonic outbox sequence for new receipts and requires a JetStream acknowledgement;
historical rows receive a stable migration order because original insertion order
was not retained; Candystore observation is separately
verified deployment evidence.

Canonical manifest `execution` fields: mode (`legacy`, `shadow`, `managed`),
policy_version2, skill_version(released version), pilot_bundle_sha256, momo_bundle_sha256, pm_actor, controller_actor, actors keyed by
actor ID, exact states name-to-UUID map, working_label, legacy_writers_fenced.
Each actor declares native_user_id, key_ref(op reference), role(pm/operator or
reviewer/interactive), runtime_id, and runtime {adapter:systemd, unit_prefix}.
The owning PM runtime also declares planner_argv for its installed Hermes/Momo
planning invocation. The heartbeat honors reconcile.enabled=false as a planning
pause while continuing valid active lease maintenance. Unique native
identities are required; interactive Codex/Claude are separate actors. Readiness
must verify source/installed skill and runtime writer inventory before setting
legacy_writers_fenced. PJangler rejects incomplete managed bindings; shadow
bindings can remain incomplete and make no writes.

Rollback sets mode to shadow and stops new execution. Terminate/prove existing
workers stopped before retiring authority. Keep legacy writers fenced until a
separate, explicit migration reassigns ownership. Never enable both authorities.

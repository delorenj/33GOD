# Execution v2 operations

The supported supervisor is the host's user systemd manager. Package `krebs` with
`uv sync --frozen`; package Pilot separately and set `KREBS_PILOT_HELPER` to the
verified immutable helper. Configuration is process environment:

- `KREBS_DATABASE_URL`: resolve from environment or 1Password at service launch.
- `KREBS_MANIFESTS`: JSON array of canonical `.project.json` paths.
- `KREBS_PILOT_HELPER`: absolute path to the pinned Pilot provider helper.
- `NATS_URL`, optional `NATS_TOKEN`: authenticated Bloodbank broker binding.

Never store literal secrets in the environment file: use a supervisor launch
resolver with op references. The example unit describes process ownership and
requires that launch integration before installation. It is not deployed by the
source implementation.

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
requires a JetStream acknowledgement; Candystore observation is separately
verified deployment evidence.

Canonical manifest `execution` fields: mode (`legacy`, `shadow`, `managed`),
policy_version2, skill_version(SHA256), pm_actor, controller_actor, actors keyed by
actor ID, exact states name-to-UUID map, working_label, legacy_writers_fenced.
Each actor declares native_user_id, key_ref(op reference), role(pm/operator or
reviewer), runtime_id, and runtime {adapter:systemd, unit_prefix}. Unique native
identities are required; interactive Codex/Claude are separate actors. Readiness
must verify source/installed skill and runtime writer inventory before setting
legacy_writers_fenced. PJangler rejects incomplete managed bindings; shadow
bindings can remain incomplete and make no writes.

Rollback sets mode to shadow and stops new execution. Terminate/prove existing
workers stopped before retiring authority. Keep legacy writers fenced until a
separate, explicit migration reassigns ownership. Never enable both authorities.

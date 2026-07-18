# Lifecycle client — authoritative reads and canonical commands

`scripts/lifecycle_client.py` is Momo's implemented policy-client seam. It reads
Candystore's Lifecycle projection with `GET`, selects only current
authority-returned frontier items and pending obligations, preserves canonical
`skill_ref` values, and publishes commands through Bloodbank. It has no
Lifecycle, Candystore, provider, database, or local-state write path.

## Read the current projection

```bash
python3 <skill_dir>/scripts/lifecycle_client.py fetch \
  --candystore-url http://127.0.0.1:8683 \
  --lifecycle-id "$LIFECYCLE_ID" > snapshot.json
```

The client fails closed unless `projection_status` is `current` and frontier
items carry the same `expected_state_version` as the snapshot. Missing and stale
projections are never treated as empty legal work.

## Service an obligation

```bash
python3 <skill_dir>/scripts/lifecycle_client.py plan-obligation \
  --snapshot snapshot.json \
  --target-agent independent-reviewer \
  --actor-id momo \
  --requested-at 2026-07-18T12:00:00Z \
  --correlation-id "$CORRELATION_ID" \
  --causation-id "$SNAPSHOT_EVENT_ID" > obligation-plan.json

jq '.invocation_command' obligation-plan.json > invocation-command.json
python3 <skill_dir>/scripts/lifecycle_client.py publish \
  --envelope invocation-command.json
```

The invocation context contains the exact Lifecycle `skill_ref` and the
completion evidence fields (`lifecycle_id`, `obligation_id`,
`obligation_satisfied`) the worker must return in its canonical completion
event. Non-pending obligations and snapshots with no current legal frontier are
not invoked.

## Submit a legal Lifecycle intent after evidence

Refetch after the evidence event is committed. Select only a frontier item from
that refreshed snapshot, then build and publish the command:

```bash
python3 <skill_dir>/scripts/lifecycle_client.py plan-intent \
  --snapshot refreshed-snapshot.json \
  --frontier-id transition:waiting:active \
  --capability-version 1 \
  --evidence review-evidence.json \
  --actor-id momo \
  --requested-at 2026-07-18T12:10:00Z \
  --correlation-id "$CORRELATION_ID" \
  --causation-id "$EVIDENCE_EVENT_ID" > intent-plan.json

jq '.lifecycle_command' intent-plan.json > lifecycle-command.json
python3 <skill_dir>/scripts/lifecycle_client.py publish \
  --envelope lifecycle-command.json
```

Bloodbank v1 requires `capability_version` in command context; supply the exact
issued grant version (the current bootstrap grant is version `1`). The client
matches all other grant fields against the authoritative projection and never
guesses a missing grant.

Wait for Candystore's stable command verdict and refetch the projection. Only a
reply whose event ID, command ID, idempotency key, lifecycle ID, and expected
version match—and whose verdict is `applied` or `idempotent`—passes
`verify_command_verdict`. Never update provider or local lifecycle state in
response to a button, plan, publish acknowledgment, or decision event.

## Keep judgment separate

The plan returns `decision_rationale` beside the command, not inside the
state-changing Lifecycle intent. Record consequential judgment with
`record-decision.py`; that event explains selection and cannot enact a
transition.

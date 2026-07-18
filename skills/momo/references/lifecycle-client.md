# Lifecycle client — authoritative reads and canonical commands

`scripts/lifecycle_client.py` is Momo's implemented policy-client seam. It reads
Candystore's Lifecycle projection with `GET`, selects only current
authority-returned frontier items and pending obligations, preserves canonical
`skill_ref` and `capability_version` values, and publishes commands/events
through Bloodbank. It has no
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
  --actor-id momo \
  --parameters review-parameters.json > obligation-plan.json

jq '.invocation_command' obligation-plan.json > invocation-command.json
python3 <skill_dir>/scripts/lifecycle_client.py publish \
  --envelope invocation-command.json
```

The obligation itself is the legal actor-work contract; an unrelated frontier
transition is never treated as authorization. Lifecycle supplies the target
actor in `owner_id` and the exact `skill_ref`. The invocation context describes
the separate completion-evidence contract. The invocation/request is not
satisfaction and cannot unlock Lifecycle progression.

After the target actor produces a concrete completion artifact, build and
publish the canonical completion event:

```bash
python3 <skill_dir>/scripts/lifecycle_client.py complete-obligation \
  --invocation-plan obligation-plan.json \
  --completed-at 2026-07-18T12:10:00Z \
  --evidence completion-evidence.json > completion-plan.json

jq '.completion_evidence' completion-plan.json > completion-event.json
python3 <skill_dir>/scripts/lifecycle_client.py publish \
  --envelope completion-event.json
```

Completion evidence requires `kind=skill_completion`, `outcome=completed`, an
artifact identity, lowercase SHA-256, and a concise summary. Lifecycle alone
evaluates that observation and decides whether the obligation is satisfied.

## Submit a legal Lifecycle intent after evidence

Refetch after the evidence event is committed. Select only a frontier item from
that refreshed snapshot, then build and publish the command:

```bash
python3 <skill_dir>/scripts/lifecycle_client.py plan-intent \
  --snapshot refreshed-snapshot.json \
  --frontier-id transition:waiting:active \
  --evidence review-evidence.json \
  --actor-id momo > intent-plan.json

jq '.lifecycle_command' intent-plan.json > lifecycle-command.json
python3 <skill_dir>/scripts/lifecycle_client.py publish \
  --envelope lifecycle-command.json
```

Bloodbank requires `capability_version` in command context. The client derives
it from the exact current authority grant in the projection; a missing or
invalid version fails closed. There is no caller default or fallback.

Wait for Candystore's stable command verdict and refetch the projection. The
verdict gate verifies the exact Bloodbank reply subject/type/schema/kind,
Lifecycle authority source/producer/service/actor, complete causal and command
identity, repository/lifecycle/version/capability identity, and internally
consistent verdict fields. Only `applied` or `idempotent` passes. Never update
provider or local lifecycle state in response to a plan, publish acknowledgment,
or decision event.

Invocation and intent IDs, command IDs, correlation/causation IDs, and
idempotency keys are derived from canonical immutable request semantics. The
authoritative projection event time is preserved as the command timestamp, so
an identical retry reproduces the exact envelope while any material payload
change produces a new identity.

## Keep judgment separate

The plan returns `decision_rationale` beside the command, not inside the
state-changing Lifecycle intent. Record consequential judgment with
`record-decision.py`; that event explains selection and cannot enact a
transition.

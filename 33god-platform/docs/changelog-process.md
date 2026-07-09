# Pipeline Changelog Process

Add a pipeline changelog entry when a change affects another component, agent
config, template, hook, schema, or deployment boundary.

## Required files

1. Append one JSON object to `changes/YYYY-MM-DD-<slug>.jsonl`.
2. Add the human summary to `CHANGELOG.pipeline.md`.
3. Add or update a backfill check if old repos/configs can drift.
4. Update `skills/33god-hub/` if agent routing changes.

## Machine fields

- `id`: stable change id.
- `date`: `YYYY-MM-DD`.
- `component`: component that owns the change.
- `kind`: `contract.changed`, `platform.added`, `runtime.changed`, etc.
- `summary`: one sentence.
- `affects`: component ids.
- `required_backfills`: backfill ids or empty list.
- `docs`: changed reference docs.

Run:

```bash
python3 scripts/platform.py validate
```

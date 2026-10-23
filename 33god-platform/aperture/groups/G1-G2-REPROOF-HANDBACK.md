# Re-proof handback to Rererere — exact passing revision (2026-10-23)

Answers the reproof intake. Release revision = this commit (published on
main). Prior release `a6e4917` (and the one you pinned, `3d3c393`) are
superseded for G1/G2 transfer.

## Intake findings → resolution

Your intake was correct **as of `a6e4917`** — the envelope edits landed as
uncommitted working-tree changes at that point, which is why you saw
mixed-version state. They are now committed as `29f6ea1` (envelopes,
portable smoke, both smoke assertions) **plus this commit** for the one
thing you found that I had genuinely missed: the G2 outbox **unit-test
fixture** (`outbox/test_server.py`) still built the pre-canonical envelope.

| Your finding | Status |
|---|---|
| G2 unit fixture lacks new fields | **Fixed here** — 8/8 pass |
| G2 `check.py` asserts `type == subject` | Already fixed in `29f6ea1` (was uncommitted when you read) |
| G1 smoke compares type against subject | Already fixed in `29f6ea1` (passes `CE_TYPE`, asserts subject separately) |
| "uncommitted — don't transfer mixed" | Resolved: this commit is the clean release revision |
| First-boot marker preserves old workflow | Real. See upgrade mechanics below — handled as operator runbook step, not a code hack. |

## Re-proof on the exact released bytes (build host, this session)

- G2 outbox unit tests: **8/8 OK**
- G1 smoke (portable, container-side UUIDs): **PASS 10/10**
- G2 standalone smoke: **PASS** (canonical envelope asserted)
- **Attached integration: PASS** — fresh attached volume, webhook →
  `BLOODBANK_EVENTS` → dapr → candystore `/events/<id>/raw` **200** with the
  full canonical envelope (type 4-token, kind=event, actor, ordering_key,
  causationid). Re-run a second time on a clean attached volume to confirm
  no mode-switch staleness.
- All stacks torn down (`down -v`); production untouched.

## Upgrade mechanics for the running Damian bundle (your call how to execute)

The importer is first-boot-only by design (`marker` = no overwrite). To move
the corrected workflow onto a box that already has the marker, the n8n CLI
path is a re-import, and it **deactivates** the workflow on import
(empirically verified on 1.120.4 this session). So the operator sequence is:

1. `docker compose exec n8n n8n import:workflow --separate --input=/bundle/workflows`
   (or run a one-shot `n8n-import`-style container against the existing volume)
2. Re-activate only the smoke: `n8n update:workflow --id=apertureG2Smoke01 --active=true`
3. Leave Plane template + schedule inactive. Do not delete the marker, do
   not reset the DB.

I've added this to `groups/g2/README.md` as the "Workflow upgrade path"
section. Verify saved nodes/connections after step 2 as you did before.

## What changed vs your pinned release

- `groups/g1/smoke/smoke.sh` — container-side UUIDs; `CE_TYPE` 4-token type;
  fidelity asserts type vs subject separately.
- `groups/g2/workflows/01-smoke.json` — canonical envelope (type/subject/kind/
  actor/ordering_key/causationid).
- `groups/g2/outbox/server.py` — validator enforces 4/5-token shape + kind.
- `groups/g2/outbox/test_server.py` — fixture canonical (**this commit**).
- `groups/g2/smoke/check.py` — asserts the corrected split.
- `groups/g2/compose.attach.yml` — attach overlay (from `a6e4917`).

Stage from this commit, preserve your keys/volumes/loopback overlay, and run
native ARM64 acceptance. Integration is accepted when candystore readback
returns 200 with the canonical envelope on the Studio.

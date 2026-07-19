# Decisions as Bloodbank events

There is no built-in hook that fires when an agent makes a decision, so Momo fires one
itself. Every consequential judgment call becomes a canonical Bloodbank **decision event**
carrying the decision, the **pillars it rests on**, and the reasoning. This is what makes
Momo's autonomy auditable — the operator (and Hermes, and dashboards) can query *why* Momo
did what it did.

**Authority limit:** a decision event records business reasoning only. It does
not legalize an action, satisfy an obligation, validate a capability, or write
lifecycle state. State-changing intent uses the separate versioned/idempotent
Lifecycle command contract.

## The mechanism

```bash
python3 <skill_dir>/scripts/record-decision.py \
  --decision "<one-line decision>" \
  --basis "<pillar-slug>" [--basis "<pillar-slug>" ...] \
  --reasoning "<why: the tradeoff, what you rejected>" \
  [--issue <TICKET-KEY>] [--actor momo] [--dry-run] [--local-only]
```

The script (repo-agnostic; resolves the slug from `.project.json`):

1. **Always** appends the full CloudEvents envelope to the durable local trail
   `<repo>/_bmad-output/implementation-artifacts/bloodbank-events.jsonl` — the same spool
   the Hermes sentinel reads. A decision is never lost even if the bus is down.
2. **Best-effort** publishes to the live Bloodbank bus (NATS v3) on subject
   `bloodbank.evt.v1.repo.decision.recorded` via bloodbank's stdlib publisher. If NATS is
   unreachable it warns and exits 3 (decision safe in the trail; bus is behind) — it does
   not fail the decision.

Use `--dry-run` to inspect the envelope without emitting; `--local-only` when the bus is
knowingly offline.

## The contract (get this exactly right)

- **CloudEvents `type` = `bloodbank.v1.repo.decision.recorded`** — exactly 5 dotted tokens.
  The repo slug goes in **`data.repo`**, NEVER in the type. The 6-token form
  `bloodbank.v1.repo.<repo>.decision.recorded` is INVALID — it fails the contract regex and
  the entity allowlist and will be rejected by the bus validator.
- **NATS subject** = the type with the `evt` kind-marker inserted:
  `bloodbank.evt.v1.repo.decision.recorded`. The script derives both from one constant, so
  they can never drift.
- **`data`** (schema: repo + decision required; `additionalProperties: true`):
  - `repo` — the project slug.
  - `decision` — the one-line statement.
  - `basis` — **array of pillar slugs** (the schema-blessed home for what the decision rests
    on). Prefer stable slugs from `references/pillars.md` and `<repo>/.momo/pillars.md`.
  - `reasoning` — prose why.
  - `decided_by` (=`momo`), `decided_at`, optional `issue`, `artifacts_root`.
- **Envelope** is a full v1 CloudEvent (`kind=event`, `domain=repo`, `actor.agent_id=momo`,
  `ordering_key=repo:<slug>`, `producer=agent:momo`, `service=<slug>`) — so it validates
  against the existing schema at `bloodbank/schemas/bloodbank/v1/repo/decision.recorded.v1.json`.
  No schema-tree change is needed; the type already exists and validates.

## When to record (mandatory)

- Choosing a legal frontier item and submitting work-start intent.
- **Accepting** or **holding** a review-lane ticket.
- **Cutting scope** / deferring an AC to unblock a dependent.
- Choosing an **approach or architecture** among alternatives.
- **Stopping** the board-clearing loop (name the stop condition).
- **Rolling back** a review-accepted ticket a dependent proved broken.
- A **board_id / binding self-heal** (PJangler/bootstrap metadata repair).

Trivial, obvious, or purely mechanical steps do **not** need an event — reserve the trail
for calls where knowing the *why* later has value.

## Verify a live event landed

The `event-toaster` subscribes `bloodbank.evt.v1.>` and forwards to `ntfy.delo.sh/bloodbank`:

```bash
docker logs bloodbank-event-toaster --tail 5
curl -s 'https://ntfy.delo.sh/bloodbank/json?poll=1&since=120s'
```

## Note on the sentinel's own events

The current sentinel scripts (`issue-autonomous-review.sh`, close gate) emit their own repo-lane
events (`…issue.autonomous_review.decided`, `…issue.gate.passed/failed`) via the local
`emit-event.py`. Those are complementary — let the scripts emit them. Momo's
`record-decision.py` is for the *judgment* decisions that have no script of their
own. These events remain audit history; Lifecycle consumes observations/evidence
and independently determines the authoritative result.

# Holyfields CloudEvents Coverage Audit — 2026-04-24

**Context:** ADR-0002 follow-up #1. Purpose: determine whether existing
Holyfields base schemas satisfy the CloudEvents 1.0 + 33GOD extension-field
contract defined in ADR-0001.

**TL;DR:** They do not. Holyfields ships a v2-shaped base event schema
(`_common/base_event.v1.json`) that does not match CloudEvents 1.0 at the wire
level. Services that currently use `from holyfields.generated...` produce
events with v2 field names and shape. Dapr's `pubsub.jetstream` adds its own
CloudEvents envelope around the posted payload, so nothing is broken in the
sandbox smoke tests, but the CloudEvents envelope that lands on the wire is
NOT built from a Holyfields type yet.

The fix is to add a new v3 CloudEvents base schema to Holyfields and regenerate
Pydantic/Zod. Existing v2 schemas stay in place for backward compatibility.
This audit documents the gap, recommends the minimal path forward, and queues
the implementation work as a follow-up PR.

## Required shape (per ADR-0001, verified against Dapr live)

| Field | Required? | Type | Source |
|---|---|---|---|
| `specversion` | yes | string, const `"1.0"` | CloudEvents 1.0 |
| `id` | yes | uuid | CloudEvents 1.0 |
| `source` | yes | URI-reference string | CloudEvents 1.0 |
| `type` | yes | dotted name string | CloudEvents 1.0 |
| `subject` | no | string | CloudEvents 1.0 |
| `time` | recommended | RFC3339 timestamp | CloudEvents 1.0 |
| `datacontenttype` | no | MIME type | CloudEvents 1.0 |
| `dataschema` | no | URI | CloudEvents 1.0 |
| `correlationid` | yes (33GOD) | uuid | 33GOD extension |
| `causationid` | optional | uuid or null | 33GOD extension |
| `producer` | yes (33GOD) | string | 33GOD extension |
| `service` | yes (33GOD) | string | 33GOD extension |
| `domain` | yes (33GOD) | string | 33GOD extension |
| `schemaref` | recommended | short schema ref | 33GOD extension |
| `traceparent` | recommended | W3C Trace Context | 33GOD extension (also Dapr) |
| `data` | yes | domain-specific | CloudEvents 1.0 |

**Verified on the wire** via `smoketest-dapr.sh` and `smoketest-dapr-subscribe.sh`:
Dapr preserves every one of these when posted with
`Content-Type: application/cloudevents+json`. Dapr also adds `topic`,
`pubsubname`, `traceid`, `tracestate` on top.

## What Holyfields ships today

`holyfields/schemas/_common/base_event.v1.json` (v2-shaped):

```
event_id        uuid                              ← should be `id`
event_type      string, dotted name               ← should be `type`
timestamp       RFC3339                           ← should be `time`
version         semver                            ← not in CloudEvents; payload concern
correlation_id  uuid                              ← should be `correlationid`
causation_id    uuid                              ← should be `causationid`
source          OBJECT {host, app, trigger_type}  ← CloudEvents requires STRING URI
                                                    the v2 `source.app` is adjacent to
                                                    `service` but not the same concept
```

## Gap analysis

### Missing CloudEvents-required fields
- `specversion` — not present
- `id` — present as `event_id` (wrong name)
- `source` — present but wrong shape (object vs URI string)
- `type` — present as `event_type` (wrong name)

### Missing CloudEvents-recommended fields
- `subject` — not present
- `datacontenttype` — not present
- `dataschema` — not present

### Missing 33GOD extension fields
- `producer` — not present
- `service` — partially covered by `source.app`, not matching intent
- `domain` — not present
- `schemaref` — not present
- `traceparent` — not present

### Naming convention drift
- CloudEvents uses camelCase for attribute names (`specversion`, `correlationid`).
- Holyfields v2 base uses snake_case (`event_id`, `correlation_id`).
- Mixed casing in the same envelope is not a CloudEvents violation but is
  inconsistent with spec recommendations and our stated direction.

## What this means in practice

**Today's smoke tests still pass.** The tests construct CloudEvents envelopes
**by hand** in `smoketest-dapr.sh` and `smoketest-dapr-subscribe.sh`. They do
not use `from holyfields.generated` for envelope construction. So the mismatch
between the Holyfields base and CloudEvents is currently latent.

**The mismatch will surface when the first real service imports from
Holyfields.** If `weather-service` does:

```python
from holyfields.generated.weather import WeatherReadingRecordedV1
payload = WeatherReadingRecordedV1(...).model_dump()
requests.post("http://daprd:3500/v1.0/publish/bloodbank-v3-pubsub/event.weather.reading.recorded",
              json=payload)
```

The posted body will be the v2-shape (with `event_id`, `event_type`, nested
`source` object, etc.). Dapr will wrap it in a CloudEvents envelope, so what
lands on NATS looks like:

```
(CloudEvents outer envelope added by Dapr)
  id = dapr-generated-uuid
  type = (not set, or derived from topic)
  time = now
  data = {
    event_id = our-uuid
    event_type = "weather.reading.recorded"
    timestamp = our-timestamp
    correlation_id = our-uuid
    source = { host, app, trigger_type }
    ...
  }
```

Two sets of IDs, two sets of timestamps, two correlation concepts. Consumers
have to choose which to trust. That is exactly the situation ADR-0001 was
trying to prevent.

## Recommendation

Add a **new** v3 CloudEvents base schema to Holyfields without removing the
v2 schema. Forward-compatible; v2-consuming legacy services keep working.

**File:** `holyfields/schemas/_common/cloudevent_base.v1.json`

**Shape:** matches the required table above. All CloudEvents 1.0 required
fields + 33GOD extension fields. `data` is `{ "type": "object" }` at the base
level (domain schemas define its structure separately).

**Generation:** add to the generator's input list; produce
`CloudEventBaseV1` Pydantic model and Zod schema.

**Downstream (NOT part of this audit):** domain schemas migrate from
`allOf: [{ "$ref": "../_common/base_event.v1.json" }]` to
`allOf: [{ "$ref": "../_common/cloudevent_base.v1.json" }]` on a schedule owned
by each domain. Cutover is per-schema; no big-bang. Versioned properly
(`.v2.json` for migrated schemas so `.v1.json` stays stable for v2 consumers).

## Sizing

- Adding the new base schema: S
- Regenerating the single base Pydantic + Zod: S
- Domain schema migration pass (~30 schemas): M, worth per-domain PRs
- Service code changes to use the new base: depends on service count, but each
  is a narrow swap of the import

Total for bringing the FIRST service to CloudEvents via the new base: S+S+small
per-service.

## Proposed implementation PR content

One PR, scoped to Holyfields:

1. `holyfields/schemas/_common/cloudevent_base.v1.json` — new base schema
2. `holyfields/src/holyfields/generated/python/_common/cloudevent_base_v1.py`
   — regenerated Pydantic
3. `holyfields/src/holyfields/generated/typescript/_common/cloudevent_base_v1.ts`
   — regenerated Zod
4. A single unit test that constructs a canonical envelope and round-trips it
   through `model_dump()` / `json.loads` to prove the shape matches what Dapr
   accepts
5. Short README note in `holyfields/schemas/_common/README.md` (create if
   missing) explaining which base to use when (v1 base_event for legacy v2
   RabbitMQ path; v1 cloudevent_base for v3 Dapr/NATS path)

Metarepo PR follow-up: bump `bloodbank` gitlink if nothing is needed there;
bump `holyfields` gitlink to the tip of this work.

## Out of scope for this audit

- Migrating the 30+ existing domain schemas to the new base. That is per-domain
  work owned by whoever lands the first real v3 service in that domain.
- Deprecating or removing `_common/base_event.v1.json`. It remains valid for
  any legacy v2 code still in the tree.
- Changing the Holyfields generator beyond adding the new file to its inputs.

## Cross-references

- [ADR-0001: v3 Platform Pivot](./ADR-0001-v3-platform-pivot.md) — origin of
  the CloudEvents + extension-field requirements
- [ADR-0002: Holyfields Scope Refactor](./ADR-0002-holyfields-scope-refactor.md)
  — defined the follow-up this audit closes
- `bloodbank/ops/v3/smoketest/smoketest-dapr.sh` — live proof of the
  envelope fields Dapr preserves and adds

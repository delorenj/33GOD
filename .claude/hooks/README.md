# Claude Code → Bloodbank v3 Publisher Hooks

Publishes Claude Code session and tool-use events to the v3 event bus
(Dapr → NATS JetStream) as CloudEvents 1.0 envelopes.

## Architecture

```
Claude Code
    ↓ (PostToolUse / Stop / SessionStart)
.claude/hooks/bloodbank-publisher.sh
    ↓ (POST /v1.0/publish/<pubsub>/<topic>, application/cloudevents+json)
daprd-claude-events sidecar (host:3503 → container:3500)
    ↓ (pubsub.jetstream component)
NATS JetStream (BLOODBANK_V3_EVENTS stream, event.agent.* subjects)
    ↓ Dapr delivers to claude-events-recorder app
        → /events/{session_started,session_ended,tool_invoked}
        → in-memory buffer + per-session aggregate
        → GET /inspect/recorded (host:3602)
```

The publisher is **best-effort by design**. If the Dapr sidecar is not
reachable on the configured URL, the hook logs to
`.claude/sessions/publish-errors.log` and exits 0 so Claude Code never
blocks waiting on the event bus.

## Events Published

| Hook event         | CloudEvents `type`           | NATS subject                       |
|--------------------|------------------------------|------------------------------------|
| `SessionStart`     | `agent.session.started`      | `event.agent.session.started`      |
| `UserPromptSubmit` | `agent.prompt.submitted`     | `event.agent.prompt.submitted`     |
| `PreToolUse`       | `agent.tool.requested`       | `event.agent.tool.requested`       |
| `PostToolUse`      | `agent.tool.invoked`         | `event.agent.tool.invoked`         |
| `SubagentStop`     | `agent.subagent.completed`   | `event.agent.subagent.completed`   |
| `Stop`             | `agent.session.ended`        | `event.agent.session.ended`        |

Envelope shape follows
`holyfields/schemas/_common/cloudevent_base.v1.json`. The data block of
each type is constrained by the matching schema under
`holyfields/schemas/agent/<type>.v1.json` and is documented inline in
`bloodbank-publisher.sh`.

`agent.tool.requested` and `agent.tool.invoked` share a `turn_number`
within a session: the request fires from `PreToolUse` (intent), the
invocation fires from `PostToolUse` (result). Same `correlationid`
(session_id) + `turn_number` correlates them.

## Configuration

Set in `.claude/settings.json` under `env`:

| var                          | default                       | purpose |
|------------------------------|-------------------------------|---------|
| `BLOODBANK_ENABLED`          | `true`                        | `false` disables publishing entirely |
| `BLOODBANK_DEBUG`            | `false`                       | `true` logs each publish to stderr |
| `BLOODBANK_DAPR_URL`         | `http://localhost:3503`       | Dapr sidecar HTTP base URL |
| `BLOODBANK_PUBSUB`           | `bloodbank-v3-pubsub`         | Dapr pubsub component name |
| `BLOODBANK_PUBLISH_TIMEOUT`  | `2`                           | curl `--max-time` seconds |

## Bringing up the publish target

The hook expects a daprd sidecar on `localhost:3503`. Bring up the
dedicated `claude-events` compose profile, which runs
`daprd-claude-events` (sidecar exposed on host:3503) and
`claude-events-recorder` (subscriber that records all three agent.*
event types and exposes `/inspect/recorded` on host:3602):

```bash
docker compose --project-name bloodbank-v3 \
  --profile claude-events \
  -f bloodbank/compose/v3/docker-compose.yml \
  up -d nats nats-init dapr-placement claude-events-recorder daprd-claude-events
```

You can run the heartbeat profile alongside this one (different ports,
different sidecars) without conflict. If you only want to publish and
don't care about the recorder, pointing `BLOODBANK_DAPR_URL` at any
Dapr sidecar with the `bloodbank-v3-pubsub` component loaded will work
(Dapr publish is generic and not bound to the sidecar's app-id).

## Verifying the round-trip

```bash
# Hook fires session-start manually
echo '{}' | .claude/hooks/bloodbank-publisher.sh session-start

# Inspect what the recorder captured
curl -sS http://127.0.0.1:3602/inspect/recorded | jq '.count_by_type, .sessions'

# Or pull the raw envelope from the stream
docker run --rm -i --network bloodbank-v3-network natsio/nats-box:0.14.5 \
  nats --server nats://nats:4222 sub 'event.agent.session.started' \
  --count=1 --last-per-subject --raw
```

## Publish errors

Errors are appended to `.claude/sessions/publish-errors.log` (rotated at
~1 MB). Sample entry:

```
2026-04-26T11:14:37Z [192681] publish failed http=000 topic=event.agent.tool.invoked url=http://localhost:3502/...
```

`http=000` means curl could not reach the sidecar (most likely v3 is
not running). Other 4xx/5xx codes mean Dapr received the request but
rejected it — most often a missing pubsub component or a NATS-side
error. Check `docker logs bloodbank-v3-daprd-heartbeat` in that case.

## Session tracking

The hook keeps in-flight session state in `.claude/session-tracking.json`
and archives it to `.claude/sessions/<session_id>.json` on
`session-end`. This file is local-only state, not source-of-truth — the
canonical record lives on the event stream.

## Schema follow-up

The `agent.session.{started,ended}` and `agent.tool.invoked` schemas
that ship in Holyfields today are v2-shaped (extend the legacy
`_common/base_event.v1.json`). The publisher emits v3-shaped envelopes
that match `_common/cloudevent_base.v1.json` directly. Authoring v3
versions of the agent schemas (and wiring strict validation in CI) is
tracked separately as part of the broader Holyfields v3-base migration.

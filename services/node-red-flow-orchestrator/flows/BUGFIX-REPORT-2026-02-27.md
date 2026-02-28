# Bugfix Report: fireflies-bloodbank.json

**Date:** 2026-02-27
**Component:** node-red-flow-orchestrator
**File:** `services/node-red-flow-orchestrator/flows/fireflies-bloodbank.json`
**Branch:** `feat/god-10-obs-1-conformance`
**Author:** Jarad DeLorenzo

---

## Summary

Two bugs were identified in the Node-RED Fireflies ingest/publish flow. Both prevented the flow from functioning: one blocked all messages at the filter stage, and the other caused every Bloodbank publish to fail silently via malformed curl commands.

No changes were made to Bloodbank event types, Holyfields schemas, or routing keys. All fixes are internal to Node-RED flow wiring and exec node configuration.

---

## Bug 1: Wrong chokidar event name in file watch filter

**Node:** `filter_events` (tab: Ingest -> Bloodbank)
**Severity:** Critical (flow completely non-functional)

**Problem:** The switch node filtered on `msg.event == "update"`, but the Node-RED watch node (chokidar) emits `"change"` for file modifications. No messages could ever pass through this filter.

**Fix:** Changed the rule value from `"update"` to `"change"`. Updated the node label from "File update only" to "File change only" for clarity.

---

## Bug 2: Space in curl `-d @` file reference (2 instances)

**Nodes:** `bb_publish_upload` (tab: Ingest -> Bloodbank), `bb_publish_ready` (tab: Webhook -> Ready Event)
**Severity:** Critical (all Bloodbank publishes fail)

**Problem:** The exec nodes used `command: "curl ... -d @"` with `addpay: "filename"`. The exec node appends the msg property with a space separator, producing:

```
curl -s -X POST http://localhost:8682/publish -H "Content-Type: application/json" -d @ /path/to/envelope.json
```

The space between `@` and the file path breaks curl's read-from-file syntax. The `-d` flag receives the literal string `@` instead of reading from the envelope file.

**Fix:** In both `build_upload_envelope` and `build_ready_envelope` function nodes, added `msg.curlData = '@' + outPath` which pre-bakes the `@` prefix into the value. Changed both exec nodes to use `addpay: "curlData"` and removed the trailing `@` from the command string. Result:

```
curl -s -X POST http://localhost:8682/publish -H "Content-Type: application/json" -d @/path/to/envelope.json
```

---

## Affected Event Types

These events are published by the fixed nodes. Their schemas and routing keys are **unchanged**:

| Event Type | Routing Key | Direction | Tab |
|---|---|---|---|
| `fireflies.transcript.upload` | `fireflies.transcript.upload` | Publish to Bloodbank | Ingest -> Bloodbank |
| `fireflies.transcript.ready` | `fireflies.transcript.ready` | Publish to Bloodbank | Webhook -> Ready Event |

---

## What Did NOT Change

- No Bloodbank API contract changes (still POST to `http://localhost:8682/publish`)
- No Holyfields schema modifications
- No new event types or routing keys
- No changes to the consume/subscribe tabs
- No changes to the Fireflies API integration logic

---

## Files Modified

| File | Changes |
|---|---|
| `flows/fireflies-bloodbank.json` | 5 edits across 5 nodes (1 switch rule, 2 function nodes, 2 exec nodes) |

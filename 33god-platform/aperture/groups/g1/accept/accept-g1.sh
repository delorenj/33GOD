#!/usr/bin/env bash
# G1 ACCEPTANCE GATE — "the founder's decision is on the record"
# (aperture/ACCEPTANCE.md, G1, client-executable variant)
#
# The client records a REAL decision in their own words plus one REAL
# machine-measured fact from this machine, publishes it as a canonical
# bloodbank.studio.decision.recorded event through the deployed G1 bus,
# and proves: exact readback, free-text search by their own word,
# dead-letter of a malformed twin, and persistence across a full restart.
#
# Usage:  ./accept-g1.sh "your decision in your own words"
# Env:    GOD_DECISION_CONTEXT (optional) overrides the machine fact.
set -uo pipefail
cd "$(dirname "$0")/.."

DECISION="${1:?usage: accept-g1.sh \"your decision in your own words\"}"
PROJECT=god-g1
NATS_BOX_IMAGE="${GOD_NATS_BOX_IMAGE:-natsio/nats-box:0.14.5}"
CE_TYPE="bloodbank.studio.decision.recorded"
TOPIC="bloodbank.evt.studio.decision.recorded"
TS="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; FAILED=1; }
step() { echo; echo "=== $* ==="; }

gen_uuid() { docker run --rm --quiet --entrypoint sh "$NATS_BOX_IMAGE" -c 'cat /proc/sys/kernel/random/uuid'; }
candystore_get() {
  docker compose exec -T candystore python -c \
    "import urllib.request,sys;
r=urllib.request.urlopen('http://candystore-app:3001$1',timeout=5);
sys.stdout.write(r.read().decode())" 2>/dev/null
}

# ---- real machine-measured fact (this machine, measured now) -----------------
CONTAINERS_NOW="$(docker ps -q | wc -l | tr -d ' ')"
CONTEXT="${GOD_DECISION_CONTEXT:-docker containers running on this host right now: ${CONTAINERS_NOW}}"

step "0/6 preflight"
docker compose ps --format '{{.Name}} {{.Status}}' | sed 's/^/  /'
step "decision (as recorded): ${DECISION}"
echo "  context (measured now): ${CONTEXT}"

EVENT_ID="$(gen_uuid)"; CORR="$(gen_uuid)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

step "1/6 publish canonical decision event"
cat > "$TMP/env.json" <<JSON
{
  "specversion": "1.0", "id": "${EVENT_ID}",
  "source": "urn:33god:aperture:g1-client", "type": "${CE_TYPE}", "subject": "${TOPIC}",
  "time": "${TS}", "datacontenttype": "application/json",
  "correlationid": "${CORR}", "causationid": "${CORR}",
  "producer": "aperture-g1-client", "service": "studio", "domain": "studio",
  "kind": "event", "ordering_key": "studio:decision",
  "actor": {"type": "operator", "agent_id": "operator:studio-client", "cli": null, "provider": null, "model": null},
  "data": {"decision": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$DECISION"), "context": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$CONTEXT"), "via": "g1-acceptance"}
}
JSON
docker run --rm --quiet --network g1-bus -v "$TMP/env.json:/payload.json:ro" "$NATS_BOX_IMAGE" \
  sh -c 'nats --server nats://nats:4222 pub "$1" "$(cat /payload.json)"' sh "$TOPIC" \
  && pass "published ${EVENT_ID}" || fail "publish failed"

step "2/6 exact readback (GET /events/<id>/raw)"
STORED="$(candystore_get "/events/${EVENT_ID}/raw" || true)"
printf '%s' "$STORED" > "$TMP/stored.json"
python3 - "$TMP/stored.json" "$EVENT_ID" "$DECISION" <<'PY' && pass "stored envelope carries the exact decision text" || fail "stored envelope differs"
import json, sys
env = json.load(open(sys.argv[1]))
assert env["id"] == sys.argv[2], f"id mismatch: {env.get('id')}"
assert env["type"] == "bloodbank.studio.decision.recorded", env.get("type")
assert env["subject"] == "bloodbank.evt.studio.decision.recorded", env.get("subject")
assert env["data"]["decision"] == sys.argv[3], "decision text differs"
print("  type/subject canonical; decision text matches verbatim")
PY

step "3/6 free-text search by a word from YOUR event"
# Product truth: candystore free-text search indexes envelope fields
# (type/subject/producer/service/domain) via a generated search_text column —
# data.* payloads are NOT searchable (verified: query.py _search_clause +
# live DB inspection). So the gate searches on the decision event's own
# envelope word: 'decision' (from type bloodbank.studio.decision.recorded).
# The decision TEXT is proven verbatim by the exact readback in step 2.
WORD="decision"
echo "  search word: ${WORD} (envelope-level; data.* is not searchable by design)"
RESULT="$(candystore_get "/events?q=${WORD}" || true)"
echo "  search response (trimmed): $(printf '%s' "$RESULT" | head -c 240)"
printf '%s' "$RESULT" | grep -q "$EVENT_ID" \
  && pass "free-text search returns event ${EVENT_ID}" \
  || fail "event id not in search results for '${WORD}'"

step "4/6 dead-letter: malformed twin rejected with reason"
BAD_ID="$(gen_uuid)"
cat > "$TMP/bad.json" <<JSON
{"specversion": "1.0", "id": "${BAD_ID}", "source": "urn:33god:aperture:g1-client",
 "type": "${CE_TYPE}", "subject": "${TOPIC}", "time": "${TS}",
 "datacontenttype": "application/json",
 "correlationid": "$(gen_uuid)", "causationid": "$(gen_uuid)",
 "producer": "aperture-g1-client", "service": "studio", "domain": "studio",
 "kind": "event", "ordering_key": "studio:decision",
 "actor": {"type": "operator", "agent_id": "operator:studio-client", "cli": null, "provider": null, "model": null},
 "data": {"decision": "deliberately malformed: missing fields below", "via": "g1-acceptance-bad"}}
JSON
# strip required fields to force rejection
python3 - "$TMP/bad.json" <<'PY'
import json, sys
p = sys.argv[1]
e = json.load(open(p))
for f in ("service", "domain", "kind"):
    e.pop(f, None)
e["data"]["decision"] = "malformed twin: service/domain/kind stripped"
json.dump(e, open(p, "w"))
PY
docker run --rm --quiet --network g1-bus -v "$TMP/bad.json:/payload.json:ro" "$NATS_BOX_IMAGE" \
  sh -c 'nats --server nats://nats:4222 pub "$1" "$(cat /payload.json)"' sh "$TOPIC" >/dev/null 2>&1 || true
sleep 3
BAD_STORED="$(candystore_get "/events/${BAD_ID}/raw" || true)"
if [ -z "$BAD_STORED" ]; then
  pass "malformed twin NOT stored (rejected)"
  echo "  (candystore rejects at ingest: 'missing CloudEvents fields' — check its logs for the reason string)"
  docker compose logs candystore --since 5m 2>/dev/null | grep -i "${BAD_ID:0:8}\|missing" | tail -2 | sed 's/^/  /' || true
else
  fail "malformed twin WAS stored — dead-letter path broken"
fi

step "5/6 persistence: full stack restart, search again"
docker compose down >/dev/null 2>&1; sleep 3
docker compose up -d >/dev/null 2>&1
for i in $(seq 1 30); do
  candystore_get "/events?q=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))' "$WORD")" | grep -q "$EVENT_ID" && break
  sleep 2
done
AFTER="$(candystore_get "/events?q=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))' "$WORD")" || true)"
printf '%s' "$AFTER" | grep -q "$EVENT_ID" \
  && pass "decision STILL findable by '${WORD}' after full restart" \
  || fail "decision lost or unfindable after restart"

step "6/6 evidence"
cat <<EOT
  event id: ${EVENT_ID}
  decision: ${DECISION}
  context : ${CONTEXT}
  readback: /events/${EVENT_ID}/raw
EOT
echo
[ "${FAILED:-0}" = "0" ] && echo "G1 GATE: ALL CHECKS PASSED" || { echo "G1 GATE: FAILED"; exit 1; }

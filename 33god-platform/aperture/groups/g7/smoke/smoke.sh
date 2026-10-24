#!/usr/bin/env bash
# Aperture G7 smoke — cold bring-up + full memory+enrichment plane proof.
#
# DESTRUCTIVE to god-g7: cold `down -v`, build, up, real work, `down -v`.
# Never touches any other compose project. Exit: 0 = PASS, 1 = FAIL.
#
# Proves, in order:
#   1. Cold bring-up with EMPTY GOD_LLM_*: every core service healthy,
#      hindsight-bridge healthy AND degraded (healthz names the empty vars) —
#      degraded-not-crashed is the D1 boundary.
#   2. Publish a canonical source event on the bus (nats-box, in-network) ->
#      enrichment worker consumes it, emits a derived canonical event with
#      causationid = source id (4-token type / 5-token subject, no conflation).
#   3. candystore readback of BOTH events via the query API (/events/<id>/raw)
#      — the downstream consumer's stored envelope, not the emitter's ack.
#   4. memory-reference backend received BOTH events (bridge fan-out) and
#      keyword search finds them (keyword works without any LLM).
#   5. Restart persistence: restart the stack; both events + extractions
#      survive (candystore PG volume + enrichment SQLite volume).
#   6. Malformed event rejected: non-canonical type -> enrichment 400, and a
#      well-formed-but-off-contract envelope on the bus is dropped by the
#      worker (never enriched, never published).
#   7. Teardown: down -v leaves zero god-g7 volumes/containers/networks.
#
# Stdlib only (bash + python3 stdlib + docker compose). UUIDs generated inside
# Linux containers (macOS host portability).

set -uo pipefail
cd "$(dirname "$0")/.."

PASS=0; FAIL=0
step() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
ok()   { printf 'PASS: %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf 'FAIL: %s\n' "$*"; FAIL=$((FAIL + 1)); }

NATS_BOX="${GOD_NATS_BOX_IMAGE:-natsio/nats-box:0.14.5}"
BUS_URL="${GOD_BUS_NATS_URL:-nats://nats:4222}"

cid() { docker compose ps -aq "$1" 2>/dev/null | head -1; }
wait_healthy() {
  local svc="$1" timeout="${2:-150}" i st
  for ((i = 0; i < timeout; i += 2)); do
    st="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$(cid "$svc")" 2>/dev/null || true)"
    [ "$st" = "healthy" ] && return 0
    sleep 2
  done
  return 1
}
wait_state() {
  local svc="$1" want="$2" timeout="${3:-90}" i st
  for ((i = 0; i < timeout; i += 2)); do
    st="$(docker inspect --format '{{.State.Status}}' "$(cid "$svc")" 2>/dev/null || true)"
    [ "$st" = "$want" ] && return 0
    sleep 2
  done
  return 1
}
gen_uuid() { docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid'; }

# HTTP inside the bundle network from a named service (python images have no
# curl; use their own python). svc_get <service> <url-path> [method body]
svc_json() {
  local svc="$1" url="$2" body="${3:-}"
  if [ -n "$body" ]; then
    docker compose exec -T "$svc" python -c "
import json, urllib.request
req = urllib.request.Request('http://$svc:8791$url', data=json.dumps($body).encode(), headers={'Content-Type':'application/json'})
try:
    r = urllib.request.urlopen(req, timeout=10); print(r.status); print(r.read().decode())
except urllib.error.HTTPError as e: print(e.code); print(e.read().decode())"
  else
    docker compose exec -T "$svc" python -c "
import urllib.request
try:
    r = urllib.request.urlopen('http://$svc:8791$url', timeout=10); print(r.status); print(r.read().decode())
except urllib.error.HTTPError as e: print(e.code); print(e.read().decode())"
  fi
}

step "0/7 cold start: down -v, build, up (EMPTY GOD_LLM_* — degraded mode)"
docker compose down -v --remove-orphans >/dev/null 2>&1
# explicitly empty LLM env to prove degraded-not-crashed
if docker compose build >/dev/null 2>&1 && \
   GOD_LLM_BASE_URL= GOD_LLM_API_KEY= docker compose up -d --wait --wait-timeout 300 >/dev/null 2>&1; then
  ok "cold up --wait healthy with empty GOD_LLM_*"
else
  bad "cold up failed"
  docker compose ps -a
  exit 1
fi

step "1/7 degraded boundary: hindsight-bridge healthy + degraded + says why"
HZ="$(docker compose exec -T hindsight-bridge python -c "
import urllib.request, json
print(urllib.request.urlopen('http://127.0.0.1:8790/healthz', timeout=5).read().decode())")"
echo "healthz: $HZ" | head -c 400; echo
python3 - "$HZ" <<'PY' && ok "healthz: healthy AND degraded with named reasons" || bad "healthz degraded contract violated"
import json, sys
h = json.loads(sys.argv[1])
assert h["ready"] is True and h["degraded"] is True, h
r = h["degraded_reason"]
assert "degraded" in r and "GOD_LLM_BASE_URL" in r and "GOD_LLM_API_KEY" in r, r
assert h["llm"]["configured"] is False and h["llm"]["base_url"] is None, h
assert h["backend_count"] >= 1, "reference backend missing"
PY

step "2/7 publish canonical source event -> derived event with causationid chain"
SRC_ID="$(gen_uuid)"
CORR_ID="$(gen_uuid)"
SRC_TYPE="bloodbank.aperture.smoke.g7"
SRC_SUBJECT="bloodbank.evt.aperture.smoke.g7"
EVENT_TIME="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
ENV_JSON=$(cat <<JSON
{
  "specversion": "1.0",
  "id": "${SRC_ID}",
  "source": "urn:33god:aperture:g7-smoke",
  "type": "${SRC_TYPE}",
  "subject": "${SRC_SUBJECT}",
  "time": "${EVENT_TIME}",
  "datacontenttype": "application/json",
  "correlationid": "${CORR_ID}",
  "causationid": "${CORR_ID}",
  "producer": "aperture-g7-smoke",
  "service": "smoke",
  "domain": "aperture",
  "kind": "event",
  "ordering_key": "g7:smoke",
  "actor": {"type": "operator", "agent_id": "operator:aperture-g7-smoke", "cli": null, "provider": null, "model": null},
  "data": {"ping": true, "project": "33GOD", "note": "pyramid alignment ritual"}
}
JSON
)
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
printf '%s' "$ENV_JSON" > "$TMP/source.json"
docker run --rm --quiet --network g7-bus -v "$TMP/source.json:/payload.json:ro" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.aperture.smoke.g7 "$(cat /payload.json)"' \
  && ok "source event published (${SRC_ID})" || bad "publish failed"

# wait for enrichment to process it (consumer lag + processing)
DERIVED_ID=""
for ((i = 0; i < 30; i += 1)); do
  W="$(docker compose exec -T enrichment python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8791/extractions', timeout=5).read().decode())" 2>/dev/null || true)"
  DERIVED_ID="$(printf '%s' "$W" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    rows = [r for r in d.get('extractions', []) if r['source_id'] == '$SRC_ID']
    print(rows[0]['derived_id'] if rows else '')
except Exception:
    print('')" 2>/dev/null || true)"
  [ -n "$DERIVED_ID" ] && break
  sleep 2
done
if [ -n "$DERIVED_ID" ]; then
  ok "extraction recorded, derived_id=${DERIVED_ID}"
else
  bad "enrichment never processed ${SRC_ID}"
fi
WH="$(docker compose exec -T enrichment python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8791/healthz', timeout=5).read().decode())")"
echo "worker healthz: $WH"

step "3/7 candystore readback of BOTH events (query API, /events/<id>/raw)"
for ID_LABEL in "${SRC_ID}|source-out" "${DERIVED_ID}|derived-out"; do
  ID="${ID_LABEL%%|*}"; LABEL="${ID_LABEL##*|}"
  GOT=""
  for ((i = 0; i < 20; i += 1)); do
    GOT="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/$ID/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
    [ -n "$GOT" ] && break
    sleep 2
  done
  if [ -n "$GOT" ]; then
    printf '%s' "$GOT" > "$TMP/$LABEL.json"
    ok "candystore /events/$ID/raw returned the $LABEL envelope"
  else
    bad "candystore never returned $LABEL event $ID"
  fi
done
python3 - "$TMP/source.json" "$TMP/source-out.json" "$TMP/derived-out.json" "$SRC_ID" "$DERIVED_ID" "$CORR_ID" <<'PY' && ok "chain verified: derived.causationid == source.id; canonical 4/5-token shapes; type != subject" || bad "chain/shape verification failed"
import json, sys
pub, src_out, drv_out, src_id, drv_id, corr = sys.argv[1:7]
pub_env = json.load(open(pub))
src_env = json.load(open(src_out))
drv_env = json.load(open(drv_out))
# source fidelity through the bus + store
assert src_env["id"] == src_id and src_env["type"] == pub_env["type"]
assert src_env["subject"] == pub_env["subject"] and src_env["data"]["ping"] is True
# derived event: canonical shape + THE CHAIN
assert drv_env["id"] == drv_id, (drv_env.get("id"), drv_id)
tokens = drv_env["type"].split(".")
assert len(tokens) == 4 and tokens[0] == "bloodbank" and tokens[3] == "enriched", drv_env["type"]
assert drv_env["subject"] == "bloodbank.evt." + ".".join(tokens[1:]), drv_env["subject"]
assert drv_env["type"] != drv_env["subject"], "type==subject conflation"
assert tokens[1:3] == pub_env["type"].split(".")[1:3], "domain/entity must carry through"
assert drv_env["causationid"] == src_id, "THE CHAIN: causationid must be the source id"
assert drv_env["correlationid"] == corr, "correlationid must carry through"
assert drv_env["kind"] == "event" and drv_env["specversion"] == "1.0"
assert drv_env["service"] == "aperture-g7" and drv_env["domain"] == tokens[1]
assert isinstance(drv_env.get("ordering_key"), str) and drv_env["ordering_key"]
# the transform is real: extraction fields the source did not carry
x = drv_env["data"]["extraction"]
assert x["source_id"] == src_id
assert len(x["payload_sha256"]) == 64 and x["payload_bytes"] > 0
assert x["size_class"] in ("tiny", "small", "large")
assert "ping" in x["payload_keys"] and "project" in x["payload_keys"]
print("derived type:", drv_env["type"])
print("causationid:", drv_env["causationid"], "== source id:", src_id)
PY

step "4/7 memory plane: bridge tailed BOTH events into memory-reference; keyword search finds them"
# wait for the bridge tail to catch up
for ((i = 0; i < 20; i += 1)); do
  MEMCOUNT="$(docker compose exec -T hindsight-bridge python -c "
import urllib.request, json
print(json.loads(urllib.request.urlopen('http://127.0.0.1:8790/healthz', timeout=5).read())['tailed'])" 2>/dev/null || true)"
  [ "${MEMCOUNT:-0}" -ge 2 ] 2>/dev/null && break
  sleep 2
done
echo "bridge tailed: ${MEMCOUNT:-?} events"
[ "${MEMCOUNT:-0}" -ge 2 ] 2>/dev/null && ok "bridge tailed >=2 events (source + derived)" || bad "bridge tail did not reach 2"
Q="$(docker compose exec -T hindsight-bridge python -c "
import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:8790/query', data=json.dumps({'q': 'aperture-g7-smoke', 'limit': 10}).encode(), headers={'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=10).read().decode())")"
printf '%s' "$Q" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['mode'] == 'keyword', d['mode']  # degraded: keyword, no rerank
ids = {r['event_id'] for r in d['results']}
assert ids >= {'$SRC_ID', '$DERIVED_ID'}, ids
print('keyword search found', len(ids), 'events incl. source + derived')" \
  && ok "keyword search (no LLM) returns source + derived by producer" || bad "memory query failed"
# data.* select-field search (project=33GOD indexed by contract)
Q2="$(docker compose exec -T hindsight-bridge python -c "
import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:8790/query', data=json.dumps({'q': '33GOD', 'limit': 10}).encode(), headers={'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=10).read().decode())")"
printf '%s' "$Q2" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert any(r['event_id'] == '$SRC_ID' for r in d['results']), 'project field not searchable'
print('data.project term searchable for source event')" \
  && ok "keyword search over indexed data field (project=33GOD)" || bad "data-field search failed"

step "5/7 restart persistence: both events + extractions survive a stack restart"
docker compose restart candystore-postgres candystore enrichment memory-reference >/dev/null 2>&1
wait_healthy candystore 120; wait_healthy enrichment 90; wait_healthy memory-reference 90
R1="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/$SRC_ID/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
R2="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/$DERIVED_ID/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
if [ -n "$R1" ] && [ -n "$R2" ]; then
  ok "candystore served both events after restart"
else
  bad "events missing after restart (src=${#R1} derived=${#R2} bytes)"
fi
RX="$(docker compose exec -T enrichment python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8791/extractions', timeout=5).read().decode())" 2>/dev/null || true)"
printf '%s' "$RX" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert any(r['source_id'] == '$SRC_ID' for r in d['extractions']), d
print('extraction row survived restart')" \
  && ok "enrichment side table survived restart" || bad "extraction lost on restart"
RM="$(docker compose exec -T memory-reference python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8792/healthz', timeout=5).read().decode())" 2>/dev/null || true)"
printf '%s' "$RM" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['ready'] is True and d['events'] >= 2, d
print('memory events:', d['events'])" \
  && ok "memory-reference store survived restart (>=2 events)" || bad "memory lost on restart"

step "6/7 malformed rejection: non-canonical input never enriched"
BAD1="$(docker compose exec -T enrichment python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8791/inqueue', data=json.dumps({'id': 'not-a-uuid', 'type': 'wrong.shape', 'subject': 'x', 'data': {}}).encode(), headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except urllib.error.HTTPError as e:
    print(e.code)
" 2>/dev/null || true)"
[ "${BAD1:-x}" = "400" ] && ok "POST /inqueue rejects non-canonical envelope (400)" || bad "inqueue accepted malformed event (got ${BAD1:-none})"
# publish a well-formed-looking but off-contract event on the bus (5-token
# type) — worker must reject it internally (never enrich, never publish)
BAD_ID="$(gen_uuid)"
BAD_TIME="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
cat > "$TMP/bad.json" <<JSON
{"specversion":"1.0","id":"${BAD_ID}","source":"urn:33god:aperture:g7-smoke","type":"bloodbank.evt.aperture.smoke.bad","subject":"bloodbank.evt.aperture.smoke.bad","time":"${BAD_TIME}","datacontenttype":"application/json","correlationid":"${BAD_ID}","causationid":"${BAD_ID}","producer":"aperture-g7-smoke","service":"smoke","domain":"aperture","kind":"event","ordering_key":"g7:smoke","actor":{"type":"operator","agent_id":"o"},"data":{"bad":true}}
JSON
docker run --rm --quiet --network g7-bus -v "$TMP/bad.json:/payload.json:ro" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.aperture.smoke.bad "$(cat /payload.json)"' >/dev/null 2>&1
sleep 4
cat > "$TMP/derive_id.py" <<'PY'
import sys, uuid
print(uuid.uuid5(uuid.UUID("6f1a2c34-83b5-4d97-9f0e-a1b2c3d4e5f6"), sys.argv[1]))
PY
BAD_DERIVED="$(python3 "$TMP/derive_id.py" "$BAD_ID")"
BADSTORED="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/${BAD_DERIVED}/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
if [ -z "$BADSTORED" ]; then
  ok "off-contract event - 5-token type - never produced a derived event"
else
  bad "off-contract event WAS enriched - derived ${BAD_DERIVED} exists"
fi
# Note: the off-contract event itself IS stored by candystore (its own
# REQUIRED_ENVELOPE_FIELDS pass — id/source/type/time/producer/service/
# domain/kind are present). That is correct store behavior; the rejection
# under test here is the ENRICHMENT validator's, which refuses non-canonical
# type shapes and so never enriched it (rejected count in worker healthz).

step "7/7 teardown: down -v leaves zero residue"
docker compose down -v --remove-orphans >/dev/null 2>&1
RESIDUE="$(docker volume ls -q --filter name=god-g7- ; docker network ls -q --filter name=g7- ; docker compose ps -aq 2>/dev/null)"
if [ -z "$(echo "$RESIDUE" | tr -d '[:space:]')" ]; then
  ok "zero god-g7 volumes / networks / containers remain"
else
  bad "residue: $RESIDUE"
fi

step "verdict"
echo "passed: ${PASS}  failed: ${FAIL}"
if [ "$FAIL" -eq 0 ]; then
  echo "SMOKE RESULT: PASS — G7 memory+enrichment plane proven cold"
  exit 0
else
  echo "SMOKE RESULT: FAIL"
  exit 1
fi

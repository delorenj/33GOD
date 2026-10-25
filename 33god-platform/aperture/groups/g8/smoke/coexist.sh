#!/usr/bin/env bash
# G8 coexistence gate: prove that with a G1-shaped consumer ALREADY consuming,
# an attached G8 receives EVERY event into BOTH stores — no durable/queue
# collision, no event splitting (the shared-durable failure mode).
#
# Simulates the target topology honestly (g7 pattern):
#   - one external bus (BLOODBANK_EVENTS)
#   - a G1-side consumer: candystore stack with G1's durable names
#     ("candystore-events"/"candystore") ALREADY RUNNING AND CONSUMING
#   - G8 attached via compose.attach.yml (own durables g8-*)
#
# Proves:
#   1. both consumers hold DISTINCT durables on the stream (no collision)
#   2. N events published while BOTH consume -> N rows in BOTH stores
#   3. same event id read back field-equal from both stores
#   4. a G8 real-cycle event (code.commit.landed) reaches the G1-side store
#      too — G8's own output does not split either
#
# The G1-side stack is a THROWAWAY candystore (same vendored image, G1's
# durable names) — the real god-g1 project is never touched.
set -uo pipefail
cd "$(dirname "$0")/.."

PASS=0; FAIL=0
ok() { printf 'PASS: %s\n' "$*"; PASS=$((PASS + 1)); }
bad() { printf 'FAIL: %s\n' "$*"; FAIL=$((FAIL + 1)); }
step() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

NATS_BOX="${GOD_NATS_BOX_IMAGE:-natsio/nats-box:0.14.5}"
NET="g1-bus"   # external network name the attach overlay expects

cleanup() {
  docker compose -f compose.yml -f compose.attach.yml down -v --remove-orphans >/dev/null 2>&1
  docker compose -p g8-coexist-g1side -f /tmp/g8-coexist-g1side.yml down -v --remove-orphans >/dev/null 2>&1
  docker rm -f g8-coexist-bus g8-coexist-g1init >/dev/null 2>&1
  docker network rm "$NET" >/dev/null 2>&1
}
trap cleanup EXIT

G1SIDE=/tmp/g8-coexist-g1side.yml
cat > "$G1SIDE" <<'YML'
# THROWAWAY G1-side candystore (G1's durable names) — simulates the already-
# running G1 consumer on the target bus. Never the real god-g1 project.
name: g8-coexist-g1side
networks:
  g1-bus:
    name: g1-bus
    external: true
services:
  g1-postgres:
    image: pgvector/pgvector:0.8.0-pg17
    environment: {POSTGRES_USER: candystore, POSTGRES_PASSWORD: candystore, POSTGRES_DB: candystore}
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U candystore"], interval: 5s, retries: 20}
    networks: [g1-bus]
  g1-candystore:
    image: candystore:g8
    environment:
      APP_PORT: "3001"
      APP_HOST: 0.0.0.0
      DATABASE_URL: postgresql://candystore:candystore@g1-postgres:5432/candystore
      SUBSCRIBE_PUBSUB: bloodbank-pubsub
      SUBSCRIBE_TOPIC: bloodbank.evt.>
      SUBSCRIBE_ROUTE: /events/all
    depends_on: {g1-postgres: {condition: service_healthy}}
    networks: [g1-bus]
  g1-daprd:
    image: daprio/daprd:1.13.0
    command: ["./daprd","--app-id=g1candystore","--dapr-http-port=3500","--app-port=3001",
              "--app-channel-address=g1-candystore","--app-protocol=http",
              "--resources-path=/components","--log-level=info"]
    volumes:
      - type: bind
        source: /tmp/g8-coexist-g1-pubsub.yaml
        target: /components/pubsub.yaml
        read_only: true
    depends_on: [g1-candystore]
    networks: [g1-bus]
YML
# G1's ORIGINAL durable names (the names the real G1 owns)
cat > /tmp/g8-coexist-g1-pubsub.yaml <<'YAML'
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: bloodbank-pubsub
spec:
  type: pubsub.jetstream
  version: v1
  metadata:
    - name: natsURL
      value: "nats://nats:4222"
    - name: name
      value: "bloodbank-pubsub"
    - name: durableName
      value: "candystore-events"
    - name: queueGroupName
      value: "candystore"
    - name: streamName
      value: "BLOODBANK_EVENTS"
    - name: deliverPolicy
      value: "all"
    - name: ackWait
      value: "30s"
YAML

step "external bus + G1-side consumer ALREADY consuming"
docker network create --attachable "$NET" >/dev/null 2>&1 || true
docker run -d --rm --name g8-coexist-bus --network "$NET" --network-alias nats \
  nats:2.10-alpine -js -sd /data -m 8222 >/dev/null
sleep 3
docker run --rm --name g8-coexist-g1init --network "$NET" \
  -v "$PWD/nats/streams.json:/work/streams.json:ro" \
  -v "$PWD/nats/init.sh:/work/init.sh:ro" \
  -e NATS_URL=nats://nats:4222 -e NATS_GUARD=0 \
  --entrypoint /bin/sh "$NATS_BOX" /work/init.sh >/dev/null 2>&1
# fail fast: streams must exist before the G1-side stack starts consuming
docker run --rm --network "$NET" "$NATS_BOX" \
  nats --server nats://nats:4222 stream info BLOODBANK_EVENTS >/dev/null 2>&1 \
  || { bad "coexist bus streams missing after init"; exit 1; }
docker compose -p g8-coexist-g1side -f "$G1SIDE" up -d --wait --wait-timeout 240 >/dev/null 2>&1 \
  && ok "G1-side consumer up (durable candystore-events, ALREADY consuming)" \
  || { bad "G1-side stack failed"; docker compose -p g8-coexist-g1side -f "$G1SIDE" ps -a; exit 1; }

step "attach G8 (own durables) onto the same bus"
docker compose -f compose.yml -f compose.attach.yml down -v --remove-orphans >/dev/null 2>&1
GOD_LLM_BASE_URL= GOD_LLM_API_KEY= \
docker compose -f compose.yml -f compose.attach.yml up -d --wait --wait-timeout 300 >/dev/null 2>&1 \
  && ok "G8 attached (own durables g8-*)" \
  || { bad "G8 attach failed"; docker compose -f compose.yml -f compose.attach.yml ps -a; exit 1; }

step "distinct durables on the stream (no collision)"
DURABLES="$(docker run --rm --quiet --network "$NET" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 consumer ls BLOODBANK_EVENTS --names' 2>/dev/null | tr '\n' ' ')"
echo "  durables: ${DURABLES}"
echo "$DURABLES" | grep -q "candystore-events" \
  && echo "$DURABLES" | grep -q "g8-candystore-events" \
  && echo "$DURABLES" | grep -q "g8-momod" \
  && echo "$DURABLES" | grep -q "g8-dashboard" \
  && ok "G1's durable + G8's durables coexist as distinct consumers" \
  || bad "durable set wrong: ${DURABLES}"

step "readiness canary (both sidecars bound) BEFORE the split check"
CANARY_ID="$(docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid')"
TMP="$(mktemp -d)"
cat > "$TMP/canary.json" <<JSON
{"specversion":"1.0","id":"${CANARY_ID}","source":"urn:33god:aperture:g8-coexist","type":"bloodbank.aperture.canary.g8","subject":"bloodbank.evt.aperture.canary.g8","time":"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)","datacontenttype":"application/json","correlationid":"${CANARY_ID}","causationid":"${CANARY_ID}","producer":"aperture-g8-coexist","service":"smoke","domain":"aperture","kind":"event","ordering_key":"g8:coexist:canary","actor":{"type":"operator","agent_id":"o"},"data":{"canary":true}}
JSON
docker run --rm --quiet --network "$NET" -v "$TMP/canary.json:/payload.json:ro" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.aperture.canary.g8 "$(cat /payload.json)"' >/dev/null 2>&1 || true
CANARY_A=""; CANARY_B=""
for ((i = 0; i < 60; i += 1)); do
  [ -z "$CANARY_A" ] && CANARY_A="$(docker compose -p g8-coexist-g1side -f "$G1SIDE" exec -T g1-candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://g1-candystore:3001/events/${CANARY_ID}/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null)"
  [ -z "$CANARY_B" ] && CANARY_B="$(docker compose -f compose.yml -f compose.attach.yml exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/${CANARY_ID}/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null)"
  [ -n "$CANARY_A" ] && [ -n "$CANARY_B" ] && break
  sleep 2
done
[ -n "$CANARY_A" ] && [ -n "$CANARY_B" ] && ok "canary reached BOTH stores (both durables delivering)" \
                                          || bad "canary did not reach both stores (A=${#CANARY_A}B ${#CANARY_B} bytes)"

step "publish N=5 canonical events while BOTH consume -> every event in BOTH stores"
N=5
declare -a IDS
for i in $(seq 1 "$N"); do
  ID="$(docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid')"
  IDS+=("$ID")
  cat > "$TMP/e$i.json" <<JSON
{"specversion":"1.0","id":"$ID","source":"urn:33god:aperture:g8-coexist","type":"bloodbank.aperture.coexist.g8","subject":"bloodbank.evt.aperture.coexist.g8","time":"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)","datacontenttype":"application/json","correlationid":"$ID","causationid":"$ID","producer":"aperture-g8-coexist","service":"smoke","domain":"aperture","kind":"event","ordering_key":"g8:coexist:$i","actor":{"type":"operator","agent_id":"o"},"data":{"i":$i,"project":"33GOD","note":"coexist $i"}}
JSON
  docker run --rm --quiet --network "$NET" -v "$TMP/e$i.json:/payload.json:ro" "$NATS_BOX" \
    sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.aperture.coexist.g8 "$(cat /payload.json)"' >/dev/null 2>&1
done
ok "published $N events onto the shared bus"

g8_get() { docker compose -f compose.yml -f compose.attach.yml exec -T candystore python -c "
import urllib.request,sys
try: sys.stdout.write(urllib.request.urlopen('http://candystore-app:3001/events/$1/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null; }
g1_get() { docker compose -p g8-coexist-g1side -f "$G1SIDE" exec -T g1-candystore python -c "
import urllib.request,sys
try: sys.stdout.write(urllib.request.urlopen('http://g1-candystore:3001/events/$1/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null; }

IN_G1=0; IN_G8=0; BOTH_FIELD_EQUAL=0
for i in $(seq 0 $((N - 1))); do
  ID="${IDS[$i]}"
  A=""; B=""
  for _ in $(seq 1 15); do
    [ -z "$A" ] && A="$(g1_get "$ID")"
    [ -z "$B" ] && B="$(g8_get "$ID")"
    [ -n "$A" ] && [ -n "$B" ] && break
    sleep 2
  done
  [ -n "$A" ] && IN_G1=$((IN_G1 + 1))
  [ -n "$B" ] && IN_G8=$((IN_G8 + 1))
  if [ -n "$A" ] && [ -n "$B" ]; then
    printf '%s\n%s\n' "$A" "$B" > "$TMP/pair$i.json"
    if python3 - "$TMP/pair$i.json" <<'PY'
import json, sys
lines = open(sys.argv[1]).read().splitlines()
a, b = json.loads(lines[0]), json.loads(lines[1])
assert a["id"] == b["id"]
for f in ("type", "producer", "service", "domain", "kind", "data"):
    assert a[f] == b[f], (f, a.get(f), b.get(f))
PY
    then BOTH_FIELD_EQUAL=$((BOTH_FIELD_EQUAL + 1)); fi
  fi
done
echo "  events in G1 store: ${IN_G1}/${N}   in G8 store: ${IN_G8}/${N}   field-equal pairs: ${BOTH_FIELD_EQUAL}/${N}"
[ "$IN_G1" -eq "$N" ] && ok "every event reached the G1-side store (no split)" || bad "G1-side store missing $((N - IN_G1)) events"
[ "$IN_G8" -eq "$N" ] && ok "every event reached the G8 store (no split)" || bad "G8 store missing $((N - IN_G8)) events"
[ "$BOTH_FIELD_EQUAL" -eq "$N" ] && ok "stored envelopes field-equal across both stores" || bad "field mismatch in $((N - BOTH_FIELD_EQUAL)) pairs"

step "G8's own cycle output (code.commit.landed) also reaches the G1-side store"
TITLE="coexist cycle ticket"
CREATE="$(docker compose -f compose.yml -f compose.attach.yml exec -T board python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8793/command',
    data=json.dumps({'action': 'create', 'title': '''$TITLE'''}).encode(),
    headers={'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=15).read().decode())")"
TICKET_ID="$(printf '%s' "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['ticket']['id'])" 2>/dev/null || true)"
CORR="$(printf '%s' "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['ticket']['correlationid'])" 2>/dev/null || true)"
LANDED_IN_G1=""
for ((i = 0; i < 90; i += 1)); do
  E="$(docker compose -p g8-coexist-g1side -f "$G1SIDE" exec -T g1-candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://g1-candystore:3001/events?limit=50', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  LANDED_IN_G1="$(printf '%s' "$E" | python3 -c "
import json, sys
d = json.load(sys.stdin)
rows = [e for e in d.get('events', []) if e.get('correlationid') == '$CORR'
        and e['type'] == 'bloodbank.code.commit.landed']
print(rows[0]['id'] if rows else '')" 2>/dev/null || true)"
  [ -n "$LANDED_IN_G1" ] && break
  sleep 2
done
[ -n "$LANDED_IN_G1" ] && ok "G8's derived cycle events also delivered to the G1-side durable (no split of G8 output)" \
                          || bad "G1-side store never saw G8's cycle events"

step "verdict"
echo "passed: ${PASS}  failed: ${FAIL}"
if [ "$FAIL" -eq 0 ]; then
  echo "COEXIST RESULT: PASS — G1 + G8 share one bus; every event reaches both stores"
  exit 0
else
  echo "COEXIST RESULT: FAIL"
  exit 1
fi

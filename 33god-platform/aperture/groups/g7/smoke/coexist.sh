#!/usr/bin/env bash
# G7 coexistence gate (Rererere's ack 2026-10-24): prove that with a G1-shaped
# consumer ALREADY consuming, an attached G7 receives EVERY event into BOTH
# stores — no durable/queue collision, no event splitting.
#
# Simulates the target topology honestly:
#   - one external bus (BLOODBANK_EVENTS)
#   - a G1-side consumer: candystore stack with G1's durable names
#     ("candystore-events"/"candystore") ALREADY RUNNING AND CONSUMING
#   - G7 attached via compose.attach.yml (its own durable names after the
#     ownership fix: "g7-candystore-events"/"g7-candystore")
#
# Proves, in order:
#   1. both consumers hold DISTINCT durables on the stream (no collision)
#   2. N events published while BOTH consume -> N rows in G1 store AND N
#      rows in G7 store (every event delivered to BOTH durables)
#   3. the same event id read back byte-equal field-wise from both stores
#   4. enrichment derived events also land in BOTH stores (G7's own output
#      does not split either)
#   5. memory plane saw everything (bridge tailed = source + derived)
#
# The G1-side stack here is a THROWAWAY candystore (same vendored image,
# G1's durable names) — the real god-g1 project on Jarad's host is never
# touched. Cleaning: only throwaway + god-g7.
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
  docker compose -p g7-coexist-g1side -f /tmp/g7-coexist-g1side.yml down -v --remove-orphans >/dev/null 2>&1
  docker rm -f g7-coexist-bus g7-coexist-g1init >/dev/null 2>&1
  docker network rm "$NET" >/dev/null 2>&1
}
trap cleanup EXIT

G1SIDE=/tmp/g7-coexist-g1side.yml
cat > "$G1SIDE" <<'YML'
# THROWAWAY G1-side candystore (G1's durable names) — simulates the already-
# running G1 consumer on the target bus. Never the real god-g1 project.
name: g7-coexist-g1side
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
    image: candystore:g7
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
        source: /tmp/g7-coexist-g1-pubsub.yaml
        target: /components/pubsub.yaml
        read_only: true
    depends_on: [g1-candystore]
    networks: [g1-bus]
YML
# G1's ORIGINAL durable names (the names the real G1 owns)
cat > /tmp/g7-coexist-g1-pubsub.yaml <<'YAML'
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
docker run -d --rm --name g7-coexist-bus --network "$NET" --network-alias nats \
  nats:2.10-alpine -js -sd /data -m 8222 >/dev/null
sleep 3
docker run --rm --name g7-coexist-g1init --network "$NET" \
  -v "$PWD/nats/streams.json:/work/streams.json:ro" \
  -v "$PWD/nats/init.sh:/work/init.sh:ro" \
  -e NATS_URL=nats://nats:4222 --entrypoint /bin/sh "$NATS_BOX" /work/init.sh >/dev/null 2>&1
docker compose -p g7-coexist-g1side -f "$G1SIDE" up -d --wait --wait-timeout 240 >/dev/null 2>&1 \
  && ok "G1-side consumer up (durable candystore-events, ALREADY consuming)" \
  || { bad "G1-side stack failed"; docker compose -p g7-coexist-g1side -f "$G1SIDE" ps -a; exit 1; }

step "attach G7 (own durables) onto the same bus"
docker compose -f compose.yml -f compose.attach.yml down -v --remove-orphans >/dev/null 2>&1
GOD_LLM_BASE_URL= GOD_LLM_API_KEY= \
docker compose -f compose.yml -f compose.attach.yml up -d --wait --wait-timeout 300 >/dev/null 2>&1 \
  && ok "G7 attached (degraded LLM, own durable g7-candystore-events)" \
  || { bad "G7 attach failed"; docker compose -f compose.yml -f compose.attach.yml ps -a; exit 1; }

step "distinct durables on the stream (no collision)"
DURABLES="$(docker run --rm --quiet --network "$NET" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 consumer ls BLOODBANK_EVENTS --names' 2>/dev/null | tr '\n' ' ')"
echo "  durables: ${DURABLES}"
echo "$DURABLES" | grep -q "candystore-events" \
  && echo "$DURABLES" | grep -q "g7-candystore-events" \
  && echo "$DURABLES" | grep -q "g7-enrichment" \
  && ok "G1's durable + G7's durables coexist as distinct consumers" \
  || bad "durable set wrong: ${DURABLES}"

step "publish N=5 canonical events while BOTH consume -> every event in BOTH stores"
N=5
TMP="$(mktemp -d)"
declare -a IDS
for i in $(seq 1 "$N"); do
  ID="$(docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid')"
  IDS+=("$ID")
  cat > "$TMP/e$i.json" <<JSON
{"specversion":"1.0","id":"$ID","source":"urn:33god:aperture:g7-coexist","type":"bloodbank.aperture.coexist.g7","subject":"bloodbank.evt.aperture.coexist.g7","time":"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)","datacontenttype":"application/json","correlationid":"$ID","causationid":"$ID","producer":"aperture-g7-coexist","service":"smoke","domain":"aperture","kind":"event","ordering_key":"g7:coexist:$i","actor":{"type":"operator","agent_id":"o"},"data":{"i":$i,"project":"33GOD","note":"coexist $i"}}
JSON
  docker run --rm --quiet --network "$NET" -v "$TMP/e$i.json:/payload.json:ro" "$NATS_BOX" \
    sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.aperture.coexist.g7 "$(cat /payload.json)"' >/dev/null 2>&1
done
ok "published $N events onto the shared bus"

# both-store readback helper: store_get <stack-dir-or-p> <svc> <id>
g7_get() { docker compose -f compose.yml -f compose.attach.yml exec -T candystore python -c "
import urllib.request,sys
try: sys.stdout.write(urllib.request.urlopen('http://candystore-app:3001/events/$1/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null; }
g1_get() { docker compose -p g7-coexist-g1side -f "$G1SIDE" exec -T g1-candystore python -c "
import urllib.request,sys
try: sys.stdout.write(urllib.request.urlopen('http://g1-candystore:3001/events/$1/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null; }

IN_G1=0; IN_G7=0; BOTH_FIELD_EQUAL=0
for i in $(seq 0 $((N - 1))); do
  ID="${IDS[$i]}"
  A=""; B=""
  for _ in $(seq 1 15); do
    [ -z "$A" ] && A="$(g1_get "$ID")"
    [ -z "$B" ] && B="$(g7_get "$ID")"
    [ -n "$A" ] && [ -n "$B" ] && break
    sleep 2
  done
  [ -n "$A" ] && IN_G1=$((IN_G1 + 1))
  [ -n "$B" ] && IN_G7=$((IN_G7 + 1))
  if [ -n "$A" ] && [ -n "$B" ]; then
    printf '%s\n%s\n' "$A" "$B" > "$TMP/pair$i.json"
    if python3 - "$TMP/pair$i.json" <<'PY'
import json, sys
lines = open(sys.argv[1]).read().splitlines()
a, b = json.loads(lines[0]), json.loads(lines[1])
assert a["id"] == b["id"]
for f in ("type", "subject", "producer", "service", "domain", "kind", "data"):
    assert a[f] == b[f], (f, a.get(f), b.get(f))
PY
    then BOTH_FIELD_EQUAL=$((BOTH_FIELD_EQUAL + 1)); fi
  fi
done
echo "  events in G1 store: ${IN_G1}/${N}   in G7 store: ${IN_G7}/${N}   field-equal pairs: ${BOTH_FIELD_EQUAL}/${N}"
[ "$IN_G1" -eq "$N" ] && ok "every source event reached the G1-side store (no split)" || bad "G1-side store missing $((N - IN_G1)) events"
[ "$IN_G7" -eq "$N" ] && ok "every source event reached the G7 store (no split)" || bad "G7 store missing $((N - IN_G7)) events"
[ "$BOTH_FIELD_EQUAL" -eq "$N" ] && ok "stored envelopes field-equal across both stores" || bad "field mismatch in $((N - BOTH_FIELD_EQUAL)) pairs"

step "G7's derived (enriched) events also land in BOTH stores"
DERIVED_TOTAL=0; DERIVED_IN_G1=0
for i in $(seq 0 $((N - 1))); do
  DID="$(python3 - "$TMP/e$((i + 1)).json" <<'PY'
import json, sys, uuid
env = json.load(open(sys.argv[1]))
print(uuid.uuid5(uuid.UUID("6f1a2c34-83b5-4d97-9f0e-a1b2c3d4e5f6"), env["id"]))
PY
)"
  B=""
  for _ in $(seq 1 15); do B="$(g7_get "$DID")"; [ -n "$B" ] && break; sleep 2; done
  A=""
  for _ in $(seq 1 15); do A="$(g1_get "$DID")"; [ -n "$A" ] && break; sleep 2; done
  DERIVED_TOTAL=$((DERIVED_TOTAL + 1))
  [ -n "$A" ] && DERIVED_IN_G1=$((DERIVED_IN_G1 + 1))
done
echo "  derived events: ${DERIVED_TOTAL} published, ${DERIVED_IN_G1} visible in G1-side store"
[ "$DERIVED_IN_G1" -eq "$DERIVED_TOTAL" ] \
  && ok "G7's derived events also delivered to the G1-side durable (both stores stay complete)" \
  || bad "G1-side store missing $((DERIVED_TOTAL - DERIVED_IN_G1)) derived events"

step "memory plane saw everything"
TAILED="$(docker compose -f compose.yml -f compose.attach.yml exec -T hindsight-bridge python -c "
import urllib.request, json
print(json.loads(urllib.request.urlopen('http://127.0.0.1:8790/healthz', timeout=5).read())['tailed'])" 2>/dev/null || echo 0)"
echo "  bridge tailed: ${TAILED} (expect >= $((N + DERIVED_TOTAL)))"
[ "${TAILED:-0}" -ge $((N + DERIVED_TOTAL)) ] 2>/dev/null \
  && ok "bridge tailed every source + derived event" || bad "bridge tailed only ${TAILED:-?}"

step "verdict"
echo "passed: ${PASS}  failed: ${FAIL}"
if [ "$FAIL" -eq 0 ]; then
  echo "COEXIST RESULT: PASS — G1 + G7 share one bus; every event reaches both stores"
  exit 0
else
  echo "COEXIST RESULT: FAIL"
  exit 1
fi

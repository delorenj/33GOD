#!/usr/bin/env bash
# G7 attach-mode proof: fire the REAL path across the G1 seam.
#
# Stands up a THROWAWAY bus that is wire-identical to G1's (same nats image,
# same streams.json topology, same network name conventions — the real god-g1
# project may be down on this host), attaches G7 via compose.attach.yml, then
# proves: publish on the EXTERNAL bus -> enrichment derives + publishes back
# onto the EXTERNAL bus -> candystore (G7's) reads BOTH via dapr on the
# external bus. The standalone smoke stays authoritative for everything else.
#
# Never touches the real god-g1 project or any production stack. Cleans up
# only the throwaway + god-g7.
set -uo pipefail
cd "$(dirname "$0")/.."

PASS=0; FAIL=0
ok() { printf 'PASS: %s\n' "$*"; PASS=$((PASS + 1)); }
bad() { printf 'FAIL: %s\n' "$*"; FAIL=$((FAIL + 1)); }

NATS_BOX="${GOD_NATS_BOX_IMAGE:-natsio/nats-box:0.14.5}"
THROWAWAY_NET="g1-bus"   # same name the overlay expects (external: true)

cleanup() {
  docker compose -f compose.yml -f compose.attach.yml down -v --remove-orphans >/dev/null 2>&1
  docker rm -f g7-attach-bus g7-attach-init >/dev/null 2>&1
  docker network rm "$THROWAWAY_NET" >/dev/null 2>&1
}
trap cleanup EXIT

step() { printf '\n== %s ==\n' "$*"; }

step "stand up throwaway external bus (G1 wire-identical)"
docker network create --attachable "$THROWAWAY_NET" >/dev/null 2>&1 || true
docker run -d --rm --name g7-attach-bus --network "$THROWAWAY_NET" \
  --network-alias nats nats:2.10-alpine -js -sd /data -m 8222 >/dev/null
sleep 3
docker run --rm --name g7-attach-init --network "$THROWAWAY_NET" \
  -v "$PWD/nats/streams.json:/work/streams.json:ro" \
  -v "$PWD/nats/init.sh:/work/init.sh:ro" \
  -e NATS_URL=nats://nats:4222 --entrypoint /bin/sh "$NATS_BOX" /work/init.sh >/dev/null 2>&1
ok "throwaway bus + BLOODBANK_EVENTS up on external net ${THROWAWAY_NET}"

step "attach G7 (overlay) with EMPTY GOD_LLM_*"
docker compose -f compose.yml -f compose.attach.yml down -v --remove-orphans >/dev/null 2>&1
if docker compose -f compose.yml -f compose.attach.yml build >/dev/null 2>&1 && \
   GOD_LLM_BASE_URL= GOD_LLM_API_KEY= \
   docker compose -f compose.yml -f compose.attach.yml up -d --wait --wait-timeout 300 >/dev/null 2>&1; then
  ok "attached stack healthy (degraded LLM)"
else
  bad "attached stack failed to come up"
  docker compose -f compose.yml -f compose.attach.yml ps -a
  exit 1
fi

step "publish canonical event on the EXTERNAL bus -> derived event back onto it"
SRC_ID="$(docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid')"
CORR_ID="$(docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid')"
TMP="$(mktemp -d)"
cat > "$TMP/source.json" <<JSON
{"specversion":"1.0","id":"${SRC_ID}","source":"urn:33god:aperture:g7-smoke","type":"bloodbank.aperture.attach.g7","subject":"bloodbank.evt.aperture.attach.g7","time":"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)","datacontenttype":"application/json","correlationid":"${CORR_ID}","causationid":"${CORR_ID}","producer":"aperture-g7-smoke","service":"smoke","domain":"aperture","kind":"event","ordering_key":"g7:attach","actor":{"type":"operator","agent_id":"o"},"data":{"attach":true,"project":"33GOD"}}
JSON
docker run --rm --quiet --network "$THROWAWAY_NET" -v "$TMP/source.json:/payload.json:ro" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.aperture.attach.g7 "$(cat /payload.json)"' \
  && ok "published source event on external bus (${SRC_ID})" || bad "publish failed"

DERIVED_ID=""
for i in $(seq 1 30); do
  W="$(docker compose -f compose.yml -f compose.attach.yml exec -T enrichment python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8791/extractions', timeout=5).read().decode())" 2>/dev/null || true)"
  DERIVED_ID="$(printf '%s' "$W" | python3 -c "
import json, sys
try:
    rows = [r for r in json.load(sys.stdin).get('extractions', []) if r['source_id'] == '$SRC_ID']
    print(rows[0]['derived_id'] if rows else '')
except Exception:
    print('')" 2>/dev/null || true)"
  [ -n "$DERIVED_ID" ] && break
  sleep 2
done
[ -n "$DERIVED_ID" ] && ok "enrichment consumed from EXTERNAL bus, derived ${DERIVED_ID}" || bad "no extraction"

step "candystore readback (dapr on the external bus)"
GOT=""
for i in $(seq 1 20); do
  GOT="$(docker compose -f compose.yml -f compose.attach.yml exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/$DERIVED_ID/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  [ -n "$GOT" ] && break
  sleep 2
done
if [ -n "$GOT" ]; then
  printf '%s' "$GOT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['id'] == '$DERIVED_ID'
assert d['causationid'] == '$SRC_ID', 'chain broken across the seam'
assert d['type'] == 'bloodbank.aperture.attach.enriched'
assert d['subject'] == 'bloodbank.evt.aperture.attach.enriched'
print('readback chain OK: causationid == external source id')" \
    && ok "derived event stored via dapr on external bus, chain intact" || bad "chain verification failed"
else
  bad "candystore never stored the derived event"
fi

# bridge saw it too (tailed the external bus)
TAILED="$(docker compose -f compose.yml -f compose.attach.yml exec -T hindsight-bridge python -c "
import urllib.request, json
print(json.loads(urllib.request.urlopen('http://127.0.0.1:8790/healthz', timeout=5).read())['tailed'])" 2>/dev/null || echo 0)"
[ "${TAILED:-0}" -ge 2 ] 2>/dev/null && ok "bridge tailed >=2 events off the external bus" || bad "bridge tailed only ${TAILED:-?}"

step "verdict"
echo "passed: ${PASS}  failed: ${FAIL}"
if [ "$FAIL" -eq 0 ]; then
  echo "ATTACH RESULT: PASS — G7 seam to external bus proven with the real path"
  exit 0
else
  echo "ATTACH RESULT: FAIL"
  exit 1
fi

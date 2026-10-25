#!/usr/bin/env bash
# G8 attach-mode proof: fire the REAL cycle path across an external bus seam.
#
# Stands up a THROWAWAY bus wire-identical to G1's (same nats image, same
# streams.json topology, network name g1-bus — the real god-g1 project may be
# down on this host), attaches god-g8 via compose.attach.yml, then proves:
# the client creates a ticket through the board (which publishes on the
# EXTERNAL bus), momod consumes from the EXTERNAL bus, the code-worker's
# command + reply ride the EXTERNAL streams, and candystore (G8's) reads the
# chain via its dapr sidecar ON the external bus.
#
# Never touches the real god-g1 project or any production stack. Cleans up
# only the throwaway + god-g8.
set -uo pipefail
cd "$(dirname "$0")/.."

PASS=0; FAIL=0
ok() { printf 'PASS: %s\n' "$*"; PASS=$((PASS + 1)); }
bad() { printf 'FAIL: %s\n' "$*"; FAIL=$((FAIL + 1)); }
step() { printf '\n== %s ==\n' "$*"; }

NATS_BOX="${GOD_NATS_BOX_IMAGE:-natsio/nats-box:0.14.5}"
THROWAWAY_NET="g1-bus"   # same name the overlay expects (external: true)

cleanup() {
  docker compose -f compose.yml -f compose.attach.yml down -v --remove-orphans >/dev/null 2>&1
  docker rm -f g8-attach-bus g8-attach-init >/dev/null 2>&1
  docker network rm "$THROWAWAY_NET" >/dev/null 2>&1
}
trap cleanup EXIT

step "stand up throwaway external bus (G1 wire-identical)"
docker network create --attachable "$THROWAWAY_NET" >/dev/null 2>&1 || true
docker run -d --rm --name g8-attach-bus --network "$THROWAWAY_NET" \
  --network-alias nats nats:2.10-alpine -js -sd /data -m 8222 >/dev/null
sleep 3
docker run --rm --name g8-attach-init --network "$THROWAWAY_NET" \
  -v "$PWD/nats/streams.json:/work/streams.json:ro" \
  -v "$PWD/nats/init.sh:/work/init.sh:ro" \
  -e NATS_URL=nats://nats:4222 -e NATS_GUARD=0 \
  --entrypoint /bin/sh "$NATS_BOX" /work/init.sh >/dev/null 2>&1
# fail fast: the init above MUST leave both streams queryable (its own exit
# code is swallowed above; verify the result, not the run)
for _ in 1 2 3 4 5; do
  if docker run --rm --network "$THROWAWAY_NET" "$NATS_BOX" \
      nats --server nats://nats:4222 stream info BLOODBANK_EVENTS >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker run --rm --network "$THROWAWAY_NET" "$NATS_BOX" \
  nats --server nats://nats:4222 stream info BLOODBANK_EVENTS >/dev/null 2>&1 \
  && ok "throwaway bus + BLOODBANK_EVENTS/COMMANDS up on external net ${THROWAWAY_NET}" \
  || { bad "throwaway bus streams missing after init"; exit 1; }

step "attach G8 (overlay) with EMPTY GOD_LLM_*"
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

step "readiness canary across the seam (fresh dapr durables bind late)"
CANARY_ID="$(docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid')"
TMP="$(mktemp -d)"
cat > "$TMP/canary.json" <<JSON
{"specversion":"1.0","id":"${CANARY_ID}","source":"urn:33god:aperture:g8-attach","type":"bloodbank.aperture.canary.g8","subject":"bloodbank.evt.aperture.canary.g8","time":"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)","datacontenttype":"application/json","correlationid":"${CANARY_ID}","causationid":"${CANARY_ID}","producer":"aperture-g8-attach","service":"smoke","domain":"aperture","kind":"event","ordering_key":"g8:attach","actor":{"type":"operator","agent_id":"o"},"data":{"canary":true}}
JSON
docker run --rm --quiet --network "$THROWAWAY_NET" -v "$TMP/canary.json:/payload.json:ro" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.aperture.canary.g8 "$(cat /payload.json)"' >/dev/null 2>&1 || true
CANARY_OK=""
for ((i = 0; i < 60; i += 1)); do
  C="$(docker compose -f compose.yml -f compose.attach.yml exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/${CANARY_ID}/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  [ -n "$C" ] && { CANARY_OK=1; break; }
  sleep 2
done
[ -n "$CANARY_OK" ] && ok "canary round-tripped candystore across the seam" \
                      || bad "canary never reached candystore within 120s"

step "THE CYCLE across the external bus"
TITLE="attach mode ticket for G8"
CREATE="$(docker compose -f compose.yml -f compose.attach.yml exec -T board python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8793/command',
    data=json.dumps({'action': 'create', 'title': '''$TITLE'''}).encode(),
    headers={'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=15).read().decode())")"
TICKET_ID="$(printf '%s' "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['ticket']['id'])" 2>/dev/null || true)"
CORR="$(printf '%s' "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['ticket']['correlationid'])" 2>/dev/null || true)"
[ -n "$TICKET_ID" ] && ok "ticket created on the EXTERNAL bus (${TICKET_ID})" || bad "create failed"

CYCLE_DONE=""
for ((i = 0; i < 120; i += 1)); do
  MC="$(docker compose -f compose.yml -f compose.attach.yml exec -T momod python -c "
import urllib.request
try: print(urllib.request.urlopen('http://127.0.0.1:8795/cycles', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  CYCLE_DONE="$(printf '%s' "$MC" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    rows = [r for r in d.get('cycles', []) if r['ticket_id'] == '$TICKET_ID' and r['state'] == 'done']
    print(rows[0]['commit_sha'] if rows else '')
except Exception: print('')" 2>/dev/null || true)"
  [ -n "$CYCLE_DONE" ] && break
  sleep 2
done
[ -n "$CYCLE_DONE" ] && ok "full cycle completed ON the external bus (commit ${CYCLE_DONE:0:12})" \
                        || { bad "cycle never completed"; docker compose -f compose.yml -f compose.attach.yml logs momod --since 5m 2>&1 | tail -8 | sed 's/^/  /'; }

step "chain stored via dapr on the external bus"
GOT=""
for ((i = 0; i < 20; i += 1)); do
  # the completed event's id is unknown here; find it via the correlationid
  E="$(docker compose -f compose.yml -f compose.attach.yml exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events?limit=50', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  GOT="$(printf '%s' "$E" | python3 -c "
import json, sys
d = json.load(sys.stdin)
rows = [e for e in d.get('events', []) if e.get('correlationid') == '$CORR'
        and e['type'] == 'bloodbank.task.ticket.completed']
print(rows[0]['id'] if rows else '')" 2>/dev/null || true)"
  [ -n "$GOT" ] && break
  sleep 2
done
if [ -n "$GOT" ]; then
  RAW="$(docker compose -f compose.yml -f compose.attach.yml exec -T candystore python -c "
import urllib.request
print(urllib.request.urlopen('http://candystore-app:3001/events/$GOT/raw', timeout=5).read().decode())")"
  printf '%s' "$RAW" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['correlationid'] == '$CORR', 'correlation broken across seam'
assert d['data']['commit_sha'] == '$CYCLE_DONE', 'commit sha broken across seam'
assert d['data']['tests_passed'] is True
print('  completed event intact across the seam (chain + evidence)')" \
    && ok "chain intact across the seam: one correlationid, commit evidence" \
    || bad "chain verification failed across seam"
else
  bad "candystore never stored the completed event"
fi

step "verdict"
echo "passed: ${PASS}  failed: ${FAIL}"
if [ "$FAIL" -eq 0 ]; then
  echo "ATTACH RESULT: PASS — G8 real cycle proven across the external-bus seam"
  exit 0
else
  echo "ATTACH RESULT: FAIL"
  exit 1
fi

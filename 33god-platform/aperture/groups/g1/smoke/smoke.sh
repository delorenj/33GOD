#!/usr/bin/env bash
# Aperture G1 smoke test — bring-up check + full bus round-trip proof.
#
# Proves, in order:
#   1. Every service reaches its healthy/running state (nats, nats-init
#      exit 0, candystore-postgres, candystore, candystore-daprd).
#   2. The JetStream topology exists (BLOODBANK_EVENTS stream).
#   3. A CloudEvent published DIRECTLY to the NATS subject candystore
#      subscribes to (bloodbank.evt.>) is captured by the stream and
#      delivered by the Dapr sidecar to the app's POST /events/all.
#   4. The query API serves back the SAME envelope (id/type/producer/data),
#      read through the network alias — not by peeking at the database.
#
# Everything runs inside the bundle's own networks; no host ports exist.
# The script never tears the stack down — run `docker compose down` after.
#
# Usage:  bash smoke/smoke.sh          (from anywhere; it cds to the bundle root)
# Exit:   0 = PASS, 1 = FAIL

set -uo pipefail

cd "$(dirname "$0")/.."   # bundle root (where compose.yml lives)

PROJECT="god-g1"
NATS_BOX_IMAGE="${GOD_NATS_BOX_IMAGE:-natsio/nats-box:0.14.5}"
NATS_URL="${GOD_NATS_URL:-nats://nats:4222}"
TOPIC="bloodbank.evt.aperture.smoke.ping"   # NATS subject (5 tokens, kind marker)
CE_TYPE="bloodbank.aperture.smoke.ping"     # CloudEvents type (4 tokens, canonical §2)

PASS=0
FAIL=0
step() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
ok()   { printf 'PASS: %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf 'FAIL: %s\n' "$*"; FAIL=$((FAIL + 1)); }

# ---------------------------------------------------------------- helpers ----
# Id of a compose service's container (works for exited one-shots too).
cid() { docker compose ps -aq "$1" 2>/dev/null | head -1; }

wait_state() {  # wait_state <service> <running|exited> [timeout]
  local svc="$1" want="$2" timeout="${3:-90}" i st
  for ((i = 0; i < timeout; i += 2)); do
    st="$(docker inspect --format '{{.State.Status}}' "$(cid "$svc")" 2>/dev/null || true)"
    [ "$st" = "$want" ] && return 0
    sleep 2
  done
  return 1
}

wait_healthy() {  # wait_healthy <service> [timeout]
  local svc="$1" timeout="${2:-90}" i st
  for ((i = 0; i < timeout; i += 2)); do
    st="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$(cid "$svc")" 2>/dev/null || true)"
    [ "$st" = "healthy" ] && return 0
    sleep 2
  done
  return 1
}

# HTTP GET from inside the candystore container, via the network alias
# (real DNS + TCP hop, not loopback). Echoes the body; fails non-zero.
candystore_get() {  # candystore_get <path>
  docker compose exec -T candystore python -c \
    "import urllib.request,sys;
r=urllib.request.urlopen('http://candystore-app:3001$1',timeout=5);
sys.stdout.write(r.read().decode())" 2>/dev/null
}

# ------------------------------------------------------- 1. bring-up check ----
step "1/5 bring-up: waiting for services (project ${PROJECT})"

if wait_healthy nats; then ok "nats is healthy"; else bad "nats never became healthy"; fi
if wait_state nats-init exited 60 && \
   [ "$(docker inspect --format '{{.State.ExitCode}}' "$(cid nats-init)")" = "0" ]; then
  ok "nats-init completed with exit 0 (streams applied)"
else
  bad "nats-init did not exit 0"
fi
if wait_healthy candystore-postgres; then ok "candystore-postgres is healthy"; else bad "candystore-postgres never became healthy"; fi
if wait_healthy candystore; then ok "candystore is healthy (/readyz)"; else bad "candystore never became healthy"; fi
if wait_state candystore-daprd running; then ok "candystore-daprd is running"; else bad "candystore-daprd is not running"; fi

# Dapr sidecar readiness (it has no shell; probe its HTTP healthz from the
# candystore container over the g1-internal network).
DAPRD_READY=0
for ((i = 0; i < 30; i += 1)); do
  if docker compose exec -T candystore python -c \
      "import urllib.request; urllib.request.urlopen('http://candystore-daprd:3500/v1.0/healthz',timeout=3)" \
      >/dev/null 2>&1; then DAPRD_READY=1; break; fi
  sleep 2
done
if [ "$DAPRD_READY" = "1" ]; then ok "candystore-daprd :3500/v1.0/healthz responds"; else bad "candystore-daprd healthz never responded"; fi

echo "--- docker compose ps ---"
docker compose ps

# ------------------------------------------------------ 2. stream topology ----
step "2/5 JetStream topology: BLOODBANK_EVENTS must exist"
STREAM_INFO="$(docker run --rm --quiet --network g1-bus "$NATS_BOX_IMAGE" \
  nats --server "$NATS_URL" stream info BLOODBANK_EVENTS 2>&1 || true)"
echo "$STREAM_INFO" | sed -n '1,12p'
if echo "$STREAM_INFO" | grep -q "Subjects: bloodbank.evt.>"; then
  ok "stream BLOODBANK_EVENTS present with subject bloodbank.evt.>"
else
  bad "stream BLOODBANK_EVENTS missing or wrong subjects"
fi

# ------------------------------------------------------------- 3. publish ----
step "3/5 publish test CloudEvent straight onto NATS subject ${TOPIC}"
# Portable UUIDs: /proc/sys/kernel/random/uuid is Linux-only on the HOST
# (Damian acceptance: macOS has no /proc). The nats-box container itself is
# Linux regardless of host OS — generate inside it.
gen_uuid() { docker run --rm --quiet --entrypoint sh "$NATS_BOX_IMAGE" -c 'cat /proc/sys/kernel/random/uuid'; }
EVENT_ID="$(gen_uuid)"
CORRELATION_ID="$(gen_uuid)"
EVENT_TIME="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"

TMPDIR_SMOK="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_SMOK"' EXIT
PAYLOAD="$TMPDIR_SMOK/envelope.json"
cat > "$PAYLOAD" <<JSON
{
  "specversion": "1.0",
  "id": "${EVENT_ID}",
  "source": "urn:33god:aperture:g1-smoke",
  "type": "${CE_TYPE}",
  "subject": "${TOPIC}",
  "time": "${EVENT_TIME}",
  "datacontenttype": "application/json",
  "correlationid": "${CORRELATION_ID}",
  "causationid": "${CORRELATION_ID}",
  "producer": "aperture-g1-smoke",
  "service": "smoke",
  "domain": "aperture",
  "traceparent": "00-00000000000000000000000000000000-0000000000000000-00",
  "kind": "event",
  "actor": {"type": "operator", "agent_id": "operator:aperture-g1-smoke", "cli": null, "provider": null, "model": null},
  "ordering_key": "aperture:g1-smoke",
  "data": {"source_id": "aperture-g1-smoke", "sequence": 1, "ping": true, "via": "nats-direct"}
}
JSON

echo "envelope id: ${EVENT_ID}"
docker run --rm --quiet \
  --network g1-bus \
  -v "$PAYLOAD":/payload.json:ro \
  "$NATS_BOX_IMAGE" \
  sh -c 'nats --server nats://nats:4222 pub "$1" "$(cat /payload.json)" && echo published: "$(cat /payload.json | head -c 80)..."' \
  sh "$TOPIC"
if [ $? -eq 0 ]; then ok "CloudEvent published to ${TOPIC} via NATS (nats-box, in-network)"; else bad "NATS publish failed"; fi

# ----------------------------------------------- 4. wait for Dapr delivery ----
step "4/5 wait for Dapr delivery + storage (poll GET /events/<id>/raw, up to 60s)"
STORED=""
for ((i = 0; i < 30; i += 1)); do
  STORED="$(candystore_get "/events/${EVENT_ID}/raw" || true)"
  [ -n "$STORED" ] && break
  sleep 2
done
if [ -n "$STORED" ]; then
  ok "query API returned the stored raw envelope for id ${EVENT_ID}"
else
  bad "event ${EVENT_ID} never appeared in the query API"
fi

# ----------------------------------------------------------- 5. round-trip ----
step "5/5 assert round-trip fidelity (envelope served == envelope published)"
if [ -n "$STORED" ]; then
  STORED_JSON="$TMPDIR_SMOK/stored.json"
  printf '%s' "$STORED" > "$STORED_JSON"
  python3 - "$STORED_JSON" "$EVENT_ID" "$CE_TYPE" "$CORRELATION_ID" <<'PY' && ok "envelope matches: id, type, subject, correlationid, producer, data.ping" || bad "stored envelope differs from the published one"
import json, sys
path, expected_id, expected_type, expected_corr = sys.argv[1:5]
env = json.load(open(path))
assert env["id"] == expected_id, f"id mismatch: {env.get('id')}"
assert env["type"] == expected_type, f"type mismatch: {env.get('type')}"
assert env["subject"] == "bloodbank.evt." + expected_type.split(".", 1)[1], "subject mismatch"
assert env["correlationid"] == expected_corr, "correlationid mismatch"
assert env["producer"] == "aperture-g1-smoke", f"producer mismatch: {env.get('producer')}"
assert env["data"]["ping"] is True and env["data"]["via"] == "nats-direct", "data mismatch"
print("evidence (stored raw envelope):")
print(json.dumps(env, indent=2)[:900])
PY
  echo
  echo "evidence (stream state after publish):"
  docker run --rm --quiet --network g1-bus "$NATS_BOX_IMAGE" \
    nats --server "$NATS_URL" stream info BLOODBANK_EVENTS 2>/dev/null | grep -E 'Messages|Last Sequence|Subjects' || true
else
  bad "round-trip assertion skipped (no stored envelope)"
fi

# ------------------------------------------------------------- verdict -------
step "verdict"
echo "passed: ${PASS}  failed: ${FAIL}"
if [ "$FAIL" -eq 0 ]; then
  echo "SMOKE RESULT: PASS — G1 bus round-trip proven (NATS → JetStream → Dapr → candystore → query API)"
  exit 0
else
  echo "SMOKE RESULT: FAIL"
  exit 1
fi

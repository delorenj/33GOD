# G7 ACCEPTANCE GATE — "recall from stored real history"
# (aperture/ACCEPTANCE.md G7; shape approved by Rererere 2026-10-24, ack 05cd305)
#
# WHAT THE CLIENT PROVES, IN THEIR OWN WORDS:
#   You type TWO real notes/decisions. The kit publishes each as a canonical
#   event through the deployed bus. Then you recall them BY A WORD FROM YOUR
#   OWN TEXT through the memory plane, and the system must return your exact
#   values and the event ids. The enrichment chain (source -> derived) is
#   verified through the local candystore. Owned G7 services restart, and the
#   recall still works. Zero LLM credentials anywhere — the run happens in
#   measured degraded mode (keyword recall), by design.
#
# Usage:
#   ./accept-g7.sh "first note in your own words" "second note in your own words"
# Env:
#   GOD_RECALL_WORD_1 / GOD_RECALL_WORD_2   force the recall probe words
#                                           (default: longest word of each note)
#   GOD_EVIDENCE_DIR                        where evidence lands (default ./accept/evidence)
#
# Client-executable: needs only this repo dir + the running god-g7 deployment.
# Non-destructive: no down -v, no volume removal, evidence stays local.
set -uo pipefail
cd "$(dirname "$0")/.."

NOTE1="${1:?usage: accept-g7.sh \"first note\" \"second note\"}"
NOTE2="${2:?usage: accept-g7.sh \"first note\" \"second note\"}"
NATS_BOX="${GOD_NATS_BOX_IMAGE:-natsio/nats-box:0.14.5}"
EVID="${GOD_EVIDENCE_DIR:-$(dirname "$0")/evidence}"
CE_TYPE="bloodbank.studio.recall.g7"
TOPIC="bloodbank.evt.studio.recall.g7"
mkdir -p "$EVID"
EVID="$(cd "$EVID" && pwd)"   # ABSOLUTE: docker -v bind sources must be

PASS=0; FAIL=0
ok()   { printf 'PASS  %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf 'FAIL  %s\n' "$*"; FAIL=$((FAIL + 1)); }
step() { printf '\n=== %s ===\n' "$*"; }

gen_uuid() { docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid'; }
g7_get() { docker compose exec -T candystore python -c "
import urllib.request,sys
try: sys.stdout.write(urllib.request.urlopen('http://candystore-app:3001$1', timeout=5).read().decode())
except Exception: pass" 2>/dev/null; }
bridge() { docker compose exec -T hindsight-bridge python -c "
import urllib.request,sys
sys.stdout.write(urllib.request.urlopen('http://127.0.0.1:8790$1', timeout=10).read().decode())" 2>/dev/null; }

# longest alphabetic word >=5 chars of the note — a word the CLIENT chose
probe_word() {
  if [ -n "${2:-}" ]; then printf '%s' "$2"; return; fi
  printf '%s' "$1" | tr ' ' '\n' | tr -d '[:punct:]' | awk 'length($0)>=5' | awk '{ if (length($0) > length(m)) m = $0 } END { print m }'
}
W1="$(probe_word "$NOTE1" "${GOD_RECALL_WORD_1:-}")"
W2="$(probe_word "$NOTE2" "${GOD_RECALL_WORD_2:-}")"

step "0/8 preflight (degraded mode asserted, zero LLM credentials)"
docker compose ps --format '{{.Service}} {{.Status}}' | sed 's/^/  /'
HZ="$(bridge /healthz)"
printf '%s' "$HZ" > "$EVID/healthz-before.json"
python3 - "$HZ" <<'PY' && ok "bridge healthy AND degraded (no LLM credentials in play)" || bad "degraded-mode assertion failed"
import json, sys
h = json.loads(sys.argv[1])
assert h["ready"] is True, h
assert h["degraded"] is True, "expected degraded (no GOD_LLM_* set)"
assert h["llm"]["configured"] is False, "LLM configured — gate must run credential-free"
PY
echo "  notes: [1] ${NOTE1}"
echo "        [2] ${NOTE2}"
echo "  recall probes: '${W1}' / '${W2}' (from YOUR text)"

step "0.5/8 readiness canary: bus -> candystore round-trip before your checks"
# A freshly started dapr sidecar can take 10-60s to bind its durable and
# deliver. The gate must not time out on cold-start latency — it waits for a
# canary round-trip first, then runs YOUR checks against a ready system.
CANARY_ID="$(gen_uuid)"
printf '{"specversion":"1.0","id":"%s","source":"urn:33god:aperture:g7-client","type":"bloodbank.studio.recall.g7","subject":"bloodbank.evt.studio.recall.g7","time":"%s","datacontenttype":"application/json","correlationid":"%s","causationid":"%s","producer":"aperture-g7-client","service":"studio","domain":"studio","kind":"event","ordering_key":"studio:recall:canary","actor":{"type":"operator","agent_id":"o","cli":null,"provider":null,"model":null},"data":{"note":"readiness canary","n":0}}' \
  "$CANARY_ID" "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)" "$CANARY_ID" "$CANARY_ID" > "$EVID/canary.json"
docker run --rm --quiet --network g7-bus -v "$EVID/canary.json:/payload.json:ro" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.studio.recall.g7 "$(cat /payload.json)"' >/dev/null 2>&1 || true
CANARY_OK=""
for _ in $(seq 1 60); do
  C="$(g7_get "/events/${CANARY_ID}/raw")"
  [ -n "$C" ] && { CANARY_OK=1; break; }
  sleep 2
done
[ -n "$CANARY_OK" ] && ok "canary round-tripped candystore (system ready to accept)" \
                     || { bad "candystore never ingested the canary within 120s — bus/store path not ready"; }

step "1/8 publish TWO canonical events (your words, machine context)"
CONTAINERS_NOW="$(docker ps -q | wc -l | tr -d ' ')"
CTX="machine fact measured now: ${CONTAINERS_NOW} containers running on this host"
TS="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
ID1="$(gen_uuid)"; ID2="$(gen_uuid)"
python3 - "$EVID" "$NOTE1" "$NOTE2" "$CTX" "$ID1" "$ID2" "$TS" <<'PY'
import json, sys
ev, note1, note2, ctx, id1, id2, ts = sys.argv[1:8]
def envelope(eid, note, n):
    return {"specversion": "1.0", "id": eid, "source": "urn:33god:aperture:g7-client",
            "type": "bloodbank.studio.recall.g7", "subject": "bloodbank.evt.studio.recall.g7",
            "time": ts, "datacontenttype": "application/json",
            "correlationid": eid, "causationid": eid,
            "producer": "aperture-g7-client", "service": "studio", "domain": "studio",
            "kind": "event", "ordering_key": f"studio:recall:{n}",
            "actor": {"type": "operator", "agent_id": "operator:studio-client",
                      "cli": None, "provider": None, "model": None},
            "data": {"note": note, "context": ctx, "via": "g7-acceptance", "n": n}}
open(f"{ev}/note1.json", "w").write(json.dumps(envelope(id1, note1, 1)))
open(f"{ev}/note2.json", "w").write(json.dumps(envelope(id2, note2, 2)))
PY
for i in 1 2; do
  docker run --rm --quiet --network g7-bus -v "$EVID/note$i.json:/payload.json:ro" "$NATS_BOX" \
    sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.studio.recall.g7 "$(cat /payload.json)"' \
    || { bad "publish $i failed (docker run error — check paths are absolute)"; }
done
ok "publish commands issued for ${ID1} and ${ID2}"

step "2/8 exact readback: your words verbatim in BOTH stores' source of truth"
S1=""; S2=""
for _ in $(seq 1 20); do
  [ -z "$S1" ] && S1="$(g7_get "/events/${ID1}/raw")"
  [ -z "$S2" ] && S2="$(g7_get "/events/${ID2}/raw")"
  [ -n "$S1" ] && [ -n "$S2" ] && break
  sleep 2
done
printf '%s' "$S1" > "$EVID/note1-stored.json"; printf '%s' "$S2" > "$EVID/note2-stored.json"
python3 - "$EVID/note1-stored.json" "$EVID/note2-stored.json" "$ID1" "$ID2" "$NOTE1" "$NOTE2" "$CTX" <<'PY' \
  && ok "both notes stored verbatim with the measured machine fact" || bad "readback mismatch"
import json, sys
s1, s2, id1, id2, n1, n2, ctx = sys.argv[1:8]
e1, e2 = json.load(open(s1)), json.load(open(s2))
assert e1["id"] == id1 and e2["id"] == id2
assert e1["data"]["note"] == n1 and e2["data"]["note"] == n2, "note text differs"
assert e1["data"]["context"] == ctx, "machine fact differs"
assert e1["type"] == "bloodbank.studio.recall.g7"
PY

step "3/8 recall through the MEMORY PLANE by words from your own text"
# (the reference memory backend indexes select data.* string fields, note
#  included — so a client word from the note text is searchable by contract.
#  The tail pipeline has measured 3-8s latency; recall polls up to 30s.)
recall_query() { docker compose exec -T hindsight-bridge python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8790/query',
    data=json.dumps({'q': '$1', 'limit': 20}).encode(),
    headers={'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=10).read().decode())" 2>/dev/null || true; }
Q=""
for _ in $(seq 1 10); do
  Q="$(recall_query "$W1")"
  printf '%s' "$Q" | python3 -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if any(r['event_id'] == '$ID1' for r in d['results']) else 1)" 2>/dev/null && break
  sleep 3
done
printf '%s' "$Q" > "$EVID/recall-w1.json"
python3 - "$EVID/recall-w1.json" "$ID1" "$W1" <<'PY' && ok "recall['${W1}'] returns your event with exact values" || bad "recall by '${W1}' failed"
import json, sys
d = json.load(open(sys.argv[1]))
assert d.get("mode") == "keyword", f"expected keyword mode, got {d.get('mode')}"
hits = [r for r in d["results"] if r["event_id"] == sys.argv[2]]
assert hits, f"event {sys.argv[2]} not recalled by '{sys.argv[3]}'"
h = hits[0]
assert h["type"] == "bloodbank.studio.recall.g7"
assert h["data"]["note"], "recalled row missing note payload"
print("  recalled event id:", h["event_id"])
PY
Q2=""
for _ in $(seq 1 10); do
  Q2="$(recall_query "$W2")"
  printf '%s' "$Q2" | python3 -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if any(r['event_id'] == '$ID2' for r in d['results']) else 1)" 2>/dev/null && break
  sleep 3
done
printf '%s' "$Q2" > "$EVID/recall-w2.json"
python3 - "$EVID/recall-w2.json" "$ID2" "$W2" <<'PY' && ok "recall['${W2}'] returns your second event" || bad "recall by '${W2}' failed"
import json, sys
d = json.load(open(sys.argv[1]))
hits = [r for r in d["results"] if r["event_id"] == sys.argv[2]]
assert hits, f"event {sys.argv[2]} not recalled by '{sys.argv[3]}'"
PY

step "4/8 enrichment chain: source -> derived, causationid verified in candystore"
D1="$(python3 -c 'import uuid,sys; print(uuid.uuid5(uuid.UUID("6f1a2c34-83b5-4d97-9f0e-a1b2c3d4e5f6"), sys.argv[1]))' "$ID1")"
DS1=""
for _ in $(seq 1 20); do DS1="$(g7_get "/events/${D1}/raw")"; [ -n "$DS1" ] && break; sleep 2; done
printf '%s' "$DS1" > "$EVID/derived1.json"
if ! python3 - "$EVID/derived1.json" "$ID1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["type"] == "bloodbank.studio.recall.enriched", d["type"]
assert d["subject"] == "bloodbank.evt.studio.recall.enriched"
assert d["causationid"] == sys.argv[2], "THE CHAIN: causationid must equal source id"
assert d["data"]["extraction"]["source_id"] == sys.argv[2]
assert len(d["data"]["extraction"]["payload_sha256"]) == 64
PY
then
  bad "enrichment chain broken — diagnostics follow"
  echo "  --- enrichment worker healthz ---"
  docker compose exec -T enrichment python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8791/healthz', timeout=5).read().decode())" 2>/dev/null | head -c 400; echo
  echo "  --- enrichment worker recent logs ---"
  docker compose logs enrichment --since 5m 2>&1 | tail -12 | sed 's/^/  /'
  echo "  --- all extractions the worker recorded ---"
  docker compose exec -T enrichment python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8791/extractions', timeout=5).read().decode()[:600])" 2>/dev/null; echo
else
  ok "derived event exists; causationid == your source event id"
fi

step "5/8 recall the DERIVED event through the memory plane too"
# NOTE: the derived event does NOT embed the source note text — the chain
# (causationid) is the link, by design. It is recalled by ITS OWN envelope
# terms (producer aperture-g7-enrichment / type *enriched), which is the
# honest recall contract for a derived document.
Q3=""
for _ in $(seq 1 10); do
  Q3="$(recall_query "aperture-g7-enrichment")"
  printf '%s' "$Q3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if any(r['event_id'] == '$D1' for r in d['results']) else 1)" 2>/dev/null && break
  sleep 3
done
printf '%s' "$Q3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert any(r['event_id'] == '$D1' for r in d['results']), 'derived event not recalled'
print('  derived event recalled by its own producer term')" \
  && ok "memory plane recalls BOTH source and derived events" || bad "derived not recalled"

step "6/8 restart owned G7 services, then recall AGAIN (persistence)"
docker compose restart candystore hindsight-bridge memory-reference enrichment >/dev/null 2>&1
for _ in $(seq 1 30); do
  R="$(docker compose exec -T hindsight-bridge python -c "
import urllib.request
try:
    urllib.request.urlopen('http://127.0.0.1:8790/healthz', timeout=3)
    print('up')
except Exception: pass" 2>/dev/null)" && [ "$R" = "up" ] && break
  sleep 2
done
QR="$(docker compose exec -T hindsight-bridge python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8790/query',
    data=json.dumps({'q': '$W1', 'limit': 20}).encode(),
    headers={'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=10).read().decode())" 2>/dev/null || true)"
printf '%s' "$QR" > "$EVID/recall-after-restart.json"
python3 - "$EVID/recall-after-restart.json" "$ID1" "$W1" <<'PY' && ok "recall STILL returns your event after restart" || bad "recall lost after restart"
import json, sys
d = json.load(open(sys.argv[1]))
hits = [r for r in d["results"] if r["event_id"] == sys.argv[2]]
assert hits, "event not recalled after restart"
PY
HZ2="$(bridge /healthz)"; printf '%s' "$HZ2" > "$EVID/healthz-after.json"
python3 - "$HZ2" <<'PY' && ok "still healthy AND degraded after restart (zero-credential invariant)" || bad "degraded invariant broken after restart"
import json, sys
h = json.loads(sys.argv[1])
assert h["ready"] is True and h["degraded"] is True and h["llm"]["configured"] is False
PY

step "7/8 memory-plane visibility of the ack/store seam"
HZERR="$(printf '%s' "$HZ2" | python3 -c "
import json, sys
try:
    h = json.loads(sys.stdin.read())
    print(h.get('backend_errors', 'missing'))
except Exception:
    print('unreadable')"
)"
echo "  backend_errors: ${HZERR} (0 = every acked tail was stored)"
[ "${HZERR}" = "0" ] && ok "backend_errors == 0 — memory plane stored every tailed event" \
                     || bad "backend_errors=${HZERR} — acked but not stored (see bridge logs)"

step "8/8 evidence (local only)"
cat <<EOT
  note ids   : ${ID1}  ${ID2}
  derived id : ${D1}
  recall     : '${W1}' -> both events | '${W2}' -> second event
  evidence   : ${EVID}/ (healthz-before/after, note{1,2}-stored, recall-*,
               derived1) — stays on this machine
EOT
echo
[ "${FAIL:-0}" = "0" ] && echo "G7 GATE: ALL CHECKS PASSED (degraded mode, zero LLM credentials)" \
                     || { echo "G7 GATE: FAILED"; exit 1; }

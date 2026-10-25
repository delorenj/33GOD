#!/usr/bin/env bash
# G8 ACCEPTANCE GATE — "Momo closes a real ticket with real code"
# (aperture/ACCEPTANCE.md G8; client-executable kit)
#
# WHAT THE CLIENT PROVES, IN THEIR OWN WORDS:
#   You type ONE real small task (your own title, e.g. "add one acceptance
#   doc page"). You do nothing else. The deployed orchestrator takes it from
#   there: the ticket goes backlog -> in_progress -> done, closed BY EVIDENCE
#   — a real commit exists in the code lane's real git repo, real tests
#   passed. You then verify with your own eyes: the board state, the commit
#   in the repo, the dashboard showing the completed item, and the entire
#   event chain in candystore under ONE correlationid. Zero LLM credentials
#   anywhere — the run happens in measured degraded mode (deterministic
#   evidence review), by design.
#
# Usage:
#   ./accept-g8.sh "your real small task title"
# Env:
#   GOD_EVIDENCE_DIR     where evidence lands (default ./accept/evidence)
#
# Client-executable: needs only this repo dir + the running god-g8 deployment.
# Non-destructive: no down -v, no volume removal, evidence stays local.
set -uo pipefail
cd "$(dirname "$0")/.."

TITLE="${1:?usage: accept-g8.sh \"your real small task title\"}"
EVID="${GOD_EVIDENCE_DIR:-$(dirname "$0")/evidence}"
mkdir -p "$EVID"
EVID="$(cd "$EVID" && pwd)"   # ABSOLUTE: docker -v bind sources must be

PASS=0; FAIL=0
ok()   { printf 'PASS  %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf 'FAIL  %s\n' "$*"; FAIL=$((FAIL + 1)); }
step() { printf '\n=== %s ===\n' "$*"; }

step "0/8 preflight (degraded mode asserted, zero LLM credentials)"
docker compose ps --format '{{.Service}} {{.Status}}' | sed 's/^/  /'
MH="$(docker compose exec -T momod python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8795/healthz', timeout=5).read().decode())" 2>/dev/null || true)"
printf '%s' "$MH" > "$EVID/momod-healthz-before.json"
python3 - "$MH" <<'PY' && ok "momod healthy AND degraded (deterministic review; no LLM credentials in play)" || bad "degraded-mode assertion failed"
import json, sys
h = json.loads(sys.argv[1])
assert h["bus"] == "connected", h
assert h["degraded"] is True, "expected degraded (no GOD_LLM_* set)"
assert "GOD_LLM_BASE_URL" in h["degraded_reason"], h
assert h["review_mode"] == "deterministic", h
PY
echo "  your task: ${TITLE}"

step "0.5/8 readiness canary: bus -> candystore round-trip before your checks"
NATS_BOX="${GOD_NATS_BOX_IMAGE:-natsio/nats-box:0.14.5}"
CANARY_ID="$(docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid')"
printf '{"specversion":"1.0","id":"%s","source":"urn:33god:aperture:g8-client","type":"bloodbank.aperture.canary.g8","subject":"bloodbank.evt.aperture.canary.g8","time":"%s","datacontenttype":"application/json","correlationid":"%s","causationid":"%s","producer":"aperture-g8-client","service":"studio","domain":"aperture","kind":"event","ordering_key":"aperture:canary","actor":{"type":"operator","agent_id":"o"},"data":{"canary":true}}' \
  "$CANARY_ID" "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)" "$CANARY_ID" "$CANARY_ID" > "$EVID/canary.json"
# resolve the ACTIVE bus network (standalone g8-bus or attached g1-bus)
NET="g8-bus"
docker network inspect g1-bus >/dev/null 2>&1 && NET="g1-bus"
docker run --rm --quiet --network "$NET" -v "$EVID/canary.json:/payload.json:ro" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.aperture.canary.g8 "$(cat /payload.json)"' >/dev/null 2>&1 || true
CANARY_OK=""
for _ in $(seq 1 60); do
  C="$(docker compose exec -T candystore python -c "
import urllib.request
try: sys.stdout.write(urllib.request.urlopen('http://candystore-app:3001/events/${CANARY_ID}/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null)"
  [ -n "$C" ] && { CANARY_OK=1; break; }
  sleep 2
done
[ -n "$CANARY_OK" ] && ok "canary round-tripped candystore (system ready to accept your task)" \
                       || bad "candystore never ingested the canary within 120s — bus/store path not ready"

step "1/8 YOU initiate: create the real ticket (this is the only human step)"
CREATE="$(docker compose exec -T board python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8793/command',
    data=json.dumps({'action': 'create', 'title': '''$TITLE'''}).encode(),
    headers={'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=15).read().decode())" 2>/dev/null || true)"
printf '%s' "$CREATE" > "$EVID/create.json"
TICKET_ID="$(printf '%s' "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['ticket']['id'])" 2>/dev/null || true)"
CORR="$(printf '%s' "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['ticket']['correlationid'])" 2>/dev/null || true)"
if [ -n "$TICKET_ID" ] && [ -n "$CORR" ]; then
  ok "ticket created in backlog — yours: ${TICKET_ID}"
  echo "  correlationid for the whole cycle: ${CORR}"
else
  bad "ticket create failed (is the stack up?)"
fi

step "2/8 the orchestrator closes it BY EVIDENCE (you wait, hands off)"
CYCLE_DONE=""
for _ in $(seq 1 120); do
  MC="$(docker compose exec -T momod python -c "
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
if [ -n "$CYCLE_DONE" ]; then
  ok "momod closed your ticket by evidence: commit ${CYCLE_DONE:0:12}"
else
  bad "the orchestrator never completed your ticket"
  echo "  --- momod logs (last 20) ---"
  docker compose logs momod --since 10m 2>&1 | grep -v "GET /" | tail -20 | sed 's/^/  /'
fi

step "3/8 board state matches repo evidence (px-shaped check: state == git log)"
BT="$(docker compose exec -T board python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8793/ticket/$TICKET_ID', timeout=5).read().decode())" 2>/dev/null || true)"
printf '%s' "$BT" > "$EVID/board-ticket.json"
SHOW="$(docker compose exec -T code-worker sh -c "cd /data/workbench && git show --stat $CYCLE_DONE 2>&1 | head -6" 2>/dev/null || true)"
printf '%s' "$SHOW" > "$EVID/git-show.txt"
python3 - "$EVID/board-ticket.json" "$CYCLE_DONE" <<'PY' && ok "board: done + commit + tests; the commit resolves in the REAL repo" || bad "board/repo evidence mismatch"
import json, sys
t = json.load(open(sys.argv[1]))["ticket"]
assert t["state"] == "done", t
assert t["commit_sha"] == sys.argv[2], (t["commit_sha"], sys.argv[2])
assert t["tests_passed"] is True, t
print("  board state:", t["state"], "| commit:", t["commit_sha"][:12], "| tests: pass")
PY
# git show prints a SHORT sha; assert the short prefix + the 2-file stat
SHORT_SHA="$(printf '%s' "$CYCLE_DONE" | cut -c1-7)"
head -1 "$EVID/git-show.txt" | grep -q "^${SHORT_SHA}" \
  && grep -q "2 files changed" "$EVID/git-show.txt" \
  && ok "git show: your task's module + test landed (2 files)" \
  || bad "git show output unexpected (see evidence/git-show.txt)"

step "4/8 the dashboard displays your completed work item"
DASH_OK=""
for _ in $(seq 1 30); do
  DI="$(docker compose exec -T dashboard python -c "
import urllib.request
try: print(urllib.request.urlopen('http://127.0.0.1:8796/api/items', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  printf '%s' "$DI" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    rows = [it for it in d.get('items', []) if it['ticket_id'] == '$TICKET_ID'
            and it['state'] == 'done' and it.get('commit_sha')]
    sys.exit(0 if rows else 1)
except Exception: sys.exit(1)" 2>/dev/null && { DASH_OK=1; break; }
  sleep 2
done
printf '%s' "$DI" > "$EVID/dashboard-items.json"
[ -n "$DASH_OK" ] && ok "dashboard shows YOUR item: done, with commit + tests evidence" \
                   || bad "dashboard never displayed your completed item"

step "5/8 the ENTIRE chain in candystore under ONE correlationid"
CHAIN=""
for _ in $(seq 1 20); do
  E="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events?limit=100', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  CHAIN="$(printf '%s' "$E" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    rows = [e for e in d.get('events', []) if e.get('correlationid') == '$CORR']
    print('\n'.join(sorted(r['type'] for r in rows)))
except Exception: print('')" 2>/dev/null || true)"
  echo "$CHAIN" | grep -q "bloodbank.task.ticket.completed" && break
  sleep 2
done
printf '%s' "$CHAIN" > "$EVID/chain-types.txt"
echo "  your cycle's events in candystore:"
sed 's/^/    /' "$EVID/chain-types.txt"
python3 - "$EVID/chain-types.txt" <<'PY' && ok "full chain present: your create -> orchestrator start -> real code -> review -> done" || bad "chain incomplete"
import sys
types = set(open(sys.argv[1]).read().split())
need = {"bloodbank.task.ticket.created", "bloodbank.task.ticket.started",
        "bloodbank.code.commit.landed", "bloodbank.task.cycle.reviewed",
        "bloodbank.task.ticket.completed"}
missing = need - types
assert not missing, f"missing: {sorted(missing)}"
PY

step "6/8 the completed event carries YOUR commit evidence"
E="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events?limit=100', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
CID="$(printf '%s' "$E" | python3 -c "
import json, sys
d = json.load(sys.stdin)
rows = [e for e in d.get('events', []) if e.get('correlationid') == '$CORR'
        and e['type'] == 'bloodbank.task.ticket.completed']
print(rows[0]['id'] if rows else '')" 2>/dev/null || true)"
RAW="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/$CID/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
printf '%s' "$RAW" > "$EVID/completed-raw.json"
python3 - "$EVID/completed-raw.json" "$CYCLE_DONE" "$TICKET_ID" "$CORR" <<'PY' && ok "completed event: canonical envelope + your commit sha + tests + one correlationid" || bad "completed event verification failed"
import json, sys
e = json.load(open(sys.argv[1]))
assert e["data"]["commit_sha"] == sys.argv[2], "commit mismatch"
assert e["data"]["tests_passed"] is True
assert e["data"]["ticket_id"] == sys.argv[3]
assert e["correlationid"] == sys.argv[4]
toks = e["type"].split(".")
assert len(toks) == 4 and toks[0] == "bloodbank", e["type"]
assert e["subject"] == "bloodbank.evt." + ".".join(toks[1:])
assert e["type"] != e["subject"]
assert e["kind"] == "event"
print("  canonical 4-token type / 5-token subject; commit:", sys.argv[2][:12])
PY

step "7/8 persistence: owned services restart, your evidence survives"
docker compose restart board dashboard momod code-worker >/dev/null 2>&1
for _ in $(seq 1 30); do
  R="$(docker compose exec -T board python -c "
import urllib.request
try:
    urllib.request.urlopen('http://127.0.0.1:8793/healthz', timeout=3)
    print('up')
except Exception: pass" 2>/dev/null)" && [ "$R" = "up" ] && break
  sleep 2
done
RBT="$(docker compose exec -T board python -c "
import urllib.request
try: print(urllib.request.urlopen('http://127.0.0.1:8793/ticket/$TICKET_ID', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
printf '%s' "$RBT" | python3 -c "
import json, sys
t = json.load(sys.stdin)['ticket']
assert t['state'] == 'done' and t['commit_sha'], t" \
  && ok "board still shows your ticket done after restart" || bad "board lost your ticket state"
RGL="$(docker compose exec -T code-worker sh -c "cd /data/workbench && git rev-parse HEAD" 2>/dev/null || true)"
[ "$RGL" = "$CYCLE_DONE" ] && ok "the real repo still holds your commit after restart" \
  || bad "repo HEAD drifted after restart"

step "8/8 evidence (local only)"
cat <<EOT
  your task    : ${TITLE}
  ticket id    : ${TICKET_ID}
  correlation  : ${CORR}   (ONE id, create -> done)
  commit       : ${CYCLE_DONE}
  evidence     : ${EVID}/ (momod-healthz-before, create, board-ticket,
                git-show, dashboard-items, chain-types, completed-raw)
                — stays on this machine
EOT
echo
[ "${FAIL:-0}" = "0" ] && echo "G8 GATE: ALL CHECKS PASSED (degraded mode, zero LLM credentials — closed by evidence)" \
                     || { echo "G8 GATE: FAILED"; exit 1; }

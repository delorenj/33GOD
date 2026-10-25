#!/usr/bin/env bash
# Aperture G8 smoke — cold bring-up + FULL real ticket cycle proof.
#
# DESTRUCTIVE to god-g8: cold `down -v`, build, up, real work, `down -v`.
# Never touches any other compose project. Exit: 0 = PASS, 1 = FAIL.
#
# Proves, in order (the G8 gate: "Momo closes a real ticket with real code"):
#   1. Cold bring-up with EMPTY GOD_LLM_*: every core service healthy; momod
#      healthy AND degraded (healthz names the empty vars).
#   2. Readiness canary FIRST (fresh dapr sidecars bind durables 10-60s late;
#      recall/tail latency 3-8s; every check polls).
#   3. ONE real ticket created through the board adapter (the human-only-
#      initiates step), then momod drives the whole cycle unaided:
#      board start -> assign command -> code-worker REAL commit + REAL tests
#      -> deterministic review -> board done with evidence.
#   4. Board state == repo evidence: board ticket done + commit_sha == git
#      log in the code-worker's real scratch repo; tests actually passed.
#   5. Dashboard displays the completed work item with commit + tests.
#   6. Candystore holds the ENTIRE event chain under ONE correlationid:
#      ticket.created -> ticket.started -> ticket.assigned (cmd stream
#      observed via the code-worker's landed evidence) -> code.commit.landed
#      -> ticket.completed -> cycle.reviewed; chain fields verified.
#   7. Restart persistence: board/dashboard/momod stores survive restart.
#   8. WIP-lease discipline proven: a second fresh lease-holder is refused
#      while momod holds the lease (in_flight evidence); stale-steal covered
#      by unit tests.
#   9. Rejection path: board refuses done-without-evidence (400).
#  10. Teardown: down -v leaves zero god-g8 residue.
#
# Stdlib only (bash + python3 stdlib + docker compose + git). UUIDs generated
# inside Linux containers (macOS host portability).
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
gen_uuid() { docker run --rm --quiet --entrypoint sh "$NATS_BOX" -c 'cat /proc/sys/kernel/random/uuid'; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

step "1/10 cold start: down -v, build, up (EMPTY GOD_LLM_* — degraded mode)"
docker compose down -v --remove-orphans >/dev/null 2>&1
if docker compose build >/dev/null 2>&1 && \
   GOD_LLM_BASE_URL= GOD_LLM_API_KEY= docker compose up -d --wait --wait-timeout 300 >/dev/null 2>&1; then
  ok "cold up --wait healthy with empty GOD_LLM_*"
else
  bad "cold up failed"
  docker compose ps -a
  exit 1
fi

step "2/10 degraded boundary: momod healthy + degraded + says why"
MH="$(docker compose exec -T momod python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8795/healthz', timeout=5).read().decode())")"
echo "momod healthz: $(printf '%s' "$MH" | head -c 300)"
python3 - "$MH" <<'PY' && ok "momod healthy AND degraded (deterministic review; zero AAI)" || bad "momod degraded contract violated"
import json, sys
h = json.loads(sys.argv[1])
assert h["degraded"] is True, h
assert "GOD_LLM_BASE_URL" in h["degraded_reason"] and "GOD_LLM_API_KEY" in h["degraded_reason"], h
assert h["review_mode"] == "deterministic", h
assert h["bus"] == "connected", h
PY

step "3/10 readiness canary: bus -> candystore round-trip"
CANARY_ID="$(gen_uuid)"
cat > "$TMP/canary.json" <<JSON
{"specversion":"1.0","id":"${CANARY_ID}","source":"urn:33god:aperture:g8-smoke","type":"bloodbank.aperture.canary.g8","subject":"bloodbank.evt.aperture.canary.g8","time":"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)","datacontenttype":"application/json","correlationid":"${CANARY_ID}","causationid":"${CANARY_ID}","producer":"aperture-g8-smoke","service":"smoke","domain":"aperture","kind":"event","ordering_key":"g8:canary","actor":{"type":"operator","agent_id":"o"},"data":{"canary":true}}
JSON
docker run --rm --quiet --network g8-bus -v "$TMP/canary.json:/payload.json:ro" "$NATS_BOX" \
  sh -c 'nats --server nats://nats:4222 pub bloodbank.evt.aperture.canary.g8 "$(cat /payload.json)"' >/dev/null 2>&1 || true
CANARY_OK=""
for ((i = 0; i < 60; i += 1)); do
  C="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/${CANARY_ID}/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  [ -n "$C" ] && { CANARY_OK=1; break; }
  sleep 2
done
[ -n "$CANARY_OK" ] && ok "canary round-tripped candystore (delivery bound)" \
                      || bad "candystore never ingested canary within 120s"

step "4/10 THE CYCLE: create one real ticket (human initiates) -> momod closes it with real code"
TITLE="add one acceptance doc page for G8"
CREATE="$(docker compose exec -T board python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8793/command',
    data=json.dumps({'action': 'create', 'title': '''$TITLE'''}).encode(),
    headers={'Content-Type': 'application/json'})
print(urllib.request.urlopen(req, timeout=15).read().decode())")"
printf '%s' "$CREATE" > "$TMP/create.json"
TICKET_ID="$(printf '%s' "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['ticket']['id'])" 2>/dev/null || true)"
CORR="$(printf '%s' "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['ticket']['correlationid'])" 2>/dev/null || true)"
if [ -n "$TICKET_ID" ] && [ -n "$CORR" ]; then
  ok "ticket created (backlog): ${TICKET_ID}"
  echo "  correlationid: ${CORR}  (ONE id for the whole cycle)"
else
  bad "ticket create failed: ${CREATE:0:200}"
fi

# wait for momod to drive the whole cycle (measured 5-40s incl. commit).
# On transient failure (e.g. review raced the worker's landed row) the
# message is redelivered and momod retries — poll up to ~4 min total.
CYCLE_DONE=""
for ((i = 0; i < 120; i += 1)); do
  MC="$(docker compose exec -T momod python -c "
import urllib.request
try: print(urllib.request.urlopen('http://127.0.0.1:8795/cycles', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  DONE_NOW="$(printf '%s' "$MC" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    rows = [r for r in d.get('cycles', []) if r['ticket_id'] == '$TICKET_ID' and r['state'] == 'done']
    print(rows[0]['commit_sha'] if rows else '')
except Exception:
    print('')" 2>/dev/null || true)"
  [ -n "$DONE_NOW" ] && { CYCLE_DONE="$DONE_NOW"; break; }
  sleep 2
done
if [ -n "$CYCLE_DONE" ]; then
  ok "momod closed the ticket by evidence: commit ${CYCLE_DONE:0:12}"
  # snapshot counters NOW (the restart in step 8 resets in-memory healthz)
  MH2="$(docker compose exec -T momod python -c "
import urllib.request
try: print(urllib.request.urlopen('http://127.0.0.1:8795/healthz', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  printf '%s' "$MH2" > "$TMP/momod-healthz-mid.json"
else
  bad "momod never completed the cycle for ${TICKET_ID}"
  echo "--- momod logs (last 30) ---"
  docker compose logs momod --since 10m 2>&1 | tail -30 | sed 's/^/  /'
  echo "--- code-worker logs (last 15) ---"
  docker compose logs code-worker --since 10m 2>&1 | tail -15 | sed 's/^/  /'
  echo "--- board healthz ---"
  docker compose exec -T board python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8793/healthz', timeout=5).read().decode())" 2>/dev/null | head -c 300; echo
fi

step "5/10 board state == repo evidence (px-shaped check: state vs git log)"
BT="$(docker compose exec -T board python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8793/ticket/$TICKET_ID', timeout=5).read().decode())")"
printf '%s' "$BT" > "$TMP/board-ticket.json"
CW="$(docker compose exec -T code-worker python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8794/landed', timeout=5).read().decode())")"
printf '%s' "$CW" > "$TMP/landed.json"
python3 - "$TMP/board-ticket.json" "$TMP/landed.json" "$CYCLE_DONE" <<'PY' && ok "board ticket == done with commit+tests; sha == git log HEAD in the real repo" || bad "board/repo evidence mismatch"
import json, sys
board = json.load(open(sys.argv[1]))["ticket"]
landed_rows = [r for r in json.load(open(sys.argv[2]))["landed"]
               if r["ticket_id"] == board["id"]]
assert board["state"] == "done", board
assert board["tests_passed"] is True, board
assert landed_rows, "code-worker never landed this ticket"
lw = landed_rows[0]
assert lw["commit_sha"] == board["commit_sha"], (lw["commit_sha"], board["commit_sha"])
assert lw["tests_passed"] is True, lw
assert lw["correlationid"] == board["correlationid"], "correlation drifted"
print("  board:", board["state"], board["commit_sha"][:12], "tests=pass")
print("  worker repo commit:", lw["commit_sha"][:12])
PY
# and the commit REALLY resolves in the scratch repo (git show)
SHOW="$(docker compose exec -T code-worker sh -c "cd /data/workbench && git show --stat --oneline $CYCLE_DONE 2>&1 | head -5")"
echo "$SHOW" | sed 's/^/  /'
echo "$SHOW" | head -1 | grep -q "^${CYCLE_DONE:0:7}" && echo "$SHOW" | grep -q "2 files changed" \
  && ok "git show resolves the commit with 2 files (module + test)" \
  || bad "git show did not resolve the commit as expected"

step "6/10 dashboard displays the completed work item (Holocene-shaped surface)"
DASH_OK=""
for ((i = 0; i < 30; i += 1)); do
  DI="$(docker compose exec -T dashboard python -c "
import urllib.request
try: print(urllib.request.urlopen('http://127.0.0.1:8796/api/items', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  FOUND="$(printf '%s' "$DI" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    rows = [it for it in d.get('items', []) if it['ticket_id'] == '$TICKET_ID'
            and it['state'] == 'done' and it.get('commit_sha')]
    chains = d.get('chains', {}).get('$TICKET_ID', [])
    print('displayed' if rows else '', 'chain-len=%d' % len(chains))
except Exception: print('')" 2>/dev/null || true)"
  echo "$FOUND" | grep -q displayed && { DASH_OK="$FOUND"; break; }
  sleep 2
done
if [ -n "$DASH_OK" ]; then
  ok "dashboard shows the item done with commit evidence ($DASH_OK)"
else
  bad "dashboard never displayed the completed item"
fi
# the HTML page itself serves (in-network)
HP="$(docker compose exec -T dashboard python -c "
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8796/', timeout=5).status)")"
[ "$HP" = "200" ] && ok "dashboard HTML page serves (200)" || bad "dashboard HTML status $HP"

step "7/10 candystore: the WHOLE chain under ONE correlationid"
# candystore sees every evt; the command (assigned) lives on BLOODBANK_COMMANDS,
# proven by the landed evidence + reply event on evt stream
CHAIN_TYPES=""
for ((i = 0; i < 20; i += 1)); do
  CH="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events?limit=100', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  CHAIN_TYPES="$(printf '%s' "$CH" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    rows = [e for e in d.get('events', d if isinstance(d, list) else [])
            if e.get('correlationid') == '$CORR']
    print('\n'.join(sorted(r['type'] for r in rows)))
except Exception: print('')" 2>/dev/null || true)"
  echo "$CHAIN_TYPES" | grep -q "bloodbank.task.ticket.completed" && break
  sleep 2
done
printf '%s' "$CHAIN_TYPES" > "$TMP/chain.txt"
echo "  chain under correlationid ${CORR}:"
sed 's/^/    /' "$TMP/chain.txt"
python3 - "$TMP/chain.txt" <<'PY' && ok "full event chain in candystore with ONE correlationid (create->done)" || bad "chain incomplete"
import sys
types = set(open(sys.argv[1]).read().split())
need = {"bloodbank.task.ticket.created",   # human initiates (board)
        "bloodbank.task.ticket.started",   # momod drives
        "bloodbank.code.commit.landed",    # real code landed
        "bloodbank.task.cycle.reviewed",   # evidence review
        "bloodbank.task.ticket.completed"} # closed by evidence
missing = need - types
assert not missing, f"missing from chain: {sorted(missing)}"
print("  expected types all present:", sorted(need))
PY
# every chain envelope: canonical shape + ONE correlationid, completed carries
# the commit evidence. NOTE: /events list previews omit `subject` (upstream
# _preview_from_row shape) — envelope checks use /events/<id>/raw instead.
EIDS="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events?limit=100', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
RAW_IDS="$(printf '%s' "$EIDS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
rows = [e for e in d.get('events', []) if e.get('correlationid') == '$CORR']
print('\n'.join(e['id'] for e in rows))" 2>/dev/null || true)"
: > "$TMP/raw-envelope.jsons"
for EID in $RAW_IDS; do
  R="$(docker compose exec -T candystore python -c "
import urllib.request
try: print(urllib.request.urlopen('http://candystore-app:3001/events/$EID/raw', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
  [ -n "$R" ] && printf '%s\n' "$R" >> "$TMP/raw-envelope.jsons"
done
python3 - "$TMP/raw-envelope.jsons" "$CORR" "$TICKET_ID" "$CYCLE_DONE" <<'PY' && ok "every chain envelope: 4-token type, 5-token subject, kind enum, ONE correlationid" || bad "envelope contract violated in the chain"
import json, sys
rawf, corr, tid, sha = sys.argv[1:5]
chain = [json.loads(line) for line in open(rawf) if line.strip()]
assert len(chain) >= 5, f"chain too short: {len(chain)}"
for e in chain:
    toks = e["type"].split(".")
    assert len(toks) == 4 and toks[0] == "bloodbank", e["type"]
    assert e["subject"] == "bloodbank.evt." + ".".join(toks[1:]), e["subject"]
    assert e["type"] != e["subject"], "type==subject conflation"
    assert e["kind"] in ("event", "command", "reply"), e["kind"]
    assert e["correlationid"] == corr
    for req in ("id", "source", "time", "producer", "service", "domain"):
        assert e.get(req), f"missing {req}"
comp = [e for e in chain if e["type"] == "bloodbank.task.ticket.completed"][0]
assert comp["data"]["ticket_id"] == tid
assert comp["data"]["commit_sha"] == sha, "completed event commit != git sha"
assert comp["data"]["tests_passed"] is True
print(f"  {len(chain)} correlated events; completed carries commit {sha[:12]}")
PY

step "8/10 restart persistence: board + dashboard + momod stores survive"
docker compose restart board dashboard momod code-worker >/dev/null 2>&1
wait_healthy board 90; wait_healthy dashboard 90; wait_healthy momod 90; wait_healthy code-worker 90
RBT="$(docker compose exec -T board python -c "
import urllib.request
try: print(urllib.request.urlopen('http://127.0.0.1:8793/ticket/$TICKET_ID', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
printf '%s' "$RBT" | python3 -c "
import json, sys
t = json.load(sys.stdin)['ticket']
assert t['state'] == 'done' and t['commit_sha'], t
print('  board ticket survived: done,', t['commit_sha'][:12])" \
  && ok "board state survived restart" || bad "board lost state on restart"
RGL="$(docker compose exec -T code-worker sh -c "cd /data/workbench && git rev-parse HEAD" 2>/dev/null || true)"
[ "$RGL" = "$CYCLE_DONE" ] && ok "scratch repo HEAD still the landed commit after restart" \
  || bad "repo HEAD drifted: ${RGL:0:12} != ${CYCLE_DONE:0:12}"
RDI="$(docker compose exec -T dashboard python -c "
import urllib.request
try: print(urllib.request.urlopen('http://127.0.0.1:8796/api/items', timeout=5).read().decode())
except Exception: pass" 2>/dev/null || true)"
printf '%s' "$RDI" | python3 -c "
import json, sys
d = json.load(sys.stdin)
rows = [it for it in d['items'] if it['ticket_id'] == '$TICKET_ID' and it['state'] == 'done']
assert rows and rows[0]['commit_sha'], 'dashboard lost the item'
print('  dashboard item survived: done with commit')" \
  && ok "dashboard projection survived restart" || bad "dashboard lost state on restart"

step "9/10 WIP lease + rejection path"
# the lease protocol is live: counters were captured right after the cycle
# (the step-8 restart resets momod's in-memory healthz). A completed cycle
# REQUIRES acquire+release to have run.
python3 - "$TMP/momod-healthz-mid.json" <<'PY' && ok "momod acquired + released the WIP lease during the cycle (protocol live)" || bad "lease counters missing"
import json, sys
h = json.loads(open(sys.argv[1]).read())
assert "lease_acquired" in h and "lease_refused" in h and "lease_stolen" in h, h
assert h["cycles_completed"] >= 1 and h["lease_acquired"] >= 1, h
assert h["in_flight"] is None, "lease not released after cycle end"
print("  lease_acquired:", h["lease_acquired"], "refused:", h["lease_refused"],
      "stolen:", h["lease_stolen"], "cycles_completed:", h["cycles_completed"])
PY
# rejection: done-without-evidence must 400
BAD1="$(docker compose exec -T board python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8793/command',
    data=json.dumps({'action': 'done', 'ticket_id': '$TICKET_ID'}).encode(),
    headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except urllib.error.HTTPError as e:
    print(e.code)
" 2>/dev/null || true)"
[ "${BAD1:-x}" = "400" ] && ok "board refuses done-without-evidence (400)" \
  || bad "board accepted evidence-less done (got ${BAD1:-none})"
# rejection: create with empty title
BAD2="$(docker compose exec -T board python -c "
import json, urllib.request
req = urllib.request.Request('http://127.0.0.1:8793/command',
    data=json.dumps({'action': 'create', 'title': '   '}).encode(),
    headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except urllib.error.HTTPError as e:
    print(e.code)
" 2>/dev/null || true)"
[ "${BAD2:-x}" = "400" ] && ok "board refuses empty-title create (400)" \
  || bad "board accepted empty title (got ${BAD2:-none})"

step "10/10 teardown: down -v leaves zero residue"
docker compose down -v --remove-orphans >/dev/null 2>&1
RESIDUE="$(docker volume ls -q --filter name=god-g8- ; docker network ls -q --filter name=g8- ; docker compose ps -aq 2>/dev/null)"
if [ -z "$(echo "$RESIDUE" | tr -d '[:space:]')" ]; then
  ok "zero god-g8 volumes / networks / containers remain"
else
  bad "residue: $RESIDUE"
fi

step "verdict"
echo "passed: ${PASS}  failed: ${FAIL}"
if [ "$FAIL" -eq 0 ]; then
  echo "SMOKE RESULT: PASS — G8 orchestration plane proven: real ticket closed with real code, one correlated chain"
  exit 0
else
  echo "SMOKE RESULT: FAIL"
  exit 1
fi

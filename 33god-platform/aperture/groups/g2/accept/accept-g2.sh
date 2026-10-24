#!/usr/bin/env bash
# G2 ACCEPTANCE GATE (bus-side checks) — run AFTER the client built, edited,
# activated and submitted their own form (see ACCEPT-G2.md for the manual
# flow). Usage: accept-g2.sh "the exact note text you submitted"
set -uo pipefail
cd "$(dirname "$0")/.."
NOTE="${1:?usage: accept-g2.sh \"the note text you submitted\"}"
TOKEN="${GOD_DEMO_HEADER_TOKEN:-aperture-g2-demo-only}"
SUBJ="bloodbank.evt.studio.note.recorded"
pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; FAILED=1; }
step() { echo; echo "=== $* ==="; }
q() { docker compose run --rm -T smoke-client -s "$1" -H "X-Aperture-Demo: ${TOKEN}" 2>/dev/null; }

step "1/4 your form values arrived in the bus (latest ${SUBJ})"
LATEST="$(q "http://nats-outbox:8789/latest?subject=${SUBJ}")"
printf '%s' "$LATEST" | python3 -c "
import json, sys
d = json.load(sys.stdin)
ev = d['event']
assert ev['type'] == 'bloodbank.studio.note.recorded', ev['type']
assert ev['data']['via'] == 'client-form-workflow', ev['data'].get('via')
print('  sequence', d['sequence'], '| note:', ev['data']['note'], '| mood:', ev['data']['mood'])
assert ev['data']['note'] == sys.argv[1], 'NOTE MISMATCH — expected what you typed'
" "$NOTE" && pass "latest studio-note event carries YOUR exact note text" || fail "note mismatch"

step "2/4 the rejection path holds (no header → 401)"
CODE="$(docker compose run --rm -T smoke-client -s -o /dev/null -w '%{http_code}' -X POST http://nats-outbox:8789/publish -H 'Content-Type: application/json' -d '{"x":1}' 2>/dev/null)"
[ "$CODE" = "401" ] && pass "outbox refused unauthenticated publish (401)" || fail "expected 401, got ${CODE}"

step "3/4 no ghost deliveries (deactivated workflow must not publish)"
BEFORE="$(printf '%s' "$LATEST" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sequence"])')"
echo "  (deactivate your workflow in the n8n UI, then press Enter to continue)"
read -r _
AFTER="$(q "http://nats-outbox:8789/latest?subject=${SUBJ}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sequence"])')"
[ "$BEFORE" = "$AFTER" ] && pass "sequence unchanged (${AFTER}) — deactivation stops events" || fail "sequence advanced ${BEFORE} → ${AFTER}: ghost delivery"

step "4/4 workflow is real n8n state"
docker compose exec -T n8n n8n export:workflow --id=apertureG2ClientForm01 2>/dev/null \
  | grep -q "apertureG2ClientForm01" \
  && pass "workflow apertureG2ClientForm01 exists in n8n (your edits are the graph)" \
  || fail "workflow not found in n8n — was the template imported/activated?"

echo
[ "${FAILED:-0}" = "0" ] && echo "G2 GATE (bus side): ALL CHECKS PASSED — pair with the n8n UI screenshots" || { echo "G2 GATE: FAILED"; exit 1; }

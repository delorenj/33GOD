#!/bin/bash
# W8-3 failure-path driver (Mac). Reads two throwaway Jev keys from stdin
# (line 1 rpm-limited, line 2 budget-limited); never stores or prints them.
set -u
cd "$HOME/33god-migration/2026-11-10/w8-3"
read -r SIM_KEY_RPM; read -r SIM_KEY_BUDGET
export SIM_KEY_RPM SIM_KEY_BUDGET
D=/usr/local/bin/docker; NATS="/opt/homebrew/bin/nats --server nats://127.0.0.1:4222"
C="$D --context colima"
t(){ date -u +%H:%M:%S; }
pub(){ # mode lineno
  local line; line=$(sed -n "${2}p" ev-$1.jsonl)
  $NATS pub "w83sim.$1.in" "$line" >/dev/null 2>&1 && echo "$(t) pub $1 #$2"
}
echo "$(t) up"
perl -e 'alarm 120; exec @ARGV' $C compose -p 33god-enricher-sim -f compose.w83sim.yaml up -d 2>&1 | tail -6
sleep 6
rm -f sim-out.log; (perl -e 'alarm 130; exec @ARGV' $NATS sub 'w83sim.>' > sim-out.log 2>&1 &)
sleep 2
# rpm: three in a row inside one minute: 200, 429, paused
pub rpm 1; pub rpm 2; sleep 1; pub rpm 3
# badkey: 401 twice (not pushback, both published w/ signal null)
pub badkey 1; pub badkey 2
# down: transport error pauses; second event skipped
pub down 1; sleep 1; pub down 2
# budget: first call spends > 1e-5; wait for litellm to flush spend, then budget_exceeded
pub budget 1
echo "$(t) waiting 45s for LiteLLM spend flush"; sleep 45
pub budget 2; sleep 3; pub budget 3
sleep 8
for m in rpm budget badkey down; do
  echo "===== w83sim-$m log"
  $C logs w83sim-$m 2>&1 | grep -Ev 'nats connected|subscribed:|starting:' | cut -c1-220
done
echo "===== nats sub (w83sim.>) payload summary"
python3_bin=/opt/homebrew/bin/python3
$python3_bin - <<'PY'
import re, json
txt = open('sim-out.log').read()
for m in re.finditer(r"Received on \"(w83sim\.[a-z]+\.out)\"[^\n]*\n(\{.*\})", txt):
    e = json.loads(m.group(2)); d = e['data']
    print(m.group(1), 'target', d['target_event_id'][:8], 'turn', d['turn_id'], 'signal', d['signal'], 'extractors', d['extractors'])
PY
echo "===== down"
perl -e 'alarm 90; exec @ARGV' $C compose -p 33god-enricher-sim -f compose.w83sim.yaml down 2>&1 | tail -6
$C ps -a --format '{{.Names}} {{.Status}}' | grep 'w83sim' || echo "no w83sim containers remain"

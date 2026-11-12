#!/bin/bash
set -u
M=hellosubconscious@100.117.109.60
MK=$(op read "op://DeLoSecrets/olonpzrcmxdx52vhoib3uyfzdi/credential" 2>/dev/null) || exit 2
gen(){ curl -s -m 20 -X POST https://jev.delo.sh/key/generate -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -d "$1"; }
RPM=$(gen '{"key_alias":"w83-probe-rpm1","rpm_limit":1,"max_budget":0.01,"metadata":{"purpose":"W8-3 transient 429 probe; deleted after","owner":"w83"}}')
BUD=$(gen '{"key_alias":"w83-probe-budget","max_budget":0.00001,"rpm_limit":60,"metadata":{"purpose":"W8-3 transient budget_exceeded probe; deleted after","owner":"w83"}}')
KR=$(echo "$RPM" | python3 -c "import sys,json;print(json.load(sys.stdin).get('key') or '')")
KB=$(echo "$BUD" | python3 -c "import sys,json;print(json.load(sys.stdin).get('key') or '')")
[ -n "$KR" ] && [ -n "$KB" ] || { echo "mint failed"; exit 3; }
echo "minted: rpm1 alias=w83-probe-rpm1 rpm_limit=1; budget alias=w83-probe-budget max_budget=1e-5"
echo "damian-studio spend before:"; docker exec jev-litellm-postgres psql -U litellm -d litellm -At -c "select round(spend::numeric,8) from \"LiteLLM_VerificationToken\" where key_alias='damian-studio'"
printf '%s\n%s\n' "$KR" "$KB" | ssh -o BatchMode=yes $M '/bin/bash ~/33god-migration/2026-11-10/w8-3/sim-mac.sh'
echo "ssh rc=$?"
echo "=== LiteLLM spend rows for the throwaway aliases"
docker exec jev-litellm-postgres psql -U litellm -d litellm -P pager=off -c "select to_char(\"startTime\" at time zone 'utc','HH24:MI:SS') t_utc, metadata->>'user_api_key_alias' alias, model, spend, status from \"LiteLLM_SpendLogs\" where metadata->>'user_api_key_alias' like 'w83-probe%' order by \"startTime\""
echo "=== LiteLLM key spend (tokens)"
docker exec jev-litellm-postgres psql -U litellm -d litellm -P pager=off -c "select key_alias, spend, max_budget, rpm_limit from \"LiteLLM_VerificationToken\" where key_alias like 'w83-probe%' or key_alias='damian-studio' order by key_alias"
for a in w83-probe-rpm1 w83-probe-budget; do curl -s -m 20 -X POST https://jev.delo.sh/key/delete -H "Authorization: Bearer $MK" -H 'Content-Type: application/json' -d "{\"key_aliases\":[\"$a\"]}" | python3 -c "import sys,json;print('delete',str(json.load(sys.stdin))[:120])"; done
docker exec jev-litellm-postgres psql -U litellm -d litellm -At -c "select count(*) from \"LiteLLM_VerificationToken\" where key_alias like 'w83-probe%'" | sed 's/^/remaining w83 keys: /'

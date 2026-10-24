#!/usr/bin/env bash
# Destructive only to the isolated god-g6 project; never adopted/live resources.
set -euo pipefail
cd "$(dirname "$0")/.."
export GOD_GPU=0
unset COMPOSE_PROFILES
# Disposable key tests authentication without shipping a credential.
export GOD_VOX_API_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
compose() { docker compose -f compose.yml "$@"; }
cleanup() { compose --profile gpu down -v --remove-orphans; }
trap cleanup EXIT
cleanup
python3 smoke/manifests.py
python3 smoke/audit.py
python3 - <<'PY'
import json,subprocess
cfg=json.loads(subprocess.check_output(['docker','compose','-f','compose.yml','--profile','gpu','config','--format','json']))
assert cfg['name']=='god-g6'
assert not any(s.get('ports') for s in cfg['services'].values())
assert not any(s.get('container_name') for s in cfg['services'].values())
assert cfg['services']['voxxy-engine-voxcpm']['profiles']==['gpu']
for name,s in cfg['services'].items():
    if name != 'voxxy-engine-voxcpm':
        assert not s.get('deploy',{}).get('resources',{}).get('reservations',{}).get('devices'), name
print('PASS config zero published ports; GPU reservations isolated to gpu profile')
PY
compose build
compose up -d --wait --wait-timeout 420
compose ps
# If explicitly regenerating the fixture, use a REAL TTS engine, never tones/silence.
# The fixture is checked into the bundle. See smoke/FIXTURE.md.
compose exec -T audio-intake python -m smoke.unit
compose exec -T -e GOD_VOX_API_KEY="$GOD_VOX_API_KEY" audio-intake python -m smoke.roundtrip
compose exec -T vinyld-serve python -m smoke.vinyl
for id in $(compose ps -q); do
  docker inspect --format '{{.Name}} health={{.State.Health.Status}} restarts={{.RestartCount}} requests={{json .HostConfig.DeviceRequests}}' "$id"
  test "$(docker inspect --format '{{.RestartCount}}' "$id")" = 0
done
docker stats --no-stream $(compose ps -q) --format '{{.Name}} {{.MemUsage}}'
cleanup
trap - EXIT
python3 - <<'PY'
import subprocess
for kind in ('container','volume','network'):
    ids=subprocess.check_output(['docker',kind,'ls','-q','--filter','label=com.docker.compose.project=god-g6']).decode().strip()
    assert not ids,(kind,ids)
print('PASS down -v: zero project containers, volumes, networks')
PY
printf 'SMOKE RESULT: PASS — CPU TTS/STT, Vinyl, intake, no-GPU, teardown\n'

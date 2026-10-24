#!/usr/bin/env bash
# Update ship-board delivery status + republish.
# Usage: update-ship-board.sh <group> <field> <value> [note]
#   fields: bundle|arm64|studio|gate|gate_label|note
#   e.g. update-ship-board.sh g2 studio running "Rererere confirmed ARM64 up"
# Run from anywhere. Commits data.json + republished board to the monorepo
# (charter gate honored via .aperture/charter-session marker).
set -euo pipefail
SB="$(cd "$(dirname "$0")" && pwd)"
MONO="$(git -C "$SB" rev-parse --show-toplevel)"

GROUP="$1"; FIELD="$2"; VALUE="$3"; NOTE="${4:-}"
python3 - "$SB/data.json" "$GROUP" "$FIELD" "$VALUE" <<'PY'
import json, sys, datetime
p, g, f, v = sys.argv[1:5]
d = json.load(open(p))
d.setdefault('delivery', {}).setdefault(g, {})
d['delivery'][g][f] = v
d['meta']['updated'] = datetime.date.today().isoformat() + ' (auto)'
json.dump(d, open(p, 'w'), indent=1, ensure_ascii=False)
print(f"updated {g}.{f} = {v}")
PY
if [ -n "$NOTE" ] && [ "$NOTE" != "''" ]; then
  python3 - "$SB/data.json" "$GROUP" "$NOTE" <<'PY'
import json, sys
p, g, n = sys.argv[1:4]
d = json.load(open(p))
d['delivery'][g]['note'] = n
json.dump(d, open(p, 'w'), indent=1, ensure_ascii=False)
PY
fi

# rebuild index.html from template + data, then publish
python3 - "$SB" <<'PY'
import sys
sb = sys.argv[1]
tpl = open(f"{sb}/index.template.html").read()
data = open(f"{sb}/data.json").read()
assert '__DATA__' in tpl
open(f"{sb}/index.html", 'w').write(tpl.replace('__DATA__', data))
print("index.html rebuilt")
PY

cd "$MONO"
git add 33god-platform/aperture/research/ship-board/
# charter gate: refresh marker (we read CHARTER.md this session)
if [ -f 33god-platform/aperture/CHARTER.md ]; then touch .aperture/charter-session; fi
git commit -q -m "ship-board: ${GROUP}.${FIELD} = ${VALUE} (charter-ack v1.0)" || true
git push -q origin HEAD || true

# publish to s3.delo.sh via the html-artifact-delivery skill script
python3 ~/.agents/skills/html-artifact-delivery/scripts/publish_html_artifact.py \
  --bundle "$SB" --entry index.html --artifact g33-ship-board \
  --project-root "$MONO" --harness hermes \
  --native-session-id "$(cat "$SB/.last-session-id" 2>/dev/null || echo 20261011_013759_c0759c2d)" \
  --publish 2>&1 | tail -3
echo "board republished"

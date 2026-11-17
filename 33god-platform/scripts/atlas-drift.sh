#!/usr/bin/env bash
# Atlas drift pass (I-12). Fired daily by the `atlas-drift` candybar
# (.candybars/atlas-drift.candybar.toml); safe to run by hand any time.
#
#   1. audit the registry against the running system (atlas.py audit --live)
#   2. heal the mechanical drift: evidence whose cited line moved, stale renders
#   3. land the heal (only registry/atlas paths, only if they were clean before)
#   4. anything that needs a person -> one report on MinIO + one Plane ticket,
#      keyed by the finding digest so an unchanged backlog never re-files
#
# Exit 0: audit ran (findings, if any, are ticketed). Exit 2: the pass itself
# broke (a probe, the heal, the publish or the ticket) and needs looking at.
set -uo pipefail
ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$ROOT"
ATLAS="33god-platform/scripts/atlas.py"
PATHS=(33god-platform/components 33god-platform/components.yaml 33god-platform/atlas)
OUT="${XDG_STATE_HOME:-$HOME/.local/state}/atlas-drift"
mkdir -p "$OUT"
DAY="$(date +%F)"

was_clean=0
[ -z "$(git status --porcelain -- "${PATHS[@]}")" ] && was_clean=1

heal=(); [ "$was_clean" = 1 ] && heal=(--heal)   # never rewrite someone's in-flight edit
python3 "$ATLAS" audit --live "${heal[@]}" --json >"$OUT/report.json"
rc=$?
if [ "$rc" -gt 1 ] || ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$OUT/report.json" 2>/dev/null; then
  echo "atlas-drift: audit crashed (exit $rc)" >&2; exit 2
fi

# 3. land the heal
if [ "$was_clean" = 1 ] && [ -n "$(git status --porcelain -- "${PATHS[@]}")" ]; then
  git add -- "${PATHS[@]}"
  git commit -q -m "chore(atlas): drift heal $DAY (moved evidence lines, re-render)" \
             -m "Automated by the atlas-drift candybar (33god-platform/scripts/atlas-drift.sh)." \
             -- "${PATHS[@]}" || { echo "atlas-drift: heal commit refused" >&2; exit 2; }
  git push -q 2>/dev/null || { git pull -q --rebase --autostash && git push -q; } \
    || { echo "atlas-drift: heal committed but not pushed" >&2; exit 2; }
  echo "atlas-drift: healed and pushed $(git rev-parse --short HEAD)"
elif [ "$was_clean" = 0 ]; then
  echo "atlas-drift: registry has uncommitted edits; heal skipped (their author's commit re-renders)"
fi

read -r NEED DIGEST < <(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["needs_human"], d["digest"])' "$OUT/report.json")
if [ "$NEED" = 0 ]; then
  echo "atlas-drift: clean"; exit 0
fi

# 4. one report + one ticket per distinct finding set
python3 - "$OUT/report.json" "$OUT/atlas-drift.md" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
skip = {"evidence-moved", "stale-render"}
rows = [f for f in d["findings"] if f["kind"] not in skip]
lines = [f"# Atlas drift: {len(rows)} finding(s)", "",
         f"digest `{d['digest']}`, {d['components']} components, live probes: {d['live']}", "",
         "Fix each one in the registry (33god-platform/components/*.yaml or components.yaml):",
         "- unregistered: add the surface to a component's `surfaces:`, write a new record, or add it to `atlas_ignore`",
         "- evidence-gone / evidence-unverifiable: re-cite the relation (path:line) or drop it, then `atlas.py anchor`",
         "- status: correct the component's `status:` or bring the service back", "",
         "| kind | subject | detail |", "|---|---|---|"]
lines += [f"| {f['kind']} | `{f['subject']}` | {f['detail']} |" for f in rows]
open(sys.argv[2], "w").write("\n".join(lines) + "\n")
PY

URL="$(python3 "$HOME/.agents/skills/artifacts/scripts/publish.py" "$OUT/atlas-drift.md" \
        --name atlas-drift --project 33god 2>"$OUT/publish.err" | tail -1)"
case "$URL" in https://*) ;; *) echo "atlas-drift: publish failed: $(tail -3 "$OUT/publish.err")" >&2; URL="" ;; esac

created="$(px task create "Atlas drift: $NEED finding(s) need a person" --idempotency-key "atlas-drift-$DIGEST" 2>&1)" \
  || { echo "atlas-drift: ticket create failed: $created" >&2; exit 2; }
REF="$(grep -oE '\b[A-Z0-9]*[A-Z][A-Z0-9]*-[0-9]+\b' <<<"$created" | head -1)"
[ -n "$REF" ] || { echo "atlas-drift: no ticket ref in: $created" >&2; exit 2; }
if ! px show "$REF" 2>/dev/null | grep -q "$DIGEST"; then
  body="$(cat "$OUT/atlas-drift.md")"
  [ -n "$URL" ] && body="$body"$'\n\n'"Report: $URL"
  px comment "$REF" -m "$body" >/dev/null || { echo "atlas-drift: comment on $REF failed" >&2; exit 2; }
fi
echo "atlas-drift: $NEED finding(s) -> $REF ${URL:-(report not published)}"
[ -n "$URL" ] || exit 2
exit 0

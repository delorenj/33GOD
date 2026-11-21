#!/usr/bin/env bash
# The Factory forge (I-10). Fired nightly by the `factory-forge` candybar
# (.candybars/factory-forge.candybar.toml); safe to run by hand any time.
#
#   1. pick one Atlas component (factory_forge.py pick): untouched bodies first, busiest first;
#      once every component has one, polish the weakest
#   2. brief a headless Claude Code agent (PROMPT.md + the record + the contract) and let it build the asset
#   3. verify independently (factory_forge.py verify): scope, manifest, glb, typecheck, build, selfcheck, browser
#   4. PASS: commit ONLY src/assets/<id>/, push, deploy the Factory, publish a showcase page, log the run
#      FAIL: restore src/assets/<id>/ to HEAD (the agent's copy kept in the run dir), log the run, exit 1
#      Either way the agent's lessons in the Factory skill (skills/33god-hub/subskills/the-factory/) land in their
#      own commit when they lint (self-evolving skill)
#
#   factory-forge.sh [--component ID] [--dry-run] [--no-deploy] [--no-publish]
#
# --dry-run picks, renders the prompt and prints the command; it runs no agent, commits nothing, writes no ledger.
# Exit 0: nothing to do, or the night's asset shipped. Exit 1: the agent's work failed verification or the pass broke.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM="$(cd "$HERE/.." && pwd)"
SANDBOX="$PLATFORM/manual/sandbox"
FORGE="$HERE/factory_forge.py"
REPO="$(git -C "$PLATFORM" rev-parse --show-toplevel)"

# Belt and braces: drop the hook state a `mise activate` shell leaks into children, so a nested `mise run` starts clean.
for v in $(compgen -e | grep -E '^(__MISE_|MISE_SHELL$)'); do unset "$v"; done
# Candybar's exec environment is stripped: name every tool by absolute path.
export HOME="${HOME:-/home/delorenj}"
# (system dirs go LAST: /usr/bin has a node 20, and ahead of mise's dirs it beats the sandbox's node 24 inside `mise run`)
export PATH="$HOME/.local/bin:${PATH:+$PATH:}/usr/local/bin:/usr/bin:/bin"
MISE="$HOME/.local/bin/mise"; [ -x "$MISE" ] || MISE="$(command -v mise || true)"
if [ -n "$MISE" ] && NODE="$(cd "$SANDBOX" && "$MISE" which node 2>/dev/null)" && [ -n "$NODE" ]; then
  export PATH="$(dirname "$NODE"):$PATH"
fi
PY=""
OP="$HOME/.local/bin/op"
CLAUDE="$HOME/.local/bin/claude"
export BLENDER="$HOME/.local/bin/blender" BLENDER_BIN="$HOME/.local/bin/blender"
PROV="$HOME/.agents/providers/automaticai"
PUBLISH="$HOME/.agents/skills/artifacts/scripts/publish.py"
TIMEOUT_S="${FACTORY_FORGE_TIMEOUT_S:-5400}"   # the agent's hard limit; the candybar's own is 6000

COMPONENT="" DRY=0 DEPLOY=1 PUBLISH_PAGE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --component) COMPONENT="${2:?--component needs an id}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --no-deploy) DEPLOY=0; shift ;;
    --no-publish) PUBLISH_PAGE=0; shift ;;
    -h|--help) sed -n 2,16p "$0"; exit 0 ;;
    *) echo "factory-forge: unknown flag $1" >&2; exit 64 ;;
  esac
done

STATE="${FACTORY_FORGE_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/factory-forge}"
mkdir -p "$STATE"

# ---- the candybar result file is always written, whatever happens -----------------------------------
R_STATUS=fail R_MSG="factory-forge exited before it finished" R_TOKENS=0 R_COST=""
write_result() {
  [ -n "${CANDYBAR_RESULT_FILE:-}" ] || return 0
  "$PY" - "$CANDYBAR_RESULT_FILE" "$R_STATUS" "$R_MSG" "$R_TOKENS" "$R_COST" <<'PY' 2>/dev/null
import json, sys
f, status, msg, tok, cost = sys.argv[1:6]
m = {"token_spend": int(float(tok or 0))}
if cost not in ("", "None"):
    m["cost_usd"] = round(float(cost), 4)
json.dump({"status": status, "message": msg[:500], "metrics": m}, open(f, "w"))
PY
}
trap write_result EXIT
done_ok()   { R_STATUS=success R_MSG="$1"; echo "factory-forge: $1"; exit 0; }
done_fail() { R_STATUS=fail R_MSG="$1"; echo "factory-forge: $1" >&2; exit "${2:-1}"; }

# Candybar's PATH leads with its own venv, which has no PIL or playwright: find the python that has everything.
for cand in "${FACTORY_FORGE_PYTHON:-}" "$(cd "$SANDBOX" && "$MISE" which python3 2>/dev/null)" "$HOME/.local/share/mise/shims/python3" /usr/bin/python3; do
  if [ -n "$cand" ] && [ -x "$cand" ] && "$cand" -c 'import yaml, PIL, playwright' 2>/dev/null; then PY="$cand"; break; fi
done
[ -n "$PY" ] || done_fail "no python with yaml, PIL and playwright found (set FACTORY_FORGE_PYTHON)"
PY_DIR="$(dirname "$PY")"; export PATH="$PY_DIR:$PATH"

# ---- one run at a time ---------------------------------------------------------------------------------
exec 9>"$STATE/lock"
flock -n 9 || done_ok "another forge run holds the lock; nothing to do"

# ---- 1. pick -----------------------------------------------------------------------------------------
# last night's waybill is what "busiest first" ranks on; a failed refresh is loud but does not stop the pick
"$PY" "$FORGE" traffic --refresh || echo "factory-forge: WARNING: no fresh traffic (pick ranks on the last waybill it has, or alphabetically)" >&2
pick_args=(pick --json); [ -n "$COMPONENT" ] && pick_args+=(--component "$COMPONENT")
PICK="$("$PY" "$FORGE" "${pick_args[@]}")" || done_fail "pick failed"
ID="$("$PY" -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$PICK")"
MODE="$("$PY" -c 'import json,sys; print(json.load(sys.stdin)["mode"])' <<<"$PICK")"
explain_args=(pick --explain); [ -n "$COMPONENT" ] && explain_args+=(--component "$COMPONENT")
"$PY" "$FORGE" "${explain_args[@]}"

STAMP="$(date +%Y%m%dT%H%M%S)"
RUN="$STATE/runs/$ID-$STAMP"; mkdir -p "$RUN"
RUN_ID="$(date +%Y-%m-%dT%H:%M%z)"
ASSET_DIR="$SANDBOX/src/assets/$ID"

# ---- 2. the brief and the command ----------------------------------------------------------------------
"$PY" "$FORGE" prompt "$ID" > "$RUN/prompt.md" || done_fail "could not render the prompt for $ID"
CMD=(env -u CLAUDE_CODE_OAUTH_TOKEN -u ANTHROPIC_API_KEY
     timeout --signal=TERM --kill-after=30 "$TIMEOUT_S"
     "$OP" run --no-masking --env-file="$PROV/claude-code.env.op" --
     "$CLAUDE" --settings "$PROV/claude-code.settings.json" --dangerously-skip-permissions -p --output-format json)
# Test seam: FACTORY_FORGE_AGENT_CMD replaces the whole op+claude chain (reads the prompt on stdin, prints claude's JSON).
[ -n "${FACTORY_FORGE_AGENT_CMD:-}" ] && CMD=(timeout --signal=TERM --kill-after=30 "$TIMEOUT_S" "$FACTORY_FORGE_AGENT_CMD")

if [ "$DRY" = 1 ]; then
  echo
  echo "factory-forge --dry-run: $MODE $ID (nothing will run, commit or be logged)"
  echo "  cwd:     $SANDBOX"
  echo "  prompt:  $RUN/prompt.md ($(wc -c < "$RUN/prompt.md") bytes, fed on stdin)"
  echo "  command: cd $SANDBOX && ${CMD[*]} < $RUN/prompt.md > $RUN/claude.json"
  echo "  then:    verify $ID; on pass commit src/assets/$ID/$([ "$DEPLOY" = 1 ] && echo ', mise run assets && mise run build')$([ "$PUBLISH_PAGE" = 1 ] && echo ', publish the showcase'), log the run"
  done_ok "dry run: would $MODE $ID"
fi

"$PY" "$FORGE" snapshot --out "$RUN/baseline.json" || done_fail "could not snapshot the tree"
echo "factory-forge: $MODE $ID, running Claude Code (limit ${TIMEOUT_S}s), run dir $RUN"
T0=$SECONDS
( cd "$SANDBOX" && "${CMD[@]}" < "$RUN/prompt.md" > "$RUN/claude.json" 2> "$RUN/claude.err" )
CLAUDE_RC=$?
TOKENS_JSON="$("$PY" "$FORGE" usage "$RUN/claude.json" 2>/dev/null || echo '{"total":0}')"
R_TOKENS="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("total",0))' <<<"$TOKENS_JSON")"
R_COST="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("cost_usd") or "")' <<<"$TOKENS_JSON")"
SUBTYPE="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("subtype") or "")' <<<"$TOKENS_JSON")"
echo "factory-forge: claude exit $CLAUDE_RC, $R_TOKENS tokens, subtype '${SUBTYPE:-none}'"

ledger() {  # outcome score commit showcase note failed-checks
  local a=(ledger add --run "$RUN_ID" --id "$ID" --mode "$MODE" --outcome "$1" --tokens "$TOKENS_JSON" --duration-s "$((SECONDS - T0))")
  [ -n "${2:-}" ] && a+=(--score "$2"); [ -n "${3:-}" ] && a+=(--commit "$3"); [ -n "${4:-}" ] && a+=(--showcase-url "$4")
  [ -n "${5:-}" ] && a+=(--note "$5"); [ -n "${6:-}" ] && a+=(--failed "$6")
  "$PY" "$FORGE" "${a[@]}" > /dev/null
}
ledger_commit() {  # push the ledger on its own, so tomorrow's pick sees tonight
  local L="$SANDBOX/forge/ledger.json"
  git -C "$REPO" add -- "$L" \
    && git -C "$REPO" commit -q -m "chore(factory): forge ledger, $ID $1" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>" -- "$L" \
    && { git -C "$REPO" push -q 2>/dev/null || { git -C "$REPO" pull -q --rebase --autostash && git -C "$REPO" push -q; }; }
}
restore() {  # exactly the asset dir, and the glb it generated (kept in the run dir first: a false verdict must not cost the work)
  if [ -d "$ASSET_DIR" ]; then
    mkdir -p "$RUN/asset-failed" && cp -a "$ASSET_DIR/." "$RUN/asset-failed/" 2>/dev/null
    [ -f "$SANDBOX/public/assets/$ID/model.glb" ] && cp -a "$SANDBOX/public/assets/$ID/model.glb" "$RUN/asset-failed/model.glb" 2>/dev/null
  fi
  git -C "$REPO" checkout -q -- "$ASSET_DIR" 2>/dev/null
  git -C "$REPO" clean -fdq -- "$ASSET_DIR" 2>/dev/null
  rm -rf "$SANDBOX/public/assets/$ID"          # a failed glb must never be served by the next build
}

SKILL_DIR="$PLATFORM/skills/33god-hub/subskills/the-factory"
LESSONS=""
land_skill() {  # the agent's lessons (self-evolving skill): commit the Factory skill on its own when they lint
  local rep rc n dirty
  rep="$("$PY" "$FORGE" skill --baseline "$RUN/baseline.json" 2>/dev/null)"; rc=$?
  printf '%s\n' "$rep" > "$RUN/skill.json"
  n="$("$PY" -c 'import json,sys; print(len(json.load(sys.stdin)["changed"]))' <<<"$rep" 2>/dev/null || echo 0)"
  dirty="$("$PY" -c 'import json,sys; print(len(json.load(sys.stdin)["dirty_before"]))' <<<"$rep" 2>/dev/null || echo 0)"
  [ "${n:-0}" -gt 0 ] || return 0
  mkdir -p "$RUN/skill-after" && cp -a "$SKILL_DIR/." "$RUN/skill-after/"
  if [ "${dirty:-0}" -gt 0 ]; then   # someone else's edits were already there: never commit or wipe them
    LESSONS="lessons left uncommitted (the skill was dirty before the run)"; echo "factory-forge: $LESSONS" >&2; return 0
  fi
  if [ "$rc" -ne 0 ]; then
    git -C "$REPO" checkout -q -- "$SKILL_DIR" 2>/dev/null; git -C "$REPO" clean -fdq -- "$SKILL_DIR" 2>/dev/null
    LESSONS="lessons rejected (skill lint: see $RUN/skill.json)"; echo "factory-forge: $LESSONS" >&2; return 0
  fi
  git -C "$REPO" add -A -- "$SKILL_DIR" \
    && git -C "$REPO" commit -q -m "docs(factory): forge lessons from the $ID $1 run" \
         -m "Self-evolving skill: the nightly forge agent folded what this run taught it back into the-factory." \
         -m "Co-Authored-By: Claude Code <noreply@anthropic.com>" -- "$SKILL_DIR" \
    && { git -C "$REPO" push -q 2>/dev/null || { git -C "$REPO" pull -q --rebase --autostash && git -C "$REPO" push -q; }; } \
    && LESSONS="lessons landed ($n path(s))" || LESSONS="lessons commit failed"
  echo "factory-forge: $LESSONS"
}

# The agent never ran (no usable result from claude at all): an infrastructure error, not a verdict on the asset.
if [ -z "$SUBTYPE" ] && [ "$CLAUDE_RC" -ne 0 ]; then
  restore
  land_skill error
  ledger error "" "" "" "claude produced no result (exit $CLAUDE_RC): $(tail -c 300 "$RUN/claude.err" | tr '\n' ' ')"
  ledger_commit error || true
  done_fail "claude produced no result (exit $CLAUDE_RC); see $RUN/claude.err"
fi

# ---- 3. verify, independently ------------------------------------------------------------------------------
"$PY" "$FORGE" verify "$ID" --baseline "$RUN/baseline.json" --out "$RUN" > "$RUN/verdict.json" 2> "$RUN/verify.err"
VERIFY_RC=$?
jfield() { "$PY" -c 'import json,sys; v=json.load(sys.stdin).get(sys.argv[1]); print(",".join(v) if isinstance(v,list) else (v if v is not None else ""))' "$1" < "$RUN/verdict.json" 2>/dev/null; }
FAILED="$(jfield failed)"; SCORE="$(jfield score)"; TITLE="$(jfield title)"

# ---- 4b. FAIL: put the tree back -------------------------------------------------------------------------
if [ "$VERIFY_RC" -ne 0 ]; then
  restore
  land_skill failed
  ledger failed "$SCORE" "" "" "verification failed: ${FAILED:-no verdict}${LESSONS:+; $LESSONS}" "$FAILED"
  ledger_commit failed || echo "factory-forge: ledger not pushed" >&2
  done_fail "$MODE $ID failed verification (${FAILED:-no verdict}); asset dir restored, the agent's work kept in $RUN/asset-failed; verdict $RUN/verdict.json"
fi

# ---- 4a. PASS: commit only the asset, push, deploy, showcase -------------------------------------------------
VERB="gets a body"; [ "$MODE" = polish ] && VERB="gets a polish pass"
git -C "$REPO" add -A -- "$ASSET_DIR"
git -C "$REPO" commit -q -m "feat(factory): $ID $VERB — ${TITLE:-$ID}" \
  -m "Forged by the nightly factory-forge candybar ($MODE mode, self-score ${SCORE:-?}/10, $R_TOKENS tokens). Verified independently: scope, manifest, glb budget and clips, tsc, build, waybill selfcheck, browser console." \
  -m "Co-Authored-By: Claude Code <noreply@anthropic.com>" -- "$ASSET_DIR" || done_fail "commit of $ID refused (a guard fired?)"
git -C "$REPO" push -q 2>/dev/null || { git -C "$REPO" pull -q --rebase --autostash && git -C "$REPO" push -q; } \
  || done_fail "committed $ID but could not push"
COMMIT="$(git -C "$REPO" log -1 --format=%h --fixed-strings --grep="feat(factory): $ID ")"
NOTE=""
land_skill shipped
[ -n "$LESSONS" ] && NOTE="$LESSONS"

if [ "$DEPLOY" = 1 ]; then
  ( cd "$SANDBOX" && "$MISE" run assets && "$MISE" run build ) > "$RUN/deploy.log" 2>&1 \
    && echo "factory-forge: deployed to manual.delo.sh/sandbox" \
    || { NOTE="deploy failed, see $RUN/deploy.log"; echo "factory-forge: $NOTE" >&2; }
else
  NOTE="not deployed (--no-deploy)"
fi

SHOWCASE_URL=""
if [ "$PUBLISH_PAGE" = 1 ]; then
  if "$PY" "$FORGE" showcase "$ID" --shots "$RUN/shots" --out "$RUN/showcase" --tokens "$TOKENS_JSON" --commit "$COMMIT" >/dev/null 2>"$RUN/showcase.err" \
     && PUB="$("$PY" "$PUBLISH" "$RUN/showcase" --name "factory-forge-$ID" --project 33god 2>"$RUN/publish.err")"; then
    SHOWCASE_URL="$(tail -1 <<<"$PUB")"
  fi
  case "$SHOWCASE_URL" in
    https://*) echo "factory-forge: showcase $SHOWCASE_URL" ;;
    *) SHOWCASE_URL=""; NOTE="${NOTE:+$NOTE; }showcase not published: $(tail -c 200 "$RUN/publish.err" "$RUN/showcase.err" 2>/dev/null | tr '\n' ' ')"; echo "factory-forge: $NOTE" >&2 ;;
  esac
fi

ledger shipped "$SCORE" "$COMMIT" "$SHOWCASE_URL" "$NOTE"
ledger_commit shipped || NOTE="${NOTE:+$NOTE; }ledger not pushed"
done_ok "$MODE $ID shipped at $COMMIT (score ${SCORE:-?}/10, $R_TOKENS tokens)${SHOWCASE_URL:+ $SHOWCASE_URL}${NOTE:+ [$NOTE]}"

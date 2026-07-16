#!/usr/bin/env bash
# When a PM is provisioned with with_scrum_master=yes, chain a paired Scrum
# Master provision for the same repo + ticket provider into a sibling role dir.
# Idempotent: skips if agents/hermes/scrum-master already exists.
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"
load_role_env

already_done 90-chain-scrum-master && { log "[90] scrum master already chained — skipping"; exit 0; }

# Sibling path: .../agents/hermes/scrum-master  (peer of this pm role dir).
HERMES_DIR="$(dirname "$ROLE_DIR")"
SM_DIR="$HERMES_DIR/scrum-master"

if [[ -d "$SM_DIR" ]]; then
  log "[90] $SM_DIR already exists — not re-provisioning"; mark_done 90-chain-scrum-master; exit 0
fi

# Resolve the template source from this provision's copier answers.
ANSWERS="$ROLE_DIR/.copier-answers.yml"
SRC="$(yaml_get _src_path 2>/dev/null || true)"
[[ -z "$SRC" && -f "$ANSWERS" ]] && SRC="$(python3 -c 'import sys,re,pathlib;
t=pathlib.Path(sys.argv[1]).read_text();m=re.search(r"(?m)^_src_path:\s*(.+)$",t);print((m.group(1).strip() if m else ""))' "$ANSWERS")"
SRC="${SRC:-gh:delorenj/hermes-agent-template}"

PROVIDER="$(yaml_get ticket_provider.name)"; PROVIDER="${PROVIDER:-plane}"

if ! command -v copier >/dev/null 2>&1; then
  warn "[90] copier not on PATH; provision the Scrum Master manually:"
  warn "     copier copy --trust $SRC $SM_DIR --data role=scrum-master --data target_repo=$REPO --data ticket_provider=$PROVIDER"
  mark_done 90-chain-scrum-master; exit 0
fi

log "[90] chaining Scrum Master provision -> $SM_DIR (provider: $PROVIDER)"
# --trust is REQUIRED: the hermes-agent template uses copier `tasks`, which copier
# refuses to run unless explicitly trusted. Without it the chained provision aborts
# with "Template uses potentially unsafe feature: tasks" and the SM is never created.
copier copy --defaults --overwrite --trust \
  --data role=scrum-master \
  --data target_repo="$REPO" \
  --data ticket_provider="$PROVIDER" \
  "$SRC" "$SM_DIR" \
  || warn "[90] chained scrum-master provision failed; run it manually (see command above)"

mark_done 90-chain-scrum-master

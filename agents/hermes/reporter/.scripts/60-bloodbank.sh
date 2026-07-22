#!/usr/bin/env bash
# Install the bloodbank consumer + envelope helper into the runtime submodule.
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"
load_role_env

already_done 60-bloodbank && { log "[60] bloodbank already installed — skipping"; exit 0; }
[[ "${SKIP_BLOODBANK:-0}" == "1" ]] && { log "[60] bloodbank — SKIPPED"; mark_done 60-bloodbank; exit 0; }

RUNTIME="$ROLE_DIR/runtime"
[[ -d "$RUNTIME" ]] || die "runtime not initialized; run 20-runtime-repo.sh first"

log "[60] installing bloodbank consumer for $AGENT_ID"

# Ensure the runtime consumer exists AND is rendered.
#
# Step 20 (20-runtime-repo.sh) only renders into a TMP dir during the
# initial GH-repo push — the on-disk $RUNTIME_SCAFFOLD_DIR copy that lands
# in the project repo keeps its `{{agent_id}}`/`{{repo}}`/`{{role}}`
# placeholders. If $RUNTIME/bloodbank-consumer.py was ever lost (runtime
# submodule wiped, manual rm, etc.) and then someone restored it by
# copying from $RUNTIME_SCAFFOLD_DIR, they'd end up with an un-rendered
# consumer subscribing to literal `bloodbank.evt.v1.repo.{{repo}}.>`.
# This block handles both failure modes idempotently.
CONSUMER="$RUNTIME/bloodbank-consumer.py"
SCAFFOLD_CONSUMER="$RUNTIME_SCAFFOLD_DIR/bloodbank-consumer.py"

needs_restore=0
if [[ ! -f "$CONSUMER" ]]; then
  log "    consumer missing in runtime — restoring from scaffold"
  needs_restore=1
elif grep -qE '\{\{(agent_id|repo|role|display_name)\}\}' "$CONSUMER"; then
  warn "    consumer in runtime has un-rendered placeholders — re-rendering"
  needs_restore=1
fi

if [[ "$needs_restore" == "1" ]]; then
  [[ -f "$SCAFFOLD_CONSUMER" ]] || die "scaffold source missing: $SCAFFOLD_CONSUMER"
  cp "$SCAFFOLD_CONSUMER" "$CONSUMER"
  # Same placeholder set + values as 20-runtime-repo.sh's render pass.
  python3 - "$CONSUMER" "$AGENT_ID" "$REPO" "$ROLE" "$DISPLAY_NAME" <<'PYEOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
agent_id, repo, role, display = sys.argv[2:6]
mapping = {
    "{{agent_id}}": agent_id, "{{repo}}": repo, "{{role}}": role,
    "{{display_name}}": display,
}
t = p.read_text()
for k, v in mapping.items():
    t = t.replace(k, v)
p.write_text(t)
PYEOF
fi
chmod +x "$CONSUMER"

# Health check: is NATS up?
if (echo > /dev/tcp/$BLOODBANK_NATS_HOST/$BLOODBANK_NATS_PORT) 2>/dev/null; then
  log "    NATS reachable at $BLOODBANK_NATS_HOST:$BLOODBANK_NATS_PORT"
else
  warn "    NATS not reachable; consumer will retry on start"
  warn "    bring up:  cd $BLOODBANK_COMPOSE_DIR && docker compose -f compose/docker-compose.yml up -d"
fi

# Ensure nats-py is available in the hermes venv (uv-managed, no pip binary)
if ! "$HERMES_AGENT_REPO/.venv/bin/python" -c "import nats" 2>/dev/null; then
  warn "    python nats-py not installed in hermes venv; installing via uv"
  if command -v uv >/dev/null 2>&1; then
    (cd "$HERMES_AGENT_REPO" && uv pip install --quiet --python .venv/bin/python nats-py 2>&1 | tail -3) || true
  else
    warn "    uv not available either — install nats-py manually: cd $HERMES_AGENT_REPO && uv pip install nats-py"
  fi
fi

mark_done 60-bloodbank

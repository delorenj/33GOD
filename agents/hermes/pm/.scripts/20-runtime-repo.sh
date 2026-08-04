#!/usr/bin/env bash
# Provision the per-agent, pure-local Hermes runtime without creating a Git
# repository or a project submodule. Runtime durability belongs to Hindsight;
# this directory may contain secrets and mutable agent state (PJAN-41).
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"
load_role_env

already_done 20-runtime-repo && { log "[20] local runtime already set up — skipping"; exit 0; }
[[ "${SKIP_RUNTIME_REPO:-0}" == "1" ]] && { log "[20] local runtime — SKIPPED (SKIP_RUNTIME_REPO=1)"; mark_done 20-runtime-repo; exit 0; }

PROFILE_HOME="$HOME/.hermes/profiles/$PROFILE_NAME"
RUNTIME_LOCAL="$ROLE_DIR/runtime"
PROJECT_PATH="$(project_repo_path)" || die "no project git root"
REL_ROLE_PATH="$(realpath --relative-to="$PROJECT_PATH" "$ROLE_DIR")"
REL_RUNTIME_PATH="${REL_ROLE_PATH}/runtime"

log "[20] local runtime: $RUNTIME_LOCAL"

# Fail closed if an older installation still models runtime as a project
# submodule. `pjangler migrate` performs the non-destructive index transition;
# this provisioner never removes or rewrites an existing nested repository.
if git -C "$PROJECT_PATH" ls-files --stage -- "$REL_RUNTIME_PATH" | grep -q '^160000 '; then
  die "$REL_RUNTIME_PATH is still a tracked gitlink; run 'pjangler migrate' before provisioning"
fi
if [[ -f "$PROJECT_PATH/.gitmodules" ]] &&
   git -C "$PROJECT_PATH" config -f .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null |
     awk -v expected="$REL_RUNTIME_PATH" '$2 == expected { found=1 } END { exit !found }'; then
  die "$REL_RUNTIME_PATH still has a stale .gitmodules mapping; run 'pjangler migrate' before provisioning"
fi

mkdir -p "$RUNTIME_LOCAL"
if [[ -e "$RUNTIME_LOCAL/.git" ]]; then
  warn "    existing nested runtime repository preserved; no fetch, commit, or push will be attempted"
fi

# Render the scaffold in a temporary directory, then copy only missing paths.
# Existing memory, configuration, credentials, and sessions always win.
TMP="$(mktemp -d)"
cleanup() { rm -rf -- "$TMP"; }
trap cleanup EXIT
cp -a "$RUNTIME_SCAFFOLD_DIR/." "$TMP/"
python3 - "$TMP" "$AGENT_ID" "$REPO" "$ROLE" "$DISPLAY_NAME" <<'PYEOF'
import pathlib
import sys

root, agent_id, repo, role, display = sys.argv[1:6]
root = pathlib.Path(root)
mapping = {
    "{{agent_id}}": agent_id,
    "{{repo}}": repo,
    "{{role}}": role,
    "{{display_name}}": display,
}
for path in root.rglob("*"):
    if path.is_file() and path.suffix in (".md", ".yaml", ".yml", ".sh", ".py", ".gitignore", ".gitattributes"):
        try:
            text = path.read_text()
            for source, target in mapping.items():
                text = text.replace(source, target)
            path.write_text(text)
        except UnicodeDecodeError:
            pass
PYEOF
cp -an "$TMP/." "$RUNTIME_LOCAL/"

# Seed mutable identity/config only when no local value exists.
CANONICAL_PM_CONFIG="$(config_get fleet.canonical_pm_config "$HOME/.hermes/config.yaml")"
if [[ -f "$CANONICAL_PM_CONFIG" && ! -e "$RUNTIME_LOCAL/config.yaml" ]]; then
  cp "$CANONICAL_PM_CONFIG" "$RUNTIME_LOCAL/config.yaml"
fi
if [[ ! -e "$RUNTIME_LOCAL/SOUL.md" ]]; then
  cp "$ROLE_DIR/SOUL.md" "$RUNTIME_LOCAL/SOUL.md"
fi

# Fold the two supported staging-profile files into the runtime without
# deleting unknown profile content. Unknown content blocks the symlink so an
# operator can reconcile it explicitly instead of losing state.
if [[ -d "$PROFILE_HOME" && ! -L "$PROFILE_HOME" ]]; then
  log "    migrating supported staging profile state into the local runtime"
  for file_name in .env config.yaml; do
    [[ -f "$PROFILE_HOME/$file_name" && ! -e "$RUNTIME_LOCAL/$file_name" ]] && cp "$PROFILE_HOME/$file_name" "$RUNTIME_LOCAL/$file_name"
    [[ -f "$PROFILE_HOME/$file_name" ]] && rm -f -- "$PROFILE_HOME/$file_name"
  done
  if ! rmdir "$PROFILE_HOME" 2>/dev/null; then
    die "staging profile contains unrecognized state and was preserved: $PROFILE_HOME"
  fi
fi
ln -sfn "$RUNTIME_LOCAL" "$PROFILE_HOME"
log "    profile symlink $PROFILE_HOME -> $RUNTIME_LOCAL"

env HERMES_HOME="$RUNTIME_LOCAL" "$HERMES_BIN" config set terminal.cwd "$PROJECT_PATH" >/dev/null 2>&1 || true

if [[ "$ROLE" == "pm" ]]; then
  VOXXY_PLUGIN_DIR="${VOXXY_PLUGIN_DIR:-$(config_get fleet.voxxy_plugin_dir "$HOME/code/voxxy/plugins/tts/voxxy")}"
  if [[ -d "$VOXXY_PLUGIN_DIR" ]]; then
    mkdir -p "$RUNTIME_LOCAL/plugins/tts"
    ln -sfn "$VOXXY_PLUGIN_DIR" "$RUNTIME_LOCAL/plugins/tts/voxxy"
    log "    linked Voxxy plugin into runtime"
  else
    warn "    Voxxy plugin dir missing: $VOXXY_PLUGIN_DIR"
  fi

  if [[ -x "$HERMES_BIN" ]]; then
    env HERMES_HOME="$RUNTIME_LOCAL" "$HERMES_BIN" config set plugins.enabled.0 tts/voxxy >/dev/null 2>&1 || true
    env HERMES_HOME="$RUNTIME_LOCAL" "$HERMES_BIN" config set tts.provider voxxy >/dev/null 2>&1 || true
    env HERMES_HOME="$RUNTIME_LOCAL" "$HERMES_BIN" config set tts.voice rick >/dev/null 2>&1 || true
    log "    set PM runtime TTS provider -> voxxy"
  else
    warn "    Hermes bin missing; skipped PM Voxxy config"
  fi
fi

mark_done 20-runtime-repo

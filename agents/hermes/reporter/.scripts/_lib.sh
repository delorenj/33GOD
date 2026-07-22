# shellcheck shell=bash
# Common helpers sourced by every numbered provisioning step.

set -euo pipefail

# These three are set by Copier into the rendered role.yaml; we re-derive them
# here so each script is callable in isolation (e.g. for repair runs).
ROLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE_YAML="$ROLE_DIR/role.yaml"
PROV_LOG="$ROLE_DIR/.scripts/.provision.log"

mkdir -p "$ROLE_DIR/.scripts"

# Logging
log()  { local msg="[$(date +%H:%M:%S)] $*"; printf '\033[36m%s\033[0m\n' "$msg" >&2; printf '%s\n' "$msg" >> "$PROV_LOG"; }
warn() { local msg="[$(date +%H:%M:%S)] $*"; printf '\033[33m%s\033[0m\n' "$msg" >&2; printf '%s\n' "$msg" >> "$PROV_LOG"; }
err()  { local msg="[$(date +%H:%M:%S)] $*"; printf '\033[31m%s\033[0m\n' "$msg" >&2; printf '%s\n' "$msg" >> "$PROV_LOG"; }
die()  { err "$*"; exit 1; }

# Read a single field from role.yaml. Requires python3 (no yaml dep).
yaml_get() {
  # yaml_get  KEY[.SUBKEY]    e.g.  yaml_get role,  yaml_get telegram.bot_username
  local key="$1"
  python3 - "$ROLE_YAML" "$key" <<'PYEOF'
import sys, re, pathlib
path, key = sys.argv[1:3]
text = pathlib.Path(path).read_text()
parts = key.split(".")
# Trivial YAML walker — handles flat and one-level nested keys.
indent = -1
prefix = ""
for part in parts[:-1]:
    indent += 2
    prefix += part + ":"
    m = re.search(rf"(?m)^{re.escape(part)}:\s*$", text)
    if not m:
        sys.exit(0)
    text = text[m.end():]
key = parts[-1]
m = re.search(rf'(?m)^\s*{re.escape(key)}:\s*"?([^"\n]*)"?\s*$', text)
if m:
    print(m.group(1).strip())
PYEOF
}

# Apply a sed substitution to role.yaml in-place. Used to record IDs after
# external provisioning steps return them.
yaml_set() {
  # yaml_set KEY VALUE   (only updates the first match; key must already exist)
  local key="$1" val="$2"
  python3 - "$ROLE_YAML" "$key" "$val" <<'PYEOF'
import sys, re, pathlib
path, key, val = sys.argv[1:4]
p = pathlib.Path(path); text = p.read_text()
# Match `<indent><key>:<...>` and rewrite the value (last leaf only).
leaf = key.split(".")[-1]
new = re.sub(rf'(?m)^(\s*{re.escape(leaf)}:\s*)("?)[^"\n]*("?)\s*$',
             lambda m: f'{m.group(1)}"{val}"', text, count=1)
if new == text:
    sys.exit(f"yaml_set: leaf '{leaf}' not found in {path}")
p.write_text(new)
PYEOF
}

# ─── Distributable config (~/.config/hermes-agent-template/config.toml) ──────
# Single source of truth for environment-specific defaults so this template can
# be handed to someone else without editing any script. Ship config.example.toml
# is copied here on first provision (see .scripts/01-config.sh).
HERMES_TEMPLATE_CONFIG="${HERMES_TEMPLATE_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/hermes-agent-template/config.toml}"
export HERMES_TEMPLATE_CONFIG

# config_get <dotted.key> [default]   — print a value from config.toml (paths are
# tilde-expanded; arrays are space-joined). Falls back to [default] when the file,
# python3, or the key is missing. Always exits 0 so it's safe under `set -e`.
config_get() {
  local key="$1" def="${2:-}"
  if [[ ! -f "$HERMES_TEMPLATE_CONFIG" ]] || ! command -v python3 >/dev/null 2>&1; then
    printf '%s' "$def"; return 0
  fi
  python3 - "$HERMES_TEMPLATE_CONFIG" "$key" "$def" <<'PYEOF' || printf '%s' "$def"
import sys, os
try:
    import tomllib
except ModuleNotFoundError:  # python < 3.11
    print(sys.argv[3], end=""); sys.exit(0)
path, key, default = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path, "rb") as f:
        cur = tomllib.load(f)
except Exception:
    print(default, end=""); sys.exit(0)
for part in key.split("."):
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        print(default, end=""); sys.exit(0)
if isinstance(cur, list):
    cur = " ".join(str(x) for x in cur)
else:
    cur = str(cur)
print(os.path.expanduser(cur), end="")
PYEOF
  return 0
}

# Re-export role fields into the environment for the rest of the script.
load_role_env() {
  ROLE=$(yaml_get role)
  REPO=$(yaml_get repo)
  AGENT_ID=$(yaml_get agent_id)
  DISPLAY_NAME=$(yaml_get display_name)
  BOT_HANDLE=$(yaml_get telegram.bot_username)
  PROFILE_NAME=$(yaml_get profile)

  # Plane workspace: empty in role.yaml -> resolve from config.toml.
  PLANE_WORKSPACE=$(yaml_get plane.workspace)
  [[ -n "$PLANE_WORKSPACE" ]] || PLANE_WORKSPACE=$(config_get plane.workspace "33god")

  # Runtime repo: role.yaml stores the bare repo name plus an optional owner.
  # Older manifests stored "owner/name" directly in github_repo; honor both.
  RUNTIME_REPO=$(yaml_get runtime.github_repo)
  if [[ "$RUNTIME_REPO" != */* ]]; then
    local owner; owner=$(yaml_get runtime.github_owner)
    [[ -n "$owner" ]] || owner=$(config_get github.runtime_repo_owner "delorenj")
    RUNTIME_REPO="$owner/$RUNTIME_REPO"
  fi

  export ROLE REPO AGENT_ID DISPLAY_NAME BOT_HANDLE \
         PLANE_WORKSPACE RUNTIME_REPO PROFILE_NAME
}

# Skip a step if previously completed (idempotent reruns).
already_done() {
  local marker="$ROLE_DIR/.scripts/.done-$1"
  [[ -f "$marker" ]]
}
mark_done() {
  touch "$ROLE_DIR/.scripts/.done-$1"
}

# Fleet source-of-truth (shared across all wrappers/provisioners).
# Every default below resolves as: env var > fleet.env > config.toml > fallback.
FLEET_ENV="${HERMES_FLEET_ENV:-$(config_get fleet.fleet_env "$HOME/.hermes/fleet.env")}"
if [[ -f "$FLEET_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$FLEET_ENV"
fi

# Tools we expect on the host
HERMES_BIN="${HERMES_BIN:-${HERMES_FLEET_BIN:-$(config_get fleet.hermes_bin "$HOME/.hermes/hermes-agent/.venv/bin/hermes")}}"
HERMES_AGENT_REPO="${HERMES_AGENT_REPO:-${HERMES_FLEET_REPO:-$(config_get fleet.hermes_repo "$HOME/.hermes/hermes-agent")}}"
HERMES_OAUTH_FILE="${HERMES_OAUTH_FILE:-${HERMES_FLEET_OAUTH_FILE:-$(config_get fleet.oauth_file "$HOME/.hermes/auth.json")}}"
CODEX_HOME="${CODEX_HOME:-${HERMES_FLEET_CODEX_HOME:-$(config_get fleet.codex_home "$HOME/.codex")}}"
# Prefer a scaffold vendored into this agent directory; fall back to the configured template path.
RUNTIME_SCAFFOLD_DIR="${RUNTIME_SCAFFOLD_DIR:-$ROLE_DIR/.runtime-scaffold}"
if [[ ! -d "$RUNTIME_SCAFFOLD_DIR" ]]; then
  RUNTIME_SCAFFOLD_DIR="${HERMES_TEMPLATE_RUNTIME_SCAFFOLD:-$(config_get fleet.runtime_scaffold_dir "$HOME/code/hermes-agent-template/runtime-scaffold")}"
fi
REGISTRY_FILE="${REGISTRY_FILE:-${HERMES_FLEET_REGISTRY_FILE:-$(config_get fleet.registry_file "$HOME/.hermes/agents-registry.yaml")}}"

# Bloodbank / NATS
BLOODBANK_NATS_HOST="${BLOODBANK_NATS_HOST:-$(config_get bloodbank.nats_host '127.0.0.1')}"
BLOODBANK_NATS_PORT="${BLOODBANK_NATS_PORT:-$(config_get bloodbank.nats_port '4222')}"
BLOODBANK_COMPOSE_DIR="${BLOODBANK_COMPOSE_DIR:-$(config_get bloodbank.compose_dir "$HOME/code/33GOD/bloodbank")}"

# Plane
PLANE_BASE="${PLANE_BASE:-$(config_get plane.base 'https://plane.delo.sh')}"
PLANE_API_KEY="${PLANE_API_KEY:-${PLANE_33GOD_API_KEY:-}}"

export FLEET_ENV HERMES_BIN HERMES_AGENT_REPO HERMES_OAUTH_FILE CODEX_HOME \
       RUNTIME_SCAFFOLD_DIR REGISTRY_FILE \
       BLOODBANK_NATS_HOST BLOODBANK_NATS_PORT BLOODBANK_COMPOSE_DIR \
       PLANE_BASE PLANE_API_KEY

# systemd --user health check. Accept running/degraded/starting — only one
# broken unit shouldn't disqualify the rest of the user manager.
systemd_user_available() {
  command -v systemctl >/dev/null || return 1
  local state; state=$(systemctl --user is-system-running 2>&1)
  [[ "$state" =~ ^(running|degraded|starting|maintenance)$ ]]
}

# Resolve project repo path (the repo that holds agents/hermes/<role>/).
# Walk up from $ROLE_DIR until we find a git root that isn't us.
project_repo_path() {
  local d="$ROLE_DIR"
  [[ -d "$d/.git" || -f "$d/.git" ]] && { echo "$d"; return 0; }
  for _ in 1 2 3 4 5; do
    d="$(dirname "$d")"
    [[ -d "$d/.git" || -f "$d/.git" ]] && { echo "$d"; return 0; }
  done
  return 1
}

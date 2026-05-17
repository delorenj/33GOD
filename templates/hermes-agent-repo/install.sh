#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $(basename "$0") <repo-path> [--agent-name <name>] [--provision]
USAGE
}

if [[ ${1:-} == "" || ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

REPO_PATH="$(realpath "$1")"
shift || true
AGENT_NAME="hermes"
DO_PROVISION="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent-name)
      AGENT_NAME="$2"
      shift 2
      ;;
    --provision)
      DO_PROVISION="1"
      shift
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -d "$REPO_PATH" ]]; then
  echo "Repo path does not exist: $REPO_PATH" >&2
  exit 1
fi

if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repo: $REPO_PATH" >&2
  exit 1
fi

if [[ ! "$AGENT_NAME" =~ ^[a-z0-9-]+$ ]]; then
  echo "Invalid agent name (use lowercase letters, digits, hyphen): $AGENT_NAME" >&2
  exit 1
fi

REPO_SLUG="$(basename "$REPO_PATH" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
AGENT_DIR="$REPO_PATH/agents/$AGENT_NAME"
BIN_DIR="$AGENT_DIR/bin"
RUNTIME_DIR="$AGENT_DIR/runtime"
LAUNCHER_NAME="$AGENT_NAME-$REPO_SLUG"

mkdir -p "$BIN_DIR" "$RUNTIME_DIR"

if [[ ! -f "$REPO_PATH/agents/README.md" ]]; then
  cat > "$REPO_PATH/agents/README.md" <<AGENTS_README
# Repo Agents

Repository-local autonomous agents live here.

## Rule
Each deployed agent for this repository must live inside this repository and remain independently operable.
AGENTS_README
fi

cat > "$AGENT_DIR/README.md" <<AGENT_README
# ${AGENT_NAME^} (${REPO_SLUG})

${AGENT_NAME^} is the repository-scoped PM/ingress agent for this repository.

## Contract
- Consumes Bloodbank events relevant to this repository.
- Produces Bloodbank events as outputs/decisions/artifacts.
- Operates independently from agent instances assigned to other repositories.

## Initial subject lane (proposed)
- agent.${AGENT_NAME}.${REPO_SLUG}.#

## Usage
From repo root:

\`\`\`bash
./agents/$AGENT_NAME/provision.sh
./agents/$AGENT_NAME/bin/$LAUNCHER_NAME status
./agents/$AGENT_NAME/bin/$LAUNCHER_NAME chat
\`\`\`

## Notes
- Runtime state in \`agents/$AGENT_NAME/runtime\` is intentionally git-ignored.
AGENT_README

cat > "$BIN_DIR/$LAUNCHER_NAME" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${AGENT_DIR}/runtime"
HERMES_BIN="${HERMES_BIN:-/home/delorenj/code/hermes-agent/.venv/bin/hermes}"

if [[ ! -x "$HERMES_BIN" ]]; then
  echo "Hermes binary not found/executable at: $HERMES_BIN" >&2
  echo "Set HERMES_BIN to your hermes executable path and retry." >&2
  exit 1
fi

exec env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" "$@"
LAUNCHER
chmod +x "$BIN_DIR/$LAUNCHER_NAME"

cat > "$AGENT_DIR/provision.sh" <<'PROVISION'
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AGENT_DIR="$REPO_ROOT/agents/$(basename "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")"
HERMES_HOME="$AGENT_DIR/runtime"
HERMES_BIN="${HERMES_BIN:-/home/delorenj/code/hermes-agent/.venv/bin/hermes}"

mkdir -p "$HERMES_HOME"

env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" status >/dev/null
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" config set terminal.cwd "$REPO_ROOT"
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" config set model.default qwen3.6
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" config set model.provider ollama-launch

# Prefer VOX/Y TTS by default for all repo-scoped Hermes runtimes created
# from this template.
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" config set tts.provider vox
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" config set tts.vox.base_url https://vox.delo.sh
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" config set tts.vox.voice rick
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" config set tts.vox.steps 10
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" config set tts.vox.cfg 2
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" config set tts.vox.timeout 60

echo "Provisioned Hermes runtime at: $HERMES_HOME"
env HERMES_HOME="$HERMES_HOME" "$HERMES_BIN" doctor
PROVISION
chmod +x "$AGENT_DIR/provision.sh"

cat > "$RUNTIME_DIR/.gitignore" <<'RUNTIME_IGNORE'
# Runtime state only; keep this directory but do not commit state.
*
!.gitignore
RUNTIME_IGNORE

if [[ ! -f "$REPO_PATH/.gitignore" ]]; then
  touch "$REPO_PATH/.gitignore"
fi

IGNORE_BLOCK=$'\n# Repo-local Hermes runtime state (secrets/sessions/logs)\nagents/'"$AGENT_NAME"$'/runtime/**\n!agents/'"$AGENT_NAME"$'/runtime/.gitignore\n'
if ! grep -q "agents/$AGENT_NAME/runtime/\*\*" "$REPO_PATH/.gitignore"; then
  printf "%s" "$IGNORE_BLOCK" >> "$REPO_PATH/.gitignore"
fi

echo "Installed template in: $AGENT_DIR"
echo "Launcher: $BIN_DIR/$LAUNCHER_NAME"

if [[ "$DO_PROVISION" == "1" ]]; then
  "$AGENT_DIR/provision.sh"
else
  echo "Next: $AGENT_DIR/provision.sh"
fi

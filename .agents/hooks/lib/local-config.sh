#!/usr/bin/env bash
# Per-dev project-hook overrides. Missing/malformed config fails open.

_god_local_json() {
  local root
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." 2>/dev/null && pwd)" || return 1
  printf '%s/.agents/local.json' "$root"
}

_god_listed() {
  local jq_path="$1" value="$2" file
  file="$(_god_local_json)" || return 1
  [[ -f "$file" ]] || return 1
  command -v jq >/dev/null 2>&1 || return 1
  jq -e --arg value "$value" "((${jq_path} // []) | index(\$value)) != null" "$file" >/dev/null 2>&1
}

hook_disabled()  { _god_listed '.hooks.disabled' "$1"; }
agent_disabled() { _god_listed '.hooks.disabled_agents' "$1"; }

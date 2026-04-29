#!/usr/bin/env bash
#
# Bloodbank v3 Event Publisher for Claude Code Hooks
#
# Reads a Claude Code hook payload from stdin, builds a CloudEvents 1.0
# envelope matching holyfields/schemas/_common/cloudevent_base.v1.json, and
# POSTs it to a local Dapr sidecar's publish endpoint. Best-effort by
# design: if the sidecar is not reachable, the hook silently exits 0 so
# Claude Code never blocks waiting on the event bus.
#
# Usage:
#   cat hook_input.json | bloodbank-publisher.sh <event-type> [end-reason]
#
# Event types:
#   tool-action       -> event.agent.tool.invoked
#   tool-request      -> event.agent.tool.requested
#   session-start     -> event.agent.session.started
#   session-end       -> event.agent.session.ended
#   prompt-submitted  -> event.agent.prompt.submitted
#   subagent-stopped  -> event.agent.subagent.completed
#
# Environment:
#   BLOODBANK_ENABLED       "false" disables publishing entirely (default: true)
#   BLOODBANK_DEBUG         "true" logs to stderr + error log file
#   BLOODBANK_DAPR_URL      Dapr sidecar HTTP base URL (default: http://localhost:3502)
#   BLOODBANK_PUBSUB        Dapr pubsub component (default: bloodbank-v3-pubsub)
#   BLOODBANK_PUBLISH_TIMEOUT  curl --max-time seconds (default: 2)
#
# Bring up the publish target (a daprd sidecar exposed on host:3503) via:
#   docker compose --project-name bloodbank-v3 \
#     --profile claude-events -f bloodbank/compose/v3/docker-compose.yml \
#     up -d nats nats-init dapr-placement claude-events-recorder daprd-claude-events
#
# When the sidecar is down, errors are logged once to
# .claude/sessions/publish-errors.log (rotated at ~1MB) and the hook
# returns 0. This keeps a record without spamming the user terminal.

set -uo pipefail

BLOODBANK_ENABLED="${BLOODBANK_ENABLED:-true}"
BLOODBANK_DEBUG="${BLOODBANK_DEBUG:-false}"
BLOODBANK_DAPR_URL="${BLOODBANK_DAPR_URL:-http://localhost:3503}"
BLOODBANK_PUBSUB="${BLOODBANK_PUBSUB:-bloodbank-v3-pubsub}"
BLOODBANK_PUBLISH_TIMEOUT="${BLOODBANK_PUBLISH_TIMEOUT:-2}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SESSION_FILE="${PROJECT_ROOT}/.claude/session-tracking.json"
SESSIONS_DIR="${PROJECT_ROOT}/.claude/sessions"
ERROR_LOG="${SESSIONS_DIR}/publish-errors.log"
ERROR_LOG_MAX_BYTES=1048576

mkdir -p "$SESSIONS_DIR" 2>/dev/null || true

log_debug() {
    [[ "$BLOODBANK_DEBUG" == "true" ]] && echo "[bloodbank-publisher] $*" >&2
}

log_error_once() {
    # Append to error log with size-based rotation. Never write to stderr in
    # the non-debug path (Claude Code surfaces stderr as a hook error which
    # was the original failure mode this rewrite eliminates).
    local msg="$*"
    if [[ -f "$ERROR_LOG" ]]; then
        local size
        size=$(stat -c%s "$ERROR_LOG" 2>/dev/null || echo 0)
        if (( size > ERROR_LOG_MAX_BYTES )); then
            mv "$ERROR_LOG" "${ERROR_LOG}.1" 2>/dev/null || true
        fi
    fi
    printf '%s [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$$" "$msg" >> "$ERROR_LOG" 2>/dev/null || true
    [[ "$BLOODBANK_DEBUG" == "true" ]] && echo "[bloodbank-publisher] $msg" >&2
}

now_iso() {
    date -u +%Y-%m-%dT%H:%M:%SZ
}

new_uuid() {
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr '[:upper:]' '[:lower:]'
    else
        # Fallback: extract from /proc/sys/kernel/random/uuid (Linux).
        cat /proc/sys/kernel/random/uuid 2>/dev/null || \
            echo "00000000-0000-0000-0000-$(printf '%012d' "$$$RANDOM")"
    fi
}

git_branch() {
    git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown"
}

git_remote() {
    git -C "$PROJECT_ROOT" remote get-url origin 2>/dev/null || echo ""
}

git_status_word() {
    if git -C "$PROJECT_ROOT" status --porcelain 2>/dev/null | grep -q .; then
        echo "modified"
    else
        echo "clean"
    fi
}

# ---- Session state ---------------------------------------------------------

init_session() {
    local session_id="${1:-$(new_uuid)}"
    local branch
    branch=$(git_branch)
    cat > "$SESSION_FILE" <<EOF
{
  "session_id": "$session_id",
  "started_at": "$(now_iso)",
  "working_directory": "$PWD",
  "git_branch": "$branch",
  "turn_number": 0,
  "tools_used": {}
}
EOF
}

load_session() {
    if [[ ! -f "$SESSION_FILE" ]]; then
        init_session
    fi
    cat "$SESSION_FILE"
}

bump_session_stats() {
    local tool_name="$1"
    local data
    data=$(load_session)
    local current
    current=$(echo "$data" | jq -r --arg t "$tool_name" '.tools_used[$t] // 0')
    local turn
    turn=$(echo "$data" | jq -r '.turn_number // 0')
    echo "$data" | jq \
        --arg t "$tool_name" \
        --argjson c "$((current + 1))" \
        --argjson n "$((turn + 1))" \
        '.tools_used[$t] = $c | .turn_number = $n' \
        > "$SESSION_FILE"
}

# ---- CloudEvents envelope --------------------------------------------------

# Builds an envelope per holyfields/schemas/_common/cloudevent_base.v1.json
# given a CloudEvents `type`, `subject`, and JSON `data` blob.
build_envelope() {
    local ce_type="$1"
    local ce_subject="$2"
    local data_json="$3"
    local correlation_id="${4:-$(new_uuid)}"

    jq -cn \
        --arg id "$(new_uuid)" \
        --arg type "$ce_type" \
        --arg subject "$ce_subject" \
        --arg time "$(now_iso)" \
        --arg correlation "$correlation_id" \
        --argjson data "$data_json" \
        '{
            specversion: "1.0",
            id: $id,
            source: "urn:33god:agent:claude-code",
            type: $type,
            subject: $subject,
            time: $time,
            datacontenttype: "application/json",
            correlationid: $correlation,
            causationid: null,
            producer: "claude-code",
            service: "claude-code",
            domain: "agent",
            schemaref: ($type + ".v1"),
            traceparent: "00-00000000000000000000000000000000-0000000000000000-00",
            data: $data
        }'
}

publish() {
    local topic="$1"
    local envelope="$2"

    if [[ "$BLOODBANK_ENABLED" != "true" ]]; then
        log_debug "publishing disabled, skipping topic=$topic"
        return 0
    fi

    local url="${BLOODBANK_DAPR_URL}/v1.0/publish/${BLOODBANK_PUBSUB}/${topic}"
    log_debug "POST $url"

    local http_code
    http_code=$(curl -sS -o /dev/null -w '%{http_code}' \
        --max-time "$BLOODBANK_PUBLISH_TIMEOUT" \
        -X POST \
        -H "Content-Type: application/cloudevents+json" \
        -d "$envelope" \
        "$url" 2>/dev/null) || http_code="000"

    if [[ "$http_code" =~ ^2[0-9][0-9]$ ]]; then
        log_debug "published ok (http=$http_code) topic=$topic"
        return 0
    fi

    log_error_once "publish failed http=$http_code topic=$topic url=$url"
    return 0  # never fail the hook
}

# ---- Event handlers --------------------------------------------------------

handle_session_start() {
    local session_id
    session_id=$(new_uuid)
    init_session "$session_id"

    local data
    data=$(jq -cn \
        --arg session_id "$session_id" \
        --arg working_directory "$PWD" \
        --arg git_branch "$(git_branch)" \
        --arg git_remote "$(git_remote)" \
        --arg started_at "$(now_iso)" \
        '{
            session_id: $session_id,
            working_directory: $working_directory,
            git_branch: $git_branch,
            git_remote: $git_remote,
            started_at: $started_at
        }')

    local envelope
    envelope=$(build_envelope \
        "agent.session.started" \
        "agent/$session_id" \
        "$data" \
        "$session_id")
    publish "event.agent.session.started" "$envelope"
}

handle_tool_action() {
    local input="$1"
    local session_data
    session_data=$(load_session)

    local session_id tool_name tool_input turn working_dir branch
    session_id=$(echo "$session_data" | jq -r '.session_id')
    tool_name=$(echo "$input" | jq -r '.tool_name // "unknown"')
    tool_input=$(echo "$input" | jq -c '.tool_input // {}')
    turn=$(echo "$session_data" | jq -r '.turn_number // 0')
    working_dir=$(echo "$session_data" | jq -r '.working_directory')
    branch=$(echo "$session_data" | jq -r '.git_branch')

    local data
    data=$(jq -cn \
        --arg session_id "$session_id" \
        --arg tool_name "$tool_name" \
        --argjson tool_input "$tool_input" \
        --arg working_directory "$working_dir" \
        --arg git_branch "$branch" \
        --arg git_status "$(git_status_word)" \
        --argjson turn_number "$((turn + 1))" \
        '{
            session_id: $session_id,
            tool_name: $tool_name,
            tool_input: $tool_input,
            working_directory: $working_directory,
            git_branch: $git_branch,
            git_status: $git_status,
            turn_number: $turn_number,
            success: true
        }')

    local envelope
    envelope=$(build_envelope \
        "agent.tool.invoked" \
        "agent/$session_id/tool/$tool_name" \
        "$data" \
        "$session_id")
    publish "event.agent.tool.invoked" "$envelope"
    bump_session_stats "$tool_name"
}

handle_prompt_submitted() {
    local input="$1"
    local session_data
    session_data=$(load_session)

    local session_id prompt_text working_dir branch
    session_id=$(echo "$session_data" | jq -r '.session_id')
    # The Claude Code UserPromptSubmit hook sends the prompt text in the
    # `prompt` field of the stdin JSON. Be defensive: empty if missing.
    prompt_text=$(echo "$input" | jq -r '.prompt // ""')
    working_dir=$(echo "$session_data" | jq -r '.working_directory')
    branch=$(echo "$session_data" | jq -r '.git_branch')

    local prompt_length
    prompt_length=$(printf %s "$prompt_text" | wc -c | tr -d ' ')

    local data
    data=$(jq -cn \
        --arg session_id "$session_id" \
        --arg prompt_text "$prompt_text" \
        --argjson prompt_length "$prompt_length" \
        --arg working_directory "$working_dir" \
        --arg git_branch "$branch" \
        '{
            session_id: $session_id,
            prompt_text: $prompt_text,
            prompt_length: $prompt_length,
            working_directory: $working_directory,
            git_branch: $git_branch
        }')

    local envelope
    envelope=$(build_envelope \
        "agent.prompt.submitted" \
        "agent/$session_id" \
        "$data" \
        "$session_id")
    publish "event.agent.prompt.submitted" "$envelope"
}

handle_tool_requested() {
    local input="$1"
    local session_data
    session_data=$(load_session)

    local session_id tool_name tool_input turn working_dir branch
    session_id=$(echo "$session_data" | jq -r '.session_id')
    tool_name=$(echo "$input" | jq -r '.tool_name // "unknown"')
    tool_input=$(echo "$input" | jq -c '.tool_input // {}')
    turn=$(echo "$session_data" | jq -r '.turn_number // 0')
    working_dir=$(echo "$session_data" | jq -r '.working_directory')
    branch=$(echo "$session_data" | jq -r '.git_branch')

    # Don't bump_session_stats here; the matching tool.invoked event from
    # PostToolUse will. Both events share turn_number (current+1) so the
    # request/invoke pair correlates on it.
    local data
    data=$(jq -cn \
        --arg session_id "$session_id" \
        --arg tool_name "$tool_name" \
        --argjson tool_input "$tool_input" \
        --arg working_directory "$working_dir" \
        --arg git_branch "$branch" \
        --argjson turn_number "$((turn + 1))" \
        '{
            session_id: $session_id,
            tool_name: $tool_name,
            tool_input: $tool_input,
            working_directory: $working_directory,
            git_branch: $git_branch,
            turn_number: $turn_number
        }')

    local envelope
    envelope=$(build_envelope \
        "agent.tool.requested" \
        "agent/$session_id/tool/$tool_name" \
        "$data" \
        "$session_id")
    publish "event.agent.tool.requested" "$envelope"
}

handle_subagent_completed() {
    local input="$1"
    local session_data
    session_data=$(load_session)

    local session_id working_dir
    session_id=$(echo "$session_data" | jq -r '.session_id')
    working_dir=$(echo "$session_data" | jq -r '.working_directory')

    # Claude Code's SubagentStop hook does not surface a structured stop
    # reason or agent type today; default to "completed" and leave
    # agent_type unset. The schema permits both as optional.
    local data
    data=$(jq -cn \
        --arg session_id "$session_id" \
        --arg working_directory "$working_dir" \
        '{
            session_id: $session_id,
            stop_reason: "completed",
            working_directory: $working_directory
        }')

    local envelope
    envelope=$(build_envelope \
        "agent.subagent.completed" \
        "agent/$session_id/subagent" \
        "$data" \
        "$session_id")
    publish "event.agent.subagent.completed" "$envelope"
}

handle_session_end() {
    local end_reason="${1:-user_stop}"

    if [[ ! -f "$SESSION_FILE" ]]; then
        log_debug "no active session to end"
        return 0
    fi

    local session_data
    session_data=$(load_session)

    local session_id started_at tools_used turn working_dir branch
    session_id=$(echo "$session_data" | jq -r '.session_id')
    started_at=$(echo "$session_data" | jq -r '.started_at')
    tools_used=$(echo "$session_data" | jq -c '.tools_used')
    turn=$(echo "$session_data" | jq -r '.turn_number // 0')
    working_dir=$(echo "$session_data" | jq -r '.working_directory')
    branch=$(echo "$session_data" | jq -r '.git_branch')

    local now duration
    now=$(now_iso)
    duration=$(( $(date -d "$now" +%s) - $(date -d "$started_at" +%s) ))

    local files_modified git_commits
    files_modified=$(git -C "$PROJECT_ROOT" diff --name-only 2>/dev/null | jq -R . | jq -cs . || echo '[]')
    git_commits=$(git -C "$PROJECT_ROOT" log --since="$started_at" --format='%H' 2>/dev/null | jq -R . | jq -cs . || echo '[]')

    local data
    data=$(jq -cn \
        --arg session_id "$session_id" \
        --arg end_reason "$end_reason" \
        --argjson duration_seconds "$duration" \
        --argjson total_turns "$turn" \
        --argjson tools_used "$tools_used" \
        --argjson files_modified "$files_modified" \
        --argjson git_commits "$git_commits" \
        --arg working_directory "$working_dir" \
        --arg git_branch "$branch" \
        '{
            session_id: $session_id,
            end_reason: $end_reason,
            duration_seconds: $duration_seconds,
            total_turns: $total_turns,
            tools_used: $tools_used,
            files_modified: $files_modified,
            git_commits: $git_commits,
            final_status: "success",
            working_directory: $working_directory,
            git_branch: $git_branch
        }')

    local envelope
    envelope=$(build_envelope \
        "agent.session.ended" \
        "agent/$session_id" \
        "$data" \
        "$session_id")
    publish "event.agent.session.ended" "$envelope"

    mv "$SESSION_FILE" "${SESSIONS_DIR}/${session_id}.json" 2>/dev/null || true
}

main() {
    local event_type="${1:-}"
    if [[ -z "$event_type" ]]; then
        log_error_once "missing event-type argument"
        exit 0
    fi

    local input=""
    if [[ ! -t 0 ]]; then
        input=$(cat || true)
    fi

    case "$event_type" in
        tool-action)
            handle_tool_action "$input"
            ;;
        tool-request)
            handle_tool_requested "$input"
            ;;
        session-start)
            handle_session_start
            ;;
        session-end)
            handle_session_end "${2:-user_stop}"
            ;;
        prompt-submitted)
            handle_prompt_submitted "$input"
            ;;
        subagent-stopped)
            handle_subagent_completed "$input"
            ;;
        *)
            log_error_once "unknown event-type: $event_type"
            ;;
    esac
    exit 0
}

main "$@"

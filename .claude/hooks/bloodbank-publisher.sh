#!/usr/bin/env bash
#
# Bloodbank Event Publisher for Claude Code Hooks
#
# This script publishes Claude Code tool usage and session events to Bloodbank.
# It reads hook input from stdin (JSON) and publishes structured events.
#
# Usage: cat hook_input.json | bloodbank-publisher.sh <event-type> [options]
#
# Environment Variables:
#   BLOODBANK_URL - Bloodbank HTTP API endpoint (default: http://localhost:8682)
#   RABBIT_URL - Direct RabbitMQ connection (default: amqp://delorenj:REDACTED_CREDENTIAL@192.168.1.12:5672/)
#   BLOODBANK_ENABLED - Set to "false" to disable publishing (default: true)
#   BLOODBANK_DEBUG - Set to "true" for verbose logging
#
# Event Types:
#   tool-action - Tool was invoked (PostToolUse)
#   session-start - Session started (init hook)
#   session-end - Session ended (Stop hook)
#   session-error - Error occurred
#   thinking - Thinking/reasoning event

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

BLOODBANK_URL="${BLOODBANK_URL:-http://localhost:8682}"
BLOODBANK_ENABLED="${BLOODBANK_ENABLED:-true}"
BLOODBANK_DEBUG="${BLOODBANK_DEBUG:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Session tracking file
SESSION_FILE="${PROJECT_ROOT}/.claude/session-tracking.json"
STATS_FILE="${PROJECT_ROOT}/.claude/session-stats.json"

# ============================================================================
# Utility Functions
# ============================================================================

log_debug() {
    if [[ "$BLOODBANK_DEBUG" == "true" ]]; then
        echo "[bloodbank-publisher] $*" >&2
    fi
}

log_error() {
    echo "[bloodbank-publisher ERROR] $*" >&2
}

# Initialize session tracking
init_session() {
    local session_id="${1:-$(uuidgen)}"
    local git_branch
    git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

    cat > "$SESSION_FILE" <<EOF
{
  "session_id": "$session_id",
  "started_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "working_directory": "$PWD",
  "git_branch": "$git_branch",
  "turn_number": 0,
  "tools_used": {}
}
EOF
    log_debug "Session initialized: $session_id"
}

# Load session data
load_session() {
    if [[ -f "$SESSION_FILE" ]]; then
        cat "$SESSION_FILE"
    else
        init_session
        cat "$SESSION_FILE"
    fi
}

# Update session stats
update_session_stats() {
    local tool_name="$1"
    local session_data
    session_data=$(load_session)

    # Increment tool count
    local current_count
    current_count=$(echo "$session_data" | jq -r ".tools_used[\"$tool_name\"] // 0")
    local new_count=$((current_count + 1))

    # Update turn number
    local turn
    turn=$(echo "$session_data" | jq -r '.turn_number // 0')
    local new_turn=$((turn + 1))

    echo "$session_data" | jq \
        ".tools_used[\"$tool_name\"] = $new_count | .turn_number = $new_turn" \
        > "$SESSION_FILE"
}

# Get hostname
get_hostname() {
    hostname -f 2>/dev/null || hostname || echo "localhost"
}

# Get session ID
get_session_id() {
    if [[ -f "$SESSION_FILE" ]]; then
        jq -r '.session_id' "$SESSION_FILE"
    else
        echo "unknown-session"
    fi
}

# ============================================================================
# Event Publishing Functions
# ============================================================================

publish_to_bloodbank() {
    local event_type="$1"
    local payload="$2"

    if [[ "$BLOODBANK_ENABLED" != "true" ]]; then
        log_debug "Publishing disabled, skipping event: $event_type"
        return 0
    fi

    log_debug "Publishing event: $event_type"
    log_debug "Payload: $payload"

    # Try HTTP API first (faster)
    if curl -f -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "${BLOODBANK_URL}/events/claude-code/${event_type}" \
        > /dev/null 2>&1; then
        log_debug "Event published successfully via HTTP"
        return 0
    fi

    # Fallback to CLI (requires bloodbank package)
    if command -v bb &> /dev/null; then
        log_debug "HTTP failed, trying CLI fallback"
        echo "$payload" | bb publish "$event_type" --json - 2>&1 | log_debug
    else
        log_error "Failed to publish event, bloodbank CLI not available"
        return 1
    fi
}

# ============================================================================
# Event Handlers
# ============================================================================

handle_tool_action() {
    local input="$1"
    local session_data
    session_data=$(load_session)
    local session_id
    session_id=$(echo "$session_data" | jq -r '.session_id')
    local turn_number
    turn_number=$(echo "$session_data" | jq -r '.turn_number')
    local working_dir
    working_dir=$(echo "$session_data" | jq -r '.working_directory')
    local git_branch
    git_branch=$(echo "$session_data" | jq -r '.git_branch')

    # Extract tool info from input
    local tool_name
    tool_name=$(echo "$input" | jq -r '.tool_name // "unknown"')
    local tool_input
    tool_input=$(echo "$input" | jq -c '.tool_input // {}')

    # Get git status
    local git_status
    if git status --porcelain 2>/dev/null | grep -q '^'; then
        git_status="modified"
    else
        git_status="clean"
    fi

    # Build payload
    local payload
    payload=$(jq -n \
        --arg session_id "$session_id" \
        --arg tool_name "$tool_name" \
        --argjson tool_input "$tool_input" \
        --arg working_dir "$working_dir" \
        --arg git_branch "$git_branch" \
        --arg git_status "$git_status" \
        --arg turn_number "$turn_number" \
        '{
            session_id: $session_id,
            tool_metadata: {
                tool_name: $tool_name,
                tool_input: $tool_input,
                success: true
            },
            working_directory: $working_dir,
            git_branch: $git_branch,
            git_status: $git_status,
            turn_number: ($turn_number | tonumber),
            model: "claude-sonnet-4-5"
        }')

    publish_to_bloodbank "tool-action" "$payload"
    update_session_stats "$tool_name"
}

handle_session_end() {
    local input="$1"
    local end_reason="${2:-user_stop}"

    if [[ ! -f "$SESSION_FILE" ]]; then
        log_debug "No active session to end"
        return 0
    fi

    local session_data
    session_data=$(load_session)
    local session_id
    session_id=$(echo "$session_data" | jq -r '.session_id')
    local started_at
    started_at=$(echo "$session_data" | jq -r '.started_at')
    local tools_used
    tools_used=$(echo "$session_data" | jq -c '.tools_used')
    local turn_number
    turn_number=$(echo "$session_data" | jq -r '.turn_number')
    local working_dir
    working_dir=$(echo "$session_data" | jq -r '.working_directory')
    local git_branch
    git_branch=$(echo "$session_data" | jq -r '.git_branch')

    # Calculate duration
    local now
    now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local duration_seconds
    duration_seconds=$(( $(date -d "$now" +%s) - $(date -d "$started_at" +%s) ))

    # Get files modified in this session
    local files_modified
    files_modified=$(git diff --name-only 2>/dev/null | jq -R . | jq -s . || echo '[]')

    # Get commits created
    local git_commits
    git_commits=$(git log --since="$started_at" --format="%H" 2>/dev/null | jq -R . | jq -s . || echo '[]')

    local payload
    payload=$(jq -n \
        --arg session_id "$session_id" \
        --arg end_reason "$end_reason" \
        --arg duration_seconds "$duration_seconds" \
        --arg turn_number "$turn_number" \
        --argjson tools_used "$tools_used" \
        --argjson files_modified "$files_modified" \
        --argjson git_commits "$git_commits" \
        --arg working_dir "$working_dir" \
        --arg git_branch "$git_branch" \
        '{
            session_id: $session_id,
            end_reason: $end_reason,
            duration_seconds: ($duration_seconds | tonumber),
            total_turns: ($turn_number | tonumber),
            tools_used: $tools_used,
            files_modified: $files_modified,
            git_commits: $git_commits,
            final_status: "success",
            working_directory: $working_dir,
            git_branch: $git_branch
        }')

    publish_to_bloodbank "session-end" "$payload"

    # Archive session data
    if [[ ! -d "${PROJECT_ROOT}/.claude/sessions" ]]; then
        mkdir -p "${PROJECT_ROOT}/.claude/sessions"
    fi
    mv "$SESSION_FILE" "${PROJECT_ROOT}/.claude/sessions/${session_id}.json" 2>/dev/null || true
}

handle_session_start() {
    local input="$1"
    local session_id
    session_id=$(uuidgen)

    init_session "$session_id"

    local session_data
    session_data=$(load_session)
    local working_dir
    working_dir=$(echo "$session_data" | jq -r '.working_directory')
    local git_branch
    git_branch=$(echo "$session_data" | jq -r '.git_branch')

    # Get git remote
    local git_remote
    git_remote=$(git remote get-url origin 2>/dev/null || echo "")

    local payload
    payload=$(jq -n \
        --arg session_id "$session_id" \
        --arg working_dir "$working_dir" \
        --arg git_branch "$git_branch" \
        --arg git_remote "$git_remote" \
        '{
            session_id: $session_id,
            working_directory: $working_dir,
            git_branch: $git_branch,
            git_remote: $git_remote,
            model: "claude-sonnet-4-5",
            started_at: (now | todate)
        }')

    publish_to_bloodbank "session-start" "$payload"
}

# ============================================================================
# Main
# ============================================================================

main() {
    local event_type="${1:-}"

    if [[ -z "$event_type" ]]; then
        log_error "Usage: bloodbank-publisher.sh <event-type>"
        exit 1
    fi

    # Read input from stdin
    local input
    input=$(cat)

    log_debug "Processing event type: $event_type"

    case "$event_type" in
        tool-action)
            handle_tool_action "$input"
            ;;
        session-end)
            handle_session_end "$input" "${2:-user_stop}"
            ;;
        session-start)
            handle_session_start "$input"
            ;;
        *)
            log_error "Unknown event type: $event_type"
            exit 1
            ;;
    esac
}

main "$@"

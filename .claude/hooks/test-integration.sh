#!/usr/bin/env bash
#
# Test Bloodbank Integration
#
# Tests the Claude Code -> Bloodbank event publishing pipeline
#

set -euo pipefail

BLOODBANK_URL="${BLOODBANK_URL:-http://localhost:8682}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🧪 Testing Bloodbank Integration"
echo "================================="
echo ""

# ============================================================================
# Test 1: Bloodbank Health Check
# ============================================================================

echo "Test 1: Bloodbank Health Check"
if curl -f -s "${BLOODBANK_URL}/healthz" > /dev/null 2>&1; then
    echo "✅ Bloodbank is running at ${BLOODBANK_URL}"
else
    echo "❌ Bloodbank is not reachable at ${BLOODBANK_URL}"
    echo "   Start Bloodbank with: cd bloodbank/trunk-main && mise run start"
    exit 1
fi
echo ""

# ============================================================================
# Test 2: Hook Script Execution
# ============================================================================

echo "Test 2: Hook Script Execution"
if [[ -x "${SCRIPT_DIR}/bloodbank-publisher.sh" ]]; then
    echo "✅ Hook script is executable"
else
    echo "❌ Hook script is not executable"
    chmod +x "${SCRIPT_DIR}/bloodbank-publisher.sh"
    echo "✅ Fixed permissions"
fi
echo ""

# ============================================================================
# Test 3: Session Start Event
# ============================================================================

echo "Test 3: Session Start Event"
SESSION_ID=$(uuidgen)
echo '{}' | BLOODBANK_DEBUG=true "${SCRIPT_DIR}/bloodbank-publisher.sh" session-start 2>&1 | grep -q "Session initialized"
if [[ $? -eq 0 ]]; then
    echo "✅ Session start event processed"
else
    echo "❌ Session start event failed"
fi
echo ""

# ============================================================================
# Test 4: Tool Action Event
# ============================================================================

echo "Test 4: Tool Action Event"
cat <<EOF | "${SCRIPT_DIR}/bloodbank-publisher.sh" tool-action 2>&1 | tail -1
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "echo 'test integration'",
    "description": "Test command"
  }
}
EOF
if [[ $? -eq 0 ]]; then
    echo "✅ Tool action event processed"
else
    echo "❌ Tool action event failed"
fi
echo ""

# ============================================================================
# Test 5: Direct HTTP Publishing
# ============================================================================

echo "Test 5: Direct HTTP Publishing"
RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "session_id": "test-session",
        "tool_metadata": {
            "tool_name": "Test",
            "tool_input": {},
            "success": true
        },
        "working_directory": "/test",
        "git_branch": "test",
        "git_status": "clean",
        "turn_number": 1,
        "model": "test-model"
    }' \
    "${BLOODBANK_URL}/events/claude-code/tool-action")

if echo "$RESPONSE" | jq -e '.event_id' > /dev/null 2>&1; then
    echo "✅ HTTP publishing successful"
    echo "   Event ID: $(echo "$RESPONSE" | jq -r '.event_id')"
else
    echo "❌ HTTP publishing failed"
    echo "   Response: $RESPONSE"
fi
echo ""

# ============================================================================
# Test 6: Session Tracking Files
# ============================================================================

echo "Test 6: Session Tracking Files"
if [[ -f "${SCRIPT_DIR}/../session-tracking.json" ]]; then
    echo "✅ Session tracking file exists"
    echo "   Session ID: $(jq -r '.session_id' "${SCRIPT_DIR}/../session-tracking.json")"
else
    echo "⚠️  No active session tracking file (normal if no session running)"
fi

if [[ -d "${SCRIPT_DIR}/../sessions" ]]; then
    SESSION_COUNT=$(ls "${SCRIPT_DIR}/../sessions"/*.json 2>/dev/null | wc -l)
    echo "✅ Sessions directory exists"
    echo "   Archived sessions: $SESSION_COUNT"
else
    echo "⚠️  Sessions directory does not exist"
    mkdir -p "${SCRIPT_DIR}/../sessions"
    echo "✅ Created sessions directory"
fi
echo ""

# ============================================================================
# Test 7: Session End Event
# ============================================================================

echo "Test 7: Session End Event"
echo '{}' | "${SCRIPT_DIR}/bloodbank-publisher.sh" session-end user_stop 2>&1 | tail -1
if [[ $? -eq 0 ]]; then
    echo "✅ Session end event processed"
else
    echo "⚠️  Session end event failed (may be normal if no active session)"
fi
echo ""

# ============================================================================
# Summary
# ============================================================================

echo "================================="
echo "🎉 Integration Tests Complete"
echo ""
echo "Next Steps:"
echo "1. Start using Claude Code - hooks will automatically publish events"
echo "2. Monitor events: cd bloodbank/trunk-main && python watch_events.py --pattern 'session.thread.#'"
echo "3. View session history: cat .claude/sessions/*.json | jq"
echo ""
echo "Configuration:"
echo "  BLOODBANK_URL: $BLOODBANK_URL"
echo "  BLOODBANK_ENABLED: ${BLOODBANK_ENABLED:-true}"
echo "  BLOODBANK_DEBUG: ${BLOODBANK_DEBUG:-false}"
echo ""

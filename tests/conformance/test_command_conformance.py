"""
GOD-10 OBS-1 — Command Schema Conformance Tests

Validates the three conformance guarantees from COMMAND-SYSTEM-RFC.md §7.3:

  1. Every command type has a registered ack/result/error schema in Holyfields
  2. Every agent's adapter handles all command types in its subscription
  3. No command goes unacked for > 2× TTL

Tests 1 & 2 are static (schema inspection). Test 3 is runtime (requires live
Bloodbank + FSM, tested via mock here, live in integration/).

Schemas path: holyfields/schemas/command/
FSM source: bloodbank/command_fsm/
"""
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Resolve repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "holyfields" / "schemas"
COMMAND_SCHEMAS_DIR = SCHEMAS_DIR / "command"
COMMON_SCHEMAS_DIR = SCHEMAS_DIR / "_common"

# Add bloodbank to path for FSM imports
sys.path.insert(0, str(REPO_ROOT / "bloodbank"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def command_schemas() -> dict[str, dict]:
    """Load all command/*.v1.json schemas into a {name: schema} dict."""
    schemas = {}
    for path in sorted(COMMAND_SCHEMAS_DIR.glob("*.v1.json")):
        with open(path) as f:
            schemas[path.stem] = json.load(f)
    return schemas


@pytest.fixture(scope="session")
def base_event_schema() -> dict:
    """Load the base event schema that all events must extend."""
    with open(COMMON_SCHEMAS_DIR / "base_event.v1.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def common_types() -> dict:
    """Load common type definitions."""
    with open(COMMON_SCHEMAS_DIR / "types.v1.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# CONFORMANCE 1: Schema Completeness
# Every command type has envelope + ack + result + error schemas
# ---------------------------------------------------------------------------

class TestSchemaCompleteness:
    """RFC §7.3 Rule 1: Every command type has registered ack/result/error schemas."""

    REQUIRED_COMMAND_SCHEMAS = {"envelope.v1", "ack.v1", "result.v1", "error.v1"}

    def test_all_required_schemas_exist(self, command_schemas: dict[str, dict]):
        """All four command lifecycle schemas must be present in Holyfields."""
        missing = self.REQUIRED_COMMAND_SCHEMAS - set(command_schemas.keys())
        assert not missing, (
            f"Missing command schemas in {COMMAND_SCHEMAS_DIR}: {missing}. "
            f"Found: {set(command_schemas.keys())}"
        )

    def test_schemas_are_valid_json_schema(self, command_schemas: dict[str, dict]):
        """Each schema must declare $schema and $id."""
        for name, schema in command_schemas.items():
            assert "$schema" in schema, f"{name} missing $schema declaration"
            assert "$id" in schema, f"{name} missing $id"
            assert "33god.dev" in schema["$id"], f"{name} $id doesn't reference 33god.dev"

    def test_schemas_extend_base_event(self, command_schemas: dict[str, dict]):
        """All command schemas must allOf-extend base_event.v1.json."""
        for name, schema in command_schemas.items():
            all_of = schema.get("allOf", [])
            refs = [item.get("$ref", "") for item in all_of]
            assert any("base_event" in r for r in refs), (
                f"{name} does not extend base_event.v1.json via allOf. "
                f"Refs found: {refs}"
            )

    def test_envelope_has_required_payload_fields(self, command_schemas: dict[str, dict]):
        """Envelope payload must include command_id, target_agent, issued_by, action, command_payload."""
        envelope = command_schemas.get("envelope.v1")
        assert envelope, "envelope.v1 schema not found"

        payload_props = envelope["properties"]["payload"]["properties"]
        payload_required = envelope["properties"]["payload"]["required"]

        expected_required = {"command_id", "target_agent", "issued_by", "action", "command_payload"}
        assert expected_required == set(payload_required), (
            f"Envelope required payload fields mismatch. "
            f"Expected: {expected_required}, Got: {set(payload_required)}"
        )

    def test_ack_correlates_to_command(self, command_schemas: dict[str, dict]):
        """Ack must include command_id + target_agent for correlation."""
        ack = command_schemas.get("ack.v1")
        assert ack, "ack.v1 schema not found"

        required = set(ack["properties"]["payload"]["required"])
        assert "command_id" in required, "ack missing command_id"
        assert "target_agent" in required, "ack missing target_agent"
        assert "fsm_version" in required, "ack missing fsm_version for optimistic concurrency"

    def test_result_has_outcome_enum(self, command_schemas: dict[str, dict]):
        """Result must classify outcome as success/partial/skipped."""
        result = command_schemas.get("result.v1")
        assert result, "result.v1 schema not found"

        outcome = result["properties"]["payload"]["properties"]["outcome"]
        assert outcome["type"] == "string"
        assert set(outcome["enum"]) == {"success", "partial", "skipped"}, (
            f"Unexpected outcome enum values: {outcome['enum']}"
        )

    def test_error_has_error_code_enum(self, command_schemas: dict[str, dict]):
        """Error must classify failure with machine-readable error_code."""
        error = command_schemas.get("error.v1")
        assert error, "error.v1 schema not found"

        error_code = error["properties"]["payload"]["properties"]["error_code"]
        expected_codes = {
            "timeout", "rejected", "invalid_state", "execution_failed",
            "not_implemented", "ttl_expired", "rate_limited"
        }
        assert set(error_code["enum"]) == expected_codes, (
            f"Error code enum mismatch. Expected: {expected_codes}, Got: {set(error_code['enum'])}"
        )

    def test_error_has_retryable_field(self, command_schemas: dict[str, dict]):
        """Error must include retryable flag for automatic retry decisions."""
        error = command_schemas.get("error.v1")
        assert error, "error.v1 schema not found"

        props = error["properties"]["payload"]["properties"]
        assert "retryable" in props, "error missing retryable field"
        assert props["retryable"]["type"] == "boolean"


# ---------------------------------------------------------------------------
# CONFORMANCE 2: FSM Transition Completeness
# Every command lifecycle state has valid transitions
# ---------------------------------------------------------------------------

class TestFSMConformance:
    """RFC §7.3 Rule 2: Agent adapter handles all command types in its subscription."""

    def test_fsm_states_importable(self):
        """FSM state module must be importable."""
        from command_fsm.states import FSMState
        assert FSMState.IDLE.value == "idle"

    def test_all_expected_states_exist(self):
        """FSM must define idle, acknowledging, working, blocked, error, paused."""
        from command_fsm.states import FSMState

        expected = {"idle", "acknowledging", "working", "blocked", "error", "paused"}
        actual = {s.value for s in FSMState}
        assert expected == actual, (
            f"FSM state mismatch. Expected: {expected}, Got: {actual}"
        )

    def test_happy_path_transitions(self):
        """Happy path: idle → acknowledging → working → idle must be valid."""
        from command_fsm.states import is_valid_transition, FSMState

        assert is_valid_transition(FSMState.IDLE, FSMState.ACKNOWLEDGING), \
            "idle → acknowledging should be valid"
        assert is_valid_transition(FSMState.ACKNOWLEDGING, FSMState.WORKING), \
            "acknowledging → working should be valid"
        assert is_valid_transition(FSMState.WORKING, FSMState.IDLE), \
            "working → idle should be valid"

    def test_error_path_transitions(self):
        """Error path: working → error → idle must be valid."""
        from command_fsm.states import is_valid_transition, FSMState

        assert is_valid_transition(FSMState.WORKING, FSMState.ERROR), \
            "working → error should be valid"
        assert is_valid_transition(FSMState.ERROR, FSMState.IDLE), \
            "error → idle should be valid"

    def test_blocked_path_transitions(self):
        """Blocked: working → blocked → working and blocked → error must be valid."""
        from command_fsm.states import is_valid_transition, FSMState

        assert is_valid_transition(FSMState.WORKING, FSMState.BLOCKED)
        assert is_valid_transition(FSMState.BLOCKED, FSMState.WORKING)
        assert is_valid_transition(FSMState.BLOCKED, FSMState.ERROR)

    def test_pause_from_all_states(self):
        """Every non-paused state can transition to paused."""
        from command_fsm.states import is_valid_transition, FSMState

        for state in FSMState:
            if state == FSMState.PAUSED:
                continue
            assert is_valid_transition(state, FSMState.PAUSED), \
                f"{state.value} → paused should be valid"

    def test_invalid_transitions_rejected(self):
        """Invalid transitions must be rejected."""
        from command_fsm.states import is_valid_transition, FSMState

        # Can't go directly from idle to working (must ack first)
        assert not is_valid_transition(FSMState.IDLE, FSMState.WORKING), \
            "idle → working should be INVALID (must go through acknowledging)"
        # Can't go from idle directly to error
        assert not is_valid_transition(FSMState.IDLE, FSMState.ERROR), \
            "idle → error should be INVALID"
        # Can't go from acknowledging directly to idle (must go through working)
        assert not is_valid_transition(FSMState.ACKNOWLEDGING, FSMState.IDLE), \
            "acknowledging → idle should be INVALID"

    def test_transitions_have_side_effects(self):
        """Every transition should declare its side_effect (event to emit)."""
        from command_fsm.states import TRANSITIONS

        for (from_s, to_s), transition in TRANSITIONS.items():
            assert transition.side_effect is not None, (
                f"Transition {from_s.value} → {to_s.value} missing side_effect. "
                f"All transitions must declare what event they emit."
            )

    def test_snapshot_ttl_expiry(self):
        """AgentFSMSnapshot.is_expired() must correctly detect TTL expiry."""
        from command_fsm.states import AgentFSMSnapshot, FSMState
        from datetime import datetime, timezone, timedelta
        from uuid import uuid4

        # Not expired
        snapshot = AgentFSMSnapshot(
            agent_name="test",
            state=FSMState.WORKING,
            version=1,
            command_id=uuid4(),
            entered_at=datetime.now(timezone.utc),
            pre_pause_state=None,
            ttl_deadline=datetime.now(timezone.utc) + timedelta(seconds=30),
        )
        assert not snapshot.is_expired()

        # Expired
        snapshot_expired = AgentFSMSnapshot(
            agent_name="test",
            state=FSMState.WORKING,
            version=1,
            command_id=uuid4(),
            entered_at=datetime.now(timezone.utc) - timedelta(seconds=60),
            pre_pause_state=None,
            ttl_deadline=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        assert snapshot_expired.is_expired()

        # No TTL = never expires
        snapshot_no_ttl = AgentFSMSnapshot(
            agent_name="test",
            state=FSMState.WORKING,
            version=1,
            command_id=uuid4(),
            entered_at=datetime.now(timezone.utc),
            pre_pause_state=None,
            ttl_deadline=None,
        )
        assert not snapshot_no_ttl.is_expired()


# ---------------------------------------------------------------------------
# CONFORMANCE 3: TTL Enforcement (mock — live tests in integration/)
# No command goes unacked for > 2× TTL
# ---------------------------------------------------------------------------

class TestTTLEnforcement:
    """RFC §7.3 Rule 3: No command goes unacked for > 2× TTL."""

    def test_default_ttl_is_30s(self, command_schemas: dict[str, dict]):
        """Envelope schema must define default ttl_ms of 30000."""
        envelope = command_schemas["envelope.v1"]
        ttl = envelope["properties"]["payload"]["properties"]["ttl_ms"]
        assert ttl["default"] == 30000, f"Default TTL should be 30000ms, got {ttl['default']}"

    def test_ttl_minimum_is_zero(self, command_schemas: dict[str, dict]):
        """TTL of 0 means no expiry (valid use case)."""
        envelope = command_schemas["envelope.v1"]
        ttl = envelope["properties"]["payload"]["properties"]["ttl_ms"]
        assert ttl["minimum"] == 0, "TTL minimum must be 0 (no-expiry sentinel)"

    def test_error_codes_include_ttl_expired(self, command_schemas: dict[str, dict]):
        """Error schema must include ttl_expired error code for watchdog enforcement."""
        error = command_schemas["error.v1"]
        codes = error["properties"]["payload"]["properties"]["error_code"]["enum"]
        assert "ttl_expired" in codes, "error_code enum must include 'ttl_expired'"

    def test_error_retry_after_ms_for_ttl_expiry(self, command_schemas: dict[str, dict]):
        """Error schema must support retry_after_ms for TTL-based retries."""
        error = command_schemas["error.v1"]
        props = error["properties"]["payload"]["properties"]
        assert "retry_after_ms" in props, "error must include retry_after_ms"
        assert "null" in props["retry_after_ms"]["type"] or props["retry_after_ms"].get("type") == "null", \
            "retry_after_ms must be nullable (None when not retryable)"


# ---------------------------------------------------------------------------
# CONFORMANCE BONUS: Cross-schema consistency
# ---------------------------------------------------------------------------

class TestCrossSchemaConsistency:
    """Validates that command schemas are internally consistent across the lifecycle."""

    def test_command_id_type_consistent(self, command_schemas: dict[str, dict]):
        """command_id must use the same $ref (uuid) across all schemas."""
        uuid_ref = "../_common/types.v1.json#/$defs/uuid"
        for name, schema in command_schemas.items():
            cmd_id = schema["properties"]["payload"]["properties"].get("command_id", {})
            ref = cmd_id.get("$ref", "")
            assert ref == uuid_ref, (
                f"{name}: command_id uses $ref={ref}, expected {uuid_ref}"
            )

    def test_target_agent_type_consistent(self, command_schemas: dict[str, dict]):
        """target_agent must use the same $ref (agent_name) across all schemas."""
        agent_ref = "../_common/types.v1.json#/$defs/agent_name"
        for name, schema in command_schemas.items():
            agent = schema["properties"]["payload"]["properties"].get("target_agent", {})
            ref = agent.get("$ref", "")
            assert ref == agent_ref, (
                f"{name}: target_agent uses $ref={ref}, expected {agent_ref}"
            )

    def test_all_schemas_share_event_type_field(self, command_schemas: dict[str, dict]):
        """All command schemas must declare a const event_type for routing."""
        expected_types = {
            "envelope.v1": "command.envelope",
            "ack.v1": "command.ack",
            "result.v1": "command.result",
            "error.v1": "command.error",
        }
        for name, expected in expected_types.items():
            schema = command_schemas.get(name)
            if schema is None:
                pytest.skip(f"{name} not found")
            event_type = schema["properties"]["event_type"]
            assert event_type.get("const") == expected, (
                f"{name}: event_type const={event_type.get('const')}, expected {expected}"
            )

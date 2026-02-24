"""
Tests for hookd-bridge translation layer (GOD-11 MIG-1).

Validates hook → CommandEnvelope mapping without requiring AMQP connectivity.
"""
import sys
from pathlib import Path
from uuid import UUID

import pytest

# Add hookd to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hookd"))

from bridge import (
    CommandEnvelope,
    CommandPriority,
    hook_to_command,
    infer_action,
    infer_agent,
    infer_priority,
)


class TestInferAgent:
    """Agent name extraction from hook paths and payloads."""

    def test_hooks_agent_path(self):
        assert infer_agent("/hooks/cack", {}) == "cack"

    def test_hooks_agent_subpath(self):
        assert infer_agent("/hooks/agent/rererere", {}) == "rererere"

    def test_hooks_agent_with_action(self):
        assert infer_agent("/hooks/lenoon/drift_check", {}) == "lenoon"

    def test_payload_target_agent_overrides_path(self):
        assert infer_agent("/hooks/cack", {"target_agent": "grolf"}) == "grolf"

    def test_payload_agent_field(self):
        assert infer_agent("/hooks/unknown", {"agent": "tonny"}) == "tonny"

    def test_fallback_unknown(self):
        assert infer_agent("/", {}) == "unknown"


class TestInferAction:
    """Action inference from hook paths and payloads."""

    def test_explicit_action_in_payload(self):
        assert infer_action("/hooks/cack", {"action": "deploy_service"}) == "deploy_service"

    def test_heartbeat_path(self):
        assert infer_action("/hooks/cack/heartbeat", {}) == "process_heartbeat"

    def test_system_heartbeat_tick(self):
        payload = {"event_type": "system.heartbeat.tick"}
        assert infer_action("/hooks/cack/system.heartbeat.tick", payload) == "process_heartbeat"

    def test_webhook_path(self):
        assert infer_action("/hooks/lenoon/webhook", {}) == "process_webhook"

    def test_task_assign_path(self):
        assert infer_action("/hooks/rererere/task.assign", {}) == "execute_task"

    def test_unknown_path_fallback(self):
        result = infer_action("/hooks/cack/custom-thing", {})
        assert result == "hooks_cack_custom_thing"


class TestInferPriority:
    """Priority inference from payloads."""

    def test_explicit_priority(self):
        assert infer_priority({"priority": "critical"}) == CommandPriority.CRITICAL

    def test_heartbeat_is_low(self):
        assert infer_priority({"event_type": "system.heartbeat.tick"}) == CommandPriority.LOW

    def test_default_normal(self):
        assert infer_priority({}) == CommandPriority.NORMAL

    def test_invalid_priority_defaults(self):
        assert infer_priority({"priority": "mega-urgent"}) == CommandPriority.NORMAL


class TestHookToCommand:
    """End-to-end hook → CommandEnvelope translation."""

    def test_basic_translation(self):
        envelope = hook_to_command(
            "/hooks/cack/heartbeat",
            {"event_type": "system.heartbeat.tick", "data": {"uptime": 3600}},
        )

        assert isinstance(envelope, CommandEnvelope)
        assert envelope.payload.target_agent == "cack"
        assert envelope.payload.action == "process_heartbeat"
        assert envelope.payload.issued_by == "hookd-bridge"
        assert envelope.payload.priority == CommandPriority.LOW
        assert envelope.payload.ttl_ms == 30_000
        assert "data" in envelope.payload.command_payload

    def test_correlation_id_passthrough(self):
        corr_id = "test-correlation-123"
        envelope = hook_to_command("/hooks/cack", {}, correlation_id=corr_id)
        assert envelope.correlation_id == corr_id

    def test_correlation_id_generated_when_missing(self):
        envelope = hook_to_command("/hooks/cack", {})
        # Should be a valid UUID
        UUID(envelope.correlation_id)

    def test_command_id_is_uuid(self):
        envelope = hook_to_command("/hooks/cack", {})
        UUID(envelope.payload.command_id)

    def test_event_type_is_command_envelope(self):
        envelope = hook_to_command("/hooks/cack", {})
        assert envelope.event_type == "command.envelope"

    def test_version_is_1_0_0(self):
        envelope = hook_to_command("/hooks/cack", {})
        assert envelope.version == "1.0.0"

    def test_source_app_is_hookd_bridge(self):
        envelope = hook_to_command("/hooks/cack", {})
        assert envelope.source.app == "hookd-bridge"
        assert envelope.source.trigger_type == "webhook"

    def test_metadata_fields_stripped_from_command_payload(self):
        """target_agent, action, priority should not be duplicated in command_payload."""
        envelope = hook_to_command(
            "/hooks/cack",
            {"target_agent": "cack", "action": "test", "priority": "high", "real_data": 42},
        )
        assert "target_agent" not in envelope.payload.command_payload
        assert "action" not in envelope.payload.command_payload
        assert "priority" not in envelope.payload.command_payload
        assert envelope.payload.command_payload["real_data"] == 42

    def test_custom_ttl_from_payload(self):
        envelope = hook_to_command("/hooks/cack", {"ttl_ms": 60_000})
        assert envelope.payload.ttl_ms == 60_000

    def test_idempotency_key_passthrough(self):
        envelope = hook_to_command("/hooks/cack", {"idempotency_key": "dedup-123"})
        assert envelope.payload.idempotency_key == "dedup-123"

    def test_webhook_translation(self):
        envelope = hook_to_command(
            "/hooks/lenoon/webhook",
            {"source": "github", "event": "push", "repo": "33GOD"},
        )
        assert envelope.payload.target_agent == "lenoon"
        assert envelope.payload.action == "process_webhook"
        assert envelope.payload.command_payload["source"] == "github"

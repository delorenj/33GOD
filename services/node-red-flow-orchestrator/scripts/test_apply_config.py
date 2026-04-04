"""P1 tests for apply_config.py (T20-T23)."""
import json
import tempfile
import os

from apply_config import apply_config


def _write_json(tmp_dir, filename, data):
    """Helper: write a Python object as JSON to a temp file, return path."""
    path = os.path.join(tmp_dir, filename)
    with open(path, "w") as f:
        json.dump(data, f)
    return path


# T20: apply_config() substitutes ${KEY} in JSON string values
def test_substitutes_placeholder_in_string_values():
    with tempfile.TemporaryDirectory() as tmp:
        flow_path = _write_json(tmp, "flow.json", [
            {"id": "test", "name": "${FLOW_NAME}", "value": 42}
        ])
        config_path = _write_json(tmp, "config.json", {"FLOW_NAME": "my-flow"})

        raw = apply_config(flow_path, config_path)
        result = json.loads(raw)

        assert result[0]["name"] == "my-flow"
        assert result[0]["value"] == 42


# T21: apply_config() leaves non-string values untouched
def test_non_string_values_preserved():
    with tempfile.TemporaryDirectory() as tmp:
        flow_path = _write_json(tmp, "flow.json", [
            {"count": 42, "active": True, "tags": ["a", "b"], "meta": None}
        ])
        config_path = _write_json(tmp, "config.json", {"UNUSED": "whatever"})

        raw = apply_config(flow_path, config_path)
        result = json.loads(raw)

        assert result[0]["count"] == 42
        assert result[0]["active"] is True
        assert result[0]["tags"] == ["a", "b"]
        assert result[0]["meta"] is None


# T22: apply_config() preserves unmatched ${UNKNOWN} placeholders
def test_unmatched_placeholder_preserved():
    with tempfile.TemporaryDirectory() as tmp:
        flow_path = _write_json(tmp, "flow.json", [
            {"name": "${UNKNOWN_VAR}"}
        ])
        config_path = _write_json(tmp, "config.json", {"OTHER": "value"})

        raw = apply_config(flow_path, config_path)
        result = json.loads(raw)

        assert result[0]["name"] == "${UNKNOWN_VAR}"


# T23: apply_config() does not recurse on substituted values
def test_no_recursive_substitution():
    with tempfile.TemporaryDirectory() as tmp:
        flow_path = _write_json(tmp, "flow.json", [
            {"name": "${KEY1}"}
        ])
        config_path = _write_json(tmp, "config.json", {
            "KEY1": "${KEY2}",
            "KEY2": "recursed",
        })

        raw = apply_config(flow_path, config_path)
        result = json.loads(raw)

        assert result[0]["name"] == "${KEY2}"

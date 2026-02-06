"""Unit tests for semantic enrichment logic."""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import RepoContext, ToolMutationEvent, EnrichedMutation
from src.enrichment import enrich, classify_intent, classify_domain, compute_language


def make_event(
    tool_name: str = "Write",
    file_path: str | None = "/home/user/project/src/main.rs",
    file_ext: str | None = "rs",
    lines_changed: int | None = 42,
    branch: str = "feature/hookd",
) -> ToolMutationEvent:
    return ToolMutationEvent(
        event_type=f"tool.mutation.{tool_name.lower()}",
        hook_type="post_tool_use",
        tool_name=tool_name,
        agent_id="claude-test-123",
        repo=RepoContext(
            git_root="/home/user/project",
            branch=branch,
            head_sha="abc123",
            remote_url="git@github.com:user/project.git",
        ),
        file_path=file_path,
        file_ext=file_ext,
        lines_changed=lines_changed,
        raw_payload={"tool_input": {"file_path": file_path, "content": "hello"}},
        timestamp=datetime.now(timezone.utc),
        source_pid=12345,
        correlation_id="test-corr-001",
    )


def test_classify_intent_test_file():
    event = make_event(file_path="/home/user/project/tests/test_auth.py", file_ext="py")
    assert classify_intent(event) == "test"


def test_classify_intent_config():
    event = make_event(file_path="/home/user/project/config/settings.yaml", file_ext="yaml")
    assert classify_intent(event) == "configuration"


def test_classify_intent_docs():
    event = make_event(file_path="/home/user/project/docs/README.md", file_ext="md")
    assert classify_intent(event) == "documentation"


def test_classify_intent_new_file():
    event = make_event(tool_name="Write", file_path="/home/user/project/src/new.rs")
    assert classify_intent(event) == "new-file"


def test_classify_intent_edit():
    event = make_event(tool_name="Edit", file_path="/home/user/project/src/lib.rs")
    assert classify_intent(event) == "modification"


def test_classify_intent_docker():
    event = make_event(file_path="/home/user/project/Dockerfile")
    assert classify_intent(event) == "infrastructure"


def test_classify_intent_ci():
    event = make_event(file_path="/home/user/project/.github/workflows/ci.yml")
    assert classify_intent(event) == "ci-cd"


def test_classify_domain_src():
    assert classify_domain("/home/user/project/src/main.rs") == "implementation"


def test_classify_domain_test():
    assert classify_domain("/home/user/project/tests/test_auth.py") == "testing"


def test_classify_domain_api():
    assert classify_domain("/home/user/project/src/api/routes.rs") == "api-layer"


def test_compute_language():
    assert compute_language("/foo/bar.rs", "rs") == "rust"
    assert compute_language("/foo/bar.py", "py") == "python"
    assert compute_language("/foo/bar.tsx", "tsx") == "react-typescript"
    assert compute_language("/foo/Cargo.toml", "toml") == "config"
    assert compute_language("/foo/Dockerfile", None) == "dockerfile"


def test_enrich_produces_summary():
    event = make_event()
    enriched = enrich(event)

    assert isinstance(enriched, EnrichedMutation)
    assert enriched.intent == "new-file"
    assert enriched.domain == "implementation"
    assert enriched.language == "rust"
    assert "Agent claude-test-123" in enriched.summary
    assert "src/main.rs" in enriched.summary
    assert "rust" in enriched.summary
    assert "feature/hookd" in enriched.summary


def test_enrich_bash_event():
    event = make_event(tool_name="Bash", file_path=None, file_ext=None, lines_changed=None)
    enriched = enrich(event)
    assert enriched.intent == "command-execution"
    assert enriched.language == "unknown"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    exit(1 if failed else 0)

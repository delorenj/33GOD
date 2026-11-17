"""Static guard: every Dapr publisher into Bloodbank sends application/cloudevents+json.

Why (33GOD-95): POSTing a bare dict to
`/v1.0/publish/<pubsub>/<topic>` with Content-Type application/json makes Dapr
wrap it as `com.dapr.event.sent`; the type, producer, service, domain and kind
vanish and Candystore dead-letters it (reason=malformed). Only a body sent as
application/cloudevents+json passes through as the envelope the publisher built.

This test scans every non-test .py under 33god-platform/ and bloodbank/services/
for a Dapr publish call (a string literal containing "/v1.0/publish/" in code,
not in a docstring or comment) and fails if the same file never uses the
"application/cloudevents+json" content type. One level up from the enricher
fix: the next service that publishes through a Dapr sidecar inherits the check.

Exempt by construction: files that only MENTION the publish path in prose.
aperture/groups/g3/heartbeat/main.py is one: it publishes straight to NATS
JetStream (nats_publish.publish_event), there is no Dapr sidecar on G3.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parent
SCAN_ROOTS = (PLATFORM_ROOT, REPO_ROOT / "bloodbank" / "services")

PUBLISH_MARKER = "/v1.0/publish/"
CLOUDEVENTS = "application/cloudevents+json"
SKIP_PARTS = {"tests", "test", "node_modules", ".venv", "venv", "__pycache__", ".git", "site-packages"}


def _is_test_file(path: Path) -> bool:
    return bool(SKIP_PARTS & set(path.parts)) or path.name.startswith("test_") or path.name.endswith("_test.py") or path.name == "conftest.py"


def _string_constants(tree: ast.AST) -> list[str]:
    """All string literals in code, excluding docstrings (f-string literal parts included)."""
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
    ]


def violation(source: str) -> str | None:
    """Return a reason when `source` publishes through Dapr without cloudevents+json, else None."""
    strings = _string_constants(ast.parse(source))
    if not any(PUBLISH_MARKER in s for s in strings):
        return None
    if any(CLOUDEVENTS in s for s in strings):
        return None
    return f"posts to {PUBLISH_MARKER} but never sends Content-Type {CLOUDEVENTS}"


def dapr_publishers() -> dict[Path, str | None]:
    """Every non-test .py that makes a Dapr publish call -> its violation (None = ok)."""
    found: dict[Path, str | None] = {}
    for root in SCAN_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if _is_test_file(path.relative_to(REPO_ROOT)):
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if PUBLISH_MARKER not in source:
                continue
            try:
                strings = _string_constants(ast.parse(source))
            except SyntaxError:
                continue
            if any(PUBLISH_MARKER in s for s in strings):
                found[path.relative_to(REPO_ROOT)] = violation(source)
    return found


class ScannerSelfTests(unittest.TestCase):
    """The guard must be able to fail, or a green run proves nothing."""

    def test_bare_json_publisher_is_flagged(self) -> None:
        src = 'import requests\nrequests.post(f"http://d:3500/v1.0/publish/ps/{topic}", json={"a": 1})\n'
        self.assertIsNotNone(violation(src))

    def test_wrong_content_type_is_flagged(self) -> None:
        src = 'h = {"Content-Type": "application/json"}\nu = "/v1.0/publish/ps/t"\n'
        self.assertIsNotNone(violation(src))

    def test_cloudevents_publisher_passes(self) -> None:
        src = 'u = f"{d}/v1.0/publish/ps/t"\nh = {"Content-Type": "application/cloudevents+json"}\n'
        self.assertIsNone(violation(src))

    def test_prose_mention_in_a_docstring_is_not_a_publisher(self) -> None:
        src = '"""Emits via POST {dapr}/v1.0/publish/{pubsub}/{topic} elsewhere."""\nx = 1\n'
        self.assertIsNone(violation(src))

    def test_mention_in_a_comment_is_not_a_publisher(self) -> None:
        self.assertIsNone(violation("# POST /v1.0/publish/ps/t\nx = 1\n"))


class DaprPublishersSendCloudEventsTests(unittest.TestCase):
    def test_scan_actually_finds_the_known_publishers(self) -> None:
        found = {str(p) for p in dapr_publishers()}
        self.assertIn("33god-platform/enricher/main.py", found)
        self.assertIn("bloodbank/services/heartbeat-tick/main.py", found)

    def test_aperture_g3_heartbeat_is_not_a_dapr_publisher(self) -> None:
        # It names the Dapr path in prose only and publishes to NATS directly.
        self.assertNotIn(
            Path("33god-platform/aperture/groups/g3/heartbeat/main.py"),
            dapr_publishers(),
        )

    def test_every_dapr_publisher_sends_application_cloudevents_json(self) -> None:
        bad = {str(p): why for p, why in dapr_publishers().items() if why}
        self.assertEqual(
            bad,
            {},
            "Dapr wraps any other Content-Type as com.dapr.event.sent and Candystore dead-letters it "
            "(33GOD-95). Send the full Bloodbank envelope with Content-Type application/cloudevents+json.",
        )


if __name__ == "__main__":
    unittest.main()

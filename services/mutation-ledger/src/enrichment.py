"""Semantic enrichment of tool mutation events.

Classifies change intent, computes complexity signals, and generates
a human-readable summary suitable for embedding.
"""

import re
from pathlib import PurePosixPath

from .models import EnrichedMutation, ToolMutationEvent

# File extension to language/domain mapping
EXT_MAP: dict[str, str] = {
    "rs": "rust",
    "py": "python",
    "ts": "typescript",
    "tsx": "react-typescript",
    "js": "javascript",
    "jsx": "react-javascript",
    "toml": "config",
    "yaml": "config",
    "yml": "config",
    "json": "config",
    "md": "documentation",
    "sql": "database",
    "sh": "shell",
    "bash": "shell",
    "css": "styling",
    "html": "markup",
    "dockerfile": "infrastructure",
    "lock": "lockfile",
}

# Path patterns for intent classification
INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"test[s_]?/|_test\.|\.test\.|spec\.", "test"),
    (r"\.lock$|lock\.json$", "dependency-lock"),
    (r"migrations?/|schema\.", "schema-migration"),
    (r"config/|\.env|settings\.", "configuration"),
    (r"docs?/|README|CHANGELOG|\.md$", "documentation"),
    (r"Dockerfile|docker-compose|\.dockerignore", "infrastructure"),
    (r"\.github/|\.gitlab|ci/|cd/", "ci-cd"),
    (r"__init__|mod\.rs$|index\.", "module-structure"),
]


def classify_intent(event: ToolMutationEvent) -> str:
    """Classify the mutation intent based on file path and tool context."""
    path = event.file_path or ""

    for pattern, intent in INTENT_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return intent

    # Heuristic: new file (Write) vs modification (Edit/MultiEdit)
    tool = event.tool_name.lower()
    if tool == "write":
        return "new-file"
    elif tool in ("edit", "multiedit"):
        return "modification"
    elif tool == "bash":
        return "command-execution"
    elif tool == "notebookedit":
        return "notebook-edit"

    return "unknown"


def classify_domain(file_path: str | None) -> str:
    """Classify the architectural domain from the file path."""
    if not file_path:
        return "unknown"

    path_lower = file_path.lower()

    # Check specific domains before generic /src/ catch-all
    # Use trailing slash patterns to avoid false matches (e.g. /test-project/)
    if any(p in path_lower for p in ["/tests/", "/test/", "/spec/", "/fixture/", "/_test.", ".test.", ".spec."]):
        return "testing"
    if any(p in path_lower for p in ["/api/", "/routes/", "/handlers/"]):
        return "api-layer"
    if any(p in path_lower for p in ["/models/", "/model/", "/schemas/", "/schema/", "/entities/", "/entity/"]):
        return "data-layer"
    if any(p in path_lower for p in ["/config/", "/configs/", "/settings/", ".env"]):
        return "configuration"
    if any(p in path_lower for p in ["/docs/", "/doc/", "/readme", "/changelog"]):
        return "documentation"
    if any(p in path_lower for p in ["/deploy/", "/infra/", "/docker/", "/ci/", "/cd/"]):
        return "infrastructure"
    if any(p in path_lower for p in ["/src/", "/lib/", "/core/"]):
        return "implementation"

    return "general"


def compute_language(file_path: str | None, file_ext: str | None) -> str:
    """Determine the language/technology from file metadata."""
    ext = (file_ext or "").lower().lstrip(".")

    if ext in EXT_MAP:
        return EXT_MAP[ext]

    # Check filename patterns
    if file_path:
        name = PurePosixPath(file_path).name.lower()
        if name in ("dockerfile", "makefile", "justfile"):
            return name
        if name.startswith("cargo"):
            return "rust"
        if name.startswith("pyproject") or name == "setup.py":
            return "python"
        if name.startswith("package") or name == "tsconfig.json":
            return "typescript"

    return ext or "unknown"


def generate_summary(event: ToolMutationEvent, intent: str, domain: str, language: str) -> str:
    """Generate a human-readable summary for embedding.

    This summary is what gets vectorized. It should capture the semantic
    meaning of the mutation in natural language.
    """
    parts = []

    # Agent context
    agent = event.agent_id if event.agent_id != "unknown" else "an agent"
    parts.append(f"Agent {agent}")

    # Action
    tool = event.tool_name.lower()
    if tool == "write":
        parts.append("created")
    elif tool in ("edit", "multiedit"):
        parts.append("modified")
    elif tool == "bash":
        parts.append("executed a command affecting")
    elif tool == "notebookedit":
        parts.append("edited notebook")
    else:
        parts.append(f"used {tool} on")

    # File
    if event.file_path:
        parts.append(f"'{event.file_path}'")
    else:
        parts.append("a file")

    # Language/domain context
    if language != "unknown":
        parts.append(f"({language})")

    # Lines changed
    if event.lines_changed:
        parts.append(f"changing {event.lines_changed} lines")

    # Intent
    parts.append(f"for {intent.replace('-', ' ')}")

    # Branch context
    parts.append(f"on branch '{event.repo.branch}'")

    # Domain
    if domain != "general":
        parts.append(f"in the {domain.replace('-', ' ')} layer")

    return " ".join(parts)


def enrich(event: ToolMutationEvent) -> EnrichedMutation:
    """Enrich a raw ToolMutationEvent with semantic metadata."""
    intent = classify_intent(event)
    domain = classify_domain(event.file_path)
    language = compute_language(event.file_path, event.file_ext)
    summary = generate_summary(event, intent, domain, language)

    return EnrichedMutation(
        event=event,
        intent=intent,
        domain=domain,
        language=language,
        summary=summary,
    )

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RepoContext(BaseModel):
    git_root: str
    branch: str
    head_sha: str
    remote_url: str | None = None


class ToolMutationEvent(BaseModel):
    """Canonical event schema published by hookd daemon."""

    event_type: str
    hook_type: str
    tool_name: str
    agent_id: str
    repo: RepoContext
    file_path: str | None = None
    file_ext: str | None = None
    lines_changed: int | None = None
    raw_payload: dict[str, Any]
    timestamp: datetime
    source_pid: int
    correlation_id: str


class EnrichedMutation(BaseModel):
    """Semantically enriched mutation, ready for embedding."""

    event: ToolMutationEvent
    intent: str          # new-file, modification, test, configuration, etc.
    domain: str          # implementation, testing, api-layer, data-layer, etc.
    language: str        # rust, python, typescript, etc.
    summary: str         # human-readable summary for vector embedding

"""Per-repo SQLite database for append-only mutation storage."""

import json
from pathlib import Path

import aiosqlite
import structlog

from .models import ToolMutationEvent

logger = structlog.get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS mutations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    hook_type TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    file_path TEXT,
    file_ext TEXT,
    lines_changed INTEGER,
    branch TEXT NOT NULL,
    head_sha TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mutations_file ON mutations(file_path);
CREATE INDEX IF NOT EXISTS idx_mutations_timestamp ON mutations(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_mutations_agent ON mutations(agent_id);
CREATE INDEX IF NOT EXISTS idx_mutations_branch ON mutations(branch);
"""


def db_path_for_repo(git_root: str) -> Path:
    """Resolve the SQLite DB path for a given repo root."""
    return Path(git_root) / ".hookd" / "mutations.db"


async def ensure_db(path: Path) -> None:
    """Create the database and schema if it doesn't exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(path)) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def insert_mutation(event: ToolMutationEvent) -> None:
    """Insert a mutation event into the appropriate repo's database."""
    path = db_path_for_repo(event.repo.git_root)
    await ensure_db(path)

    async with aiosqlite.connect(str(path)) as db:
        await db.execute(
            """
            INSERT INTO mutations (
                event_type, hook_type, tool_name, agent_id,
                file_path, file_ext, lines_changed,
                branch, head_sha, correlation_id,
                raw_payload, event_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_type,
                event.hook_type,
                event.tool_name,
                event.agent_id,
                event.file_path,
                event.file_ext,
                event.lines_changed,
                event.repo.branch,
                event.repo.head_sha,
                event.correlation_id,
                json.dumps(event.raw_payload),
                event.timestamp.isoformat(),
            ),
        )
        await db.commit()

    logger.info(
        "mutation_stored",
        repo=event.repo.git_root,
        tool=event.tool_name,
        file=event.file_path,
    )

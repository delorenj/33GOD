"""CLI for querying the mutation ledger (SQLite cache + Qdrant semantic search)."""

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from .config import settings
from .db import db_path_for_repo
from .vector_store import MutationVectorStore, collection_name_for_repo


def parse_since(since_str: str) -> datetime:
    """Parse a relative time string like '1h', '30m', '7d' into a datetime."""
    units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
    unit = since_str[-1]
    if unit not in units:
        raise ValueError(f"Invalid time unit '{unit}'. Use s/m/h/d.")
    value = int(since_str[:-1])
    delta = timedelta(**{units[unit]: value})
    return datetime.now(timezone.utc) - delta


def resolve_git_root(repo_path: str) -> tuple[str, str | None]:
    """Resolve the git root and remote URL for a given path."""
    root_result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if root_result.returncode != 0:
        print(f"Error: not a git repository: {repo_path}", file=sys.stderr)
        sys.exit(1)

    git_root = root_result.stdout.strip()

    remote_result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    remote_url = remote_result.stdout.strip() if remote_result.returncode == 0 else None

    return git_root, remote_url


# ─── SQLite structured queries ───


async def query_mutations_sqlite(
    db_file: Path,
    since: datetime | None = None,
    file_filter: str | None = None,
    agent_filter: str | None = None,
    branch_filter: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Query mutations from the SQLite local cache."""
    if not db_file.exists():
        return []

    conditions = []
    params = []

    if since:
        conditions.append("event_timestamp >= ?")
        params.append(since.isoformat())
    if file_filter:
        conditions.append("file_path LIKE ?")
        params.append(f"%{file_filter}%")
    if agent_filter:
        conditions.append("agent_id = ?")
        params.append(agent_filter)
    if branch_filter:
        conditions.append("branch = ?")
        params.append(branch_filter)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with aiosqlite.connect(str(db_file)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"""
            SELECT id, event_type, tool_name, agent_id, file_path, file_ext,
                   lines_changed, branch, head_sha, event_timestamp
            FROM mutations
            {where}
            ORDER BY event_timestamp ASC
            LIMIT ?
            """,
            [*params, limit],
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ─── Qdrant semantic search ───


def query_mutations_semantic(
    collection: str,
    query: str,
    limit: int = 10,
    branch: str | None = None,
    agent_id: str | None = None,
) -> list[dict]:
    """Semantic search over mutations via Qdrant."""
    store = MutationVectorStore()
    return store.search(
        collection=collection,
        query=query,
        limit=limit,
        branch=branch,
        agent_id=agent_id,
    )


# ─── Formatting ───


def format_text(mutations: list[dict], semantic: bool = False) -> str:
    """Format mutations as human-readable text."""
    if not mutations:
        return "No mutations found."

    lines = []
    for m in mutations:
        if semantic:
            score = f"[{m.get('score', 0):.3f}]"
            summary = m.get("summary", "")
            lines.append(f"  {score} {summary}")
        else:
            ts = m["event_timestamp"][:19]
            tool = m["tool_name"]
            path = m.get("file_path") or "(unknown)"
            agent = m["agent_id"][:12]
            changed = f" ({m['lines_changed']}L)" if m.get("lines_changed") else ""
            lines.append(f"  {ts}  {tool:<10} {path}{changed}  [{agent}]")

    return f"  {len(mutations)} mutations:\n" + "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="hookd-query",
        description="Query the mutation ledger for a repository",
    )
    parser.add_argument(
        "--repo", default=".", help="Path to repository (default: current dir)"
    )

    # Mode: structured (SQLite) or semantic (Qdrant)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--search", "-s",
        help="Semantic search query (e.g. 'authentication changes')",
    )
    mode.add_argument(
        "--since",
        help="Time filter for structured query, e.g. 1h, 30m, 7d",
    )

    parser.add_argument("--file", help="Filter by file path (substring match)")
    parser.add_argument("--agent", help="Filter by agent ID")
    parser.add_argument("--branch", help="Filter by branch name")
    parser.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    git_root, remote_url = resolve_git_root(args.repo)

    if args.search:
        # Semantic search via Qdrant
        collection = collection_name_for_repo(git_root, remote_url)
        mutations = query_mutations_semantic(
            collection=collection,
            query=args.search,
            limit=args.limit,
            branch=args.branch,
            agent_id=args.agent,
        )
        if args.format == "json":
            print(json.dumps(mutations, indent=2, default=str))
        else:
            print(format_text(mutations, semantic=True))
    else:
        # Structured query via SQLite cache
        db_file = db_path_for_repo(git_root)
        since = parse_since(args.since) if args.since else None

        mutations = asyncio.run(
            query_mutations_sqlite(
                db_file,
                since=since,
                file_filter=args.file,
                agent_filter=args.agent,
                branch_filter=args.branch,
                limit=args.limit,
            )
        )

        if args.format == "json":
            print(json.dumps(mutations, indent=2, default=str))
        else:
            print(format_text(mutations))


if __name__ == "__main__":
    main()

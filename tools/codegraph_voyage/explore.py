"""Integration with `codegraph explore` — invokes the codegraph CLI with semantic
candidates as the query input.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .ranking import RankingResult


def codegraph_explore(
    candidates: list[RankingResult],
    project_path: str | Path | None = None,
    max_files: int = 12,
    codegraph_bin: str = "codegraph",
    *,
    dry_run: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """Invoke `codegraph explore` with semantic candidate symbols.

    Builds a query string from the top-ranked candidate names and qualified
    names, then runs `codegraph explore <query>`.

    Args:
        candidates: Ranked results from hybrid search.
        project_path: Project root path (for -p flag).
        max_files: Max files for codegraph explore.
        codegraph_bin: Path to the codegraph binary.
        dry_run: If True, return the command string without running.
        timeout: Timeout in seconds for the subprocess call.

    Returns:
        Dict with keys: command, stdout, stderr, returncode, error.
    """
    # Build query from top candidates — use names and qualified names
    query_parts: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        for part in [c.qualified_name, c.name]:
            if part and part not in seen:
                query_parts.append(part)
                seen.add(part)
            if len(query_parts) >= 20:
                break
        if len(query_parts) >= 20:
            break

    if not query_parts:
        return {
            "command": "",
            "stdout": "",
            "stderr": "No candidate symbols to explore.",
            "returncode": 1,
            "error": "No candidates",
        }

    query_str = " ".join(query_parts)

    cmd = [codegraph_bin, "explore"]
    if project_path:
        cmd.extend(["-p", str(project_path)])
    cmd.append(query_str)
    if max_files:
        cmd.extend(["--max-files", str(max_files)])

    if dry_run:
        return {
            "command": " ".join(cmd),
            "stdout": "",
            "stderr": "",
            "returncode": 0,
            "error": None,
            "query_symbols": query_parts,
        }

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "command": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": None if result.returncode == 0 else result.stderr.strip(),
            "query_symbols": query_parts,
        }
    except FileNotFoundError:
        return {
            "command": " ".join(cmd),
            "stdout": "",
            "stderr": f"codegraph binary not found: {codegraph_bin}",
            "returncode": -1,
            "error": f"Binary not found: {codegraph_bin}",
        }
    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(cmd),
            "stdout": "",
            "stderr": f"codegraph explore timed out after {timeout}s",
            "returncode": -1,
            "error": "Timeout",
        }
    except Exception as exc:
        return {
            "command": " ".join(cmd),
            "stdout": "",
            "stderr": str(exc),
            "returncode": -1,
            "error": str(exc),
        }


def build_explore_query(
    candidates: list[RankingResult],
    max_symbols: int = 20,
) -> str:
    """Build a query string from ranked candidates for codegraph explore.

    Uses the top-ranked candidates, preferring qualified names over simple
    names, and deduplicating.
    """
    parts: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        for field in [c.qualified_name, c.name, c.file_path]:
            if not field:
                continue
            # Transform paths first, then deduplicate the transformed value.
            value = Path(field).stem if field == c.file_path else field
            if value not in seen:
                parts.append(value)
                seen.add(value)
            if len(parts) >= max_symbols:
                break
        if len(parts) >= max_symbols:
            break
    return " ".join(parts[:max_symbols])
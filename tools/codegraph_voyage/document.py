"""Document construction from CodeGraph node metadata.

Builds symbol-level documents from indexed node metadata and source line
ranges read from the CodeGraph DB.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Any


class DocumentConstructionError(Exception):
    """Raised when document construction fails."""


def _read_source_lines(root: Path, file_path: str, start_line: int, end_line: int) -> str:
    """Read source lines from a file within the project root.

    Returns empty string if the file cannot be read or is out of range.
    """
    # Resolve both paths so traversal (../) and symlink escapes cannot read
    # arbitrary host files into an embedding document.
    root_resolved = root.resolve()
    try:
        full = (root_resolved / file_path).resolve()
        full.relative_to(root_resolved)
        text = full.read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, IsADirectoryError, OSError, ValueError):
        return ""
    lines = text.splitlines()
    # start_line/end_line are 1-indexed from CodeGraph
    start = max(0, start_line - 1)
    end = min(len(lines), end_line)
    if start >= end:
        return ""
    return "\n".join(lines[start:end])


def build_document(
    node: dict[str, Any],
    root: Path,
    *,
    include_source: bool = True,
    max_source_lines: int = 200,
) -> str:
    """Build a single symbol-level document from a CodeGraph node.

    The document is a structured text block that combines metadata, docstring,
    signature, and (optionally) source lines.

    Args:
        node: A dict with keys matching the CodeGraph nodes table columns.
        root: Absolute project root path for reading source files.
        include_source: Whether to include source lines in the document.
        max_source_lines: Maximum number of source lines to include (prevents
            giant documents from bloating embeddings).

    Returns:
        A plain-text document string suitable for embedding.
    """
    parts: list[str] = []

    name = node.get("name", "").strip()
    qualified_name = node.get("qualified_name", "").strip()
    kind = node.get("kind", "").strip()
    file_path = node.get("file_path", "").strip()
    language = node.get("language", "").strip()
    docstring = (node.get("docstring") or "").strip()
    signature = (node.get("signature") or "").strip()
    visibility = (node.get("visibility") or "").strip()
    return_type = (node.get("return_type") or "").strip()
    start_line = node.get("start_line")
    end_line = node.get("end_line")

    # --- Header ---
    parts.append(f"Symbol: {name}")
    if qualified_name and qualified_name != name:
        parts.append(f"Qualified Name: {qualified_name}")
    parts.append(f"Kind: {kind}")
    parts.append(f"File: {file_path}")
    if language:
        parts.append(f"Language: {language}")
    if start_line and end_line:
        parts.append(f"Lines: {start_line}-{end_line}")
    if visibility:
        parts.append(f"Visibility: {visibility}")
    if return_type:
        parts.append(f"Return Type: {return_type}")

    # --- Signature ---
    if signature:
        parts.append(f"\nSignature:\n{signature}")

    # --- Docstring ---
    if docstring:
        parts.append(f"\nDocstring:\n{docstring}")

    # --- Source lines ---
    if include_source and start_line and end_line and file_path:
        source = _read_source_lines(root, file_path, start_line, end_line)
        if source:
            src_lines = source.splitlines()
            if len(src_lines) > max_source_lines:
                src_lines = src_lines[:max_source_lines]
                src_lines.append(
                    f"# ... truncated at {max_source_lines} lines for embedding"
                )
            parts.append("\nSource:\n" + "\n".join(src_lines))

    return "\n".join(parts)


def compute_content_hash(document: str) -> str:
    """Return SHA-256 hex digest of the document text."""
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


def build_documents_from_db(
    codegraph_db: Path,
    root: Path,
    *,
    include_source: bool = True,
    max_source_lines: int = 200,
    node_kinds: tuple[str, ...] | None = None,
    file_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Build documents for all (or filtered) nodes in the CodeGraph DB.

    Returns a list of dicts with keys:
        node_id, node_kind, name, qualified_name, file_path, document,
        content_hash, language, start_line, end_line
    """
    if not codegraph_db.is_file():
        raise DocumentConstructionError(
            f"CodeGraph DB not found: {codegraph_db}"
        )

    conn = sqlite3.connect(f"file://{codegraph_db.resolve()}?mode=ro", uri=True)
    try:
        query = """
            SELECT id, kind, name, qualified_name, file_path, language,
                   start_line, end_line, docstring, signature, visibility,
                   return_type
            FROM nodes
            WHERE 1=1
        """
        params: list[Any] = []
        if node_kinds:
            placeholders = ",".join("?" for _ in node_kinds)
            query += f" AND kind IN ({placeholders})"
            params.extend(node_kinds)
        if file_filter:
            query += " AND file_path LIKE ?"
            params.append(f"%{file_filter}%")

        rows = conn.execute(query, params).fetchall()
        columns = [
            "id", "kind", "name", "qualified_name", "file_path", "language",
            "start_line", "end_line", "docstring", "signature", "visibility",
            "return_type",
        ]
    finally:
        conn.close()

    results: list[dict[str, Any]] = []
    for row in rows:
        node = dict(zip(columns, row))
        if not node.get("name") and not node.get("qualified_name"):
            continue
        doc = build_document(
            node, root,
            include_source=include_source,
            max_source_lines=max_source_lines,
        )
        results.append({
            "node_id": node["id"],
            "node_kind": node["kind"],
            "name": node["name"],
            "qualified_name": node["qualified_name"],
            "file_path": node["file_path"],
            "language": node["language"],
            "start_line": node["start_line"],
            "end_line": node["end_line"],
            "document": doc,
            "content_hash": compute_content_hash(doc),
        })

    return results


def build_document_for_node_id(
    codegraph_db: Path,
    root: Path,
    node_id: str,
    *,
    include_source: bool = True,
    max_source_lines: int = 200,
) -> dict[str, Any] | None:
    """Build a document for a single node by its ID."""
    conn = sqlite3.connect(f"file://{codegraph_db.resolve()}?mode=ro", uri=True)
    try:
        row = conn.execute(
            """SELECT id, kind, name, qualified_name, file_path, language,
                      start_line, end_line, docstring, signature, visibility,
                      return_type
               FROM nodes WHERE id = ?""",
            (node_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    columns = [
        "id", "kind", "name", "qualified_name", "file_path", "language",
        "start_line", "end_line", "docstring", "signature", "visibility",
        "return_type",
    ]
    node = dict(zip(columns, row))
    doc = build_document(
        node, root,
        include_source=include_source,
        max_source_lines=max_source_lines,
    )
    return {
        "node_id": node["id"],
        "node_kind": node["kind"],
        "name": node["name"],
        "qualified_name": node["qualified_name"],
        "file_path": node["file_path"],
        "language": node["language"],
        "start_line": node["start_line"],
        "end_line": node["end_line"],
        "document": doc,
        "content_hash": compute_content_hash(doc),
    }
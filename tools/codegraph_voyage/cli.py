"""CLI entry point for codegraph-voyage.

Usage:
    python -m tools.codegraph_voyage index [options]
    python -m tools.codegraph_voyage search <query> [options]
    python -m tools.codegraph_voyage status [options]
    python -m tools.codegraph_voyage explore <query> [options]

The API key is read from the VOYAGE_API_KEY environment variable only;
no CLI flag accepts a secret value.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Any

from . import __version__
from .document import (
    build_documents_from_db,
    build_document_for_node_id,
    compute_content_hash,
)
from .explore import codegraph_explore
from .providers import (
    EmbeddingProvider,
    FakeEmbeddingProvider,
    VoyageEmbeddingProvider,
    create_provider,
)
from .ranking import (
    RankingResult,
    find_pinned_candidates,
    hybrid_search,
)
from .sanitize import sanitize_content, is_sensitive_path
from .sidecar import SidecarDB, SidecarError

DEFAULT_CODEGRAPH_DIR = ".codegraph"
DEFAULT_SIDECAR_NAME = "codegraph-voyage.db"
DEFAULT_PROVIDER = "fake"
DEFAULT_MODEL = "voyage-code-4"
DEFAULT_DIMENSIONS = 512


def _resolve_project_root(path: str | Path | None = None) -> Path:
    """Resolve project root — the directory containing .codegraph/."""
    start = Path(path or os.getcwd()).resolve()
    # Walk up looking for .codegraph/
    d = start
    while d != d.parent:
        if (d / DEFAULT_CODEGRAPH_DIR).is_dir():
            return d
        d = d.parent
    # If not found, use start
    return start


def _codegraph_db_path(root: Path) -> Path:
    return root / DEFAULT_CODEGRAPH_DIR / "codegraph.db"


def _sidecar_db_path(root: Path) -> Path:
    return root / DEFAULT_CODEGRAPH_DIR / DEFAULT_SIDECAR_NAME


def _make_provider(args: argparse.Namespace) -> EmbeddingProvider:
    """Create an embedding provider from CLI args.

    The API key is read from the VOYAGE_API_KEY environment variable only;
    no CLI flag accepts a secret value.
    """
    api_key = os.environ.get("VOYAGE_API_KEY", "")
    if args.provider == "voyage" and not api_key:
        raise ValueError(
            "VOYAGE_API_KEY is required for voyage provider; "
            "set the VOYAGE_API_KEY environment variable"
        )
    return create_provider(
        args.provider,
        api_key=api_key,
        model=args.model,
        dimensions=args.dimensions,
    )


def _make_provider_or_report(args: argparse.Namespace) -> EmbeddingProvider | None:
    """Build a provider and turn configuration failures into actionable CLI errors."""
    try:
        return _make_provider(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return None


def _sidecar_model_mismatch(
    status: dict[str, Any], provider: EmbeddingProvider
) -> str | None:
    """Return an actionable message when stored vectors are incompatible."""
    groups = status.get("model_groups", [])
    if not groups:
        return None
    if any(
        group[0] == provider.model_name and int(group[1]) == provider.dimensions
        for group in groups
    ):
        return None
    stored = ", ".join(f"{group[0]} dims={group[1]}" for group in groups)
    return (
        f"Sidecar contains {stored}, but selected provider is "
        f"{provider.model_name} dims={provider.dimensions}; pass the matching "
        "--provider/--model/--dimensions options or clear and rebuild the index"
    )


def cmd_index(args: argparse.Namespace) -> int:
    """Build documents from CodeGraph and store embeddings in sidecar."""
    root = _resolve_project_root(args.project)
    cg_db = _codegraph_db_path(root)
    sidecar_db = _sidecar_db_path(root)

    if not cg_db.is_file():
        print(f"Error: CodeGraph DB not found at {cg_db}", file=sys.stderr)
        print("Run `codegraph init` or `codegraph sync` first.", file=sys.stderr)
        return 1

    provider = _make_provider_or_report(args)
    if provider is None:
        return 2
    print(f"Provider: {provider.model_name} (dimensions={provider.dimensions})")

    # Build documents
    print("Building documents from CodeGraph DB...")
    docs = build_documents_from_db(
        cg_db,
        root,
        include_source=not args.no_source,
        max_source_lines=args.max_source_lines,
        node_kinds=tuple(args.kind.split(",")) if args.kind else None,
        file_filter=args.file_filter,
    )
    print(f"  Total documents: {len(docs)}")

    # Sanitization is mandatory before any remote call. There is deliberately
    # no CLI bypass: exclusions are a security boundary, not a tuning option.
    # Hash the exact sanitized payload used for embedding.
    print("Applying path/content sanitization...")
    for doc in docs:
        doc["document"] = sanitize_content(
            doc["document"], doc.get("file_path", "")
        )
        doc["content_hash"] = compute_content_hash(doc["document"])

    # Open sidecar
    sidecar = SidecarDB(sidecar_db)
    sidecar.open()
    try:
        # Find changed nodes
        print("Finding changed nodes for incremental indexing...")
        changed = sidecar.find_changed_nodes(docs, provider)
        print(f"  Changed/new: {len(changed)} / {len(docs)}")

        if not changed:
            print("No changes to index.")
            # Still remove stale records
            current_ids = {d["node_id"] for d in docs}
            removed = sidecar.remove_stale_records(current_ids, provider)
            if removed:
                print(f"  Removed stale records: {removed}")
            status = sidecar.get_status()
            print(f"  Total embeddings: {status.get('total_embeddings', 0)}")
            return 0

        # Generate embeddings
        print(f"Generating embeddings for {len(changed)} documents...")
        texts = [d["document"] for d in changed]
        try:
            embeddings = provider.embed_documents(texts, input_type="document")
        except (RuntimeError, OSError, ValueError) as exc:
            print(f"Embedding failed; sidecar left unchanged: {exc}", file=sys.stderr)
            return 2
        if len(embeddings) != len(changed):
            print(
                "Embedding failed; sidecar left unchanged: provider returned "
                f"{len(embeddings)} vectors for {len(changed)} documents",
                file=sys.stderr,
            )
            return 2
        print(f"  Generated {len(embeddings)} embeddings")

        # Store embeddings
        records = []
        for doc, emb in zip(changed, embeddings):
            records.append({
                "node_id": doc["node_id"],
                "content_hash": doc["content_hash"],
                "embedding": emb,
                "node_kind": doc["node_kind"],
                "name": doc["name"],
                "qualified_name": doc["qualified_name"],
                "file_path": doc["file_path"],
                "language": doc["language"],
                "start_line": doc["start_line"],
                "end_line": doc["end_line"],
                "document_text": doc["document"],
            })

        try:
            stored = sidecar.store_embeddings(records, provider)
        except (SidecarError, ValueError, OSError) as exc:
            print(f"Embedding store failed; sidecar left unchanged: {exc}", file=sys.stderr)
            return 2
        print(f"  Stored embeddings: {stored}")

        # Remove stale records
        current_ids = {d["node_id"] for d in docs}
        removed = sidecar.remove_stale_records(current_ids, provider)
        if removed:
            print(f"  Removed stale records: {removed}")

        status = sidecar.get_status()
        print(f"  Total embeddings: {status.get('total_embeddings', 0)}")
    finally:
        sidecar.close()

    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Hybrid semantic search (semantic_candidates)."""
    root = _resolve_project_root(args.project)
    cg_db = _codegraph_db_path(root)
    sidecar_db = _sidecar_db_path(root)
    query = args.query

    if not cg_db.is_file():
        print(f"Error: CodeGraph DB not found at {cg_db}", file=sys.stderr)
        return 1
    if not sidecar_db.is_file():
        print(
            f"Sidecar DB not found at {sidecar_db}. Run 'index' first.",
            file=sys.stderr,
        )
        return 1

    provider = _make_provider_or_report(args)
    if provider is None:
        return 2

    # Build lexical candidates (all docs)
    if not args.json:
        print(f"Building documents for query: {query}")
    docs = build_documents_from_db(
        cg_db,
        root,
        include_source=not args.no_source,
        max_source_lines=args.max_source_lines,
        node_kinds=tuple(args.kind.split(",")) if args.kind else None,
        file_filter=args.file_filter,
    )

    # Load sidecar embeddings
    sidecar = SidecarDB(sidecar_db)
    sidecar.open()
    try:
        mismatch = _sidecar_model_mismatch(sidecar.get_status(), provider)
        if mismatch:
            print(f"Error: {mismatch}", file=sys.stderr)
            return 2
        emb_candidates = sidecar.get_all_embeddings(provider)
    finally:
        sidecar.close()

    # Match docs with embeddings
    emb_map = {c["node_id"]: c for c in emb_candidates}
    vector_candidates: list[dict[str, Any]] = []
    for d in docs:
        if d["node_id"] in emb_map:
            vector_candidates.append({
                "node_id": d["node_id"],
                "name": d["name"],
                "qualified_name": d["qualified_name"],
                "file_path": d["file_path"],
                "node_kind": d["node_kind"],
                "language": d["language"],
                "start_line": d["start_line"],
                "end_line": d["end_line"],
                "embedding": emb_map[d["node_id"]]["embedding"],
                "document_text": d["document"],
            })

    # Lexical candidates
    lexical_candidates: list[dict[str, Any]] = [
        {
            "node_id": d["node_id"],
            "name": d["name"],
            "qualified_name": d["qualified_name"],
            "file_path": d["file_path"],
            "node_kind": d["node_kind"],
            "language": d["language"],
            "start_line": d["start_line"],
            "end_line": d["end_line"],
            "document_text": d["document"],
        }
        for d in docs
    ]

    # Generate query embedding; network/API failure degrades to lexical-only.
    if not args.json:
        print("Generating query embedding...")
    try:
        query_vector = provider.embed_query(query, input_type="query")
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"Vector lookup unavailable; continuing lexical-only: {exc}", file=sys.stderr)
        query_vector = None

    # Find pinned candidates
    if not args.json:
        print("Identifying pinned candidates...")
    pinned = find_pinned_candidates(
        query, lexical_candidates + vector_candidates
    )
    if not args.json:
        print(f"  Pinned: {len(pinned)}")

    # Hybrid search
    if not args.json:
        print("Running hybrid search (weighted RRF)...")
    results = hybrid_search(
        query,
        query_vector,
        vector_candidates,
        lexical_candidates,
        pinned_candidates=pinned if pinned else None,
        top_k=args.top_k,
        lexical_weight=args.lexical_weight,
        vector_weight=args.vector_weight,
        rrf_k=args.rrf_k,
    )

    # Output
    if args.json:
        output = [r.to_dict() for r in results]
        print(json.dumps(output, indent=2))
    else:
        print(f"\nTop {len(results)} results:\n")
        for i, r in enumerate(results, start=1):
            provenance = r.provenance or "fused"
            print(
                f"  {i:2d}. [{r.node_kind:12s}] {r.name:40s}  "
                f"score={r.score:.4f}  "
                f"{'[PINNED]' if r.is_pinned else ''}  "
                f"provenance={provenance}"
            )
            if r.qualified_name:
                print(f"      Qualified: {r.qualified_name}")
            print(f"      File: {r.file_path}:{r.start_line or ''}")
            print()

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show sidecar status."""
    root = _resolve_project_root(args.project)
    cg_db = _codegraph_db_path(root)
    sidecar_db = _sidecar_db_path(root)

    print(f"Project root: {root}")
    print(f"CodeGraph DB: {cg_db}")
    print(f"Sidecar DB:   {sidecar_db}")

    # CodeGraph status
    if cg_db.is_file():
        import sqlite3
        conn = sqlite3.connect(f"file://{cg_db.resolve()}?mode=ro", uri=True)
        try:
            total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            total_files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            total_edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            print(f"\nCodeGraph:")
            print(f"  Nodes: {total_nodes}")
            print(f"  Files: {total_files}")
            print(f"  Edges: {total_edges}")
        finally:
            conn.close()
    else:
        print(f"\nCodeGraph: NOT FOUND")

    # Sidecar status
    if sidecar_db.is_file():
        sidecar = SidecarDB(sidecar_db)
        sidecar.open()
        try:
            status = sidecar.get_status()
            print(f"\nSidecar:")
            print(f"  Connected: {status.get('connected')}")
            print(f"  Total embeddings: {status.get('total_embeddings', 0)}")
            for group in status.get("model_groups", []):
                print(f"  Group: model={group[0]} dims={group[1]} dtype={group[2]} count={group[3]}")
            print(f"  Schema version: {status.get('schema_version')}")
        finally:
            sidecar.close()
    else:
        print(f"\nSidecar: NOT FOUND (run 'index' first)")

    return 0


def cmd_explore(args: argparse.Namespace) -> int:
    """Integration: hybrid search then codegraph explore with candidates."""
    root = _resolve_project_root(args.project)
    cg_db = _codegraph_db_path(root)
    sidecar_db = _sidecar_db_path(root)
    query = args.query

    if not cg_db.is_file():
        print(f"Error: CodeGraph DB not found at {cg_db}", file=sys.stderr)
        return 1

    provider = _make_provider_or_report(args)
    if provider is None:
        return 2
    sidecar_available = sidecar_db.is_file()

    # Build docs
    docs = build_documents_from_db(
        cg_db, root,
        include_source=not args.no_source,
        max_source_lines=args.max_source_lines,
    )

    lexical_candidates: list[dict[str, Any]] = [
        {
            "node_id": d["node_id"],
            "name": d["name"],
            "qualified_name": d["qualified_name"],
            "file_path": d["file_path"],
            "node_kind": d["node_kind"],
            "language": d["language"],
            "start_line": d["start_line"],
            "end_line": d["end_line"],
            "document_text": d["document"],
        }
        for d in docs
    ]

    # Query embedding
    query_vector = None
    if sidecar_available:
        sidecar = SidecarDB(sidecar_db)
        sidecar.open()
        try:
            mismatch = _sidecar_model_mismatch(sidecar.get_status(), provider)
            if mismatch:
                print(f"Error: {mismatch}", file=sys.stderr)
                return 2
            emb_candidates = sidecar.get_all_embeddings(provider)
            emb_map = {c["node_id"]: c for c in emb_candidates}
            vector_candidates = [
                {**d, "embedding": emb_map[d["node_id"]]["embedding"]}
                for d in docs if d["node_id"] in emb_map
            ]
            try:
                query_vector = provider.embed_query(query, input_type="query")
            except (RuntimeError, OSError, ValueError) as exc:
                print(f"Vector lookup unavailable; continuing lexical-only: {exc}", file=sys.stderr)
                query_vector = None
        finally:
            sidecar.close()
    else:
        vector_candidates = []

    # Pinned
    pinned = find_pinned_candidates(query, lexical_candidates + vector_candidates)

    # Hybrid search
    results = hybrid_search(
        query,
        query_vector,
        vector_candidates,
        lexical_candidates,
        pinned_candidates=pinned if pinned else None,
        top_k=args.top_k,
        lexical_weight=args.lexical_weight,
        vector_weight=args.vector_weight,
        rrf_k=args.rrf_k,
    )

    if args.dry_run:
        from .explore import build_explore_query
        q = build_explore_query(results, max_symbols=20)
        print(f"Explore query ({len(results)} candidates → {len(q.split())} symbols):")
        print(f"  {q}")
        return 0

    # Run codegraph explore
    result = codegraph_explore(
        results,
        project_path=root,
        max_files=args.max_files,
        codegraph_bin=args.codegraph_bin,
        timeout=args.timeout,
    )

    if result.get("error"):
        print(f"codegraph explore error: {result['error']}", file=sys.stderr)
        return 1

    print(result.get("stdout", ""))
    if result.get("stderr"):
        print(result["stderr"], file=sys.stderr)

    return result.get("returncode", 0)


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="codegraph-voyage: hybrid semantic retrieval sidecar for CodeGraph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Index with fake provider (no API key needed)
              python -m tools.codegraph_voyage index

              # Index with voyage-code-4
              VOYAGE_API_KEY=... python -m tools.codegraph_voyage index --provider voyage

              # Search (hybrid lexical + vector)
              python -m tools.codegraph_voyage search "AuthService" --top-k 10

              # Explore with semantic candidates
              python -m tools.codegraph_voyage explore "UserManager" --max-files 8

              # Status
              python -m tools.codegraph_voyage status
        """),
    )
    ap.add_argument("--version", action="version", version=f"codegraph-voyage {__version__}")

    # Common options
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-p", "--project",
        default=None,
        help="Project root path (default: current dir, walks up for .codegraph/)",
    )
    common.add_argument(
        "--provider",
        default=DEFAULT_PROVIDER,
        choices=["fake", "voyage"],
        help=f"Embedding provider (default: {DEFAULT_PROVIDER})",
    )
    common.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Embedding model name (default: {DEFAULT_MODEL})",
    )
    common.add_argument(
        "--dimensions",
        type=int,
        default=DEFAULT_DIMENSIONS,
        help=f"Embedding dimensions (default: {DEFAULT_DIMENSIONS})",
    )

    sub = ap.add_subparsers(dest="command", required=True)

    # index
    p_index = sub.add_parser("index", help="Build documents and store embeddings", parents=[common])
    p_index.add_argument(
        "--no-source", action="store_true",
        help="Exclude source lines from documents",
    )
    p_index.add_argument(
        "--max-source-lines", type=int, default=200,
        help="Max source lines per document (default: 200)",
    )
    p_index.add_argument(
        "--kind", default=None,
        help="Comma-separated node kinds to index (e.g. 'function,class')",
    )
    p_index.add_argument(
        "--file-filter", default=None,
        help="Optional file path filter (SQL LIKE pattern)",
    )
    p_index.set_defaults(func=cmd_index)

    # search
    p_search = sub.add_parser("search", aliases=["semantic_candidates"],
                              help="Hybrid semantic search", parents=[common])
    p_search.add_argument("query", help="Search query")
    p_search.add_argument(
        "--top-k", type=int, default=20,
        help="Max results (default: 20)",
    )
    p_search.add_argument(
        "--json", action="store_true",
        help="Output as JSON",
    )
    p_search.add_argument(
        "--no-source", action="store_true",
    )
    p_search.add_argument(
        "--max-source-lines", type=int, default=200,
    )
    p_search.add_argument(
        "--kind", default=None,
        help="Comma-separated node kinds to filter",
    )
    p_search.add_argument(
        "--file-filter", default=None,
    )
    p_search.add_argument(
        "--lexical-weight", type=float, default=0.5,
        help="Weight for lexical RRF contribution (default: 0.5)",
    )
    p_search.add_argument(
        "--vector-weight", type=float, default=0.5,
        help="Weight for vector RRF contribution (default: 0.5)",
    )
    p_search.add_argument(
        "--rrf-k", type=int, default=60,
        help="RRF constant k (default: 60)",
    )
    p_search.set_defaults(func=cmd_search)

    # status
    p_status = sub.add_parser("status", help="Show sidecar status", parents=[common])
    p_status.set_defaults(func=cmd_status)

    # explore
    p_explore = sub.add_parser("explore",
                               help="Hybrid search + codegraph explore",
                               parents=[common])
    p_explore.add_argument("query", help="Search query")
    p_explore.add_argument(
        "--top-k", type=int, default=15,
        help="Max candidates to pass to explore (default: 15)",
    )
    p_explore.add_argument(
        "--max-files", type=int, default=12,
        help="Max files for codegraph explore (default: 12)",
    )
    p_explore.add_argument(
        "--codegraph-bin", default="codegraph",
        help="Path to codegraph binary (default: codegraph)",
    )
    p_explore.add_argument(
        "--timeout", type=int, default=60,
        help="Timeout for codegraph explore (default: 60s)",
    )
    p_explore.add_argument(
        "--dry-run", action="store_true",
        help="Show the explore query without running it",
    )
    p_explore.add_argument(
        "--no-source", action="store_true",
    )
    p_explore.add_argument(
        "--max-source-lines", type=int, default=200,
    )
    p_explore.add_argument(
        "--lexical-weight", type=float, default=0.5,
    )
    p_explore.add_argument(
        "--vector-weight", type=float, default=0.5,
    )
    p_explore.add_argument(
        "--rrf-k", type=int, default=60,
    )
    p_explore.set_defaults(func=cmd_explore)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = _build_parser()
    args = ap.parse_args(argv)
    if hasattr(args, "func"):
        return args.func(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
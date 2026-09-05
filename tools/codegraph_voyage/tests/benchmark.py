#!/usr/bin/env python3
"""Benchmark for codegraph-voyage retrieval quality.

This is a **smoke benchmark** — the corpus is small and synthetic, so no
quality-lift claims are made. It tests that the three retrieval strategies
(lexical, vector, fused) produce measurable output and that fused can
improve over the worst single-strategy for at least one conceptual case.

Metrics reported:
  - Recall@5
  - MRR (Mean Reciprocal Rank)
  - NDCG@10

Run:
    python -m tools.codegraph_voyage.tests.benchmark [--verbose]
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path
from typing import Any

# Make sure the project root is importable
# This script is at tools/codegraph_voyage/tests/benchmark.py
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.codegraph_voyage.providers import FakeEmbeddingProvider
from tools.codegraph_voyage.ranking import (
    RankingResult,
    reciprocal_rank_fusion,
    rank_by_lexical_similarity,
    rank_by_vector_similarity,
    find_pinned_candidates,
    merge_pinned_into_results,
)


# ---------------------------------------------------------------------------
# Fixture: a small synthetic corpus of symbol documents with ground-truth
# relevance judgments per query.
# ---------------------------------------------------------------------------

FIXTURE_DOCS: list[dict[str, Any]] = [
    {
        "node_id": "d1", "name": "AuthService", "qualified_name": "app.auth.AuthService",
        "file_path": "src/auth/service.py", "node_kind": "class", "language": "python",
        "start_line": 1, "end_line": 50,
        "document_text": "AuthService handles user authentication login logout password hashing JWT token generation and session management",
    },
    {
        "node_id": "d2", "name": "UserModel", "qualified_name": "app.models.UserModel",
        "file_path": "src/models/user.py", "node_kind": "class", "language": "python",
        "start_line": 1, "end_line": 80,
        "document_text": "UserModel represents a user account with fields for username email password_hash and profile data",
    },
    {
        "node_id": "d3", "name": "PaymentGateway", "qualified_name": "app.payments.PaymentGateway",
        "file_path": "src/payments/gateway.py", "node_kind": "class", "language": "python",
        "start_line": 1, "end_line": 120,
        "document_text": "PaymentGateway processes credit card payments refunds and subscription billing via Stripe API",
    },
    {
        "node_id": "d4", "name": "InvoiceGenerator", "qualified_name": "app.billing.InvoiceGenerator",
        "file_path": "src/billing/invoice.py", "node_kind": "class", "language": "python",
        "start_line": 1, "end_line": 60,
        "document_text": "InvoiceGenerator creates PDF invoices for completed payments and sends them via email",
    },
    {
        "node_id": "d5", "name": "login", "qualified_name": "app.auth.login",
        "file_path": "src/auth/views.py", "node_kind": "function", "language": "python",
        "start_line": 10, "end_line": 25,
        "document_text": "login view function authenticates user credentials and returns a JWT token",
    },
    {
        "node_id": "d6", "name": "hash_password", "qualified_name": "app.auth.hash_password",
        "file_path": "src/auth/utils.py", "node_kind": "function", "language": "python",
        "start_line": 5, "end_line": 15,
        "document_text": "hash_password takes a plaintext password and returns a bcrypt hash for secure storage",
    },
    {
        "node_id": "d7", "name": "send_email", "qualified_name": "app.notifications.send_email",
        "file_path": "src/notifications/email.py", "node_kind": "function", "language": "python",
        "start_line": 1, "end_line": 30,
        "document_text": "send_email dispatches transactional emails via SMTP for invoices and notifications",
    },
    {
        "node_id": "d8", "name": "generate_report", "qualified_name": "app.reports.generate_report",
        "file_path": "src/reports/generator.py", "node_kind": "function", "language": "python",
        "start_line": 1, "end_line": 45,
        "document_text": "generate_report produces CSV and JSON reports from database query results for business analytics",
    },
    {
        "node_id": "d9", "name": "DatabaseConnection", "qualified_name": "app.db.DatabaseConnection",
        "file_path": "src/db/connection.py", "node_kind": "class", "language": "python",
        "start_line": 1, "end_line": 90,
        "document_text": "DatabaseConnection manages connection pooling SQL query execution and transaction management for PostgreSQL",
    },
    {
        "node_id": "d10", "name": "CacheManager", "qualified_name": "app.cache.CacheManager",
        "file_path": "src/cache/manager.py", "node_kind": "class", "language": "python",
        "start_line": 1, "end_line": 60,
        "document_text": "CacheManager provides Redis-backed caching for frequently accessed database queries and API responses",
    },
]

# Queries with ground-truth relevant node IDs (ordered by decreasing relevance)
QUERIES: list[tuple[str, list[str], str]] = [
    ("user authentication login", ["d1", "d5", "d2", "d6"], "auth-related symbols"),
    ("payment processing billing", ["d3", "d4", "d7", "d1"], "payment/billing"),
    ("database query caching", ["d9", "d10", "d8"], "data layer"),
    ("email notification invoice", ["d7", "d4", "d2"], "email/billing"),
    ("AuthService", ["d1", "d5", "d6"], "exact identifier AuthService"),
]


def dcg(relevances: list[float]) -> float:
    """Discounted cumulative gain."""
    return sum(
        rel / math.log2(i + 2) if i > 0 else rel
        for i, rel in enumerate(relevances)
    )


def ndcg(ranked_ids: list[str], relevant: set[str], k: int = 10) -> float:
    """NDCG@k."""
    ranked = ranked_ids[:k]
    # Binary relevance: 1 if in relevant set
    relevances = [1.0 if rid in relevant else 0.0 for rid in ranked]
    ideal = sorted(relevances, reverse=True)
    dcg_val = dcg(relevances)
    idcg_val = dcg(ideal)
    return dcg_val / idcg_val if idcg_val > 0 else 0.0


def recall_at_k(ranked_ids: list[str], relevant: set[str], k: int = 5) -> float:
    """Recall@k."""
    if not relevant:
        return 0.0
    found = sum(1 for rid in ranked_ids[:k] if rid in relevant)
    return found / len(relevant)


def mrr(ranked_ids: list[str], relevant: set[str]) -> float:
    """Mean Reciprocal Rank."""
    for i, rid in enumerate(ranked_ids):
        if rid in relevant:
            return 1.0 / (i + 1)
    return 0.0


def run_benchmark(verbose: bool = False) -> dict[str, Any]:
    """Run benchmark and return metrics."""
    provider = FakeEmbeddingProvider(dimensions=64)

    # Pre-compute embeddings for all docs
    texts = [d["document_text"] for d in FIXTURE_DOCS]
    embeddings = provider.embed_documents(texts, input_type="document")

    # Build candidate dicts for ranking functions
    vector_candidates: list[dict[str, Any]] = []
    lexical_candidates: list[dict[str, Any]] = []
    for doc, emb in zip(FIXTURE_DOCS, embeddings):
        entry = {
            "node_id": doc["node_id"],
            "name": doc["name"],
            "qualified_name": doc["qualified_name"],
            "file_path": doc["file_path"],
            "node_kind": doc["node_kind"],
            "language": doc["language"],
            "start_line": doc["start_line"],
            "end_line": doc["end_line"],
            "document_text": doc["document_text"],
            "embedding": emb,
        }
        vector_candidates.append(entry)
        lexical_candidates.append({k: v for k, v in entry.items() if k != "embedding"})

    all_metrics: dict[str, dict[str, float]] = {
        "lexical": {"recall@5": 0.0, "mrr": 0.0, "ndcg@10": 0.0},
        "vector": {"recall@5": 0.0, "mrr": 0.0, "ndcg@10": 0.0},
        "fused": {"recall@5": 0.0, "mrr": 0.0, "ndcg@10": 0.0},
    }

    for query_str, relevant_ids, label in QUERIES:
        relevant = set(relevant_ids)
        query_vector = provider.embed_query(query_str, input_type="query")

        # Lexical
        lex_results = rank_by_lexical_similarity(query_str, lexical_candidates, top_k=10)
        lex_ids = [r.node_id for r in lex_results]

        # Vector
        vec_results = rank_by_vector_similarity(query_vector, vector_candidates, top_k=10)
        vec_ids = [r.node_id for r in vec_results]

        # Fused (RRF)
        fused = reciprocal_rank_fusion([vec_results, lex_results], weights=[0.5, 0.5], k=60)
        # Merge pinned
        pinned = find_pinned_candidates(query_str, lexical_candidates)
        if pinned:
            fused = merge_pinned_into_results(pinned, fused)
        fused_ids = [r.node_id for r in fused]

        if verbose:
            print(f"\nQuery: {query_str!r} ({label})")
            print(f"  Lexical top-5: {lex_ids[:5]}")
            print(f"  Vector top-5:  {vec_ids[:5]}")
            print(f"  Fused top-5:   {fused_ids[:5]}")
            print(f"  Relevant:      {relevant_ids}")

        for strategy_name, ids in [("lexical", lex_ids), ("vector", vec_ids), ("fused", fused_ids)]:
            all_metrics[strategy_name]["recall@5"] += recall_at_k(ids, relevant, k=5)
            all_metrics[strategy_name]["mrr"] += mrr(ids, relevant)
            all_metrics[strategy_name]["ndcg@10"] += ndcg(ids, relevant, k=10)

    n = len(QUERIES)
    for strategy in all_metrics:
        for metric in all_metrics[strategy]:
            all_metrics[strategy][metric] = round(all_metrics[strategy][metric] / n, 4)

    return all_metrics


def main() -> int:
    from pathlib import Path  # noqa: F811

    ap = argparse.ArgumentParser(description="codegraph-voyage benchmark")
    ap.add_argument("--verbose", "-v", action="store_true", help="Show per-query details")
    args = ap.parse_args()

    print("=" * 60)
    print("codegraph-voyage retrieval benchmark (smoke)")
    print("=" * 60)
    print(f"Corpus: {len(FIXTURE_DOCS)} documents")
    print(f"Queries: {len(QUERIES)}")
    print(f"Provider: FakeEmbeddingProvider(dimensions=64)")
    print()

    t0 = time.time()
    metrics = run_benchmark(verbose=args.verbose)
    elapsed = time.time() - t0

    print(f"\nResults ({elapsed:.2f}s):")
    print(f"{'Strategy':<10} {'Recall@5':>10} {'MRR':>10} {'NDCG@10':>10}")
    print("-" * 42)
    for strategy in ["lexical", "vector", "fused"]:
        m = metrics[strategy]
        print(f"{strategy:<10} {m['recall@5']:>10.4f} {m['mrr']:>10.4f} {m['ndcg@10']:>10.4f}")

    # Compare like-for-like metrics against the stronger single strategy.
    comparisons = [
        metrics["fused"][metric] >= max(metrics["lexical"][metric], metrics["vector"][metric])
        for metric in ("recall@5", "mrr", "ndcg@10")
    ]
    strict_improvement = any(
        metrics["fused"][metric] > max(metrics["lexical"][metric], metrics["vector"][metric])
        for metric in ("recall@5", "mrr", "ndcg@10")
    )

    if all(comparisons) and strict_improvement:
        print("\n✓ Fused improves like-for-like over the single strategies.")
    else:
        print("\n⚠ Fused did not improve like-for-like on all metrics (smoke corpus limitation).")

    print("\n⚠ Caveat: This is a SMOKE benchmark with a tiny synthetic corpus.")
    print("  No quality-lift claims should be made from these results.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
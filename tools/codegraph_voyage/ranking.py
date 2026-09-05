"""Ranking: weighted reciprocal-rank fusion (RRF) with pinned candidates.

Pinned candidates (exact path matches, exact identifier matches) are always
included and never displaced by vector or lexical ranking.
"""

from __future__ import annotations

import math
import re
from typing import Any


class RankingResult:
    """A single ranked result with provenance tracking."""

    def __init__(
        self,
        node_id: str,
        score: float = 0.0,
        *,
        is_pinned: bool = False,
        lexical_score: float | None = None,
        vector_score: float | None = None,
        exact_score: float | None = None,
        path_score: float | None = None,
        name: str = "",
        qualified_name: str = "",
        file_path: str = "",
        node_kind: str = "",
        language: str = "",
        start_line: int | None = None,
        end_line: int | None = None,
        provenance: str | None = None,
    ):
        self.node_id = node_id
        self.score = score
        self.is_pinned = is_pinned
        self.lexical_score = lexical_score
        self.vector_score = vector_score
        self.exact_score = exact_score
        self.path_score = path_score
        self.name = name
        self.qualified_name = qualified_name
        self.file_path = file_path
        self.node_kind = node_kind
        self.language = language
        self.start_line = start_line
        self.end_line = end_line
        self.provenance = provenance or ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict for JSON output."""
        return {
            "node_id": self.node_id,
            "score": round(self.score, 6),
            "is_pinned": self.is_pinned,
            "lexical_score": round(self.lexical_score, 6) if self.lexical_score is not None else None,
            "vector_score": round(self.vector_score, 6) if self.vector_score is not None else None,
            "exact_score": round(self.exact_score, 6) if self.exact_score is not None else None,
            "path_score": round(self.path_score, 6) if self.path_score is not None else None,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file_path": self.file_path,
            "node_kind": self.node_kind,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "provenance": self.provenance,
        }


def reciprocal_rank_fusion(
    ranked_lists: list[list[RankingResult]],
    *,
    weights: list[float] | None = None,
    k: int = 60,
) -> list[RankingResult]:
    """Combine multiple ranked lists using weighted reciprocal-rank fusion.

    Each list contributes its own RRF score per item:
        rrf_score(item, list_i) = weight_i / (k + rank_i(item))

    where rank_i is 1-based position in list_i. Items not present in a list
    get 0 from that list.

    Args:
        ranked_lists: List of ranked result lists (each list is of RankingResult).
        weights: Per-list weight. If None, equal weight (1/N).
        k: RRF constant (default 60, the standard value).

    Returns:
        A single ranked list, sorted by fused score descending.
    """
    n = len(ranked_lists)
    if n == 0:
        return []

    if weights is None:
        weights = [1.0 / n] * n
    else:
        # Normalize weights
        total = sum(abs(w) for w in weights)
        if total > 0:
            weights = [w / total for w in weights]
        else:
            weights = [1.0 / n] * n

    # Accumulate fused scores
    fused_map: dict[str, tuple[RankingResult, float]] = {}

    for lst_idx, lst in enumerate(ranked_lists):
        w = weights[lst_idx]
        for rank, item in enumerate(lst, start=1):
            node_id = item.node_id
            rrf = w / (k + rank)
            if node_id in fused_map:
                existing, score = fused_map[node_id]
                # Merge provenance
                existing.provenance = _merge_provenance(existing.provenance, item.provenance)
                existing.score = score + rrf
                # Track sub-scores
                if item.lexical_score is not None:
                    existing.lexical_score = (existing.lexical_score or 0) + item.lexical_score
                if item.vector_score is not None:
                    existing.vector_score = (existing.vector_score or 0) + item.vector_score
                if item.exact_score is not None:
                    existing.exact_score = (existing.exact_score or 0) + item.exact_score
                if item.path_score is not None:
                    existing.path_score = (existing.path_score or 0) + item.path_score
                if item.is_pinned:
                    existing.is_pinned = True
                fused_map[node_id] = (existing, existing.score)
            else:
                item.score = rrf
                fused_map[node_id] = (item, rrf)

    # Sort by fused score descending
    results = sorted(fused_map.values(), key=lambda x: -x[1])
    return [r for r, _ in results]


def _merge_provenance(p1: str, p2: str) -> str:
    """Merge two provenance strings with dedup."""
    parts = set()
    if p1:
        parts.update(p1.split("+"))
    if p2:
        parts.update(p2.split("+"))
    # Filter empty
    parts = {p.strip() for p in parts if p.strip()}
    if not parts:
        return ""
    return "+".join(sorted(parts))


def find_pinned_candidates(
    query: str,
    candidates: list[dict[str, Any]],
) -> list[RankingResult]:
    """Find exactly matching identifiers and paths; return as pinned candidates.

    Pinned candidates match the query as an exact identifier:
      - query matches name exactly (case-insensitive)
      - query matches qualified_name exactly (case-insensitive)
      - query matches file_path exactly (case-insensitive)
      - query matches the file_path basename exactly (case-insensitive)

    These are always included in the final result set and never displaced.
    """
    query_lower = query.lower().strip()
    if not query_lower:
        return []
    pinned: list[RankingResult] = []
    seen_ids: set[str] = set()

    for c in candidates:
        node_id = c.get("node_id", "")
        if not node_id or node_id in seen_ids:
            continue
        name = (c.get("name") or "").lower()
        qname = (c.get("qualified_name") or "").lower()
        fpath = (c.get("file_path") or "").replace("\\", "/").lower()
        basename = fpath.rsplit("/", 1)[-1]
        score = 0.0
        provenance_parts: list[str] = []

        # Exact name match
        if name == query_lower:
            score += 10.0
            provenance_parts.append("exact_name")

        # Exact qualified name match
        if qname == query_lower:
            score += 10.0
            provenance_parts.append("exact_qname")

        if fpath == query_lower:
            score += 5.0
            provenance_parts.append("exact_path")

        if basename == query_lower:
            score += 5.0
            provenance_parts.append("exact_basename")

        if score > 0:
            seen_ids.add(node_id)
            pinned.append(
                RankingResult(
                    node_id=node_id,
                    score=score,
                    is_pinned=True,
                    exact_score=score,
                    name=c.get("name", ""),
                    qualified_name=c.get("qualified_name", ""),
                    file_path=c.get("file_path", ""),
                    node_kind=c.get("node_kind", ""),
                    language=c.get("language", ""),
                    start_line=c.get("start_line"),
                    end_line=c.get("end_line"),
                    provenance="+".join(provenance_parts),
                )
            )

    return pinned


def merge_pinned_into_results(
    pinned: list[RankingResult],
    fused: list[RankingResult],
) -> list[RankingResult]:
    """Merge pinned candidates into the fused result list.

    Pinned items are placed at the top (sorted by their exact_score within
    the pinned group), and duplicates are removed from the fused list.
    """
    fused_by_id = {r.node_id: r for r in fused}
    for item in pinned:
        fused_item = fused_by_id.get(item.node_id)
        if fused_item is None:
            continue
        item.provenance = _merge_provenance(item.provenance, fused_item.provenance)
        item.lexical_score = fused_item.lexical_score
        item.vector_score = fused_item.vector_score
        item.path_score = fused_item.path_score if item.path_score is None else item.path_score
        item.score += fused_item.score
        for attr in ("name", "qualified_name", "file_path", "node_kind", "language"):
            if not getattr(item, attr):
                setattr(item, attr, getattr(fused_item, attr))
        if item.start_line is None:
            item.start_line = fused_item.start_line
        if item.end_line is None:
            item.end_line = fused_item.end_line
    pinned_ids = {p.node_id for p in pinned}
    # Deduplicate fused list
    fused_deduped = [r for r in fused if r.node_id not in pinned_ids]
    # Sort pinned by their exact score descending
    pinned_sorted = sorted(pinned, key=lambda p: -(p.exact_score or 0))
    return pinned_sorted + fused_deduped


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_by_vector_similarity(
    query_vector: list[float],
    candidates: list[dict[str, Any]],
    *,
    top_k: int = 30,
) -> list[RankingResult]:
    """Rank candidates by cosine similarity to the query vector.

    Args:
        query_vector: The query embedding vector.
        candidates: List of dicts with 'node_id', 'embedding', etc.
        top_k: Max results to return.

    Returns:
        Ranked list of RankingResult with vector_score populated.
    """
    scored: list[tuple[float, dict[str, Any]]] = []
    for c in candidates:
        emb = c.get("embedding")
        if emb is None:
            continue
        sim = cosine_similarity(query_vector, emb)
        scored.append((sim, c))

    scored.sort(key=lambda x: -x[0])

    results: list[RankingResult] = []
    for sim, c in scored[:top_k]:
        results.append(
            RankingResult(
                node_id=c.get("node_id", ""),
                score=sim,
                vector_score=sim,
                name=c.get("name", ""),
                qualified_name=c.get("qualified_name", ""),
                file_path=c.get("file_path", ""),
                node_kind=c.get("node_kind", ""),
                language=c.get("language", ""),
                start_line=c.get("start_line"),
                end_line=c.get("end_line"),
                provenance="vector",
            )
        )
    return results


def rank_by_lexical_similarity(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    top_k: int = 30,
) -> list[RankingResult]:
    """Rank candidates by lexical (BM25-like) text overlap with the query.

    Uses a simple TF-IDF-like scoring on the document text for a lightweight
    lexical ranking without external dependencies.
    """
    query_lower = query.lower().strip()
    query_terms = re.findall(r"[a-zA-Z0-9_]+", query_lower)
    if not query_terms:
        # Fall back to per-char matching
        query_terms = [query_lower]

    scored: list[tuple[float, dict[str, Any]]] = []
    for c in candidates:
        doc_text = (c.get("document_text") or "").lower()
        if not doc_text:
            scored.append((0.0, c))
            continue

        score = 0.0
        for term in query_terms:
            # Count occurrences
            count = doc_text.count(term)
            if count > 0:
                # Simple TF: log(1 + count)
                tf = math.log(1.0 + count)
                # IDF-like: fewer terms in the query = higher weight
                idf = math.log(1.0 + len(query_terms) / len(set(query_terms)))
                score += tf * idf

        # Bonus for term in name or qualified_name
        name = (c.get("name") or "").lower()
        qname = (c.get("qualified_name") or "").lower()
        for term in query_terms:
            if term in name:
                score += 2.0
            if term in qname:
                score += 1.0

        scored.append((score, c))

    scored.sort(key=lambda x: -x[0])

    results: list[RankingResult] = []
    for score, c in scored[:top_k]:
        results.append(
            RankingResult(
                node_id=c.get("node_id", ""),
                score=score,
                lexical_score=score,
                name=c.get("name", ""),
                qualified_name=c.get("qualified_name", ""),
                file_path=c.get("file_path", ""),
                node_kind=c.get("node_kind", ""),
                language=c.get("language", ""),
                start_line=c.get("start_line"),
                end_line=c.get("end_line"),
                provenance="lexical",
            )
        )
    return results


def hybrid_search(
    query: str,
    query_vector: list[float] | None,
    vector_candidates: list[dict[str, Any]],
    lexical_candidates: list[dict[str, Any]],
    pinned_candidates: list[RankingResult] | None = None,
    *,
    top_k: int = 20,
    lexical_weight: float = 0.5,
    vector_weight: float = 0.5,
    rrf_k: int = 60,
) -> list[RankingResult]:
    """Perform hybrid search with weighted RRF and pinned candidate merging.

    Args:
        query: The search query string.
        query_vector: Query embedding vector (None for vector-only search).
        vector_candidates: Full list of candidates with embeddings.
        lexical_candidates: Full list of candidates for lexical scoring.
        pinned_candidates: Pre-computed pinned candidates (or None to compute).
        top_k: Max final results.
        lexical_weight: RRF weight for lexical rank list.
        vector_weight: RRF weight for vector rank list.
        rrf_k: RRF constant.

    Returns:
        Ranked list of RankingResult.
    """
    # Compute pinned if not provided
    if pinned_candidates is None:
        pinned_candidates = find_pinned_candidates(query, lexical_candidates)

    # Build ranked lists
    ranked_lists: list[list[RankingResult]] = []
    weights: list[float] = []

    if query_vector is not None:
        vec_results = rank_by_vector_similarity(
            query_vector, vector_candidates, top_k=top_k * 2
        )
        if vec_results:
            ranked_lists.append(vec_results)
            weights.append(vector_weight)

    lex_results = rank_by_lexical_similarity(
        query, lexical_candidates, top_k=top_k * 2
    )
    if lex_results:
        ranked_lists.append(lex_results)
        weights.append(lexical_weight)

    # Fuse
    if ranked_lists:
        fused = reciprocal_rank_fusion(ranked_lists, weights=weights, k=rrf_k)
    else:
        fused = []

    # Merge pinned
    final_results = merge_pinned_into_results(pinned_candidates, fused)

    return final_results[:top_k]
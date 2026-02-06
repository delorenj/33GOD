"""Qdrant vector store for per-project mutation embeddings."""

import hashlib
import re
from typing import Any

import structlog
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from .config import settings
from .models import EnrichedMutation

logger = structlog.get_logger(__name__)

# Singleton embedding model (loads once, reuses)
_embedding_model: TextEmbedding | None = None


def get_embedding_model() -> TextEmbedding:
    """Lazy-init the fastembed model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("loading_embedding_model", model=settings.embedding_model)
        _embedding_model = TextEmbedding(model_name=settings.embedding_model)
        logger.info("embedding_model_loaded")
    return _embedding_model


def collection_name_for_repo(git_root: str, remote_url: str | None) -> str:
    """Derive a stable Qdrant collection name from the repo identity.

    Uses remote_url if available (portable across machines), falls back to
    git_root path. Collection name format: mutations-{short_hash}
    """
    # Prefer remote URL for portability
    identity = remote_url or git_root
    # Normalize: strip .git suffix, trailing slashes
    identity = re.sub(r"\.git/?$", "", identity).rstrip("/")

    # Extract a human-readable suffix from the repo name
    repo_name = identity.rstrip("/").split("/")[-1]
    repo_name = re.sub(r"[^a-zA-Z0-9_-]", "_", repo_name).lower()

    # Short hash for uniqueness
    short_hash = hashlib.sha256(identity.encode()).hexdigest()[:8]

    return f"{settings.qdrant_collection_prefix}-{repo_name}-{short_hash}"


class MutationVectorStore:
    """Manages Qdrant collections for mutation embeddings."""

    def __init__(self) -> None:
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=10,
        )
        self._ensured_collections: set[str] = set()

    async def ensure_collection(self, name: str) -> None:
        """Create collection if it doesn't exist (idempotent)."""
        if name in self._ensured_collections:
            return

        collections = self.client.get_collections().collections
        exists = any(c.name == name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("collection_created", collection=name)

        self._ensured_collections.add(name)

    async def store(self, enriched: EnrichedMutation) -> None:
        """Embed and store an enriched mutation in the appropriate collection."""
        event = enriched.event
        collection = collection_name_for_repo(
            event.repo.git_root, event.repo.remote_url
        )

        await self.ensure_collection(collection)

        # Generate embedding from semantic summary
        model = get_embedding_model()
        embeddings = list(model.embed([enriched.summary]))
        vector = embeddings[0].tolist()

        # Build point with full payload for filtered retrieval
        point_id = hashlib.md5(
            f"{event.correlation_id}:{event.timestamp.isoformat()}".encode()
        ).hexdigest()

        payload: dict[str, Any] = {
            "event_type": event.event_type,
            "hook_type": event.hook_type,
            "tool_name": event.tool_name,
            "agent_id": event.agent_id,
            "file_path": event.file_path,
            "file_ext": event.file_ext,
            "lines_changed": event.lines_changed,
            "branch": event.repo.branch,
            "head_sha": event.repo.head_sha,
            "git_root": event.repo.git_root,
            "correlation_id": event.correlation_id,
            "timestamp": event.timestamp.isoformat(),
            "source_pid": event.source_pid,
            # Enrichment fields
            "intent": enriched.intent,
            "domain": enriched.domain,
            "language": enriched.language,
            "summary": enriched.summary,
        }

        self.client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

        logger.info(
            "mutation_embedded",
            collection=collection,
            intent=enriched.intent,
            file=event.file_path,
            summary=enriched.summary[:100],
        )

    def search(
        self,
        collection: str,
        query: str,
        limit: int = 10,
        branch: str | None = None,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over mutations in a collection."""
        model = get_embedding_model()
        query_vector = list(model.embed([query]))[0].tolist()

        # Build optional filters
        conditions = []
        if branch:
            conditions.append(
                FieldCondition(key="branch", match=MatchValue(value=branch))
            )
        if agent_id:
            conditions.append(
                FieldCondition(key="agent_id", match=MatchValue(value=agent_id))
            )

        query_filter = Filter(must=conditions) if conditions else None

        results = self.client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )

        return [
            {
                "score": point.score,
                **point.payload,
            }
            for point in results.points
        ]

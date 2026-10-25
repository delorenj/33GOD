-- Semantic Search Support
-- This requires the pgvector extension (provided by pgvector/pgvector:pg16 image).
CREATE EXTENSION IF NOT EXISTS vector;

-- We use a sidecar table rather than adding the column directly to `events`
-- to avoid bloating the primary audit trail table. Not all events (e.g. 
-- simple system ticks) will require embeddings.
CREATE TABLE IF NOT EXISTS event_embeddings (
    event_id uuid PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    -- 384 dimensions optimized for local models like bge-small-en-v1.5 or nomic-embed-text
    embedding vector(384) NOT NULL
);

-- HNSW (Hierarchical Navigable Small World) index for fast approximate nearest neighbor search
-- We use vector_cosine_ops for cosine distance, standard for embedding similarity.
CREATE INDEX IF NOT EXISTS idx_event_embeddings_hnsw 
ON event_embeddings USING hnsw (embedding vector_cosine_ops);

"""Sidecar SQLite database for embedding storage.

The sidecar stores embeddings keyed by node identity, source content hash,
model, dimensions, and dtype. It supports incremental indexing (skip unchanged
records, remove stale records) and segregated indices for incompatible metadata.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from .providers import EmbeddingProvider

SCHEMA_VERSION = 2

SIDECAR_SCHEMA = """
CREATE TABLE IF NOT EXISTS sidecar_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embeddings (
    node_id TEXT NOT NULL,
    source_content_hash TEXT NOT NULL,
    model TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    dtype TEXT NOT NULL DEFAULT 'float32',
    embedding BLOB NOT NULL,
    node_kind TEXT,
    name TEXT,
    qualified_name TEXT,
    file_path TEXT,
    language TEXT,
    start_line INTEGER,
    end_line INTEGER,
    document_text TEXT,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (node_id, source_content_hash, model, dimensions, dtype)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_file_path
    ON embeddings(file_path);
CREATE INDEX IF NOT EXISTS idx_embeddings_name
    ON embeddings(name);
CREATE INDEX IF NOT EXISTS idx_embeddings_content_hash
    ON embeddings(source_content_hash);
"""


class SidecarError(Exception):
    """Raised on sidecar DB operations."""


class SidecarDB:
    """Manages the sidecar SQLite database for embedding storage.

    The sidecar is read/write. The CodeGraph DB is always opened read-only.
    """

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        """Open (or create) the sidecar database and apply schema."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._migrate_legacy_primary_key()
        self._conn.executescript(SIDECAR_SCHEMA)
        # Track schema version
        cur = self._conn.execute(
            "SELECT value FROM sidecar_meta WHERE key = 'schema_version'"
        )
        row = cur.fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO sidecar_meta (key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
        else:
            self._conn.execute(
                "UPDATE sidecar_meta SET value = ? WHERE key = 'schema_version'",
                (str(SCHEMA_VERSION),),
            )
        self._conn.commit()

    def _migrate_legacy_primary_key(self) -> None:
        """Upgrade the v1 key without discarding existing embeddings."""
        exists = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'embeddings'"
        ).fetchone()
        if not exists:
            return
        pk_columns = [
            row[1]
            for row in sorted(
                (row for row in self.conn.execute("PRAGMA table_info(embeddings)") if row[5]),
                key=lambda row: row[5],
            )
        ]
        expected = ["node_id", "source_content_hash", "model", "dimensions", "dtype"]
        if pk_columns == expected:
            return
        with self.conn:
            self.conn.execute("DROP INDEX IF EXISTS idx_embeddings_file_path")
            self.conn.execute("DROP INDEX IF EXISTS idx_embeddings_name")
            self.conn.execute("DROP INDEX IF EXISTS idx_embeddings_content_hash")
            self.conn.execute("ALTER TABLE embeddings RENAME TO embeddings_legacy")
            self.conn.executescript(SIDECAR_SCHEMA)
            self.conn.execute(
                """INSERT OR REPLACE INTO embeddings
                   SELECT node_id, source_content_hash, model, dimensions, dtype,
                          embedding, node_kind, name, qualified_name, file_path,
                          language, start_line, end_line, document_text, created_at
                   FROM embeddings_legacy"""
            )
            self.conn.execute("DROP TABLE embeddings_legacy")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise SidecarError("SidecarDB not opened. Call open() first.")
        return self._conn

    def store_embeddings(
        self,
        records: list[dict[str, Any]],
        provider: EmbeddingProvider,
    ) -> int:
        """Store embedding records, replacing existing ones.

        Args:
            records: List of dicts with keys:
                node_id, content_hash, embedding (list[float]), node_kind,
                name, qualified_name, file_path, language, start_line,
                end_line, document_text
            provider: The embedding provider (for model/dimensions metadata).

        Returns:
            Number of records stored.
        """
        now = int(time.time())
        model = provider.model_name
        dims = provider.dimensions
        raw_bytes = provider.raw_bytes

        count = 0
        # Validate the complete batch before entering one atomic transaction.
        for rec in records:
            if len(rec["embedding"]) != dims:
                raise SidecarError(
                    f"Embedding dimension mismatch for node {rec['node_id']}: "
                    f"expected {dims}, got {len(rec['embedding'])}"
                )
        with self.conn:
            for rec in records:
                emb_bytes = raw_bytes(rec["embedding"])
                self.conn.execute(
                    """INSERT OR REPLACE INTO embeddings
                       (node_id, source_content_hash, model, dimensions, dtype,
                        embedding, node_kind, name, qualified_name, file_path,
                        language, start_line, end_line, document_text, created_at)
                       VALUES (?, ?, ?, ?, 'float32', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        rec["node_id"], rec["content_hash"], model, dims, emb_bytes,
                        rec.get("node_kind", ""), rec.get("name", ""),
                        rec.get("qualified_name", ""), rec.get("file_path", ""),
                        rec.get("language", ""), rec.get("start_line"),
                        rec.get("end_line"), rec.get("document_text", ""), now,
                    ),
                )
                self.conn.execute(
                    """DELETE FROM embeddings
                       WHERE node_id = ? AND model = ? AND dimensions = ?
                         AND dtype = 'float32' AND source_content_hash <> ?""",
                    (rec["node_id"], model, dims, rec["content_hash"]),
                )
                count += 1
        return count

    def remove_stale_records(
        self,
        current_ids: set[str],
        provider: EmbeddingProvider,
    ) -> int:
        """Remove embeddings for nodes no longer in the index.

        Args:
            current_ids: Set of node IDs that are current.
            provider: The embedding provider (for model/dimensions filter).

        Returns:
            Number of records removed.
        """
        if not current_ids:
            result = self.conn.execute(
                """DELETE FROM embeddings
                   WHERE model = ? AND dimensions = ? AND dtype = 'float32'""",
                (provider.model_name, provider.dimensions),
            )
            self.conn.commit()
            return result.rowcount
        placeholders = ",".join("?" for _ in current_ids)
        result = self.conn.execute(
            f"""DELETE FROM embeddings
                WHERE model = ? AND dimensions = ? AND dtype = 'float32'
                AND node_id NOT IN ({placeholders})""",
            (provider.model_name, provider.dimensions, *current_ids),
        )
        self.conn.commit()
        return result.rowcount

    def find_changed_nodes(
        self,
        documents: list[dict[str, Any]],
        provider: EmbeddingProvider,
    ) -> list[dict[str, Any]]:
        """Return only documents whose content hash has changed or are new.

        Compares against existing embeddings for the same model/dimensions.
        """
        model = provider.model_name
        dims = provider.dimensions
        result: list[dict[str, Any]] = []
        for doc in documents:
            row = self.conn.execute(
                """SELECT 1 FROM embeddings
                   WHERE node_id = ? AND source_content_hash = ?
                     AND model = ? AND dimensions = ? AND dtype = 'float32'""",
                (doc["node_id"], doc["content_hash"], model, dims),
            ).fetchone()
            if row is None:
                result.append(doc)
        return result

    def get_embedding(
        self, node_id: str, provider: EmbeddingProvider
    ) -> list[float] | None:
        """Retrieve a single embedding by node ID."""
        row = self.conn.execute(
            """SELECT embedding FROM embeddings
               WHERE node_id = ? AND model = ? AND dimensions = ? AND dtype = 'float32'""",
            (node_id, provider.model_name, provider.dimensions),
        ).fetchone()
        if row is None:
            return None
        return provider.from_bytes(row[0])

    def get_all_embeddings(
        self, provider: EmbeddingProvider
    ) -> list[dict[str, Any]]:
        """Retrieve all embeddings for the given provider."""
        rows = self.conn.execute(
            """SELECT node_id, embedding, name, qualified_name, file_path,
                      start_line, end_line, node_kind, language, document_text
               FROM embeddings
               WHERE model = ? AND dimensions = ? AND dtype = 'float32'""",
            (provider.model_name, provider.dimensions),
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            results.append({
                "node_id": row[0],
                "embedding": provider.from_bytes(row[1]),
                "name": row[2] or "",
                "qualified_name": row[3] or "",
                "file_path": row[4] or "",
                "start_line": row[5],
                "end_line": row[6],
                "node_kind": row[7] or "",
                "language": row[8] or "",
                "document_text": row[9] or "",
            })
        return results

    def get_status(self) -> dict[str, Any]:
        """Return status information about the sidecar."""
        if self._conn is None:
            return {"connected": False}
        try:
            total = self.conn.execute(
                "SELECT COUNT(*) FROM embeddings"
            ).fetchone()[0]
            models = [
                list(r)
                for r in self.conn.execute(
                    "SELECT model, dimensions, dtype, COUNT(*) FROM embeddings "
                    "GROUP BY model, dimensions, dtype"
                ).fetchall()
            ]
            schema_v = self.conn.execute(
                "SELECT value FROM sidecar_meta WHERE key = 'schema_version'"
            ).fetchone()
            return {
                "connected": True,
                "path": str(self._path),
                "total_embeddings": total,
                "model_groups": models,
                "schema_version": int(schema_v[0]) if schema_v else None,
            }
        except Exception as exc:
            return {"connected": True, "error": str(exc)}

    def clear(self, provider: EmbeddingProvider | None = None) -> int:
        """Clear embeddings, optionally filtered by provider."""
        if provider:
            result = self.conn.execute(
                """DELETE FROM embeddings
                   WHERE model = ? AND dimensions = ? AND dtype = 'float32'""",
                (provider.model_name, provider.dimensions),
            )
        else:
            result = self.conn.execute("DELETE FROM embeddings")
        self.conn.commit()
        return result.rowcount
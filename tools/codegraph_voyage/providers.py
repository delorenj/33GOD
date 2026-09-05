"""Embedding provider strategy — abstract base and concrete implementations.

Supports:
  - VoyageEmbeddingProvider: Real voyage-code-4 API via urllib.request (stdlib).
  - FakeEmbeddingProvider: Deterministic fake for tests.

Each provider produces embeddings as lists of floats with a configurable
dimension.
"""

from __future__ import annotations

import json
import os
import struct
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""

    @abstractmethod
    def embed_documents(self, texts: list[str], *, input_type: str = "document") -> list[list[float]]:
        """Embed a list of document texts.

        Returns a list of embedding vectors (list of floats).
        """
        ...

    @abstractmethod
    def embed_query(self, text: str, *, input_type: str = "query") -> list[float]:
        """Embed a single query string.

        Returns an embedding vector (list of floats).
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier (e.g. 'voyage-code-4')."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimension."""
        ...

    def raw_bytes(self, vector: list[float]) -> bytes:
        """Serialize a float vector to raw bytes (float32 little-endian)."""
        return struct.pack(f"<{len(vector)}f", *vector)

    def from_bytes(self, data: bytes) -> list[float]:
        """Deserialize raw bytes back to a float vector."""
        n = len(data) // 4
        return list(struct.unpack(f"<{n}f", data))


class VoyageEmbeddingProvider(EmbeddingProvider):
    """Real voyage-code-4 embedding provider via the Voyage API.

    Uses the official Voyage AI embeddings API:
      POST https://api.voyageai.com/v1/embeddings
    """

    API_URL = "https://api.voyageai.com/v1/embeddings"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "voyage-code-4",
        dimensions: int = 512,
        timeout: int = 60,
        batch_size: int = 128,
    ):
        if not api_key:
            api_key = os.environ.get("VOYAGE_API_KEY", "")
        if not api_key:
            raise ValueError(
                "VOYAGE_API_KEY is required. Set the environment variable or pass api_key."
            )
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._timeout = timeout
        if not 1 <= batch_size <= 128:
            raise ValueError("batch_size must be between 1 and 128")
        self._batch_size = batch_size

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(
        self, texts: list[str], *, input_type: str = "document"
    ) -> list[list[float]]:
        """Embed documents in Voyage batches while preserving input order."""
        result: list[list[float]] = []
        for offset in range(0, len(texts), self._batch_size):
            batch = texts[offset:offset + self._batch_size]
            try:
                result.extend(self._call_api(batch, input_type=input_type))
            except (RuntimeError, OSError, ValueError) as exc:
                batch_number = offset // self._batch_size + 1
                raise RuntimeError(
                    f"Voyage embedding batch {batch_number} failed: {exc}"
                ) from exc
        return result

    def embed_query(self, text: str, *, input_type: str = "query") -> list[float]:
        """Embed a query using voyage-code-4 with input_type='query'."""
        result = self._call_api([text], input_type=input_type)
        return result[0]

    def _call_api(
        self, texts: list[str], *, input_type: str
    ) -> list[list[float]]:
        """Make the actual API call to Voyage AI via stdlib urllib.request.

        Empty texts are filtered out before the API call; the returned list
        is mapped back to the original text order (empty lists for skipped
        texts).
        """
        # Track which original indices are non-empty
        valid_indices: list[int] = []
        valid_texts: list[str] = []
        for i, t in enumerate(texts):
            if t.strip():
                valid_indices.append(i)
                valid_texts.append(t)

        if not valid_texts:
            return [[] for _ in texts]

        payload: dict[str, Any] = {
            "model": self._model,
            "input": valid_texts,
            "input_type": input_type,
        }
        if self._dimensions:
            payload["output_dimension"] = self._dimensions

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Read minimal error info — never include response body (may
            # echo sensitive content).
            raise RuntimeError(
                f"Voyage API error {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Voyage API connection error: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Voyage API request failed: {exc}"
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError("Voyage API returned malformed JSON") from exc

        try:
            items = data["data"]
            if not isinstance(items, list) or len(items) != len(valid_texts):
                raise ValueError("embedding count mismatch")
            by_index: dict[int, list[float]] = {}
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("malformed embedding item")
                index = item.get("index")
                embedding = item.get("embedding")
                if not isinstance(index, int) or isinstance(index, bool):
                    raise ValueError("invalid embedding index")
                if index < 0 or index >= len(valid_texts) or index in by_index:
                    raise ValueError("duplicate or out-of-range embedding index")
                if not isinstance(embedding, list) or len(embedding) != self._dimensions:
                    raise ValueError("embedding dimension mismatch")
                if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in embedding):
                    raise ValueError("malformed embedding vector")
                by_index[index] = [float(value) for value in embedding]
            valid_embeddings = [by_index[index] for index in range(len(valid_texts))]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Voyage API response validation failed: {exc}") from exc

        # Map back to original text order
        result: list[list[float] | None] = [None] * len(texts)
        for orig_idx, emb in zip(valid_indices, valid_embeddings):
            result[orig_idx] = emb
        # Fill in empty lists for skipped texts
        return [r if r is not None else [] for r in result]


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic fake embedding provider for testing.

    Produces embedding vectors where each dimension is a deterministic
    function of the text content and dimension index.
    """

    def __init__(self, dimensions: int = 512, model: str = "fake-embedding-v1"):
        self._dimensions = dimensions
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _derive(self, text: str, seed: int = 0) -> list[float]:
        """Deterministic embedding from text content."""
        import hashlib

        h = hashlib.sha256(f"{text}:{seed}".encode("utf-8")).hexdigest()
        # Use the hash to seed a deterministic pseudo-random sequence
        vals: list[float] = []
        for i in range(self._dimensions):
            # Mix hash bytes with position
            h2 = hashlib.sha256(f"{h}:{i}:{seed}".encode("utf-8")).hexdigest()
            # Convert first 8 hex chars to a float in [0, 1)
            chunk = int(h2[:8], 16) / 0xFFFFFFFF
            vals.append(chunk)
        return vals

    def embed_documents(
        self, texts: list[str], *, input_type: str = "document"
    ) -> list[list[float]]:
        seed = 1 if input_type == "document" else 2
        return [self._derive(t, seed) for t in texts]

    def embed_query(self, text: str, *, input_type: str = "query") -> list[float]:
        return self._derive(text, 2 if input_type == "query" else 1)


def create_provider(
    provider_name: str = "fake",
    *,
    api_key: str | None = None,
    model: str = "voyage-code-4",
    dimensions: int = 512,
) -> EmbeddingProvider:
    """Factory: create an embedding provider by name.

    Supported names: 'voyage', 'fake'.
    """
    if provider_name == "voyage":
        return VoyageEmbeddingProvider(
            api_key=api_key, model=model, dimensions=dimensions
        )
    elif provider_name == "fake":
        return FakeEmbeddingProvider(dimensions=dimensions)
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use 'voyage' or 'fake'.")
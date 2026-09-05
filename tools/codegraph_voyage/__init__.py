"""codegraph-voyage — hybrid semantic retrieval sidecar for CodeGraph.

A self-contained CLI tool that builds symbol-level documents from a CodeGraph
index, generates voyage-code-4 embeddings, stores them in a sidecar SQLite DB,
and fuses lexical + vector retrieval with weighted reciprocal-rank fusion.
"""

__version__ = "0.1.0"
# codegraph-voyage

Hybrid semantic retrieval sidecar for [CodeGraph](https://github.com/nousresearch/codegraph).

## What it does

Builds symbol-level documents from a CodeGraph index, generates embedding vectors
via the Voyage AI API (or a deterministic fake for testing), stores them in a
sidecar SQLite database, and fuses lexical + vector retrieval via **weighted
reciprocal-rank fusion (RRF)**.

## Setup

```bash
# No dependencies beyond stdlib (Python 3.10+)
# Optional: set VOYAGE_API_KEY for real embedding
export VOYAGE_API_KEY="paas-...-...-..."
```

## Privacy & retention risk

Source text is transmitted to Voyage AI when the Voyage provider is selected.
The locally sanitized/redacted document content is what is sent, and Voyage
AI's data-use and retention policy applies to that transmission. Embeddings can
retain information about their inputs and should still be treated as sensitive.
The sidecar also stores the sanitized document text locally alongside each
embedding for provenance. It lives at `.codegraph/codegraph-voyage.db`; deleting
that sidecar removes these local text and embedding copies without affecting the
CodeGraph index.

## Source exclusions

Before any content is sent to the remote embedding API, the sanitizer
removes or redacts:

- **Sensitive paths**: `.env`, `credentials/`, `secrets/`, `*.pem`, `*.key`,
  `.git/`, `__pycache__/`, `node_modules/`, `.venv/`, `dist/`, `build/`, etc.
- **Sensitive line patterns**: Lines matching `password=`, `api_key=`,
  `token=`, `secret=`, etc. with apparent values are replaced with a
  `[redacted]` comment.

These checks happen **locally, before the API call**. The Voyage API never
sees the excluded content.

## Commands

| Command | Description |
|---|---|
| `python -m tools.codegraph_voyage index` | Build documents and store embeddings |
| `python -m tools.codegraph_voyage search <query>` | Hybrid semantic search |
| `python -m tools.codegraph_voyage status` | Show sidecar & CodeGraph status |
| `python -m tools.codegraph_voyage explore <query>` | Search + `codegraph explore` integration |

### `index`

Reads the CodeGraph DB at `.codegraph/codegraph.db`, builds symbol-level
documents from node metadata and source line ranges, generates embeddings
via the configured provider, and stores them in `.codegraph/codegraph-voyage.db`.

Incremental: only changed/new documents are re-embedded. Stale records are
removed.

```bash
# Index with fake provider (no API key, for testing)
python -m tools.codegraph_voyage index

# Index with voyage-code-4
VOYAGE_API_KEY="paas-..." python -m tools.codegraph_voyage index --provider voyage

# Index only functions and classes
python -m tools.codegraph_voyage index --kind "function,class"

# Index only files matching a pattern
python -m tools.codegraph_voyage index --file-filter "src/auth"
```

### `search` / `semantic_candidates`

Performs hybrid lexical + vector search on the indexed corpus. Results are
fused via weighted RRF. Exact identifier and path matches are **pinned** to
the top of results.

```bash
python -m tools.codegraph_voyage search "user authentication"
python -m tools.codegraph_voyage search "AuthService" --top-k 10 --json
```

### `explore`

Runs hybrid search, then passes the top-ranked candidate symbols to
`codegraph explore` for a full dependency-graph walk.

```bash
python -m tools.codegraph_voyage explore "PaymentGateway" --max-files 8
python -m tools.codegraph_voyage explore "UserManager" --dry-run  # preview only
```

### `status`

Shows the project root, CodeGraph DB stats, and sidecar embedding status.

```bash
python -m tools.codegraph_voyage status
```

## Architecture

```
tools/codegraph_voyage/
├── __init__.py       # Package metadata
├── __main__.py       # python -m entry point
├── cli.py            # CLI argument parsing and command dispatch
├── document.py       # Symbol-level document construction from CodeGraph nodes
├── providers.py      # EmbeddingProvider ABC, FakeEmbeddingProvider, VoyageEmbeddingProvider
├── ranking.py        # Weighted RRF, pinned candidates, cosine similarity
├── sidecar.py        # SQLite sidecar for embedding storage with incremental indexing
├── sanitize.py       # Path/content sanitization before remote transmission
├── explore.py        # Integration with `codegraph explore` CLI
└── tests/
    ├── __init__.py
    ├── test_all.py   # Unit test suite
    └── benchmark.py  # Retrieval quality benchmark (smoke)
```

The importable Python path is `tools.codegraph_voyage` (the underscore is
standard for multi-word CLI package names).

## Offline / fake mode

By default, the provider is `fake`, which produces deterministic embeddings
from text content. No API key or network access is needed. The fake provider
is suitable for development, testing, and CI.

```bash
python -m tools.codegraph_voyage index                   # uses fake by default
python -m tools.codegraph_voyage index --provider fake   # explicit
```

## Real Voyage AI (opt-in)

Set `VOYAGE_API_KEY` in your environment and pass `--provider voyage`:

```bash
export VOYAGE_API_KEY="paas-..."
python -m tools.codegraph_voyage index --provider voyage
```

The API key is **never** accepted via CLI flags to prevent secret leakage
through process listings or shell history.

## Benchmark

A smoke benchmark is included to verify the retrieval pipeline works:

```bash
python -m tools.codegraph_voyage.tests.benchmark
```

This uses a tiny synthetic corpus (10 documents, 5 queries). It reports
Recall@5, MRR, and NDCG@10 separately for lexical, vector, and fused
strategies. **No quality-lift claims should be made from these results.**
The benchmark exists to verify that the pipeline produces measurable output
and that fusion can improve over the worst single strategy.

## Testing

```bash
python -m tools.codegraph_voyage.tests.test_all
```

## Limitations

- **Small corpus**: Real-world benefit requires hundreds of indexed symbols.
- **Lexical ranker**: Uses a simple TF-IDF-like scorer, not a full BM25
  implementation. Adequate for moderate queries but not tuned for maximum
  lexical precision.
- **Vector search**: Brute-force cosine similarity. For large corpora
  (>10K vectors), an approximate nearest-neighbor index would be needed.
- **Sidecar DB**: All embeddings are stored in a single SQLite database.
  For very large projects, consider sharding by model or module.
- **Voyage API**: Requires network access. The `input_type` parameter is
  set to `document` for indexing and `query` for search queries, as
  recommended by Voyage AI's documentation.
- **No `requests` dependency**: The Voyage provider uses `urllib.request`
  from stdlib, so no pip install is needed for the runtime.
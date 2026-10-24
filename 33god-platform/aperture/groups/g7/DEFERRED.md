# DEFERRED — Aperture G7 (Memory + Enrichment)

Gaps, not delivered services or inferred acceptance. Each records why it was
deferred and the extraction contract to land it later.

## 1. Real hindsight server integration

**Deferred:** the memory plane talks to the bundled `memory-reference`
(SQLite FTS5 keyword store), not a real hindsight server.

**Why:** hindsight's wire surface is not a documented stable contract we can
vendor blindly, and this host's hindsight deployment is a production system
the charter keeps us from adopting or mutating for a smoke. Faking it was not
an option — so the bridge ships a REAL reference backend and the seam is the
config.

**Extraction contract:**
- A backend is any HTTP service implementing
  `POST /ingest {"events":[...]}` -> `{"stored": n}` and
  `POST /query {"q","limit"}` -> `{"results":[...]}` (2xx).
- Swap it in via `GOD_MEMORY_BACKENDS=hindsight=http://hindsight:PORT`
  (multiple backends allowed, `;`-separated).
- Prove it the same way the reference backend is proven: publish → tail →
  `/query` readback through the bridge, plus a dead-backend isolation check
  (bridge stays healthy, error counted in healthz).
- If the real server wants embeddings, it uses its OWN client-owned
  `GOD_LLM_*`-style config; the bridge's `/embed` endpoint is available as a
  convenience but ingestion must not depend on it.

## 2. Embeddings + rerank against a live external endpoint

**Deferred:** end-to-end proof of `/v1/embeddings` and `/v1/rerank` against a
real OpenAI-compatible endpoint.

**Why:** D1 zero-AAI — the bundle must not reference, require, or prove
against any operator-owned endpoint. EMPTY defaults are the contract; what is
proven is the degraded side of the boundary (healthy, degraded, says why,
keyword works) plus unit tests that a configured-but-dead endpoint degrades
to None/502 without crashing. The positive path is the client's to exercise
with their own endpoint at deploy time.

**Extraction contract:** with a real endpoint set, assert `/embed` returns
vectors of the configured model's dimension, `/query` reports
`"mode":"semantic"` with `reranked:true` when a rerank model is set, and
kill-the-endpoint mid-run leaves healthz healthy with keyword fallback.

## 3. Candystore test fixtures (excluded, deliberately)

**Deferred:** shipping candystore's test suite inside the bundle.

**Why:** `tests/fixtures/envelopes.jsonl` is a capture of real production
traffic — client project names, client-facing report bodies with addresses
and invoice amounts, personal home-dir paths, internal workspace names.
Vendoring it would violate secrets-never-travel. Found by the bundle's own
secrets scan on first run.

**Extraction contract:** if an in-bundle suite is ever wanted, generate
SYNTHETIC fixtures (the schema is fully known: 21 events-table columns +
envelope contract) rather than sanitizing captures; run the upstream suite
against the live submodule in the PM review gate (this run: 167 passed).

## 4. arm64 runtime execution

**Deferred:** running the bundle on real arm64 hardware.

**Why:** this build host is amd64. Every external image is arm64+amd64
manifest-verified (PROOF §4); the three local builds are from
`python:3.12-alpine` (multi-arch, native builder on target).

**Extraction contract:** on an arm64 host run the same cold cycle + smoke +
attach proof and record output; no code change expected.

## 5. Enrichment pass inventory (one pass shipped, more are additive)

**Shipped:** `typed-extraction-v1` (deterministic; no LLM).

**Deferred:** LLM-backed passes (summarization, entity linking, importance
scoring). They belong behind the SAME client-owned `GOD_LLM_*` surface as the
bridge's, with the same degraded-not-crashed semantics: a pass that needs the
LLM and finds it unconfigured must mark its derived events as
`pass: <name>-degraded` or simply not run — never fabricate enrichment.

**Extraction contract:** new pass = new `data.pass` name + new derived-event
shape review (4/5-token type/subject, causationid = source id), its own
unit tests pinning the transform, and a smoke arm if the pass is on the
default path.

## 6. Multi-G7 coexistence peak measurement

**Deferred:** measured G1–G6 + G7 summed peak on the target VM.

**Why:** G7's own budget is measured and capped (1216 MiB core; ~121 MiB
observed warm). The target's total coexistence peak depends on the other
groups' states, which change independently of this bundle.

**Extraction contract:** on the target host, snapshot `docker stats` across
all `god-g*` projects simultaneously under a representative load and record
it in the deploy runbook.

"""Tests for codegraph-voyage — document construction, sanitization, sidecar,
ranking, providers, and CLI integration."""

from __future__ import annotations

import json
import io
import email.message
import os
import sqlite3
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from unittest import mock


# =========================================================================
# Document construction
# =========================================================================

class TestDocumentConstruction(unittest.TestCase):
    """build_document, build_documents_from_db, build_document_for_node_id."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        # Create a source file
        self.src = self.root / "src" / "example.py"
        self.src.parent.mkdir(parents=True)
        self.src.write_text("""def hello():
    \"\"\"Say hello.\"\"\"
    return "hello"

class Greeter:
    \"\"\"A greeter class.\"\"\"
    def greet(self, name: str) -> str:
        return f"Hello {name}"
""")

    def tearDown(self):
        # Clean up temp dir
        import shutil
        shutil.rmtree(str(self.root), ignore_errors=True)

    def _make_node(self, **overrides: Any) -> dict[str, Any]:
        node = {
            "name": "hello",
            "qualified_name": "example.hello",
            "kind": "function",
            "file_path": "src/example.py",
            "language": "python",
            "start_line": 1,
            "end_line": 3,
            "docstring": "Say hello.",
            "signature": "def hello()",
            "visibility": "public",
            "return_type": "str",
        }
        node.update(overrides)
        return node

    def test_build_document_basic(self):
        from tools.codegraph_voyage.document import build_document
        doc = build_document(self._make_node(), self.root)
        self.assertIn("Symbol: hello", doc)
        self.assertIn("Qualified Name: example.hello", doc)
        self.assertIn("Kind: function", doc)
        self.assertIn("Say hello.", doc)
        self.assertIn('def hello():', doc)
        self.assertIn('return "hello"', doc)

    def test_build_document_no_source(self):
        from tools.codegraph_voyage.document import build_document
        doc = build_document(self._make_node(), self.root, include_source=False)
        self.assertIn("Symbol: hello", doc)
        self.assertNotIn('def hello():', doc)

    def test_build_document_max_lines(self):
        from tools.codegraph_voyage.document import build_document
        doc = build_document(self._make_node(), self.root, max_source_lines=1)
        self.assertIn("truncated at 1 lines", doc)

    def test_build_document_missing_file(self):
        from tools.codegraph_voyage.document import build_document
        node = self._make_node(file_path="nonexistent.py")
        doc = build_document(node, self.root)
        self.assertIn("Symbol: hello", doc)
        # No source lines, no error
        self.assertNotIn("Source:", doc)

    def test_source_path_cannot_escape_root(self):
        from tools.codegraph_voyage.document import build_document
        outside = self.root.parent / "outside-codegraph-voyage.txt"
        outside.write_text("must-not-be-embedded")
        try:
            node = self._make_node(file_path="../outside-codegraph-voyage.txt")
            doc = build_document(node, self.root)
            self.assertNotIn("must-not-be-embedded", doc)
            self.assertNotIn("Source:", doc)
        finally:
            outside.unlink(missing_ok=True)

    def test_compute_content_hash(self):
        from tools.codegraph_voyage.document import compute_content_hash
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        h3 = compute_content_hash("hello world!")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_build_documents_from_db_empty(self):
        """Table doesn't exist yet — should raise or handle gracefully."""
        from tools.codegraph_voyage.document import build_documents_from_db, DocumentConstructionError
        fake_db = self.root / "codegraph.db"
        # Not a valid SQLite DB
        fake_db.write_text("not a database")
        with self.assertRaises((sqlite3.DatabaseError, DocumentConstructionError)):
            build_documents_from_db(fake_db, self.root)


# =========================================================================
# Sanitization
# =========================================================================

class TestSanitization(unittest.TestCase):
    """is_sensitive_path and sanitize_content."""

    def test_sensitive_paths(self):
        from tools.codegraph_voyage.sanitize import is_sensitive_path
        self.assertTrue(is_sensitive_path(".env"))
        self.assertTrue(is_sensitive_path("config/.env.production"))
        self.assertTrue(is_sensitive_path("credentials/aws.json"))
        self.assertTrue(is_sensitive_path("secrets/keys.yaml"))
        self.assertTrue(is_sensitive_path(".git/config"))
        self.assertTrue(is_sensitive_path("src/__pycache__/foo.pyc"))
        self.assertTrue(is_sensitive_path("node_modules/bar.js"))
        self.assertTrue(is_sensitive_path(r"home\.aws\credentials"))
        self.assertTrue(is_sensitive_path(".ssh/id_ed25519"))
        self.assertTrue(is_sensitive_path(".docker/config.json"))
        self.assertTrue(is_sensitive_path("config/service-account-prod.json"))
        self.assertTrue(is_sensitive_path(".git-credentials"))
        self.assertTrue(is_sensitive_path("deploy_id_rsa"))
        self.assertFalse(is_sensitive_path("pyproject.toml"))
        self.assertFalse(is_sensitive_path("src/main.py"))
        self.assertFalse(is_sensitive_path("README.md"))

    def test_sanitize_content(self):
        from tools.codegraph_voyage.sanitize import sanitize_content
        content = "public code\npassword = 'supersecret'\nmore public code"
        result = sanitize_content(content, "src/main.py")
        self.assertIn("public code", result)
        self.assertIn("[redacted", result)
        self.assertIn("more public code", result)
        self.assertNotIn("supersecret", result)

    def test_sanitize_content_sensitive_path(self):
        from tools.codegraph_voyage.sanitize import sanitize_content
        result = sanitize_content("anything", ".env")
        self.assertEqual(result, "[content excluded: sensitive path]")

    def test_sanitize_content_all_redacted(self):
        from tools.codegraph_voyage.sanitize import sanitize_content
        # Use a value >= 8 chars to match the {8,} pattern
        result = sanitize_content("password = 'hunter2!!'", "src/main.py")
        # The line is replaced with a redacted marker, not removed
        self.assertIn("[redacted", result)

    def test_structured_secret_assignments_are_redacted(self):
        from tools.codegraph_voyage.sanitize import sanitize_content
        secret = "live-secret-938475"
        content = "\n".join([
            f'{{"password": "{secret}"}}',
            f"client_secret: {secret}",
            f'api_key = "{secret}"',
            f"auth_token={secret}",
            f"aws_secret_access_key = {secret}",
        ])
        result = sanitize_content(content, "config/settings.toml")
        self.assertNotIn(secret, result)
        self.assertEqual(result.count("[redacted"), 5)

    def test_placeholders_are_not_redacted(self):
        from tools.codegraph_voyage.sanitize import sanitize_content
        content = 'password = "placeholder"\ntoken: ${TOKEN}'
        self.assertEqual(sanitize_content(content, "config/example.yaml"), content)

    def test_private_key_block_is_redacted(self):
        from tools.codegraph_voyage.sanitize import sanitize_content
        begin_marker = "-----BEGIN " + "OPENSSH PRIVATE KEY" + "-----"
        end_marker = "-----END " + "OPENSSH PRIVATE KEY" + "-----"
        secret = "SECRETKEYDATA"
        content = f"{begin_marker}\n{secret}\n{end_marker}"
        result = sanitize_content(content, "src/example.txt")
        self.assertNotIn(secret, result)

    def test_sanitized_outbound_payload_has_no_secret(self):
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider
        from tools.codegraph_voyage.sanitize import sanitize_content
        secret = "voyage-must-never-see-this"
        sanitized = sanitize_content(f'{{"api_key": "{secret}"}}', "config.json")
        provider = VoyageEmbeddingProvider(api_key="test-key", dimensions=2)
        response = json.dumps({"data": [{"index": 0, "embedding": [0.1, 0.2]}]}).encode()
        with mock.patch("urllib.request.urlopen") as mocked:
            mocked.return_value.__enter__.return_value.read.return_value = response
            provider.embed_documents([sanitized])
            payload = mocked.call_args[0][0].data.decode()
        self.assertNotIn(secret, payload)
        self.assertIn("redacted", payload)


# =========================================================================
# Embedding providers
# =========================================================================

class TestProviders(unittest.TestCase):
    """FakeEmbeddingProvider determinism, VoyageEmbeddingProvider request
    construction via mocked urllib."""

    def test_fake_determinism(self):
        from tools.codegraph_voyage.providers import FakeEmbeddingProvider
        p = FakeEmbeddingProvider(dimensions=8)
        texts = ["hello", "world"]
        emb1 = p.embed_documents(texts)
        emb2 = p.embed_documents(texts)
        self.assertEqual(emb1, emb2)
        self.assertEqual(len(emb1), 2)
        self.assertEqual(len(emb1[0]), 8)
        self.assertEqual(len(emb1[1]), 8)
        # Different texts → different embeddings
        emb3 = p.embed_documents(["hello", "goodbye"])
        self.assertEqual(emb1[0], emb3[0])  # same text, same seed → same

    def test_fake_query_vs_document(self):
        from tools.codegraph_voyage.providers import FakeEmbeddingProvider
        p = FakeEmbeddingProvider(dimensions=4)
        q = p.embed_query("test")
        d = p.embed_documents(["test"])[0]
        # Different input_type → different seed → different embedding
        self.assertNotEqual(q, d)

    def test_fake_properties(self):
        from tools.codegraph_voyage.providers import FakeEmbeddingProvider
        p = FakeEmbeddingProvider(dimensions=256)
        self.assertEqual(p.model_name, "fake-embedding-v1")
        self.assertEqual(p.dimensions, 256)

    def test_raw_bytes_roundtrip(self):
        from tools.codegraph_voyage.providers import FakeEmbeddingProvider
        p = FakeEmbeddingProvider(dimensions=8)
        vec = p._derive("test")
        blob = p.raw_bytes(vec)
        restored = p.from_bytes(blob)
        self.assertAlmostEqual(vec[0], restored[0], places=6)
        self.assertEqual(len(vec), len(restored))

    def test_voyage_requires_key(self):
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider
        with mock.patch.dict("os.environ", {"VOYAGE_API_KEY": ""}):
            with self.assertRaises(ValueError):
                VoyageEmbeddingProvider(api_key="")

    def test_voyage_mocked_request(self):
        """Mock urllib.request to verify input_type payload."""
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider

        provider = VoyageEmbeddingProvider(api_key="test-key", model="voyage-code-4", dimensions=512)

        fake_response = json.dumps({
            "data": [
                {"index": 0, "embedding": [0.1] * 512},
                {"index": 1, "embedding": [0.2] * 512},
            ]
        }).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = fake_response

            result = provider.embed_documents(["hello", "world"], input_type="document")

            # Verify payload was sent correctly
            call_args = mock_urlopen.call_args
            req: urllib.request.Request = call_args[0][0]
            self.assertIsInstance(req, urllib.request.Request)
            payload = json.loads(req.data)
            self.assertEqual(payload["input_type"], "document")
            self.assertEqual(payload["model"], "voyage-code-4")
            self.assertEqual(payload["input"], ["hello", "world"])
            self.assertEqual(payload["output_dimension"], 512)
            self.assertEqual(req.headers["Authorization"], "Bearer test-key")

            # Verify result
            self.assertEqual(len(result), 2)
            self.assertEqual(len(result[0]), 512)
            self.assertEqual(result[0][0], 0.1)

    def test_voyage_query_uses_query_input_type(self):
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider
        provider = VoyageEmbeddingProvider(api_key="test-key", dimensions=2)
        fake_response = json.dumps({
            "data": [{"index": 0, "embedding": [0.4, 0.6]}]
        }).encode("utf-8")
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = fake_response
            result = provider.embed_query("find auth", input_type="query")
            payload = json.loads(mock_urlopen.call_args[0][0].data)
            self.assertEqual(payload["input_type"], "query")
            self.assertEqual(payload["input"], ["find auth"])
            self.assertEqual(result, [0.4, 0.6])

    def test_voyage_empty_texts(self):
        """Empty texts should return empty lists without API call."""
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider
        provider = VoyageEmbeddingProvider(api_key="test-key")
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            result = provider.embed_documents(["", "  "])
            mock_urlopen.assert_not_called()
            # Should return empty lists for each
            self.assertEqual(len(result), 2)

    def test_voyage_mixed_empty_and_valid(self):
        """Mix of empty and valid texts — only valid ones sent to API."""
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider
        provider = VoyageEmbeddingProvider(api_key="test-key", dimensions=4)

        fake_response = json.dumps({
            "data": [
                {"index": 0, "embedding": [0.1, 0.2, 0.3, 0.4]},
                {"index": 1, "embedding": [0.5, 0.6, 0.7, 0.8]},
            ]
        }).encode("utf-8")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = fake_response

            texts = ["hello", "", "world"]
            result = provider.embed_documents(texts, input_type="document")

            # Verify only non-empty texts sent
            payload = json.loads(mock_urlopen.call_args[0][0].data)
            self.assertEqual(payload["input"], ["hello", "world"])

            # Verify mapping back
            self.assertEqual(len(result), 3)
            self.assertEqual(len(result[0]), 4)  # "hello" embedding
            self.assertEqual(result[1], [])       # empty text → empty list
            self.assertEqual(len(result[2]), 4)   # "world" embedding

    def test_voyage_http_error_no_body_in_message(self):
        """HTTP error should not include response body in error message."""
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider
        provider = VoyageEmbeddingProvider(api_key="test-key")

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="https://api.voyageai.com/v1/embeddings",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=None,
            )
            with self.assertRaises(RuntimeError) as ctx:
                provider.embed_documents(["test"], input_type="document")
            self.assertNotIn("sensitive", str(ctx.exception).lower())
            self.assertIn("401", str(ctx.exception))

    def test_voyage_batches_more_than_128_in_order(self):
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider
        provider = VoyageEmbeddingProvider(api_key="test-key", dimensions=2)

        def response_for(request, timeout=None):
            inputs = json.loads(request.data)["input"]
            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps({
                "data": [
                    {"index": i, "embedding": [float(text[1:]), 1.0]}
                    for i, text in enumerate(inputs)
                ]
            }).encode()
            return response

        with mock.patch("urllib.request.urlopen", side_effect=response_for) as mocked:
            result = provider.embed_documents([f"t{i}" for i in range(257)])
        self.assertEqual(mocked.call_count, 3)
        self.assertEqual(
            [len(json.loads(call.args[0].data)["input"]) for call in mocked.call_args_list],
            [128, 128, 1],
        )
        self.assertEqual([row[0] for row in result], list(map(float, range(257))))

    def test_voyage_configurable_batch_size_and_partial_failure(self):
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider
        provider = VoyageEmbeddingProvider(api_key="test-key", dimensions=1, batch_size=2)
        good = mock.MagicMock()
        good.__enter__.return_value.read.return_value = json.dumps({
            "data": [{"index": 0, "embedding": [1.0]}, {"index": 1, "embedding": [2.0]}]
        }).encode()
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=[good, urllib.error.URLError("offline")],
        ):
            with self.assertRaisesRegex(RuntimeError, "batch 2"):
                provider.embed_documents(["a", "b", "c"])

    def test_voyage_response_validation(self):
        from tools.codegraph_voyage.providers import VoyageEmbeddingProvider
        provider = VoyageEmbeddingProvider(api_key="test-key", dimensions=2)
        invalid = [
            {"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
            {"data": [{"index": 0, "embedding": [0.1, 0.2]}, {"index": 0, "embedding": [0.3, 0.4]}]},
            {"data": [{"index": 0, "embedding": [0.1]}, {"index": 1, "embedding": [0.3, 0.4]}]},
            {"unexpected": []},
        ]
        for payload in invalid:
            with self.subTest(payload=payload), mock.patch("urllib.request.urlopen") as mocked:
                mocked.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
                with self.assertRaisesRegex(RuntimeError, "response validation"):
                    provider.embed_documents(["a", "b"])

    def test_create_provider(self):
        from tools.codegraph_voyage.providers import create_provider, FakeEmbeddingProvider, VoyageEmbeddingProvider
        p1 = create_provider("fake")
        self.assertIsInstance(p1, FakeEmbeddingProvider)
        with self.assertRaises(ValueError):
            create_provider("unknown")


# =========================================================================
# Sidecar DB
# =========================================================================

class TestSidecarDB(unittest.TestCase):
    """SidecarDB create, store, retrieve, stale removal, incremental indexing."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.db_path = self.tmpdir / "sidecar.db"

    def tearDown(self):
        import shutil
        shutil.rmtree(str(self.tmpdir), ignore_errors=True)

    def _make_provider(self, name="fake-embedding-v1", dims=512):
        from tools.codegraph_voyage.providers import FakeEmbeddingProvider
        return FakeEmbeddingProvider(dimensions=dims, model=name)

    def test_open_and_close(self):
        from tools.codegraph_voyage.sidecar import SidecarDB
        db = SidecarDB(self.db_path)
        db.open()
        self.assertIsNotNone(db.conn)
        status = db.get_status()
        self.assertTrue(status["connected"])
        self.assertEqual(status["total_embeddings"], 0)
        pk_columns = [
            row[1]
            for row in sorted(
                (row for row in db.conn.execute("PRAGMA table_info(embeddings)") if row[5]),
                key=lambda row: row[5],
            )
        ]
        self.assertEqual(
            pk_columns,
            ["node_id", "source_content_hash", "model", "dimensions", "dtype"],
        )
        db.close()
        with self.assertRaises(Exception):
            db.conn

    def test_store_and_retrieve(self):
        from tools.codegraph_voyage.sidecar import SidecarDB
        provider = self._make_provider(dims=3)
        db = SidecarDB(self.db_path)
        db.open()
        try:
            records = [{
                "node_id": "n1",
                "content_hash": "abc",
                "embedding": [0.1, 0.2, 0.3],
                "node_kind": "function",
                "name": "hello",
                "qualified_name": "mod.hello",
                "file_path": "src/main.py",
                "language": "python",
                "start_line": 1,
                "end_line": 5,
                "document_text": "def hello(): pass",
            }]
            stored = db.store_embeddings(records, provider)
            self.assertEqual(stored, 1)

            # Retrieve
            emb = db.get_embedding("n1", provider)
            self.assertIsNotNone(emb)
            self.assertEqual(len(emb), 3)
            self.assertAlmostEqual(emb[0], 0.1)

            # All embeddings
            all_emb = db.get_all_embeddings(provider)
            self.assertEqual(len(all_emb), 1)
            self.assertEqual(all_emb[0]["node_id"], "n1")
        finally:
            db.close()

    def test_replace_existing(self):
        from tools.codegraph_voyage.sidecar import SidecarDB
        provider = self._make_provider(dims=3)
        db = SidecarDB(self.db_path)
        db.open()
        try:
            db.store_embeddings([{
                "node_id": "n1",
                "content_hash": "abc",
                "embedding": [0.1, 0.2, 0.3],
                "node_kind": "function",
                "name": "hello",
                "qualified_name": "mod.hello",
                "file_path": "src/main.py",
                "language": "python",
                "start_line": 1,
                "end_line": 5,
                "document_text": "def hello(): pass",
            }], provider)
            db.store_embeddings([{
                "node_id": "n1",
                "content_hash": "def",
                "embedding": [0.9, 0.8, 0.7],
                "node_kind": "function",
                "name": "hello",
                "qualified_name": "mod.hello",
                "file_path": "src/main.py",
                "language": "python",
                "start_line": 1,
                "end_line": 5,
                "document_text": "def hello(): pass",
            }], provider)
            emb = db.get_embedding("n1", provider)
            self.assertAlmostEqual(emb[0], 0.9)
            self.assertEqual(db.get_status()["total_embeddings"], 1)
        finally:
            db.close()

    def test_find_changed_nodes(self):
        from tools.codegraph_voyage.sidecar import SidecarDB
        provider = self._make_provider(dims=2)
        db = SidecarDB(self.db_path)
        db.open()
        try:
            # Store one
            db.store_embeddings([{
                "node_id": "n1",
                "content_hash": "abc",
                "embedding": [0.1, 0.2],
                "node_kind": "function",
                "name": "hello",
                "qualified_name": "",
                "file_path": "src/main.py",
                "language": "python",
                "start_line": 1,
                "end_line": 5,
                "document_text": "def hello(): pass",
            }], provider)

            # Same hash → unchanged
            docs = [{"node_id": "n1", "content_hash": "abc"}]
            changed = db.find_changed_nodes(docs, provider)
            self.assertEqual(len(changed), 0)

            # Different hash → changed
            docs2 = [{"node_id": "n1", "content_hash": "xyz"}]
            changed2 = db.find_changed_nodes(docs2, provider)
            self.assertEqual(len(changed2), 1)

            # New node → changed
            docs3 = [{"node_id": "n2", "content_hash": "new"}]
            changed3 = db.find_changed_nodes(docs3, provider)
            self.assertEqual(len(changed3), 1)
        finally:
            db.close()

    def test_remove_stale_records(self):
        from tools.codegraph_voyage.sidecar import SidecarDB
        provider = self._make_provider(dims=1)
        db = SidecarDB(self.db_path)
        db.open()
        try:
            db.store_embeddings([
                {
                    "node_id": "n1",
                    "content_hash": "a",
                    "embedding": [0.1],
                    "node_kind": "f",
                    "name": "a",
                    "qualified_name": "a",
                    "file_path": "a.py",
                    "language": "py",
                    "start_line": 1,
                    "end_line": 2,
                    "document_text": "a",
                },
                {
                    "node_id": "n2",
                    "content_hash": "b",
                    "embedding": [0.2],
                    "node_kind": "f",
                    "name": "b",
                    "qualified_name": "b",
                    "file_path": "b.py",
                    "language": "py",
                    "start_line": 1,
                    "end_line": 2,
                    "document_text": "b",
                },
            ], provider)

            # Remove n2 (stale)
            removed = db.remove_stale_records({"n1"}, provider)
            self.assertEqual(removed, 1)

            # n1 should still exist
            self.assertIsNotNone(db.get_embedding("n1", provider))
            self.assertIsNone(db.get_embedding("n2", provider))
        finally:
            db.close()

    def test_empty_current_set_removes_all_for_provider(self):
        from tools.codegraph_voyage.sidecar import SidecarDB
        provider = self._make_provider(dims=1)
        db = SidecarDB(self.db_path)
        db.open()
        try:
            db.store_embeddings([{
                "node_id": "stale", "content_hash": "x", "embedding": [0.1],
                "node_kind": "f", "name": "stale", "qualified_name": "stale",
                "file_path": "stale.py", "language": "python",
                "start_line": 1, "end_line": 1, "document_text": "stale",
            }], provider)
            self.assertEqual(db.remove_stale_records(set(), provider), 1)
            self.assertIsNone(db.get_embedding("stale", provider))
        finally:
            db.close()

    def test_dimension_mismatch_is_atomic(self):
        from tools.codegraph_voyage.sidecar import SidecarDB, SidecarError
        provider = self._make_provider(dims=2)
        db = SidecarDB(self.db_path)
        db.open()
        try:
            records = [
                {"node_id": "ok", "content_hash": "a", "embedding": [0.1, 0.2]},
                {"node_id": "bad", "content_hash": "b", "embedding": [0.3]},
            ]
            with self.assertRaises(SidecarError):
                db.store_embeddings(records, provider)
            self.assertEqual(db.get_status()["total_embeddings"], 0)
        finally:
            db.close()

    def test_model_incompatibility(self):
        """Different model/dimensions are segregated."""
        from tools.codegraph_voyage.sidecar import SidecarDB
        from tools.codegraph_voyage.providers import FakeEmbeddingProvider
        provider_a = FakeEmbeddingProvider(dimensions=4, model="fake-model-a")
        provider_b = FakeEmbeddingProvider(dimensions=4, model="fake-model-b")
        db = SidecarDB(self.db_path)
        db.open()
        try:
            db.store_embeddings([{
                "node_id": "n1",
                "content_hash": "a",
                "embedding": [0.1, 0.2, 0.3, 0.4],
                "node_kind": "f",
                "name": "a",
                "qualified_name": "a",
                "file_path": "a.py",
                "language": "py",
                "start_line": 1,
                "end_line": 2,
                "document_text": "a",
            }], provider_a)

            # Provider B should not see n1 (different model, same dimensions)
            self.assertIsNone(db.get_embedding("n1", provider_b))

            # Provider A should see it
            self.assertIsNotNone(db.get_embedding("n1", provider_a))
        finally:
            db.close()

    def test_clear(self):
        from tools.codegraph_voyage.sidecar import SidecarDB
        provider = self._make_provider(dims=1)
        db = SidecarDB(self.db_path)
        db.open()
        try:
            db.store_embeddings([{
                "node_id": "n1",
                "content_hash": "a",
                "embedding": [0.1],
                "node_kind": "f",
                "name": "a",
                "qualified_name": "",
                "file_path": "a.py",
                "language": "py",
                "start_line": 1,
                "end_line": 2,
                "document_text": "a",
            }], provider)
            cleared = db.clear(provider)
            self.assertEqual(cleared, 1)
            self.assertEqual(db.get_status()["total_embeddings"], 0)
        finally:
            db.close()


# =========================================================================
# Ranking
# =========================================================================

class TestRanking(unittest.TestCase):
    """Pinned candidates, lexical ranking, vector ranking, RRF fusion, hybrid search."""

    def _make_doc(self, node_id: str, name: str = "", qname: str = "",
                  fpath: str = "", kind: str = "function", doc_text: str = "",
                  embedding: list[float] | None = None) -> dict[str, Any]:
        return {
            "node_id": node_id,
            "name": name,
            "qualified_name": qname,
            "file_path": fpath,
            "node_kind": kind,
            "language": "python",
            "start_line": 1,
            "end_line": 5,
            "document_text": doc_text or f"def {name}: pass",
            "embedding": embedding or [0.0] * 4,
        }

    def test_pinned_exact_name(self):
        from tools.codegraph_voyage.ranking import find_pinned_candidates
        candidates = [
            self._make_doc("n1", name="AuthService", qname="app.AuthService"),
            self._make_doc("n2", name="UserModel", qname="app.UserModel"),
        ]
        pinned = find_pinned_candidates("AuthService", candidates)
        self.assertEqual(len(pinned), 1)
        self.assertEqual(pinned[0].node_id, "n1")
        self.assertTrue(pinned[0].is_pinned)
        self.assertIn("exact_name", pinned[0].provenance)

        # The same node may arrive from both vector and lexical candidate lists.
        deduped = find_pinned_candidates("AuthService", candidates + candidates)
        self.assertEqual([p.node_id for p in deduped], ["n1"])

    def test_pinned_path_match(self):
        from tools.codegraph_voyage.ranking import find_pinned_candidates
        candidates = [
            self._make_doc("n1", name="f1", fpath="src/auth/login.py"),
            self._make_doc("n2", name="f2", fpath="src/utils/helper.py"),
        ]
        self.assertEqual(find_pinned_candidates("auth", candidates), [])
        pinned = find_pinned_candidates("login.py", candidates)
        self.assertEqual([p.node_id for p in pinned], ["n1"])
        self.assertIn("exact_basename", pinned[0].provenance)
        exact_path = find_pinned_candidates("SRC/AUTH/LOGIN.PY", candidates)
        self.assertEqual([p.node_id for p in exact_path], ["n1"])
        self.assertIn("exact_path", exact_path[0].provenance)

    def test_pinned_partial_qname(self):
        from tools.codegraph_voyage.ranking import find_pinned_candidates
        candidates = [
            self._make_doc("n1", qname="app.services.auth.AuthService"),
            self._make_doc("n2", qname="app.models.User"),
        ]
        self.assertEqual(find_pinned_candidates("auth service", candidates), [])

    def test_pinning_rejects_empty_and_substring_queries(self):
        from tools.codegraph_voyage.ranking import find_pinned_candidates
        candidates = [self._make_doc("n1", name="Alpha", fpath="src/data.py")]
        self.assertEqual(find_pinned_candidates("", candidates), [])
        self.assertEqual(find_pinned_candidates("   ", candidates), [])
        self.assertEqual(find_pinned_candidates("a", candidates), [])

    def test_cosine_similarity(self):
        from tools.codegraph_voyage.ranking import cosine_similarity
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)
        self.assertAlmostEqual(cosine_similarity([1, 1], [1, 1]), 1.0)
        # Zero vectors
        self.assertEqual(cosine_similarity([0, 0], [0, 0]), 0.0)

    def test_rank_by_vector_similarity(self):
        from tools.codegraph_voyage.ranking import rank_by_vector_similarity
        qv = [1.0, 0.0, 0.0, 0.0]
        candidates = [
            self._make_doc("n1", embedding=[0.9, 0.1, 0.0, 0.0]),
            self._make_doc("n2", embedding=[0.0, 0.9, 0.0, 0.0]),
        ]
        results = rank_by_vector_similarity(qv, candidates, top_k=5)
        self.assertEqual(len(results), 2)
        # n1 is more similar (closer to [1,0,0,0])
        self.assertEqual(results[0].node_id, "n1")
        self.assertGreater(results[0].vector_score, results[1].vector_score)

    def test_rank_by_lexical_similarity(self):
        from tools.codegraph_voyage.ranking import rank_by_lexical_similarity
        candidates = [
            self._make_doc("n1", name="a", doc_text="auth service login handler"),
            self._make_doc("n2", name="b", doc_text="user model data access"),
        ]
        results = rank_by_lexical_similarity("auth login", candidates, top_k=5)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].node_id, "n1")

    def test_reciprocal_rank_fusion(self):
        from tools.codegraph_voyage.ranking import (
            reciprocal_rank_fusion, RankingResult,
        )
        list_a = [
            RankingResult(node_id="n1", score=1.0, provenance="vector"),
            RankingResult(node_id="n2", score=0.8, provenance="vector"),
        ]
        list_b = [
            RankingResult(node_id="n2", score=1.0, provenance="lexical"),
            RankingResult(node_id="n3", score=0.9, provenance="lexical"),
        ]
        fused = reciprocal_rank_fusion([list_a, list_b], weights=[0.5, 0.5], k=60)
        self.assertEqual(len(fused), 3)
        # n2 appears in both lists → highest fused score
        self.assertEqual(fused[0].node_id, "n2")
        self.assertIn("vector", fused[0].provenance)
        self.assertIn("lexical", fused[0].provenance)

    def test_hybrid_search_pinned(self):
        from tools.codegraph_voyage.ranking import hybrid_search
        qv = [1.0, 0.0, 0.0, 0.0]
        vector_candidates = [
            self._make_doc("n1", name="AuthService", embedding=[0.9, 0.0, 0.0, 0.0]),
            self._make_doc("n2", name="Helper", embedding=[0.0, 0.9, 0.0, 0.0]),
        ]
        lexical_candidates = list(vector_candidates)
        results = hybrid_search("AuthService", qv, vector_candidates, lexical_candidates, top_k=5)
        self.assertEqual(len(results), 2)
        # AuthService should be pinned to top
        self.assertEqual(results[0].node_id, "n1")
        self.assertTrue(results[0].is_pinned)

    def test_merge_pinned_into_results(self):
        from tools.codegraph_voyage.ranking import merge_pinned_into_results, RankingResult
        pinned = [
            RankingResult(node_id="n1", score=10.0, is_pinned=True, exact_score=10.0),
            RankingResult(node_id="n2", score=5.0, is_pinned=True, exact_score=5.0),
        ]
        fused = [
            RankingResult(node_id="n3", score=0.5),
            RankingResult(node_id="n1", score=0.3, lexical_score=0.7,
                          vector_score=0.8, provenance="lexical+vector"),
        ]
        merged = merge_pinned_into_results(pinned, fused)
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[0].node_id, "n1")
        self.assertEqual(merged[1].node_id, "n2")
        self.assertEqual(merged[2].node_id, "n3")
        self.assertEqual(merged[0].lexical_score, 0.7)
        self.assertEqual(merged[0].vector_score, 0.8)
        self.assertIn("lexical", merged[0].provenance)
        self.assertIn("vector", merged[0].provenance)

    def test_ranking_result_to_dict(self):
        from tools.codegraph_voyage.ranking import RankingResult
        r = RankingResult(
            node_id="n1", score=0.5, is_pinned=True,
            lexical_score=0.3, vector_score=0.2,
            name="hello", provenance="lexical+vector",
        )
        d = r.to_dict()
        self.assertEqual(d["node_id"], "n1")
        self.assertEqual(d["score"], 0.5)
        self.assertTrue(d["is_pinned"])


# =========================================================================
# Explore integration
# =========================================================================

class TestExplore(unittest.TestCase):
    """build_explore_query and codegraph_explore (dry-run)."""

    def test_build_explore_query(self):
        from tools.codegraph_voyage.ranking import RankingResult
        from tools.codegraph_voyage.explore import build_explore_query
        candidates = [
            RankingResult(node_id="n1", name="hello", qualified_name="mod.hello", file_path="src/a.py"),
            RankingResult(node_id="n2", name="world", qualified_name="mod.world", file_path="src/b.py"),
        ]
        q = build_explore_query(candidates, max_symbols=10)
        self.assertIn("mod.hello", q)
        self.assertIn("mod.world", q)

    def test_codegraph_explore_dry_run(self):
        from tools.codegraph_voyage.ranking import RankingResult
        from tools.codegraph_voyage.explore import codegraph_explore
        candidates = [
            RankingResult(node_id="n1", name="hello", qualified_name="mod.hello"),
        ]
        result = codegraph_explore(candidates, project_path="/tmp", dry_run=True)
        self.assertIn("command", result)
        self.assertIn("codegraph explore", result["command"])

    def test_codegraph_explore_fake_executable(self):
        from tools.codegraph_voyage.ranking import RankingResult
        from tools.codegraph_voyage.explore import codegraph_explore
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "fake-codegraph"
            fake.write_text("#!/bin/sh\nprintf 'FAKE_EXPLORE:%s\\n' \"$*\"\n")
            fake.chmod(0o755)
            candidates = [RankingResult(
                node_id="n1", name="AuthService", qualified_name="app.AuthService"
            )]
            result = codegraph_explore(
                candidates, project_path=tmp, codegraph_bin=str(fake), timeout=5
            )
            self.assertEqual(result["returncode"], 0)
            self.assertIn("FAKE_EXPLORE:explore", result["stdout"])
            self.assertIn("app.AuthService", result["stdout"])

    def test_codegraph_explore_no_candidates(self):
        from tools.codegraph_voyage.explore import codegraph_explore
        result = codegraph_explore([], project_path="/tmp")
        self.assertEqual(result["returncode"], 1)
        self.assertEqual(result["error"], "No candidates")


# =========================================================================
# CLI
# =========================================================================

class TestCLI(unittest.TestCase):
    """CLI argument parsing and command dispatch."""

    def test_missing_voyage_key_fails_actionably(self):
        import argparse
        from tools.codegraph_voyage.cli import _make_provider
        args = argparse.Namespace(provider="voyage", model="voyage-code-4", dimensions=16)
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "VOYAGE_API_KEY"):
                _make_provider(args)

    def test_search_rejects_incompatible_sidecar_model(self):
        import argparse
        from tools.codegraph_voyage.cli import cmd_search
        from tools.codegraph_voyage.providers import FakeEmbeddingProvider
        from tools.codegraph_voyage.sidecar import SidecarDB
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph_dir = root / ".codegraph"
            graph_dir.mkdir()
            (graph_dir / "codegraph.db").touch()
            sidecar = SidecarDB(graph_dir / "codegraph-voyage.db")
            sidecar.open()
            sidecar.store_embeddings([{
                "node_id": "n1", "content_hash": "h1", "embedding": [0.1, 0.2],
                "node_kind": "f", "name": "n1", "qualified_name": "n1",
                "file_path": "n1.py", "language": "python", "start_line": 1,
                "end_line": 1, "document_text": "n1",
            }], FakeEmbeddingProvider(dimensions=2, model="voyage-code-4"))
            sidecar.close()
            args = argparse.Namespace(
                project=str(root), query="n1", provider="fake", model="voyage-code-4",
                dimensions=2, no_source=False, max_source_lines=20, kind=None,
                file_filter=None, top_k=5, lexical_weight=0.5, vector_weight=0.5,
                rrf_k=60, json=False,
            )
            stderr = io.StringIO()
            with mock.patch(
                "tools.codegraph_voyage.cli.build_documents_from_db", return_value=[]
            ), mock.patch("sys.stderr", stderr):
                rc = cmd_search(args)
            self.assertEqual(rc, 2)
            self.assertIn("Sidecar contains voyage-code-4 dims=2", stderr.getvalue())
            self.assertIn("clear and rebuild", stderr.getvalue())

    def test_search_json_stdout_is_parseable_list(self):
        import argparse
        from tools.codegraph_voyage.cli import cmd_search
        from tools.codegraph_voyage.sidecar import SidecarDB
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph_dir = root / ".codegraph"
            graph_dir.mkdir()
            (graph_dir / "codegraph.db").touch()
            sidecar = SidecarDB(graph_dir / "codegraph-voyage.db")
            sidecar.open()
            sidecar.close()
            args = argparse.Namespace(
                project=str(root), query="n1", provider="fake", model="voyage-code-4",
                dimensions=2, no_source=False, max_source_lines=20, kind=None,
                file_filter=None, top_k=5, lexical_weight=0.5, vector_weight=0.5,
                rrf_k=60, json=True,
            )
            stdout = io.StringIO()
            with mock.patch(
                "tools.codegraph_voyage.cli.build_documents_from_db", return_value=[]
            ), mock.patch("sys.stdout", stdout):
                rc = cmd_search(args)
            self.assertEqual(rc, 0)
            self.assertIsInstance(json.loads(stdout.getvalue()), list)

    def _assert_failed_index_preserves_sidecar(self, urlopen_side_effect=None, response=None):
        import argparse
        from tools.codegraph_voyage.cli import cmd_index
        from tools.codegraph_voyage.providers import FakeEmbeddingProvider, VoyageEmbeddingProvider
        from tools.codegraph_voyage.sidecar import SidecarDB
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph_dir = root / ".codegraph"
            graph_dir.mkdir()
            (graph_dir / "codegraph.db").touch()
            db_path = graph_dir / "codegraph-voyage.db"
            sidecar = SidecarDB(db_path)
            sidecar.open()
            sidecar.store_embeddings([{
                "node_id": "sentinel", "content_hash": "original", "embedding": [0.5],
                "node_kind": "f", "name": "sentinel", "qualified_name": "sentinel",
                "file_path": "sentinel.py", "language": "python", "start_line": 1,
                "end_line": 1, "document_text": "sentinel",
            }], FakeEmbeddingProvider(dimensions=1, model="sentinel-model"))
            before = sidecar.conn.execute(
                "SELECT node_id, source_content_hash, model FROM embeddings ORDER BY node_id"
            ).fetchall()
            sidecar.close()
            doc = {
                "node_id": "new", "document": 'api_key = "do-not-send"',
                "node_kind": "f", "name": "new", "qualified_name": "new",
                "file_path": "src/new.py", "language": "python", "start_line": 1,
                "end_line": 1,
            }
            args = argparse.Namespace(
                project=str(root), provider="voyage", model="voyage-code-4", dimensions=2,
                no_source=False, max_source_lines=20, kind=None, file_filter=None,
            )
            provider = VoyageEmbeddingProvider(api_key="test-key", dimensions=2)
            stderr = io.StringIO()
            patcher = mock.patch("urllib.request.urlopen")
            mocked_urlopen = patcher.start()
            if urlopen_side_effect is not None:
                mocked_urlopen.side_effect = urlopen_side_effect
            else:
                mocked_urlopen.return_value.__enter__.return_value.read.return_value = response
            try:
                with mock.patch(
                    "tools.codegraph_voyage.cli._make_provider_or_report", return_value=provider
                ), mock.patch(
                    "tools.codegraph_voyage.cli.build_documents_from_db", return_value=[doc]
                ), mock.patch("sys.stderr", stderr):
                    rc = cmd_index(args)
            finally:
                patcher.stop()
            sidecar.open()
            after = sidecar.conn.execute(
                "SELECT node_id, source_content_hash, model FROM embeddings ORDER BY node_id"
            ).fetchall()
            sidecar.close()
            self.assertEqual(rc, 2)
            self.assertEqual(after, before)
            self.assertIn("sidecar left unchanged", stderr.getvalue())
            return stderr.getvalue()

    def test_index_http_failure_is_atomic(self):
        error = urllib.error.HTTPError(
            url="https://api.voyageai.com/v1/embeddings", code=503,
            msg="Unavailable", hdrs=email.message.Message(), fp=None,
        )
        stderr = self._assert_failed_index_preserves_sidecar(urlopen_side_effect=error)
        self.assertIn("503", stderr)

    def test_index_malformed_voyage_response_is_atomic(self):
        stderr = self._assert_failed_index_preserves_sidecar(
            response=json.dumps({"data": []}).encode()
        )
        self.assertIn("response validation failed", stderr)

    def test_parser_accepts_commands(self):
        from tools.codegraph_voyage.cli import _build_parser
        ap = _build_parser()
        # Check commands are registered (--help exits, so catch SystemExit)
        for cmd in ["index", "search", "status", "explore"]:
            sub = ap._subparsers._group_actions[0]
            self.assertIn(cmd, sub.choices)

    def test_help_prints(self):
        from tools.codegraph_voyage.cli import main
        # --help on the main parser exits with code 0; catch SystemExit
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        self.assertEqual(ctx.exception.code, 0)


# =========================================================================
# Sanitize test
# =========================================================================

class TestSanitizeModule(unittest.TestCase):
    """Module-level exports."""

    def test_excluded_path_patterns(self):
        from tools.codegraph_voyage.sanitize import EXCLUDED_PATH_PATTERNS
        self.assertIsInstance(EXCLUDED_PATH_PATTERNS, list)
        self.assertTrue(len(EXCLUDED_PATH_PATTERNS) > 0)


if __name__ == "__main__":
    unittest.main()
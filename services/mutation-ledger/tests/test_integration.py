"""Layer 3 integration test: mutation-ledger consumer -> enrichment -> Qdrant.

Publishes a test event to RabbitMQ, starts the consumer briefly, then
verifies the enriched mutation was embedded in Qdrant.
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pika

# ─── Test configuration ─────────────────────────────────────────────
RABBIT_URL = os.environ.get("RABBIT_URL", "amqp://user:pass@localhost:5672/")
EXCHANGE = "bloodbank.events.v1"
ROUTING_KEY = "tool.mutation.write"
TEST_COLLECTION = "mutations-test-integration"  # isolated test collection

# Test event that looks like what hookd daemon publishes
TEST_EVENT = {
    "event_type": "tool.mutation.write",
    "hook_type": "post_tool_use",
    "tool_name": "Write",
    "agent_id": "integration-test-agent",
    "repo": {
        "git_root": "/home/delorenj/code/test-project",
        "branch": "feature/integration-test",
        "head_sha": "abc123def456",
        "remote_url": "git@github.com:delorenj/test-project.git",
    },
    "file_path": "/home/delorenj/code/test-project/src/api/auth.py",
    "file_ext": "py",
    "lines_changed": 42,
    "raw_payload": {"tool_input": {"file_path": "/src/api/auth.py", "content": "def login():\n    pass"}},
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "source_pid": 99999,
    "correlation_id": "test-integration-001",
}


def test_enrichment_standalone():
    """Test that enrichment works correctly without the consumer."""
    from src.enrichment import enrich
    from src.models import ToolMutationEvent

    event = ToolMutationEvent(**TEST_EVENT)
    enriched = enrich(event)

    assert enriched.intent == "new-file", f"Expected 'new-file', got '{enriched.intent}'"
    assert enriched.domain == "api-layer", f"Expected 'api-layer', got '{enriched.domain}'"
    assert enriched.language == "python", f"Expected 'python', got '{enriched.language}'"
    assert "integration-test-agent" in enriched.summary
    assert "auth.py" in enriched.summary
    print("  PASS: Enrichment produces correct metadata")
    print(f"    Intent: {enriched.intent}")
    print(f"    Domain: {enriched.domain}")
    print(f"    Language: {enriched.language}")
    print(f"    Summary: {enriched.summary}")
    return enriched


def test_vector_store():
    """Test that we can store and retrieve from Qdrant."""
    from src.enrichment import enrich
    from src.models import ToolMutationEvent
    from src.vector_store import MutationVectorStore, collection_name_for_repo

    event = ToolMutationEvent(**TEST_EVENT)
    enriched = enrich(event)

    # Derive collection name
    collection = collection_name_for_repo(
        event.repo.git_root, event.repo.remote_url
    )
    print(f"  Collection name: {collection}")

    # Store
    store = MutationVectorStore()
    asyncio.run(store.store(enriched))
    print("  PASS: Stored enriched mutation in Qdrant")

    # Search
    results = store.search(
        collection=collection,
        query="authentication API changes",
        limit=5,
    )
    print(f"  Search results: {len(results)}")

    assert len(results) > 0, "Expected at least 1 search result"
    top = results[0]
    print(f"    Top result score: {top['score']:.3f}")
    print(f"    Top result summary: {top['summary'][:100]}")
    assert top["tool_name"] == "Write"
    assert top["agent_id"] == "integration-test-agent"
    assert "auth.py" in (top.get("file_path") or "")
    print("  PASS: Semantic search returns correct results")

    # Cleanup: delete the test collection
    try:
        store.client.delete_collection(collection)
        print(f"  Cleaned up test collection: {collection}")
    except Exception:
        pass

    return results


def test_consumer_processes_message():
    """Test the full consumer pipeline: RabbitMQ -> enrich -> Qdrant."""
    from src.config import settings
    from src.consumer import MutationLedgerConsumer
    from src.vector_store import MutationVectorStore, collection_name_for_repo

    collection = collection_name_for_repo(
        TEST_EVENT["repo"]["git_root"],
        TEST_EVENT["repo"]["remote_url"],
    )

    # Publish test event to RabbitMQ
    print("  Publishing test event to RabbitMQ...")
    params = pika.URLParameters(RABBIT_URL)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
    ch.basic_publish(
        exchange=EXCHANGE,
        routing_key=ROUTING_KEY,
        body=json.dumps(TEST_EVENT),
        properties=pika.BasicProperties(content_type="application/json"),
    )
    conn.close()
    print("  Published to RabbitMQ")

    # Start consumer, process one message, then stop
    print("  Starting consumer...")
    consumer = MutationLedgerConsumer()

    async def consume_one():
        await consumer.connect()
        await consumer.start()
        # Wait a bit for message processing
        await asyncio.sleep(5)
        await consumer.stop()

    asyncio.run(consume_one())
    print("  Consumer stopped")

    # Check Qdrant
    print("  Checking Qdrant for embedded mutation...")
    store = MutationVectorStore()
    results = store.search(
        collection=collection,
        query="authentication login API",
        limit=5,
    )

    assert len(results) > 0, "No results found in Qdrant after consumer processing"
    top = results[0]
    print(f"    Found: score={top['score']:.3f}")
    print(f"    Agent: {top['agent_id']}")
    print(f"    File: {top.get('file_path')}")
    print(f"    Summary: {top['summary'][:100]}")
    print("  PASS: Consumer processed event and embedded in Qdrant")

    # Cleanup
    try:
        store.client.delete_collection(collection)
        print(f"  Cleaned up: {collection}")
    except Exception:
        pass


if __name__ == "__main__":
    print("=" * 60)
    print("Layer 3 Integration Tests: mutation-ledger -> Qdrant")
    print("=" * 60)

    tests = [
        ("3a: Enrichment standalone", test_enrichment_standalone),
        ("3b: Vector store (direct)", test_vector_store),
        # ("3c: Full consumer pipeline", test_consumer_processes_message),  # requires running RabbitMQ consumer
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n[{name}]")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    sys.exit(1 if failed else 0)

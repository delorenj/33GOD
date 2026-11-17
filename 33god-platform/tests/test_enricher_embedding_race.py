"""AC-3 / AC-4: the event_embeddings parent-row race (33GOD-95).

The enricher and Candystore consume BLOODBANK_EVENTS independently, so the
enricher can try to INSERT an embedding before Candystore commits the parent
events row, which violates event_embeddings.event_id REFERENCES events(id).

Everything here runs against a fake DB (no Postgres) with an injected clock and
sleep, so the bounds are asserted exactly and deterministically.

Documented bound (see enricher/main.py): in-delivery wait EMBED_PARENT_WAIT_SECONDS
(default 20s, backoff 0.25s doubling to a 4s cap), then RETRY across at most
EMBED_PARENT_MAX_ATTEMPTS (default 3) deliveries per event id, then a dead_letter
row (reason embedding_parent_absent) and DROP. No orphan embedding is ever written.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_enricher_llm import main  # noqa: E402

EVENT_ID = "9a1f6c52-0000-4000-8000-00000000abcd"
ENV = {"PATH": "/usr/bin"}


class FakeFKViolation(Exception):
    """Stands in for psycopg2.errors.ForeignKeyViolation (SQLSTATE 23503)."""

    pgcode = "23503"


class FakeDB:
    """Just enough Postgres for the enricher: events, event_embeddings, dead_letter."""

    def __init__(self) -> None:
        self.events: set[str] = set()
        self.embeddings: dict[str, list] = {}
        self.dead_letter: list[dict] = []
        self.insert_attempts = 0
        self.connections_opened = 0
        self.connections_closed = 0
        self.fail_non_fk_once = False
        self.fail_non_fk_always = False
        self.fail_dead_letter = False

    def connect(self):
        self.connections_opened += 1
        return _FakeConn(self)


class _FakeConn:
    def __init__(self, db: FakeDB) -> None:
        self.db = db
        self.pending: list = []

    def cursor(self):
        return _FakeCursor(self)

    def commit(self) -> None:
        for apply in self.pending:
            apply()
        self.pending.clear()

    def rollback(self) -> None:
        self.pending.clear()

    def close(self) -> None:
        self.db.connections_closed += 1


class _FakeCursor:
    def __init__(self, conn: _FakeConn) -> None:
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql: str, params: tuple) -> None:
        db = self.conn.db
        if sql.startswith("INSERT INTO event_embeddings"):
            db.insert_attempts += 1
            if db.fail_non_fk_once or db.fail_non_fk_always:
                db.fail_non_fk_once = False
                raise Exception("connection reset")  # no pgcode: not a FK violation
            event_id, embedding = params
            if event_id not in db.events:
                raise FakeFKViolation("insert or update on table event_embeddings violates foreign key constraint")
            if "ON CONFLICT (event_id) DO NOTHING" in sql and event_id in db.embeddings:
                return
            self.conn.pending.append(lambda: db.embeddings.__setitem__(event_id, embedding))
        elif sql.startswith("INSERT INTO dead_letter"):
            if db.fail_dead_letter:
                raise Exception('relation "dead_letter" does not exist')
            event_id, topic, reason, error, raw = params
            self.conn.pending.append(
                lambda: db.dead_letter.append({"event_id": event_id, "topic": topic, "reason": reason, "error": error, "raw": raw})
            )
        else:  # pragma: no cover
            raise AssertionError(f"unexpected SQL: {sql}")


class FakeClock:
    """Injected in place of time.monotonic / time.sleep; sleeping advances it."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []
        self.on_sleep = None  # callable(total_slept_so_far) -> None

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds
        if self.on_sleep:
            self.on_sleep(self.now)


def _body(event_id: str = EVENT_ID) -> dict:
    return {
        "id": event_id,
        "type": "bloodbank.agent.tool.completed",
        "subject": "bloodbank.evt.agent.tool.completed",
        "correlationid": "0d8c06e8-1fbb-5e96-bf89-22564a776074",
        "data": {"tool_name": "write_file", "arguments": {"path": "/tmp/x"}, "status": "success"},
    }


class _RaceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.db = FakeDB()
        self.clock = FakeClock()
        main._embedding_attempts._counts.clear()
        main._error_attempts._counts.clear()
        patches = [
            unittest.mock.patch.object(main, "get_db", self.db.connect),
            unittest.mock.patch.object(main, "_sleep", self.clock.sleep),
            unittest.mock.patch.object(main, "_monotonic", self.clock.monotonic),
            unittest.mock.patch.dict(main.os.environ, ENV, clear=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def handle(self, body: dict | None = None) -> dict:
        return main._do_handle_tool_completed(body or _body())


class ParentArrivesLateTests(_RaceTestCase):
    """AC-3: the parent commits after the first embedding attempt."""

    def test_parent_after_first_attempt_yields_exactly_one_embedding(self) -> None:
        self.clock.on_sleep = lambda total: self.db.events.add(EVENT_ID)  # parent commits during the first backoff
        self.assertEqual(self.handle(), {"status": "SUCCESS"})
        self.assertEqual(self.db.insert_attempts, 2)  # first hit the FK, second landed
        self.assertEqual(list(self.db.embeddings), [EVENT_ID])
        self.assertEqual(self.clock.sleeps, [0.25])
        self.assertEqual(self.db.dead_letter, [])

    def test_parent_already_present_needs_no_wait(self) -> None:
        self.db.events.add(EVENT_ID)
        self.assertEqual(self.handle(), {"status": "SUCCESS"})
        self.assertEqual(self.clock.sleeps, [])
        self.assertEqual(self.db.insert_attempts, 1)

    def test_duplicate_delivery_after_success_adds_no_second_embedding(self) -> None:
        self.clock.on_sleep = lambda total: self.db.events.add(EVENT_ID)
        self.assertEqual(self.handle(), {"status": "SUCCESS"})
        first = dict(self.db.embeddings)
        # Redelivery (same event id): ON CONFLICT DO NOTHING keeps exactly one row.
        self.assertEqual(self.handle(), {"status": "SUCCESS"})
        self.assertEqual(self.handle(), {"status": "SUCCESS"})
        self.assertEqual(self.db.embeddings, first)
        self.assertEqual(len(self.db.embeddings), 1)

    def test_parent_arriving_between_deliveries_succeeds_on_redelivery(self) -> None:
        # Delivery 1: parent never shows inside the in-call wait -> RETRY (no orphan).
        self.assertEqual(self.handle(), {"status": "RETRY"})
        self.assertEqual(self.db.embeddings, {})
        # Candystore commits the parent; Dapr redelivers.
        self.db.events.add(EVENT_ID)
        self.assertEqual(self.handle(), {"status": "SUCCESS"})
        self.assertEqual(list(self.db.embeddings), [EVENT_ID])
        self.assertEqual(self.db.dead_letter, [])
        self.assertNotIn(EVENT_ID, main._embedding_attempts._counts)  # counter cleared on success

    def test_connections_are_always_closed(self) -> None:
        self.db.events.add(EVENT_ID)
        self.handle()
        self.assertEqual(self.db.connections_opened, self.db.connections_closed)


class ParentNeverArrivesTests(_RaceTestCase):
    """AC-4: the bound is respected, nothing orphaned, the failure stays visible."""

    def test_in_call_wait_respects_the_configured_bound(self) -> None:
        self.assertEqual(self.handle(), {"status": "RETRY"})
        # Default budget 20s; backoff 0.25, 0.5, 1, 2, 4, 4, 4, then the 4.25s remainder is clipped.
        self.assertEqual(self.clock.sleeps, [0.25, 0.5, 1.0, 2.0, 4.0, 4.0, 4.0, 4.0, 0.25])
        self.assertAlmostEqual(sum(self.clock.sleeps), 20.0)
        self.assertLess(sum(self.clock.sleeps), 300)  # well under the durable's ackWait
        self.assertEqual(self.db.embeddings, {})  # no orphan insert

    def test_bound_is_configurable_by_env(self) -> None:
        env = {**ENV, "EMBED_PARENT_WAIT_SECONDS": "3", "EMBED_PARENT_BACKOFF_START": "1", "EMBED_PARENT_BACKOFF_MAX": "1"}
        with unittest.mock.patch.dict(main.os.environ, env, clear=True):
            self.assertEqual(self.handle(), {"status": "RETRY"})
        self.assertEqual(self.clock.sleeps, [1.0, 1.0, 1.0])
        self.assertEqual(self.db.insert_attempts, 4)

    def test_retry_until_attempts_exhausted_then_dead_letter_and_drop(self) -> None:
        body = _body()
        # EMBED_PARENT_MAX_ATTEMPTS defaults to 3: deliveries 1 and 2 RETRY, delivery 3 DROPs.
        self.assertEqual(self.handle(body), {"status": "RETRY"})
        self.assertEqual(self.handle(body), {"status": "RETRY"})
        self.assertEqual(self.db.dead_letter, [])
        self.assertEqual(self.handle(body), {"status": "DROP"})

        self.assertEqual(self.db.embeddings, {})  # never an orphan
        self.assertEqual(len(self.db.dead_letter), 1)
        row = self.db.dead_letter[0]
        self.assertEqual(row["reason"], "embedding_parent_absent")
        self.assertEqual(row["event_id"], EVENT_ID)
        self.assertEqual(row["topic"], "bloodbank.evt.agent.tool.completed")
        self.assertEqual(json.loads(row["raw"])["id"], EVENT_ID)  # exact envelope kept for replay
        self.assertIn("3 deliveries", row["error"])
        self.assertNotIn(EVENT_ID, main._embedding_attempts._counts)

    def test_drop_is_logged_at_error(self) -> None:
        for _ in range(2):
            self.handle()
        with self.assertLogs("enricher", level="ERROR") as logs:
            self.handle()
        self.assertTrue(any("parent events row absent" in line for line in logs.output))

    def test_attempt_bound_is_configurable(self) -> None:
        env = {**ENV, "EMBED_PARENT_MAX_ATTEMPTS": "1"}
        with unittest.mock.patch.dict(main.os.environ, env, clear=True):
            self.assertEqual(self.handle(), {"status": "DROP"})
        self.assertEqual(len(self.db.dead_letter), 1)

    def test_attempts_are_tracked_per_event_id(self) -> None:
        other = "9a1f6c52-0000-4000-8000-00000000beef"
        self.assertEqual(self.handle(_body()), {"status": "RETRY"})
        self.assertEqual(self.handle(_body(other)), {"status": "RETRY"})
        self.assertEqual(main._embedding_attempts._counts[EVENT_ID], 1)
        self.assertEqual(main._embedding_attempts._counts[other], 1)

    def test_attempt_counter_is_a_bounded_lru(self) -> None:
        counter = main._AttemptCounter(size=3)
        for key in ("a", "b", "c", "d"):
            counter.bump(key)
        self.assertEqual(len(counter), 3)
        self.assertNotIn("a", counter._counts)
        counter.bump("b")  # touch b: c is now the oldest
        counter.bump("e")
        self.assertNotIn("c", counter._counts)
        self.assertEqual(counter._counts["b"], 2)

    def test_non_fk_db_error_is_retry_not_orphan_and_not_dead_lettered(self) -> None:
        self.db.fail_non_fk_once = True
        self.assertEqual(self.handle(), {"status": "RETRY"})
        self.assertEqual(self.db.dead_letter, [])
        self.assertEqual(self.db.embeddings, {})
        self.assertEqual(self.clock.sleeps, [0.5])  # short backoff, no parent wait

    def test_non_fk_db_error_is_bounded_then_dead_lettered(self) -> None:
        self.db.fail_non_fk_always = True
        statuses = [self.handle() for _ in range(5)]
        self.assertEqual([x["status"] for x in statuses], ["RETRY"] * 4 + ["DROP"])
        self.assertEqual(self.clock.sleeps, [0.5, 1.0, 2.0, 4.0])  # exponential, per delivery
        self.assertEqual(len(self.db.dead_letter), 1)
        self.assertEqual(self.db.dead_letter[0]["reason"], "embedding_db_error")
        self.assertEqual(self.db.embeddings, {})
        self.assertNotIn(EVENT_ID, main._error_attempts._counts)

    def test_embed_failure_is_bounded_then_dead_lettered(self) -> None:
        with unittest.mock.patch.object(main.model, "encode", side_effect=RuntimeError("oom")):
            statuses = [self.handle()["status"] for _ in range(5)]
        self.assertEqual(statuses, ["RETRY"] * 4 + ["DROP"])
        self.assertEqual(self.db.dead_letter[0]["reason"], "embedding_failed")
        self.assertEqual(self.db.insert_attempts, 0)

    def test_error_bound_is_configurable_and_success_resets_it(self) -> None:
        with unittest.mock.patch.dict(main.os.environ, {**ENV, "EMBED_ERROR_MAX_ATTEMPTS": "2"}, clear=True):
            self.db.fail_non_fk_once = True
            self.assertEqual(self.handle(), {"status": "RETRY"})
            self.db.events.add(EVENT_ID)
            self.assertEqual(self.handle(), {"status": "SUCCESS"})
            self.assertNotIn(EVENT_ID, main._error_attempts._counts)


class DeadLetterWriteFailureTests(_RaceTestCase):
    """DROP only once the dead_letter row exists (review of 33GOD-95)."""

    def test_failed_dead_letter_write_retries_instead_of_dropping(self) -> None:
        self.db.fail_dead_letter = True
        # Deliveries 1-2 wait for the parent; delivery 3 tries the dead_letter write and fails.
        self.assertEqual([self.handle()["status"] for _ in range(3)], ["RETRY"] * 3)
        self.assertEqual(self.db.dead_letter, [])
        self.assertEqual(main._embedding_attempts._counts[EVENT_ID], 3)  # counter kept
        # The table comes back: the next delivery records the row, then DROPs.
        self.db.fail_dead_letter = False
        self.assertEqual(self.handle(), {"status": "DROP"})
        self.assertEqual(len(self.db.dead_letter), 1)
        self.assertNotIn(EVENT_ID, main._embedding_attempts._counts)

    def test_persistently_failing_dead_letter_write_is_still_bounded(self) -> None:
        self.db.fail_dead_letter = True
        # max 3 + DEAD_LETTER_WRITE_EXTRA_ATTEMPTS 3 = 6 deliveries, the sixth DROPs.
        statuses = [self.handle()["status"] for _ in range(6)]
        self.assertEqual(statuses, ["RETRY"] * 5 + ["DROP"])
        self.assertNotIn(EVENT_ID, main._embedding_attempts._counts)


class RealDriverContractTests(unittest.TestCase):
    """The suite stubs psycopg2; pin the facts the FK handling relies on to the real driver."""

    SCRIPT = (
        "import psycopg2, psycopg2.errors as e, psycopg2.errorcodes as c;"
        "print(c.FOREIGN_KEY_VIOLATION, e.lookup(c.FOREIGN_KEY_VIOLATION) is e.ForeignKeyViolation, issubclass(e.ForeignKeyViolation, psycopg2.Error))"
    )

    def _real(self, script: str) -> subprocess.CompletedProcess:
        proc = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=60)
        if proc.returncode != 0 and "No module named" in proc.stderr:
            self.skipTest("real psycopg2 not installed")
        return proc

    def test_foreign_key_violation_sqlstate_matches_the_enricher_constant(self) -> None:
        proc = self._real(self.SCRIPT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.split(), [main.FK_VIOLATION_SQLSTATE, "True", "True"])

    @unittest.skipUnless(os.environ.get("ENRICHER_TEST_DATABASE_URL"), "set ENRICHER_TEST_DATABASE_URL for a real-Postgres check")
    def test_real_postgres_raises_the_pgcode_the_enricher_checks(self) -> None:
        script = (
            "import os, psycopg2;"
            "c = psycopg2.connect(os.environ['ENRICHER_TEST_DATABASE_URL']); cur = c.cursor();"
            "cur.execute('CREATE TEMP TABLE p (id uuid PRIMARY KEY)');"
            "cur.execute('CREATE TEMP TABLE ch (event_id uuid PRIMARY KEY REFERENCES p(id))');"
            "\ntry:\n cur.execute(\"INSERT INTO ch VALUES ('9a1f6c52-0000-4000-8000-00000000abcd')\")"
            "\nexcept psycopg2.Error as err:\n print(err.pgcode)"
        )
        proc = self._real(script)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), main.FK_VIOLATION_SQLSTATE)


if __name__ == "__main__":
    unittest.main()

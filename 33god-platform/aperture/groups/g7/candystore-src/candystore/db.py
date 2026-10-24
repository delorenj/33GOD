from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json

logger = logging.getLogger("candystore.db")

DEFAULT_DATABASE_URL = "postgresql://candystore:candystore@localhost:5432/candystore"

REQUIRED_ENVELOPE_FIELDS = (
    "id",
    "source",
    "type",
    "time",
    "producer",
    "service",
    "domain",
    "kind",
)


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def _connect():
    return psycopg2.connect(database_url())


@contextmanager
def cursor() -> Iterator[Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    """Run migrations/*.sql in lexical order."""
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    if not migrations_dir.exists():
        return

    with cursor() as cur:
        for path in sorted(migrations_dir.glob("*.sql")):
            cur.execute(path.read_text(encoding="utf-8"))


def check_connection() -> bool:
    with cursor() as cur:
        cur.execute("SELECT 1")
        return cur.fetchone() == (1,)


def insert_event(envelope: dict[str, Any], sanitized: bool = False) -> bool:
    """Insert a CloudEvents envelope.

    Returns True when a new row was inserted and False when the event ID
    already existed. Duplicate IDs are intentionally treated as success so Dapr
    does not retry already-persisted messages.

    ``sanitized`` records that the envelope had a PostgreSQL-unstorable value
    (e.g. a NUL) stripped before insert (see ``sanitize_envelope``); the caller
    is responsible for stripping — this only sets the marker column.
    """
    _validate_envelope(envelope)

    sql = """
    INSERT INTO events (
        id, specversion, source, type, subject, time, datacontenttype,
        dataschema, correlationid, causationid, producer, service, domain,
        schemaref, traceparent, kind, actor, data, ordering_key, sanitized, raw
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO NOTHING
    RETURNING id
    """
    actor = envelope.get("actor")
    data = envelope.get("data")
    params = (
        str(uuid.UUID(str(envelope["id"]))),
        envelope.get("specversion", "1.0"),
        envelope.get("source"),
        envelope.get("type"),
        envelope.get("subject"),
        envelope.get("time"),
        envelope.get("datacontenttype"),
        envelope.get("dataschema"),
        _uuid_or_none(envelope.get("correlationid")),
        _uuid_or_none(envelope.get("causationid")),
        envelope.get("producer"),
        envelope.get("service"),
        envelope.get("domain"),
        envelope.get("schemaref"),
        envelope.get("traceparent"),
        envelope.get("kind"),
        Json(actor) if actor is not None else None,
        Json(data) if data is not None else None,
        envelope.get("ordering_key"),
        sanitized,
        Json(envelope),
    )

    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone() is not None


def record_dead_letter(
    raw: bytes | str,
    *,
    reason: str,
    topic: str | None = None,
    error: str | None = None,
    event_id: str | None = None,
) -> bool:
    """Persist an event candystore refused to store, preserving the exact bytes.

    Best-effort: this MUST NOT raise. It runs on the DROP path, and a failure
    here (e.g. DB briefly down) must not turn a known-bad event back into a 500
    that Dapr redelivers forever. On failure it logs and returns False.
    """
    try:
        if isinstance(raw, bytes | bytearray):
            raw_bytes = bytes(raw)
        else:
            raw_bytes = str(raw).encode("utf-8", "replace")
        # The TEXT columns cannot hold a NUL either; strip it so recording a
        # NUL-bearing error message can never itself fail and lose the record.
        with cursor() as cur:
            cur.execute(
                "INSERT INTO dead_letter (event_id, topic, reason, error, raw) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    _no_nul(event_id),
                    _no_nul(topic),
                    _no_nul(reason),
                    _no_nul(error),
                    psycopg2.Binary(raw_bytes),
                ),
            )
        return True
    except Exception:
        logger.exception("failed to record dead_letter (reason=%s topic=%s)", reason, topic)
        return False


def _strip_nul(value: Any) -> tuple[Any, bool]:
    """Recursively strip U+0000 from strings. Postgres jsonb/text cannot store
    a NUL, so an event carrying one raises DataError and (pre-fix) poison-loops.
    Returns (clean_value, changed)."""
    if isinstance(value, str):
        return (value.replace("\x00", ""), True) if "\x00" in value else (value, False)
    if isinstance(value, dict):
        changed = False
        out: dict[Any, Any] = {}
        for key, val in value.items():
            clean_key, k_changed = _strip_nul(key)
            clean_val, v_changed = _strip_nul(val)
            out[clean_key] = clean_val
            changed = changed or k_changed or v_changed
        return out, changed
    if isinstance(value, list):
        changed = False
        out_list = []
        for item in value:
            clean_item, i_changed = _strip_nul(item)
            out_list.append(clean_item)
            changed = changed or i_changed
        return out_list, changed
    return value, False


def sanitize_envelope(envelope: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return (clean_envelope, sanitized) with every NUL char removed."""
    clean, changed = _strip_nul(envelope)
    return clean, changed


def _no_nul(value: str | None) -> str | None:
    return value.replace("\x00", "") if isinstance(value, str) else value


def _validate_envelope(envelope: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_ENVELOPE_FIELDS if not envelope.get(field)]
    if missing:
        raise ValueError(f"missing CloudEvents fields: {', '.join(missing)}")
    uuid.UUID(str(envelope["id"]))
    _validate_time(envelope["time"])


def _validate_time(value: Any) -> None:
    """Reject an unparseable timestamp at validation (→ DROP + dead_letter) so a
    bad `time` surfaces with a clear reason instead of a raw DB DataError. A
    wrongly-rejected value is still recoverable from dead_letter, so strictness
    here never means silent loss."""
    text = str(value).strip()
    normalized = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid time: {value!r}") from exc


def _uuid_or_none(val: Any) -> str | None:
    if not val:
        return None
    try:
        return str(uuid.UUID(str(val)))
    except (TypeError, ValueError, AttributeError):
        return None

"""PostgreSQL event store persistence layer."""

import json as _json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
import structlog
from asyncpg import Pool

from .config import settings
from .models import EventEnvelope, EventPersistenceResult, EventQuery, WorkflowState

logger = structlog.get_logger(__name__)


class EventStore:
    """PostgreSQL-backed event store with workflow projections."""

    def __init__(self) -> None:
        """Initialize the event store."""
        self.pool: Pool | None = None

    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL."""
        try:
            logger.info("connecting_to_postgres", url=settings.database_url)
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=5,
                max_size=settings.database_pool_size,
                max_inactive_connection_lifetime=300,
            )
            logger.info("connected_to_postgres")

            # Initialize schema if needed
            await self._initialize_schema()

        except Exception as e:
            logger.error("postgres_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("disconnected_from_postgres")

    async def _initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        if not self.pool:
            raise RuntimeError("Pool not initialized")

        async with self.pool.acquire() as conn:
            # Enable UUID extension
            await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

            # Events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id UUID PRIMARY KEY,
                    event_type VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
                    source JSONB NOT NULL DEFAULT '{}'::jsonb,
                    correlation_ids UUID[] DEFAULT '{}',
                    agent_context JSONB,
                    payload JSONB NOT NULL,
                    persisted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            # Indexes for events table (PostgreSQL: must be separate statements)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_event_type ON events (event_type);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp DESC);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_correlation_ids ON events USING GIN (correlation_ids);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_persisted_at ON events (persisted_at DESC);"
            )

            # Workflow state projections table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_state (
                    workflow_id UUID PRIMARY KEY,
                    workflow_type VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    event_count INT NOT NULL DEFAULT 0,
                    last_event_type VARCHAR(255),
                    agent_sessions TEXT[] DEFAULT '{}',
                    checkpoints TEXT[] DEFAULT '{}'
                );
            """)

            # Indexes for workflow_state table
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_state_type ON workflow_state (workflow_type);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_state_status ON workflow_state (status);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_state_updated ON workflow_state (updated_at DESC);"
            )

            logger.info("schema_initialized")

    async def persist_event(self, envelope: EventEnvelope) -> EventPersistenceResult:
        """
        Persist an event to PostgreSQL.

        Returns EventPersistenceResult indicating success/failure.
        """
        if not self.pool:
            return EventPersistenceResult(
                success=False,
                event_id=envelope.event_id,
                persisted_at=datetime.now(timezone.utc),
                error="Database pool not initialized",
            )

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Insert event
                    # asyncpg requires explicit JSON serialization for JSONB cols
                    await conn.execute(
                        """
                        INSERT INTO events (
                            event_id, event_type, timestamp, version,
                            source, correlation_ids, agent_context, payload
                        ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7::jsonb, $8::jsonb)
                        ON CONFLICT (event_id) DO NOTHING
                        """,
                        envelope.event_id,
                        envelope.event_type,
                        envelope.timestamp,
                        envelope.version,
                        _json.dumps(envelope.source) if envelope.source else "{}",
                        envelope.correlation_ids,
                        _json.dumps(envelope.agent_context) if envelope.agent_context else None,
                        _json.dumps(envelope.payload) if envelope.payload else "{}",
                    )

                    # Update workflow state projection if workflow_id present
                    if "workflow_id" in envelope.payload:
                        await self._update_workflow_state(conn, envelope)

            return EventPersistenceResult(
                success=True,
                event_id=envelope.event_id,
                persisted_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(
                "event_persistence_error",
                event_id=str(envelope.event_id),
                error=str(e),
            )
            return EventPersistenceResult(
                success=False,
                event_id=envelope.event_id,
                persisted_at=datetime.now(timezone.utc),
                error=str(e),
            )

    async def _update_workflow_state(
        self, conn: Any, envelope: EventEnvelope
    ) -> None:
        """Update workflow state projection from event."""
        workflow_id = envelope.payload.get("workflow_id")
        if not workflow_id:
            return

        workflow_type = envelope.payload.get("workflow_type", "unknown")
        status = envelope.payload.get("status", "in_progress")

        # Extract agent context
        agent_sessions = []
        checkpoints = []
        if envelope.agent_context:
            if session_id := envelope.agent_context.get("session_id"):
                agent_sessions.append(session_id)
            if checkpoint_id := envelope.agent_context.get("checkpoint_id"):
                checkpoints.append(checkpoint_id)

        await conn.execute(
            """
            INSERT INTO workflow_state (
                workflow_id, workflow_type, status,
                created_at, updated_at, event_count,
                last_event_type, agent_sessions, checkpoints
            ) VALUES ($1, $2, $3, $4, $4, 1, $5, $6, $7)
            ON CONFLICT (workflow_id) DO UPDATE SET
                status = EXCLUDED.status,
                updated_at = $4,
                event_count = workflow_state.event_count + 1,
                last_event_type = EXCLUDED.last_event_type,
                agent_sessions = array_cat(workflow_state.agent_sessions, EXCLUDED.agent_sessions),
                checkpoints = array_cat(workflow_state.checkpoints, EXCLUDED.checkpoints)
            """,
            UUID(workflow_id) if isinstance(workflow_id, str) else workflow_id,
            workflow_type,
            status,
            envelope.timestamp,
            envelope.event_type,
            agent_sessions,
            checkpoints,
        )

    async def query_events(self, query: EventQuery) -> list[EventEnvelope]:
        """Query events from the store."""
        if not self.pool:
            return []

        conditions = []
        params = []
        param_idx = 1

        if query.workflow_id:
            conditions.append(f"payload @> ${{param_idx}}")
            params.append({"workflow_id": str(query.workflow_id)})
            param_idx += 1

        if query.correlation_id:
            conditions.append(f"${param_idx} = ANY(correlation_ids)")
            params.append(query.correlation_id)
            param_idx += 1

        if query.event_type:
            if query.event_type.endswith(".*"):
                # Prefix match: agent.lenoon.* → LIKE 'agent.lenoon.%'
                prefix = query.event_type[:-1]  # strip trailing *
                conditions.append(f"event_type LIKE ${param_idx}")
                params.append(f"{prefix}%")
            else:
                conditions.append(f"event_type = ${param_idx}")
                params.append(query.event_type)
            param_idx += 1

        if query.start_time:
            conditions.append(f"timestamp >= ${param_idx}")
            params.append(query.start_time)
            param_idx += 1

        if query.end_time:
            conditions.append(f"timestamp <= ${param_idx}")
            params.append(query.end_time)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT event_id, event_type, timestamp, version,
                   source, correlation_ids, agent_context, payload
            FROM events
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([query.limit, query.offset])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        def _parse_jsonb(val: Any) -> Any:
            """asyncpg returns JSONB as str; parse back to dict."""
            if isinstance(val, str):
                return _json.loads(val)
            return val if val is not None else {}

        return [
            EventEnvelope(
                event_id=row["event_id"],
                event_type=row["event_type"],
                timestamp=row["timestamp"],
                version=row["version"],
                source=_parse_jsonb(row["source"]),
                correlation_ids=list(row["correlation_ids"]),
                agent_context=_parse_jsonb(row["agent_context"]) if row["agent_context"] else None,
                payload=_parse_jsonb(row["payload"]),
            )
            for row in rows
        ]

    async def get_workflow_state(self, workflow_id: UUID) -> WorkflowState | None:
        """Retrieve workflow state projection."""
        if not self.pool:
            return None

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT workflow_id, workflow_type, status,
                       created_at, updated_at, event_count,
                       last_event_type, agent_sessions, checkpoints
                FROM workflow_state
                WHERE workflow_id = $1
                """,
                workflow_id,
            )

        if not row:
            return None

        return WorkflowState(
            workflow_id=row["workflow_id"],
            workflow_type=row["workflow_type"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            event_count=row["event_count"],
            last_event_type=row["last_event_type"],
            agent_sessions=list(row["agent_sessions"]),
            checkpoints=list(row["checkpoints"]),
        )

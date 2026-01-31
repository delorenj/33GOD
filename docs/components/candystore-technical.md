# Candystore - Technical Implementation Guide

## Overview

Candystore is the event storage and audit trail service for the 33GOD ecosystem. It subscribes to ALL events from Bloodbank with wildcard binding, stores them in a database with full payload and metadata, and provides a REST API for querying with filters and pagination.

## Implementation Details

**Language**: Python 3.12+
**Framework**: FastAPI (async HTTP server)
**Database**: SQLite or PostgreSQL (async via SQLAlchemy)
**Message Queue**: RabbitMQ (aio-pika for async consumption)
**Package Manager**: uv

### Key Technologies

- **FastAPI**: Async REST API
- **SQLAlchemy 2.0**: Async ORM
- **aio-pika**: Async RabbitMQ client
- **Prometheus**: Metrics export
- **Alembic**: Database migrations

## Architecture & Design Patterns

### Event Consumer

```python
# src/candystore/consumer.py
import aio_pika
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

class EventConsumer:
    def __init__(self, rabbit_url: str, db: AsyncSession):
        self.rabbit_url = rabbit_url
        self.db = db

    async def start(self):
        """Subscribe to all Bloodbank events with wildcard"""
        connection = await aio_pika.connect_robust(self.rabbit_url)
        channel = await connection.channel()

        # Declare exchange (must match Bloodbank)
        exchange = await channel.declare_exchange(
            'events',
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )

        # Create durable queue for Candystore
        queue = await channel.declare_queue(
            'candystore',
            durable=True
        )

        # Bind with wildcard to receive ALL events
        await queue.bind(exchange, routing_key='#')

        # Consume with prefetch (performance)
        await channel.set_qos(prefetch_count=100)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    await self.handle_event(message)

    async def handle_event(self, message: aio_pika.IncomingMessage):
        """Store event in database"""
        import time
        start_time = time.time()

        try:
            event_data = json.loads(message.body.decode())

            event = Event(
                id=event_data.get('id'),
                event_type=event_data.get('event_type'),
                source=event_data.get('source'),
                target=event_data.get('target'),
                routing_key=message.routing_key,
                timestamp=datetime.fromisoformat(event_data['timestamp']),
                stored_at=datetime.utcnow(),
                payload=event_data.get('data', {}),
                session_id=event_data.get('session_id'),
                correlation_id=event_data.get('correlation_id'),
            )

            # Calculate storage latency
            latency_ms = (time.time() - start_time) * 1000
            event.storage_latency_ms = latency_ms

            self.db.add(event)
            await self.db.commit()

            # Update metrics
            metrics.events_stored_total.labels(
                event_type=event.event_type
            ).inc()

            metrics.storage_latency.observe(latency_ms)

        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            metrics.events_failed_total.labels(
                event_type=event_data.get('event_type', 'unknown'),
                error_type=type(e).__name__
            ).inc()
```

### Database Schema

```python
# src/candystore/models.py
from sqlalchemy import Column, String, DateTime, Float, JSON, Index
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Event(Base):
    __tablename__ = 'events'

    id = Column(String(36), primary_key=True)
    event_type = Column(String(255), nullable=False, index=True)
    source = Column(String(255), nullable=False, index=True)
    target = Column(String(255))
    routing_key = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    stored_at = Column(DateTime, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    session_id = Column(String(36), index=True)
    correlation_id = Column(String(36), index=True)
    storage_latency_ms = Column(Float)

    __table_args__ = (
        Index('idx_event_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_source_timestamp', 'source', 'timestamp'),
        Index('idx_session_timestamp', 'session_id', 'timestamp'),
    )
```

### REST API

```python
# src/candystore/api.py
from fastapi import FastAPI, Query
from typing import Optional

app = FastAPI()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": str(engine.url)
    }

@app.get("/events")
async def query_events(
    session_id: Optional[str] = None,
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    target: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Query events with filters and pagination"""
    query = select(Event)

    # Apply filters
    if session_id:
        query = query.where(Event.session_id == session_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    if source:
        query = query.where(Event.source == source)
    if target:
        query = query.where(Event.target == target)
    if start_time:
        query = query.where(Event.timestamp >= start_time)
    if end_time:
        query = query.where(Event.timestamp <= end_time)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.order_by(Event.timestamp.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "events": [e.to_dict() for e in events],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total
    }

@app.get("/events/{event_id}")
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    """Get single event by ID"""
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(404, "Event not found")

    return event.to_dict()
```

### Prometheus Metrics

```python
# src/candystore/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Event metrics
events_received_total = Counter(
    'candystore_events_received_total',
    'Total events received from Bloodbank',
    ['event_type', 'source']
)

events_stored_total = Counter(
    'candystore_events_stored_total',
    'Total events successfully stored',
    ['event_type']
)

events_failed_total = Counter(
    'candystore_events_failed_total',
    'Total event storage failures',
    ['event_type', 'error_type']
)

# Performance metrics
storage_latency = Histogram(
    'candystore_storage_latency_seconds',
    'Event storage latency',
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0]
)

storage_latency_gauge = Gauge(
    'candystore_storage_latency_milliseconds',
    'Current storage latency'
)

# System metrics
consumer_connected = Gauge(
    'candystore_consumer_connected',
    'Consumer connection status (1=connected)'
)

database_connections = Gauge(
    'candystore_database_connections',
    'Active database connections'
)

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        generate_latest(),
        media_type='text/plain'
    )
```

## Configuration

```bash
# Environment variables
RABBIT_URL=amqp://guest:guest@localhost:5672/
DATABASE_URL=sqlite+aiosqlite:///./candystore.db
# Or PostgreSQL: postgresql+asyncpg://user:pass@localhost:5432/candystore

API_HOST=0.0.0.0
API_PORT=8683

LOG_LEVEL=INFO
LOG_FORMAT=json  # or 'console'

METRICS_ENABLED=true
METRICS_PORT=9090

PREFETCH_COUNT=100
BATCH_SIZE=50
```

## Integration Points

### Query from Candybar

```typescript
// In Candybar dashboard
const response = await fetch(
    'http://localhost:8683/events?session_id=abc-123&limit=100'
);

const { events, total } = await response.json();
```

### Event Storage Flow

```
WhisperLiveKit → Bloodbank → Candystore → PostgreSQL
                              ↓
                           Candybar (via REST API)
```

## Performance

- **Storage Latency**: <100ms per event (target: 10-50ms)
- **Query Latency**: <200ms (with indexes)
- **Throughput**: 1000+ events/second
- **Database Size**: ~1KB per event

## Related Components

- **Bloodbank**: Event source (RabbitMQ wildcard subscription)
- **Holyfields**: Event schema validation
- **Candybar**: Visualization client (queries Candystore API)

---

**Quick Reference**:
- Port: 8683 (API), 9090 (metrics)
- CLI: `uv run candystore serve`
- Docs: `README.md`

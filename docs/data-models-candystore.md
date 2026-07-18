# Candystore Data Models

## `events`

The PostgreSQL `events` table uses event UUID as primary key. Required columns project `specversion`, `source`, `type`, `time`, `producer`, `service`, `domain`, and `kind`. Optional columns include subject, schema references, correlation/causation IDs, trace, actor, data, and ordering key. `received_at`, JSONB `raw`, and `sanitized` preserve ingestion context.

Thirteen secondary indexes support time/type/domain/correlation/producer/service queries, actor CLI extraction, common composites, and JSONB data search. There are no foreign keys, append-only enforcement, partitions, retention rules, or indexes for several causal/derived fields.

## `dead_letter`

`dead_letter` uses `BIGSERIAL` identity and stores optional event ID/topic/error, required reason/raw bytes/receive time, and reason/time indexes. The `topic` value is currently the HTTP callback route, not the broker topic. No uniqueness or replay state exists.

## Normalization Behavior

NUL characters are recursively removed before JSONB insertion and the row is marked sanitized; original bytes are separately dead-lettered. Key collisions can occur after sanitation, and the two writes are not atomic. Invalid correlation IDs become SQL null while remaining in JSONB.

## Migration Model

Every SQL file runs lexically on each startup in one transaction. Current files are idempotent, but there is no ledger, checksum, downgrade, explicit lock, or separate deploy migration step.

## Consistency Limits

UUID conflict means duplicate regardless of payload. Count/page queries are separate statements. Raw JSON is parsed and serialized, so exact input bytes are retained only in dead letter for rejected/sanitized cases.

Lifecycle rows in `events` are immutable history/read-model inputs, not the
operational lifecycle store. A Candystore projection may lag, be rebuilt, or be
unavailable without transferring single-writer authority from Lifecycle.

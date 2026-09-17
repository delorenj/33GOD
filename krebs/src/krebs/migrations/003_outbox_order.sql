-- Historical rows receive a stable backfill order; their original insertion
-- order was not retained. New rows always receive monotonic publication order.
ALTER TABLE krebs.outbox ADD COLUMN IF NOT EXISTS sequence bigint GENERATED ALWAYS AS IDENTITY;
CREATE INDEX IF NOT EXISTS krebs_outbox_pending_sequence ON krebs.outbox(sequence) WHERE published_at IS NULL;

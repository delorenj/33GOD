CREATE SCHEMA IF NOT EXISTS krebs;
CREATE TABLE IF NOT EXISTS krebs.boards (
 project_id text PRIMARY KEY, board_id text UNIQUE NOT NULL,
 revision bigint NOT NULL DEFAULT 0, generation bigint NOT NULL DEFAULT 0,
 active jsonb, tickets jsonb NOT NULL DEFAULT '{}', pending text
);
CREATE TABLE IF NOT EXISTS krebs.commands (
 command_id text PRIMARY KEY, idempotency_key text UNIQUE NOT NULL,
 project_id text NOT NULL, body jsonb NOT NULL, digest text NOT NULL,
 receipt jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS krebs.intents (
 command_id text PRIMARY KEY REFERENCES krebs.commands(command_id),
 project_id text NOT NULL, plan jsonb NOT NULL, sent boolean NOT NULL DEFAULT false,
 verified boolean NOT NULL DEFAULT false, error text, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS krebs.history (
 id bigserial PRIMARY KEY, project_id text NOT NULL, command_id text NOT NULL,
 receipt jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS krebs.outbox (
 id text PRIMARY KEY, subject text NOT NULL, envelope jsonb NOT NULL,
 published_at timestamptz, attempts integer NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS krebs.reviews (
 id text PRIMARY KEY, project_id text NOT NULL, ticket_id text NOT NULL,
 generation bigint NOT NULL, actor_id text NOT NULL, run_id text NOT NULL,
 evidence jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);

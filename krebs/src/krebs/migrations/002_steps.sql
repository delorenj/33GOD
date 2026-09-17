ALTER TABLE krebs.boards ADD COLUMN IF NOT EXISTS used_runs jsonb NOT NULL DEFAULT '[]';
ALTER TABLE krebs.intents ADD COLUMN IF NOT EXISTS launch_attempted boolean NOT NULL DEFAULT false;
ALTER TABLE krebs.intents ADD COLUMN IF NOT EXISTS launch_confirmed boolean NOT NULL DEFAULT false;
ALTER TABLE krebs.intents ADD COLUMN IF NOT EXISTS stopped boolean NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS krebs.provider_steps (
 command_id text REFERENCES krebs.commands(command_id), step_id text,
 action jsonb NOT NULL, binding jsonb NOT NULL, sent boolean NOT NULL DEFAULT false,
 verified boolean NOT NULL DEFAULT false, observed jsonb,
 PRIMARY KEY(command_id,step_id)
);
ALTER TABLE krebs.provider_steps ADD COLUMN IF NOT EXISTS authorized boolean NOT NULL DEFAULT false;

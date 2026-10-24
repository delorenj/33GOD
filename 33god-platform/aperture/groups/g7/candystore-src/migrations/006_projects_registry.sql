-- A projection of the PJangler project registry.
--
-- `project_dir_map` (005) only knows slugs that have events. The picker has to
-- list the registry, including a project with no activity yet -- otherwise a
-- freshly created project is unselectable until something happens in it, which
-- is exactly when you want to go looking.
--
-- Why a projection and not a live read: `pjangler` is not installed in the
-- app container and should not be. The registry lives on the host, so
-- `mise run project:sync` runs there and writes both this table and the
-- directory map; the API then answers from Postgres alone. That also means
-- /projects cannot hang on a subprocess.
--
-- Purely additive, like 005 -- safe under init_schema() replaying every
-- migration on every boot (candystore/db.py; no ledger yet, CANDYS-24).

CREATE TABLE IF NOT EXISTS projects (
    slug          TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    repo_path     TEXT NOT NULL,
    -- The board prefix (CANDYS, JIMB, BB). Empty for a project with no ticket
    -- provider -- `docsidian` really is like this in the live registry, so an
    -- empty string is data, not a defect.
    ticket_prefix TEXT NOT NULL DEFAULT '',
    synced_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

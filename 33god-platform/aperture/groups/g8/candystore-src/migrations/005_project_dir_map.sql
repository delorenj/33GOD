-- Resolve a working directory to a PJangler registry project.
--
-- Why a table and not a generated column: the answer depends on the registry,
-- and a GENERATED expression may only reference its own row. Why a table and
-- not a correlated subquery at query time: measured on the live table, the
-- correlated longest-prefix version took 141 s over 886k rows. And why it is
-- cheap: there are only 718 distinct working directories across all 886,023
-- rows, so this is a 718-row lookup problem wearing an 886k-row disguise.
--
-- The map is data, not schema. A new project, or a new worktree of an existing
-- one, is an INSERT performed by `mise run project:sync` -- never a migration
-- and never a code change.
--
-- Unresolved directories are stored with slug IS NULL rather than omitted. An
-- absent row and an unresolvable row are different facts, and only one of them
-- means "the ladder needs another rung". Keeping them makes the gap queryable:
--   SELECT work_dir, seen FROM project_dir_map WHERE slug IS NULL ORDER BY seen DESC;
--
-- Purely additive: CREATE TABLE IF NOT EXISTS rewrites nothing, so unlike
-- 004_search_caps.sql this file needs no early-return guard to survive
-- init_schema() replaying it on every container boot (see candystore/db.py --
-- there is still no schema_migrations ledger, CANDYS-24).

CREATE TABLE IF NOT EXISTS project_dir_map (
    work_dir    TEXT PRIMARY KEY,
    slug        TEXT,
    -- Which rung of the ladder answered, so a wrong assignment is traceable to
    -- the rule that made it rather than being indistinguishable from a guess.
    rule        TEXT NOT NULL,
    -- Event count at last sync. Not authoritative -- it exists so the
    -- unresolved list can be read worst-first without re-scanning events.
    seen        BIGINT NOT NULL DEFAULT 0,
    resolved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- The query direction is slug -> the handful of directories under it, which is
-- how `?project=<slug>` expands into a work_dir IN (...) list.
CREATE INDEX IF NOT EXISTS idx_project_dir_map_slug ON project_dir_map(slug);

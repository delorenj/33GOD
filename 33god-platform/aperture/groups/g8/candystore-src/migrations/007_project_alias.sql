-- Resolve a project by NAME as well as by directory.
--
-- 005/006 resolve a project from the working directory an agent was in. That
-- covers agent traffic and misses the entire PM lens: measured over 7 days,
-- ZERO of the 1,100+ repo.task.* / repo.decision.* / repo.board.* rows carry a
-- working_directory at all -- they arrive from the Plane webhook and from PM
-- agents, neither of which has a filesystem. So "pick a project, click PM",
-- which is the whole point of the feature, returned nothing.
--
-- What those rows do carry is `data.repo` (present on 1,102 of 1,109), holding
-- a repo NAME rather than a registry slug: `33god`, `bloodbank`, `james-brennan`.
-- Two of those are not their project's slug -- 33god is `project` and bloodbank
-- is `bb` -- so a name needs translating, which is what this table does.
--
-- Aliases are generated from the registry by `mise run project:sync`, never
-- hand-written: slug, repo directory name, and display name. Adding a project
-- adds its aliases; there is nothing to maintain separately and nothing to
-- drift.
--
-- Purely additive, like 005 and 006 -- safe under init_schema() replaying every
-- migration on every boot.

CREATE TABLE IF NOT EXISTS project_alias (
    alias TEXT PRIMARY KEY,
    slug  TEXT NOT NULL,
    -- Which registry field produced this alias, so an ambiguous or surprising
    -- match is traceable rather than mysterious.
    source TEXT NOT NULL
);

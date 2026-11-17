# 33GOD git hooks

Versioned repo hooks. `mise` runs `.githooks/install.sh --quiet` on directory
enter, which symlinks `.git/hooks/pre-commit` to `.githooks/pre-commit`. The
fleet-wide guard (`~/.config/git/hooks/pre-commit`, via the global
`core.hooksPath`) runs first and chains to it. Do not set a repo-level
`core.hooksPath`: that would bypass the fleet guard.

## pre-commit (dispatcher)

| gate | fires when staged | does |
|---|---|---|
| Aperture charter | `aperture/` | requires a fresh (<4h) `.aperture/charter-session` marker |
| Atlas (I-12) | `33god-platform/components/`, `components.yaml`, `atlas/`, `scripts/atlas.py` | re-renders the Atlas into the same commit, then runs `atlas.py check` (schema + public scrub) |

The Atlas gate is the commit-time half of drift control. The scheduled half is
the `atlas-drift` candybar (`.candybars/atlas-drift.candybar.toml`), which runs
`33god-platform/scripts/atlas-drift.sh`: it compares the registry with the
running system (evidence anchors, unregistered surfaces, status), heals what is
mechanical and files one ticket for the rest.

Install by hand: `bash .githooks/install.sh`.

## commit-msg (not installed)

Legacy ticket-reference guard. The fleet guard only chains pre-commit, so this
hook never runs; it is kept for reference.

# Mac skill catalog: re-clone made and REVERTED (2026-11-15, late evening)

## What happened

To make the Mac's catalog updatable with git, the orchestrator replaced `~/code/skillex/all-skills` with a full clone of `delorenj/skills`, at about 22:10 EST, and cherry-picked Damian's 5 skill commits on top. It also left a full `delorenj/skills` clone at `~/33god-migration/2026-11-15/skills-upstream`; the W1-3 imports came from it.

That was wrong. **Jarad's skills are private.** Jarad curated and packaged Damian's set himself, as `skills.tar.gz` (`~/skills.tar.gz` on the Studio, 2026-10-28), and copied it over by scp. The "untracked" tree inside the checkout *is* that curated install, sitting over the old gitdir on purpose. It is not a half-finished move.

## Revert (same night)

- **Removed:** the full clone at `~/code/skillex/all-skills` and its absorbed gitdir. The `skills-upstream` clone is deleted.
- **Restored, byte for byte:** the curated tree (`all-skills.old-tree`) and its original gitdir, both from `~/.config/33god/config-backups/20261116T031046Z-all-skills-reclone/`.
- **Restored:** the two untracked leftovers.
- **Restored:** `~/code/skillex` main, back on Damian's own 4 commits (`08a7a8b`).
- **Kept:** the 17 W1-3 imports. They live in the curated tree, and they are the option-B skills Jarad picked.

Result after the revert:

| Check | Result |
|---|---|
| Entries in `all-skills` | 358 (curated) |
| `skillex sync --scope global` | 60 skills, exit 0 |
| `skillex status` | exit 0 |
| Candybar `mac-skillex-hermes-resync` | success, 6/6 synced, `catalog_commit c281845` |
| All 6 desks, `profile show` | exit 0 |
| Dangling links | 0 |
| Team-inbox gateway | 200 |

## Still on the Mac from that night (kept)

- `gitmark.checkpoint false` on `~/code/33GOD`, `~/code/skillex` and `~/code/skillex/all-skills`.

## Rule

Damian's catalog changes only through a new curated `skills.tar.gz` from Jarad. Never `git pull`, `git clone` or `skillex import` from `delorenj/skills` on his Mac.

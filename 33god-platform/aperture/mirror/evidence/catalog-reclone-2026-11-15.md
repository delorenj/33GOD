# Mac skill catalog re-cloned onto delorenj/skills (2026-11-15, late evening)

Executor: Claude Code orchestrator on big-chungus over SSH (`hellosubconscious@100.117.109.60`), under Jarad's handover ("button it up", untagged, 2026-11-15).

## What was wrong

The independent verify pass refuted "nothing reads `~/code/skillex`". Every link in `~/.agents/skills` and in every desk resolves into `~/code/skillex/all-skills`, and the Candybar resync uses it as `registry_root`. That checkout was not what it looked like:

- Its gitdir (`~/code/skillex/.git/modules/all-skills`) tracked **`delorenj/00_ceiling`**, an old public repo last pushed 2026-07-07, not `delorenj/skills`.
- HEAD was `c281845`, which is 5 local commits by Damian on top of `00_ceiling` (coaching-practice-catalog, org-chart, its routing update, parallel-work-coordinator and mission-control-reporter).
- The index had 1608 staged deletions. The working tree held a `delorenj/skills` copy from around 2026-11-03 as 4012 untracked files. That is the leftover of the 2026-10-28 and 11-03 catalog move.
- Result: the catalog could not be updated with git, and the resync's `catalog_commit` (`c281845`) described the wrong repo.

The parent `~/code/skillex` was 4 ahead and 75 behind. The 4 ahead were Damian's commits: the `hello-subconscious-coaching` pack plus three all-skills pointer bumps. It also had an untracked self-loop symlink `skillex -> skillex` and an empty `all-skills.failed-20261028-135100/`.

## What was done

Everything was backed up first to `~/.config/33god/config-backups/20261116T031046Z-all-skills-reclone/` on the Mac:

- `all-skills-tree.tgz` (the whole old tree);
- `all-skills-local.bundle` (every ref of the old repo);
- `all-skills.old-tree/` (the old directory itself, moved, not deleted);
- `git-modules-all-skills/` (the old gitdir);
- the stray `skillex` symlink and the empty failed dir.

Steps:

1. **Fresh catalog:** cloned `https://github.com/delorenj/skills.git` (public) at the skillex pin `0a891e8` onto local branch **`damian-local`**. Cherry-picked Damian's 5 skill commits on top (`d7add4f`, `aa313e4`, `e7e6e83`, `d2ccbfa`, `1cab875`); his authorship is kept and none of them conflicted.
2. **Damian-only content carried over:** `rsync --ignore-existing` copied 38 untracked paths that exist only in the old tree. Examples are `ep133-music-lab`, `participant-agent-onboarding`, his `civilwar-letterifier` outputs and `.env.local`, and skills since retired upstream. Upstream versions win for tracked files: the old copies were only older revisions.
3. **Swap and gitdir:** swapped the directories, then ran `git submodule absorbgitdirs`. The submodule URL is now `delorenj/skills`.
4. **Parent repo:** `~/code/skillex` main was reset onto `origin/main` (`39fde58`, 0.4.7 source). The coaching pack was re-added and the catalog pointer set to `1cab875` in one Damian-authored commit, `5120fdc`. Main is ahead 1 and that commit is never pushed. The old 4 commits are on branch `mac-local-pre-rebase-20261116T031317Z`.
5. **Pull-only clones:** `gitmark.checkpoint false` is set on `~/code/33GOD`, `~/code/skillex` and `~/code/skillex/all-skills` (GitMark `e4a0307` adds the opt-out). Damian has pull-only access, so checkpoint commits there could only diverge.

## Proof

| Check | Result |
|---|---|
| `skillex status --scope global` | exit 0 after one `skillex sync --scope global` (pending change was only `write-receipt`) |
| `profile show`, 6 desks (incl. team-inbox) | all exit 0 |
| Candybar `mac-skillex-hermes-resync` manual run | success in 11.0 s, exit 0; `last.json` status ok, synced 6/6, error 0, `catalog_commit 1cab875` |
| Dangling links in `~/.agents/skills` + desk skill dirs | 0 |
| Damian's skills present | `ep133-music-lab`, `participant-agent-onboarding`, `org-chart`, `mission-control-reporter` |
| team-inbox gateway | `:8642/health` 200 |
| `clients-check.py` | 14 PASS, 1 N/A (Claude Desktop not installed) |

## Updating the catalog later

```sh
cd ~/code/skillex/all-skills && git fetch origin && git rebase origin/main   # Damian's 5 commits stay on top
cd ~/code/skillex && git add all-skills && git commit -m "chore(mac): bump catalog"
```

Then `skillex sync --scope global`. The 15-minute Candybar resync brings the desks along.

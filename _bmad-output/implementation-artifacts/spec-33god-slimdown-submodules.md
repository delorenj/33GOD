---
title: 'GOD-41 Slimdown 33GOD metarepo to Blood Bank focus'
type: 'chore'
created: '2026-04-19'
status: 'ready-for-dev'
context:
  - docs/GOD.md
  - services/registry.yaml
  - ~/d/Inbox/TASKS/01_33god_repo_slimdown_submodules.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The 33GOD metarepo tracks 13 submodules, most of which are higher-level components not on the Blood Bank event backbone path. Their combined working tree, docs, and compose wiring create context noise that blocks focused work on the Blood Bank subsystem (bloodbank, holyfields, candystore, candybar).

**Approach:** Remove 9 non-Blood-Bank submodules from the metarepo (deinit, git rm, purge `.git/modules/*`), keeping them as independent repos. Update metarepo-level configs (compose.yml, AGENTS.md, mise.toml, components.toml) to stop referencing removed components. Leave `services/` folder untouched — its registry is topology, not implementation. Preserve all work on remote branches before any destructive op.

## Boundaries & Constraints

**Always:**
- Preserve all uncommitted work to remote branches/tags before deinit
- Retain bloodbank, candybar, candystore, holyfields submodules exactly as-is
- Leave `services/` folder and `services/registry.yaml` content untouched (topology survives; dependent services go dormant, not deleted)
- Leave `huuk/` directory alone on main (not tracked on main, orphan from side branch)
- Ticket prefix on branch + commits: `GOD-41`
- All ops reversible via `pre-slimdown-2026-04-19` tag

**Ask First:**
- Any request to delete files/content inside retained submodules (bloodbank, candybar, candystore, holyfields) — out of scope
- Removal of `services/theboard-meeting-trigger` service code — orthogonal
- Updating `services/registry.yaml` to drop theboard-* service entries — orthogonal

**Never:**
- Force-push, `--no-verify`, or bypass pre-commit/commit-msg hooks
- `git add -A` at metarepo level (use explicit paths; secrets scan already done in preservation phase)
- Delete remote branches of any removed submodule (their repos stay independent)
- Touch the current `GOD-38/amqp-reconnection-logic` branch or its history

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Remove submodule with clean tree | submodule clean, synced to origin | deinit + git rm + rm -rf .git/modules/$name succeeds | — |
| Remove submodule with dirty tree | submodule has uncommitted work | HALT and preserve to remote branch before deinit | STOP-AND-REPORT (already handled for HeyMa, bloodbank in Phase 0) |
| Remove submodule missing from .gitmodules | gitlink in index without mapping | `git rm --cached $path` removes gitlink | treat as already half-removed; skip deinit step |
| Dangling ref in metarepo file | compose.yml/AGENTS.md/mise.toml/components.toml mentions removed component | Remove or comment out the reference | — |
| Dangling ref in retained submodule internals | e.g. candybar/docs mentions theboard | Leave untouched (not metarepo scope) | — |
| Dependent services/ directory exists | e.g. services/theboard-meeting-trigger | Leave code and registry entry untouched | flag in SLIMDOWN_NOTES as follow-up |
| Rollback needed | any irrecoverable error | `git reset --hard pre-slimdown-2026-04-19` + restore submodules | user-triggered only |

</frozen-after-approval>

## Code Map

- `/home/delorenj/code/33GOD/.gitmodules` -- submodule registry; edit to drop 9 entries
- `/home/delorenj/code/33GOD/.git/config` -- runtime submodule config; cleaned by `git submodule deinit`
- `/home/delorenj/code/33GOD/.git/modules/` -- per-submodule internal git dirs; rm -rf for removed ones
- `/home/delorenj/code/33GOD/compose.yml` -- holocene service block (lines 359-410) references removed submodule; historical theboard-* comments are fine
- `/home/delorenj/code/33GOD/AGENTS.md` -- 7 component sections describing removed submodules
- `/home/delorenj/code/33GOD/mise.toml` -- holocene tasks (build/deploy/dev) + COMPONENTS arrays
- `/home/delorenj/code/33GOD/components.toml` -- 7 submodule entries to remove
- `/home/delorenj/code/33GOD/services/registry.yaml` -- leave intact; dependent services dormant
- `/home/delorenj/code/33GOD/SLIMDOWN_NOTES.md` -- new audit-trail doc at repo root

## Tasks & Acceptance

**Execution:**
- [ ] `.gitmodules` -- remove entries: agent-forge, holocene, iMi, jelmore, HeyMa, theboard, theboardroom, zellij-driver, TonnyBox -- keep only bloodbank, candybar, candystore, holyfields
- [ ] `git submodule deinit -f <name>` for each of: agent-forge, holocene, iMi, jelmore, HeyMa, theboard, theboardroom, zellij-driver, TonnyBox -- detach worktrees
- [ ] `git rm -f <name>` for each of those 9 -- drop gitlinks from index
- [ ] `rm -rf .git/modules/<name>` for each of those 9 -- purge internal submodule metadata
- [ ] `compose.yml` -- delete `holocene:` service block (lines ~359-410) and its `API_CORS_ORIGINS` holocene entry on line 333 -- rationale: component no longer present in tree
- [ ] `AGENTS.md` -- remove sections for: agent-forge, holocene, theboard, theboardroom, HeyMa, jelmore, zellij-driver -- keep bloodbank/candybar/candystore/holyfields sections intact
- [ ] `mise.toml` -- drop `holocene` from COMPONENTS arrays; delete holocene:build/deploy/dev task blocks -- rationale: mise tasks would fail on missing dir
- [ ] `components.toml` -- remove 7 submodule entries; retain only bloodbank/candybar/candystore/holyfields rows
- [ ] `SLIMDOWN_NOTES.md` -- new file documenting: removals list, preservation artifacts (branches/tags per remote), retained submodules, rollback command, follow-up risks (services/theboard-*, huuk orphan), links to GOD-40 epic and GOD-41..45 stories

**Acceptance Criteria:**
- Given the slimdown branch is checked out, when `git submodule status --recursive` runs, then only bloodbank, candybar, candystore, holyfields appear
- Given `.gitmodules` is read, when parsed, then it contains exactly 4 submodule blocks matching the retained set
- Given `ls .git/modules/`, when listed, then only retained submodules' directories exist
- Given any metarepo file at root (not inside a submodule) is grepped for removed component names, when searched, then zero active (non-comment, non-historical) references remain in compose.yml/AGENTS.md/mise.toml/components.toml
- Given the preservation phase completed, when checking origin remotes for HeyMa and bloodbank, then `wip/transcribe-preservation-2026-04-19` and `v3-refactor` + `pre-preservation-2026-04-19` tag are present
- Given metarepo rollback is needed, when running `git reset --hard pre-slimdown-2026-04-19`, then the pre-slimdown metarepo state is restored exactly
- Given Plane is queried for GOD-41, when state is checked, then it is `In Progress` and will transition to `Done` on PR merge

## Verification

**Commands:**
- `git submodule status --recursive` -- expected: 4 entries (bloodbank, candybar, candystore, holyfields) with no errors
- `cat .gitmodules | grep -c '^\[submodule'` -- expected: `4`
- `ls .git/modules/` -- expected: exactly bloodbank, candybar, candystore, holyfields
- `rg -n '\b(agent-forge|holocene|iMi|jelmore|HeyMa|theboard|theboardroom|zellij-driver|TonnyBox)\b' compose.yml AGENTS.md mise.toml components.toml` -- expected: zero matches (or only in comments explicitly marked historical)
- `git status` -- expected: clean working tree after commit on GOD-41/slimdown-blood-bank-focus
- `git log --oneline -5` -- expected: single new commit with GOD-41 prefix on top

**Manual checks:**
- SLIMDOWN_NOTES.md exists at repo root and documents all 9 removals with preservation locations
- Plane GOD-41 status advanced to In Progress (already done); will transition to Done on PR merge

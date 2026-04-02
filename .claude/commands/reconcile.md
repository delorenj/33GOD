Perform a **submodule reconciliation** (fold-to-trunk): merge all submodule feature branches into their `main` trunks, then update the parent repo's submodule pointers to reference `main` HEAD.

## Procedure

### Phase 1: Assess

For every initialized git submodule, collect:
- Current branch (or DETACHED)
- Dirty file count
- Commits ahead of `origin/main`
- Commits behind `origin/main`

Categorize each submodule into one of:
| Category | Condition | Action |
|----------|-----------|--------|
| **Skip** | Already at `main` HEAD | No-op |
| **Push only** | On `main`, ahead, 0 behind | `git push origin main` |
| **Fast-forward** | Ahead only (0 behind) | Checkout main, merge --ff-only, push |
| **Diverged** | Both ahead and behind | Checkout main, pull, merge, push |
| **Behind only** | 0 ahead, N behind | Checkout main, pull |
| **Dirty** | Uncommitted changes | **STOP. Ask the user what to do.** |
| **Uninitialized** | Not cloned | Skip |

Present the categorized plan as a table and **wait for user confirmation** before executing.

### Phase 2: Execute (fast-forward group first)

1. **Fast-forward submodules**: For each, note the current HEAD hash, checkout `main`, `git merge --ff-only <hash>`, push. If ff fails (local main diverged from origin), pull main first with `--rebase`, then merge the hash, then push.

2. **Diverged submodules**: For each, note the current HEAD hash, checkout `main`, `git pull origin main`, `git merge <hash> --no-edit`. If merge conflicts arise:
   - Inspect the conflict
   - Apply reasonable resolution (prefer newer content, prefer retirement notices over stale docs)
   - If the conflict is non-trivial or ambiguous, **STOP and ask the user**
   - After resolution: `git add`, commit, push

3. **Behind-only submodules**: Checkout `main`, pull.

4. **Push-only submodules**: Push main.

Use `ALLOW_NO_TICKET=1` environment variable for commit/push operations since this is maintenance, not feature work.

### Phase 3: Update parent repo

1. Run `git submodule foreach` to ensure every submodule is on `main` and pulled to latest.
2. Verify final state: print table of `name: branch @ short-hash` for all submodules.
3. Stage only the changed submodule pointer files (not unrelated dirty files).
4. Commit with message: `chore: submodule reconciliation -- fold all feature branches to main`
5. Include a summary of what was merged in the commit body.
6. Push the parent repo.

### Phase 4: Report

Print a final summary table with columns: Action, Submodules, Result.

Retain the reconciliation event in hindsight memory for the 33GOD bank.

## Arguments

$ARGUMENTS

If no arguments provided, reconcile all submodules. If arguments provided, interpret them as a filter (e.g., specific submodule names or a flag like `--dry-run` to only show the plan without executing).

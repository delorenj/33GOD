---
name: worktrees
description: 33GOD fleet policy for git worktrees — WHEN to create one, WHERE it must live (repo/.worktrees via worktrunk), and how to MAINTAIN it (constant rebases onto main, land-or-delete at task end). Use before starting any non-trivial task in any 33GOD repo, whenever two agents could touch the same checkout, when deciding whether work belongs on main directly or in a worktree, and when auditing or cleaning up stale worktrees. Command mechanics live in the `worktrunk` skill; this skill is the law.
---

# 33GOD worktree policy

The fleet runs many agents against the same repos. The main checkout of every repo is **shared infrastructure** — Hermes PMs, hooks, systemd units, and other agents all read from it. Two agents working in the same path step on each other; worktrees are how we prevent that. `wt` (worktrunk) is the only sanctioned tool for managing them — see the `worktrunk` skill for the HOW.

## The three rules

### 1. WHEN — default to a worktree

Create a worktree for any task that is more than a trivial, immediately-committed change:

- **Any ticket-sized work** (bug, feature, story) in any repo — one worktree per ticket, named after it.
- **Anything long-running** — multi-step refactors, migrations, BMAD builds. If the task outlives one tool call, it gets a worktree.
- **Anything another agent might collide with** — and you cannot know it won't. Assume parallel work exists.
- **Anything experimental** you might abandon — a worktree you delete costs nothing; a polluted shared checkout costs the next agent.

Work directly on the main checkout **only** for trivial, atomic changes you commit and push in the same breath (typo, version bump, one-line config). The global "always commit and push" rule still applies everywhere — worktrees change *where* you work, not *whether* you land it.

### 2. WHERE — `repo/.worktrees/`, no exceptions

Worktrees live **inside their own repo** at `<repo>/.worktrees/<branch>`. This is enforced by the fleet-wide worktrunk config (`~/.config/worktrunk/config.toml`), so plain `wt switch -c <branch>` already does the right thing. `.worktrees/` is machine-wide gitignored.

Forbidden:

- **Sibling directories** (`../repo.feature`) — scatter across `~/code`, invisible to repo-local tooling.
- **Central hubs** (`~/worktrees/…`) — divorces the worktree from its repo; nobody finds them again.
- **Ad-hoc paths an agent invent on the spot** — if `wt list` in the repo can't see it, it doesn't exist as far as the fleet is concerned.

Audit with `wt list` from the repo root. If you find a stray worktree elsewhere, re-home it: `wt step relocate`, or remove it and recreate properly.

### 3. MAINTAIN — rebase constantly, die young

A worktree is a short-lived staging area, not a home.

- **Rebase onto main at every natural checkpoint**: session start, after any `git fetch` shows main moved, before opening a PR, and before `wt merge`. The command is `wt step rebase` (run inside the worktree). Conflicts caught at commit 3 are trivial; conflicts caught at commit 60 are a lifestyle.
- **Push constantly.** A commit that exists only in a local worktree is queued for loss — the global checkpointing rule applies with double force inside `.worktrees/`.
- **Land or delete at task end.** The moment the task is done: `wt merge main` (squash, rebase, fast-forward, push, cleanup in one shot) or push + PR then `wt remove`. A worktree that survives its task is tech debt with a heartbeat.
- **Prune routinely.** `wt step prune` removes worktrees whose branches are already merged. Run it whenever `wt list` shows more history than future.
- **Fleet sweep:** `wt step for-each` runs a command in every worktree — e.g. rebase them all after a big main movement.

## Branch naming

`<ticket-or-type>-<slug>`, e.g. `33GOD-412-worktree-policy` or `fix-bloodbank-reconnect`. Slashes are fine (`feat/auth`); they sanitize to `-` in the directory name. One branch = one worktree = one task. Never reuse a merged branch for a new task — cut a fresh one.

## Hard don'ts

- **Never two agents in the same worktree.** If you didn't create it, don't work in it — `wt switch -c` your own.
- **Never commit `.worktrees/` content into the repo** — it's gitignored machine-wide; if a repo tracks it, `git rm --cached` and fix the ignore.
- **Never leave uncommitted work in a worktree overnight** — commit and push, even broken. Rotting local state is the failure mode this entire policy exists to kill.
- **Never bypass `wt` with raw `git worktree add`** — raw git knows nothing about the path template and will happily create a stray. (Raw `git worktree list/remove` for *inspection and repair* is fine.)

## Relationship to other rules

- **merge-forward skill:** worktrees are the delivery vehicle for merge-forward slices — smallest observable change in a worktree, landed on main immediately.
- **Global AGENTS.md checkpointing:** "always commit and push, never leave work sitting" — worktrees satisfy the isolation half of that rule; this skill's MAINTAIN section satisfies the landing half.

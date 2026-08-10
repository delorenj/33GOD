# Momo Hardening — Architecture Note (33GPM-2)

## Overview

Six new contracts harden Momo's lifecycle against the waste streams identified in the
Aug 7-9 black-box read. Each contract is a Python library module in
`momo/skill/scripts/lib/` (canonical SSOT) with a thin CLI wrapper in
`momo/skill/scripts/momo-*.py` and a re-export shim in
`agents/hermes/pm/.scripts/lib/` + `agents/hermes/pm/.scripts/momo-*.py` for the Hermes
runtime.

## The six contracts

1. **Hand-back bundle (33GPM-3)** — `momo_handback.py`: A JSON bundle
   (`handback/<ISSUE>.handback.json`) tracks worker identity, heartbeat timestamps,
   git SHAs, check results (tests/lint/mutation), and retry policy. Workers must
   `init` → `heartbeat` → `finalize` → `validate` before counting as done. The
   `momo_worker_monitor.py` watches for stale heartbeats and triggers retries.
   **GoF:** Command pattern — each subcommand is a discrete handler.

2. **Evidence capture (33GPM-4)** — `momo_evidence.py`: Reads the hand-back bundle,
   runs baseline + branch test counts, executes a mutation check (revert → fail →
   restore), and writes `evidence/<ISSUE>.evidence.json`. Momo links this artifact
   instead of narrating test runs. **GoF:** Template Method — fixed skeleton with
   overridable test/lint commands.

3. **Reporter (33GPM-5)** — `momo_reporter.py`: Enforces one-comment-per-event with
   delta + state + asks format. Deduplicates by content hash before posting.
   Post-mortems go to the decision trail, not the ticket. **GoF:** Observer — the
   reporter is the single sink for board comments, with a dedupe guard.

4. **Findings ledger (33GPM-6)** — `momo_findings.py`: Per-issue JSON ledger
   (`findings/<ISSUE>.findings.json`) with stable IDs (F001, F002, ...). Supports
   add/resolve/show/markdown. Replaces prose re-enumeration in comments.
   **GoF:** Repository — the ledger is the single source of truth for findings state.

5. **Lane gate (33GPM-7)** — `momo_lane_gate.py`: Precondition checks before lane
   transitions. `in_review` requires: tree not locked + close gate passed.
   `completed` requires: all above + autonomous review. Returns structured JSON
   with per-gate pass/fail. **GoF:** Chain of Responsibility — gates are evaluated
   in sequence, any failure blocks the transition.

6. **Tree lock (33GPM-8)** — `momo_tree_lock.py`: Advisory file lock (`.momo/tree.lock`)
   with TTL and heartbeat refresh. `guard` command lets background automation check
   before committing. Prevents unowned writes during active sessions.
   **GoF:** Singleton — one lock per repo, file-based with flock.

## Interop

The contracts form a pipeline: hand-back (1) → evidence capture (2) reads it →
findings ledger (4) tracks review discoveries → lane gate (5) checks all artifacts
before allowing transitions → reporter (3) posts delta-state-asks using ledger IDs →
tree lock (6) guards the working tree throughout. The lane gate is the integration
point: it checks the close gate (evidence file), the tree lock, and the autonomous
review before allowing any transition to `in_review` or `completed`.

## Config drift fixed

`.project.json` and `role.yaml` identifier updated from `PROJ` to `33GPM` to match
the actual Plane project identifier. The `tp` adapter now resolves the correct board.

## Tests

```bash
python3 momo/skill/scripts/tests/test_momo_hardening.py
```

16 tests covering all six contracts plus the config drift fix. All pass.

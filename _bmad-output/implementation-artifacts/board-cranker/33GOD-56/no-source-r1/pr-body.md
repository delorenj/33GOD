## What does this PR do?

Adds isolated, stateless contractor turns for trusted internal gateway callers: a fresh agent and empty history, disabled memory, explicit per-turn overrides, required-skill validation, and observable cleanup. Bloodbank is a motivating caller, not a new Hermes dependency.

33GOD-54 and its no-source publication child 33GOD-56 carry the immutable range `b0ab2e163a50d4e6c36507eba955a6067fde6abc...750ad5ccd79e1ea4dd6725486b2849c2a0defa1d`. The published merge candidate retains ordered parents `cc00fe6ef855e506ad1bf8166473eecf725af8a8` and `b0ab2e163a50d4e6c36507eba955a6067fde6abc`. This publication authored no source change or commit.

Fresh independent specification and quality/security reviews of this candidate remain pending. This evidence handback is not review, approval, integration, or merge authorization. The PR remains OPEN, unapproved, and unmerged.

## Related Issue

Plane: 33GOD-54 -> 33GOD-56. The integrated 33GOD-55 Git travel guard is the publication prerequisite; 33GOD-50, 33GOD-51, and 33GOD-53 supply the underlying feature and repairs.

## Type of Change

- [ ] Bug fix
- [x] New feature
- [ ] Security fix
- [ ] Documentation update
- [ ] Tests (adding or improving test coverage)
- [ ] Refactor
- [ ] New skill

## Changes Made

- `gateway/platforms/base.py`: typed internal contractor-turn context and platform lifecycle support.
- `gateway/run.py`: trust validation, isolated execution, per-turn overrides, and cleanup handling.
- `tests/gateway/test_contractor_turns.py`: contractor-turn behavior coverage.

These are exactly the files differing across the immutable upstream-base/candidate range.

## How to Test

Use `/home/delorenj/.hermes/hermes-agent/.venv/bin/python` and the adjacent `ruff` binary; nothing was installed and both `uv.lock` hashes match. Every command used a fresh isolated HERMES_HOME, TMPDIR, cache, and bytecode root with deterministic UTC/locale/hash-seed settings and no inherited test credentials.

1. At candidate and baseline, run the complete command `python -m pytest -q -o addopts= tests/gateway`, strictly sequentially. 2 complete pair was run. Candidate: **48 failed / 7685 passed**. Baseline: **48 failed / 7642 passed**. Every candidate failure reproduces at baseline with the same exception class. Candidate-only failed nodes: **0**; base-only failed nodes: **0**; changed error classes: **0**.
2. Candidate focused slice `tests/gateway/test_contractor_turns.py tests/gateway/test_session_split_brain_11016.py`: **50 passed**.
3. Candidate adjacent slice (`test_turn_request_overrides.py`, `test_fast_command.py`, `test_custom_provider_request_overrides.py`, `test_session_model_override_persistence.py`, `test_turn_context.py` under `tests/gateway/`): **24 passed**.
4. Ruff and `py_compile` on `gateway/platforms/base.py gateway/run.py tests/gateway/test_contractor_turns.py tests/gateway/test_session_split_brain_11016.py`: **PASS**. `git diff --check b0ab2e163a50d4e6c36507eba955a6067fde6abc...750ad5ccd79e1ea4dd6725486b2849c2a0defa1d`: **PASS**.
5. `tests/gateway/test_restart_resume_pending.py::TestResumePendingSystemNote::test_stale_tool_tail_with_production_data_shape`: **three consecutive passes at candidate, then three at baseline**. `tests/gateway/test_systemd_notify.py::test_notify_supports_systemd_abstract_socket`: **one pass at each revision**, after the broad pair ended.

Broad UTC timing: candidate **2026-09-05T13:25:49.759053Z -> 2026-09-05T13:40:21.354868Z**; baseline **2026-09-05T13:40:21.423471Z -> 2026-09-05T13:54:52.066072Z**. The supervisor waited for command exit, reaped descendants, and recorded empty process scans before the baseline started. No broad-suite overlap occurred. The isolated probes supplement the complete pair and do not replace it.

The first complete pair had 49 candidate failures and 48 baseline failures. Its candidate-only node was `tests/gateway/test_hosted_rooms.py::test_room_log_pages_are_bounded_by_serialized_event_bytes`. That triggered exactly one additional complete sequential pair, as prescribed. The counts above describe the final pair, where no candidate-only node or changed error class remains. The first pair and its failure evidence are retained; no source was changed between pairs.

Baseline disposition: **DONE_WITH_CONCERNS**. Inherited broad failures remain; this is not an all-green suite. Fresh node/exception records, complete logs, exit receipts, timestamps, process evidence, and hashes are under `33GOD-56/no-source-r1/`. Prior RED/GREEN and prerequisite evidence were preserved unchanged.

The shared failures include Unix-socket path-length errors under the isolated evidence roots. Baseline equivalence does not claim that every failure is an intrinsic upstream source defect.

## Checklist

### Code

- [ ] I've read the Contributing Guide (not re-attested by this no-source worker).
- [ ] My commit messages follow Conventional Commits (no commit authored in 33GOD-56).
- [ ] I searched for existing PRs (not re-attested by this worker).
- [x] The immutable diff contains exactly the three stated feature/test files.
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the requested gateway suites were run; inherited failures remain.
- [ ] I've added tests for my changes (no source/test edits authorized in 33GOD-56; existing tests were executed).
- [x] Tested on Linux.

### Documentation & Housekeeping

- [ ] Source documentation/configuration updates: outside this no-source task.
- [ ] Cross-platform validation: not performed in this Linux evidence run.
- [ ] Fresh independent specification review: pending.
- [ ] Fresh independent quality/security review: pending.

## Screenshots / Logs

- Sequential machine receipt SHA-256: `298e0939f299995857b65e42e9e7b540ae294eab3cd21f245e0f99979ad1ab93`.
- Guarded push transcript SHA-256: `02f7c9487a9d614e281d96aa58aa37d7abc7f18ba529e4ffd7b0554c1f0550a8`.
- Exact guard source: merge `02481c8df4cedbdc11081fe41fcf01859a399566`, command-scoped `core.hooksPath=/tmp/agents-board-cranker-55-postmerge-verification-r2/git/hooks`.
- Guard `pre-push` SHA-256: `ddc23c60fa6c67bd20a06d51b76d35d7b30fa812a54dfa9c1ee52280fea179dc`.
- Guard `_travels.py` SHA-256: `d395ff645cf25eceabe7e99f82ac969981a4b82a260f7046087d2103acf3615d`.
- Trace proves the pinned pre-push hook executed successfully. Normal fast-forward push; no force, no verification bypass, no disabled guard, no history rewrite. Remote head was read back as `750ad5ccd79e1ea4dd6725486b2849c2a0defa1d`.

GitHub mergeability and checks are platform-owned live state; local test evidence does not fabricate or replace those checks.

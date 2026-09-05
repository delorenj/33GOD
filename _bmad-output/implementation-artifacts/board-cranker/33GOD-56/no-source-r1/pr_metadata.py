from evidence import *

assert json.loads((E/'publication-pass.json').read_text())['remote_after_sha']==C
verify_ground()
remote('premetadata',C)
d = json.loads((E/'sequential-differential.json').read_text())
f = d['final']
retry_note = ''
if d['full_pairs_run'] > 1:
    first = d['pairs'][0]
    retry_note = f"The first complete pair had {len(first['candidate']['failed_nodes'])} candidate failures and {len(first['baseline']['failed_nodes'])} baseline failures. Its candidate-only node was `"+'`, `'.join(first['candidate_only_failures'])+"`. That triggered exactly one additional complete sequential pair, as prescribed. The counts above describe the final pair, where no candidate-only node or changed error class remains. The first pair and its failure evidence are retained; no source was changed between pairs."
title = 'feat(gateway): stateless contractor turns (33GOD-54, 33GOD-56; '+BASE+'...'+C+')'
body = f'''## What does this PR do?

Adds isolated, stateless contractor turns for trusted internal gateway callers: a fresh agent and empty history, disabled memory, explicit per-turn overrides, required-skill validation, and observable cleanup. Bloodbank is a motivating caller, not a new Hermes dependency.

33GOD-54 and its no-source publication child 33GOD-56 carry the immutable range `{BASE}...{C}`. The published merge candidate retains ordered parents `{P}` and `{BASE}`. This publication authored no source change or commit.

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

1. At candidate and baseline, run the complete command `python -m pytest -q -o addopts= tests/gateway`, strictly sequentially. {d['full_pairs_run']} complete pair was run. Candidate: **{len(f['candidate']['failed_nodes'])} failed / {f['candidate']['passed']} passed**. Baseline: **{len(f['baseline']['failed_nodes'])} failed / {f['baseline']['passed']} passed**. Every candidate failure reproduces at baseline with the same exception class. Candidate-only failed nodes: **{len(f['candidate_only_failures'])}**; base-only failed nodes: **{len(f['base_only_failures'])}**; changed error classes: **{len(f['error_class_changes'])}**.
2. Candidate focused slice `tests/gateway/test_contractor_turns.py tests/gateway/test_session_split_brain_11016.py`: **50 passed**.
3. Candidate adjacent slice (`test_turn_request_overrides.py`, `test_fast_command.py`, `test_custom_provider_request_overrides.py`, `test_session_model_override_persistence.py`, `test_turn_context.py` under `tests/gateway/`): **24 passed**.
4. Ruff and `py_compile` on `gateway/platforms/base.py gateway/run.py tests/gateway/test_contractor_turns.py tests/gateway/test_session_split_brain_11016.py`: **PASS**. `git diff --check {BASE}...{C}`: **PASS**.
5. `tests/gateway/test_restart_resume_pending.py::TestResumePendingSystemNote::test_stale_tool_tail_with_production_data_shape`: **three consecutive passes at candidate, then three at baseline**. `tests/gateway/test_systemd_notify.py::test_notify_supports_systemd_abstract_socket`: **one pass at each revision**, after the broad pair ended.

Broad UTC timing: candidate **{f['candidate_started_at']} -> {f['candidate_finished_at']}**; baseline **{f['baseline_started_at']} -> {f['baseline_finished_at']}**. The supervisor waited for command exit, reaped descendants, and recorded empty process scans before the baseline started. No broad-suite overlap occurred. The isolated probes supplement the complete pair and do not replace it.

{retry_note}

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

- Sequential machine receipt SHA-256: `{sha(E/'sequential-differential.json')}`.
- Guarded push transcript SHA-256: `{sha(E/'publication-push.log')}`.
- Exact guard source: merge `{GUARD}`, command-scoped `core.hooksPath={G}/git/hooks`.
- Guard `pre-push` SHA-256: `{EXPECTED[str(G/'git/hooks/pre-push')]}`.
- Guard `_travels.py` SHA-256: `{EXPECTED[str(G/'git/hooks/_travels.py')]}`.
- Trace proves the pinned pre-push hook executed successfully. Normal fast-forward push; no force, no verification bypass, no disabled guard, no history rewrite. Remote head was read back as `{C}`.

GitHub mergeability and checks are platform-owned live state; local test evidence does not fabricate or replace those checks.
'''
path = E/'pr-body.md'
with path.open('x') as out:
    out.write(body)
save('pr-requested-metadata.json',{'title':title,'body_path':str(path),'body_sha256':sha(path)})
r = run('pr-metadata-update',['gh','pr','edit','102409','--repo','NousResearch/hermes-agent','--title',title,'--body-file',str(path)])
assert r['exit_code']==0,r
actual = remote('after',C)
assert actual['title']==title and actual['body']==body
for text in [actual['title'],actual['body']]:
    assert '33GOD-54' in text and '33GOD-56' in text and BASE+'...'+C in text
save('pr-metadata-pass.json',{'status':'PASS','at':utc(),'metadata_updated':True,
     'readback':str(E/'pr-after.json'),'readback_sha256':sha(E/'pr-after.json')})
print('PR_METADATA_VERIFIED',flush=True)

from receipt_runner import *
comparison=json.loads((E/'full-comparison.json').read_text())
assert comparison['status']=='PASS' and not comparison['branch_only_failures'] and not comparison['base_only_failures'] and not comparison['error_class_changes']
for name in ['focused-head','adjacent-head','ruff-head','compile-head','diff-check-head']:
    assert json.loads((E/(name+'.json')).read_text())['exit_code']==0
for role,tree,expected in [('head',H,C),('base',B,BASE)]:
    assert checked(role+'-sha-prepublication',['git','rev-parse','HEAD'],tree)==expected
    assert checked(role+'-clean-prepublication',['git','status','--porcelain=v1','--untracked-files=all'],tree)==''
assert json.loads(checked('owner-prepublication',['cat',str(OWNER)]))['owner_agent_id']=='33god-pm'
remote_preflight('prepublication')
push=run('push',['git','push','delorenj','HEAD:refs/heads/'+BR])
assert push['exit_code']==0,'Push failed; do not mutate PR'
s=checked('remote-after-push',['git','ls-remote','--exit-code','delorenj','refs/heads/'+BR])
assert s.split()==[C,'refs/heads/'+BR]
assert checked('head-clean-after-push',['git','status','--porcelain=v1','--untracked-files=all'])==''
rng=BASE+'...'+C
title='feat(gateway): stateless contractor turns (33GOD-54; '+rng+')'
body=f'''## What does this PR do?

Adds an internal gateway path for isolated, stateless contractor turns. A trusted external orchestrator supplies typed contractor context; Hermes executes the turn with a fresh agent, empty history, disabled memory, explicit request overrides, required-skill validation, and bounded cleanup.

Bloodbank is the motivating caller; this change adds no Bloodbank import, package, service, or runtime dependency.

Plane story **33GOD-54** records evidence and publication for immutable candidate range:

`{rng}`

Candidate `{C}` has ordered parents `{P}` and `{BASE}`. This story makes no source, test, dependency, or history changes.

## Related Issue

Plane campaign: `33GOD-50` (stateless contractor turns), `33GOD-51` (quality repair), `33GOD-53` (trust-seam repair and upstream reconciliation), and **`33GOD-54` (current evidence and publication)**.

Prior repairs preserve typed disjoint project roots after trust validation, distinguish explicit null service tier from an omitted override, and surface cleanup failure without masking a primary execution failure. Their original RED/GREEN evidence remains preserved; previous review outcomes do not cover this candidate.

## Type of Change

- [ ] Bug fix
- [x] New feature
- [ ] Security fix
- [ ] Documentation update
- [ ] Tests
- [ ] Refactor
- [ ] New skill

## Changes Made

Exactly three files differ against the immutable upstream base:

- `gateway/platforms/base.py`: typed internal contractor-turn context carried by trusted platform events.
- `gateway/run.py`: context validation, isolated one-turn execution, request overrides, and observable cleanup.
- `tests/gateway/test_contractor_turns.py`: trust checks, stateless isolation, overrides, concurrency, cancellation, cleanup, and platform outcomes.

## How to Test

This evidence run used Python 3.11.12 at `/home/delorenj/.hermes/hermes-agent/.venv/bin/python` and Ruff 0.16.6 at `/home/delorenj/.hermes/hermes-agent/.venv/bin/ruff`, without installing or changing dependencies. Head and base used identical commands and credential-free deterministic environments, with separate temporary Hermes homes.

- Focused candidate: `python -m pytest -q -o 'addopts=' tests/gateway/test_contractor_turns.py tests/gateway/test_session_split_brain_11016.py` — **50 passed**.
- Adjacent candidate: `python -m pytest -q -o 'addopts=' tests/gateway/test_turn_request_overrides.py tests/gateway/test_fast_command.py tests/gateway/test_custom_provider_request_overrides.py tests/gateway/test_session_model_override_persistence.py tests/gateway/test_turn_context.py` — **24 passed**.
- `ruff check gateway/platforms/base.py gateway/run.py tests/gateway/test_contractor_turns.py tests/gateway/test_session_split_brain_11016.py` — passed.
- Compilation of those four Python files and `git diff --check {rng}` — passed.
- Identical complete `python -m pytest -q -o 'addopts=' tests/gateway` commands at candidate and base; **{comparison['full_pairs_run']} complete pair(s)**.
  - Candidate: **{comparison['head_summary']}**.
  - Base: **{comparison['base_summary']}**.
  - Final failed node/error-class signatures match byte-for-byte. Branch-only failures: **0**; base-only failures: **0**; error-class changes: **0**. The broad suite is not represented as all-green when inherited failures remain.
- `tests/gateway/test_restart_resume_pending.py::TestResumePendingSystemNote::test_stale_tool_tail_with_production_data_shape` — three consecutive isolated executions passed at candidate and three at base; isolated passes do not waive full-suite differences.

Four shared failures involve long test-runtime paths (media log truncation and Unix socket/witness paths). These are limitations of this controlled run; the exact differential does not establish an all-green upstream suite.

**Fresh specification review remains pending. A subsequent quality/security review by a different independent reviewer also remains pending.** These are controller-owned mandatory gates. This worker has not reviewed, approved, or merged the PR.

## Checklist

### Code

- [ ] Fresh reviewer confirmation of contribution and architecture requirements is pending.
- [x] The candidate range contains exactly the three scoped files listed above.
- [x] Required focused, adjacent, static, and differential evidence has been collected on Linux.
- [ ] The entire repository test suite is green — not established by this gateway-only run.
- [ ] Fresh independent specification review has passed.
- [ ] A different independent quality/security reviewer has passed the candidate after specification review.

### Documentation & Housekeeping

- [x] Current immutable range and current test outcomes are recorded here.
- [x] Original repair RED/GREEN and integration-conflict evidence is preserved.
- [x] No public configuration or model-tool schema change is introduced by this evidence story.
- [ ] Windows and macOS runtime verification — not performed in this Linux evidence run.

## Screenshots / Logs

Full commands, outputs, explicit exits, SHA-256 hashes, failed-node/error-class differentials, isolated-node runs, and publication readbacks are retained at:

`{E}/`

Machine differential: `full-comparison.json`; individual full pairs: `gateway-differential-*.json`; preserved inputs: `preserved-evidence.json` and final hash recheck. The controller owns final independent reviews and acceptance.
'''
(E/'pr-body.md').write_text(body)
save('pr-metadata-request.json',{'title':title,'body':body})
edit=run('pr-edit',['gh','pr','edit','102409','--repo','NousResearch/hermes-agent','--title',title,'--body-file',str(E/'pr-body.md')])
assert edit['exit_code']==0,'PR metadata update failed'
remote_preflight('after-publication',C)
pr=json.loads((E/'pr-after-publication-readback.json').read_text())
assert pr['title']==title and pr['body']==body
assert '33GOD-54' in pr['title'] and rng in pr['title'] and '33GOD-54' in pr['body'] and rng in pr['body']
assert pr['reviewDecision']!='APPROVED'
print('PUBLICATION_VERIFIED')

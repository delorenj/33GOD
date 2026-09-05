from publication_host import *
if __name__=='__main__':
    assert json.loads((E/'publication-verified.json').read_text())['status']=='PASS'
    d=verify_gates()
    remote_preflight('premetadata',C)
    pr=json.loads((E/'pr-premetadata-readback.json').read_text())
    assert pr['reviewDecision']!='APPROVED'
    span=BASE+'...'+C
    title='33GOD-54: stateless contractor turns ('+span+')'
    focused=parse(E/'focused-head-host.log')['summary']
    adjacent=parse(E/'adjacent-head.log')['summary']
    body=f'''## What does this PR do?

Adds an internal gateway path for isolated, stateless contractor turns. A trusted orchestrator can provide a typed contractor-turn context, and Hermes runs a fresh agent with empty conversation history, memory disabled, explicit per-turn request overrides, required-skill validation, and bounded cleanup.

Bloodbank is the motivating caller; this change adds no Bloodbank import, package, service, or runtime dependency. The repairs preserve typed disjoint project roots after trust validation, distinguish an explicitly null service tier from an omitted override, and surface cleanup failure without masking a primary execution failure.

33GOD-54 evidence/publication recovery validates the immutable range `{span}`. This attempt changes no product source or history. It publishes the existing merge candidate after verifying the integrated 33GOD-55 Git guard.

## Related Issue

Plane stories: **33GOD-54** (evidence/publication recovery), 33GOD-50 (stateless contractor turns), 33GOD-51 (quality repair), 33GOD-53 (trust-seam repair), and 33GOD-55 (integrated publication guard repair).

Immutable validation range: `{span}`.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [x] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [ ] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `gateway/platforms/base.py`: typed internal contractor-turn context for trusted platform events.
- `gateway/run.py`: validates context, runs an isolated one-turn agent, propagates overrides, and exposes cleanup failures.
- `tests/gateway/test_contractor_turns.py`: exercises trust, isolation, overrides, concurrency, cancellation, cleanup, and platform outcomes.

These are exactly the three files differing from the immutable upstream base. Candidate `{C}` has ordered parents `{P}` and `{BASE}`.

## How to Test

All commands were run on Linux with the existing shared `.venv` Python/Ruff, credential-free environments, UTC, C.UTF-8, hash seed 0, and separate temporary HERMES_HOME/TMPDIR roots. No dependencies were installed. Commands below use `python` and `ruff` from that fixed environment.

1. `python -m pytest -q -o 'addopts=' tests/gateway/test_contractor_turns.py tests/gateway/test_session_split_brain_11016.py`: **{focused}**.
2. `python -m pytest -q -o 'addopts=' tests/gateway/test_turn_request_overrides.py tests/gateway/test_fast_command.py tests/gateway/test_custom_provider_request_overrides.py tests/gateway/test_session_model_override_persistence.py tests/gateway/test_turn_context.py`: **{adjacent}**.
3. `ruff check gateway/platforms/base.py gateway/run.py tests/gateway/test_contractor_turns.py tests/gateway/test_session_split_brain_11016.py`, `python -m py_compile` on those same four files, and `git diff --check {span}`: **PASS**.
4. Identical complete `python -m pytest -q -o 'addopts=' tests/gateway` at candidate and immutable base:
   - Candidate: **{d['head']['summary']}**.
   - Base: **{d['base']['summary']}**.
   - Exactly **{d['head']['failure_count']}** matching failed node/error-class records; **0** candidate-only failures, **0** base-only failures, **0** error-class changes.
5. `{NODE}`: **3 consecutive isolated passes at candidate and 3 at base**.

The complete gateway suite is not all green. Its failures are classified as inherited only because the exact failed-node/error-class signatures match at the immutable base. An initial sandboxed focused run stalled after 47 passes and was interrupted (exit 2); its complete log is preserved. The unchanged command outside sandbox restrictions passed all 50. No source or test edits were made for the rerun.

Fresh independent **specification review remains pending**, followed by fresh independent **quality/security review**. Earlier reviews of other immutable ranges do not approve this candidate. This evidence handoff is not approval or merge authorization.

## Checklist

### Code

- [ ] I've read the Contributing Guide — not re-attested by this evidence-only worker.
- [ ] My commit messages follow Conventional Commits — no commits authored in this recovery.
- [ ] I searched for existing PRs — not re-attested in this recovery.
- [x] The candidate diff contains only the three named feature files.
- [ ] I've run `pytest tests/ -q` and all tests pass — not established; gateway differential results are recorded above.
- [x] Existing behavior tests were rerun successfully for the feature and adjacent paths.
- [x] I've tested on my platform: Linux.

### Documentation & Housekeeping

- [x] Relevant documentation — N/A; no public workflow or configuration changed in this recovery.
- [x] `cli-config.yaml.example` — N/A; no configuration keys changed.
- [x] `CONTRIBUTING.md` / `AGENTS.md` — N/A; no architecture or contributor workflow changed.
- [ ] Cross-platform verification — this recovery ran on Linux only.
- [x] Tool descriptions/schemas — N/A; no model tool schema changed.

## Screenshots / Logs

Local evidence directory: `{E}`.

- `gateway-differential-{d['attempt']}.json`: exact node IDs, error classes, command/environment receipts, and both log hashes.
- `hook-execution-proof.json`, `push.log`, and `push-trace2.jsonl`: exact integrated 33GOD-55 hook execution and normal fast-forward publication.
- `preserved-inputs-prepublication.json`: re-hashed prior attempt, original feature RED/GREEN, guard RED/GREEN, and integration/controller proofs, all unchanged.

No UI screenshots apply. Status: **DONE_WITH_CONCERNS** for matching inherited gateway failures; fresh independent review gates remain pending.
'''
    assert len(title)<256 and '33GOD-54' in title and span in title and span in body
    bodypath=E/'pr-body.md'
    with bodypath.open('x') as f:f.write(body)
    save('pr-metadata-request.json',{'title':title,'body':body,'body_sha256':sha(bodypath)})
    r=run('pr-metadata-update',['gh','pr','edit','102409','--repo','NousResearch/hermes-agent','--title',title,'--body-file',str(bodypath)])
    assert r['exit_code']==0,r
    remote_preflight('metadata-readback',C)
    actual=json.loads((E/'pr-metadata-readback-readback.json').read_text())
    assert actual['title']==title and actual['body']==body
    assert actual['reviewDecision']!='APPROVED'
    save('pr-metadata-verified.json',{'status':'PASS','title_exact':True,'body_exact':True,'body_names_ticket':True,'body_names_range':True,'state':actual['state'],'head_sha':actual['headRefOid'],'reviewDecision':actual['reviewDecision']})

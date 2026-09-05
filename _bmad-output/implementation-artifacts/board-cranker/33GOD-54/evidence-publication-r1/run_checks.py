from receipt_runner import *
assert json.loads((E/'pr-preflight-network-readback.json').read_text())['headRefOid']==P
pytest=[PY,'-m','pytest','-q','-o','addopts=']
results=[]
results.append(run('focused-head',pytest+['tests/gateway/test_contractor_turns.py','tests/gateway/test_session_split_brain_11016.py'],controlled=True))
results.append(run('adjacent-head',pytest+['tests/gateway/test_turn_request_overrides.py','tests/gateway/test_fast_command.py','tests/gateway/test_custom_provider_request_overrides.py','tests/gateway/test_session_model_override_persistence.py','tests/gateway/test_turn_context.py'],controlled=True))
results.append(run('ruff-head',[RUFF,'check']+STATIC,controlled=True))
results.append(run('compile-head',[PY,'-m','py_compile']+STATIC,controlled=True))
results.append(run('diff-check-head',['git','diff','--check',BASE+'...'+C],controlled=True))
for role,tree in [('head',H),('base',B)]:
    for attempt in range(1,4):
        run('target-'+role+'-'+str(attempt),pytest+[NODE],tree,controlled=True,attempt=attempt)
assert all(r['exit_code']==0 for r in results),'Focused/static gate failed; full suite deferred'
run('gateway-head-1',pytest+['tests/gateway'],H,controlled=True)
run('gateway-base-1',pytest+['tests/gateway'],B,controlled=True)

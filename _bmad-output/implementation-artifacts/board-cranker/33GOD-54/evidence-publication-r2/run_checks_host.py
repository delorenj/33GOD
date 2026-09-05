from receipt_runner import *
from differential_parser import parse,differential
from concurrent.futures import ThreadPoolExecutor
if __name__=='__main__':
    assert json.loads((E/'pr-preflight-network-readback.json').read_text())['headRefOid']==P
    save('execution-policy-host.json',{
      'test_runner_choice':'Explicit recovery commands override general run_tests.sh instructions.',
      'controlled_environment':'Same allowlist as attempt 1, no credentials, same absolute venv, UTC/C.UTF-8/hash seed 0, distinct HERMES_HOME/TMPDIR only; HOME unchanged.',
      'full_pair_scheduling':'Candidate and base run concurrently in separate processes with separate state roots. No other gates run concurrently with the full pair.',
      'repeat_policy':'Repeat full pair exactly once only if candidate-only failures remain.',
      'authorized_writes':'New r2 evidence, ignored test caches, exact fork fast-forward push and PR title/body only.',
      'pending_gates':['Fresh independent specification review','Fresh independent quality/security review'],
      'source_changes':[],'commits_authored':[],'history_rewritten':False})
    for name,cmd in [
      ('focused-head-host',[PY,'-m','pytest','-q','-o','addopts=','tests/gateway/test_contractor_turns.py','tests/gateway/test_session_split_brain_11016.py']),
      ('adjacent-head',[PY,'-m','pytest','-q','-o','addopts=','tests/gateway/test_turn_request_overrides.py','tests/gateway/test_fast_command.py','tests/gateway/test_custom_provider_request_overrides.py','tests/gateway/test_session_model_override_persistence.py','tests/gateway/test_turn_context.py']),
      ('ruff-head',[RUFF,'check',*STATIC]),
      ('compile-head',[PY,'-m','py_compile',*STATIC]),
      ('diff-check-head',['git','diff','--check',BASE+'...'+C])]:
        r=run(name,cmd,controlled=True); assert r['exit_code']==0,r
    for role,tree in [('head',H),('base',B)]:
        r=run('import-paths-'+role,[PY,'-B','-c','import importlib.util,json,sys; print(json.dumps({"executable":sys.executable,"gateway":importlib.util.find_spec("gateway").origin,"run_agent":importlib.util.find_spec("run_agent").origin}))'],tree,controlled=True)
        assert r['exit_code']==0
        for i in range(1,4):
            r=run('target-'+role+'-'+str(i),[PY,'-m','pytest','-q','-o','addopts=',NODE],tree,controlled=True,attempt=i)
            save('target-'+role+'-'+str(i)+'-parsed.json',parse(r['log']))
    for role in ['head','base']:
        old=E.parent/'evidence-publication-r1'/('gateway-'+role+'-1.log')
        d=parse(old); assert d['failure_count']==48
    save('parser-validation.json',{'status':'PASS','prior_failure_counts':[48,48]})
    for i in range(1,3):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(run,'gateway-'+role+'-'+str(i),[PY,'-m','pytest','-q','-o','addopts=','tests/gateway'],tree,True,i) for role,tree in [('head',H),('base',B)]]
            receipts=[f.result() for f in futures]
        d=differential(i)
        if not d['branch_only_failures']: break
    save('gates-complete.json',{'status':d['status'],'full_pairs_run':i,'branch_only_failures':d['branch_only_failures'],'base_only_failures':d['base_only_failures'],'error_class_changes':d['error_class_changes']})

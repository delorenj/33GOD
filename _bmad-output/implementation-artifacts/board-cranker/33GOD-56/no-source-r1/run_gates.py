from evidence import *

def report(name):
    p = E/(name+'.reports.json')
    data = json.loads(p.read_text())
    failed = {}
    for r in data['reports']:
        if r['outcome']=='failed':
            assert r['error_class'], r
            failed.setdefault(r['nodeid'],[]).append({'phase':r['phase'],'error_class':r['error_class']})
    passed = sum(r['phase']=='call' and r['outcome']=='passed' for r in data['reports'])
    skipped = sum(r['outcome']=='skipped' for r in data['reports'])
    result = {'name':name,'reports_path':str(p),'reports_sha256':sha(p),
              'tests_collected':data['tests_collected'],'passed':passed,'skipped':skipped,
              'failed_nodes':failed,'collection_errors':data['collection_errors'],
              'exit_status':data['exit_status']}
    save(name+'.parsed.json',result)
    return result

def differential(pair, cr, br):
    c = report(cr['name'])
    b = report(br['name'])
    cf,bf = c['failed_nodes'],b['failed_nodes']
    changes = [{'nodeid':n,'candidate':cf[n],'baseline':bf[n]} for n in sorted(cf.keys() & bf.keys()) if cf[n]!=bf[n]]
    only_c = sorted(cf.keys()-bf.keys())
    only_b = sorted(bf.keys()-cf.keys())
    overlap = cr['finished_monotonic_ns'] < br['started_monotonic_ns'] and cr['finished_at'] < br['started_at']
    complete = not c['collection_errors'] and not b['collection_errors'] and c['tests_collected']>0 and b['tests_collected']>0 and cr['exit_code'] in [0,1] and br['exit_code'] in [0,1]
    result = {'pair':pair,'candidate':c,'baseline':b,'candidate_only_failures':only_c,
              'base_only_failures':only_b,'error_class_changes':changes,
              'every_candidate_failure_reproduces':not only_c and not changes,
              'no_overlap_proven':overlap and cr['process']['all_descendants_gone'] and br['process']['all_descendants_gone'],
              'candidate_started_at':cr['started_at'],'candidate_finished_at':cr['finished_at'],
              'baseline_started_at':br['started_at'],'baseline_finished_at':br['finished_at'],
              'candidate_exit_receipt':str(E/(cr['name']+'.exit.json')),
              'baseline_exit_receipt':str(E/(br['name']+'.exit.json')),
              'complete':complete,
              'status':'PASS' if complete and overlap and not only_c and not changes else 'FAIL'}
    save('differential-pair-'+str(pair)+'.json',result)
    print(json.dumps({'pair':pair,'candidate_failed':len(cf),'baseline_failed':len(bf),
                      'candidate_only':only_c,'base_only':only_b,'error_class_changes':changes,
                      'no_overlap_proven':result['no_overlap_proven'],'status':result['status']}),flush=True)
    return result

assert (E/'local-preflight-pass.json').exists()
assert json.loads((E/'pr-before.json').read_text())['headRefOid']==P
verify_ground()
save('execution-policy.json',{'started_at':utc(),'broad_suites_concurrent':False,
     'supervision':'One supervisor, subprocess wait, Linux child subreaper, adopted-child reaping, recursive descendant and process session tracking, /proc scans before and after every command.',
     'repeat_policy':'Exactly one additional complete sequential candidate/base pair only if the first pair has a candidate-only failed node.',
     'instrumentation':'External evidence-only pytest plugin records actual call.excinfo types. No test selection or outcome modification. PYTEST_ADDOPTS only relocates pytest cache.',
     'writes':'Only evidence root including per-command state/cache/bytecode roots.',
     'network':'No inherited credentials in tests; host execution needed for AF_UNIX abstract socket and asyncio subprocess behavior.'})
cmd = [PY,'-m','pytest','-q','-o','addopts=']
sequence = 0
pairs = []
for pair in [1,2]:
    sequence += 1
    cr = run('gateway-candidate-'+str(pair),cmd+['tests/gateway'],H,True,True,sequence)
    assert cr['process']['all_descendants_gone']
    sequence += 1
    br = run('gateway-baseline-'+str(pair),cmd+['tests/gateway'],B,True,True,sequence)
    d = differential(pair,cr,br)
    pairs.append(d)
    if not d['candidate_only_failures']:
        break
save('sequential-differential.json',{'status':d['status'],'full_pairs_run':len(pairs),
     'broad_suites_concurrent':False,'no_overlap_proven':all(p['no_overlap_proven'] for p in pairs),
     'pairs':pairs,'final':d})
assert d['status']=='PASS',d

checks = [
    ('focused-candidate',H,cmd+['tests/gateway/test_contractor_turns.py','tests/gateway/test_session_split_brain_11016.py'],50),
    ('adjacent-candidate',H,cmd+['tests/gateway/'+n+'.py' for n in ['test_turn_request_overrides','test_fast_command','test_custom_provider_request_overrides','test_session_model_override_persistence','test_turn_context']],24),
    ('ruff-candidate',H,[RUFF,'check',*STATIC],None),
    ('compile-candidate',H,[PY,'-m','py_compile',*STATIC],None),
    ('diff-check-candidate',H,['git','diff','--check',BASE+'...'+C],None),
]
node = 'tests/gateway/test_restart_resume_pending.py::TestResumePendingSystemNote::test_stale_tool_tail_with_production_data_shape'
for role,tree in [('candidate',H),('baseline',B)]:
    for i in [1,2,3]:
        checks.append(('restart-'+role+'-'+str(i),tree,cmd+[node],1))
for role,tree in [('candidate',H),('baseline',B)]:
    checks.append(('systemd-'+role,tree,cmd+['tests/gateway/test_systemd_notify.py::test_notify_supports_systemd_abstract_socket'],1))
for name,tree,argv,passes in checks:
    sequence += 1
    r = run(name,argv,tree,True,passes is not None,sequence)
    assert r['exit_code']==0,r
    if passes is not None:
        parsed = report(name)
        assert parsed['passed']==passes and not parsed['failed_nodes'] and not parsed['collection_errors'],parsed
verify_ground()
save('gates-pass.json',{'status':'PASS','at':utc(),'full_pairs_run':len(pairs),
     'sequential_differential_sha256':sha(E/'sequential-differential.json'),
     'focused_passes':50,'adjacent_passes':24,'restart_passes':6,'systemd_passes':2,
     'static_gates':['ruff','py_compile','git diff --check'],
     'baseline_disposition':'DONE_WITH_CONCERNS' if d['candidate']['failed_nodes'] or d['baseline']['failed_nodes'] else 'ALL_GREEN'})
print('ALL_REQUIRED_GATES_PASS',flush=True)

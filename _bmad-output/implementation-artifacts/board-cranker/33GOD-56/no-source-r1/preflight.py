from evidence import *

verify_ground()
save('immutable-prerequisites-before.json',[{'path':p,'sha256':sha(p)} for p in EXPECTED])
save('preserved-inputs-before.json',preserved_inventory())
save('owner-before.json',{'path':str(OWNER),'sha256':sha(OWNER),'owner_agent_id':json.loads(OWNER.read_text())['owner_agent_id']})
for name, tree in [('candidate',H),('baseline',B),('guard',G),
                   ('hermes-primary',Path('/home/delorenj/.hermes/hermes-agent')),
                   ('agents-primary',Path('/home/delorenj/.agents'))]:
    s = snapshot(tree)
    save(name+'-before.json',s)
    print(name, s['head'], 'clean='+str(not s['status']), 'files='+str(len(s['files'])), flush=True)
save('processes-before.json',{'at':utc(),'matches':gateway_processes()})
assert not gateway_processes()
versions = {}
for name, cmd in [('python-version',[PY,'--version']),('ruff-version',[RUFF,'--version']),
                  ('python-environment',[PY,'-B','-c','import sys,pytest,importlib.metadata,json; print(json.dumps({"executable":sys.executable,"version":sys.version,"pytest":pytest.__version__,"packages":sorted((d.metadata["Name"],d.version) for d in importlib.metadata.distributions())},indent=2))'])]:
    r = run(name,cmd,controlled=True)
    assert r['exit_code']==0
    versions[name] = r
save('environment-validation.json',{'versions':versions,'candidate_lock_sha256':sha(H/'uv.lock'),
     'baseline_lock_sha256':sha(B/'uv.lock'),'locks_match':True,'python_binary_sha256':sha(PY),
     'ruff_binary_sha256':sha(RUFF),'install_performed':False,
     'policy':'Exact requested pytest commands override run_tests.sh. Empty allowlisted test environment; HOME unchanged; all state, caches and bytecode below evidence root. No source writes.'})
save('local-preflight-pass.json',{'status':'PASS','at':utc(),'ordered_parents':[P,BASE],'actual_diff_files':FILES})
print('LOCAL_PREFLIGHT_PASS',flush=True)

from evidence import *

before = json.loads((E/'environment-validation.json').read_text())
prior = before['versions']['python-environment']
r = run('python-environment-final',prior['argv'],controlled=True)
assert r['exit_code']==0
old = json.loads(payload(prior).split('\n',1)[1])
new = json.loads(payload(r).split('\n',1)[1])
assert old==new
assert sha(PY)==before['python_binary_sha256'] and sha(RUFF)==before['ruff_binary_sha256']
assert sha(H/'uv.lock')==sha(B/'uv.lock')==before['candidate_lock_sha256']
save('environment-validation-final.json',{'status':'PASS','at':utc(),'python':PY,'ruff':RUFF,
     'candidate_lock_sha256':sha(H/'uv.lock'),'baseline_lock_sha256':sha(B/'uv.lock'),
     'locks_match':True,'install_performed':False,'package_inventory_unchanged':True,
     'interpreter_and_ruff_binaries_unchanged':True,'before':str(E/'environment-validation.json'),
     'before_sha256':sha(E/'environment-validation.json'),'final_command':r})
print('ENVIRONMENT_UNCHANGED',flush=True)

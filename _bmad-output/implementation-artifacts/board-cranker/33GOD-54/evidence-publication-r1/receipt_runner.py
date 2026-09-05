import hashlib, json, os, pathlib, re, shlex, subprocess, sys, time
E=pathlib.Path(__file__).resolve().parent
H=pathlib.Path('/tmp/hermes-board-cranker-50')
B=pathlib.Path('/tmp/hermes-board-cranker-53-upstream-baseline')
C='750ad5ccd79e1ea4dd6725486b2849c2a0defa1d'
BASE='b0ab2e163a50d4e6c36507eba955a6067fde6abc'
P='cc00fe6ef855e506ad1bf8166473eecf725af8a8'
BR='feat/33GOD-50-stateless-contractor-turns'
PY='/home/delorenj/.hermes/hermes-agent/.venv/bin/python'
RUFF='/home/delorenj/.hermes/hermes-agent/.venv/bin/ruff'
OWNER=pathlib.Path('/home/delorenj/code/33GOD/agents/hermes/pm/runtime/board-cranker-controller-owner.json')
FILES=['gateway/platforms/base.py','gateway/run.py','tests/gateway/test_contractor_turns.py']
STATIC=FILES+['tests/gateway/test_session_split_brain_11016.py']
NODE='tests/gateway/test_restart_resume_pending.py::TestResumePendingSystemNote::test_stale_tool_tail_with_production_data_shape'
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(name,obj):
    p=E/name
    with p.open('x') as f: json.dump(obj,f,indent=2,sort_keys=True); f.write('\n')
    return p

def run(name,cmd,cwd=H,controlled=False,attempt=1):
    log=E/(name+'.log')
    env=os.environ.copy()
    env['GIT_OPTIONAL_LOCKS']='0'
    if controlled:
        rt=E/'runtime'/name
        rt.mkdir(parents=True,exist_ok=False)
        hh=rt/'hermes-home'; hh.mkdir()
        env={'PATH':'/home/delorenj/.hermes/hermes-agent/.venv/bin:/usr/bin:/bin',
             'HOME':os.environ['HOME'],'TZ':'UTC','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
             'PYTHONHASHSEED':'0','PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1',
             'HERMES_HOME':str(hh),'TMPDIR':str(rt),'GIT_OPTIONAL_LOCKS':'0','RUFF_NO_CACHE':'true'}
    started=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    with log.open('x') as f:
        f.write('$ '+shlex.join(cmd)+'\nworktree='+str(cwd)+'\nstarted='+started+'\n')
        if controlled: f.write('controlled_environment='+json.dumps(env,sort_keys=True)+'\n')
        f.flush()
        proc=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
        f.write('\n[exit_code='+str(proc.returncode)+']\n')
    record={'name':name,'command':shlex.join(cmd),'argv':cmd,'worktree':str(cwd),'attempt':attempt,
            'exit_code':proc.returncode,'log':str(log),'sha256':sha(log),'started':started,
            'completed':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    if controlled: record['environment']=env
    save(name+'.json',record)
    print(json.dumps(record),flush=True)
    return record

def payload(record):
    s=pathlib.Path(record['log']).read_text()
    return s.split('started=',1)[1].split('\n',1)[1].rsplit('\n[exit_code=',1)[0].rstrip('\n')

def checked(name,cmd,cwd=H):
    r=run(name,cmd,cwd)
    assert r['exit_code']==0,r
    return payload(r)

def local_preflight():
    owner=checked('owner-preflight',['cat',str(OWNER)])
    assert json.loads(owner)['owner_agent_id']=='33god-pm'
    for role,tree,expected in [('head',H,C),('base',B,BASE)]:
        assert checked(role+'-sha-preflight',['git','rev-parse','HEAD'],tree)==expected
        branch=checked(role+'-branch-preflight',['git','branch','--show-current'],tree)
        assert branch==(BR if role=='head' else ''),branch
        assert checked(role+'-clean-preflight',['git','status','--porcelain=v1','--untracked-files=all'],tree)==''
        common=checked(role+'-common-dir-preflight',['git','rev-parse','--path-format=absolute','--git-common-dir'],tree)
        assert common=='/home/delorenj/.hermes/hermes-agent/.git',common
        markers=['MERGE_HEAD','REBASE_HEAD','CHERRY_PICK_HEAD','REVERT_HEAD','rebase-merge','rebase-apply','sequencer','BISECT_START','index.lock']
        paths={m:checked(role+'-marker-path-'+m,['git','rev-parse','--path-format=absolute','--git-path',m],tree) for m in markers}
        existing=[p for p in paths.values() if pathlib.Path(p).exists()]
        save(role+'-operation-markers.json',{'paths':paths,'existing':existing})
        assert not existing,existing
        checked(role+'-cache-ignore',['git','check-ignore','--no-index','gateway/__pycache__/run.cpython-311.pyc','tests/gateway/__pycache__/test_contractor_turns.cpython-311.pyc','.pytest_cache/CACHEDIR.TAG','.ruff_cache/CACHEDIR.TAG'],tree)
    parents=checked('head-ordered-parents',['git','show','-s','--format=%P',C]).split()
    assert parents==[P,BASE],parents
    actual=checked('head-diff-files',['git','diff','--name-only',BASE+'...'+C]).splitlines()
    assert actual==FILES,actual
    checked('head-first-parent-ancestor',['git','merge-base','--is-ancestor',P,C])
    checked('head-upstream-ancestor',['git','merge-base','--is-ancestor',BASE,C])
    checked('fork-url',['git','remote','get-url','--push','delorenj'])
    checked('python-version',[PY,'--version'])
    checked('ruff-version',[RUFF,'--version'])
    checked('python-environment',[PY,'-B','-c','import sys,pytest,importlib.metadata,json; print(json.dumps({"executable":sys.executable,"prefix":sys.prefix,"pytest":pytest.__version__,"packages":sorted((d.metadata["Name"],d.version) for d in importlib.metadata.distributions())},indent=2))'])
    hashes=[{'path':str(p),'sha256':sha(p)} for p in [H/'uv.lock',B/'uv.lock',H/'pyproject.toml',B/'pyproject.toml',pathlib.Path(PY).resolve(),pathlib.Path(RUFF).resolve(),OWNER]]
    assert hashes[0]['sha256']==hashes[1]['sha256']
    assert hashes[2]['sha256']==hashes[3]['sha256']
    save('immutable-ground.json',{'candidate_sha':C,'ordered_parents':parents,'base_sha':BASE,'diff_files':actual,'artifact_hashes':hashes,'start_clean':True})
    prior=E.parent.parent/'33GOD-53'
    paths=sorted(p for p in prior.rglob('*') if p.is_file())
    paths+=sorted(p for p in prior.parent.glob('33GOD-53*.json') if p.is_file())
    save('preserved-evidence.json',[{'path':str(p),'sha256':sha(p)} for p in paths])
    print('LOCAL_PREFLIGHT_PASS',flush=True)

def remote_preflight(suffix='preflight',expected=P):
    s=checked('remote-'+suffix,['git','ls-remote','--exit-code','delorenj','refs/heads/'+BR])
    assert s.split()==[expected,'refs/heads/'+BR],s
    s=checked('pr-'+suffix,['gh','pr','view','102409','--repo','NousResearch/hermes-agent','--json','number,url,title,body,state,headRefOid,headRefName,headRepositoryOwner,headRepository,baseRefName,mergeable,mergeStateStatus,statusCheckRollup,reviewDecision,isDraft'])
    pr=json.loads(s)
    assert pr['state']=='OPEN' and pr['headRefOid']==expected and pr['headRefName']==BR,pr
    assert pr['headRepositoryOwner']['login']=='delorenj',pr
    save('pr-'+suffix+'-readback.json',pr)
    print('REMOTE_PREFLIGHT_PASS',flush=True)

if __name__=='__main__':
    if sys.argv[1]=='local-preflight': local_preflight()
    elif sys.argv[1]=='remote-preflight': remote_preflight()

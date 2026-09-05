from preflight import *
from differential_parser import parse

def ground(stage):
    assert json.loads(checked('owner-'+stage,['cat',str(OWNER)]))['owner_agent_id']=='33god-pm'
    for role,tree,expected,branch in [('head',H,C,BR),('base',B,BASE,'')]:
        assert checked(role+'-sha-'+stage,['git','rev-parse','HEAD'],tree)==expected
        assert checked(role+'-branch-'+stage,['git','branch','--show-current'],tree)==branch
        assert checked(role+'-clean-'+stage,['git','status','--porcelain=v1','--untracked-files=all'],tree)==''
        for m in ['MERGE_HEAD','REBASE_HEAD','CHERRY_PICK_HEAD','REVERT_HEAD','rebase-merge','rebase-apply','sequencer','BISECT_START','index.lock']:
            p=checked(role+'-marker-'+m+'-'+stage,['git','rev-parse','--path-format=absolute','--git-path',m],tree)
            assert not pathlib.Path(p).exists(),p
    assert checked('head-parents-'+stage,['git','show','-s','--format=%P',C]).split()==[P,BASE]
    assert checked('head-diff-files-'+stage,['git','diff','--name-only',BASE+'...'+C]).splitlines()==FILES
    guard(stage)

def verify_gates():
    d=json.loads((E/'gates-complete.json').read_text())
    assert d['status']=='PASS'
    assert not any(d[k] for k in ['branch_only_failures','base_only_failures','error_class_changes'])
    for name in ['focused-head-host','adjacent-head','ruff-head','compile-head','diff-check-head']:
        r=json.loads((E/(name+'.json')).read_text())
        assert r['exit_code']==0 and sha(r['log'])==r['sha256']
    for i in range(1,4):
        records=[]
        for role in ['head','base']:
            r=json.loads((E/f'target-{role}-{i}.json').read_text())
            assert sha(r['log'])==r['sha256']
            records.append((r['exit_code'],parse(r['log'])['canonical_node_error_json']))
        assert records[0]==records[1],records
    report=json.loads((E/f"gateway-differential-{d['full_pairs_run']}.json").read_text())
    for role in ['head','base']:
        assert sha(report[role]['log'])==report[role]['sha256']
    return report

def verify_preserved(stage):
    inputs=json.loads((E/'preserved-inputs-start.json').read_text())
    for item in inputs:
        item['preserved_unchanged']=sha(item['path'])==item['sha256']
    save('preserved-inputs-'+stage+'.json',inputs)
    assert all(item['preserved_unchanged'] for item in inputs)

if __name__=='__main__':
    report=verify_gates()
    ground('prepublication')
    verify_preserved('prepublication')
    remote_preflight('prepublication')
    for role,tree in [('hermes',pathlib.Path('/home/delorenj/.hermes/hermes-agent')),('agents',pathlib.Path('/home/delorenj/.agents'))]:
        current=snapshot(role,tree,'prepublication')
        assert current==json.loads((E/(role+'-primary-snapshot-start.json')).read_text()),role+' primary changed'
    assert 'GIT_GUARD_OFF' not in os.environ
    assert not any(k.startswith('GIT_CONFIG_') for k in os.environ)
    hookpath=str(G/'git/hooks')
    assert checked('pinned-effective-hook-path',['git','-c','core.hooksPath='+hookpath,'config','--get','core.hooksPath'])==hookpath
    pushcmd=['git','-c','core.hooksPath='+hookpath,'push','delorenj','HEAD:refs/heads/'+BR]
    runtime=E/'runtime/push'; runtime.mkdir(parents=True,exist_ok=False)
    os.environ['PATH']=str(pathlib.Path(PY).parent)+':/usr/bin:/bin'
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    os.environ['TMPDIR']=str(runtime)
    os.environ['GIT_TRACE']='1'
    os.environ['GIT_TRACE2_EVENT']=str(E/'push-trace2.jsonl')
    save('publication-policy.json',{'argv':pushcmd,'command':shlex.join(pushcmd),'hook_source_path':hookpath,'hook_source_merge_sha':MERGE,'GIT_GUARD_OFF_present':False,'no_verify':False,'force_push':False,'guard_disabled':False,'environment_overrides':{k:os.environ[k] for k in ['PATH','PYTHONDONTWRITEBYTECODE','TMPDIR','GIT_TRACE','GIT_TRACE2_EVENT']}})
    r=run('push',pushcmd)
    del os.environ['GIT_TRACE']; del os.environ['GIT_TRACE2_EVENT']
    assert r['exit_code']==0,r
    transcript=pathlib.Path(r['log']).read_text()
    events=[json.loads(x) for x in (E/'push-trace2.jsonl').read_text().splitlines()]
    hooks=[x for x in events if x.get('event')=='child_start' and x.get('hook_name')=='pre-push']
    assert len(hooks)==1 and hooks[0]['argv'][0]==hookpath+'/pre-push',hooks
    exits=[x for x in events if x.get('event')=='child_exit' and x.get('child_id')==hooks[0]['child_id'] and x.get('sid')==hooks[0]['sid']]
    assert len(exits)==1 and exits[0]['code']==0,exits
    assert 'git-travel: refs/heads/'+BR+':' in transcript
    assert 'forced update' not in transcript
    save('hook-execution-proof.json',{'hook_start':hooks[0],'hook_exit':exits[0],'hook_hashes':{'pre-push':sha(G/'git/hooks/pre-push'),'_travels.py':sha(G/'git/hooks/_travels.py')},'trace2_sha256':sha(E/'push-trace2.jsonl'),'push_log_sha256':sha(r['log']),'hook_executed':True,'no_bypass':True,'merge_sha':MERGE})
    remote_preflight('postpush',C)
    for role,tree in [('head',H),('base',B),('guard',G)]:
        assert checked(role+'-clean-postpush',['git','status','--porcelain=v1','--untracked-files=all'],tree)==''
    save('publication-verified.json',{'status':'PASS','remote_after_sha':C,'fast_forward':True,'push_exit_code':0,'hook_executed':True})

from receipt_runner import *
G=pathlib.Path('/tmp/agents-board-cranker-55-postmerge-verification-r2')
MERGE='02481c8df4cedbdc11081fe41fcf01859a399566'
ROOT=E.parent.parent
fixed={
'33GOD-54.implementation.attempt-1.json':'0bf1f17dbe5c99a150302374392c64d4fe2b8c313147d2215c2e444c7ae8f8c7',
'33GOD-54.blocker-reconciliation.json':'34a312da67cb5e2095f163d461ed24877eaad2c5052da7f3b9c7044d768e2ffa',
'33GOD-55.integration.json':'37ca03936fa8d58ba5bf740976c730517a9da098c283fba8a2d29cb4877f069e',
'33GOD-55.integration-controller-verification-r2.json':'c7d83164bdade7452d6bc204ffd169d617475fb5dff6e45998cfbf24853d04a3',
'33GOD-53/red.log':'7fe456453163f9369481543fdeef844717f891026b366570d61eb0132a8e0420',
'33GOD-53/green.log':'0d27d89c5ee07b12752559c11f67d8c02baacc68b4a54904e9ea09c9ee6f4baa'}
def snapshot(role,tree,stage):
    status=checked(role+'-primary-status-'+stage,['git','--no-optional-locks','status','--porcelain=v1','--untracked-files=all'],tree)
    head=checked(role+'-primary-head-'+stage,['git','rev-parse','HEAD'],tree)
    paths=checked(role+'-primary-paths-'+stage,['git','ls-files','-z','--cached','--others','--exclude-standard'],tree).split('\0')
    files={}
    for rel in paths:
        if not rel: continue
        p=tree/rel
        if p.is_symlink(): files[rel]={'symlink':os.readlink(p)}
        elif p.is_file(): files[rel]={'sha256':sha(p),'mode':p.stat().st_mode}
        elif not p.exists(): files[rel]={'missing':True}
    idx=pathlib.Path(checked(role+'-primary-index-path-'+stage,['git','rev-parse','--path-format=absolute','--git-path','index'],tree))
    obj={'head':head,'status':status,'files':files,'index_sha256':sha(idx)}
    save(role+'-primary-snapshot-'+stage+'.json',obj)
    return obj

def guard(stage):
    assert checked('guard-sha-'+stage,['git','rev-parse','HEAD'],G)==MERGE
    assert checked('guard-branch-'+stage,['git','branch','--show-current'],G)==''
    assert checked('guard-clean-'+stage,['git','status','--porcelain=v1','--untracked-files=all'],G)==''
    checked('guard-parents-'+stage,['git','show','-s','--format=%P',MERGE],G)
    for name,expected in [('pre-push','ddc23c60fa6c67bd20a06d51b76d35d7b30fa812a54dfa9c1ee52280fea179dc'),('_travels.py','d395ff645cf25eceabe7e99f82ac969981a4b82a260f7046087d2103acf3615d')]:
        p=G/'git/hooks'/name
        assert sha(p)==expected
        assert not p.is_symlink()
        checked('guard-hash-'+name+'-'+stage,['sha256sum',str(p)],G)
    assert os.access(G/'git/hooks/pre-push',os.X_OK)
    for m in ['MERGE_HEAD','REBASE_HEAD','CHERRY_PICK_HEAD','REVERT_HEAD','rebase-merge','rebase-apply','sequencer','BISECT_START','index.lock']:
        p=checked('guard-marker-'+m+'-'+stage,['git','rev-parse','--path-format=absolute','--git-path',m],G)
        assert not pathlib.Path(p).exists(),p
    checked('guard-support-hashes-'+stage,['sha256sum',str(G/'git/hooks/_guard.sh')],G)

if __name__=='__main__':
    assert 'GIT_GUARD_OFF' not in os.environ
    assert not any(k.startswith('GIT_CONFIG_') for k in os.environ)
    assert json.loads(checked('owner-fixed-check',['cat',str(OWNER)]))['owner_agent_id']=='33god-pm'
    for rel,expected in fixed.items():
        actual=sha(ROOT/rel)
        print(rel,actual,flush=True)
        assert actual==expected,(rel,actual,expected)
    assert json.loads((ROOT/'33GOD-54.implementation.attempt-1.json').read_text())['status']=='BLOCKED'
    assert json.loads((ROOT/'33GOD-55.integration.json').read_text())['status']=='INTEGRATED'
    assert json.loads((ROOT/'33GOD-55.integration-controller-verification-r2.json').read_text())['status']=='PASS'
    for rel,prefix,suffix in [('33GOD-55/implementation-r2/red.log','535cdd','4ca9'),('33GOD-55/implementation-r2/green-expanded.log','1e1247','2ce')]:
        digest=sha(ROOT/rel)
        print(rel,digest,flush=True)
        assert digest.startswith(prefix) and digest.endswith(suffix)
        fixed[rel]=digest
    local_preflight()
    guard('preflight')
    paths=set(ROOT/rel for rel in fixed)
    paths.update(p for p in (E.parent/'evidence-publication-r1').rglob('*') if p.is_file())
    prior=json.loads((ROOT/'33GOD-54.implementation.attempt-1.json').read_text())
    for x in prior['preserved_evidence']:
        p=pathlib.Path(x['path']); assert sha(p)==x['sha256']; paths.add(p)
    for x in prior['checks']:
        p=pathlib.Path(x['log']); assert sha(p)==x['sha256']; paths.add(p)
    save('preserved-inputs-start.json',[{'path':str(p),'sha256':sha(p)} for p in sorted(paths)])
    snapshot('hermes',pathlib.Path('/home/delorenj/.hermes/hermes-agent'),'start')
    snapshot('agents',pathlib.Path('/home/delorenj/.agents'),'start')
    hooks=checked('global-hooks-path',['git','config','--show-origin','--get','core.hooksPath'])
    assert '/home/delorenj/.agents/git/hooks' in hooks
    checked('pr-template',['cat','.github/PULL_REQUEST_TEMPLATE.md'])
    print('LOCAL_AND_FIXED_PREFLIGHT_PASS',flush=True)

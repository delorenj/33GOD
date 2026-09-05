import sys
from evidence import *

def audit(label):
    verify_ground()
    before_inputs = json.loads((E/'preserved-inputs-before.json').read_text())
    after_inputs = [{'path':r['path'],'sha256':sha(r['path'])} for r in before_inputs]
    mismatches = [a['path'] for a,b in zip(before_inputs,after_inputs) if a!=b]
    save('preserved-inputs-'+label+'.json',after_inputs)
    save('immutable-prerequisites-'+label+'.json',[{'path':p,'sha256':sha(p)} for p in EXPECTED])
    assert not mismatches,mismatches
    snapshots = {}
    for name,tree in [('candidate',H),('baseline',B),('guard',G),
                     ('hermes-primary',Path('/home/delorenj/.hermes/hermes-agent')),
                     ('agents-primary',Path('/home/delorenj/.agents'))]:
        after = snapshot(tree)
        path = save(name+'-'+label+'.json',after)
        before = json.loads((E/(name+'-before.json')).read_text())
        changes = [key for key in before if before[key]!=after[key]]
        snapshots[name] = {'path':str(path),'sha256':sha(path),'unchanged':not changes,
                           'changed_fields':changes,'head':after['head'],'clean':not after['status']}
    env_before = json.loads((E/'environment-validation.json').read_text())
    assert sha(PY)==env_before['python_binary_sha256'] and sha(RUFF)==env_before['ruff_binary_sha256']
    processes = gateway_processes()
    save('processes-'+label+'.json',{'at':utc(),'matches':processes})
    external = None
    external_path = E/'external-agents-primary-advance.json'
    if external_path.exists() and not snapshots['agents-primary']['unchanged']:
        external = json.loads(external_path.read_text())
        now = json.loads((E/('agents-primary-'+label+'.json')).read_text())
        accounted = json.loads((E/'agents-primary-prepublication.json').read_text())
        assert now==accounted and now['head']==external['new_head']
        assert not external['worker_mutation_performed']
        snapshots['agents-primary']['external_advance_accounted'] = True
        snapshots['agents-primary']['external_advance_receipt'] = str(external_path)
        snapshots['agents-primary']['external_advance_receipt_sha256'] = sha(external_path)
    unchanged_or_external = all(s['unchanged'] or s.get('external_advance_accounted',False) for s in snapshots.values())
    result = {'at':utc(),'status':'PASS' if unchanged_or_external and not mismatches and not processes else 'FAIL',
              'snapshots':snapshots,'preserved_input_count':len(after_inputs),'preserved_input_mismatches':mismatches,
              'owner_agent_id':json.loads(OWNER.read_text())['owner_agent_id'],
              'source_touched':False,'commits_authored':[],'history_rewritten':False,
              'external_unpinned_primary_advance':external,
              'scope':'No Plane/controller/WIP/Bloodbank/Pjangler/client board mutation; no reviews, approval or merge performed.',
              'processes':processes}
    path = save('forbidden-scope-'+label+'.json',result)
    print(json.dumps({'audit':label,'status':result['status'],'preserved_input_count':len(after_inputs),'snapshots':snapshots}),flush=True)
    assert result['status']=='PASS',result
    return path

if __name__=='__main__':
    audit(sys.argv[1])

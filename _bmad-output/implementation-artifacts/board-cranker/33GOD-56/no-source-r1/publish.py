from evidence import *
from audit import audit

gates = json.loads((E/'gates-pass.json').read_text())
assert gates['status']=='PASS'
assert json.loads((E/'gates-receipt-validation.json').read_text())['status']=='PASS'
assert json.loads((E/'environment-validation-final.json').read_text())['status']=='PASS'
assert sha(E/'sequential-differential.json')==gates['sequential_differential_sha256']
diff = json.loads((E/'sequential-differential.json').read_text())
assert diff['status']=='PASS' and diff['no_overlap_proven']
assert not diff['final']['candidate_only_failures'] and not diff['final']['error_class_changes']
audit('prepublication-reconciled')
remote('prepublication',P)
verify_ground()
url = run('fork-push-url',['git','remote','get-url','--push','delorenj'])
assert url['exit_code']==0 and payload(url)=='git@github.com:delorenj/hermes-agent.git'
env = environment('publication')
env['PATH'] = str(Path(PY).parent)+':'+os.environ['PATH']
# Keep existing authentication configuration readable for the normal SSH push.
for key in ['XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME']:
    env.pop(key)
env['GIT_TRACE'] = '1'
env['GIT_TRACE2_EVENT'] = str(E/'push-trace2.jsonl')
assert 'GIT_GUARD_OFF' not in os.environ
save('publication-authorization.json',{
     'at':utc(),'source_mutation_authorized':False,'candidate_sha':C,'first_parent_sha':P,
     'upstream_base_sha':BASE,'guard_merge_sha':GUARD,'hook_source_path':str(G/'git/hooks'),
     'pre_push_sha256':sha(G/'git/hooks/pre-push'),'travels_sha256':sha(G/'git/hooks/_travels.py'),
     'guard_support_sha256':sha(G/'git/hooks/_guard.sh'),'guard_source_override':True,
     'guard_disabled':False,'GIT_GUARD_OFF_present':False,'no_verify':False,'force_push':False,
     'python3_resolution':str(Path(PY).parent/'python3'),
     'python3_matches_required_interpreter':sha(Path(PY).parent/'python3')==sha(PY),
     'evidence_gates_receipt':str(E/'gates-pass.json'),'evidence_gates_sha256':sha(E/'gates-pass.json')})
argv = ['git','-c','core.hooksPath='+str(G/'git/hooks'),'push','delorenj','HEAD:refs/heads/'+BR]
r = run('publication-push',argv,overrides=env)
assert r['exit_code']==0,r
events = [json.loads(line) for line in (E/'push-trace2.jsonl').read_text().splitlines()]
starts = [event for event in events if event.get('event')=='child_start' and event.get('hook_name')=='pre-push' and str(G/'git/hooks/pre-push') in event.get('argv',[])]
assert starts, 'Missing pinned hook execution trace'
exits = [event for event in events if event.get('event')=='child_exit' and any(event.get('sid')==s.get('sid') and event.get('child_id')==s.get('child_id') for s in starts)]
assert exits and all(e['code']==0 for e in exits),exits
save('hook-execution-proof.json',{'status':'PASS','starts':starts,'exits':exits,
     'trace_path':str(E/'push-trace2.jsonl'),'trace_sha256':sha(E/'push-trace2.jsonl'),
     'transcript':r['log'],'transcript_sha256':r['sha256'],
     'hook_source_merge_sha':GUARD,'pre_push_sha256':sha(G/'git/hooks/pre-push'),
     'travels_sha256':sha(G/'git/hooks/_travels.py')})
remote('published',C)
save('publication-pass.json',{'status':'PASS','at':utc(),'remote_after_sha':C,
     'push_receipt':str(E/'publication-push.exit.json'),
     'push_receipt_sha256':sha(E/'publication-push.exit.json'),
     'hook_executed':True,'remote_matches_candidate':True})
print('PUBLICATION_VERIFIED',flush=True)

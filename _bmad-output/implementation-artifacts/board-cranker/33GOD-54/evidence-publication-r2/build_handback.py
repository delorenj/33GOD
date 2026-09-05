from publication_host import *

def receipt(name,status=None,summary=None):
    r=json.loads((E/(name+'.json')).read_text())
    assert sha(r['log'])==r['sha256'],name
    result={k:r[k] for k in ['name','command','worktree','attempt','exit_code','log','sha256']}
    result['status']=status or ('PASS' if r['exit_code']==0 else 'FAIL')
    result['summary']=summary or ('Command completed successfully.' if r['exit_code']==0 else 'See complete log.')
    return result

if __name__=='__main__':
    d=verify_gates()
    assert json.loads((E/'publication-verified.json').read_text())['status']=='PASS'
    assert json.loads((E/'pr-metadata-verified.json').read_text())['status']=='PASS'
    assert json.loads((E/'forbidden-scope-audit.json').read_text())['status']=='PASS'
    pr=json.loads((E/'pr-metadata-readback-readback.json').read_text())
    broad_status='BASELINE_MATCH' if d['head']['failure_count'] else 'PASS'
    checks=[receipt('preflight-workflow',summary='Owner, fixed hashes, exact commits/ordered parents/diff, clean worktrees, absent Git operation markers, primary snapshots, environment and integrated guard verified; per-command receipts retained.'),
      receipt('remote-preflight','NOT_RUN','Sandbox SSH config permission failure (128); recovered by successful host network preflight.'),
      receipt('remote-preflight-network',summary='Fork ref equals required pre-recovery SHA.'),
      receipt('pr-preflight-network',summary='PR OPEN on the exact fork branch and pre-recovery SHA.'),
      receipt('focused-head','NOT_RUN','Sandboxed focused run stalled after 47 passes; explicitly interrupted, exit 2, preserved unchanged. Superseded by same-command host run.'),
      receipt('focused-head-host',summary=parse(E/'focused-head-host.log')['summary']),
      receipt('adjacent-head',summary=parse(E/'adjacent-head.log')['summary']),
      receipt('ruff-head',summary='All four specified files pass Ruff.'),
      receipt('compile-head',summary='All four specified files compile.'),
      receipt('diff-check-head',summary='Immutable range passes whitespace checks.')]
    target={}
    for role,tree in [('head',H),('base',B)]:
        target[role]=[]
        checks.append(receipt('import-paths-'+role,summary='Fixed venv executable; gateway and run_agent resolve to this exact worktree.'))
        for i in range(1,4):
            name=f'target-{role}-{i}'; r=receipt(name,summary=parse(E/(name+'.log'))['summary']); checks.append(r)
            parsed=parse(r['log'])
            target[role].append({'attempt':i,'worktree':str(tree),'exit_code':r['exit_code'],'error_class':'NONE' if not parsed['failures'] else parsed['failures'][0]['error_class'],'log':r['log'],'sha256':r['sha256']})
    pairs=json.loads((E/'gates-complete.json').read_text())['full_pairs_run']
    for i in range(1,pairs+1):
        di=json.loads((E/f'gateway-differential-{i}.json').read_text())
        for role in ['head','base']:
            checks.append(receipt(f'gateway-{role}-{i}',broad_status if di['status']=='PASS' else 'FAIL',di[role]['summary']))
    checks.extend([
        receipt('checks-host-workflow',summary='All mandatory focused/static and isolated gates complete; exact failed-node/error-class differential PASS.'),
        receipt('publication-workflow',summary='Repeated fail-closed ground, guard and primary checks before the authorized push; verified hook execution and exact remote SHA.'),
        receipt('push',summary='Authorized normal fast-forward push through exact integrated guard; hook and push both exit 0.'),
        receipt('remote-postpush',summary='Remote ref equals exact candidate.'),
        receipt('pr-metadata-update',summary='Only existing PR title/body updated.'),
        receipt('pr-metadata-readback',summary='PR OPEN, exact candidate head, exact title/body readback; no review approval.'),
        receipt('final-audit-workflow',summary='All three worktrees clean at immutable commits; primary snapshots/indexes unchanged; prior evidence and environment unchanged.')])
    preserved=json.loads((E/'preserved-inputs-final.json').read_text())
    selected=[x for x in preserved if x['path'] in {str(ROOT/r) for r in fixed}|{str(ROOT/'33GOD-55/implementation-r2/red.log'),str(ROOT/'33GOD-55/implementation-r2/green-expanded.log')}]
    def ref(rel):return str(ROOT/rel)
    obj={
      'schema_version':'1.0','issue':'33GOD-54','phase':'evidence-and-publication',
      'status':'DONE_WITH_CONCERNS' if d['head']['failure_count'] else 'DONE',
      'summary':f"Published exact candidate {C} through the integrated 33GOD-55 guard and verified PR metadata. Focused 50 and adjacent 24 passed; static gates and six isolated runs passed. Gateway comparison has {d['head']['failure_count']} identical failed-node/error-class records and zero deltas. All three worktrees are clean; fresh independent reviews remain pending.",
      'worker':{'agent_id':'codex-33god-54-evidence-publication-r2','role':'evidence-publication-recovery-worker','provider':'openai-codex','attempt':2},
      'prior_attempt':{'path':ref('33GOD-54.implementation.attempt-1.json'),'sha256':fixed['33GOD-54.implementation.attempt-1.json'],'status':'BLOCKED','blocker_path':ref('33GOD-54.blocker-reconciliation.json'),'blocker_sha256':fixed['33GOD-54.blocker-reconciliation.json'],'verified':True},
      'guard_repair':{'issue':'33GOD-55','integration_path':ref('33GOD-55.integration.json'),'integration_sha256':fixed['33GOD-55.integration.json'],'controller_verification_path':ref('33GOD-55.integration-controller-verification-r2.json'),'controller_verification_sha256':fixed['33GOD-55.integration-controller-verification-r2.json'],'status':'INTEGRATED','merge_sha':MERGE,'worktree':str(G),'worktree_clean':True,'pre_push_sha256':sha(G/'git/hooks/pre-push'),'travels_sha256':sha(G/'git/hooks/_travels.py'),'dirty_primary_touched':False},
      'immutable_ground':{'candidate_sha':C,'first_parent_sha':P,'upstream_base_sha':BASE,'remote_before_sha':P,'ordered_parents':[P,BASE],'expected_diff_files':FILES,'actual_diff_files':FILES},
      'repository':{'owning_repo':'/home/delorenj/.hermes/hermes-agent','candidate_worktree':str(H),'baseline_worktree':str(B),'branch':BR,'start_clean':True,'end_clean':True,'guard_worktree_end_clean':True,'source_changes':[],'commits_authored':[],'history_rewritten':False},
      'environment':{'python':PY+' (Python 3.11.12)','ruff':RUFF+' (Ruff 0.16.6)','lock_source':str(H/'uv.lock')+'; identical to '+str(B/'uv.lock')+'; SHA-256 '+sha(H/'uv.lock'),'install_performed':False,'validation_log':str(E/'python-environment-final.log')},
      'preserved_evidence':selected,
      'checks':checks,
      'differential':{'full_pairs_run':pairs,'head_failures':[f"{x['node_id']} | {x['error_class']}" for x in d['head']['failures']],'base_failures':[f"{x['node_id']} | {x['error_class']}" for x in d['base']['failures']],'branch_only_failures':d['branch_only_failures'],'base_only_failures':d['base_only_failures'],'error_class_changes':[json.dumps(x,sort_keys=True) for x in d['error_class_changes']],'target_node':NODE,'target_head_isolated':target['head'],'target_base_isolated':target['base'],'status':d['status'],'machine_receipt':str(E/f'gateway-differential-{pairs}.json'),'rationale':'Identical complete pytest argv and fixed venv; credential-free environments match except isolated state roots. Exact node/error-class signatures are byte-equal; no branch-only, base-only or error-class deltas. Full pair repeated only if a candidate-only failure remained.'},
      'publication':{'push_attempted':True,'push_command':receipt('push')['command'],'push_exit_code':0,'force_push':False,'no_verify':False,'guard_disabled':False,'hook_source_override':True,'hook_source_path':str(G/'git/hooks'),'hook_source_merge_sha':MERGE,'hook_executed':True,'remote_ref':'delorenj/'+BR,'remote_after_sha':C,'remote_matches_candidate':True,'log':str(E/'push.log')},
      'pr':{'number':102409,'url':'https://github.com/NousResearch/hermes-agent/pull/102409','state':pr['state'],'head_sha':pr['headRefOid'],'title':pr['title'],'body_names_ticket':True,'body_names_range':True,'metadata_updated':True,'approved':False,'merged':False,'mergeability':pr['mergeable']+' / '+pr['mergeStateStatus'],'checks':[json.dumps(x,sort_keys=True) for x in pr['statusCheckRollup']],'readback_log':str(E/'pr-metadata-readback.log')},
      'forbidden_scope':{'hermes_primary_touched':False,'agents_primary_touched':False,'plane_touched':False,'bloodbank_touched':False,'client_board_touched':False,'source_touched':False,'review_or_merge_performed':False,'audit_log':str(E/'forbidden-scope-audit.json')},
      'deferred_gates':['Fresh independent specification review of '+BASE+'...'+C,'Fresh independent quality/security review by a different reviewer after specification review','Controller disposition after independent gates; no approval or merge authorization in this handoff'],
      'risks':['The complete gateway suite is non-green; baseline-equivalence establishes no detected branch regression, not an all-green suite.','Linux-only validation; remote CI and mergeability are reported as read back, not promoted to approval.'],
      'notes':['All prior attempt logs and fixed evidence were re-hashed unchanged; full inventory: '+str(E/'preserved-inputs-final.json'), 'All command receipts, explicit exits, full logs and SHA-256 hashes: '+str(E/'command-manifest.json'), 'Hook execution proof: '+str(E/'hook-execution-proof.json')+'; Git trace: '+str(E/'push-trace2.jsonl'), 'Initial sandbox SSH read failed (128); host read succeeded. Initial sandbox focused run was interrupted after 47 passes (2); unchanged command passed all 50 on the host. Both diagnostics are preserved.', 'Both complete gateway runs executed concurrently with distinct temporary state roots. No dependencies, source, tests or commits were changed.', 'Exact user-specified pytest commands override general run_tests.sh guidance. Global git unpushed/landing was out of scope.', 'Canonical implementation handback was not written; launcher owns atomic installation.']}
    manifest=[]
    for p in sorted(E.glob('*.json')):
        try:r=json.loads(p.read_text())
        except Exception:continue
        if isinstance(r,dict) and all(k in r for k in ['argv','exit_code','log','sha256']):
            assert sha(r['log'])==r['sha256'];manifest.append(r)
    save('command-manifest.json',manifest)
    artifacts=[{'path':str(p),'sha256':sha(p)} for p in sorted(E.iterdir()) if p.is_file()]
    save('evidence-artifact-manifest.json',artifacts)
    obj['notes'].append('Artifact hash inventory: '+str(E/'evidence-artifact-manifest.json')+'; SHA-256 '+sha(E/'evidence-artifact-manifest.json'))
    save('handback.preview.json',obj)
    print(json.dumps(obj,indent=2),flush=True)

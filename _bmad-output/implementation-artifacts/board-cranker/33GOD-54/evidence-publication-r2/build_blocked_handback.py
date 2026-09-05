from publication_host import *

def receipt(name,status=None,summary=None):
    r=json.loads((E/(name+'.json')).read_text())
    assert sha(r['log'])==r['sha256'],name
    result={k:r[k] for k in ['name','command','worktree','attempt','exit_code','log','sha256']}
    result['status']=status or ('PASS' if r['exit_code']==0 else 'FAIL')
    result['summary']=summary or ('Command completed successfully.' if r['exit_code']==0 else 'See complete log.')
    return result

if __name__=='__main__':
    d=json.loads((E/'gateway-differential-1.json').read_text())
    assert json.loads((E/'publication-blocked.json').read_text())['status']=='BLOCKED'
    assert not (E/'push.json').exists() and not (E/'pr-metadata-update.json').exists()
    assert json.loads((E/'forbidden-scope-audit.json').read_text())['status']=='PASS'
    pr=json.loads((E/'pr-blocked-final-readback.json').read_text())
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
        receipt('checks-host-workflow','FAIL','Workflow completed, but exact differential FAIL: 48 candidate failures versus 49 base failures; one base-only OSError.'),
        receipt('base-only-diagnostic-workflow',summary='Fixed abstract socket collision diagnosed; sequential isolated passes do not replace the complete pair.'),
        receipt('systemd-isolated-head',summary='Base-only diagnostic node passes alone at candidate.'),
        receipt('systemd-isolated-base',summary='Base-only diagnostic node passes alone at base.'),
        receipt('remote-blocked-final',summary='Fork remains at required pre-recovery SHA; no push attempted.'),
        receipt('pr-blocked-final',summary='PR remains OPEN on original SHA; title/body unchanged and unapproved.'),
        receipt('final-audit-workflow',summary='All three worktrees clean; both primary HEADs/indexes/file hashes/statuses and prior evidence/environment unchanged.')])
    preserved=json.loads((E/'preserved-inputs-final.json').read_text())
    selected=[x for x in preserved if x['path'] in {str(ROOT/r) for r in fixed}|{str(ROOT/'33GOD-55/implementation-r2/red.log'),str(ROOT/'33GOD-55/implementation-r2/green-expanded.log')}]
    def ref(rel):return str(ROOT/rel)
    obj={
      'schema_version':'1.0','issue':'33GOD-54','phase':'evidence-and-publication',
      'status':'BLOCKED',
      'summary':'Publication blocked by a base-only failure from the worker scheduling both complete suites concurrently: the fixed abstract socket was already in use. Candidate 48/base 49 failures; all 48 common node/error records match. Focused 50, adjacent 24, static gates and six required isolated runs passed. No push or PR metadata mutation occurred. All worktrees and forbidden primaries are unchanged.',
      'worker':{'agent_id':'codex-33god-54-evidence-publication-r2','role':'evidence-publication-recovery-worker','provider':'openai-codex','attempt':2},
      'prior_attempt':{'path':ref('33GOD-54.implementation.attempt-1.json'),'sha256':fixed['33GOD-54.implementation.attempt-1.json'],'status':'BLOCKED','blocker_path':ref('33GOD-54.blocker-reconciliation.json'),'blocker_sha256':fixed['33GOD-54.blocker-reconciliation.json'],'verified':True},
      'guard_repair':{'issue':'33GOD-55','integration_path':ref('33GOD-55.integration.json'),'integration_sha256':fixed['33GOD-55.integration.json'],'controller_verification_path':ref('33GOD-55.integration-controller-verification-r2.json'),'controller_verification_sha256':fixed['33GOD-55.integration-controller-verification-r2.json'],'status':'INTEGRATED','merge_sha':MERGE,'worktree':str(G),'worktree_clean':True,'pre_push_sha256':sha(G/'git/hooks/pre-push'),'travels_sha256':sha(G/'git/hooks/_travels.py'),'dirty_primary_touched':False},
      'immutable_ground':{'candidate_sha':C,'first_parent_sha':P,'upstream_base_sha':BASE,'remote_before_sha':P,'ordered_parents':[P,BASE],'expected_diff_files':FILES,'actual_diff_files':FILES},
      'repository':{'owning_repo':'/home/delorenj/.hermes/hermes-agent','candidate_worktree':str(H),'baseline_worktree':str(B),'branch':BR,'start_clean':True,'end_clean':True,'guard_worktree_end_clean':True,'source_changes':[],'commits_authored':[],'history_rewritten':False},
      'environment':{'python':PY+' (Python 3.11.12)','ruff':RUFF+' (Ruff 0.16.6)','lock_source':str(H/'uv.lock')+'; identical to '+str(B/'uv.lock')+'; SHA-256 '+sha(H/'uv.lock'),'install_performed':False,'validation_log':str(E/'python-environment-final.log')},
      'preserved_evidence':selected,
      'checks':checks,
      'differential':{'full_pairs_run':pairs,'head_failures':[f"{x['node_id']} | {x['error_class']}" for x in d['head']['failures']],'base_failures':[f"{x['node_id']} | {x['error_class']}" for x in d['base']['failures']],'branch_only_failures':d['branch_only_failures'],'base_only_failures':d['base_only_failures'],'error_class_changes':[json.dumps(x,sort_keys=True) for x in d['error_class_changes']],'target_node':NODE,'target_head_isolated':target['head'],'target_base_isolated':target['base'],'status':d['status'],'machine_receipt':str(E/f'gateway-differential-{pairs}.json'),'rationale':'All 48 common failed nodes have identical error classes, but the base has one extra OSError from binding the shared Linux abstract socket hermes-test-notify. Concurrent scheduling was a worker error: separate state directories do not isolate abstract sockets. Sequential isolated diagnostics pass at both commits but cannot replace the complete pair. No second full pair was permitted because no candidate-only failure remained.'},
      'publication':{'push_attempted':False,'push_command':'git -c core.hooksPath=/tmp/agents-board-cranker-55-postmerge-verification-r2/git/hooks push delorenj HEAD:refs/heads/'+BR,'push_exit_code':None,'force_push':False,'no_verify':False,'guard_disabled':False,'hook_source_override':True,'hook_source_path':str(G/'git/hooks'),'hook_source_merge_sha':MERGE,'hook_executed':False,'remote_ref':'delorenj/'+BR,'remote_after_sha':P,'remote_matches_candidate':False,'log':str(E/'publication-not-run.log')},
      'pr':{'number':102409,'url':'https://github.com/NousResearch/hermes-agent/pull/102409','state':pr['state'],'head_sha':pr['headRefOid'],'title':pr['title'],'body_names_ticket':False,'body_names_range':False,'metadata_updated':False,'approved':False,'merged':False,'mergeability':pr['mergeable']+' / '+pr['mergeStateStatus'],'checks':[json.dumps(x,sort_keys=True) for x in pr['statusCheckRollup']],'readback_log':str(E/'pr-blocked-final.log')},
      'forbidden_scope':{'hermes_primary_touched':False,'agents_primary_touched':False,'plane_touched':False,'bloodbank_touched':False,'client_board_touched':False,'source_touched':False,'review_or_merge_performed':False,'audit_log':str(E/'forbidden-scope-audit.json')},
      'deferred_gates':['New authorized recovery attempt with sequential complete candidate/base execution; exact broad equivalence is still required','Guard-pinned fast-forward push and verified remote SHA after successful evidence gates','PR title/body update and readback after verified push','Fresh independent specification review, then separate independent quality/security review'],
      'risks':['The complete broad comparison is not equivalent: one base-only infrastructure failure remains in its immutable evidence.','Worker-selected concurrent scheduling caused contention on a fixed Linux abstract socket; any next attempt must run the complete suites sequentially.','No publication or PR metadata recovery was completed; the PR still contains its prior stale range/test assertions.'],
      'notes':['The guard repair is verified integrated and clean; it was not exercised by a push because the evidence gate failed.', 'hook_source_override=true describes the explicitly authorized pin only; no push command was executed.', 'All 14076 preserved input files re-hashed unchanged; full inventory: '+str(E/'preserved-inputs-final.json'), 'Every recorded command, explicit exit, complete log and SHA-256: '+str(E/'command-manifest.json'), 'Blocker diagnosis and isolated diagnostic receipts: '+str(E/'publication-blocked.json'), 'Sandbox SSH preflight failed (128), then host preflight passed. Sandboxed focused test stalled after 47 passes and was interrupted (2); the unchanged host command passed all 50.', 'Full pair run exactly once. No repeat was allowed by the candidate-only conditional; isolated diagnostic passes were not substituted for broad evidence.', 'Publication and PR metadata scripts were prepared as evidence but never executed.', 'Explicit pytest commands override general run_tests.sh guidance. Global git unpushed/landing was out of scope.', 'No source, tests, dependency environment, history, controller state, Plane, Bloodbank, client board, reviews or approvals were changed. Canonical handback was not written; launcher owns installation.']}
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

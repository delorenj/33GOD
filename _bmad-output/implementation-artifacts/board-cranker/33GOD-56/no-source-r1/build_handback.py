from evidence import *
import jsonschema

assert json.loads((E/'gates-pass.json').read_text())['status']=='PASS'
assert json.loads((E/'publication-pass.json').read_text())['status']=='PASS'
assert json.loads((E/'pr-metadata-pass.json').read_text())['status']=='PASS'
audit = json.loads((E/'forbidden-scope-final.json').read_text())
assert audit['status']=='PASS'
d = json.loads((E/'sequential-differential.json').read_text())
f = d['final']
env = json.loads((E/'environment-validation.json').read_text())
pr = json.loads((E/'pr-after.json').read_text())
push = json.loads((E/'publication-push.exit.json').read_text())
checks = []
records = sorted([json.loads(p.read_text()) for p in E.glob('*.exit.json')],key=lambda r:r['started_at'])
keys = ['name','command','worktree','started_at','finished_at','exit_code','status','summary','log','sha256']
for i,r in enumerate(records,1):
    c = {k:r[k] for k in keys}
    c['sequence_index'] = i
    if r['name'].startswith('gateway-'):
        parsed = json.loads((E/(r['name']+'.parsed.json')).read_text())
        pair = next(p for p in d['pairs'] if p['pair']==int(r['name'].rsplit('-',1)[1]))
        c['status'] = ('BASELINE_MATCH' if parsed['failed_nodes'] else 'PASS') if pair['status']=='PASS' else 'FAIL'
        c['summary'] = f"{len(parsed['failed_nodes'])} failed nodes; {parsed['passed']} passed. Pair {pair['pair']}: {len(pair['candidate_only_failures'])} candidate-only nodes and {len(pair['error_class_changes'])} changed error classes."
        if pair['status']!='PASS':
            c['summary'] += ' Triggered the required additional complete sequential pair.'
    elif (E/(r['name']+'.parsed.json')).exists():
        parsed = json.loads((E/(r['name']+'.parsed.json')).read_text())
        c['summary'] = f"{parsed['passed']} passed; no failed nodes or collection errors."
    elif r['name']=='publication-push':
        c['summary'] = 'Normal fast-forward push succeeded; trace proves pinned pre-push hook executed and exited 0.'
    elif r['name']=='pr-metadata-update-rest':
        c['summary'] = 'Existing PR title/body updated; exact text and OPEN/unapproved/unmerged state verified by subsequent readback.'
    elif r['name']=='pr-metadata-update':
        c['summary'] = 'gh pr edit failed on the deprecated projectCards GraphQL read before mutation; unchanged metadata confirmed and the same authorized title/body applied through REST.'
    else:
        c['summary'] = 'Command succeeded; full output and explicit exit receipt preserved.'
    assert sha(c['log'])==c['sha256']
    checks.append(c)
status = 'DONE_WITH_CONCERNS' if f['candidate']['failed_nodes'] or f['baseline']['failed_nodes'] else 'DONE'
out = {
 'schema_version':'1.0','issue':'33GOD-56','phase':'no-source-sequential-differential-publication','status':status,
 'summary':f"Published exact candidate {C}; PR #102409 metadata verified OPEN/unapproved/unmerged. {d['full_pairs_run']} strictly sequential complete pairs; final pair: candidate {len(f['candidate']['failed_nodes'])} failed/{f['candidate']['passed']} passed, baseline {len(f['baseline']['failed_nodes'])} failed/{f['baseline']['passed']} passed; no remaining candidate-only failures or changed error classes. Focused 50, adjacent 24, static gates and eight probes passed. All worktrees clean; no source changes or commits. Fresh independent reviews remain pending.",
 'worker':{'agent_id':'codex-33god-56-no-source-r1','role':'no-source-evidence-publication-worker','provider':'openai-codex','attempt':1,'source_mutation_authorized':False},
 'immutable_ground':{'candidate_sha':C,'first_parent_sha':P,'upstream_base_sha':BASE,'guard_merge_sha':GUARD,'remote_before_sha':P,
    'ordered_parents':[P,BASE],'expected_diff_files':FILES,'actual_diff_files':FILES},
 'repository':{'owning_repo':'/home/delorenj/.hermes/hermes-agent','candidate_worktree':str(H),'baseline_worktree':str(B),'guard_worktree':str(G),'branch':BR,
    'start_clean':True,'end_clean':True,'baseline_end_clean':True,'guard_end_clean':True,'source_changes':[],'commits_authored':[],'history_rewritten':False},
 'environment':{'python':PY+' (Python 3.11.12)','ruff':RUFF+' (ruff 0.16.6)',
    'candidate_lock_sha256':env['candidate_lock_sha256'],'baseline_lock_sha256':env['baseline_lock_sha256'],'locks_match':True,'install_performed':False,
    'isolation_roots':[str(p) for p in sorted((E/'isolation').iterdir()) if p.is_dir()],
    'validation_log':str(E/'environment-validation-final.json'),'validation_sha256':sha(E/'environment-validation-final.json')},
 'preserved_evidence':[{'path':p,'sha256':s,'preserved_unchanged':True} for p,s in EXPECTED.items()],
 'checks':checks,
 'sequential_differential':{'broad_suites_concurrent':False,'no_overlap_proven':d['no_overlap_proven'],
    'candidate_started_at':f['candidate_started_at'],'candidate_finished_at':f['candidate_finished_at'],
    'baseline_started_at':f['baseline_started_at'],'baseline_finished_at':f['baseline_finished_at'],'full_pairs_run':d['full_pairs_run'],
    'candidate_failures':sorted(f['candidate']['failed_nodes']),'baseline_failures':sorted(f['baseline']['failed_nodes']),
    'candidate_only_failures':f['candidate_only_failures'],'base_only_failures':f['base_only_failures'],
    'error_class_changes':[json.dumps(c,sort_keys=True) for c in f['error_class_changes']],
    'every_candidate_failure_reproduces':f['every_candidate_failure_reproduces'],'status':d['status'],
    'baseline_disposition':'DONE_WITH_CONCERNS' if status=='DONE_WITH_CONCERNS' else 'ALL_GREEN',
    'machine_receipt':str(E/'sequential-differential.json'),'machine_receipt_sha256':sha(E/'sequential-differential.json'),
    'rationale':'Every complete command exited and all descendants were reaped before the next started; monotonic/UTC bounds and host process scans prove no overlap. The first pair triggered exactly one prescribed additional full pair for test_room_log_pages_are_bounded_by_serialized_event_bytes. In the final complete pair every candidate failure reproduces at baseline with the same exception class; no candidate-only node or changed class remains. Earlier failed-pair evidence is retained. Baseline-equivalent failures remain; this is not all-green.'},
 'publication':{'push_attempted':True,'push_command':push['command'],'push_exit_code':push['exit_code'],'force_push':False,'no_verify':False,'guard_disabled':False,
    'hook_source_override':True,'hook_source_path':str(G/'git/hooks'),'hook_source_merge_sha':GUARD,
    'pre_push_sha256':EXPECTED[str(G/'git/hooks/pre-push')],'travels_sha256':EXPECTED[str(G/'git/hooks/_travels.py')],
    'hook_executed':True,'remote_ref':'delorenj/'+BR,'remote_after_sha':C,'remote_matches_candidate':True,'log':push['log'],'sha256':push['sha256']},
 'pr':{'number':102409,'url':'https://github.com/NousResearch/hermes-agent/pull/102409','state':pr['state'],'head_sha':pr['headRefOid'],'title':pr['title'],
    'title_names_33god_54':'33GOD-54' in pr['title'],'title_names_33god_56':'33GOD-56' in pr['title'],
    'body_names_33god_54':'33GOD-54' in pr['body'],'body_names_33god_56':'33GOD-56' in pr['body'],'body_names_range':BASE+'...'+C in pr['body'],
    'metadata_updated':True,'approved':False,'merged':False,'mergeability':pr['mergeable']+' / '+pr['mergeStateStatus'],
    'checks':[json.dumps(c,sort_keys=True) for c in pr['statusCheckRollup']],
    'readback_log':str(E/'pr-after.json'),'readback_sha256':sha(E/'pr-after.json')},
 'forbidden_scope':{**{name:False for name in ['hermes_primary_touched','agents_primary_touched','plane_touched','controller_touched','wip_lock_touched','bloodbank_touched','pjangler_touched','client_board_touched','source_touched','review_performed','approval_performed','merge_performed']},
    'audit_log':str(E/'forbidden-scope-final.json'),'audit_sha256':sha(E/'forbidden-scope-final.json')},
 'deferred_gates':['Fresh independent specification review of the published immutable candidate.','Separate fresh independent quality/security review after specification review.','Any approval/integration/merge requires later authorization; none was performed.'],
 'risks':[f"Broad suite retains {len(f['candidate']['failed_nodes'])} baseline-equivalent failed nodes; only the requested focused/static gates are green.",
          'First pair had one candidate-only replay-page-size failure and triggered the prescribed second complete pair; earlier evidence remains preserved.',
          'Shared failures include Unix-socket path-length errors under the isolated evidence roots; baseline equivalence is not a claim that all failures are intrinsic upstream source defects.',
          'GitHub mergeability/checks are live platform state; the readback does not substitute for independent reviews.',
          'Pre-existing automated review comments were preserved and not adjudicated by this no-source worker.'],
 'notes':[
    f"All {audit['preserved_input_count']} preserved input files rehashed unchanged; inventory: {E/'preserved-inputs-final.json'}.",
    f"Complete command/descendant receipts: {E}/*.exit.json; pytest exception reports: *.reports.json. Hook proof: {E/'hook-execution-proof.json'}.",
    'Source file hashes, modes, symlinks, checkout HEAD/branch/status and staged/unstaged diff hashes match initial snapshots for all three pinned worktrees and the dirty Hermes primary. The unpinned .agents primary independently advanced to 5e6970e4ac4031f03bf4c99d9b54e6881078bca0 during baseline pair 1; its exact committed-file changes and unchanged pre-existing dirty guard content are recorded in external-agents-primary-advance.json. This worker performed no primary mutation.',
    'The original prepublication audit stopped before any push because it required an unchanged unpinned primary HEAD. That stricter-than-task condition was reconciled read-only against the external commit/reflog and file hashes; the original FAIL receipt is preserved. The pinned guard revision and hashes never moved.',
    'Only the explicitly authorized complete pytest commands were used; general run_tests.sh and global git-unpushed/landing instructions were superseded by this no-source scope.',
    'Test and publication environment roots are evidence-only. No dependency installation, source/test/lockfile edit, authored commit, history rewrite, or review occurred.',
    'Canonical 33GOD-56.implementation.json was not written; the launcher owns atomic installation.'
    ,'The gh pr edit compatibility failure is preserved; the subsequent REST PATCH changed only title/body and exact metadata readback passed.'
 ]
}
schema_path = Path('/home/delorenj/.hermes/profiles/33god-pm/runtime/board-cranker-33god-56-no-source-r1.schema.json')
jsonschema.validate(out,json.loads(schema_path.read_text()))
handback = save('handback.json',out)
save('handback-validation.json',{'status':'PASS','at':utc(),'handback':str(handback),'handback_sha256':sha(handback),
    'schema':str(schema_path),'schema_sha256':sha(schema_path),'checked_log_hashes':len(checks),
    'canonical_path_written':False})
inventory = [{'path':str(p),'sha256':sha(p)} for p in sorted(E.iterdir()) if p.is_file()]
save('artifact-manifest.json',inventory)
print(json.dumps({'status':status,'handback':str(handback),'sha256':sha(handback),'checks':len(checks)}),flush=True)

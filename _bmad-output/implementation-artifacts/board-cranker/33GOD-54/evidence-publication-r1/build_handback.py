from receipt_runner import *

def read(n): return json.loads((E/n).read_text())
records=[]
for p in sorted(E.glob('*.json')):
    r=json.loads(p.read_text())
    if isinstance(r,dict) and {'command','exit_code','log','sha256','argv'}<=r.keys():
        assert sha(r['log'])==r['sha256']
        records.append(r)
save('command-manifest.json',records)
save('evidence-artifact-manifest.json',[{'path':str(p),'sha256':sha(p)} for p in sorted(E.iterdir()) if p.is_file() and p.name not in ['handback.preview.json']])
ground=read('immutable-ground.json'); diff=read('full-comparison.json'); pr=read('pr-after-blocked-push-readback.json')
assert diff['status']=='PASS'
assert read('publication-blocked.json')['push_exit_code']==1
assert read('forbidden-scope-audit.json')['status']=='PASS'
rec={r['name']:r for r in records}
selected=['owner-preflight','head-sha-preflight','base-sha-preflight','head-ordered-parents','head-diff-files','head-clean-preflight','base-clean-preflight','remote-preflight-network','pr-preflight-network','focused-head','adjacent-head','ruff-head','compile-head','diff-check-head','gateway-head-1','gateway-base-1','comparison-finalization','push','remote-after-blocked-push','pr-after-blocked-push','final-audit']
checks=[]
for name in selected:
    r=rec[name]
    c={k:r[k] for k in ['name','command','worktree','attempt','exit_code','log','sha256']}
    c['status']='BASELINE_MATCH' if name.startswith('gateway-') else 'PASS' if r['exit_code']==0 else 'FAIL'
    summaries={'focused-head':'50 passed','adjacent-head':'24 passed','ruff-head':'All checks passed','compile-head':'Four specified Python files compiled successfully; only ignored bytecode caches permitted','diff-check-head':'No whitespace errors in the exact immutable range','gateway-head-1':diff['head_summary'],'gateway-base-1':diff['base_summary'],'comparison-finalization':'48 identical failed node/error-class pairs; branch-only/base-only/class-change sets empty; one full pair; no repeat triggered','push':'Global git guard rejected 13 reported missing repository-local imports; no bypass or source changes','final-audit':'Both worktrees clean, exact refs/parents/diff unchanged, 185 prior artifacts unchanged, executable targets/locks/package inventory unchanged','remote-after-blocked-push':'Remote still equals pre-dispatch cc00fe6ef855e506ad1bf8166473eecf725af8a8','pr-after-blocked-push':'OPEN, unchanged head/title/body, unapproved; mergeability CONFLICTING / DIRTY; no checks reported'}
    c['summary']=summaries.get(name,'Required preflight fact verified; full command output is retained')
    checks.append(c)
prior=read('preserved-evidence-final.json')
rely=['/33GOD-53/red.log','/33GOD-53/green.log','/33GOD-53/hermes-gateway-differential.json','/33GOD-53/integration-conflict-r3/preflight.log','/33GOD-53/integration-conflict-r3/focused.log','/33GOD-53/integration-conflict-r3/adjacent.log','/33GOD-53/integration-conflict-r3/branch-only-head-rerun.log','/33GOD-53/integration-conflict-r3/gateway-head.log','/33GOD-53/integration-conflict-r3/gateway-baseline.log','/33GOD-53/integration-conflict-r3/gateway-differential.json']
isolated=lambda role:[{k:r[k] for k in ['attempt','worktree','exit_code','error_class','log','sha256']} for r in diff['target_'+role+'_isolated']]
artifacts=ground['artifact_hashes']+[{'path':str(E/n),'sha256':sha(E/n)} for n in ['command-manifest.json','evidence-artifact-manifest.json','preserved-evidence.json','preserved-evidence-final.json','gateway-differential-1.json','full-comparison.json','forbidden-scope-audit.json','support-tool-exit-receipts.json']]
result={
'schema_version':'1.0','issue':'33GOD-54','phase':'evidence-and-publication','status':'BLOCKED',
'summary':'Evidence differential PASS: 48 identical head/base failures, zero differential; focused 50 and adjacent 24 passed. Publication BLOCKED: normal push exited 1 on global git-guard missing-import findings. Fork and open PR remain at cc00fe6; metadata unchanged; both worktrees clean.',
'worker':{'agent_id':'codex-33god-54-evidence-publication-r1','role':'evidence-publication-worker','provider':'openai-codex','attempt':1},
'immutable_ground':{'candidate_sha':C,'first_parent_sha':P,'upstream_base_sha':BASE,'remote_before_sha':P,'artifact_hashes':artifacts},
'repository':{'owning_repo':'/home/delorenj/.hermes/hermes-agent','candidate_worktree':str(H),'baseline_worktree':str(B),'branch':BR,'ordered_parents':[P,BASE],'expected_diff_files':FILES,'actual_diff_files':FILES,'start_clean':True,'end_clean':True,'source_changes':[],'commits_authored':[],'history_rewritten':False},
'environment':{'python':PY+' (Python 3.11.12)','ruff':RUFF+' (Ruff 0.16.6)','lock_source':str(H/'uv.lock')+'; identical to '+str(B/'uv.lock')+'; original environment reused without installation','install_performed':False,'validation_log':str(E/'python-environment.log')},
'preserved_evidence':[r for r in prior if any(r['path'].endswith(n) for n in rely)],
'checks':checks,
'differential':{'full_pairs_run':1,'head_failures':[r['node_id'] for r in diff['head_failures']],'base_failures':[r['node_id'] for r in diff['base_failures']],'branch_only_failures':[],'base_only_failures':[],'error_class_changes':[],'target_node':NODE,'target_head_isolated':isolated('head'),'target_base_isolated':isolated('base'),'status':'PASS','machine_receipt':str(E/'full-comparison.json'),'rationale':'One identical full-suite head/base pair has 48 byte-equal node/error-class records (canonical SHA-256 7ccd7b9736cc560a833f0bd4783829f00927297ca1ece004363c28241d89e571). No branch-only, base-only, or class-change outcomes. Focused/static gates pass. Target isolated node passed three consecutive times on each revision and is absent from both full-suite failure sets. No second pair was required.'},
'publication':{'push_attempted':True,'push_exit_code':1,'force_push':False,'remote_ref':'delorenj/'+BR,'remote_after_sha':P,'remote_matches_candidate':False,'log':str(E/'push.log')},
'pr':{'number':102409,'url':pr['url'],'state':pr['state'],'head_sha':pr['headRefOid'],'title':pr['title'],'body_names_ticket':'33GOD-54' in pr['body'],'body_names_range':BASE+'...'+C in pr['body'],'metadata_updated':False,'approved':False,'merged':False,'mergeability':pr['mergeable']+' / '+pr['mergeStateStatus'],'checks':[],'readback_log':str(E/'pr-after-blocked-push.log')},
'forbidden_scope':{'primary_checkout_touched':False,'plane_touched':False,'bloodbank_touched':False,'client_board_touched':False,'source_touched':False,'review_or_merge_performed':False,'audit_log':str(E/'forbidden-scope-audit.json')},
'deferred_gates':['Controller-owned resolution of the pre-push git-guard rejection; separate authorized repair/investigation scope, then publication retry.','After successful publication: fresh independent specification review.','After specification review: quality/security review by a different independent reviewer.'],
'risks':['Push guard reported 13 missing local imports involving dashboard_auth, Discord/email/Telegram adapter modules, and video_gen. Its correctness was not adjudicated; neither the guard nor accepted source was changed. Full diagnostics are in push.log.','Broad gateway suite remains non-green: 48 matching failures on both revisions. Four shared failures involve long runtime paths, including Unix socket limits and log-path truncation.','PR remains CONFLICTING / DIRTY on the old fork head, with stale range/test/review claims. Metadata could not be updated because verified push was a prerequisite.'],
'notes':['All verification commands, argv, explicit exits, full log paths, and SHA-256 hashes are retained in command-manifest.json; its hash and the complete artifact-manifest hash are included above. Individual isolated-node commands are included there.','All 185 prior 33GOD-53 logs/handbacks were hashed and rechecked unchanged. The complete input list is preserved-evidence-final.json; directly relied-on inputs are also enumerated in preserved_evidence.','Explicit story commands override the general scripts/run_tests.sh instruction. Head/base use the same absolute Python executable and credential-free deterministic allowlist; only isolated HERMES_HOME/TMPDIR roots differ. HOME was not changed.','Initial sandbox SSH read failed (exit 128); the authorized read-only network retry passed. All tests used the same execution permissions outside the sandbox for localhost fixtures.','Receipt tooling corrected summary extraction and separated an interleaved pytest RuntimeWarning; raw test logs remained unchanged and parsed failure counts were checked against terminal summaries. The stale parser monitor failed, then finalization passed without rerunning gateway tests. Support exit receipts are retained.','Only ignored test/bytecode caches were permitted in worktrees. No commits, history changes, environment installation, guard bypass, PR mutation, board/controller writes, reviews, or merge occurred.','The launcher owns canonical 33GOD-54.implementation.json installation; this worker did not write it. A handback preview exists only in this run evidence directory.']}
# Check all schema shapes and constants used in this handback before emission.
assert result['status']=='BLOCKED' and result['publication']['push_exit_code']==1
assert result['repository']['start_clean'] and result['repository']['end_clean']
assert result['differential']['status']=='PASS' and len(result['differential']['head_failures'])==48
assert result['differential']['head_failures']==result['differential']['base_failures']
assert all(r['preserved_unchanged'] for r in prior)
assert len(isolated('head'))==len(isolated('base'))==3
assert all(r['exit_code']==0 and r['error_class']=='NONE' for role in ['head','base'] for r in isolated(role))
assert not result['pr']['metadata_updated'] and result['pr']['state']=='OPEN' and result['pr']['head_sha']==P
assert all(len(a['sha256'])==64 and sha(a['path'])==a['sha256'] for a in artifacts)
save('handback.preview.json',result)
print(json.dumps({'status':result['status'],'command_receipts':len(records),'prior_preserved':len(prior),'checks':len(checks),'handback_preview':str(E/'handback.preview.json'),'handback_sha256':sha(E/'handback.preview.json')},indent=2))

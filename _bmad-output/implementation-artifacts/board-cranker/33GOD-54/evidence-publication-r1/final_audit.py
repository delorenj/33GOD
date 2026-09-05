from receipt_runner import *
for role,tree,expected in [('head',H,C),('base',B,BASE)]:
    assert checked(role+'-sha-final',['git','rev-parse','HEAD'],tree)==expected
    assert checked(role+'-branch-final',['git','branch','--show-current'],tree)==(BR if role=='head' else '')
    assert checked(role+'-clean-final',['git','status','--porcelain=v1','--untracked-files=all'],tree)==''
    markers=json.loads((E/(role+'-operation-markers.json')).read_text())['paths']
    assert not any(pathlib.Path(p).exists() for p in markers.values())
assert checked('head-parents-final',['git','show','-s','--format=%P',C]).split()==[P,BASE]
assert checked('head-diff-files-final',['git','diff','--name-only',BASE+'...'+C]).splitlines()==FILES
assert json.loads(checked('owner-final',['cat',str(OWNER)]))['owner_agent_id']=='33god-pm'
preserved=json.loads((E/'preserved-evidence.json').read_text())
for r in preserved:
    r['preserved_unchanged']=sha(r['path'])==r['sha256']
save('preserved-evidence-final.json',preserved)
assert all(r['preserved_unchanged'] for r in preserved),'Prior evidence changed'
ground=json.loads((E/'immutable-ground.json').read_text())
assert all(sha(r['path'])==r['sha256'] for r in ground['artifact_hashes']),'Immutable inputs changed'
assert str(pathlib.Path(PY).resolve())==ground['artifact_hashes'][4]['path']
assert str(pathlib.Path(RUFF).resolve())==ground['artifact_hashes'][5]['path']
original=json.loads((E/'python-environment.json').read_text())
current=run('python-environment-final',original['argv'])
assert current['exit_code']==0 and payload(current)==payload(original),'Environment package inventory changed'
save('forbidden-scope-audit.json',{'status':'PASS','start_clean':True,'end_clean':True,'candidate_sha':C,'base_sha':BASE,
    'primary_checkout_touched':False,'plane_touched':False,'bloodbank_touched':False,'client_board_touched':False,
    'source_touched':False,'review_or_merge_performed':False,'source_changes':[],'commits_authored':[],
    'history_rewritten':False,'controller_state_written':False,'wip_locks_written':False,'decision_or_event_trails_written':False,
    'canonical_handback_written':False,'environment_install_performed':False,'prior_evidence_count':len(preserved),
    'prior_evidence_unchanged':True,'immutable_artifact_hashes_unchanged':True,'environment_package_inventory_unchanged':True,
    'method':'Worker action ledger plus exact start/end refs, worktree status, git-operation marker absence, prior input/binary/lock hashes, and Python package inventory. Shared git metadata access and fixed shared venv executable reads are authorized; primary working files were not accessed or changed.'})
print('FINAL_AUDIT_PASS')

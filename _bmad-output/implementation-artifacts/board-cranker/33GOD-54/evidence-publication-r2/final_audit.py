from publication_host import *
if __name__=='__main__':
    ground('final')
    verify_preserved('final')
    audits={}
    for role,tree in [('hermes',pathlib.Path('/home/delorenj/.hermes/hermes-agent')),('agents',pathlib.Path('/home/delorenj/.agents'))]:
        actual=snapshot(role,tree,'final')
        before=json.loads((E/(role+'-primary-snapshot-start.json')).read_text())
        audits[role]={'status_unchanged':actual['status']==before['status'],'head_unchanged':actual['head']==before['head'],'index_unchanged':actual['index_sha256']==before['index_sha256'],'file_hashes_and_modes_unchanged':actual['files']==before['files']}
        assert all(audits[role].values()),audits
    original=json.loads((E/'python-environment.json').read_text())
    final=checked('python-environment-final',original['argv'])
    assert final==payload(original)
    for x in json.loads((E/'immutable-ground.json').read_text())['artifact_hashes']:
        assert sha(x['path'])==x['sha256'],x
    save('forbidden-scope-audit.json',{
       'status':'PASS','primary_snapshots':audits,'three_worktrees_end_clean':True,
       'source_changes':[],'commits_authored':[],'history_rewritten':False,
       'hermes_primary_touched':False,'agents_primary_touched':False,
       'plane_touched':False,'bloodbank_touched':False,'client_board_touched':False,
       'controller_state_touched':False,'wip_locks_touched':False,'review_or_merge_performed':False,
       'environment_install_or_mutation':False,
       'git_metadata_note':'Authorized push may update shared remote-tracking metadata; neither primary working tree, index, HEAD, nor source files changed.',
       'allowed_write_roots':[str(E)],'ignored_test_caches_permitted':True,
       'audit_basis':'Recorded command receipts plus start/end primary file hashes, modes, HEAD/index hashes and statuses; exact three-worktree SHA/branch/cleanliness checks; preserved-input rehash; environment inventory comparison. No Plane, Bloodbank, client-board, controller or review/merge API was invoked.',
       'global_git_unpushed':'Not run: global sweep/landing conflicts with explicit recovery scope.',
       'sandbox_recovery':'Only the verified owned stalled pytest process received SIGINT; preserved exit 2. Same focused command passed in host execution.'})
    print('FINAL_AUDIT_PASS',flush=True)

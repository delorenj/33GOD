from evidence import *

assert json.loads((E/'publication-pass.json').read_text())['remote_after_sha']==C
verify_ground()
current = remote('metadata-recovery-before',C)
prior = json.loads((E/'pr-premetadata.json').read_text())
assert current['title']==prior['title'] and current['body']==prior['body']
requested = json.loads((E/'pr-requested-metadata.json').read_text())
body = Path(requested['body_path']).read_text()
assert sha(requested['body_path'])==requested['body_sha256']
path = save('pr-rest-payload.json',{'title':requested['title'],'body':body})
r = run('pr-metadata-update-rest',['gh','api','--method','PATCH','repos/NousResearch/hermes-agent/pulls/102409','--input',str(path)])
assert r['exit_code']==0,r
actual = remote('after',C)
assert actual['title']==requested['title'] and actual['body']==body
for text in [actual['title'],actual['body']]:
    assert '33GOD-54' in text and '33GOD-56' in text and BASE+'...'+C in text
save('pr-metadata-pass.json',{'status':'PASS','at':utc(),'metadata_updated':True,
     'readback':str(E/'pr-after.json'),'readback_sha256':sha(E/'pr-after.json'),
     'cli_compatibility_failure':'gh pr edit failed in the deprecated projectCards GraphQL read, before mutation; unchanged metadata verified before the REST fallback.',
     'rest_payload_fields':['title','body'],'rest_update_exit_code':r['exit_code']})
print('PR_METADATA_VERIFIED',flush=True)

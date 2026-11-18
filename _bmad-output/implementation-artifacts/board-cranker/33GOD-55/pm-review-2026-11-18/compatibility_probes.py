"""Compatibility probes for existing custom refs and supported object stores."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('fixtures_compat',ROOT/'target/git/tests/test_pre_push.py')
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)
results={}
case=m.MergeTopologyTests('test_existing_ref_clean_merge_excludes_remote_known_parent')
case.setUp()
try:
    # Real notes-ref update. No bypass: immutable hook selected in local fixture config.
    case.git('notes','--ref=review','add','-m','first note',case.feature)
    old=case.git('rev-parse','refs/notes/review')
    case.publish(case.remote,old,'notes-transfer')
    case.git('update-ref','refs/notes/review',old,cwd=case.remote)
    case.git('update-ref','-d','refs/heads/notes-transfer',cwd=case.remote)
    case.git('notes','--ref=review','append','-m','second note',case.feature)
    new=case.git('rev-parse','refs/notes/review')
    for label in ['base','target']:
        case.git('config','core.hooksPath',str(ROOT/label/'git/hooks'))
        p=case.run_cmd('git','push','origin','refs/notes/review',check=False)
        results['existing_notes_'+label]={'old':old,'new':new,'command':'git push origin refs/notes/review',
            'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
        case.git('update-ref','refs/notes/review',old,cwd=case.remote)
finally:
    case.doCleanups()

class SHA256Case(m.MergeTopologyTests):
    def run_cmd(self,*args,**kwargs):
        if args[:2]==('git','init'):
            args=('git','init','--object-format=sha256',*args[2:])
        return super().run_cmd(*args,**kwargs)

m.HOOK=ROOT/'target/git/hooks/pre-push'
for label,cls in [('sha256',SHA256Case),('custom_object_store',m.MergeTopologyTests)]:
    case=cls('test_existing_ref_clean_merge_excludes_remote_known_parent')
    case.setUp()
    try:
        if label=='custom_object_store':
            custom=case.root/'custom-objects'
            shutil.copytree(case.repo/'.git/objects',custom)
            case.env['GIT_OBJECT_DIRECTORY']=str(custom)
            shutil.rmtree(case.repo/'.git/objects')
            before={str(p.relative_to(custom)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in custom.rglob('*') if p.is_file()}
        capture=io.StringIO()
        with contextlib.redirect_stdout(capture):
            p=case.hook()
        results[label]=json.loads(capture.getvalue().split('FIXTURE_RECEIPT ',1)[1])
        if label=='custom_object_store':
            after={str(p.relative_to(custom)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in custom.rglob('*') if p.is_file()}
            results[label]['custom_store_unchanged']=before==after
    finally:
        case.doCleanups()
(ROOT/'compatibility-results.json').write_text(json.dumps(results,indent=2)+'\n')
for label,r in results.items():
    print(label,json.dumps({k:r[k] for k in ['exit_code','stderr']}))

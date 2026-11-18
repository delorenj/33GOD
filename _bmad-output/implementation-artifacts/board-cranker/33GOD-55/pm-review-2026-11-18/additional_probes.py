"""Extra isolated entrypoint checks and independent RED proof."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent
TARGET = ROOT/'target'
s = importlib.util.spec_from_file_location('fixtures', TARGET/'git/tests/test_pre_push.py')
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
results = {}

# Use exactly the committed tests with the immutable base hooks, no test edits.
m.HOOK = ROOT/'base/git/hooks/pre-push'
buf = io.StringIO()
suite = unittest.TestSuite(m.MergeTopologyTests(n) for n in [
    'test_existing_ref_clean_merge_excludes_remote_known_parent',
    'test_new_ref_clean_merge_excludes_remote_known_parent'])
with contextlib.redirect_stdout(buf):
    r = unittest.TextTestRunner(stream=buf, verbosity=2).run(suite)
(ROOT/'independent-red.log').write_text(buf.getvalue())
results['base_red'] = {'tests': r.testsRun, 'failures': len(r.failures), 'errors': len(r.errors),
                       'expected_false_block': 'FALSE BLOCK' in buf.getvalue()}

case = m.MergeTopologyTests('test_existing_ref_clean_merge_excludes_remote_known_parent')
case.setUp()
try:
    # Same real porcelain push, only choose immutable hook source per run.
    blob = case.git('hash-object', '-w', '--stdin', input='release metadata\n')
    case.git('tag', '-a', 'metadata', blob, '-m', 'metadata')
    for label in ['base', 'target']:
        case.git('config', 'core.hooksPath', str(ROOT/label/'git/hooks'))
        p = case.run_cmd('git', 'push', 'origin', 'refs/tags/metadata', check=False)
        results['push_noncommit_tag_'+label] = {'argv': ['git','push','origin','refs/tags/metadata'],
            'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
        if label == 'base':
            case.git('update-ref', '-d', 'refs/tags/metadata', cwd=case.remote)
    case.git('config', '--unset', 'core.hooksPath')
    m.HOOK = TARGET/'git/hooks/pre-push'
    for kind in ['replacement','grafted','shallow']:
        if kind == 'replacement':
            case.git('update-ref', 'refs/replace/'+case.base, case.feature)
        elif kind == 'grafted':
            (case.repo/'.git/info/grafts').write_text(case.merge+' '+case.feature+'\n')
        else:
            (case.repo/'.git/shallow').write_text(case.base+'\n')
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            p = case.hook()
        results[kind] = json.loads(capture.getvalue().split('FIXTURE_RECEIPT ',1)[1])
        if kind == 'replacement':
            case.git('update-ref','-d','refs/replace/'+case.base)
        elif kind == 'grafted':
            (case.repo/'.git/info/grafts').unlink()
        else:
            (case.repo/'.git/shallow').unlink()
finally:
    case.doCleanups()
(ROOT/'additional-results.json').write_text(json.dumps(results,indent=2)+'\n')
for k,v in results.items():
    print(k, json.dumps(v if k == 'base_red' else {x:v[x] for x in ['exit_code','stderr']}))

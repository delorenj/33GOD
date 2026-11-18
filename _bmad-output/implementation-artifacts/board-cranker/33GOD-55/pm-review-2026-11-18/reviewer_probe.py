"""Read-only review probes over exported immutable hooks and private Git fixtures."""
from pathlib import Path
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'target'
BASE = ROOT / 'base'
BASE.mkdir(exist_ok=True)
data = subprocess.check_output(['git', '-C', '/home/delorenj/.agents', 'archive',
                                '36d3ed6627b1ee1819952617d7d4ebfcebc2708f', 'git'])
tarfile.open(fileobj=io.BytesIO(data)).extractall(BASE, filter='data')
spec = importlib.util.spec_from_file_location('review_fixture', TARGET/'git/tests/test_pre_push.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
results = []

def run_probe(name, setup):
    case = m.MergeTopologyTests('test_existing_ref_clean_merge_excludes_remote_known_parent')
    case.setUp()
    try:
        params, extra = setup(case)
        record = {'probe': name, **extra}
        for label, hook in [('base', BASE/'git/hooks/pre-push'), ('landed', TARGET/'git/hooks/pre-push')]:
            m.HOOK = hook
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                p = case.hook(**params)
            record[label] = json.loads(buf.getvalue().split('FIXTURE_RECEIPT ', 1)[1])
        if name == 'cross-parent-dependency-deletion':
            runtime = case.run_cmd('node', '--input-type=module',
                                   input='import "./dep.js";\n', check=False)
            case.git('config', 'core.hooksPath', str(TARGET/'git/hooks'))
            push = case.run_cmd('git', 'push', 'origin', 'feature', check=False)
            record['runtime'] = {'argv': ['node', '--input-type=module'], 'stdin': 'import "./dep.js";\n',
                                 'exit_code': runtime.returncode, 'stdout': runtime.stdout, 'stderr': runtime.stderr}
            record['porcelain_push'] = {'argv': ['git', 'push', 'origin', 'feature'],
                                       'exit_code': push.returncode, 'stdout': push.stdout, 'stderr': push.stderr}
        results.append(record)
    finally:
        case.doCleanups()

def crossed_parent_deletion(case):
    # Both published parents travel individually. The integration introduces an
    # importer; feature removes its dependency. The novel merge combines both.
    feature_files = dict(case.base_files, feature='feature\n')
    del feature_files['dep.js']
    feature = case.commit(feature_files, (case.base,), 'published dependency removal')
    integration_files = dict(case.base_files, **{'new-importer.js': 'import "./dep.js";\n'})
    integration = case.commit(integration_files, (case.base,), 'published importer')
    case.publish(case.remote, feature, 'feature')
    case.publish(case.upstream, integration, 'main')
    merge_files = dict(feature_files, **{'new-importer.js': integration_files['new-importer.js']})
    merge = case.commit(merge_files, (feature, integration), 'merge creates broken dependency')
    case.checkout(merge)
    return {'oid': merge, 'remote_sha': feature}, {
        'parents': [feature, integration], 'candidate': merge,
        'merge_files': merge_files,
        'combined_changed_paths': case.git('diff-tree', '-r', '--cc', '--name-only', merge),
        'first_parent_changed_paths': case.git('diff', '--name-only', feature, merge),
        'parent1_tree': case.git('ls-tree', '-r', '--name-only', feature),
        'parent2_tree': case.git('ls-tree', '-r', '--name-only', integration),
    }

def noncommit_tag(case):
    blob = case.git('hash-object', '-w', '--stdin', input='innocuous release metadata\n')
    case.git('tag', '-a', 'release-metadata', blob, '-m', 'metadata tag')
    tag = case.git('rev-parse', 'refs/tags/release-metadata')
    return {'oid': tag, 'remote_sha': m.ZERO, 'remote_ref': 'refs/tags/release-metadata'}, {'tag_oid': tag, 'target_oid': blob}

def novel_resolution(case):
    oid = case.commit(dict(case.merge_files, **{'resolution.js': 'import "./review-missing";\n'}),
                      (case.feature, case.integration), 'novel missing resolution')
    case.checkout(oid)
    return {'oid': oid}, {'candidate': oid}

def annotated_commit_tag(case):
    case.git('tag', '-a', 'release-commit', case.merge, '-m', 'commit tag')
    tag = case.git('rev-parse', 'refs/tags/release-commit')
    return {'oid': tag, 'remote_sha': m.ZERO, 'remote_ref': 'refs/tags/release-commit'}, {'candidate': tag}

run_probe('cross-parent-dependency-deletion', crossed_parent_deletion)
run_probe('noncommit-annotated-tag', noncommit_tag)
run_probe('novel-missing-resolution-control', novel_resolution)
run_probe('annotated-commit-tag-control', annotated_commit_tag)
(ROOT/'adversarial-results.json').write_text(json.dumps(results, indent=2)+'\n')
for r in results:
    print(json.dumps({k:v for k,v in r.items() if k not in ('base','landed')}))
    for label in ('base','landed'):
        print(label, 'exit', r[label]['exit_code'], 'state_unchanged', r[label]['state_unchanged'])
        print(r[label]['stderr'])

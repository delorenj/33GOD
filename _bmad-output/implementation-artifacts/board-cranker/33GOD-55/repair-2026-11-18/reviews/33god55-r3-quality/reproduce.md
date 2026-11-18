# Reproduce confirmed QUALITY regressions

Run from the immutable owning worktree, with `PYTHONDONTWRITEBYTECODE=1` and the active profile's `TMPDIR`. The fenced script uses real hook entrypoints and disposable Git repositories only. It does not alter the reviewed checkout.

```python
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

W = Path('/home/delorenj/.agents/.worktrees/33GOD-55-merge-guard-repair')
OUT = Path(os.environ['TMPDIR']) / '33god55-r3-quality'
BASE = '7f7bdf5807aabfb748cb25dad5086ff6bb17dd39'
spec = importlib.util.spec_from_file_location('quality_fixture', W / 'git/tests/test_pre_push.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
results = {}

with tempfile.TemporaryDirectory(prefix='quality-repro-hooks-', dir=os.environ['TMPDIR']) as tmp:
    baseline = Path(tmp)
    for name in ['pre-push', '_guard.sh', '_travels.py']:
        (baseline / name).write_bytes(subprocess.check_output(
            ['git', 'show', BASE + ':git/hooks/' + name], cwd=W))
    hooks = {'base': baseline / 'pre-push', 'repair': W / 'git/hooks/pre-push'}

    def case():
        c = m.MergeTopologyTests('test_existing_ref_clean_merge_excludes_remote_known_parent')
        c.setUp()
        return c

    def record(p):
        return {'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}

    def hook(c, label, oid, remote):
        m.HOOK = hooks[label]
        def snapshot():
            return {str(p.relative_to(c.repo)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in c.repo.rglob('*') if p.is_file() and not p.is_symlink()}
        before = snapshot()
        buf = io.StringIO()
        started = time.monotonic()
        with contextlib.redirect_stdout(buf):
            p = c.hook(oid, remote_sha=remote)
        receipt = json.loads(buf.getvalue().split('FIXTURE_RECEIPT ', 1)[1])
        receipt['seconds'] = time.monotonic() - started
        receipt['all_files_including_objects_unchanged'] = before == snapshot()
        assert receipt['all_files_including_objects_unchanged']
        return receipt

    c = case()
    try:
        def commit(files, parents, subject):
            def tree(items):
                entries, directories = [], {}
                for name, content in sorted(items.items()):
                    if '/' in name:
                        first, rest = name.split('/', 1)
                        directories.setdefault(first, {})[rest] = content
                    else:
                        blob = c.git('hash-object', '-w', '--stdin', input=content)
                        entries.append(f'100644 blob {blob}\t{name}\n')
                for name, children in sorted(directories.items()):
                    entries.append(f'040000 tree {tree(children)}\t{name}\n')
                return c.git('mktree', input=''.join(entries))
            args = ['commit-tree', tree(files), '-m', subject]
            for parent in parents:
                args += ['-p', parent]
            return c.git(*args)

        files = {
            '.gitignore': 'dist/\n',
            'README.md': 'compiled source fixture\n',
            'package.json': '{"type":"module"}\n',
            'build.mjs': ('import { mkdir, readFile, writeFile } from "node:fs/promises";\n'
                          'await mkdir("dist", {recursive:true});\n'
                          'await writeFile("dist/dep.js", await readFile("src/dep.ts", "utf8"));\n'),
            'src/dep.ts': 'export const value = 1;\n',
            'consumer.mjs': 'import { value } from "./dist/dep.js";\nconsole.log(value);\n',
        }
        root = commit(files, [], 'compiled baseline')
        a = commit({k: v for k, v in files.items() if k not in ['src/dep.ts', 'consumer.mjs']},
                   [root], 'published deletion')
        b = commit(dict(files, side='integration\n'), [root], 'published runnable importer')
        c.publish(c.remote, a, 'feature')
        c.publish(c.upstream, b, 'main')
        merged_files = {k: v for k, v in files.items() if k != 'src/dep.ts'}
        merged_files['consumer.mjs'] += 'console.log("novel resolution");\n'
        merged = commit(merged_files, [a, b], 'merge deletes build source and edits importer')
        c.checkout(b)
        r = {'candidate': merged, 'parents': [a, b], 'fixture_parent_files': files,
             'fixture_merge_files': merged_files}
        r['parent_build'] = record(c.run_cmd('node', 'build.mjs', check=False))
        r['parent_runtime'] = record(c.run_cmd('node', 'consumer.mjs', check=False))
        # Unlike a single-commit diff, this range explicitly includes consumer.mjs.
        r['parent_travel_with_importer_explicitly_selected'] = record(c.run_cmd(
            'python3', str(W / 'git/hooks/_travels.py'), a + '..' + b, check=False))
        c.checkout(merged)
        for label in hooks:
            r[label] = hook(c, label, merged, a)
        p = c.run_cmd('git', '-c', 'core.hooksPath=' + str(W / 'git/hooks'),
                      'push', 'origin', 'HEAD:refs/heads/feature', check=False)
        r['ordinary_push'] = record(p)
        r['ordinary_push']['destination_equals_candidate'] = c.git(
            'rev-parse', 'refs/heads/feature', cwd=c.remote) == merged
        clone = c.root / 'fresh-clone'
        c.run_cmd('git', 'clone', '-q', '-b', 'feature', str(c.remote), str(clone), cwd=c.root)
        r['fresh_clone_build'] = record(c.run_cmd('node', 'build.mjs', cwd=clone, check=False))
        r['fresh_clone_runtime'] = record(c.run_cmd('node', 'consumer.mjs', cwd=clone, check=False))
        assert r['parent_build']['exit_code'] == r['parent_runtime']['exit_code'] == 0
        assert r['parent_travel_with_importer_explicitly_selected']['exit_code'] == 0
        assert r['base']['exit_code'] == 1 and r['repair']['exit_code'] == 0
        assert r['ordinary_push']['exit_code'] == 0 and r['ordinary_push']['destination_equals_candidate']
        assert r['fresh_clone_build']['exit_code'] == r['fresh_clone_runtime']['exit_code'] == 1
        results['generated_source_loss'] = r
    finally:
        c.doCleanups()

    results['performance'] = []
    for count in [1, 30, 100]:
        c = case()
        try:
            text = ''.join(f'import "./never-{i}";\n' for i in range(count))
            b = c.commit(dict(c.integration_files, **{'historical.js': text}),
                         (c.base,), 'published many missing imports')
            c.publish(c.upstream, b, 'main')
            merged = c.commit(dict(c.merge_files, **{'historical.js': text}),
                              (c.feature, b), 'inherit importer unchanged')
            c.checkout(merged)
            r = {'inherited_missing_import_count': count}
            for label in hooks:
                r[label] = hook(c, label, merged, c.feature)
                assert r[label]['exit_code'] == 0
            results['performance'].append(r)
        finally:
            c.doCleanups()

(OUT / 'reproduced-confirmed.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps({
    'generated_source_loss': {
        'base_exit': results['generated_source_loss']['base']['exit_code'],
        'repair_exit': results['generated_source_loss']['repair']['exit_code'],
        'fresh_clone_build_exit': results['generated_source_loss']['fresh_clone_build']['exit_code'],
        'fresh_clone_runtime_exit': results['generated_source_loss']['fresh_clone_runtime']['exit_code'],
    },
    'timings': [{
        'imports': r['inherited_missing_import_count'],
        'base_seconds': r['base']['seconds'],
        'repair_seconds': r['repair']['seconds'],
    } for r in results['performance']],
}, indent=2))
```

Execute the retained code block without creating a script in the source checkout:

`PYTHONDONTWRITEBYTECODE=1 python3 -c 'from pathlib import Path; p=Path("/home/delorenj/.hermes/profiles/33god-pm/cache/scratch/33god55-r3-quality/reproduce.md"); exec(compile(p.read_text().split("```python\n",1)[1].split("\n```",1)[0],str(p),"exec"))'`

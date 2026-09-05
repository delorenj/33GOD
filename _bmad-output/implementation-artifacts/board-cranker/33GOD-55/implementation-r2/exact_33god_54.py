"""Read-only exact-candidate acceptance proof; all output stays in this lane."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
PHASE = sys.argv[1]
CANDIDATE = Path('/tmp/hermes-board-cranker-50')
BASELINE = Path('/tmp/hermes-board-cranker-53-upstream-baseline')
HEAD = '750ad5ccd79e1ea4dd6725486b2849c2a0defa1d'
PARENTS = ['cc00fe6ef855e506ad1bf8166473eecf725af8a8', 'b0ab2e163a50d4e6c36507eba955a6067fde6abc']
REF = 'refs/heads/feat/33GOD-50-stateless-contractor-turns'
URL = 'git@github.com:delorenj/hermes-agent.git'
HOOK = '/tmp/agents-board-cranker-55/git/hooks/pre-push'
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1')
assert ENV.get('GIT_GUARD_OFF', '0') != '1'
COMMANDS = []


def run(args, cwd=CANDIDATE, stdin=None):
    started = time.time()
    p = subprocess.run(args, cwd=cwd, input=stdin, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
    COMMANDS.append({'argv': args, 'cwd': str(cwd), 'stdin': stdin,
                     'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr,
                     'seconds': round(time.time()-started, 3)})
    (ROOT / f'exact-{PHASE}-commands.json').write_text(json.dumps(COMMANDS, indent=2)+'\n')
    if p.returncode:
        raise RuntimeError(f'failed: {shlex.join(args)}: exit {p.returncode}')
    return p.stdout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(repo):
    tracked = run(['git', 'ls-files', '-z'], cwd=repo).split('\0')
    files = {}
    for rel in tracked:
        if not rel:
            continue
        path = repo / rel
        if path.is_symlink():
            files[rel] = {'link': os.readlink(path)}
        elif path.is_file():
            files[rel] = sha(path)
        elif path.is_dir():
            files[rel] = 'directory/gitlink'
        else:
            files[rel] = 'absent'
    gitdir = Path(run(['git', 'rev-parse', '--absolute-git-dir'], cwd=repo).strip())
    index = gitdir / 'index'
    local_hook = gitdir / 'hooks/pre-push'
    assert not os.access(local_hook, os.X_OK), 'candidate local hook needs read-only inspection before execution'
    return {'head': run(['git', 'rev-parse', 'HEAD'], cwd=repo).strip(),
            'tree': run(['git', 'rev-parse', 'HEAD^{tree}'], cwd=repo).strip(),
            'branch': run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo).strip(),
            'parents': run(['git', 'show', '-s', '--format=%P', 'HEAD'], cwd=repo).split(),
            'status': run(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=repo),
            'persistent_refs': run(['git', 'show-ref'], cwd=repo),
            'index_sha256': sha(index), 'tracked_file_hashes': files,
            'local_hook_executable': False}


def snapshot():
    evidence = json.loads((ROOT/'preflight.json').read_text())['blocker_artifact_hashes']
    return {'candidate': state(CANDIDATE), 'baseline': state(BASELINE),
            'fork_ref': run(['git', 'ls-remote', 'delorenj', REF]),
            'origin_main': run(['git', 'ls-remote', 'origin', 'refs/heads/main']),
            'pr': json.loads(run(['gh', 'pr', 'view', '102409', '--repo', 'NousResearch/hermes-agent',
                                  '--json', 'title,body,state,headRefOid,statusCheckRollup'])),
            'evidence': [{'path': item['path'], 'sha256': sha(Path(item['path']))} for item in evidence]}

before = snapshot()
(ROOT/f'exact-{PHASE}-before.json').write_text(json.dumps(before, indent=2)+'\n')
assert before['candidate']['head'] == HEAD
assert before['candidate']['parents'] == PARENTS
assert before['candidate']['status'] == ''
assert before['fork_ref'] == PARENTS[0]+'\t'+REF+'\n'
assert before['pr']['headRefOid'] == PARENTS[0]
contract = f'{REF} {HEAD} {REF} {PARENTS[0]}\n'
args = ['bash', HOOK, 'delorenj', URL]
started = time.time()
p = subprocess.run(args, cwd=CANDIDATE, input=contract, text=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=ENV)
log = ROOT/f'exact-{PHASE}-hook.log'
log.write_text(p.stdout)
after = snapshot()
(ROOT/f'exact-{PHASE}-after.json').write_text(json.dumps(after, indent=2)+'\n')
receipt = {'hook_contract_command': 'printf %s '+shlex.quote(contract)+' | '+shlex.join(args),
           'argv': args, 'stdin': contract, 'cwd': str(CANDIDATE), 'exit_code': p.returncode,
           'seconds': round(time.time()-started, 3), 'log': str(log), 'sha256': sha(log),
           'candidate_head_unchanged': before['candidate']['head'] == after['candidate']['head'] == HEAD,
           'candidate_tree_clean': before['candidate']['status'] == after['candidate']['status'] == '',
           'ordered_parents_verified': before['candidate']['parents'] == after['candidate']['parents'] == PARENTS,
           'candidate_all_state_unchanged': before['candidate'] == after['candidate'],
           'baseline_all_state_unchanged': before['baseline'] == after['baseline'],
           'fork_ref_unchanged': before['fork_ref'] == after['fork_ref'],
           'origin_main_unchanged': before['origin_main'] == after['origin_main'],
           'pr_unchanged': before['pr'] == after['pr'],
           'evidence_hashes_unchanged': before['evidence'] == after['evidence'],
           'bypass_used': False, 'push_performed': False}
(ROOT/f'exact-{PHASE}-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
print(p.stdout)
assert p.returncode == 0
assert all(v for k,v in receipt.items() if k.endswith(('_unchanged', '_clean', '_verified')))

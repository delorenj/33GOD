import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

E = Path(__file__).resolve().parent
ART = E.parent.parent
H = Path('/tmp/hermes-board-cranker-50')
B = Path('/tmp/hermes-board-cranker-53-upstream-baseline')
G = Path('/tmp/agents-board-cranker-55-postmerge-verification-r2')
C = '750ad5ccd79e1ea4dd6725486b2849c2a0defa1d'
BASE = 'b0ab2e163a50d4e6c36507eba955a6067fde6abc'
P = 'cc00fe6ef855e506ad1bf8166473eecf725af8a8'
GUARD = '02481c8df4cedbdc11081fe41fcf01859a399566'
BR = 'feat/33GOD-50-stateless-contractor-turns'
PY = '/home/delorenj/.hermes/hermes-agent/.venv/bin/python'
RUFF = '/home/delorenj/.hermes/hermes-agent/.venv/bin/ruff'
OWNER = Path('/home/delorenj/code/33GOD/agents/hermes/pm/runtime/board-cranker-controller-owner.json')
FILES = ['gateway/platforms/base.py', 'gateway/run.py', 'tests/gateway/test_contractor_turns.py']
STATIC = FILES + ['tests/gateway/test_session_split_brain_11016.py']
PR_FIELDS = 'number,url,title,body,state,headRefOid,headRefName,headRepositoryOwner,headRepository,baseRefName,mergeable,mergeStateStatus,statusCheckRollup,reviewDecision,reviews,isDraft,mergedAt'
EXPECTED = {
    str(ART/'33GOD-53/red.log'): '7fe456453163f9369481543fdeef844717f891026b366570d61eb0132a8e0420',
    str(ART/'33GOD-53/green.log'): '0d27d89c5ee07b12752559c11f67d8c02baacc68b4a54904e9ea09c9ee6f4baa',
    str(ART/'33GOD-54.implementation.attempt-1.json'): '0bf1f17dbe5c99a150302374392c64d4fe2b8c313147d2215c2e444c7ae8f8c7',
    str(ART/'33GOD-54.blocker-reconciliation.json'): '34a312da67cb5e2095f163d461ed24877eaad2c5052da7f3b9c7044d768e2ffa',
    str(ART/'33GOD-54.implementation.json'): '79e286285266284134e34a6f7dd0814b682abe180517be3813946f0ba6878209',
    str(ART/'33GOD-55.integration.json'): '37ca03936fa8d58ba5bf740976c730517a9da098c283fba8a2d29cb4877f069e',
    str(ART/'33GOD-55.integration-controller-verification-r2.json'): 'c7d83164bdade7452d6bc204ffd169d617475fb5dff6e45998cfbf24853d04a3',
    str(ART/'33GOD-54.decomposition-to-56.json'): '379a5dbf154c7c70e6f0270032dcf7db1d71fd21d13ad1df0a7fe88831b04ba3',
    str(G/'git/hooks/pre-push'): 'ddc23c60fa6c67bd20a06d51b76d35d7b30fa812a54dfa9c1ee52280fea179dc',
    str(G/'git/hooks/_travels.py'): 'd395ff645cf25eceabe7e99f82ac969981a4b82a260f7046087d2103acf3615d',
}

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def save(name, data):
    p = E/name
    with p.open('x') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')
    return p

def git(tree, *args):
    return subprocess.check_output(['git', '--no-optional-locks', *args], cwd=tree, env={**os.environ, 'GIT_OPTIONAL_LOCKS':'0'})

def environment(name, pytest=False):
    root = E/'isolation'/name
    root.mkdir(parents=True, exist_ok=False)
    for sub in ['hermes-home', 'tmp', 'cache', 'bytecode', 'config', 'data', 'state']:
        (root/sub).mkdir()
    env = {
        'PATH': str(Path(PY).parent)+':/usr/bin:/bin',
        'HOME': os.environ['HOME'],
        'TZ':'UTC', 'LANG':'C.UTF-8', 'LC_ALL':'C.UTF-8',
        'PYTHONHASHSEED':'0', 'PYTHONUTF8':'1', 'PYTHONDONTWRITEBYTECODE':'1',
        'PYTHONPYCACHEPREFIX':str(root/'bytecode'),
        'HERMES_HOME':str(root/'hermes-home'), 'TMPDIR':str(root/'tmp'),
        'XDG_CACHE_HOME':str(root/'cache'), 'XDG_CONFIG_HOME':str(root/'config'),
        'XDG_DATA_HOME':str(root/'data'), 'XDG_STATE_HOME':str(root/'state'),
        'RUFF_CACHE_DIR':str(root/'cache/ruff'), 'UV_CACHE_DIR':str(root/'cache/uv'),
        'GIT_OPTIONAL_LOCKS':'0',
    }
    if pytest:
        env.update(PYTHONPATH=str(E), PYTEST_PLUGINS='evidence_plugin',
                   PYTEST_ADDOPTS='-o cache_dir='+str(root/'cache/pytest'),
                   EVIDENCE_REPORT=str(E/(name+'.reports.json')))
    return env

def process_table():
    rows = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            stat = (p/'stat').read_text().rsplit(')', 1)[1].split()
            cmd = (p/'cmdline').read_bytes().decode(errors='replace').split('\0')[:-1]
            try:
                cwd = os.readlink(p/'cwd')
            except OSError:
                cwd = None
            rows.append({'pid':int(p.name), 'state':stat[0], 'ppid':int(stat[1]),
                         'pgrp':int(stat[2]), 'session':int(stat[3]),
                         'start_ticks':stat[19], 'cwd':cwd, 'argv':cmd})
        except (OSError, ValueError, IndexError):
            continue
    return rows

def gateway_processes():
    matches = []
    for row in process_table():
        args = row['argv']
        is_test = any(a == 'pytest' or a.endswith('/pytest') or a.startswith('tests/gateway') or '/tests/gateway' in a for a in args)
        in_tree = any((row['cwd'] or '').startswith(str(tree)) or any(a.startswith(str(tree)) for a in args) for tree in [H,B])
        if is_test and in_tree:
            matches.append(row)
    return matches

def run(name, argv, tree=H, controlled=False, pytest=False, sequence=0, overrides=None):
    assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0  # Linux child subreaper
    before = gateway_processes()
    assert not before, before
    env = environment(name, pytest) if controlled else {**os.environ, 'GIT_OPTIONAL_LOCKS':'0', 'PYTHONDONTWRITEBYTECODE':'1'}
    if overrides:
        env.update(overrides)
    assert 'GIT_GUARD_OFF' not in env
    started = utc()
    start_ns = time.monotonic_ns()
    logfile = E/(name+'.log')
    observed = {}
    with logfile.open('x') as f:
        f.write('$ '+shlex.join(argv)+'\nworktree='+str(tree)+'\nstarted_at='+started+'\n')
        if controlled:
            f.write('environment='+json.dumps(env, sort_keys=True)+'\n')
        f.flush()
        proc = subprocess.Popen(argv, cwd=tree, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        while proc.poll() is None:
            rows = process_table()
            ids = {proc.pid}
            for _ in rows:
                extra = {r['pid'] for r in rows if r['ppid'] in ids or r['session']==proc.pid or r['pgrp']==proc.pid}
                if extra <= ids:
                    break
                ids |= extra
            for r in rows:
                if r['pid'] in ids:
                    observed[(r['pid'],r['start_ticks'])] = r
            time.sleep(0.2)
        returncode = proc.wait()
        command_finished = utc()
        reaped = []
        deadline = time.monotonic()+30
        while True:
            try:
                while True:
                    pid, status = os.waitpid(-1, os.WNOHANG)
                    if not pid:
                        break
                    reaped.append({'pid':pid, 'wait_status':status})
            except ChildProcessError:
                pass
            remaining = [r for r in process_table() if r['ppid']==os.getpid() or r['session']==proc.pid or r['pgrp']==proc.pid or (r['pid'],r['start_ticks']) in observed]
            if not remaining or time.monotonic() >= deadline:
                break
            time.sleep(0.1)
        after = gateway_processes()
        finished = utc()
        f.write('\ncommand_finished_at='+command_finished+'\nfinished_at='+finished+'\nexit_code='+str(returncode)+'\n')
    record = {'name':name, 'command':shlex.join(argv), 'argv':argv, 'worktree':str(tree),
              'sequence_index':sequence, 'started_at':started, 'command_finished_at':command_finished,
              'finished_at':finished, 'started_monotonic_ns':start_ns, 'finished_monotonic_ns':time.monotonic_ns(),
              'exit_code':returncode, 'status':'PASS' if returncode==0 else 'FAIL',
              'summary':'', 'log':str(logfile), 'sha256':sha(logfile),
              'process':{'supervisor_pid':os.getpid(), 'child_subreaper':True, 'pid':proc.pid,
                         'before_gateway_processes':before, 'observed_processes':list(observed.values()),
                         'reaped_adopted_descendants':reaped, 'remaining_descendants':remaining,
                         'after_gateway_processes':after, 'all_descendants_gone':not remaining and not after}}
    if controlled:
        record['environment'] = env
    elif overrides:
        record['environment_overrides'] = overrides
    save(name+'.exit.json', record)
    print(json.dumps({k:record[k] for k in ['name','started_at','finished_at','exit_code','log','sha256']}), flush=True)
    assert not remaining and not after, record['process']
    return record

def payload(record):
    text = Path(record['log']).read_text()
    return text.split('started_at=',1)[1].split('\n',1)[1].rsplit('\ncommand_finished_at=',1)[0].rstrip()

def snapshot(tree, include_sources=True):
    data = {'path':str(tree), 'head':git(tree,'rev-parse','HEAD').decode().strip(),
            'branch':git(tree,'branch','--show-current').decode().strip(),
            'status':git(tree,'status','--porcelain=v1','--untracked-files=all').decode(),
            'unstaged_diff_sha256':hashlib.sha256(git(tree,'diff','--binary')).hexdigest(),
            'staged_diff_sha256':hashlib.sha256(git(tree,'diff','--cached','--binary')).hexdigest()}
    if include_sources:
        names = git(tree,'ls-files','-z','--cached','--others','--exclude-standard').decode().split('\0')
        files = {}
        for name in sorted(set(names)-{''}):
            path = tree/name
            if path.is_symlink():
                files[name] = {'symlink':os.readlink(path)}
            elif path.is_file():
                files[name] = {'sha256':sha(path), 'mode':path.stat().st_mode & 0o777}
            elif path.exists():
                files[name] = {'directory':True}
            else:
                files[name] = {'missing':True}
        data['files'] = files
    return data

def verify_ground():
    assert json.loads(OWNER.read_text())['owner_agent_id'] == '33god-pm'
    for tree, head, branch in [(H,C,BR),(B,BASE,''),(G,GUARD,'')]:
        assert git(tree,'rev-parse','HEAD').decode().strip()==head
        assert git(tree,'branch','--show-current').decode().strip()==branch
        assert not git(tree,'status','--porcelain=v1','--untracked-files=all')
    assert git(H,'show','-s','--format=%P',C).decode().split()==[P,BASE]
    assert git(H,'diff','--name-only',BASE+'...'+C).decode().splitlines()==FILES
    git(H,'merge-base','--is-ancestor',P,C)
    git(H,'merge-base','--is-ancestor',BASE,C)
    assert sha(H/'uv.lock')==sha(B/'uv.lock')
    for path, expected in EXPECTED.items():
        assert sha(path)==expected, path

def preserved_inventory():
    paths = set(map(Path, EXPECTED))
    for issue in ['33GOD-53','33GOD-54','33GOD-55']:
        paths.update(p for p in (ART/issue).rglob('*') if p.is_file())
        paths.update(p for p in ART.glob(issue+'*.json') if p.is_file())
    return [{'path':str(p),'sha256':sha(p)} for p in sorted(paths)]

def remote(name, expected):
    r = run('remote-'+name,['git','ls-remote','--exit-code','delorenj','refs/heads/'+BR])
    assert r['exit_code']==0
    assert payload(r).split()==[expected,'refs/heads/'+BR]
    r = run('pr-'+name,['gh','pr','view','102409','--repo','NousResearch/hermes-agent','--json',PR_FIELDS])
    assert r['exit_code']==0
    data = json.loads(payload(r))
    save('pr-'+name+'.json',data)
    assert data['state']=='OPEN' and data['headRefOid']==expected and data['headRefName']==BR
    assert data['headRepositoryOwner']['login']=='delorenj' and data['mergedAt'] is None
    assert data['reviewDecision'] != 'APPROVED'
    assert not any(r['state']=='APPROVED' for r in data['reviews'])
    return data

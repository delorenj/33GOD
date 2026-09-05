import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

root=Path(__file__).resolve().parent
phase=sys.argv[1]
commands=[
 ['python3','-m','unittest','discover','-s','git/tests','-p','test_*.py','-v'],
 ['python3','-m','compileall','-q','git/hooks/_travels.py','git/tests'],
 ['bash','-n','git/hooks/pre-push','git/hooks/_guard.sh'],
 ['python3','git/hooks/_travels.py','HEAD'],
 ['git','diff','--check','36d3ed6627b1ee1819952617d7d4ebfcebc2708f...HEAD'],
 ['python3','git/tests/test_pre_push.py','MergeTopologyTests','-v'],
 ['git','diff','--check'],
]
checks=[]
for i,cmd in enumerate(commands,1):
 p=subprocess.run(cmd,cwd='/tmp/agents-board-cranker-55',text=True,
                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 log=root/f'{phase}-gate-{i}.log'
 log.write_text(p.stdout)
 checks.append({'name':f'{phase}-gate-{i}','command':shlex.join(cmd),'exit_code':p.returncode,
                'status':'PASS' if p.returncode==0 else 'FAIL','log':str(log),
                'sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
 print(checks[-1]['command'], 'exit',p.returncode, flush=True)
(root/f'{phase}-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
assert all(c['exit_code']==0 for c in checks)

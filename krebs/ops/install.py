#!/usr/bin/env python3
"""Install a digest-pinned wheel and locked dependencies; activation is separate.

Usage: python install.py release.json --destination ~/.local/share/krebs/releases/<sha>
Release JSON supplies wheel/wheel_sha256, requirements/requirements_sha256,
source_revision, pilot_root/pilot_bundle_sha256, momo_root/momo_bundle_sha256,
manifests, and environment containing op references for secret values.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

p=argparse.ArgumentParser();p.add_argument('release');p.add_argument('--destination',required=True);args=p.parse_args()
source=Path(args.release).resolve();cfg=json.loads(source.read_text())
# Complete preflight precedes any filesystem mutation or subprocess.
if not re.fullmatch('[a-f0-9]{40}',cfg.get('source_revision','')):raise SystemExit('immutable source revision required')
if not isinstance(cfg.get('environment',{}),dict):raise SystemExit('environment must be an object')
for key,value in cfg.get('environment',{}).items():
    if not isinstance(value,str):raise SystemExit('environment values must be strings')
    if any(part in key for part in ('TOKEN','PASSWORD','DATABASE_URL','API_KEY')) and not value.startswith('op://'):
        raise SystemExit('secret environment values must be vault references')
if not isinstance(cfg.get('manifests'),list) or not cfg['manifests']:raise SystemExit('canonical manifests required')
for kind in ('pilot','momo'):
    base=Path(cfg[kind+'_root']).resolve()
    paths=([base/'package.json',*base.glob('src/**/*.js'),*base.glob('bin/**/*.js')] if kind=='pilot' else
        [p for p in base.rglob('*') if p.is_file() and p.suffix in {'.md','.py','.sh'} and '__pycache__' not in p.parts])
    if not paths or not all(p.is_file() for p in paths):raise SystemExit(kind+' bundle incomplete')
    manifest=''.join(f'{p.relative_to(base).as_posix()}\0{hashlib.sha256(p.read_bytes()).hexdigest()}\n' for p in sorted(set(paths)))
    if hashlib.sha256(manifest.encode()).hexdigest()!=cfg[kind+'_bundle_sha256']:raise SystemExit(kind+' bundle digest mismatch')
for name in ('wheel','requirements'):
    path=Path(cfg[name]).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest()!=cfg[name+'_sha256']:raise SystemExit(name+' checksum mismatch')
    cfg[name]=str(path)
release=Path(args.destination).expanduser().resolve()
if release.exists():raise SystemExit('release destination already exists; never mutate an installed release')
release.mkdir(parents=True)
subprocess.run(['uv','venv',str(release/'venv')],check=True)
python=release/'venv/bin/python'
subprocess.run(['uv','pip','install','--python',str(python),'--require-hashes','-r',cfg['requirements']],check=True)
subprocess.run(['uv','pip','install','--python',str(python),'--no-deps',cfg['wheel']],check=True)
launchers=release/'bin';launchers.mkdir()
for name,entry in [('px','pilot.js'),('px-supervised','px-supervised.js')]:
    launcher=launchers/name
    launcher.write_text('#!/bin/sh\nexec node '+shlex.quote(str(Path(cfg['pilot_root'])/'bin'/entry))+' "$@"\n')
    launcher.chmod(0o555)
cfg['launcher_bin']=str(launchers)
descriptor=release/'release.json';descriptor.write_text(json.dumps(cfg,indent=2)+'\n');descriptor.chmod(0o400)
unit=Path.home()/'.config/systemd/user/krebs-execution.service';unit.parent.mkdir(parents=True,exist_ok=True)
quote=lambda text:'"'+str(text).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'
if '\n' in str(python)+str(descriptor):raise SystemExit('invalid release path')
command=f'{quote(python)} -m krebs.launch {quote(descriptor)}'
unit.write_text('[Unit]\nDescription=Krebs pinned execution authority\nAfter=network-online.target\n[Service]\nType=simple\nExecStartPre='+command+' --readiness\nExecStart='+command+'\nRestart=on-failure\nRestartSec=5\nKillMode=control-group\n[Install]\nWantedBy=default.target\n')
subprocess.run(['systemctl','--user','daemon-reload'],check=True)
print(json.dumps({'installed':str(release),'unit':str(unit),'activated':False,'readiness':[str(python),'-m','krebs.launch',str(descriptor),'--readiness']}))

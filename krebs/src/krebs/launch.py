"""Pinned host launcher. Secrets are resolved into child environment only."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile
from .bundles import bundle_digest
from .contract import require
from .adapters import secret

def verify_release(config):
    wheel=Path(config['wheel'])
    require(hashlib.sha256(wheel.read_bytes()).hexdigest()==config['wheel_sha256'],'wheel digest mismatch')
    require(bool(re.fullmatch('[a-f0-9]{40}',config.get('source_revision',''))),'immutable source revision required')
    installed=Path(__file__).resolve().parents[1]
    with ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith('krebs/') and not name.endswith('/'):
                require((installed/name).is_file() and (installed/name).read_bytes()==archive.read(name),'installed wheel content mismatch: '+name)
    require(bundle_digest(config['pilot_root'],'pilot')==config['pilot_bundle_sha256'],'Pilot release bundle drift')
    require(bundle_digest(config['momo_root'],'momo')==config['momo_bundle_sha256'],'Momo release bundle drift')

def environment(config):
    env=dict(os.environ)
    for key,value in config.get('environment',{}).items():
        require(isinstance(value,str),'environment values must be strings')
        if any(part in key for part in ('TOKEN','PASSWORD','DATABASE_URL','API_KEY')):
            require(value.startswith('op://'),'secret environment values must be vault references')
        env[key]=secret(value) if value.startswith('op://') else value
    env['KREBS_MANIFESTS']=json.dumps(config['manifests'])
    env['KREBS_PILOT_HELPER']=str(Path(config['pilot_root'])/'src/provider-helper.js')
    env['PATH']=str(Path(config['launcher_bin']))+os.pathsep+env.get('PATH','')
    return env

def main():
    parser=argparse.ArgumentParser();parser.add_argument('release');parser.add_argument('--readiness',action='store_true')
    args=parser.parse_args();config=json.loads(Path(args.release).read_text())
    verify_release(config);env=environment(config)
    env['KREBS_RELEASE_DESCRIPTOR']=str(Path(args.release).resolve())
    readiness=subprocess.run([sys.executable,'-m','krebs.service','readiness'],env=env)
    require(readiness.returncode==0,'release readiness blocked')
    if not args.readiness: os.execve(sys.executable,[sys.executable,'-m','krebs.service','serve'],env)

if __name__=='__main__':main()

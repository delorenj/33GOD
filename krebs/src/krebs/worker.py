"""Release-pinned supervised worker bootstrap; vault values never enter unit argv."""
import json
import os
from pathlib import Path
import sys
from .launch import verify_release
from .adapters import secret
from .contract import require

def main():
    config=json.loads(Path(sys.argv[1]).read_text())
    verify_release(config)
    env=dict(os.environ)
    # Only worker transport configuration; never expose the controller database.
    for key in ('NATS_URL','NATS_TOKEN'):
        value=config.get('environment',{}).get(key)
        if value:
            require(key!='NATS_TOKEN' or value.startswith('op://'),'worker token must be vault reference')
            env[key]=secret(value) if value.startswith('op://') else value
    env.pop('KREBS_DATABASE_URL',None)
    env['KREBS_MANIFESTS']=json.dumps(config['manifests'])
    env['PATH']=config['launcher_bin']+os.pathsep+env.get('PATH','')
    argv=sys.argv[2:]
    if argv and argv[0]=='--':argv=argv[1:]
    require(bool(argv),'worker argv missing')
    os.execvpe(argv[0],argv,env)
if __name__=='__main__':main()

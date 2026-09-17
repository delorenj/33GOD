#!/usr/bin/env python3
"""Required acceptance gate provisions disposable PG/NATS or fails explicitly."""
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
root=Path(__file__).resolve().parents[1]
containers=[]
env=dict(os.environ)
try:
    for label,image,port,key,url in [('pg','postgres:17-alpine',5432,'KREBS_TEST_DSN','postgresql://postgres@127.0.0.1:{port}/postgres'),('nats','nats:2.11-alpine',4222,'KREBS_TEST_NATS_URL','nats://127.0.0.1:{port}')]:
        if env.get(key):continue
        name='krebs-test-'+label+'-'+uuid.uuid4().hex[:10]
        argv=['docker','run','--rm','-d','--name',name,'-p',f'127.0.0.1::{port}']
        argv+=['-e','POSTGRES_HOST_AUTH_METHOD=trust',image] if label=='pg' else [image,'-js']
        subprocess.run(argv,check=True,capture_output=True);containers.append(name)
        mapping=subprocess.check_output(['docker','port',name,str(port)],text=True).strip()
        env[key]=url.format(port=mapping.rsplit(':',1)[1])
    env['KREBS_REQUIRE_INTEGRATION']='1'
    env['KREBS_SYSTEMD_TEST']='1'
    env.setdefault('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}')
    subprocess.run(['systemctl','--user','show-environment'],env=env,check=True,capture_output=True)
    subprocess.run(['uv','run','python','-c','import os,time,psycopg\nfor i in range(50):\n try: c=psycopg.connect(os.environ["KREBS_TEST_DSN"]);c.close();break\n except psycopg.OperationalError: time.sleep(.1)\nelse: raise SystemExit("Postgres unavailable")'],cwd=root,env=env,check=True)
    result=subprocess.run(['uv','run','pytest','-q','tests'],cwd=root,env=env)
    raise SystemExit(result.returncode)
finally:
    for name in containers:subprocess.run(['docker','stop',name],capture_output=True)

import os
import subprocess
import uuid
import pytest
from krebs.adapters import Runtime

@pytest.mark.skipif(os.environ.get('KREBS_SYSTEMD_TEST')!='1',reason='explicit isolated systemd proof required')
def test_real_systemd_unit_stops_control_group(tmp_path):
    runtime=Runtime()
    run=str(uuid.uuid4())
    project={'manifest':str(tmp_path/'.project.json'),'actors':{'test':{'runtime':{'adapter':'systemd','unit_prefix':'krebs-acceptance'}}}}
    attempt={'actor_id':'test','run_id':run,'supervisor':project['actors']['test']['runtime'].copy(),'project_root':str(tmp_path)}
    try:
        first=runtime.start(project,attempt,['/usr/bin/sleep','60'])
        assert not first['existing']
        assert runtime.running(project,attempt)
        project['actors']['test']['runtime']['unit_prefix']='changed-prefix'
        assert runtime.start(project,attempt,['/usr/bin/sleep','60'])['existing']
        assert runtime.stop(project,attempt)['state']=='stopped'
        assert not runtime.running(project,attempt)
    finally:
        subprocess.run(['systemctl','--user','stop',f'krebs-acceptance-{run}.service'],capture_output=True)
        subprocess.run(['systemctl','--user','reset-failed',f'krebs-acceptance-{run}.service'],capture_output=True)

def test_release_worker_bootstrap_uses_frozen_cli_path(monkeypatch,tmp_path):
    monkeypatch.setenv('KREBS_RELEASE_DESCRIPTOR',str(tmp_path/'release.json'));monkeypatch.setenv('PATH','/pinned/bin:/usr/bin')
    runtime=Runtime();supervisor=runtime.freeze({'adapter':'systemd','unit_prefix':'test'})
    monkeypatch.setenv('PATH','/wrong/bin');calls=[]
    def run(argv,**kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv,0,'not-found' if argv[0]=='systemctl' else '')
    monkeypatch.setattr(subprocess,'run',run)
    runtime.start({'manifest':str(tmp_path/'.project.json'),'actors':{'pm':{}}},{'actor_id':'pm','run_id':'run','supervisor':supervisor},['px','task','status'])
    launch=calls[-1]
    assert '--setenv=PATH=/pinned/bin:/usr/bin' in launch
    assert 'krebs.worker' in launch and str(tmp_path/'release.json') in launch
    assert not any('TOKEN=' in arg or 'DATABASE_URL=' in arg for arg in launch)

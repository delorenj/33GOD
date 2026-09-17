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
    attempt={'actor_id':'test','run_id':run}
    try:
        first=runtime.start(project,attempt,['/usr/bin/sleep','60'])
        assert not first['existing']
        assert runtime.running(project,attempt)
        assert runtime.start(project,attempt,['/usr/bin/sleep','60'])['existing']
        assert runtime.stop(project,attempt)['state']=='stopped'
        assert not runtime.running(project,attempt)
    finally:
        subprocess.run(['systemctl','--user','stop',f'krebs-acceptance-{run}.service'],capture_output=True)
        subprocess.run(['systemctl','--user','reset-failed',f'krebs-acceptance-{run}.service'],capture_output=True)

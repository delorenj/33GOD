import json
from pathlib import Path
import subprocess
import sys
from krebs.bundles import bundle_digest
from krebs.launch import environment
from krebs.contract import Rejected
import pytest

def test_full_bundle_tracks_dependencies_templates_and_scripts(tmp_path):
    for name in ['SKILL.md','references/managed.md','templates/review.md','scripts/check.py']:
        p=tmp_path/name;p.parent.mkdir(exist_ok=True);p.write_text('source')
    original=bundle_digest(tmp_path,'momo')
    (tmp_path/'templates/review.md').write_text('changed')
    assert bundle_digest(tmp_path,'momo')!=original
    (tmp_path/'package.json').write_text('{}');(tmp_path/'src').mkdir();(tmp_path/'src/plane.js').write_text('dependency')
    original=bundle_digest(tmp_path,'pilot');(tmp_path/'src/plane.js').write_text('changed')
    assert bundle_digest(tmp_path,'pilot')!=original

def test_installer_rejects_raw_secret_before_any_write(tmp_path):
    source=tmp_path/'input.json';source.write_text(json.dumps({'source_revision':'a'*40,'environment':{'NATS_TOKEN':'fixture-raw-value'}}))
    target=tmp_path/'release'
    result=subprocess.run([sys.executable,str(Path(__file__).parents[1]/'ops/install.py'),str(source),'--destination',str(target)],capture_output=True,text=True)
    assert result.returncode and 'vault references' in result.stderr
    assert not target.exists()

def test_launcher_rejects_raw_secret_before_resolution():
    with pytest.raises(Rejected,match='vault references'):environment({'environment':{'NATS_TOKEN':'fixture-raw-value'}})

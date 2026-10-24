#!/usr/bin/env python3
"""Audit distributable bytes, vendored provenance and all Compose modes."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
patterns = ('op' + '://', 'sk' + '-', 'Bear' + 'er', '/home/' + 'delorenj',
            'delo' + '.sh', 'automatic' + 'ai', 'A' + 'AI')
hits = []
for path in root.rglob('*'):
    if not path.is_file() or '__pycache__' in path.parts:
        continue
    raw = path.read_bytes()
    for term in patterns:
        if term.encode() in raw:
            hits.append((str(path.relative_to(root)), term))
assert not hits, hits
print('PASS secrets/personal-host scan: zero hits')
sources = json.loads((root / 'vendor/SOURCES.json').read_text())
for name, record in sources['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == record['packaged_sha256'], name
print('PASS packaged provenance hashes:', len(sources['files']), 'files')
for mode, extra in [('cpu', []), ('gpu', ['--profile', 'gpu']),
                    ('attach', ['-f', 'compose.attach.yml']),
                    ('dev-journal', ['--profile', 'dev-journal'])]:
    cfg = json.loads(subprocess.check_output(['docker', 'compose', '-f', 'compose.yml',
                      *extra, 'config', '--format', 'json'], cwd=root))
    assert cfg['name'] == 'god-g6'
    assert not any(s.get('ports') or s.get('container_name') for s in cfg['services'].values())
    for name, service in cfg['services'].items():
        devices = service.get('deploy', {}).get('resources', {}).get('reservations', {}).get('devices')
        assert not devices or (mode == 'gpu' and name == 'voxxy-engine-voxcpm'), name
    if mode == 'cpu':
        budget = sum(int(s['mem_limit']) for s in cfg['services'].values()) // 1024**2
        assert budget == 1856
        print('PASS CPU memory caps:', budget, 'MiB')
    print('PASS config', mode, 'zero published ports, no adopted container names')

#!/usr/bin/env python3
"""Temporary public SDK account fixture; requires separately scoped approval."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

root = Path('/home/ubuntu/password-store')
assert Path.cwd() == root
engine = 'sailfish-sdk-build-engine_ubuntu'
target = 'SailfishOS-5.1.0.11-aarch64'
account = f'/srv/mer/targets/{target}.default/etc/passwd'
evidence = root / 'evidence/candidate-sdk-account-fixture-20261011.json'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--restore', action='store_true', help='Restore the persisted SDK-only original after interruption')
args = parser.parse_args()
backup = root / 'evidence/candidate-sdk-passwd-original-20261011.bin'
backup_metadata = root / 'evidence/candidate-sdk-passwd-original-20261011.json'

def docker(*args, data=None):
    return subprocess.run(['docker', 'exec', '-i', '--user', 'root', engine, *args],
                          input=data, capture_output=True, check=True).stdout

metadata = docker('stat', '-c', '%F:%u:%g:%a', account).decode().strip()
assert metadata.startswith('regular file:'), 'Refuse nonregular SDK passwd path'
if args.restore:
    info = json.loads(backup_metadata.read_text())
    original = backup.read_bytes()
    assert hashlib.sha256(original).hexdigest() == info['sha256']
    assert metadata == info['metadata'], 'SDK passwd ownership/mode changed'
    docker('tee', account, data=original)
    assert docker('cat', account) == original
    assert docker('stat', '-c', '%F:%u:%g:%a', account).decode().strip() == metadata
    print('PASS: interrupted SDK account fixture restored exactly')
    raise SystemExit(0)
assert not evidence.exists() and not backup.exists() and not backup_metadata.exists(), 'Fresh fixture only'
original = docker('cat', account)
assert not any(line.split(b':')[2:3] == [b'1000'] or line.startswith(b'mersdk:')
               for line in original.splitlines()), 'Unexpected existing SDK account'
fixture = b'mersdk:x:1000:100000:Synthetic SDK account fixture:/home/ubuntu:/sbin/nologin\n'
backup.write_bytes(original)
backup.chmod(0o600)
backup_metadata.write_text(json.dumps({'sha256': hashlib.sha256(original).hexdigest(), 'metadata': metadata}, indent=2) + '\n')
record = {'original_metadata': metadata, 'persistent_backup': str(backup), 'scope': 'temporary public SDK passwd mapping only; no shadow/home contents',
          'target': target, 'original_sha256': hashlib.sha256(original).hexdigest()}
try:
    docker('tee', account, data=original.rstrip(b'\n') + b'\n' + fixture)
    result = subprocess.run(['python3', str(root / 'tools/candidate-sdk-acceptance.py')])
    record['transaction_exit'] = result.returncode
finally:
    docker('tee', account, data=original)
    restored = docker('cat', account)
    record['restored_metadata'] = docker('stat', '-c', '%F:%u:%g:%a', account).decode().strip()
    record['restored_exactly'] = restored == original and record['restored_metadata'] == metadata
    record['restored_sha256'] = hashlib.sha256(restored).hexdigest()
    evidence.write_text(json.dumps(record, indent=2) + '\n')
    assert record['restored_exactly'], 'SDK account restoration mismatch'
raise SystemExit(record.get('transaction_exit', 1))

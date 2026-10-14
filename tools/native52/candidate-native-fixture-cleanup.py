#!/usr/bin/env python3
"""Remove only the explicit synthetic native fixture after evidence collection."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

assert os.getuid() == 100000 and os.uname().machine == 'aarch64'
version = next(line.split('=', 1)[1].strip('"') for line in Path('/etc/os-release').read_text().splitlines() if line.startswith('VERSION_ID='))
assert version == '5.2.0.18', 'Scoped dev OS only'
fixture = Path(sys.argv[1])
assert fixture.parent == Path('/tmp') and fixture.name.startswith('synthetic-native-policy-')
for path in [fixture, fixture / 'home', fixture / 'store']:
    assert not path.is_symlink() and path.is_dir()
    assert path.stat().st_uid == 100000 and stat.S_IMODE(path.stat().st_mode) == 0o700
for name in ['synthetic-marker.txt', 'result.json']:
    path = fixture / name
    assert not path.is_symlink() and stat.S_ISREG(path.stat().st_mode) and path.stat().st_uid == 100000
assert (fixture / 'synthetic-marker.txt').read_text() == 'Synthetic private policy regression only\n'
records = [json.loads((fixture / 'result.json').read_text())]
if (fixture / 'tty-result.json').exists():
    path = fixture / 'tty-result.json'
    assert not path.is_symlink() and stat.S_ISREG(path.stat().st_mode) and path.stat().st_uid == 100000
    records.append(json.loads(path.read_text()))
for record in records:
    assert record['fixture'] == str(fixture) and record['cleanup'] is True and record['unknown_launch'] is False
    assert all(not Path('/proc/' + str(pid)).exists() for pid in record['verified_pids'])
socket = Path(records[0]['socket'])
assert all(record['socket'] == str(socket) for record in records)
assert socket == fixture / 'home/S.gpg-agent' or (socket.name == 'S.gpg-agent' and socket.parent.name.startswith('d.') and socket.parent.parent == Path('/run/user/100000/gnupg'))
assert not socket.exists() and not socket.is_symlink()
env = {'PATH': '/usr/bin:/bin', 'HOME': str(fixture), 'LC_ALL': 'C',
       'SAILFISH_GNUPGHOME': str(fixture / 'home')}
result = subprocess.run(['/usr/bin/sailfish-gpg-agent', 'status'], env=env,
                        text=True, capture_output=True, timeout=60)
assert result.returncode == 3, 'Refuse fixture removal while agent status is uncertain'
derived = subprocess.check_output(['/usr/libexec/sailfish-gnupg/bin/gpgconf', '--homedir', str(fixture / 'home'), '--list-dirs', 'agent-socket'], env=env, text=True, timeout=60).strip()
assert derived == str(socket), 'Socket record does not match selected home'
if socket.parent != fixture / 'home' and socket.parent.exists():
    parent = socket.parent
    assert not parent.is_symlink() and parent.stat().st_uid == 100000
    assert stat.S_IMODE(parent.stat().st_mode) == 0o700
    parent.rmdir()  # Must be empty; never recursively delete a runtime directory.
shutil.rmtree(fixture)
assert not fixture.exists()
print('PASS: exact synthetic fixture and empty fixture socket directory removed')

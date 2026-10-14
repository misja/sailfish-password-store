#!/usr/bin/env python3
"""Remove one collected, successful synthetic two-home lifecycle fixture only."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

assert os.getuid() == 100000 and os.uname().machine == 'aarch64'
version = next(line.split('=', 1)[1].strip('"') for line in Path('/etc/os-release').read_text().splitlines() if line.startswith('VERSION_ID='))
assert version == '5.1.0.11'
fixture = Path(sys.argv[1])
assert fixture.parent == Path('/tmp') and fixture.name.startswith('synthetic-native-lifecycle-')
homes = [fixture / 'home-a', fixture / 'home-b']
for path in [fixture] + homes:
    assert not path.is_symlink() and path.is_dir()
    assert path.stat().st_uid == 100000 and stat.S_IMODE(path.stat().st_mode) == 0o700
for name in ['synthetic-marker.txt', 'result.json']:
    path = fixture / name
    assert not path.is_symlink() and path.is_file() and path.stat().st_uid == 100000
assert (fixture / 'synthetic-marker.txt').read_text() == 'Synthetic agent lifecycle only; no keys or passwords\n'
record = json.loads((fixture / 'result.json').read_text())
assert record['fixture'] == str(fixture) and record['passed'] is True and record['cleanup'] is True
assert record['workers_incomplete'] is False
assert set(record['uncertain_launch']) == {str(home) for home in homes}
assert all(value is False for value in record['uncertain_launch'].values())
assert all(not Path(f'/proc/{pid}').exists() for pid in record['known_pids'])
assert set(record['sockets']) == {str(home) for home in homes}
socket_dirs = set()
for home in homes:
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(fixture), 'LC_ALL': 'C', 'SAILFISH_GNUPGHOME': str(home)}
    state = subprocess.run(['/usr/bin/sailfish-gpg-agent', 'status'], env=env,
                           capture_output=True, text=True, timeout=60)
    assert state.returncode == 3
    socket = Path(record['sockets'][str(home)])
    derived = subprocess.check_output(['/usr/libexec/sailfish-gnupg/bin/gpgconf', '--homedir', str(home), '--list-dirs', 'agent-socket'], env=env, text=True, timeout=60).strip()
    assert str(socket) == derived
    assert socket == home / 'S.gpg-agent' or (socket.name == 'S.gpg-agent' and socket.parent.name.startswith('d.') and socket.parent.parent == Path('/run/user/100000/gnupg'))
    assert not socket.exists() and not socket.is_symlink()
    if socket.parent != home:
        socket_dirs.add(socket.parent)
for parent in socket_dirs:
    if parent.exists():
        assert not parent.is_symlink() and parent.stat().st_uid == 100000
        assert stat.S_IMODE(parent.stat().st_mode) == 0o700
        parent.rmdir()  # Empty scoped directory only; never recursive runtime cleanup.
shutil.rmtree(fixture)
assert not fixture.exists()
print('PASS: exact two-home synthetic lifecycle fixture and empty socket directories removed')

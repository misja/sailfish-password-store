#!/usr/bin/env python3
"""Approved native synthetic pass core test; retain fixture for fresh TTY show.

Only creates a new /tmp fixture, never opens a real home/store. This core phase
uses loopback and cache, then stops its agent. Fresh TTY acceptance is separate.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

assert os.getuid() == 100000 and os.uname().machine == 'aarch64'
target_version = next(line.split('=', 1)[1].strip('"') for line in
                      Path('/etc/os-release').read_text().splitlines()
                      if line.startswith('VERSION_ID='))
assert target_version in ('5.2.0.18', '5.1.0.11'), 'Unreviewed native target'
fixture = Path(tempfile.mkdtemp(prefix='sailfish-pass-synthetic-', dir='/tmp'))
home, store = fixture / 'gnupg', fixture / 'store'
home.mkdir(mode=0o700)
store.mkdir(mode=0o700)
(fixture / 'synthetic-marker.txt').write_text('Synthetic Sailfish pass acceptance only\n')
environment = {'PATH': '/usr/bin:/bin', 'HOME': str(fixture), 'LC_ALL': 'C',
               'SAILFISH_GNUPGHOME': str(home), 'GNUPGHOME': str(home),
               'PASSWORD_STORE_DIR': str(store), 'TERM': 'xterm'}
phrase = 'NOT-A-REAL-SECRET-native-pass-acceptance\n'
payload = 'NOT-A-REAL-PASSWORD\nusername=synthetic@example.invalid\n'
(fixture / 'expected-demo.txt').write_text(payload)
gpg = ['/usr/bin/sailfish-gpg']
password = ['/usr/bin/pass']
conf = ['/usr/libexec/sailfish-gnupg/bin/gpgconf', '--homedir', str(home)]
ipc = ['/usr/libexec/sailfish-gnupg/bin/gpg-connect-agent', '--homedir', str(home)]
record = {'environment': f'Sailfish {target_version}/aarch64, native core; no fresh TTY claim',
          'fixture': str(fixture), 'checks': [], 'agent_stopped': False, 'core_passed': False}


def run(command, data=None):
    result = subprocess.run(command, input=data, text=True, capture_output=True,
                            env=environment, timeout=120)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed ({result.returncode}): {result.stderr}')
    return result.stdout


def passed(name):
    record['checks'].append(name)
    print('PASS: ' + name, flush=True)


def agent_identity():
    response = run(ipc + ['--no-autostart', 'GETINFO pid', '/bye'])
    pid = next(line[2:] for line in response.splitlines() if line.startswith('D '))
    assert pid.isdecimal()
    assert Path('/proc/' + pid + '/exe').resolve() == Path('/usr/libexec/sailfish-gnupg/bin/gpg-agent')
    record['agent_pid'] = pid
    return pid


try:
    socket = Path(run(conf + ['--list-dirs', 'agent-socket']).strip())
    runtime_parent = Path('/run/user') / str(os.getuid()) / 'gnupg'
    assert socket == home / 'S.gpg-agent' or (
        socket.parent.parent == runtime_parent and socket.parent.name.startswith('d.')
        and socket.name == 'S.gpg-agent'), 'Refuse default/unrelated agent socket'
    record['socket'] = str(socket)
    loopback = ['--batch', '--pinentry-mode', 'loopback', '--passphrase-fd', '0']
    run(gpg + loopback + ['--quick-generate-key',
                         'Synthetic Pass Jolla <synthetic@example.invalid>',
                         'ed25519', 'sign', '1d'], phrase)
    pid = agent_identity()
    keys = run(gpg + ['--with-colons', '--list-keys'])
    fingerprint = next(line.split(':')[9] for line in keys.splitlines() if line.startswith('fpr:'))
    run(gpg + loopback + ['--quick-add-key', fingerprint, 'cv25519', 'encr', '1d'], phrase)
    record['synthetic_fingerprint'] = fingerprint
    passed('protected synthetic signing/encryption keypair')
    run(password + ['init', fingerprint])
    assert (store / '.gpg-id').read_text().strip() == fingerprint
    passed('pass init uses synthetic recipient')
    run(password + ['insert', '--multiline', 'synthetic/demo'], payload)
    encrypted = store / 'synthetic/demo.gpg'
    assert encrypted.is_file() and payload.encode() not in encrypted.read_bytes()
    assert run(gpg + loopback + ['--decrypt', str(encrypted)], phrase) == payload
    passed('multiline insert and private runtime decrypt, identical bytes')
    assert run(password + ['show', 'synthetic/demo']) == payload
    passed('cached pass show returns identical synthetic bytes')
    run(password + ['generate', '--no-symbols', 'synthetic/generated', '24'])
    generated = run(password + ['show', 'synthetic/generated']).strip()
    assert len(generated) == 24 and generated.isascii() and generated.isalnum()
    passed('generate roundtrip with expected length/alphabet')
    run(password + ['cp', 'synthetic/demo', 'synthetic/copied'])
    assert run(password + ['show', 'synthetic/copied']) == payload
    run(password + ['mv', 'synthetic/copied', 'synthetic/moved'])
    assert not (store / 'synthetic/copied.gpg').exists()
    assert run(password + ['show', 'synthetic/moved']) == payload
    run(password + ['rm', '--force', 'synthetic/moved'])
    assert not (store / 'synthetic/moved.gpg').exists()
    passed('copy/move/remove confined to synthetic store')
    listing = run(password + ['ls', 'synthetic'])
    assert 'demo' in listing and 'generated' in listing and '.gpg' not in listing
    passed('tree-backed listing strips encrypted-file suffix')
    pid = agent_identity()
    maps = Path('/proc/' + pid + '/maps').read_text().splitlines()
    libraries = []
    for name in ('libgcrypt.so.', 'libassuan.so.', 'libgpg-error.so.', 'libnpth.so.'):
        paths = {line.split()[-1] for line in maps if name in line}
        assert paths and all(p.startswith('/usr/libexec/sailfish-gnupg/lib/') for p in paths)
        libraries.extend(sorted(paths))
    record['private_agent_libraries'] = libraries
    passed('fixture agent executable and crypto libraries private')
    record['core_passed'] = True
except Exception as error:
    record['failure'] = str(error)
    raise
finally:
    try:
        assert 'socket' in record, 'Socket not validated; retain fixture for diagnosis'
        if 'agent_pid' not in record:
            agent_identity()
        run(conf + ['--kill', 'gpg-agent'])
        for attempt in range(40):
            if (not Path('/proc/' + record['agent_pid']).exists() and
                    not Path(record['socket']).exists()):
                break
            time.sleep(0.25)
        else:
            raise RuntimeError('Fixture agent process/socket remains after bounded wait')
        record['agent_stopped'] = True
        passed('fixture agent stopped; cache empty before fresh TTY phase')
    except Exception as error:
        record['stop_failure'] = str(error)
    (fixture / 'core-evidence.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Bewaar synthetische fixture: ' + str(fixture), flush=True)
    if not record['agent_stopped']:
        raise RuntimeError('Agent stop incomplete; retain fixture and stop acceptance')

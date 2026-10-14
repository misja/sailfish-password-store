#!/usr/bin/env python3
"""Prepared synthetic integration test; requires separately approved installs.

SDK uses a deliberately warmed synthetic agent cache for pass show, because its
normal tty mapping is unsuitable. This test does not claim uncached pinentry or
phone acceptance. Never reads or exports real keys/stores.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

root = Path(__file__).resolve().parent.parent
assert root == Path('/home/ubuntu/password-store'), 'Run only in the SDK project'
for executable in ['/usr/bin/pass', '/usr/bin/sailfish-gpg',
                   '/usr/libexec/sailfish-pass-tools/bin/tree']:
    assert Path(executable).is_file(), f'Approved dependency/install missing: {executable}'
output = root / 'test-results'
output.mkdir(exist_ok=True)
fixture = Path(tempfile.mkdtemp(prefix='synthetic-pass-', dir=output))
home, store = fixture / 'gnupg', fixture / 'store'
home.mkdir(mode=0o700)
store.mkdir(mode=0o700)
(fixture / 'synthetic-marker.txt').write_text('Synthetic acceptance only\n')
environment = {'PATH': '/usr/bin:/bin', 'HOME': str(fixture), 'LC_ALL': 'C',
               'GNUPGHOME': str(home), 'SAILFISH_GNUPGHOME': str(home),
               'PASSWORD_STORE_DIR': str(store), 'TERM': 'xterm'}
phrase = 'NOT-A-REAL-SECRET-pass-sdk-acceptance\n'
gpg = ['/usr/bin/sailfish-gpg']
passwd = ['/usr/bin/pass']
conf = ['/usr/libexec/sailfish-gnupg/bin/gpgconf', '--homedir', str(home)]
ipc = ['/usr/libexec/sailfish-gnupg/bin/gpg-connect-agent', '--homedir', str(home)]
record = {'environment': '5.1 SDK integration; no uncached pinentry/5.2 claim',
          'fixture': str(fixture), 'checks': [], 'cleanup_passed': False}

def run(command, data=None):
    result = subprocess.run(command, input=data, text=True, capture_output=True,
                            env=environment, timeout=120)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed ({result.returncode}): {result.stderr}')
    return result.stdout

def passed(name):
    record['checks'].append(name)
    print('PASS ' + name, flush=True)

try:
    socket = Path(run(conf + ['--list-dirs', 'agent-socket']).strip())
    runtime_parent = Path('/run/user') / str(os.getuid()) / 'gnupg'
    assert socket == home / 'S.gpg-agent' or (
        socket.parent.parent == runtime_parent and socket.parent.name.startswith('d.')
        and socket.name == 'S.gpg-agent'), 'Refuse default or unrelated agent socket'
    record['socket'] = str(socket)
    loopback = ['--batch', '--pinentry-mode', 'loopback', '--passphrase-fd', '0']
    run(gpg + loopback + ['--quick-generate-key',
                         'Synthetic Pass SDK <synthetic@example.invalid>',
                         'ed25519', 'sign', '1d'], phrase)
    response = run(ipc + ['--no-autostart', 'GETINFO pid', '/bye'])
    pid = next(line[2:] for line in response.splitlines() if line.startswith('D '))
    assert pid.isdecimal()
    assert Path('/proc/' + pid + '/exe').resolve() == Path('/usr/libexec/sailfish-gnupg/bin/gpg-agent')
    record['agent_pid'] = pid
    keys = run(gpg + ['--with-colons', '--list-keys'])
    fingerprint = next(line.split(':')[9] for line in keys.splitlines()
                       if line.startswith('fpr:'))
    run(gpg + loopback + ['--quick-add-key', fingerprint, 'cv25519', 'encr', '1d'], phrase)
    record['synthetic_fingerprint'] = fingerprint
    passed('protected synthetic signing/encryption keypair')
    run(passwd + ['init', fingerprint])
    assert (store / '.gpg-id').read_text().strip() == fingerprint
    passed('pass init uses the synthetic recipient')
    payload = 'NOT-A-REAL-PASSWORD\nusername=synthetic@example.invalid\n'
    run(passwd + ['insert', '--multiline', 'synthetic/demo'], payload)
    encrypted = store / 'synthetic/demo.gpg'
    assert encrypted.is_file() and payload.encode() not in encrypted.read_bytes()
    assert run(gpg + loopback + ['--decrypt', str(encrypted)], phrase) == payload
    passed('pass insert produces private-runtime-decryptable ciphertext')
    # Agent cache warmed only with this synthetic protected key; no TTY claim.
    assert run(passwd + ['show', 'synthetic/demo']) == payload
    passed('pass show retrieves exact multiline synthetic payload from cache')
    run(passwd + ['generate', '--no-symbols', 'synthetic/generated', '24'])
    generated = run(passwd + ['show', 'synthetic/generated']).strip()
    assert len(generated) == 24 and generated.isascii() and generated.isalnum()
    passed('pass generate roundtrip with expected length/alphabet')
    run(passwd + ['cp', 'synthetic/demo', 'synthetic/copied'])
    assert run(passwd + ['show', 'synthetic/copied']) == payload
    run(passwd + ['mv', 'synthetic/copied', 'synthetic/moved'])
    assert not (store / 'synthetic/copied.gpg').exists()
    assert run(passwd + ['show', 'synthetic/moved']) == payload
    run(passwd + ['rm', '--force', 'synthetic/moved'])
    assert not (store / 'synthetic/moved.gpg').exists()
    passed('pass copy/move/remove stay within synthetic store')
    listing = run(passwd + ['ls', 'synthetic'])
    assert 'demo' in listing and 'generated' in listing and '.gpg' not in listing
    passed('tree-backed store listing')
    response = run(ipc + ['--no-autostart', 'GETINFO pid', '/bye'])
    pid = next(line[2:] for line in response.splitlines() if line.startswith('D '))
    assert pid.isdecimal()
    assert Path('/proc/' + pid + '/exe').resolve() == Path('/usr/libexec/sailfish-gnupg/bin/gpg-agent')
    record['agent_pid'] = pid
    passed('fixture agent executable is private')
except Exception as error:
    record['failure'] = str(error)
    raise
finally:
    try:
        assert 'socket' in record, 'Socket not validated; retain fixture for bounded diagnosis'
        if 'agent_pid' not in record:
            response = run(ipc + ['--no-autostart', 'GETINFO pid', '/bye'])
            pid = next(line[2:] for line in response.splitlines() if line.startswith('D '))
            assert pid.isdecimal()
            assert Path('/proc/' + pid + '/exe').resolve() == Path('/usr/libexec/sailfish-gnupg/bin/gpg-agent')
            record['agent_pid'] = pid
        run(conf + ['--kill', 'gpg-agent'])
        for attempt in range(40):
            probe = subprocess.run(ipc + ['--no-autostart', 'GETINFO pid', '/bye'],
                                   env=environment, text=True, capture_output=True, timeout=5)
            process_absent = not Path('/proc/' + record['agent_pid']).exists()
            if ('no gpg-agent running in this session' in probe.stderr and process_absent
                    and not Path(record.get('socket', str(home / 'S.gpg-agent'))).exists()):
                break
            time.sleep(0.25)
        else:
            raise RuntimeError('Fixture agent process/socket still present after bounded wait')
        if 'socket' in record and socket.parent != home and socket.parent.exists():
            socket.parent.rmdir()  # Only the verified nondefault directory, and only if empty.
        assert fixture.parent == output and not fixture.is_symlink()
        shutil.rmtree(fixture)
        record['cleanup_passed'] = True
    except Exception as error:
        record['cleanup_failure'] = str(error)
    (root / 'evidence/e2e-sdk-20261011.json').write_text(json.dumps(record, indent=2) + '\n')
    if not record['cleanup_passed']:
        raise RuntimeError('Synthetic cleanup incomplete; see recorded fixture')

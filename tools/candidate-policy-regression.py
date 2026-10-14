#!/usr/bin/env python3
"""Focused synthetic regression, after separately approved candidate installation.

No real homes, keys or stores; no RPM installation. SDK loopback does not prove
fresh TTY pinentry. Earlier core algorithm/interoperability evidence is reused.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path('/home/ubuntu/password-store')
assert Path(__file__).resolve().parents[1] == root, 'SDK project only'
assert os.getuid() != 0, 'Run as ordinary SDK test user'
(root / 'test-results').mkdir(exist_ok=True)
fixture = Path(tempfile.mkdtemp(prefix='synthetic-policy-', dir=root / 'test-results'))
home, store = fixture / 'home', fixture / 'store'
home.mkdir(mode=0o700)
store.mkdir(mode=0o700)
env = {'PATH': '/usr/bin:/bin', 'HOME': str(fixture), 'LC_ALL': 'C',
       'SAILFISH_GNUPGHOME': str(home), 'PASSWORD_STORE_DIR': str(store), 'TERM': 'dumb'}
gpg = '/usr/bin/sailfish-gpg'
control = '/usr/bin/sailfish-gpg-agent'
password = '/usr/bin/sailfish-pass'
record = {'scope': 'focused SDK synthetic runtime regression; no TTY/native/release claim',
          'fixture': str(fixture), 'checks': [], 'cleanup': False, 'passed': False}
pid = None
unknown_launch = False

def run(args, data=None, expected=0):
    global unknown_launch
    if expected == 0 and (args[0] in (gpg, password) or args == [control, 'start']):
        unknown_launch = True
    result = subprocess.run(args, input=data, text=True, capture_output=True,
                            env=env, timeout=60)
    assert result.returncode == expected, (args[0], result.returncode, result.stderr)
    if args == [control, 'stop'] and result.returncode == 0:
        unknown_launch = False
    return result.stdout

def passed(name):
    record['checks'].append(name)
    print('PASS: ' + name, flush=True)

try:
    run([control, 'status'], expected=3)
    for name in ['common.conf', 'gpg-agent.conf']:
        path = home / name
        path.write_text('# Synthetic forbidden configuration\n')
        try:
            run([gpg, '--version'], expected=78)
            run([control, 'start'], expected=78)
        finally:
            path.unlink()
    passed('ordinary GPG and agent control refuse synthetic unsupported configs')
    unknown_launch = True
    response = run([control, 'start'])
    pid = int(response.strip().split()[-1])
    unknown_launch = False
    assert Path(f'/proc/{pid}/exe').resolve() == Path('/usr/libexec/sailfish-gnupg/bin/gpg-agent')
    assert run([control, 'start']) == response
    assert run([control, 'status']) == response
    run([gpg, '--version'])
    passed('real private agent start/status/reuse passes executable and mapped-library policy')
    run([control, 'stop'])
    assert not Path(f'/proc/{pid}').exists()
    pid = None
    run([control, 'status'], expected=3)
    passed('real stop confirms fixture process and socket disappearance')
    phrase = 'NOT-A-REAL-SECRET-policy-regression\n'
    loopback = [gpg, '--batch', '--pinentry-mode', 'loopback', '--passphrase-fd', '0']
    unknown_launch = True
    run(loopback + ['--quick-generate-key', 'Synthetic Policy <synthetic@example.invalid>',
                    'ed25519', 'sign', '1d'], phrase)
    keys = run([gpg, '--with-colons', '--list-keys'])
    fingerprint = next(line.split(':')[9] for line in keys.splitlines() if line.startswith('fpr:'))
    run(loopback + ['--quick-add-key', fingerprint, 'cv25519', 'encr', '1d'], phrase)
    pid = int(run([control, 'status']).strip().split()[-1])
    unknown_launch = False
    run([password, 'init', fingerprint])
    payload = 'NOT-A-REAL-PASSWORD\nusername=synthetic@example.invalid\n'
    run([password, 'insert', '--multiline', 'synthetic/demo'], payload)
    run([control, 'stop'])
    pid = None
    run([control, 'status'], expected=3)
    # Protected-key loopback proves decryption after agent reset. It then warms
    # only this fixture cache for pass show; this is explicitly not a TTY test.
    unknown_launch = True
    assert run(loopback + ['--decrypt', str(store / 'synthetic/demo.gpg')], phrase) == payload
    pid = int(run([control, 'status']).strip().split()[-1])
    unknown_launch = False
    assert run([password, 'show', 'synthetic/demo']) == payload
    passed('one protected synthetic pass roundtrip; reset then loopback decryption and cached show')
    record['passed'] = True
except Exception as error:
    record['failure'] = str(error)
    raise
finally:
    try:
        state = subprocess.run([control, 'status'], env=env, text=True,
                               capture_output=True, timeout=60)
        if state.returncode == 0:
            verified_pid = int(state.stdout.strip().split()[-1])
            run([control, 'stop'])
            assert not Path(f'/proc/{verified_pid}').exists()
            unknown_launch = False
        else:
            # Absence alone cannot prove an orphan is gone. Preserve fixture
            # if the last confirmed process still exists or status is unsafe.
            assert state.returncode == 3
            assert not unknown_launch, 'Unverified launch outcome; preserve fixture/packages for exact process audit'
        assert pid is None or not Path(f'/proc/{pid}').exists()
        record['cleanup'] = True
    except Exception as error:
        record['cleanup_failure'] = str(error)
        raise
    finally:
        record['unknown_launch'] = unknown_launch
        (fixture / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        print('Evidence fixture:', fixture, flush=True)

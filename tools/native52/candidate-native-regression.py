#!/usr/bin/env python3
"""Focused native synthetic regression, after separately approved dev installation.

No real homes, keys or stores; no RPM installation. Core loopback does not prove fresh TTY; explicit tty phase tests prompting. Earlier core algorithm/interoperability evidence is reused.
"""
import re
import argparse
import stat
import json
import os
from pathlib import Path
import subprocess
import tempfile

assert os.getuid() == 100000 and os.uname().machine == 'aarch64', 'Native dev user only'
version = next(line.split('=', 1)[1].strip('"') for line in Path('/etc/os-release').read_text().splitlines() if line.startswith('VERSION_ID='))
assert version == '5.2.0.18', 'Scoped dev OS only'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('phase', choices=['core', 'tty'])
parser.add_argument('fixture', nargs='?', type=Path)
args = parser.parse_args()
if args.phase == 'core':
    assert args.fixture is None
    fixture = Path(tempfile.mkdtemp(prefix='synthetic-native-policy-', dir='/tmp'))
    home, store = fixture / 'home', fixture / 'store'
    home.mkdir(mode=0o700)
    store.mkdir(mode=0o700)
    (fixture / 'synthetic-marker.txt').write_text('Synthetic private policy regression only\n')
    (fixture / 'expected-demo.txt').write_text('NOT-A-REAL-PASSWORD\nusername=synthetic@example.invalid\n')
else:
    fixture = args.fixture
    assert fixture is not None and fixture.parent == Path('/tmp') and fixture.name.startswith('synthetic-native-policy-')
    for path in [fixture, fixture / 'home', fixture / 'store']:
        assert not path.is_symlink() and path.is_dir()
        assert path.stat().st_uid == 100000 and stat.S_IMODE(path.stat().st_mode) == 0o700
    for name in ['synthetic-marker.txt', 'result.json', 'expected-demo.txt']:
        path = fixture / name
        assert not path.is_symlink() and stat.S_ISREG(path.stat().st_mode) and path.stat().st_uid == 100000
    assert (fixture / 'synthetic-marker.txt').read_text() == 'Synthetic private policy regression only\n'
    prior = json.loads((fixture / 'result.json').read_text())
    assert prior['fixture'] == str(fixture) and prior['passed'] is True and prior['cleanup'] is True and prior['unknown_launch'] is False
    assert all(not Path('/proc/' + str(pid)).exists() for pid in prior['verified_pids'])
    assert not (fixture / 'tty-result.json').exists(), 'Fresh TTY evidence only'
    home, store = fixture / 'home', fixture / 'store'
env = {'PATH': '/usr/bin:/bin', 'HOME': str(fixture), 'LC_ALL': 'C',
       'SAILFISH_GNUPGHOME': str(home), 'PASSWORD_STORE_DIR': str(store), 'TERM': 'dumb'}
gpg = '/usr/bin/sailfish-gpg'
control = '/usr/bin/sailfish-gpg-agent'
password = '/usr/bin/sailfish-pass'
record = {'scope': 'focused native Xperia5.2 synthetic regression; no release claim',
          'fixture': str(fixture), 'checks': [], 'cleanup': False, 'passed': False}
socket = None
verified_pids = set()
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
    socket = Path(run(['/usr/libexec/sailfish-gnupg/bin/gpgconf', '--homedir', str(home), '--list-dirs', 'agent-socket']).strip())
    assert socket == home / 'S.gpg-agent' or (socket.name == 'S.gpg-agent' and socket.parent.name.startswith('d.') and socket.parent.parent == Path('/run/user/100000/gnupg'))
    record['socket'] = str(socket)
    if args.phase == 'tty':
        assert str(socket) == prior['socket']
        assert not socket.exists() and not socket.is_symlink()
    if args.phase == 'tty':
        run([control, 'status'], expected=3)
        tty = os.ttyname(0)
        assert re.fullmatch(r'/dev/(?:pts/[0-9]+|tty[0-9]+)', tty) and stat.S_ISCHR(os.stat(tty).st_mode)
        env['GPG_TTY'] = tty
        env['TERM'] = os.environ.get('TERM', 'xterm')
        print('Fresh-cache synthetic passphrase: NOT-A-REAL-SECRET-policy-regression', flush=True)
        unknown_launch = True
        actual = subprocess.run([password, 'show', 'synthetic/demo'], env=env,
                                text=True, stdout=subprocess.PIPE, timeout=120)
        assert actual.returncode == 0 and actual.stdout == (fixture / 'expected-demo.txt').read_text()
        pid = int(run([control, 'status']).strip().split()[-1])
        verified_pids.add(pid)
        unknown_launch = False
        passed('fresh tty pinentry pass show returns exact synthetic bytes')
        record['passed'] = True
    else:
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
        verified_pids.add(pid)
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
        verified_pids.add(pid)
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
        verified_pids.add(pid)
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
            verified_pids.add(verified_pid)
            run([control, 'stop'])
            assert not Path(f'/proc/{verified_pid}').exists()
            unknown_launch = False
        else:
            # Absence alone cannot prove an orphan is gone. Preserve fixture
            # if the last confirmed process still exists or status is unsafe.
            assert state.returncode == 3
            assert not unknown_launch, 'Unverified launch outcome; preserve fixture/packages for exact process audit'
        assert all(not Path('/proc/' + str(p)).exists() for p in verified_pids)
        assert socket is not None and not socket.exists() and not socket.is_symlink()
        record['cleanup'] = True
    except Exception as error:
        record['cleanup_failure'] = str(error)
        raise
    finally:
        record['unknown_launch'] = unknown_launch
        record['verified_pids'] = sorted(verified_pids)
        (fixture / ('result.json' if args.phase == 'core' else 'tty-result.json')).write_text(json.dumps(record, indent=2) + '\n')
        print('Evidence fixture:', fixture, flush=True)

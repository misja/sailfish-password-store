#!/usr/bin/env python3
"""Focused two-home/concurrent-start native dev5.1 test; no keys or store.

Run only after separately scoped installation of the frozen candidate RPMs.
Interrupted-owner IPC is measured by the separate host-only stub test. This
script never kills an unverified agent or treats a missing socket as process
absence. Preserve the fixture if startup/cleanup is uncertain.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile

assert os.getuid() == 100000 and os.uname().machine == 'aarch64'
version = next(line.split('=', 1)[1].strip('"') for line in Path('/etc/os-release').read_text().splitlines() if line.startswith('VERSION_ID='))
assert version == '5.1.0.11', 'Scoped dev device only'
for package, identity in [('sailfish-gnupg-private', '2.5.24-0.3 aarch64'),
                          ('sailfish-pass', '1.7.4-0.3 noarch'),
                          ('sailfish-pass-tree', '2.3.2-0.1 aarch64')]:
    assert subprocess.check_output(['/usr/bin/rpm', '-q', '--qf', '%{VERSION}-%{RELEASE} %{ARCH}', package], text=True) == identity

fixture = Path(tempfile.mkdtemp(prefix='synthetic-native-lifecycle-', dir='/tmp'))
(fixture / 'synthetic-marker.txt').write_text('Synthetic agent lifecycle only; no keys or passwords\n')
homes = [fixture / 'home-a', fixture / 'home-b']
for home in homes:
    home.mkdir(mode=0o700)
control = '/usr/bin/sailfish-gpg-agent'
conf = '/usr/libexec/sailfish-gnupg/bin/gpgconf'
known = set()
uncertain = {str(home): False for home in homes}
sockets = {}
record = {'scope': 'native dev5.1 two synthetic homes and concurrent start only',
          'fixture': str(fixture), 'checks': [], 'passed': False, 'cleanup': False}
workers = []
workers_incomplete = False

def environment(home):
    return {'PATH': '/usr/bin:/bin', 'HOME': str(fixture), 'LC_ALL': 'C',
            'SAILFISH_GNUPGHOME': str(home), 'TERM': 'dumb'}

def run(home, action, expected=0):
    if action == 'start':
        uncertain[str(home)] = True
    response = subprocess.run([control, action], env=environment(home),
                              capture_output=True, text=True, timeout=60)
    assert response.returncode == expected, (action, response.returncode, response.stderr)
    if expected == 0 and action in ('start', 'status'):
        assert response.stdout.startswith('Private agent running: ')
        pid = int(response.stdout.strip().split()[-1])
        assert Path(f'/proc/{pid}/exe').resolve() == Path('/usr/libexec/sailfish-gnupg/bin/gpg-agent')
        known.add(pid)
        uncertain[str(home)] = False
        return pid
    return response

def passed(name):
    record['checks'].append(name)
    print('PASS: ' + name, flush=True)

try:
    for home in homes:
        raw = subprocess.check_output([conf, '--homedir', str(home), '--list-dirs', 'agent-socket'],
                                      env=environment(home), text=True, timeout=60).strip()
        socket = Path(raw)
        assert socket == home / 'S.gpg-agent' or (socket.name == 'S.gpg-agent' and socket.parent.name.startswith('d.') and socket.parent.parent == Path('/run/user/100000/gnupg'))
        assert not socket.exists() and not socket.is_symlink()
        sockets[str(home)] = str(socket)
        run(home, 'status', expected=3)
    assert len(set(sockets.values())) == 2
    uncertain[str(homes[0])] = True
    for _ in range(2):
        workers.append(subprocess.Popen([control, 'start'], env=environment(homes[0]),
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                        start_new_session=True))
    replies = []
    outcomes = []
    for worker in workers:
        try:
            stdout, stderr = worker.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            workers_incomplete = True
            outcomes.append({'returncode': None, 'timeout': True})
            continue
        outcomes.append({'returncode': worker.returncode, 'stdout': stdout, 'stderr': stderr})
        if worker.returncode != 0:
            workers_incomplete = True
        if stdout.startswith('Private agent running: ') and stdout.strip().split()[-1].isdigit():
            reply_pid = int(stdout.strip().split()[-1])
            known.add(reply_pid)  # Retain every reported PID if concurrent replies differ.
            replies.append(reply_pid)
    record['concurrent_worker_outcomes'] = outcomes
    assert not workers_incomplete and len(replies) == 2, 'Concurrent worker failure: preserve fixture/runtime'
    pid_a = run(homes[0], 'status')
    assert replies == [pid_a, pid_a]
    passed('two concurrent starts report the same verified agent PID')
    pid_b = run(homes[1], 'start')
    assert pid_a != pid_b and run(homes[0], 'status') == pid_a
    passed('two canonical synthetic homes have distinct agents and sockets')
    run(homes[0], 'stop')
    assert not Path(f'/proc/{pid_a}').exists()
    run(homes[0], 'status', expected=3)
    assert run(homes[1], 'status') == pid_b
    passed('stopping home A leaves home B agent unchanged')
    run(homes[1], 'stop')
    assert not Path(f'/proc/{pid_b}').exists()
    passed('home B stop confirms its verified process disappearance')
    record['passed'] = True
except Exception as error:
    record['failure'] = str(error)
    raise
finally:
    try:
        # These are only our own foreground control workers, never agent PIDs.
        for worker in workers:
            if worker.poll() is None:
                workers_incomplete = True
                worker.terminate()
                try:
                    worker.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait(timeout=3)
        for home in homes:
            state = subprocess.run([control, 'status'], env=environment(home),
                                   capture_output=True, text=True, timeout=60)
            if state.returncode == 0:
                pid = run(home, 'status')
                run(home, 'stop')
                assert not Path(f'/proc/{pid}').exists()
            else:
                assert state.returncode == 3 and not uncertain[str(home)], 'Uncertain launch: preserve fixture/runtime'
        assert all(not Path(f'/proc/{pid}').exists() for pid in known)
        assert all(not Path(path).exists() and not Path(path).is_symlink() for path in sockets.values())
        assert not workers_incomplete, 'Uncertain control-worker outcome: preserve fixture/runtime for exact audit'
        record['cleanup'] = True
    except Exception as error:
        record['cleanup_failure'] = str(error)
    record['known_pids'] = sorted(known)
    record['uncertain_launch'] = uncertain
    record['workers_incomplete'] = workers_incomplete
    record['sockets'] = sockets
    record['limitations'] = ['No interrupted-owner/native watchdog test',
                             'Known process/socket cleanup only; no claim about unobserved orphans',
                             'No changed-payload upgrade or RPM-enforced shutdown']
    (fixture / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Evidence fixture:', fixture, flush=True)
    if not record['cleanup']:
        raise SystemExit('Cleanup uncertain; retain fixture and packages for exact audit')

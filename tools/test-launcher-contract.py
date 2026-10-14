#!/usr/bin/env python3
"""Host-only launcher contract checks with synthetic directories and stub payloads.

No package install, private key, real store or cryptographic integration test.
Only fixed payload paths are substituted in temporary wrapper copies.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import socket
import signal
import time
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--gpg-wrapper', type=Path, required=True)
parser.add_argument('--output', type=Path)
args = parser.parse_args()
def invoke(command, env, timeout=10):
    # Every endpoint is a synthetic stub. Isolate its process group so failed
    # shell/timer experiments cannot leak helpers or consume the user's CPU.
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()

pass_wrapper = Path(__file__).resolve().parents[1] / 'runtime/sailfish-pass'
record = {'scope': 'host-only synthetic contract checks; stub payloads, no crypto/device claim',
          'entry_interpreter': '/usr/bin/busybox sh',
          'source_sha256': {'policy': hashlib.sha256((args.gpg_wrapper.parent / 'runtime-policy.sh').read_bytes()).hexdigest(),
                            'agent_control': hashlib.sha256((args.gpg_wrapper.parent / 'sailfish-gpg-agent').read_bytes()).hexdigest(),
                            'pass': hashlib.sha256(pass_wrapper.read_bytes()).hexdigest(),
                            'gpg': hashlib.sha256(args.gpg_wrapper.read_bytes()).hexdigest()},
          'checks': []}
with tempfile.TemporaryDirectory(prefix='synthetic-launcher-contract-', dir='/tmp') as directory:
    root = Path(directory).resolve()
    home, store, hostile = root / 'private-home', root / 'private-store', root / 'hostile'
    for path in (home, store, hostile):
        path.mkdir(mode=0o700)
    marker = root / 'startup-executed'
    startup = hostile / 'startup.sh'
    startup.write_text(f'/usr/bin/touch "{marker}"\n')
    for name in ('stat', 'id', 'bash'):
        path = hostile / name
        path.write_text(f'#!/bin/sh\n/usr/bin/touch "{marker}"\nexit 0\n')
        path.chmod(0o700)
    payload = root / 'synthetic-payload'
    payload.write_text('''#!/bin/sh
test synthetic = synthetic || exit 1
printf 'SYNTHETIC_PAYLOAD\n'
printf 'BASH_ENV=%s ENV=%s LD_AUDIT=%s GPG_AGENT_INFO=%s\n' "${BASH_ENV-unset}" "${ENV-unset}" "${LD_AUDIT-unset}" "${GPG_AGENT_INFO-unset}"
printf 'GNUPGHOME=%s\n' "$GNUPGHOME"
printf 'ARG=%s\n' "$@"
''')
    payload.chmod(0o700)
    prefix, proc = root / 'runtime', root / 'proc'
    for path in (prefix / 'bin', prefix / 'lib', prefix / 'libexec', prefix / 'etc/gnupg', proc):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    account_home, socket_parent = root / 'account-home', root / 'socket-dir'
    account_home.mkdir(mode=0o700)
    socket_parent.mkdir(mode=0o700)
    agent_socket = socket_parent / 'S.gpg-agent'
    account_file = root / 'account-record'
    account_file.write_text(f'synthetic:x:{os.getuid()}:{os.getgid()}:Synthetic:{account_home}:/bin/sh\n')
    getent = root / 'getent-stub'
    getent.write_text(f'#!/bin/sh\n/bin/cat "{account_file}"\n')
    getent.chmod(0o700)
    conf = prefix / 'bin/gpgconf'
    conf.write_text(f'#!/bin/sh\nprintf "%s\\n" "{agent_socket}"\n')
    conf.chmod(0o700)
    response_file = root / 'ipc-response'
    response_file.write_text('D 4242\nOK\n')
    ipc = prefix / 'bin/gpg-connect-agent'
    ipc_guard = """for argument in "$@"; do
case "$argument" in --no-history|--homedir|--raw-socket|--agent-program) ;; --*) exit 2 ;; esac
done
"""
    ipc.write_text('#!/bin/sh\n' + ipc_guard + f'/bin/cat "{response_file}"\n')
    ipc.chmod(0o700)
    initial_ipc = ipc.read_text()
    agent = prefix / 'bin/gpg-agent'
    agent.write_text('synthetic executable metadata fixture\n')
    agent.chmod(0o700)
    policy = prefix / 'libexec/runtime-policy.sh'
    policy.write_text((args.gpg_wrapper.parent / 'runtime-policy.sh').read_text()
                      .replace('/usr/libexec/sailfish-gnupg', str(prefix))
                      .replace('proc_root=/proc', f'proc_root={proc}')
                      .replace('/usr/bin/getent', str(getent))
                      .replace('/usr/bin/busybox sleep 15 &', '/usr/bin/busybox sleep 1 &'))
    control = root / 'agent-control'
    control.write_text((args.gpg_wrapper.parent / 'sailfish-gpg-agent').read_text()
                       .replace('/usr/libexec/sailfish-gnupg', str(prefix)))
    control.chmod(0o700)
    copies = {}
    for kind, source in (('pass', pass_wrapper), ('gpg', args.gpg_wrapper)):
        text = source.read_text()
        if kind == 'pass':
            text = text.replace('/usr/bin/sailfish-gpg', str(payload))
            text = text.replace('/usr/libexec/sailfish-pass/bin/pass', str(payload))
        else:
            text = text.replace('/usr/libexec/sailfish-gnupg/bin/gpg ', str(payload) + ' ')
            text = text.replace('/usr/libexec/sailfish-gnupg', str(prefix))
        path = root / (kind + '-wrapper')
        path.write_text(text)
        path.chmod(0o700)
        copies[kind] = path
    base = {'PATH': str(hostile), 'HOME': str(root), 'LANG': 'C',
            'SAILFISH_GNUPGHOME': str(home), 'PASSWORD_STORE_DIR': str(store),
            'BASH_ENV': str(startup), 'ENV': str(startup), 'CDPATH': str(hostile),
            'GPG_AGENT_INFO': 'synthetic:invalid:1',
            'SHELLOPTS': 'xtrace', 'GCONV_PATH': str(hostile),
            'BASH_FUNC_test%%': f'() {{ /usr/bin/touch "{marker}"; return 0; }}'}

    def run(kind, env=None, arguments=None, expected=64, name=''):
        result = invoke([str(copies[kind])] + (arguments or ['--version']), env=env or base)
        assert result.returncode == expected, (kind, name, result.returncode, result.stderr)
        assert not marker.exists(), (kind, name, 'caller startup or utility executed')
        if expected == 0:
            assert 'SYNTHETIC_PAYLOAD' in result.stdout
            assert 'BASH_ENV=unset ENV=unset LD_AUDIT=unset GPG_AGENT_INFO=unset' in result.stdout
            assert 'GNUPGHOME=' + (env or base)['SAILFISH_GNUPGHOME'] in result.stdout
        else:
            assert 'SYNTHETIC_PAYLOAD' not in result.stdout
        record['checks'].append(kind + ': ' + name)
        return result

    alias = root / 'alias'
    alias.symlink_to(home, target_is_directory=True)
    parent_alias = root / 'parent-alias'
    parent_alias.symlink_to(root, target_is_directory=True)
    unsafe = root / 'unsafe'
    unsafe.mkdir(mode=0o755)
    for kind in ('pass', 'gpg'):
        run(kind, expected=0, name='valid canonical paths; hostile PATH and startup hooks ignored')
        for name, value in [('missing home', ''), ('relative home', 'synthetic-relative'),
                            ('mode755', str(unsafe)), ('final symlink', str(alias)),
                            ('parent symlink', str(parent_alias / 'private-home')),
                            ('dot alias', str(home) + '/.'), ('parent alias', str(home) + '/../private-home'),
                            ('trailing separator', str(home) + '/')]:
            run(kind, dict(base, SAILFISH_GNUPGHOME=value), name=name)
    for name, value in [('missing store', ''), ('relative store', 'synthetic-relative'),
                        ('same home/store', str(home)), ('store path alias', str(parent_alias / 'private-store'))]:
        run('pass', dict(base, PASSWORD_STORE_DIR=value), name=name)
    child = home / 'nested-store'
    child.mkdir(mode=0o700)
    run('pass', dict(base, PASSWORD_STORE_DIR=str(child)), name='store nested in home')
    child2 = store / 'nested-home'
    child2.mkdir(mode=0o700)
    run('pass', dict(base, SAILFISH_GNUPGHOME=str(child2)), name='home nested in store')
    spaced_home, spaced_store = root / 'private home with spaces', root / 'private store with spaces'
    spaced_home.mkdir(mode=0o700)
    spaced_store.mkdir(mode=0o700)
    for kind in ('pass', 'gpg'):
        run(kind, dict(base, SAILFISH_GNUPGHOME=str(spaced_home)), expected=0, name='canonical home with spaces')
    run('pass', dict(base, PASSWORD_STORE_DIR=str(spaced_store)), expected=0, name='canonical store with spaces')
    for option in ('--homedir', '--homed', '--options', '--opt', '--agent-program', '--agent-p', '--keyring', '--keyr', '--secret-keyring', '--secret-key'):
        run('gpg', arguments=[option + '=synthetic'], name='override refusal ' + option)
    for option in ('--dirmngr-program', '--dirmngr-p', '--keyboxd-program', '--keyboxd-p', '--exec-path', '--exec-p'):
        run('gpg', arguments=[option + '=synthetic'], name='helper override equals refusal ' + option)
        run('gpg', arguments=[option, 'synthetic'], name='helper override separate refusal ' + option)
    for option in ('--photo-viewer', '--photo-v', '--chuid', '--chu', '--use-keyboxd', '--use-keyb', '--primary-keyring', '--primary-keyr', '--trustdb-name', '--trustdb-n'):
        run('gpg', arguments=[option + '=synthetic'], name='additional isolation override refusal ' + option)
    result = run('gpg', arguments=['--version'], expected=0, name='forced no-options and home passed to payload')
    assert f'ARG=--no-options\nARG=--homedir\nARG={home}\n' in result.stdout
    assert f'ARG=--agent-program\nARG={prefix}/bin/gpg-agent|--no-options\nARG=--disable-dirmngr\nARG=--version\n' in result.stdout

    for name in ('common.conf', 'gpg-agent.conf', 'common.conf-2.5.24', 'gpg-agent.conf-2.5'):
        configuration = home / name
        configuration.write_text('synthetic unsupported option\n')
        run('gpg', expected=78, name='configuration file refused ' + name)
        configuration.unlink()
        configuration.symlink_to(root / 'nonexistent')
        run('gpg', expected=78, name='dangling configuration symlink refused ' + name)
        configuration.unlink()
        configuration.mkdir()
        run('gpg', expected=78, name='configuration directory refused ' + name)
        configuration.rmdir()
    for configuration in (prefix / 'etc/gnupg/common.conf', prefix / 'etc/gnupg/gpg-agent.conf', prefix / 'etc/gnupg/gpg.conf', prefix / 'etc/gnupg/common.conf-2.5', prefix / 'bin/gpgconf.ctl'):
        configuration.write_text('synthetic unsupported system configuration\n')
        run('gpg', expected=78, name='system configuration refused ' + configuration.name)
        configuration.unlink()
    stock_home = account_home / '.gnupg'
    stock_home.mkdir(mode=0o700)
    run('gpg', dict(base, SAILFISH_GNUPGHOME=str(stock_home)), name='account stock home refused independently of HOME')
    nested_stock = stock_home / 'nested'
    nested_stock.mkdir(mode=0o700)
    run('gpg', dict(base, SAILFISH_GNUPGHOME=str(nested_stock)), name='home within stock home refused')
    run('gpg', dict(base, SAILFISH_GNUPGHOME=str(account_home)), name='home containing stock home refused')
    nested_stock.rmdir()
    stock_home.rmdir()
    stock_home.symlink_to(home, target_is_directory=True)
    run('gpg', name='stock home alias to private home refused')
    stock_home.unlink()
    saved_account = account_file.read_text()
    account_file.write_text('synthetic:x:999999:999999:Synthetic:/nonexistent:/bin/sh\n')
    run('gpg', name='mismatched account refused')
    account_file.write_text(saved_account)

    fake_process = proc / '4242'
    fake_process.mkdir(mode=0o700)
    (fake_process / 'exe').symlink_to(agent)
    cmdline = fake_process / 'cmdline'
    expected_cmdline = b'\0'.join(os.fsencode(x) for x in (str(agent), '--homedir', str(home), '--no-options', '--daemon')) + b'\0'
    cmdline.write_bytes(expected_cmdline)
    map_lines = []
    for soname in ('libgcrypt.so.20', 'libassuan.so.9', 'libgpg-error.so.0', 'libnpth.so.0'):
        library = prefix / 'lib' / (soname + '.synthetic')
        library.write_text('public synthetic mapping fixture\n')
        (prefix / 'lib' / soname).symlink_to(library.name)
        map_lines.append(f'1000-2000 r-xp 00000000 00:00 {library.stat().st_ino} {library}\n')
    maps = fake_process / 'maps'
    good_maps = ''.join(map_lines)
    maps.write_text(good_maps)
    with socket.socket(socket.AF_UNIX) as fixture_socket:
        fixture_socket.bind(str(agent_socket))
        agent_socket.chmod(0o700)
        run('gpg', expected=0, name='current private agent metadata accepted')
        agent_socket.chmod(0o755)
        run('gpg', expected=78, name='unsafe agent socket mode refused')
        agent_socket.chmod(0o700)
        response_file.write_text('OK\n')
        run('gpg', expected=78, name='IPC success without PID refused')
        response_file.write_text('D invalid\nOK\n')
        run('gpg', expected=78, name='invalid PID refused')
        response_file.write_text('D 4242\nOK\n')
        (fake_process / 'exe').unlink()
        (fake_process / 'exe').symlink_to(payload)
        run('gpg', expected=78, name='foreign executable refused')
        (fake_process / 'exe').unlink()
        (fake_process / 'exe').symlink_to(agent)
        cmdline.write_bytes(expected_cmdline.replace(b'--no-options', b'--pinentry-program'))
        run('gpg', expected=78, name='foreign agent launch options refused')
        cmdline.write_bytes(expected_cmdline)
        for name, value in [('deleted private mapping', good_maps.replace('\n', ' (deleted)\n', 1)),
                            ('foreign crypto mapping', good_maps.replace(str(prefix / 'lib'), '/synthetic-stock/lib', 1)),
                            ('missing crypto mapping', ''.join(map_lines[1:])),
                            ('obsolete library inode', good_maps.replace(str((prefix / 'lib/libgcrypt.so.20.synthetic').stat().st_ino), '0', 1))]:
            maps.write_text(value)
            run('gpg', expected=78, name=name)
        maps.write_text(good_maps)
        ipc.write_text('#!/bin/sh\n' + ipc_guard + f'printf "%s\\n" "$$" > "{root}/hung-ipc-pid"\nexec /usr/bin/busybox sleep 30\n')
        started = time.monotonic()
        run('gpg', expected=78, name='hung IPC terminated by own process watchdog')
        assert time.monotonic() - started < 5
        hung_pid = int((root / 'hung-ipc-pid').read_text())
        assert not Path(f'/proc/{hung_pid}').exists()
        ipc.write_text('#!/bin/sh\n' + ipc_guard + f'trap "" TERM\nprintf "%s\\n" "$$" > "{root}/hung-ipc-pid"\nexec /usr/bin/busybox sleep 30\n')
        started = time.monotonic()
        run('gpg', expected=78, name='TERM-ignoring IPC killed after bounded grace')
        assert time.monotonic() - started < 5
        hung_pid = int((root / 'hung-ipc-pid').read_text())
        assert not Path(f'/proc/{hung_pid}').exists()
        ipc.write_text(initial_ipc)
        result = invoke([str(control), 'status'], env=base, timeout=10)
        assert result.returncode == 0 and '4242' in result.stdout
        record['checks'].append('agent control: verified status')
        result = invoke([str(control), 'start'], env=base, timeout=10)
        assert result.returncode == 0 and '4242' in result.stdout
        record['checks'].append('agent control: reuse verified agent')
    agent_socket.unlink()
    lifecycle_stub = root / 'lifecycle-ipc-stub.py'
    lifecycle_stub.write_text('''#!/usr/bin/python3
import os, pathlib, socket, sys
root = pathlib.Path(__file__).resolve().parent
prefix = root / 'runtime'
proc = root / 'proc/4242'
sock = root / 'socket-dir/S.gpg-agent'
if 'KILLAGENT' in sys.argv:
    for file in proc.iterdir(): file.unlink()
    proc.rmdir()
    sock.unlink()
else:
    proc.mkdir(exist_ok=True, mode=0o700)
    (proc / 'exe').symlink_to(prefix / 'bin/gpg-agent')
    argv = (str(prefix / 'bin/gpg-agent'), '--homedir', str(root / 'private-home'), '--no-options', '--daemon')
    (proc / 'cmdline').write_bytes(b'\\0'.join(os.fsencode(x) for x in argv) + b'\\0')
    lines = []
    for name in ('libgcrypt.so.20', 'libassuan.so.9', 'libgpg-error.so.0', 'libnpth.so.0'):
        file = (prefix / 'lib' / name).resolve()
        lines.append(f'1000-2000 r-xp 00000000 00:00 {file.stat().st_ino} {file}\\n')
    (proc / 'maps').write_text(''.join(lines))
    with socket.socket(socket.AF_UNIX) as fixture: fixture.bind(str(sock))
    sock.chmod(0o700)
print('D 4242\\nOK')
''')
    lifecycle_stub.chmod(0o700)
    # Existing original metadata fixture is absent before simulating autostart.
    for file in fake_process.iterdir(): file.unlink()
    fake_process.rmdir()
    ipc.write_text('#!/bin/sh\n' + ipc_guard + f'case " $* " in *" KILLAGENT "*|*" --agent-program "*) exec "{lifecycle_stub}" "$@";; esac\n/bin/cat "{response_file}"\n')
    result = invoke([str(control), 'start'], env=base, timeout=20)
    assert result.returncode == 0 and '4242' in result.stdout, result.stderr
    record['checks'].append('agent control: absent start verifies newly created metadata fixture')
    result = invoke([str(control), 'stop'], env=base, timeout=20)
    assert result.returncode == 0 and not agent_socket.exists() and not fake_process.exists(), result.stderr
    record['checks'].append('agent control: stop confirms process and socket absence')
    result = invoke([str(control), 'start'], env=base, timeout=20)
    assert result.returncode == 0, result.stderr
    ipc.write_text(initial_ipc)  # A success reply alone must not prove stop.
    result = invoke([str(control), 'stop'], env=base, timeout=20)
    assert result.returncode == 78 and agent_socket.exists() and fake_process.exists(), result.stderr
    record['checks'].append('agent control: stop success without disappearance refused')
    for file in fake_process.iterdir(): file.unlink()
    fake_process.rmdir()
    agent_socket.unlink()
    # A fabricated successful autostart response is insufficient without a socket/process.
    result = invoke([str(control), 'start'], env=base, timeout=20)
    assert result.returncode == 78 and not agent_socket.exists(), result.stderr
    record['checks'].append('agent control: autostart success without verified process refused')
    for action, expected in [('status', 3), ('stop', 3), ('unsupported', 64)]:
        result = invoke([str(control), action], env=base, timeout=10)
        assert result.returncode == expected, (action, result.returncode, result.stderr)
        record['checks'].append('agent control: absent ' + action)

record['passed'] = True
if args.output:
    args.output.write_text(json.dumps(record, indent=2) + '\n')
print(f'PASS: {len(record["checks"])} synthetic launcher-contract checks; stub payloads only')

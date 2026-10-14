#!/usr/bin/env python3
"""Approved synthetic SDK transaction test, including mandatory cleanup."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

scratch = Path('/var/tmp/sailfish-shell-sdk-review')
runner = scratch / 'shell-provider-transaction.py'
inputs = scratch / 'fixture-inputs'
prefix = Path('/usr/share/sailfish-shell-transaction-fixture')
packages = ['sailfish-shell-fixture-' + name for name in ('alias', 'gnu', 'consumer')]
record = {'steps': [], 'cleanup': False}


def command(args, check=True):
    result = subprocess.run(args, text=True, capture_output=True)
    entry = {'command': args, 'exit': result.returncode,
             'stdout': result.stdout, 'stderr': result.stderr}
    record['steps'].append(entry)
    print(json.dumps(entry), flush=True)
    if check and result.returncode:
        raise RuntimeError(f'Failed: {args}')
    return result


def snapshot():
    stock = ['gnupg2', 'gpgme', 'libgcrypt', 'libgpg-error', 'libksba',
             'pth', 'glibc', 'zlib', 'busybox', 'gnu-bash', 'ncurses-libs']
    versions = sorted(subprocess.check_output(
        ['rpm', '-qa', '--qf', '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n'], text=True).splitlines())
    files = {}
    verification = {}
    for package in stock:
        result = subprocess.run(['rpm', '-V', package], text=True, capture_output=True)
        verification[package] = (result.returncode, result.stdout, result.stderr)
        for name in subprocess.check_output(['rpm', '-ql', package], text=True).splitlines():
            path = Path(name)
            if path.is_symlink():
                files[name] = ['link', str(path.readlink())]
            elif path.is_file():
                files[name] = ['sha256', hashlib.sha256(path.read_bytes()).hexdigest()]
    return {'versions': versions, 'files': files, 'verification': verification}


def verify_fixture():
    # SDK's documented file UID/GID mapping is excluded only in fixture verify.
    command(['rpm', '-V', '--nouser', '--nogroup'] +
            [p for p in packages if subprocess.run(['rpm', '-q', p], capture_output=True).returncode == 0])
    assert (prefix / 'consumer').read_text() == 'synthetic consumer\n'


assert not prefix.exists()
assert hashlib.sha256(runner.read_bytes()).hexdigest() == 'dbad44d5ff81a5c4b6aca8d2ea71da757f0a2614ec74711bce5c9131e965d6bc'
assert all(subprocess.run(['rpm', '-q', p], capture_output=True).returncode != 0 for p in packages)
before = snapshot()
record['before'] = before
installed = False
try:
    alias = str(inputs / 'sailfish-shell-fixture-alias-1-1.noarch.rpm')
    consumer = str(inputs / 'sailfish-shell-fixture-consumer-1-1.noarch.rpm')
    command(['rpm', '-ivh', '--test', alias, consumer])
    installed = True  # Cleanup also handles a partial failed installation.
    command(['rpm', '-ivh', alias, consumer])
    verify_fixture()
    failed = command(['rpm', '-e', '--test', packages[0]], check=False)
    assert failed.returncode != 0 and 'sailfish-shell-fixture-provider' in failed.stderr
    for direction, expected in [('to-gnu', 'synthetic gnu\n'), ('to-alias', 'synthetic alias\n')]:
        for mode in ('test', 'apply'):
            bytes_before = (prefix / 'provider').read_bytes()
            command([sys.executable, str(runner), '--profile', 'fixture', '--direction', direction,
                     '--mode', mode, '--rpm-dir', str(inputs)])
            if mode == 'test':
                assert (prefix / 'provider').read_bytes() == bytes_before
                verify_fixture()
        assert (prefix / 'provider').read_text() == expected
        verify_fixture()
    record['acceptance'] = True
finally:
    if installed:
        present = [p for p in packages if subprocess.run(['rpm', '-q', p], capture_output=True).returncode == 0]
        if present:
            command(['rpm', '-e', '--test'] + present)
            command(['rpm', '-e'] + present)
        if prefix.exists():
            prefix.rmdir()  # Fails rather than deleting unexpected files.
    after = snapshot()
    record['after'] = after
    record['cleanup'] = after == before and not prefix.exists()
    output = Path('/home/ubuntu/password-store/sdk-shell-review/fixture-acceptance-local.json')
    output.write_text(json.dumps(record, indent=2) + '\n')
    assert record['cleanup'], 'Stock state not fully restored'
    print(f'PASS: fixture cleanup; {len(before["files"])} stock files and all package versions identical', flush=True)

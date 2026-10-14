#!/usr/bin/env python3
"""Preserve exact partial RPM-only stage and trace the original approved preflight."""
import hashlib
import os
from pathlib import Path
import stat
import subprocess

assert os.getuid() == 0 and os.uname().machine == 'aarch64'
version = next(line.split('=', 1)[1].strip('"') for line in Path('/etc/os-release').read_text().splitlines() if line.startswith('VERSION_ID='))
assert version == '5.1.0.11'
os.umask(0o077)
stage = Path('/var/tmp/sailfish-policy-dev-root-20261012')
backup = Path(str(stage) + '.preflight-failed')
bootstrap = Path('/var/tmp/sailfish-policy-bootstrap.GzwdYF')
script = bootstrap / 'validation.sh'
log = bootstrap / 'preflight-trace.log'
expected = {
    'sailfish-gnupg-private-2.5.24-0.3.aarch64.rpm': 'eb4cde3411df247262a6e7811b3fa1e05d76d8a1b4e064f95c68507c0d4e77c8',
    'sailfish-pass-1.7.4-0.3.noarch.rpm': 'abb673fdde0a54ef1b3e094f2e5fd8272c83c9704e8f05110337dd2857312f63',
    'sailfish-pass-tree-2.3.2-0.1.aarch64.rpm': '33578eae9014099575c0f5fa010ee5243b89c8f8e02b19e19105c5b33d24a32b',
}
for directory in [stage, bootstrap]:
    assert not directory.is_symlink() and directory.is_dir()
    assert directory.stat().st_uid == 0 and stat.S_IMODE(directory.stat().st_mode) == 0o700
assert {path.name for path in stage.iterdir()} == set(expected), 'Not an exact partial RPM-only stage'
for name, digest in expected.items():
    path = stage / name
    assert not path.is_symlink() and stat.S_ISREG(path.stat().st_mode)
    assert path.stat().st_uid == 0 and stat.S_IMODE(path.stat().st_mode) == 0o600
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
assert not script.is_symlink() and stat.S_ISREG(script.stat().st_mode)
assert script.stat().st_uid == 0 and stat.S_IMODE(script.stat().st_mode) == 0o600
assert hashlib.sha256(script.read_bytes()).hexdigest() == 'e5b8e383f0874fa8942fbd22d248e32c55f6231044696e0b2ae3f8a54dbb71ef'
assert not backup.exists() and not backup.is_symlink()
assert not log.exists() and not log.is_symlink()
for name in ['sailfish-pass', 'sailfish-pass-tree', 'sailfish-gnupg-private']:
    result = subprocess.run(['/usr/bin/rpm', '-q', name], capture_output=True, timeout=30)
    assert result.returncode == 1, 'Refuse recovery over installed package'
with log.open('x') as stream:
    stage.rename(backup)
    print('Preserved partial stage:', backup, flush=True)
    print('Original preflight trace:', log, flush=True)
    process = subprocess.Popen(['/usr/bin/busybox', 'sh', '-x', str(script), 'preflight'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
    for line in process.stdout:
        stream.write(line)
        stream.flush()
        if line.startswith(('Stockcontrole:', 'PASS:', 'STOP:')):
            print(line, end='', flush=True)
    code = process.wait()
print('Logged preflight exitcode:', code, flush=True)
if code:
    print(''.join(log.read_text().splitlines(keepends=True)[-35:]), end='', flush=True)
raise SystemExit(code)

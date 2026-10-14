#!/usr/bin/env python3
"""Approved temporary three-private-package SDK experiment; synthetic only."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path('/home/ubuntu/password-store')
assert Path.cwd() == root
sfdk = '/home/ubuntu/SailfishOS/bin/sfdk'
evidence = root / 'evidence'
record = {'target': 'SailfishOS-5.1.0.11-aarch64', 'steps': [], 'cleanup': False}
names = ['sailfish-pass', 'sailfish-pass-tree', 'sailfish-gnupg-private']
inspection = json.loads((evidence / 'rpm-inspection-20261011.json').read_text())
inputs = {
    root / 'sailfish-gnupg-private-2.5.24-0.1.aarch64.rpm':
    '485dac976a4631b2bc1d79ffe32cf1976c45eb52dcd760ddf60037025770fcb5',
    root / 'build/rpmbuild/RPMS/noarch/sailfish-pass-1.7.4-0.2.noarch.rpm': inspection['binary_sha256'],
    root / 'build/rpmbuild/RPMS/aarch64/sailfish-pass-tree-2.3.2-0.1.aarch64.rpm': inspection['tree']['binary_sha256'],
}
for path, digest in inputs.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
record['inputs'] = {str(path): digest for path, digest in inputs.items()}

def shell(args, maintain=False, check=True):
    command = [sfdk, '-c', 'target=' + record['target'], 'build-shell']
    if maintain:
        command.append('--maintain')
    result = subprocess.run(command + args, cwd='/home/ubuntu/gnupg-runtime',
                            text=True, capture_output=True, timeout=300)
    record['steps'].append({'command': args, 'maintain': maintain,
                            'exit': result.returncode, 'stdout': result.stdout,
                            'stderr': result.stderr})
    print(result.stdout, end='', flush=True)
    if check and result.returncode:
        raise RuntimeError(f'SDK command failed: {args}; {result.stderr}')
    return result

snapshot_code = '''
import hashlib,json,pathlib,subprocess,sys
packages=['gnupg2','gpgme','libgcrypt','libgpg-error','libksba','pth','glibc','zlib']
def query(args): return subprocess.check_output(['rpm']+args,text=True)
r={'versions':query(['-qa','--qf','%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\\n']), 'files':{}, 'verification':{}}
r['versions']='\\n'.join(sorted(line for line in r['versions'].splitlines() if not line.startswith(('sailfish-pass ', 'sailfish-pass-tree ', 'sailfish-gnupg-private '))))
for package in packages:
 v=subprocess.run(['rpm','-V',package],text=True,capture_output=True)
 r['verification'][package]={'exit':v.returncode,'stdout':v.stdout,'stderr':v.stderr}
 for name in query(['-ql',package]).splitlines():
  p=pathlib.Path(name)
  if p.is_symlink():r['files'][name]={'symlink':str(p.readlink())}
  elif p.is_file():r['files'][name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
pathlib.Path('/home/ubuntu/password-store/evidence/stock-pass-'+sys.argv[1]+'.json').write_text(json.dumps(r,indent=2)+'\\n')
print('Stock snapshot',sys.argv[1],len(r['files']),'files')
'''
installed = False
e2e_started = False
try:
    for name in names:
        assert shell(['rpm', '-q', name], maintain=True, check=False).returncode == 1
    shell(['python3', '-c', snapshot_code, 'before'], maintain=True)
    shell(['rpm', '-ivh', '--test', *map(str, inputs)], maintain=True)
    installed = True  # Cleanup also covers a partially failed transaction.
    shell(['rpm', '-ivh', *map(str, inputs)], maintain=True)
    verification = shell(['rpm', '-V', *names], maintain=True, check=False)
    if verification.returncode:
        assert verification.returncode == len(names) and not verification.stderr, 'Unexpected verification status'
        assert verification.stdout and all(line.startswith('.....UG.. ') for line in verification.stdout.splitlines())
        record['sdk_ownership_mapping_limitation'] = True
    shell(['rpm', '-V', '--nouser', '--nogroup', *names], maintain=True)
    shell(['python3', '-c', snapshot_code, 'installed'], maintain=True)
    before = json.loads((evidence / 'stock-pass-before.json').read_text())
    during = json.loads((evidence / 'stock-pass-installed.json').read_text())
    generated_cache = '/var/cache/ldconfig/aux-cache'
    record['generated_ldconfig_cache'] = {'before': before['files'].get(generated_cache),
                                         'installed': during['files'].get(generated_cache)}
    for snapshot in (before, during):
        snapshot['files'].pop(generated_cache, None)
    assert before == during, 'Distributed stock files, versions or verification changed'
    fixture_record = evidence / 'e2e-sdk-20261011.json'
    if fixture_record.exists():
        fixture_record.rename(evidence / 'e2e-sdk-previous-20261011.json')
    e2e_started = True
    shell(['python3', str(root / 'tools/e2e-sdk.py')])
    assert json.loads((evidence / 'e2e-sdk-20261011.json').read_text())['cleanup_passed']
    record['e2e_passed'] = True
except Exception as error:
    record['failure'] = str(error)
finally:
    if installed:
        # Agent cleanup must be established before removing its executable.
        fixture_record = evidence / 'e2e-sdk-20261011.json'
        if e2e_started and (not fixture_record.exists() or not json.loads(fixture_record.read_text())['cleanup_passed']):
            record['cleanup_failure'] = 'Fixture cleanup incomplete; retain runtime for diagnosis'
        else:
            try:
                present = [name for name in names if shell(['rpm', '-q', name], maintain=True, check=False).returncode == 0]
                if present:
                    shell(['rpm', '-e', *present], maintain=True)
                for name in names:
                    assert shell(['rpm', '-q', name], maintain=True, check=False).returncode == 1
                shell(['python3', '-c', snapshot_code, 'removed'], maintain=True)
                assert json.loads((evidence / 'stock-pass-before.json').read_text()) == json.loads((evidence / 'stock-pass-removed.json').read_text())
                record['cleanup'] = True
            except Exception as error:
                record['cleanup_failure'] = str(error)
    (evidence / 'sdk-acceptance-20261011.json').write_text(json.dumps(record, indent=2) + '\n')
if not record.get('e2e_passed') or not record['cleanup']:
    raise SystemExit('SDK acceptance incomplete; see evidence/sdk-acceptance-20261011.json')
print('PASS: synthetic pass acceptance, private package cleanup and full stock comparison')

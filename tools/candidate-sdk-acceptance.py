#!/usr/bin/env python3
"""Scoped candidate SDK transaction; synthetic regression only."""
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
inspection = json.loads((evidence / 'candidate-build-20261011.json').read_text())['inspection']
gpg_inspection = json.loads(Path('/home/ubuntu/gnupg-runtime/evidence/candidate-build-20261011.json').read_text())['inspection']
for name in ['candidate-sdk-acceptance-20261011.json', 'stock-candidate-before.json', 'stock-candidate-installed.json', 'stock-candidate-removed.json']:
    assert not (evidence / name).exists(), 'Fresh evidence only: ' + name
regression = root / 'tools/candidate-policy-regression.py'
assert hashlib.sha256(regression.read_bytes()).hexdigest() == '3d17bb3c1de8b44ae4b3338cac80c619f5b92eb4439a6d6c1f7f0c13023f82bc'
record['regression_sha256'] = '3d17bb3c1de8b44ae4b3338cac80c619f5b92eb4439a6d6c1f7f0c13023f82bc'
inputs = {
    Path('/home/ubuntu/gnupg-runtime/RPMS/sailfish-gnupg-private-2.5.24-0.3.aarch64.rpm'):
    gpg_inspection['artifact_sha256'],
    root / 'build/rpmbuild/RPMS/noarch/sailfish-pass-1.7.4-0.3.noarch.rpm': inspection['binary_sha256'],
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
pathlib.Path('/home/ubuntu/password-store/evidence/stock-candidate-'+sys.argv[1]+'.json').write_text(json.dumps(r,indent=2)+'\\n')
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
    before = json.loads((evidence / 'stock-candidate-before.json').read_text())
    during = json.loads((evidence / 'stock-candidate-installed.json').read_text())
    generated_cache = '/var/cache/ldconfig/aux-cache'
    record['generated_ldconfig_cache'] = {'before': before['files'].get(generated_cache),
                                         'installed': during['files'].get(generated_cache)}
    for snapshot in (before, during):
        snapshot['files'].pop(generated_cache, None)
    assert before == during, 'Distributed stock files, versions or verification changed'
    e2e_started = True
    result = shell(['python3', str(root / 'tools/candidate-policy-regression.py')], check=False)
    fixture_lines = [line.removeprefix('Evidence fixture: ') for line in result.stdout.splitlines() if line.startswith('Evidence fixture: ')]
    assert len(fixture_lines) == 1, 'Fixture outcome unavailable; retain packages'
    fixture = Path(fixture_lines[0])
    assert fixture.parent == root / 'test-results' and fixture.name.startswith('synthetic-policy-')
    fixture_record = fixture / 'result.json'
    record['fixture_record'] = str(fixture_record)
    fixture_result = json.loads(fixture_record.read_text())
    assert fixture_result['fixture'] == str(fixture)
    assert fixture_result.get('unknown_launch') is False, 'Unresolved fixture launch'
    record['fixture_result'] = fixture_result
    assert result.returncode == 0 and fixture_result['passed'] is True and fixture_result['cleanup'] is True
    record['e2e_passed'] = True
except Exception as error:
    record['failure'] = str(error)
finally:
    if installed:
        # Agent cleanup must be established before removing its executable.
        if e2e_started and not (record.get('fixture_result', {}).get('cleanup') is True):
            record['cleanup_failure'] = 'Fixture cleanup incomplete; retain runtime for diagnosis'
        else:
            try:
                present = [name for name in names if shell(['rpm', '-q', name], maintain=True, check=False).returncode == 0]
                if present:
                    shell(['rpm', '-e', *present], maintain=True)
                for name in names:
                    assert shell(['rpm', '-q', name], maintain=True, check=False).returncode == 1
                shell(['python3', '-c', snapshot_code, 'removed'], maintain=True)
                before = json.loads((evidence / 'stock-candidate-before.json').read_text())
                removed = json.loads((evidence / 'stock-candidate-removed.json').read_text())
                assert before == removed, 'Full stock baseline changed'
                record['cleanup'] = True
            except Exception as error:
                record['cleanup_failure'] = str(error)
    (evidence / 'candidate-sdk-acceptance-20261011.json').write_text(json.dumps(record, indent=2) + '\n')
if not record.get('e2e_passed') or not record['cleanup']:
    raise SystemExit('SDK acceptance incomplete; see evidence/candidate-sdk-acceptance-20261011.json')
print('PASS: focused synthetic regression, private package cleanup and distributed stock comparison')

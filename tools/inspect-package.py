#!/usr/bin/env python3
"""Read RPM metadata/payloads without installing or running crypto."""
import argparse
import hashlib
from datetime import datetime, timezone
import re
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import tarfile

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path)
args = parser.parse_args()
spec = (root / 'rpm/sailfish-pass.spec').read_text()
version = re.search(r'^Version:\s+(\S+)$', spec, re.M)[1]
release = re.search(r'^Release:\s+(\S+)$', spec, re.M)[1]
identity = f'{version}-{release}'
runtime_requirement = re.search(r'^Requires:\s+(sailfish-gnupg-runtime = \S+)$', spec, re.M)[1]
binary = root / f'build/rpmbuild/RPMS/noarch/sailfish-pass-{identity}.noarch.rpm'
source = root / f'build/rpmbuild/SRPMS/sailfish-pass-{identity}.src.rpm'
output = args.output or root / f'evidence/rpm-inspection-{identity}.json'
if output.exists():
    raise SystemExit(f'Refusing to overwrite inspection evidence: {output}')

def query(path, *args):
    return subprocess.check_output(['rpm', '-qp', *args, str(path)], text=True)

def payload(path):
    raw = subprocess.check_output(['rpm2cpio', str(path)])
    offset, entries = 0, {}
    while True:
        assert offset + 110 <= len(raw), 'Truncated newc header'
        assert raw[offset:offset + 6] in (b'070701', b'070702')
        fields = [int(raw[offset + 6 + i * 8:offset + 14 + i * 8], 16) for i in range(13)]
        mode, size, namesize = fields[1], fields[6], fields[11]
        offset += 110
        assert namesize > 1 and offset + namesize <= len(raw) and raw[offset + namesize - 1] == 0 and b'\0' not in raw[offset:offset + namesize - 1], 'Invalid newc name'
        name = raw[offset:offset + namesize - 1].decode()
        offset = (offset + namesize + 3) & ~3
        assert offset + size <= len(raw), 'Truncated newc data'
        data = raw[offset:offset + size]
        offset = (offset + size + 3) & ~3
        if name == 'TRAILER!!!':
            return entries
        name = name.removeprefix('./')
        assert name not in entries, 'Duplicate normalized payload entry'
        entries[name] = (mode, data)

files = payload(binary)
assert files['usr/share/licenses/sailfish-pass/GPL-3.0.txt'][1] == (root / 'LICENSE').read_bytes()
assert files['usr/share/licenses/sailfish-pass/LICENSING.md'][1] == (root / 'LICENSING.md').read_bytes()
script = files['usr/libexec/sailfish-pass/bin/pass'][1]
wrapper_mode, wrapper = files['usr/bin/pass']
assert stat.S_ISREG(wrapper_mode) and wrapper_mode & 0o7777 == 0o755
assert b'GPG="/usr/bin/sailfish-gpg"' in script
assert b'which gpg2' not in script
assert wrapper == (root / 'runtime/sailfish-pass').read_bytes()
assert b'SYSTEM_EXTENSION_DIR="/usr/libexec/sailfish-pass/password-store/extensions"' in script
assert all(name == 'usr/bin/pass' or name.startswith(('usr/libexec/sailfish-pass',
                            'usr/share/licenses/sailfish-pass', 'usr/share/doc/sailfish-pass')) for name in files)
assert all(not data.startswith(b'\x7fELF') for _, data in files.values())
requires = query(binary, '--requires')
assert runtime_requirement in requires.splitlines()
for requirement in ['/usr/bin/busybox', '/usr/bin/env', '/usr/bin/id', '(/bin/stat or /usr/bin/stat)']:
    assert requirement in requires.splitlines(), requirement
assert 'gnupg2' not in requires
assert 'gnu-bash >= 5.0.18' in requires
assert b'\\x1B' not in script
assert b"$'\\033'" in script
assert script.count(b' 3>&- | tail -n +2') == 2
provides = query(binary, '--provides')
assert provides.strip() == f'sailfish-pass = {identity}'
assert not query(binary, '--scripts').strip()
source_files = payload(source)
for name, original in [('LICENSE', root / 'LICENSE'),
                       ('LICENSING.md', root / 'LICENSING.md'),
                       ('private-gpg.patch', root / 'rpm/private-gpg.patch'),
                       ('pass-tree-fd3.patch', root / 'rpm/pass-tree-fd3.patch'),
                       ('sailfish-pass', root / 'runtime/sailfish-pass'),
                       ('sources.lock.json', root / 'sources.lock.json'),
                       ('pass-tag-verification.json', root / 'evidence/pass-tag-verification.json'),
                       ('pass-release-key.asc', root / 'sources/pass-release-key.asc'),
                       ('password-store-1.7.4-verified.tar', root / 'sources/password-store-1.7.4-verified.tar'),
                       ('sailfish-pass.spec', root / 'rpm/sailfish-pass.spec')]:
    assert source_files[name][1] == original.read_bytes(), name
record = {'date': datetime.now(timezone.utc).date().isoformat(), 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'requires': requires, 'provides': provides,
          'payload': query(binary, '--list'), 'source_files': sorted(source_files),
          'checks': ['private engine binding', 'no stock gpg2 selection', 'wrapper identity',
                     'private extension path', 'private-only payload', 'no ELF',
                     'private RPM dependency', 'no scriptlets', 'complete matching SRPM inputs']}
tree_rpm = root / 'build/rpmbuild/RPMS/aarch64/sailfish-pass-tree-2.3.2-0.1.aarch64.rpm'
tree_srpm = root / 'build/rpmbuild/SRPMS/sailfish-pass-tree-2.3.2-0.1.src.rpm'
tree_files = payload(tree_rpm)
assert all(name.startswith(('usr/libexec/sailfish-pass-tools', 'usr/share/licenses/sailfish-pass-tree',
                            'usr/share/doc/sailfish-pass-tree')) for name in tree_files)
tree_binary = tree_files['usr/libexec/sailfish-pass-tools/bin/tree'][1]
assert tree_binary.startswith(b'\x7fELF')
assert not query(tree_rpm, '--scripts').strip()
tree_sources = payload(tree_srpm)
for name, original in [('tree-2.3.2.tar.gz', root / 'sources/tree-2.3.2.tar.gz'),
                       ('tree-source.json', root / 'evidence/tree-source.json'),
                       ('sailfish-pass-tree.spec', root / 'rpm/sailfish-pass-tree.spec')]:
    assert tree_sources[name][1] == original.read_bytes(), name
with tempfile.TemporaryDirectory(prefix='synthetic-tree-inspect-') as temporary:
    executable = Path(temporary) / 'tree'
    executable.write_bytes(tree_binary)
    header = subprocess.check_output(['readelf', '-h', str(executable)], text=True)
    assert 'AArch64' in header
    dynamic = subprocess.check_output(['readelf', '-d', str(executable)], text=True)
    assert 'RPATH' not in dynamic and 'RUNPATH' not in dynamic
tree_build = root / 'build/rpmbuild/BUILD/tree-1a41b51bea1cec4109eb9f726370449b384b4576/tree'
tree_version = subprocess.check_output([str(tree_build), '--version'], text=True)
assert 'v2.3.2' in tree_version
record['tree'] = {'binary_sha256': hashlib.sha256(tree_rpm.read_bytes()).hexdigest(),
                  'source_sha256': hashlib.sha256(tree_srpm.read_bytes()).hexdigest(),
                  'requires': query(tree_rpm, '--requires'), 'provides': query(tree_rpm, '--provides'),
                  'payload': query(tree_rpm, '--list'), 'version_from_built_binary': tree_version,
                  'checks': ['AArch64', 'no build RPATH/RUNPATH', 'private paths only',
                             'no scriptlets', 'SRPM inputs match', 'built binary version executes']}
# Inspect OATH/OTP payloads and matching source packages without running crypto.
lock = json.loads((root / 'sources.lock.json').read_text())
oath_version = lock['oath_toolkit']['version']
oath_identity = oath_version + '-0.3'
oath_source = root / f'build/rpmbuild/SRPMS/oath-toolkit-{oath_identity}.src.rpm'
oath_source_files = payload(oath_source)
for name, original in [
    (lock['oath_toolkit']['archive'], root / 'sources' / lock['oath_toolkit']['archive']),
    ('oath-source.json', root / 'evidence/oath-source.json'),
    ('oath-COPYING.LESSER', root / 'sources/oath-COPYING.LESSER'),
    ('oath-toolkit.spec', root / 'rpm/oath-toolkit.spec')]:
    assert oath_source_files[name][1] == original.read_bytes(), name
with tarfile.open(root / 'sources' / lock['oath_toolkit']['archive']) as archive:
    oath_copying = archive.extractfile(f'oath-toolkit-{oath_version}/COPYING').read()
oath_results = {}
for package in ('sailfish-liboath', 'sailfish-oathtool'):
    rpm = root / f'build/rpmbuild/RPMS/aarch64/{package}-{oath_identity}.aarch64.rpm'
    entries = payload(rpm)
    prefix = 'usr/libexec/sailfish-oath/'
    allowed = (prefix, f'usr/share/licenses/{package}', f'usr/share/doc/{package}')
    assert all(name == 'usr/libexec/sailfish-oath' or name.startswith(allowed) for name in entries)
    assert not query(rpm, '--scripts').strip()
    assert not re.search(r'^liboath\.so', query(rpm, '--provides'), re.M)
    assert not re.search(r'^liboath\.so', query(rpm, '--requires'), re.M)
    assert entries[f'usr/share/licenses/{package}/COPYING'][1] == oath_copying
    if package == 'sailfish-liboath':
        assert entries['usr/share/licenses/sailfish-liboath/COPYING.LESSER'][1] == (root / 'sources/oath-COPYING.LESSER').read_bytes()
        assert entries['usr/share/doc/sailfish-liboath/source-verification.json'][1] == (root / 'evidence/oath-source.json').read_bytes()
        assert 'usr/libexec/sailfish-oath/lib/liboath.so' not in entries
    else:
        assert f'sailfish-liboath = {oath_identity}' in query(rpm, '--requires').splitlines()
    assert query(rpm, '--qf', '%{SOURCERPM}') == oath_source.name
    elf = []
    with tempfile.TemporaryDirectory(prefix='synthetic-oath-inspect-') as temporary:
        for name, (mode, data) in entries.items():
            if not data.startswith(b'\x7fELF'): continue
            executable = Path(temporary) / 'object'
            executable.write_bytes(data)
            header = subprocess.check_output(['readelf', '-h', str(executable)], text=True)
            dynamic = subprocess.check_output(['readelf', '-d', str(executable)], text=True)
            assert 'AArch64' in header, name
            paths = re.findall(r'\((?:RUNPATH|RPATH)\).*\[(.*?)\]', dynamic)
            expected = ['/usr/libexec/sailfish-oath/lib']
            assert paths == expected if name.endswith('/bin/oathtool') else paths in ([], expected), (name, paths)
            elf.append({'path': name, 'runpath': paths})
    assert elf
    oath_results[package] = {
        'sha256': hashlib.sha256(rpm.read_bytes()).hexdigest(),
        'requires': query(rpm, '--requires'), 'provides': query(rpm, '--provides'), 'elf': elf}
record['oath'] = {
    'source_sha256': hashlib.sha256(oath_source.read_bytes()).hexdigest(),
    'source_inputs': sorted(oath_source_files), 'packages': oath_results,
    'checks': ['matching SRPM inputs', 'private payload and library resolution',
               'AArch64 ELF', 'no scriptlets', 'exact GPL/LGPL notices']}
otp_version = lock['pass_otp']['version']
otp_spec = (root / 'rpm/sailfish-pass-otp.spec').read_text()
otp_release = re.search(r'^Release:\s+(\S+)$', otp_spec, re.M)[1]
otp_identity = otp_version + '-' + otp_release
otp_rpm = root / f'build/rpmbuild/RPMS/noarch/sailfish-pass-otp-{otp_identity}.noarch.rpm'
otp_srpm = root / f'build/rpmbuild/SRPMS/sailfish-pass-otp-{otp_identity}.src.rpm'
otp_files = payload(otp_rpm)
otp_sources = payload(otp_srpm)
otp_archive = root / f'sources/pass-otp-{otp_version}.tar.gz'
for name, original in [
    (otp_archive.name, otp_archive),
    ('pass-otp-stdin.patch', root / 'patches/pass-otp-stdin.patch'),
    ('pass-otp-private-backend.patch', root / 'patches/pass-otp-private-backend.patch'),
    ('pass-otp-final-line.patch', root / 'patches/pass-otp-final-line.patch'),
    ('sailfish-pass-otp.spec', root / 'rpm/sailfish-pass-otp.spec')]:
    assert otp_sources[name][1] == original.read_bytes(), name
with tarfile.open(otp_archive) as archive:
    original_script = archive.extractfile(f'pass-otp-{otp_version}/otp.bash').read()
    original_license = archive.extractfile(f'pass-otp-{otp_version}/LICENSE').read()
    original_append_test = archive.extractfile(f'pass-otp-{otp_version}/test/append.t').read()
with tempfile.TemporaryDirectory(prefix='synthetic-otp-inspect-') as temporary:
    prepared = Path(temporary) / 'otp.bash'
    prepared.write_bytes(original_script)
    (prepared.parent / 'test').mkdir()
    (prepared.parent / 'test/append.t').write_bytes(original_append_test)
    for patch in ('pass-otp-stdin.patch', 'pass-otp-private-backend.patch', 'pass-otp-final-line.patch'):
        subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(root / 'patches' / patch)],
                       cwd=temporary, check=True, capture_output=True)
    assert otp_files['usr/libexec/sailfish-pass/password-store/extensions/otp.bash'][1] == prepared.read_bytes()
assert otp_files['usr/share/licenses/sailfish-pass-otp/LICENSE'][1] == original_license
assert all(name.startswith(('usr/libexec/sailfish-pass/password-store/extensions/otp.bash',
                           'usr/share/man/man1/sailfish-pass-otp.1',
                           'usr/share/licenses/sailfish-pass-otp')) for name in otp_files)
assert not query(otp_rpm, '--scripts').strip()
assert query(otp_rpm, '--qf', '%{SOURCERPM}') == otp_srpm.name
otp_requires = query(otp_rpm, '--requires').splitlines()
assert f'sailfish-pass = {identity}' in otp_requires
assert f'sailfish-oathtool = {oath_identity}' in otp_requires
assert '/usr/libexec/sailfish-oath/bin/oathtool' in otp_requires
record['otp'] = {
    'binary_sha256': hashlib.sha256(otp_rpm.read_bytes()).hexdigest(),
    'source_sha256': hashlib.sha256(otp_srpm.read_bytes()).hexdigest(),
    'source_inputs': sorted(otp_sources), 'requires': otp_requires,
    'checks': ['matching SRPM inputs', 'exact upstream-plus-three-patches payload',
               'private backend dependency', 'exact upstream license', 'no scriptlets']}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))

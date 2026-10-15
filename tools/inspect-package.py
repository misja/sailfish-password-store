#!/usr/bin/env python3
"""Read RPM metadata/payloads without installing or running crypto."""
import argparse
import hashlib
import re
import json
from pathlib import Path
import stat
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path)
args = parser.parse_args()
spec = (root / 'rpm/sailfish-pass.spec').read_text()
version = re.search(r'^Version:\s+(\S+)$', spec, re.M)[1]
release = re.search(r'^Release:\s+(\S+)$', spec, re.M)[1]
identity = f'{version}-{release}'
runtime_requirement = re.search(r'^Requires:\s+(sailfish-gnupg-private = \S+)$', spec, re.M)[1]
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
provides = query(binary, '--provides')
assert provides.strip() == f'sailfish-pass = {identity}'
assert not query(binary, '--scripts').strip()
source_files = payload(source)
for name, original in [('LICENSE', root / 'LICENSE'),
                       ('LICENSING.md', root / 'LICENSING.md'),
                       ('private-gpg.patch', root / 'rpm/private-gpg.patch'),
                       ('sailfish-pass', root / 'runtime/sailfish-pass'),
                       ('sources.lock.json', root / 'sources.lock.json'),
                       ('pass-tag-verification.json', root / 'evidence/pass-tag-verification.json'),
                       ('pass-release-key.asc', root / 'sources/pass-release-key.asc'),
                       ('password-store-1.7.4-verified.tar', root / 'sources/password-store-1.7.4-verified.tar'),
                       ('sailfish-pass.spec', root / 'rpm/sailfish-pass.spec')]:
    assert source_files[name][1] == original.read_bytes(), name
record = {'date': '2026-10-11', 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
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
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))

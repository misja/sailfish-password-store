#!/usr/bin/env python3
"""Stage only locked public sources and packaging inputs; no software install."""
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent.parent
lock = json.loads((root / 'sources.lock.json').read_text())
archive = root / 'sources' / lock['pass']['archive']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == lock['pass']['sha256']
tree = lock['tree']
assert hashlib.sha256((root / 'sources' / tree['archive']).read_bytes()).hexdigest() == tree['sha256']
verification = json.loads((root / 'evidence/pass-tag-verification-20261011.json').read_text())
assert verification['verify_tag_exit'] == 0
assert verification['commit'] == lock['pass']['commit']
assert verification['allowed_primary_fingerprint'] == lock['pass']['primary_fingerprint']
for source, destination in [
    ('LICENSE', 'LICENSE'),
    ('LICENSING.md', 'LICENSING.md'),
    ('rpm/private-gpg.patch', 'private-gpg.patch'),
    ('runtime/sailfish-pass', 'sailfish-pass'),
    ('sources.lock.json', 'sources.lock.json'),
    ('evidence/pass-tag-verification-20261011.json', 'pass-tag-verification-20261011.json'),
    ('evidence/tree-source-20261011.json', 'tree-source-20261011.json'),
]:
    shutil.copy2(root / source, root / 'sources' / destination)
assert (root / 'sources/pass-release-key.asc').is_file()
for directory in ['BUILD', 'BUILDROOT', 'RPMS', 'SRPMS', 'SPECS']:
    (root / 'build/rpmbuild' / directory).mkdir(parents=True, exist_ok=True)
print('Prepared locked source archive and complete RPM source inputs')

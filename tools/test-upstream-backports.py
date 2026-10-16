#!/usr/bin/env python3
"""Focused synthetic regressions; supplied source files are software, never user homes."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
for name in ('pass-source', 'otp-source', 'pass-before', 'otp-before'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--tree', type=Path, default=Path('/usr/bin/tree'))
args = parser.parse_args()


def functions(path, names):
    text = path.read_text()
    return '\n'.join(re.search(r'^' + name + r'\(\) \{\n.*?^\}', text,
                               re.M | re.S)[0] for name in names)


with tempfile.TemporaryDirectory(prefix='synthetic-upstream-backports-') as temporary:
    root = Path(temporary)
    store = root / 'store'
    store.mkdir()
    (store / 'sample.gpg').write_text('synthetic placeholder, never decrypted')
    bin_dir = root / 'bin'
    bin_dir.mkdir()
    sed = bin_dir / 'sed'
    sed.write_text('#!/bin/sh\nexec /usr/bin/busybox sed "$@"\n')
    sed.chmod(0o700)
    env = dict(PATH=str(bin_dir) + ':/usr/bin:/bin', HOME=str(root), LC_ALL='C', TERM='xterm',
               LS_COLORS='*.gpg=01;32', TREE_COLORS='*.gpg=01;32')
    for source, fixed in ((args.pass_before, False), (args.pass_source, True)):
        f = root / 'pass-functions'
        f.write_text(functions(source, ('cmd_show', 'cmd_find')))
        for command in ('cmd_show', 'cmd_find'):
            fd3 = root / 'fd3'
            shell = '''source "$1"
PREFIX="$2"; GETOPT=/usr/bin/getopt; PROGRAM=pass; COMMAND=show
check_sneaky_paths() { :; }
die() { echo "$*" >&2; exit 1; }
# Observe inherited FD3 independently of whether this tree version still writes JSON.
tree() {
    if { true >&3; } 2>/dev/null; then printf 'synthetic inherited descriptor\n' >&3; fi
    "$TREE_BINARY" "$@"
}
exec 3> "$3"
if [ "$4" = cmd_show ]; then cmd_show ''; else cmd_find sample; fi
'''
            r = subprocess.run(['/bin/bash', '-c', shell, 'test', str(f), str(store),
                                str(fd3), command], env={**env, 'TREE_BINARY': str(args.tree)},
                               capture_output=True)
            assert r.returncode == 0, (command, r.stderr)
            assert b'sample' in r.stdout and b'.gpg' not in r.stdout, r.stdout
            assert b'\x1b' in r.stdout, 'Colored listing did not exercise BusyBox ESC handling'
            assert bool(fd3.read_bytes()) is not fixed, ('FD3 regression', command, fixed)
    decrypt = root / 'decrypt'
    decrypt.write_text('#!/bin/bash\ncat "${@: -1}"\n')
    decrypt.chmod(0o700)
    for source, fixed in ((args.otp_before, False), (args.otp_source, True)):
        f = root / 'otp-functions'
        f.write_text(functions(source, ('cmd_otp_append',)))
        for original in ('synthetic password with spaces', 'first line\nlast line without newline'):
            entry = store / 'demo.gpg'
            entry.write_text(original)
            shell = '''source "$1"
PREFIX="$2"; GPG="$3"; GETOPT=/usr/bin/getopt; PROGRAM=pass; COMMAND=otp
GPG_OPTS=()
die() { echo "$*" >&2; exit 1; }
yesno() { exit 90; }
otp_read_uri() { otp_uri='otpauth://totp/Synthetic?secret=JBSWY3DPEHPK3PXP'; }
otp_insert() { printf '%s' "$3" > "$2"; }
cmd_otp_append demo
'''
            r = subprocess.run(['/bin/bash', '-c', shell, 'test', str(f), str(store),
                                str(decrypt)], env=env, capture_output=True)
            assert r.returncode == 0, r.stderr
            expected = original + '\notpauth://totp/Synthetic?secret=JBSWY3DPEHPK3PXP'
            assert (entry.read_text() == expected) is fixed, ('Last-line regression', fixed)
print('PASS show/find FD3 and BusyBox colored listing; exact no-newline OTP append; both old-source regressions reproduced')

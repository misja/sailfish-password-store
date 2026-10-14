#!/usr/bin/env python3
"""Read-only dependency check of the exact approved two-provider transaction.

RPM 4.16.1.3 declarations: upstream commit
3659b8a04f5b8bacf6535e0124e7fe23f15286bd, lib/rpmts.h and rpmlib.h.
No transaction execution function is bound or called. No flags disable checks.
"""
import ctypes as C
import hashlib
import os
from pathlib import Path
import subprocess

assert subprocess.check_output(['rpm', '-q', '--qf', '%{VERSION}', 'rpm'], text=True) == '4.16.1.3+git20'
path = Path('/tmp/sailfish-pass-review.rkyyZi/official/gnu-bash-5.0.18+git2-1.6.8.jolla.aarch64.rpm')
assert hashlib.sha256(path.read_bytes()).hexdigest() == 'da752ffd216222a29b143acfc4134922995dd67e59138a1649bb3a73fb729980'
def inventory():
    return sorted(subprocess.check_output(['rpm', '-qa', '--qf', '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n'], text=True).splitlines())
before = inventory()
rpm = C.CDLL('librpm.so.9')
io = C.CDLL('librpmio.so.9')
P = C.c_void_p
I = C.c_int
S = C.c_char_p
def bind(lib, name, result, args):
    f = getattr(lib, name)
    f.restype, f.argtypes = result, args
    return f
config = bind(rpm, 'rpmReadConfigFiles', I, [S, S])
create = bind(rpm, 'rpmtsCreate', P, [])
free = bind(rpm, 'rpmtsFree', P, [P])
mode = bind(rpm, 'rpmtsSetDBMode', I, [P, I])
open_db = bind(rpm, 'rpmtsOpenDB', I, [P, I])
iterator = bind(rpm, 'rpmtsInitIterator', P, [P, I, S, C.c_size_t])
next_header = bind(rpm, 'rpmdbNextIterator', P, [P])
free_iterator = bind(rpm, 'rpmdbFreeIterator', P, [P])
read = bind(rpm, 'rpmReadPackageFile', I, [P, P, S, C.POINTER(P)])
header_free = bind(rpm, 'headerFree', P, [P])
install = bind(rpm, 'rpmtsAddInstallElement', I, [P, P, S, I, P])
erase = bind(rpm, 'rpmtsAddEraseElement', I, [P, P, I])
check = bind(rpm, 'rpmtsCheck', I, [P])
problems = bind(rpm, 'rpmtsProblems', P, [P])
problem_count = bind(rpm, 'rpmpsNumProblems', I, [P])
problem_free = bind(rpm, 'rpmpsFree', P, [P])
order = bind(rpm, 'rpmtsOrder', I, [P])
fopen = bind(io, 'Fopen', P, [S, S])
fclose = bind(io, 'Fclose', I, [P])
assert config(None, None) == 0
ts = create()
assert ts
try:
    assert mode(ts, os.O_RDONLY) == 0
    assert open_db(ts, os.O_RDONLY) == 0
    header = P()
    fd = fopen(os.fsencode(path), b'r.ufdio')
    assert fd
    try:
        rc = read(ts, fd, os.fsencode(path), C.byref(header))
        assert rc in (0, 4) and header.value, f'RPM header verification failed: {rc}'
        print(f'Header read status: {rc} (4 = known NOKEY exception)', flush=True)
    finally:
        fclose(fd)
    try:
        assert install(ts, header, os.fsencode(path), 0, None) == 0
    finally:
        header_free(header)
    it = iterator(ts, 1000, b'busybox-symlinks-bash', 0)
    assert it
    try:
        installed = next_header(it)
        assert installed
        assert erase(ts, installed, 0) == 0
        assert not next_header(it), 'Multiple installed shell providers'
    finally:
        free_iterator(it)
    assert check(ts) == 0
    ps = problems(ts)
    count = problem_count(ps) if ps else 0
    if ps:
        problem_free(ps)
    print(f'Combined transaction dependency problems: {count}', flush=True)
    assert count == 0, 'Unresolved dependency/conflict problems'
    assert order(ts) == 0
    print('PASS: combined remove alias + install GNU dependency check/order; NOT executed')
finally:
    free(ts)
    assert inventory() == before, 'Package inventory changed unexpectedly'

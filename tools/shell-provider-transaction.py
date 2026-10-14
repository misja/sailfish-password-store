#!/usr/bin/env python3
"""Bounded official shell-provider transaction, never a general RPM installer.

Pinned ABI: upstream RPM 4.16.1.3 commit
3659b8a04f5b8bacf6535e0124e7fe23f15286bd, lib/rpm{ts,te,callback,types}.h.
Native apply requires the separately approved experiment. SDK apply requires its
approved temporary validation. TEST always runs first; failures are not atomic.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import subprocess


PACKAGES = {
    'dev-alias': ('busybox-symlinks-bash', '1.36.1+git10', '1.14.1.jolla', 'aarch64',
                  '83d3d93f2f0937c9c1e99464515a97f6ece34807bc178dae0befb9ce65447870'),
    'dev-gnu': ('gnu-bash', '5.0.18+git2', '1.6.7.jolla', 'aarch64',
                '298136960d2a4ed126a4040e2ba5122ecaa005a378394f81e0386e315d04b456'),
    'alias': ('busybox-symlinks-bash', '1.36.1+git11', '1.15.1.jolla', 'aarch64',
              '8e1ebb23c7c93a30314dbc1cf4542ebfac4f7292df3db12e182eed58b8c64abb'),
    'native-gnu': ('gnu-bash', '5.0.18+git2', '1.6.8.jolla', 'aarch64',
                   'da752ffd216222a29b143acfc4134922995dd67e59138a1649bb3a73fb729980'),
    'sdk-gnu': ('gnu-bash', '5.0.18+git2', '1.6.7.jolla', 'aarch64',
                '298136960d2a4ed126a4040e2ba5122ecaa005a378394f81e0386e315d04b456'),
    'fixture-alias': ('sailfish-shell-fixture-alias', '1', '1', 'noarch',
                      'e01d1d8776e0bcd5b8f540ff0eb3515c4c3d6d0166919c898a96459e02439f3d'),
    'fixture-gnu': ('sailfish-shell-fixture-gnu', '1', '1', 'noarch',
                    '316f9c778a163feda312604baab5397bcc9212fd61fa5f4f2c71555300616f50'),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def inventory():
    return sorted(subprocess.check_output(
        ['/usr/bin/rpm', '-qa', '--qf', '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n'],
        text=True).splitlines())


def row(identity):
    name, version, release, arch = identity[:4]
    return f'{name} {version}-{release} {arch}'


def rpm_path(directory, identity):
    name, version, release, arch = identity[:4]
    path = directory / f'{name}-{version}-{release}.{arch}.rpm'
    require(not path.is_symlink() and path.is_file(), f'Unsafe/missing input: {path}')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == identity[4],
            f'RPM hash mismatch: {path}')
    return path


def transaction(directory, incoming, outgoing, stage):
    """Construct one exact set; dependency checking uses DB read-only."""
    rpm = C.CDLL('librpm.so.9')
    io = C.CDLL('librpmio.so.9')
    P, I, U, S = C.c_void_p, C.c_int, C.c_uint, C.c_char_p
    callback_type = C.CFUNCTYPE(P, P, I, C.c_uint64, C.c_uint64, P, P)

    def bind(lib, name, result, args):
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = result, args
        return fn

    config = bind(rpm, 'rpmReadConfigFiles', I, [S, S])
    create = bind(rpm, 'rpmtsCreate', P, [])
    free = bind(rpm, 'rpmtsFree', P, [P])
    root = bind(rpm, 'rpmtsSetRootDir', I, [P, S])
    mode = bind(rpm, 'rpmtsSetDBMode', I, [P, I])
    open_db = bind(rpm, 'rpmtsOpenDB', I, [P, I])
    close_db = bind(rpm, 'rpmtsCloseDB', I, [P])
    iterator = bind(rpm, 'rpmtsInitIterator', P, [P, I, S, C.c_size_t])
    next_header = bind(rpm, 'rpmdbNextIterator', P, [P])
    free_iterator = bind(rpm, 'rpmdbFreeIterator', P, [P])
    read = bind(rpm, 'rpmReadPackageFile', I, [P, P, S, C.POINTER(P)])
    header_free = bind(rpm, 'headerFree', P, [P])
    header_string = bind(rpm, 'headerGetString', S, [P, I])
    install = bind(rpm, 'rpmtsAddInstallElement', I, [P, P, P, I, P])
    erase = bind(rpm, 'rpmtsAddEraseElement', I, [P, P, I])
    check = bind(rpm, 'rpmtsCheck', I, [P])
    problems = bind(rpm, 'rpmtsProblems', P, [P])
    problem_count = bind(rpm, 'rpmpsNumProblems', I, [P])
    problem_free = bind(rpm, 'rpmpsFree', P, [P])
    problem_print = bind(rpm, 'rpmpsPrint', None, [P, P])
    order = bind(rpm, 'rpmtsOrder', I, [P])
    tsi_init = bind(rpm, 'rpmtsiInit', P, [P])
    tsi_next = bind(rpm, 'rpmtsiNext', P, [P, U])
    tsi_free = bind(rpm, 'rpmtsiFree', P, [P])
    te_type = bind(rpm, 'rpmteType', I, [P])
    te_fields = [bind(rpm, name, S, [P]) for name in ('rpmteN', 'rpmteV', 'rpmteR', 'rpmteA')]
    set_flags = bind(rpm, 'rpmtsSetFlags', U, [P, U])
    notify = bind(rpm, 'rpmtsSetNotifyCallback', I, [P, callback_type, P])
    run = bind(rpm, 'rpmtsRun', I, [P, P, U])
    fopen = bind(io, 'Fopen', P, [S, S])
    fclose = bind(io, 'Fclose', I, [P])
    ferror = bind(io, 'Ferror', I, [P])

    def identity(header):
        return tuple(header_string(header, tag).decode() for tag in (1000, 1001, 1002, 1022))

    def no_problems(ts):
        ps = problems(ts)
        try:
            count = problem_count(ps) if ps else 0
            if count:
                problem_print(P.in_dll(C.CDLL(None), 'stderr'), ps)
            require(count == 0, f'Transaction has {count} unresolved RPM problems')
        finally:
            if ps:
                problem_free(ps)

    def plan(ts):
        it = tsi_init(ts)
        require(it, 'Cannot inspect transaction plan')
        entries = []
        try:
            while True:
                te = tsi_next(it, 0)
                if not te:
                    break
                entries.append((te_type(te), tuple(fn(te).decode() for fn in te_fields)))
        finally:
            tsi_free(it)
        require(sorted(entries) == sorted([(1, incoming[:4]), (2, outgoing[:4])]),
                f'Unexpected transaction plan: {entries}')
        print(json.dumps({'stage': stage, 'plan': entries}), flush=True)

    path = rpm_path(directory, incoming)
    key_buffer = C.create_string_buffer(os.fsencode(path))
    fd_state = {'fd': None, 'errors': []}

    @callback_type
    def callback(header, what, amount, total, key, data):
        # Exceptions must never escape a ctypes callback.
        try:
            if what == 4:  # RPMCALLBACK_INST_OPEN_FILE
                require(key == C.addressof(key_buffer), 'Unexpected package retrieval key')
                require(fd_state['fd'] is None, 'Duplicate RPM payload open')
                rpm_path(directory, incoming)  # Recheck approved exact payload.
                fd = fopen(os.fsencode(path), b'r.ufdio')
                require(fd, 'Cannot open approved RPM payload')
                if ferror(fd):
                    fclose(fd)
                    raise RuntimeError('Cannot read approved RPM payload')
                fd_state['fd'] = fd
                return fd
            if what == 8:  # RPMCALLBACK_INST_CLOSE_FILE
                require(fd_state['fd'] is not None, 'RPM payload close without open')
                fd = fd_state['fd']
                fd_state['fd'] = None
                require(fclose(fd) == 0, 'RPM payload close failure')
            if what in (1 << 13, 1 << 14, 1 << 15):
                # Nonfatal script failures must still fail our acceptance.
                fd_state['errors'].append(f'RPM error event {what}, code {total}')
        except Exception as exc:
            fd_state['errors'].append(str(exc))
        return None

    require(config(None, None) == 0, 'RPM configuration failed')
    ts = create()
    require(ts, 'RPM transaction creation failed')
    try:
        require(root(ts, b'/') == 0, 'RPM root setup failed')
        require(mode(ts, os.O_RDONLY) == 0, 'RPM read-only mode failed')
        require(open_db(ts, os.O_RDONLY) == 0, 'RPM DB open failed')
        header = P()
        fd = fopen(os.fsencode(path), b'r.ufdio')
        require(fd, 'RPM header open failed')
        if ferror(fd):
            fclose(fd)
            raise RuntimeError('RPM header read failed')
        try:
            rc = read(ts, fd, os.fsencode(path), C.byref(header))
            require(rc in (0, 4) and header.value, f'RPM header verification failed: {rc}')
            print(f'Header status {rc}; known NOKEY=4 permitted, verification flags unchanged', flush=True)
        finally:
            fclose(fd)
        try:
            require(identity(header) == incoming[:4], 'Incoming RPM identity mismatch')
            require(install(ts, header, C.addressof(key_buffer), 0, None) == 0, 'RPM add install failed')
        finally:
            header_free(header)
        it = iterator(ts, 1000, outgoing[0].encode(), 0)
        require(it, 'Missing installed outgoing provider')
        try:
            installed = next_header(it)
            require(installed and identity(installed) == outgoing[:4], 'Outgoing RPM identity mismatch')
            require(erase(ts, installed, 0) == 0, 'RPM add erase failed')
            require(not next_header(it), 'Multiple outgoing provider records')
        finally:
            free_iterator(it)
        plan(ts)
        require(check(ts) == 0, 'RPM dependency check failed')
        no_problems(ts)
        require(order(ts) == 0, 'RPM order failed')
        plan(ts)
        if stage == 'check':
            return
        require(os.geteuid() == 0, 'Root required for TEST/apply')
        # Reopen for the normal RPM run. No dependency/problem filters are used.
        require(close_db(ts) == 0, 'RPM DB close failed')
        require(mode(ts, os.O_RDWR) == 0, 'RPM run DB mode failed')
        require(notify(ts, callback, None) == 0, 'RPM callback setup failed')
        set_flags(ts, 1 if stage == 'test' else 0)
        rc = run(ts, None, 0)
        no_problems(ts)
        require(rc == 0 and not fd_state['errors'], f'RPM run failure: rc={rc}, {fd_state["errors"]}')
        print(f'PASS: exact combined {stage} transaction', flush=True)
    finally:
        if fd_state['fd'] is not None:
            fclose(fd_state['fd'])
        free(ts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('native', 'sdk', 'fixture', 'dev'), required=True)
    parser.add_argument('--direction', choices=('to-gnu', 'to-alias'), required=True)
    parser.add_argument('--mode', choices=('check', 'test', 'apply'), default='check')
    parser.add_argument('--rpm-dir', type=Path, required=True)
    args = parser.parse_args()
    def safe_owner(info):
        # SDK fakeroot metadata does not survive Python exec for staged files.
        # This accommodation can install only the fixed synthetic fixture RPMs.
        return info.st_uid == 0 or (args.profile == 'fixture' and
                                   info.st_uid == 1000 and info.st_gid in (1000, 100000))
    require(subprocess.check_output(['/usr/bin/rpm', '-q', '--qf', '%{VERSION}', 'rpm'], text=True)
            == '4.16.1.3+git20', 'Unsupported RPM ABI')
    if args.profile == 'fixture':
        require(subprocess.check_output(['/usr/bin/rpm', '-q', '--qf', '%{RELEASE}', 'rpm'], text=True)
                == '1.13.2.jolla', 'Fixture profile restricted to recorded SDK RPM release')
    directory = args.rpm_dir.resolve(strict=True)
    if args.mode != 'check':
        require(os.geteuid() == 0, 'Root required for transaction test/apply')
        for path in (directory, Path(__file__).resolve()):
            info = path.stat()
            require(safe_owner(info) and info.st_mode & 0o022 == 0,
                    f'Execution input must be root-owned and not group/world writable: {path}')
    gnu = PACKAGES[args.profile + '-gnu']
    alias = PACKAGES[{'fixture': 'fixture-alias', 'dev': 'dev-alias'}.get(args.profile, 'alias')]
    for package in (gnu, alias):
        path = rpm_path(directory, package)
        if args.mode != 'check':
            info = path.stat()
            require(safe_owner(info) and info.st_mode & 0o022 == 0, f'Unsafe RPM permissions: {path}')
    incoming, outgoing = (gnu, alias) if args.direction == 'to-gnu' else (alias, gnu)
    before = inventory()
    require(before.count(row(outgoing)) == 1 and row(incoming) not in before,
            'Unexpected initial shell provider state')
    try:
        transaction(directory, incoming, outgoing, 'check' if args.mode == 'check' else 'test')
        require(inventory() == before, 'Preflight unexpectedly changed inventory')
        if args.mode == 'apply':
            transaction(directory, incoming, outgoing, 'apply')
            expected = before.copy()
            expected.remove(row(outgoing))
            expected.append(row(incoming))
            require(inventory() == sorted(expected), 'Unexpected post-transaction package inventory')
    except Exception:
        print('STOP: do not retry blindly; inspect provider state and preserved rollback inputs.', flush=True)
        raise


if __name__ == '__main__':
    main()

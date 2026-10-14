#!/usr/bin/env python3
"""Read-only PackageKit simulation using the installed SIMULATE enum.

Send on SSH stdin; no installation method is ever called without SIMULATE.
No credentials, keys or password stores are read.
"""
import ctypes as C
import json
import subprocess
import sys

package = 'gnu-bash;5.0.18+git2-1.6.8.jolla;aarch64;jolla'
assert sys.argv[1:] in ([], ['--remove-symlink'])
remove = sys.argv[1:] == ['--remove-symlink']
if remove:
    package = 'busybox-symlinks-bash;1.36.1+git11-1.15.1.jolla;aarch64;installed'
pk = C.CDLL('libpackagekit-glib2.so.18')
gio = C.CDLL('libgio-2.0.so.0')
glib = C.CDLL('libglib-2.0.so.0')

def bind(lib, name, result, arguments):
    f = getattr(lib, name)
    f.restype, f.argtypes = result, arguments
    return f

enum = bind(pk, 'pk_transaction_flag_enum_from_string', C.c_uint, [C.c_char_p])
simulate = enum(b'simulate')
assert simulate == 2, 'Unexpected installed simulation enum; abort'
flags = (1 << simulate) | (1 << enum(b'only-trusted'))
get_bus = bind(gio, 'g_bus_get_sync', C.c_void_p, [C.c_int, C.c_void_p, C.c_void_p])
call = bind(gio, 'g_dbus_connection_call_sync', C.c_void_p,
            [C.c_void_p, C.c_char_p, C.c_char_p, C.c_char_p, C.c_char_p,
             C.c_void_p, C.c_void_p, C.c_int, C.c_int, C.c_void_p, C.c_void_p])
new_uint = bind(glib, 'g_variant_new_uint64', C.c_void_p, [C.c_uint64])
new_bool = bind(glib, 'g_variant_new_boolean', C.c_void_p, [C.c_int])
new_strings = bind(glib, 'g_variant_new_strv', C.c_void_p, [C.POINTER(C.c_char_p), C.c_ssize_t])
new_tuple = bind(glib, 'g_variant_new_tuple', C.c_void_p, [C.POINTER(C.c_void_p), C.c_size_t])
child = bind(glib, 'g_variant_get_child_value', C.c_void_p, [C.c_void_p, C.c_size_t])
get_string = bind(glib, 'g_variant_get_string', C.c_char_p, [C.c_void_p, C.c_void_p])
render = bind(glib, 'g_variant_print', C.c_void_p, [C.c_void_p, C.c_int])
free = bind(glib, 'g_free', None, [C.c_void_p])
loop_new = bind(glib, 'g_main_loop_new', C.c_void_p, [C.c_void_p, C.c_int])
loop_run = bind(glib, 'g_main_loop_run', None, [C.c_void_p])
loop_quit = bind(glib, 'g_main_loop_quit', None, [C.c_void_p])
callback_type = C.CFUNCTYPE(None, C.c_void_p, C.c_char_p, C.c_char_p,
                           C.c_char_p, C.c_char_p, C.c_void_p, C.c_void_p)
subscribe = bind(gio, 'g_dbus_connection_signal_subscribe', C.c_uint,
                 [C.c_void_p, C.c_char_p, C.c_char_p, C.c_char_p, C.c_char_p,
                  C.c_char_p, C.c_int, callback_type, C.c_void_p, C.c_void_p])
timer_type = C.CFUNCTYPE(C.c_int, C.c_void_p)
add_timer = bind(glib, 'g_timeout_add_seconds', C.c_uint,
                 [C.c_uint, timer_type, C.c_void_p])
before = subprocess.check_output(['rpm', '-qa'], text=True).splitlines()
bus = get_bus(1, None, None)
assert bus
result = call(bus, b'org.freedesktop.PackageKit', b'/org/freedesktop/PackageKit',
              b'org.freedesktop.PackageKit', b'CreateTransaction', None, None,
              0, 10000, None, None)
assert result, 'CreateTransaction failed'
path = get_string(child(result, 0), None)
loop = loop_new(None, 0)
signals = []

@callback_type
def signal(connection, sender, object_path, interface, name, parameters, data):
    text_pointer = render(parameters, 1)
    text = C.string_at(text_pointer).decode()
    free(text_pointer)
    signals.append({'signal': name.decode(), 'parameters': text})
    if name == b'Finished':
        loop_quit(loop)

@timer_type
def timeout(data):
    signals.append({'signal': 'Timeout'})
    loop_quit(loop)
    return 0

subscribe(bus, b'org.freedesktop.PackageKit', b'org.freedesktop.PackageKit.Transaction',
          None, path, None, 0, signal, None, None)
items = (C.c_char_p * 1)(package.encode())
arguments = ((C.c_void_p * 4)(new_uint(flags), new_strings(items, 1), new_bool(0), new_bool(0))
             if remove else (C.c_void_p * 2)(new_uint(flags), new_strings(items, 1)))
params = new_tuple(arguments, len(arguments))
assert flags & (1 << simulate), 'SIMULATE required'
result = call(bus, b'org.freedesktop.PackageKit', path,
              b'org.freedesktop.PackageKit.Transaction',
              b'RemovePackages' if remove else b'InstallPackages', params,
              None, 0, 10000, None, None)
assert result, 'Simulation call failed; no real transaction fallback'
add_timer(30, timeout, None)
loop_run(loop)
after = subprocess.check_output(['rpm', '-qa'], text=True).splitlines()
assert sorted(before) == sorted(after), 'Installed package inventory changed'
print(json.dumps({'package': package, 'method': 'RemovePackages' if remove else 'InstallPackages',
                  'simulation_flag': flags,
                  'installed_inventory_unchanged': True, 'signals': signals}, indent=2))
assert any(s['signal'] == 'Finished' for s in signals), 'Simulation incomplete'

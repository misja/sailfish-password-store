#!/usr/bin/busybox sh
set -eu
umask 077
test "$(id -u)" = 100000
fixture=/tmp/sailfish-pass-synthetic-lu9vjbpn
socket=/run/user/100000/gnupg/d.awtapgwfy3m48yw1xcijogkf/S.gpg-agent
test ! -L "$fixture"
test "$(stat -c '%u %a' "$fixture")" = '100000 700'
test "$(stat -c '%u %a' "$fixture/gnupg")" = '100000 700'
test "$(stat -c '%u %a' "$fixture/store")" = '100000 700'
grep -Fxq 'Synthetic Sailfish pass acceptance only' "$fixture/synthetic-marker.txt"
python3 - "$fixture" <<'VALIDATE_CORE'
import json,sys
from pathlib import Path
r=json.loads((Path(sys.argv[1])/'core-evidence.json').read_text())
assert r['fixture']==sys.argv[1] and r['core_passed'] and r['agent_stopped']
assert len(r['checks'])==9 and 'failure' not in r
assert r['socket']=='/run/user/100000/gnupg/d.awtapgwfy3m48yw1xcijogkf/S.gpg-agent'
assert not Path('/proc/'+r['agent_pid']).exists()
assert not Path(r['socket']).exists()
VALIDATE_CORE
tty_path=$(tty)
case "$tty_path" in /dev/pts/*|/dev/tty[0-9]*) ;; *) printf 'STOP: geen bruikbare TTY.\n'; exit 1 ;; esac
test -c "$tty_path"
test ! -e "$socket"
env -i PATH=/usr/bin:/bin HOME="$fixture" LC_ALL=C GNUPGHOME="$fixture/gnupg" /usr/libexec/sailfish-gnupg/bin/gpg-connect-agent --homedir "$fixture/gnupg" --no-autostart 'GETINFO pid' /bye > "$fixture/before-tty-agent-probe.txt" 2>&1 || :
cat "$fixture/before-tty-agent-probe.txt"
grep -Fxq 'gpg-connect-agent: no gpg-agent running in this session' "$fixture/before-tty-agent-probe.txt"
if grep -Eq '^D [0-9]+$' "$fixture/before-tty-agent-probe.txt"; then printf 'STOP: agent draait al.\n'; exit 1; fi
test ! -e "$socket"
printf 'Cache leeg; verwacht nu tty-pinentry voor pass show.\n'
env -i PATH=/usr/bin:/bin HOME="$fixture" LC_ALL=C TERM="${TERM:-xterm}" GPG_TTY="$tty_path" SAILFISH_GNUPGHOME="$fixture/gnupg" GNUPGHOME="$fixture/gnupg" PASSWORD_STORE_DIR="$fixture/store" /usr/bin/pass show synthetic/demo > "$fixture/tty-demo-actual.txt"
cmp "$fixture/expected-demo.txt" "$fixture/tty-demo-actual.txt"
printf 'PASS: gewone pass show na lege cache, synthetische bytes identiek.\n'
env -i PATH=/usr/bin:/bin HOME="$fixture" LC_ALL=C GNUPGHOME="$fixture/gnupg" /usr/libexec/sailfish-gnupg/bin/gpg-connect-agent --homedir "$fixture/gnupg" --no-autostart 'GETINFO pid' /bye > "$fixture/tty-agent-pid.txt" 2>&1
cat "$fixture/tty-agent-pid.txt"
agent_pid=$(sed -n 's/^D \([0-9][0-9]*\)$/\1/p' "$fixture/tty-agent-pid.txt")
case "$agent_pid" in ''|*[!0-9]*) printf 'STOP: agent-PID ontbreekt.\n'; exit 1 ;; esac
test "$(readlink "/proc/$agent_pid/exe")" = /usr/libexec/sailfish-gnupg/bin/gpg-agent
printf 'PASS: tty-fixture-agent executable privaat; PID %s.\n' "$agent_pid"

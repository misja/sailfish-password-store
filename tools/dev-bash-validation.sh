#!/usr/bin/busybox sh
# Bounded Sailfish 5.1 dev-device validation; never reads user stores or keys.
set -eu
umask 077
PATH=/usr/bin:/bin
export PATH
unset LD_PRELOAD LD_LIBRARY_PATH PYTHONPATH PYTHONHOME BASH_ENV ENV
mode=${1:?prepare|apply|postboot|rollback}
review=/var/tmp/sailfish-bash-dev.0cHs5x
stage=/var/tmp/sailfish-bash-dev-root-20261011
runner_hash=da88155f8d33b08b11a403956cd8b1216aff3e77435046e9d470de034b399cd6
test "$(id -u)" = 0
check_inputs() {
 test ! -L "$stage"
 test "$(stat -c '%u %a' "$stage")" = '0 700'
 test "$(sha256sum "$stage/shell-provider-transaction.py" | cut -d ' ' -f 1)" = "$runner_hash"
 test "$(sha256sum "$stage/gnu-bash-5.0.18+git2-1.6.7.jolla.aarch64.rpm" | cut -d ' ' -f 1)" = 298136960d2a4ed126a4040e2ba5122ecaa005a378394f81e0386e315d04b456
 test "$(sha256sum "$stage/busybox-symlinks-bash-1.36.1+git10-1.14.1.jolla.aarch64.rpm" | cut -d ' ' -f 1)" = 83d3d93f2f0937c9c1e99464515a97f6ece34807bc178dae0befb9ce65447870
}
run_transaction() {
 env -i PATH=/usr/bin:/bin HOME="$stage" LANG=C /usr/bin/python3 "$stage/shell-provider-transaction.py" --profile dev --direction "$1" --mode "$2" --rpm-dir "$stage"
}
inventory() { rpm -qa --qf '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n' | sort; }
files() {
 while IFS= read -r p; do
  if [ -L "$p" ]; then printf 'LINK %s %s\n' "$p" "$(readlink "$p")"
  elif [ -f "$p" ]; then sha256sum "$p"
  else printf 'ABSENT %s\n' "$p"
  fi
 done < "$stage/stock-paths.txt"
}
verify_stock() {
 for pkg in busybox glibc zlib systemd; do
  if rpm -V "$pkg" > "$stage/$pkg.verify-$1.txt" 2>&1; then rc=0; else rc=$?; fi
  printf '%s\n' "$rc" > "$stage/$pkg.verify-$1.exit"
 done
}
compare_stock() {
 files > "$stage/stock-$1.txt"
 awk '$2!="/bin/bash" && $2!="/bin/sh" && $2!="/usr/bin/bash" && $2!="/usr/bin/sh" && $2!="/etc/profile.d/set_ps1.sh"' "$stage/stock-before.txt" > "$stage/unrelated-before.txt"
 awk '$2!="/bin/bash" && $2!="/bin/sh" && $2!="/usr/bin/bash" && $2!="/usr/bin/sh" && $2!="/etc/profile.d/set_ps1.sh"' "$stage/stock-$1.txt" > "$stage/unrelated-$1.txt"
 cmp "$stage/unrelated-before.txt" "$stage/unrelated-$1.txt"
 verify_stock "$1"
 for pkg in busybox glibc zlib systemd; do
  cmp "$stage/$pkg.verify-before.txt" "$stage/$pkg.verify-$1.txt"
  cmp "$stage/$pkg.verify-before.exit" "$stage/$pkg.verify-$1.exit"
 done
}
check_gnu() {
 rpm -V gnu-bash
 test "$(rpm -q gnu-bash)" = gnu-bash-5.0.18+git2-1.6.7.jolla.aarch64
 if rpm -q busybox-symlinks-bash >/dev/null 2>&1; then return 1; fi
 for p in /bin/bash /bin/sh /usr/bin/bash /usr/bin/sh; do test -x "$p"; done
 env -i PATH=/usr/bin:/bin HOME="$stage" LANG=C /bin/bash --noprofile --norc -c 'set -eu; set -o pipefail; a=(synthetic); test "${a[0]}" = synthetic; printf "BASH_VERSION=%s\n" "$BASH_VERSION"'
 env -i PATH=/usr/bin:/bin HOME="$stage" LANG=C /bin/sh -c 'set -eu; test "$(printf shell-ok)" = shell-ok'
 test "$(/usr/bin/getopt -o a -- -a)" = " -a --"
 inventory > "$stage/packages-current.txt"
 cmp "$stage/packages-expected.txt" "$stage/packages-current.txt"
 compare_stock "$1"
 run_transaction to-alias test
}
case "$mode" in
 prepare)
  test "$(uname -m)" = aarch64
  test "$(sed -n 's/^VERSION_ID=//p' /etc/os-release)" = 5.1.0.11
  test "$(rpm -q busybox-symlinks-bash)" = busybox-symlinks-bash-1.36.1+git10-1.14.1.jolla.aarch64
  if rpm -q gnu-bash >/dev/null 2>&1; then exit 1; fi
  rpm -V busybox-symlinks-bash
  for p in /etc/skel/.bash_logout /etc/skel/.bash_profile /etc/skel/.bashrc; do test ! -e "$p"; test ! -L "$p"; done
  test ! -e "$stage"; test ! -L "$stage"
  mkdir -m 700 "$stage"
  test ! -L "$review"
  for f in shell-provider-transaction.py gnu-bash-5.0.18+git2-1.6.7.jolla.aarch64.rpm busybox-symlinks-bash-1.36.1+git10-1.14.1.jolla.aarch64.rpm; do
   test ! -L "$review/$f"; cp "$review/$f" "$stage/$f"; chmod 600 "$stage/$f"
  done
  test ! -L "$0"
  test "$(stat -c '%u %a' "$0")" = '0 600'
  cp "$0" "$stage/dev-bash-validation.sh"
  chmod 600 "$stage/dev-bash-validation.sh"
  check_inputs
  inventory > "$stage/packages-before.txt"
  awk '$1!="busybox-symlinks-bash"' "$stage/packages-before.txt" > "$stage/packages-expected.unsorted"
  printf '%s\n' 'gnu-bash 5.0.18+git2-1.6.7.jolla aarch64' >> "$stage/packages-expected.unsorted"
  sort "$stage/packages-expected.unsorted" > "$stage/packages-expected.txt"
  { rpm -ql busybox glibc zlib systemd | awk '/^\/(usr\/)?(bin|sbin|lib64)\//'; printf '%s\n' /bin/bash /bin/sh /usr/bin/bash /usr/bin/sh /etc/profile.d/set_ps1.sh; } | sort -u > "$stage/stock-paths.txt"
  files > "$stage/stock-before.txt"
  verify_stock before
  cat /proc/sys/kernel/random/boot_id > "$stage/boot-before.txt"
  systemctl --failed --no-legend --no-pager > "$stage/failed-before.txt"
  systemctl show sshd.socket connman.service ofono.service dbus.service --property=Id --property=LoadState --property=ActiveState --property=SubState > "$stage/services-before.txt"
  run_transaction to-gnu test > "$stage/test.log" 2>&1
  cat "$stage/test.log"
  inventory > "$stage/packages-after-test.txt"
  cmp "$stage/packages-before.txt" "$stage/packages-after-test.txt"
  files > "$stage/stock-after-test.txt"
  cmp "$stage/stock-before.txt" "$stage/stock-after-test.txt"
  printf 'PASS: root baseline and exact TEST; no provider change. Evidence: %s\n' "$stage"
  ;;
 apply)
  check_inputs
  inventory > "$stage/packages-preapply.txt"
  cmp "$stage/packages-before.txt" "$stage/packages-preapply.txt"
  files > "$stage/stock-preapply.txt"
  cmp "$stage/stock-before.txt" "$stage/stock-preapply.txt"
  run_transaction to-gnu apply > "$stage/apply.log" 2>&1
  cat "$stage/apply.log"
  if /usr/bin/busybox sh "$stage/dev-bash-validation.sh" verify-apply > "$stage/verification.log" 2>&1; then
   cat "$stage/verification.log"
   printf 'PASS: official GNU Bash installed; inverse TEST passed. Reboot pending.\n'
  else
   cat "$stage/verification.log"
   printf 'Verification failed; attempting exact provider restoration.\n'
   run_transaction to-alias apply
   exit 1
  fi
  ;;
 verify-apply)
  check_inputs
  check_gnu after-apply
  ;;
 postboot)
  check_inputs
  cat /proc/sys/kernel/random/boot_id > "$stage/boot-after.txt"
  if cmp -s "$stage/boot-before.txt" "$stage/boot-after.txt"; then printf 'STOP: reboot not proved.\n'; exit 1; fi
  check_gnu postboot
  systemctl --failed --no-legend --no-pager > "$stage/failed-after.txt"
  systemctl show sshd.socket connman.service ofono.service dbus.service --property=Id --property=LoadState --property=ActiveState --property=SubState > "$stage/services-after.txt"
  cmp "$stage/services-before.txt" "$stage/services-after.txt"
  cat "$stage/failed-after.txt"
  if cmp -s "$stage/failed-before.txt" "$stage/failed-after.txt"; then printf 'PASS: failed-unit list unchanged.\n'; else printf 'REVIEW: failed-unit list differs; investigate before acceptance.\n'; exit 1; fi
  printf 'PASS: postboot package, shell, stock and rollback checks. Manual phone checks still required.\n'
  ;;
 rollback)
  check_inputs
  run_transaction to-alias apply
  rpm -V busybox-symlinks-bash
  inventory > "$stage/packages-restored.txt"
  cmp "$stage/packages-before.txt" "$stage/packages-restored.txt"
  files > "$stage/stock-restored.txt"
  cmp "$stage/stock-before.txt" "$stage/stock-restored.txt"
  compare_stock restored
  for p in /etc/skel/.bash_logout /etc/skel/.bash_profile /etc/skel/.bashrc; do test ! -e "$p"; test ! -L "$p"; done
  printf 'PASS: original provider and measured baseline restored.\n'
  ;;
 *) exit 1 ;;
esac

#!/usr/bin/busybox sh
# Exact policy candidate RPMs on Sailfish 5.2; keep the official Bash provider.
set -eu
umask 077
PATH=/usr/bin:/bin
export PATH
unset LD_PRELOAD LD_LIBRARY_PATH BASH_ENV ENV PYTHONPATH PYTHONHOME
mode=${1:?preflight|install|remove}
review=/var/tmp/sailfish-otp-dev-20261012
stage=/var/tmp/sailfish-otp-dev-root-20261012
test "$(id -u)" = 0
test "$(sed -n 's/^VERSION_ID=//p' /etc/os-release)" = 5.2.0.18
test "$(uname -m)" = aarch64
test "$(rpm -q gnu-bash)" = gnu-bash-5.0.18+git2-1.6.8.jolla.aarch64
rpm -V gnu-bash
check_inputs() {
 test ! -L "$stage"; test "$(stat -c '%u %a' "$stage")" = '0 700'
 test "$(sha256sum "$stage/sailfish-gnupg-private-2.5.24-0.3.aarch64.rpm" | cut -d ' ' -f 1)" = eb4cde3411df247262a6e7811b3fa1e05d76d8a1b4e064f95c68507c0d4e77c8
 test "$(sha256sum "$stage/sailfish-pass-1.7.4-0.3.noarch.rpm" | cut -d ' ' -f 1)" = abb673fdde0a54ef1b3e094f2e5fd8272c83c9704e8f05110337dd2857312f63
 test "$(sha256sum "$stage/sailfish-pass-tree-2.3.2-0.1.aarch64.rpm" | cut -d ' ' -f 1)" = 33578eae9014099575c0f5fa010ee5243b89c8f8e02b19e19105c5b33d24a32b
 test "$(sha256sum "$stage/sailfish-oathtool-2.6.14-0.3.aarch64.rpm" | cut -d ' ' -f 1)" = 3e915357880a36bb0a1e57d4ab375bc0dcfbad26893add5bbfeb37b02d83fe52
 test "$(sha256sum "$stage/sailfish-pass-otp-1.2.0-0.3.noarch.rpm" | cut -d ' ' -f 1)" = f35949e0b250c9f4427a6f4df96c3c8ab42b31c3c98198deae222551caf253a8
 test "$(sha256sum "$stage/sailfish-liboath-2.6.14-0.3.aarch64.rpm" | cut -d ' ' -f 1)" = d7cbd3a1fbf394650be46cc815e93d0e4afccd1555aecd0b2cdb697adc642a94
}
inventory() { rpm -qa --qf '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n' | sort; }
stock() {
 count=0
 while IFS= read -r p; do
  if [ -L "$p" ]; then printf 'LINK %s %s\n' "$p" "$(readlink "$p")"
  elif [ -f "$p" ]; then sha256sum "$p"
  else printf 'ABSENT %s\n' "$p"
  fi
  count=$((count + 1))
  if test "$((count % 40))" = 0; then printf 'Stockcontrole: %s bestanden\n' "$count" >&2; fi
 done < "$stage/stock-paths.txt"
}
verify_stock() {
 for pkg in gnu-bash busybox glibc zlib systemd gnupg2 gpgme libgcrypt libgpg-error libksba pth; do
  if rpm -V "$pkg" > "$stage/$pkg.verify-$1.txt" 2>&1; then rc=0; else rc=$?; fi
  printf '%s\n' "$rc" > "$stage/$pkg.verify-$1.exit"
 done
}
compare_stock() {
 stock > "$stage/stock-$1.txt"
 cmp "$stage/stock-before.txt" "$stage/stock-$1.txt"
 verify_stock "$1"
 for previous in "$stage"/*.verify-before.txt; do
  pkg=${previous##*/}; pkg=${pkg%.verify-before.txt}
  cmp "$previous" "$stage/$pkg.verify-$1.txt"
  cmp "$stage/$pkg.verify-before.exit" "$stage/$pkg.verify-$1.exit"
 done
}
no_private_processes() {
  # Never install/remove over existing private processes; inspect executable paths only.
  for p in /proc/[0-9]*/exe; do
   target=$(readlink "$p" 2>/dev/null || :)
   case "$target" in /usr/libexec/sailfish-gnupg/*|/usr/libexec/sailfish-oath/*) printf 'STOP: private process remains: %s\n' "$p"; exit 1;; esac
  done
}
absent() {
 no_private_processes
 for pkg in sailfish-gnupg-private sailfish-pass sailfish-pass-tree sailfish-liboath sailfish-oathtool sailfish-pass-otp; do
  if rpm -q "$pkg" >/dev/null 2>&1; then printf 'STOP: %s already installed\n' "$pkg"; exit 1; fi
 done
 for p in /usr/bin/sailfish-gpg /usr/bin/sailfish-gpg-agent /usr/bin/sailfish-pass /usr/libexec/sailfish-gnupg /usr/libexec/sailfish-pass /usr/libexec/sailfish-pass-tools /usr/libexec/sailfish-oath; do test ! -e "$p"; test ! -L "$p"; done
}
case "$mode" in
 preflight)
  absent
  test ! -e "$stage"; test ! -L "$stage"; mkdir -m 700 "$stage"
  test ! -L "$review"; test "$(stat -c '%u %a' "$review")" = '100000 700'
  for f in sailfish-gnupg-private-2.5.24-0.3.aarch64.rpm sailfish-pass-1.7.4-0.3.noarch.rpm sailfish-pass-tree-2.3.2-0.1.aarch64.rpm sailfish-oathtool-2.6.14-0.3.aarch64.rpm sailfish-pass-otp-1.2.0-0.3.noarch.rpm sailfish-liboath-2.6.14-0.3.aarch64.rpm; do
   test ! -L "$review/$f"; cp "$review/$f" "$stage/$f"; chmod 600 "$stage/$f"
  done
  check_inputs
  test ! -L "$0"; test "$(stat -c '%u %a' "$0")" = '0 600'
  cp "$0" "$stage/candidate-native-otp-packages.sh"; chmod 600 "$stage/candidate-native-otp-packages.sh"
  { rpm -ql busybox glibc zlib systemd gnupg2 gpgme libgcrypt libgpg-error libksba pth | awk '/^\/(usr\/)?(bin|sbin|lib64)\//'; printf '%s\n' /bin/bash /bin/sh /usr/bin/bash /usr/bin/sh; } | sort -u > "$stage/stock-paths.txt"
  inventory > "$stage/packages-before.txt"
  stock > "$stage/stock-before.txt"
  verify_stock before
  rpm -ivh --test "$stage/sailfish-gnupg-private-2.5.24-0.3.aarch64.rpm" "$stage/sailfish-pass-tree-2.3.2-0.1.aarch64.rpm" "$stage/sailfish-pass-1.7.4-0.3.noarch.rpm" "$stage/sailfish-oathtool-2.6.14-0.3.aarch64.rpm" "$stage/sailfish-pass-otp-1.2.0-0.3.noarch.rpm" "$stage/sailfish-liboath-2.6.14-0.3.aarch64.rpm" 
  inventory > "$stage/packages-after-test.txt"; cmp "$stage/packages-before.txt" "$stage/packages-after-test.txt"
  compare_stock after-test
  printf 'PASS: private-package preflight; no installation. Evidence: %s\n' "$stage"
  ;;
 install)
  check_inputs; absent
  inventory > "$stage/packages-preinstall.txt"; cmp "$stage/packages-before.txt" "$stage/packages-preinstall.txt"
  compare_stock preinstall
  rpm -ivh --test "$stage/sailfish-gnupg-private-2.5.24-0.3.aarch64.rpm" "$stage/sailfish-pass-tree-2.3.2-0.1.aarch64.rpm" "$stage/sailfish-pass-1.7.4-0.3.noarch.rpm" "$stage/sailfish-oathtool-2.6.14-0.3.aarch64.rpm" "$stage/sailfish-pass-otp-1.2.0-0.3.noarch.rpm" "$stage/sailfish-liboath-2.6.14-0.3.aarch64.rpm" 
  rpm -ivh "$stage/sailfish-gnupg-private-2.5.24-0.3.aarch64.rpm" "$stage/sailfish-pass-tree-2.3.2-0.1.aarch64.rpm" "$stage/sailfish-pass-1.7.4-0.3.noarch.rpm" "$stage/sailfish-oathtool-2.6.14-0.3.aarch64.rpm" "$stage/sailfish-pass-otp-1.2.0-0.3.noarch.rpm" "$stage/sailfish-liboath-2.6.14-0.3.aarch64.rpm" 
  rpm -V sailfish-gnupg-private sailfish-pass sailfish-pass-tree sailfish-liboath sailfish-oathtool sailfish-pass-otp
  inventory > "$stage/packages-installed.txt"
  { cat "$stage/packages-before.txt"; printf '%s\n' 'sailfish-gnupg-private 2.5.24-0.3 aarch64' 'sailfish-pass 1.7.4-0.3 noarch' 'sailfish-pass-tree 2.3.2-0.1 aarch64' 'sailfish-liboath 2.6.14-0.3 aarch64' 'sailfish-oathtool 2.6.14-0.3 aarch64' 'sailfish-pass-otp 1.2.0-0.3 noarch'; } | sort > "$stage/packages-expected.txt"
  cmp "$stage/packages-expected.txt" "$stage/packages-installed.txt"
  compare_stock installed
  printf 'PASS: exact six private packages installed; measured stock unchanged.\n'
  ;;
 remove)
  check_inputs
  no_private_processes
  rpm -V sailfish-gnupg-private sailfish-pass sailfish-pass-tree sailfish-liboath sailfish-oathtool sailfish-pass-otp
  inventory > "$stage/packages-preremove.txt"; cmp "$stage/packages-expected.txt" "$stage/packages-preremove.txt"
  rpm -e --test sailfish-pass-otp sailfish-oathtool sailfish-liboath sailfish-pass sailfish-pass-tree sailfish-gnupg-private
  rpm -e sailfish-pass-otp sailfish-oathtool sailfish-liboath sailfish-pass sailfish-pass-tree sailfish-gnupg-private
  absent
  inventory > "$stage/packages-final.txt"; cmp "$stage/packages-before.txt" "$stage/packages-final.txt"
  compare_stock final
  printf 'PASS: private packages removed; baseline restored, GNU Bash retained.\n'
  ;;
 *) exit 1;;
esac

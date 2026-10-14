#!/bin/sh
# Synthetic stdin-only probes; no store/key, fixture files or packages touched.
PATH=/usr/bin:/bin
LC_ALL=C
export PATH LC_ALL
failed=0
check() {
    if [ "$2" = "$3" ]; then printf 'PASS: %s\n' "$1";
    else printf 'FAIL: %s\n' "$1"; failed=$((failed + 1)); fi
}
check 'tr alphanumeric character class' "$(printf 'aA0!_Z9' | tr -dc '[:alnum:]')" 'aA0Z9'
check 'tr punctuation and alphanumeric' "$(printf 'aA0!_ Z9' | tr -dc '[:punct:][:alnum:]')" 'aA0!_Z9'
check 'base64 encode/decode' "$(printf 'U3ludGhldGljCg==\n' | base64 -d)" 'Synthetic'
check 'sed extended expression' "$(printf 'demo.gpg\n' | sed -E 's/\.gpg( ->|$)/\1/g')" 'demo'
check 'upstream listing sed ANSI stripping' "$(printf 'demo.gpg\033[0m\n' | sed -E 's/\.gpg(\x1B\[[0-9]+m)?( ->|$)/\1\2/g')" "$(printf 'demo\033[0m')"
check 'sed BRE plus and sort unique' "$(printf 'gpg: public key is ABC123\ngpg: public key is ABC123\n' | sed -n 's/^gpg: public key is \([A-F0-9]\+\)$/\1/p' | sort -u)" 'ABC123'
check 'head/tail selected line' "$(printf 'one\ntwo\nthree\n' | tail -n +2 | head -n 1)" 'two'
check 'grep exact recipient filter' "$(printf 'cfg:group:synthetic:ABC123\nother\n' | grep '^cfg:group:.*')" 'cfg:group:synthetic:ABC123'
if find -L /dev/null -path '*/.git' -prune -o -iname '*.gpg' -print0 >/dev/null; then
    printf 'PASS: find flags for synthetic paths\n'
else printf 'FAIL: find flags\n'; failed=$((failed + 1)); fi
getopt --test >/dev/null 2>&1
if [ "$?" = 4 ]; then printf 'PASS: util-linux getopt semantics\n';
else printf 'FAIL: getopt semantics\n'; failed=$((failed + 1)); fi
printf 'Utility probe failures: %s\n' "$failed"
exit "$failed"

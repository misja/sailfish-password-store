#!/usr/bin/env bash
# Build staged recipes with the selected SDK; never install dependencies or RPMs.
set -euo pipefail
project_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
sdk_root=${SAILFISH_SDK_ROOT:-"$HOME/SailfishOS"}
: "${SAILFISH_SDK_TARGET:?Set the exact reviewed installed SDK build target}"
test -x "$sdk_root/bin/sfdk" || {
  echo 'Set SAILFISH_SDK_ROOT to an installed SDK directory' >&2; exit 1;
}
cd "$project_dir"
python3 tools/prepare-package.py
mkdir -p evidence
build_log=$(mktemp "$project_dir/evidence/sdk-build.XXXXXX.log")
for recipe in sailfish-pass-tree oath-toolkit sailfish-pass sailfish-pass-otp; do
  "$sdk_root/bin/sfdk" -c "target=$SAILFISH_SDK_TARGET" \
    -c "specfile=rpm/$recipe.spec" -c no-pull-build-requires -c no-vcs-apply build-shell rpmbuild -ba \
    --define "_topdir $project_dir/build/rpmbuild" \
    --define "_sourcedir $project_dir/sources" \
    "$project_dir/rpm/$recipe.spec" 2>&1 | tee -a "$build_log"
done

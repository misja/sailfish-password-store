#!/usr/bin/env bash
set -euo pipefail
project_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test "$project_dir" = /home/ubuntu/password-store || {
    echo 'Run in the existing sailfish-sdk container project' >&2; exit 1;
}
cd "$project_dir"
python3 tools/prepare-package.py
build_log=$(mktemp "$project_dir/evidence/sdk-build-20261011.XXXXXX.log")
# No dependency installation, target update or RPM installation.
# Reuse the already initialized SDK build shell; outputs belong to this project.
cd /home/ubuntu/gnupg-runtime
 /home/ubuntu/SailfishOS/bin/sfdk -c target=SailfishOS-5.1.0.11-aarch64 \
    build-shell rpmbuild -ba \
    --define '_topdir /home/ubuntu/password-store/build/rpmbuild' \
    --define '_sourcedir /home/ubuntu/password-store/sources' \
    /home/ubuntu/password-store/rpm/sailfish-pass-tree.spec \
    2>&1 | tee "$build_log"
/home/ubuntu/SailfishOS/bin/sfdk -c target=SailfishOS-5.1.0.11-aarch64 \
    build-shell rpmbuild -ba \
    --define '_topdir /home/ubuntu/password-store/build/rpmbuild' \
    --define '_sourcedir /home/ubuntu/password-store/sources' \
    /home/ubuntu/password-store/rpm/sailfish-pass.spec \
    2>&1 | tee -a "$build_log"

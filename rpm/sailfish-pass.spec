Name: sailfish-pass
Version: 1.7.4
Release: 0.5
Summary: Private pass CLI feasibility package
License: GPL-2.0-or-later AND GPL-3.0-or-later
URL: https://www.passwordstore.org/
BuildArch: noarch
Source0: password-store-1.7.4-verified.tar
Source1: private-gpg.patch
Source2: sailfish-pass
Source3: sources.lock.json
Source4: pass-tag-verification.json
Source5: pass-release-key.asc
Source6: LICENSE
Source7: LICENSING.md
Source8: pass-tree-fd3.patch
BuildRequires: gnu-bash
# Sailfish SDK supplies GNU Make 4.4.1 as build tooling (not a target RPM).
# See evidence/dependency-inventory-20261011.md; no target dependency bypass.
BuildRequires: patch
Requires: /usr/bin/busybox
Requires: /usr/bin/env
Requires: sailfish-gnupg-private = 2.5.24-0.6
Requires: gnu-bash >= 5.0.18
Requires: /usr/bin/bash
Requires: /usr/bin/getopt
Requires: /usr/bin/tr
Requires: /usr/bin/base64
Requires: /usr/bin/find
Requires: /usr/bin/grep
Requires: /bin/sed
Requires: sailfish-pass-tree = 2.3.2
Requires: /usr/libexec/sailfish-pass-tools/bin/tree
Requires: /usr/bin/id
Requires: (/bin/stat or /usr/bin/stat)

%description
Offline pass CLI bound explicitly to the private GnuPG runtime. Requires
full Bash and compatible utilities; does not replace Jolla software. This
prototype has not completed representative device end-to-end acceptance.

%prep
%setup -q -n password-store-1.7.4
patch -p1 < %{SOURCE1}
patch -p1 < %{SOURCE8}

%build
/usr/bin/bash -n src/password-store.sh

%install
make install DESTDIR=%{buildroot} PREFIX=/usr/libexec/sailfish-pass \
    LIBDIR=/usr/libexec/sailfish-pass WITH_ALLCOMP=no
install -D -m 0755 %{SOURCE2} %{buildroot}/usr/bin/pass
install -D -m 0644 COPYING %{buildroot}/usr/share/licenses/sailfish-pass/COPYING
install -D -m 0644 %{SOURCE6} %{buildroot}/usr/share/licenses/sailfish-pass/GPL-3.0.txt
install -D -m 0644 %{SOURCE7} %{buildroot}/usr/share/licenses/sailfish-pass/LICENSING.md
install -D -m 0644 %{SOURCE3} %{buildroot}/usr/share/doc/sailfish-pass/sources.lock.json
install -D -m 0644 %{SOURCE4} %{buildroot}/usr/share/doc/sailfish-pass/source-verification.json

%files
/usr/bin/pass
/usr/libexec/sailfish-pass
/usr/share/licenses/sailfish-pass
/usr/share/doc/sailfish-pass

Name: sailfish-pass-tree
Version: 2.3.2
Release: 0.1
Summary: Private tree utility for the pass CLI prototype
License: GPL-2.0-or-later
URL: https://gitlab.com/OldManProgrammer/unix-tree
Source0: tree-2.3.2.tar.gz
Source1: tree-source.json
# Make/GCC are supplied by pinned Sailfish SDK build tooling.

%description
Upstream tree installed only under a private tools prefix. Does not provide
or replace /usr/bin/tree or change any stock file or loader configuration.

%prep
%setup -q -n tree-1a41b51bea1cec4109eb9f726370449b384b4576

%build
make %{?_smp_mflags} CC=gcc CFLAGS="%{optflags}" LDFLAGS="%{?build_ldflags}"

%install
install -D -m 0755 tree %{buildroot}/usr/libexec/sailfish-pass-tools/bin/tree
install -D -m 0644 LICENSE %{buildroot}/usr/share/licenses/sailfish-pass-tree/LICENSE
install -D -m 0644 doc/tree.1 %{buildroot}/usr/libexec/sailfish-pass-tools/share/man/man1/tree.1
install -D -m 0644 %{SOURCE1} %{buildroot}/usr/share/doc/sailfish-pass-tree/source-provenance.json

%files
/usr/libexec/sailfish-pass-tools
/usr/share/licenses/sailfish-pass-tree
/usr/share/doc/sailfish-pass-tree

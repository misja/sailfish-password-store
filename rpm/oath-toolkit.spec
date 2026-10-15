%global private_prefix /usr/libexec/sailfish-oath
%global __provides_exclude ^liboath\\.so.*$
%global __requires_exclude ^liboath\\.so.*$
Name: oath-toolkit
Version: 2.6.14
Release: 0.3
Summary: One-time password components
License: GPL-3.0-or-later AND LGPL-2.1-or-later
URL: https://oath-toolkit.codeberg.page/
Source0: oath-toolkit-2.6.14.tar.gz
Source1: oath-source.json
Source2: oath-COPYING.LESSER
BuildRequires: chrpath

%description
OATH Toolkit packaging follows separate library and CLI binary packages.
PAM and PSKC are excluded from this private Sailfish prototype.

%package -n sailfish-liboath
Summary: Library for OATH handling
License: LGPL-2.1-or-later
Provides: bundled(gnulib)

%description -n sailfish-liboath
Supported technologies include event-based HOTP (RFC4226) and time-based TOTP
(RFC6238). This package contains the OATH Toolkit Liboath library.

%package -n sailfish-oathtool
Summary: A command line tool for generating and validating OTPs
License: GPL-3.0-or-later
Requires: sailfish-liboath = %{version}-%{release}
Provides: bundled(gnulib)

%description -n sailfish-oathtool
A command line tool for generating and validating OTPs.

%prep
%setup -q -n oath-toolkit-2.6.14

%build
./configure --prefix=%{private_prefix} --libdir=%{private_prefix}/lib --disable-pam --disable-pskc --enable-shared --disable-static
make %{?_smp_mflags}

%check
make -C liboath check
make -C oathtool check

%install
install -D -m 0755 oathtool/.libs/oathtool %{buildroot}%{private_prefix}/bin/oathtool
mkdir -p %{buildroot}%{private_prefix}/lib
cp -a liboath/.libs/liboath.so* %{buildroot}%{private_prefix}/lib/
# The unversioned link is a development artifact, not a runtime payload.
rm %{buildroot}%{private_prefix}/lib/liboath.so
chrpath -c -r %{private_prefix}/lib %{buildroot}%{private_prefix}/bin/oathtool
install -D -m 0644 COPYING %{buildroot}/usr/share/licenses/sailfish-liboath/COPYING
install -D -m 0644 %{SOURCE2} %{buildroot}/usr/share/licenses/sailfish-liboath/COPYING.LESSER
install -D -m 0644 COPYING %{buildroot}/usr/share/licenses/sailfish-oathtool/COPYING
install -D -m 0644 %{SOURCE1} %{buildroot}/usr/share/doc/sailfish-liboath/source-verification.json

%files -n sailfish-liboath
%dir %{private_prefix}
%{private_prefix}/lib
/usr/share/licenses/sailfish-liboath
/usr/share/doc/sailfish-liboath

%files -n sailfish-oathtool
%{private_prefix}/bin
/usr/share/licenses/sailfish-oathtool

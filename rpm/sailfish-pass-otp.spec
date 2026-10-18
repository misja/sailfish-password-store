Name: sailfish-pass-otp
Version: 1.2.0
Release: 0.6
Summary: pass extension for managing one-time-password tokens
License: GPL-3.0-or-later
URL: https://github.com/pass-extension/pass-otp
BuildArch: noarch
Source0: pass-otp-1.2.0.tar.gz
Source1: pass-otp-stdin.patch
Source2: pass-otp-private-backend.patch
Source3: pass-otp-final-line.patch
BuildRequires: gnu-bash
BuildRequires: patch
Requires: sailfish-pass = 1.7.4-0.6
Requires: sailfish-oathtool = 2.6.14-0.3
Requires: /usr/libexec/sailfish-oath/bin/oathtool

%description
OTP support for pass, using the packaged OATH tools. OTP entries are encrypted
in the password store. User-provided extensions remain disabled.

%prep
%setup -q -n pass-otp-1.2.0
patch -p1 < %{SOURCE1}
patch -p1 < %{SOURCE2}
patch -p1 < %{SOURCE3}

%build
/usr/bin/bash -n otp.bash

%install
install -D -m 0755 otp.bash %{buildroot}/usr/libexec/sailfish-pass/password-store/extensions/otp.bash
install -D -m 0644 pass-otp.1 %{buildroot}/usr/share/man/man1/sailfish-pass-otp.1
install -D -m 0644 LICENSE %{buildroot}/usr/share/licenses/sailfish-pass-otp/LICENSE

%files
/usr/libexec/sailfish-pass/password-store/extensions/otp.bash
/usr/share/man/man1/sailfish-pass-otp.1*
/usr/share/licenses/sailfish-pass-otp

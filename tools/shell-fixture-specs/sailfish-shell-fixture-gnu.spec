Name: sailfish-shell-fixture-gnu
Version: 1
Release: 1
Summary: Synthetic RPM transaction acceptance fixture
License: GPL-3.0-or-later
BuildArch: noarch
Provides: sailfish-shell-fixture-provider = 1
Conflicts: sailfish-shell-fixture-alias

%description
Synthetic fixture only; no executable shell or secrets.

%install
mkdir -p %{buildroot}/usr/share/sailfish-shell-transaction-fixture
printf 'synthetic gnu\n' > %{buildroot}/usr/share/sailfish-shell-transaction-fixture/provider

%files
/usr/share/sailfish-shell-transaction-fixture/provider

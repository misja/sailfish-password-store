Name: sailfish-shell-fixture-consumer
Version: 1
Release: 1
Summary: Synthetic RPM transaction acceptance fixture
License: GPL-3.0-or-later
BuildArch: noarch
Requires: sailfish-shell-fixture-provider = 1

%description
Synthetic fixture only; no executable shell or secrets.

%install
mkdir -p %{buildroot}/usr/share/sailfish-shell-transaction-fixture
printf 'synthetic consumer\n' > %{buildroot}/usr/share/sailfish-shell-transaction-fixture/consumer

%files
/usr/share/sailfish-shell-transaction-fixture/consumer

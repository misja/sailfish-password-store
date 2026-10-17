# pass and OTP for Sailfish OS

Command-line password and OTP storage for Sailfish OS, using
[pass](https://www.passwordstore.org/) and pass-otp. Packages include pass 1.7.4,
pass-otp 1.2.0 and the tree/OATH tools they need.

## How the packages fit together

The `pass` command uses [our separately packaged GnuPG runtime](https://github.com/misja/sailfish-gnupg-runtime)
through `sailfish-gpg`. That runtime has its own commands, libraries, key directory
and agent, alongside Jolla’s GnuPG.

Before running `pass` or `pass otp`, select a key directory with
`SAILFISH_GNUPGHOME` and a separate password-store directory with
`PASSWORD_STORE_DIR`. Both must be existing directories owned by you, with mode
`0700`, using absolute physical paths; they must not overlap. The launcher does
not automatically select or migrate your existing store or keys.

The pass package installs `/usr/bin/pass` and requires GNU Bash. Check for an
existing pass package and a compatible Bash provider before installation.
GnuPG’s separate namespace does not resolve those package conflicts.

## Status and development

Earlier builds were exercised on a development Xperia running Sailfish OS
5.2.0.18; package preservation was checked after its update to 5.2.0.20. Current
revisions have SDK build/regression checks. General migration, synchronization
and production support remain outside the accepted scope.

This repository contains RPM recipes, launchers, patches and integration tests.
Adapted pass and pass-otp sources live in [upstream forks](docs/UPSTREAM_FORKS.md),
with exact revisions recorded here. See the [documentation index](docs/index.md)
for source/build instructions and fork maintenance.

Development uses AI-assisted tools under maintainer review. See [CONTRIBUTING](CONTRIBUTING.md) for review and testing requirements. Shared working agreements live in [sailfish-workspace](https://github.com/misja/sailfish-workspace).

Original work is [GPL-3.0-or-later](LICENSING.md). The pass, pass-otp and other [upstream licenses](THIRD_PARTY.md) remain in force.

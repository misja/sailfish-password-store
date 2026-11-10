# pass and OTP for Sailfish OS

Command-line password and OTP storage for Sailfish OS, using
[pass](https://github.com/misja/sailfish-pass/tree/sailfish/private-gpg) and
[pass-otp](https://github.com/misja/pass-otp/tree/sailfish/stdin-private-backend). Packages include pass,
pass-otp and the tree and OATH tools they need.

## How the packages fit together

The `pass` command uses the [Sailfish GnuPG runtime](https://github.com/misja/sailfish-gnupg-runtime)
through `sailfish-gpg`. That runtime has its own commands, libraries, key directory
and agent, alongside Jolla's GnuPG.

Before running `pass` or `pass otp`, select a key directory with
`SAILFISH_GNUPGHOME` and a separate password-store directory with
`PASSWORD_STORE_DIR`. Both must be existing directories owned by you, with mode
`0700`, using absolute physical paths; they must not overlap. The launcher does
not automatically select or migrate your existing store or keys.

The pass package installs `/usr/bin/pass`, so it cannot be installed next to
another pass package; remove that first. It needs GNU Bash. When upgrading an existing installation, update the runtime, pass and pass-otp in
the same package transaction.

Moving an existing password store or keys into these packages, and
synchronising a store, are not supported.

## Development

This repository contains RPM recipes, launchers, patches and integration tests.
Adapted pass and pass-otp sources live in [upstream forks](docs/UPSTREAM_FORKS.md),
with exact revisions recorded here. See the [documentation index](docs/index.md)
for source/build instructions and fork maintenance.

Development uses AI-assisted tools under maintainer review; see [CONTRIBUTING](CONTRIBUTING.md).

Original work is [GPL-3.0-or-later](LICENSING.md). The pass, pass-otp and other [upstream licenses](THIRD_PARTY.md) remain in force.

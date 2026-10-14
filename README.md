# pass and OTP packaging for Sailfish OS

Experimental packaging of pass 1.7.4 and pass-otp 1.2.0, using the isolated Sailfish GnuPG runtime. The repository also contains tree and OATH package recipes.

[Source adaptations](docs/UPSTREAM_FORKS.md) use upstream forks with pinned commit
bases. This repository contains packaging, wrappers and integration tests.

The launcher requires an explicitly selected private GnuPG home and password-store directory. The OTP patches send backend secrets through standard input. Package recipes, patches and test tools are in rpm/, patches/ and tools/; start with the [documentation index](docs/index.md).

Synthetic tests and a limited development trial exist. General migration, synchronization and production use remain outside the accepted scope. Package/provider compatibility and behavior on the current OS target still need verification.

Development uses AI-assisted tools under maintainer review. See [CONTRIBUTING](CONTRIBUTING.md) for review and testing requirements. Shared working agreements live in [sailfish-workspace](https://github.com/misja/sailfish-workspace).

Original work is [GPL-3.0-or-later](LICENSING.md). The pass, pass-otp and other [upstream licenses](THIRD_PARTY.md) remain in force.

See [fork and packaging maintenance](docs/FORK_WORKFLOW.md).

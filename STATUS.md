# Current source and delivery

Updated: 2026-10-17. Live release work: [package #1](https://github.com/misja/sailfish-password-store/issues/1)
and [workspace delivery #2](https://github.com/misja/sailfish-workspace/issues/2).
Misja decides merge/publication. A separate Release Manager owns presentation;
independent review checks package/source/signature evidence.

Pass 1.7.4-0.6 and OTP 1.2.0-0.6 now use the renamed GnuPG runtime 2.5.24-0.7.
Update the three packages together: old pass has an exact old-runtime dependency.
The coordinated transition passed an isolated copy of the SDK RPM database;
no payload or scriptlet was installed/executed by that metadata check.

The two upstream backports and private GnuPG/OATH binding remain unchanged.
Current binary/source RPMs built with the existing SDK and passed source/input,
namespace, scriptlet and dependency inspection. Tree/OATH outputs were reused.
See [the current packaging record](docs/packaging-06-20261017.json); the earlier
[backport record](docs/upstream-backports-20261016.json) retains historical hashes.

The private runtime removal hook has its own bounded synthetic Xperia5.2.0.20
confirmation. This is not a new full pass/OTP device trial or general migration,
synchronization or production acceptance. Public /usr/bin/pass ownership and
compatible GNU Bash remain installation considerations described in the README.

Draft refresh is in progress with signed RPMs and matching source RPMs. Existing
public source pins remain unchanged; no upstream submission or publication.

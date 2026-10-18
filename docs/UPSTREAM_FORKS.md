# pass and pass-otp source forks

The downstream source changes are maintained in:

- [misja/sailfish-pass](https://github.com/misja/sailfish-pass/tree/sailfish/private-gpg), from zx2c4/password-store
- [misja/pass-otp](https://github.com/misja/pass-otp/tree/sailfish/stdin-private-backend), from pass-extension/pass-otp

`sources.lock.json` records exact upstream bases and downstream commits. The
links above open the maintained adaptation branches; the lock identifies the
source revisions used for packaging. Fork
history preserves the upstream ancestry; review our changes against those bases.
The existing pass and pass-otp patches have the same code deltas as the fork
commits. Initial source files were compared with the authenticated cached
upstream archives before those commits were made.

Packaging still uses the locked upstream archive plus its patches. The fork
does not silently replace the authenticated source input or cause patching twice.
Wrappers, RPM recipes, source preparation and integration tests remain here.
The source forks keep upstream licenses; original independent integration work
is GPL-3.0-or-later.

A fork migration is source organization, not a new functional, native or release
acceptance result. Use this repository's issues for work and approved upstream
PRs for contributions to the original projects.

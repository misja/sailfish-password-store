# Current source status

Experimental packages; general release acceptance remains open.
Upstream review [#4](https://github.com/misja/sailfish-password-store/issues/4)
is complete: both source PRs, package PR #8 and workspace PR #11 are merged.
Current work: release preparation under [#1](https://github.com/misja/sailfish-password-store/issues/1)
and workspace delivery #2. Primary assistant prepares delivery; a separate reviewer
checks release evidence; Misja Hoebe decides release/publication.

Release bases stay pass 1.7.4 / OTP 1.2.0. Two attributed upstream backports
close tree FD3 and preserve an OTP append's last line without a newline.
Private GnuPG/OATH selection, seed stdin and diagnostic redaction are retained.
Fork pins, generated snapshots and recipes are updated together. Candidates are
pass 1.7.4-0.5 and OTP 1.2.0-0.5; pass binds reviewed runtime 2.5.24-0.6.

Focused host/SDK regressions reproduce the old errors and pass with the backports.
All four source-staging tests and 34 existing synthetic OTP checks pass. Both
changed binary/source RPMs built and passed inspection in the installed SDK
3.13.5 / SailfishOS-5.1.0.11-aarch64. Unchanged tree/OATH artifacts were reused.
See the [bounded record](docs/upstream-backports-20261016.json) for identities,
review and limitations. No package/dependency installation, device operation,
real-data access or upstream submission occurred. Device and release gates remain.
Separate source/artifact review found no blocker: four artifact hashes verified,
full packaged scripts match the reviewed forks after installation transforms,
and dependencies are coherent. This is not human security/release acceptance.

# Source snapshot and build prerequisites

This repository starts with selected prototype sources. Original operational
history, raw test reports, device inventories and binary/source archives are
kept separately. The initial commit identifies the local source basis; it
does not import that repository's original Git history.

Source identities are pinned in sources.lock.json where present. Obtain and
authenticate the upstream archives, public release keys and signatures before
building. A private key is not a build input.

Some tools expect sources and dated verification records under sources/,
artifacts/, build/ or evidence/. These inputs are not copied wholesale into
this source snapshot. SDK/device harnesses also require an explicitly approved
test environment. A clean-checkout build has not been established.

pass source staging requires authenticated archives, a public release key,
pass-tag-verification and tree-source records. Native pinentry packaging
requires the pinned Sailfish Secrets archive and matching Assuan sources.
Complete source and relink delivery remains a package distribution gate.

Production agent lifecycle, provider/upgrade behavior and exact Sailfish 5.2
vendor provenance remain open. Historical 5.2.0.18 results do not establish
acceptance on 5.2.0.20. Follow repository issues for the remaining work.

Original work is GPL-3.0-or-later, copyright (c) 2026 Misja Hoebe. See
[LICENSING](../LICENSING.md) and [upstream exceptions](../THIRD_PARTY.md).
Source publication is separate from package releases, device changes and
upstream submissions.

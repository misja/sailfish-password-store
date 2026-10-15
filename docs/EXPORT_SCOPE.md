# Source snapshot and build prerequisites

This repository starts with selected prototype sources. Original operational
history, raw test reports, device inventories and binary/source archives are
kept separately. The initial commit identifies the local source basis; it
does not import that repository's original Git history.

Source identities are pinned in sources.lock.json where present. Obtain and
authenticate the upstream archives, public release keys and signatures before
building. A private key is not a build input.

Public source archives and verification records can be recreated with the
sibling workspace's tools/fetch-sources.py. It uses temporary public-only keyrings
and preserves the existing archive/version/signer pins. See the
[public source bootstrap guide](https://github.com/misja/sailfish-workspace/blob/main/docs/development/source-bootstrap.md).
Generated sources/ and evidence/ inputs are ignored; do not copy historical
private trial evidence to satisfy staging.

SDK build entry points accept SAILFISH_SDK_ROOT and require an explicit
SAILFISH_SDK_TARGET. Follow the ordinary official SDK route, normally Docker
directly on Linux. The maintainer's outer LXC container is optional. Historical
test harnesses can still have fixed paths; a clean SDK build and complete
source/binary RPM acceptance remain open. Native vendor-source and relink inputs
are separate gates.

Production agent lifecycle, provider/upgrade behavior and exact Sailfish 5.2
vendor provenance remain open. Historical 5.2.0.18 results do not establish
acceptance on 5.2.0.20. Follow repository issues for the remaining work.

Original work is GPL-3.0-or-later, copyright (c) 2026 Misja Hoebe. See
[LICENSING](../LICENSING.md) and [upstream exceptions](../THIRD_PARTY.md).
Source publication is separate from package releases, device changes and
upstream submissions.

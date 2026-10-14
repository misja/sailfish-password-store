#!/usr/bin/env python3
"""Stage locked public sources and notices for all pass/OTP component recipes."""
import hashlib
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
lock = json.loads((root / "sources.lock.json").read_text())

def path(relative):
    target = root / relative
    if root.is_symlink() or any(p.is_symlink() for p in [target, *target.parents] if p != root.parent):
        raise SystemExit("Refusing source-staging symlink")
    return target

def require(condition, message):
    if not condition:
        raise SystemExit(message)

for component in ("pass", "tree", "pass_otp", "oath_toolkit"):
    entry = lock[component]
    filename = entry.get("archive") or f"pass-otp-{entry['version']}.tar.gz"
    require(hashlib.sha256(path("sources/" + filename).read_bytes()).hexdigest() == entry["sha256"],
            "Archive differs from lock: " + component)
verification = json.loads(path("evidence/pass-tag-verification.json").read_text())
require(verification["verify_tag_exit"] == 0 and
        verification["tag_object"] == lock["pass"]["tag_object"] and
        verification["commit"] == lock["pass"]["commit"] and
        verification["allowed_primary_fingerprint"] == lock["pass"]["primary_fingerprint"] and
        verification["verified_archive_sha256"] == lock["pass"]["sha256"],
        "Pass verification record does not match locked source")
for component, record in [("tree", "tree-source.json"), ("pass_otp", "pass-otp-source.json"),
                          ("oath_toolkit", "oath-source.json")]:
    evidence = json.loads(path("evidence/" + record).read_text())
    require(evidence["archive_sha256"] == lock[component]["sha256"],
            "Verification digest differs: " + component)
    if component == "oath_toolkit":
        require(evidence["primary_fingerprint"] == lock[component]["primary_fingerprint"] and
                evidence["signer_fingerprint"] == lock[component]["signer_fingerprint"] and
                evidence["verification"] == "gpg-detached-signature", "OATH verification differs")
notice = lock["bootstrap"]["oath_lgpl_notice"]
require(hashlib.sha256(path("sources/oath-COPYING.LESSER").read_bytes()).hexdigest() == notice["sha256"],
        "OATH LGPL notice differs from pin")
require(path("sources/pass-release-key.asc").is_file(), "Missing public pass release key")
copies = [
    ("LICENSE", "LICENSE"), ("LICENSING.md", "LICENSING.md"),
    ("rpm/private-gpg.patch", "private-gpg.patch"),
    ("runtime/sailfish-pass", "sailfish-pass"), ("sources.lock.json", "sources.lock.json"),
    ("patches/pass-otp-stdin.patch", "pass-otp-stdin.patch"),
    ("patches/pass-otp-private-backend.patch", "pass-otp-private-backend.patch"),
]
for name in ("pass-tag-verification.json", "tree-source.json", "oath-source.json"):
    copies.append(("evidence/" + name, name))
# Validate all source and destination paths before copying.
for source, destination in copies:
    require(path(source).is_file(), "Missing packaging input: " + source)
    path("sources/" + destination)
for source, destination in copies:
    shutil.copy2(path(source), path("sources/" + destination))
for directory in ("BUILD", "BUILDROOT", "RPMS", "SRPMS", "SPECS"):
    path("build/rpmbuild/" + directory).mkdir(parents=True, exist_ok=True)
print("Staged locked pass/tree/OTP/OATH sources, patches and notices; no build or install")
